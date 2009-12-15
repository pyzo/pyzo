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
        
        # create and add widgets
        self._tabs = QtGui.QTabWidget(self)
        self._ws = QtGui.QFrame(self)
        self._boxLayout.addWidget(self._ws, 1)
        self._boxLayout.addWidget(self._tabs, 0)
        
        # set layout
        self.setLayout(self._boxLayout)
        
        # make callbacks
        self._tabs.currentChanged.connect(self.sizeShellTo80Columns)
    
    def addShell(self):
        """ addShell()
        Add a shell to the widget. """
        shell = PythonShell(None)
        self._tabs.addTab(shell, 'Python (v?)')
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
        else:
            return w
        
    
    def sizeShellTo80Columns(self, event=None):
        """ Is the name not descriptive enough?
        """
        # are we hidden?
        if not self.isVisible():
            return
            
        # shell now selected
        shell = self.getCurrentShell()
        if shell is None:
            return
        
#         # get its current size
#         w,h = shell.size()  
        
        # get size it should be (but font needs to be monospaced!
        w = shell.textWidth(32, "-"*80)
        w += 26 # add scrollbar and margin
        
        # clean up
        self.resize(w,shell.height())
        # use result to set minsize of the NoteBook (+8 border pixels): 
        # this makes the sizer behave like we want...
#         ww,hh = self.book.GetSize()        
#         self.book.SetMinSize((w+8,hh))        
#         self.Layout()
#         # let's redraw, because I see some artifacts when I only do Update()
#         self.Refresh()