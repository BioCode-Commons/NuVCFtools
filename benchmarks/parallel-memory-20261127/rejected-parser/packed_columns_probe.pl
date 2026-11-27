use strict;
use warnings;
use utf8;
use Vcf;
use JSON::PP;
my @lines=("22\t1\t.\tA\tC\t.\tPASS\t.\tGT\t0/1\n","22 1 . A C . PASS . GT 0/1\n");
my @pieces=(q[],q[A],"\t","\n");
for my $code (0..4**5-1) {
 my ($n,$s)=($code,q[]);
 for (1..5) {$s.=$pieces[$n%4];$n=int($n/4);}
 push @lines,$s;
}
push @lines,"chr样本\t7\t.\tA\tC\t.\tPASS\t.\tGT\t0/1\t", "a\0b\tend\r\n";
my @out;
for my $separator ("\n",q[],undef,"X\tY") {
 local $/=$separator;
 for my $ncols (1,3,10) {
  for my $line (@lines) {
   my $v=Vcf->new(version=>'4.1');$v->{columns}=[map {"C$_"} 1..$ncols];$v->{header_parsed}=1;
   # No stream fallback: next_line is made explicitly empty for false-valued input.
   no warnings 'redefine';
   local *Vcf::next_line=sub {undef};
   my ($value,$err,$warning);$warning='';
   {
    local *STDERR;open(STDERR,'>',\$warning) or die $!;
    eval {$value=$v->prepare_data_columns($line,1);1} or $err=$@;
   }
   for ($err,$warning) {next unless defined; s/0x[0-9a-f]+/<address>/g;s/\bline \d+/line <source>/g;s/ at .*?Vcf\.pm/ at <source>/g;}
   push @out,[$ncols,$line,$value,defined($value)?!!utf8::is_utf8($value):undef,$err,$warning,$v->{trailing_tabs_warned}];
  }
 }
}
print JSON::PP->new->canonical->ascii->encode(\@out),"\n";
