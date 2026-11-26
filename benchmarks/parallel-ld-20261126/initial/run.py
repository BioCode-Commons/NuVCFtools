import gzip, hashlib, json, os, platform, re, resource, shutil, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
BASE=Path('/jobtmp/zliu328')
INPUT=BASE/'nuvcftools-expanded-20261121/data'
BIN={'before':BASE/'nuvcftools-ld-workspace-20261126/install/candidate/bin/vcftools',
     'candidate':ROOT/'install/candidate/bin/vcftools',
     'original':BASE/'nuvcftools-benchmark-20261121/install/VCFtools/bin/vcftools'}
MODE=sys.argv[1]; RESULTS=[]
def save():
 p=ROOT/(MODE+'-status.json')
 p.with_suffix('.tmp').write_text(json.dumps({'job':os.environ.get('SLURM_JOB_ID'),'node':platform.node(),'results':RESULTS},indent=2));p.with_suffix('.tmp').replace(p)
def equal(a,b):
 if a.stat().st_size!=b.stat().st_size:return False
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1024*1024);v=y.read(1024*1024)
   if u!=v:return False
   if not u:return True
def normalize(p,prefix,tmp):
 s=p.read_bytes().replace(str(prefix).encode(),b'<output>').replace(str(tmp).encode(),b'<temp>')
 s=re.sub(rb'Run Time = [^\n]*',b'Run Time = <elapsed>',s)
 s=re.sub(rb'VCFtools (?:\([^\n]*\)|- [^\n]*)',b'VCFtools <build>',s)
 s=re.sub(rb'^\t--ld-threads [^\n]*\n',b'',s,flags=re.M)
 return s

def run(tag,label,cores,file,flags):
 work=ROOT/'runs'/tag;work.mkdir(parents=True,exist_ok=True)
 prefix=work/label;tmp=ROOT/'temp';tmp.mkdir(exist_ok=True)
 binary='candidate' if label.startswith('candidate') else label
 cmd=[str(BIN[binary]),'--bcf' if str(file).endswith('.bcf') else '--gzvcf' if str(file).endswith('.gz') else '--vcf',str(file)]+flags
 if binary=='candidate':cmd+=['--ld-threads',str(cores)]
 cmd+=['--temp',str(tmp),'--out',str(prefix)]
 with Path(str(prefix)+'.stdout').open('wb') as out,Path(str(prefix)+'.stderr').open('wb') as err:
  result=subprocess.run(['srun','--exact','-n1','-c',str(cores),'--cpu-bind=cores','/usr/bin/time','-f','%e %M %U %S','-o',str(prefix)+'.time']+cmd,stdout=out,stderr=err,timeout=1800)
 values=Path(str(prefix)+'.time').read_text().splitlines()[-1].split()
 scientific={p.name[len(prefix.name):]:p for p in work.glob(prefix.name+'.*') if p.suffix not in ('.stderr','.log','.time')}
 return {'exit':result.returncode,'cores':cores,'wall_seconds':float(values[0]),'rss_kib':int(values[1]),'user_cpu_seconds':float(values[2]),'system_cpu_seconds':float(values[3]),'command':cmd,'files':{k:p.stat().st_size for k,p in scientific.items()},'temp_files_remaining':len(list(tmp.iterdir()))},scientific,normalize(Path(str(prefix)+'.stderr'),prefix,tmp),work

def case(tag,file,flags,labels):
 evidence={};reference=None;passed=True
 for label,cores in labels:
  r=run(tag,label,cores,file,flags);evidence[label]=r[0]
  if reference is None:reference=r
  ok=r[0]['exit']==0 and r[0]['temp_files_remaining']==0 and r[0]['files']==reference[0]['files'] and r[2]==reference[2] and all(equal(p,reference[1][k]) for k,p in r[1].items())
  passed=passed and ok
  if not ok:
   RESULTS.append({'case':tag,'passed':False,'measurements':evidence});save();raise RuntimeError('Output/diagnostic/cleanup mismatch: '+tag+' '+label)
 RESULTS.append({'case':tag,'passed':passed,'measurements':evidence});save()
 shutil.rmtree(reference[3])

def prepare():
 start=time.monotonic();header=[];rows=[]
 with gzip.open(INPUT/'cohort100.vcf.gz','rt') as f:
  for line in f:
   if line.startswith('#'):header.append(line)
   elif len(rows)<1000:rows.append(line)
   else:break
 for name,selected in [('small',rows),('two',rows[:2]),('unsorted',list(reversed(rows[:40])))]:
  (DATA/(name+'.vcf')).write_text(''.join(header+selected))
 subprocess.run(['bcftools','view','-Ob','-o',str(DATA/'small.bcf'),str(DATA/'small.vcf')],check=True)
 with gzip.open(INPUT/'cohort_all.vcf.gz','rt') as f:
  for line in f:
   if line.startswith('#CHROM'):
    samples=line.rstrip().split('\t')[9:509];break
 (DATA/'samples500.txt').write_text('\n'.join(samples)+'\n')
 subprocess.run(['bcftools','view','-S',str(DATA/'samples500.txt'),'-Oz','-o',str(DATA/'cohort500.vcf.gz'),str(INPUT/'cohort_all.vcf.gz')],check=True)
 (ROOT/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-start,'records':22382,'samples':[100,500,2504],'files':{p.name:p.stat().st_size for p in DATA.iterdir()}},indent=2))

