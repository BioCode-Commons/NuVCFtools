#!/usr/bin/env python3
"""Byte-feed invariant for line-chomp versus bounded LF deletion."""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);z.set_param(proof=True)
seq=z.SeqSort(z.IntSort());empty=z.Empty(seq)
consumed=z.Const('reference_consumed',seq);line=z.Const('pending_line',seq);chunked=z.Const('optimized_consumed',seq);byte=z.Int('byte')
invariant=chunked==z.Concat(consumed,line)
next_consumed=z.If(byte==10,z.Concat(consumed,line),consumed)
next_line=z.If(byte==10,empty,z.Concat(line,z.Unit(byte)))
next_chunked=z.If(byte==10,chunked,z.Concat(chunked,z.Unit(byte)))
rows=[]
for name,claim in [('sequence_feed_step',next_chunked==z.Concat(next_consumed,next_line)),('sequence_eof_flush',z.And(z.Concat(consumed,line)==chunked,z.Length(z.Concat(consumed,line))==z.Length(chunked)))]:
 s=z.Solver();s.add(invariant,byte>=0,byte<=255,z.Not(claim));(d/(name+'.smt2')).write_text(s.to_smt2());v=s.check();assert v==z.unsat;(d/(name+'.proof')).write_text(str(s.proof()));rows.append({'name':name,'result':str(v)})
(d/'results.json').write_text(json.dumps({'solver':z.get_version_string(),'checks':rows,'scope':'logical digest input bytes; digest library and Perl I/O assumed'},indent=2)+'\n');print(rows)
