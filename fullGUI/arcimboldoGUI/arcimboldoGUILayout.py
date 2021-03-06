from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ..common.layout_utils import *


class ArcimboldoLayoutForm(QDialog):
    def __init__(self, stand_alone, parent=None):
        super(ArcimboldoLayoutForm, self).__init__(parent)
        # TITLE
        self.setWindowTitle("Arcimboldo GUI")
        # WIDGETS
        # MTZ
        self.mtz_file_display = QLineEdit("")
        self.mtz_file_browse = QPushButton("Browse")
        self.mtz_update = QPushButton("Update MTZ file info")
        self.mtz_column_i = QComboBox()
        self.mtz_column_i.setMinimumWidth(80)
        self.mtz_column_i.setFixedHeight(20)
        self.mtz_column_i.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.mtz_column_f = QComboBox()
        self.mtz_column_f.setMinimumWidth(80)
        self.mtz_column_f.setFixedHeight(20)
        self.mtz_column_f.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.mtz_column_sig = QComboBox()
        self.mtz_column_sig.setMinimumWidth(80)
        self.mtz_column_sig.setFixedHeight(20)
        self.mtz_column_sig.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # Stack for columns F (amplitudes) or I (intensities)
        self.mtz_column_label = QLabel("I:")
        self.mtz_sig_label = QLabel("SIGI:")
        self.mtz_column_cb = QComboBox()
        self.mtz_column_cb.addItems(["I: Intensities", "F: Amplitudes"])
        self.mtz_column_stack = QStackedWidget()
        self.mtz_column_stack.setFixedHeight(20)
        self.mtz_column_stack.addWidget(self.mtz_column_i)
        self.mtz_column_stack.addWidget(self.mtz_column_f)
        mtz_columns_layout = QHBoxLayout()
        mtz_columns_layout.addWidget(self.mtz_column_cb)
        mtz_columns_layout.addWidget(self.mtz_column_label)
        mtz_columns_layout.addWidget(self.mtz_column_stack)
        mtz_columns_layout.addWidget(self.mtz_sig_label)
        mtz_columns_layout.addWidget(self.mtz_column_sig)
        self.mtz_info = QWidget()
        mtz_info_layout = QVBoxLayout()
        self.mtz_info_resolution = QLineInfo("Resolution Range: ")
        self.mtz_info_cell = QLineInfo("Cell Dimensions: ")
        mtz_info_layout.addWidget(self.mtz_info_resolution)
        mtz_info_layout.addWidget(self.mtz_info_cell)
        self.mtz_info.setLayout(mtz_info_layout)
        # Sequence
        seq_layout = QHBoxLayout()
        seq_layout.setMargin(0)
        self.seq_display = QLineEdit("")
        self.seq_browse = QPushButton("Browse")
        seq_layout.addWidget(QLabel("Sequence File"))
        seq_layout.addWidget(self.seq_display)
        seq_layout.addWidget(self.seq_browse)
        # Prediction
        prediction_layout = QHBoxLayout()
        prediction_layout.setMargin(0)
        self.prediction_display = QLineEdit("")
        self.prediction_browse = QPushButton("Browse")
        prediction_layout.addWidget(QLabel("Prediction File"))
        prediction_layout.addWidget(self.prediction_display)
        prediction_layout.addWidget(self.prediction_browse)
        # Title/root (working directory
        self.root_edit = QLineEdit("")
        self.root_info = QLineInfo("Next job number: ")
        # Run buttons
        self.run_cb = QComboBox()
        self.run_cb.addItems(["Psipred + Arcimboldo", "Arcimboldo", "Psipred"])
        self.run_button = QPushButton("Run")
        bot_layout = QHBoxLayout()
        bot_layout.addWidget(QLabel("Title"))
        bot_layout.addWidget(self.root_edit)
        bot_layout.addWidget(self.root_info)
        bot_layout.addStretch()
        bot_layout.addWidget(QLabel("Type of job: "))
        bot_layout.addWidget(self.run_cb)
        bot_layout.addWidget(self.run_button)
        # LAYOUT
        layout = QGridLayout()
        row = 0
        # If this is a standalone program, create its own info and jobs display
        if stand_alone[0]:
            # Display information
            self.InfoDisplay = QTextBrowser()
            set_color(self.InfoDisplay, 255, 255, 204)
            size = 96
            width = 310
            self.InfoDisplay.setMaximumHeight(size)
            # Display jobs
            self.jobs_display = QDialog()
            jobs_scroll = QScrollArea()
            jobs_scroll.setWidget(self.jobs_display)
            jobs_scroll.setMaximumHeight(size)
            jobs_layout = QVBoxLayout()
            jobs_layout.setAlignment(Qt.AlignTop)
            jobs_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
            jobs_layout.addWidget(QLabel("JOBS:"))
            self.jobs_display.setLayout(jobs_layout)
            layout.addWidget(jobs_scroll, row, 0, 1, 3)
            layout.addWidget(self.InfoDisplay, row, 3, 1, 3)
            row += 1
            self.InfoDisplay.setMinimumWidth(width)
            self.jobs_display.setMinimumWidth(width)
        else:  # Get the pointer to info and jobs displayer
            self.InfoDisplay = stand_alone[1]
            self.jobs_display = stand_alone[2]
        layout.addLayout(seq_layout, row, 0, 1, 6)
        row += 1
        layout.addLayout(prediction_layout, row, 0, 1, 6)
        row += 1
        layout.addWidget(QLabel("MTZ Input File"), row, 0)
        layout.addWidget(self.mtz_file_display, row, 1, 1, 4)
        layout.addWidget(self.mtz_file_browse, row, 5)
        row += 1
        layout.addWidget(QLabel("MTZ Column Labels"), row, 0)
        layout.addLayout(mtz_columns_layout, row, 1, 1, 2)
        layout.addWidget(self.mtz_update, row, 4)
        row += 1
        layout.addWidget(QLabel("Selected MTZ File Info"), row, 0)
        layout.addWidget(self.mtz_info, row, 1, 1, 5)
        row += 1
        layout.addLayout(bot_layout, row, 0, 1, 6)
        layout.setVerticalSpacing(18)
        self.setLayout(layout)
        # SIGNALS
        self.connect(self.seq_browse, SIGNAL("clicked()"),
                     self.get_seq_file)
        self.connect(self.prediction_browse, SIGNAL("clicked()"),
                     self.get_horiz_file)
        self.connect(self.run_cb, SIGNAL("currentIndexChanged(int)"),
                     self.update_stack_input)
        self.connect(self.mtz_file_display, SIGNAL("textChanged(QString)"),
                     self.clear_mtz_info)
        self.connect(self.mtz_column_cb, SIGNAL("currentIndexChanged(int)"),
                     self.update_mtz_stack)
        self.connect(self.mtz_update, SIGNAL("clicked()"),
                     self.update_mtz_info)
        self.connect(self.mtz_file_browse, SIGNAL("clicked()"),
                     self.get_mtz_file)
        self.connect(self.root_edit, SIGNAL("textChanged(QString)"),
                     self.update_root_info)
        self.connect(self.run_button, SIGNAL("clicked()"),
                     self.process)
