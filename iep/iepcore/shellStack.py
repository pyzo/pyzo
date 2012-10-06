# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module shellStack

Implements the stack of shells. Also implements the nifty debug button
and a dialog to edit the shell configurations. 

"""

import os, sys, time, re
from iep.codeeditor.qt import QtCore, QtGui

import iep
from iep.iepcore.compactTabWidget import CompactTabWidget
from iep.iepcore.shell import PythonShell
from iep.iepcore.iepLogging import print
from iep.iepcore.menu import ShellTabContextMenu
from iep.iepcore.icons import ShellTabToolButton


class ShellStackWidget(QtGui.QWidget):
    """ The shell stack widget provides a stack of shells,
    and makes sure they are of the correct width such that 
    they have exactly 80 columns. 
    """
    
    # When the current shell changes.
    currentShellChanged = QtCore.Signal()
    
    # When the current shells state (or debug state) changes,
    # or when a new prompt is received. 
    # Also fired when the current shell changes.
    currentShellStateChanged = QtCore.Signal() 
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # create toolbar
        self._toolbar = QtGui.QToolBar(self)
        self._toolbar.setMaximumHeight(25)
        self._cbShells = QtGui.QComboBox(self._toolbar)
        self._cbShells.setEditable(False)
        self._cbShells.setMinimumContentsLength(25)
        self._dbc = DebugControl(self._toolbar)
        self._toolbar.addWidget(self._cbShells)
        self._toolbar.addWidget(self._dbc)
        
        # create stack
        self._stack = QtGui.QStackedWidget(self)
        
        # widget layout
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._stack)
        self.setLayout(layout)
        
        # make callbacks
        self._cbShells.currentIndexChanged.connect(self.onCurrentChanged)
    

    def __iter__(self):
        i = 0
        while i < self._stack.count():
            w = self._stack.widget(i)
            i += 1
            yield w 
    
    
    def onCurrentChanged(self, index):
        """ When another shell is selected, update some things. 
        """
        
        # Update state info
        if index<0:
            iep.main.setWindowIcon(iep.icon)
        else:
            shell_id = self._cbShells.itemData(index)
            shell = None
            for s in self:
                if id(s) == shell_id:
                    shell = s
                    break

            if shell:
                self._stack.setCurrentWidget(shell)
                self.onShellStateChange(shell)
                self.onShellDebugStateChange(shell)
        
        # Signal
        self.currentShellChanged.emit()
    
    
    def onShellStateChange(self, shell):
        """ Called when the shell state changes, and is called
        by onCurrentChanged. Sets the mainwindow's icon if busy.
        """
        
        # Build text for combobox
        text = 'Python {}'.format(shell._version)  
        gui = shell._startup_info.get('gui')
        if gui:
            text += ' with ' + gui
        
        # Set tab text and tooltip
        self._cbShells.setItemText(self._cbShells.findData(id(shell)), text)
        
        if shell is self.getCurrentShell():
            # Update application icon
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
                self._dbc.setTrace(shell._debugState)
            else:
                self._dbc.setTrace(None)
            
            # Send signal
            self.currentShellStateChanged.emit()

    
    def addShell(self, shellInfo=None):
        """ addShell()
        Add a shell to the widget. """
        
        # Create shell and add item to combobox
        shell = PythonShell(self, shellInfo)
        index = self._stack.addWidget(shell)
        self._cbShells.addItem('Python', id(shell))
        
        # Bind to signals
        shell.stateChanged.connect(self.onShellStateChange)
        shell.debugStateChanged.connect(self.onShellDebugStateChange)
        
        # Focus on it
        self._cbShells.setCurrentIndex(self._cbShells.findData(id(shell)))
        shell.setFocus()
    
    
    def removeShell(self, shell):
        """ removeShell()
        Remove an existing shell from the widget"""
        
        index = self._stack.indexOf(shell)
        self._cbShells.removeItem(self._cbShells.findData(id(shell)))
        self._stack.removeWidget(shell)
    
    
    def getCurrentShell(self):
        """ getCurrentShell()
        Get the currently active shell.
        """
        
        w = None
        if self._stack.count():
            w = self._stack.currentWidget()
        if not w:
            return None
        elif hasattr(w, '_disconnectPhase'):
            return None
        else:
            return w
    
    
    def getShells(self):
        """ Get all shell in stack as list """
        
        shells = []
        for i in range(self._stack.count()):
            shell = self.getShellAt(i)
            if shell is not None:
                shells.append(shell)
        
        return shells
    
    
    def getShellAt(self, i):
        return
        """ Get shell at current tab index """
        
        return self._stack.widget(i)
    

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
                text = "Stack Trace ({}/{}):  ".format(i, len(frames))
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
            blocknr = linenr - 1 
            editor.gotoLine(blocknr)
            cursor = editor.textCursor()
            cursor.movePosition(cursor.StartOfBlock)
            cursor.movePosition(cursor.EndOfBlock, cursor.KeepAnchor)
            editor.setTextCursor(cursor)

