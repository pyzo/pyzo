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
from queue import Queue, Empty
from pyzolib import ssdf, paths

import iep
from iep.iepcore.icons import IconArtist
from iep.codeeditor.qt import QtCore, QtGui



class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None, locale=None):
        QtGui.QMainWindow.__init__(self, parent)
        
        self._closeflag = 0  # Used during closing/restarting
        
        # Init window title and application icon
        # Set title to something nice. On Ubuntu 12.10 this text is what
        # is being shown at the fancy title bar (since it's not properly 
        # updated)
        self.setWindowTitle("The Interactive Editor for Python")
        loadAppIcons()
        self.setWindowIcon(iep.icon)
        
        # Restore window geometry before drawing for the first time,
        # such that the window is in the right place
        self.resize(800, 600) # default size
        self.restoreGeometry()
        
        # Change background of main window to create a splash-screen-efefct
        iconImage = 'pyzologo256.png' if iep.pyzo_mode else 'ieplogo256.png'
        iconImage = os.path.join(iep.iepDir, 'resources','appicons', iconImage)
        iconImage = iconImage.replace(os.path.sep, '/') # Fix for Windows
        self.setStyleSheet( """QMainWindow { 
                            background-color: #268bd2;
                            background-image: url("%s");
                            background-repeat: no-repeat;
                            background-position: center;
                            }
                            """ % iconImage)
        
        # Show empty window and disable updates for a while
        self.show()
        self.paintNow()
        self.setUpdatesEnabled(False)
        
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
        
        # Load icons
        loadIcons()
        
        # Set qt style and test success
        self.setQtStyle(None) # None means init!
        
        # Populate the window (imports more code)
        self._populate()
        
        # Revert to normal background, and enable updates
        self.setStyleSheet('')
        self.setUpdatesEnabled(True)
        
        # Restore window state, force updating, and restore again
        self.restoreState()
        self.paintNow()
        self.restoreState()
        
        # Load basic tools if new user
        if iep.config.state.newUser and not iep.config.state.loadedTools:
            iep.toolManager.loadTool('iepsourcestructure')
            iep.toolManager.loadTool('iepprojectmanager')
        
        # Present user with wizard if he/she is new.
        if iep.config.state.newUser:
            from iep.util.iepwizard import IEPWizard
            w = IEPWizard(self)
            w.show() # Use show() instead of exec_() so the user can interact with IEP
        
        # Create new shell config if there is None
        if not iep.config.shellConfigs2:
            from iep.iepcore.kernelbroker import KernelInfo
            iep.config.shellConfigs2.append( KernelInfo() )
    
    # To force drawing ourselves
    def paintEvent(self, event):
        QtGui.QMainWindow.paintEvent(self, event)
        self._ispainted = True
    
    def paintNow(self):
        """ Enforce a repaint and keep calling processEvents until
        we are repainted.
        """
        self._ispainted = False
        self.update()
        while not self._ispainted:   
            QtGui.qApp.flush()
            QtGui.qApp.processEvents()
            time.sleep(0.01)
    
    def _populate(self):
        
        # Delayed imports
        from iep.iepcore.editorTabs import EditorTabs
        from iep.iepcore.shellStack import ShellStackWidget
        from iep.iepcore import codeparser
        from iep.tools import ToolManager
        
        # Instantiate tool manager
        iep.toolManager = ToolManager()
        
        # Instantiate and start source-code parser
        if iep.parser is None:
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorTabs(self)
        self.setCentralWidget(iep.editors)
        
        
        # Create floater for shell
        self._shellDock = dock = QtGui.QDockWidget(self)
        dock.setFeatures(dock.DockWidgetMovable)
        dock.setObjectName('shells')
        dock.setWindowTitle('Shells')
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        
        # Create shell stack
        iep.shells = ShellStackWidget(self)
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
        from iep.iepcore import menu
        iep.keyMapper = menu.KeyMapper()
        menu.buildMenus(self.menuBar())
        
        # Add the context menu to the editor
        iep.editors.addContextMenu()
        iep.shells.addContextMenu()
        
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
        geometry = self.saveGeometry()
        try:
            geometry = bytes(geometry) # PyQt4
        except:
            geometry = bytes().join(geometry) # PySide
        geometry = base64.encodebytes(geometry).decode('ascii')
        iep.config.state.windowGeometry = geometry
        
        # Store window state
        state = self.saveState()
        try:
            state = bytes(state) # PyQt4
        except:
            state = bytes().join(state) # PySide
        state = base64.encodebytes(state).decode('ascii')
        iep.config.state.windowState = state
    
    
    def restoreGeometry(self, value=None):
        # Restore window position and whether it is maximized
        
        if value is not None:
            return super().restoreGeometry(value)
        
        # No value give, try to get it from the config
        if iep.config.state.windowGeometry:
            try:
                geometry = iep.config.state.windowGeometry
                geometry = base64.decodebytes(geometry.encode('ascii'))
                self.restoreGeometry(geometry)  
            except Exception as err:
                print('Could not restore window geomerty: ' + str(err))
    
    
    def restoreState(self, value=None):
        # Restore layout of dock widgets and toolbars
        
        if value is not None:
            return super().restoreState(value)
        
        # No value give, try to get it from the config
        if iep.config.state.windowState:
            try:
                state = iep.config.state.windowState
                state = base64.decodebytes(state.encode('ascii'))
                self.restoreState(state)
            except Exception as err:
                print('Could not restore window state: ' + str(err))
    
    
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
        
        # Are we restaring?
        restarting = time.time() - self._closeflag < 1.0
        
        # Save settings
        iep.saveConfig()
        
        # Proceed with closing...
        result = iep.editors.closeAll()
        if not result:
            self._closeflag = False
            event.ignore()
            return
        else:
            self._closeflag = True
            #event.accept()  # Had to comment on Windows+py3.3 to prevent error
        
        # Proceed with closing shells
        iep.localKernelManager.terminateAll()
        for shell in iep.shells:
            shell._context.close()
        
        # Close tools
        for toolname in iep.toolManager.getLoadedTools():
            tool = iep.toolManager.getTool(toolname) 
            tool.close()
        
        # Stop all threads (this should really only be daemon threads)
        import threading
        for thread in threading.enumerate():
            if hasattr(thread, 'stop'):
                try:
                    thread.stop(0.1)
                except Exception:
                    pass
        
