#!/bin/bash
#SBATCH --job-name=nuvcf-native-standard
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
cp -a /jobtmp/zliu328/nuvcftools-parallel-ld-20261126/source source
cp configure.ac source/configure.ac
cp Makefile.am source/src/cpp/Makefile.am
(cd source && make clean && autoreconf -fi && ./configure CXXFLAGS=-O2 --prefix="$SLURM_SUBMIT_DIR/install/candidate" && make -j4 && make check && make install) > build.log 2>&1
sha256sum install/candidate/bin/vcftools > binary.sha256
