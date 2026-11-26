import gzip,json,os,platform,random,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def norm(b,lib):
 b=b.replace(str(lib).encode(),b'<lib>');b=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',b);return re.sub(rb'<lib>/([^\s]+) line [0-9]+',rb'<lib>/\1 line <source>',b)
def pair(file,flags,tag,seed=0):
 result={}
 for label in (['before','candidate'] if len(RESULT)%2==0 else ['candidate','before']):
  lib=ROOT/label/'src/perl';env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C');stem=ROOT/(tag+'-'+label)
  with open(str(stem)+'.out','wb') as f,open(str(stem)+'.err','wb') as e:
   p=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(stem)+'.time','perl',str(lib/'vcf-subset')]+flags+[str(file)],stdout=f,stderr=e,env=env,timeout=240)
  raw=Path(str(stem)+'.out').read_bytes();err=norm(Path(str(stem)+'.err').read_bytes(),lib);stats=Path(str(stem)+'.time').read_text().splitlines()[-1].split()
  result[label]=({'wall_seconds':float(stats[0]),'rss_kib':int(stats[1]),'exit':p.returncode,'bytes':len(raw)},raw,err)
 a,b=result['before'],result['candidate'];passed=a[0]['exit']==b[0]['exit'] and a[1:]==b[1:]
 RESULT.append({'case':tag,'flags':flags,'before':a[0],'candidate':b[0],'passed':passed});(ROOT/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Mismatch '+tag)
 if tag.startswith('real') and a[0]['exit']:raise RuntimeError('Real input failed')
 for label in result:
  for ext in ('.out','.err','.time'):Path(str(ROOT/(tag+'-'+label))+ext).unlink()

def main():
 cases=[['-c','S0,S3,S7','-u'],['-c','S0,S3,S7','-e'],['-c','S0,S3,S7','-a'],['-c','S0,S3,S7','-p'],['-c','S0,S3,S7','-t','SNPs,indels'],['-c','S0,S3,S7','-r','-t','ref,indels','-u'],['-c','S0,S3,S7','-a','-p','-e'],['-c','S0,S3,S7','-t','MNPs,other','-u']]
 for seed in range(12):
  rng=random.Random(seed);f=D/'fuzz.vcf';header='##fileformat=VCFv4.1\n'+''.join(f'##FORMAT=<ID={k},Number={n},Type={t},Description="test">\n' for k,n,t in [('GT','1','String'),('DP','1','Integer'),('PL','G','Integer'),('AD','R','Integer')])
  header+='#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t'+'\t'.join('S'+str(i) for i in range(24))+'\n';rows=[]
  for i in range(60):
   ref,alt=rng.choice([('A','G,C'),('AT','A,ATT'),('AC','GT,A'),('G','<DEL>,*')]);fmt=rng.choice(['GT','GT:DP','GT:PL:AD','DP:GT']);samples=[]
   for j in range(24):
    gt=rng.choice(['0/0','0/1','1|0','1','./.','0/.','2/2','0/1/2'])
    if i==59 and seed%3==0 and j==0:gt=rng.choice(['99/0','0/0/','X/1'])
    vals={'GT':gt,'DP':str(rng.randrange(40)),'PL':'0,1,2,3,4,5','AD':'1,2,3'};samples.append(':'.join(vals[k] for k in fmt.split(':')))
   rows.append(f'22\t{i+1}\t.\t{ref}\t{alt}\t50\tPASS\t.\t{fmt}\t'+'\t'.join(samples)+'\n')
  f.write_text(header+''.join(rows))
  for i,flags in enumerate(cases):pair(f,flags,f'fuzz-{seed}-{i}',seed)
 source=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz')
 with gzip.open(source,'rt') as f:
  for line in f:
   if line.startswith('#CHROM'):names=line.rstrip().split('\t')[9:];break
 realcases=[('select10',['-c',','.join(names[:10])]),('select100',['-c',','.join(names)]),('types100',['-t','SNPs,indels']),('trim100',['-a','-c',','.join(names)]),('private10',['-p','-c',','.join(names[:10])])]
 for name,flags in realcases:
  for rep in range(3):pair(source,flags,f'real-{name}-{rep}')
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
try:main()
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
