import json,shutil,sys,time
from pathlib import Path
for arg in sys.argv[1:]:
 root=Path(arg)
 if root.parent!=Path('/jobtmp/zliu328') or not root.name.startswith('nuvcftools-'):raise RuntimeError('Unexpected root')
 done=json.loads((root/'complete.json').read_text());state=json.loads((root/'status.json').read_text())
 if done.get('passed') is not True or not all(r.get('passed') is True for r in state['results']):raise RuntimeError('Not verified')
 data=root/'data';files=[p for p in data.rglob('*') if p.is_file()] if data.exists() else []
 report={'state':'complete','removed_files':len(files),'removed_bytes':sum(p.stat().st_size for p in files),'scope':str(data),'scientific_outputs':'already byte-compared and removed per successful pair','retained':['source snapshots','status.json','complete.json','input.json','annotation-input.json'],'time_epoch':time.time()}
 if data.exists():shutil.rmtree(data)
 (root/'cleanup.json').write_text(json.dumps(report,indent=2)+'\n')
 print(root.name,report['removed_bytes'])
