""" Module shellStack
Implements the stack of shells.
"""

import os, sys, time
from PyQt4 import QtCore, QtGui

import iep
from shell import PythonShell


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
    
    def addShell(self, pythonExecutable=None):
        """ addShell()
        Add a shell to the widget. """
        shell = PythonShell(pythonExecutable)
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
            action = menu.addAction('__main__ (stop debugging)')
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
    
    
# 
# class DebugControl2(QtGui.QWidget):
#     def __init__(self, parent):
#         QtGui.QWidget.__init__(self, parent)
#         
#         # Create button
#         self._but = QtGui.QPushButton(self)
#         self._but.setToolTip("Start/Stop post mortem debugging.")
#         self._but.setText('Post mortem')
#         self._but.move(0,0)
#         
#         
#         # Create list
#         self._list = QtGui.QToolButton(self)
#         self._list.setText("__main__")
#         self._list.move(0,0)
#         # Attach menu
#         self._menu = QtGui.QMenu(self._list)
#         self._list.setMenu(self._menu)
#         a = self._menu.addAction("__main__")
#         b = self._menu.addAction("aap")
#         self._menu.addAction("noot")
#         self._menu.addAction("mies")
#         self._menu.setDefaultAction(b)
#         
#         self._list.setPopupMode(self._list.InstantPopup)
#         
#         self._but.setMinimumHeight(26)
#         
#         # Layout
#         self._sizer =  QtGui.QHBoxLayout(self)
#         self._sizer.addStretch(1)
#         self._sizer.addWidget(self._list, 0)
#         self._sizer.addWidget(self._but, 0)
# #         self.setLayout(self._sizer)
#         
#         # 
#         self.setMinimumSize(120,16)
#         self.resize(120,16)
#         self._sizer.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
#     
#     
# #     def minimumSizeHint(self):
# #         return QtCore.QSize(100,26)
#         
#     def sizeHint(self):
#         return self.size()#QtCore.QSize(200,300)