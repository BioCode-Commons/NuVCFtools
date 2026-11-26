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
 source=Path('/jobtmp/zliu328/nuvcftools-concat-tree-20261126/data/contiguous-2/0.vcf.gz')
 pair([source],1,'real-single-input')
 pair([source,source],2,'real-duplicate-input')
 # Exercise the pre-existing object API as well as the CLI's class helper.
 values={}
 for label in ['before','candidate']:
  lib=ROOT/label/'src/perl';env=dict(os.environ,PERL5LIB=str(lib))
  command=['perl','-MVcf','-e','my $v=Vcf->new(file=>$ARGV[0]); print join("\n",@{$v->get_chromosomes()}),"\n";',str(source)]
  result=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
  values[label]=(result.stdout,result.stderr)
 if values['before']!=values['candidate']:raise RuntimeError('Object API chromosome list mismatch')
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT),'object_chromosome_api_passed':True}))
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
