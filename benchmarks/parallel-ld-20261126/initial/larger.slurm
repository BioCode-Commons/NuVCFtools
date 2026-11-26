#!/bin/bash
#SBATCH --job-name=nuvcf-larger-ld
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=larger-%j.out
#SBATCH --error=larger-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
ulimit -c 0
python3 -u run.py larger
