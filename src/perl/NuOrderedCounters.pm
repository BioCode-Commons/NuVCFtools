package NuOrderedCounters;

use strict;
use warnings;
use Scalar::Util qw(refaddr);

# Spools are written and read by one Perl runtime on the same machine. Native
# unsigned Perl integer indices cover every representable array index. Keys
# stay in a separate array, preserving byte/Unicode flags and embedded NULs.
use constant EVENT_BYTES => length(pack('J2',0,0));

# Statistics workers start from an empty counter tree. Record first insertion
# order separately from values so reduction does not reorder unsorted dumps.
sub new
{
    my ($class)=@_;
    my $root={};
    my $self=bless {events=>[q[],[]],nodes=>[$root],ids=>{refaddr($root)=>0},root=>$root},$class;
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
        $active->{events}[0] .= pack('J2',$active->{ids}{refaddr($hash)},$id);
        push @{$active->{events}[1]},$key;
    }
    return $child;
}
sub add
{
    my ($hash,$value,@path)=@_;
    my $key=pop @path;
    $hash=branch($hash,$_) for @path;
    if (!exists $hash->{$key}) {
        # Root is node 0; created child nodes start at 1, so 0 marks a leaf.
        $active->{events}[0] .= pack('J2',$active->{ids}{refaddr($hash)},0);
        push @{$active->{events}[1]},$key;
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
    my ($metadata,$keys)=@{$part->[0]};
    my $offset=0;
    for my $key (@$keys) {
        my ($parent,$child)=unpack('J2',substr($metadata,$offset,EVENT_BYTES));
        $offset += EVENT_BYTES;
        my $hash=$nodes[$parent];
        if ($child) {
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
