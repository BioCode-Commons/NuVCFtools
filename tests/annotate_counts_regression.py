#!/usr/bin/env python3
"""Exact annotation counts, likelihood output, and malformed-field diagnostics."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
(d/'FixedHeaderClock.pm').write_text('package FixedHeaderClock; BEGIN { *CORE::GLOBAL::time = sub () { 1795737600 }; } 1;\n')
header='##fileformat=VCFv4.1\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ta\tb\tc\td\n'
fixtures={}
for tag,fmt,cols in [('normal','GT:DP',['0/1:2','0/1:2','1|0:3','1/1:4']),('haploid','GT',['0','1','1','.']),('polyploid','GT',['0/1/2','0/1/2','1/0/2','1']),('missing','GT',['./.','./.','.|1','0/.']),('short','DP:GT',['3','3','2:0/1','2:0/1']),('empty','GT',['','','0','1']),('noGT','DP',['3','3','2','2']),('bad','GT',['x/y','x/y','0','1'])]:
 lines=[]
 for i,alt in enumerate(['C','C,G','.']):lines.append('\t'.join(['22',str(101+i),'.','A',alt,'.','PASS','.',fmt]+cols)+'\n')
 fixtures[tag]=(header+''.join(lines)).encode()
results=[]
for seed in [0,1,19]:
 for tag,data in fixtures.items():
  for flag in ['--fill-AC-AN','--fill-HWE','--fill-ICF']:
   runs=[]
   for root in [a.before,a.candidate]:
    r=subprocess.run(['perl',str(Path(root)/'vcf-annotate'),flag],input=data,capture_output=True,env=dict(os.environ,PERL5LIB=root,PERL5OPT='-I'+str(d)+' -MFixedHeaderClock',PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C'),timeout=10)
    err=re.sub(rb' line \d+',b' line <source>',r.stderr.replace(root.encode(),b'<source>'))
    runs.append((r.returncode,r.stdout,err))
   passed=runs[0]==runs[1]
   results.append(dict(case=tag,flag=flag,seed=seed,passed=passed,exit_codes=[x[0] for x in runs]))
   if not passed:
    for label,r in zip(['before','candidate'],runs):
     (d/(tag+'-'+label+'.stdout')).write_bytes(r[1]);(d/(tag+'-'+label+'.stderr')).write_bytes(r[2])
    (d/'results.json').write_text(json.dumps(results,indent=2));raise RuntimeError(tag+' '+flag+' mismatch')
(d/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(dict(passed=True,cases=len(results))))
