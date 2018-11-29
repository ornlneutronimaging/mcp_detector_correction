from subprocess import check_output
import subprocess
import glob
import os
from os.path import expanduser
import sys
import numpy as np
import pickle
import shutil

try:
    from PyQt4.QtGui import QFileDialog
    from PyQt4 import QtCore, QtGui
    from PyQt4.QtGui import QMainWindow, QTableWidgetItem, QDialog, QProgressBar, QApplication
except ImportError:
    from PyQt5.QtWidgets import QFileDialog
    from PyQt5 import QtCore, QtGui
    from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QTableWidgetItem, QDialog, QProgressBar

from ui.main_window import Ui_MainWindow as UiMainWindow
from ui.configuration import Ui_Dialog as UiDialog

user_home = expanduser("~")
CONFIG_FILE = os.path.join(user_home, '.mcp_config')
EXE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'code', 'TPX_CubeRead.exe')

LIST_PREFIX_TO_COPY = ['ShutterCount.txt', 'ShutterTimes.txt', 'Spectra.txt', 'SummedImg.fits']
DEBUG = False


class Interface(QMainWindow):

    config_working_folder = ''
    config_output_folder = ''
    config_time_out = 35

    list_folders = []

    tutorial_web_link = "https://neutronimaging.pages.ornl.gov/"

    def __init__(self, parent=None):

        QMainWindow.__init__(self, parent=parent)
        self.ui = UiMainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Anton's MCP Detector Efficiency Correction UI")
        self.statusbar()

        self.load_config_file()
        self.check_run_correction_button_status()

    # Event handlers

    def row_selected(self):
        self.check_run_correction_button_status()

    def select_parent_folder_clicked(self):
        parent_folder = str(QFileDialog.getExistingDirectory(caption='Select Working Folder ...',
                                                             options=QFileDialog.ShowDirsOnly,
                                                             directory=self.config_working_folder))

        if not parent_folder:
            return

        self.populate_list_of_working_folders(parent_folder=parent_folder)
        self.config_working_folder = parent_folder
        self.check_run_correction_button_status()

    def select_output_folder_clicked(self):
        output_folder = str(QFileDialog.getExistingDirectory(caption='Select Output Folder ...',
                                                             directory=self.config_working_folder))

        if not output_folder:
            return

        self.ui.output_folder_label.setText(output_folder)
        self.config_output_folder = output_folder
        self.check_run_correction_button_status()

    def edit_config_clicked(self):
        o_config = Configuration(parent=self,
                                 working_folder=self.config_working_folder,
                                 output_folder=self.config_output_folder)
        o_config.exec_()  # to make window modal
        o_config.show()

    def add_logbook(self, text):
        self.ui.logbook.append(text)

    def run_correction_clicked(self):
        list_folders_selected = self.get_list_folders_selected()
        output_folder = self.config_output_folder
        self.add_logbook("output folder selected is {}".format(output_folder))
        self.add_logbook("time out is: {}".format(self.config_time_out))

        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # first evaluate how many processes we will run
        nbr_command_to_run = self.evaluate_number_of_commands_to_run(list_folders_selected)
        self.ui.eventProgress.setMinimum(1)
        nbr_steps_total = nbr_command_to_run * 5 # 5 steps per loop
        self.ui.eventProgress.setMaximum(nbr_steps_total)
        self.ui.eventProgress.setValue(1)
        self.ui.eventProgress.setVisible(True)

        QApplication.processEvents()

        # built command lines
        counter = 1
        for _folder in list_folders_selected:
            self.add_logbook("> Working with folder: {}".format(_folder))
            _first_file_full_name = self.get_first_file_full_name(folder=_folder)
            local_output_folder = os.path.join(output_folder, os.path.basename(os.path.dirname(_folder)) + "_corrected")
            self.add_logbook(" output folder will be: {}".format(local_output_folder))

            # create folder if not there yet
            if not os.path.exists(local_output_folder):
                if not DEBUG:
                    os.mkdir(local_output_folder)

            for _first_file in _first_file_full_name:

                self.add_logbook("-> Working with first file: {}".format(_first_file))
                cmd = EXE_FILE + ' "{}"'.format(_first_file)
                self.add_logbook("  Running command line!")
                self.add_logbook("  cmd: {}".format(cmd))

                try:
                    if not DEBUG:
                        subprocess.run(cmd, shell=True, check=True, timeout=self.config_time_out)
                except:
                    pass

                counter += 1
                self.ui.eventProgress.setValue(counter)
                QApplication.processEvents()

                # full name of folder created by code
                correction_folder_full_name = os.path.join(os.path.dirname(_first_file), 'Corrected')
                self.add_logbook("  Full name of folder created by Anton's code: {}".format(correction_folder_full_name))

                # get file base name
                _base_file_name_for_folder_creation = self.get_base_file_name(_first_file)
                self.add_logbook(" _ base_file_name_for_folder_creation is: {}".format(_base_file_name_for_folder_creation))

                # rename Corrected folder into final name
                # if folder already there, remove it first
                data_set_folder = os.path.join(local_output_folder, _base_file_name_for_folder_creation)
                data_set_folder = data_set_folder + os.path.sep

                # make sure the output folder does not exist yet
                if os.path.exists(data_set_folder):
                    if not DEBUG:
                        shutil.rmtree(data_set_folder)
