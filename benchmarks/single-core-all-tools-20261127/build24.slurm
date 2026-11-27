#!/bin/bash
#SBATCH --job-name=vcf-native24-build
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/jobtmp/zliu328/nuvcftools-parallel-tools-v1/build24-%j.out
#SBATCH --error=/jobtmp/zliu328/nuvcftools-parallel-tools-v1/build24-%j.err
set -euo pipefail
cd /jobtmp/zliu328/nuvcftools-parallel-tools-v1/candidate24
./autogen.sh
./configure CXXFLAGS='-O2 -g' CFLAGS='-O2 -g'
make -j4
make -j4 check
sha256sum src/cpp/vcftools
