import gzip,hashlib,json,os,platform,random,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent; D=ROOT/'data';D.mkdir(exist_ok=True)
RESULT=[]
def save(): (ROOT/'status.json').write_text(json.dumps({'node':platform.node(),'job':os.environ.get('SLURM_JOB_ID'),'results':RESULT},indent=2)+'\n')
def shell(args,**kwargs): return subprocess.run(args,check=True,**kwargs)
def compress(p,kind='vcf'):
 with open(str(p)+'.gz','wb') as f:shell(['bgzip','-c',str(p)],stdout=f)
 shell(['tabix','-f']+(['-p','vcf'] if kind=='vcf' else ['-s','1','-b','2','-e','3'])+[str(p)+'.gz'])
 return str(p)+'.gz'
def vcf(p,rows,names=None):
 n=len(rows[0].rstrip('\n').split('\t'))-9 if rows and len(rows[0].split('\t'))>8 else -1
 columns='#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO'
 if n>=0:columns+='\tFORMAT\t'+'\t'.join(names if names is not None else ['S'+str(i) for i in range(n)])
 p.write_text('##fileformat=VCFv4.1\n##contig=<ID=22,length=51304566>\n##contig=<ID=23,length=50000000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n'+columns+'\n'+''.join(rows));return compress(p)

def normalize(b):
 return b'\n'.join(x for x in b.splitlines() if not x.startswith(b'##source='))
