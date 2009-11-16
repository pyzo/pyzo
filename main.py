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
from menu import MenuHelper


from PyQt4 import QtCore, QtGui
qt = QtGui



class MainWindow(qt.QMainWindow):
    
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        
        # store myself
        iep.main = self
        
        # set layout as it was the previous time
        pos = iep.config.layout
        self.move(pos.left, pos.top)
        self.resize(pos.width, pos.heigth)
        if pos.maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # set label and icon
        self.setWindowTitle("IEP")
        iep.icon = qt.QIcon('iep.ico')
        self.setWindowIcon(iep.icon)
        
        # create splitter
        #self.splitter0 = qt.QSplitter(self)
        
        # set central widget
        iep.editors = EditorStack(self)
        self.setCentralWidget(iep.editors)
        
        # create statusbar en menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        status = self.statusBar()
        self._menuhelper = MenuHelper(self.menuBar())
        
        # test dock widgets
        dock = qt.QDockWidget("Find in files", self)
        dock.setAllowedAreas(QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        dock.setFeatures(qt.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
    
        
        # show now
        self.show()
    
    def onTrigger(self, action):
        print('trigger:', action.text())
    

    def saveConfig(self):
        """ Save all configureations to file. """ 
        
        # store editorStack settings
        iep.editors.storeSettings()
        
        # store splitter layout
        pos = iep.config.layout
        if self.windowState() == QtCore.Qt.WindowMaximized:
            pos.maximized = 1
            self.setWindowState(QtCore.Qt.WindowNoState)
        else:
            pos.maximized = 0            
        pos.left, pos.top = self.x(), self.y()
        pos.width, pos.heigth = self.width(), self.height()
        
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
        
        # put a space in front of all args
        args = []
        for i in sys.argv:
            args.append(" "+i)
        
        # replace the process!                
        os.execv(sys.executable, args)
    
    
if __name__ == "__main__":    
    iep.startIep()
    
