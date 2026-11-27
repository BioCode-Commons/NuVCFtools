#!/bin/bash
#SBATCH --job-name=vcf-controls
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/jobtmp/zliu328/nuvcftools-remaining-20261127/controls-%j.out
#SBATCH --error=/jobtmp/zliu328/nuvcftools-remaining-20261127/controls-%j.err
set -euo pipefail
module load samtools/1.19.2-fm2x bcftools/1.21-yc5i
cd /jobtmp/zliu328/nuvcftools-remaining-20261127
export PYTHONPATH="$PWD/candidate5/tests"
srun --cpu-bind=cores python3 "$PWD/perl_remaining_regression.py" --reference "$PWD/before/src/perl" --candidate "$PWD/candidate5/src/perl" --output "$PWD/cache-final-controls-before"
srun --cpu-bind=cores python3 "$PWD/perl_remaining_regression.py" --reference /jobtmp/zliu328/nuvcftools-benchmark-20261121/install/VCFtools --candidate "$PWD/candidate5/src/perl" --output "$PWD/cache-final-controls-original"
srun --cpu-bind=cores perl -I"$PWD/candidate5/src/perl" "$PWD/candidate5/tests/readonly_genotypes.pl"
