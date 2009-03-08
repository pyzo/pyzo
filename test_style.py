""" SCRIPT
To test the style for QT.

"""

from PyQt4 import QtCore, QtGui
qt = QtGui


class TestWidget(qt.QWidget):
    
    def __init__(self, parent=None):
        # init the window (create it)
        qt.QWidget.__init__(self, None)
        
        # create list
        self.list = list = qt.QListView(self)
        list.setGeometry(0,0,80,100)
        self.model = model = qt.QStandardItemModel()
        list.setModel(model)
        
        # create find/replace stuff
        yy = 100
        stext = qt.QLabel("Find / Replace", self)
        stext.setFont( qt.QFont('helvetica',8,qt.QFont.Bold) ) 
        stext.move(5,yy)
        
        hidebut = qt.QPushButton("hide", self)
        hidebut.setFont( qt.QFont('helvetica',7) )
        hidebut.setToolTip("Escape")
        hidebut.setGeometry(94,yy,24,16)
        
        yy+=18
        caseCheck = qt.QCheckBox("Match case", self)
        caseCheck.move(2,yy)
        
        findText = qt.QLineEdit(self)
        findText.setGeometry(2,yy,116,20)
        yy += 22
        findPrev = qt.QPushButton("Previous", self) 
        findPrev.setGeometry(2,yy, 58,20)
        findNext = qt.QPushButton("Next", self)
        findNext.setGeometry(60,yy,58,20)
        findPrev.setToolTip("shift-F3")
        findNext.setToolTip("F3 (ctrl-F3 to set searchstring)")
        
        
    def fillList(self):
        self.model.appendRow( qt.QStandardItem("hallo"))
        self.model.appendRow( qt.QStandardItem("what"))
        self.model.appendRow( qt.QStandardItem("This is a very long item"))
        self.model.appendRow( qt.QStandardItem("foo"))  
        self.model.appendRow( qt.QStandardItem("bar"))
        self.model.appendRow( qt.QStandardItem("And also this one, \n contains newline!"))    
        self.model.appendRow( qt.QStandardItem("more"))
        self.model.appendRow( qt.QStandardItem("and more"))  
        
class MainWindow(qt.QWidget):
    
    def __init__(self):
        
        # init the window (create it)
        qt.QWidget.__init__(self, None)
        
        # configure its size, position, etc        
        self.setGeometry(100, 100, 400, 400)        
        
        # set icon and title
        self.setWindowIcon(qt.QIcon('iep.ico'))
        self.setWindowTitle('IEP - Testing Style')
        
        # create tree
        self.model = model = qt.QStandardItemModel()             
        #model = QtGui.QDirModel()
        self.tree = tree = qt.QTreeView()
        tree.setModel(model)
        
        # test widget
        self.tw = TestWidget(self)
        
        # splitter        
        self.splitter0 = qt.QSplitter(self)
        self.splitter0.addWidget(self.tw)
        self.splitter0.addWidget(tree)
                
        # the splitter0 fills up the widget completely
        layout = qt.QHBoxLayout(self)
        layout.addWidget(self.splitter0)
        self.setLayout(layout)
        
        # show the window
        self.show()
        
    def BuildTree(self):
        self.model.appendRow( qt.QStandardItem("hallo"))
        self.model.appendRow( qt.QStandardItem("what"))
        self.model.appendRow( qt.QStandardItem("This is a very long item"))
        self.model.appendRow( qt.QStandardItem("foo"))  
        self.model.appendRow( qt.QStandardItem("bar"))
        self.model.appendRow( qt.QStandardItem("And also this one, \n contains newline!"))    
        self.model.appendRow( qt.QStandardItem("more"))
        self.model.appendRow( qt.QStandardItem("and more"))  
        self.tw.fillList()
        
#qt.QApplication.setDesktopSettingsAware(False)
app = qt.QApplication([])
app.setStyle("cleanlooks")
win = MainWindow()
win.BuildTree()
app.exec_()

# ON LINUX (KUBUNTU)
# When not using setStyle nor setDesktop***, the hide button is too small and the 
# widgets overlap. 
# When setDesktopSettingsAware to False, the style is very similar to plastique. bar 
# is then half-visible (no matter the style). In windows style the widgets do look "windows".
# In plastique, cleanlooks and windows style (setDesktop*** not used), bar is just 
# completely visible, and the buttons look good. I guess I need to let the user chose
# between these three styles. I like cleanlooks a lot!

# ON WINDOWS 
# setDesktopSettingsAware made my app not want to startup for the editorBook test.
