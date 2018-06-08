#!/usr/bin/env python
from qtpy import QtCore
from ..common.constants import bl13_GUI_ccp4_user, bl13_GUI_ccp4_server
from subprocess import Popen
import os


class BalbesProcessor(QtCore.QThread):
    # SIGNALS
    giving_info = QtCore.Signal(str)
    giving_error = QtCore.Signal(str)
    giving_model = QtCore.Signal(str, float)
    done = QtCore.Signal()

    # METHODS
    def __init__(self, pdb_widget, ensemble, parent=None):
        super(BalbesProcessor, self).__init__(parent)
        self.moveToThread(self)
        self.ensemble = ensemble
        self.pdb_widget = pdb_widget

    def run(self):
        if not os.path.isdir(os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_balbes")):
            os.system("mkdir -p " + os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_balbes"))
        seq_file = str(self.pdb_widget.PDB_balbes_seq_display.displayText())
        if not os.path.isfile(seq_file):
            self.giving_error.emit("The sequence file you provided for Balbes doesn't exist")
        else:
            self.giving_info.emit("Running Balbes...")
            try:
                cmd = "balbes -o " + os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_balbes") +\
                      " -s " + seq_file
                ssh_cmd = ['ssh', '%s@%s' % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server), cmd]
                p = Popen(ssh_cmd)
                p.wait()
                # Search balbes output for PDB name and identity with our sequence
                name = ""
                identity = 0
                with open(os.path.join(self.ensemble.form.tmp_dir,
                                       "tmp_autoMRphaser/tmp_balbes/results/Process_information.txt")) as f:
                    line = "0"
                    count = 0
                    while not line.startswith("The best identity found is ") and count < 100:
                        line = f.readline()
                        count += 1
                    if count == 100:
                        raise Exception("Unexpected Balbes output."
                                        " Maybe there are no models similar enough your sequence")
                    identity = line.split()[5]
                    count = 0
                    while not line.startswith("| PDB_CODE") and count < 100:
                        line = f.readline()
                        count += 1
                    if count == 100:
                        raise Exception("Unexpected Balbes output."
                                        " Maybe there are no models similar enough your sequence")
                    name = line.split("|")[2].split()[0]
                pdb_file = os.path.join(self.ensemble.form.tmp_dir, "tmp_autoMRphaser/tmp_balbes/scratch/model_DB.pdb")
                if not os.path.isfile(pdb_file):
                    raise Exception("Unexpected Balbes behaviour: PDB file ~/" + pdb_file + " not found")
            except Exception as args:
                self.giving_error.emit(str(args))
            else:
                self.giving_info.emit("The best model found by Balbes is " + name + " with identity " + identity)
                self.giving_model.emit(QString(pdb_file), int(100*float(identity)))
        self.done.emit()
        return
