# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module shellStack

Implements the stack of shells. Also implements the nifty debug button
and a dialog to edit the shell configurations. 

"""

import os, sys, time
from PyQt4 import QtCore, QtGui, uic

import iep
from compactTabWidget import CompactTabWidget
from shell import PythonShell
from iepLogging import print

ssdf = iep.ssdf

class ShellStack(QtGui.QWidget):
    """ The shell stack widget provides a stack of shells,
    and makes sure they are of the correct width such that 
    they have exactly 80 columns. 
    """
    
    # When the current shell changes.
    currentShellChanged = QtCore.pyqtSignal()
    
    # When the current shells state (or debug state) changes. 
    # Also fired when the current shell changes.
    currentShellStateChanged = QtCore.pyqtSignal() 
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # create sizer
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout.setSpacing(0)
        
        # create tab widget
        self._tabs = CompactTabWidget(self)
        
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
        
        # Signal
        self.currentShellChanged.emit()
    
    
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
            
            # Send signal
            self.currentShellStateChanged.emit()
    
    
    def onShellDebugStateChange(self, shell):
        """ Called when the shell debug state changes, and is called
        by onCurrentChanged. Sets the debug button.
        """
        if shell is self.getCurrentShell():
            # Update debug info
            if shell._debugState:
                self._tabs.cornerWidget().setTrace(shell._debugState)
            else:
                self._tabs.cornerWidget().setTrace(None)
            
            # Send signal
            self.currentShellStateChanged.emit()
    
    def addContextMenu(self):
        """ Adds a context menu to the tab bar """
        
        # Uses new menu system, so check if it is enabled
        if 'useNewMenus' in iep.config.advanced and iep.config.advanced.useNewMenus:
            from menu import ShellTabContextMenu
            self._menu = ShellTabContextMenu(self, "ShellTabMenu")
            self._tabs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self._tabs.customContextMenuRequested.connect(self.contextMenuTriggered)

    
    def contextMenuTriggered(self, p):
        """ Called when context menu is clicked """
        
        # Get index of shell belonging to the tab
        index = self._tabs.tabBar().tabAt(p)
        self._menu.setIndex(index)
        
        # Get shell at index
        if index < 0:
            shell = None
        else:
            shell = self.getShells()[index]
        
        # Show menu if shell is available
        if shell:
            p = self._tabs.tabBar().tabRect(index).bottomLeft()
            self._menu.exec_(self._tabs.tabBar().mapToGlobal(p))

    
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

    def getShells(self):
        """ Get all shell in stack as list """
        
        shells = []
        for i in range(self._tabs.count()):
            shell = self.getShellAt(i)
            if shell is not None:
                shells.append(shell)
        
        return shells
    
    def getShellAt(self, i):
        """ Get shell at current tab index """
        
        return self._tabs.widget(i)
    

class DebugControl(QtGui.QToolButton):
    """ A button that can be used for post mortem debuggin. 
    """
    
    def __init__(self, parent):
        QtGui.QToolButton.__init__(self, parent)
        
        # Set text and tooltip
        self.setText('Debug')
        self.setIcon(iep.icons.bug)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
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
                shell.executeCommand('DB START\n')
    
    
    def onTriggered(self, action):
        
        # Get shell
        shell = iep.shells.getCurrentShell()
        if not shell:
            return
        
        if action._index < 1:
            # Stop debugging
            shell.executeCommand('DB STOP\n')
        else:
            # Change stack index
            if not action._isCurrent:
                shell.executeCommand('DB FRAME {}\n'.format(action._index))
            # Open file and select line
            if True:
                line = action.text().split(': ',1)[1]
                self.debugFocus(line)
    
    
    def setTrace(self, info):
        """ Set the stack trace. This method is called from
        the shell that receives the trace via its status channel
        directly from the interpreter. 
        If trace is None, removes the trace
        """
        
        # Get info
        if info:
            index, frames = info['index'], info['frames']
        else:
            index, frames = -1, []
        
        if not frames:
            
            # Remove trace
            self.setMenu(None)
            self.setText('Debug')
        
        else:
            # todo: there might be an offset in the index
            # Get the current frame
            theAction = None
            
            # Create menu and add __main__
            menu = QtGui.QMenu(self)
            self.setMenu(menu)
            action = menu.addAction('MAIN: stop debugging')
            action._index = 0
            
            # Fill trace
            for i in range(len(frames)):
                thisIndex = i + 1
                action = menu.addAction('{}: {}'.format(thisIndex, frames[i]))
                action._index = thisIndex
                action._isCurrent = False
                if thisIndex == index:
                    action._isCurrent = True
                    theAction = action
                    
            
            # Highlight current item and set the button text
            if theAction:
                menu.setDefaultAction(theAction)
                #self.setText(theAction.text().ljust(20))
                i = theAction._index
                text = "Stack Trace ({}/{}):  ".format(i, len(frames)-1)
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
            # Goto line and select it
            editor.gotoLine(linenr)
            cursor = editor.textCursor()
            cursor.movePosition(cursor.StartOfBlock)
            cursor.movePosition(cursor.EndOfBlock, cursor.KeepAnchor)
            editor.setTextCursor(cursor)


## Shell configuration dialog

# Load classes for configuration dialog and tabs
ShellCfgDlg, ShellCfgDlgBase = uic.loadUiType("gui/shells_dialog.ui")
ShellCfgTab, ShellCfgTabBase = uic.loadUiType("gui/shell_tab.ui")

class ShellConfigTab(ShellCfgTab, ShellCfgTabBase):
    """
    Implements a shell configuration tab in the configuration dialog
    """
    
    # Maps GUI toolkits to corresponding radiobuttons
    _tkButtons = {"none": "rbNone",
                  "tk": "rbTk",
                  "wx": "rbWx",
                  "qt4": "rbQt",
                  "fltk": "rbFltk",
                  "gtk": "rbGtk"}
                         
    def __init__(self, *args):
        ShellCfgTabBase.__init__(self, *args)
        self.setupUi(self)
        
        # Holds the settings for this shell
        self._info = None
        
        # Hold custom search path and startup script
        self._customSearchPath = ""
        self._customStartup = ""
        
        # Editing the name should change table title
        self.edtName.editingFinished.connect(self.edtNameCallback)
        
        # Set callback for checkboxes
        self.chkSearchSysDef.toggled.connect(self.chkSearchSysDefCallback)
        self.chkStartupSysDef.toggled.connect(self.chkStartupCallBack)
    
    def setConfigInfo(self, info):
        self._info = info
    
    def setTabTitle(self):
        tabWidget = self.parent().parent()
        tabWidget.setTabText(tabWidget.indexOf(self), self._info.name)
    
    def setDefaults(self):        
        # Name
        self._info.name = "Default shell"
        
        # Executable
        self._info.exe = findPythonExecutables()[0]
        
        # Toolkit
        self._info.gui = "qt4"
        
        # Python search path
        self._info.PYTHONPATH_custom = ""
        self._info.PYTHONPATH_useCustom = False
        
        # Startup script
        self._info.PYTHONSTARTUP_custom = ""
        self._info.PYTHONSTARTUP_useCustom = False
        
        # Startup directory
        self._info.startDir = ""
        
        # Update form fields
        self.setInfo()
    
    def setInfo(self):        
        try:            
            # Name
            self.edtName.setText(self._info.name)
            
            # Set name in tab
            self.setTabTitle()
            
            # Executable
            locations = findPythonExecutables()
            locations.insert(0, self._info.exe)
            self.cbExe.clear()
            for location in locations:
                self.cbExe.addItem(location)
            self.cbExe.setEditText(locations[0])
            
            # GUI toolkit            
            rb = self._tkButtons[self._info.gui.lower()]
            if hasattr(self, rb):
                getattr(self, rb).setChecked(True)
            
            # Python search path
            self.edtSearchPath.setText(self._info.PYTHONPATH_custom)
            self.chkSearchSysDef.setChecked(not self._info.PYTHONPATH_useCustom)
            
            # Startup script
            self.edtStartup.setText(self._info.PYTHONSTARTUP_custom)
            self.chkStartupSysDef.setChecked(not self._info.PYTHONSTARTUP_useCustom)
            
            # Startup directory
            self.edtStartDir.setText(self._info.startDir)
        except Exception as why:
            print("Error when setting info in shell config:", why)
            print(self._info)
    
    def getInfo(self):
        # Name
        self._info.name = self.edtName.text()
        
        # Executable
        self._info.exe = self.cbExe.currentText()
        
        # GUI toolkit
        self._info.gui = ""
        for rb in self._tkButtons.keys():
            if hasattr(self, self._tkButtons[rb]):
                if getattr(self, self._tkButtons[rb]).isChecked():
                    self._info.gui = rb
        
        # Python search path   
        self._info.PYTHONPATH_custom = self._customSearchPath
        self._info.PYTHONPATH_useCustom = not self.chkSearchSysDef.isChecked()
        
        # Startup script
        self._info.PYTHONSTARTUP_custom = self._customStartup
        self._info.PYTHONSTARTUP_useCustom = not self.chkStartupSysDef.isChecked()
        
        # Startup directory
        self._info.startDir = self.edtStartDir.text()
    
    def edtNameCallback(self):
        self._info.name = self.edtName.text()
        self.setTabTitle()
    
    def chkSearchSysDefCallback(self, state):
        if state:
            # Store any custom set search path
            self._customSearchPath = self.edtSearchPath.toPlainText()
            path = os.environ.get("PYTHONPATH", "")
            path = path.replace(os.pathsep, "\n").replace(",", "\n")
            self.edtSearchPath.setText(path + "\n")
        else:
            self.edtSearchPath.setText(self._customSearchPath)
    
    def chkStartupCallBack(self, state):
        if state:
            self._customStartup = self.edtStartup.text()
            startup = os.environ.get("PYTHONSTARTUP", "")
            self.edtStartup.setText(startup)
        else:
            self.edtStartup.setText(self._customStartup)

class ShellConfigDialog(ShellCfgDlg, ShellCfgDlgBase):  
    """
    Implements the shell configuration dialog.
    """
    
    def __init__(self, *args):
        ShellCfgDlgBase.__init__(self, *args)
        self.setupUi(self)
        
        # Connect OK button
        self.buttonBox.accepted.connect(self.applyAndClose)
        
        # Connect add and remove buttons
        self.btnAdd.clicked.connect(self.addShellConfig)
        self.btnRemove.clicked.connect(self.removeShellConfig)
        
        # Create tab widget
        #self._tabs = CompactTabWidget(self, padding=(2,1,4,2))
        
        # Introduce an entry if there's none
        if not iep.config.shellConfigs:
            self.addShellConfig()
        else:
            # Fill tabs
            for config in iep.config.shellConfigs:
                t = ShellConfigTab(self.wdtShellConfigs)
                self.wdtShellConfigs.addTab(t, "---")
                t.setConfigInfo(config)
                t.setInfo()
        
        # Auto-save on tab change (after tabs have been added!)
        self.wdtShellConfigs.currentChanged.connect(self.apply)
    
    def addShellConfig(self):
        # Create new info entry
        info = ssdf.new()
        iep.config.shellConfigs.append(info)
        
        # Add new shell configuration tab
        t = ShellConfigTab(self.wdtShellConfigs)
        self.wdtShellConfigs.addTab(t, "---")
        t.setConfigInfo(info)
        t.setDefaults()
        self.wdtShellConfigs.setCurrentIndex(self.wdtShellConfigs.indexOf(t))
    
    def removeShellConfig(self):        
        # Try to figure out which shell config to delete
        t = self.wdtShellConfigs.currentWidget()
        ind = [i for i, info in enumerate(iep.config.shellConfigs) if info == t._info]
        
        # Delete tab
        self.wdtShellConfigs.removeTab(self.wdtShellConfigs.indexOf(t))
        
        # Delete corresponding info
        iep.config.shellConfigs.pop(ind[0])
    
    def applyAndClose(self):
        self.apply()
        self.close()
    
    def apply(self):
        for i in range(self.wdtShellConfigs.count()):
            self.wdtShellConfigs.widget(i).getInfo()

## Find all python executables

def findPythonExecutables():
    if sys.platform.startswith('win'):
        return findPythonExecutables_win()
    else:
        return findPythonExecutables_posix()

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


def findPythonExecutables_posix():
    found=[]
    for searchpath in ['/usr/bin','/usr/local/bin','/opt/local/bin']: 
        # Get files
        try:
            files = os.listdir(searchpath)
        except Exception:
            continue
        
        # Search for python executables
        for fname in files:
            if fname.startswith('python') and not fname.count('config'):
                found.append( os.path.join(searchpath, fname) )
    # Done
    return found


