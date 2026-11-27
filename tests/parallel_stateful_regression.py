#!/usr/bin/env python3
"""Small exact-byte checks of window groups, interval cursors and ordered writers."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--before',required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',required=True);p.add_argument('--indexed',action='store_true');a=p.parse_args()
d=Path(a.output).resolve();d.mkdir(parents=True,exist_ok=False)
header='##fileformat=VCFv4.2\n##contig=<ID=22,length=2000>\n##contig=<ID=23,length=2000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample\n'
rows=[]
for chrom in ['22','23']:
 for i in range(80):
  ref,alt=[('AT','A'),('A','ATTT'),('ATTT','A,AT'),('A','C'),('A','.'),('AC','GT'),('A','AT,C'),('A','<DEL>')][i%8]
  rows.append(f'{chrom}\t{i*9+1}\t.\t{ref}\t{alt}\t.\tPASS\t.\tGT\t0/1\n')
input=d/'input.vcf';input.write_text(header+''.join(rows))
exons=d/'exons.tsv';exons.write_text('22\t2\t90\n22\t12\t40\n22\t80\t150\n22\t300\t600\n23\t10\t40\n23\t40\t710\n')
cases=[('indel','vcf-indel-stats',['-e',str(exons)],input.read_bytes()),('indel-verbose','vcf-indel-stats',['-e',str(exons),'-v'],input.read_bytes()),('indel-empty','vcf-indel-stats',['-e',str(exons)],header.encode()),('indel-no-newline','vcf-indel-stats',['-e',str(exons)],input.read_bytes().rstrip())]
if a.indexed:
 files=[]
 for label,selected in [('a',rows),('b',[r for i,r in enumerate(rows) if i%3]),('c',[r for i,r in enumerate(rows) if i%4])]:
  f=d/(label+'.vcf');f.write_text(header+''.join(selected))
  with Path(str(f)+'.gz').open('wb') as out:subprocess.run(['bgzip','-c',str(f)],stdout=out,check=True)
  subprocess.run(['tabix','-p','vcf',str(f)+'.gz'],check=True);files.append(str(f)+'.gz')
 for label,opts in [('plain',[]),('window',['-w','11']),('all',['-a']),('complement',['-c']),('nfiles',['-n','+2'])]:
  cases.append(('isec-'+label,'vcf-isec',opts+files,None))
results=[]
for seed in [0,1,19]:
 for label,tool,args,data in cases:
  def run(root,extra):
   env=dict(os.environ,PERL5LIB=str(root),PERL_HASH_SEED=str(seed),PERL_PERTURB_KEYS='0',LC_ALL='C')
   return subprocess.run(['perl',str(Path(root)/tool)]+args+extra,input=data,capture_output=True,env=env,timeout=60)
  before=run(a.before,[])
  if before.returncode:raise RuntimeError(f'baseline {label}: {before.stderr.decode()}')
  for workers in [1,2,4]:
   after=run(a.candidate,['--workers',str(workers),'--worker-batch-bytes','256'])
   passed=(before.returncode,before.stdout,before.stderr)==(after.returncode,after.stdout,after.stderr)
   results.append(dict(case=label,workers=workers,seed=seed,passed=passed))
   (d/'results.json').write_text(json.dumps(results,indent=2)+'\n')
   if not passed:
    for n,r in [('before',before),('candidate',after)]:
     (d/f'{label}-{n}.stdout').write_bytes(r.stdout);(d/f'{label}-{n}.stderr').write_bytes(r.stderr)
    raise RuntimeError(f'{label} mismatch seed={seed} workers={workers}')
print(json.dumps(dict(passed=True,cases=len(results))))
