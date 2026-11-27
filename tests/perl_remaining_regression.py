#!/usr/bin/env python3
"""Deterministic full-output checks for remaining Perl tool changes.

Requires bgzip, tabix, and samtools. Reference/candidate may be source Perl
folders or installations. This is a small compatibility suite, not a fuzzer.
"""
import argparse, gzip, json, os, re, subprocess
from pathlib import Path
from perl_stats_merge_regression import locations


def main():
    ap=argparse.ArgumentParser()
    for name in ['reference','candidate','output']:ap.add_argument('--'+name,required=True)
    a=ap.parse_args();d=Path(a.output).resolve();d.mkdir(parents=True,exist_ok=False)
    fa=d/'reference.fa';fa.write_text('>22\n'+('ACGT'*500)+'\n>chrExtra\n'+('ACGT'*200)+'\n')
    subprocess.run(['samtools','faidx',str(fa)],check=True)
    header='##fileformat=VCFv4.2\n##contig=<ID=22,length=2000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tz\ta\tm\n'
    rows=[]
    for i in range(12):
        rows.append('\t'.join(['22',str(101+i*4),'.','A',['C','AT','C,G'][i%3],'.','PASS','.', 'GT:DP', '0/1:4','1|0:9','0/1:4'])+'\n')
    vcf=d/'input.vcf';vcf.write_text(header+''.join(rows))
    with (d/'input.vcf.gz').open('wb') as out:subprocess.run(['bgzip','-c',str(vcf)],stdout=out,check=True)
    subprocess.run(['tabix','-p','vcf',str(d/'input.vcf.gz')],check=True)
    bed=d/'mask.bed';bed.write_text('22\t90\t110\n22\t95\t140\n22\t145\t155\n')
    with (d/'mask.bed.gz').open('wb') as out:subprocess.run(['bgzip','-c',str(bed)],stdout=out,check=True)
    subprocess.run(['tabix','-p','bed',str(d/'mask.bed.gz')],check=True)
    cases=[('tab','vcf-to-tab',[],vcf,True),('aa','fill-aa',['-a',str(fa)],vcf,True),
           ('aa-filter','fill-aa',['-a',str(fa),'-t','snp'],vcf,True),
           ('fs','fill-fs',['-r',str(fa),'-l','7'],vcf,True),
           ('fs-cluster','fill-fs',['-r',str(fa),'-l','7','-c','8'],vcf,True),
           ('fs-masks','fill-fs',['-r',str(fa),'-l','7','-v',str(d/'input.vcf.gz'),'-m','lc','-b',str(d/'mask.bed.gz')],vcf,True)]
    for tag,fmt,vals,ref,alt,flags,ok in [
        ('iupac','GT',['0/1','1|0','./.'],'A','G',['-i'],True),
        ('haploid','GT',['0','1','.'],'A','C',[],True),
        ('no-gt','DP',['3','4','3'],'A','C',[],True),
        ('bad-gt','GT',['x','0','0'],'A','C',[],False),
        ('bad-iupac','GT',['0/1','0/0','0/0'],'A','AT',['-i'],False),
        ('range','GT',['9/0','9/0','9/0'],'A','C',[],True)]:
        f=d/(tag+'.vcf');f.write_text(header+'\t'.join(['22','101','.',ref,alt,'.','PASS','.',fmt]+vals)+'\n')
        cases.append((tag,'vcf-to-tab',flags,f,ok))
    # Lossless site suffix parsing includes trailing tabs, absent final newline,
    # VCF 4.0/4.1 case rules, symbolic ALT and missing sample columns.
    for i,(version,tail) in enumerate([(v,t) for v in ['4.0','4.1','4.2'] for t in ['\n','\t\n','','\t','\t\t']]):
        f=d/f'tail-{i}.vcf';f.write_text(header.replace('4.2',version)+'22\t101\t.\ta\tc,<DEL>\t.\tPASS\t.\tGT:DP\t0/1:4\t0/1:4\t0/1:4'+tail)
        cases.append((f'tail-{i}','fill-aa',['-a',str(fa)],f,True))
    sort=d/'sort.vcf';sort.write_text(header+''.join(reversed(rows))+rows[0])
    cases += [('sort','vcf-sort',[],sort,True),('sort-natural','vcf-sort',['-c'],sort,True)]
    # Header and dictionary outputs are captured separately from compressed bytes.
    cases.append(('md5','fill-ref-md5',['-r',str(fa),'-d',str(d/'dictionary'),str(d/'input.vcf.gz'),str(d/'md5.vcf.gz')],None,True))
    # Rich FORMAT conversion must retain missing-field/FT semantics, and phased
    # joins must retain score accumulation, phase sets, allele and sample order.
    snp=d/'convert.vcf';snp.write_text(header+''.join(row for row in rows if '\tAT\t' not in row))
    cases += [('convert-4.0','vcf-convert',['-v','4.0'],snp,True),('convert-4.2','vcf-convert',['-v','4.2'],snp,True)]
    phase_header=header.replace('#CHROM', '##FORMAT=<ID=PS,Number=1,Type=Integer,Description="Phase set">\n##FORMAT=<ID=PQ,Number=1,Type=Float,Description="Phase quality">\n#CHROM')
    blocks=[]
    for side,indices in [('left',range(8)),('right',range(4,12))]:
        lines=[]
        for i in indices:
            gt=['0|1','1|0','0|0'] if side=='left' else ['1|0','1|0','0|0']
            if i==6:gt[1]='./.'
            if i==7:gt[2]='1'
            lines.append('\t'.join(['22',str(101+i*4),'.','A','C','.','PASS','.', 'GT:PS:PQ']+[g+':101:0.9' for g in gt])+'\n')
        f=d/('phase-'+side+'.vcf');f.write_text(phase_header+''.join(lines))
        with Path(str(f)+'.gz').open('wb') as out:subprocess.run(['bgzip','-c',str(f)],stdout=out,check=True)
        subprocess.run(['tabix','-p','vcf',str(f)+'.gz'],check=True);blocks.append(str(f)+'.gz')
    cases += [('phase-overlap','vcf-phased-join',['-o','-']+blocks,None,True),('phase-threshold','vcf-phased-join',['-q','0.95','-j','1','-o','-']+blocks,None,True)]
    sexes=d/'sexes';sexes.write_text('z M\na F\nm M\n')
    policy=d/'ploidy.pl';policy.write_text('{22=>[{from=>100,to=>125,M=>1,F=>0},{from=>126,to=>160,M=>2,F=>1}]}\n')
    cases += [('ploidy-pass','vcf-fix-ploidy',['-s',str(sexes)],vcf,True),('ploidy-active','vcf-fix-ploidy',['-s',str(sexes),'-p',str(policy)],vcf,True)]
    large_fa=d/'cache-reference.fa';large_fa.write_text('>22\n'+('ACGT'*524288)+'\n')
    subprocess.run(['samtools','faidx',str(large_fa)],check=True)
    cases.append(('fs-cache','fill-fs',['-r',str(large_fa),'-l','7'],vcf,True))
    results=[]
    for seed in [0,1,19]:
        for name,tool,args,stdin,ok in cases:
            runs=[]
            for label,source in [('reference',a.reference),('candidate',a.candidate)]:
                bindir,libdir=locations(source)
                for p in [d/'dictionary',d/'md5.vcf.gz',d/'md5.vcf.gz.header']:p.unlink(missing_ok=True)
                env=dict(os.environ,PERL5LIB=str(libdir),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C')
                with stdin.open('rb') if stdin else open(os.devnull,'rb') as inp:
                    extra_args=['--reference-cache-size','1048576'] if name=='fs-cache' and label=='candidate' else []
                    p=subprocess.run(['perl',str(bindir/tool)]+args+extra_args,stdin=inp,capture_output=True,env=env,timeout=60)
                err=p.stderr.replace(str(libdir).encode(),b'<source>').replace(str(bindir).encode(),b'<source>')
                err=re.sub(rb' line \d+',b' line <source>',err)
                err=re.sub(rb'(HASH|ARRAY|CODE)\(0x[0-9a-fA-F]+\)',rb'\1(<address>)',err)
                extra=[]
                if tool=='fill-ref-md5' and p.returncode==0:
                    extra=[gzip.decompress((d/'md5.vcf.gz').read_bytes()),(d/'md5.vcf.gz.header').read_bytes(),(d/'dictionary').read_bytes()]
                runs.append((p.returncode,p.stdout,err,extra))
            passed=runs[0]==runs[1] and (not ok or runs[0][0]==0)
            results.append(dict(case=name,seed=seed,passed=passed,exit_codes=[r[0] for r in runs]))
            (d/'results.json').write_text(json.dumps(results,indent=2))
            if not passed:
                for label,r in zip(['reference','candidate'],runs):
                    (d/(name+'-'+label+'.stdout')).write_bytes(r[1]);(d/(name+'-'+label+'.stderr')).write_bytes(r[2])
                raise RuntimeError(f'{name} seed {seed} differs')
    print(json.dumps(dict(passed=True,cases=len(results))))

if __name__=='__main__':main()
