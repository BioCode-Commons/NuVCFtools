#!/usr/bin/env python3
"""Exact tournament ordering and CLI checks against the frozen serial version."""
import argparse,itertools,json,os,re,subprocess,shutil
from pathlib import Path
from perl_stats_merge_regression import fixture
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
p.add_argument('--workers',type=int,default=1);p.add_argument('--indexed',action='store_true');a=p.parse_args()
d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
loader=r'''my $root=shift @ARGV;open(my $f,'<',"$root/vcf-compare") or die $!;local $/;my $s=<$f>;close $f;
$s =~ s/my \$opts = parse_params\(\);.*?\bexit;//s or die 'entry';eval $s;die $@ if $@;
'''
# Exhaust all head-position combinations, preserving ties and the legacy scan's
# false-valued positions. No real VCF records are needed for this routine check.
program=loader+r'''for my $n (1..6) {
for my $code (0..4**$n-1) {
my $x=$code;my @f;for my $i (0..$n-1) {my $v=$x%4;$x=int($x/4);push @f,{id=>$i,eof=>1,buf=>$v==3?[]:[{pos=>$v}]};}
my $o={};while(my $f=get_min_position($o,\@f)){print $f->{id};shift @{$f->{buf}};}print "\n";
}}
'''
results=[]
for seed in [0,1,19]:
 runs=[]
 for label,root in [('before',a.before),('candidate',a.candidate)]:
  r=subprocess.run(['perl','-e',program,root],capture_output=True,env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0'),timeout=30)
  runs.append((r.returncode,r.stdout,r.stderr))
 passed=runs[0]==runs[1] and runs[0][0]==0
 results.append(dict(case='tournament',seed=seed,passed=passed))
 if not passed:
  for label,r in zip(['before','candidate'],runs):
   (d/(label+'.stdout')).write_bytes(r[1]);(d/(label+'.stderr')).write_bytes(r[2])
  raise RuntimeError('tournament mismatch')
if a.indexed:
 fixture(d)
 copies=[]
 for i in range(3):
  f=d/f'copy-{i}.vcf.gz';shutil.copyfile(d/'all.vcf.gz',f);shutil.copyfile(d/'all.vcf.gz.tbi',str(f)+'.tbi');copies.append(str(f))
 fa=d/'reference.fa';fa.write_text('>22\n'+('A'*20002000)+'\n')
 subprocess.run(['samtools','faidx',str(fa)],check=True)
 cases=[('genotypes',['-g']),('selection',['-g','-s','S0,S3,S9']),('filter',['-g','-a']),('positions',[]),('windows',['-w','30']),('sequence',['-R',str(fa),'-w','30'])]
 for seed in [0,1,19]:
  for tag,flags in cases:
   # Identical rich records cover FORMAT and allele handling; region transitions
   # reset the winner tree, and duplicate source paths still preserve file order.
   args=flags+['-r','22:20000001-20000750,22:20000800-20002000']+copies
   runs=[]
   for root in [a.before,a.candidate]:
    extra=['--workers',str(a.workers),'--worker-batch-bytes','1024'] if root==a.candidate and tag!='sequence' else []
    r=subprocess.run(['perl',str(Path(root)/'vcf-compare')]+args+extra,capture_output=True,env=dict(os.environ,PERL5LIB=root,PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C'),timeout=60)
    err=re.sub(rb' line \d+',b' line <source>',r.stderr.replace(root.encode(),b'<source>'))
    runs.append((r.returncode,r.stdout,err))
   passed=runs[0]==runs[1] and runs[0][0]==0
   results.append(dict(case=tag,seed=seed,passed=passed))
   if not passed:
    for label,r in zip(['before','candidate'],runs):
     (d/(tag+'-'+label+'.stdout')).write_bytes(r[1]);(d/(tag+'-'+label+'.stderr')).write_bytes(r[2])
    (d/'results.json').write_text(json.dumps(results,indent=2));raise RuntimeError(tag+' mismatch')
(d/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(dict(passed=True,cases=len(results),tournament_head_combinations=5460)))
