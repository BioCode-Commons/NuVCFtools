#!/bin/bash
#SBATCH --job-name=nuvcf-ld-workspace-build
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=build-%j.out
#SBATCH --error=build-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
cp -a /jobtmp/zliu328/nuvcftools-ld-chisq-output-20261126/source source
cp variant_file_output.cpp ld_chisq.h source/src/cpp/
make -C source/src/cpp -j2 > build.log 2>&1
mkdir -p install/candidate/bin
cp source/src/cpp/vcftools install/candidate/bin/vcftools
sha256sum install/candidate/bin/vcftools > binary-sha256.txt
