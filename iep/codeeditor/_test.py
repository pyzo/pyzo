#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This script runs a test for the code editor component.
"""

import os, sys
from qt import QtGui, QtCore
Qt = QtCore.Qt

## Go up one directory and then import the codeeditor package

os.chdir('..') 
sys.path.insert(0,'.')
from codeeditor import CodeEditor

if __name__=='__main__':
    
    app = QtGui.QApplication([])
    
    class TestEditor(CodeEditor):
        def keyPressEvent(self,event):
            key = event.key()
            if key == Qt.Key_F1:
                self.autocompleteShow()
                return
            elif key == Qt.Key_F2:
                self.autocompleteCancel()
                return
            elif key == Qt.Key_F3:
                self.calltipShow(0, 'test(foo, bar)')
                return
            elif key == Qt.Key_Backtab: #Shift + Tab
                self.dedentSelection()
                return
           
            super(TestEditor, self).keyPressEvent(event)
            
    # Create editor instance    
    e = TestEditor(highlightCurrentLine = True, longLineIndicatorPosition = 20,
        showIndentationGuides = True, showWhitespace = True, 
        showLineEndings = True, wrap = True, showLineNumbers = True)
    
    # Run application
    e.show()
    s=QtGui.QSplitter()
    s.addWidget(e)
    s.addWidget(QtGui.QLabel('test'))
    s.show()
    app.exec_()
