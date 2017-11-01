#!usr/bin/env python
import os, subprocess, shlex
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QIcon, QMessageBox, QFileDialog, QTextCursor
from .phaserGUILayout import PhaserLayoutForm, SummaryDisplay
from .phaserGUIProcessor import PhaserProcessor, PhaserJobWidget
from .phaserGUIWidgets import EnsembleWidget, ProteinCompWidget
from ..common.functions import now
from ..common.layout_utils import colorize
from ..common.constants import bl13_GUI_dir, bl13_GUI_phaser_jobs_dir_ending,\
                               bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, bl13_GUI_tmpdir


class PhaserForm(PhaserLayoutForm):
    # stand_alone args are only used if first one is False, "names" are here to remember what to include when calling
    def __init__(self, app, stand_alone=(True, "info_widget", "jobs_widget", "central_widget", "tmp_dir"), parent=None):
        PhaserLayoutForm.__init__(self, stand_alone, parent)
        # Vars
        self.runNum = 0
        self.root_name = ""
        self.processor_list = []
        self.displayer_list = []
        self.app = app
        self.cw = ""
        self.work_dir = os.getcwd().replace("/storagebls", "")
        # Start setup commands
        self.file_root_edit.setText("project")  # This must be set (with any name) to set the run_number (self.runNum)
        if stand_alone[0]:
            self.displayInfo("Welcome")
            #self.tmp_dir = os.path.join(bl13_GUI_dir, "tmp", "_".join(now().split()))
            self.tmp_dir = os.path.join(bl13_GUI_tmpdir, "_".join(now().split()))
            # Icon
            self.setWindowIcon(QIcon(os.path.join(bl13_GUI_dir,'fullGUI/XamuraiIcon.png')))
        else:
            self.cw = stand_alone[3]
            self.tmp_dir = stand_alone[4]
        self.add_ensemble(self.mainTab.count()-1)
        self.mainTab.setCurrentIndex(1)
        # Creating tmp directory if needed
        if not os.path.isdir(os.path.join(self.tmp_dir, "tmp_autoMRphaser/tmp_runfiles")):
            os.system("mkdir -p " + os.path.join(self.tmp_dir, "tmp_autoMRphaser/tmp_pdb"))
            os.system("mkdir -p " + os.path.join(self.tmp_dir, "tmp_autoMRphaser/tmp_runfiles"))
        self.show()

    # CALL MAIN METHOD
    def process(self):
        # Freeze the Form
        self.self_enable(False)
        # Create processor
        processor = PhaserProcessor(self)
        # Prepare signals
        self.connect(processor, SIGNAL("giving_info(QString)"), self.displayInfo, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_warn(QString)"), self.displayWarning, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_error(QString)"), self.displayError, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("info_read(QString)"), self.wake, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_result(QString,QString,int,int)"),
                     self.get_job_results, Qt.QueuedConnection)
        if self.cw != "":  # There is a central widget, inform when logs are ready
            self.connect(processor, SIGNAL("log_is_ready()"), self.cw.selectDataSet, Qt.QueuedConnection)
        # Run
        processor.start()
        self.processor_list.append(processor)

    # PROCESSOR METHODS
    def wake(self, work_dir):
        # Create a job widget
        job = PhaserJobWidget(self.root_name, self.runNum, str(work_dir), self)
        self.jobs_display.layout().addWidget(job)
        # Calculate next run num and enable
        self.update_file_info(self.file_root_edit.displayText())
        self.self_enable()

    def self_enable(self, value=True):
        self.file_root_edit.setEnabled(value)
        self.mainTab.setEnabled(value)
        self.start_button.setEnabled(value)

    def get_job_results(self, job_dir, job_name, job_num, error_code):
        job_code = str(job_name + "_" + str(job_num))
        job_dir = str(job_dir)
        if error_code == 0:  # Finished normally
            job = self.jobs_display.findChildren(PhaserJobWidget, job_code)[0]
            if not os.path.isfile(os.path.join(job_dir, "autoMRphaser.log")):
                job.set_status("Failure")
            elif os.path.isfile(os.path.join(job_dir, "phaser_output.1.mtz")):
                job.set_status("Done: Success")
                job.set_view_button()
                self.display_summary(job_dir, job_code, with_solution=True)
            else:
                job.set_status("Done: No success")
                self.display_summary(job_dir, job_code, with_solution=False)
        elif error_code == 1:  # Wrong user input
            pass
        elif error_code == 2:  # Phaser command failure
            job = self.jobs_display.findChildren(PhaserJobWidget, job_code)[0]
            job.set_status("Error")
        self.update_file_info(self.file_root_edit.displayText())
        self.self_enable()

    def display_summary(self, job_dir, job_code, with_solution):
        # Display results
        summary_display = SummaryDisplay(job_dir, job_code, with_solution, self)
        self.app.processEvents()
        summary_display.text.verticalScrollBar().setValue(summary_display.text.verticalScrollBar().maximum())
        # Handle results by user decision
        self.connect(summary_display, SIGNAL("accepted()"), summary_display.call_coot)
        self.displayer_list.append(summary_display)

    def display_on_coot(self, job_dir):  # Used to display results on Coot
        command = 'ssh -X %s@%s "coot --pdb %s --auto %s --no-guano --script %s --script %s"' \
                  % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server,
                     os.path.join(job_dir, "phaser_output.1.pdb"), os.path.join(job_dir, "phaser_output.1.mtz"),
                     os.path.join(bl13_GUI_dir, "scripts/coot-startup.scm"), os.path.join(bl13_GUI_dir, "scripts/coot-startup.py"))
        with open(os.devnull, 'w') as FNULL:
            subprocess.Popen(shlex.split(command), cwd=self.tmp_dir, stdout=FNULL)

    # LAYOUT METHODS
    def add_ensemble(self, index):
        last_index = self.mainTab.count()-1
        if index != last_index:
            return
        num = self.mainTab.count()
        if num >= 9:
            self.mainTab.setCurrentIndex(self.mainTab.currentIndex()-1)
            self.displayWarning("You cannot add more ensembles")
            return
        existing = self.mainTab.findChildren(EnsembleWidget)
        max_num = 0
        for ensemble in existing:
            max_num = max(max_num, ensemble.number)
        new_item = EnsembleWidget(self.app, self, max_num + 1)
        self.mainTab.insertTab(last_index, new_item, "Ensemble " + str(max_num + 1))
        self.mainTab.setCurrentIndex(last_index)

    def close_tab(self, index):
        if index == 0:
            self.displayWarning("MTZ tab cannot be closed")
            return
        if index == self.mainTab.count()-1:
            return
        if self.mainTab.count() <= 3:
            self.displayWarning("You must keep at least one ensemble")
            return
        if not self.mainTab.widget(index).isEnabled():
            self.displayWarning("This ensemble is running Balbes")
            return
        ensemble = self.mainTab.widget(index)
        alert = QMessageBox()
        alert.setText("Are you sure you want to delete Ensemble " + str(ensemble.number) + "?")
        alert.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = alert.exec_()
        if ret == QMessageBox.Yes:
            current_index = self.mainTab.currentIndex()
            # Prevent to be in the Add Ensemble tab
            if current_index == self.mainTab.count()-2:
                self.mainTab.setCurrentIndex(current_index-1)
            ensemble.deleteLater()            

    def add_comp_item(self, mw=0, num_res=0, num_in_asu=1):
        new_item = ProteinCompWidget(self)
        self.comp_items_layout.removeWidget(self.add_comp_button)
        self.comp_items_layout.addWidget(new_item)
        self.comp_items_layout.addWidget(self.add_comp_button)
        new_item.MW_widget.setValue(mw)
        new_item.num_res_widget.setValue(num_res)
        new_item.num.num_box.setValue(num_in_asu)
        self.connect(new_item, SIGNAL("destroyed()"), self.update_comp_area)
        self.update_comp_area()

    def update_comp_area(self):
        self.app.processEvents()
        self.comp_widget.resize(0, 0)
        self.comp_widget.show()
        self.comp_widget.adjustSize()

    def delete_comp_item(self):
        for comp_item in self.comp_widget.findChildren(ProteinCompWidget):
            if comp_item.to_be_deleted:
                comp_item.deleteLater()
                return

    def update_file_info(self, q_string):
        self.root_name = "_".join(str(q_string).split()) + "_" + bl13_GUI_phaser_jobs_dir_ending
        full_root_dir = os.path.join(str(self.work_dir), str(self.root_name))
        # Check existing dirs
        self.runNum = 1
        if os.path.isdir(full_root_dir):
            for name in os.listdir(full_root_dir):
                if os.path.isdir(os.path.join(full_root_dir, name)) and name.isdigit():
                    num = int(name)
                    self.runNum = max(num+1, self.runNum)
        # Check existing jobs (should not be necessary)
        job_list = self.jobs_display.findChildren(PhaserJobWidget)
        if len(job_list) > 0:
            max_job_num = 0
            for job in job_list:
                if job.name == self.root_name:
                    max_job_num = max(max_job_num, job.number)
            self.runNum = max(self.runNum, max_job_num + 1)
        # Finally we get the max number among running jobs and existing files
        #self.displayWarning("update_file_info %s %s" % (full_root_dir, str(self.runNum)) )
        self.file_prefix_info.setText(os.path.join(full_root_dir, str(self.runNum)))

    # MTZ LAYOUT METHODS
    def clear_mtz_info(self):
        self.mtz_info_cell.setText(" ")
        self.mtz_info_resolution.setText(" ")
        self.mtz_column_f.clear()
        self.mtz_column_sigf.clear()

    def get_mtz_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select MTZ file", self.work_dir, "MTZ (*.mtz)")
        self.mtz_file_display.setText(filename)
        self.update_mtz_info()

    def update_mtz_info(self):
        MTZfile = str(self.mtz_file_display.displayText())
        if MTZfile == "":
            return
        if not os.path.isfile(MTZfile):
            self.displayError("The MTZ file you introduced for processing doesn't exist")
            return
        dump_out = os.path.join(self.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_mtzdmp.out")
        # Run mtzdmp
        os.system('ssh %s@%s "mtzdmp %s -e > %s"' % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, str(MTZfile), dump_out))
        # Retrieve results
        try:
            with open(dump_out) as f:
                line = "0"
                count = 0
                # CellDimensions
                while not line.startswith(" * Dataset ID, project/crystal/dataset names, cell") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                for _ in range(4):  # Jump 4 lines
                    f.readline()
                line = f.readline()
                CellDim = " ".join(line.split())
                count = 0
                # Columns
                while not line.startswith(" * Column Labels :") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                f.readline()
                columnLabels = f.readline().split()
                for _ in range(3):  # Jump 3 lines
                    f.readline()
                columnTypes = f.readline().split()
                if len(columnLabels) != len(columnTypes):
                    raise Exception("mtzdmp failed!")
                # Get the possible F columns
                indicesF = [i for i, j in enumerate(columnTypes) if j == "F"]
                columnsF = [columnLabels[i] for i in indicesF]
                # Get the possible SIGF columns
                indicesSIGF = [i for i, j in enumerate(columnTypes) if j == "Q"]
                columnsSIGF = [columnLabels[i] for i in indicesSIGF]
                count = 0
                # Resolution Range
                while not line.startswith(" *  Resolution Range :") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                f.readline()
                line = f.readline()
                resolution_range = " ".join(line.split())
        except: 
            self.displayWarning("Unexpected mtzdmp output. You may check " + dump_out)
            return
        # Show them in the Form
        self.displayInfo("MTZ file information updated successfully")
        self.mtz_info_cell.setText(colorize(CellDim, "Green"))
        self.mtz_info_resolution.setText(colorize(resolution_range, "Green"))
        self.mtz_column_f.clear()
        self.mtz_column_f.insertItems(0, columnsF)
        self.mtz_column_sigf.clear()
        self.mtz_column_sigf.insertItems(0, columnsSIGF)

    # INFO METHODS
    def displayError(self, arg):
        content = colorize("Error: " + str(arg), "Red")
        self.displayInfo(content)

    def displayWarning(self, arg):
        content = colorize("Warning: " + arg, "Navy")
        self.displayInfo(content)

    def displayInfo(self, arg):
        content = now() + "> " + arg
        self.InfoDisplay.moveCursor(QTextCursor.End)
        self.InfoDisplay.insertPlainText("\n")
        self.InfoDisplay.insertHtml(content)
        self.app.processEvents()
        self.InfoDisplay.verticalScrollBar().setValue(self.InfoDisplay.verticalScrollBar().maximum())

    # MINOR METHODS
    def closeEvent(self, event):
        # we want the processes to keep running
        # for aim in self.processor_list:
        # aim.kill()
        event.accept()
