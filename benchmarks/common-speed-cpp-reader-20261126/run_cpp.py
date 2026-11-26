import gzip,hashlib,json,os,platform,random,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def pair(file,flags,tag):
 runs={}
 for label in (['before','candidate'] if len(RESULT)%2==0 else ['candidate','before']):
  binary=ROOT/'install'/label/'bin/vcftools';prefix=ROOT/(tag+'-'+label)
  cmd=[str(binary),'--gzvcf' if str(file).endswith('.gz') else '--vcf',str(file)]+flags+['--out',str(prefix)]
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
 header='''##fileformat=VCFv4.1
##contig=<ID=22,length=51304566>
##contig=<ID=23,length=51304566>
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=GQ,Number=1,Type=Float,Description="Quality">
##FORMAT=<ID=FT,Number=1,Type=String,Description="Filter">
'''
 for seed in range(20):
  rng=random.Random(seed);n=rng.randrange(1,32);cols='#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t'+'\t'.join('S'+str(i) for i in range(n))+'\n';rows=[]
  for i in range(70):
   ref,alt=rng.choice([('A','G,C'),('AT','A,ATT'),('AC','GT,A')]);fmt=rng.choice(['GT','GT:DP:GQ','DP:GT:FT']);gt=[]
   for j in range(n):
    v={'GT':rng.choice(['0/0','0|1','1','./.','0/.','2/2','0/1/2']),'DP':str(rng.randrange(40)),'GQ':str(rng.randrange(50)),'FT':rng.choice(['PASS','.','q10'])}
    gt.append(':'.join(v[k] for k in fmt.split(':')))
   if i==69 and seed%3==0:gt=gt[:len(gt)//2]
   rows.append(f'{22+i//40}\t{i%40+1}\t.\t{ref}\t{alt}\t50\tPASS\t.\t{fmt}\t'+'\t'.join(gt)+'\n')
  f=D/'fuzz.vcf';f.write_text(header+cols+''.join(rows));other=D/'other.vcf';other.write_text(header+cols+''.join(rows[::2]))
  for i,flags in enumerate([['--freq'],['--missing-indv'],['--recode','--recode-INFO-all'],['--minDP','10','--minGQ','5','--recode','--recode-INFO-all'],['--recode-bcf'],['--diff',str(other),'--diff-site-discordance']]):pair(f,flags,f'fuzz-{seed}-{i}')
 real=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 cases=[('freq',['--freq']),('missing',['--missing-indv']),('het',['--het']),('recode',['--recode','--recode-INFO-all']),('filter',['--minQ','50','--max-missing','0.95','--recode','--recode-INFO-all'])]
 for name,flags in cases:
  for rep in range(3):pair(real,flags,f'real-{name}-{rep}')
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
try:main()
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
