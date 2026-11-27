#!/usr/bin/env python3
"""Preservation of the unconsumed delimiter's first-occurrence invariant."""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);z.set_param(proof=True)
chars=z.Array('characters',z.IntSort(),z.IntSort());start,consumed,other,end,delimiter,k=z.Ints('start consumed other end delimiter k');next_start=consumed+1
base=[start>=0,consumed>=start,consumed<end,z.Or(other==-1,z.And(other>consumed,other<end)),z.Implies(other>=0,z.Select(chars,other)==delimiter),z.ForAll(k,z.Implies(z.And(k>=start,k<end,z.Or(other==-1,k<other)),z.Select(chars,k)!=delimiter))]
claim=z.And(z.Or(other==-1,other>=next_start),z.Implies(other>=0,z.Select(chars,other)==delimiter),z.ForAll(k,z.Implies(z.And(k>=next_start,k<end,z.Or(other==-1,k<other)),z.Select(chars,k)!=delimiter)))
s=z.Solver();s.set(timeout=30000);s.add(*base,z.Not(claim));(d/'unconsumed_cursor.smt2').write_text(s.to_smt2());v=s.check();assert v==z.unsat; (d/'unconsumed_cursor.proof').write_text(str(s.proof()));(d/'results.json').write_text(json.dumps({'result':str(v),'solver':z.get_version_string(),'scope':'first-occurrence cursor invariant; string index and Perl string behavior assumed'},indent=2)+'\n');print(v)
