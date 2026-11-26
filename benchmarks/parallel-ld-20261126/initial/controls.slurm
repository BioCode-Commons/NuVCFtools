#!/bin/bash
#SBATCH --job-name=nuvcf-parallel-check
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=controls-%j.out
#SBATCH --error=controls-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
python3 -u run.py controls
