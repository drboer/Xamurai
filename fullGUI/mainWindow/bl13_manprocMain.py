import subprocess, shlex, os, glob
from qtpy.QtCore import QTimer, SIGNAL, Qt
from qtpy.QtGui import QTextCursor, QColor
from qtpy.QtWidgets import QFileDialog
from .bl13_manprocLayout import MainWindowLayout, AutoProcJobWidget
from .bl13_remoteProcessing import runRemoteProcessing, getManualProcessingOutputLogFilename
from ..common.layout_utils import colorize
from ..common.functions import now
from ..common.constants import bl13_GUI_phasing_dir, bl13_GUI_dataproc_dir, bl13_GUI_dir, \
                               bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, \
                               bl13_GUI_cluster_user, bl13_GUI_cluster_server, \
                               bl13_GUI_processing_script, bl13_GUI_searchdepth, \
                               bl13_GUI_autoproc_files2recover, bl13_GUI_xia2_files2recover
import names

# # command to find image directories and time stamp
#find . -type d -name "images" -printf '%c %p\n'

class MainWindow(MainWindowLayout):
    def __init__(self, app, *args):
        
        print 'Starting MainWindowLayout init'
        MainWindowLayout.__init__(self, app)
        print 'Returned from MainWindowLayout init'
        
        # Variables
        self.app = app
        self.datakeys = ['name', 'processed', 'approved', 'solved']
        # keys are the directory names, the index points to the data list
        self.datasetMasterNameList = {}
        #        Data list contains info on processing approval etc
        self.datasetMasterDataList = []
        #        Logs list contains the list of processing log files
        self.datasetMasterLogsList = []
        #        Sum list contains the lists of phaser summary files
        self.datasetMasterSumList = []
        self.latestproclogfile = ''
        self.latestanalysislogfile = ''
        
    # UPDATE internal lists of datasets and files
    def changeDirectory(self):
        path = str(QFileDialog.getExistingDirectory(self,"Beamtime data directory",self.directory.text()).replace('/storagebls',''))
        if path not in [None, '']:
            self.displayInfo('Changing root directory: ' + path, prnt=True)
            self.directory.setText( str(path) )
            # Now update data dir list
            self.scanRootDirectory(True)
            
    def findProcessingLogFiles(self, path=''):
        """ Searches for processing log files in a sample root path """
        print 'findProcessingLogFiles:'
        latestlogfile = None
        # Get information
        if path == '':
            path = str(self.datasetList.currentText())
        if path == '':
            print 'findProcessingLogFiles: empty path, returning'
            self.textOutput.setPlainText('')
            return ''
        print 'Looking for process files in %s' % path
        self.displayInfo('Looking for process files in %s' % path, prnt=True)
        newlogsfound = False # backward compatibility with older XALOC paths (when processing files were still in images)
        data_set_index = self.datasetMasterNameList[path]
        # Get approved and other processing files
        log_list = []
        analysis_dir = os.path.join(str(path), bl13_GUI_phasing_dir)
        if os.path.isdir(analysis_dir):
            for name_file in os.listdir(analysis_dir): 
                if name_file == "currently_approved_processing.log":
                    log_file = os.path.join(analysis_dir, name_file)
                    log_list.append(log_file)
                    latestlogfile = log_file
                    break
        if len(log_list) > 0:
            self.displayInfo('Found approved log files', prnt=True)
        # Get older processing log files
        manual_log_file = os.path.join(str(path), 'manual_processing.log')
        if os.path.isfile(manual_log_file): 
            latestlogfile = manual_log_file
            log_list.append(manual_log_file)
        # Look for newer processing log files in dataproc directories
        dataproc_dir = os.path.join(str(path), bl13_GUI_dataproc_dir)
        # To find the highest index of hand processed data
        hid = -1
        if os.path.isdir(dataproc_dir):
            #print 'dataproc_dir %s' % dataproc_dir
            for dir_file in sorted(os.listdir(dataproc_dir)):
                if os.path.isdir(os.path.join(dataproc_dir, dir_file)):
                    #print 'list of files: %s\n' % os.listdir(os.path.join(dataproc_dir, dir_file))
                    #for name_file in os.listdir(os.path.join(dataproc_dir, dir_file)):
                    #    if name_file.endswith("processing.log"):
                    os.chdir(os.path.join(dataproc_dir, dir_file))
                    for logfile in glob.glob('*processing.log'):
                            #log_list.append(os.path.join(dataproc_dir, dir_file, name_file))
                            fulllogname = os.path.join(dataproc_dir, dir_file, logfile)
                            print 'Found log file %s' % fulllogname
                            log_list.append(fulllogname)
                            if not 'manual' in logfile:
                                newlogsfound = True # if newer type default logs are found, no need to look later for older logs
                                latestlogfile = os.path.join(dataproc_dir, dir_file, logfile)
                            else:
                                # Identify latest manual processing
                                manrunnumber = dir_file.split('_')[-1]
                                if manrunnumber.isdigit() and int(manrunnumber)>hid: 
                                    hid = int(manrunnumber)
                                    latestlogfile = os.path.join(dataproc_dir, dir_file, logfile)
                                #break
        #print 'The manual processing file with highest index is ', hid
        if newlogsfound:
            self.displayInfo('Found processing files', prnt=True)
        # Get default processing file from older paths
        images_dir = os.path.join(str(path), 'images')
        print 'The image dir is ', images_dir
        if not newlogsfound:
          print 'No new default processing logs found, checking for old default processing data files in ',os.path.join(dataproc_dir, images_dir)
          os.chdir(os.path.join(dataproc_dir, images_dir))
          for name_file in glob.glob('*_defaultprocessing.log'):
          #for name_file in os.listdir(os.path.join(images_dir)): # this is very, very slow
          #  if name_file.endswith("_defaultprocessing.log"):
                default_log = os.path.join(images_dir, name_file)
                log_list.append(default_log)
                self.displayInfo('Found old default processing file', prnt=True)
                if latestlogfile == None:
                        latestlogfile = default_log
                print latestlogfile
                break
        if len(log_list) == 0:
            err_msg = 'No default processing files found in images nor manual processing in data dir'
            self.processLogFile.setText(err_msg)
            self.textOutput.setPlainText(err_msg)
        self.datasetMasterLogsList.insert(data_set_index, log_list)
        return latestlogfile, log_list
        
    def findAnalysisLogFiles(self, path=''):
        # Includes Phaser MR and Arcimboldo files
        ## Get information ##
        if path == '':
            path = str(self.datasetList.currentText())
        if path == '':
            self.textOutput.setPlainText('')
            return
        data_set_index = self.datasetMasterNameList[ path.split(' ')[0] ]
        sum_files = []
        phasing_path = os.path.join(path, bl13_GUI_phasing_dir)
        latestlogfile = ''
        idir=-1
        if not os.path.isdir(phasing_path):
            self.displayInfo('No log files exist yet (%s directory not found)' % bl13_GUI_phasing_dir, prnt=True)
        else:
            # Phaser MR
            self.displayInfo('Looking for phaser log files in %s' % phasing_path, prnt=True)
            ## Get all summary files ##
            for dir_name in os.listdir(phasing_path):
                if dir_name.endswith('_phaserMR'):
                    for dir_num in os.listdir(os.path.join(phasing_path, dir_name)):
                        if dir_num.isdigit() and os.path.isdir(os.path.join(phasing_path, dir_name, dir_num)):
                            log_file = os.path.join(phasing_path, dir_name, dir_num, "autoMRphaser.log")
                            if os.path.isfile(log_file):
                                sum_files.append(log_file)
                                if dir_num > idir: 
                                    idir = dir_num
                                    latestlogfile = log_file
            # Arcimboldo
            self.displayInfo('Looking for arcimboldo log files in %s' % phasing_path, prnt=True)
            ## Get all summary files ##
            for dir_name in os.listdir(phasing_path):
                if dir_name.endswith('_arcimboldo'):
                    for dir_num in os.listdir(os.path.join(phasing_path, dir_name)):
                        if dir_num.isdigit() and os.path.isdir(os.path.join(phasing_path, dir_name, dir_num)):
                            count = 0
                            for dir_file in os.listdir(os.path.join(phasing_path, dir_name, dir_num)):
                                if count == 2:
                                    break
                                if dir_file.endswith(".html") or dir_file == "terminal_output.log":
                                    log_file = os.path.join(phasing_path, dir_name, dir_num, dir_file)
                                    if os.path.isfile(log_file):
                                        sum_files.append(log_file)
                                        count += 1
                                        if dir_num > idir: 
                                            idir = dir_num
                                            latestlogfile = log_file
        self.datasetMasterSumList.insert(data_set_index, sum_files)
        return latestlogfile, sum_files
                                        
    def findAllLogFiles(self):
        print 'findAllLogFiles'
        path = str(self.datasetList.currentText()).split(' ')[0]
        if not os.path.isdir(path):
            print 'findAllLogFiles: the given path is not a directory or doesnt exist'
            print '  path: %s' %path
            return

        data_set_index = self.datasetMasterNameList[path]
        print self.datasetMasterNameList
        print path, data_set_index
        latestproclogfile, log_list = self.findProcessingLogFiles(path)
        #print self.latestproclogfile
        latestanalysislogfile, log_list = self.findAnalysisLogFiles(path)
        return latestproclogfile, latestanalysislogfile

    def setTimerForLogFile(self):
        print 'setTimerForLogFile'
        QTimer.singleShot(10*1000, self.selectDataSet)

    def setStageFromData(self, path):
        state = self.get_state(self.datasetMasterDataList[self.datasetMasterNameList[path]])
        self.datasetSelCB.setCurrentIndex(state)
        
    def repopulateLogFilePullDown(self):
        print 'repopulateLogFilePullDown'
        stage = self.datasetSelCB.currentIndex()
        if stage == 0: #  all files
            path = str(self.datasetList.currentText()).split()[0]
            self.latestproclogfile, self.latestanalysislogfile = self.findAllLogFiles()
            latestlogfile = self.latestanalysislogfile
            if not os.path.isfile(self.latestanalysislogfile): latestlogfile = self.latestproclogfile
            self.repopulateProcessLogFilePullDown()
            self.repopulateAnalysisFilePullDown(False)
        elif stage == 1: # images to mtz stage
            latestlogfile, log_list = self.findProcessingLogFiles()
            self.repopulateProcessLogFilePullDown()
        elif stage == 2: # analysis stage
            latestlogfile, log_list = self.findAnalysisLogFiles()
            self.repopulateAnalysisFilePullDown()
        elif stage == 3:
            pass
        return latestlogfile
        
    def repopulateProcessLogFilePullDown(self, clear = True):
        print 'repopulateProcessLogFilePullDown'
        # Repopulate the log file pulldown when changing dataset/sample
        path = str(self.datasetList.currentText()).split(' ')[0]
        if path == '' or path.startswith('<'):
            self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
            self.logsList.clear()
            self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
            return
        self.useImageSpec.setCheckable(False)
        self.imgName.setText(path.split("/")[-2])
        self.useImageSpec.setCheckable(True)
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        if clear: self.logsList.clear()
        for log in self.datasetMasterLogsList[self.datasetMasterNameList[path]]:
            self.logsList.addItem(log)
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        
    def repopulateAnalysisFilePullDown(self, clear = True):
        print 'repopulateAnalysisFilePullDown'
        path = str(self.datasetList.currentText())
        if path == '' or path.startswith('<'):
            self.logsList.clear()
            return
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        if clear: self.logsList.clear()
        index = self.datasetMasterNameList[ path.split(' ')[0] ]
        # Approved processing log file
        log_file = os.path.join(path, bl13_GUI_phasing_dir, "currently_approved_processing.log")
        self.logsList.addItem(log_file + ' (Approved processing log file)')
        # RB 20171001: following line is broken after changing to qtpy
        #self.logsList.setItemData(0, QColor(Qt.gray), Qt.TextColorRole)
        # All sum, log files, from phaser, arcimboldo...
        if len(self.datasetMasterSumList) > 0:            
            for item in self.datasetMasterSumList[index]:
                self.logsList.addItem(item)
            self.logsList.setCurrentIndex(self.logsList.count()-1)
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        
        # Prepare molecular replacement parameters
        mtz_file = os.path.join(path, bl13_GUI_phasing_dir, "currently_approved_truncate-unique.mtz")
        self.auto_molrep.mtz_file_display.setText(mtz_file)
        self.auto_molrep.update_mtz_info()
        self.arcimboldo.mtz_file_display.setText(mtz_file)
        self.arcimboldo.update_mtz_info()
        dirname = self.datasetMasterDataList[index]['name']
        self.auto_molrep.work_dir = os.path.join(dirname, bl13_GUI_phasing_dir)
        self.auto_molrep.file_root_edit.setText(str(dirname.split("/")[-2]))
        self.arcimboldo.work_dir = os.path.join(dirname, bl13_GUI_phasing_dir)
        self.arcimboldo.root_edit.setText(str(dirname.split("/")[-2]))

    def SelectStage(self):
        ## Update buttons and layout ##
        print 'SelectStage'
        stage = self.datasetSelCB.currentIndex()
        if stage == 0:
            self.backPB.setText('-')
            self.backPB.setEnabled(False)
            self.approvePB.setText('-') # hide instead of adding bad text
            self.approvePB.hide()
            self.approvePB.setEnabled(False)
            self.refreshLogPB.setEnabled(False)
            self.refresh_logs.setEnabled(False)
            self.textOutput.setHtml(self.wel_txt)
            self.disconnect(self.logsListPB, SIGNAL('clicked()'), self.coot_selection)
            self.logsListPB.hide()
        elif stage == 1:
            self.backPB.setText('-')
            self.backPB.setEnabled(False)
            self.approvePB.setText('Accept ' + names.stage1)
            self.approvePB.show()
            self.approvePB.setEnabled(True)
            self.refreshLogPB.setEnabled(True)
            self.refresh_logs.setEnabled(True)
            self.disconnect(self.logsListPB, SIGNAL('clicked()'), self.coot_selection)
            self.logsListPB.hide()
        elif stage == 2:
            self.backPB.setText('Back to ' + names.stage1)
            self.backPB.setEnabled(True)
            self.approvePB.setText('Accept ' + names.stage2)
            self.approvePB.show()
            self.approvePB.setEnabled(True)
            self.refreshLogPB.setEnabled(True)
            self.refresh_logs.setEnabled(True)
            self.logsListPB.setText('Coot results')    
            self.connect(self.logsListPB, SIGNAL('clicked()'), self.coot_selection)
            self.logsListPB.show()
        elif stage == 3:
            self.backPB.setText('Back to ' + names.stage1)
            self.backPB.setEnabled(True)
            self.approvePB.setText('-')
            self.approvePB.hide()
            self.approvePB.setEnabled(False)
            self.refreshLogPB.setEnabled(False)
            self.refresh_logs.setEnabled(False)
            self.disconnect(self.logsListPB, SIGNAL('clicked()'), self.coot_selection)
            self.logsListPB.hide()
        # Change widget to display depending on selection
        self.change_stack()

        datasetindex = self.datasetList.currentIndex()
        self.repopulateDataSetList()
        self.datasetList.setCurrentIndex(0)
        if datasetindex == self.datasetList.currentIndex(): self.selectDataSet()
        
    def repopulateDataSetList(self): 
        # self.logsList log files selection pull down menu
        # datasetSelCB is stage selection button (images to mtz, phasing, etc)
        # stage is current index of datasetSelCB
        print 'repopulateDataSetList'
        self.textOutput.setText('')
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.logsList.clear()
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        
        stage = self.datasetSelCB.currentIndex()
        
        if stage == 0:  # If the user has selected the ALL tab
            self.disconnect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
            self.datasetList.clear()
            self.datasetList.insertItem(0, '<Select dataset path>')
            count = 1
            for key in self.datasetMasterNameList:
                data_stage = self.get_state(self.datasetMasterDataList[self.datasetMasterNameList[key]])
                (text, color) = self.state_string(data_stage)
                self.datasetList.insertItem(count, key + ' ' + text)
                # RB 20171001: following line is broken after changing to qtpy
                #self.datasetList.setItemData(count, color, Qt.TextColorRole)
                count += 1
            self.connect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
            return
        
        print 'repopulateDataSetList: after stage settings'
        selind = -1
        # print 'nr of dirs %d' % len(self.datasetMasterNameList)
        prevtext = self.datasetList.currentText()
        var = str(prevtext).split()
        if len(var) > 1:
            prevtext = var[0]
        if prevtext == '' or '<Select dataset path>':
            selind = 0
        self.disconnect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
        self.datasetList.clear()
        # print 'repopulateDataSetList: Adding datasets that are; ', str(self.datasetSelCB.currentText()).lower()
        # print 'From ', self.datasetMasterNameList
        # print 'Current selection: ', prevtext
        for key in self.datasetMasterNameList: 
            # print masteritem
            # cbname = masteritem['name']
            addit = False
            index = self.datasetMasterNameList[key]
            # print index, key, self.datasetMasterDataList[index]
            # print 'seleting ', self.datasetSelCB.currentText()
            data_state = self.get_state(self.datasetMasterDataList[index])
            if data_state == stage or stage == 0:
                addit = True
            if addit: 
                # print 'Adding ', key
                self.datasetList.addItem(key)
            if key == prevtext:
                if addit: 
                    selind = self.datasetList.findText(key)
                    self.datasetList.setCurrentIndex(selind)
                else: 
                    selind = 0
                    self.datasetList.setCurrentIndex(selind)
        if selind == -1:
            self.processLogFile.setText('No default processing files found in images nor manual processing in data dir')
            self.textOutput.setPlainText('No default processing files found in images nor manual processing in data dir')
        if len(self.datasetList) == 0:
            self.datasetList.insertItem(0, '<Select a stage containing at least one data set>')
        self.connect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)

    def selectDataSet(self):
        print 'selectDataSet'
        
        latestlogfile = self.repopulateLogFilePullDown()
        print latestlogfile
        self.findSelectLogFile(latestlogfile)
            
    def selectLogFile(self):
        # Given aprocessing job selection (ie the entry of the logs list), the output file is retrieved and displayed
        print 'selectLogFile', self.latestproclogfile, str(self.logsList.currentText())
        stage = self.datasetSelCB.currentIndex()
        log_file = str(self.logsList.currentText())
        print self.logsList.currentText()
        if self.logsList.currentText() == '':
            print 'No log file selected'
            self.textOutput.setPlainText('No log file selected')
        else:
            if stage == 0 or stage == 1 or (stage==2 and self.logsList.currentIndex() == 0):
                self.processLogFile.setText(log_file)
                file2display = str(self.logsList.currentText())
                print 'Showing processing file: %s' % log_file
                self.updateProcessingInfo(self.logsList.currentText())
                html_summary = "/".join(file2display.split("/")[:-1] + ["summary.html"])
                print 'Looking for summary.html: %s' % html_summary
                if os.path.isfile(html_summary):
                    file2display = html_summary
            elif stage == 2:
                file2display = str(self.logsList.currentText())

            if os.path.isfile(file2display):
                with open(file2display,'r') as log:
                    text = log.read()
                if file2display.endswith(".html") or file2display.endswith("autoMRphaser.log"):
                    cur_dir = os.getcwd()
                    proc_dir = "/".join(file2display.split("/")[:-1])
                    os.chdir(proc_dir)
                    self.textOutput.setHtml(text)
                else:
                    self.textOutput.setText(text)
                self.scroll_to_end()
            else:
                self.textOutput.setText('File ' + log_file + ' doesn\'t exist')

    def findSelectLogFile(self,logfilenamepath):
        print 'findSelectLogFile', self.logsList.currentIndex()
        currentindex = self.logsList.currentIndex()
        logindex = self.logsList.findText(logfilenamepath)
        print self.latestproclogfile,'found at index',logindex
        self.logsList.setCurrentIndex(logindex)
        if currentindex == logindex: self.selectLogFile() # force loading the log file if index didnt change

    def refreshLogFiles(self):
        """ Updates the log file list, but doesnt change the log file index """
        current_log = self.logsList.currentText()
        latestlogfile = self.repopulateLogFilePullDown()
        logindex = self.logsList.findText(current_log.split(' ')[0])
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.logsList.setCurrentIndex(logindex)
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        
    def updateProcessingInfo(self, locallogfile):
        # This function finds the processing file and extracts parameters from it
        # it is only meant for the images to mtz stage 
        print 'updateProcessingInfo'
        # read contents of log file extract space group info etc from output file
        text=open(locallogfile).read()
        textlines = text.splitlines()
        self.displayInfo('Log file contents updated')
        for line in textlines:
            srchstr =  'Cell parameters ......................................'
            if srchstr in line:
                cellpars = line.split(srchstr)[1].split()
                #print 'cellpars %s' %str(cellpars)
                if len(cellpars) == 6:
                    self.useCell.setCheckable(False)
                    self.cella.setValue(float(cellpars[0]))
                    self.cellb.setValue(float(cellpars[1]))
                    self.cellc.setValue(float(cellpars[2]))
                    self.cellalpha.setValue(float(cellpars[3]))
                    self.cellbeta.setValue(float(cellpars[4]))
                    self.cellgamma.setValue(float(cellpars[5]))
                    self.useCell.setCheckable(True)
            srchstr = 'Resolution ...........................................'
            if srchstr in line:
                resol = line.split(srchstr)[1].split()
                if len(resol) == 4:
                    self.resLimitLow.setValue(float(resol[0]))
                    self.resLimitHigh.setValue(float(resol[2]))
            srchstr = 'Spacegroup name ......................................'
            if srchstr in line:
                self.useSG.setCheckable(False)
                self.SG.setText( line.split(srchstr)[1].lstrip().rstrip() )
                self.useSG.setCheckable(True)

    # MAIN (autoproc)
    def runManProc(self):
        print 'runManProc'
        self.setEnabled(False)

        # Find source data dir
        data_dir_root = str(self.datasetList.currentText()).replace('/storagebls','')
        data_dir = os.path.join(data_dir_root,'images') # runRemoteAutoproc expects images in the file, so add it
        sampleroot = os.path.basename( os.path.normpath( str(self.datasetList.currentText()) ) )
        if str(self.procprogSelCB.currentText()).split(' ')[0] == 'autoproc':
            proc_parameters = self.getAutoprocParameters(data_dir)
            program2run = 'process'
            filelist2recover = bl13_GUI_autoproc_files2recover
        elif str(self.procprogSelCB.currentText()).split(' ')[0] == 'xia2':
            proc_parameters = self.getXIA2Parameters(data_dir)
            program2run = 'xia2'
            filelist2recover = bl13_GUI_xia2_files2recover
        # TODO: Change the parameters when inverse beam collection is detected

        print "Datadir name", data_dir
        print "proc_parameters", proc_parameters

        # Calculate the number of this job/launch
        name = str(self.datasetList.currentText()).split("/")[-2]
        print "Dataset list name", str(self.datasetList.currentText())
        print "Name of this dataset",name
        print 'Sample root : ', sampleroot
        
        genprocdir, num, jobprocdir, joblogfile = getManualProcessingOutputLogFilename(data_dir_root, sampleroot)
        print genprocdir, num, jobprocdir, joblogfile
        if not os.path.exists(os.path.join(str(self.datasetList.currentText()),bl13_GUI_dataproc_dir)):
            os.mkdir(os.path.join(str(self.datasetList.currentText()),bl13_GUI_dataproc_dir))
        try:     
            os.mkdir(jobprocdir)
        except:
            raise Exception('cant make processing dir')
        
        # Display job information on screen
        jobWidget = AutoProcJobWidget(sampleroot, num, jobprocdir)
        self.jobs_display.layout().addWidget(jobWidget)

        ret, all_ok = runRemoteProcessing(bl13_GUI_cluster_user, bl13_GUI_cluster_server,
                                bl13_GUI_processing_script, program2run, data_dir, filelist2recover, proc_parameters, jobprocdir, joblogfile)
        #print ret
        all_ok = True
        
        # Update GUI and job
        if all_ok:
            jobWidget.set_status("Sent")
        else:
            jobWidget.set_status("Error")
        # self.processLogFile.setText(logfile)
        # RB 20161115
        self.setTimerForLogFile()
        self.setEnabled(True)
        return
        
    def getAutoprocParameters(self, data_dir):
        print 'getAutoprocParameters'
        # 1. Set parameters
        autoproc_parameters = ['StopIfSubdirExists=no', 'BeamCentreFrom=header:x,y',
                               'autoPROC_TwoThetaAxis=\\"-1 0 0\\"']
        if self.useCell.isChecked():
            autoproc_parameters.append('cell=\\"%s %s %s %s %s %s\\"' % (self.cella.value(), self.cellb.value(),
                                                                        self.cellc.value(), self.cellalpha.value(),
                                                                        self.cellbeta.value(), self.cellgamma.value()))
        if self.useSG.isChecked():
            autoproc_parameters.append('symm=\\"%s\\"' % str(self.SG.text()).lstrip().rstrip())
        if self.useMinimalSpotSearch.isChecked():
            autoproc_parameters.append('XdsSpotSearchMinNumSpotsPerImage=\\"0\\"')
        if self.useResolLimits.isChecked():
            autoproc_parameters.append('-R %.2f %.2f' % (self.resLimitLow.value(), self.resLimitHigh.value()))
        else:
            autoproc_parameters.append('-R 50.0 0.0')
        # MR: 2017 05 05
        # Cutoff parameters added
        if self.useRmerge.isChecked():
            # autoproc_parameters.append('ScaleAnaRmergeCut_123=\\"99.9:99.9 %s:%s %s:%s %s:%s\\"' % (self.Rmerge_low.value(), self.Rmerge_up.value(),self.Rmerge_low.value(), self.Rmerge_up.value(),self.Rmerge_low.value(), self.Rmerge_up.value()))
            autoproc_parameters.append('ScaleAnaRmergeCut_123=\\"%s:%s\\"' % (self.Rmerge_cut.value(), self.Rmerge_cut.value()))
        if self.useIoverSig.isChecked():
            autoproc_parameters.append('ScaleAnaISigmaCut_123=\\"%s:%s\\"' % (self.IoverSig_cut.value(), self.IoverSig_cut.value()))
        if self.useCcHalf.isChecked():
            autoproc_parameters.append('ScaleAnaCChalfCut_123=\\"%s:%s\\"' % (self.CcHalf_cut.value(), self.CcHalf_cut.value()))

        
        # MR: 2017 05 05
        # Added image specification
        if self.useImageSpec.isChecked():
            autoproc_parameters.append('-Id \\"Xamurai_%s,%s,%s_####.cbf,%d,%d\\"' % (self.imgName.text(), data_dir, self.imgName.text(),
                                                                                      self.first_image.value(), self.last_image.value()))
        else:
            autoproc_parameters.append('-I \\"' + data_dir + '\\"')

        return autoproc_parameters
        

    def getXIA2Parameters(self, data_dir):
        print 'getXIA2Parameters'

        xia2_parameters = ['pipeline=3d']
        # image specification
        if self.useImageSpec.isChecked():
            xia2_parameters.append('image=%s_0001.cbf:%d:%d' % ( os.path.join(data_dir, self.imgName.text()), self.first_image.value(), self.last_image.value() ) )
        else:
            xia2_parameters.append(data_dir)

        if self.useCell.isChecked():
            xia2_parameters.append('unit_cell=%s, %s, %s, %s, %s, %s' % (self.cella.value(), self.cellb.value(),
                                                                        self.cellc.value(), self.cellalpha.value(),
                                                                        self.cellbeta.value(), self.cellgamma.value()))
        if self.useSG.isChecked():
            xia2_parameters.append('space_group=\\\'%s\\\'' % str(self.SG.text()).lstrip().rstrip() )
        #if self.useMinimalSpotSearch.isChecked():
        #    xia2_parameters.append('XdsSpotSearchMinNumSpotsPerImage=\\"0\\"')
        if self.useSmallMolecule.isChecked():
            xia2_parameters.append('small_molecule=true')
        if self.useResolLimits.isChecked():
            xia2_parameters.append('d_max=%.2f' % self.resLimitLow.value())
            xia2_parameters.append('d_min=%.2f' % self.resLimitHigh.value())
        else:
            xia2_parameters.append('d_min=None')
            xia2_parameters.append('d_max=None')

        # Cutoff parameters: the XALOC default is to only cut off based on cchalf, unless otherwise specified. Unmerged I/sigma is not used
        xia2_parameters.append('isigma=0.0001')
        cchalfstr = '' 
        #if self.useRmerge.isChecked():
        #    xia2_parameters.append('ScaleAnaRmergeCut_123=\\"%s:%s\\"' % (self.Rmerge_low.value(), self.Rmerge_low.value()))
        if self.useIoverSig.isChecked():
            xia2_parameters.append('misigma=%s' % self.IoverSig_cut.value() )
            cchalfstr = 'cc_half=0.0001'
        else:
            xia2_parameters.append('misigma=0.0001')
        if self.useCcHalf.isChecked():
            cchalfstr ='cc_half=%.3f' % self.CcHalf_cut.value()

        if (cchalfstr): xia2_parameters.append(cchalfstr)
            
        return xia2_parameters
        
    def procprogChanged(self):
        if str(self.procprogSelCB.currentText()).split(' ')[0] == 'autoproc':
            self.useSmallMolecule.setEnabled(False)
            self.useMinimalSpotSearch.setEnabled(True)
            self.useRmerge.setEnabled(True)
            self.Rmerge_cut.setEnabled(True)
        elif str(self.procprogSelCB.currentText()).split(' ')[0] == 'xia2':
            self.useSmallMolecule.setEnabled(True)
            self.useMinimalSpotSearch.setEnabled(False)
            self.useRmerge.setEnabled(False)
            self.Rmerge_cut.setEnabled(False)

    # ACCEPT/BACK
    def setStatusBack(self):
        print 'setStatusBack'
        current_dir = str(self.datasetList.currentText())
        if current_dir == '' or current_dir.startswith('<'):
            return
        ## Set the state one phase back ##
        curindex = self.datasetMasterNameList[current_dir]
        if self.datasetMasterDataList[curindex]['solved'] == 'Solved':
            self.datasetMasterDataList[curindex]['solved'] = 'Not_solved'
            self.writeDataInfoFile(self.datasetList.currentText(), self.datasetMasterDataList[curindex])
            self.datasetSelCB.setCurrentIndex(2)
        elif self.datasetMasterDataList[curindex]['approved'] == 'Approved':
            self.datasetMasterDataList[curindex]['approved'] = 'Not_approved'
            self.writeDataInfoFile(self.datasetList.currentText(), self.datasetMasterDataList[curindex])
            self.datasetSelCB.setCurrentIndex(1)
        return
        
    def setStatusForward(self):
        print 'setStatusForward'
        current_dir = str(self.datasetList.currentText())
        if current_dir == '' or current_dir.startswith('<'):
            return
        ## Set the state one phase forward ##
        cur_index = self.datasetMasterNameList[current_dir]
        print 'setStatusForward %s %s' % (current_dir, cur_index)
        if self.datasetMasterDataList[cur_index]['approved'] == 'Not_approved':
            # Make a link to the approved .log file
            log_file = str(self.logsList.currentText())
            print 'setStatusForward %s' % (log_file)
            if log_file.endswith("currently_approved_processing.log"):  # Read the link in case you approve with the link
                log_file = os.readlink(log_file)
            analysis_dir = os.path.join(current_dir, bl13_GUI_phasing_dir)
            if not os.path.isdir(analysis_dir):
                os.system("mkdir " + analysis_dir)
            log_link = os.path.join(analysis_dir, "currently_approved_processing.log")
            # and to the .mtz file
            mtz_file = 'not-listed'
            mtz_link = os.path.join(analysis_dir, "currently_approved_truncate-unique.mtz")
            #log_file_name = log_file.split("/")[-1]
            (data_proc_dir, log_file_name) = os.path.split(log_file)
            # 20161214 RB: the output filename is defined in runRemoteAutoproc as XALOC_manual_processing.log. 
            # TODO: pass the output file as an argument to runRemoteAutoproc
            #if log_file_name.startswith("manual_processing_"):
                # Expected: within dataproc, an output file starting with manual_processing_ followed by a processsing number
            if log_file_name == "XALOC_manual_processing.log":  
                # Expected: within dataproc, an output file named XALOC_manual_processing.log
                #num = log_file_name.replace("manual_processing_", "")[0]
                #mtz_file = os.path.join(current_dir, bl13_GUI_dataproc_dir, num, "truncate-unique.mtz")
                mtz_file = os.path.join(data_proc_dir, "truncate-unique.mtz")
            elif log_file_name.startswith("manual_processing"):  # Older
                mtz_file = os.path.join(current_dir, "data", "truncate-unique.mtz")
            elif "manual_processing" in log_file:  # Added 20171019
                logcontent = open(log_file, 'r').read()
                if 'xia2' in logcontent: 
                    mtz_file = os.path.join(data_proc_dir, "DataFiles", "AUTOMATIC_DEFAULT_free.mtz")
                elif 'autoPROC' in logcontent:
                    mtz_file = os.path.join(data_proc_dir, "truncate-unique.mtz")
            elif log_file_name.startswith("autoproc_"):
                num = log_file.split("/")[-2]
                mtz_file = os.path.join(current_dir, bl13_GUI_dataproc_dir, num, "truncate-unique.mtz")
            elif '_default_processing' in log_file:
                mtz_file = os.path.join(os.path.dirname(log_file),"truncate-unique.mtz")
            print 'setStatusForward mtz file %s' % (mtz_file)
            if not os.path.isfile(mtz_file):
                self.displayError("You are trying to approve a processing without .mtz (" + mtz_file + ") or .log (" +
                                  log_file + "). Maybe one of them has been misplaced.")
                return
            # If no Error, link and set status forward
            os.system("ln -s -f " + log_file + " " + log_link)
            os.system("ln -s -f " + mtz_file + " " + mtz_link)
            self.displayInfo('Data set approved with ' + log_file)
            self.datasetMasterDataList[cur_index]['approved'] = 'Approved'
            self.writeDataInfoFile(self.datasetList.currentText(),self.datasetMasterDataList[cur_index])
            print 'setStatusForward writeDataInfoFile'
            self.datasetSelCB.setCurrentIndex(2)
            print 'setStatusForward datasetSelCB'
        elif self.datasetMasterDataList[cur_index]['solved'] == 'Not_solved':
            self.datasetMasterDataList[cur_index]['solved'] = 'Solved'
            self.writeDataInfoFile(self.datasetList.currentText(),self.datasetMasterDataList[cur_index])
            self.datasetSelCB.setCurrentIndex(3)
        return

    # .dataInfo related methods
    def scanRootDirectory(self, request=False):
        """ repopulates the dataset pulldown """
        print 'scanRootDirectory: Finding images directories in root %s' % self.directory.text()
        if os.path.isdir(self.directory.text()): 
            #prevtext = self.datasetList.currentText()
            #print prevind
            shcom = 'find %s ' % self.directory.text()
            #shcom = shcom + '-maxdepth 3 -type d -name "images" -printf \'%p %c\\n\'' 
            shcom = shcom + '-maxdepth %d -type d -name "images"' % bl13_GUI_searchdepth# RB 20161118: make it faster
            #print 'shell command  is %s' % shcom
            imageslist = subprocess.Popen(shcom, shell=True, stdout=subprocess.PIPE).stdout.read().splitlines()
            #print imageslist
            if len(imageslist) != len(self.datasetMasterNameList) or request:
                self.displayInfo('New data directories found')
                self.datasetMasterNameList = {}
                self.datasetMasterDataList = []
                nimdir = 0
                for imdir in imageslist:
                    #cbname = self.extractPrefix(imdir)
                    #cbname = (imdir.split()[0]).rstrip('images')
                    cbname = imdir.rstrip('images')
                    #print cbname
                    (thisdata, need_to_write) = self.readDataInfoFile(cbname)
                    #print thisdata
                    self.datasetMasterNameList[cbname] = nimdir
                    self.datasetMasterDataList.append(thisdata)
                    self.latestlogfile, log_list = self.findProcessingLogFiles(cbname)
                    self.datasetMasterLogsList.insert(nimdir, log_list)
                    self.latestlogfile, log_list = self.findAnalysisLogFiles(cbname)
                    self.datasetMasterSumList.insert(nimdir, sorted(log_list))
                    if need_to_write:
                        self.writeDataInfoFile(cbname,thisdata)
                    nimdir = nimdir + 1
                # Now reset the selection list
                self.repopulateDataSetList()
        else: 
            print 'Not a valid directory, ignored'
    
    def readDataInfoFile(self, indir):
        infofile = os.path.join(indir,'.dataInfo')
        self.displayInfo('Looking for info file %s' % infofile, prnt=True) 
        need_to_write = True
        inkey = [indir, 'Not_processed', 'Not_approved', 'Not_solved']
        intup = dict(zip(self.datakeys,inkey))
        if os.path.isfile(infofile):
            infolines = open(infofile).readlines()
            count = 0
            for line in infolines:
                cols = line.split()
                if cols[0] in intup:
                    intup[cols[0]] = cols[1]
                    count += 1
            if count == len(inkey):
                need_to_write = False
        return intup, need_to_write

    def writeDataInfoFile(self, indir, intup):
        ### indir is the directory on top of the images and test directories
        infofile = os.path.join(str(indir),'.dataInfo')
        #intupd = dict(intup)
        print ' Writing to file %s' % infofile
        print intup
        fw = open(infofile, 'w')
        for ikey in intup:
            #print 'key', ikey
            print ' Writing key ',ikey,' value ',intup[ikey]
            fw.write('%s %s\n' %(ikey,intup[ikey]))

    def genKeysFromDir(self, dirname):
        return ['name', str('%s_proc' % dirname), str('%s_appr' % dirname) ]

    # Change PROCESSING parameters
    def toggleSG(self):
        if not self.useSG.isChecked():
            self.SG.setText('')
            self.useSG.setChecked(False)

    def changeSG(self):
        #print 'changeSG'
        self.useSG.setChecked(True)

    def resolChange(self):
        self.useResolLimits.setChecked(True)

    def cellChange(self):
        self.useCell.setChecked(True)

    def useRmergeCheck(self):
        self.useRmerge.setChecked(True)
        
    def useCcHalfCheck(self):
        self.useCcHalf.setChecked(True)
        
    def useIoverSigCheck(self):
        self.useIoverSig.setChecked(True)

    def useImageSpecCheck(self):
        self.useImageSpec.setChecked(True)
    
    # INFO
    def displayError(self, arg, prnt=False):
        content = colorize("Error: " + str(arg), "Red")
        self.displayInfo(content, prnt)

    def displayWarning(self, arg, prnt=False):
        content = colorize("Warning: " + str(arg), "Navy")
        self.displayInfo(content, prnt)

    def displayInfo(self, arg, prnt=False):
        content = now() + "> " + arg
        self.info_display.moveCursor(QTextCursor.End)
        self.info_display.insertPlainText("\n")
        self.info_display.insertHtml(content)
        #self.info_display.verticalScrollBar().setValue(self.info_display.verticalScrollBar().maximum())
        self.info_display.moveCursor(QTextCursor.End)
        if prnt:
            print content

    # LAYOUT changes
    def change_stack(self):
        state = self.datasetSelCB.currentIndex()
        old_index = self.stack_widget.currentIndex()
        new_index = state
        if old_index == new_index and new_index != 2:
            return
        ## Display the corresponding widget and adjust size ##
        self.stack_widget.setCurrentIndex(new_index)
        self.update_stack_size(new_index)

    def hide_job_widget(self):
        if self.stack_widget.height() == 0:
            self.update_stack_size(self.stack_widget.currentIndex())
        else:
            self.stack_widget.setFixedHeight(0)
            self.hidePB.setText('Show job widget')

    def update_stack_size(self, index):
        self.hidePB.setText('Hide job widget')
        if index == 0:
            self.stack_widget.setFixedHeight(0)
        elif index == 1:
            self.stack_widget.setFixedHeight(220)
        elif index == 2:
            if self.phasingCB.currentIndex() == 0:  # phaser
                self.stack_widget.setFixedHeight(440)
            if self.phasingCB.currentIndex() == 1:  # arcimboldo
                self.stack_widget.setFixedHeight(320)
        elif index == 3:
            self.stack_widget.setFixedHeight(60)
            
    def set_phasing_tip(self):
        text = ''
        strategy = str(self.phasingCB.currentText())
        if strategy == 'Phaser':
            text = 'Molecular replacement with Phaser'
        if strategy == 'Arcimboldo':
            text = 'Phase solving based on structure prediction'
        self.phasing_tip.setText(text)

    def scroll_to_end(self):
        self.app.processEvents()
        vscrollb = self.textOutput.verticalScrollBar()
        vscrollb.setValue(vscrollb.maximum())

    # States/Stages int <--> string
    @staticmethod
    def state_string(ind):
        if ind == 0:
            return '(Error on dataInfo file)', QColor(155, 155, 155)
        if ind == 1:
            return '(' + names.stage1 + ' stage)', QColor(Qt.red)
        if ind == 2:
            return '(' + names.stage2 + ' stage)', QColor(255, 165, 0)
        if ind == 3:
            return '(' + names.stage3 + ' stage)', QColor(Qt.green)
           
    def get_state(self, info_array):
        if info_array['approved'] == 'Not_approved':
            return 1
        if info_array['approved'] == 'Approved' and info_array['solved'] == 'Not_solved':
            return 2
        if info_array['approved'] == 'Approved' and info_array['solved'] == 'Solved':
            return 3
        self.displayError(".dataInfo of this directory has unexpected state. This data set will not perform properly")
        return 0

    # MISC
    def coot_selection(self):
        if self.logsList.currentIndex() == 0:
            self.displayWarning("Xamurai will only coot the results of phasing")
            return
        print 'Running coot'
        sum_file = str(self.logsList.currentText())
        # Phaser
        if sum_file.endswith("autoMRphaser.log"):
            path = sum_file.replace('autoMRphaser.log', '')
            pdb = path + "phaser_output.1.pdb"
            map_file = path + "phaser_output.1.mtz"
            input_option = "--auto"
        # Arcimboldo
        elif ('_arcimboldo' in sum_file and sum_file.endswith(".html")) or sum_file.endswith("terminal_output.log"):
            path = "/".join(sum_file.split("/")[:-1])
            pdb = os.path.join(path, "best.pdb")
            map_file = os.path.join(path, "best.phs")
            input_option = "--data"
        else:
            self.displayWarning("No solution files known for this job")
            return
        if os.path.isfile(pdb) and os.path.isfile(map_file):
            command = 'ssh -X %s@%s "coot --pdb %s %s %s --no-guano --script %s --script %s"' \
                      % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, pdb, input_option, map_file,
                         os.path.join(bl13_GUI_dir, "scripts/coot-startup.scm"),
                         os.path.join(bl13_GUI_dir, "scripts/coot-startup.py"))
            print 'Command = %s ' % command
            with open(os.devnull, 'w') as FNULL:
                subprocess.Popen(shlex.split(command), cwd=self.tmp_dir, stdout=FNULL)
            self.displayInfo("Displaying results for job in path " + path)
        else:
            self.displayError("Solution files (" + pdb + ", " + map_file + ") not found")

    def exit(self):
        self.info.deleteLater()
        self.jobs.deleteLater()
        self.deleteLater()

    def closeEvent(self, event):
        event.ignore()
        self.exit()
