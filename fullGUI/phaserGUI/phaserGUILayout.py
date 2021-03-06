#!/usr/bin/env python
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ..common.layout_utils import *


class PhaserLayoutForm(QDialog):
    def __init__(self, stand_alone, parent=None):
        super(PhaserLayoutForm, self).__init__(parent)
        # TAB WIDGETS
        self.mainTab = QTabWidget()
        self.mainTab.setTabPosition(QTabWidget.North)
        self.mainTab.setMinimumWidth(860)
        self.mainTab.setMinimumHeight(200)
        self.mainTab.setTabsClosable(True)
        # MTZ input/ Name for output TAB
        self.IOTab = QWidget()
        io_tab_layout = QVBoxLayout()
        # Mtz input file
        mtz_file_label = QLabel("MTZ Input File")
        self.mtz_file_display = QLineEdit("")
        self.mtz_file_browse = QPushButton("Browse")
        self.mtz_file_browse.setMaximumWidth(100)
        self.mtz_update = QPushButton("Update MTZ file info")
        mtz_columns_label = QLabel("MTZ Column Labels")
        self.mtz_column_f = QComboBox()
        self.mtz_column_f.setMinimumWidth(80)
        self.mtz_column_f.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        mtz_column_f_label = QLabel("F:")
        self.mtz_column_sigf = QComboBox()
        self.mtz_column_sigf.setMinimumWidth(80)
        self.mtz_column_sigf.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        mtz_column_sigf_label = QLabel("SIGF:")
        mtz_columns_layout = QHBoxLayout()
        mtz_columns_layout.addStretch()
        mtz_columns_layout.addWidget(mtz_column_f_label)
        mtz_columns_layout.addWidget(self.mtz_column_f)
        mtz_columns_layout.addWidget(mtz_column_sigf_label)
        mtz_columns_layout.addWidget(self.mtz_column_sigf)
        mtz_info_label = QLabel("Selected MTZ File Info")
        self.mtz_info = QWidget()
        mtz_info_layout = QVBoxLayout()
        self.mtz_info_resolution = QLineInfo("Resolution Range: ")
        self.mtz_info_cell = QLineInfo("Cell Dimensions: ")
        mtz_info_layout.addWidget(self.mtz_info_resolution)
        mtz_info_layout.addWidget(self.mtz_info_cell)
        self.mtz_info.setLayout(mtz_info_layout)
        mtz_space_group_label = QLabel("Use all alternative space groups")
        mtz_space_group_label.setToolTip("Test all possible space groups that are in same laue group"
                                         " as that given in the MTZ file")
        self.mtz_space_group_check = QCheckBox()
        self.mtz_space_group_check.setCheckState(Qt.Checked)
        mtz_layout = QGridLayout()
        mtz_layout.addWidget(mtz_file_label, 0, 0)
        mtz_layout.addWidget(self.mtz_file_display, 0, 1, 1, 3)
        mtz_layout.addWidget(self.mtz_file_browse, 0, 4)
        mtz_layout.addWidget(mtz_columns_label, 1, 0)
        mtz_layout.addLayout(mtz_columns_layout, 1, 1, 1, 2)
        mtz_layout.addWidget(self.mtz_update, 1, 3)
        mtz_layout.addWidget(mtz_info_label, 2, 0)
        mtz_layout.addWidget(self.mtz_info, 2, 1, 1, 4)
        mtz_layout.addWidget(mtz_space_group_label, 3, 0)
        mtz_layout.addWidget(self.mtz_space_group_check, 3, 1)
        # layout
        io_tab_layout.addLayout(mtz_layout)
        io_tab_layout.addStretch()
        self.IOTab.setLayout(io_tab_layout)
        self.mainTab.addTab(self.IOTab, "MTZ")
        self.mainTab.tabBar()
        # Add ensemble tab
        self.add_ensemble_tab = QWidget()
        self.mainTab.addTab(self.add_ensemble_tab, "Add Ensemble")
        # FIXED WIDGETS
        # File prefix name for output
        file_root_label = QLabel("Title")
        self.file_root_edit = QLineEdit("")
        self.file_prefix_info = QLineInfo("Output files will be saved on ")
        self.file_expected_out_name = QLabel("Expected output files are output_phaser"
                                             " (.sol, .1.pdb, .1.mtz) and autoMRphaser.log")
        tip_prefix_layout = QVBoxLayout()
        tip_prefix_layout.addWidget(self.file_prefix_info)
        tip_prefix_layout.addWidget(self.file_expected_out_name)
        self.title_tip = QDialog()
        self.title_tip.setWindowTitle("Output files extra information")
        self.title_tip.setLayout(tip_prefix_layout)
        # Buttons
        tip_button = QPushButton("?")
        tip_button.setMaximumSize(12, 16)
        self.start_button = QPushButton("Run Phaser MR")
        self.add_comp_button = QPushButton("Add item")
        self.add_comp_button.setMaximumWidth(120)
        # composition items
        self.comp = QGroupBox("Composition in the asymmetric unit")
        comp_layout = QVBoxLayout()
        self.comp_widget = QDialog()
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.comp_widget)
        self.comp_items_layout = QVBoxLayout()
        self.comp_items_layout.setAlignment(Qt.AlignTop)
        self.comp_items_layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.comp_items_layout.setSpacing(0)
        self.comp_items_layout.setMargin(6)
        self.comp_items_layout.addWidget(self.add_comp_button)
        self.comp_widget.setLayout(self.comp_items_layout)
        comp_layout.addWidget(scroll_area)
        self.comp.setLayout(comp_layout)
        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(file_root_label)
        buttons_layout.addWidget(tip_button)
        buttons_layout.addWidget(self.file_root_edit)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.start_button)
        # LAYOUT
        layout = QGridLayout()
        layout.addWidget(self.mainTab, 2, 0, 1, 6)
        layout.addWidget(self.comp, 3, 0, 1, 6)
        layout.addLayout(buttons_layout, 4, 0, 1, 6)
        # If this is a standalone program, create its own info and jobs display
        if stand_alone[0]:
            # Display information
            self.InfoDisplay = QTextBrowser()
            set_color(self.InfoDisplay, 255, 255, 204)
            size = 96
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
            layout.addWidget(jobs_scroll, 0, 0, 1, 3)
            layout.addWidget(self.InfoDisplay, 0, 3, 1, 3)
        else:  # Get the pointer to info and jobs displayer
            self.InfoDisplay = stand_alone[1]
            self.jobs_display = stand_alone[2]
        self.setLayout(layout)
        # SIGNALS
        self.connect(self.start_button, SIGNAL("clicked()"),
                     self.process)
        self.connect(tip_button, SIGNAL("clicked()"),
                     self.title_tip.show)
        self.connect(self.add_comp_button, SIGNAL("clicked()"),
                     self.add_comp_item)
        self.connect(self.file_root_edit, SIGNAL("textChanged(QString)"),
                     self.update_file_info)
        self.connect(self.mtz_file_display, SIGNAL("textChanged(QString)"),
                     self.clear_mtz_info)
        self.connect(self.mtz_update, SIGNAL("clicked()"),
                     self.update_mtz_info)
        self.connect(self.mtz_file_browse, SIGNAL("clicked()"),
                     self.get_mtz_file)
        self.connect(self.mainTab, SIGNAL("tabCloseRequested(int)"),
                     self.close_tab)
        self.connect(self.mainTab, SIGNAL("currentChanged(int)"),
                     self.add_ensemble)
        # TITLE
        self.setWindowTitle("Automated MR with Phaser")


