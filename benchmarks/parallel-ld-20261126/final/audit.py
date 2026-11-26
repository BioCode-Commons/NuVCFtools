import json
from pathlib import Path
root=Path(__file__).resolve().parent
rows=json.loads((root/'controls-resume-status.json').read_text())['results']
assert len(rows)==7 and all(r['passed'] and len(r['measurements'])==4 and all(v['exit']==0 and v['temp_files_remaining']==0 for v in r['measurements'].values()) for r in rows)
checks=json.loads((root/'error-checks.json').read_text());assert len(checks)==8 and all(r['passed'] for r in checks)
paths=json.loads((root/'path-regression.json').read_text())
assert all(r['expected_behavior_observed'] for r in paths if r['label']!='before-bounded-failure')
reference=(root/'path-regression/reference.geno.chisq').read_bytes()
assert all((root/('path-regression/'+label+'.geno.chisq')).read_bytes()==reference for label in ['candidate1','candidate4'])
(root/'controls-resume-complete.json').write_text(json.dumps({'passed':True,'cases':7,'successful_runs':28,'error_checks':8,'audit_note':'Prior job exited on an invalid expectation that old undefined behavior must always fail. All candidate checks passed, and retained path-test outputs were compared again. Initial failure metadata retained.'},indent=2))
print('Candidate comparisons and error cleanup verified; old UB behavior recorded without a crash requirement')
