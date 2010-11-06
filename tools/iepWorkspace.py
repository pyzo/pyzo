import sys, os, time

from PyQt4 import QtCore, QtGui
import iep 

tool_name = "Workspace"
tool_summary = "Lists the variables in the current shell."



class WorkspaceProxy(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
    

class WorkspaceModel(QtCore.QAbstractItemModel):
    def __init__(self):
        QtCore.QAbstractItemModel.__init__(self)
    
    
class IepWorkspace(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Create view and model
        self._model = WorkspaceModel()
        self._view = QtGui.QTreeView(self)
        self._view.setModel(self._model)
        
        # Set layout
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self._view)
        self.setLayout(layout)
    