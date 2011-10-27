# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module shellTabs

Implements the stack of shells. Also implements the nifty debug button
and a dialog to edit the shell configurations. 

"""

import os, sys, time, re
from PyQt4 import QtCore, QtGui, uic

import iep
from iepcore.compactTabWidget import CompactTabWidget
from iepcore.shell import PythonShell
from iepcore.iepLogging import print

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
            from iepcore.menu import ShellTabContextMenu
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
ShellCfgDlg, ShellCfgDlgBase = uic.loadUiType(iep.iepDir + "/gui/shells_dialog.ui")
ShellCfgTab, ShellCfgTabBase = uic.loadUiType(iep.iepDir + "/gui/shell_tab.ui")

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


_LANGUAGE_EN = """
shell_configurations = 'IEP - shell configurations'

shell_name = 'Name: >> The name of this configuration'
shell_executable = 'Executable: >> The Python executable. e.g. "/usr/python3.1" or "c:/python/python.exe."'
shell_gui = 'GUI Toolkit: >> The selected GUI's event loop is integrated in the interpreter.'
shell_pythonpath = 'Python search path: >> Python module search path (i.e. PYTHONPATH), one path per line.' 
shell_pythonstartup = 'Python startup script: >> Shells run this script on startup (i.e. PYTHONSTARTUP), but not in script mode.' 
shell_startdir = 'Startup directory: >> Shells start here. e.g. "/home/almar/py", but not in script mode.'
"""

_LANGUAGE_NL = """
shell_configurations = 'IEP - shell configuraties (dope shizzle)'

