#!/bin/bash
#SBATCH --job-name=vcf-remaining
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/jobtmp/zliu328/nuvcftools-remaining-20261127/run-%j.out
#SBATCH --error=/jobtmp/zliu328/nuvcftools-remaining-20261127/run-%j.err
set -euo pipefail
module load bcftools/1.21-yc5i
cd /jobtmp/zliu328/nuvcftools-remaining-20261127
srun --cpu-bind=cores python3 run.py
