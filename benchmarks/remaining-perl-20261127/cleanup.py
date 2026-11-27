import json
from pathlib import Path
r=Path(__file__).resolve().parent
for folder in ['audit','cache','md5','site-parser','sort-parallel']:
 s=json.loads((r/folder/'status.json').read_text())
 assert s['state']=='complete' and all(x['passed'] for x in s['results']),folder
s=json.loads((r/'status.json').read_text());assert s['state']=='complete' and all(x['passed'] for x in s['results'])
s=json.loads((r/'reference2/status.json').read_text());assert len(s['results'])==3 and all(x['passed'] for x in s['results'])
files=['audit/data/cohort500.vcf','audit/data/windows.vcf','audit/data/left.vcf.gz','audit/data/left.vcf.gz.tbi','audit/data/right.vcf.gz','audit/data/right.vcf.gz.tbi','md5/data/cohort500.vcf.gz','md5/data/cohort500.vcf.gz.tbi','md5/data/md5.vcf.gz','reference/data/GRCh37.22.fa','reference/data/GRCh37.22.fa.fai','reference/data/GRCh37.22.fa.gz','reference/data/snps.vcf.gz','reference/data/snps.vcf.gz.tbi','reference/data/small.vcf.gz']
removed=[]
for name in files:
 p=r/name
 if p.is_file():
  removed.append({'path':name,'bytes':p.stat().st_size});p.unlink()
(r/'cleanup.json').write_text(json.dumps({'state':'complete','removed':removed,'canonical_inputs_preserved':True,'GRCh37_reference_preserved':'reference2/data/GRCh37.22.fa','timed_raw_outputs':'Removed by each runner only after full comparison passed; synthetic negative-case diagnostics retained.'},indent=2))
print(json.dumps({'removed_files':len(removed),'removed_bytes':sum(x['bytes'] for x in removed)}))
