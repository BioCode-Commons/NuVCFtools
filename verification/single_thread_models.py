#!/usr/bin/env python3
"""Abstract obligations for column borrowing, stable filtering and readonly reuse.

The implementation-to-model assumptions are recorded in single-thread-contracts.md.
This does not verify Perl, its callbacks, or the complete programs.
"""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True)
z.set_param(proof=True);rows=[]
def check(name,assumptions,claim):
 s=z.Solver();s.set(timeout=30000);s.add(*assumptions,z.Not(claim));(d/(name+'.smt2')).write_text(s.to_smt2());r=s.check()
 if r!=z.unsat:raise RuntimeError((name,str(r)))
 (d/(name+'.proof')).write_text(str(s.proof()));rows.append(dict(name=name,result=str(r)))
# The borrowed array remains stable for all reads; snapshot is value-equal.
A,B=[z.Array(name,z.IntSort(),z.StringSort()) for name in ['A','B']];i=z.Int('i')
check('stable_column_read',[A==B],z.Select(A,i)==z.Select(B,i))
# For any two retained header entries, selected entries between them include
# the first entry. Prefix-count ranks therefore preserve their strict order.
i,j,ki,kj,ri,rj,between=z.Ints('i j ki kj ri rj between')
check('filtered_sample_order',[i<j,ki<kj,between>=1,rj==ri+between],z.And(ri<rj,ki<kj))
# One loop step emits exactly one selected key or leaves the prefix untouched.
n,k,selected=z.Int('n'),z.Int('k'),z.Bool('selected');out=z.Array('out',z.IntSort(),z.IntSort())
new=z.If(selected,z.Store(out,n,k),out);nn=n+z.If(selected,1,0);q=z.Int('q')
check('filtered_prefix_step',[n>=0,q>=0,q<n],z.And(z.Select(new,q)==z.Select(out,q),nn>=n,nn<=n+1,z.Implies(selected,z.Select(new,n)==k)))
# Decode is pure for a fixed record and well-formed equal complete fields.
context,x,y=z.Strings('context x y');decode=z.Function('decode',z.StringSort(),z.StringSort(),z.IntSort())
check('readonly_field_reuse',[x==y],decode(context,x)==decode(context,y))
(d/'results.json').write_text(json.dumps(dict(solver=z.get_version_string(),scope='abstract contracts, not whole-program equivalence',checks=rows),indent=2)+'\n');print(json.dumps(rows))
