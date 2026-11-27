import gzip,hashlib,json,os,platform,re,shlex,subprocess,time,traceback
from pathlib import Path
R=Path(__file__).resolve().parent
D=R/'data';D.mkdir(exist_ok=True)
O=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':O/'lib/perl5','before':R/'before/src/perl','candidate':R/'candidate/src/perl'}
BIN={k:O/'bin' if k=='original' else v for k,v in LIB.items()}
ENV=dict(os.environ,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC')
results=[];controls=[]
def save(state):
 (R/'status.json').write_text(json.dumps(dict(state=state,node=platform.node(),job=os.getenv('SLURM_JOB_ID'),before='f7b152dfb10e674c65f2fa016409f61a65c7bedb',results=results,controls=controls),indent=2))
def norm(b):
 for p in list(LIB.values())+list(BIN.values()):b=b.replace(str(p).encode(),b'<source>')
 b=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',b)
 return re.sub(rb' line \d+',b' line <source>',b)
def equal(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
def runrow(tag,tool,args,stdin=None,compressed=False,labels=None,expected=True):
 row=dict(case=tag,tool=tool,args=args,stdin=str(stdin),measurements={});paths={}
 for label in labels or ['original','before','candidate']:
  pref=R/(tag+'-'+label);paths[label]=pref
  cmd=['perl',str(BIN[label]/tool)]+args
  if stdin:
   reader=['gzip','-dc',str(stdin)] if compressed else ['cat',str(stdin)]
   cmd=['bash','-o','pipefail','-c',shlex.join(reader)+' | '+shlex.join(cmd)]
  with pref.with_suffix('.out').open('wb') as out,pref.with_suffix('.err').open('wb') as err:
   p=subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(pref)+'.time']+cmd,env=dict(ENV,PERL5LIB=str(LIB[label])),stdout=out,stderr=err,timeout=1800)
  t=Path(str(pref)+'.time').read_text().splitlines()[-1].split()
  row['measurements'][label]=dict(wall_seconds=float(t[0]),rss_kib=int(t[1]),user_seconds=float(t[2]),sys_seconds=float(t[3]),exit=p.returncode,output_bytes=pref.with_suffix('.out').stat().st_size)
  (R/'progress.json').write_text(json.dumps(row,indent=2))
  if expected and p.returncode:raise RuntimeError(f'{tag} {label} exit {p.returncode}')
 base=next(iter(paths.values()))
 row['passed']=len({m['exit'] for m in row['measurements'].values()})==1 and all(equal(base.with_suffix('.out'),p.with_suffix('.out')) and norm(base.with_suffix('.err').read_bytes())==norm(p.with_suffix('.err').read_bytes()) for p in paths.values())
 results.append(row);save('running')
 if not row['passed']:raise RuntimeError(tag+' mismatch')
 for p in paths.values():
  p.with_suffix('.out').unlink();p.with_suffix('.err').unlink()
 return row
try:
 save('preparing')
 p500=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
 p2504=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 # Small deterministic controls exercise success, partial output on errors,
 # sample order, rich FORMATs, missing GT, and haploid/multiallelic alleles.
 header='##fileformat=VCFv4.2\n##contig=<ID=22,length=100000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tz\ta\tm\n'
 fixtures=[('diploid','A','C,G','GT:DP',['0/1:4','1|2:9','0/1:4'],True,[]),('haploid','T','C','GT',['0','1','.'],True,[]),('missing-gt','T','C','DP',['3','4','3'],True,[]),('iupac','A','G','GT',['0/1','1|0','./.'],True,['-i']),('iupac-error','A','AT','GT',['0/1','0/0','0/0'],False,['-i']),('invalid-gt','A','C','GT',['bad','0/0','0/0'],False,[]),('out-of-range','A','C','GT',['9/0','9/0','9/0'],True,[])]
 for seed in [0,1,19]:
  ENV['PERL_HASH_SEED']=str(seed)
  for tag,ref,alt,fmt,vals,success,flags in fixtures:
   f=D/(tag+'.vcf');f.write_text(header+'\t'.join(['22','100','.',ref,alt,'.','PASS','.',fmt]+vals)+'\n')
   runrow('control-'+tag+'-'+str(seed),'vcf-to-tab',flags,f,expected=success)
 ENV['PERL_HASH_SEED']='0'
 for n,p in [(500,p500),(2504,p2504)]:runrow('to-tab-'+str(n),'vcf-to-tab',[],p,True)
 for n,p in [(500,p500),(2504,p2504)]:runrow('sort-'+str(n),'vcf-sort',[],p,True)
 save('complete')
except Exception as e:
 save('failed');(R/'failure.txt').write_text(traceback.format_exc());raise
