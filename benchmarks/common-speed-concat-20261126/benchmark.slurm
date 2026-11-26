#!/bin/bash
#SBATCH --job-name=nuvcf-concat-tree-v3
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=6G
#SBATCH --hint=nomultithread
#SBATCH --time=00:45:00
#SBATCH --output=bench-%j.out
#SBATCH --error=bench-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
exec srun --cpu-bind=threads python3 -u run_real.py
