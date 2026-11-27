import importlib.util,json,os,subprocess,time,platform,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent;R=ROOT/'final-validation';R.mkdir(exist_ok=True)
ENV=dict(os.environ,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
LIB={'before':ROOT/'before/src/perl','candidate':ROOT/'candidate6/src/perl'}
def equal(a,b):
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   u=x.read(1048576);v=y.read(1048576)
   if u!=v:return False
   if not u:return True
try:
 subprocess.run(['python3',str(ROOT/'candidate6/tests/query_rendering_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(R/'query-controls')],env=ENV,check=True)
 subprocess.run(['perl',str(ROOT/'readonly_genotypes.pl')],env=dict(ENV,PERL5LIB=str(LIB['candidate'])),check=True)
 # Exercise non-repeating complete sample fields as well as GT-only real data.
 lines=(R/'query-controls/all.vcf').read_text().splitlines(True)
 header=[x for x in lines if x.startswith('#')];records=[x.rstrip('\n').split('\t') for x in lines if not x.startswith('#')]
 p=R/'rich-fields.vcf'
 with p.open('w') as f:
  f.writelines(header)
  for i in range(16000):
   row=records[i%len(records)].copy();row[1]=str(20000001+i);f.write('\t'.join(row)+'\n')
 names=header[-1].rstrip('\n').split('\t')[9:];results=[]
 for tag,tool,args in [('query-rich-default','vcf-query',[str(p)]),('query-rich-fields','vcf-query',['-f','%CHROM:%POS[%SAMPLE:%GT:%DP:%AD:%PL]\\n',str(p)]),('subset-rich','vcf-subset',['-c',','.join(names),str(p)])]:
  row={'case':tag,'synthetic_control':True,'measurements':{}}
  for label in LIB:
   prefix=R/f'{tag}-{label}'
   with Path(str(prefix)+'.out').open('wb') as out,Path(str(prefix)+'.err').open('wb') as err:
    run=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(prefix)+'.time','perl',str(LIB[label]/tool)]+args,env=dict(ENV,PERL5LIB=str(LIB[label])),stdout=out,stderr=err,timeout=180)
   vals=Path(str(prefix)+'.time').read_text().splitlines()[-1].split();row['measurements'][label]={'wall_seconds':float(vals[0]),'rss_kib':int(vals[1]),'exit':run.returncode}
  row['passed']=equal(R/f'{tag}-before.out',R/f'{tag}-candidate.out')
  diagnostics=[]
  for label in LIB:
   b=(R/f'{tag}-{label}.err').read_bytes().replace(str(LIB[label]).encode(),b'<lib>');diagnostics.append(re.sub(rb' line \d+',b' line <source>',b))
  row['passed']=row['passed'] and diagnostics[0]==diagnostics[1] and all(x['exit']==0 for x in row['measurements'].values())
  results.append(row);(R/'results.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':results},indent=2))
  if not row['passed']:raise RuntimeError(tag+' mismatch')
  for label in LIB:
   for suffix in ['.out','.err']:(R/f'{tag}-{label}{suffix}').unlink()
 p.unlink();(R/'complete.json').write_text(json.dumps({'passed':True}))
except Exception as e:(R/'failure.txt').write_text(repr(e));raise
