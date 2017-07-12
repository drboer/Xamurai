#!/bin/csh
# Shell script to run autoPROC at ALBA, beamline XALOC (courtesy of Joshua Carter, Shamrock Structures)
# equipped with Pilatus 6M pixel-array detector.
#
# Updated 05/14/2011
#
# Usage:
# Enter crystal directory (e.g. /depot17id/bms/3November2010/G4_9)
# as the first, and only, argument.  Can use . for pwd.
# Expects ./images subdirectory to exist and contain *.cbf images.
# Creates ./autoproc/0 subdirectory if not present (increments otherwise).
# Creates ./data subdirectory if not present.
#
# Start of set program options and parameters.
# Minimum number of diffraction images required to initiate autoPROC.
set mincbf = '50'
#
# Process log file.
set process_log_file = 'autoproc_ALBA_XALOC.log'
set read_scale_log_file = 'read_scale.log'
#
# Key for do_read_scale.
#   2 = do not run read_scale.pl (even if aimless.log found)
#   1 = run read_scale.pl (provided aimless.log found)
#   0 = unable to run read_scale.pl (aimless.log not found)
#set do_read_scale = '2'
set do_read_scale = '1'
# End of set program options and parameters.
#
# Start of facility configuration.
set start_dir = `pwd`
# For use at IMCA-CAT.
setup-autoproc
set path_read_scale = '/beamlines/bl13/inhouse/rboer/scripts/manproc/'
#
# For use at BMS.
#unsetenv _CCP4_CSHRC
#source /ap/bin/ccp4_beta.cshrc
#unsetenv _XDS_CSHRC
#source /ap/bin/xds_beta.cshrc
#unsetenv _GPL_CSHRC
#source /ap/bin/gpl_beta.cshrc
#set path_read_scale = '/ap/bms/mmc'
# End of facility configuration.
#
# Prepare to run autoPROC.
echo "******** AUTOPROC SCRIPT ********"
echo "* XALOC (ALBA-CELLS) Pilatus 6M *"
echo "*********************************"
echo "\n`date`"
if ($#argv == 0) then
  echo "\n  Usage: autoproc.csh path_to_collected_dataset"
  echo "Example: autoproc.csh /depot17id/bms/3November2010/G4_9"
  goto STOP
endif
#
set dataset_dir = "${1}"
if ("${dataset_dir}" == '.' ) set dataset_dir = `pwd`
if ("${dataset_dir}" == './' ) set dataset_dir = `pwd`
if (! -e "${dataset_dir}") then
  echo "\nDirectory ${dataset_dir} not found.  Exit."
  goto STOP
endif
cd "${dataset_dir}"
echo "\nProcess dataset ${dataset_dir}."
if (! -e ./images) then
  echo "\nDirectory ${dataset_dir}/images not found.  Exit."
  goto STOP
else
  set numcbf = `find ./images/ -maxdepth 1 -type f -name '*.cbf' | wc -l`
  if ("${numcbf}" < "${mincbf}") then
    echo "\nFewer than minimum number of *.cbf images (${mincbf}) detected in ./images directory.  Exit."
    goto STOP
  endif
endif
if (-e ./autoproc) then
  set ap_num = `find ./autoproc -maxdepth 1 -type d -regex '\./autoproc/[0-9][0-9]*' | sort -n | tail -1 | sed 's^./autoproc/^^'`
  @ ap_num = ${ap_num} + 1
# set tag = `date | sed 's/ //g'`
# /bin/mv autoproc autoproc_${tag}
else
 mkdir ./autoproc
 set ap_num = '0'
endif
mkdir ./autoproc/${ap_num}
cd ./autoproc/${ap_num}
#
# Run autoPROC.
# Contact information for Clemens Vonrhein at Global Phasing.
# Email: vonrhein@globalphasing.com
# Telephone: 9-011-497616966491
# Contact information for IMCA-CAT beamline 17-ID.
# Telephone: 630-252-1717
# Online documentation
# /ap/gpl/current/docs/autoproc/manual/autoPROC0.html
#
# Omitted AutomaticChunking by default (it can do more harm that good).
# Add if significant decay is observed.
# AutomaticChunking="yes" \
# AutomaticChunking_MaxRuns="39" \
#
# autoPROC_XdsKeyword_OSCILLATION_RANGE=0.2023 \
#goto SKIP_PROCESS
/bin/rm -f "${process_log_file}"
process StopIfSubdirExists="no" \
  -d "${dataset_dir}/autoproc/${ap_num}" \
  -I "${dataset_dir}/images" \
#  -Id "truncate,${dataset_dir}/images,purple15_02_####.cbf,1,499" \
  BeamCentreFrom=header:x,y \
#  beam="1273 1322"   \
  autoPROC_TwoThetaAxis="-1 0 0" \
  -R 50.0 0.0 \
#  XdsSpotSearchMinNumSpotsPerImage=0   \
#  autoPROC_ScaleWithAimless="no"  \
 # ScalaAnaRmergeCut_123="99.9:0.9 99.9:0.8 99.9:0.7" \
 # ScalaAnaISigmaCut_123="0.50:1.0 1.0:1.5 1.5:2.0" \
  #ScalaAnaRpimallCut_123="99.9:0.8 99.9:0.6 99.9:0.4" \
 # ScalaAnaRmeasallCut_123="99.9:0.9 99.9:0.8 99.9:0.7" \
#  ScalaAnaCompletenessCut_123="0.0:0.4 0.0:0.45 0.0:0.5" \
#### ATAD2 UNIT CELL SPECIFIC COMMANDS \
# -ref /depot17id/bms/MTZ/atad2_reference_data.mtz  \
# -free /depot17id/bms/MTZ/atad2_reference_data.mtz  \
# cell="115 115 34 90 90 120" \
# symm=p64   \
#### FXIA UNIT CELL SPECIFIC COMMANDS  \
# -ref /depot17id/bms/MTZ/fxia_reference_data.mtz  \
# -free /depot17id/bms/MTZ/fxia_reference_data.mtz  \
#### DENV3 UNIT CELL SPECIFIC COMMANDS  \
# -ref /depot17id/bms/MTZ/Denv3_ns5_reference_data_p21212.mtz  \
# -free /depot17id/bms/MTZ/Denv3_ns5_reference_data_p21212.mtz  \
#  symm=P21212   \
#  cell="46 160 61 90 90 90" \
#  symm=p21   \
#  cell="176 57 161 90 90 90" \
#### KATII UNIT CELL SPECIFIC COMMANDS \
# symm=p43212   \
# cell="102 102 87 90 90 90" \
  Anom="yes" | tee "${process_log_file}"
SKIP_PROCESS:
#
# Make data directory and populate with key files.
#if (! -e ${dataset_dir}/data) mkdir ${dataset_dir}/data
echo
foreach file (aP_scale.log aimless.log truncate-unique.mtz CORRECT.LP INTEGRATE.LP)
  if (-e "${file}") then
#    /bin/cp -p "${file}" "${dataset_dir}/data"
#    echo "Copy ${file} from ./autoproc/${ap_num} to ./data (${dataset_dir})."
    if ("${file}" == 'aimless.log' && "${do_read_scale}" == '0') set do_read_scale = '1'
  else
#    echo "File ${file} not found.  Unable to copy from ./autoproc/${ap_num} to ./data (${dataset_dir})."
    if ("${file}" == 'aimless.log' && "${do_read_scale}" == '1') set do_read_scale = '0'
  endif
#end
#
# Optionally run read_scale.pl.
# Take date assigned to last image as creation date of dataset.
if ("${do_read_scale}" == '1') then
  cd "${dataset_dir}/images"
  set fdate = `ls --full-time *.cbf | tail -1 | awk '{print $6}'`
  set fyear = `echo "${fdate}" | awk '{print substr($0,1,4)}'`
  set fmonth = `echo "${fdate}" | awk '{print substr($0,6,2)}'`
  if (${fmonth} == '01') set fmonth = 'JAN'
  if (${fmonth} == '02') set fmonth = 'FEB'
  if (${fmonth} == '03') set fmonth = 'MAR'
  if (${fmonth} == '04') set fmonth = 'APR'
  if (${fmonth} == '05') set fmonth = 'MAY'
  if (${fmonth} == '06') set fmonth = 'JUN'
  if (${fmonth} == '07') set fmonth = 'JUL'
  if (${fmonth} == '08') set fmonth = 'AUG'
  if (${fmonth} == '09') set fmonth = 'SEP'
  if (${fmonth} == '10') set fmonth = 'OCT'
  if (${fmonth} == '11') set fmonth = 'NOV'
  if (${fmonth} == '12') set fmonth = 'DEC'
  set fday = `echo "${fdate}" | awk '{print substr($0,9,2)}'`
  set fdmy = "${fday}-${fmonth}-${fyear}"
  set year = `date | sed "s/ /\#/g" | awk '{print substr($0,25,4)}'`
  set month = `date | sed "s/ /\#/g" | awk '{print toupper(substr($0,5,3))}'`
  set day = `date | sed "s/ /\#/g" | awk '{print substr($0,9,2)}' | sed "s/\#/0/"`
  set dmy = "${day}-${month}-${year}"
  cd "${dataset_dir}/data"
  echo '\nRun read_scale.pl (aimless.log found).'
  /bin/rm -f "${read_scale_log_file}"
  ${path_read_scale}/read_scale.pl -b XALOC -m Dectris -d CCD -model "Pilatus 6M" -w 1.0 -t 100 -date ${fdmy} -radsource ALBA -p 3 ../autoproc/${ap_num}/aimless.log | tee "${read_scale_log_file}"
  #${path_read_scale}/read_scale.pl -b 17-ID -m Dectris -d CCD -model "Pilatus 6M" -w 1.0 -t 100 -date ${fdmy} -radsource ALBA -p 3 ../autoproc/${ap_num}/aimless.log | tee "${read_scale_log_file}"
else if ("${do_read_scale}" == '0') then
  echo '\nUnable to run read_scale.pl (aimless.log not found).'
else
  echo '\nIntentionally did not run read_scale.pl.'
endif
#
# Tidy up and exit.
STOP:
cd "${start_dir}"
# unset tag
unset ap_num
unset start_dir dataset_dir
unset mincbf numcbf
unset day month year dmy
unset fday fmonth fyear fdmy
unset path_read_scale
unset file do_read_scale
unset process_log_file read_scale_log_file
echo "\n`date`"
exit
