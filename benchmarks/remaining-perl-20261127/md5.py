from pathlib import Path
exec((Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:')[0])
import shutil
BASE=R;R=BASE/'md5';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
LIB['candidate']=BASE/'candidate5/src/perl';BIN['candidate']=LIB['candidate']
try:
 save('preparing');start=time.monotonic()
 fa=BASE/'reference2/data/GRCh37.22.fa'
 src=D/'cohort500.vcf.gz'
 shutil.copyfile('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz',src)
 subprocess.run(['tabix','-p','vcf',str(src)],check=True)
 (R/'preparation.json').write_text(json.dumps({'seconds':time.monotonic()-start,'excluded':True}))
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
