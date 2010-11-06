import sys, os, time

from PyQt4 import QtCore, QtGui
import iep 

tool_name = "Workspace"
tool_summary = "Lists the variables in the current shell."



class WorkspaceProxy(QtCore.QObject):
    def __init__(self, model):
        QtCore.QObject.__init__(self)
        
        # Store model
        self._model = model
    
    
    def getWhos(self):
        
        names = remoteEval('",".join(dir())')
        names = names.split(',')
        # Select names
        names = [name for name in names if not name.startswith('__')]
        # Get class and repr for all names at once
        if names:
            # Define list comprehensions (the one for the class is huge!)
            nameString = ','.join(names)
            classGetter = '[str(c) for c in '
            classGetter += '[a[1] or a[0].__class__.__name__ for a in '
            classGetter += '[(b, not hasattr(b,"__class__")) for b in [{}]'
            classGetter += ']]]'
            reprGetter = '[repr(name) for name in [{}]]'
            #
            classGetter = classGetter.format(nameString)
            reprGetter = reprGetter.format(nameString)
            # Use special seperator that is unlikely to be used, ever.
            namesClass = remoteEval('"##IEP##".join({})'.format(classGetter))
            namesRepr = remoteEval('"##IEP##".join({})'.format(reprGetter))
            namesClass = namesClass.split('##IEP##')
            namesRepr = namesRepr.split('##IEP##')


class WorkspaceModel(QtCore.QAbstractItemModel):
    def __init__(self):
        QtCore.QAbstractItemModel.__init__(self)
    
    def data(self, index, role):
        if not index.isValid() or role not in [0, 8]:
            return None
        
        # get menu or action item
        item = index.internalPointer()
        if index.column() == 0:
            return 'aap'
        if index.column() == 1:
            return 'noot'
        if index.column() == 2:
            return 'mies'
    
    
    def rowCount(self, parent):
        if parent.isValid():
            return 0
        else:
            return 4
    
    def columnCount(self, parent):
        return 3
    
    
    def headerData(self, section, orientation, role):
        if role == 0:# and orientation==1:
            tmp = ['Name','Type','Repr']
            return tmp[section]
    
    
    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        
        return QtCore.QModelIndex()
        
#         item = index.internalPointer()
#         pitem = item.parent()
#         if pitem is self._root:
#             return QtCore.QModelIndex()
#         else:
#             L = pitem.parent().actions()
#             row = 0
#             if pitem in L:
#                 row = L.index(pitem)
#             return self.createIndex(row, 0, pitem)
    
    def index(self, row, column, parent):
#         if not self.hasIndex(row, column, parent):
#             return QtCore.QModelIndex()
        # establish parent
        return self.createIndex(row, column, )
        
#         if not parent.isValid():
#             parentMenu = self._root
#         else:
#             parentMenu = parent.internalPointer()
#         # produce index and make menu if the action represents a menu
#         childAction = parentMenu.actions()[row]
#         if childAction.menu():
#             childAction = childAction.menu()        
#         return self.createIndex(row, column, childAction)
#         # This is the trick. The internal pointer is the way to establish
#         # correspondence between ModelIndex and underlying data.
    
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
    