#!/usr/bin/env python3
"""Compare actual packed preparation results, flags, reader state and diagnostics."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
probe=Path(__file__).with_name('packed_columns_probe.pl');paths=[]
for name,root in [('before',a.before),('candidate',a.candidate)]:
 path=d/(name+'.json');paths.append(path)
 with path.open('wb') as f:
  subprocess.run(['perl',str(probe)],stdout=f,check=True,env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0'),timeout=30)
before=paths[0].read_bytes();after=paths[1].read_bytes();passed=before==after
result=dict(passed=passed,cases=len(json.loads(before)),comparison='complete JSON bytes, including value UTF8 flag and parser state; diagnostic callsite/address normalized')
(d/'results.json').write_text(json.dumps(result,indent=2)+'\n')
if not passed:raise RuntimeError('packed column preparation mismatch; artifacts retained')
for path in paths:path.unlink()
print(json.dumps(result))
