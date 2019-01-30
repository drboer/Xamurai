import os, shlex, time
from subprocess import Popen, PIPE, STDOUT
#from PyQt4.QtCore import QString, pyqtSignal
from PyQt4.QtCore import pyqtSignal
from ..common.processor import FormProcessor, JobWidget
from ..common.constants import bl13_GUI_ccp4_user, bl13_GUI_ccp4_server,\
                               bl13_GUI_cluster_user, bl13_GUI_cluster_server,\
                               bl13_GUI_setup_bor, ARCIMBOLDO_path                 


class ArcimboldoProcessor(FormProcessor):
    # SIGNALS
    giving_result = pyqtSignal(str, str, int, int)

    # METHODS
    def __init__(self, form, parent=None):
        super(ArcimboldoProcessor, self).__init__(form, parent)
        # Run number and name
        self.run_num = self.form.run_num
        self.name = str(self.form.root_name)
        self.work_dir = os.path.join(str(self.form.work_dir), self.name, str(self.run_num))

    def exit(self, int_return_code=0):
        self.giving_result.emit(self.work_dir, self.name, self.run_num, int_return_code)
        self.deleteLater()

    def work(self):
        # Get data from the form
        try:
            # Title
            if self.name == "" or self.run_num == 0:
                raise Exception("You must specify a Title. It will determine the output directory")
            # MTZ
            mtz_in = str(self.form.mtz_file_display.displayText())
            if self.form.mtz_column_stack.currentIndex() == 0:  # I
                i_column = str(self.form.mtz_column_i.currentText())
            else:  # F
                f_column = str(self.form.mtz_column_f.currentText())
            sig_column = str(self.form.mtz_column_sig.currentText())
            mtz_resolution = self.form.lowest_resolution
            mtz_cell_unit = self.form.mtz_info_cell.getText()
            space_group = self.form.space_group
            if not mtz_in:
                raise Exception("MTZ file is mandatory")
            if not os.path.isfile(mtz_in):
                raise Exception("The MTZ file you specified doesn't exist")
            if mtz_resolution > 2.5:
                raise Exception("The resolution range of your .mtz is too high to run Arcimboldo")
            run_button_text = str(self.form.run_cb.currentText())
            if run_button_text == "Arcimboldo":
                job_type = 1
            else:
                job_type = 0
            # USER INPUT
            # FASTA
            seq_in = str(self.form.seq_display.displayText())
            if not seq_in:
                raise Exception("Sequence file is mandatory")
            if not os.path.isfile(seq_in):
                raise Exception("The sequence file you specified doesn't exist")
            # HORIZ
            horiz_in = str(self.form.prediction_display.displayText())
            if job_type == 1:
                if not horiz_in:
                    raise Exception("Prediction .horiz file is mandatory, otherwise run Psipred first")
                if not os.path.isfile(horiz_in):
                    raise Exception("The prediction file you specified doesn't exist")
            # Creating output dir and we are ready to start
            if not os.path.isdir(self.work_dir):
                self.giving_info.emit("Creating " + self.work_dir + " directory for output")
                os.system("mkdir -p " + self.work_dir)
            else:
                raise Exception("The directory " + self.work_dir + "already exists. Stopped to prevent overriding data")
        except Exception as args:
            # Print Error, Stop and Enable the Form
            self.giving_error.emit(str(args))
            self.exit(1)
        # If all the data is ok, proceed with the job
        else:
            # Enable form we have got all we need
            self.info_read.emit(self.work_dir)
            try:
                # Describe the type of job
                with open(os.path.join(self.work_dir, "job_type.txt"), 'w') as f:
                    f.write("The type of this job is:\n\n" + run_button_text)
                # Copy input files
                mtz_file = os.path.join(self.work_dir, "input_reflections.mtz")
                os.system("ln -s " + os.path.realpath(mtz_in) + " " + mtz_file)
                ##################################################################################
                # Create the .hkl
                # RB 20170727: do we need this?
                hkl_file = os.path.join(self.work_dir, "input_reflections.hkl")
                with open(os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "mtz2khl.in"), "w") as f:
                    if self.form.mtz_column_stack.currentIndex() == 0:  # I
                        f.write("OUTPUT SHELX\nLABIN I=" + i_column + " SIGI=" + sig_column + "\nEND")
                    else:  # F
                        f.write("OUTPUT SHELX\nLABIN FP=" + f_column + " SIGFP=" + sig_column + "\nEND")
                #print 'ssh %s@%s "mtz2various HKLIN %s HKLOUT %s < %s > %s"' \
                #          % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, mtz_in, hkl_file, \
                #             os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "mtz2khl.in"), \
                #             os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "mtz2khl.out"))
                os.system('ssh %s@%s "mtz2various HKLIN %s HKLOUT %s < %s > %s"'
                          % (bl13_GUI_ccp4_user, bl13_GUI_ccp4_server, mtz_in, hkl_file,
                             os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "mtz2khl.in"),
                             os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "mtz2khl.out")))
                # End of create.hkl file? ###############################################################
                
                # Collect data for the configuration .bor file for arcimboldo
                
                # Read the sequence file
                molecular_weight = self.read_sequence_file(seq_in)
                
                # Get the estimated number of components from MATHEWS_COEF (CCP4i)
                maxprob_number_components = get_matthews_coef_lst(self, mtz_cell_unit, space_group, molecular_weight)
                
                if maxprob_number_components == 0:
                    maxprob_number_components = 1
                    self.giving_warn.emit("An error occurred trying to determine the number of components using"
                                          "matthews_coef. Using 1 as a default value")
                
            except Exception as args:
                self.giving_error.emit(str(args))
                self.giving_warn.emit("Problem in analysing sequence file or getting matthews coef")
                self.exit(2)

            try:
                # Get the secondary structure prediction
                result_file = os.path.join(self.work_dir, "input_fasta.horiz")
                if job_type == 0:
                    # Run Psipred on the sequence file to get secondary structure prediction
                    self.update_job_status.emit(self.name + "_" + str(self.run_num), "Running Psipred")
                    psipred_log = os.path.join(self.work_dir, 'psipred.log')
                    cmd = "/beamlines/bl13/commissioning/software/psipred/BLAST+/runpsipredplus input_fasta.seq"
                    # # This is to run locally
                    # p = Popen(shlex.split(cmd)), cwd=self.work_dir, stdout=open(psipred_log, 'w'))
                    # # This is to run on cluster
                    print "ssh %s@%s\ncd %s\n" % (bl13_GUI_cluster_user, bl13_GUI_cluster_server, self.work_dir) +\
                               "srun --mem=16G " + cmd + " > " + psipred_log 
                    cmd_list = "ssh %s@%s\ncd %s\n" % (bl13_GUI_cluster_user, bl13_GUI_cluster_server, self.work_dir) +\
                               "srun --mem=16G " + cmd + " > " + psipred_log  
                               # Apparently, Psipred uses a lot of memory, so we need to specify it (srun --mem= )
                    p = Popen("/bin/bash", stdin=PIPE)
                    p.stdin.write(cmd_list)
                    p.stdin.close()
                    # #
                    p.wait()
                elif job_type == 1:
                    # Get the psipred prediction file from input
                    os.system("cp " + horiz_in + " " + result_file)
                if not os.path.isfile(result_file):
                    raise Exception("Psipred prediction file " + result_file + " not found")
                psipred_prediction = process_psipred_output(result_file)  # A list with lengths of helices
                # We sort the list, larger helices first, to optimize arcimboldo search
                psipred_prediction.sort(reverse=True)
                # We check that the prediction is sufficient to run Arcimboldo
                if not minimal_requisites(psipred_prediction, mtz_resolution):
                    raise Exception("The secondary structure prediction from Psipred does not provide enough or not"
                                    "long enough helix fragments to start a Arcimboldo job")
                self.giving_info.emit("Job " + self.name + "_" + str(self.run_num) + " is preparing Arcimboldo")
                # Arcimboldo .bor file
                bor_file = "[CONNECTION]\n##Option to run locally, uncomment, and comment other lines in connection\n"
                bor_file += "#distribute_computing: multiprocessing\n"
                bor_file += "distribute_computing: remote_grid\n"
                bor_file += "setup_bor_path: " + bl13_GUI_setup_bor + "\n"

                bor_file += "[GENERAL]\nworking_directory= " + self.work_dir + "\n"
                bor_file += "mtz_path: " + os.path.realpath(mtz_file) + "\n"
                bor_file += "hkl_path: " + hkl_file + "\n"

                arcimboldo_job_name = self.name.replace("_arcimboldo", "")
                bor_file += "[ARCIMBOLDO]\nname_job: " + arcimboldo_job_name + "_" + str(self.run_num) + "\n"
                bor_file += "molecular_weight: " + str(molecular_weight) + "\n"
                if self.form.mtz_column_stack.currentIndex() == 0:  # I
                    bor_file += "i_label: " + i_column + "\nsigi_label: " + sig_column + "\n"
                else:  # F
                    bor_file += "f_label: " + f_column + "\nsigf_label: " + sig_column + "\n"
                bor_file += "number_of_component: " + str(num_components) + "\n"

                bor_file += "fragment_to_search: " + str(len(psipred_prediction) * num_components) + "\n"
                i = 0
                helix_num = 1
                while i < len(psipred_prediction):
                    j = 0
                    while j < num_components:  # We search for helices once per component in the cell
                        bor_file += "helix_length_" + str(helix_num) + ": " + str(psipred_prediction[i]) + "\n"
                        helix_num += 1
                        j += 1
                    i += 1

                if helix_num > 5:
                    self.giving_warn.emit("More than 5 helices to search for, may take a long while...")

                bor_file += "[LOCAL]\n"\
                            "path_local_phaser: /beamlines/bl13/commissioning/software/phenix_arcimboldo/phenix.phaser"\
                            "\n"\
                            "path_local_shelxe: /beamlines/bl13/commissioning/software/shelx_arcimboldo/shelxe"

                with open(os.path.join(self.work_dir, "config.bor"), "w") as f:
                    f.write(bor_file)
                if run_button_text == "Psipred":  # User didn't ask for arcimboldo, END
                    self.exit(0)
                    return  # Need return, otherwise keeps running, in the other exit cases, try clause stops it OK
            except Exception as args:
                self.giving_error.emit(str(args))
                self.giving_warn.emit("Arcimboldo job did not launch")
                self.exit(2)
            else:
                # Execute Arcimboldo
                try:
                    cmd = ARCIMBOLDO_path + ' config.bor'
                    log_file = open(os.path.join(self.work_dir, "terminal_output.log"), 'w')
                    p = Popen(shlex.split(cmd), cwd=self.work_dir, stdout=log_file, stderr=STDOUT)
                    time.sleep(60)  # Inform
                    self.giving_info.emit("Running Arcimboldo... (Job " + self.name + "_" + str(self.run_num) + ")")
                    self.update_job_status.emit(self.name + "_" + str(self.run_num), "Running Arcimboldo")
                    self.log_is_ready.emit()
                    p.wait()
                    p.terminate()
                    time.sleep(10)
                    p.kill()
                except Exception as args:
                    # Print Error, Stop and Enable the Form
                    self.giving_error.emit(str(args))
                    self.exit(2)
                else:
                    # END
                    self.exit(0)

    def read_sequence_file(self, seqfilen):
        # Copy input files
        os.system("cp " + seqfilen + " " + os.path.join(self.work_dir, "input_fasta.seq"))
        # Get the molecular weight from the sequence file
        with open(os.path.join(self.work_dir, "input_fasta.seq"), "r") as f:
            lines = [line.rstrip('\n') for line in f]
        if lines[0].startswith(">"):
            sequence = "".join(lines[1:])
        else:
            sequence = "".join(lines)
        molecular_weight = 18.01524  # Water
        for X in sequence:
            molecular_weight += amino_acid_weight[X]
        return molecular_weight
        
    def get_matthews_coef_lst(self, mtz_cell_unit, space_group, molecular_weight):
        with open(os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "matthews_coef.in"),"w") as f:
            f.write("CELL " + " ".join(mtz_cell_unit.split(" ")[:3]) + "\nSYMM " + space_group + "\n" +
                            "\nMOLW " + str(molecular_weight) + "\nAUTO\nEND")
        os.system('ssh %s@%s "matthews_coef  < %s > %s"' %(bl13_GUI_ccp4_user, bl13_GUI_ccp4_server,
                            os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "matthews_coef.in"),
                            os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "matthews_coef.out")))
        with open(os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles", "matthews_coef.out"), "r") as f:
            lines = f.readlines()
        i = 0
        while not lines[i].startswith("Nmol/asym  Matthews Coeff  %solvent") and i < 150:
            i += 1
            if i == 150:
                raise Exception("Unexpected output from matthews_coef, you may want to check " +
                                  os.path.join(self.form.tmp_dir, "tmp_arcimboldo/tmp_runfiles",
                                                 "matthews_coef.out"))
            i += 2
            num_components = 0
            max_prob = 0
            while not lines[i].startswith("_"):
                numbers = lines[i].split()
                if float(numbers[3]) > max_prob:
                    num_components = int(numbers[0])
                i += 1
        return num_components
                    
                    
class ArcimboldoJobWidget(JobWidget):
    def __init__(self, name, num, work_dir, form, parent=None):
        super(ArcimboldoJobWidget, self).__init__(name, num, work_dir, form, parent)
        self.set_null_button()


def process_psipred_output(horiz_file):
    # Open .horiz file and get the important lines
    lines = [line.rstrip('\n') for line in open(horiz_file)]
    i = 0
    while not lines[i].startswith("Conf: "):
        i += 1
    conf_line = lines[i].replace("Conf: ", "")
    pred_line = lines[i + 1].replace("Pred: ", "")
    while i < len(lines) - 7:
        i += 6
        conf_line += lines[i]
        pred_line += lines[i + 1]
    # Now find the helix fragments
    helix_list = []
    i = 0
    while i < len(pred_line):
        if pred_line[i] == "H":
            start = i
            while pred_line[i] == "H":
                i += 1
            end = i - 1
            if end - start + 1 >= 10:  # Ignore the helix if it's too short to be used (less than 10 residues long)
                helix_list.append([start, end])
        i += 1
    helix_list = cut_helix_fragments(helix_list, conf_line)
    return [helix[1] - helix[0] + 1 for helix in helix_list]


def cut_helix_fragments(helix_list, conf_values):
    # Cut the helix fragments using the criteria based on their length, and confidence value
    for helix in helix_list:
        length = helix[1] - helix[0] + 1
        if length > 26:
            max_remove = 8
        elif length > 10:
            max_remove = min(4, length - 10)
        else:
            max_remove = 0
        while max_remove > 0:
            if conf_values[helix[1]] > 3 and conf_values[helix[0]] > 3:
                max_remove = 0
            elif conf_values[helix[1]] < conf_values[helix[0]] and conf_values[helix[1]] < 4:
                helix[1] -= 1
                max_remove -= 1
            elif conf_values[helix[0]] < 4:
                helix[0] += 1
                max_remove -= 1
    return helix_list


def minimal_requisites(prediction, resolution):
    if resolution < 1.2:
        if len(prediction) >= 1:
            return True
    elif resolution < 1.6:
        count = 0
        for helix in prediction:
            if helix >= 16:
                return True
            elif helix >= 10:
                count += 1
                if count >= 2:
                    return True
    elif resolution < 2.2:
        count = 0
        for helix in prediction:
            if helix >= 18:
                return True
            elif helix >= 10:
                count += 1
                if count >= 3:
                    return True
    elif resolution < 2.8:
        count = 0
        for helix in prediction:
            if helix >= 20:
                return True
            elif helix >= 10:
                count += 1
                if count >= 4:
                    return True
    else:
        return False


amino_acid_weight = {'A': 71.0788, 'C': 103.1388, 'D': 115.0886, 'E': 129.1155, 'F': 147.1766,
                     'G': 57.0519, 'H': 137.1411, 'I': 113.1594, 'K': 128.1741, 'L': 113.1594,
                     'M': 131.1926, 'N': 114.1038, 'P': 97.1167, 'Q': 128.1307, 'R': 156.1875,
                     'S': 87.0782, 'T': 101.1051, 'V': 99.1326, 'W': 186.2132, 'Y': 163.1760}
