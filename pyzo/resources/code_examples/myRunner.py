"""
Simple example Pyzo tool for running custom commands via some buttons

Place this file "myRunner.py" in one of the following two folders:
a) the "tools" folder inside the Pyzo source directory
b) the "tools" folder inside the Pyzo userdata directory

To obtain the Pyzo source directory and Pyzo userdata directory,
see the "About Pyzo" dialog ("Help -> About Pyzo" in the menu).

You can even interactively modify the object of this class in Pyzo's Logger tool:
    obj = pyzo.toolManager.getTool('myrunner')
    obj._btn1.setText('xyz')
And you will also see the output of normal print commands in the Logger tools.

After changing this file, select "Tools -> Reload tools" in Pyzo's menu.

For more information, look at: https://github.com/pyzo/pyzo/blob/main/pyzo/tools/__init__.py
"""

import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets  # noqa
from pyzo import translate

tool_name = translate("myRunner", "My Runner")
tool_summary = "Run custom actions."

Qt = QtCore.Qt

class MyRunner(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Layout
        self._layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self._layout)

        # Widgets
        btn = QtWidgets.QPushButton(icon=pyzo.icons.script, text='abc')
        btn.clicked.connect(lambda: self.onButtonClicked('btn1'))
        btn.setShortcut('Ctrl+Shift+1')
        btn.setToolTip('insert some text in the editor')
        self._layout.addWidget(btn)
        self._btn1 = btn

        btn = QtWidgets.QPushButton(icon=pyzo.icons.monitor, text='def')
        btn.clicked.connect(lambda: self.onButtonClicked('btn2'))
        btn.setShortcut('Ctrl+Shift+2')
        btn.setToolTip('run some command in the shell')
        self._layout.addWidget(btn)
        self._btn2 = btn

        btn = QtWidgets.QPushButton(icon=pyzo.icons.wand, text='test')
        btn.clicked.connect(lambda: self.onButtonClicked('btn3'))
        btn.setShortcut('Ctrl+Shift+3')
        btn.setToolTip('show a message box')
        self._layout.addWidget(btn)
        self._btn3 = btn

        btn = QtWidgets.QPushButton(icon=pyzo.icons.wrench_orange, text='')
        btn.clicked.connect(lambda: self.onButtonClicked('btn4'))
        btn.setShortcut('Ctrl+Shift+4')
        btn.setToolTip('show a message box')
        self._layout.addWidget(btn)
        self._btn4 = btn

        self._layout.addStretch()

    def onButtonClicked(self, s):
        print(self.__class__.__name__, 'onButtonClicked', s)
        if s == 'btn1':
            # manipulate the text of the current editor
            editor = pyzo.editors.getCurrentEditor()
            editor.insertPlainText(
                'This text will be inserted\nat the cursor pos of the current editor\n'
            )
        elif s == 'btn2':
            # run a command in the current Python shell
            shell = pyzo.shells.getCurrentShell()
            shell.executeCode('myvar = 123\nprint(myvar + 4)', '<myrunner>')
        else:
            QtWidgets.QMessageBox.information(self, tool_name,'button "{}" clicked'.format(s))

    def close(self):
        pass  # do some clean-up here if necessary