#                correction_folder_new_location_full_name = os.path.join(local_output_folder, 'Corrected')

                counter += 1
                self.ui.eventProgress.setValue(counter)
                QApplication.processEvents()

                # self.add_logbook("  Renaming that folder into new name")
                # self.add_logbook("   - full input folder name: {}".format(correction_folder_new_location_full_name))
                # self.add_logbook("   - full new folder name: {}".format(data_set_folder))

                # move corrected data into new location #FIXME (replace copy by move in final version)
                self.add_logbook("  Moving Corrected folder to final location")
                self.add_logbook("   - full input folder name: {}".format(correction_folder_full_name))
                self.add_logbook("   - full output folder name: {}".format(data_set_folder))
                if not DEBUG:
                    shutil.copytree(correction_folder_full_name, data_set_folder)
                ##shutil.move(correction_folder_full_name, local_output_folder)

                counter += 1
                self.ui.eventProgress.setValue(counter)
                QApplication.processEvents()

                # also copy the 4 files from source file
                working_folder = os.path.dirname(_first_file)
                full_base_name = os.path.join(working_folder, _base_file_name_for_folder_creation)
                for _add_file in LIST_PREFIX_TO_COPY:
                    full_file = "{}_{}".format(full_base_name, _add_file)
                    self.add_logbook("  Copy file {} to new location {}".format(full_file, data_set_folder))
                    self.add_logbook("   file exists? {}".format(os.path.exists(full_file)))
                    self.add_logbook("   folder exists?{}".format(os.path.exists(data_set_folder)))

                    if not DEBUG:
                        shutil.copy(full_file, data_set_folder)

                counter += 1
                self.ui.eventProgress.setValue(counter)
                QApplication.processEvents()

                # remove Corrected folder created by Anton's code
                self.add_logbook("   Remove input corrected folder {}".format(correction_folder_full_name))
                if not DEBUG:
                    shutil.rmtree(correction_folder_full_name)

                counter += 1
                self.ui.eventProgress.setValue(counter)
                QApplication.processEvents()

                QApplication.processEvents()

        self.ui.eventProgress.setVisible(False)
        QApplication.processEvents()

        QApplication.restoreOverrideCursor()

    def help_clicked(self):
        import webbrowser
        webbrowser.open(self.tutorial_web_link)

    # Utilities

    @staticmethod
    def get_base_file_name(_file_name):
        _base_name = os.path.basename(_file_name)
        [prefix, _] = _base_name.split("_00000.fits")
        return prefix

    def statusbar(self):
        self.ui.eventProgress = QProgressBar(self.ui.statusbar)
        self.ui.eventProgress.setMinimumSize(300, 20)
        self.ui.eventProgress.setMaximumSize(300, 20)
        self.ui.eventProgress.setVisible(False)
        self.ui.statusbar.addPermanentWidget(self.ui.eventProgress)

    def evaluate_number_of_commands_to_run(self, list_folders_selected):
        nbr_command = 0
        for _folder in list_folders_selected:
            _first_file_full_name = self.get_first_file_full_name(folder=_folder)
            nbr_command += len(_first_file_full_name)
        return nbr_command

    def get_first_file_full_name(self, folder=''):
        if folder:
            list_first_files = glob.glob(os.path.join(self.config_working_folder, folder, "*_00000.fits"))
            return list_first_files
        else:
            return []

    def load_config_file(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'rb') as handle:
                _cfg = pickle.load(handle)

