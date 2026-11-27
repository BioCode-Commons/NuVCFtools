#!/usr/bin/env python3
"""String split and singleton-fold obligations; see the companion contract."""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);z.set_param(proof=True);checks=[]
def check(name,assumptions,claim):
 s=z.Solver();s.set(timeout=5000);s.add(*assumptions,z.Not(claim));(d/(name+'.smt2')).write_text(s.to_smt2());res=s.check();assert res==z.unsat,(name,res)
 (d/(name+'.proof')).write_text(str(s.proof()));checks.append(dict(name=name,result=str(res)))
field,tail=z.Consts('field tail',z.SeqSort(z.IntSort()));sep=z.Unit(z.IntVal(58));whole=z.Concat(field,sep,tail);i=z.Length(field)
# Token boundaries are assumed from the delimiter scan (manual proof below).
# Character sequences model both bytes and Unicode code points.
check('token_boundary_step',[],z.And(z.SubSeq(whole,0,i)==field,z.SubSeq(whole,i+1,z.Length(whole))==tail))
whole=z.Const('last_field',z.SeqSort(z.IntSort()));check('token_tail',[],z.SubSeq(whole,0,z.Length(whole))==whole)
# The map result and state are opaque: the obligation changes only scheduling.
state,x,y=z.Ints('state record1 record2');classify=z.Function('classify',z.IntSort(),z.IntSort());reduce=z.Function('reduce',z.IntSort(),z.IntSort(),z.IntSort());items=z.SeqSort(z.IntSort())
# A recursive fold over the classified sequence, not a numeric sum assumption.
fold=z.RecFunction('fold',z.IntSort(),items,z.IntSort());s=z.Int('s');seq=z.Const('seq',items)
z.RecAddDefinition(fold,[s,seq],z.If(z.Length(seq)==0,s,fold(reduce(s,seq[0]),z.SubSeq(seq,1,z.Length(seq)-1))))
check('singleton_fold',[],fold(fold(state,z.Unit(classify(x))),z.Unit(classify(y)))==reduce(reduce(state,classify(x)),classify(y)))
(d/'results.json').write_text(json.dumps(dict(solver=z.get_version_string(),scope='Abstract contracts; no whole-program or Data::Dumper proof',checks=checks),indent=2)+'\n');print(checks)
