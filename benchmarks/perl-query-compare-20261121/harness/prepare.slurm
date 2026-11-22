#!/usr/bin/env bash
#SBATCH --job-name=nuvcf-qc-cacheprep
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:45:00
#SBATCH --output=prepare-%j.out
#SBATCH --error=prepare-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
module load bcftools/1.21-yc5i
exec python3 -u harness/prepare.py
