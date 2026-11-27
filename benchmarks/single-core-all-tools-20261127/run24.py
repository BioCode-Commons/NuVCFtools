import gzip,hashlib,json,os,re,shlex,subprocess,time,traceback,shutil,signal
from pathlib import Path
R=Path('/jobtmp/zliu328/nuvcftools-parallel-tools-v1');D=R/'data';E=R/'evidence24';E.mkdir(exist_ok=True);D=E/'data';D.mkdir(exist_ok=True)
ORIG=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':ORIG/'lib/perl5','before':R/'before24/src/perl','candidate':R/'candidate24/src/perl'}
BIN=dict(LIB,original=ORIG/'bin')
ENV=dict(os.environ,PYTHONPATH=str(R/'candidate24/tests'),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TMPDIR=str(E))
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
 subprocess.run(['perl',str(R/'candidate24/tests/worker_lazy_load_regression.pl')],check=True,env=dict(ENV,PERL5LIB=str(LIB['candidate'])))
 subprocess.run(['python3',str(R/'candidate24/tests/ordered_workers_regression.py'),'--before',str(LIB['before']),'--source',str(LIB['candidate']),'--output',str(E/'ordered-controls')],check=True,env=ENV)
 subprocess.run(['python3',str(R/'candidate24/tests/perl_remaining_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers','1','--output',str(E/'remaining-controls')],check=True,env=ENV)
 save('preparing');start=time.monotonic()
 clock=E/'FixedHeaderClock.pm';clock.write_text('package FixedHeaderClock; BEGIN { *CORE::GLOBAL::time = sub () { 1795737600 }; } 1;\n')
 ENV['PERL5OPT']='-I'+str(E)+' -MFixedHeaderClock'
 small=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
 full=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 small100=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz')
 ref=Path('/jobtmp/zliu328/nuvcftools-remaining-20261127/reference2/data');fa=ref/'GRCh37.22.fa'
 halves=Path('/jobtmp/zliu328/nuvcftools-mqs-20261126/data')
 shards=Path('/jobtmp/zliu328/nuvcftools-concat-tree-20261126/data/interleaved-128')
 names=subprocess.check_output(['bcftools','query','-l',str(small)],text=True).splitlines()
 names100=subprocess.check_output(['bcftools','query','-l',str(small100)],text=True).splitlines()
 keep=D/'keep.txt';keep.write_text('\n'.join(names[:250])+'\n')
 sexes=D/'sexes.txt';sexes.write_text(''.join(n+' M\n' for n in names))
 policy=D/'ploidy.pl';policy.write_text('{22=>[{from=>1,to=>51304566,M=>1,F=>2}]}\n')
 regions=D/'region.tsv';regions.write_text('22\t20000001\t21000000\n')
 blocks=[]
 for name,region in [('left','22:20000001-20600000'),('right','22:20400000-21000000')]:
  f=D/(name+'.vcf.gz');subprocess.run(['bcftools','view','--no-version','-t',region,'-Oz','-o',str(f),str(small)],check=True);subprocess.run(['tabix','-p','vcf',str(f)],check=True);blocks.append(f)
 fragment=D/'fragment.fa'
 with fragment.open('wb') as dst:subprocess.run(['samtools','faidx',str(fa),'22:20000001-21000000'],stdout=dst,check=True)
 subset=D/'mask.vcf';count=0
 with gzip.open(small,'rb') as inp,subset.open('wb') as out:
  for line in inp:
   if not line.startswith(b'#'):
    if count==2000:break
    count+=1
   out.write(line)
 with Path(str(subset)+'.gz').open('wb') as out:subprocess.run(['bgzip','-c',str(subset)],stdout=out,check=True)
 subprocess.run(['tabix','-p','vcf',str(subset)+'.gz'],check=True)
 crlf=D/'crlf.vcf'
 with gzip.open(full,'rb') as inp,crlf.open('wb') as out:
  for line in inp:out.write(line.replace(b'\n',b'\r\n'))
 template=D/'template.vcf';sample_header=subprocess.check_output(['bcftools','view','-h',str(full)]).splitlines()[-1].split(b'\t');template.write_bytes(b'##fileformat=VCFv4.2\n'+b'\t'.join(sample_header[:9]+sample_header[9:][::-1])+b'\n')
 # Reverse record order in a derived real input, preparation excluded.
 shuffled=D/'shuffled.vcf'
 with gzip.open(small,'rb') as inp:lines=inp.readlines()
 with shuffled.open('wb') as out:out.writelines(x for x in lines if x.startswith(b'#'));out.writelines(x for x in reversed(lines) if not x.startswith(b'#'))
 del lines
 (E/'preparation.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,excluded=True,bytes=sum(p.stat().st_size for p in D.iterdir() if p.is_file()))))
 tasks=[
 ('query2504','vcf-query',[str(full)],None,False,False,True),
 ('shuffle2504','vcf-shuffle-cols',['-t',str(template),str(full)],None,False,False,True),
 ('tstv2504','vcf-tstv',[],full,True,False,True),
 ('newlines2504','vcf-fix-newlines',[str(crlf)],None,False,False,True),
 ('an-ac500','fill-an-ac',[],small,True,False,True),
 ('annotate500','vcf-annotate',['--fill-HWE'],small,True,False,True),
 ('subset500','vcf-subset',['-c',str(keep),str(small)],None,False,False,True),
 ('contrast100','vcf-contrast',['+'+','.join(names100[:10]),'-'+','.join(names100[10:]),str(small100)],None,False,False,True),
 ('convert500','vcf-convert',['-v','4.2'],ref/'snps.vcf.gz',True,False,True),
 ('ploidy500','vcf-fix-ploidy',['-s',str(sexes),'-p',str(policy)],small,True,False,True),
 ('indel500','vcf-indel-stats',['-e',str(regions)],small,True,False,True),
 ('concat128','vcf-concat',['-s','128']+[str(shards/f'{i}.vcf.gz') for i in range(128)],None,False,False,False),
 ('aa500','fill-aa',['-a',str(fa)],small,True,False,False),
 ('fs2000','fill-fs',['-r',str(fa),'-l','7','-v',str(subset)+'.gz'],subset,False,False,True),
 ('md5','fill-ref-md5',['-r',str(fa),'-d',str(D/'dictionary'),str(full),str(D/'md5.vcf.gz')],None,False,True,True),
 ('consensus','vcf-consensus',[str(halves/'500-A.vcf.gz')],fragment,False,False,False),
 ('isec','vcf-isec',['-a',str(shards/'0.vcf.gz'),str(shards/'1.vcf.gz')],None,False,False,True),
 ('merge500','vcf-merge',[str(halves/'500-A.vcf.gz'),str(halves/'500-B.vcf.gz')],None,False,False,True),
 ('phase500','vcf-phased-join',['-o','-']+list(map(str,blocks)),None,False,False,True),
 ('sort500','vcf-sort',['-p','1'],shuffled,False,False,False),
 ('tab500','vcf-to-tab',[str(small)],None,False,False,True),
 ('stats500','vcf-stats',[str(small)],None,False,False,True),
 ('validator500','vcf-validator',[str(small)],None,False,False,False),
 ('compare500','vcf-compare',['-g',str(R/'evidence16/a.vcf.gz'),str(R/'evidence16/b.vcf.gz')],None,False,False,True),
 ]
 failures=[]
 for task in tasks:
  try:runrow(*task)
  except Exception:
   failures.append(task[0]);(E/(task[0]+'-failure.txt')).write_text(traceback.format_exc());(E/'failures.json').write_text(json.dumps(failures));save('running-with-failures')
 if failures:save('failed')
 else:
  removed=sum(p.stat().st_size for p in D.iterdir() if p.is_file());shutil.rmtree(D);(E/'input-cleanup.json').write_text(json.dumps(dict(state='complete',removed_bytes=removed)));save('complete')
except Exception:
 save('failed');(E/'failure.txt').write_text(traceback.format_exc());raise
