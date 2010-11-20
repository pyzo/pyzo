#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Module main
This module contains the main frame. Implements the main window.
Also adds some variables to the iep namespace, such as the callLater
function which is also defined here.
"""

import os, sys
import iep

from PyQt4 import QtCore, QtGui
from queue import Queue, Empty


class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        # Store myself
        iep.main = self
        
        # Init dockwidget settings
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas,QtGui.QTabWidget.South)
        self.setDockOptions(
                QtGui.QMainWindow.AllowNestedDocks
            |  QtGui.QMainWindow.AllowTabbedDocks
            #|  QtGui.QMainWindow.AnimatedDocks
            )
        
        # Set window atrributes
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        
        # Set layout as it was the previous time
        if iep.config.state.windowPos:
            xy = iep.config.state.windowPos
            r = QtGui.qApp.desktop().visibleRegion()
            if r.contains(QtCore.QPoint(*xy)):
                self.move(*iep.config.state.windowPos)
            else:
                print('Not setting stored windowPos because its not on screen.')
        if iep.config.state.windowSize:
            self.resize(*iep.config.state.windowSize)
        if iep.config.state.windowMaximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # Load icons now
        loadIcons()
        
        # Set label and icon
        self.setWindowTitle("IEP (loading ...)")
        self.setWindowIcon(iep.icon)
        
        # Change background color to a kind of darkish python-blue,
        # to suggest that it will be filled (which it will)
        self.setStyleSheet( 'QMainWindow { background-color: #285078;} ')
        
        # Show empty window
        self.show()
        QtGui.qApp.processEvents()
        self.setUpdatesEnabled(False)
        
        # Fill the window
        self.init1()
        
        # Set mainwindow back to normal
        self.setStyleSheet('')
        self.setUpdatesEnabled(True)
        
        # Insert editor, shell, and all the tools
        self._insertEditorAndShell()
        callLater(self.restoreWindowState)
    
    
    def init1(self):
        
        # Delayed imports
        from editorStack import EditorStack
        from shellStack import ShellStack
        from menu import MenuHelper
        import codeparser
        import tools
        
        # Instantiate tool manager
        iep.toolManager = toolManager = tools.ToolManager()
        
        # Instantiate and start source-code parser
        if iep.parser is None:
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorStack(self)        
        #self.setCentralWidget(iep.editors)
        
        # Create shell stack and instantiate a default shell
        iep.shells = ShellStack(self)
        iep.shells.addShell()
        
        # Create statusbar and menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        if iep.config.view.showStatusbar:
            iep.status = self.statusBar()
        else:
            iep.status = None
            self.setStatusBar(None)
        self._menuhelper = MenuHelper(self.menuBar())
    
    
    def _insertEditorAndShell(self):
        """ Insert the editor and shell in the main window.
        The first as the central widget, the other in a dock widget.
        """
        # Set central widget
        self.setCentralWidget(iep.editors)
        # Create floater for shell
        dock = QtGui.QDockWidget("Shells", self)
        dock.setObjectName('shells')
        dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        # Insert
        dock.setWidget(iep.shells)
    
    
    def saveWindowState(self):
        """ Save which tools are loaded and all window positions. """
        import base64
        
        # store window position
        if self.windowState() == QtCore.Qt.WindowMaximized:
            iep.config.state.windowMaximized = 1
            # left,right, width, height stored when maximized
        else:
            iep.config.state.windowMaximized = 0 
            iep.config.state.windowPos = self.x(), self.y()
            iep.config.state.windowSize = self.width(), self.height()
        
        # Save tool list
        tools = iep.toolManager.getLoadedTools()
        iep.config.state.loadedTools = tools
        
        # Get state and make unicode string
        state = bytes(self.saveState())
        state = base64.encodebytes(state).decode('ascii')
        iep.config.state.windowState = state
    
    
    def restoreWindowState(self):
        """ Restore toolss and positions of all windows. """
        import base64
        
        # Obtain default style
        app = QtGui.qApp
        iep.defaultQtStyleName = str(app.style().objectName())
        # Other than gtk+, cleanlooks looks best (is my opinion)
        if 'gtk' in iep.defaultQtStyleName.lower():
            pass # Use default style
        elif 'macintosh' in iep.defaultQtStyleName.lower():
            pass # Use default style
        else:
            iep.defaultQtStyleName = 'Cleanlooks'
        
        # Set style if there is no style yet
        if not iep.config.view.qtstyle:
            iep.config.view.qtstyle = iep.defaultQtStyleName 
        
        # Set qt style and test success
        qstyle = app.setStyle(iep.config.view.qtstyle)
        if qstyle:
            # We succeeded in setting the style
            app.setPalette(QtGui.QStyle.standardPalette(qstyle))
        else:
            # We still have the default style
            pass
        
        # Load toolss
        if iep.config.state.loadedTools:            
            for toolId in iep.config.state.loadedTools:
                iep.toolManager.loadTool(toolId)
        
        # Restore state
        if iep.config.state.windowState:
            state = iep.config.state.windowState
            state = base64.decodebytes(state.encode('ascii'))
            self.restoreState(state)        
    
    
    def changeEvent(self, event):
        
        # Capture window state change events
        if event.type() == QtCore.QEvent.WindowStateChange:
            ok = [QtCore.Qt.WindowNoState, QtCore.Qt.WindowActive]
            if event.oldState() in ok:
                # Store layout if now non-maximized
                iep.config.state.windowPos = self.x(), self.y()
                iep.config.state.windowSize = self.width(), self.height()
        
        # Proceed normally
        QtGui.QMainWindow.changeEvent(self, event)
    
    
    def closeEvent(self, event):
        """ Override close event handler. """
        
        # Save settings
        iep.saveConfig()
        
        # Proceed with closing...
        result = iep.editors.closeAll()
        if not result:
            self._didClose = False
            event.ignore()
            return
        else:
            self._didClose = True
            event.accept()
        
        # Proceed with closing shells
        for shell in iep.shells:
            shell.terminateNow()
    
    
    def restart(self):
        """ Restart IEP. """
        
        # Close
        self.close()
        
        if self._didClose:
            # Get args
            args = [arg for arg in sys.argv]
            
            if not iep.isFrozen():
                # Prepend the executable name (required on Linux)
                lastBit = os.path.basename(sys.executable)
                args.insert(0, lastBit)
            
            # Replace the process!
            os.execv(sys.executable, args)
    
    
    def createPopupMenu(self):
        
        # Init menu
        menu = QtGui.QMenu()
        
        # Insert two items
        for item in ['Editors', 'Shells']:
            action = menu.addAction(item)
            action.setCheckable(True)
            action.setChecked(True)
            action.setEnabled(False)
        
        # Insert tools
        for tool in iep.toolManager.loadToolInfo():
            action = menu.addAction(tool.name)
            action.setCheckable(True)
            action.setChecked(bool(tool.instance))
            action.menuLauncher = tool.menuLauncher
        
        # Show menu and process result
        a = menu.exec_(QtGui.QCursor.pos())
        if a:
            a.menuLauncher(not a.menuLauncher(None))


def loadIcons():
    """ loadIcons()
    Load all icons in the icon dir.
    """
    
    # Construct icon (if we'd load the .ico that contains a 16x16, 32x32
    # and 48x48 image, only the largest is loaded)
    
    # Get directory containing all icons
    iconDir = os.path.join(iep.iepDir,'icons')
    
    # Construct normal iep icon
    iep.icon = QtGui.QIcon() 
    tmp = os.path.join(iconDir,'iep{}.png')
    iep.icon.addFile(tmp.format(16), QtCore.QSize(16,16), 0, 0)
    iep.icon.addFile(tmp.format(32), QtCore.QSize(32,32), 0, 0)
    iep.icon.addFile(tmp.format(48), QtCore.QSize(48,48), 0, 0)
    
    # Construct another icon to show when the current shell is busy
    iep.iconRunning = QtGui.QIcon() 
    tmp = os.path.join(iconDir,'iep{}_running.png')
    iep.iconRunning.addFile(tmp.format(16), QtCore.QSize(16,16), 0, 0)
    iep.iconRunning.addFile(tmp.format(32), QtCore.QSize(32,32), 0, 0)
    iep.iconRunning.addFile(tmp.format(48), QtCore.QSize(48,48), 0, 0)
    
    # Construct other icons
    iep.icons = {}
    for fname in os.listdir(iconDir):
        if fname.startswith('iep'):
            continue
        if fname.endswith('.png'):
            try:
                # Short and full name
                name = fname.split('.')[0]
                ffname = os.path.join(iconDir,fname)
                # Create icon
                icon = QtGui.QIcon() 
                icon.addFile(ffname, QtCore.QSize(16,16), 0, 0)
                # Store
                iep.icons[name] = icon
            except Exception:
                print('Could not load icon ', fname)


class _CallbackEventHandler(QtCore.QObject):
    """ Helper class to provide the callLater function. 
    """
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.queue = Queue()

    def customEvent(self, event):
        while True:
            try:
                callback, args = self.queue.get_nowait()
            except Empty:
                break
            try:
                callback(*args)
            except Exception as why:
                print('callback failed: {}:\n{}'.format(callback, why))

    def postEventWithCallback(self, callback, *args):
        self.queue.put((callback, args))
        QtGui.qApp.postEvent(self, QtCore.QEvent(QtCore.QEvent.User))

def callLater(callback, *args):
    """ callLater(callback, *args)
    Post a callback to be called in the main thread. 
    """
    _callbackEventHandler.postEventWithCallback(callback, *args)
    
# Create callback event handler instance and insert function in IEP namespace
_callbackEventHandler = _CallbackEventHandler()   
iep.callLater = callLater

