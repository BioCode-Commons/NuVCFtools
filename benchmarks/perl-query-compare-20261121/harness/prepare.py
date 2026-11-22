import gzip, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'data'; M=R/'metadata'
for p in (D,M,R/'tools'):p.mkdir(exist_ok=True)
def save(p,d):
    q=p.with_suffix('.tmp');q.write_text(json.dumps(d,indent=2)+'\n');q.replace(p)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def run(args,tag,**kw):
    with (M/(tag+'.log')).open('wb') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,**kw)
start=time.monotonic(); state={'state':'running','job':os.environ['SLURM_JOB_ID']};save(M/'prepare.json',state)
try:
    url='https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr22.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz'
    source=D/'chr22.vcf.gz'
    run(['curl','-fL','--retry','2','--max-time','900','-o',str(source),url],'input-download')
    digest=sha(source)
    if digest!='a90c16c4ff2b3196476d506ae13cb3047fae8670163c7c932c4b0239aef3daf5':raise RuntimeError('Input identity changed')
    count=0;all_count=0
    with gzip.open(source,'rt') as src,(D/'region.vcf').open('w') as dst:
        for line in src:
            if line.startswith('#'):
                dst.write(line)
                if line.startswith('#CHROM'):samples=line.rstrip().split('\t')[9:]
            else:
                all_count+=1;a=line.split('\t',2)
                if a[0]=='22' and 20000001<=int(a[1])<=21000000:dst.write(line);count+=1
    if all_count!=1103547 or count!=22382 or len(samples)!=2504:raise RuntimeError('Unexpected input counts')
    source.unlink()
    for n in (100,400):
        sels={'cohort':samples[:n],'A':samples[:n//2],'B':samples[n//2:n]}
        for label,names in sels.items():
            select=D/(label+str(n)+'.samples');select.write_text('\n'.join(names)+'\n')
            dst=D/(label+str(n)+'.vcf')
            run(['bcftools','view','--no-version','-S',str(select),'-Ov','-o',str(dst),str(D/'region.vcf')],dst.stem)
            with open(str(dst)+'.gz','wb') as f:subprocess.run(['bgzip','-c',str(dst)],stdout=f,check=True)
            run(['tabix','-p','vcf',str(dst)+'.gz'],dst.stem+'-index')
        with (D/('cohort'+str(n)+'.vcf')).open() as src,(D/('compare'+str(n)+'.vcf')).open('w') as dst:
            row=0
            for line in src:
                if line.startswith('#'):dst.write(line)
                else:
                    if row%2==0:dst.write(line)
                    row+=1
        with open(D/('compare'+str(n)+'.vcf.gz'),'wb') as f:subprocess.run(['bgzip','-c',str(D/('compare'+str(n)+'.vcf'))],stdout=f,check=True)
        run(['tabix','-p','vcf',str(D/('compare'+str(n)+'.vcf.gz'))],'compare'+str(n)+'-index')
    (D/'region.vcf').unlink()
    save(M/'inputs.json',{'url':url,'source_sha256':digest,'region':'GRCh37 chr22:20000001-21000000','records':count,'source_samples':2504,
         'selection':'First 100 or 400 VCF-header samples; merge uses disjoint halves; compare second file keeps alternating real records. No genotype or allele fabrication.',
         'files':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in D.iterdir() if p.is_file()}})
    state.update(state='complete',elapsed_seconds=time.monotonic()-start);save(M/'prepare.json',state)
except BaseException as e:
    state.update(state='failed',error=str(e));save(M/'prepare.json',state);raise
