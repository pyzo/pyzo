# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module main

This module contains the main frame. Implements the main window.
Also adds some variables to the iep namespace, such as the callLater
function which is also defined here.

"""

import os, sys, time
import ssdf
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
        
        # Get native pallette (used when changing styles)
        QtGui.qApp.nativePalette = QtGui.qApp.palette()

        # Obtain default style
        iep.defaultQtStyleName = str(QtGui.qApp.style().objectName())
        # Other than gtk+, cleanlooks looks best (in my opinion)
        if 'gtk' in iep.defaultQtStyleName.lower():
            pass # Use default style
        elif 'macintosh' in iep.defaultQtStyleName.lower():
            pass # Use default style
        else:
            iep.defaultQtStyleName = 'Cleanlooks'
        
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
        
        # Create the default shell (after the tools so it can use settings of
        # the tools at startup)
        callLater(iep.shells.addShell)
    
    
    def init1(self):
        
        # Delayed imports
        from iepcore.editorTabs import EditorTabs
        from iepcore.shellTabs import ShellStack
        from iepcore import codeparser
        import tools
        
        # Instantiate tool manager
        iep.toolManager = toolManager = tools.ToolManager()
        
        # Instantiate and start source-code parser
        if iep.parser is None:
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorTabs(self)
        #self.setCentralWidget(iep.editors)
        

        # Create shell stack
        iep.shells = ShellStack(self)
        # The default shell is instantiated after the tools are loaded

        # Create statusbar and menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        if iep.config.view.showStatusbar:
            iep.status = self.statusBar()
        else:
            iep.status = None
            self.setStatusBar(None)
        
        if 'useNewMenus' in iep.config.advanced and iep.config.advanced.useNewMenus:
            from iepcore import menu
            iep.keyMapper = menu.KeyMapper()
            menu.buildMenus(self.menuBar())
            
            # Add the context menu to the shell tab bar
            iep.shells.addContextMenu()
        else:
            from iepcore.menu_old import MenuHelper
            self._menuhelper = MenuHelper(self.menuBar())
    
    # todo: remove old menu
    
    def _insertEditorAndShell(self):
        """ Insert the editor and shell in the main window.
        The first as the central widget, the other in a dock widget.
        """
        # Set central widget
        self.setCentralWidget(iep.editors)
        # Create floater for shell
        dock = QtGui.QDockWidget("Shells", self)
        dock.setObjectName('shells')
        if sys.platform == 'darwin':
            #TODO: moving the shells SEGFAULTS on Mac. disable it for now
            dock.setFeatures(dock.NoDockWidgetFeatures)
        else:
            dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable)

        self._shellDock = dock

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
        
        # Set style if there is no style yet
        if not iep.config.view.qtstyle:
            iep.config.view.qtstyle = iep.defaultQtStyleName 
        
        # Set qt style and test success
        self.setQtStyle(iep.config.view.qtstyle)
        
        # Load tools
        if iep.config.state.loadedTools: 
            for toolId in iep.config.state.loadedTools:
                iep.toolManager.loadTool(toolId)
        
        # Restore state
        if iep.config.state.windowState:
            state = iep.config.state.windowState
            state = base64.decodebytes(state.encode('ascii'))
            self.restoreState(state)        
    
    
    
    def setQtStyle(self, stylename):
        """ Set the style and the palette, based on the given style name.
        Returns the QStyle instance.
        """
        
        # Init
        useStandardStyle = False
        stylename2 = stylename
        
        # Handle special cleanlooks style
        if stylename.lower().startswith('cleanlooks'):
            stylename2 = stylename.rstrip('+')
            if stylename2 != stylename:
                useStandardStyle = True
        
        # Try changing the style
        qstyle = QtGui.qApp.setStyle(stylename2)
        
        # Set palette
        if qstyle:
            if useStandardStyle:
                QtGui.qApp.setPalette(QtGui.QStyle.standardPalette(qstyle))
            else:
                QtGui.qApp.setPalette(QtGui.qApp.nativePalette)
        
        # Done
        return qstyle
    
    
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
        iep.localKernelManager.terminateAll()
        for shell in iep.shells:
            shell._context.destroy()
    
    
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
    iep.icons = ssdf.new()
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

