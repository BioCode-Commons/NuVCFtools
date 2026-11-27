#!/usr/bin/env python3
"""Abstract stream contracts; source-to-model mapping remains manual."""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);z.set_param(proof=True);rows=[]
def check(name,assumptions,claim):
 s=z.Solver();s.set(timeout=30000);s.add(*assumptions,z.Not(claim));(d/(name+'.smt2')).write_text(s.to_smt2());result=s.check()
 if result!=z.unsat:raise RuntimeError((name,str(result)))
 (d/(name+'.proof')).write_text(str(s.proof()));rows.append(dict(name=name,result=str(result)))
ByteSeq=z.SeqSort(z.IntSort());empty=z.Empty(ByteSeq);unit=lambda x:z.Unit(z.IntVal(x) if isinstance(x,int) else x)
pending=z.Bool('pending');c=z.Int('byte');q=z.Int('reference_prefix_length');cr,lf=13,10
relation=z.And(q>=0,q<=1,pending==(q==1))
# Reference: a greedy CRLF matcher with one pending prefix byte.
ref_state=z.If(q==1,z.If(c==lf,0,z.If(c==cr,1,0)),z.If(c==cr,1,0))
ref_out=z.If(q==1,z.If(c==lf,unit(lf),z.If(c==cr,unit(cr),z.Concat(unit(cr),unit(c)))),z.If(c==cr,empty,unit(c)))
# Streaming state: hold CR, emit an old unmatched CR, then a non-CR byte.
stream_state=c==cr
stream_out=z.Concat(z.If(z.And(pending,c!=lf),unit(cr),empty),z.If(c==cr,empty,unit(c)))
check('crlf_transition',[relation,c>=0,c<=255],z.And((ref_state==1)==stream_state,ref_out==stream_out))
# Identical initial state and identical pending-byte flush complete the
# induction for arbitrary byte streams, within this abstract transducer.
check('crlf_flush',[relation],z.SubSeq(unit(cr),0,q)==z.If(pending,unit(cr),empty))
check('cr_byte_map',[c>=0,c<=255],z.If(c==cr,unit(lf),unit(c))==unit(z.If(c==cr,lf,c)))
# Array gather and incremental append use the same ordered indices, including
# repeated indices. Bounds exclude undefined-field diagnostic behavior, which
# stays on the existing path in the implementation.
fields=z.Array('fields',z.IntSort(),z.StringSort());indices=z.Ints('i1 i2 i3 i4');sep=z.StringVal('\t')
values=[z.Select(fields,0)]+[z.Select(fields,i) for i in indices]
old=values[0]
for value in values[1:]:old=z.Concat(old,sep,value)
flat=[]
for i,value in enumerate(values):
 if i:flat.append(sep)
 flat.append(value)
check('ordered_column_join',[z.And(i>=0,i<100) for i in indices],old==z.Concat(*flat))
x,y,delta=z.Ints('old_count new_count delta');limit=2**63-1
check('serial_count_step',[x==y,x>=0,delta>=0,x+delta<=limit],x+delta==y+delta)
(d/'results.json').write_text(json.dumps(dict(solver=z.get_version_string(),scope='abstract stream contracts, not verified Perl or regex implementation',checks=rows),indent=2)+'\n');print(json.dumps(rows))
