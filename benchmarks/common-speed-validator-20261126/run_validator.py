import gzip,json,os,platform,random,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def save(): (ROOT/'status.json').write_text(json.dumps({'job':os.environ.get('SLURM_JOB_ID'),'node':platform.node(),'results':RESULT},indent=2))
def execute(label,file,flags,tag,seed):
 lib=ROOT/label/'src/perl';env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C')
 out=ROOT/(tag+'-'+label+'.out');err=ROOT/(tag+'-'+label+'.err');tm=ROOT/(tag+'-'+label+'.time')
 with out.open('wb') as f,err.open('wb') as e:r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(tm),'perl',str(lib/'vcf-validator')]+flags+[str(file)],stdout=f,stderr=e,env=env,timeout=240)
 stats=tm.read_text().splitlines()[-1].split();diag=err.read_bytes().replace(str(lib).encode(),b'<lib>');diag=re.sub(rb'<lib>/([^\s]+) line [0-9]+',rb'<lib>/\1 line <source>',diag)
 out_bytes=out.read_bytes().replace(str(lib).encode(),b'<lib>');out_bytes=re.sub(rb'<lib>/([^\s]+) line [0-9]+',rb'<lib>/\1 line <source>',out_bytes)
 return {'wall_seconds':float(stats[0]),'rss_kib':int(stats[1]),'exit':r.returncode,'stdout_bytes':out.stat().st_size,'stderr_bytes':len(diag)},out_bytes,diag

def pair(file,flags,tag,seed=0):
 order=['before','candidate'] if len(RESULT)%2==0 else ['candidate','before'];r={label:execute(label,file,flags,tag,seed) for label in order};a,b=r['before'],r['candidate'];passed=a[0]['exit']==b[0]['exit'] and a[1:]==b[1:]
 RESULT.append({'case':tag,'input':str(file),'flags':flags,'seed':seed,'before':a[0],'candidate':b[0],'passed':passed});save()
 if not passed:raise RuntimeError('Mismatch '+tag)
 if tag.startswith('real') and a[0]['exit']!=0:raise RuntimeError('Real input failed')
 for label in order:
  for ext in ('.out','.err','.time'):(ROOT/(tag+'-'+label+ext)).unlink()

def main():
 for seed in range(20):
  rng=random.Random(seed);f=D/'fuzz.vcf';version=['3.3','4.0','4.1','4.2'][seed%4]
  head='##fileformat=VCFv'+version+'\n'+''.join((f'##FORMAT={k},{n},{t},"test"\n' if version=='3.3' else f'##FORMAT=<ID={k},Number={n},Type={t},Description="test">\n') for k,n,t in [('GT','1','String'),('DP','1','Integer'),('PL','G','Integer'),('AD','R','Integer'),('FA','A','Float')])
  head+='#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t'+'\t'.join('S'+str(i) for i in range(16))+'\n'
  rows=[]
  for i in range(35):
   fmt=rng.choice(['GT','GT:DP','GT:PL:AD:FA','DP:GT','GT:XX']);alts=rng.choice(['G','G,C','.']);samples=[]
   for j in range(16):
    values={'GT':rng.choice(['0/0','0|1','1','./.','0/1/2','X/1','9/0','0/','-1','0//1']),'DP':rng.choice(['5','.','-2','X']),'PL':rng.choice(['0,10,20','0,1,2,3,4,5','.','0,1']),'AD':rng.choice(['1,2','1,2,3','.']),'FA':rng.choice(['0.1','0.2,0.3','.']),'XX':'1'}
    samples.append(':'.join(values[k] for k in fmt.split(':')))
   rows.append('22\t'+str(1+i//2)+'\t.\tA\t'+alts+'\t50\tPASS\t.\t'+fmt+'\t'+'\t'.join(samples)+'\n')
  f.write_text(head+''.join(rows))
  for flags in ([],['-d'],['-u']):pair(f,flags,'fuzz-'+str(seed)+'-'+str(len(RESULT)),seed)
 real=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz')
 for rep in range(3):pair(real,[],'real100-'+str(rep))
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
try:main()
except Exception as e:
 (ROOT/'failure.txt').write_text(repr(e));raise
