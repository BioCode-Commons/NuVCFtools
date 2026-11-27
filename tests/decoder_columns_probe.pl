use strict;
use warnings;
use Vcf;
use JSON::PP;
use Storable qw(dclone);
my @out;
for my $version ('3.3','4.0','4.1','4.2') {
for my $format ('GT','GT:DP','DP:GT','GT:GT','GT:','') {
 for my $text ('0/1','0/1:5','0/1:5:9','.','','./.:2','1|0:7') {
  for my $share (0,1) {
   for my $compact (0,1) {
    for my $packed (0,1) {
     my $vcf=Vcf->new(version=>$version);
     $vcf->{columns}=[qw(CHROM POS ID REF ALT QUAL FILTER INFO FORMAT z a)];
     my @columns=('22','7','.','A','C,G','.','PASS','DP=2;FLAG',$format,$text,$text);
     my $columns=$packed ? join("\t",@columns) : \@columns;
     my $before=JSON::PP->new->canonical->encode($columns);
     my($rec,$err,$warnings);$warnings='';
     {local *STDERR;open(STDERR,'>',\$warnings) or die $!;eval {$rec=$vcf->next_prepared_hash($columns,$share,$compact,1);1} or $err=$@;}
     for ($err,$warnings) {next unless defined; s/ at .*? line \d+/ at <source>/g;}
     die 'changed input columns' unless JSON::PP->new->canonical->encode($columns) eq $before;
     push @out,{record=>$rec,error=>$err,warnings=>$warnings,share=>$share,compact=>$compact,packed=>$packed};
    }
   }
  }
 }
}
}
print JSON::PP->new->canonical->encode(\@out);