shell_name = 'Naam: >> De naam van deze shell configuratie'
shell_executable = 'Applicatie: >> Het Python uitvoerbare bestand. b.v. "/usr/python3.1" of "c:/python/python.exe."'
shell_gui = 'GUI Toolkit: >> De event-loop van de geselecteerde toolkit wordt geintegreerd in de shell.'
shell_pythonpath = 'Python zoek pad: >> Python module zoek pad (PYTHONPATH), een map per regel.' 
shell_pythonstartup = 'Python opstart script: >> De shell voert dit uit bij het opstarten (PYTHONSTARTUP), maar niet in script modus.' 
shell_startdir = 'Opstart directory: >> De Shell start hier. b.v. "/home/almar/py", maar niet in script modus.'
"""
class Translater:

    def __init__(self):
        # todo: load from file instead of variable
        self._D = ssdf.loads(_LANGUAGE_NL)
    
    def _cleanName(self, name):
        # hide anything between brackets
        name = re.sub('\(.*\)', '', name)
        # replace invalid chars
        name = name.replace(' ', '_')
        if name[0] in '0123456789_':
            name = "_" + name
        name = re.sub('[^a-zA-z_0-9]','',name)
        return name.lower()
    
    
    def translate(self, name):
        """ translate(name)
        
        Given a name, returns the translated name and corresponding tooltip.
        
        """
        
        key = self._cleanName(name)
        if not key in self._D:
            return name, ''
        else:
            # Get string
            s = self._D[key].strip()
            # Extract tooltip
            if '>>' in s:
                name, dummy, tt = s.partition('>>')
                name, tt = name.rstrip(), tt.lstrip()
            else:
                name, tt = s, ''
            # Done
            return name, tt
    
    
    def translateWidget(self, widget):
        """
        For labels and menu items. 
        Get name from text(), translate and apply new name and tooltip.
        Also attach signal such that the widget is auto updated if
        the language is changed.
        
        Misschien dat deze methode ook de icoontjes kan toewijzen, zodat
        ook dat op een generieke manier gebeurt.
        
        """
        pass
_translater = Translater()
iep.translate = _translater.translate


class ShellInfoTab(QtGui.QWidget):
    
    GUIS = ['None', 'TK', 'WX', 'QT4', 'FLTK', 'GTK']
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        self._formLayout = QtGui.QFormLayout(self)
        parent = self
        
        # Name
        self._editName = QtGui.QLineEdit(parent)
        self._addRow('Shell name:', self._editName)
        # Exe
        self._editExe = QtGui.QComboBox(parent)
        self._editExe.setEditable(True)
        self._editExe.setInsertPolicy(self._editExe.InsertAtTop)
        self._addRow('Shell executable:', self._editExe)
        # GUI
        guiRadios = ['h']
        for guiName in self.GUIS:
            w = QtGui.QRadioButton(guiName, parent)
            guiRadios.append(w)
            wname = '_editGui' + guiName[0].upper() + guiName[1:].lower()
            setattr(self, wname, w)
        self._addRow('Shell GUI:', guiRadios)
        # PATH
        self._editPathCheck = QtGui.QCheckBox('Use system default', parent)
        self._editPath = QtGui.QTextEdit(parent)
        self._editPath.setMaximumHeight(80)
        self._editPath.setMinimumWidth(400)
        self._addRow('shell PYTHONPATH:', 
            ['v', self._editPath, self._editPathCheck])
        # Startup
        self._editStartupCheck = QtGui.QCheckBox('Use system default', parent)
        self._editStartup = QtGui.QLineEdit(parent)
        self._addRow('Shell PYTHONSTARTUP:', 
                ['v', self._editStartup, self._editStartupCheck])
        # Initial directory
        self._editStartdir = QtGui.QLineEdit(parent)
        self._addRow('Shell startdir:', self._editStartdir)
        
        # Apply layout
        self._formLayout.setSpacing(15)
        self.setLayout(self._formLayout)
        
        # Connect some signals
        self._editName.editingFinished.connect(self.onEditNameChanged)
        self._editPathCheck.stateChanged.connect(self.onEditPathCheckChanged)
        self._editStartupCheck.stateChanged.connect(self.onEditStartupCheckChanged)
    
    
    def _addRow(self, name, widget, tooltip=''):
        
        # If multiple widgets, make box layout
        if isinstance(widget, list):
            widgets = widget[1:]
            if widget[0].lower() == 'h':
                widget = QtGui.QHBoxLayout()
            else:
                widget = QtGui.QVBoxLayout()
            widget.setSpacing(1)
            for w in widgets:
                widget.addWidget(w)
        
        # Create row
        name, tooltip = iep.translate(name)
        label = QtGui.QLabel(name, self)
        label.setToolTip(tooltip)
        self._formLayout.addRow(label, widget)
    
    
    def setTabTitle(self, name):
        tabWidget = self.parent().parent()
        tabWidget.setTabText(tabWidget.indexOf(self), name)
    
    
    def onEditNameChanged(self): 
        self.setTabTitle(self._editName.text())
    
    
    def onEditPathCheckChanged(self, state):
        
        # Enable or disable
        #self._ppList.setEnabled(not state)
        self._editPath.setReadOnly(state)
        tmp = [QtGui.QColor('#000'), QtGui.QColor('#777')][bool(state)]
        self._editPath.setTextColor(tmp)
        # Show text
        if state:
            self._editPathBuffer = self._editPath.toPlainText()
            pp = os.environ.get('PYTHONPATH','')
            pp = pp.replace(os.pathsep,'\n').replace(',','\n')
            self._editPath.setText(pp+'\n')
        else:
            self._editPath.setText(self._editPathBuffer)
    
    
    def onEditStartupCheckChanged(self, state):
        
        # Enable or disable
        self._editStartup.setEnabled(not state)
        # Show text
        if state:
            self._editStartupBuffer = self._editStartup.text()
            pp = os.environ.get('PYTHONSTARTUP','')            
            self._editStartup.setText(pp)
        else:
            self._startup.setText(self._editStartupBuffer)
    
    
    def setInfo(self, info=None):
        """ setInfo(info=None)
        
        Set the shell config info. Set to defaults if info not given.
        
        """
        
        # Default?
        if info is None:
            info = ssdf.new()        
            # Name
            n = self.parent().parent().count()
            info.name = "Shell config %i" % n
            # Executable. Simply use the command "python", except for Windows;
            # I've experienced that the PATH is not always set. Use the last
            # found executable instead (highest Python version).
            info.exe = 'python'
            exes = findPythonExecutables()
            if exes and sys.platform.startswith('win'):
                info.exe = exes[-1]
            # Toolkit
            info.gui = "None"
            # Python search path
            info.PYTHONPATH_custom = ""
            info.PYTHONPATH_useCustom = False
            # Startup script
            info.PYTHONSTARTUP_custom = ""
            info.PYTHONSTARTUP_useCustom = False
            # Startup directory
            info.startDir = ""
        
        try:            
            # Name
            self._editName.setText(info.name)
            self.setTabTitle(info.name)
            
            # Executable
            locations = findPythonExecutables()
            if info.exe not in locations:
                locations.insert(0, info.exe)
            if 'python' not in locations:
                locations.insert(0, 'python')
            self._editExe.clear()
            for location in locations:
                self._editExe.addItem(location)
            self._editExe.setEditText(info.exe)
            
            # GUI toolkit            
            rb = '_editGui' + info.gui[0].upper() + info.gui[1:].lower()
            if hasattr(self, rb):
                getattr(self, rb).setChecked(True)
            
            # Python search path
            self._editPath.setText(info.PYTHONPATH_custom)
            self._editPathCheck.setChecked(not info.PYTHONPATH_useCustom)
            self._editPathBuffer = info.PYTHONPATH_custom
            
            # Startup script
            self._editStartup.setText(info.PYTHONSTARTUP_custom)
            self._editStartupCheck.setChecked(not info.PYTHONSTARTUP_useCustom)
            self._editStartupBuffer = info.PYTHONSTARTUP_custom
            
            # Startup directory
            self._editStartdir.setText(info.startDir)
        
        except Exception as why:
            print("Error when setting info in shell config:", why)
            print(info)
    
    
    def getInfo(self):
        
        info = ssdf.new()
        
        # Name
        info.name = self._editName.text()
        
        # Executable
        info.exe = self._editExe.currentText()
        
        # GUI toolkit
        info.gui = ""
        for guiName in self.GUIS:
            wName = '_editGui' + guiName[0].upper() + guiName[1:].lower()
            if hasattr(self, wName):
                if getattr(self, wName).isChecked():
                    info.gui = guiName
        
        # Python search path   
        info.PYTHONPATH_custom = self._editPathBuffer
        info.PYTHONPATH_useCustom = not self._editPathCheck.isChecked()
        
        # Startup script
        info.PYTHONSTARTUP_custom = self._editStartupBuffer
        info.PYTHONSTARTUP_useCustom = not self._editStartupCheck.isChecked()
        
        # Startup directory
        info.startDir = self._editStartdir.text()
        
        return info


class ShellInfoDialog(QtGui.QDialog):
    """ Dialog to edit the shell configurations. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # Set title
        self.setWindowTitle(iep.translate('shell configurations')[0])
        self.setWindowIcon(iep.icon)
        
        # Create tab widget
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.setMovable(True)
        
        # Introduce an entry if there's none
        if not iep.config.shellConfigs:
            w = ShellInfoTab(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo()
        
        # Fill tabs
        for item in iep.config.shellConfigs:
            w = ShellInfoTab(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo(item) # sets the title
        
        # Enable making new tabs and closing tabs    
        self._add = QtGui.QToolButton(self)        
        self._tabs.setCornerWidget(self._add)
        self._add.clicked.connect(self.onAdd)
        self._add.setIcon(iep.icons.add)
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

    
    def onAdd(self):
        # Create widget and add to tabs
        w = ShellInfoTab(self._tabs)            
        self._tabs.addTab(w, '---')
        w.setInfo()
        # Select
        self._tabs.setCurrentWidget(w)
        w.setFocus()
    
    
    def onTabClose(self, index):
        self._tabs.removeTab( index )
    
    
    def applyAndClose(self, event=None):
        self.apply()
        self.close()
    
    
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


