#!/bin/bash 

### Usage and parameters #######################################################
# 1: program to run (currently xia2 or autoproc)
# 2: BASE DATA FOLDER (aka SOURCEDATA) contains the /images folder)
# 3: RESULTS FOLDER (aka PROCDIR)
# 4: File recovery list
# 5 - ..: process parameters (as a shell formatted string)
################################################################################

### SLURM environment ##########################################################
#SBATCH --export=ALL
#SBATCH -N 1 -c 14
#SBATCH -p beamlines
#SBATCH --tmp=30G
################################################################################

### MANDATORY: export this variable in your bash.rc script #####################
if [ -z ${POST_PROCESSING_SCRIPTS_ROOT+x} ];then
    echo "YOU MUST export POST_PROCESSING_SCRIPTS_ROOT in your local bash.rc"
else
    echo "POST_PROCESSING_SCRIPTS_ROOT = '$POST_PROCESSING_SCRIPTS_ROOT'"
fi
################################################################################

### ALBA cluster environment ###################################################
export OMP_NUM_THREADS=64
export  PATH="$PATH:/mnt/hpcsoftware/share/XDS-INTEL64_Linux_x86_64"
export  KMP_STACKSIZE=8m
source  /mnt/hpcsoftware/share/ccp4/ccp4-linux64/bin/ccp4.setup-sh
source  /mnt/hpcsoftware/share/GPhL/autoPROC/setup.sh
################################################################################

### LOCAL environment ##########################################################
INSTALL_DIR=${POST_PROCESSING_SCRIPTS_ROOT}
source ${INSTALL_DIR}/etc/SLURM.rc
# We assume ALL directories passed as arguments ALREADY exist.
SOURCEDATA=$2
PROCDIR=$3
WORKDIR="/tmp/autoproc_$SLURM_JOBID"
#FILELIST="${INSTALL_DIR}/autoproc/autoproc.files2recover"
FILELIST=$4
################################################################################

### MAIN script ################################################################
echo "Calling parameters: $*"
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

if [ ${SOURCEDATA} == '.' ]; then
   SOURCEDATA=$(pwd); fi
if [ ${SOURCEDATA} == './' ]; then
   SOURCEDATA=$(pwd); fi
if [ ! -d ${SOURCEDATA} ]; then
   echo "Directory ${SOURCEDATA} not found.  Exit."
   quit 1
fi
cd ${SOURCEDATA}
echo "Process dataset ${SOURCEDATA}."
if [ ! -e ./images ]; then
   echo "Directory ${SOURCEDATA}/images not found.  Exit."
   quit 1
else
   numcbf=`find ./images/ -maxdepth 1 -type f -name '*.cbf' | wc -l`
   if [ "${numcbf}" -lt "${mincbf}" ]; then
      echo "Fewer than minimum number of *.cbf images (${mincbf}) detected in ./images directory.  Exit."
      cd ${start_dir}
      quit 1
   fi
fi


###############################################################################
# Copy files to computing nodes
###############################################################################
mkdir -p $WORKDIR/images
mkdir -p $WORKDIR/proc

for f in ./images/*.cbf ; do
   # echo $f
    sbcast $f $WORKDIR/images/`basename $f`
done

###############################################################################
# The -d option of autoproc doesnt work properly, we cd to the output dir
###############################################################################
if [ -d "${WORKDIR}"/proc ]
then
    pushd "${WORKDIR}"/proc 

    ### RUN ########################################################################
    # Run autoPROC.
    # Contact information for Clemens Vonrhein at Global Phasing.
    # Email: vonrhein@globalphasing.com
    # Telephone: 9-011-497616966491
    #
    if [ "$1" == 'process' ]
    then
       srun process -I "$WORKDIR"/images "${@:5}"
    elif [ "$1" == 'xia2' ]
    then
       srun xia2 "$WORKDIR" "${@:5}"
    fi
    ################################################################################

    ### Recovering results #########################################################
    # We assume that PROCDIR already exist.
    # mkdir -p $PROCDIR

    gather_files_bundle_from_filelist $WORKDIR/proc $PROCDIR $FILELIST
    #gather_files_from_filelist $WORKDIR/proc $PROCDIR $FILELIST

    # Files excluded from list
    # 1) Symbolic links
    gather_links $WORKDIR/proc $PROCDIR
    # 2) Specific files identified by pattern
    # This is the log!!!!!
    #gather_file_by_pattern $WORKDIR/proc $PROCDIR "_default_processing.log"
    ################################################################################

    echo "`date`"
    popd
fi
quit 0

