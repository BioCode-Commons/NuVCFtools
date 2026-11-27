#!/usr/bin/env python3
"""Differential comparison queue tests, including ordered failures and INDEL stops."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
header='''##fileformat=VCFv4.1
##contig=<ID=22,length=100000>
##INFO=<ID=INDEL,Number=0,Type=Flag,Description="Indel">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS0\tS1
'''
cases=['valid','trailing','missing','extra','bad-gt','info-warning','indel-first','indel-second','indel-value','indel-substring','no-gt','duplicate']
results=[]
for case in cases:
 files=[]
 for j in range(2):
  lines=[]
  for i in range(1,13):
   f=['22',str(i*10),'.','A','C','.','PASS','.','GT:DP','0/1:8','1/1:9']
   if i==6:
    if case=='trailing':f+=['','']
    if case=='missing':f.pop()
    if case=='extra':f+=['0/0:4']
    if case=='bad-gt':f[9]='bad:8'
    if case=='info-warning':f[7]=';X=1'
    if case=='indel-first':f[7]='INDEL' if j==0 else '.';f[9]='bad:8' if j==1 else '0/1:8'
    if case=='indel-second':f[7]='INDEL' if j==1 else '.'
    if case=='indel-value':f[7]='INDEL=1'
    if case=='indel-substring':f[7]='X=INDEL'
    if case=='no-gt':f[8]='DP';f[9:] = ['8','9']
    if case=='duplicate':f[1]='50'
   lines.append('\t'.join(f)+'\n')
  v=d/(case+str(j)+'.vcf');v.write_text(header+''.join(lines))
  g=Path(str(v)+'.gz')
  with g.open('wb') as out:subprocess.run(['bgzip','-c',str(v)],stdout=out,check=True)
  subprocess.run(['tabix','-p','vcf',str(g)],check=True);files.append(str(g))
 for n in [1,4]:
  for seed in [0,1,19]:
   runs=[]
   for root in [a.before,a.candidate]:
    cmd=['perl',str(Path(root)/'vcf-compare'),'-g','-d','-d','--workers',str(n),'--worker-batch-bytes','128']
    if case.startswith('indel'):cmd+=['--ignore-indels']
    r=subprocess.run(cmd+files,capture_output=True,timeout=30,env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C'))
    err=re.sub(rb' line \d+',b' line <source>',r.stderr.replace(root.encode(),b'<source>'))
    # Carp prints process-specific reference addresses in stack frames. Keep
    # quoted arguments and the actual diagnostic/record text unchanged.
    def frame(line):
     if not line.startswith(b'\t') or b' called at ' not in line:return line
     token=rb'"(?:[^"\\]|\\.)*"|((?:HASH|ARRAY|CODE|SCALAR)\()0x[0-9a-f]+(\))'
     return re.sub(token,lambda m:m[1]+b'<address>'+m[2] if m[1] else m[0],line)
    err=b''.join(frame(line) for line in err.splitlines(keepends=True))
    runs.append((r.returncode,r.stdout,err))
   ok=runs[0]==runs[1];results.append(dict(case=case,workers=n,seed=seed,passed=ok,exit_codes=[r[0] for r in runs]))
   (d/'results.json').write_text(json.dumps(results,indent=2)+'\n')
   if not ok:
    for label,r in zip(['before','candidate'],runs):
     (d/(case+str(n)+str(seed)+label+'.out')).write_bytes(r[1]);(d/(case+str(n)+str(seed)+label+'.err')).write_bytes(r[2])
    raise RuntimeError('comparison mismatch '+case)
print(json.dumps(dict(passed=True,cases=len(results))))
