""" MAIN MODULE OF IEP
This module contains the main frame. The menu's are defined here,
and therefore also some functionality (if we do not call
methods in other windows). For example the functions for the running 
of code is implemented here (well, only the part to select the right 
code).

$Author: almar@SAS $
$Date: 2009-01-30 14:48:05 +0100 (Fri, 30 Jan 2009) $
$Rev: 946 $

"""

print("Importing iep.main ...")

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
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtGui.QTabWidget.West)
        self.setDockOptions(
                QtGui.QMainWindow.AllowNestedDocks
            |  QtGui.QMainWindow.AllowTabbedDocks
            #|  QtGui.QMainWindow.AnimatedDocks
            )
        
        # Set window atrributes
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        
        # Set layout as it was the previous time
        pos = iep.config.layout
        self.move(pos.left, pos.top)
        self.resize(pos.width, pos.heigth)
        if pos.maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # Construct icon
        tmp = os.path.join(iep.path,'')
        iep.icon = QtGui.QIcon()
        iep.icon.addFile(tmp+'icon16.png', QtCore.QSize(16,16), 0, 0)
        iep.icon.addFile(tmp+'icon32.png', QtCore.QSize(32,32), 0, 0)
        iep.icon.addFile(tmp+'icon48.png', QtCore.QSize(48,48), 0, 0)
        
        # Set label and icon
        self.setWindowTitle("IEP")
        self.setWindowIcon(iep.icon)
        
#         # Show spash screen
#         im = QtGui.QPixmap(tmp+'icon48.png')
#         iconContainer = QtGui.QSplashScreen(im)
#         iconContainer.show()
        
        # Show empty window
        self.show()
        QtGui.qApp.processEvents()
        
        # Fill the window
        self.init1()
        
        # Show finally
        self.restoreIepState()
        self.show()
    
    
    def init1(self):
        
        # Delayed imports
        from editorStack import EditorStack
        from shellStack import ShellStack
        from menu import MenuHelper
        import codeparser

        # Create "global" parser instance
        if not hasattr(iep, 'parser'):
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorStack(self)
        self.setCentralWidget(iep.editors)
        
        # Create statusbar and menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        if iep.config.showStatusbar:
            iep.status = self.statusBar()
        else:
            iep.status = None
        self._menuhelper = MenuHelper(self.menuBar())
        
        # Create floater
        dock = QtGui.QDockWidget("Shells", self)
        dock.setObjectName('shells')
        dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        
        # Insert shell stack and add the default shell
        iep.shells = ShellStack(self)
        dock.setWidget(iep.shells)
        iep.shells.addShell()
    
    
    def saveIepState(self):
        """ Save which plugins are loaded and all window positions. """
        import base64
        
        # Save plugin list
        plugins = iep.pluginManager.getLoadedPlugins()
        
        # Get state and make unicode string
        state = bytes(self.saveState())
        state = base64.encodebytes(state).decode('ascii')
        
        # Save in config
        iep.config.state = plugins + [state]
    
    
    def restoreIepState(self):
        """ Restore plugins and positions of all windows. """
        import base64
        
        # Set qt style and obtain style name of the default style
        app = QtGui.qApp
        iep.defaultStyleName = str(app.style().objectName())
        qstyle = app.setStyle(iep.config.qtstyle)
        if qstyle:
            # We succeeded in setting the style
            app.setPalette(QtGui.QStyle.standardPalette(qstyle))
        else:
            # We still have the default style
            iep.config.qtstyle = iep.defaultStyleName 
        
        # Load from config
        plugins = iep.config.state
        if not plugins:
            return
        state = plugins.pop(-1)
        
        # Load plugins
        for pluginId in plugins:
            iep.pluginManager.loadPlugin(pluginId)
        
        # Restore state
        state = base64.decodebytes(state.encode('ascii'))
        self.restoreState(state)
    
    
    def saveConfig(self):
        """ Save all configureations to file. """ 
        import ssdf
        
        # store editorStack settings
        iep.editors.storeSettings()
        
        # store window position
        layout = iep.config.layout
        if self.windowState() == QtCore.Qt.WindowMaximized:
            layout.maximized = 1
            # left,right, width, height stored when maximized
        else:
            layout.maximized = 0 
            layout.left, layout.top = self.x(), self.y()
            layout.width, layout.heigth = self.width(), self.height()
        
        # store state
        self.saveIepState()
        
        # store config
        ssdf.save( os.path.join(iep.path,"config.ssdf"), iep.config )
    
    
    def changeEvent(self, event):
        
        # Capture window state change events
        if event.type() == QtCore.QEvent.WindowStateChange:
            ok = [QtCore.Qt.WindowNoState, QtCore.Qt.WindowActive]
            if event.oldState() in ok:
                # Store layout if now non-maximized
                layout = iep.config.layout
                layout.left, layout.top = self.x(), self.y()
                layout.width, layout.heigth = self.width(), self.height()
        
        # Proceed normally
        QtGui.QMainWindow.changeEvent(self, event)
    
    
    def closeEvent(self, event):
        """ Override close event handler. """
        
        # Save settings
        self.saveConfig()
        
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
            
            # Prepend the executable name (required on Linux somehow)
            lastBit = os.path.basename(sys.executable)
            args.insert(0, lastBit)
            
            # Replace the process!                
            os.execv(sys.executable,args)


class CallbackEventHandler(QtCore.QObject):

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
            except Exception:
                print('callback failed: {}'.format(callback))

    def postEventWithCallback(self, callback, *args):
        self.queue.put((callback, args))
        QtGui.qApp.postEvent(self, QtCore.QEvent(QtCore.QEvent.User))

callbackEventHandler = CallbackEventHandler()

def callLater(callback, *args):
    """ callLater(callback, *args)
    Post a callback to be called in the main thread. 
    """
    callbackEventHandler.postEventWithCallback(callback, *args)
iep.callLater = callLater
    
    
if __name__ == "__main__":    
    iep.startIep()
    
