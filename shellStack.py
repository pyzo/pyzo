#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Module shellStack
Implements the stack of shells. Also implements the nifty debug button
and a dialog to edit the shell configurations. 
"""

import os, sys, time
from PyQt4 import QtCore, QtGui

import iep
from shell import PythonShell
from iepLogging import print

ssdf = iep.ssdf

class ShellStack(QtGui.QWidget):
    """ The shell stack widget provides a stack of shells,
    and makes sure they are of the correct width such that 
    they have exactly 80 columns. 
    """
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # create sizer
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout.setSpacing(0)
        
        # create tab widget
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.setTabPosition(QtGui.QTabWidget.North) # North/South
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True) # Prevents extra frame being drawn
        
        # add widgets
        self._boxLayout.addWidget(self._tabs, 1)
        #self._boxLayout.addStretch(1)
        
        # set layout
        self.setLayout(self._boxLayout)
        
        # Create debug control (which is not layed out)
        dbc = DebugControl(self)
        self._tabs.setCornerWidget(dbc, QtCore.Qt.TopRightCorner)
        #dbc.move(0,0)
        
        # make callbacks
        self._tabs.currentChanged.connect(self.onCurrentChanged)
        
    
    def __iter__(self):
        i = 0
        while i < self._tabs.count():
            w = self._tabs.widget(i)
            i += 1
            yield w 
    
    
    def onCurrentChanged(self, index):
        """ When another shell is selected, update some things. 
        """
        # Update state info
        if index<0:
            iep.main.setWindowIcon(iep.icon)
        else:
            shell = self._tabs.widget(index)
            if shell:
                self.onShellStateChange(shell)
                self.onShellDebugStateChange(shell)
    
    
    def onShellStateChange(self, shell):
        """ Called when the shell state changes, and is called
        by onCurrentChanged. Sets the mainwindow's icon if busy.
        """
        if True:
            
            # Determine the text to display in the tab
            if shell._state == 'Ready':
                stateText = 'Python {}'.format(shell._version)
            else:
                tmp = 'Python {} ({})'
                stateText = tmp.format(shell._version, shell._state)
            
            # Show status in tab text            
            i = self._tabs.indexOf(shell)
            self._tabs.setTabText(i, stateText)
        
        if shell is self.getCurrentShell():
            
            # Update icon
            if shell._state in ['Busy']:
                iep.main.setWindowIcon(iep.iconRunning)
            else:
                iep.main.setWindowIcon(iep.icon)
    
    
    def onShellDebugStateChange(self, shell):
        """ Called when the shell debug state changes, and is called
        by onCurrentChanged. Sets the debug button.
        """
        if shell is self.getCurrentShell():
            # Update debug info
            if shell._debugState:
                debugState = shell._debugState.split(';')
                self._tabs.cornerWidget().setTrace(debugState)
            else:
                self._tabs.cornerWidget().setTrace(None)
    
    
    def addShell(self, shellInfo=None):
        """ addShell()
        Add a shell to the widget. """
        shell = PythonShell(self._tabs, shellInfo)
        self._tabs.addTab(shell, 'Python')
        # Bind to signals
        shell.stateChanged.connect(self.onShellStateChange)
        shell.debugStateChanged.connect(self.onShellDebugStateChange)
        # Focus on it
        self._tabs.setCurrentWidget(shell)
        shell.setFocus()
    
    
    def getCurrentShell(self):
        """ getCurrentShell()
        Get the currently active shell.
        """
        w = None
        if self._tabs.count():
            w = self._tabs.currentWidget()
        if not w:
            return None
        elif hasattr(w, '_disconnectPhase'):
            return None
        else:
            return w
    

class DebugControl(QtGui.QToolButton):
    """ A button that can be used for post mortem debuggin. 
    """
    
    def __init__(self, parent):
        QtGui.QToolButton.__init__(self, parent)
        
        # Set text and tooltip
        self.setText('Post mortem')
        self.setToolTip("Start/Stop post mortem debugging.")
        
        # Set mode
        self.setPopupMode(self.InstantPopup)
        
        # Bind to triggers
        self.pressed.connect(self.onPressed)
        self.triggered.connect(self.onTriggered)
    
    
    def onPressed(self):
        # Also fires after clicking on an action and (if there's a
        # menu) clicking outside the button and menu 
        
        if not self.menu():
            
            # Initiate debugging
            shell = iep.shells.getCurrentShell()
            if shell:
                shell.processLine('db start')    
    
    
    def onTriggered(self, action):
        
        # Get shell
        shell = iep.shells.getCurrentShell()
        if not shell:
            return
        
        if action._index < 1:
            # Stop debugging
            shell.processLine('db stop')
        else:
            # Change stack index
            if not action._isCurrent:
                shell.processLine('db frame {}'.format(action._index))
            # Open file and select line
            if True:
                line = action.text().split(': ',1)[1]
                self.debugFocus(line)
    
    
    def setTrace(self, trace):
        """ Set the stack trace. This method is called from
        the shell that receives the trace via its status channel
        directly from the interpreter. 
        If trace is None, removes the trace
        """
        
        if not trace:
            
            # Remove trace
            self.setMenu(None)
            self.setText('Post mortem')
        
        else:
            
            # Get the current frame
            current = int(trace[0])
            theAction = None
            
            # Create menu and add __main__
            menu = QtGui.QMenu(self)
            self.setMenu(menu)
            action = menu.addAction('MAIN: stop debugging')
            action._index = 0
            
            # Fill trace
            for i in range(1, len(trace)):
                action = menu.addAction('{}: {}'.format(i, trace[i]))
                action._index = i
                action._isCurrent = False
                if i == current:
                    action._isCurrent = True
                    theAction = action
                    
            
            # Highlight current item and set the button text
            if theAction:
                menu.setDefaultAction(theAction)
                #self.setText(theAction.text().ljust(20))
                i = theAction._index
                text = "Stack Trace ({}/{}):  ".format(i, len(trace)-1)
                self.setText(text)
    
    
    def debugFocus(self, lineFromDebugState):
        """ debugFocus(lineFromDebugState)
        Open the file and show the linenr of the given lineFromDebugState.
        """
        # Get filenr and item
        try:
            tmp = lineFromDebugState.split(', in ')[0].split(', line ')
            filename = tmp[0][len('File '):].strip('"')
            linenr = int(tmp[1].strip())
        except Exception:
            return 'Could not focus!'
        # Cannot open <console>            
        if filename == '<console>':
            return 'Stack frame is <console>.'
        # Go there!
        result = iep.editors.loadFile(filename)
        if not result:
            return 'Could not open file where the error occured.'
        else:
            editor = result._editor
            i1 = editor.getPositionFromLinenr(linenr-1)
            i2 = editor.getPositionFromLinenr(linenr)
            editor.setPosition(i1)
            editor.setAnchor(i2)
            editor.ensureCursorVisible()


class ShellInfoDialogEntries(QtGui.QWidget):
    """ A page in the tab widget of the shell configuration dialog. 
    """
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Init
        offset1 = 20
        offset2 = offset1
        desWidth = offset2 - offset1 - 5  # Width of description text
        y = 10
        dy = 20
        
        def createLabel(y, name, description):
            label = QtGui.QLabel(self)            
            #label.setWordWrap(True)
            label.setText('<b>'+name+':</b>  ' + description)            
            #label.setMaximumWidth(desWidth)
            label.move(offset2, y)
            #label.show()
            return 16
        
        # Create name entry
        dyl = createLabel(y, 'Name', 'The name of this configuration.')
        self._name = QtGui.QLineEdit(self)        
        self._name.move(offset2, y+dyl)
        y += dy + dyl + self._name.height()
        
        # Create executable entry
        dyl = createLabel(y, 'Executable', 
            'e.g. "/usr/python3.1" or "c:/program files/python24/python.exe."')
        self._exe = QtGui.QComboBox(self)
        self._exe.setEditable(True)
        self._exe.setInsertPolicy(self._exe.InsertAtTop)
        self._exe.move(offset2, y+dyl)
        self._exe.resize(390-offset1, self._exe.height())
        y += dy + dyl + self._exe.height()
        
        # Create GUI toolkit chooser
        dx = 60
        dyl = createLabel(y, 'GUI toolkit',
            "The selected GUI's event loop is integrated in the interpreter.")
        #
        self._gui_none = QtGui.QRadioButton(self)
        self._gui_none.move(offset2+dx*0, y+dyl)
        self._gui_none.setText('None')
        #
        self._gui_tk = QtGui.QRadioButton(self)
        self._gui_tk.move(offset2+dx*1, y+dyl)
        self._gui_tk.setText('TK')
        #
        self._gui_wx = QtGui.QRadioButton(self)
        self._gui_wx.move(offset2+dx*2, y+dyl)
        self._gui_wx.setText('WX')
        #
        self._gui_qt4 = QtGui.QRadioButton(self)
        self._gui_qt4.move(offset2+dx*3, y+dyl)
        self._gui_qt4.setText('QT4')
        #
        self._gui_fltk = QtGui.QRadioButton(self)
        self._gui_fltk.move(offset2+dx*4, y+dyl)
        self._gui_fltk.setText('FLTK')
        #
        self._gui_gtk = QtGui.QRadioButton(self)
        self._gui_gtk.move(offset2+dx*5, y+dyl)
        self._gui_gtk.setText('GTK')
        #        
        y += dy + dyl + self._gui_none.height()
        
        # Create Pythonpath line edit
        dyl = createLabel(y, 'PYTHONPATH', 
            'Python module search path, one path per line.')
        self._ppCheck = QtGui.QCheckBox(self)        
        self._ppCheck.setText('Use system default')
        self._ppCheck.move(offset2, y+dyl)
        self._ppCheck.stateChanged.connect(self.pythonPathCheckBoxCallback)
        #
        self._ppList = QtGui.QTextEdit(self)
        self._ppList.move(offset2, y + dyl + self._ppCheck.height())
        self._ppList.resize(290, 60)
        self._ppListCustom = '' # to store text
        #
        y += dy + dyl + self._ppCheck.height() + self._ppList.height()
        
        # Create run startup script checkbox
        dyl = createLabel(y, 'PYTHONSTARTUP', 
            '(Interactive mode only) Shells run this script on startup.')
        self._startupCheck = QtGui.QCheckBox(self)
        self._startupCheck.setText('Use system default')
        self._startupCheck.stateChanged.connect(self.startupCheckBoxCallBack)
        self._startupCheck.move(offset2, y+dyl)
        self._startup = QtGui.QLineEdit(self)
        self._startup.resize(390-offset1, self._startup.height())
        self._startup.move(offset2, y + dyl + self._startupCheck.height())
        y += dy + dyl + self._startupCheck.height() + self._startup.height()
        
        # Create initial directory edit
        dyl = createLabel(y, 'Initial directory', 
            '(Interactive mode only) Shells start here. e.g. "/home/almar/py".')
        self._startdir = QtGui.QLineEdit(self)
        self._startdir.move(offset2, y+dyl)
        self._startdir.resize(290, self._startdir.height())
        y += dy + dyl + self._startdir.height()
        
#         # Create close button
#         #self._close = QtGui.QToolButton(self)
#         self._close = QtGui.QPushButton(self)
#         style = QtGui.qApp.style()
#         self._close.setIcon( style.standardIcon(style.SP_DialogCloseButton) )
#         closeSize = self._close.iconSize()
#         #self._close.move(400-closeSize.width()-20, 10)
#         self._close.move(offset1, y+16)
#         self._close.setText('Remove this config')
#         self._close.clicked.connect(self.onClose)
#         y += self._close.height() + 30
        
        # Define size and show
        size = 550, y
        self.resize(*size)
        self.setMaximumSize(*size)
        self.setMinimumSize(*size)        
        self.show()
        
        # Init values
        self.setDefaults()
        
        # Editing the name should edit it in the tab
        self._name.editingFinished.connect(self.setNameInTab)
    
    
    def pythonPathCheckBoxCallback(self, state):
        
        # Enable or disable
        self._ppList.setEnabled(not state)
        # Show text
        if state:
            self._ppListCustom = self._ppList.toPlainText()
            pp = os.environ.get('PYTHONPATH','')
            pp = pp.replace(';','\n').replace(',','\n')
            if not 'win' in sys.platform:
                pp = pp.replace(':','\n')
            self._ppList.setText(pp+'\n')
        else:
            self._ppList.setText(self._ppListCustom)
    
    def startupCheckBoxCallBack(self, state):
        
        # Enable or disable
        self._startup.setEnabled(not state)
        
        # Show text
        if state:
            self._startupCustom = self._startup.text()
            pp = os.environ.get('PYTHONSTARTUP','')            
            self._startup.setText(pp)
        else:
            self._startup.setText(self._startupCustom)
    
    
    def setDefaults(self):
        """ Set defaults. """
        self._name.setText('Default')        
        self._gui_tk.setChecked(True)
        self._ppCheck.setChecked(True)
        self._startupCheck.setChecked(True)
        self._startdir.setText('')
        
        locations = findPythonExecutables()
        locations.insert(0, 'python')
        self._exe.clear()
        for location in locations:
            self._exe.addItem(location)
        self._exe.setEditText('python') 
    
    
    def onClose(self):        
        # Get tab widget
        tabs = self.parent().parent()
        # Remove
        tabs.removeTab( tabs.indexOf(self) )
    
    
    def setNameInTab(self):        
        tabWidget = self.parent().parent()
        i = tabWidget.indexOf(self)
        tabWidget.setTabText(i, self._name.text())
    
    
    def setInfo(self, info):
        """ Set the contents based on an ssdf item in the shellConfigs. """
        try:
            self._name.setText(info.name)
            self.setNameInTab()
            #
            #self._exe.setText(info.exe)
            self._exe.setEditText(info.exe)
            #
            if info.gui == 'tk':
                self._gui_tk.setChecked(True)
            elif info.gui == 'wx':
                self._gui_wx.setChecked(True)
            elif info.gui == 'qt4':
                self._gui_qt4.setChecked(True)
            elif info.gui == 'fltk':
                self._gui_fltk.setChecked(True)
            elif info.gui == 'gtk':
                self._gui_gtk.setChecked(True)
            else:
                self._gui_none.setChecked(True)
            #
            self._ppListCustom = info.PYTHONPATH_custom
            self._ppCheck.setChecked(not info.PYTHONPATH_useCustom)
            self._ppListCustom = info.PYTHONPATH_custom
            #
            self._startupCustom = info.PYTHONSTARTUP_custom
            self._startupCheck.setChecked(not info.PYTHONSTARTUP_useCustom)
            self._startupCustom = info.PYTHONSTARTUP_custom
            #
            self._startdir.setText(info.startDir)
        
        except Exception as why:
            print('Error when setting info in shell config:', why)
    
    
    def getInfo(self):
        """ Get an ssdf struct based on the contents. """
        info = ssdf.new()
        #
        info.name = self._name.text()
        #
        info.exe = self._exe.currentText()
        #
        if self._gui_tk.isChecked():
            info.gui = 'tk'
        elif self._gui_wx.isChecked():
            info.gui = 'wx'
        elif self._gui_qt4.isChecked():
            info.gui = 'qt4'
        elif self._gui_fltk.isChecked():
            info.gui = 'fltk'
        elif self._gui_gtk.isChecked():
            info.gui = 'gtk'
        else:
            info.gui = ''
        # store states
        self._ppCheck.setChecked( not self._ppCheck.isChecked() )
        self._ppCheck.setChecked( not self._ppCheck.isChecked() )
        self._startupCheck.setChecked( not self._startupCheck.isChecked() )
        self._startupCheck.setChecked( not self._startupCheck.isChecked() )
        #   
        info.PYTHONPATH_custom = self._ppListCustom
        info.PYTHONPATH_useCustom = not self._ppCheck.isChecked()
        #
        info.PYTHONSTARTUP_custom = self._startupCustom
        info.PYTHONSTARTUP_useCustom = not self._startupCheck.isChecked()
        #
        info.startDir = self._startdir.text()
        # Done
        return info


class ShellInfoDialog(QtGui.QDialog):
    """ Dialog to edit the shell configurations. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # Set title
        self.setWindowTitle('IEP - shell configurations')
        self.setWindowIcon(iep.icon)
        
        # Create tab widget
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.setMovable(True)
        
        # Introduce an entry if there's none
        if not iep.config.shellConfigs:
            w = ShellInfoDialogEntries(self._tabs)
            self._tabs.addTab(w, 'Default')
        
        # Fill tabs
        for item in iep.config.shellConfigs:
            w = ShellInfoDialogEntries(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo(item) # sets the title
        
        # Enable making new tabs and closing tabs    
        self._add = QtGui.QToolButton(self)        
        self._tabs.setCornerWidget(self._add)
        self._add.clicked.connect(self.onAdd)
        self._add.setText('+')
        #
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self.onTabClose)
        
        # Create buttons
        cancelBut = QtGui.QPushButton("Cancel", self)        
        okBut = QtGui.QPushButton("Done", self)
        cancelBut.clicked.connect(self.close)
        okBut.clicked.connect(self.applyAndClose)
        # Layout for buttons
        buttonLayout = QtGui.QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(cancelBut)
        buttonLayout.addSpacing(10)
        buttonLayout.addWidget(okBut)
        
        
        # Layout the widgets
        mainLayout = QtGui.QVBoxLayout()
        mainLayout.addSpacing(8)
        mainLayout.addWidget(self._tabs,0)
        mainLayout.addLayout(buttonLayout,0)
        self.setLayout(mainLayout)
        
        # Prevent resizing
        self.show()
        size = self.size()
        self.setMaximumSize(size)
        self.setMinimumSize(size)
    
    
    def onTabClose(self, index):
        self._tabs.removeTab( index )
    
    
    def applyAndClose(self, event=None):
        self.apply()
        self.close()
    
    
    def onAdd(self):
        # Create widget and add to tabs
        w = ShellInfoDialogEntries(self._tabs)            
        self._tabs.addTab(w, 'new')
        # Select
        self._tabs.setCurrentWidget(w)
        w.setFocus()
    
    
    def apply(self):
        """ Apply changes for all tabs. """
        
        # Clear
        iep.config.shellConfigs = []
        
        # Set new versions
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            iep.config.shellConfigs.append( w.getInfo() )


