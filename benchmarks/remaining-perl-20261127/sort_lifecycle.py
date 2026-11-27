import json,os,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent;d=r/'sort-lifecycle';d.mkdir(exist_ok=True)
w=d/'sort';w.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then exec /usr/bin/sort --help; fi\npython3 -c \'import sys,time; data=sys.stdin.buffer.read(); time.sleep(2); sys.stdout.buffer.write(data)\'\n');w.chmod(0o755)
start=time.monotonic()
p=subprocess.Popen(['perl',str(r/'before/src/perl/vcf-sort')],stdin=subprocess.PIPE,stdout=(d/'output').open('wb'),stderr=(d/'error').open('wb'),env=dict(os.environ,PATH=str(d)+':'+os.environ['PATH']))
p.communicate(b'#header\n22\t1\tA\n');elapsed=time.monotonic()-start
print(json.dumps({'tool_return_seconds':elapsed,'bytes_at_return':(d/'output').stat().st_size,'returncode':p.returncode}))
time.sleep(3)
print(json.dumps({'bytes_after_child_should_finish':(d/'output').stat().st_size}))
