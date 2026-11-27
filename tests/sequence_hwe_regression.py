#!/usr/bin/env python3
"""Bitwise HWE probability and exact FASTA flush checks of isolated routines."""
import argparse,subprocess,os,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);a=p.parse_args()
d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
loader=r'''my ($path,$tool)=@ARGV;open(my $f,'<',"$path/$tool") or die $!; local $/;my $s=<$f>;close $f;
$s =~ s/my \$opts = parse_params\(\);.*?\bexit;//s or die 'entry';eval $s;die $@ if $@;
'''
hwe=loader+r'''for my $a (0..14) { for my $b (0..14) {for my $h (0..14) {
print unpack('H*',pack('d',eval_hwe($a,$b,$h,undef))),"\n";
}}}
for my $v ([0,0,1],[4999,1,0],[1,1,5000],[2500,2500,2500],[1,9999,1]) { print unpack('H*',pack('d',eval_hwe(@$v,undef))),"\n"; }
'''
flush=loader+r'''for my $n (0,1,59,60,61,119,120,121,1001,100000) {
for my $keep (0,60) { for my $idx (0,1,5) {
my $s=substr('ACGT'x(1+int($n/4)),0,$n);my $o={fa_len=>$n,fa_buf=>$s,fa_pos=>21,fa_idx=>$idx};
flush_fa_buffer($o,$keep);print "state ",join('|',map {$o->{$_}} qw(fa_len fa_buf fa_pos fa_idx)),"\n";
}}}
'''
results=[]
for name,tool,program in [('hwe','vcf-annotate',hwe),('consensus-flush','vcf-consensus',flush)]:
 outs=[]
 for label,root in [('before',a.before),('candidate',a.candidate)]:
  r=subprocess.run(['perl','-e',program,root,tool],env=dict(os.environ,PERL5LIB=root),capture_output=True,timeout=30)
  (d/f'{name}-{label}.stdout').write_bytes(r.stdout);(d/f'{name}-{label}.stderr').write_bytes(r.stderr)
  outs.append((r.returncode,r.stdout,r.stderr))
 passed=outs[0]==outs[1] and outs[0][0]==0
 results.append(dict(case=name,passed=passed))
 if not passed:raise RuntimeError(name+' mismatch')
(d/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(passed=True,hwe_cases=3380,flush_cases=60)))
