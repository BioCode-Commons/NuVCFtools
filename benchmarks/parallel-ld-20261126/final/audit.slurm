#!/bin/bash
#SBATCH --job-name=nuvcf-control-audit
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:02:00
#SBATCH --output=audit-%j.out
#SBATCH --error=audit-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
python3 audit.py
