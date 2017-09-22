# -*- coding: utf8 -*-
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ..phaserGUI.phaserGUIMain import PhaserForm
from ..arcimboldoGUI.arcimboldoGUIMain import ArcimboldoForm
from ..common.layout_utils import colorize, QLineInfo
from ..common.constants import *
from ..common.functions import now, update_maximum, update_minimum
import names


class MainWindowLayout(QMainWindow):

    def __init__(self, app, *args):
                
        QMainWindow.__init__(self)
                
        ### To get updated data from the robot about crystal info, centering etc, a thread is started
        self.eventTimer = QTimer()
        self.connect(self.eventTimer, SIGNAL('timeout()'), self.updateDatasetInfo)
        self.eventTimer.start(10000)
        self.setFixedWidth(1120)
        self.resize(1120,800)
        self.setWindowTitle(names.title)
        self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowMinimizeButtonHint)
        self.cw=QWidget()
        self.setCentralWidget(self.cw)
        self.cw.setLayout(QGridLayout())
        self.cw.layout().setSpacing(4)

        self.processLogFile = QLabel('')
        
        # Welcome text
        with open(os.path.join(bl13_GUI_dir,'fullGUI/welcome.html'), 'r') as f:
            self.wel_txt = f.read()
        # Icon
        self.setWindowIcon(QIcon(os.path.join(bl13_GUI_dir,'fullGUI/XamuraiIcon.png')))

        # Temporary directory
        self.tmp_dir = os.path.join(bl13_GUI_tmpdir, "_".join(now().split()))
        #self.tmp_dir = os.path.join(bl13_GUI_dir, "tmp", "_".join(now().split())) 

        self.processLogFileName = ''

        self.datasetSelCB = QComboBox()
        self.datasetSelCB.addItems(['<Select data stage>',names.stage1 + ' stage',
                                    names.stage2 + ' stage', names.stage3 + ' stage'])
        self.datasetSelCB.setCurrentIndex(0)
        self.datasetList = QComboBox()
        #self.datasetList.addItem('No data yet')
        self.backPB = QPushButton('-')
        self.approvePB = QPushButton('Accept ' + names.stage1)
        #self.dataInfoTuple = ('no info','no info','no info')
        self.logsListPB = QPushButton('')
        self.logsListPB.hide()
        self.logsList = QComboBox()

        self.refresh_logs = QPushButton('Refresh output log files')
        self.refreshLogPB = QPushButton('Refresh processing output')
        self.refreshLogPB.setToolTip('Updates current shown log_file, and uses its parameters for the widget below')
        self.refreshDirPB = QPushButton('Refresh directory listing')
        self.datadirPB = QPushButton('Change directory')
        self.jobsPB = QPushButton('Jobs')
        self.infoPB = QPushButton('GUI log')
        self.hidePB = QPushButton('Hide job widget')
        self.lower_PBs = QWidget()
        self.lower_PBs.setLayout(QHBoxLayout())
        self.lower_PBs.layout().addWidget(self.jobsPB)
        self.lower_PBs.layout().addWidget(self.infoPB)
        self.lower_PBs.layout().setMargin(0)
        self.closePB = QPushButton('Close')
        self.runPB = QPushButton('Run autoproc')
      
        self.textOutput = QTextBrowser()
        self.textOutput.setOpenExternalLinks(True)
        #self.textOutput.setStyleSheet("font: 9pt "Courier";")
        f = QFont( "Courier", 10)
        self.textOutput.setFont(f)
        #self.textOutput.setLineWidth(5000)
      
        self.directory = QLineEdit()

        self.useCellPB = QRadioButton('Set cell')
        self.cella = QDoubleSpinBox()
        self.cella.setDecimals(3)
        self.cella.setMaximum(2000)
        self.cella.setSuffix(u' \u00C5')
        self.cellb = QDoubleSpinBox()
        self.cellb.setDecimals(3)
        self.cellb.setMaximum(2000)
        self.cellb.setSuffix(u' \u00C5')
        self.cellc = QDoubleSpinBox()
        self.cellc.setDecimals(3)
        self.cellc.setMaximum(2000)
        self.cellc.setSuffix(u' \u00C5')
        self.cellalpha = QDoubleSpinBox()
        self.cellalpha.setDecimals(3)
        self.cellalpha.setMaximum(2000)
        self.cellalpha.setSuffix(u' \u00B0')
        self.cellbeta = QDoubleSpinBox()
        self.cellbeta.setDecimals(3)
        self.cellbeta.setMaximum(2000)
        self.cellbeta.setSuffix(u' \u00B0')
        self.cellgamma = QDoubleSpinBox()
        self.cellgamma.setDecimals(3)
        self.cellgamma.setMaximum(2000)
        self.cellgamma.setSuffix(u' \u00B0')
    
        self.useSG = QRadioButton('Set SG to')
        self.SG = QLineEdit()
        self.SG.setMaximumWidth(60)
    
        self.useMinimalSpotSearch = QRadioButton('No spot search limit')
        self.useResolLimits = QRadioButton('Set resolution limits to')
        self.resLimitLow = QDoubleSpinBox()
        self.resLimitLow.setDecimals(2)
        self.resLimitLow.setValue(50.0)
        self.resLimitLow.setSuffix(u' \u00C5')
        self.resLimitHigh = QDoubleSpinBox()
        self.resLimitHigh.setDecimals(2)
        self.resLimitHigh.setValue(0.0)
        self.resLimitHigh.setSuffix(u' \u00C5')
        # Conection between max and min value
        self.resLimitLow.updateValue = update_minimum(self.resLimitLow, self.resLimitHigh)
        self.resLimitHigh.updateValue = update_maximum(self.resLimitHigh, self.resLimitLow)
        self.connect(self.resLimitHigh, SIGNAL("editingFinished()"), self.resLimitLow.updateValue)
        self.connect(self.resLimitLow, SIGNAL("editingFinished()"), self.resLimitHigh.updateValue)
        
        self.useRmerge = QRadioButton('Use R_merge cutoff')
        self.Rmerge_low = QDoubleSpinBox()
        self.Rmerge_low.setDecimals(2)
        self.Rmerge_low.setSingleStep(0.1)
        self.Rmerge_up = QDoubleSpinBox()
        self.Rmerge_up.setDecimals(2)
        self.Rmerge_up.setSingleStep(0.1)
        self.useCHalf = QRadioButton('Use C 1/2 cutoff')
        self.CHalf_low = QDoubleSpinBox()
        self.CHalf_low.setDecimals(2)
        self.CHalf_low.setSingleStep(0.1)
        self.CHalf_up = QDoubleSpinBox()
        self.CHalf_up.setDecimals(2)
        self.CHalf_up.setSingleStep(0.1)
        self.useIoverSig = QRadioButton(u'Use I/\u03C3(I) cutoff')
        self.IoverSig_low = QDoubleSpinBox()
        self.IoverSig_low.setDecimals(2)
        self.IoverSig_low.setSingleStep(0.1)
        self.IoverSig_up = QDoubleSpinBox()
        self.IoverSig_up.setDecimals(2)
        self.IoverSig_up.setSingleStep(0.1)
        # Conection between max and min value on the ranges
        self.Rmerge_low.updateValue = update_minimum(self.Rmerge_low, self.Rmerge_up)
        self.Rmerge_up.updateValue = update_maximum(self.Rmerge_up, self.Rmerge_low)
        self.connect(self.Rmerge_up, SIGNAL("editingFinished()"), self.Rmerge_low.updateValue)
        self.connect(self.Rmerge_low, SIGNAL("editingFinished()"), self.Rmerge_up.updateValue)
        self.CHalf_low.updateValue = update_maximum(self.CHalf_low, self.CHalf_up)
        self.CHalf_up.updateValue = update_minimum(self.CHalf_up, self.CHalf_low)
        self.connect(self.CHalf_up, SIGNAL("editingFinished()"), self.CHalf_low.updateValue)
        self.connect(self.CHalf_low, SIGNAL("editingFinished()"), self.CHalf_up.updateValue)
        self.IoverSig_low.updateValue = update_maximum(self.IoverSig_low, self.IoverSig_up)
        self.IoverSig_up.updateValue = update_minimum(self.IoverSig_up, self.IoverSig_low)
        self.connect(self.IoverSig_up, SIGNAL("editingFinished()"), self.IoverSig_low.updateValue)
        self.connect(self.IoverSig_low, SIGNAL("editingFinished()"), self.IoverSig_up.updateValue)
        # Default values and ranges
        self.CHalf_low.setMinimum(-2.0)
        self.CHalf_up.setMinimum(-2.0)
        self.IoverSig_low.setMaximum(1.0)
        self.IoverSig_up.setMaximum(1.0)
        self.Rmerge_low.setValue(99.9)
        self.Rmerge_up.setValue(99.9)
        self.CHalf_low.setValue(-1.0)
        self.CHalf_up.setValue(-1.0)
        self.IoverSig_low.setValue(0.0)
        self.IoverSig_up.setValue(0.0) 
        
        self.useImageSpec = QRadioButton('Restrict images to name')
        self.imgName = QLineEdit()
        self.first_image = QSpinBox()
        self.first_image.setMinimum(1)
        self.first_image.setMaximum(999)
        self.last_image = QSpinBox()    
        self.last_image.setMinimum(1)
        self.last_image.setMaximum(999)
        # Conection between first and last img on the range
        self.first_image.updateValue = update_maximum(self.first_image, self.last_image)
        self.last_image.updateValue = update_minimum(self.last_image, self.first_image)
        self.connect(self.last_image, SIGNAL("editingFinished()"), self.first_image.updateValue)
        self.connect(self.first_image, SIGNAL("editingFinished()"), self.last_image.updateValue)
        
        self.group = QButtonGroup()
        self.group.addButton(self.useMinimalSpotSearch)
        self.group.addButton(self.useCellPB)
        self.group.addButton(self.useSG)
        self.group.addButton(self.useResolLimits)
        self.group.addButton(self.useRmerge)
        self.group.addButton(self.useCHalf)
        self.group.addButton(self.useIoverSig)
        self.group.addButton(self.useImageSpec)
        self.group.setExclusive(False)
        
        
        row = 0
        # If a directory is specified on the command line, add change directory buttons. Else just use the default
        #numarg = len(sys.argv)
        #if numarg >1:
        self.cw.layout().addWidget(QLabel('Beamtime data directory'),row,0)
        self.cw.layout().addWidget(self.directory,row,1,1,5)
        self.cw.layout().addWidget(self.datadirPB,row,6)
        row += 1
        self.cw.layout().addWidget(self.datasetSelCB,row,0)
        self.cw.layout().addWidget(self.datasetList,row,1,1,5)
        #self.cw.layout().addWidget(self.processLogFile,row,2,1,4)
        self.cw.layout().addWidget(self.backPB,row,6)
        row += 1
        self.cw.layout().addWidget(self.logsListPB,row,0)
        self.cw.layout().addWidget(self.logsList,row,1,1,5)
        self.cw.layout().addWidget(self.approvePB,row,6)
        row += 1
        self.cw.layout().addWidget(self.textOutput, row, 0, 1, 7)
        row += 1
        self.cw.layout().addWidget(self.refreshLogPB, row, 0, 1, 3)
        self.cw.layout().addWidget(self.refresh_logs, row, 3, 1, 2)
        self.cw.layout().addWidget(self.refreshDirPB, row, 5, 1, 2)
        
        # Display information
        self.info = QDialog()
        self.info_display = QTextBrowser()
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.info_display)
        self.info.setLayout(info_layout)
        self.info.setFont(f)
        self.info.setWindowTitle('GUI log')
        self.info.setFixedSize(600,400)
        # Display jobs
        self.jobs = QDialog()
        scroll = QScrollArea()
        self.jobs_display = QDialog()
        jobs_layout = QVBoxLayout()
        jobs_layout.setAlignment(Qt.AlignTop)
        jobs_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.jobs_display.setLayout(jobs_layout)
        scroll.setWidget(self.jobs_display)
        self.jobs.setLayout(QVBoxLayout())
        self.jobs.layout().addWidget(scroll)
        self.jobs.setWindowTitle('Jobs')
        self.jobs.setFixedSize(540,220)
        
        # Define a new layout to include both widgets, showing only one at time, which will adjust in size
        self.stack_widget = QStackedWidget()
        
        # Zeroth widget
        self.zero_widget = QLabel('')
        self.stack_widget.addWidget(self.zero_widget)
        
        # First widget
        autoproc_layout = QGridLayout() 
            
        self.cellGB = QGroupBox('Cell parameters')
        self.cellGB.setLayout(QGridLayout())
        self.cellGB.layout().addWidget(self.useCellPB,1,0)
        self.cellGB.layout().addWidget(QLabel('a'),0,1)
        self.cellGB.layout().addWidget(self.cella,1,1)
        self.cellGB.layout().addWidget(QLabel('b'),0,2)
        self.cellGB.layout().addWidget(self.cellb,1,2)
        self.cellGB.layout().addWidget(QLabel('c'),0,3)
        self.cellGB.layout().addWidget(self.cellc,1,3)
        self.cellGB.layout().addWidget(QLabel(u'\u03B1'),0,4)
        self.cellGB.layout().addWidget(self.cellalpha,1,4)
        self.cellGB.layout().addWidget(QLabel(u'\u03B2'),0,5)
        self.cellGB.layout().addWidget(self.cellbeta,1,5)
        self.cellGB.layout().addWidget(QLabel(u'\u03B3'),0,6)
        self.cellGB.layout().addWidget(self.cellgamma,1,6)
        
        self.cutsGB = QGroupBox('Cutoff parameters')
        self.cutsGB.setLayout(QGridLayout())
        self.cutsGB.layout().addWidget(self.useRmerge,0,0,1,2)
        self.cutsGB.layout().addWidget(self.Rmerge_low,1,0)
        #self.cutsGB.layout().addWidget(self.Rmerge_up,1,1)
        self.cutsGB.layout().addWidget(self.useCHalf,0,2,1,2)
        self.cutsGB.layout().addWidget(self.CHalf_low,1,2)
        #self.cutsGB.layout().addWidget(self.CHalf_up,1,3)
        self.cutsGB.layout().addWidget(self.useIoverSig,0,4,1,2)
        self.cutsGB.layout().addWidget(self.IoverSig_low,1,4)
        #self.cutsGB.layout().addWidget(self.IoverSig_up,1,5)
        
        inner_row = 0
        autoproc_layout.addWidget(self.cellGB,inner_row,0,1,10)       
      
        inner_row += 1
        autoproc_layout.addWidget(self.useSG,inner_row,0)
        autoproc_layout.addWidget(self.SG,inner_row,1)     
        autoproc_layout.addWidget(self.useResolLimits,inner_row,2)
        autoproc_layout.addWidget(self.resLimitLow,inner_row,3)
        autoproc_layout.addWidget(self.resLimitHigh,inner_row,4)
        autoproc_layout.addWidget(self.useImageSpec,inner_row,5)
        autoproc_layout.addWidget(self.imgName,inner_row,6)
        autoproc_layout.addWidget(QLabel('_####.cbf  and range'),inner_row,7)
        autoproc_layout.addWidget(self.first_image,inner_row,8)
        autoproc_layout.addWidget(self.last_image,inner_row,9)
        
        inner_row += 1
        autoproc_layout.addWidget(self.cutsGB,inner_row,0,1,7)
        autoproc_layout.addWidget(self.useMinimalSpotSearch,inner_row,7)
        autoproc_layout.addWidget(self.runPB,inner_row,8,1,2)
        
        
        autoproc_widget = QWidget()
        autoproc_widget.setLayout(autoproc_layout)
        self.stack_widget.addWidget(autoproc_widget)
        self.autoproc_widget_size = 220
        
        #Second widget
        second_widget = QWidget()
        second_widget.setLayout(QGridLayout())
        self.phasingCB = QComboBox()
        self.phasingCB.addItems(['Phaser','Arcimboldo'])
        self.phasing_tip = QLineInfo('(',')')
        self.phasing_tip.setText('Molecular replacement with phaser')
        # Create another stack widget to hold diferent phasing strategies
        self.phasing_stack = QStackedWidget()
        self.auto_molrep = PhaserForm(app, (False, self.info_display, self.jobs_display, self, self.tmp_dir))
        self.arcimboldo = ArcimboldoForm(app, (False, self.info_display, self.jobs_display, self, self.tmp_dir))
        self.phasing_stack.addWidget(self.auto_molrep)
        self.phasing_stack.addWidget(self.arcimboldo)        
        second_widget.layout().addWidget(QLabel('Phasing strategy'),0,0)
        second_widget.layout().addWidget(self.phasingCB,0,1)
        second_widget.layout().addWidget(self.phasing_tip,0,2)
        second_widget.layout().addWidget(self.phasing_stack,1,0,1,10)
        self.stack_widget.addWidget(second_widget)
        
        # Third widget
        self.third = QLabel("\n Under development \n")
        self.stack_widget.addWidget(self.third)
        
        # Add everything to the main layout
        row += 1
        self.cw.layout().addWidget(self.stack_widget,row,0,1,7)
        self.stack_widget.setFixedHeight(0)
        
        # Rest of the widgets
        row += 1
        self.cw.layout().addWidget(self.lower_PBs, row, 0)
        self.cw.layout().addWidget(self.hidePB, row, 1)
        self.cw.layout().addWidget(self.closePB, row, 6)
        
        self.show()

                #self.connect(self.directory, SIGNAL('textChanged(QString)'), self.updateFileTemplate)
        self.connect(self.datasetList, SIGNAL('currentIndexChanged(int)'), self.selectDataSet)
        # self.datasetSelCB is the stage selector dropdown
        self.connect(self.datasetSelCB, SIGNAL('currentIndexChanged(int)'), self.repopulateSelectList)
        self.connect(self.logsList, SIGNAL('currentIndexChanged(int)'), self.selectLogFile)
        self.connect(self.refreshLogPB, SIGNAL('clicked()'), self.updateProcessingInfo)
        self.connect(self.refreshDirPB, SIGNAL('clicked()'), self.updateDatasetInfo)
        self.connect(self.refresh_logs, SIGNAL('clicked()'), self.findAllFiles)
        self.connect(self.backPB, SIGNAL('clicked()'), self.setStatusBack)
        self.connect(self.approvePB, SIGNAL('clicked()'), self.setStatusForward)
        self.connect(self.datadirPB, SIGNAL('clicked()'), self.changeDirectory)
        self.connect(self.phasingCB, SIGNAL('currentIndexChanged(int)'), self.phasing_stack, SLOT('setCurrentIndex(int)'))
        self.connect(self.phasingCB, SIGNAL('currentIndexChanged(int)'), self.change_stack)
        self.connect(self.phasingCB, SIGNAL('currentIndexChanged(int)'), self.set_phasing_tip)
        self.connect(self.closePB, SIGNAL("clicked()"), self.exit)
        self.connect(self.infoPB, SIGNAL("clicked()"), self.info.show)
        self.connect(self.jobsPB, SIGNAL("clicked()"), self.jobs.show)
        self.connect(self.hidePB, SIGNAL("clicked()"), self.hide_job_widget)
        self.connect(self.useSG, SIGNAL("toggled(bool)"), self.toggleSG)
        self.connect(self.runPB, SIGNAL("clicked()"), self.runManProc)
        #self.connect(self.SG, SIGNAL('textChanged(QString)'), self.changeSG)
        self.connect(self.SG, SIGNAL('editingFinished()'), self.changeSG)
        #self.connect(self.cella, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cella, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.cellb, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cellb, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.cellc, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cellc, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.cellalpha, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cellalpha, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.cellbeta, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cellbeta, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.cellgamma, SIGNAL('valueChanged(double)'), self.cellChange)
        self.connect(self.cellgamma, SIGNAL('editingFinished()'), self.cellChange)
        #self.connect(self.resLimitLow, SIGNAL('valueChanged(double)'), self.resolChange)
        self.connect(self.resLimitLow, SIGNAL('editingFinished()'), self.resolChange)
        #self.connect(self.resLimitHigh, SIGNAL('valueChanged(double)'), self.resolChange)
        self.connect(self.resLimitHigh, SIGNAL('editingFinished()'), self.resolChange)


class AutoProcJobWidget(QWidget):
    def __init__(self, name, num, work_dir, parent=None):
        super(AutoProcJobWidget, self).__init__(parent)
        # LAYOUT
        self.layout = QHBoxLayout()
        # Label
        self.layout.addWidget(QLabel("Job " + colorize("AutoProc_" + name, "Green") + "_" + colorize(str(num), "Red")))
        self.layout.addStretch()
        # Status
        self.status = QLineInfo("Status: ")
        self.set_status("Sending")
        self.layout.addWidget(self.status)
        # Button
        self.button = QPushButton("-")
        self.button.setEnabled(False)
        self.layout.addStretch()
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.setMaximumHeight(38)
        # Vars
        self.work_dir = work_dir
        # Timer
        QTimer.singleShot(1*60*1000, self.self_check)

    def set_status(self, line):
        self.status.setText(line)
        
    def self_check(self):
        print 'AutoProcJobWidget: self_check'
        if os.path.isfile(os.path.join(str(self.work_dir), 'truncate-unique.mtz')):
            self.set_status("Done")
        else:
            QTimer.singleShot(1*60*1000, self.self_check)
            pass
