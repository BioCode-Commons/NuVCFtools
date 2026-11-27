#!/usr/bin/env python3
"""SMT obligations for explicit contracts, NOT a proof of the Perl interpreter.
Run with z3-solver installed; write SMT-LIB queries and proof terms to --output.
The mapping/assumptions and implementation checks are documented separately.
"""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True)
z.set_param(proof=True)
rows=[]
def check(name,assumptions,claim):
 s=z.Solver();s.add(*assumptions,z.Not(claim));(d/(name+'.smt2')).write_text(s.to_smt2());r=s.check()
 assert r==z.unsat,(name,r,s.model() if r==z.sat else s.reason_unknown())
 (d/(name+'.proof')).write_text(str(s.proof()));rows.append(dict(name=name,result=str(r)))
# Integer counter regrouping; range assumption excludes Perl integer overflow.
x,y,w,old=z.Ints('x y w old');limit=2**63-1
check('counter_partition',[v>=0 for v in [x,y,w,old]]+[old+x+y+w<=limit],(old+x)+y+w==old+(x+y+w))
# Earliest insertion wins across consecutive partitions, preserving tie order.
a0,a1,b0,b1=z.Ints('a0 a1 b0 b1');minimum=lambda a,b:z.If(a<b,a,b)
check('first_insertion',[],minimum(minimum(a0,a1),minimum(b0,b1))==minimum(a0,minimum(a1,minimum(b0,b1))))
# The ordered engine emits exactly a prefix, even if later workers finish first.
emitted,submitted,workers=z.Ints('emitted submitted workers');inv=z.And(0<=emitted,emitted<=submitted,submitted-emitted<=workers,workers>=1)
check('submit_bound',[inv,submitted-emitted<workers],z.And(emitted<=submitted+1,submitted+1-emitted<=workers))
check('emit_prefix',[inv,emitted<submitted],z.And(0<=emitted+1,emitted+1<=submitted,submitted-emitted-1<=workers))
# Sequential batch concatenation is independent of completion order, provided
# the queue drains submission order. Sequence theory models exact bytes.
A,B,C=z.Strings('A B C');check('ordered_bytes',[],z.Concat(z.Concat(A,B),C)==z.Concat(A,z.Concat(B,C)))
# Pure record-local validation may reuse successful results for equal keys.
context,k1,k2=z.Strings('context k1 k2');F=z.Function('validation',z.StringSort(),z.StringSort(),z.StringSort())
check('successful_validation_memo',[k1==k2,F(context,k1)==z.StringVal('')],F(context,k2)==z.StringVal(''))
# Three disjoint blocks cannot all contain a mismatch with distance <=2.
e0,e1,e2=z.Ints('e0 e1 e2');check('message_index_complete',[e0>=0,e1>=0,e2>=0,e0+e1+e2<=2],z.Or(e0==0,e1==0,e2==0))
# Packed event metadata consists of two native-width unsigned indices. Keys
# remain separate. This models lossless fixed-width pairing, not Perl pack's
# implementation or cross-machine serialization (worker spools are local).
for bits in (32,64):
 p0,c0,p1,c1=z.BitVecs('p0_%d c0_%d p1_%d c1_%d' % ((bits,)*4),bits)
 pair=z.Concat(p0,c0)
 check('event_indices_%d' % bits,[],z.And(z.Extract(2*bits-1,bits,pair)==p0,z.Extract(bits-1,0,pair)==c0,z.Implies(pair==z.Concat(p1,c1),z.And(p0==p1,c0==c1))))
(d/'results.json').write_text(json.dumps(dict(solver=z.get_version_string(),scope='abstract contract obligations; not whole-program equivalence',checks=rows),indent=2)+'\n');print(json.dumps(rows))
