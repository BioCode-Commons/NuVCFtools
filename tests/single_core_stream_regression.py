#!/usr/bin/env python3
"""Exact CLI output/exit/diagnostics for serial stream transformations."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False);results=[]
def check(name,tool,flags,payload):
 for workers in [1,4]:
  runs=[]
  for src in [a.before,a.candidate]:
   r=subprocess.run(['perl',str(Path(src)/tool),*flags,'--workers',str(workers),'--worker-batch-bytes','256'],input=payload,capture_output=True,env=dict(os.environ,PERL5LIB=src,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C'),timeout=30)
   err=re.sub(rb' line \d+',b' line <source>',r.stderr.replace(src.encode(),b'<source>'))
   def frame(line):
    if not line.startswith(b'\t') or b' called at ' not in line:return line
    token=rb'"(?:[^"\\]|\\.)*"|((?:HASH|ARRAY|CODE|SCALAR)\()0x[0-9a-f]+(\))'
    return re.sub(token,lambda m:m[1]+b'<address>'+m[2] if m[1] else m[0],line)
   runs.append((r.returncode,r.stdout,b''.join(frame(x) for x in err.splitlines(keepends=True))))
  ok=runs[0]==runs[1];results.append(dict(case=name,tool=tool,workers=workers,passed=ok))
  if not ok:
   for label,v in zip(['before','candidate'],runs):
    (d/(label+'.stdout')).write_bytes(v[1]);(d/(label+'.stderr')).write_bytes(v[2])
   (d/'results.json').write_text(json.dumps(results,indent=2));raise RuntimeError(results[-1])
header='##fileformat=VCFv4.2\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ta\tb\tc\td\n'
template=d/'template.vcf';template.write_text(header.replace('\ta\tb\tc\td\n','\td\tb\ta\tc\n'))
rows=['22\t%d\t.\t%s\t%s\t.\tPASS\t.\tGT\t0/1\t1/1\t0|0\t./.\n'%(i+1,*v) for i,v in enumerate([('A','G'),('C','T'),('G','A,C'),('A','AT'),('AT','A'),('A','.'),('a','g'),('N','C'),('A','G,AT')]*4)]
normal=(header+''.join(rows)).encode()
for name,data in [('normal',normal),('empty',header.encode()),('unterminated',normal.rstrip(b'\n')),('trailing',normal.replace(b'\n22',b'\t\n22')),('short',normal+b'22\t90\t.\tA\tC\n'),('blank',normal+b'\n'),('no-fields',normal+b'broken\n')]:
 check(name,'vcf-shuffle-cols',['-t',str(template)],data)
 check(name,'vcf-tstv',[],data)
for nl in [b'\r',b'\r\n']:
 for offset in [-2,-1,0,1,2]:
  data=b'header'+nl+b'x'*(65536+offset)+nl+b'last'+nl
  check('boundary-'+repr(nl)+'-'+str(offset),'vcf-fix-newlines',[],data)
 for tail in [b'',b'\r',b'\n',b'\rX',b'\n\r']:
  data=(b'h'+nl)*600+b'x'*65535+nl+tail
  check('tail-'+repr(nl)+'-'+repr(tail),'vcf-fix-newlines',[],data)
for name,data in [('empty',b''),('unix',normal),('unknown',b'x'*2048),('mixed',b'x\r\ny\nz\rw\r\n')]:
 for flags in [[],['-i']]:check(name+str(flags),'vcf-fix-newlines',flags,data)
(d/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(results))))
