import hashlib,json
from pathlib import Path
m=json.loads(Path('source-manifest.json').read_text());n=0
for label,items in m.items():
 for filename,want in items.items():
  actual=hashlib.sha256((Path(label)/filename).read_bytes()).hexdigest()
  if actual!=want:raise RuntimeError((label,filename))
  n+=1
Path('source-verification.json').write_text(json.dumps({'passed':True,'files':n,'manifest_sha256':hashlib.sha256(Path('source-manifest.json').read_bytes()).hexdigest()},indent=2))
print('verified',n)
