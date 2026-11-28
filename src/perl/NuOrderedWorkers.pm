package NuOrderedWorkers;

use strict;
use warnings;

our $serial_reader = 0;

# Bounded, ordered fork/map/reduce. The caller defines independent batches;
# this module does not partition VCF regions or infer biological independence.
# One batch is owned by each child. Only the parent reads the input stream.
sub positive_integer
{
    my ($value, $name) = @_;
    die "$name requires a positive integer\n"
        unless defined($value) && $value =~ /\A[1-9][0-9]*\z/ && $value <= 2147483647;
    return 0 + $value;
}

# Resource options are excluded from legacy scientific-output provenance.
# The argument cursor comes from the real CLI parser, so an option's value that
# happens to spell --workers is never mistaken for a resource option.
sub take_option
{
    my ($opts,$arg,$argv)=@_;
    return 0 unless $arg eq '--workers' || $arg eq '--worker-batch-bytes';
    my $index = exists($$opts{args}) ? @{$$opts{args}}-@$argv-1 : undef;
    my $value=positive_integer(shift(@$argv),$arg);
    $$opts{$arg eq '--workers' ? 'workers' : 'worker_batch_bytes'}=$value;
    splice(@{$$opts{args}},$index,2) if defined $index;
    return 1;
}

sub run
{
    my (%args) = @_;
    my $workers = positive_integer($args{workers}, '--workers');
    local $serial_reader = $workers == 1;
    my $next = $args{next};
    my $work = $args{work};
    my $reduce = $args{reduce};
    if ($workers == 1)
    {
        while (defined(my $batch = $next->()))
        {
            $! = 0; $? = 0;
            my $result = $work->($batch);
            $reduce->($result) if $reduce;
        }
        return;
    }

    # Serial callers need neither child IPC nor temporary output storage.
    require File::Temp;
    require IO::Handle;
    require POSIX;
    require Storable;
    require Errno;

    my $directory = File::Temp::tempdir('nuvcf-workers-XXXXXXXX', TMPDIR=>1, CLEANUP=>1);
    my @queue;
    my $sequence = 0;
    my $ended = 0;
    my $cleanup = sub {
        # Reaping cancelled children must not replace the primary error status.
        local ($!, $?);
#line 64
        kill 'TERM', map { $_->{pid} } @queue if @queue;
        for my $entry (@queue) { _wait($entry->{pid}); }
        @queue = ();
    };
    # A child can receive cancellation immediately after inheriting these handlers.
    # That child must exit, not unwind the parent's copied queue and attempt
    # to wait for sibling processes that it does not own.
    my $parent_pid = $$;
    local $SIG{INT} = sub { POSIX::_exit(130) if $$ != $parent_pid; die "Interrupted (SIGINT)\n"; };
    local $SIG{TERM} = sub { POSIX::_exit(143) if $$ != $parent_pid; die "Interrupted (SIGTERM)\n"; };
    # Keep the original diagnostic locations in callbacks and cleanup.
#line 70
    local $SIG{PIPE} = 'IGNORE';
    my $ok = eval {
        while (!$ended || @queue)
        {
            while (!$ended && @queue < $workers)
            {
                my $batch = $next->();
                if (!defined $batch) { $ended=1; last; }
                my $prefix = "$directory/".$sequence++;
                STDOUT->flush() or die "Flush stdout: $!\n";
                STDERR->flush() or die "Flush stderr: $!\n";
                my $pid = fork();
                die "Cannot start worker: $!\n" unless defined $pid;
                if (!$pid)
                {
                    # The inherited handlers exit directly in children.
                    my $child_ok = eval {
                        open(STDOUT, '>', "$prefix.out") or die "Worker stdout: $!\n";
                        open(STDERR, '>', "$prefix.err") or die "Worker stderr: $!\n";
                        # Framework descriptor operations must not change the
                        # application error status (Perl die consults errno).
                        $! = 0; $? = 0;
                        my $result = $work->($batch);
                        Storable::nstore([$result], "$prefix.result") if $reduce;
                        1;
                    };
                    my $failure_status = $! || ($? >> 8) || 255;
                    if (!$child_ok) { print STDERR $@; }
                    my $flushed = STDOUT->flush();
                    $flushed = STDERR->flush() && $flushed;
                    POSIX::_exit($child_ok ? ($flushed ? 0 : 255) : $failure_status);
                }
                push @queue, {pid=>$pid, prefix=>$prefix};
            }
            next unless @queue;
            my $entry = $queue[0];
            my $status = _wait($entry->{pid});
            shift @queue;
            _copy("$entry->{prefix}.out", \*STDOUT);
            _copy("$entry->{prefix}.err", \*STDERR);
            if ($status)
            {
                $cleanup->();
                STDOUT->flush(); STDERR->flush();
                # Preserve a signal as an unsuccessful command, not a success
                # with a partial file. Ordinary worker failures retain status.
                exit(($status & 127) ? 128+($status & 127) : $status >> 8);
            }
            $reduce->(Storable::retrieve("$entry->{prefix}.result")->[0]) if $reduce;
            for my $suffix (qw(out err result))
            {
                my $path = "$entry->{prefix}.$suffix";
                unlink($path) or die "Remove worker output $path: $!\n" if -e $path;
            }
        }
        1;
    };
    my $error = $@;
    if (!$ok) { $cleanup->(); die $error; }
}

