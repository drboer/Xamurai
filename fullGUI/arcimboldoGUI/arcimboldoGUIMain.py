import os
from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QIcon, QTextCursor, QFileDialog
from .arcimboldoGUILayout import ArcimboldoLayoutForm
from .arcimboldoGUIProcessor import ArcimboldoProcessor, ArcimboldoJobWidget
from ..common.functions import now
from ..common.layout_utils import set_color, colorize
from ..common.constants import bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, bl13_GUI_tmpdir, \
                               bl13_GUI_dir, bl13_GUI_arcimboldo_jobs_dir_ending, \
                               bl13_GUI_disabled_color_r, bl13_GUI_disabled_color_g, bl13_GUI_disabled_color_b


class ArcimboldoForm(ArcimboldoLayoutForm):
    # stand_alone args are only used if first one is False, "names" are here to remember what to include when calling
    def __init__(self, app, stand_alone=(True, "info_widget", "jobs_widget", "central_widget", "tmp_dir"), parent=None):
        ArcimboldoLayoutForm.__init__(self, stand_alone, parent)
        # Vars
        self.cw = ""
        self.app = app
        self.work_dir = os.getcwd().replace("/storagebls", "")
        self.run_num = 0
        self.root_name = ""
        self.processor_list = []
        self.lowest_resolution = 0
        self.space_group = 0
        # Widget mtz vars
        self.mtz_column_i.default = 0
        self.mtz_column_f.default = 0
        self.mtz_column_sig.default_sigi = 0
        self.mtz_column_sig.default_sigf = 0
        # Start setup commands
        if stand_alone[0]:
            self.displayInfo("Welcome")
            #self.tmp_dir = os.path.join(bl13_GUI_dir, "tmp", "_".join(now().split()))
            self.tmp_dir = os.path.join(bl13_GUI_tmpdir, "_".join(now().split()))
            # Icon
            self.setWindowIcon(QIcon(os.path.join(bl13_GUI_dir,'fullGUI/XamuraiIcon.png')))
        else:
            self.cw = stand_alone[3]
            self.tmp_dir = stand_alone[4]
        self.update_stack_input()
        # Creating tmp directory if needed
        if not os.path.isdir(os.path.join(self.tmp_dir, "tmp_arcimboldo/tmp_runfiles")):
            os.system("mkdir -p " + os.path.join(self.tmp_dir, "tmp_arcimboldo/tmp_runfiles"))
        self.show()

    # CALL MAIN METHOD
    def process(self):
        # Freeze the Form
        self.self_enable(False)
        # Create processor
        processor = ArcimboldoProcessor(self)
        # Prepare signals
        self.connect(processor, SIGNAL("giving_info(QString)"), self.displayInfo, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_warn(QString)"), self.displayWarning, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_error(QString)"), self.displayError, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("info_read(QString)"), self.wake, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("giving_result(QString,QString,int,int)"),
                     self.get_job_results, Qt.QueuedConnection)
        self.connect(processor, SIGNAL("update_job_status(QString,QString)"),
                     self.update_job_status, Qt.QueuedConnection)
        if self.cw != "":  # There is a central widget, inform when logs are ready
            self.connect(processor, SIGNAL("log_is_ready()"), self.cw.ready_log_files, Qt.QueuedConnection)
        # Run
        processor.start()
        self.processor_list.append(processor)

    # PROCESSOR METHODS
    def wake(self, work_dir):
        # Create a job widget
        job = ArcimboldoJobWidget(self.root_name, self.run_num, str(work_dir), self)
        self.jobs_display.layout().addWidget(job)
        # Calculate next run num and enable
        self.update_root_info(self.root_edit.displayText())
        self.self_enable()

    def self_enable(self, value=True):
        self.root_edit.setEnabled(value)
        self.seq_display.setEnabled(value)
        self.seq_browse.setEnabled(value)
        self.mtz_file_display.setEnabled(value)
        self.mtz_file_browse.setEnabled(value)
        self.mtz_update.setEnabled(value)
        self.mtz_column_i.setEnabled(value)
        self.mtz_column_sig.setEnabled(value)
        self.run_button.setEnabled(value)

    def update_job_status(self, job_code, text):
        job_code = str(job_code)
        job = self.jobs_display.findChildren(ArcimboldoJobWidget, job_code)[0]
        job.set_status(str(text))

    def get_job_results(self, job_dir, job_name, job_num, error_code):
        job_code = str(job_name + "_" + str(job_num))
        job_dir = str(job_dir)
        if error_code == 0:  # Finished normally
            job = self.jobs_display.findChildren(ArcimboldoJobWidget, job_code)[0]
            job.set_status("--")
            self.displayInfo("Job " + job_code + " finished. Output on " + job_dir)
        elif error_code == 1:  # Wrong user input
            pass
        elif error_code == 2:  # Programs before Arcimboldo failure
            job = self.jobs_display.findChildren(ArcimboldoJobWidget, job_code)[0]
            job.set_status("Error")
        self.update_root_info(self.root_edit.displayText())
        self.self_enable()

    # MTZ METHODS
    def clear_mtz_info(self):
        self.mtz_info_cell.setText(" ")
        self.mtz_info_resolution.setText(" ")
        self.mtz_column_i.clear()
        self.mtz_column_sig.clear()
        self.lowest_resolution = 0
        self.space_group = 0

    def update_mtz_info(self):
        mtz_file = str(self.mtz_file_display.displayText())
        if mtz_file == "":
            return
        if not os.path.isfile(mtz_file):
            self.displayError("The MTZ file you introduced for processing doesn't exist")
            return
        # Run mtzdmp
        dump_out = os.path.join(self.tmp_dir, "tmp_arcimboldo/tmp_runfiles/tmp_mtzdmp.out")
        os.system('ssh %s@%s "mtzdmp %s -e > %s"' % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, str(mtz_file), dump_out))
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
                cell_dim = " ".join(line.split())
                count = 0
                # Columns
                while not line.startswith(" * Column Labels :") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                f.readline()
                column_labels = f.readline().split()
                for _ in range(3):  # Jump 3 lines
                    f.readline()
                column_types = f.readline().split()
                if len(column_labels) != len(column_types):
                    raise Exception("mtzdmp failed!")
                # Get the possible I,F and SIG columns
                columns_i = []
                columns_f = []
                columns_sig = []
                self.mtz_column_i.default = 0
                self.mtz_column_f.default = 0
                self.mtz_column_sig.default_sigi = 0
                self.mtz_column_sig.default_sigf = 0
                for i, index in enumerate(column_types):
                    if index == "J":
                        columns_i.append(column_labels[i])
                        if column_labels[i] == "IMEAN":
                            self.mtz_column_i.default = len(columns_i) - 1
                    elif index == "Q":
                        columns_sig.append(column_labels[i])
                        if column_labels[i] == "SIGIMEAN":
                            self.mtz_column_sig.default_sigi = len(columns_sig) - 1
                        elif column_labels[i] == "SIGF":
                            self.mtz_column_sig.default_sigf = len(columns_sig) - 1
                    elif index == "F":
                        columns_f.append(column_labels[i])
                        if column_labels[i] == "F":
                            self.mtz_column_f.default = len(columns_f) - 1
                # Resolution Range
                count = 0
                while not line.startswith(" *  Resolution Range :") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                f.readline()
                line = f.readline()
                resolution_range = " ".join(line.split())
                count = 0
                while not line.startswith(" * Space group") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("mtzdmp failed!")
                self.space_group = line.split("(")[-1].split()[-1].split(")")[0]
        except:
            self.displayError("Unexpected mtzdmp output. You may check " + dump_out)
            return
        # Show them in the Form
        self.displayInfo("MTZ file information updated successfully")
        self.mtz_info_cell.setText(cell_dim)
        lowest_resolution = float(resolution_range.split("-")[-1].split(" A")[0])
        if lowest_resolution > 2.5:
            self.mtz_info_resolution.setText(colorize(resolution_range + "  (Above 2.5 A not supported)", "Red"))
        elif lowest_resolution > 2:
            self.mtz_info_resolution.setText(colorize(resolution_range + "  (Unlikely to be solved)", "Orange"))
        elif lowest_resolution > 1.5:
            self.mtz_info_resolution.setText(colorize(resolution_range + "  (Likely to be solved)", "Green"))
        else:
            self.mtz_info_resolution.setText(colorize(resolution_range + "  (Use of Arcimboldo encouraged)", "Blue"))
        self.lowest_resolution = lowest_resolution
        self.mtz_column_i.clear()
        self.mtz_column_i.insertItems(0, columns_i)
        self.mtz_column_i.setCurrentIndex(self.mtz_column_i.default)
        self.mtz_column_f.clear()
        self.mtz_column_f.insertItems(0, columns_f)
        self.mtz_column_f.setCurrentIndex(self.mtz_column_f.default)
        self.mtz_column_sig.clear()
        self.mtz_column_sig.insertItems(0, columns_sig)
        if True:
            self.mtz_column_sig.setCurrentIndex(self.mtz_column_sig.default_sigi)
        else:
            self.mtz_column_sig.setCurrentIndex(self.mtz_column_sig.default_sigf)

    def update_mtz_stack(self, index):
        self.mtz_column_stack.setCurrentIndex(index)
        if index == 0:  # Intensities
            self.mtz_column_label.setText("I:")
            self.mtz_sig_label.setText("SIGI:")
            self.mtz_column_i.setCurrentIndex(self.mtz_column_i.default)
            self.mtz_column_sig.setCurrentIndex(self.mtz_column_sig.default_sigi)
        if index == 1:  # Amplitudes
            self.mtz_column_label.setText("F:")
            self.mtz_sig_label.setText("SIGF:")
            self.mtz_column_f.setCurrentIndex(self.mtz_column_f.default)
            self.mtz_column_sig.setCurrentIndex(self.mtz_column_sig.default_sigf)

    # FILES METHODS
    def update_root_info(self, q_string):
        if len(str(q_string)) == 0:
            self.root_info.setText("")
            self.run_num = 0
            return
        self.root_name = "_".join(str(q_string).split()) + "_" + bl13_GUI_arcimboldo_jobs_dir_ending
        full_dir = os.path.join(str(self.work_dir), str(self.root_name))
        # Check existing files
        if not os.path.isdir(full_dir):
            self.run_num = 1
        else:
            self.run_num = 1
            for name in os.listdir(full_dir):
                if os.path.isdir(os.path.join(full_dir, name)) and name.isdigit():
                    num = int(name)
                    self.run_num = max(self.run_num, num + 1)
        # Check existing jobs (no need anymore, the directory for output is always created before job widget)
        # Finally we get the max number among running jobs and existing files
        self.root_info.setText(str(self.run_num))
        # We set the tooltip to show the full directory where this will be saved
        self.root_info.setToolTip("Full path to output:\n" + os.path.join(full_dir, str(self.run_num)))

    def get_seq_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select FASTA file", self.work_dir,
                                               "FASTA (*.fasta *.fas *.fsa *.faa *.seq)")
        self.seq_display.setText(filename)

    def get_horiz_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select prediction file", self.work_dir,
                                               "Psipred (*.horiz *.psipass2)")
        self.prediction_display.setText(filename)

    def get_mtz_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select MTZ file", self.work_dir, "MTZ (*.mtz)")
        self.mtz_file_display.setText(filename)
        self.update_mtz_info()

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

    # LAYOUT METHODS
    def update_stack_input(self):
        text = str(self.run_cb.currentText())
        if text == "Arcimboldo":
            self.prediction_browse.setEnabled(True)
            self.prediction_display.setEnabled(True)
            set_color(self.prediction_display, 255, 255, 255)
        else:
            self.prediction_browse.setEnabled(False)
            self.prediction_display.setEnabled(False)
            set_color(self.prediction_display,
                      bl13_GUI_disabled_color_r, bl13_GUI_disabled_color_g, bl13_GUI_disabled_color_b)
