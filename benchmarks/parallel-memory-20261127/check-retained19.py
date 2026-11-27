import gzip,hashlib,json,os,re,shlex,subprocess,time,traceback,shutil,signal
from pathlib import Path
R=Path('/jobtmp/zliu328/nuvcftools-parallel-tools-v1');D=R/'data';E=R/'retained19-controls';D.mkdir(exist_ok=True);E.mkdir(exist_ok=True)
ORIG=Path('/jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools')
LIB={'original':ORIG/'lib/perl5','before':R/'candidate17/src/perl','candidate':R/'candidate19/src/perl','queue':R/'candidate18/src/perl','memory':R/'candidate19/src/perl'}
BIN={'original':ORIG/'bin','before':R/'candidate17/src/perl','candidate':LIB['candidate'],'queue':LIB['queue'],'memory':LIB['memory']}
ENV=dict(os.environ,PYTHONPATH=str(R/'candidate20/tests'),PERL_HASH_SEED='0',PERL_PERTURB_KEYS='0',LC_ALL='C',TMPDIR=str(E))
for test in ['counter_event_layout_regression.pl','worker_ownership_regression.pl']:
 subprocess.run(['perl',str(R/'candidate20/tests'/test)],check=True,env=dict(ENV,PERL5LIB=str(LIB['candidate'])))
subprocess.run(['perl',str(R/'candidate20/tests/compare_queue_ownership_regression.pl'),str(LIB['candidate'])],check=True,env=dict(ENV,PERL5LIB=str(LIB['candidate'])))
for n in [1,4]:
 subprocess.run(['python3',str(R/'candidate20/tests/compare_index_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers',str(n),'--indexed','--output',str(E/f'compare-controls{n}')],check=True,env=ENV)
subprocess.run(['python3',str(R/'candidate20/tests/compare_queue_diagnostics_regression.py'),'--before',str(LIB['before']),'--candidate',str(LIB['candidate']),'--output',str(E/'diagnostics-controls')],check=True,env=ENV)
for n in [1,4,16]:
 subprocess.run(['python3',str(R/'candidate20/tests/perl_stats_merge_regression.py'),'--reference',str(LIB['before']),'--candidate',str(LIB['candidate']),'--workers',str(n),'--output',str(E/f'stats-merge-controls{n}')],check=True,env=ENV)
subprocess.run(['python3',str(R/'candidate20/tests/ordered_workers_regression.py'),'--before',str(LIB['before']),'--source',str(LIB['candidate']),'--output',str(E/'ordered-controls')],check=True,env=ENV)
(E/'status.json').write_text(json.dumps(dict(state='complete',candidate='candidate19',job=os.environ.get('SLURM_JOB_ID'))))