sub _wait
{
    my ($pid) = @_;
    while (1)
    {
        my $result = waitpid($pid, 0);
        next if $result == -1 && $! == Errno::EINTR();
        die "Wait for worker $pid: $!\n" if $result == -1;
        return $?;
    }
}

sub _copy
{
    my ($path, $output) = @_;
    open(my $input, '<', $path) or die "Open worker output $path: $!\n";
    while (1)
    {
        my $n = read($input, my $buffer, 65536);
        die "Read worker output $path: $!\n" unless defined $n;
        last unless $n;
        print {$output} $buffer or die "Write command output: $!\n";
    }
    close($input) or die "Close worker output $path: $!\n";
}

# Scheduling is measured in bytes rather than sample/variant-specific limits.
# An individual record is never split and may exceed the batch target.
sub line_batches
{
    my ($reader, $bytes) = @_;
    return prepared_line_batches($reader,sub { $_[0] },$bytes);
}

# Prepare stream state in the parent and attach its diagnostics to the exact
# record. Errors travel behind earlier records, including earlier batches.
sub prepared_line_batches
{
    my ($reader,$prepare,$bytes,$weight) = @_;
    $bytes=positive_integer($bytes,'--worker-batch-bytes');
    my $index=0;
    my $ended=0;
    return sub {
        return undef if $ended;
        my @items;
        my $size=0;
        while ($size < ($serial_reader ? 1 : $bytes) && !$ended) {
            my ($line,$value,$warning,$error,$error_status);
            $warning='';
            {
                local *STDERR;
                open(STDERR,'>',\$warning) or die "Capture reader diagnostics: $!\n";
                local $! = 0;
                local $? = 0;
                my $ok=eval {
                    $line=$reader->();
                    $value=$prepare->($line) if defined $line;
                    1;
                };
                if (!$ok) { $error=$@; $error_status=$! || ($? >> 8) || 255; }
            }
            $ended=1 if !defined($line) || defined($error);
            if (defined($line) || length($warning) || defined($error)) {
                # Successful records carry only sequence and payload. Diagnostic
                # slots are allocated only when the stream actually emits them.
                my $item=[$index++,$value];
                if (length($warning) || defined($error)) {
                    @$item[2,3,4]=($warning,$error,$error_status);
                }
                push @items,$item;
                $size += defined($line) ? ($weight ? $weight->($line) : length($line)) : 0;
            }
        }
        return @items ? \@items : undef;
    };
}

sub prepared_value
{
    my ($item)=@_;
    print STDERR $$item[2] if defined($$item[2]) && length($$item[2]);
    if (defined $$item[3]) { $!=$$item[4]; die $$item[3]; }
    return $$item[1];
}

# A worker consumes each queued item exactly once. Release the queue's payload
# reference before processing so completed records (including parsing caches)
# do not stay alive until the whole batch exits. The accessor above remains
# non-destructive for callers that need to inspect a payload repeatedly.
sub take_prepared_value
{
    my ($item)=@_;
    my $value=prepared_value($item);
    undef $$item[1];
    return $value;
}

1;
