import gzip,json,os,platform,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;D=ROOT/'data';D.mkdir(exist_ok=True);RESULT=[]
BASE=Path('/jobtmp/zliu328')
ORIGINAL=BASE/'nuvcftools-benchmark-20261121/install/VCFtools'
BINARY={'original':ORIGINAL/'bin/vcftools','before':BASE/'nuvcftools-cpp-reader-20261126/install/before/bin/vcftools','candidate':ROOT/'install/candidate/bin/vcftools'}
LIB={'original':ORIGINAL/'lib/perl5','before':BASE/'nuvcftools-common-speed-20261126/before/src/perl','candidate':ROOT/'source/src/perl'}
def equal(a,b):
 if a.stat().st_size!=b.stat().st_size:return False
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(4*1024*1024);v=y.read(4*1024*1024)
   if u!=v:return False
   if not u:return True

def norm_diag(data,label,prefix):
 data=data.replace(str(prefix).encode(),b'<output>').replace(str(LIB[label]).encode(),b'<lib>')
 data=data.replace(str(ORIGINAL/'bin').encode(),b'<scripts>')
 data=re.sub(rb'VCFtools \([^\n]*\)',b'VCFtools (<recorded-build-version>)',data)
 data=re.sub(rb'Run Time = [^\n]*',b'Run Time = <elapsed>',data)
 data=re.sub(rb'(<lib>/[^\s]+) line [0-9]+',rb'\1 line <source>',data)
 data=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',data)
 return data

def case(tag,tool,file,flags):
 records={};prefixes={};labels=['original','before','candidate'];shift=len(RESULT)%3;labels=labels[shift:]+labels[:shift]
 for label in labels:
  prefix=ROOT/(tag+'-'+label);prefixes[label]=prefix
  cmd=[str(BINARY[label]),'--gzvcf',str(file)]+flags+['--out',str(prefix)] if tool=='cpp' else ['perl',str((ORIGINAL/'bin' if label=='original' else LIB[label])/tool)]+flags+[str(file)]
  env=dict(os.environ,PERL5LIB=str(LIB[label]),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
  with Path(str(prefix)+'.stdout').open('wb') as out,Path(str(prefix)+'.stderr').open('wb') as err:r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(prefix)+'.time']+cmd,env=env,stdout=out,stderr=err,timeout=300)
  values=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
  scientific={p.name.removeprefix(prefix.name):p for p in ROOT.glob(prefix.name+'.*') if p.suffix not in ['.stderr','.time','.log']}
  records[label]={'wall_seconds':float(values[0]),'rss_kib':int(values[1]),'exit':r.returncode,'files':{k:p.stat().st_size for k,p in scientific.items()},'_files':scientific,'_diag':norm_diag(Path(str(prefix)+'.stderr').read_bytes(),label,prefix)}
 reference=records['original'];passed=all(x['exit']==0 and x['files']==reference['files'] and all(equal(p,reference['_files'][k])for k,p in x['_files'].items()) and x['_diag']==reference['_diag'] for x in records.values())
 RESULT.append({'case':tag,'tool':tool,'flags':flags,'measurements':{k:{a:b for a,b in v.items()if not a.startswith('_')}for k,v in records.items()},'passed':passed})
 (ROOT/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':RESULT},indent=2))
 if not passed:raise RuntimeError('Output/diagnostic mismatch or failed exit: '+tag)
 for prefix in prefixes.values():
  for p in ROOT.glob(prefix.name+'.*'):p.unlink()

try:
 small=BASE/'nuvcftools-expanded-20261121/data/cohort100.vcf.gz';large=small.with_name('cohort_all.vcf.gz')
 header=[]
 with gzip.open(small,'rt') as f:
  for line in f:
   if line.startswith('##'):header.append(line)
   elif line.startswith('#CHROM'):names=line.rstrip('\n').split('\t')[9:];break
 for tag,flags in [('frequency',['--freq']),('individual-missingness',['--missing-indv']),('site-missingness',['--missing-site']),('heterozygosity',['--het']),('rewrite-vcf',['--recode','--recode-INFO-all']),('filter-rewrite',['--minQ','50','--max-missing','0.95','--recode','--recode-INFO-all'])]:case(tag,'cpp',large,flags)
 for tag,tool,flags in [('validator','vcf-validator',[]),('subset-all','vcf-subset',['-c',','.join(names)]),('subset-types','vcf-subset',['-t','SNPs,indels']),('subset-private','vcf-subset',['-p','-c',','.join(names[:10])]),('stats','vcf-stats',[])]:case(tag,tool,small,flags)
 with gzip.open(large,'rt') as f:
  hdr=[]
  for line in f:
   hdr.append(line)
   if line.startswith('#CHROM'):
    cols=line.rstrip('\n').split('\t');hdr[-1]='\t'.join(cols[:9]+list(reversed(cols[9:])))+'\n';break
 template=D/'reverse-template.vcf';template.write_text(''.join(hdr));case('shuffle-columns','vcf-shuffle-cols',large,['-t',str(template)])
 (ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT),'runs':len(RESULT)*3}))
except Exception as e:(ROOT/'failure.txt').write_text(repr(e));raise
