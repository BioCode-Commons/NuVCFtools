"""Reference-header induction; VCF headers represented as count + exact map."""
import argparse,json
from pathlib import Path
import z3 as z
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);z.set_param(proof=True)
r=z.Array('reference_map',z.StringSort(),z.IntSort());h=z.Array('earlier_map',z.StringSort(),z.IntSort());c=z.Array('current_map',z.StringSort(),z.IntSort());rn,hn,cn=z.Ints('reference_count earlier_count current_count');key=z.String('key')
# -1 is absent; real parsed column indices are positive. Whole-array equality
# denotes the two-direction key/value test, not just equal key counts.
s=z.Solver();s.add(r==h,rn==hn,z.Or(z.And(c==r,cn==rn)!=z.And(c==h,cn==hn),z.Select(r,key)!=z.Select(h,key)))
(d/'header_transitivity.smt2').write_text(s.to_smt2());v=s.check();assert v==z.unsat; (d/'header_transitivity.proof').write_text(str(s.proof()));(d/'results.json').write_text(json.dumps({'result':str(v),'solver':z.get_version_string(),'scope':'abstract parsed-header relation; manual connection to Perl'} ,indent=2)+'\n');print(v)
