import datetime,json,os,re,subprocess,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'merge-date-replay';D.mkdir(exist_ok=True)
P=R/'third';status=json.loads((P/'status.json').read_text());row=next(x for x in status['results'] if x['case']=='merge-2504')
original=P/'merge-2504-original.out';dates=[]
with original.open('rb') as f:
 for line in f:
  if not line.startswith(b'#'):break
  m=re.match(rb'^##sourceFiles_(\d{8})\.\d+=',line)
  if m:dates.append(m.group(1).decode())
assert len(dates)==1
fixed=int(datetime.datetime.strptime(dates[0],'%Y%m%d').replace(tzinfo=datetime.timezone.utc).timestamp())
(D/'FixedHeaderClock.pm').write_text('package FixedHeaderClock; use strict; use warnings; BEGIN { *CORE::GLOBAL::time = sub () { '+str(fixed)+' }; } 1;\n')
lib=R/'candidate6/src/perl';env=dict(os.environ,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC',PERL5LIB=str(D)+':'+str(lib))
with (D/'candidate.out').open('wb') as out,(D/'candidate.err').open('wb') as err:
 p=subprocess.run(['perl','-MFixedHeaderClock',str(lib/'vcf-merge')]+row['args'],env=env,stdout=out,stderr=err,timeout=900)
def eq(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
def norm(b):
 for v in [lib,R/'before/src/perl',Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools/lib/perl5'),Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools/bin')]:b=b.replace(str(v).encode(),b'<lib>')
 b=re.sub(rb' line \d+',b' line <source>',b);return re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',b)
result={'purpose':'Validation-only replay, not a timing measurement','fixed_utc_date':dates[0],'test_only_clock_override':True,'product_time_calls':'Vcf.pm::add_header_line gmtime(time); no analysis clock use in vcf-merge/Vcf.pm','exit':p.returncode,'stdout_exact_original':eq(original,D/'candidate.out'),'stdout_exact_before':eq(P/'merge-2504-before.out',D/'candidate.out'),'stderr_original':norm((P/'merge-2504-original.err').read_bytes())==norm((D/'candidate.err').read_bytes()),'stderr_before':norm((P/'merge-2504-before.err').read_bytes())==norm((D/'candidate.err').read_bytes()),'source_sha256':{str(k):hashlib.sha256(k.read_bytes()).hexdigest() for k in [lib/'Vcf.pm',lib/'vcf-merge']}}
result['passed']=p.returncode==0 and all(result[k] for k in ['stdout_exact_original','stdout_exact_before','stderr_original','stderr_before']);(D/'comparison.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['passed']
