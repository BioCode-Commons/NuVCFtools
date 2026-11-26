#!/bin/bash
#SBATCH --job-name=nuvcf-subset-speed
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --hint=nomultithread
#SBATCH --output=subset-%j.out
#SBATCH --error=subset-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
exec srun --cpu-bind=threads python3 -u run_subset.py
