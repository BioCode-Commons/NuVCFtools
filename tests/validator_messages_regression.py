#!/usr/bin/env python3
"""Exact ordered-message grouping checks, including non-transitive matches."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);a=p.parse_args()
d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
messages=['','one','two tokens','a b c','a x c','a x y','z x y','z b c']
for width in range(1,25):
 for i in range(24):
  tokens=[f'w{width}_{j}_{i}' for j in range(width)]
  messages.append(' '.join(tokens))
  for changes in range(1,min(width,4)+1):
   variant=tokens[:]
   for j in range(changes):variant[(j*7)%width]='replacement'+str(j)
   messages.append(' \t'.join(variant))
messages=messages+list(reversed(messages))+['same prefix x','same prefix y','same other z']
input_data=('\n'.join(messages)+'\n').encode()
program=r'''
my ($file)=@ARGV;
open(my $fh,'<',$file) or die $!; local $/; my $code=<$fh>; close $fh;
$code =~ s/my \$opts = parse_params\(\);\s*do_validation\(\$opts\);\s*exit;// or die "entry point not found";
eval $code; die $@ if $@;
my $opts={known_lines=>[]};
local $/="\n";
while(my $line=<STDIN>) { print_or_discard_line($opts,$line); }
print_summary($opts);
'''
results=[]
for seed in [0,1,19]:
 outs=[]
 for name,root in [('before',a.before),('candidate',a.candidate)]:
  env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0')
  r=subprocess.run(['perl','-e',program,str(Path(root)/'vcf-validator')],input=input_data,capture_output=True,env=env,timeout=60)
  (d/f'{name}-{seed}.stdout').write_bytes(r.stdout);(d/f'{name}-{seed}.stderr').write_bytes(r.stderr)
  outs.append((r.returncode,r.stdout,r.stderr))
 passed=outs[0]==outs[1] and outs[0][0]==0
 results.append(dict(seed=seed,passed=passed,messages=len(messages)))
 if not passed:raise RuntimeError(f'message grouping mismatch, seed {seed}')
(d/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=len(results),messages=len(messages))))
