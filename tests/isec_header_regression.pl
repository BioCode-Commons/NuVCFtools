use strict;
use warnings;
use JSON::PP;
my ($before,$candidate)=@ARGV;
die "usage: before/vcf-isec candidate/vcf-isec\n" unless defined $candidate;
sub load_check {
    my ($path,$package)=@_;
    open(my $fh,'<',$path) or die "$path: $!";
    local $/;my $text=<$fh>;
    my ($body)=$text =~ /(sub check_columns\n.*?)(?=\nsub vcf_isec)/s;
    die "missing check_columns" unless defined $body;
    eval "package $package; use strict; use warnings; $body";
    die $@ if $@;
}
load_check($before,'Reference');load_check($candidate,'Candidate');
my $json=JSON::PP->new->canonical;
my @names=qw(CHROM POS ID REF ALT QUAL FILTER INFO FORMAT z a m);
my $cases=0;
for my $n (0..12) {
    for my $bad (-1..$n-1) {
        for my $kind (0..5) {
            my @vcfs;
            for my $i (0..$n-1) {
                if ($i%4==0) { push @vcfs,{}; next; }
                my @cols=@names;my %map=map {$cols[$_]=>$_+1} 0..$#cols;
                if ($i==$bad) {
                    if ($kind==0) { pop @cols; delete $map{m}; }
                    if ($kind==1) { $map{a}=12;$map{m}=11;@cols[10,11]=@cols[11,10]; }
                    if ($kind==2) { delete $map{m};$map{x}=12;$cols[11]='x'; }
                    if ($kind==3) { delete $map{m}; }
                    if ($kind==4) { $map{x}=13; }
                    if ($kind==5) { @cols=();%map=(); }
                }
                push @vcfs,{columns=>\@cols,has_column=>\%map};
            }
            my $saved=$json->encode(\@vcfs);my @out;
            for my $f (\&Reference::check_columns,\&Candidate::check_columns) {
                my $warning='';local $SIG{__WARN__}=sub {$warning.=join('',@_)};
                $f->({},\@vcfs);push @out,$warning;
                die "mutated header" unless $json->encode(\@vcfs) eq $saved;
            }
            die "different diagnostic n=$n bad=$bad kind=$kind\n" unless $out[0] eq $out[1];
            $cases++;
        }
    }
}
print "$cases header equivalence cases passed\n";
