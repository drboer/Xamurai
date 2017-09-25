# -*- coding: utf-8 -*-
"""
Created on Wed May 10 12:12:02 2017

@author: mroda
"""
import subprocess, time, os, shlex


def runRemoteProcessing(remoteuser, remoteserver, script2run, program2run, sourcedatadir, filelist2recover, processing_args, default='FALSE'):
       msg=''
       sourcedatadir = sourcedatadir.rstrip('images')
       print 'runRemoteAutoproc: sourcedatadir ',sourcedatadir
       sampledatadir = os.path.basename(os.path.normpath(sourcedatadir))
       msg += ("Source data in %s\n" % sourcedatadir)
       ### TODO: check if these directories exist before executing autoprocess
       #https://www.globalphasing.com/autoproc/manual/appendix1.html
       
       if not os.path.exists(sourcedatadir):
              msg_DirNotFound = 'Image directory %s NOT found!' %sourcedatadir
              msg+=msg_DirNotFound
              print msg_DirNotFound
              return msg
       
       dataproc = '%s/dataproc' % sourcedatadir
       if not os.path.isdir(dataproc):
           os.mkdir(dataproc)
       if default == 'FALSE':
           ap_num=subprocess.check_output("find %s -maxdepth 1 -type d -regex '%s/[0-9][0-9]*' | sed 's^%s/^^' | sort -g | tail -1 " % (dataproc,dataproc,dataproc), shell='True')
           try:
               ap_num = int(ap_num) + 1
           except ValueError:
               ap_num = 0
           procdir =  os.path.join(sourcedatadir,'dataproc',str(ap_num))
           processlogfile= os.path.join(procdir, 'XALOC_manual_processing.log')
           os.mkdir(procdir)
       else:
           procdir =  os.path.join(sourcedatadir,'dataproc','%s_default_processing' % default)
           processlogfile=os.path.join(procdir, '%s_default_processing.log' % default)
           os.mkdir(procdir)

       #CLUSTER COMMAND
       #print 'sbatch --output=%s --error=%s --job-name=%s --open-mode=append %s %s %s' % (processlogfile, processlogfile, sampledatadir, script2run, sourcedatadir, procdir)
       
       proccommand = 'sbatch --output=%s --error=%s --job-name=%s --open-mode=append %s %s %s %s %s' % (processlogfile, processlogfile, sampledatadir,
                                                                                                  script2run, program2run, sourcedatadir, procdir, filelist2recover)

       # Here we add the autoproc parameters:
       # This IF-ELSE clause allows to use both a list ['arg','arg','arg'] or a string 'arg arg arg'
       if isinstance(processing_args, basestring):  # This checks both for str and unicode
           proccommand += ' ' + processing_args
       else:
           for argument in processing_args: 
               proccommand += ' ' + argument       
       proccommand += ' >& ' + processlogfile
              
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