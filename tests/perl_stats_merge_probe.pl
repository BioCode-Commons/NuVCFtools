use strict;
use warnings;
use Vcf;
use VcfStats;
use JSON::PP;
use Storable qw(dclone);
my @out;
# A genotype-to-count optimization must retain haploid, partial and legacy
# polyploid counting, even though vcf-stats rejects polyploid calls.
for my $version ('3.3','4.0','4.1','4.2') {
    my $v=Vcf->new(version=>$version);
    for my $n (1,2,3,19) {
        my %g;
        my @gt=('0/0','0/1','1|0','1/1','1/2','./1','1/.','.','./.','2','0|1|2','01/1','1/01','00/2');
        for my $i (0..$n*scalar(@gt)-1) {$g{"S$i"}={GT=>$gt[$i%@gt]};}
        $g{no_GT}={DP=>5};
        push @out,[$version,'counts',$n,[$v->calc_an_ac(\%g,3)]];
    }
    for my $trim (0,1) {
        $v->{trim_redundant_ALTs}=$trim;
        for my $ref ('A','C','ACT') {
            my @gt=($ref.'/G','G|'.$ref,'G/G','./G','G/.','.','0','1/2','2|1','*','G|G|'.$ref);
            my $rec={REF=>$ref,ALT=>['G','T','AG'],gtypes=>{}};
            my @samples=map {'S'.$_} (0..87);
            for my $i (0..$#samples) {$rec->{gtypes}{$samples[$i]}={GT=>$gt[$i%@gt]};}
            $v->format_genotype_strings($rec,\@samples);
            push @out,[$version,'format',$trim,$rec];
        }
    }
}
print JSON::PP->new->canonical->encode(\@out),"\n";
