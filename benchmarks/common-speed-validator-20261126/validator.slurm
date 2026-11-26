#!/bin/bash
#SBATCH --job-name=nuvcf-validator-speed
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --hint=nomultithread
#SBATCH --output=validator-%j.out
#SBATCH --error=validator-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
exec srun --cpu-bind=threads python3 -u run_validator.py
