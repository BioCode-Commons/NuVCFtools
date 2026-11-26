#!/bin/bash
#SBATCH --job-name=nuvcf-serial-regression
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=compare-%j.out
#SBATCH --error=compare-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
ulimit -c 0
srun --cpu-bind=cores python3 compare.py
