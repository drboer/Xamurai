#!/bin/bash
#SBATCH --export=ALL
#SBATCH -N 1 -c 14
#SBATCH -p beamlines

# Usage of the parameters:
# 1: data_dir
# 2: process parameters (as a shell formated string)

# Start of Cluster options and parameters
export OMP_NUM_THREADS=64

export  PATH="$PATH:/mnt/hpcsoftware/share/XDS-INTEL64_Linux_x86_64"
export  KMP_STACKSIZE=8m
source  /mnt/hpcsoftware/share/ccp4/ccp4-linux64/bin/ccp4.setup-sh
source  /mnt/hpcsoftware/share/GPhL/autoPROC/setup.sh
# End of Cluster options and parameters

echo "Calling parameters: $*"

# Start of export program options and parameters.
data_set_dir=$1
procdir=$2
# Minimum number of diffraction images required to initiate autoPROC.
mincbf='20'
# Standard log file
# Starting directory (not sure why it's used)
start_dir=$(pwd)
# End of export program options and parameters.

# Prepare to run autoPROC.
echo ""
echo "******** AUTOPROC SCRIPT ********"
echo "* XALOC (ALBA-CELLS) Pilatus 6M *"
echo "*********************************"
echo "`date`"
#
function quit {
    cd ${start_dir}
    exit $1
}

if [ ${data_set_dir} == '.' ]; then
   data_set_dir=$(pwd); fi
if [ ${data_set_dir} == './' ]; then
   data_set_dir=$(pwd); fi
if [ ! -d ${data_set_dir} ]; then
   echo "Directory ${data_set_dir} not found.  Exit."
   quit 1
fi
cd ${data_set_dir}
echo "Process dataset ${data_set_dir}."
if [ ! -e ./images ]; then
   echo "Directory ${data_set_dir}/images not found.  Exit."
   quit 1
else
   numcbf=`find ./images/ -maxdepth 1 -type f -name '*.cbf' | wc -l`
   if [ "${numcbf}" -lt "${mincbf}" ]; then
      echo "Fewer than minimum number of *.cbf images (${mincbf}) detected in ./images directory.  Exit."
      cd ${start_dir}
      quit 1
   fi
fi
# Run autoPROC.
# Contact information for Clemens Vonrhein at Global Phasing.
# Email: vonrhein@globalphasing.com
# Telephone: 9-011-497616966491
#
# TODO: an extra subdirectory should be added after ${ap_num} to put all output, and links to most important files should be made
srun process -d "${procdir}" "${@:3}"

# Exit
echo "`date`"
quit 0