def run(label,tool,args,seed,tag):
 lib=ROOT/label/'src/perl';env=dict(os.environ,PERL5LIB=str(lib),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C')
 prefix=ROOT/(tag+'-'+label);out=prefix.with_suffix('.out');err=prefix.with_suffix('.err');tim=prefix.with_suffix('.time')
 start=time.monotonic()
 with out.open('wb') as f,err.open('wb') as e:
  r=subprocess.run(['/usr/bin/time','-f','%e %M','-o',str(tim),'perl',str(lib/tool)]+args,stdout=f,stderr=e,env=env,timeout=180)
 elapsed=time.monotonic()-start;timing=tim.read_text().splitlines()[-1].split();wall=float(timing[0]);mem=int(timing[1]);raw=out.read_bytes();diag=err.read_bytes()
 diag=re.sub(rb'at [^\n]*?/(?:vcf-isec|vcf-annotate) line [0-9]+',b'at <tool location>',diag)
 return {'returncode':r.returncode,'wall_seconds':wall,'harness_elapsed_seconds':elapsed,'peak_rss_kib':mem,'bytes':len(raw)},normalize(raw),diag

def pair(tool,args,tag,seed=0,allow_error=False):
 order=('before','candidate') if len(RESULT)%2==0 else ('candidate','before');results={}
 for label in order:results[label]=run(label,tool,args,seed,tag)
 x,y=results['before'],results['candidate'];passed=x[0]['returncode']==y[0]['returncode'] and x[1:]==y[1:] and (allow_error or x[0]['returncode']==0)
 RESULT.append({'case':tag,'tool':tool,'args':args,'hash_seed':seed,'before':x[0],'candidate':y[0],'passed':passed});save()
 if not passed:raise RuntimeError('Mismatch '+tag)
 # Compare full output bytes above; retain only metadata after success.
 for label in order:
  for ext in ('.out','.err','.time'):(ROOT/(tag+'-'+label)).with_suffix(ext).unlink()

def main():
 for seed in range(12):
  rng=random.Random(seed);files=[]
  for f in range(rng.randrange(2,10)):
   rows=[]
   for p in sorted(rng.choices(range(1,350),k=120)):
    rows.append(f'22\t{p}\t.\tA\tG\t50\t'+('q10' if rng.randrange(4)==0 else 'PASS')+'\t.\tGT:DP\t'+'\t'.join(rng.choice(['0/0','0|1','1','./.'])+':'+str(rng.randrange(40)) for _ in range(12))+'\n')
   rows += [r.replace('22\t','23\t',1) for r in rows[::3]]
   files.append(vcf(D/f'f{f}.vcf',rows))
  for args in ([],['-n','+1'],['-c'],['-w','5','-n','+1'],['-o'],['-a']):
   pair('vcf-isec',args+files,f'fuzz-isec-{seed}-{len(RESULT)}',seed)
  ann=D/'ann.tsv'
  # Tabix needs noninverted intervals; randomize length, ties and overlaps.
  ann.write_text(''.join(f'22\t{a}\t{a+rng.randrange(0,150)}\t{i}\n' for i,a in enumerate(sorted(rng.choices(range(1,330),k=250)))))
  annot=compress(ann,'bed')
  args=['-a',annot,'-c','CHROM,FROM,TO,INFO/T','-d','key=INFO,ID=T,Number=.,Type=String,Description="test"']
  with gzip.open(files[0],'rt') as f:input_text=f.read()
  # annotate CLI takes VCF on stdin; redirect via explicit file flag - no, positional accepts VCF.
  for flags in ([],['--fill-AC-AN'],['-r','FORMAT/DP'],['-f','Qual=20']):
   pair('vcf-annotate',args+flags+[files[0]],f'fuzz-annot-{seed}-{len(RESULT)}',seed)
 # Real VCF: 1000 Genomes phase3 chr22 20,000,001-21,000,000, stored by previous runs.
 source=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz');rows=[];full_rows=[]
 with gzip.open(source,'rt') as f:
  for line in f:
   if line.startswith('#CHROM'):sample_names=line.rstrip().split('\t')[9:]
   if not line.startswith('#'):
    full_rows.append(line);rows.append('\t'.join(line.rstrip().split('\t')[:8])+'\n')
 (ROOT/'input.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'records':len(rows),'sample_columns':'removed for site intersection/annotation'},indent=2))
 for representation,records in [('sites',rows),('cohort100',full_rows)]:
  for n in (2,8,32):
   files=[vcf(D/f'{representation}-real{f}.vcf',[r for i,r in enumerate(records) if i%3==0 or i%n==f],names=sample_names if representation=='cohort100' else None) for f in range(n)]
   for mode,flags in [('intersection',[]),('union',['-n','+1']),('windowed-intersection',['-w','10000'])]:
    for rep in range(3):pair('vcf-isec',flags+files,f'real-{representation}-{mode}-{n}-{rep}')
 # Actual transcript intervals from UCSC hg19 refGene.
 url='https://hgdownload.soe.ucsc.edu/goldenPath/hg19/database/refGene.txt.gz';gene=D/'refGene.txt.gz'
 shell(['curl','--fail','--location','--retry','2','--max-time','180','-o',str(gene),url])
 intervals=[]
 with gzip.open(gene,'rt') as f:
  for l in f:
   a=l.rstrip().split('\t');start,end=int(a[4])+1,int(a[5])
   if a[2]=='chr22' and start<=21000000 and end>=20000001:intervals.append((start,end,a[1]))
 ann=D/'genes.tsv';ann.write_text(''.join(f'22\t{a}\t{b}\t{v}\n' for a,b,v in sorted(intervals)));annot=compress(ann,'bed')
 (ROOT/'annotation-input.json').write_text(json.dumps({'url':url,'sha256':hashlib.sha256(gene.read_bytes()).hexdigest(),'intervals':len(intervals)},indent=2))
 for representation,records in [('sites',rows),('cohort100',full_rows)]:
  sites=vcf(D/(representation+'-annot.vcf'),records,names=sample_names if representation=='cohort100' else None)
  args=['-a',annot,'-c','CHROM,FROM,TO,INFO/TRANSCRIPT','-d','key=INFO,ID=TRANSCRIPT,Number=.,Type=String,Description="UCSC refGene transcript"',sites]
  for rep in range(3):pair('vcf-annotate',args,f'real-{representation}-annot-{rep}')
 save();(ROOT/'complete.json').write_text(json.dumps({'passed':True,'cases':len(RESULT)}))
try:main()
except Exception as e:
 (ROOT/'failure.txt').write_text(repr(e));raise
