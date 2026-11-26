#!/bin/bash
#SBATCH --job-name=nuvcf-parallel-build
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:20:00
#SBATCH --output=build-%j.out
#SBATCH --error=build-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
module purge
mkdir source
 tar -xf base.tar -C source
(cd source && patch -p1 < ../candidate.patch)
cp variant_file_ld_parallel.cpp source/src/cpp/
(cd source && autoreconf -fi && ./configure CXXFLAGS=-O2 --prefix="$SLURM_SUBMIT_DIR/install/candidate" && make -j4 && make check && make install) > build.log 2>&1
sha256sum install/candidate/bin/vcftools > binary.sha256
g++ --version > compiler.txt
lscpu > cpu.txt
