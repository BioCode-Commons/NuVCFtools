use strict;
use warnings;
use Test::More;
use Scalar::Util 'refaddr';
use Data::Dumper;
use Vcf;
my $header=join("\n",'##fileformat=VCFv4.1','##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">','##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">',"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB\tC",'');
sub reader { open(my $fh,'<',\$header) or die $!; my $v=Vcf->new(fh=>$fh); $v->parse_header(); return $v; }
my $line="22\t1\t.\tA\tC\t.\tPASS\t.\tGT:DP\t0/1:8\t0/1:8\t1/1:8\n";
my ($v,$r)=(reader(),reader());
my $normal=$v->next_data_hash($line);
my $shared=$r->next_data_hash_readonly($line);
is_deeply($shared,$normal,'equal record values');
is(refaddr($shared->{gtypes}{A}),refaddr($shared->{gtypes}{B}),'equal neighboring fields share one object');
isnt(refaddr($shared->{gtypes}{B}),refaddr($shared->{gtypes}{C}),'different fields remain separate');
isnt(refaddr($normal->{gtypes}{A}),refaddr($normal->{gtypes}{B}),'mutable API remains independent');
$normal->{gtypes}{A}{GT}='0/0';is($normal->{gtypes}{B}{GT},'0/1','mutating one sample does not affect its neighbor');
my $second=$r->next_data_hash_readonly($line);
isnt(refaddr($second->{gtypes}{A}),refaddr($shared->{gtypes}{A}),'sharing ends at record boundary');
for my $format ('GT:DP','DP:GT','GT:GT','GT','DP') {
 for my $value ('0/1:8','0/1','.:.','0/1:8:9') {
  my $row="22\t2\t.\tA\tC\t.\tPASS\t.\t$format\t$value\t$value\t$value\n";
  my(@records,@warnings);
  for my $readonly (0,1) {
   my $x=reader();my $warnings='';local $SIG{__WARN__}=sub {$warnings.=join('',@_)};
   push @records,$readonly ? $x->next_data_hash_readonly($row) : $x->next_data_hash($row);
   push @warnings,$warnings;
  }
  is_deeply($records[0],$records[1],"values for $format / $value");
  is($warnings[0],$warnings[1],"diagnostics for $format / $value");
 }
}
$r=reader();$r->set_samples(include=>['A','C']);
is_deeply([sort keys %{$r->next_data_hash_readonly($line)->{gtypes}}],['A','C'],'sample selection retained');
done_testing();
