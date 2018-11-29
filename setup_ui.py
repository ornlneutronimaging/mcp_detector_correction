import os
import py2exe





















class UiBuilder(object):
    pyuic = ''

    def __init__(self, ui_name=''):
        self.define_pyuic_to_run()
        self.ui_name = os.path.abspath('ui_template/' + ui_name)
        [base, ext] = os.path.splitext(ui_name)
        py_name = base + '.py'
        self.py_name = os.path.abspath('ui/' + py_name)

        # run command
        print(self.pyuic + ' ' + self.ui_name + ' -o ' + self.py_name)
        os.system(self.pyuic + ' ' + self.ui_name + ' -o ' + self.py_name)

    def define_pyuic_to_run(self):
        try:
            from PyQt4 import QtGui
            self.pyuic = 'pyuic4'
        except:
            from PyQt5 import QtGui
            self.pyuic = 'pyuic5'


if __name__ == "__main__":
    o_builder = UiBuilder(ui_name='main_window.ui')
    o_builder = UiBuilder(ui_name='configuration.ui')