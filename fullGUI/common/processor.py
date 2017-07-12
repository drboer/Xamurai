from PyQt4.QtCore import pyqtSignal, QThread
from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, QPushButton
from ..common.layout_utils import QLineInfo, colorize


class FormProcessor(QThread):
    # SIGNALS
    giving_info = pyqtSignal(str)
    giving_warn = pyqtSignal(str)
    giving_error = pyqtSignal(str)
    info_read = pyqtSignal(str)
    log_is_ready = pyqtSignal()
    update_job_status = pyqtSignal(str,str)

    # METHODS
    def __init__(self, form, parent=None):
        super(FormProcessor, self).__init__(parent)
        self.form = form
        self.moveToThread(self)

    def run(self):
        self.work()


class JobWidget(QWidget):
    def __init__(self, name, num, work_dir, form, parent=None):
        super(JobWidget, self).__init__(parent)
        # LAYOUT
        self.layout = QHBoxLayout()
        # Label
        self.layout.addWidget(QLabel("Job " + colorize(name, "Green") + "_" + colorize(str(num), "Red")))
        self.layout.addStretch()
        # Status
        self.status = QLineInfo("Status: ")
        self.status.setText("Running")
        self.layout.addWidget(self.status)
        # Button
        self.button = QPushButton("-")
        self.button.setEnabled(False)
        self.layout.addStretch()
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.setMaximumHeight(38)
        # Vars
        self.form = form
        self.number = num
        self.name = name
        self.work_dir = work_dir
        self.setObjectName(name + "_" + str(num))

    def set_status(self, line):
        self.status.setText(line)
        self.set_null_button()

    def set_null_button(self):
        self.button.setText("-")
        self.button.setEnabled(False)