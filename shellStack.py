""" Module shellStack
Implements the stack of shells.
"""

import os, sys, time
from PyQt4 import QtCore, QtGui

import iep
from shell import PythonShell

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
        self._boxLayout.addWidget(self._tabs, 999)
#         self._boxLayout.addStretch(1)
        
        
        # set layout
        self.setLayout(self._boxLayout)
        
        # Create debug control (which is not layed out)
        dbc = DebugControl(self)
        self._tabs.setCornerWidget(dbc, QtCore.Qt.TopRightCorner)
        #dbc.move(0,0)
        
        # make callbacks
        self._tabs.currentChanged.connect(self.sizeShellTo80Columns)
    
    
    def __iter__(self):
        i = 0
        while i < self._tabs.count():
            w = self._tabs.widget(i)
            i += 1
            yield w 
    
    
    def addShell(self, shellInfo=None):
        """ addShell()
        Add a shell to the widget. """
        shell = PythonShell(self._tabs, shellInfo)
        self._tabs.addTab(shell, 'Python (Initializing)')
        self.sizeShellTo80Columns()
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
    
    
    def showEvent(self, event):
        """ Overload to set size. """
        QtGui.QWidget.showEvent(self, event)
        self.sizeShellTo80Columns()
    
    
    def sizeShellTo80Columns(self, event=None):
        """ Is the name not descriptive enough?
        """
        return 
        
        # are we hidden?
        if not self.isVisible():
            return
            
        # shell now selected
        shell = self.getCurrentShell()
        if shell is None:
            return
        
        # get size it should be (but font needs to be monospaced!
        w = shell.textWidth(32, "-"*80)
        w += 26 # add scrollbar and margin
        
        # fix the width
        shell.setMinimumWidth(w)
        shell.setMaximumWidth(w)
    
    

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
                shell._control.write('DEBUG START')
                shell.processLine('[Enter debug mode]', False)
                shell._stdin.write('\n')
    
    
    def onTriggered(self, action):
        
        # Get shell
        shell = iep.shells.getCurrentShell()
        if not shell:
            return
        
        if action._index < 0:
            # Stop debugging
            shell._control.write('DEBUG END')
            shell.processLine('[Exit debug mode]', False)
            shell._stdin.write('\n')
        else:
            # Change stack index
            shell._control.write('DEBUG INDEX {}'.format(action._index))
            shell.processLine('[Change debug frame]', False)
            shell._stdin.write('\n')
    
    
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
            current = int(trace[-1])
            theAction = None
            
            # Create menu and add __main__
            menu = QtGui.QMenu(self)
            self.setMenu(menu)
            action = menu.addAction('MAIN: stop debugging')
            action._index = -1
            
            # Fill trace
            for i in range(len(trace)-1):
                action = menu.addAction(trace[i])
                action._index = i
                if i == current:
                    theAction = action
            
            # Highlight current item and make that the button text
            if theAction:
                menu.setDefaultAction(theAction)
                self.setText(theAction.text().ljust(20))
    


