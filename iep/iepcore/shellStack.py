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
from iep import translate
from iep.iepcore.compactTabWidget import CompactTabWidget
from iep.iepcore.shell import PythonShell
from iep.iepcore.iepLogging import print
from iep.iepcore.menu import ShellTabContextMenu, ShellButtonMenu
from iep.iepcore.icons import ShellIconMaker


def shellTitle(shell, gui=False, state=False, runtime=False):
    """ Given a shell instance, build the text title to represent it.
    """ 
    
    # Build text title
    if shell._version:
        titleText = 'Python {}'.format(shell._version) 
    else:
        titleText = "Python (initializing)"
    
    # Build gui text
    gui_ = shell._startup_info.get('gui')
    if gui_ and shell._version:
        guiText = ' with ' + gui_
    else:
        guiText = ''
    
    # Build state text
    stateText = shell._state or ''
    if stateText.lower() == 'none':
        stateText = ''
    elif stateText:
        stateText = ' (%s)' % stateText
    
    # Build text for elapsed time
    e = time.time() - shell._start_time
    mm = e //60; e = e % 60
    hh = e //60; 
    ss = e % 60
    runtimeText = ' - runtime: %i:%02i:%02i' % (hh, mm, ss)
    
    # Build text
    text = titleText
    if gui:
        text += guiText
    if state:
        text += stateText
    if runtime:
        text  += runtimeText
    
    # Done
    return text


