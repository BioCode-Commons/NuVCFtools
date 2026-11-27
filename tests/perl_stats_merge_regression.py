#!/usr/bin/env python3
"""Differential CLI/API regression. Requires Perl, bgzip, tabix and a reference install.

python3 tests/perl_stats_merge_regression.py --reference /path/to/install \
    --candidate /path/to/repo/src/perl --output /path/to/evidence

The reference may be an installed prefix (bin/, lib/perl5/) or src/perl/.
All CLI stdout/stderr bytes are compared, including unsorted stats dumps.
"""
import argparse, hashlib, json, os, random, subprocess
from pathlib import Path


def locations(root):
    root=Path(root).resolve()
    return (root/'bin',root/'lib/perl5') if (root/'bin').is_dir() else (root,root)


def fixture(directory):
    rng=random.Random(73519)
    header='''##fileformat=VCFv4.1
##contig=<ID=22,length=51304566>
##FILTER=<ID=q10,Description="Low quality">
##INFO=<ID=DP,Number=1,Type=Integer,Description="Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele frequencies">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allele depths">
##FORMAT=<ID=FA,Number=A,Type=Integer,Description="Alternate allele values">
##FORMAT=<ID=PL,Number=G,Type=Integer,Description="Genotype likelihoods">
'''
    for label in ('all','A','B','sitesA','sitesB'):
        names=[] if label.startswith('sites') else ['S'+str(i) for i in (range(32) if label=='all' else range(16) if label=='A' else range(16,32))]
        lines=[header, '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO'+ ('\tFORMAT\t'+'\t'.join(names) if names else '')+'\n']
        for site in range(160):
            # Different lengths and ALT orders at matching positions exercise REF
            # padding and allele-number remapping rather than only GT-only SNPs.
            if label in ('B','sitesB') and site%5==0:continue
            ref,alts=[('A',['G','C']),('AT',['A','ATT']),('AC',['GT','A']),('G',['C','T','GA'])][site%4]
            if label in ('B','sitesB'):
                alts=alts[::-1]
                if site%7==0:ref+='A';alts=[a+'A' for a in alts]
            k=len(alts)
            fmt='GT:DP:AD:FA:PL' if site%11 else 'DP'
            fields=['22',str(20000001+site*10),'.',ref,','.join(alts),str(10+site%80),'q10' if site%9==0 else 'PASS','DP=32;AF='+','.join(['0.1']*k)]
            if names:
                fields.append(fmt)
                for name in names:
                    if fmt=='DP':fields.append(str(rng.randrange(50)));continue
                    alleles=[str(i) for i in range(k+1)]+['.']
                    a,b=rng.choice(alleles),rng.choice(alleles)
                    gt=a if site%13==0 else a+rng.choice(['/','|'])+b
                    vals=[gt,str(rng.randrange(100)),','.join(str(rng.randrange(30)) for _ in range(k+1)),','.join(str(rng.randrange(20)) for _ in range(k)),','.join(str(rng.randrange(80)) for _ in range((k+1)*(k+2)//2))]
                    fields.append(':'.join(vals))
            lines.append('\t'.join(fields)+'\n')
        p=directory/(label+'.vcf');p.write_text(''.join(lines))
        with Path(str(p)+'.gz').open('wb') as f:subprocess.run(['bgzip','-c',str(p)],stdout=f,check=True)
        subprocess.run(['tabix','-p','vcf',str(p)+'.gz'],check=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--reference',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=1);a=p.parse_args()
    root=Path(a.output).resolve();root.mkdir(parents=True,exist_ok=False);data=root/'data';data.mkdir();fixture(data)
    cases=[('stats', 'vcf-stats',[str(data/'all.vcf.gz')]),
           ('stats-filters','vcf-stats',['-f','FILTER,QUAL=10:200,FORMAT/DP=10:200,SAMPLE/S0/DP=1:200',str(data/'all.vcf.gz')]),
           ('stats-subset','vcf-stats',['-s','S0,S3,S9',str(data/'all.vcf.gz')]),
           ('stats-sites','vcf-stats',['-s','-',str(data/'all.vcf.gz')])]
    for name,args in [('merge',[]),('merge-trim',['-t']),('merge-missing',['-R','0/0']),('merge-separate',['-c','none'])]:
        cases.append((name,'vcf-merge',args+[str(data/'A.vcf.gz'),str(data/'B.vcf.gz')]))
    cases.append(('merge-sites','vcf-merge',[str(data/'sitesA.vcf.gz'),str(data/'sitesB.vcf.gz')]))
    probe=Path(__file__).with_name('perl_stats_merge_probe.pl')
    results=[]
    for seed in (0,1,19):
        for name,tool,args in cases+[('api',None,[])]:
            outputs=[]
            for label,base in [('reference',a.reference),('candidate',a.candidate)]:
                bindir,lib=locations(base)
                env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C',TZ='UTC')
                command=['perl',str(bindir/tool)]+args if tool else ['perl',str(probe)]
                if label=='candidate' and tool in {'vcf-merge','vcf-stats'}:command+=['--workers',str(a.workers),'--worker-batch-bytes','1024']
                run=subprocess.run(command,env=env,capture_output=True,timeout=60)
                out=root/(name+'-'+str(seed)+'-'+label);out.mkdir()
                (out/'stdout').write_bytes(run.stdout);(out/'stderr').write_bytes(run.stderr)
                outputs.append((run.returncode,run.stdout,run.stderr))
            result={'case':name,'hash_seed':seed,'passed':outputs[0]==outputs[1] and outputs[0][0]==0,
                    'exit_codes':[x[0] for x in outputs], 'stdout_sha256':[hashlib.sha256(x[1]).hexdigest() for x in outputs]}
            results.append(result);(root/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
            if not result['passed']:raise RuntimeError('Mismatch: '+name+' seed '+str(seed)+'; see '+str(root))
    print(json.dumps({'passed':len(results),'cases':len(cases)+1,'hash_seeds':3}))

if __name__=='__main__':main()
