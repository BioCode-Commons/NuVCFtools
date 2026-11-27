use strict;use warnings;use JSON::PP;
my ($before,$candidate)=@ARGV;
sub load_split {
 my ($path,$package)=@_;open(my $fh,'<',$path) or die $!;local $/;my $s=<$fh>;
 my ($body)=$s=~/(sub split_gt\n.*?)(?=\n=head2 split_by)/s;die 'split function missing' unless defined $body;
 eval "package $package;use strict;use warnings;$body";die $@ if $@;
}
load_split($before,'Reference');load_split($candidate,'Candidate');
my $json=JSON::PP->new->canonical;my $cases=0;
sub check {
 my($text)=@_;my @out;
 for my $f (\&Reference::split_gt,\&Candidate::split_gt) {
  my $warn='';local $SIG{__WARN__}=sub {$warn.=join('',@_)};my @values=$f->(undef,$text);
  $warn =~ s/ at \(eval \d+\) line \d+/ at <source>/g;
  push @out,$json->encode([\@values,$warn]);
 }
 die 'genotype split differs: '.$json->encode($text) unless $out[0] eq $out[1];$cases++;
}
my @level=('');check('');
for (1..6) {my @next;for my $s (@level) {for my $c ('/','|','0','1','.') {my $t=$s.$c;check($t);push @next,$t}}@level=@next;}
check(undef);
for my $sep ('/','|','/|') {check(join($sep,('0123456789')x10000));}
for my $s ("a\0b/\t|\n",chr(0x4e00).'|'.chr(0x4e8c).'/',"0/|",'not-a-genotype') {check($s);}
print "$cases genotype cursor cases passed\n";
