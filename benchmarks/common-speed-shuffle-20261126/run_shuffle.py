import json,os,platform,random,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def pair(file,mode,tag):
 runs={}
 for label in (['before','candidate'] if len(RESULT)%2==0 else ['candidate','before']):
  lib=ROOT/label/'src/perl';stem=ROOT/(tag+'-'+label);env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
  cmd=['perl',str(lib/'vcf-shuffle-cols'),'-t',str(D/(mode+'.vcf')),str(file)]
  with open(str(stem)+'.out','wb') as out,open(str(stem)+'.err','wb') as err:r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(stem)+'.time']+cmd,env=env,stdout=out,stderr=err,timeout=240)
  wall,rss=Path(str(stem)+'.time').read_text().splitlines()[-1].split();raw=Path(str(stem)+'.out').read_bytes();err=Path(str(stem)+'.err').read_bytes().replace(str(lib).encode(),b'<lib>');err=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',err);err=re.sub(rb'(<lib>/[^\s]+) line [0-9]+',rb'\1 line <source>',err)
  runs[label]=({'wall_seconds':float(wall),'rss_kib':int(rss),'exit':r.returncode,'bytes':len(raw)},raw,err)
 a,b=runs['before'],runs['candidate'];passed=a[0]['exit']==b[0]['exit'] and a[1:]==b[1:];RESULT.append({'case':tag,'mode':mode,'before':a[0],'candidate':b[0],'passed':passed});(ROOT/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Mismatch '+tag)
 if tag.startswith('real') and a[0]['exit']:raise RuntimeError('Real input failed')
 for label in runs:
  for ext in ['.out','.err','.time']:Path(str(ROOT/(tag+'-'+label))+ext).unlink()

import gzip
try:
 for dataset in ['cohort100','cohort_all']:
  real=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data')/(dataset+'.vcf.gz')
  header=[]
  with gzip.open(real,'rt') as f:
   for line in f:
    if line.startswith('##'):header.append(line)
    elif line.startswith('#CHROM'):
     columns=line.rstrip('\n').split('\t');break
  for mode in ['same','reverse']:
   cols=columns[:9]+(columns[9:] if mode=='same' else list(reversed(columns[9:])))
   (D/(mode+'.vcf')).write_text(''.join(header)+'\t'.join(cols)+'\n')
   for rep in range(3):pair(real,mode,f'real-{dataset}-{mode}-{rep}')
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
