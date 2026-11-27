use strict;
use warnings;
use utf8;
use NuOrderedCounters;
use Storable qw(nfreeze thaw);
my @keys=(q[],"nul\0key",'样本',"01",'1',map {"sample$_"} 1..1000);
my $c=NuOrderedCounters->new();
{
 local $NuOrderedCounters::active=$c;
 for my $i (0..$#keys) {
  NuOrderedCounters::add($c->root(),$i+1,$keys[$i],'REF');
  NuOrderedCounters::add($c->root(),2,$keys[$i],'ALT');
  NuOrderedCounters::add($c->root(),3,$keys[$i],'REF');
 }
}
my $part=thaw(nfreeze($c->snapshot()));
my $events=$part->[0];
die "counter log still allocates an array per event\n" unless @$events==2 && !ref($events->[0]) && ref($events->[1]) eq 'ARRAY';
my $stride=length(pack('J2',0,0));
die 'event metadata/key cardinality mismatch' unless length($events->[0])==@keys*3*$stride;
my $out={};
NuOrderedCounters::merge($out,$part);
for my $i (0..$#keys) {
 die 'replay changed counter' unless $out->{$keys[$i]}{REF}==$i+4 && $out->{$keys[$i]}{ALT}==2;
}
NuOrderedCounters::merge($out,thaw(nfreeze($c->snapshot())));
for my $i (0..$#keys) {
 die 'merge mutated serialized source' unless $c->root()->{$keys[$i]}{REF}==$i+4 && $out->{$keys[$i]}{REF}==2*($i+4);
}
print 'packed events passed: ',scalar(@keys)*3,' entries, ',length($events->[0])," metadata bytes; Unicode/NUL keys and detached replay preserved\n";
