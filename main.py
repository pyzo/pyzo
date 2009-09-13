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
from editorBook import EditorBook
from menu import MenuHelper

from PyQt4 import QtCore, QtGui
qt = QtGui



class MainWindow(qt.QMainWindow):
    
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        
        # set layout as it was the previous time
        pos = iep.config.layout
        self.move(pos.left, pos.top)
        self.resize(pos.width, pos.heigth)
        if pos.maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # set label and icon
        self.setWindowTitle("IEP")
        icon = qt.QIcon('iep.ico')
        self.setWindowIcon(icon)
        
        # create splitter
        #self.splitter0 = qt.QSplitter(self)
        
        # set central widget
        iep.editors = EditorBook(self)
        self.setCentralWidget(iep.editors)
        
        # create menu
        status = self.statusBar()
        menu = self.menuBar()
        
        MenuHelper(self.menuBar())

#         fmenu = menu.addMenu("File")
#         ds, cb = "Create new file", self.m_new
#         fmenu.addAction( self.createAction("New file", ds, "Ctrl+N", cb ))
#         ds, cb = "Close the currently selected file", self.m_close
#         fmenu.addAction( self.createAction("Close file", ds, "Ctrl+W", cb ))
#         ds, cb = "Close and restart IEP", self.m_restart
#         fmenu.addAction( self.createAction("Restart IEP", ds, "", cb ))
#         ds, cb = "Exit from IEP", self.m_exit
#         fmenu.addAction( self.createAction("Exit IEP", ds, "Alt+F4", cb ) )
#         menu.addMenu("Session")
        
        menu.triggered.connect(self.onTrigger)
#         item = ("New File",
#             "Create a new file",
#             key,
#             callback)
        
        # test dock widgets
        dock = qt.QDockWidget("Find in files", self)
        dock.setAllowedAreas(QtCore.Qt.TopDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        dock.setFeatures(qt.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
    
        
        # show now
        self.show()
    
    def onTrigger(self, action):
        print('trigger:', action.text())
        
    def m_new(self):
        iep.editors.newFile()
    def m_close(self):
        iep.editors.closeFile()
        
    def m_exit(self):
        """ Close IEP """
        self.close()
        
    def m_restart(self, event):
        """ Restart IEP """
        print('event:',event)
        self.close()
        
        # put a space in front of all args
        args = []
        for i in sys.argv:
            args.append(" "+i)
        # replace the process!                
        os.execv(sys.executable, args)
    
    
    def createAction(self, name, descr, shortcut, cb):
        """ Create an action object, with the specified stuff. """
        act = qt.QAction(name,self)
        act.setShortcut(shortcut)
        act.setStatusTip(descr)
        if cb is not None:
            act.triggered.connect(cb)
            #self.connect(act, QtCore.SIGNAL('triggered()'), cb)
        return act


    def closeEvent(self, event):
        """ Override close event handler. """
        
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
        iep.saveConfig()
        
        # proceed with closing...
        event.accept()
        
    
app = QtGui.QApplication([])
w = MainWindow()
app.exec_()

# if __name__ == "__main__":    
#     iep.startIep()
    
