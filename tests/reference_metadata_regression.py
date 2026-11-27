#!/usr/bin/env python3
"""Shared immutable FAI metadata, with unchanged first-query diagnostics."""
import argparse,json,os,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
for k in ['before','candidate','output']:p.add_argument('--'+k,required=True)
a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=False)
fa=d/'ref.fa';fa.write_text(''.join('>c'+str(i)+'\n'+'ACGT'*250+'\n' for i in range(32)))
subprocess.run(['samtools','faidx',str(fa)],check=True)
program=r'''use strict;use warnings;use FaSlice;use Scalar::Util qw(refaddr);use JSON::PP;
my ($file,$report)=@ARGV;my (%cache,@readers,%ids);
for my $i (0..31) {my $fa=FaSlice->new(file=>$file,size=>60,length_cache=>\%cache);push @readers,$fa;
print $fa->get_base("c$i",1),"\n";print $fa->get_slice("c$i",2,9),"\n";$ids{refaddr($fa->{chr_lengths})}=1;}
for my $i (0,1) {my $fa=FaSlice->new(file=>$file,size=>60,length_cache=>\%cache);
for my $pos (999,1001,1) {my $v=eval {$fa->get_base('c0',$pos)};print defined($v)?"value=$v\n":"failure=$@\n";}}
open(my $out,'>',$report) or die $!;print $out JSON::PP->new->encode({dictionaries=>scalar(keys %ids),readers=>scalar(@readers),entries=>scalar(keys %{$readers[0]{chr_lengths}})});close $out;
'''
outputs=[];metrics=[]
for label,root in [('before',a.before),('candidate',a.candidate)]:
 r=subprocess.run(['perl','-e',program,str(fa),str(d/(label+'.json'))],capture_output=True,env=dict(os.environ,PERL5LIB=root),timeout=60)
 def norm(x):return re.sub(rb' line \d+',b' line <source>',x.replace(root.encode(),b'<source>'))
 outputs.append((r.returncode,norm(r.stdout),norm(r.stderr)));metrics.append(json.loads((d/(label+'.json')).read_text()))
 for suffix,v in [('stdout',r.stdout),('stderr',r.stderr)]: (d/(label+'.'+suffix)).write_bytes(v)
assert outputs[0]==outputs[1] and outputs[0][0]==0,'FASTA result or diagnostics mismatch'
assert metrics[1]['dictionaries']==1 and metrics[0]['dictionaries']==32,metrics
# The actual fill-aa command must produce the same header, annotations and summary.
vcf='##fileformat=VCFv4.1\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'+''.join(f'c{i}\t1\t.\tA\tC\t.\tPASS\t.\n' for i in range(32))
runs=[]
for root in [a.before,a.candidate]:
 r=subprocess.run(['perl',str(Path(root)/'fill-aa'),'-a',str(fa)],input=vcf.encode(),capture_output=True,env=dict(os.environ,PERL5LIB=root),timeout=60)
 runs.append((r.returncode,r.stdout,re.sub(rb' line \d+',b' line <source>',r.stderr.replace(root.encode(),b'<source>'))))
assert runs[0]==runs[1] and runs[0][0]==0,'fill-aa mismatch'
(d/'results.json').write_text(json.dumps(dict(passed=True,before=metrics[0],candidate=metrics[1]),indent=2));print(json.dumps(dict(passed=True,shared_dictionaries=metrics)))
