import hashlib,json,os,platform,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent/'yang';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
base=Path('/jobtmp/zliu328')
bin={'original':base/'nuvcftools-benchmark-20261121/install/VCFtools/bin/vcftools','before':base/'nuvcftools-ld-native-standard-20261126/install/candidate/bin/vcftools','candidate':R.parent/'install/yang/bin/vcftools'}
results=[]
def equal(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True

def norm(b,p):
 b=b.replace(str(p).encode(),b'<output>')
 b=re.sub(rb'VCFtools \([^\n]*\)',b'VCFtools (<build>)',b)
 return re.sub(rb'Run Time = [^\n]*',b'Run Time = <elapsed>',b)

def run(tag,source,flags):
 records={};paths={}
 for label in bin:
  prefix=R/f'{tag}-{label}'; paths[label]=prefix
  cmd=[str(bin[label]),'--bcf' if source.suffix=='.bcf' else '--gzvcf' if source.suffix=='.gz' else '--vcf',str(source),'--relatedness']+flags+['--out',str(prefix)]
  with Path(str(prefix)+'.stdout').open('wb') as out,Path(str(prefix)+'.stderr').open('wb') as err:
   p=subprocess.run(['/usr/bin/time','-f','%e %M %U %S','-o',str(prefix)+'.time']+cmd,stdout=out,stderr=err,timeout=1200)
  v=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
  files={x.name.removeprefix(prefix.name):x for x in R.glob(prefix.name+'.*') if x.suffix not in ('.stderr','.log','.time')}
  records[label]={'wall_seconds':float(v[0]),'rss_kib':int(v[1]),'user_seconds':float(v[2]),'sys_seconds':float(v[3]),'exit':p.returncode,'files':{k:x.stat().st_size for k,x in files.items()},'_files':files,'_diag':norm(Path(str(prefix)+'.stderr').read_bytes(),prefix)}
  (R/'progress.json').write_text(json.dumps({'case':tag,'measurements':{k:{a:b for a,b in x.items() if not a.startswith('_')} for k,x in records.items()}},indent=2))
 ref=records['original'];passed=all(x['exit']==0 and x['files']==ref['files'] and all(equal(p,ref['_files'][k]) for k,p in x['_files'].items()) and x['_diag']==ref['_diag'] for x in records.values())
 row={'case':tag,'flags':flags,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'passed':passed,'measurements':{k:{a:b for a,b in x.items() if not a.startswith('_')} for k,x in records.items()}}
 results.append(row);(R/'results.json').write_text(json.dumps({'job':os.environ['SLURM_JOB_ID'],'node':platform.node(),'binary_sha256':{k:hashlib.sha256(x.read_bytes()).hexdigest() for k,x in bin.items()},'results':results},indent=2))
 if not passed:raise RuntimeError(tag+' output/diagnostics/exit mismatch')
 for p in paths.values():
  for f in R.glob(p.name+'.*'):
   if f.suffix!='.time':f.unlink()

try:
 names=['S'+str(i) for i in range(9)]
 header='##fileformat=VCFv4.2\n##contig=<ID=22,length=51304566>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Quality">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t'+'\t'.join(names)+'\n'
 calls=['0/0','0/1','1|1','./.','./1','1/0','0|1','0/.','1/1']
 rows=[]
 for i in range(140):
  alt='C,G' if i%17==0 else 'C';gt=[calls[(i+j)%len(calls)]+':'+str(5+j*5) for j in range(9)]
  if i%19==0:gt[0]='1:30'
  rows.append('22\t'+str(100+i)+'\t.\tA\t'+alt+'\t40\tPASS\t.\tGT:GQ\t'+'\t'.join(gt)+'\n')
 source=D/'mixed.vcf';source.write_text(header+''.join(rows));(D/'keep.txt').write_text('S0\nS3\nS7\n');(D/'empty.vcf').write_text(header)
 for tag,flags in [('mixed',[]),('keep',['--keep',str(D/'keep.txt')]),('filters',['--minGQ','20','--max-missing','0.1']),('stream',['--stdout'])]:run(tag,source,flags)
 run('empty',D/'empty.vcf',[])
 subprocess.run(['bcftools','view','--no-version','-Ob','-o',str(D/'mixed.bcf'),str(source)],check=True)
 run('bcf',D/'mixed.bcf',[])
 run('real500',base/'nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz',[])
 run('real2504-keep500',base/'nuvcftools-expanded-20261121/data/cohort_all.vcf.gz',['--keep',str(base/'nuvcftools-parallel-ld-20261126/data/samples500.txt')])
 (R/'complete.json').write_text(json.dumps({'passed':True,'cases':len(results),'runs':3*len(results),'verified_raw_removed':True}))
except Exception as e:(R/'failure.txt').write_text(repr(e));raise
