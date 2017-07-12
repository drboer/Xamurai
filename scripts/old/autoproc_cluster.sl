#!/bin/bash
#SBATCH --export=ALL
#SBATCH -N 1 -c 32

export OMP_NUM_THREADS=64

export  PATH="$PATH:/mnt/hpcsoftware/share/XDS-INTEL64_Linux_x86_64"
export  KMP_STACKSIZE=8m
source  /mnt/hpcsoftware/share/ccp4/ccp4-linux64/bin/ccp4.setup-sh
source  /mnt/hpcsoftware/share/GPhL/autoPROC/setup.sh

srun $1 $2 >> $3 2>&1