from pathlib import Path
exec((Path(__file__).resolve().parent/'run.py').read_text().split('\ntry:')[0])
BASE=R;R=BASE/'site-parser';R.mkdir(exist_ok=True);D=R/'data';D.mkdir(exist_ok=True)
LIB['candidate']=BASE/'candidate6/src/perl';BIN['candidate']=LIB['candidate']
try:
 save('validating')
 for label,source in [('before',BASE/'before/src/perl'),('original',O)]:
  subprocess.run(['python3',str(BASE/'candidate6/tests/perl_remaining_regression.py'),'--reference',str(source),'--candidate',str(LIB['candidate']),'--output',str(R/('controls-'+label))],env=ENV,check=True)
 for n,src in [(500,Path('/jobtmp/zliu328/nuvcftools-parallel-ld-20261126/data/cohort500.vcf.gz')),(2504,Path('/jobtmp/zliu328/nuvcftools-expanded-20261121/data/cohort_all.vcf.gz'))]:
  names=subprocess.check_output(['bcftools','query','-l',str(src)],text=True).splitlines()
  sexes=D/f'sexes{n}.txt';sexes.write_text(''.join(x+' M\n' for x in names))
  runrow('ploidy-pass-through-'+str(n),'vcf-fix-ploidy',['-s',str(sexes)],src,True)
  policy=D/'ploidy.pl';policy.write_text('{22=>[{from=>20000001,to=>21000000,M=>1}]}\n')
  if n==500:runrow('ploidy-active-500','vcf-fix-ploidy',['-s',str(sexes),'-p',str(policy)],src,True)
 save('complete')
except Exception:
 save('failed');(R/'failure.txt').write_text(traceback.format_exc());raise
