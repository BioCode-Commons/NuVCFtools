import gzip,hashlib,importlib.util,json,os,platform,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent; R=ROOT/'third'; R.mkdir(exist_ok=True); D=R/'data'; D.mkdir(exist_ok=True)
O=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':O/'lib/perl5','before':ROOT/'before/src/perl','candidate':ROOT/'candidate3/src/perl'}
BIN={k:O/'bin' if k=='original' else v for k,v in LIB.items()}
ENV=dict(os.environ,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC')
RESULT=[]; CONTROLS=[]
def save():
 (R/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'before_commit':'e337a33bed983024349001bfdc16f46c89a07d50','controls':CONTROLS,'results':RESULT},indent=2))
def eq(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
def norm(b):
 for k,v in LIB.items():b=b.replace(str(v).encode(),b'<lib>')
 for k,v in BIN.items():b=b.replace(str(v).encode(),b'<lib>')
 b=re.sub(rb' line \d+',b' line <source>',b)
 b=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',b)
 return b
try:
 spec=importlib.util.spec_from_file_location('fixture',ROOT/'candidate3/tests/perl_stats_merge_regression.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 F=D/'controls';F.mkdir();mod.fixture(F)
 cases=[]
 for i,fmt in enumerate(['[%SAMPLE]','[%GT%SAMPLE]','[%SAMPLE%GT]','[%GTR]','[%SAMPLE:%GT:%DP]','[%SAMPLE:%*=,]','[%SAMPLE:%SAMPLE:%GT:%GT]','[%PL:%FA:%AD:%GT]','%CHROM:%POS[\\t%SAMPLE:%GTR]\\n']):
  cases.append((f'query-{i}','vcf-query',['-f',fmt,str(F/'all.vcf.gz')]))
 cases += [('query-selected','vcf-query',['-c','S7,S2,S7','-f','[%SAMPLE:%DP:%GT]',str(F/'all.vcf.gz')]),('query-region','vcf-query',['-r','22:20000011-20000300',str(F/'all.vcf.gz')]),('query-old','vcf-query',['--use-old-method',str(F/'all.vcf.gz')])]
 for label,args in [('all',['-c','S0,S1,S3,S9']),('trim',['-a','-c','S0,S2']),('private',['-p','-c','S0,S1']),('types',['-t','SNPs,indels']),('replace',['-r','-t','indels']),('uncalled',['-u','-c','S0'])]:cases.append(('subset-'+label,'vcf-subset',args+[str(F/'all.vcf.gz')]))
 # Malformed rows are deterministic diagnostic checks, not a fuzzer.
 header=(F/'all.vcf').read_text().splitlines(True)
 h=[line for line in header if line.startswith('#')]
 row=next(line for line in header if not line.startswith('#')).rstrip('\n').split('\t')
 for tag,values in [('extra',[x+':unexpected' for x in row[9:]]),('empty',['']+row[10:]),('short',row[9:-1]),('missing',['.']*32)]:
  path=F/(tag+'.vcf');path.write_text(''.join(h)+'\t'.join(row[:9]+values)+'\n')
  cases.append(('query-'+tag,'vcf-query',['-f','[%SAMPLE:%GT:%*=,]',str(path)]))
 for seed in [0,1,19]:
  for name,tool,args in cases:
   runs=[]
   for label in ['before','candidate']:
    p=subprocess.run(['perl',str(BIN[label]/tool)]+args,env=dict(ENV,PERL5LIB=str(LIB[label]),PERL_HASH_SEED=str(seed)),capture_output=True,timeout=60)
    runs.append((p.returncode,p.stdout,norm(p.stderr)))
   passed=runs[0]==runs[1]
   CONTROLS.append({'case':name,'seed':seed,'passed':passed,'exit':[x[0] for x in runs]});save()
   if not passed:
    for label,run in zip(['before','candidate'],runs):
     (R/f'failure-{name}-{label}.out').write_bytes(run[1]);(R/f'failure-{name}-{label}.err').write_bytes(run[2])
    raise RuntimeError('control '+name)
 subprocess.run(['python3',str(ROOT/'candidate3/tests/perl_stats_merge_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(R/'regression')],env=ENV,check=True)
 subprocess.run(['perl',str(ROOT/'candidate3/tests/readonly_genotypes.pl')],env=dict(ENV,PERL5LIB=str(LIB['candidate'])),check=True)
 input500=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
 input2504=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 bench=[]
 prep=time.monotonic()
 for n,src in [(500,input500),(2504,input2504)]:
  names=subprocess.check_output(['bcftools','query','-l',str(src)],text=True).splitlines()
  for side,subset in []:
   listing=D/f'{n}-{side}.samples';listing.write_text('\n'.join(subset)+'\n')
   out=D/f'{n}-{side}.vcf.gz'
   subprocess.run(['bcftools','view','--no-version','-S',str(listing),'-Oz','-o',str(out),str(src)],check=True)
   subprocess.run(['tabix','-p','vcf',str(out)],check=True)
  bench += [(f'subset-{n}','vcf-subset',['-c',str(ROOT/'data'/f'{n}-A.samples'),str(src)]),(f'merge-{n}','vcf-merge',[str(ROOT/'data'/f'{n}-A.vcf.gz'),str(ROOT/'data'/f'{n}-B.vcf.gz')])]
 (R/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-prep,'excluded_from_timing':True,'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [input500,input2504]}}))
 for index,(tag,tool,args) in enumerate(bench):
  row={'case':tag,'tool':tool,'args':args,'measurements':{}};paths={}
  labels=['original','before','candidate'];labels=labels[index%3:]+labels[:index%3]
  for label in labels:
   prefix=R/f'{tag}-{label}';paths[label]=prefix
   with Path(str(prefix)+'.out').open('wb') as out,Path(str(prefix)+'.err').open('wb') as err:
    p=subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(prefix)+'.time','perl',str(BIN[label]/tool)]+args,env=dict(ENV,PERL5LIB=str(LIB[label])),stdout=out,stderr=err,timeout=1800)
   t=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
   row['measurements'][label]={'wall_seconds':float(t[0]),'rss_kib':int(t[1]),'user_seconds':float(t[2]),'sys_seconds':float(t[3]),'exit':p.returncode,'output_bytes':Path(str(prefix)+'.out').stat().st_size}
   (R/'progress.json').write_text(json.dumps(row,indent=2))
   if p.returncode:raise RuntimeError(tag+' '+label+' failed')
  row['passed']=all(eq(Path(str(paths['original'])+'.out'),Path(str(p)+'.out')) and norm(Path(str(paths['original'])+'.err').read_bytes())==norm(Path(str(p)+'.err').read_bytes()) for p in paths.values())
  RESULT.append(row);save()
  if not row['passed']:raise RuntimeError(tag+' mismatch')
  for prefix in paths.values():
   for suffix in ['.out','.err']:Path(str(prefix)+suffix).unlink()
 (R/'complete.json').write_text(json.dumps({'passed':True,'runs':len(RESULT)*3,'verified_raw_removed':True}))
except Exception as e:
 (R/'failure.txt').write_text(repr(e));raise
