# -*- coding: utf-8 -*-
"""
Created on Wed May 10 12:12:02 2017

@author: mroda
"""
import subprocess, time, os, shlex
from ..common.constants import bl13_GUI_dataproc_dir, bl13_GUI_manual_processdir_ext, bl13_GUI_manual_outlog_extension

def runRemoteProcessing(remoteuser, remoteserver, script2run, program2run, sourcedatadir, filelist2recover, processing_args, procdir, outputlog):
       msg=''
       sourcedatadir = sourcedatadir.rstrip('images')
       print 'runRemoteProcessing: sourcedatadir ',sourcedatadir
       sampledatadir = os.path.basename(os.path.normpath(sourcedatadir))
       msg += ("Source data in %s\n" % sourcedatadir)
       ### TODO: check if these directories exist before executing autoprocess
       #https://www.globalphasing.com/autoproc/manual/appendix1.html
       
       if not os.path.exists(sourcedatadir):
              msg_DirNotFound = 'Image directory %s NOT found!' %sourcedatadir
              msg+=msg_DirNotFound
              print msg_DirNotFound
              return msg
       
       proccommand = 'sbatch --output=%s --error=%s --job-name=%s --open-mode=append %s %s %s %s %s' % (outputlog, outputlog, sampledatadir,
                                                                                                  script2run, program2run, sourcedatadir, procdir, filelist2recover)

       # Here we add the autoproc parameters:
       # This IF-ELSE clause allows to use both a list ['arg','arg','arg'] or a string 'arg arg arg'
       if isinstance(processing_args, basestring):  # This checks both for str and unicode
           proccommand += ' ' + processing_args
       else:
           for argument in processing_args: 
               proccommand += ' ' + argument       
       proccommand += ' >& ' + outputlog
              
       sshcmd = 'ssh %s@%s \"' % (remoteuser,remoteserver) + str(proccommand) + '\"'
       msg += ('sshcmd: %s\n' % sshcmd)
       pssh=subprocess.Popen(shlex.split(sshcmd))
       print 'Done sending job'
       waitcycles=0
       maxwaitcycles=30
       waitcycletime=0.2
       while pssh.poll() is None:                 
           time.sleep(waitcycletime)
           waitcycles+=1
           #print "Wait"
           if waitcycles==maxwaitcycles:               
               all_ok = False
               msg+='crystallography.runRemoteAutoproc: The remote autoproc job took to long to start (%d secs), it has not been sent!!' % (waitcycletime*maxwaitcycles)
               break
       else:           
           all_ok = True
           out, err = pssh.communicate()
           msg += str(out) 

       #print msg
       #pssh.terminate()
       return msg, all_ok
       
       
def getProcessingOutputDirectory(samplerootdir): # samplerootdir is where the image test and dataproc directories are
    # This function returns the directory with highest incremented number in the list of dirs in the samplerootdir
    dataprocdir = os.path.join(samplerootdir,bl13_GUI_dataproc_dir)
    returnnum = -1 # the data processing directory does not exist
    if os.path.isdir(dataprocdir):
        #print 'Find numbered subdir command',("find %s -maxdepth 1 -type d -regex '%s/[0-9][0-9]*' | sed 's^%s/^^' | sort -g | tail -1 " % (dataprocdir,dataprocdir,dataprocdir))
        ap_num_list=subprocess.check_output("find %s -maxdepth 1 -type d -name '*[0-9]' | sed 's^%s/^^'" % (dataprocdir,dataprocdir), shell='True').split('\n')[:-1]
        try:
            for ap_num in ap_num_list:
                try:
                    newnum = int(ap_num.split('_')[-1])
                    #print newnum
                    if newnum > returnnum: returnnum = newnum
                except: 
                    print 'getProcessingOutputDirectory: problem with string ', ap_num
            returnnum = returnnum + 1 # Numbered subdirectories exist, next number is ap_num
        except ValueError:
            returnnum = 0 # the data processing directory already exists, but no numbered subdirectories

    #print returnnum
    return dataprocdir, returnnum
    
def getManualProcessingOutputLogFilename(samplerootdir, imagesweeptemplate): # samplerootdir is where the image test and dataproc directories are
    generaldataprocdir, ap_num = getProcessingOutputDirectory(samplerootdir)
    if ap_num == -1 or ap_num == 0:
        joblogdir = '%s_%s_0' % (imagesweeptemplate, bl13_GUI_manual_processdir_ext)
        joblogfile = '%s_%s' % (imagesweeptemplate, bl13_GUI_manual_outlog_extension)
    elif ap_num > 0:
        joblogdir = '%s_%s_%d' % (imagesweeptemplate, bl13_GUI_manual_processdir_ext, ap_num)
        joblogfile = '%s_%s' % (imagesweeptemplate, bl13_GUI_manual_outlog_extension)

    processlogdir = os.path.join(generaldataprocdir, joblogdir)
    processlogfile = os.path.join(processlogdir, joblogfile)

    return generaldataprocdir, ap_num, processlogdir, processlogfile