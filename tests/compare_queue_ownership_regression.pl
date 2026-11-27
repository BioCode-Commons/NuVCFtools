use strict;
use warnings;
use Vcf;
use NuOrderedWorkers;
my $root=shift @ARGV;
open(my $fh,'<',"$root/vcf-compare") or die $!;
my $source=do {local $/;<$fh>};close $fh;
$source =~ s/my \$opts = parse_params\(\);.*?\bexit;//s or die 'entry';
eval $source;die $@ if $@;
my @readers=map {Vcf->new(version=>'4.1')} (0,1);
my $id=0;
for my $r (@readers) {$r->{file}="input".$id++;$r->{columns}=[qw(CHROM POS ID REF ALT QUAL FILTER INFO FORMAT S0 S1)];}
my $line="22\t7\t.\tA\tC\t.\tPASS\t.\tGT\t0/1\t1/1\n";
my $expected=length($line)*2;
my @groups=map {[map {{line=>$line,chr=>22,pos=>7,ref=>'A',alt=>'C',vcf=>$_}} @readers]} (1..3);
my $seen=0;
{
 no warnings qw(redefine once);
 local *main::read_next_group=sub {shift @groups};
 local *NuOrderedWorkers::run=sub {
  my (%args)=@_;
  while (my $batch=$args{next}->()) {
   die 'input-byte batch boundary changed' unless @$batch==1;
   for my $item (@$batch) {
    my $group=NuOrderedWorkers::take_prepared_value($item);
    for my $record (@$group) {
     die "queue retains both raw and prepared text\n" if exists($record->{line}) && exists($record->{prepared});
     my $columns=NuOrderedWorkers::take_prepared_value($record->{prepared});
     my $parsed=$record->{vcf}->next_prepared_hash($columns);
     die 'prepared data changed' unless $parsed->{gtypes}{S0}{GT} eq '0/1' && $parsed->{gtypes}{S1}{GT} eq '1/1';
    }
    $seen++;
   }
  }
 };
 do_region_stats({workers=>4,cmp_genotypes=>1,worker_batch_bytes=>$expected},\@readers);
}
die 'missing group' unless $seen==3;
print "comparison queue ownership and original-byte boundaries passed\n";