# Modified QDialog to display the summary file, and if asked to, open coot
class SummaryDisplay(QDialog):
    def __init__(self, job_dir, job_code, with_solution, form, parent=None):
        super(QDialog, self).__init__(parent)
        summary = os.path.join(job_dir, "autoMRphaser.log")
        if not os.path.isfile(summary):
            form.displayWarning("Phaser summary/log file not found")
            self.deleteLater()
            return
        with open(summary) as f:
            content = f.read()
        self.setWindowTitle("Phaser summary (Job: " + job_code + ")")
        displayer_layout = QVBoxLayout()
        self.text = QTextBrowser()
        self.text.setPlainText(content)
        displayer_layout.addWidget(self.text)
        self.rejectButton = QPushButton("Back")
        displayer_buttons_layout = QHBoxLayout()
        if with_solution:
            self.acceptButton = QPushButton("View Results")
            displayer_buttons_layout.addWidget(self.acceptButton)
            self.connect(self.acceptButton, SIGNAL("clicked()"),
                         self, SLOT("accept()"))
        form.displayInfo("Job " + job_code + " done")
        self.connect(self.rejectButton, SIGNAL("clicked()"),
                     self, SLOT("reject()"))
        displayer_buttons_layout.addWidget(self.rejectButton)
        displayer_layout.addLayout(displayer_buttons_layout)
        self.setLayout(displayer_layout)
        self.resize(600, 280)
        self.data = [job_dir, job_code]
        self.form = form
        self.show()

    def call_coot(self):
        self.form.display_on_coot(self.data[0])
