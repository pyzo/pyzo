import sys, os, time

from PyQt4 import QtCore, QtGui
import iep 

tool_name = "Workspace"
tool_summary = "Lists the variables in the current shell."



class WorkspaceProxy(QtCore.QObject):
    
    haveNewData = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        
        # Create timer to keep polling the process
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(2000)  # ms
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        
        # Variables
        self._variables = []
    
    
    def poll(self):
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.postRequest('VARIABLES a', self.processResponse)
        
        # If no response poll again in 5 seconds
        self._timer.start(5000)
    
    
    def processResponse(self, response, id=None):
        
        # Poll next time
        self._timer.start(2000)
        
        # Check
        if not '##IEP##' in response:
            print('Error getting VARIABLES:', response)
            return
        
        # Store variables
        self._variables = [r for r in response.split('##IEP##') if r]
        
        # Signal
        self.haveNewData.emit()
    
#     def getWhos(self):
#         
#         names = remoteEval('",".join(dir())')
#         names = names.split(',')
#         # Select names
#         names = [name for name in names if not name.startswith('__')]
#         # Get class and repr for all names at once
#         if names:
#             # Define list comprehensions (the one for the class is huge!)
#             nameString = ','.join(names)
#             classGetter = '[str(c) for c in '
#             classGetter += '[a[1] or a[0].__class__.__name__ for a in '
#             classGetter += '[(b, not hasattr(b,"__class__")) for b in [{}]'
#             classGetter += ']]]'
#             reprGetter = '[repr(name) for name in [{}]]'
#             #
#             classGetter = classGetter.format(nameString)
#             reprGetter = reprGetter.format(nameString)
#             # Use special seperator that is unlikely to be used, ever.
#             namesClass = remoteEval('"##IEP##".join({})'.format(classGetter))
#             namesRepr = remoteEval('"##IEP##".join({})'.format(reprGetter))
#             namesClass = namesClass.split('##IEP##')
#             namesRepr = namesRepr.split('##IEP##')


class WorkspaceTree(QtGui.QTreeWidget):
    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        
        # Set header stuff
        self.setHeaderHidden(False)
        self.setColumnCount(3)
        self.setHeaderLabels(['Name', 'Type', 'Repr'])
        #self.setColumnWidth(0, 100)
        self.setSortingEnabled(True)
        
        # Nice rows
        self.setAlternatingRowColors(True)
        
        # Create proxy
        self._proxy = WorkspaceProxy()
        self._proxy.haveNewData.connect(self.fillWorkspace)
    
    
    def fillWorkspace(self):
        
        # Cleat first
        self.clear()
        
        # Add elements
        for des in self._proxy._variables:
            
            # Get parts
            parts = des.split(',',4)
            if len(parts) < 4:
                continue
            
            # Create item
            kind = parts.pop(2)
            tt = '%s: %s' % (parts[0], parts[-1])
            item = QtGui.QTreeWidgetItem(parts, 0)
            item.setToolTip(0,tt)
            item.setToolTip(1,tt)
            item.setToolTip(2,tt)
            self.addTopLevelItem(item)
    

class IepWorkspace(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        self._tree = WorkspaceTree(self)
        
        # Set layout
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self._tree)
        self.setLayout(layout)
    