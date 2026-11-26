import gzip,hashlib,json,os,platform,random,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def pair(file,flags,tag):
 runs={}
 for label in (['before','candidate'] if len(RESULT)%2==0 else ['candidate','before']):
  binary=ROOT/'install'/label/'bin/vcftools';prefix=ROOT/(tag+'-'+label)
  cmd=[str(binary),'--bcf' if str(file).endswith('.bcf') else '--gzvcf' if str(file).endswith('.gz') else '--vcf',str(file)]+flags+['--out',str(prefix)]
  with open(str(prefix)+'.stdout','wb') as out,open(str(prefix)+'.stderr','wb') as err:
   r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(prefix)+'.time']+cmd,stdout=out,stderr=err,timeout=240)
  stats=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
  files={p.name.removeprefix(prefix.name):p.read_bytes() for p in ROOT.glob(prefix.name+'.*') if p.suffix not in ('.log','.time','.stdout','.stderr')}
  diagnostics=Path(str(prefix)+'.stderr').read_bytes().replace(str(prefix).encode(),b'<output>')
  diagnostics=re.sub(rb'Run Time = [^\n]*',b'Run Time = <elapsed>',diagnostics)
  runs[label]=({'wall_seconds':float(stats[0]),'rss_kib':int(stats[1]),'exit':r.returncode,'files':{k:len(v) for k,v in files.items()}},files,Path(str(prefix)+'.stdout').read_bytes(),diagnostics)
 a,b=runs['before'],runs['candidate'];passed=a[0]['exit']==b[0]['exit'] and a[1:]==b[1:]
 RESULT.append({'case':tag,'flags':flags,'input':str(file),'before':a[0],'candidate':b[0],'passed':passed});(ROOT/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Mismatch '+tag)
 if tag.startswith('real') and a[0]['exit']:raise RuntimeError('Real input failed')
 for label in runs:
  for p in ROOT.glob(tag+'-'+label+'.*'):p.unlink()

def main():
 real=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 import gzip
 with gzip.open(real,'rt') as f:
  for line in f:
   if line.startswith('#CHROM'):names=line.rstrip().split('\t')[9:];break
 keep=D/'keep.txt';keep.write_text('\n'.join(names[::2])+'\n')
 cases=[('missing-indv',['--missing-indv']),('missing-site',['--missing-site']),('kept-indv',['--keep',str(keep),'--missing-indv']),('kept-site',['--keep',str(keep),'--missing-site']),('filtered',['--minGQ','5','--minDP','10','--missing-indv'])]
 for name,flags in cases:
  for rep in range(3):pair(real,flags,f'real-{name}-{rep}')
 # Native BCF output uses the same legacy reader/writer version as this tool.
 small=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz')
 prep=D/'prepared';r=subprocess.run([str(ROOT/'install/before/bin/vcftools'),'--gzvcf',str(small),'--recode-bcf','--out',str(prep)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
 bcf=Path(str(prep)+'.recode.bcf')
 for mode in ['--missing-indv','--missing-site']:
  pair(bcf,[mode],f'real-bcf-{mode[2:]}')
 for p in D.glob('prepared.*'):p.unlink()
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
try:main()
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
