#!/usr/bin/env python3
"""Small deterministic checks for ordered workers and their CLI consumers."""
import argparse, json, os, subprocess, tempfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--before',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    source=Path(a.source).resolve();before=Path(a.before).resolve();out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    header='##fileformat=VCFv4.2\n##FORMAT=<ID=GT,Number=1,Type=String,Description="GT">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="DP">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tz\ta\n'
    rows=['22\t%d\t.\tA\tC,G\t.\tPASS\tDP=7\t%s\t%s\t%s\n' % (i+1,*([('GT','0/1','1|2'),('GT:DP','./.:3','0/2:7'),('DP:GT','4:1/1','5:0/0')][i%3])) for i in range(60)]
    data=out/'input.vcf';data.write_text(header+''.join(rows))
    template=out/'template.vcf';template.write_text(header.replace('\tz\ta\n','\ta\tz\n'))
    results=[]
    cases=[('query-default','vcf-query',[]),('query-template','vcf-query',['--reuse-sample-templates']),('query-raw','vcf-query',['-f','%CHROM:%POS[\t%SAMPLE=%GTR]\n']),('query-rich','vcf-query',['-f','%CHROM:%POS[\t%SAMPLE:%*=,]\n']),('shuffle','vcf-shuffle-cols',['-t',str(template)]),('tstv','vcf-tstv',[]),('to-tab','vcf-to-tab',[]),('an-ac','fill-an-ac',[]),('convert','vcf-convert',['-v','4.2']),('subset','vcf-subset',['-c','a'])]
    def run(src,tool,args,payload,seed,extra=()):
        env=dict(os.environ,PERL5LIB=str(src),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C',TMPDIR=str(out/'tmp'))
        return subprocess.run(['perl',str(src/tool),*args,*extra],input=payload,capture_output=True,env=env,timeout=30)
    (out/'tmp').mkdir(exist_ok=True)
    for seed in [0,1,19]:
        for name,tool,args in cases:
            for mode,payload in [('normal',data.read_bytes()),('lowercase',data.read_bytes().replace(b'\tA\tC,G\t',b'\ta\tc,g\t')),('empty',header.encode()),('unterminated',data.read_bytes().rstrip(b'\n')),('trailing-tabs',data.read_bytes().replace(b'\n22',b'\t\n22'))]:
                ref=run(before,tool,args,payload,seed)
                assert ref.returncode==0,(name,ref.stderr)
                for workers in [1,2,4]:
                    cur=run(source,tool,args,payload,seed,['--workers',str(workers),'--worker-batch-bytes','127'])
                    def norm(b):
                        import re
                        for src in [source,before]:b=b.replace(str(src).encode(),b'<source>')
                        return re.sub(rb' line \d+',b' line <source>',b)
                    passed=(cur.returncode,cur.stdout,norm(cur.stderr))==(ref.returncode,ref.stdout,norm(ref.stderr))
                    results.append(dict(case=name,mode=mode,seed=seed,workers=workers,passed=passed))
                    if not passed:
                        for label,r in [('before',ref),('after',cur)]:
                            (out/(name+'-'+label+'.stdout')).write_bytes(r.stdout);(out/(name+'-'+label+'.stderr')).write_bytes(r.stderr)
                        raise AssertionError(results[-1])
                    assert not list((out/'tmp').iterdir()),'worker temporary files remain'
    for newline in [b'\r\n',b'\r']:
        payload=data.read_bytes().replace(b'\n',newline)
        ref=run(before,'vcf-fix-newlines',[],payload,0)
        assert ref.returncode==0
        for workers in [1,2,4]:
            cur=run(source,'vcf-fix-newlines',[],payload,0,['--workers',str(workers),'--worker-batch-bytes','127'])
            assert (cur.returncode,cur.stdout,cur.stderr)==(ref.returncode,ref.stdout,ref.stderr)
            results.append(dict(case='newlines',newline=repr(newline),workers=workers,passed=True))
    # Errors after an earlier successful batch must retain partial stdout and
    # the application's exit status, not errno from the worker framework.
    for badline in [b'22\t99\t.\tA\tC\t.\tPASS\t.\tGT\tx\tx\n', b'broken\n']:
        payload=header.encode()+rows[0].encode()+badline
        ref=run(before,'vcf-to-tab',[],payload,0)
        assert ref.returncode!=0
        for workers in [1,2,4]:
            cur=run(source,'vcf-to-tab',[],payload,0,['--workers',str(workers),'--worker-batch-bytes','1'])
            assert (cur.returncode,cur.stdout)==(ref.returncode,ref.stdout),(cur.returncode,ref.returncode)
            assert cur.stderr.split(b'\n')[0]==ref.stderr.split(b'\n')[0]
            results.append(dict(case='partial-output-error',workers=workers,passed=True))
    # Out-of-order completion, bounded output copying, map/reduce and failure.
    harness=out/'pool.pl';harness.write_text('''use strict; use warnings; use NuOrderedWorkers;
my $n=0;my $sum=0;
NuOrderedWorkers::run(workers=>3,next=>sub {return $n<6 ? [$n++] : undef},work=>sub {
 my($b)=@_;my $i=$b->[0];select undef,undef,undef,0.01*(5-$i);
 print "$i\\n";print STDERR "err$i\\n";
 die "expected failure\\n" if $ENV{FAIL} && $i==2;
 return $i;
},reduce=>sub {$sum+=$_[0]});
print "sum=$sum\\n";
''')
    env=dict(os.environ,PERL5LIB=str(source),TMPDIR=str(out/'tmp'))
    for fail in [False,True]:
        r=subprocess.run(['perl',str(harness)],env=dict(env,FAIL=str(int(fail))),capture_output=True,timeout=10)
        expected=b'0\n1\n2\n' if fail else b'0\n1\n2\n3\n4\n5\nsum=15\n'
        assert r.stdout==expected,(r.stdout,r.stderr)
        assert (r.returncode!=0)==fail
        assert r.stderr==(b'err0\nerr1\nerr2\nexpected failure\n' if fail else b'err0\nerr1\nerr2\nerr3\nerr4\nerr5\n'),r.stderr
        assert not list((out/'tmp').iterdir())
        results.append(dict(case='pool-failure' if fail else 'pool-order-reduction',passed=True))
    for bad in ['0','-1','1.5','x','99999999999999999999']:
        r=run(source,'vcf-query',[],data.read_bytes(),0,['--workers',bad]);assert r.returncode!=0 and not r.stdout
        results.append(dict(case='invalid-workers-'+bad,passed=True))
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(results))))
if __name__=='__main__':main()
