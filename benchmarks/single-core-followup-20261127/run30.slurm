#!/bin/bash
#SBATCH --job-name=vcf-single30
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=/jobtmp/zliu328/nuvcftools-parallel-tools-v1/run-%j.out
#SBATCH --error=/jobtmp/zliu328/nuvcftools-parallel-tools-v1/run-%j.err
set -euo pipefail
module load samtools/1.19.2-fm2x bcftools/1.21-yc5i
cd /jobtmp/zliu328/nuvcftools-parallel-tools-v1
srun --cpu-bind=cores python3 run30.py
