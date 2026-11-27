import gzip,hashlib,json,os,re,shlex,subprocess,time,traceback,shutil,signal
from pathlib import Path
R=Path('/jobtmp/zliu328/nuvcftools-parallel-tools-v1');D=R/'data';E=R/'evidence26';E.mkdir(exist_ok=True);D=E/'data';D.mkdir(exist_ok=True)
ORIG=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':ORIG/'lib/perl5','before':R/'candidate25/src/perl','candidate':R/'candidate26/src/perl'}
BIN=dict(LIB,original=ORIG/'bin')
ENV=dict(os.environ,PYTHONPATH=str(R/'candidate26/tests'),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TMPDIR=str(E))
cpus=sorted(os.sched_getaffinity(0));results=[]
def save(state):
 (E/'status.json').write_text(json.dumps(dict(state=state,job=os.environ.get('SLURM_JOB_ID'),node=os.uname().nodename,cpus=cpus,results=results),indent=2))
def equal(a,b):
 with open(a,'rb') as x,open(b,'rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
def normalize(b):
 for p in list(LIB.values())+list(BIN.values()):b=b.replace(str(p).encode(),b'<source>')
 return re.sub(rb' line \d+',b' line <source>',b)
def memory(root):
 todo=[root];seen=set();rss=pss=0
 while todo:
  pid=todo.pop()
  if pid in seen:continue
  seen.add(pid)
  try:
   for task in Path(f'/proc/{pid}/task').iterdir():todo += [int(x) for x in (task/'children').read_text().split()]
   for line in Path(f'/proc/{pid}/status').read_text().splitlines():
    if line.startswith('VmRSS:'):rss+=int(line.split()[1])
   for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines():
    if line.startswith('Pss:'):pss+=int(line.split()[1])
  except (FileNotFoundError,ProcessLookupError,PermissionError):pass
 return rss,pss

def runrow(tag,tool,args,stdin=None,compressed=False,md5=False,parallel=True):
 row=dict(case=tag,tool=tool,arguments=args,stdin=str(stdin),measurements={});paths=[]
 for label,version,n in [('original','original',1),('before','before',1),('candidate','candidate',1)]:
  if shutil.disk_usage(E).free < 4*1024**3:raise RuntimeError('less than 4 GiB free; inputs and pending outputs preserved')
  pref=E/(tag+'-'+label);paths.append(pref)
  if md5:
   for suffix in ['md5.vcf.gz','md5.vcf.gz.header','dictionary']:(D/suffix).unlink(missing_ok=True)
  cmd=['perl',str(BIN[version]/tool)]+args
  if parallel and version!='original':cmd+=['--workers',str(n)]
  if stdin:
   reader=['gzip','-dc',str(stdin)] if compressed else ['cat',str(stdin)]
   cmd=['bash','-o','pipefail','-c',shlex.join(reader)+' | '+shlex.join(cmd)]
  cmd=['/usr/bin/time','-f','%e %M %U %S','-o',str(pref)+'.time','taskset','-c',','.join(map(str,cpus[:n]))]+cmd
  with open(str(pref)+'.out','wb') as out,open(str(pref)+'.err','wb') as err:
   p=subprocess.Popen(cmd,stdout=out,stderr=err,env=dict(ENV,PERL5LIB=str(LIB[version])),start_new_session=True)
   peakrss=peakpss=0;start=time.monotonic()
   while p.poll() is None:
    rss,pss=memory(p.pid);peakrss=max(peakrss,rss);peakpss=max(peakpss,pss)
    if time.monotonic()-start>1800 or sum(Path(str(x)+'.out').stat().st_size for x in paths)>2*1024**3:
     os.killpg(p.pid,signal.SIGTERM);p.wait();raise RuntimeError(tag+' timeout/output budget; outputs preserved')
    time.sleep(.1)
  t=Path(str(pref)+'.time').read_text().splitlines()[-1].split()
  row['measurements'][label]=dict(wall_seconds=float(t[0]),gnu_peak_rss_kib=int(t[1]),user_seconds=float(t[2]),system_seconds=float(t[3]),sampled_tree_rss_kib=peakrss,sampled_tree_pss_kib=peakpss,sampling_seconds=.1,exit=p.returncode,cores=n,command=cmd)
  (E/'progress.json').write_text(json.dumps(row,indent=2))
  if p.returncode:raise RuntimeError(tag+' '+label+' nonzero exit')
  if md5:
   with gzip.open(D/'md5.vcf.gz','rb') as inp,open(str(pref)+'.vcf','wb') as out:
    while chunk:=inp.read(1048576):out.write(chunk)
   Path(str(pref)+'.dictionary').write_bytes((D/'dictionary').read_bytes());Path(str(pref)+'.header').write_bytes((D/'md5.vcf.gz.header').read_bytes())
 suffixes=['.out','.vcf','.dictionary','.header'] if md5 else ['.out']
 passed=all(equal(str(paths[0])+s,str(p)+s) for p in paths[1:] for s in suffixes) and all(normalize(Path(str(paths[0])+'.err').read_bytes())==normalize(Path(str(p)+'.err').read_bytes()) for p in paths[1:])
 row['passed']=passed;results.append(row);save('running')
 if not passed:raise RuntimeError(tag+' output mismatch; preserved all outputs')
 row['cleaned_bytes']=sum(Path(str(p)+s).stat().st_size for p in paths for s in suffixes)
 for p in paths:
  for suffix in suffixes:Path(str(p)+suffix).unlink()
 save('running')
try:
 save('controls')
 subprocess.run(['python3',str(R/'candidate26/tests/chunk_stream_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(E/'chunk-controls')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate26/tests/validator_record_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(E/'validator-controls')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate26/tests/perl_remaining_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers','4','--output',str(E/'remaining-controls')],check=True,env=ENV)
 small=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz');full=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz');fa=Path('/jobtmp/zliu328/nuvcftools-remaining-20261127/reference2/data/GRCh37.22.fa')
 start=time.monotonic();shuffled=D/'shuffled.vcf'
 with gzip.open(small,'rb') as inp:lines=inp.readlines()
 with shuffled.open('wb') as out:out.writelines(x for x in lines if x.startswith(b'#'));out.writelines(x for x in reversed(lines) if not x.startswith(b'#'))
 del lines
 (E/'preparation.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,excluded=True)))
 for repeat in range(3):
  runrow('md5-r'+str(repeat),'fill-ref-md5',['-r',str(fa),'-d',str(D/'dictionary'),str(full),str(D/'md5.vcf.gz')],md5=True)
  runrow('sort500-r'+str(repeat),'vcf-sort',['-p','1'],shuffled,parallel=False)
 runrow('validator500','vcf-validator',[str(small)],parallel=False)
 runrow('validator-unique500','vcf-validator',['-u',str(small)],parallel=False)
 removed=sum(p.stat().st_size for p in D.iterdir() if p.is_file());shutil.rmtree(D);(E/'input-cleanup.json').write_text(json.dumps(dict(state='complete',removed_bytes=removed)));save('complete')
except Exception:
 save('failed');(E/'failure.txt').write_text(traceback.format_exc());raise