class ShellStackWidget(QtGui.QWidget):
    """ The shell stack widget provides a stack of shells.
    
    It wrapps a QStackedWidget that contains the shell objects. This 
    stack is used as a reference to synchronize the shell selection with.
    We keep track of what is the current selected shell and apply updates
    if necessary. Therefore, changing the current shell in the stack
    should be enough to invoke a full update.
    
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
        
        # create stack
        self._stack = QtGui.QStackedWidget(self)
        
        # Populate toolbar
        self._shellButton = ShellControl(self._toolbar, self._stack)
        self._dbc = DebugControl(self._toolbar)
        #
        self._toolbar.addWidget(self._shellButton)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self._dbc)
        
        # widget layout
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._stack)
        self.setLayout(layout)
        
        # make callbacks
        self._stack.currentChanged.connect(self.onCurrentChanged)
    

    def __iter__(self):
        i = 0
        while i < self._stack.count():
            w = self._stack.widget(i)
            i += 1
            yield w 
    
    
    def addShell(self, shellInfo=None):
        """ addShell()
        Add a shell to the widget. """
        
        # Create shell and add to stack
        shell = PythonShell(self, shellInfo)
        index = self._stack.addWidget(shell)
        # Bind to signals
        shell.stateChanged.connect(self.onShellStateChange)
        shell.debugStateChanged.connect(self.onShellDebugStateChange)
        # Select it and focus on it (invokes onCurrentChanged)
        self._stack.setCurrentWidget(shell)
        shell.setFocus()
    
    
    def removeShell(self, shell):
        """ removeShell()
        Remove an existing shell from the widget
        """
        self._stack.removeWidget(shell)
    
    
    def onCurrentChanged(self, index):
        """ When another shell is selected, update some things. 
        """
        
        # Get current
        shell = self.getCurrentShell()
        # Call functions
        self.onShellStateChange(shell)
        self.onShellDebugStateChange(shell)
        # Emit Signal
        self.currentShellChanged.emit()
    
    
    def onShellStateChange(self, shell):
        """ Called when the shell state changes, and is called
        by onCurrentChanged. Sets the mainwindow's icon if busy.
        """
        
        # Keep shell button and its menu up-to-date
        self._shellButton.updateShellMenu(shell)
       
        if shell is self.getCurrentShell(): # can be None
            # Update application icon
            if shell and shell._state in ['Busy']:
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
            if shell and shell._debugState:
                self._dbc.setTrace(shell._debugState)
            else:
                self._dbc.setTrace(None)
            # Send signal
            self.currentShellStateChanged.emit()
    
    
    def getCurrentShell(self):
        """ getCurrentShell()
        Get the currently active shell.
        """
        
        w = None
        if self._stack.count():
            w = self._stack.currentWidget()
        if not w:
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

    
    def addContextMenu(self):
        # A bit awkward... but the ShellMenu needs the ShellStack, so it
        # can only be initialized *after* the shellstack is created ...
        
        # Give shell tool button a menu
        self._shellButton.setMenu(ShellButtonMenu(self, 'Shell button menu'))
        self._shellButton.menu().aboutToShow.connect(self._shellButton._elapsedTimesTimer.start)
        
        # Also give it a context menu
        self._shellButton.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._shellButton.customContextMenuRequested.connect(self.contextMenuTriggered)

    
    def contextMenuTriggered(self, p):
        """ Called when context menu is clicked """
        
        # Get index of shell belonging to the tab
        shell = self.getCurrentShell()
        
        if shell:
            p = self._shellButton.mapToGlobal(self._shellButton.rect().bottomLeft())
            ShellTabContextMenu(shell=shell, parent=self).exec_(p)


class ShellControl(QtGui.QToolButton):
    """ A button that can be used to select a shell and start a new shell.
    """
    
    def __init__(self, parent, shellStack):
        QtGui.QToolButton.__init__(self, parent)
        
        # Store reference of shell stack
        self._shellStack = shellStack
        
        # Keep reference of actions corresponding to shells
        self._shellActions = []
        
        # Set text and tooltip
        self.setText('Warming up ...')
        self.setToolTip("Click to select shell.")
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setPopupMode(self.InstantPopup)
        
        # Set icon
        self._iconMaker = ShellIconMaker(self)
        self._iconMaker.updateIcon('busy') # Busy initializing
        
        # Create timer
        self._elapsedTimesTimer = QtCore.QTimer(self)
        self._elapsedTimesTimer.setInterval(200)
        self._elapsedTimesTimer.setSingleShot(False)
        self._elapsedTimesTimer.timeout.connect(self.onElapsedTimesTimer)
    
    
    def updateShellMenu(self, shellToUpdate=None):
        """ Update the shell menu. Ensure that there is a menu item
        for each shell. If shellToUpdate is given, updates the corresponding
        menu item.
        """ 
        menu = self.menu()
        
        # Get shells now active
        currentShell = self._shellStack.currentWidget() 
        shells = [self._shellStack.widget(i) for i in range(self._shellStack.count())]
        
        # Synchronize actions. Remove invalid actions
        for action in self._shellActions:
            # Check match with shells
            if action._shell in shells:
                shells.remove(action._shell)  
            else:
                menu.removeAction(action)
            # Update checked state
            if action._shell is currentShell and currentShell:
                action.setChecked(True)
            else:
                action.setChecked(False)
            # Update text if necessary
            if action._shell is shellToUpdate:
                action.setText(shellTitle(shellToUpdate, True, True, True))
        
        # Any items left in shells need a menu item
        # Dont give them an icon, or the icon is used as checkbox thingy
        for shell in shells:
            text = shellTitle(shell)
            action = menu.addItem(text, None, self._shellStack.setCurrentWidget, shell)
            action._shell = shell
            action.setCheckable(True)
            self._shellActions.append(action)
        
        # Is the shell being updated the current?
        if currentShell is shellToUpdate and currentShell is not None:
            self._iconMaker.updateIcon(currentShell._state)
            self.setText(shellTitle(currentShell, True))
        elif currentShell is None:
            self._iconMaker.updateIcon('')
            self.setText('No shell selected')
    
    
    def onElapsedTimesTimer(self):
        # Automatically turn timer off is menu is hidden
        if not self.menu().isVisible():
            self._elapsedTimesTimer.stop()
            return
        
        # Update text for each shell action
        for action in self._shellActions:
            action.setText(shellTitle(action._shell, True, True, True))



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

