#!/usr/bin/env python3
"""Full CLI bytes/diagnostics for column ownership and stable sample ordering."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False);rows=[]
header='##fileformat=VCFv4.2\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="DP">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tz\ta\tm\n'
records=[['22','1','.','A','C,G','.','PASS','.','GT','0/1','1|2','./.'],['22','2','.','G','T','.','PASS','.','GT:DP','1/1:8','0/1:7','0/0:9']]
variants={'normal':records,'missing-middle':[[*records[0][:9],'0/1','','0/0'],records[1]],'missing-first':[[*records[0][:9],'','0/1','0/0'],records[1]],'all-empty':[[*records[0][:9],'','',''],records[1]],'no-gt':[[*records[0][:8],'DP','3','4','5'],records[1]],'bad-gt':[records[0],[*records[1][:9],'bad','0/1','0/0']],'field-count':[records[0],records[1][:-1]],'extra':[records[0],records[1]+['0/0']],'extra-format':[[*records[0][:9],'0/1:9','0/1','0/0']], 'haploid':[[*records[0][:9],'0','1','2']], 'iupac-error':[records[0]],'empty':[]}
payloads={case:(header+''.join('\t'.join(x)+'\n' for x in data)).encode() for case,data in variants.items()}
normal=payloads['normal']
payloads.update({'site-only':(header.split('#CHROM')[0]+'#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'+'\t'.join(records[0][:8])+'\n').encode(), 'duplicate-name':normal.replace(b'\tz\ta\tm\n',b'\tz\ta\tz\n'), 'headerless':('\t'.join(records[0])+'\n').encode(), 'no-final-newline':normal.rstrip(b'\n')})
for case,payload in payloads.items():
 for flag in [[],['--iupac']]:
  for workers in [1,4]:
   for seed in [0,19]:
    vals=[]
    for src in [a.before,a.candidate]:
     v=subprocess.run(['perl',str(Path(src)/'vcf-to-tab'),*flag,'--workers',str(workers),'--worker-batch-bytes','100'],input=payload,capture_output=True,env=dict(os.environ,PERL5LIB=src,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C'),timeout=30)
     err=re.sub(rb' line \d+',b' line <source>',v.stderr.replace(src.encode(),b'<source>'))
     def frame(line):
      if not line.startswith(b'\t') or b' called at ' not in line:return line
      token=rb'"(?:[^"\\]|\\.)*"|((?:HASH|ARRAY|CODE|SCALAR)\()0x[0-9a-f]+(\))'
      return re.sub(token,lambda m:m[1]+b'<address>'+m[2] if m[1] else m[0],line)
     err=b''.join(frame(line) for line in err.splitlines(keepends=True))
     vals.append((v.returncode,v.stdout,err))
    ok=vals[0]==vals[1];rows.append(dict(case=case,iupac=bool(flag),workers=workers,seed=seed,passed=ok))
    if not ok:
     for label,v in zip(['before','candidate'],vals):
      (d/(label+'.stdout')).write_bytes(v[1]);(d/(label+'.stderr')).write_bytes(v[2])
     (d/'results.json').write_text(json.dumps(rows,indent=2));raise RuntimeError(rows[-1])
(d/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(rows))))
