package NuOrderedCounters;

use strict;
use warnings;
use Scalar::Util qw(refaddr);

# Statistics workers start from an empty counter tree. Record first insertion
# order separately from values so reduction does not reorder unsorted dumps.
sub new
{
    my ($class)=@_;
    my $root={};
    my $self=bless {events=>[],nodes=>[$root],ids=>{refaddr($root)=>0},root=>$root},$class;
    return $self;
}
our $active;
sub branch
{
    my ($hash,$key)=@_;
    return $hash->{$key} if exists $hash->{$key};
    my $child=$hash->{$key}={};
    if ($active) {
        my $id=@{$active->{nodes}};
        $active->{ids}{refaddr($child)}=$id;
        push @{$active->{nodes}},$child;
        push @{$active->{events}},[$active->{ids}{refaddr($hash)},$key,$id];
    }
    return $child;
}
sub add
{
    my ($hash,$value,@path)=@_;
    my $key=pop @path;
    $hash=branch($hash,$_) for @path;
    if (!exists $hash->{$key}) {
        push @{$active->{events}},[$active->{ids}{refaddr($hash)},$key,undef];
    }
    $hash->{$key}+=$value;
}
sub root { return $_[0]{root}; }
sub snapshot
{
    my ($self)=@_;
    # Serialize the existing nodes by reference. Building [key,value] pairs
    # copied every leaf into another Perl array immediately before nstore.
    # Storable preserves aliases; consumers read scalar leaves only.
    return [$self->{events},$self->{nodes}];
}
sub merge
{
    my ($root,$part)=@_;
    my @nodes=($root);
    for my $event (@{$part->[0]}) {
        my ($parent,$key,$child)=@$event;
        my $hash=$nodes[$parent];
        if (defined $child) {
            $hash->{$key}={} unless exists $hash->{$key};
            $nodes[$child]=$hash->{$key};
        }
        else { $hash->{$key}=0 unless exists $hash->{$key}; }
    }
    for my $id (0..$#{$part->[1]}) {
        while (my ($key,$value)=each %{$part->[1][$id]}) {
            $nodes[$id]{$key} += $value unless ref $value;
        }
    }
}

1;