class ShellInfoDialogEntries(QtGui.QWidget):
    
    def __init__(self, *args):        
        QtGui.QWidget.__init__(self, *args)    
        
        # Init
        offset = 20
        y = 10
        dy = 60
        
        # Create name entry
        label = QtGui.QLabel(self)
        label.move(offset, y)
        label.setText('Configuration name')        
        self._name = QtGui.QLineEdit(self)        
        self._name.move(offset, y+16)
        y += dy
        
        # Create executable widget
        label = QtGui.QLabel(self)
        label.move(offset, y)
        label.setText('Executable (e.g. "python" or "/usr/python3.1"\n'+
                            ' or"c:/program files/python24/python.exe" )')
        y += 16
        self._exe = QtGui.QLineEdit(self)
        self._exe.move(offset, y+16)
        self._exe.resize(350, self._exe.height())
        y += dy
        
        # Create GUI toolkit chooser
        dx = 60
        label = QtGui.QLabel(self)
        label.move(offset, y)
        label.setText('Gui toolkit to interact with.')        
        #
        self._gui_none = QtGui.QRadioButton(self)
        self._gui_none.move(offset+dx*0, y+16)
        self._gui_none.setText('None')
        #
        self._gui_tk = QtGui.QRadioButton(self)
        self._gui_tk.move(offset+dx*1, y+16)
        self._gui_tk.setText('TK')
        #
        self._gui_wx = QtGui.QRadioButton(self)
        self._gui_wx.move(offset+dx*2, y+16)
        self._gui_wx.setText('WX')
        #
        self._gui_qt4 = QtGui.QRadioButton(self)
        self._gui_qt4.move(offset+dx*3, y+16)
        self._gui_qt4.setText('QT4')
        #
        self._gui_fl = QtGui.QRadioButton(self)
        self._gui_fl.move(offset+dx*4, y+16)
        self._gui_fl.setText('FLTK')
        #        
        y += dy
        
        # Create run startup script checkbox
        label = QtGui.QLabel(self)
        label.move(offset, y)
        label.setText('Run startup script (if set).')
        self._runsus = QtGui.QCheckBox(self)
        self._runsus.move(offset, y+16)
        y += dy
        
        # Create initial directory edit
        label = QtGui.QLabel(self)
        label.move(offset, y)
        label.setText('Initial directory (e.g. "/home/almar/py")')        
        self._startdir = QtGui.QLineEdit(self)        
        self._startdir.move(offset, y+16)
        self._startdir.resize(350, self._exe.height())
        y += dy
        
        self.show()
        
        # Create close button
        self._close = QtGui.QPushButton(self)
        self._close.setText('Remove')
        self._close.move(offset, y+20)
        self._close.clicked.connect(self.onClose)
        
        # Init values
        self.setDefaults()
        
        # A few callbacks so we do not need an apply button
        self._name.editingFinished.connect(self.apply)
        self._name.editingFinished.connect(self.setNameInTab)
        self._exe.editingFinished.connect(self.apply)
        self._gui_none.clicked.connect(self.apply)
        self._gui_tk.clicked.connect(self.apply)
        self._gui_wx.clicked.connect(self.apply)
        self._gui_qt4.clicked.connect(self.apply)
        self._gui_fl.clicked.connect(self.apply)
        self._runsus.clicked.connect(self.apply)
        self._startdir.editingFinished.connect(self.apply)
    
    
    def setDefaults(self):
        """ Set defaults. """
        self._name.setText('new')
        self._exe.setText('python')
        self._gui_tk.setChecked(True)
        self._runsus.setChecked(True)
        self._startdir.setText('')
    
    
    def onClose(self):        
        # Get tab widget
        tabs = self.parent().parent()
        # Remove
        tabs.removeTab( tabs.indexOf(self) )
        
        
    
    def apply(self):
        """ Apply the current config. """
        
        # Get the dialog
        parent = self.parent()
        while not isinstance(parent, ShellInfoDialog):
            parent = parent.parent()
        
        # Call apply 
        parent.apply()
    
    
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
            self._exe.setText(info.exe)
            #
            if info.gui == 'tk':
                self._gui_tk.setChecked(True)
            elif info.gui == 'wx':
                self._gui_wx.setChecked(True)
            elif info.gui == 'qt4':
                self._gui_qt4.setChecked(True)
            elif info.gui == 'fl':
                self._gui_fl.setChecked(True)
            else:
                self._gui_none.setChecked(True)
            #
            self._runsus.setChecked(info.runsus)
            #
            self._startdir.setText(info.startdir)
        except Exception:
            print('Error when setting info in shell config.')
    
    
    def getInfo(self):
        """ Get an ssdf struct based on the contents. """
        info = ssdf.new()
        #
        info.name = self._name.text()
        #
        info.exe = self._exe.text()
        #
        if self._gui_tk.isChecked():
            info.gui = 'tk'
        elif self._gui_wx.isChecked():
            info.gui = 'wx'
        elif self._gui_qt4.isChecked():
            info.gui = 'qt4'
        elif self._gui_fl.isChecked():
            info.gui = 'fl'
        else:
            info.gui = ''
        # 
        info.runsus = self._runsus.isChecked()
        #
        info.startdir = self._startdir.text()
        # Done
        return info


class ShellInfoDialog(QtGui.QDialog):
    """ Dialog to edit the shell configurations. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP - shell configurations')
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 400,400
        offset = 0
        
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*size2)
        
        # Create tab widget
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.resize(*size)
        self._tabs.move(0,offset)
        self._tabs.setMovable(True)
        
        # Introduce an entry if there's none
        if not iep.config.shellConfigs:
            w = ShellInfoDialogEntries(self._tabs)
            self._tabs.addTab(w, 'new')
        
        # Fill tabs
        for item in iep.config.shellConfigs:
            w = ShellInfoDialogEntries(self._tabs)
            self._tabs.addTab(w, '---')
            w.setInfo(item) # sets the title
        
        # Enable making new tabs
        self._add = QtGui.QPushButton(self)
        self._add.setText('+')
        self._tabs.setCornerWidget(self._add)
        self._add.clicked.connect(self.onAdd)
        
        # Enable removing tabs
#         self._tabs.setTabsClosable(True)
#         self._tabs.tabCloseRequested.connect(self.onTabClose)
        
    
    def closeEvent(self, event):
        """ Apply first! """
        self.apply()
        QtGui.QDialog.closeEvent(self, event)
    
    
    def onAdd(self):
        # Create widget and add to tabs
        w = ShellInfoDialogEntries(self._tabs)            
        self._tabs.addTab(w, 'new')
        # Select
        self._tabs.setCurrentWidget(w)
        w.setFocus()
    
    
    def onTabClose(self, index):
        self._tabs.removeTab(index)
        self.apply()
    
    
    def apply(self):
        """ Apply changes for all tabs. """
        
        # Clear
        iep.config.shellConfigs = []
        
        # Set new versions
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            iep.config.shellConfigs.append( w.getInfo() )