# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module shellInfoDialog

Implements shell configuration dialog.

"""

import os, sys, time, re
from iep.codeeditor.qt import QtCore, QtGui

import iep
from iep.iepcore.compactTabWidget import CompactTabWidget
from iep.iepcore.iepLogging import print
from iep.iepcore.kernelbroker import KernelInfo
from iep import translate


## Implement widgets that have a common interface


class ShellInfoLineEdit(QtGui.QLineEdit):
    
    def setTheText(self, value):
        self.setText(value)
    
    def getTheText(self):
        return self.text()



class ShellInfo_name(ShellInfoLineEdit):
    
    def __init__(self, *args, **kwargs):
        ShellInfoLineEdit.__init__(self, *args, **kwargs)
        self.editingFinished.connect(self.onValueChanged)
    
    
    def setTheText(self, value):
        ShellInfoLineEdit.setTheText(self, value)
        self.onValueChanged()
    
    
    def onValueChanged(self): 
        self.parent().setTabTitle(self.getTheText())



class ShellInfo_exe(QtGui.QComboBox):
    
    def setTheText(self, value):
        
        # Get options
        exes = findPythonExecutables()
        if value not in exes:
            exes.insert(0, value)
        if 'python' not in exes:
            exes.insert(0, 'python')
        
        # Set some settings
        self.setEditable(True)
        self.setInsertPolicy(self.InsertAtTop)
        
        # Set options
        self.clear()
        for exe in exes:
            self.addItem(exe)
        
        # Set current text
        self.setEditText(value)
    
    
    def getTheText(self):
        return self.currentText()



class ShellInfo_gui(QtGui.QComboBox):
    
    # For (backward) compatibility
    COMPAT = {'QT4':'PYQT4'}
    
    # GUI names
    GUIS = [    ('None', 'no GUI support'), 
                ('PySide', 'LGPL licensed wrapper to Qt (recommended)'),
                ('PyQt4', 'GPL/commercial licensed wrapper to Qt (recommended)'), 
                ('Tk', 'Tk widget toolkit'), 
                ('WX', 'wxPython'), 
                ('FLTK', 'The fast light toolkit'), 
                ('GTK', 'GIMP Toolkit'),
            ]
    
    # GUI descriptions
    
    def setTheText(self, value):
        
        # Process value
        value = value.upper()
        value = self.COMPAT.get(value, value)
        
        # Set options
        ii = 0
        self.clear()
        for i in range(len(self.GUIS)):
            gui, des = self.GUIS[i]
            if value == gui.upper():
                ii = i
            self.addItem('%s  -  %s' % (gui, des))
        
        # Set current text
        self.setCurrentIndex(ii)
    
    
    def getTheText(self):
        text = self.currentText().lower()
        return text.partition('-')[0].strip()



class ShellinfoWithSystemDefault(QtGui.QVBoxLayout):
    
    DISABLE_SYSTEM_DEFAULT = sys.platform == 'darwin' 
    
    def __init__(self, parent, widget, systemValue):
        # Do not pass parent, because is a sublayout
        QtGui.QVBoxLayout.__init__(self) 
        
        # Layout
        self.setSpacing(1)
        self.addWidget(widget)
        
        # Create checkbox widget
        if not self.DISABLE_SYSTEM_DEFAULT:
            t = translate('shell', 'Use system default')
            self._check = QtGui.QCheckBox(t, parent)
            self._check.stateChanged.connect(self.onCheckChanged)
            self.addWidget(self._check)
        
        # The actual value of this shell config attribute
        self._value = ''
        
        # The value of self._value if the system default is selected
        self._systemValue = systemValue
        
        # A buffered version, so that clicking the text box does not
        # remove the value at once
        self._bufferedValue = ''
    
    
    def onEditChanged(self):
       if self.DISABLE_SYSTEM_DEFAULT or not self._check.isChecked():
           self._value = self.getWidgetText()
    
    
    def onCheckChanged(self, state):
        if state:
            self._bufferedValue = self._value
            self.setTheText(self._systemValue)
        else:
            self.setTheText(self._bufferedValue)
    
    
    def setTheText(self, value):
        
        if self.DISABLE_SYSTEM_DEFAULT:
            # Just set the value
            self._edit.setReadOnly(False)
            self.setWidgetText(value)
        
        elif value != self._systemValue:
            # Value given, enable edit
            self._check.setChecked(False)
            self._edit.setReadOnly(False)
            # Set the text
            self.setWidgetText(value)
        
        else:
            # Use system default, disable edit widget
            self._check.setChecked(True)
            self._edit.setReadOnly(True)
            # Set text using system environment
            self.setWidgetText(None)
        
        # Store value
        self._value = value
    
    
    def getTheText(self):
        return self._value



class ShellInfo_pythonPath(ShellinfoWithSystemDefault):
    
    def __init__(self, parent):
        
        # Create sub-widget
        self._edit = QtGui.QTextEdit(parent)
        self._edit.setMaximumHeight(80)
        self._edit.setMinimumWidth(400)
        self._edit.textChanged.connect(self.onEditChanged)
        
        # Instantiate
        ShellinfoWithSystemDefault.__init__(self, parent, self._edit, '$PYTHONPATH') 
    
    
    def getWidgetText(self):
        return self._edit.toPlainText()
    
    
    def setWidgetText(self, value=None):
        if value is None:
            pp = os.environ.get('PYTHONPATH','')
            pp = pp.replace(os.pathsep, '\n  ').strip()
            value = '$PYTHONPATH (\n  %s\n)' % pp
        
        self._edit.setText(value)



class ShellInfo_startupScript(ShellinfoWithSystemDefault):
    
    def __init__(self, parent):
        
        # Create sub-widget
        self._edit = QtGui.QLineEdit(parent)
        self._edit.textEdited.connect(self.onEditChanged)
        
        # Instantiate
        ShellinfoWithSystemDefault.__init__(self, parent, self._edit, '$PYTHONSTARTUP') 
    
    
    def getWidgetText(self):
        return self._edit.text()
    
    
    def setWidgetText(self, value=None):
        if value is None:
            pp = os.environ.get('PYTHONSTARTUP','').strip()
            if pp:          
                value = '$PYTHONSTARTUP ("%s")' % pp
            else:
                value = '$PYTHONSTARTUP (is empty)'
        
        self._edit.setText(value)



class ShellInfo_startDir(ShellInfoLineEdit):
    pass


## The dialog class and container with tabs


class ShellInfoTab(QtGui.QWidget):
    
    INFO_KEYS = [   translate('shell', 'name ::: The name of this configuration.'), 
                    translate('shell', 'exe ::: The Python executable.'), 
                    translate('shell', 'gui ::: The GUI toolkit to integrate (for interactive plotting, etc.).'), 
                    translate('shell', 'pythonPath ::: A list of directories to search for modules and packages. Write each path on a new line, or separate with the default seperator for this OS.'), 
                    translate('shell', 'startupScript ::: The script to run at startup (not in script mode).'), 
                    translate('shell', 'startDir ::: The start directory (not in script mode).')
                ]
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Create layout
        self._formLayout = QtGui.QFormLayout(self)
        
        # Collect classes of widgets to instantiate
        classes = []
        defaultInfo = KernelInfo()
        for t in self.INFO_KEYS:
            className = 'ShellInfo_' + t.key
            cls = globals()[className]
            classes.append((t, cls))
        
        # Instantiate all classes
        self._shellInfoWidgets = {}
        for t, cls in classes:
            # Instantiate and store
            instance = cls(self)
            self._shellInfoWidgets[t.key] = instance
            # Create label 
            label = QtGui.QLabel(t, self)
            label.setToolTip(t.tt)
            # Add to layout
            self._formLayout.addRow(label, instance)
        
        # Add delete button  
        
        t = translate('shell', 'Delete ::: Delete this shell configuration')
        label = QtGui.QLabel('', self)        
        instance = QtGui.QPushButton(iep.icons.cancel, t, self)
        instance.setToolTip(t.tt)
        instance.clicked.connect(self.parent().parent().onTabClose)
        deleteLayout = QtGui.QHBoxLayout()
        deleteLayout.addWidget(instance, 0)
        deleteLayout.addStretch(1)
        # Add to layout
        self._formLayout.addRow(label, deleteLayout)
        
        # Apply layout
        self._formLayout.setSpacing(15)
        self.setLayout(self._formLayout)
    
    
    def setTabTitle(self, name):
        tabWidget = self.parent().parent()
        tabWidget.setTabText(tabWidget.indexOf(self), name)
    
    
    def setInfo(self, info=None):
        """  Set the shell info struct, and use it to update the widgets.
        Not via init, because this function also sets the tab name.
        """ 
        
        # If info not given, use default as specified by the KernelInfo struct
        if info is None:
            info = KernelInfo()
            # Name
            n = self.parent().parent().count()
            info.name = "Shell config %i" % n
            # Executable. Simply use the command "python", except for Windows;
            # I've experienced that the PATH is not always set. Use the last
            # found executable instead (highest Python version).
            exes = findPythonExecutables()
            if exes and sys.platform.startswith('win'):
                info.exe = exes[-1]
        
        # Store info
        self._info = info
        
        # Set widget values according to info
        try:            
           for key in info:
               widget = self._shellInfoWidgets.get(key, None)
               if widget is not None:
                   widget.setTheText(info[key])
        
        except Exception as why:
            print("Error setting info in shell config:", why)
            print(info)

    
    def getInfo(self):
        
        info = self._info
        
        # Set struct values according to widgets
        try:            
           for key in info:
               widget = self._shellInfoWidgets.get(key, None)
               if widget is not None:
                   info[key] = widget.getTheText()
        
        except Exception as why:
            print("Error getting info in shell config:", why)
            print(info)
        
        # Return the original (but modified) ssdf struct object
        return info



class ShellInfoDialog(QtGui.QDialog):
    """ Dialog to edit the shell configurations. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        self.setModal(True)
        
        # Set title
        self.setWindowTitle(iep.translate('shell', 'Shell configurations'))
        # Create tab widget
        #self._tabs = QtGui.QTabWidget(self) 
        self._tabs = CompactTabWidget(self, padding=(4,4,5,5))
        self._tabs.setDocumentMode(False)
        self._tabs.setMovable(True)
        
        # Introduce an entry if there's none
        if not iep.config.shellConfigs2:
            w = ShellInfoTab(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo()
        
        # Fill tabs
        for item in iep.config.shellConfigs2:
            w = ShellInfoTab(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo(item)
        
        # Enable making new tabs and closing tabs    
        self._add = QtGui.QToolButton(self)        
        self._tabs.setCornerWidget(self._add)
        self._add.clicked.connect(self.onAdd)
        self._add.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._add.setIcon(iep.icons.add)
        self._add.setText(translate('shell', 'Add config'))
        #
        #self._tabs.setTabsClosable(True)
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
        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.addSpacing(8)
        mainLayout.addWidget(self._tabs,0)
        mainLayout.addLayout(buttonLayout,0)
        self.setLayout(mainLayout)
        
        # Prevent resizing
        self.show()
        size = self.size()
        self.setMinimumSize(size)
        self.setMaximumHeight(size.height())

    
    def onAdd(self):
        # Create widget and add to tabs
        w = ShellInfoTab(self._tabs)
        self._tabs.addTab(w, '---')
        w.setInfo()
        # Select
        self._tabs.setCurrentWidget(w)
        w.setFocus()
    
    
    def onTabClose(self, index=None):
        if index is None:
            index = self._tabs.currentIndex()
        self._tabs.removeTab( index )
    
    
    def applyAndClose(self, event=None):
        self.apply()
        self.close()
    
    
    def apply(self):
        """ Apply changes for all tabs. """
        
        # Clear
        iep.config.shellConfigs2 = []
        
        # Set new versions. Note that although we recreate the list,
        # the list is filled with the orignal structs, so having a
        # reference to such a struct (as the shell has) will enable
        # you to keep track of any made changes.
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            iep.config.shellConfigs2.append( w.getInfo() )


## Find all python executables
# todo: use new version that will probably be part of pyzolib

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
    
    # Query Python versions from registry
    versions = set()
    for i in range(nsub):
        try:
            # Get name and subkey 
            name =  winreg.EnumKey(key, i)
            subkey = winreg.OpenKey(key, name + '\\InstallPath', 0, winreg.KEY_READ)
            # Get install location and store
            location = winreg.QueryValue(subkey, '')
            versions.add(location)
            # Close
            winreg.CloseKey(subkey)
        except Exception:
            pass
    
    # Close keys
    winreg.CloseKey(key)
    winreg.CloseKey(base)
    
    # Query Python versions from file system
    for rootname in ['c:/', 'C:/program files/', 'C:/program files (x86)/']:
        if not os.path.isdir(rootname):
            continue
        for dname in os.listdir(rootname):
            if dname.lower().startswith('python'):
                versions.add(os.path.join(rootname, dname))
    
    # Normalize all paths, and remove trailing backslashes
    versions = set([os.path.normcase(v).strip('\\') for v in versions])
    
    # Append "python.exe" and check if that file exists
    versions2 = []
    for dname in sorted(versions,key=lambda x:x[-2:]):
        exename = os.path.join(dname, 'python.exe')
        if os.path.isfile(exename):
            versions2.append(exename)
    
    # Done
    return versions2


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


