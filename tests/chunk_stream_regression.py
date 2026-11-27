#!/usr/bin/env python3
"""Exact CLI output checks for raw sort transfer and streamed reference MD5."""
import argparse,subprocess,os,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);a=p.parse_args();d=Path(a.output);d.mkdir(parents=True,exist_ok=True);rows=[]
h=b'##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'
base=b'22\t2\t.\tA\tC\t.\tPASS\t.\n22\t1\t.\tA\tG\t.\tPASS\t.\n'
for name,payload in [('empty',b''),('header',h),('normal',h+base),('unterminated',h+base[:-1]),('crlf',(h+base).replace(b'\n',b'\r\n')),('boundary',h+base*2000),('huge-record',h+b'22\t2\t.\tA\tC\t.\tPASS\tX='+b'x'*131073+b'\n'+base),('mid-comment',h+base+b'#mid\n'+base)]:
 vals=[]
 for src in [a.before,a.candidate]:
  env=dict(os.environ,PERL5LIB=src,LC_ALL='C');v=subprocess.run(['perl',str(Path(src)/'vcf-sort'),'-p','1'],input=payload,env=env,capture_output=True,timeout=30);err=v.stderr.replace(str(Path(src)).encode(),b'<source>');err=re.sub(rb' line \d+',b' line <source>',err);vals.append((v.returncode,v.stdout,err))
 assert vals[0]==vals[1],name
 if name!='empty':assert vals[0][0]==0,(name,'requires GNU sort')
 rows.append(dict(case=name,passed=True))
# Test the sequence-stream contract independently of samtools formatting.
script=d/'digest.pl';script.write_text('''use strict;use warnings;use Digest::MD5;
my($mode,$file)=@ARGV;open(my $fh,'<',$file) or die $!;my $digest=Digest::MD5->new;my $len=0;
if($mode eq 'lines'){while(my $line=<$fh>){chomp $line;$len+=length($line);$digest->add($line)}}
else{while(read($fh,my $sequence,65536)){$sequence=~tr/\\n//d;$len+=length($sequence);$digest->add($sequence)}}
print "$len ",$digest->hexdigest,"\\n";
''')
for n in [0,1,59,60,61,65535,65536,65537,131073]:
 for ending in [b'',b'\n',b'\r\n']:
  seq=(b'ACGTNacgtn\r\0\n'*((n+12)//13))[:n]+ending;f=d/'sequence.bin';f.write_bytes(seq)
  vals=[subprocess.check_output(['perl',str(script),mode,str(f)]) for mode in ['lines','chunks']];assert vals[0]==vals[1];rows.append(dict(case='digest',length=n,ending=ending.hex(),passed=True))
f.unlink();(d/'results.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(rows))))
