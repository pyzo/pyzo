import sys, os, time
from PyQt4 import QtCore, QtGui
import iep 

tool_name = "File browser"
tool_summary = "Browse and search in files."


class PathInput(QtGui.QComboBox):
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)
        
        self.setEditable(True)
        self.setInsertPolicy(self.InsertAtTop)
        
        
        # To receive focus events
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        
        # Flag
        self._typingFlag = False
        
        # Bind to signals
        self.editTextChanged.connect(self.onTyping)
    
    
    def onTyping(self, text=None):
        
        if self._typingFlag:
            return
        
        self._typingFlag = True
        
        try:
            if text is None:
                text = self.currentText()
            texto = text
            
            # Normalize text
            text = text.replace('\\', '/')
            text = text.replace('//', '/').replace('//', '/')
            text = text.rsplit('/',1)[0]
            
            
            # 
            dirs = []
            if os.path.isdir(text):            
                for sub in os.listdir(text):
                    sub = text + '/' + sub
                    if os.path.isdir(sub):
                        dirs.append(sub)
            
            text += '/'
            print(text)
            # Add possible options
            self.clear()
            for d in dirs:
                self.addItem(d)
            self.setEditText(texto)
            
        finally:
            self._typingFlag = False

    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Backspace:
            QtGui.QComboBox.keyPressEvent(self, event)
            self.onTyping()
        elif event.key() == QtCore.Qt.Key_Tab:
            pass # todo: complete
        else:
            QtGui.QComboBox.keyPressEvent(self, event)
    
    def focusOutEvent(self, event):
        QtGui.QComboBox.focusOutEvent(self, event)
        self._typingFlag = True
        try:
            text = self.currentText()
            self.clear()
            self.addItem('aap')
            self.addItem('noot')
            self.addItem('mies')            
            self.setEditText(text)
        finally:
            self._typingFlag = False
        

class IepFileBrowser(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Get initial dir
        # todo: store path
        p = os.path.expanduser('~')
        
        # Create current-directory-tool
        self._path = path = PathInput(self)
#         path.setEditable(True)
#         path.setInsertPolicy(path.InsertAtTop)
        
#         path.addItem('aap')
#         path.addItem('noot')
        path.setEditText(p)
        
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(path,0)
        layout.addStretch(1)
        self.setLayout(layout)
        
        