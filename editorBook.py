""" EditorBook class (implemented in qt)
"""

from PyQt4 import QtCore, QtGui
qt = QtGui

barwidth = 120

class Label(qt.QLabel):
    def __init__(label, parent, name, tooltip):
        qt.QLabel.__init__(label,parent)
        label.setText(name)
        #label.connect(label, QtCore.SIGNAL('enter()'), label.highlight)
    def enterEvent(label, event):
        label.setStyleSheet("QLabel { background-color:#8888CC; }") 
        label.repaint()
    def leaveEvent(label, event):
        label.setStyleSheet("QLabel { background-color:}") 
        label.repaint()
        
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
            label = Label(self, s, "tt "+ s)
            label.setGeometry(1,y,barwidth, 14)
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
        
    
    
if __name__ == "__main__":
    app = QtGui.QApplication([])
    win = EditorBook(None)
    win.show()
