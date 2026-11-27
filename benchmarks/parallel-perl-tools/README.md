# Reproducing the Perl worker measurements

These are the submitted Oscar harnesses, not portable examples. They reference the retained input and original installation paths under `/jobtmp/zliu328`. `runN.py` records wall time, GNU time accounting, 100 ms process-tree RSS/PSS sampling, actual byte comparisons and successful-output cleanup; its matching Slurm script loads the recorded dependencies and binds the allocated physical CPUs.

The candidate manifests identify every frozen source/test file. Runs 4/6/7/8/9/10/11/12/13 use candidates 3/5/7/8/9/10/11/11/13 respectively. Candidate 13 is the final source snapshot; report rows retain the snapshot actually measured. Before is the complete Perl directory from commit 92c7721ec154339aed5638b2142a39e49fa54f56. The upstream script identity audit is separate.

No biological output files are committed. Verified full output files were deleted after comparison; metadata and unsuccessful comparisons remain on Oscar. The parent report and JSON select the newest completed case for each command. Earlier measurements in intermediate runs are retained only to explain the experiments and memory changes.
