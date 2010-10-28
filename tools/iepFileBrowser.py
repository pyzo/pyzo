import sys, os, time
from PyQt4 import QtCore, QtGui
import iep 

tool_name = "File browser"
tool_summary = "Browse and search in files."


class PathInput(QtGui.QComboBox):
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)
        
        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        
        
        # To receive focus events
        #self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        
        # Flag
        self._typingFlag = False
        
        # Bind to signals
        self.editTextChanged.connect(self.onTyping)
        self.activated.connect(self.onActivated)
    
    def onActivated(self, s):
        text = self.currentText()
        self.setEditText(text+'/')
    
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
                    if sub.startswith('.'):
                        continue
                    sub = text + '/' + sub
                    if os.path.isdir(sub):
                        dirs.append(sub)
            
            text += '/'
            print(text)
            # Add possible options
            dirs.sort()
            self.clear()            
            for d in dirs:
                self.addItem(d)
            self.setEditText(texto)
            
        finally:
            self._typingFlag = False
    
    def getSubDirs(self):
        text = self.currentText()
        
        # Normalize text
        text = text.replace('\\', '/')
        text = text.replace('//', '/').replace('//', '/')
        tmp = text.rsplit('/',1)
        txt, needle = tmp[0], tmp[1]
        
        # 
        dirs = []
        if os.path.isdir(text):            
            for sub in os.listdir(text):
                if sub.startswith('.'):
                    continue
                sub2 = text + '/' + sub
                if os.path.isdir(sub2):
                    dirs.append(sub)
        
        # Add possible options
        dirs.sort()
        return dirs, text, needle
    
    
    def event(self, event):
        if isinstance(event, QtGui.QKeyEvent):
            
#             if event.key() == QtCore.Qt.Key_Backspace:
#                 tmp = QtGui.QComboBox.keyPressEvent(self, event)
#                 self.onTyping()
#                 return tmp
            if event.key() == QtCore.Qt.Key_Tab:
                self.parent()._up.setFocus(7)
                self.setFocus(7)
                return True
            else:
                return QtGui.QComboBox.event(self, event)
        else:
            return QtGui.QComboBox.event(self, event)
    
    def goUp(self):
    
        # Get text
        text = self.currentText()
        
        # Normalize text
        text = text.replace('\\', '/')
        text = text.replace('//', '/').replace('//', '/')
        text = text.rsplit('/',2)[0]
        
        self.setEditText(text+'/')
        
    def focusOutEvent(self, event):
        QtGui.QComboBox.focusOutEvent(self, event)
        
        text = self.currentText()
        
        # Normalize text
        text = text.replace('\\', '/')
        text = text.replace('//', '/').replace('//', '/')
        text = text.rstrip('/')
        
        while not os.path.isdir(text):
            text = text.rsplit('/',1)[0]
        
        self.setEditText(text+'/')
        
        
        

class IepFileBrowser(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Get initial dir
        # todo: store path
        p = os.path.expanduser('~')
        
        # Create current-directory-tool
        self._path = path = PathInput(self)
        self._up = QtGui.QToolButton(self)
        self._up.setText('up')
        
        path.setEditText(p)
        
        
        layout2 = QtGui.QHBoxLayout()
        layout2.addWidget(self._up,0)        
        layout2.addWidget(path,1)
        
        layout = QtGui.QVBoxLayout(self)
        layout.addLayout(layout2)
        layout.addStretch(1)
        self.setLayout(layout)
        
        self._up.pressed.connect(self._path.goUp)
        
        