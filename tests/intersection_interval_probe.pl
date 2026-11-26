use strict;
use warnings;
use Test::More;
my ($before,$after)=@ARGV;
sub code {
 my ($p)=@_;open my $f,'<',$p or die $!;local $/;return <$f>;
}
for my $spec (['Ref',$before],['Opt',$after]) {
 my ($pkg,$dir)=@$spec;my $s=code("$dir/src/perl/vcf-isec");
 $s=~/(sub get_min_position\n.*?)(?=\n# Read one line)/s or die 'extract';my $fn=$1;
 my $stub=q{
 sub read_line { my ($opts,$f)=@_; return if $f->{eof};
    if (@{$f->{data}}) {push @{$f->{buf}},{pos=>shift @{$f->{data}}};$f->{nread}++} else {$f->{eof}=1} }
 sub prune_finished_sources {}
 };
 eval "package $pkg; $stub $fn";die $@ if $@;
}
srand(3917);
for my $case (0..499) {
 my @lists;for (0..int(rand(40))) {push @lists,[sort {$a<=>$b} map {int(rand(40))} 1..int(rand(50))]}
 my @outputs;
 for my $pkg ('Ref','Opt') {
  my @f=map {{data=>[@{$lists[$_]}],buf=>[],id=>$_}} 0..$#lists;my $opts={};my @out;
  no strict 'refs';
  while (my $winner=&{"${pkg}::get_min_position"}($opts,\@f)) {push @out,$winner->{id}.':'.shift(@{$winner->{buf}})->{pos}}
  push @outputs,\@out;
 }
 is_deeply($outputs[1],$outputs[0],"winner order including zero/ties, case $case");
}
my $s=code("$after/src/perl/vcf-annotate");$s=~/(sub prepare_annotation_group\n.*?)(?=\n# Called only by)/s or die 'extract index';eval $1;die $@ if $@;
for my $case (0..299) {
 my @rows=map {[int(rand(200))-10,int(rand(230))-10]} 1..int(rand(300));
 my $index=prepare_annotation_group(\@rows,{FROM=>0,TO=>1});
 for my $pos (map {int(rand(250))-15} 1..10) {
  my @expected=grep {$rows[$_][0]<=$pos && $rows[$_][1]>=$pos} 0..$#rows;
  is_deeply(annotation_rows_for_position($index,$pos),\@expected,"inclusive interval hits/order case $case position $pos");
 }
}
done_testing();
