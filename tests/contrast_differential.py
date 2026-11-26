#!/usr/bin/env python3
"""Small CLI differential campaign and end-to-end scaling benchmark (macOS)."""
import argparse, json, os, random, re, subprocess, time
from pathlib import Path

HEADER='''##fileformat=VCFv4.1
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=PL,Number=G,Type=Integer,Description="Likelihood">
'''
def fixture(path, n, rows, seed=None):
    rng=random.Random(seed)
    gts=['0/0','0/1','1/0','1|0','1/1','2/2','0','1','.','./.','0/.','.|1','0/1/2','2/1/0']
    with path.open('w') as f:
        f.write(HEADER+'#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t'+'\t'.join('S'+str(i) for i in range(2*n))+'\n')
        for i in range(rows):
            fmt=rng.choice(['DP:GT','GT:DP','GT:DP:PL']) if seed is not None else 'GT'
            samples=[]
            for j in range(2*n):
                gt=rng.choice(gts) if seed is not None else ('0/0' if j<n else '2/2')
                vals={'GT':gt,'DP':str(rng.randrange(40)),'PL':rng.choice(['0,10,20,30,40,50','50,40,30,20,10,0','.'])}
                samples.append(':'.join(vals[k] for k in fmt.split(':')))
            f.write('1\t'+str(i+1)+'\t.\tA\tC,G\t50\t'+('q10' if i%7==0 else 'PASS')+'\t.\t'+fmt+'\t'+'\t'.join(samples)+'\n')

def clean(data):
    return b'\n'.join(x for x in data.splitlines() if not x.startswith(b'##source='))

def run(root, data, n, flags, seed):
    env=dict(os.environ,PERL5LIB=str(root/'src/perl'),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C')
    args=['+'+','.join('S'+str(i) for i in range(n,2*n)), '-'+','.join('S'+str(i) for i in range(n))]+flags+[str(data)]
    t=time.perf_counter()
    p=subprocess.run(['/usr/bin/time','-l','perl',str(root/'src/perl/vcf-contrast')]+args,env=env,capture_output=True,timeout=90)
    wall=time.perf_counter()-t
    # macOS time reports the maximum resident set size in bytes.
    m=re.search(rb'^\s*(\d+)\s+maximum resident set size',p.stderr,re.M)
    telemetry=re.search(rb'^\s*[0-9.]+ real\s+[0-9.]+ user\s+[0-9.]+ sys',p.stderr,re.M)
    err=p.stderr[:telemetry.start()] if telemetry else p.stderr
    err=re.sub(rb'at [^\n]*?/src/perl/vcf-contrast line [0-9]+',b'at vcf-contrast line <location>',err)
    return p.returncode,clean(p.stdout),err,wall,int(m.group(1)) if m else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--before',type=Path,required=True);ap.add_argument('--after',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True); results=[]
    for random_seed in range(5):
        data=a.output/('random-'+str(random_seed)+'.vcf');fixture(data,12,400,random_seed)
        for flags in ([],['-n'],['-f'],['-d','10']):
            for hash_seed in (0,19):
                x=run(a.before,data,12,flags,hash_seed);y=run(a.after,data,12,flags,hash_seed)
                # time stderr is machine telemetry; biological output and exit must agree.
                if x[:3]!=y[:3]:
                    (a.output/'before.out').write_bytes(x[1]);(a.output/'after.out').write_bytes(y[1]);raise RuntimeError((random_seed,flags,hash_seed,x[0],y[0]))
                if x[0] or y[0]:raise RuntimeError('Both programs failed')
                results.append({'seed':random_seed,'flags':flags,'hash_seed':hash_seed,'passed':True})
        data.unlink()
    benches=[]
    for n in (16,64,128):
        data=a.output/('scaling-'+str(n)+'.vcf');fixture(data,n,300)
        for rep in range(3):
            runs=[run(root,data,n,[],0) for root in (a.before,a.after)]
            if runs[0][:3]!=runs[1][:3] or runs[0][0]:raise RuntimeError('Scaling mismatch')
            benches.append({'foreground':n,'background':n,'records':300,'repetition':rep,'before_wall':runs[0][3],'after_wall':runs[1][3],'before_rss_bytes':runs[0][4],'after_rss_bytes':runs[1][4],'passed':True})
        data.unlink()
    (a.output/'results.json').write_text(json.dumps({'fuzz':results,'benchmark':benches},indent=2)+'\n')
    print(json.dumps({'passed_cli_cases':len(results),'benchmark_runs':len(benches)*2}))
if __name__=='__main__':main()
