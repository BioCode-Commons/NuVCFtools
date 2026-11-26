import json,os,subprocess,platform,hashlib,shutil
from pathlib import Path
R=Path(__file__).resolve().parent
O=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':O/'lib/perl5','before':R/'before/src/perl','candidate':R/'candidate/src/perl'}
BINS={'original':O/'bin','before':LIB['before'],'candidate':LIB['candidate']}
env=dict(os.environ,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
results=[]
def equal(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
try:
 subprocess.run(['python3',str(R/'candidate/tests/perl_stats_merge_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(R/'controls')],env=env,check=True)
 for n,source in [(500,Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')),(2504,Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz'))]:
  item={'tool':'vcf-stats','samples':n,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'measurements':{}}
  for label in ['original','before','candidate']:
   prefix=R/f'stats-{n}-{label}'
   with prefix.with_suffix('.out').open('wb') as out,prefix.with_suffix('.err').open('wb') as err:
    p=subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(prefix)+'.time','perl',str(BINS[label]/'vcf-stats'),str(source)],env=dict(env,PERL5LIB=str(LIB[label])),stdout=out,stderr=err,timeout=1200)
   vals=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
   item['measurements'][label]={'wall_seconds':float(vals[0]),'rss_kib':int(vals[1]),'user_seconds':float(vals[2]),'sys_seconds':float(vals[3]),'exit':p.returncode}
   (R/'progress.json').write_text(json.dumps(item,indent=2))
   if p.returncode:raise RuntimeError(f'{n} {label} exit {p.returncode}')
  ref=R/f'stats-{n}-original'
  item['passed']=all(equal(Path(str(ref)+suffix),R/f'stats-{n}-{label}{suffix}') for label in ['before','candidate'] for suffix in ['.out','.err'])
  results.append(item);(R/'results.json').write_text(json.dumps({'node':platform.node(),'job':os.environ['SLURM_JOB_ID'],'results':results},indent=2))
  if not item['passed']:raise RuntimeError(f'{n} mismatch')
  for label in LIB:
   for suffix in ['.out','.err']:(R/f'stats-{n}-{label}{suffix}').unlink()
 (R/'complete.json').write_text(json.dumps({'passed':True,'runs':6,'verified_raw_removed':True}))
except Exception as e:
 (R/'failure.txt').write_text(repr(e));raise
