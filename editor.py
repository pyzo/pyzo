""" Module editor
Defines the IepEditor class which is used to edit documents.
This module/class also implements all the relatively low level
file loading/saving /reloading stuff.

"""
import os

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui

from baseTextCtrl import BaseTextCtrl, normalizePath


def determineLineEnding(text):
    """get the line ending style used in the text.
    \n, \r, \r\n,
    The EOLmode is determined by counting the occurances of each
    line ending...    
    """
    # test line ending by counting the occurances of each
    c_win = text.count("\r\n")
    c_mac = text.count("\r") - c_win
    c_lin = text.count("\n") - c_win
    
    # set the appropriate style
    if c_win > c_mac and c_win > c_lin:
        mode = '\r\n'
    elif c_mac > c_win and c_mac > c_lin:            
        mode = '\r'
    else:
        mode = '\n'
    
    # return
    return mode


def createEditor(parent, filename=None):
    """ Tries to load the file given by the filename and
    if succesful, creates an editor instance to put it in, 
    which is returned.
    If filename is None, an new/unsaved/temp file is created. 
    """
    
    if filename is None:
        
        # create editor
        editor = IepEditor(parent)
        editor.makeDirty(True)
    
    else:
        
        # check and normalize
        if not os.path.isfile(filename):
            raise IOError("File does not exist '%s'." % filename)
        filename = normalizePath(filename)
        
        # load file (as bytes)
        with open(filename, 'rb') as f:
            bb = f.read()
            f.close()
        
        # convert to text
        text = bb.decode('UTF-8')
        
        # process line endings
        lineEndings = determineLineEnding(text)
        text = text.replace('\r\n','\n').replace('\r','\n')
        
        # if we got here safely ...
        
        # create editor and set text
        editor = IepEditor(parent)
        editor.setText(text)
        editor.makeDirty(False)
        
        # store name and line endings
        editor._filename = filename
        editor._name = os.path.split(filename)[1]
        editor._lineEndings = lineEndings
    
    # clear undo history
    editor.SendScintilla(editor.SCI_EMPTYUNDOBUFFER)
    
    # set style
    ext = os.path.splitext(editor._filename)[1]
    editor.setStyle(ext)
    
    # return
    return editor


class IepEditor(BaseTextCtrl):
    
    # called when dirty changed or filename changed, etc
    somethingChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, *args, **kwargs):
        BaseTextCtrl.__init__(self, parent, *args, **kwargs)
        
        # init some stuff
        self._filename = ''
        self._name = '<TMP>'
        self._lineEndings = '\n'
        
        # to see whether the doc has been changed
        self._dirty = False
        SIGNAL = QtCore.SIGNAL
        self.connect(self, SIGNAL('SCN_SAVEPOINTLEFT()'), self.makeDirty)
        self.connect(self, SIGNAL('SCN_SAVEPOINTREACHED()'), self.makeDirtyNot)
    
    
    def makeDirty(self, value=True): 
        """ Handler of the callback for SAVEPOINTLEFT,
        and used as a way to tell scintilla we just saved. """
        self._dirty = value
        if not value:
            self.SendScintilla(self.SCI_SETSAVEPOINT)
        self.somethingChanged.emit()
    
    def makeDirtyNot(self): 
        """ This is the handler for SAVEPOINTREACHED. If we would let
        it call makeDirty(False), that would send the SETSAVEPOINT signal,
        which results in a SAVEPOINTREACHED signal being emitted, etc ...
        """
        self._dirty = False
        self.somethingChanged.emit()
    
    
    def save(self, filename=None):
        """ Save the file. No checking is done. """
        
        # get filename
        if filename is None:
            filename = self._filename
        if not filename:
            raise ValueError("No filename specified, and no filename known.")
        
        # get text and convert line endings
        text = self.getText()
        text = text.replace('\n', self._lineEndings)
        
        # make bytes
        bb = text.encode('UTF-8')
        
        # store
        f = open(filename, 'wb')
        try:
            f.write(bb)
        finally:
            f.close()
        
        # update stats
        self._filename = normalizePath(filename)
        self._name = os.path.split(filename)[1]        
        self.makeDirty(False)
        
        # allow item to update its texts (no need: makeDirty call does this)
        #self.somethingChanged.emit()


if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepEditor(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    app.exec_()