#!/usr/bin/env python3
"""Compare complete validator streams, including unknown-field state and errors."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
header='''##fileformat=VCFv{version}
##contig=<ID=22,length=100000>
##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="DP">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="AD">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\ta\tb\tc\td
'''
fixtures={}
for label,fmt,values,info in [
 ('valid','GT:DP',['0/1:2','1/1:5','0/1:2','0/1:2'],'.'),
 ('missing','GT',['.','./.','.','./.'],'.'),
 ('unknown','GT:NEW',['0/1:2','0/1:2','1:3','0/1:2'],'UNKNOWN=4'),
 ('bad','GT:DP',['x/y:no','0/9:-1','x/y:no','0/9:-1'],'.'),
 ('cardinality','GT:AD',['0/1:1,2,3','0/1:1','0/1:1,2,3','0/1:1'],'.'),
 ('empty','GT',['','','0/1',''],'.'),
 ('noGT','DP',['2','2','4','2'],'.'),
 ('counts','GT',['0/1','0/1','1/1','0/1'],'AN=8;AC=5'),
 ('short','GT:DP',['0/1','0/1','1/1:4','0/1'],'.'),
 ('extra','GT',['0/1:4','0/1:4','1','0/1:4'],'.')]:
 fixtures[label]=''.join('\t'.join(['22',str(pos),'.','A','C','.','PASS',info,fmt]+values)+'\n' for pos in [10,10,9,12,10])
results=[]
for version in ['3.3','4.0','4.1','4.2']:
 for seed in [0,1,19]:
  for name,records in fixtures.items():
   for flags in [[],['-d'],['-u','-d']]:
    runs=[]
    inp=d/'input.vcf';inp.write_text(header.format(version=version)+records)
    for root in [a.before,a.candidate]:
     r=subprocess.run(['perl',str(Path(root)/'vcf-validator')]+flags+[str(inp)],capture_output=True,env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C'),timeout=15)
     def norm(x):return re.sub(rb' line \d+',b' line <source>',x.replace(root.encode(),b'<source>'))
     runs.append((r.returncode,norm(r.stdout),norm(r.stderr)))
    ok=runs[0]==runs[1];results.append(dict(version=version,seed=seed,case=name,flags=flags,passed=ok))
    if not ok:
     for label,r in zip(['before','candidate'],runs):
      (d/(label+'.stdout')).write_bytes(r[1]);(d/(label+'.stderr')).write_bytes(r[2])
     (d/'results.json').write_text(json.dumps(results,indent=2));raise RuntimeError(results[-1])
(d/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(dict(passed=True,cases=len(results))))
