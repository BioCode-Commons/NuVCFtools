from pathlib import Path
exec((Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:')[0])
BASE=R; R=BASE/'reference2';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
LIB['candidate']=BASE/'candidate2/src/perl';BIN['candidate']=LIB['candidate']
try:
 save('preparing');begin=time.monotonic()
 for label in ['original','before']:
  prior=R/('controls-'+label)/'results.json'
  if prior.exists() and len(json.loads(prior.read_text()))==90 and all(x['passed'] for x in json.loads(prior.read_text())):continue
  source=O if label=='original' else LIB['before']
  subprocess.run(['python3',str(BASE/'candidate2/tests/perl_remaining_regression.py'),'--reference',str(source),'--candidate',str(LIB['candidate']),'--output',str(R/('controls-'+label))],env=ENV,check=True)
 url='https://ftp.ensembl.org/pub/grch37/current/fasta/homo_sapiens/dna/Homo_sapiens.GRCh37.dna.chromosome.22.fa.gz'
 fa=D/'GRCh37.22.fa';gz=D/'GRCh37.22.fa.gz'
 subprocess.run(['curl','-fL','--retry','2','--max-time','120','-o',str(gz),url],check=True)
 with gzip.open(gz,'rb') as inp,fa.open('wb') as out:
  import shutil;shutil.copyfileobj(inp,out)
 subprocess.run(['samtools','faidx',str(fa)],check=True)
 src=Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')
 # Real phased VCF SNPs for conversion/consensus; no invented genotypes.
 snps=D/'snps.vcf.gz'
 subprocess.run(['bcftools','view','--no-version','-v','snps','-m2','-M2','-Oz','-o',str(snps),str(src)],check=True)
 subprocess.run(['tabix','-f','-p','vcf',str(snps)],check=True)
 subset=D/'small.vcf.gz'
 subprocess.run(['bcftools','view','--no-version','-t','22:20000001-20100000','-Oz','-o',str(subset),str(src)],check=True)
 subprocess.run(['tabix','-f','-p','vcf',str(subset)],check=True)
 (R/'preparation.json').write_text(json.dumps(dict(seconds=time.monotonic()-begin,excluded=True,url=url,fasta_sha256=hashlib.sha256(fa.read_bytes()).hexdigest(),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest()),indent=2))
 runrow('flanks-500','fill-fs',['-r',str(fa),'-l','100'],src,True)
 runrow('flanks-mask-500-small','fill-fs',['-r',str(fa),'-l','100','-v',str(subset)],subset,True)
 runrow('convert-snps-500','vcf-convert',['-v','4.2'],snps,True)
 # Same output filename for every version; compare decompressed output,
 # full header, dictionary and diagnostics. Recompute from a fresh dictionary.
 row=dict(case='reference-md5',measurements={});outputs={}
 for label in ['original','before','candidate']:
  out=D/'md5.vcf.gz';dictionary=D/'reference.dict'
  for f in [out,dictionary,Path(str(out)+'.header')]:f.unlink(missing_ok=True)
  pref=R/('md5-'+label)
  with pref.with_suffix('.out').open('wb') as stdout,pref.with_suffix('.err').open('wb') as stderr:
   cmd=['/usr/bin/time','-f','%e %M %U %S','-o',str(pref)+'.time','perl',str(BIN[label]/'fill-ref-md5'),'-r',str(fa),'-d',str(dictionary),str(src),str(out)]
   p=subprocess.run(cmd,env=dict(ENV,PERL5LIB=str(LIB[label])),stdout=stdout,stderr=stderr,timeout=120)
  if p.returncode:raise RuntimeError('md5 '+label)
  t=Path(str(pref)+'.time').read_text().split();row['measurements'][label]=dict(wall_seconds=float(t[0]),rss_kib=int(t[1]),user_seconds=float(t[2]),sys_seconds=float(t[3]),exit=p.returncode)
  dest=R/('md5-'+label+'.vcf')
  with gzip.open(out,'rb') as inp,dest.open('wb') as dst:shutil.copyfileobj(inp,dst)
  outputs[label]=(dest,Path(str(out)+'.header').read_bytes(),dictionary.read_bytes(),pref.with_suffix('.out').read_bytes(),norm(pref.with_suffix('.err').read_bytes()))
 row['passed']=all(equal(outputs['original'][0],v[0]) and outputs['original'][1:]==v[1:] for v in outputs.values())
 results.append(row);save('running')
 if not row['passed']:raise RuntimeError('md5 mismatch')
 for v in outputs.values():v[0].unlink()
 save('complete')
except Exception:
 save('failed');(R/'failure.txt').write_text(traceback.format_exc());raise
