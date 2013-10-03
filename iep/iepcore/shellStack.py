# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
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


def shellTitle(shell, moreinfo=False):
    """ Given a shell instance, build the text title to represent it.
    """ 
    
    # Get name
    nameText = shell._info.name
    
    # Build version text
    if shell._version:
        versionText = 'v{}'.format(shell._version) 
    else:
        versionText = 'v?'
    
    # Build gui text
    guiText = shell._startup_info.get('gui')
    guiText = guiText or ''
    if guiText.lower() in ['none', '']:
        guiText = 'without gui'
    else:
        guiText = 'with ' + guiText
    
    # Build state text
    stateText = shell._state or ''
    
    # Build text for elapsed time
    elapsed = time.time() - shell._start_time
    hh = elapsed//3600
    mm = (elapsed - hh*3600)//60
    ss = elapsed - hh*3600 - mm*60
    runtimeText = 'runtime: %i:%02i:%02i' % (hh, mm, ss)
    
    # Build text
    if not moreinfo:
        text = nameText
    else:
        text = "'%s' (%s %s) - %s, %s" % (nameText, versionText, guiText, stateText, runtimeText)
    
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
        self._toolbar.setIconSize(QtCore.QSize(16,16))
        
        # create stack
        self._stack = QtGui.QStackedWidget(self)
        
        # Populate toolbar
        self._shellButton = ShellControl(self._toolbar, self._stack)
        self._dbc = DebugControl(self._toolbar)
        self._dbs = DebugStack(self._toolbar)
        #
        self._toolbar.addWidget(self._shellButton)
        self._toolbar.addSeparator()
        # self._toolbar.addWidget(self._dbc) -> delayed, see addContextMenu()
        
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
                self._dbs.setTrace(shell._debugState)
                self._dbc.setTrace(shell._debugState)
            else:
                self._dbs.setTrace(None)
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
        
        # Add actions
        for action in iep.main.menuBar()._menumap['shell']._shellActions:
            action = self._toolbar.addAction(action)
        # Delayed-add debug control buttons
        self._toolbar.addWidget(self._dbc)
        self._toolbar.addWidget(self._dbs)
    
    
    def contextMenuTriggered(self, p):
        """ Called when context menu is clicked """
        
        # Get index of shell belonging to the tab
        shell = self.getCurrentShell()
        
        if shell:
            p = self._shellButton.mapToGlobal(self._shellButton.rect().bottomLeft())
            ShellTabContextMenu(shell=shell, parent=self).popup(p)
    
    
    def onShellAction(self, action):
        shell = self.getCurrentShell()
        if shell:
            getattr(shell, action)()



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
                action.setText(shellTitle(shellToUpdate, True))
        
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
            self.setText(shellTitle(currentShell))
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
            action.setText(shellTitle(action._shell, True))



class DebugControl(QtGui.QToolButton):
    """ A button to control debugging. 
    """
    
    def __init__(self, parent):
        QtGui.QToolButton.__init__(self, parent)
        
        # Flag
        self._debugmode = False
        
        # Set text
        self.setText(translate('debug', 'Debug'))
        self.setIcon(iep.icons.bug)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        #self.setPopupMode(self.InstantPopup)
        
        # Bind to triggers
        self.triggered.connect(self.onTriggered)
        self.pressed.connect(self.onPressed)
        self.buildMenu()
    
    
    def buildMenu(self):
        
        # Count breakpoints
        bpcount = 0
        for e in iep.editors:
            bpcount += len(e.breakPoints())
        
        # Prepare a text
        clearallbps = translate('debug', 'Clear all {} breakpoints')
        clearallbps = clearallbps.format(bpcount)
        
        # Set menu
        menu = QtGui.QMenu(self)
        self.setMenu(menu)
        
        for cmd, enabled, icon, text in [ 
                ('CLEAR', self._debugmode==0, iep.icons.bug_delete, clearallbps),
                ('PM', self._debugmode==0, iep.icons.bug_error, 
                    translate('debug', 'Postmortem: debug from last traceback')),
                ('STOP', self._debugmode>0, iep.icons.arrow_left, 
                    translate('debug', 'Stop debugging')),
                (None, None, None, None),
                ('NEXT', self._debugmode==2, None, 
                    translate('debug', 'Next: proceed until next line')),
                ('STEP', self._debugmode==2, None, 
                    translate('debug', 'Step: proceed one step')),
                ('RETURN', self._debugmode==2, None, 
                    translate('debug', 'Return: proceed until returns')),
                ('CONTINUE', self._debugmode==2, None, 
                    translate('debug', 'Continue: proceed to next breakpoint')),
                ]:
            if cmd is None:
                menu.addSeparator()
            else:
                if icon is not None:
                    a = menu.addAction(icon, text)
                else:
                    a = menu.addAction(text)
                if hasattr(text, 'tt'):
                    a.setToolTip(text.tt)    
                a.cmd = cmd
                a.setEnabled(enabled)
    
    
    def onPressed(self, show=True):
        self.buildMenu()
        self.showMenu()
    
    
    def onTriggered(self, action):
        if action.cmd == 'PM':  
            # Initiate postmortem debugging
            shell = iep.shells.getCurrentShell()
            if shell:
                shell.executeCommand('DB START\n')
        
        elif action.cmd == 'CLEAR':
            # Clear all breakpoints
            for e in iep.editors:
                e.clearBreakPoints()
        
        else:
            command = action.cmd.upper()
            shell = iep.shells.getCurrentShell()
            if shell:
                shell.executeCommand('DB %s\n' % command)
    
    
    def setTrace(self, info):
        """ Determine whether we are in debug mode. 
        """
        if info is None:
            self._debugmode = 0
        else:
            self._debugmode = info['debugmode']



class DebugStack(QtGui.QToolButton):
    """ A button that shows the stack trace.
    """
    
    def __init__(self, parent):
        QtGui.QToolButton.__init__(self, parent)
        
        # Set text and tooltip
        self._baseText = translate('debug', 'Stack')
        self.setText('%s:' % self._baseText)
        self.setIcon(iep.icons.text_align_justify)
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setPopupMode(self.InstantPopup)
        
        # Bind to triggers
        self.triggered.connect(self.onTriggered)
    
    
    def onTriggered(self, action):
        
        # Get shell
        shell = iep.shells.getCurrentShell()
        if not shell:
            return
        
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
            self.setText(self._baseText)
            self.setEnabled(False)
            iep.editors.setDebugLineIndicator('', 0)
        
        else:
            # Get the current frame
            theAction = None
            
            # Create menu and add __main__
            menu = QtGui.QMenu(self)
            self.setMenu(menu)
            
            # Fill trace
            for i in range(len(frames)):
                thisIndex = i + 1
                text = '{}: File "{}", line {}, in {}'
                text = text.format(thisIndex, *frames[i])
                action = menu.addAction(text)
                action._index = thisIndex
                action._isCurrent = False
                if thisIndex == index:
                    action._isCurrent = True
                    theAction = action
                    # Send notice to editor stack
                    filename, linenr, func = frames[i]
                    iep.editors.setDebugLineIndicator(filename, linenr)
            
            # Highlight current item and set the button text
            if theAction:
                menu.setDefaultAction(theAction)
                #self.setText(theAction.text().ljust(20))
                i = theAction._index
                text = "{} ({}/{}):  ".format(self._baseText, i, len(frames))
                self.setText(text)
            
            self.setEnabled(True)
    
    
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