## Find all python executables

def findPythonExecutables():
    if sys.platform.startswith('win'):
        return findPythonExecutables_win()
    else:
        return findPythonExecutables_linux()
    # todo: and mac?

def findPythonExecutables_win():
    import winreg
    
    # Open base key
    base = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    try:
        key = winreg.OpenKey(base, 'SOFTWARE\\Python\\PythonCore', 0, winreg.KEY_READ)
    except Exception:
        return []
    
    # Get info about subkeys
    nsub, nval, modified = winreg.QueryInfoKey(key)
    
    # Query all
    versions = []
    for i in range(nsub):
        try:
            # Get name and subkey 
            name =  winreg.EnumKey(key, i)
            subkey = winreg.OpenKey(key, name + '\\InstallPath', 0, winreg.KEY_READ)
            # Get install location and store
            location = winreg.QueryValue(subkey, '')
            versions.append(location)
            # Close
            winreg.CloseKey(subkey)
        except Exception:
            pass
    
    # Append "python.exe"
    versions = [os.path.join(v, 'python.exe') for v in versions]
    
    # Close keys
    winreg.CloseKey(key)
    winreg.CloseKey(base)
    
    # Done
    return versions


def findPythonExecutables_linux():
    
    # Get files
    try:
        files = os.listdir('/usr/bin')
    except Exception:
        return []
    
    # Search for python executables
    versions = []
    for fname in os.listdir('/usr/bin'):
        if fname.startswith('python') and not fname.count('config'):
            versions.append( '/usr/bin/' + fname )
    
    # Done
    return versions