#         # Wait for threads to die ... 
#         # This should not be necessary, but I used it in the hope that it
#         # would prevent the segfault on Python3.3. It didn't.
#         timeout = time.time() + 0.5
#         while threading.activeCount() > 1 and time.time() < timeout:
#             time.sleep(0.1)
#         print('Number of threads alive:', threading.activeCount())
        
        # Proceed as normal
        QtGui.QMainWindow.closeEvent(self, event)
        
        # Harder exit to prevent segfault. Not really a solution,
        # but it does the job until Pyside gets fixed.
        if sys.version_info >= (3,3,0) and not restarting:
            if hasattr(os, '_exit'):
                os._exit(0)
    
    
    def restart(self):
        """ Restart IEP. """
        
        self._closeflag = time.time()
        
        # Close
        self.close()
        
        if self._closeflag:
            # Get args
            args = [arg for arg in sys.argv]
            
            if not paths.is_frozen():
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
        a = menu.popup(QtGui.QCursor.pos())
        if a:
            a.menuLauncher(not a.menuLauncher(None))


def loadAppIcons():
    """ loadAppIcons()
    Load the application iconsr.
    """
    # Get directory containing the icons
    appiconDir =  os.path.join(iep.iepDir, 'resources', 'appicons')
    
    # Determine template for filename of the application icon-files.
    # Use the Pyzo logo if in pyzo_mode.
    if iep.pyzo_mode:
        fnameT = 'pyzologo{}.png'
    else:
        fnameT = 'ieplogo{}.png'
    
    # Construct application icon. Include a range of resolutions. Note that
    # Qt somehow does not use the highest possible res on Linux/Gnome(?), even
    # the logo of qt-designer when alt-tabbing looks a bit ugly.
    iep.icon = QtGui.QIcon()
    for sze in [16, 32, 48, 64, 128, 256]:
        fname = os.path.join(appiconDir, fnameT.format(sze))
        if os.path.isfile(fname):
            iep.icon.addFile(fname, QtCore.QSize(sze, sze))
    
    # Set as application icon. This one is used as the default for all
    # windows of the application.
    QtGui.qApp.setWindowIcon(iep.icon)
    
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


def loadIcons():
    """ loadIcons()
    Load all icons in the icon dir.
    """
    # Get directory containing the icons
    iconDir = os.path.join(iep.iepDir, 'resources', 'icons')
    
    # Construct other icons
    dummyIcon = IconArtist().finish()
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

