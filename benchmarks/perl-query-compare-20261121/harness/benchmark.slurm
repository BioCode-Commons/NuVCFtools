#!/usr/bin/env bash
#SBATCH --job-name=nuvcf-qc-cachebench
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:30:00
#SBATCH --hint=nomultithread
#SBATCH --output=bench-%j.out
#SBATCH --error=bench-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
exec srun --cpu-bind=threads python3 -u harness/run.py
