import json,os,platform,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;RESULT=[]
INPUT=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
BIN={'previous':Path('/jobtmp/zliu328/nuvcftools-ld-workspace-20261126/install/candidate/bin/vcftools'),'cxx11':Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/install/candidate/bin/vcftools'),'native':ROOT/'install/candidate/bin/vcftools'}
def same(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   p=x.read(1048576);q=y.read(1048576)
   if p!=q:return False
   if not p:return True
for trial in range(3):
 work=ROOT/('trial-'+str(trial));work.mkdir();runs={}
 order=['previous','cxx11','native'];order=order[trial:]+order[:trial]
 for label in order:
  prefix=work/label
  cmd=[str(BIN[label]),'--gzvcf',str(INPUT),'--geno-chisq','--ld-window-bp','1000','--temp','/tmp','--out',str(prefix)]
  with Path(str(prefix)+'.stdout').open('wb') as out,Path(str(prefix)+'.stderr').open('wb') as err:r=subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(prefix)+'.time']+cmd,stdout=out,stderr=err,timeout=120)
  v=Path(str(prefix)+'.time').read_text().splitlines()[-1].split();diag=Path(str(prefix)+'.stderr').read_bytes().replace(str(prefix).encode(),b'<out>');diag=re.sub(rb'Run Time = [^\n]*',b'Run Time = <elapsed>',diag)
  runs[label]={'exit':r.returncode,'wall_seconds':float(v[0]),'rss_kib':int(v[1]),'user_seconds':float(v[2]),'system_seconds':float(v[3]),'_diag':diag,'_files':{p.suffix:p for p in work.glob(label+'.*') if p.suffix not in ['.stderr','.time','.log']}}
 ref=runs['previous'];passed=all(r['exit']==0 and r['_diag']==ref['_diag'] and r['_files'].keys()==ref['_files'].keys() and all(same(p,ref['_files'][k]) for k,p in r['_files'].items()) for r in runs.values())
 RESULT.append({'trial':trial,'order':order,'passed':passed,'measurements':{k:{a:b for a,b in v.items() if not a.startswith('_')} for k,v in runs.items()}})
 (ROOT/'status.json').write_text(json.dumps({'job':os.environ.get('SLURM_JOB_ID'),'node':platform.node(),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Mismatch')
 shutil.rmtree(work)
(ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
