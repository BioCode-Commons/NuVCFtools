import argparse,os,subprocess,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
sex=a.output/'sex';sex.write_text('A M\nB F\nC M\n');policy=a.output/'policy';policy.write_text('{22=>[{from=>1,to=>20,M=>1,F=>0},{from=>21,to=>1000,M=>2,F=>1}]}\n');reg=a.output/'regions';reg.write_text('22\t1\t1000\n');cases=[]
header='##fileformat=VCFv{v}\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n##FORMAT=<ID=PL,Number=G,Type=Integer,Description="PL">\n##FORMAT=<ID=GL,Number=G,Type=Float,Description="GL">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB\tC\n'
for version in ['4.0','4.1','4.2']:
 for fmt in ['GT','PL:GT:GL','GT:GL:PL','DP:GT:PL:GL:XX']:
  rows=[]
  for i in range(40):
   vals={'GT':['0/1','0|0','1','.','./.','0/1/1',''][i%7],'PL':['0,20,30','0,20','.'][i%3],'GL':['-1,-2,-3','-1,-2','.'][i%3],'DP':'3','XX':''}
   field=':'.join(vals[k] for k in fmt.split(':'))
   fields=[field,field.rstrip(':'),field.split(':')[0]]
   rows.append('\t'.join(['22',str(i+1),'.','A','C','.','PASS','.',fmt]+fields)+'\n')
  for likelihood in [False,True]:cases.append((f'ploidy-{version}-{fmt}-{likelihood}','vcf-fix-ploidy',['-s',str(sex),'-p',str(policy)]+(['-l'] if likelihood else []),(header.format(v=version)+''.join(rows)).encode()))
for name,positions,alts in [('sorted',[1,2,3],['AT','A','.']),('unsorted',[3,2,1],['AT','A','C']),('multi',[1,2,3],['AT,A,C','<DEL>','AA']),('empty',[],[]),('repeat',[1,1,2],['AT','AT','A'])]:
 body=''.join('\t'.join(['22',str(pos),'.','AC',alt,'.','PASS','.','GT','0/1','0/0','1/1'])+'\n' for pos,alt in zip(positions,alts))
 cases.append(('indel-'+name,'vcf-indel-stats',['-e',str(reg),'-v'],(header.format(v='4.2')+body).encode()))
results=[];single_errors=set();excluded=[]
for workers in [1,4]:
 for name,tool,args,data in cases:
  # The preceding version has nondeterministic worker-cancellation diagnostics.
  # Error/partial-output comparisons remain mandatory at one worker.
  if workers==4 and name in single_errors:
   excluded.append(dict(case=name,workers=4,reason='Baseline parallel error-cleanup diagnostic is nondeterministic; exact single-worker error comparison retained.'))
   (a.output/'excluded.json').write_text(json.dumps(excluded,indent=2)+'\n')
   continue
  outputs=[]
  for root in [a.before,a.candidate]:
   env=dict(os.environ,PERL5LIB=str(root),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C')
   q=subprocess.run(['perl',str(root/tool),*args,'--workers',str(workers),'--worker-batch-bytes','128'],input=data,capture_output=True,env=env,timeout=30)
   err=q.stderr.replace(str(root).encode(),b'<source>');err=re.sub(rb' line \d+',b' line <source>',err)
   err=re.sub(rb' at <source>/[^\n]+ line <source>(?:, <[^>]+> line <source>)?\.',b' at <callsite>.',err)
   err=b'\n'.join(x for x in err.split(b'\n') if not (x.startswith(b'\t') and b' called at ' in x))
   err=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',err)
   outputs.append((q.returncode,q.stdout,err))
  if workers==1 and outputs[0][0]!=0:single_errors.add(name)
  passed=outputs[0]==outputs[1];results.append(dict(case=name,workers=workers,passed=passed,exits=[x[0] for x in outputs]))
  (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
  if not passed:
   for label,res in zip(['before','candidate'],outputs):
    (a.output/(label+'.out')).write_bytes(res[1]);(a.output/(label+'.err')).write_bytes(res[2])
   raise RuntimeError((name,workers))
print(json.dumps(dict(passed=True,cases=len(results))))
