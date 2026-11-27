use strict;
use warnings;
use Scalar::Util qw(weaken);
use NuOrderedWorkers;
use NuOrderedCounters;
use Storable qw(nfreeze thaw);

my $payload={text=>'record'};
my $weak=$payload;weaken($weak);
my $item=[0,$payload];undef $payload;
my $a=NuOrderedWorkers::prepared_value($item);
my $b=NuOrderedWorkers::prepared_value($item);
die 'accessor changed identity' unless $a==$b;
undef $a;undef $b;
my $value=NuOrderedWorkers::take_prepared_value($item);
die 'queue retained payload' if defined $item->[1];
die 'value prematurely freed' unless defined $weak;
undef $value;
die 'completed record still retained' if defined $weak;

my $c=NuOrderedCounters->new();
{
 local $NuOrderedCounters::active=$c;
 NuOrderedCounters::add($c->root(),2,'sample','ALT');
 NuOrderedCounters::add($c->root(),3,'sample','REF');
 NuOrderedCounters::add($c->root(),4,'sample','ALT');
}
my $part=thaw(nfreeze($c->snapshot()));
my $out={};NuOrderedCounters::merge($out,$part);
die 'counter mismatch' unless $out->{sample}{ALT}==6 && $out->{sample}{REF}==3;
NuOrderedCounters::merge($out,thaw(nfreeze($c->snapshot())));
die 'counter alias changed source' unless $out->{sample}{ALT}==12 && $c->root()->{sample}{ALT}==6;
print "ownership and compact counter serialization passed\n";
