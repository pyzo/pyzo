""" EditorBook class (implemented in qt)
"""

from PyQt4 import QtCore, QtGui
qt = QtGui

barwidth = 120

class Label(qt.QLabel):
    """ Label class, labels for a list of files and projects.
    Some of the styling is implemented here. I advocate reusing
    the labels. Unused labales can be hidden.
    """
    # type
    TYPE_HIDDEN = 0
    TYPE_FILE = 1
    TYPE_PROJECT = 2
    # style
    STYLE_NORMAL = 0
    STYLE_HOOVER = 1
    STYLE_SELECTED = 2
    
    def __init__(self, parent):
        """ Create the label. """
        
        qt.QLabel.__init__(self,parent)
        
        # init
        self._isSelected = False
        self._indent = 1
        self._type = Label.TYPE_HIDDEN
        
        # test framewidths when raised
        self.setLineWidth(1)
        self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
        self._frameWidth = self.frameWidth() + 3 # correction        
        self.setFrameStyle(0)
    
    def reset(self, type, name, tooltip, selected=False, indent=1):
        """ (re)set the label. type can be 
        Label.TYPE_HIDDEN, Label.TYPE_FILE, or Label.TYPE_PROJECT.
        Indicate whether the file is selected, and the amount of
        indentation for the label (in pixels).
        """
        # hide/show
        if type==Label.TYPE_HIDDEN:
            self.hide()
        else:
            self.show()
        # set stuff
        self.setText(name)
        self.setToolTip(tooltip)
        self._type = type
        self._isSelected = selected
        # set indent and size        
        self._indent = indent
        self.resize(barwidth-indent, 15)
        # update
        self.updateStyle()
    
    def hide(self):
        """ Override hide """
        self._type = Label.TYPE_HIDDEN
        qt.QLabel.hide(self)
    
    def makeDirty(self, dirty):        
        """ Indicate that the file is dirty """
        self.setText( "*"+self.text() )
        self.setStyleSheet("QLabel { color:#603000 }")
    
    def makeMain(self, main):
        """ Make the file appear as a main file """
        if main:       
            self.setStyleSheet("QLabel { font:bold ; color:blue }")
        else:
            self.setStyleSheet("QLabel { font: ; color: }")
    
    def updateStyle(self):
        """ Update the style. Automatically detects whether the mouse
        is over the label. Depending on the type and whether the file is
        selected, sets its appearance and redraw! """
        
        if self._type == Label.TYPE_HIDDEN:
            return        
        elif self._type == Label.TYPE_FILE:
            if self._isSelected:
                self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Sunken)
                self.move(self._indent ,self.y())
            elif self.underMouse():
                self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
                self.move(self._indent ,self.y())
            else:            
                self.setFrameStyle(0)
                self.move(self._frameWidth+self._indent,self.y())                
        elif self._type == Label.TYPE_PROJECT:
            if self.underMouse():
                self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Plain)
                self.move(self._indent,self.y())
            else:
                self.setFrameStyle(0)
                self.move(self._frameWidth+self._indent,self.y())            
        self.repaint()
    
    def enterEvent(self, event):
        self.updateStyle()
    def leaveEvent(self, event):        
        self.updateStyle()
    
        
class FileListCtrl(qt.QWidget):
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        self.resize(barwidth,300)
        
        
        # create list of items
        self._items = []
        self.DrawList()
        
        
    def DrawList(self):
        tmp = ["asd", "foo", "bar", "iep.py", "lala.oy"]
        
        # clear old labels
        for label in self._items:
            label.close()            
        self._items= []
        
        y = 10
        for s in tmp:
            label = Label(self)
            if y>30:
                label.reset(Label.TYPE_FILE, s,self.tr("tooltip"),indent=10)
            else:
                label.reset(Label.TYPE_FILE, s,self.tr("tooltip"))
            label.move(label.x(),y)
            y+=15
#         for s in tmp:
#             label = qt.QLabel(self)
#             label.setText(s)
#             label.setGeometry(1,y,barwidth, 14)
#             if y<30:
#                 label.setStyleSheet("QLabel { background-color:#8888CC; }")            
#             self._items.append(label)
#             label.setToolTip("tooltip "+s)
#             
#             y+=15
            
    
            
        
class EditorBook(qt.QWidget):
    
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        self.list = FileListCtrl(self)
        #self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips,True)
    
    
if __name__ == "__main__":
    app = QtGui.QApplication([])
    win = EditorBook(None)
    win.show()
