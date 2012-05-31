# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module main

This module contains the main frame. Implements the main window.
Also adds some variables to the iep namespace, such as the callLater
function which is also defined here.

"""

import os, sys, time
import base64
import ssdf
import iep
from iepcore.icons import IconArtist

from codeeditor.qt import QtCore, QtGui
from queue import Queue, Empty


class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None, locale=None):
        QtGui.QMainWindow.__init__(self, parent)
        
        # Set locale of main widget, so that qt strings are translated
        # in the right way
        if locale:
            self.setLocale(locale)
        
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
        
        # Load icons now
        loadIcons()
        
        # Set qt style and test success
        self.setQtStyle(None) # None means init!
        
        # Set label and icon
        self.setWindowTitle("IEP (loading ...)")
        self.setWindowIcon(iep.icon)
        
        # Change background color to a kind of darkish python-blue,
        # to suggest that it will be filled (which it will)
        self.setStyleSheet( 'QMainWindow { background-color: #285078;} ')
        
        # Restore window geometry before drawing for the first time,
        # such that the window is in the right place
        self.resize(800, 600) # default size
        self.restoreWindowState(geometryOnly=True)
        
        # Show empty window and disable updates for a while
        self.show()
        QtGui.qApp.processEvents()
        QtGui.qApp.flush()
        self.setUpdatesEnabled(False)
        
        # Populate the window (imports more code)
        self._populate()
        
        # Restore state while updates are disabled. This doesnt set the
        # state correctly, but at least approximately correct, and thereby
        # prevents flicker.
        self.restoreWindowState()
        
        # Show window again with normal background, and enable updates
        self.setStyleSheet('')
        self.setUpdatesEnabled(True)
        self.show() 
        
        # Restore one more time, but in a short while. 
        # If we do not do this, the state is not set corerctly (see issue 95)
        self._initTimer = QtCore.QTimer()
        self._initTimer.timeout.connect(self.restoreWindowState)
        self._initTimer.setInterval(10.0) # 10 ms
        self._initTimer.setSingleShot(True)
        self._initTimer.start()
    
      
    def _populate(self):
        
        # Delayed imports
        from iepcore.editorTabs import EditorTabs
        from iepcore.shellTabs import ShellStack
        from iepcore import codeparser
        import tools
        
        # Instantiate tool manager
        iep.toolManager = tools.ToolManager()
        
        # Instantiate and start source-code parser
        if iep.parser is None:
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorTabs(self)
        self.setCentralWidget(iep.editors)
        
        
        # Create floater for shell
        self._shellDock = dock = QtGui.QDockWidget(self)
        if sys.platform == 'darwin':
            #TODO: moving the shells SEGFAULTS on Mac. disable it for now
            # todo: maybe its fixed now?
            dock.setFeatures(dock.NoDockWidgetFeatures)
            # dock.setFeatures(dock.DockWidgetFloatable | dock.DockWidgetMovable)
        else:
            dock.setFeatures(dock.DockWidgetMovable)
        dock.setObjectName('shells')
        dock.setWindowTitle('Shells')
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        
        # Create shell stack
        iep.shells = ShellStack(self)
        dock.setWidget(iep.shells)
        
        # Create the default shell when returning to the event queue
        callLater(iep.shells.addShell)
        
        
        # Create statusbar
        if iep.config.view.showStatusbar:
            iep.status = self.statusBar()
        else:
            iep.status = None
            self.setStatusBar(None)
        
        # Create menu
        from iepcore import menu
        iep.keyMapper = menu.KeyMapper()
        menu.buildMenus(self.menuBar())
        
        # Add the context menu to the shell and editor
        iep.shells.addContextMenu()
        iep.editors.addContextMenu()
        
        # Load tools
        if iep.config.state.loadedTools: 
            for toolId in iep.config.state.loadedTools:
                iep.toolManager.loadTool(toolId)
    
    
    def saveWindowState(self):
        """ Save:
            * which tools are loaded 
            * geometry of the top level windows
            * layout of dockwidgets and toolbars
        """
        
        # Save tool list
        tools = iep.toolManager.getLoadedTools()
        iep.config.state.loadedTools = tools
        
        # Store window geometry
        #geometry = str( self.saveGeometry().toBase64() )
        geometry = bytes(self.saveGeometry())
        geometry = base64.encodebytes(geometry).decode('ascii')
        iep.config.state.windowGeometry = geometry
        
        # Store window state
        #state = str( self.saveState().toBase64() )
        state = bytes(self.saveState())
        state = base64.encodebytes(state).decode('ascii')
        iep.config.state.windowState = state
    
    
    def restoreWindowState(self, geometryOnly=False):
        """ Restore tools and positions of all windows. """
        
        # Restore layout of dock widgets and toolbars
        # On Linux this can mess up the geometry.
        if iep.config.state.windowState and not geometryOnly:
            try:
                state = iep.config.state.windowState
                state = base64.decodebytes(state.encode('ascii'))
                #state = QtCore.QByteArray.fromBase64(iep.config.state.windowState)
                self.restoreState(state)
            except Exception as err:
                print('Could not restore window state: ' + str(err))
        
        # Restore window geometry
        if iep.config.state.windowGeometry:
            try:
                geometry = iep.config.state.windowGeometry
                geometry = base64.decodebytes(geometry.encode('ascii'))
                #geometry = QtCore.QByteArray.fromBase64(iep.config.state.windowGeometry)
                self.restoreGeometry(geometry)  
            except Exception as err:
                print('Could not restore window geomerty: ' + str(err))
        
        
    
    def setQtStyle(self, stylename=None):
        """ Set the style and the palette, based on the given style name.
        If stylename is None or not given will do some initialization.
        If bool(stylename) evaluates to False will use the default style
        for this system. Returns the QStyle instance.
        """
        
        if stylename is None:
            # Initialize
            
            # Get native pallette (used below)
            QtGui.qApp.nativePalette = QtGui.qApp.palette()
            
            # Obtain default style name
            iep.defaultQtStyleName = str(QtGui.qApp.style().objectName())
            
            # Other than gtk+ and mac, cleanlooks looks best (in my opinion)
            if 'gtk' in iep.defaultQtStyleName.lower():
                pass # Use default style
            elif 'macintosh' in iep.defaultQtStyleName.lower():
                pass # Use default style
            else:
                iep.defaultQtStyleName = 'Cleanlooks'
            
            # Set style if there is no style yet
            if not iep.config.view.qtstyle:
                iep.config.view.qtstyle = iep.defaultQtStyleName 
        
        # Init
        if not stylename:
            stylename = iep.config.view.qtstyle
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
            shell._context.close()
        
        # Close as normal
        QtGui.QMainWindow.closeEvent(self, event)
    
    
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
    iep.icon.addFile(tmp.format(16), QtCore.QSize(16,16))
    iep.icon.addFile(tmp.format(32), QtCore.QSize(32,32))
    iep.icon.addFile(tmp.format(48), QtCore.QSize(48,48))
    
    # Construct another icon to show when the current shell is busy
    artist = IconArtist(iep.icon) # extracts the 16x16 version
    artist.setPenColor('#0B0')
    for x in range(11, 16):
        d = x-11 # runs from 0 to 4
        artist.addLine(x,6+d,x,15-d)
    pm = artist.finish().pixmap(16,16)
    #
    iep.iconRunning = QtGui.QIcon(iep.icon)
    iep.iconRunning.addPixmap(pm) # Change only 16x16 icon
    
    # Create dummy icon
    dummyIcon = IconArtist().finish()
    
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
                icon.addFile(ffname, QtCore.QSize(16,16))
                # Store
                iep.icons[name] = icon
            except Exception as err:
                iep.icons[name] = dummyIcon
                print('Could not load icon %s: %s' % (fname, str(err)))


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

