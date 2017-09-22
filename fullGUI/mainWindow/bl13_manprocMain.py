import subprocess, shlex, os, glob
from PyQt4.QtCore import QTimer, SIGNAL, Qt
from PyQt4.QtGui import QFileDialog, QTextCursor, QColor
from .bl13_manprocLayout import MainWindowLayout, AutoProcJobWidget
from .bl13_remoteAutoproc import runRemoteAutoproc
from ..common.layout_utils import colorize
from ..common.functions import now
from ..common.constants import bl13_GUI_phasing_dir, bl13_GUI_dataproc_dir, bl13_GUI_dir, \
                               bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, \
                               bl13_GUI_cluster_user, bl13_GUI_cluster_server, \
                               bl13_GUI_autoproc_script, bl13_GUI_searchdepth
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
        self.latestproclogfile = -1
        self.latestanalysislogfile = -1
        
    # UPDATE internal lists of datasets and files
    def changeDirectory(self):
        path = str(QFileDialog.getExistingDirectory(self,"Beamtime data directory",self.directory.text()).replace('/storagebls',''))
        if path not in [None, '']:
            self.displayInfo('Changing root directory: ' + path, prnt=True)
            self.directory.setText( str(path) )
            # Now update data dir list
            self.updateDatasetInfo(True)
            
    def findProcessingLogFiles(self, path=''):
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
                            print 'Found log file %s' % logfile
                            log_list.append(os.path.join(dataproc_dir, dir_file, logfile))
                            if not 'manual' in logfile:
                                newlogsfound = True # if newer logs are found, no need to look later for older logs
                            # Identify latest manual processing
                            if dir_file.isdigit() and int(dir_file)>hid: 
                                hid = int(dir_file)
                                latestlogfile = os.path.join(dataproc_dir, dir_file, logfile)
                            break
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
        
    def findPhasingLogFiles(self, path=''):
        # Includes Phaser MR and Arcimboldo files
        ## Get information ##
        if path == '':
            path = str(self.datasetList.currentText())
        if path == '':
            self.textOutput.setPlainText('')
            return
        sum_files = []
        phasing_path = os.path.join(path, bl13_GUI_phasing_dir)
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
        return path, path, sum_files
                                        
    def findAllFiles(self):
        print 'findAllFiles'
        path = str(self.datasetList.currentText())
        if not os.path.isdir(path):
            print 'findAllFiles: the given path is not a directory or doesnt exist'
            return
        data_set_index = self.datasetMasterNameList[path]
        self.latestproclogfile, log_list = self.findProcessingLogFiles(path)
        #print self.latestproclogfile
        self.datasetMasterLogsList.insert(data_set_index, log_list)
        used_log_file, self.latestanalysislogfile, log_list = self.findPhasingLogFiles(path)
        self.datasetMasterSumList.insert(data_set_index, sorted(log_list))
        self.displayUpdate()        

    def ready_log_files(self):
        print 'ready_log_files'
        QTimer.singleShot(10*1000, self.findAllFiles)

    def displayUpdate(self):
        # UPDATE lists and files, depending on the stage and then display
        state = self.datasetSelCB.currentIndex()
        print 'displayUpdate state %d' % state
        current_log = self.processLogFile.text()
        path = str(self.datasetList.currentText())
        try: data_set_index = self.datasetMasterNameList[path]
        except: return None
        if state == 0: #  all files
            path = str(self.datasetList.currentText()).split(' ')[0]
            self.findAllFiles()
            self.displaySelectedData(path)
        elif state == 1: # images to mtz stage
            self.latestproclogfile, log_list = self.findProcessingLogFiles(path)
            self.datasetMasterLogsList.insert(data_set_index, log_list)
            self.displayProcessingFiles()
        elif state == 2: # analysis stage
            used_log_file, self.latestanalysislogfile, log_list = self.findPhasingLogFiles(path)
            self.datasetMasterSumList.insert(data_set_index, sorted(log_list))
            self.displaySummaryFiles()
        elif state == 3:
            pass
        return current_log
            
    def displaySelectedData(self, path):
        state = self.get_state(self.datasetMasterDataList[self.datasetMasterNameList[path]])
        self.datasetSelCB.setCurrentIndex(state)
        
    def displayProcessingFiles(self):
        print 'displayProcessingFiles'
        # Repopulate the log file pulldown when changing dataset/sample
        path = str(self.datasetList.currentText())
        if path == '' or path.startswith('<'):
            self.logsList.clear()
            return
        self.imgName.setText(path.split("/")[-2])
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.logsList.clear()
        for log in self.datasetMasterLogsList[self.datasetMasterNameList[path]]:
            self.logsList.addItem(log)
        self.logsList.setCurrentIndex(0)
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        
    def displaySummaryFiles(self):
        path = str(self.datasetList.currentText())
        if path == '' or path.startswith('<'):
            self.logsList.clear()
            return
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.logsList.clear()
        index = self.datasetMasterNameList[path]
        # Approved processing log file
        log_file = os.path.join(path, bl13_GUI_phasing_dir, "currently_approved_processing.log")
        self.logsList.addItem(log_file + ' (Approved processing log file)')
        self.logsList.setItemData(0, QColor(Qt.gray), Qt.TextColorRole)
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

    def repopulateSelectList(self): 
        ## Update buttons and layout ##
        # self.logsList log files selection pull down menu
        # datasetSelCB is stage selection button (images to mtz, phasing, etc)
        # state is current index of datasetSelCB
        print 'repopulateSelectList'
        self.textOutput.setText('')
        self.disconnect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.logsList.clear()
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        state = self.datasetSelCB.currentIndex()
        if state == 0:
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
        elif state == 1:
            self.backPB.setText('-')
            self.backPB.setEnabled(False)
            self.approvePB.setText('Accept ' + names.stage1)
            self.approvePB.show()
            self.approvePB.setEnabled(True)
            self.refreshLogPB.setEnabled(True)
            self.refresh_logs.setEnabled(True)
            self.disconnect(self.logsListPB, SIGNAL('clicked()'), self.coot_selection)
            self.logsListPB.hide()
        elif state == 2:
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
        elif state == 3:
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
        
        if state == 0:  # If the user has selected the ALL tab
            self.disconnect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
            self.datasetList.clear()
            self.datasetList.insertItem(0, '<Select dataset path>')
            count = 1
            for key in self.datasetMasterNameList:
                data_state = self.get_state(self.datasetMasterDataList[self.datasetMasterNameList[key]])
                (text, color) = self.state_string(data_state)
                self.datasetList.insertItem(count, key + ' ' + text)
                self.datasetList.setItemData(count, color, Qt.TextColorRole)
                count += 1
            self.connect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
            return
        
        print 'repopulateSelectList: after state settings'
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
        # print 'repopulateSelectList: Adding datasets that are; ', str(self.datasetSelCB.currentText()).lower()
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
            if data_state == state or state == 0:
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
        print 'repopulateSelectList: before displayUpdate'
        self.selectDataSet()
        print 'repopulateSelectList: after displayUpdate'

    def selectDataSet(self):
        print 'selectDataSet'
        current_log = self.displayUpdate()
        stage = self.datasetSelCB.currentIndex()
        print 'selectDataSet', stage, self.latestproclogfile, self.latestanalysislogfile
        if stage == 0: #  all files
            path = str(self.datasetList.currentText()).split()[0]
            self.findAllFiles()
            self.displaySelectedData(path)
        elif stage == 1: # images to mtz stage
            self.findSelectLogFile(self.latestproclogfile)
        elif stage == 2: # analysis stage
            self.findSelectLogFile(self.latestanalysislogfile)
        elif stage == 3:
            pass
       
    def selectLogFile(self):
        # Given aprocessing job selection (ie the entry of the logs list), the output file is retrieved and displayed
        print 'selectLogFile', self.latestproclogfile, str(self.logsList.currentText())
        stage = self.datasetSelCB.currentIndex()
        log_file = str(self.logsList.currentText())
        if stage == 1:
            self.processLogFile.setText(log_file)
            print 'Showing processing file: %s' % log_file
            self.updateProcessingInfo()
        elif stage == 2:
            if self.logsList.currentIndex() == 0 and os.path.isfile(log_file.split()[0]):
                log_file = os.readlink(log_file.split()[0])
                print 'Showing processing file: %s' % log_file
                # MR: 2017 05 04
                # If there is an .html, it should be displayed instead
                html_summary = "/".join(log_file.split("/")[:-1] + ["summary.html"])
                if os.path.isfile(html_summary):
                    with open(html_summary,'r') as summary:
                        html = summary.read()
                    self.textOutput.setHtml(html)
                    self.textOutput.verticalScrollBar().setValue(380)
                # If there is not, display the log and continue as usual
                else:
                    with open(log_file,'r') as log:
                        text = log.read()
                    self.textOutput.setHtml(text)
                    self.scroll_to_end()
            elif os.path.isfile(log_file):
                print 'Showing summary file: %s' % log_file
                text = open(log_file, 'r').read()
                if log_file.endswith(".html") or log_file.endswith("autoMRphaser.log"):
                    self.textOutput.setHtml(text)  # The log file is an HTML
                else:
                    self.textOutput.setText(text)
                self.scroll_to_end()
            else:
                self.textOutput.setText('File ' + log_file + ' doesn\'t exist')

    def findSelectLogFile(self,logfilenamepath):
        index = self.logsList.findText(logfilenamepath)
        #print self.latestproclogfile,'found at index',index
        self.logsList.setCurrentIndex(index)
        return
                
    def updateProcessingInfo(self):
        # This function finds the processing file and extracts parameters from it
        print 'updateProcessingInfo'
        if self.datasetSelCB.currentIndex() == 1: # stage 1
            if self.processLogFile.text() == '':
                print 'empty file'
                self.textOutput.setPlainText('')
            else:
                selected_file = str(self.processLogFile.text())
                if os.path.isfile(selected_file):
                    text=open(selected_file).read()
                    # MR: 2017 05 04
                    # If there is an .html, it should be displayed instead
                    html_summary = "/".join(selected_file.split("/")[:-1] + ["summary.html"])
                    #html_summary = "summary.html"
                    print 'HTML file at %s' % html_summary
                    if os.path.isfile(html_summary):
                        curdir = os.getcwd()
                        os.chdir( "/"+str("/".join(selected_file.split("/")[1:-1])) )
                        with open(html_summary,'r') as summary:
                            html = summary.read()
                        print 'Current dir %s' % os.getcwd()
                        self.textOutput.setHtml(html)
                        #os.chdir(curdir)
                        #self.textOutput.verticalScrollBar().setValue(380)
                    # If there is not, display the log and continue as usual
                    else:
                        self.textOutput.setPlainText(text)
                    self.scroll_to_end()
                    textlines = text.splitlines()
                    self.displayInfo('Log file contents updated')
                    for line in textlines:
                        srchstr =  'Cell parameters ......................................'
                        if srchstr in line:
                            cellpars = line.split(srchstr)[1].split()
                            #print 'cellpars %s' %str(cellpars)
                            if len(cellpars) == 6:
                                self.cella.setValue(float(cellpars[0]))
                                self.cellb.setValue(float(cellpars[1]))
                                self.cellc.setValue(float(cellpars[2]))
                                self.cellalpha.setValue(float(cellpars[3]))
                                self.cellbeta.setValue(float(cellpars[4]))
                                self.cellgamma.setValue(float(cellpars[5]))
                        srchstr = 'Resolution ...........................................'
                        if srchstr in line:
                            resol = line.split(srchstr)[1].split()
                            if len(resol) == 4:
                                self.resLimitLow.setValue(float(resol[0]))
                                self.resLimitHigh.setValue(float(resol[2]))
                        srchstr = 'Spacegroup name ......................................'
                        if srchstr in line:
                            self.SG.setText( line.split(srchstr)[1] )
                else:
                    self.displayError('Can\'t read, not a file: %s' % selected_file, prnt=True)
        elif self.datasetSelCB.currentIndex() == 2: # stage 2: analysis
            #pass
            self.selectLogFile()

    # MAIN (autoproc)
    def runManProc(self):
        print 'runManProc'
        self.setEnabled(False)
        # 1. Set parameters
        autoproc_parameters = ['StopIfSubdirExists=no', 'BeamCentreFrom=header:x,y',
                               'autoPROC_TwoThetaAxis=\\"-1 0 0\\"']
        if self.useCellPB.isChecked():
            autoproc_parameters.append('cell=\\"%s %s %s %s %s %s\\"' % (self.cella.value(), self.cellb.value(),
                                                                        self.cellc.value(), self.cellalpha.value(),
                                                                        self.cellbeta.value(), self.cellgamma.value()))
        if self.useSG.isChecked():
            autoproc_parameters.append('symm=\\"%s\\"' % self.SG.text())
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
            autoproc_parameters.append('ScaleAnaRmergeCut_123=\\"%s:%s\\"' % (self.Rmerge_low.value(), self.Rmerge_low.value()))
        if self.useIoverSig.isChecked():
            autoproc_parameters.append('ScaleAnaISigmaCut_123=\\"%s:%s\\"' % (self.IoverSig_low.value(), self.IoverSig_low.value()))
        if self.useCHalf.isChecked():
            autoproc_parameters.append('ScaleAnaCChalfCut_123=\\"%s:%s\\"' % (self.CHalf_low.value(), self.CHalf_low.value()))

        # 2. Calculate the number of this job/launch
        name = str(self.datasetList.currentText()).split("/")[-2]
        print "Dataset list name", str(self.datasetList.currentText())
        print "Name of this dataset",name
        work_dir = os.path.join(str(self.datasetList.currentText()), 'dataproc').replace('/storagebls','')
        num = 0
        if os.path.isdir(work_dir):
            existing_num = []
            for number in os.listdir(work_dir):
                if os.path.isdir(os.path.join(work_dir, number)) and number.isdigit():
                    existing_num.append(int(number))
            if len(existing_num):
                num = max(existing_num) + 1
        else:
            os.system("mkdir " + work_dir)
        
        # 3. Find data dir
        data_dir = str(self.datasetList.currentText()).replace('/storagebls','')
        data_dir = os.path.join(data_dir,'images') # runRemoteAutoproc expects images in the file, so add it
        print "Datadir name", data_dir
        # MR: 2017 05 05
        # Added image specification
        if self.useImageSpec.isChecked():
            autoproc_parameters.append('-Id \\"Xamurai_%s,%s,%s_####.cbf,%d,%d\\"' % (self.imgName.text(), data_dir, self.imgName.text(),
                                                                                      self.first_image.value(), self.last_image.value()))
        else:
            autoproc_parameters.append('-I \\"' + data_dir + '\\"')
        # TODO: Change the autoproc parameters when inverse beam collection is detected

        # 4. Display job information on screen
        job = AutoProcJobWidget(name, num, os.path.join(work_dir, str(num)))
        self.jobs_display.layout().addWidget(job)

        # 5. Run Autoproc
        ret, all_ok = runRemoteAutoproc(bl13_GUI_cluster_user, bl13_GUI_cluster_server,
                                bl13_GUI_autoproc_script, data_dir, autoproc_parameters)
        print ret     
        
        # 6. Update GUI and job
        if all_ok:
            job.set_status("Sent")
        else:
            job.set_status("Error")
        # self.processLogFile.setText(logfile)
        # RB 20161115
        self.ready_log_files()
        #self.findAllFiles()
        self.setEnabled(True)
        
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
    def updateDatasetInfo(self, request=False):
        print 'updateDatasetInfo: Finding images directories in root %s' % self.directory.text()
        #prevtext = self.datasetList.currentText()
        #print prevind
        shcom = 'find %s ' % self.directory.text()
        #shcom = shcom + '-maxdepth 3 -type d -name "images" -printf \'%p %c\\n\'' 
        shcom = shcom + '-maxdepth %d -type d -name "images"' % bl13_GUI_searchdepth# RB 20161118: make it faster
        #print 'shell command  is %s' % shcom
        if os.path.isdir(self.directory.text()): 
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
                    latestlogile, self.latestlogfile, log_list = self.findPhasingLogFiles(cbname)
                    self.datasetMasterSumList.insert(nimdir, sorted(log_list))
                    if need_to_write:
                        self.writeDataInfoFile(cbname,thisdata)
                    nimdir = nimdir + 1
                # Now reset the selection list
                self.repopulateSelectList()
        else: 
            print 'Not a valid directory, ignored'
            
        #print 'exit updateDatasetInfo'
    
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

    def changeSG(self):
        self.useSG.setChecked(True)

    def resolChange(self):
        self.useResolLimits.setChecked(True)

    def cellChange(self):
        self.useCellPB.setChecked(True)

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
