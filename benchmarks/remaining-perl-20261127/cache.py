from pathlib import Path
text=(Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:')[0]
text=text.replace("str(BIN[label]/tool)]+args", "str(BIN[label]/tool)]+(['--reference-cache-size','1048576'] if label=='candidate' else [])+args")
exec(text)
BASE=R;R=BASE/'cache';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
LIB['candidate']=BASE/'candidate5/src/perl';BIN['candidate']=LIB['candidate']
try:
 save('preparing')
 fa=D/'reference.fa';fa.write_text('>22\n'+('ACGT'*524288)+'\n')
 subprocess.run(['samtools','faidx',str(fa)],check=True)
 header='##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'
 # Nonmonotone positions force cache eviction/reload; symbolic and indel
 # records use the same legacy normalization and masking paths.
 vcf=D/'cases.vcf';vcf.write_text(header+''.join(f'22\t{p}\t.\tA\tAT\t.\tPASS\t.\n' for p in [101,105,1000101,201,1000201,205]))
 runrow('cache-controls','fill-fs',['-r',str(fa),'-l','40'],vcf)
 realfa=BASE/'reference2/data/GRCh37.22.fa'
 for n,src in [(500,Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')),(2504,Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz'))]:
  row=runrow('flanks-cache-'+str(n),'fill-fs',['-r',str(realfa),'-l','100'],src,True)
  row['candidate_flags']=['--reference-cache-size','1048576'];save('running')
 save('complete')
except Exception:
 save('failed');(R/'failure.txt').write_text(traceback.format_exc());raise
