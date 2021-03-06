#!/usr/bin/env python
import os
from subprocess import Popen, PIPE
from PyQt4.QtCore import QString, SIGNAL
from .phaserGUIWidgets import EnsembleWidget, ProteinCompWidget
from ..common.processor import FormProcessor, JobWidget, pyqtSignal
from ..common.constants import bl13_GUI_cluster_server, bl13_GUI_cluster_user,\
                               bl13_GUI_phaser_jobs_dir_ending


class PhaserProcessor(FormProcessor):
    # SIGNALS
    giving_result = pyqtSignal(QString, QString, int, int)

    # METHODS
    def __init__(self, form, parent=None):
        super(PhaserProcessor, self).__init__(form, parent)
        # Run number and name
        self.run_num = form.runNum
        self.name = ""
        self.work_dir = ""

    def exit(self, int_return_code=0):
        self.giving_result.emit(self.work_dir, self.name, self.run_num, int_return_code)
        self.deleteLater()

    def work(self):
        # Receiving parameters from the Form
        try:
            # Title (File prefix)
            if self.form.root_name == "_" + bl13_GUI_phaser_jobs_dir_ending:
                raise Exception("You must specify a Title")
            # MTZ
            mtz_in = str(self.form.mtz_file_display.displayText())
            f = str(self.form.mtz_column_f.currentText())
            sigf = str(self.form.mtz_column_sigf.currentText())
            if not mtz_in:
                raise Exception("MTZ file is mandatory")
            if not os.path.isfile(mtz_in):
                raise Exception("The MTZ file you specified doesn't exist")
            mtz_input = "\nHKLI " + mtz_in + "\nLABI F=" + f + " SIGF=" + sigf
            if self.form.mtz_space_group_check.isChecked():
                mtz_input += " SGAL SELE ALL"
            # PDB
            pdb_item_list = self.form.mainTab.findChildren(EnsembleWidget)
            if len(pdb_item_list) == 0:
                raise Exception("You must provide at least one ensemble")
            pdb_list_models = []
            pdb_input = ""
            search_input = ""
            pdb_count = 0
            for item in pdb_item_list:
                # PDB model
                pdb_file = item.actual_pdb_file.getText()
                if not pdb_file:
                    raise Exception("You must provide a PDB file")
                if not os.path.isfile(pdb_file):
                    raise Exception("The PDB file you specified doesn't exist")
                identity = str(item.pdb_widget.PDBfileId.value())
                pdb_used = "pdb_model_" + str(item.number) + ".pdb"
                pdb_list_models.append([pdb_file, pdb_used])
                # Number
                num_to_search = str(item.pdb_widget.num_search.value())
                pdb_input += "\nENSE " + self.form.root_name + "_aim" + str(pdb_count) +\
                             " PDB " + pdb_used + " IDEN 0." + identity
                search_input += "\nSEAR ENSE " + self.form.root_name + "_aim" + str(pdb_count) +\
                                " NUM " + num_to_search
                pdb_count += 1
            # COMP
            comp_item_list = self.form.comp_widget.findChildren(ProteinCompWidget)
            molecule_num = len(comp_item_list)
            if molecule_num == 0:
                raise Exception("You must provide at least one composition item for each ensemble")
            comp_input = ""
            for comp_item in comp_item_list:
                comp_input += "\n"
                if comp_item.type.currentText() == "Protein":
                    item_composition = "COMP PROT "
                elif comp_item.type.currentText() == "Nucleic acid":
                    item_composition = "COMP NUCL "
                else:
                    raise Exception("Unexpected GUI option")
                if comp_item.CompCombo.currentText() == "Molecular Weight":
                    mw = comp_item.MW_widget.value()
                    if mw == 0:
                        raise Exception("You must provide a non zero Molecular Weight")
                    item_composition += "MW " + str(mw)
                elif comp_item.CompCombo.currentText() == "Sequence (FASTA)":
                    fasta_file = comp_item.Comp_seq_display.displayText()
                    if not fasta_file:
                        raise Exception("You must provide a Sequence file ")
                    if not os.path.isfile(fasta_file):
                        raise Exception("The sequence file you provided doesn't exist")
                    item_composition += "SEQ " + fasta_file
                elif comp_item.CompCombo.currentText() == "Number of Residues":
                    num_res = comp_item.num_res_widget.value()
                    if num_res == 0:
                        raise Exception("You must provide a positive number of residues")
                    item_composition += "NRES " + str(num_res)
                else:
                    raise Exception("Unexpected GUI option")
                item_composition += " NUM " + str(comp_item.num.num_box.value())
                comp_input += item_composition
        except Exception as args:
            # Print Error, Stop and Enable the Form
            self.giving_error.emit(str(args))
            self.exit(1)
        else:
            self.name = self.form.root_name
            self.work_dir = self.form.file_prefix_info.getText()
            # Creating output dir if necessary
            if not os.path.isdir(self.work_dir):
                os.system("mkdir -p " + self.work_dir)
            # Copy models to use
            for pair in pdb_list_models:
                os.system("cp " + pair[0] + " " + os.path.join(self.work_dir, pair[1]))
            # Make link to used mtz
            os.system("ln -s " + os.path.realpath(mtz_in) + " " + os.path.join(self.work_dir, "mtz_input.mtz"))
            # Enable form
            self.info_read.emit(self.work_dir)
            # Writing scripts to execute
            exec_string = "phaser << eof\nTITLe " + self.name + "_" + str(self.run_num) + "\nMODE MR_AUTO" +\
                          mtz_input + pdb_input + comp_input + search_input +\
                          "\nROOT phaser_output\neof"
            with open(os.path.join(self.work_dir, "phaserMR_runfile"), "w") as f:
                f.write(exec_string)
            commands = "ssh %s@%s\ncd %s\n" % (bl13_GUI_cluster_user, bl13_GUI_cluster_server, self.work_dir) + \
                       "srun /mnt/hpcsoftware/share/phenix/phenix.phaser < 'phaserMR_runfile' > 'autoMRphaser.log'"
            # Execute script
            self.giving_info.emit("Running Phaser... (Job " + self.name + "_" + str(self.run_num) + ")")
            try:
                p = Popen("/bin/bash", stdin=PIPE)
                p.stdin.write(commands)
                p.stdin.close()
                self.log_is_ready.emit()
                p.wait()
            except Exception as args:
                # Print Error, Stop and Enable the Form
                self.giving_error.emit(str(args))
                self.exit(2)
            else:
                # END
                self.exit(0)


class PhaserJobWidget(JobWidget):

    def set_view_button(self):
        self.button.setText("Coot")
        self.connect(self.button, SIGNAL("clicked()"), self.view_coot)
        self.button.setEnabled(True)

    def view_coot(self):
        self.form.display_on_coot(self.work_dir)
