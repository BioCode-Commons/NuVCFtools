import hashlib,json,os,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tests'))
from perl_stats_merge_regression import fixture
D=R/'regression-data';D.mkdir(exist_ok=True)
fixture(D)
cases=[('query-basic','vcf-query',['-f','%CHROM\\t%POS[\\t%SAMPLE=%GTR]\\n',str(D/'all.vcf.gz')]),
('query-rich','vcf-query',['-f','%CHROM:%POS:%INFO/DP[\\t%SAMPLE=%GT:%DP:%AD:%PL]\\n',str(D/'all.vcf.gz')]),
('query-subset','vcf-query',['-c','S0,S3,S9','-f','%REF/%ALT[\\t%SAMPLE=%GTR:%FA]\\n',str(D/'all.vcf.gz')]),
('query-plain','vcf-query',['-f','%LINE[\\t%SAMPLE=%GTR]\\n',str(D/'all.vcf')]),
('compare-genotypes','vcf-compare',['-g',str(D/'all.vcf.gz'),str(D/'all.vcf.gz')]),
('compare-subset','vcf-compare',['-g','-s','S0,S3,S9',str(D/'all.vcf.gz'),str(D/'all.vcf.gz')]),
('compare-filter','vcf-compare',['-g','-a',str(D/'all.vcf.gz'),str(D/'all.vcf.gz')]),
('compare-positions','vcf-compare',[str(D/'all.vcf.gz'),str(D/'all.vcf.gz')])]
S={'state':'running','cases':[]};p=R/'metadata/regression.json'
def save():p.write_text(json.dumps(S,indent=2)+'\n')
save()
try:
 for seed in ('0','1'):
  for name,tool,args in cases:
   results={}
   for v in ('Original','Before','After'):
    base=R/'versions'/v;env=dict(os.environ,PERL5LIB=str(base/'lib/perl5'),PERL_HASH_SEED=seed,PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC')
    proc=subprocess.run(['perl',str(base/'bin'/tool)]+args,capture_output=True,env=env,timeout=60)
    results[v]=(proc.returncode,proc.stdout,proc.stderr)
   hashes={v:hashlib.sha256(x[1]).hexdigest() for v,x in results.items()}
   c={'name':name,'seed':seed,'passed':results['Original']==results['Before']==results['After'] and results['After'][0]==0,'stdout_sha256':hashes,'exit_codes':{v:x[0] for v,x in results.items()}}
   S['cases'].append(c);save()
   if not c['passed']:
    evidence=R/'regression-mismatch'/name/seed;evidence.mkdir(parents=True,exist_ok=True)
    for v,x in results.items():
     (evidence/(v+'.stdout')).write_bytes(x[1]);(evidence/(v+'.stderr')).write_bytes(x[2])
    raise RuntimeError('Regression mismatch: '+name+' seed '+seed)
 S['state']='complete';save()
 for x in D.iterdir():x.unlink()
 D.rmdir()
except BaseException as e:
 S.update(state='failed',error=str(e));save();raise
