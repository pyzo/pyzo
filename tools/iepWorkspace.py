# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


import sys, os, time

from PyQt4 import QtCore, QtGui
import iep 

tool_name = "Workspace"
tool_summary = "Lists the variables in the current shell's namespace."



def splitName(name):
    """ splitName(name)    
    Split an object name in parts, taking dots and indexing into account.
    """    
    name = name.replace('[', '.[')
    parts = name.split('.')
    return [p for p in parts if p]


def joinName(parts):
    """ joinName(parts)    
    Join the parts of an object name, taking dots and indexing into account.
    """    
    name = '.'.join(parts)
    return name.replace('.[', '[')


class WorkspaceProxy(QtCore.QObject):
    """ WorkspaceProxy
    
    A proxy class to handle the asynchonous behaviour of getting information
    from the shell. The workspace tool asks for a certain name, and this
    class notifies when new data is available using a qt signal.
    
    """
    
    haveNewData = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        
        # Variables
        self._variables = []
        
        # Element to get more info of
        self._name = ''
        
        # Bind to events
        iep.shells.currentShellChanged.connect(self.onCurrentShellChanged)
        iep.shells.currentShellStateChanged.connect(self.onCurrentShellStateChanged)
        
        # Initialize
        self.onCurrentShellStateChanged()
    
    
    
    def addNamePart(self, part):
        """ addNamePart(part)
        Add a part to the name.
        """
        parts = splitName(self._name)
        parts.append(part)
        self.setName(joinName(parts))
    
    
    def setName(self, name):
        """ setName(name)        
        Set the name that we want to know more of. 
        """
        self._name = name
        
        shell = iep.shells.getCurrentShell()
        if shell:
            future = shell._request.dir2(self._name)
            future.add_done_callback(self.processResponse)
    
    
    def goUp(self):
        """ goUp()
        Cut the last part off the name. 
        """
        parts = splitName(self._name)
        if parts:
            parts.pop()
        self.setName(joinName(parts))
    
    
    def onCurrentShellChanged(self):
        """ onCurrentShellChanged()
        When no shell is selected now, update this. In all other cases,
        the onCurrentShellStateChange will be fired too. 
        """
        shell = iep.shells.getCurrentShell()
        if not shell:
            self._variables = []
            self.haveNewData.emit()
    
    
    def onCurrentShellStateChanged(self):
        """ onCurrentShellStateChanged()
        Do a request for information! 
        """ 
        shell = iep.shells.getCurrentShell()
        if not shell:
            # Should never happen I think, but just to be sure
            self._variables = []
        elif shell._state.lower() != 'busy':
            future = shell._request.dir2(self._name)
            future.add_done_callback(self.processResponse)
    
    
    def processResponse(self, future):
        """ processResponse(response)
        We got a response, update our list and notify the tree.
        """
        if future.exception() or future.cancelled():
            response = []
        else:
            response = future.result()
        self._variables = response
        self.haveNewData.emit()
    
    


class WorkspaceTree(QtGui.QTreeWidget):
    """ WorkspaceTree
    
    The tree that displays the items in the current namespace.
    I first thought about implementing this using the mode/view 
    framework, but it is so much work and I can't seem to fully 
    understand how it works :(
    
    The QTreeWidget is so very simple and enables sorting very 
    easily, so I'll stick with that ...
    
    """
    
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
        self.setRootIsDecorated(False)
        
        # Create proxy
        self._proxy = WorkspaceProxy()
        self._proxy.haveNewData.connect(self.fillWorkspace)
        
        # For menu
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self._menu = QtGui.QMenu()
        self._menu.triggered.connect(self.contextMenuTriggered)
        
        # Bind to events
        self.itemActivated.connect(self.onItemExpand)
    
    
    def contextMenuEvent(self, event):
        """ contextMenuEvent(event)
        Show the context menu. 
        """
        
        QtGui.QTreeView.contextMenuEvent(self, event)
        
        # Get if an item is selected
        item = self.currentItem()
        if not item:
            return
        
        # Create menu
        self._menu.clear()
        for a in ['Show namespace', 'Show help', 'Delete']:
            action = self._menu.addAction(a)
            parts = splitName(self._proxy._name)
            parts.append(item.text(0))
            action._objectName = joinName(parts)
            action._item = item
        
        # Show
        self._menu.exec_(QtGui.QCursor.pos())
    
    
    def contextMenuTriggered(self, action):
        """ contextMenuTriggered(action)
        Process a request from the context menu.
        """
        
        # Get text
        req = action.text().lower()
        
        if 'namespace' in req:
            # Go deeper
            self.onItemExpand(action._item)
        
        elif 'help' in req:
            # Show help in help tool (if loaded)
            hw = iep.toolManager.getTool('iepinteractivehelp')
            if hw:
                hw.setObjectName(action._objectName)
        
        elif 'delete' in req:
            # Delete the variable
            shell = iep.shells.getCurrentShell()
            if shell:
                shell.processLine('del ' + action._objectName)
    
    
    def onItemExpand(self, item):
        """ onItemExpand(item)
        Inspect the attributes of that item.
        """
        self._proxy.addNamePart(item.text(0))
    
    
    def fillWorkspace(self):
        """ fillWorkspace()
        Update the workspace tree.
        """
        
        # Clear first
        self.clear()
        
        # Set name
        line = self.parent()._line
        line.setText(self._proxy._name)
        
        
        # Add elements
        for des in self._proxy._variables:
            
            # Get parts
            parts = des.split(',',4)
            if len(parts) < 4:
                continue
            
            # Pop the 'kind' element
            kind = parts.pop(2)
            
            # Create item
            item = QtGui.QTreeWidgetItem(parts, 0)
            self.addTopLevelItem(item)
            
            # Set tooltip
            tt = '%s: %s' % (parts[0], parts[-1])
            item.setToolTip(0,tt)
            item.setToolTip(1,tt)
            item.setToolTip(2,tt)


class IepWorkspace(QtGui.QWidget):
    """ IepWorkspace
    
    The main widget for this tool.
    
    """
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Create tool button
        self._up = QtGui.QToolButton(self)
        style = QtGui.qApp.style()
        self._up.setIcon( style.standardIcon(style.SP_ArrowLeft) )
        self._up.setIconSize(QtCore.QSize(16,16))
        
        # Create "path" line edit
        self._line = QtGui.QLineEdit(self)
        self._line.setReadOnly(True)
        self._line.setStyleSheet("QLineEdit { background:#ddd; }")
        self._line.setFocusPolicy(QtCore.Qt.NoFocus)
        
        # Create tree
        self._tree = WorkspaceTree(self)
        
        # Set layout
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self._up, 0)
        layout.addWidget(self._line, 1)
        #
        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.addLayout(layout, 0)
        mainLayout.addWidget(self._tree, 1)
        mainLayout.setSpacing(2)
        self.setLayout(mainLayout)
        
        # Bind up event
        self._up.pressed.connect(self._tree._proxy.goUp)
