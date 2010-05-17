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
import ssdf

import iep
from editorStack import EditorStack
from shellStack import ShellStack
from menu import MenuHelper


from PyQt4 import QtCore, QtGui
from queue import Queue, Empty

# Create "global" parser instance
import codeparser
if not hasattr(iep, 'parser'):
    iep.parser = codeparser.Parser()
    iep.parser.start()

class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        # store myself
        iep.main = self
        
        # set layout as it was the previous time
        pos = iep.config.layout
        self.move(pos.left, pos.top)
        self.resize(pos.width, pos.heigth)
        if pos.maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # construct icon
        tmp = os.path.join(iep.path,'')
        iep.icon = QtGui.QIcon()
        iep.icon.addFile(tmp+'icon16.png', QtCore.QSize(16,16), 0, 0)
        iep.icon.addFile(tmp+'icon32.png', QtCore.QSize(32,32), 0, 0)
        iep.icon.addFile(tmp+'icon48.png', QtCore.QSize(48,48), 0, 0)
        
        # set label and icon
        self.setWindowTitle("IEP")
        self.setWindowIcon(iep.icon)
        
        # create splitter
        #self.splitter0 = QtGui.QSplitter(self)
        
        # set central widget
        iep.editors = EditorStack(self)
        self.setCentralWidget(iep.editors)
        
        # create statusbar en menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        status = self.statusBar()
        self._menuhelper = MenuHelper(self.menuBar())
        
        # create floater
        dock = QtGui.QDockWidget("Shells", self)
        dock.setObjectName('shells')
        dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        
        # insert shell stack
        iep.shells = ShellStack(self)
        dock.setWidget(iep.shells)
        #iep.shells.show()
        iep.shells.addShell()
        iep.shells.addShell()
        
        # show now
        self.restoreIepState()
        self.show()
    
    
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
        
        # store editorStack settings
        iep.editors.storeSettings()
        
        # store window position
        pos = iep.config.layout
        if self.windowState() == QtCore.Qt.WindowMaximized:
            pos.maximized = 1
            self.setWindowState(QtCore.Qt.WindowNoState)
        else:
            pos.maximized = 0            
        pos.left, pos.top = self.x(), self.y()
        pos.width, pos.heigth = self.width(), self.height()
        
        # store state
        self.saveIepState()
        
        # store config
        ssdf.save( os.path.join(iep.path,"config.ssdf"), iep.config )
    
    
    def closeEvent(self, event):
        """ Override close event handler. """
        
        if not hasattr(self, '_restarting') or not self._restarting:
            self.saveConfig()
        
        # proceed with closing...
        self._restarting = False
        result = iep.editors.closeAll()
        if not result:
            event.ignore()
        else:
            event.accept()


    def restart(self):
        """ Restart IEP without saving changes. """
        self._restarting = True
        self.close()
        
        # todo: test under windows
        args = sys.argv
#         # put a space in front of all args
#         args = []
#         for i in sys.argv:
#             args.append(" "+i)
        
        # prepend the executable name (required on Linux somehow)
        lastBit = os.path.basename(sys.executable)
        args.insert(0, lastBit)
        
        # replace the process!                
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
    
