import gzip,json,os,platform,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
def pair(files,window,tag):
 results={}
 for label in (['before','candidate']if len(RESULT)%2==0 else ['candidate','before']):
  lib=ROOT/label/'src/perl';prefix=ROOT/(tag+'-'+label);env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
  cmd=['perl',str(lib/'vcf-concat'),'-s',str(window)]+[str(x)for x in files]
  with Path(str(prefix)+'.stdout').open('wb')as out,Path(str(prefix)+'.stderr').open('wb')as err:r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(prefix)+'.time']+cmd,env=env,stdout=out,stderr=err,timeout=240)
  wall,rss=Path(str(prefix)+'.time').read_text().splitlines()[-1].split();err=Path(str(prefix)+'.stderr').read_bytes().replace(str(lib).encode(),b'<lib>');err=re.sub(rb'(<lib>/[^\s]+) line [0-9]+',rb'\1 line <source>',err)
  results[label]=({'wall_seconds':float(wall),'rss_kib':int(rss),'exit':r.returncode,'bytes':Path(str(prefix)+'.stdout').stat().st_size},Path(str(prefix)+'.stdout').read_bytes(),err)
 a,b=results['before'],results['candidate'];passed=a[0]['exit']==b[0]['exit']==0 and a[1:]==b[1:]
 RESULT.append({'case':tag,'input_files':len(files),'window':window,'before':a[0],'candidate':b[0],'passed':passed});(ROOT/'status.json').write_text(json.dumps({'job':os.environ.get('SLURM_JOB_ID'),'node':platform.node(),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Mismatch '+tag)
 for label in results:
  for ext in ['.stdout','.stderr','.time']:Path(str(ROOT/(tag+'-'+label))+ext).unlink()

def prepare(header,rows,count,mode):
 directory=D/f'{mode}-{count}';directory.mkdir();paths=[]
 for i in range(count):
  selected=rows[i::count]if mode=='interleaved'else rows[len(rows)*i//count:len(rows)*(i+1)//count]
  raw=directory/f'{i}.vcf';raw.write_text(''.join(header+selected));out=raw.with_suffix('.vcf.gz')
  with out.open('wb')as f:subprocess.run(['bgzip','-c',str(raw)],stdout=f,check=True)
  subprocess.run(['tabix','-p','vcf',str(out)],check=True);raw.unlink();paths.append(out)
 return paths
try:
 source=Path('/jobtmp/zliu328/nuvcftools-concat-tree-20261126/data')
 fixtures={(mode,n):[source/f'{mode}-{n}'/f'{i}.vcf.gz'for i in range(n)] for mode in ['contiguous','interleaved']for n in [2,8,32,128]}
 for(mode,n),files in fixtures.items():pair(files,n,f'real-{mode}-{n}')
 files=fixtures['interleaved',32];empty=source/'empty.vcf.gz'
 for width in [2,8]:pair(files,width,f'real-window-{width}')
 pair([empty]+files,8,'real-empty-first');pair(files[:16]+[empty]+files[16:],8,'real-empty-middle')
 for mode,n in [('contiguous',32),('interleaved',128)]:
  for rep in range(2):pair(fixtures[mode,n],n,f'real-repeat-{mode}-{n}-{rep}')
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT),'reuses_prepared_fixtures_from':str(source)}))
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
