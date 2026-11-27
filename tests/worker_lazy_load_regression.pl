use strict;
use warnings;
use NuOrderedWorkers;

my @dependencies=qw(File/Temp.pm Storable.pm POSIX.pm IO/Handle.pm Errno.pm);
my %initial=map { $_ => exists $INC{$_} } @dependencies;
my @trace;
my $index=0;
NuOrderedWorkers::run(workers=>1,next=>sub { $index<3 ? $index++ : undef },
    work=>sub { push @trace,"work:$_[0]"; return $_[0]*2 },
    reduce=>sub { push @trace,"reduce:$_[0]" });
die "serial callback order changed" unless join(',',@trace) eq 'work:0,reduce:0,work:1,reduce:2,work:2,reduce:4';
for my $module (@dependencies) { die "serial load: $module" if !$initial{$module} && exists $INC{$module}; }
my $sum=0;$index=0;
NuOrderedWorkers::run(workers=>2,next=>sub { $index<3 ? $index++ : undef },
    work=>sub { return $_[0]*2 },reduce=>sub { $sum += $_[0] });
die "parallel reduction changed" unless $sum==6;
for my $module (@dependencies) { die "missing parallel dependency: $module" unless exists $INC{$module}; }
print "serial dependencies deferred; serial and parallel callbacks passed\n";
