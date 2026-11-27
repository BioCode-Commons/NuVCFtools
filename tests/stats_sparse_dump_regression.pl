use strict;use warnings;use Data::Dumper;
my ($before,$after)=@ARGV;
for my $pair ([$before,'Before'],[$after,'After']) {
 open(my $f,'<',$pair->[0]) or die $!;local $/;my $s=<$f>;
 my ($body)=$s=~/(sub dump\n.*?)(?=\nsub _calc_tstv)/s;die 'missing dump' unless $body;
 eval 'package '.$pair->[1].'; use Data::Dumper;'.$body;die $@ if $@;
}
my $count=0;
for my $perl (0,1) {for my $purity (0,1) {for my $terse (0,1) {
 local $Data::Dumper::Useperl=$perl;local $Data::Dumper::Purity=$purity;local $Data::Dumper::Terse=$terse;
 for my $n (0..30) {
  my $tree={};for my $i (0..$n) {$tree->{'s'.$i}={count=>$i,snp=>{'A>G'=>$i,'C>T'=>2*$i},zero=>0,missing=>undef,text=>"a\0b\n"};}
  my $shared={a=>[1,2,3]};$tree->{alias1}=$shared;$tree->{alias2}=$shared;$tree->{cycle}=$tree if $n%2;
  my $scalar='same';$tree->{scalar1}=\$scalar;$tree->{scalar2}=\$scalar;
  my $self={stats=>$tree};my ($x,$y)=(Before::dump($self),After::dump($self));die "Dump mismatch n=$n perl=$perl purity=$purity terse=$terse" unless $x eq $y;
  delete $tree->{cycle};$count++;
 }
}}}
print "$count sparse Dumper cases passed\n";
