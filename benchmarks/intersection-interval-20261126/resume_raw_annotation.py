import gzip,hashlib,json,shutil
from pathlib import Path
root=Path('/jobtmp/zliu328/nuvcftools-bytecheck-20261126')
ns={'__file__':str(root/'run.py'),'__name__':'resume_validation'}
exec((root/'run.py').read_text().split('try:main()')[0],ns)
ns['RESULT']=json.loads((root/'status.json').read_text())['results']
assert len(ns['RESULT'])==138 and all(r['passed'] for r in ns['RESULT'])
source=Path('/jobtmp/zliu328/nuvcftools-prefix-20261126')
gene=source/'data/refGene.txt.gz';expected=json.loads((source/'annotation-input.json').read_text())
assert hashlib.sha256(gene.read_bytes()).hexdigest()==expected['sha256']
D=ns['D'];shutil.copyfile(gene,D/'refGene.txt.gz')
intervals=[]
with gzip.open(gene,'rt') as f:
 for l in f:
  a=l.rstrip().split('\t');start,end=int(a[4])+1,int(a[5])
  if a[2]=='chr22' and start<=21000000 and end>=20000001:intervals.append((start,end,a[1]))
assert len(intervals)==expected['intervals']
ann=D/'genes.tsv';ann.write_text(''.join(f'22\t{a}\t{b}\t{v}\n' for a,b,v in sorted(intervals)));annot=ns['compress'](ann,'bed')
(root/'annotation-input.json').write_text(json.dumps(dict(expected,reused_verified_file=str(gene)),indent=2))
rows=[];full=[]
with gzip.open('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort100.vcf.gz','rt') as f:
 for line in f:
  if line.startswith('#CHROM'):names=line.rstrip().split('\t')[9:]
  if not line.startswith('#'):full.append(line);rows.append('\t'.join(line.rstrip().split('\t')[:8])+'\n')
for representation,records in [('sites',rows),('cohort100',full)]:
 sites=ns['vcf'](D/(representation+'-annot.vcf'),records,names=names if representation=='cohort100' else None)
 args=['-a',annot,'-c','CHROM,FROM,TO,INFO/TRANSCRIPT','-d','key=INFO,ID=TRANSCRIPT,Number=.,Type=String,Description="UCSC refGene transcript"',sites]
 ns['pair']('vcf-annotate',args,f'real-{representation}-annot-0')
ns['save']()
(root/'complete.json').write_text(json.dumps({'passed':True,'cases':len(ns['RESULT']),'initial_job':9638611,'resume_job':__import__('os').environ.get('SLURM_JOB_ID'),'resumption_reason':'stalled duplicate UCSC download; reused SHA256-verified cached annotation','comparison':'raw stdout bytes, no normalization'},indent=2))