def errors():
 binary=str(BIN['candidate']);checks=[]
 for i,flags in enumerate([['--ld-threads','0'],['--ld-threads','-1'],['--ld-threads','4x'],['--ld-threads','2147483648'],['--ld-threads','4','--freq'],['--ld-threads','4','--geno-chisq','--stdout']]):
  p=subprocess.run([binary,'--vcf',str(DATA/'two.vcf')]+flags,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  checks.append({'case':'invalid-option-'+str(i),'exit':p.returncode,'passed':p.returncode!=0})
 for name,limit in [('full-output',None),('descriptor-limit',16)]:
  work=ROOT/'runs'/name;work.mkdir(parents=True);tmp=work/'tmp';tmp.mkdir()
  if limit is None:(work/'out.geno.chisq').symlink_to('/dev/full')
  def fd_limit(): resource.setrlimit(resource.RLIMIT_NOFILE,(limit,limit))
  p=subprocess.run([binary,'--vcf',str(DATA/'small.vcf'),'--geno-chisq','--ld-window-bp','1000','--ld-threads','8','--temp',str(tmp),'--out',str(work/'out')],stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec_fn=fd_limit if limit else None,timeout=60)
  checks.append({'case':name,'exit':p.returncode,'temp_files_remaining':len(list(tmp.iterdir())),'passed':p.returncode!=0 and not list(tmp.iterdir())})
  if checks[-1]['passed']:shutil.rmtree(work)
 (ROOT/'error-checks.json').write_text(json.dumps(checks,indent=2))
 if not all(x['passed'] for x in checks):raise RuntimeError('Error handling check failed')

def path_regression():
 work=ROOT/'path-regression';work.mkdir(exist_ok=True)
 root=work/'p';padding=(-len(str(root)+'/vcftools.XXXXXX'))%16
 long_tmp=Path(str(root)+'x'*padding);long_tmp.mkdir(exist_ok=True)
 normal_tmp=work/'normal';normal_tmp.mkdir(exist_ok=True)
 results=[];reference=None
 for label,binary,threads,tmp in [('reference','before',1,normal_tmp),('candidate1','candidate',1,long_tmp),('candidate4','candidate',4,long_tmp),('before-bounded-failure','before',1,long_tmp)]:
  prefix=work/label;cmd=[str(BIN[binary]),'--vcf',str(DATA/'small.vcf'),'--geno-chisq','--ld-window','0','--temp',str(tmp),'--out',str(prefix)]
  if binary=='candidate':cmd+=['--ld-threads',str(threads)]
  def limit_memory():resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
  with Path(str(prefix)+'.stderr').open('wb') as err:
   try:p=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=err,timeout=10,preexec_fn=limit_memory if label=='before-bounded-failure' else None);code=p.returncode
   except subprocess.TimeoutExpired:code='timeout'
  output=Path(str(prefix)+'.geno.chisq')
  if label=='reference':reference=output.read_bytes()
  ok=(code!=0) if label=='before-bounded-failure' else code==0 and output.read_bytes()==reference and not list(tmp.iterdir())
  results.append({'label':label,'exit':code,'temp_template_bytes':len(str(tmp)+'/vcftools.XXXXXX'),'expected_behavior_observed':ok})
 (ROOT/'path-regression.json').write_text(json.dumps(results,indent=2))
 # An undefined write in the old executable need not fail on every run.
 if not all(r['expected_behavior_observed'] for r in results if r['label']!='before-bounded-failure'):raise RuntimeError('Temp-path regression failed')

try:
 if MODE in ('controls','controls-resume'):
  if MODE=='controls':prepare()
  else:RESULTS.extend(r for r in json.loads((ROOT/'controls-status.json').read_text())['results'] if r['passed'])
  labels=[('before',1),('candidate1',1),('candidate4',4),('candidate8',8)]
  for tag,file,flags in [
   ('ordinary',INPUT/'cohort100.vcf.gz',['--geno-chisq','--ld-window-bp','1000']),
   ('windows',DATA/'small.vcf',['--geno-chisq','--ld-window','15','--ld-window-min','3','--ld-window-bp','1000','--ld-window-bp-min','30']),
   ('filters',INPUT/'cohort100.vcf.gz',['--geno-chisq','--ld-window-bp','1000','--thin','100','--max-missing','0.95','--maf','0.05']),
   ('bcf',DATA/'small.bcf',['--geno-chisq','--ld-window-bp','1000']),
   ('two',DATA/'two.vcf',['--geno-chisq','--ld-window-bp','1000']),
   ('empty-window',DATA/'small.vcf',['--geno-chisq','--ld-window','0']),
   ('unsorted',DATA/'unsorted.vcf',['--geno-chisq','--ld-window-bp','1000'])]:
   if tag not in {r['case'] for r in RESULTS}:case(tag,file,flags,labels)
  errors()
  path_regression()
 elif MODE=='larger':
  if not json.loads((ROOT/'controls-resume-complete.json').read_text())['passed']:raise RuntimeError('Controls incomplete')
  for tag,file,labels in [
   ('500-samples',DATA/'cohort500.vcf.gz',[('original',1),('candidate4',4),('before',1),('candidate8',8),('candidate1',1)]),
   ('2504-samples',INPUT/'cohort_all.vcf.gz',[('candidate1',1),('candidate8',8),('original',1),('candidate4',4),('before',1)])]:case(tag,file,['--geno-chisq','--ld-window-bp','1000'],labels)
 else:raise ValueError(MODE)
 (ROOT/(MODE+'-complete.json')).write_text(json.dumps({'passed':True,'cases':len(RESULTS)}))
except Exception as e:
 (ROOT/(MODE+'-failure.txt')).write_text(repr(e));raise
