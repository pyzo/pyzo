# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

"""
This file provides the pyzo history viewer. It contains two main components: the
History class, which is a Qt model, and the PyzoHistoryViewer, which is a Qt view



"""

import sys, os, time, re
from pyzolib.qt import QtCore, QtGui
import pyzo
from pyzo import translate
from pyzo.core.menu import Menu

tool_name = "History viewer"
tool_summary = "Shows the last used commands."



class HistoryViewer(QtGui.QListView):
    """
    The history viewer has several ways of using the data stored in the history:
     - double click a single item to execute in the current shell
     - drag and drop one or multiple selected lines into the editor or any 
       other widget or application accepting plain text
     - copy selected items using the copy item in the pyzo edit menu
     - copy selected items using the context menu
     - execute selected items in the current shell using the context menu
    """
    def __init__(self, parent = None):
        super().__init__(parent)
        
        # Drag/drop
        self.setSelectionMode(self.ExtendedSelection)
        self.setDragEnabled(True)
        
        # Double click
        self.doubleClicked.connect(self._onDoubleClicked)
        
        # Context menu
        self._menu = Menu(self, translate("menu", "History"))
        self._menu.addItem(translate("menu", "Copy ::: Copy selected lines"),
            pyzo.icons.page_white_copy, self.copy, "copy")
        self._menu.addItem(translate("menu", "Run ::: Run selected lines in current shell"),
            pyzo.icons.run_lines, self.runSelection, "run")
        
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onCustomContextMenuRequested)
        

        
    def runSelection(self, event = None):
        text = self.model().plainText(self.selectedIndexes())
        shell = pyzo.shells.getCurrentShell()
        if shell is not None:
            shell.executeCommand(text)
        
    def copy(self, event = None):
        text = self.model().plainText(self.selectedIndexes())
        QtGui.qApp.clipboard().setText(text)
        
    def _onCustomContextMenuRequested(self, pos):
        self._menu.popup(self.viewport().mapToGlobal(pos))
        
    def _onDoubleClicked(self, index):
        text = self.model().data(index, QtCore.Qt.DisplayRole)
        
        shell = pyzo.shells.getCurrentShell()
        if shell is not None:
            shell.executeCommand(text + '\n')
    
        
    def setModel(self, model):
        """
        As QtGui.QListView.setModel, but connects appropriate signals
        """
        if self.model() is not None:
            self.model().rowsInserted.disconnect(self.scrollToBottom)
        
        super().setModel(model)
        self.model().rowsInserted.connect(self.scrollToBottom)
        self.scrollToBottom()
    
class PyzoHistoryViewer(HistoryViewer):
    """
    PyzoHistoryViewer is a thin HistoryViewer that connects itself to the shared
    history of the pyzo shell stack
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setModel(pyzo.shells.sharedHistory)
        

class History(QtGui.QStringListModel):
    markerPrefix = None # Text to prepend to the marker, or None for no marker
    maxLines = 100 # Only enforced upon loading
    def __init__(self, fname):
        super().__init__()
        
        self._file = None
        
        try:
            filename = os.path.join(pyzo.appDataDir, fname)
            if not os.path.isfile(filename):
                open(filename, 'wt').close()
            file = self._file = open(filename, 'r+', encoding = 'utf-8')
        
            # Truncate the file to my max number of lines
            lines = file.readlines()
            if len(lines) > self.maxLines:
                lines = lines[-self.maxLines:]
                
                # move to start of file, write the last lines and truncate
                file.seek(0)
                file.writelines(lines)
                file.truncate()
            
            # Move to the end of the file for appending
            file.seek(0, 2) # 2 = relative to end
            
            self.setStringList([line.rstrip() for line in lines])
            
        except Exception as e:
            print ('An error occurred while loading the history: ' + str(e))
            self._file = None
        
        # When data is appended for the first time, a marker will be appended first
        self._firstTime = True
        
    
    def plainText(self, indexes):
        """
        Get the \n separated text for the selected indices (includes \n at the end)
        """
        text = ""
        for index in indexes:
            if index.isValid():
                text += self.data(index, QtCore.Qt.DisplayRole) + "\n"
        return text

    def mimeTypes(self):
        return ["text/plain"]
        
    def mimeData(self, indexes):
        mimeData = QtCore.QMimeData()
        mimeData.setData("text/plain", self.plainText(indexes))
        return mimeData
        
    
    def flags(self, item):
        return QtCore.Qt.ItemIsSelectable | \
            QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEnabled    
        
    def append(self, value):
        # When data is appended for the first time, a marker will be appended first
        if self._firstTime:
            if self.markerPrefix is not None:
                self._append(self.markerPrefix + time.strftime("%c"))
            self._firstTime = False
        
        self._append(value)
        
        
    def _append(self, value):
        value = value.rstrip()
        
        length = self.rowCount()
        self.insertRows(length, 1)
        self.setData(self.index(length), value) 
        
        if self._file is not None:
            self._file.write(value +'\n')
            self._file.flush()
         


class PythonHistory(History):
    """
    A history-list that is aware of Python syntax. It inserts a Python-formatted
    date / time upon first append after creation, and it shows Python comments
    in green
    """
    markerPrefix = "# "
    def data(self, index, role):
        if role == QtCore.Qt.ForegroundRole:
            text = super().data(index, QtCore.Qt.DisplayRole)
            if text.lstrip().startswith('#'):
                return QtGui.QBrush(QtGui.QColor('#007F00'))
        return super().data(index, role)
        

if __name__ == '__main__':
    import pyzo.core.main
    pyzo.core.main.loadIcons()
    history = PythonHistory('shellhistorytest.py')
    view = PyzoHistoryViewer()
    view.setModel(history)
    view.show()
    history.append('test')