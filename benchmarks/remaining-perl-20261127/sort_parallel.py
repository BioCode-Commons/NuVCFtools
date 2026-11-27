from pathlib import Path
exec((Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:')[0])
import random
BASE=R;R=BASE/'sort-parallel';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
# Final sort implementation was restored byte-for-byte to the frozen Before.
LIB['candidate']=BASE/'before/src/perl';BIN['candidate']=LIB['candidate']
try:
 save('preparing');start=time.monotonic()
 src=Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz')
 header=[];rows=[]
 with gzip.open(src,'rb') as inp:
  for line in inp:(header if line.startswith(b'#') else rows).append(line)
 random.Random(20261127).shuffle(rows)
 f=D/'shuffled.vcf.gz'
 with gzip.open(f,'wb',compresslevel=1) as out:
  out.writelines(header);out.writelines(rows)
 (R/'preparation.json').write_text(json.dumps(dict(seconds=time.monotonic()-start,excluded=True,records=len(rows),input_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),shuffled_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),sort_candidate_identical_to_before=True,allocated_cores=4)))
 del header,rows
 for n in [1,4]:runrow('sort-shuffled-threads'+str(n),'vcf-sort',['-p',str(n)],f,True)
 f.unlink();save('complete')
except Exception:
 save('failed');(R/'failure.txt').write_text(traceback.format_exc());raise