#                print(_cfg['working_folder'])
                try:
                    self.config_working_folder = _cfg['working_dir']
                    self.config_output_folder = _cfg['output_dir']
                    self.config_time_out = np.float(_cfg['time_out'])
                except KeyError:
                    return

        self.ui.output_folder_label.setText(self.config_output_folder)

    @staticmethod
    def is_parameter_defined(parameter):
        if parameter == '':
            return False
        return True

    def check_run_correction_button_status(self):
        """will enable the run correction button only if all the conditions are met
        - list of folders selected
        - output correctly defined in the configuration window
        """
        # if we are missing at least  one of the config info, we disabled the button
        if (not self.is_parameter_defined(self.config_output_folder)) or \
            (not self.is_parameter_defined(self.config_working_folder)):
            self.ui.run_correction_button.setEnabled(False)
            return

        # if table is empty, we disabled the button
        if self.ui.tableWidget.rowCount() == 0:
            self.ui.run_correction_button.setEnabled(False)
            return

        # if no folder selected
        selection_table = self.ui.tableWidget.selectedRanges()
        if selection_table == []:
            self.ui.run_correction_button.setEnabled(False)
            return

        self.ui.run_correction_button.setEnabled(True)

    # def check_list_row_selected(self, list_row_selected=[]):
    #     ui = self.ui.tableWidget
    #     for _row in list_row_selected:
    #         _text = str(ui.item(_row, 0).text())
    #         _new_text = _text + u'\u2713'
    #         new_item = QTableWidgetItem(_new_text)
    #         new_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
    #         ui.setItem(_row, 0, new_item)

    @staticmethod
    def get_list_row_selected(ui=None):
        if ui is None:
            return []

        list_row_selected = []
        list_ranges = ui.selectedRanges()
        for _range in list_ranges:
            top_row = _range.topRow()
            bottom_row = _range.bottomRow()
            _row = top_row
            while _row <= bottom_row:
                list_row_selected.append(_row)
                _row += 1

        list_row_selected = list(list_row_selected)
        list_row_selected.sort()

        return list_row_selected

    def get_list_folders_selected(self):
        list_row_selected = self.get_list_row_selected(ui=self.ui.tableWidget)
        return [self.list_folders[i] for i in list_row_selected]

    def populate_list_of_working_folders(self, parent_folder='./'):
        list_folders = self.get_list_folders(parent_folder=parent_folder)
        self.list_folders = list_folders

        self.clear_table(ui=self.ui.tableWidget)

        for _index, _folder in enumerate(list_folders):
            self.ui.tableWidget.insertRow(_index)
            _base_dir = os.path.basename(os.path.dirname(_folder))
            item = QTableWidgetItem(_base_dir)
            item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.ui.tableWidget.setItem(_index, 0, item)

    @staticmethod
    def clear_table(ui=None):
        if ui is None:
            return

        nbr_row = ui.rowCount()
        if nbr_row > 0:
            for _ in np.arange(nbr_row):
                ui.removeRow(0)

    @staticmethod
    def get_list_folders(parent_folder='./'):
        return glob.glob(parent_folder + '/*/')


class Configuration(QDialog):

    executable = ''
    working_folder = ''
    output_folder = ''

    def __init__(self, parent=None,
                 working_folder='',
                 output_folder=''):

        QDialog.__init__(self, parent=parent)
        self.ui = UiDialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Configurations")

        self.parent = parent
        self.working_folder = working_folder
        self.output_folder = output_folder
        self.populate_config_widgets()

    # event handlers

    def time_out_slider_moved(self, value):
        self.ui.time_out_label.setText(str(value))

    def time_out_slider_clicked(self):
        slider_value = str(self.ui.time_out_slider.value())
        self.ui.time_out_label.setText(slider_value)

    # def select_executable(self):
    #     if self.executable_file:
    #         executable_folder = os.path.dirname(self.executable_file)
    #     else:
    #         executable_folder = './'
    #
    #     executable = QFileDialog.getOpenFileName(caption='Select Executable ...',
    #                                                  directory=executable_folder,
    #                                                  filter=("Exe (*.exe)"))
    #     if executable[0] == "":
    #         return
    #
    #     self.ui.executable_label.setText(str(executable[0]))
    #     self.executable = str(executable[0])

    def select_default_input_folder(self):
        input_folder = str(QFileDialog.getExistingDirectory(caption='Select Default Input Folder ...',
                                                            directory=self.working_folder))

        if not input_folder:
            return

        self.ui.input_folder_label.setText(input_folder)
        self.working_folder = input_folder

    def select_default_output_folder(self):
        output_folder = str(QFileDialog.getExistingDirectory(caption='Select Default Output Folder ...',
                                                             directory=self.output_folder))

        if not output_folder:
            return

        self.ui.output_folder_label.setText(output_folder)
        self.output_folder = output_folder

    def cancel_clicked(self):
        self.close()

    def closeEvent(self, event=None):
        pass

    def save_clicked(self):
        config_file_name = CONFIG_FILE
        working_folder = self.working_folder
        output_folder = self.output_folder
        time_out = str(self.ui.time_out_slider.value())

        _dir = {'working_dir': working_folder,
                'output_dir': output_folder,
                'time_out': time_out}

        with open(config_file_name, 'wb') as handle:
            pickle.dump(_dir, handle, protocol=pickle.HIGHEST_PROTOCOL)

        self.parent.config_working_folder = working_folder
        self.parent.config_output_folder = output_folder
        self.parent.config_time_out = time_out

        self.parent.ui.output_folder_label.setText(output_folder)

        self.parent.check_run_correction_button_status()
        self.close()

    # tools
    def populate_config_widgets(self):
        """retrieve the hidden config ascii file (if there) and update the ui"""
        self.ui.input_folder_label.setText(self.working_folder)
        self.ui.output_folder_label.setText(self.output_folder)
        self.ui.time_out_slider.setValue(np.int(self.parent.config_time_out))
        self.ui.time_out_label.setText(str(self.parent.config_time_out))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    o_interface = Interface()
    o_interface.show()
    sys.exit(app.exec_())
