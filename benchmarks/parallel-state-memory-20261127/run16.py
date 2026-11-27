import gzip,hashlib,json,os,re,shlex,subprocess,time,traceback
from pathlib import Path
R=Path('/jobtmp/zliu328/nuvcftools-parallel-tools-v1');D=R/'data';E=R/'evidence16';D.mkdir(exist_ok=True);E.mkdir(exist_ok=True)
ORIG=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':ORIG/'lib/perl5','before':R/'candidate13/src/perl','candidate':R/'candidate16/src/perl'}
BIN={'original':ORIG/'bin','before':R/'candidate13/src/perl','candidate':LIB['candidate']}
ENV=dict(os.environ,PYTHONPATH=str(R/'candidate16/tests'),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TMPDIR=str(E))
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
 for label,version,n in [('original','original',1),('before','before',1),('before16','before',16),('serial','candidate',1),('workers4','candidate',4),('workers16','candidate',16)]:
  if not parallel and n>1:continue
  if label=='before16' and tool in {'vcf-annotate','vcf-compare'}:continue
  pref=E/(tag+'-'+label);paths.append(pref)
  if md5:
   for suffix in ['md5.vcf.gz','md5.vcf.gz.header','dictionary']:(D/suffix).unlink(missing_ok=True)
  cmd=['perl',str(BIN[version]/tool)]+args
  if parallel and (version=='candidate' or (version=='before' and tool not in {'vcf-annotate','vcf-compare'})):cmd+=['--workers',str(n)]
  if stdin:
   reader=['gzip','-dc',str(stdin)] if compressed else ['cat',str(stdin)]
   cmd=['bash','-o','pipefail','-c',shlex.join(reader)+' | '+shlex.join(cmd)]
  cmd=['/usr/bin/time','-f','%e %M %U %S','-o',str(pref)+'.time','taskset','-c',','.join(map(str,cpus[:n]))]+cmd
  with open(str(pref)+'.out','wb') as out,open(str(pref)+'.err','wb') as err:
   p=subprocess.Popen(cmd,stdout=out,stderr=err,env=dict(ENV,PERL5LIB=str(LIB[version])))
   peakrss=peakpss=0;start=time.monotonic()
   while p.poll() is None:
    rss,pss=memory(p.pid);peakrss=max(peakrss,rss);peakpss=max(peakpss,pss)
    if time.monotonic()-start>1800:p.terminate();p.wait();raise RuntimeError(tag+' timeout')
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
 subprocess.run(['python3',str(R/'candidate16/tests/reference_metadata_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(E/'reference-controls')],check=True,env=ENV)
 subprocess.run(['perl',str(R/'candidate16/tests/worker_ownership_regression.pl')],check=True,env=dict(ENV,PERL5LIB=str(LIB['candidate'])))
 subprocess.run(['python3',str(R/'candidate16/tests/ordered_workers_regression.py'),'--before',str(LIB['before']),'--source',str(LIB['candidate']),'--output',str(E/'ordered-controls')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate16/tests/perl_remaining_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers','4','--output',str(E/'remaining-controls')],check=True,env=ENV)
 for n in [1,4,16]:
  subprocess.run(['python3',str(R/'candidate16/tests/perl_stats_merge_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers',str(n),'--output',str(E/f'stats-merge-controls{n}')],check=True,env=ENV)
 for n in [1,4]:
  subprocess.run(['python3',str(R/'candidate16/tests/compare_index_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers',str(n),'--indexed','--output',str(E/f'compare-controls{n}')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate16/tests/validator_record_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(E/'validator-controls')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate16/tests/annotate_counts_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers','4','--output',str(E/'annotate-controls')],check=True,env=ENV)
 clock=E/'FixedHeaderClock.pm'
 clock.write_text('package FixedHeaderClock; BEGIN { *CORE::GLOBAL::time = sub () { 1795737600 }; } 1;\n')
 ENV['PERL5OPT']='-I'+str(E)+' -MFixedHeaderClock'
 small=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
 halves=Path('/jobtmp/zliu328/nuvcftools-mqs-20261126/data')
 started=time.monotonic()
 # The stats input has no tabix index. Prepare an isolated BGZF/index pair;
 # never overwrite the source or include preparation in any tool measurement.
 indexed=E/'compare-input.vcf.gz'
 subprocess.run(['bcftools','view','--no-version','-Oz','-o',str(indexed),str(small)],check=True)
 subprocess.run(['tabix','-p','vcf',str(indexed)],check=True)
 for name in ['a','b']:
  f=E/(name+'.vcf.gz');f.symlink_to(indexed);Path(str(f)+'.tbi').symlink_to(str(indexed)+'.tbi')
 (E/'preparation.json').write_text(json.dumps(dict(seconds=time.monotonic()-started,excluded=True)))
 runrow('stats500-interned','vcf-stats',[str(small)])
 runrow('merge500-shared-metadata','vcf-merge',[str(halves/'500-A.vcf.gz'),str(halves/'500-B.vcf.gz')])
 runrow('annotate500-workers','vcf-annotate',['--fill-HWE'],small,True)
 runrow('compare500-genotypes','vcf-compare',['-g',str(E/'a.vcf.gz'),str(E/'b.vcf.gz')])
 runrow('validator500-memo','vcf-validator',['-u',str(small)],parallel=False)
 runrow('fill-aa-shared-index','fill-aa',['-a','/jobtmp/zliu328/nuvcftools-remaining-20261127/reference2/data/GRCh37.22.fa'],small,True,parallel=False)
 save('complete')
except BaseException:
 save('failed');(E/'failure.txt').write_text(traceback.format_exc());raise
