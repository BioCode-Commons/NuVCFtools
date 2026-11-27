#!/bin/bash
#SBATCH --job-name=vcf-sort-life
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/jobtmp/zliu328/nuvcftools-remaining-20261127/sort-lifecycle-%j.out
#SBATCH --error=/jobtmp/zliu328/nuvcftools-remaining-20261127/sort-lifecycle-%j.err
set -euo pipefail
module load samtools/1.19.2-fm2x bcftools/1.21-yc5i
cd /jobtmp/zliu328/nuvcftools-remaining-20261127
srun --cpu-bind=cores python3 sort_lifecycle.py
