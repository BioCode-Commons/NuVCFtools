import hashlib,json,os,platform,shutil,signal,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1];D=R/'data';M=R/'metadata';O=R/'results';W=R/'runs'
W.mkdir(exist_ok=True)
def save(p,d):
    q=p.with_suffix('.tmp');q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def equal(a,b):
    with a.open('rb') as x,b.open('rb') as y:
        while True:
            p=x.read(1048576);q=y.read(1048576)
            if p!=q:return False
            if not p:return True
def guard():
    size=sum(p.stat().st_size for base in (D,W) for p in base.rglob('*') if p.is_file())
    if size>4*1024**3 or shutil.disk_usage(R).free<4*1024**3:raise RuntimeError('Disk guard')
S={'state':'running','job':os.environ['SLURM_JOB_ID'],'node':platform.node(),'affinity':sorted(os.sched_getaffinity(0)),
   'repetitions':1,'cases':[],
   'commits':{'Original':'1f87a83402ffd17ea2723a456b7edf5d80b4a22c','Before':'be50ce72d8ec05894317e385d9fd6d7802f18d70','After':'54ee384e01a28f067de7160d617c2df7cec56dfe'},
   'time_scope':'Uninstrumented end-to-end process: startup, reading/decompression, computation, output writing. Input preparation/indexing and output comparison excluded.',
   'rss_scope':'GNU time maximum RSS (KiB), including accounted child maxima; not the sum of simultaneous process-tree RSS.',
   'comparison':'Every stdout and stderr byte, no normalization, against Original and Before. Fixed PERL_HASH_SEED=0/PERL_PERTURB_KEYS=0 for legacy hash-ordered output.',
   'input_scope':'1000 Genomes Phase 3 chr22:20000001-21000000, 22382 real records, first 100/400 samples. Compare uses alternate-record subset. FORMAT=GT. Rich FORMAT correctness checked separately.'}
save(O/'summary.json',S)
start=time.monotonic()
try:
    if len(S['affinity'])!=1:raise RuntimeError('Expected one bound physical core')
    assert json.loads((M/'prepare.json').read_text())['state']=='complete'
    identities=json.loads((M/'frozen.json').read_text())
    def check_product():
        for path,digest in identities['sha256'].items():
            if sha(R/path)!=digest:raise RuntimeError('Product changed: '+path)
    check_product()
    for name,v in json.loads((M/'inputs.json').read_text())['files'].items():
        if sha(D/name)!=v['sha256']:raise RuntimeError('Input changed: '+name)
    # Synthetic VCF with rich FORMAT and diverse ALT/GT patterns; full bytes.
    subprocess.run(['python3',str(R/'harness/regression.py')],check=True)
    S['regression_checks_passed']=True;save(O/'summary.json',S)
    with (M/'runtime.txt').open('w') as f:
        subprocess.run(['lscpu'],stdout=f,check=True)
        subprocess.run(['perl','-V'],stdout=f,check=True)
        subprocess.run(['bcftools','--version'],stdout=f,check=True)
    cases=[(tool,n) for n in (100,400) for tool in ('vcf-query','vcf-compare')]
    for i,(tool,n) in enumerate(cases):
        versions=['Original','Before','After'];versions=versions[i%3:]+versions[:i%3]
        c={'tool':tool,'samples':n,'records':22382,'order':versions,'runs':{}};S['cases'].append(c)
        args=['-f','%CHROM\t%POS[\t%SAMPLE=%GTR]\n',str(D/('cohort'+str(n)+'.vcf.gz'))] if tool=='vcf-query' else ['-g',str(D/('cohort'+str(n)+'.vcf.gz')),str(D/('compare'+str(n)+'.vcf.gz'))]
        for version in versions:
            guard();p=W/(tool+'-'+str(n)+'-'+version);p.mkdir()
            v=R/'versions'/version
            env=dict(os.environ,PERL5LIB=str(v/'lib/perl5'),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC')
            command=['perl',str(v/'bin'/tool)]+args
            print('START',tool,n,version,flush=True);save(O/'summary.json',S)
            with (p/'stdout').open('wb') as out,(p/'stderr').open('wb') as err:
                proc=subprocess.Popen(['/usr/bin/time','-f','%e\t%U\t%S\t%M\t%x','-o',str(p/'time.tsv')]+command,cwd=p,env=env,stdout=out,stderr=err,start_new_session=True)
                deadline=time.monotonic()+1200
                while proc.poll() is None:
                    if time.monotonic()>deadline:
                        os.killpg(proc.pid,signal.SIGKILL);proc.wait();raise RuntimeError('Timeout')
                    guard();time.sleep(2)
            if proc.returncode:raise RuntimeError('Command failed: '+tool+' '+version)
            t=(p/'time.tsv').read_text().strip().split('\t')
            m={'wall_seconds':float(t[0]),'user_seconds':float(t[1]),'system_seconds':float(t[2]),'peak_rss_kib':int(t[3]),'exit_code':proc.returncode,'command':command,
               'outputs':{k:{'bytes':(p/k).stat().st_size,'sha256':sha(p/k)} for k in ('stdout','stderr')}}
            c['runs'][version]=m;save(O/'summary.json',S);print('FINISH',tool,n,version,m['wall_seconds'],flush=True)
        c['comparison']={}
        for ref in ('Original','Before'):
            a=W/(tool+'-'+str(n)+'-After');b=W/(tool+'-'+str(n)+'-'+ref)
            c['comparison'][ref]={k:equal(a/k,b/k) for k in ('stdout','stderr')}
        c['passed']=all(x for d in c['comparison'].values() for x in d.values())
        save(O/'summary.json',S)
        if not c['passed']:raise RuntimeError('Output mismatch; all raw files retained')
        for version in versions:
            p=W/(tool+'-'+str(n)+'-'+version)
            shutil.copy2(p/'time.tsv',O/(p.name+'-time.tsv'))
            for k in ('stdout','stderr'):(p/k).unlink()
            (p/'time.tsv').unlink();p.rmdir()
        c['verified_output_cleanup']='complete';save(O/'summary.json',S)
    check_product()
    # Delete only inputs created for this task after all comparisons pass.
    for p in D.iterdir():
        if p.is_file():p.unlink()
    D.rmdir();W.rmdir()
    S.update(state='complete',elapsed_seconds=time.monotonic()-start,input_cleanup='complete',product_identity_rechecked=True)
    save(O/'summary.json',S)
except BaseException as e:
    S.update(state='failed',error=str(e),elapsed_seconds=time.monotonic()-start);save(O/'summary.json',S);raise
