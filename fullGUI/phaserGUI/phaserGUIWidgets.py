#!/usr/bin/env python
import urllib, os, shlex, subprocess
#from PyQt4.QtCore import Qt, SIGNAL, SLOT, QTimer
#from PyQt4.QtGui import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, \
#                        QDialog, QLabel, QLineEdit, QComboBox, QSpinBox, \
#                        QStackedWidget, QFileDialog, QCheckBox
from qtpy.QtCore import Qt, SIGNAL, SLOT, QTimer
from qtpy.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, \
                        QDialog, QLabel, QLineEdit, QComboBox, QSpinBox, \
                        QStackedWidget, QFileDialog, QCheckBox
from ..common.layout_utils import IDENSelector, num_widget, QLineInfo, CustomObj
from ..common.constants import bl13_GUI_ccp4_user, bl13_GUI_ccp4_server
from .phaserGUIBalbesProcessor import BalbesProcessor


class EnsembleWidget(QWidget):
    def __init__(self, app, form, num, parent=None):
        super(EnsembleWidget, self).__init__(parent)
        # VARS
        self.app = app
        self.form = form
        self.number = num
        self.true_pdb = ""
        self.pdb_is_alright = True
        # PDB model title
        self.pdb_widget = PDBModelWidget(self)
        self.pdb_title = QLineInfo("PDB Title: ")
        pdb_tip_button = QPushButton('?')
        pdb_tip_button.setMaximumSize(12, 16)
        pdb_title_info = QWidget()
        pdb_title_info.setLayout(QHBoxLayout())
        pdb_title_info.layout().setMargin(0)
        pdb_title_info.layout().addWidget(self.pdb_title)
        pdb_title_info.layout().addWidget(pdb_tip_button)
        pdb_title_info.layout().addStretch()
        # PDB file information
        self.actual_pdb_file = QLineInfo("The pdb file that will be actually used is:\n",
                                         "\nThis model will be created based on your configuration input\n"
                                         "After Phaser has run, this model will be saved with the results")
        tip_pdb_layout = QVBoxLayout()
        tip_pdb_layout.addWidget(self.actual_pdb_file)
        self.pdb_tip = QDialog()
        self.pdb_tip.setWindowTitle("PDB model file extra information")
        self.pdb_tip.setLayout(tip_pdb_layout)
        # Inspect pdb button
        self.inspect_pdb_button = QPushButton("Inspect PDB")
        # Calculate comp button
        self.update_comp = QPushButton("Calculate composition")
        self.update_comp.setToolTip("Calculates the composition for this ensemble and adds it to composition tab")
        # PDB structure info
        self.pdb_info = PDBAdditionalWidget(self)
        # LAYOUT
        ensemble_layout = QVBoxLayout()
        ensemble_layout.addWidget(self.pdb_widget)
        ensemble_layout.addWidget(pdb_title_info)
        ensemble_layout.addWidget(self.pdb_info)
        button_layout = QHBoxLayout()
        button_layout.setMargin(0)
        button_layout.addWidget(self.inspect_pdb_button)
        button_layout.addStretch()
        button_layout.addWidget(self.update_comp)
        ensemble_layout.addLayout(button_layout)
        ensemble_layout.setSpacing(6)
        self.setLayout(ensemble_layout)
        # TIMERS
        self.define_actual_timer = QTimer()
        self.define_actual_timer.setSingleShot(True)
        self.connect(self.define_actual_timer, SIGNAL("timeout()"), self.create_define_actual)
        # SIGNALS
        self.connect(self.inspect_pdb_button, SIGNAL("clicked()"),
                     self.inspect_pdb)
        self.connect(self.update_comp, SIGNAL("clicked()"),
                     self.calculate_comp)
        self.connect(pdb_tip_button, SIGNAL("clicked()"),
                     self.pdb_tip.show)

    # METHODS
    def create_define_actual(self):
        if self.true_pdb == "":
            return
        if not self.pdb_info.non_default.isChecked():
            self.actual_pdb_file.setText(os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_pdb/tmp_first_model." +
                                                      str(self.number) + ".pdb"))
            return
        pdb_out = os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_pdb/tmp_model." + str(self.number) + ".pdb")
        try:
            self.form.start_button.setEnabled(False)
            model_list = self.pdb_info.model_stack.findChildren(QWidget, "model")
            current_model = 0
            for model in model_list:
                if model.use_model.isChecked():
                    current_model = model
                    break
            if not current_model:
                raise Exception("You must specify the model to use")
            else:
                # Create new pdb with pdbcur
                # Input keyword file
                with open(os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"), "w") as f:
                    f.write("lvmodel /" + str(current_model.number) + "\n")
                    chain_list = current_model.chain_stack.findChildren(QWidget, "chain")
                    some_chain = 0
                    for chain in chain_list:
                        if chain.use_chain.isChecked():
                            some_chain += 1
                            span_list = chain.chain_residues.findChildren(QWidget, "span")
                            for span in span_list:
                                bot = span.range.split("-")[0]
                                top = span.range.split("-")[1]
                                if not span.use_span.isChecked():
                                    f.write("delresidue " + chain.name + "/" + bot + "-" + top + "\n")
                                else:
                                    to = span.to_spin.value()
                                    _from = span.from_spin.value()
                                    if not _from == int(bot):
                                        f.write("delresidue " + chain.name + "/" + bot + "-" + str(_from-1) + "\n")
                                    if not to == int(top):
                                        f.write("delresidue " + chain.name + "/" + str(to+1) + "-" + top + "\n")
                        else:
                            f.write("delchain " + chain.name + "\n")
                    if some_chain == 0:
                        raise Exception("You must use at least one chain")
                # Run pdbcur
                os.system('ssh %s@%s "pdbcur xyzin %s xyzout %s < %s > %s"'
                          % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, self.true_pdb, pdb_out,
                             os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"),
                             os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out")))
                if not os.path.isfile(pdb_out):
                    raise Exception("PDB model output from pdbcur lost")
        except Exception as args:
            self.form.displayError(args)
            self.form.displayWarning("PDB model based on your specification hasn't been created properly")
            self.pdb_is_alright = False
            self.actual_pdb_file.setText(os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_pdb/tmp_first_model." +
                                                      str(self.number) + ".pdb"))
            self.form.start_button.setEnabled(True)
        else:
            self.actual_pdb_file.setText(pdb_out)
            if not self.pdb_is_alright:
                self.form.displayInfo("PDB model built from your specifications successfully")
                self.pdb_is_alright = True
            self.form.start_button.setEnabled(True)
                
    def ready_create_define_actual(self):
        self.form.start_button.setEnabled(False)
        self.define_actual_timer.start(1000)

    def inspect_pdb(self):
        pdb_file = self.actual_pdb_file.getText()
        if pdb_file == "":
            pdb_file = self.true_pdb
            if pdb_file == "":
                return
        if os.path.isfile(pdb_file):
            os.system("cp " + pdb_file + " " + os.path.join(self.form.tmp_dir,
                                                            "tmp_autoMRphaser/tmp_pdb/inspected.pdb"))
            command = "xterm -e \"kwrite " + os.path.join(self.form.tmp_dir,
                                                          "tmp_autoMRphaser/tmp_pdb/inspected.pdb") + "\""
            subprocess.Popen(shlex.split(command))
        else:
            self.form.displayError("PDB file " + pdb_file + " doesn't exist")

    def calculate_comp(self):
        if self.define_actual_timer.isActive():
            QTimer.singleShot(250, self.calculate_comp)
            return
        pdb_in = self.actual_pdb_file.getText()
        if pdb_in == "":
            return
        if not os.path.isfile(pdb_in):
            self.form.displayError("PDB file introduced to calculate composition doesn't exist")
            return            
        mw = 0
        num_res = 0
        num_in_asu = self.pdb_widget.num_search.value()
        try:
            self.form.start_button.setEnabled(False)
            # Run rwcontents
            with open(os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.in"), "w") as f:
                f.write("END")
            os.system('ssh %s@%s "rwcontents xyzin %s < %s > %s"'
                      % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, pdb_in,
                         os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.in"),
                         os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.out")))
            # Retrieve results
            with open("" + os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.out"), "r") as f:
                line = "0"
                count = 0
                while not line.startswith(" Number of amino-acids residues =") and count < 1000:
                    line = f.readline()
                    count += 1
                if count == 1000:
                    raise Exception("Unexpected rwcontents output. You may check ~/" +
                                    os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.out"))
                num_res = int(line.split()[5])
                count = 0
                while not line.startswith(" Molecular Weight of protein:") and count < 50:
                    line = f.readline()
                    count += 1
                if count == 50:
                    raise Exception("Unexpected rwcontents output. You may check ~/" +
                                    os.path.join(self.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_rw.out"))
                mw = int(line.split()[4].split(".")[0])
        except Exception as args:
            self.form.displayError(args)
            self.form.start_button.setEnabled(True)
        else:
            # Display them on the form
            self.form.add_comp_item(mw=mw, num_res=num_res, num_in_asu=num_in_asu)
            self.form.displayInfo("Protein composition calculated successfully")
            self.form.start_button.setEnabled(True)


# ENSEMBLE INCLUDES:
class PDBModelWidget(QWidget):
    def __init__(self, ensemble, parent=None):
        super(PDBModelWidget, self).__init__(parent)
        # LAYOUT OPTIONS
        self.setFixedHeight(50)
        self.setMinimumWidth(860)
        # WIDGETS
        # Option box
        self.PDBCombo = QComboBox()
        self.PDBCombo.insertItems(0, ["PDB Model", "Balbes"])
        # Individual widgets ->
        self.PDBfile = QWidget()  # 1
        pdb_file_layout = QHBoxLayout()
        self.pdb_file_display = QLineEdit("")
        self.pdb_file_browse = QPushButton("Browse")
        pdb_file_id_label = QLabel("Identity")
        pdb_file_id_label.setToolTip('Identity between model and sample (%)')
        self.PDBfileId = IDENSelector()
        pdb_file_layout.addWidget(self.pdb_file_display)
        pdb_file_layout.addWidget(self.pdb_file_browse)
        pdb_file_layout.addWidget(pdb_file_id_label)
        pdb_file_layout.addWidget(self.PDBfileId)
        self.PDBfile.setLayout(pdb_file_layout)
        self.pdb_balbes = QWidget()  # 2
        pdb_balbes_layout = QHBoxLayout()
        pdb_balbes_fasta_label = QLabel("Sequence:")
        self.PDB_balbes_seq_display = QLineEdit("")
        self.pdb_balbes_fasta_browse = QPushButton("Browse")
        self.balbes_run_button = QPushButton("Run Balbes")
        pdb_balbes_layout.addWidget(pdb_balbes_fasta_label)
        pdb_balbes_layout.addWidget(self.PDB_balbes_seq_display)
        pdb_balbes_layout.addWidget(self.pdb_balbes_fasta_browse)
        pdb_balbes_layout.addWidget(self.balbes_run_button)
        self.pdb_balbes.setLayout(pdb_balbes_layout)
        self.stackedPDB = QStackedWidget()  # Stacked widget
        self.stackedPDB.addWidget(self.PDBfile)
        self.stackedPDB.addWidget(self.pdb_balbes)
        # Num to search for
        self.num_search = QSpinBox()
        self.num_search.setRange(1, 50)
        num_label = QLabel("Number")
        num_label.setToolTip("Number of copies of this ensemble to search for in the asymmetric unit")
        num_search_layout = QHBoxLayout()
        num_search_layout.addWidget(num_label)
        num_search_layout.addWidget(self.num_search)
        self.num_search_wid = QWidget()
        self.num_search_wid.setLayout(num_search_layout)
        # LAYOUT
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.PDBCombo)
        layout.addWidget(self.stackedPDB)
        layout.addWidget(num_label)
        layout.addWidget(self.num_search_wid)
        self.setLayout(layout)
        # SIGNALS
        self.connect(self.PDBCombo, SIGNAL("activated(int)"),
                     self.stackedPDB, SLOT("setCurrentIndex(int)"))
        self.connect(self.stackedPDB, SIGNAL("currentChanged(int)"),
                     self.PDBCombo, SLOT("setCurrentIndex(int)"))
        self.connect(self.pdb_file_display, SIGNAL("textChanged(QString)"),
                     self.ready_update_pdb)
        self.connect(self.pdb_file_browse, SIGNAL("clicked()"),
                     self.get_pdb_file)
        self.connect(self.pdb_balbes_fasta_browse, SIGNAL("clicked()"),
                     self.get_balbes_seq_file)
        # VARS
        self.ensemble = ensemble
        # TIMERS
        self.update_pdb_timer = QTimer()
        self.update_pdb_timer.setSingleShot(True)
        self.connect(self.update_pdb_timer, SIGNAL("timeout()"), self.update_pdb_info)
        # THREADS
        self.balbes_processor = BalbesProcessor(self, self.ensemble)
        self.connect(self.balbes_run_button, SIGNAL("clicked()"),
                     self.balbes_start)
        self.connect(self.balbes_processor, SIGNAL("giving_model(QString,double)"),
                     self.balbes_info, Qt.QueuedConnection)
        self.connect(self.balbes_processor, SIGNAL("done()"),
                     self.balbes_end, Qt.QueuedConnection)
        self.connect(self.balbes_processor, SIGNAL("giving_info(QString)"),
                     self.ensemble.form.displayInfo, Qt.QueuedConnection)
        self.connect(self.balbes_processor, SIGNAL("giving_error(QString)"),
                     self.ensemble.form.displayError, Qt.QueuedConnection)

    # METHODS
    def update_pdb_info(self):
        #pdb_file = str(self.pdb_file_display.displayText())
        pdb_file = str(self.pdb_file_display.text())
        print 'Extracting info from %s' % pdb_file
        if pdb_file == "":
            return
        if len(pdb_file) == 4:
            self.ensemble.form.displayInfo("Input seen as PDB id")
            if not self.get_pdb_from_id(pdb_file):
                return
            self.ensemble.form.displayInfo("Did not work, trying as a file/path")
        if not os.path.isfile(pdb_file):
            self.ensemble.form.displayError("The PDB file you introduced doesn't exist")
            self.clear_pdb()
            return
        # Get the title of the pdb
        title = ""
        try:
            count = 0
            with open(pdb_file, "r") as f:
                line = f.readline()
                while not line.startswith("TITLE") and count < 50:
                    line = f.readline()
                    count += 1
                #if count == 50:
                #    raise Exception("TITLE of the pdb not found")
                while line.startswith("TITLE"):
                    title += line[10:-1]
                    line = f.readline()
                if title == "": title = 'NoTitle'
            # Prepare a model without solvent nor hetatoms
            pdb_out = os.path.join(self.ensemble.form.tmp_dir,
                                   "tmp_autoMRphaser/tmp_pdb/tmp_first_model." + str(self.ensemble.number) + ".pdb")
            # Input keyword file
            with open("" + os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"), "w") as f:
                f.write("delsolvent")
            # Run pdbcur
            os.system('ssh %s@%s "pdbcur xyzin %s xyzout %s < %s > %s"'
                       % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, pdb_file, pdb_out,
                          os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"),
                          os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out")))
            # Remove hetatoms
            with open(pdb_out, "r") as f:
                lines = f.readlines()
            previous_line = ''
            with open(pdb_out, "w") as f:
                for line in lines:
                    if line.startswith('HETATM'):
                        pass
                    elif previous_line.startswith('HETATM') and line.startswith('ANISOU'):
                        pass
                    else:
                        f.write(line)
                    previous_line = line
        except Exception as args:
            self.ensemble.form.displayError(args)
            self.clear_pdb()
            self.ensemble.form.displayWarning("There was an error with your PDB file, please check it carefully")
            return
        else:
            self.ensemble.actual_pdb_file.setText(pdb_out)
            self.ensemble.true_pdb = pdb_out
            self.ensemble.pdb_title.setText(title)
            pdb_file = pdb_out
        pdb_info = CustomObj()
        pdb_info.models = []
        try:
            # Run pdbcur
            with open("" + os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"), "w") as f:
                f.write("summarise")
            os.system('ssh %s@%s "pdbcur xyzin %s < %s > %s"'
                      % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, pdb_file,
                         os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.in"),
                         os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out")))
            # Retrieve results
            with open("" + os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out"), "r") as f:
                line = "0"
                count = 0
                # Get the number of models
                while not line.startswith(" Number of models") and count < 100:
                    line = f.readline()
                    count += 1
                if count == 100:
                    raise Exception("Unexpected pdbcur output. You may check ~/" +
                                    os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out"))
                model_number = int(line.split()[4])
                pdb_info.models = []
                model = 1
                while model <= model_number:
                    model_info = CustomObj()
                    model_info.chains = []
                    model_info.number = model
                    count = 0
                    # Get the number of chains
                    while not line.startswith("   Model " + str(model) + " has ") and count < 100:
                        line = f.readline()
                        count += 1
                    if count == 100:
                        raise Exception("Unexpected pdbcur output. You may check ~/" +
                                        os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out"))
                    chain_number = int(line.split()[3])
                    chain = 1
                    while chain <= chain_number:
                        chain_info = CustomObj()
                        chain_info.number = chain
                        count = 0
                        # Get info about each chain
                        while not line.startswith("     Chain ") and count < 100:
                            line = f.readline()
                            count += 1
                        if count == 100:
                            raise Exception("Unexpected pdbcur output. You may check ~/" +
                                            os.path.join(self.ensemble.form.tmp_dir,
                                                         "tmp_autoMRphaser/tmp_runfiles/tmp_pdbcur.out"))
                        chain_info.name = line.split("\"")[1]
                        chain_info.res_num = line.split()[3]
                        line = f.readline()
                        chain_info.span_num = line.split()[1]
                        chain_info.spans = line.split()[3:]
                        model_info.chains.append(chain_info)
                        chain += 1
                    pdb_info.models.append(model_info)
                    model += 1
        except Exception as args:
            print 'There was an error with your PDB file, please check it carefully'
            self.ensemble.form.displayError(args)
            self.clear_pdb()
        else:
            # Display results on form
            print 'Xamurai found', len(model_info.chains), ' chains in your pdb'
            self.ensemble.pdb_info.self_update(pdb_info)
            self.ensemble.form.displayInfo("PDB information processed successfully")

    def ready_update_pdb(self):
        #print 'ready_update_pdb'
        self.update_pdb_timer.start(1250)

    def clear_pdb(self):
        self.ensemble.true_pdb = ""
        self.ensemble.actual_pdb_file.setText("")
        self.ensemble.pdb_title.setText("")
        self.ensemble.pdb_info.clear_pdb_info()

    def get_pdb_file(self):
        file = QFileDialog.getOpenFileName(self, "Select PDB file", self.ensemble.form.work_dir, "PDB (*.pdb)")
        self.pdb_file_display.setText(file)

    def get_pdb_from_id(self, name):
        try:
            if name == "" or "_" in name:
                raise Exception("You must provide a valid PDB name")
            pdb_file = os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_pdb/downloaded_" + name + ".pdb")
            if not os.path.isfile(pdb_file):
                man = urllib.URLopener()  # Download the pdb file
                self.ensemble.form.displayInfo("Downloading " + name + ".pdb form PDB")
                man.retrieve("http://files.rcsb.org/view/" + name + ".pdb", pdb_file)
                if not os.path.isfile(pdb_file):
                    raise Exception("PDB file not found (download error or not in PDB website)")
        except Exception as args:
            self.ensemble.form.displayError(args)
            return 1
        else:
            self.pdb_file_display.setText(pdb_file)
            return 0

    def get_balbes_seq_file(self):
        file = QFileDialog.getOpenFileName(self, "Select FASTA file", self.ensemble.form.work_dir, "FASTA (*.seq)")
        self.PDB_balbes_seq_display.setText(file)

    def balbes_start(self):
        self.balbes_run_button.setEnabled(False)
        self.balbes_run_button.setText("Running...")
        self.balbes_processor.start()
        self.ensemble.form.start_button.setEnabled(False)
        self.ensemble.setEnabled(False)

    def balbes_info(self, name, identity):
        self.pdb_file_display.setText(name)
        self.PDBfileId.setValue(identity)
        self.stackedPDB.setCurrentIndex(0)

    def balbes_end(self):
        self.balbes_run_button.setEnabled(True)
        self.balbes_run_button.setText("Run Balbes")
        self.ensemble.form.start_button.setEnabled(True)
        self.ensemble.setEnabled(True)


class PDBAdditionalWidget(QWidget):
    def __init__(self, ensemble, parent=None):
        super(PDBAdditionalWidget, self).__init__(parent)
        # LAYOUT OPTIONS
        self.setMinimumHeight(60)
        self.setMaximumHeight(100)
        # WIDGETS
        self.non_default = QCheckBox()
        self.non_default.setChecked(True)
        self.models = QComboBox()
        self.models.setMinimumWidth(80)
        self.models.hide()
        self.model_stack = QStackedWidget()
        # LAYOUT
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Use modified settings"))
        layout.addWidget(self.non_default)
        layout.addWidget(self.models)
        layout.addWidget(self.model_stack)
        layout.addStretch()
        self.setLayout(layout)
        # VARS
        self.ensemble = ensemble
        # SIGNALS
        self.connect(self.non_default, SIGNAL("stateChanged(int)"), self.models.setEnabled)
        self.connect(self.non_default, SIGNAL("stateChanged(int)"), self.model_stack.setEnabled)
        self.connect(self.non_default, SIGNAL("stateChanged(int)"), self.ensemble.create_define_actual)
        # Start disabled
        self.non_default.setChecked(False)

    def self_update(self, obj):
        self.clear_pdb_info()
        for model in obj.models:
            self.models.addItem("Model " + str(model.number))
            use_model = QCheckBox()
            use_model.setChecked(True)
            combo = QComboBox()
            chain_stack = QStackedWidget()
            for chain in model.chains:
                combo.addItem("Chain " + chain.name)
                use_chain = QCheckBox()
                use_chain.setChecked(True)
                use_chain.setObjectName("use_chain")
                chain_residues = QWidget()
                chain_res_layout = QVBoxLayout()
                chain_res_layout.setMargin(0)
                for span in chain.spans:
                    chain_span_full = QHBoxLayout()
                    chain_span_widget = QWidget()
                    chain_span_layout = QHBoxLayout()
                    chain_span_layout.setMargin(0)
                    chain_span_layout.addWidget(QLabel("Span (" + span + ") use"))
                    chain_span_layout.addWidget(QLabel("from"))
                    from_spin = QSpinBox()
                    from_spin.setRange(int(span.split("-")[0]), int(span.split("-")[1]))
                    chain_span_layout.addWidget(from_spin)
                    chain_span_layout.addWidget(QLabel("to"))
                    to_spin = QSpinBox()
                    to_spin.setRange(int(span.split("-")[0]), int(span.split("-")[1]))
                    # Correlated spins
                    self.connect(to_spin, SIGNAL("valueChanged(int)"), from_spin.setMaximum)
                    self.connect(from_spin, SIGNAL("valueChanged(int)"), to_spin.setMinimum)
                    to_spin.setValue(int(span.split("-")[1]))
                    from_spin.setValue(int(span.split("-")[0]))
                    # ######
                    self.connect(to_spin, SIGNAL("valueChanged(int)"), self.ensemble.ready_create_define_actual)
                    self.connect(from_spin, SIGNAL("valueChanged(int)"), self.ensemble.ready_create_define_actual)
                    chain_span_layout.addWidget(to_spin)
                    chain_span_widget.setLayout(chain_span_layout)
                    use_span = QCheckBox()
                    use_span.setChecked(True)
                    self.connect(use_span, SIGNAL("stateChanged(int)"), chain_span_widget.setEnabled)
                    self.connect(use_span, SIGNAL("stateChanged(int)"), self.ensemble.ready_create_define_actual)
                    # Declare vars to access later
                    chain_span_widget.setObjectName("span")
                    chain_span_widget.use_span = use_span
                    chain_span_widget.range = span
                    chain_span_widget.from_spin = from_spin
                    chain_span_widget.to_spin = to_spin
                    # Add to layout
                    chain_span_full.addWidget(chain_span_widget)
                    chain_span_full.addWidget(QLabel("Use span"))
                    chain_span_full.addWidget(use_span)
                    chain_res_layout.addLayout(chain_span_full)
                chain_residues.setLayout(chain_res_layout)
                chain_widget = QWidget()
                chain_layout = QHBoxLayout()
                chain_layout.setMargin(0)
                chain_layout.addWidget(QLabel("Use chain"))
                chain_layout.addWidget(use_chain)
                chain_layout.addWidget(chain_residues)
                chain_layout.addStretch()
                chain_widget.setLayout(chain_layout)
                chain_widget.setObjectName("chain")
                # Declare vars to access later
                chain_widget.name = chain.name
                chain_widget.use_chain = use_chain
                chain_widget.chain_residues = chain_residues
                # Add widget to stack
                chain_stack.addWidget(chain_widget)
                self.connect(use_chain, SIGNAL("stateChanged(int)"), chain_residues.setEnabled)
                self.connect(use_chain, SIGNAL("stateChanged(int)"), self.ensemble.ready_create_define_actual)
            self.connect(combo, SIGNAL("activated(int)"), chain_stack, SLOT("setCurrentIndex(int)"))
            self.connect(use_model, SIGNAL("stateChanged(int)"), combo.setEnabled)
            self.connect(use_model, SIGNAL("stateChanged(int)"), chain_stack.setEnabled)
            self.connect(use_model, SIGNAL("stateChanged(int)"), self.ensemble.ready_create_define_actual)
            model_widget = QWidget()
            layout = QHBoxLayout()
            layout.setMargin(0)
            layout.addWidget(QLabel("Use model"))
            layout.addWidget(use_model)
            layout.addWidget(combo)
            layout.addWidget(chain_stack)
            layout.addStretch()
            model_widget.setLayout(layout)
            model_widget.setObjectName("model")
            # Declare vars to access later
            model_widget.use_model = use_model
            model_widget.number = model.number
            model_widget.chain_stack = chain_stack
            # Add widget to stack
            self.model_stack.addWidget(model_widget)
        self.connect(self.models, SIGNAL("activated(int)"), self.model_stack, SLOT("setCurrentIndex(int)"))
        self.models.show()

    def clear_pdb_info(self):
        self.non_default.setChecked(False)
        self.models.clear()
        self.models.hide()
        for widget in self.model_stack.findChildren(QWidget):
            widget.deleteLater()


# For all the ensembles there's one composition, composed of various:
class ProteinCompWidget(QWidget):
    def __init__(self, form, parent=None):
        super(ProteinCompWidget, self).__init__(parent)
        # LAYOUT OPTIONS
        self.setMaximumHeight(44)
        self.setMinimumWidth(826)
        self.setMaximumWidth(826)
        # WIDGETS
        # Option box for stacked
        self.CompCombo = QComboBox()
        self.CompCombo.insertItems(0, ["Molecular Weight", "Sequence (FASTA)", "Number of Residues"])
        # Individual widgets ->
        self.MW_widget = QSpinBox()  # 1
        self.MW_widget.setRange(0, 1e9)
        self.MW_widget.setSingleStep(100)
        self.MW_widget.setSuffix(" DA")
        self.MW_widget.setMaximumWidth(120)
        self.seq_widget = QWidget()  # 2
        seq_layout = QHBoxLayout()
        seq_layout.setMargin(0)
        self.Comp_seq_display = QLineEdit("")
        self.Comp_seq_browse = QPushButton("Browse")
        seq_layout.addWidget(self.Comp_seq_display)
        seq_layout.addWidget(self.Comp_seq_browse)
        self.num_res_widget = QSpinBox()  # 3
        self.num_res_widget.setRange(0, 1e5)
        self.num_res_widget.setSingleStep(5)
        self.num_res_widget.setMaximumWidth(120)
        self.seq_widget.setLayout(seq_layout)
        self.stackedComp = QStackedWidget()  # Stacked widget
        self.stackedComp.addWidget(self.MW_widget)
        self.stackedComp.addWidget(self.seq_widget)
        self.stackedComp.addWidget(self.num_res_widget)
        self.stackedComp.setMinimumWidth(280)
        # Num
        self.num = num_widget()
        # Type
        type_label = QLabel("Type: ")
        self.type = QComboBox()
        self.type.insertItems(0, ["Protein", "Nucleic acid"])
        # Remove button
        self.remove_button = QPushButton("Remove Item")
        # Vars
        self.form = form
        self.to_be_deleted = False
        # LAYOUT
        layout = QHBoxLayout()
        layout.addWidget(type_label)
        layout.addWidget(self.type)
        layout.addWidget(self.num)
        layout.addWidget(self.CompCombo)
        layout.addWidget(self.stackedComp)
        layout.addSpacing(0)
        layout.addWidget(self.remove_button)
        self.setLayout(layout)
        # SIGNALS
        self.connect(self.CompCombo, SIGNAL("activated(int)"),
                     self.stackedComp, SLOT("setCurrentIndex(int)"))
        self.connect(self.Comp_seq_browse, SIGNAL("clicked()"),
                     self.get_seq_file)
        self.connect(self.remove_button, SIGNAL("clicked()"),
                     self.self_remove)

    # METHODS
    def get_seq_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select FASTA file", ".", "FASTA files (*.seq)")
        self.Comp_seq_display.setText(filename)

    def self_remove(self):
        self.setEnabled(False)
        self.hide()
        self.to_be_deleted = True
        QTimer.singleShot(25, self.form.delete_comp_item)
