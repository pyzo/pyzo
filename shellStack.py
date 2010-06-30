""" Module shellStack
Implements the stack of shells.
"""

import os, sys, time
from PyQt4 import QtCore, QtGui

import iep
from shell import PythonShell


class ShellStack(QtGui.QFrame):
    """ The shell stack widget provides a stack of shells,
    and makes sure they are of the correct width such that 
    they have exactly 80 columns. 
    """
    
    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)
        
        # create sizer
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout.setSpacing(0)
        
        # create tab widget
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.setTabPosition(QtGui.QTabWidget.South) # North/South
        self._tabs.setMovable(True)
        
        # add widgets
        self._boxLayout.addWidget(self._tabs, 999)
        self._boxLayout.addStretch(1)
        
        
        # set layout
        self.setLayout(self._boxLayout)
        
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
        QtGui.QFrame.showEvent(self, event)
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
       