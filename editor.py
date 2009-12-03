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
import iep

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


def determineIndentation(text):
    """ Get the indentation used in this document.
    The text is analyzed to find the most used 
    indentations.
    The result is -1 if tab indents are most common.
    A positive result means spaces are used; the amount
    signifies the amount of spaces per indentation.
    """
    
    # create dictionary of indents, -1 means a tab
    indents = {}   
    indents[-1] = 0
    
    lines = text.splitlines()
    lines.insert(0,"") # so the lines start at 1
    for i in range( len(lines) ):
        line = lines[i]
        linelen = len(line)
        
        # remove indentation
        tmp = line.lstrip()
        indent = len(line) - len(tmp)
        line = tmp.rstrip()
        
        if line.startswith('#'):
            continue        
        else:
            # remove everything after the #
            line = line.split("#",1)[0].rstrip()        
        if not line:
            # continue of no line left
            continue
        
        # a colon means there will be an indent
        # check the next line (or the one thereafter)
        # and calculate the indentation difference with THIS line.
        if line.endswith(":"):
            if len(lines) > i+2:
                line2 = lines[i+1]
                tmp = line2.lstrip()
                if not tmp:
                    line2 = lines[i+2] 
                    tmp = line2.lstrip()
                if tmp:
                    ind2 = len(line2)-len(tmp)
                    ind3 = ind2 - indent
                    if line2.startswith("\t"):
                       indents[-1] += 1
                    elif ind3>0:
                        if not ind3 in indents:
                            indents[ind3] = 1
                        indents[ind3] += 1    
    
    # find which was the most common tab width.
    indent, maxvotes = 0,0
    for nspaces in indents:
        if indents[nspaces] > maxvotes:
            indent, maxvotes = nspaces, indents[nspaces]            
    #print "found tabwidth %i" % indent
    return indent


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
        
        # load file (as bytes)
        with open(filename, 'rb') as f:
            bb = f.read()
            f.close()
        
        # convert to text, be gentle with files not encoded with utf-8
        text = bb.decode('UTF-8','replace')
        
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
        
        # process indentation
        indentWidth = determineIndentation(text)
        editor.setIndentation(indentWidth)
    
    # clear undo history and modify time
    editor.SendScintilla(editor.SCI_EMPTYUNDOBUFFER)
    if editor._filename:
        editor._modifyTime = os.path.getmtime(editor._filename)
    
    # set style
    if editor._filename:
        ext = os.path.splitext(editor._filename)[1]
        editor.setStyle(ext)
    else:
        editor.setStyle(iep.config.editor.defaultStyle)
    
    
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
        tmp = {'LF':'\n', 'CR':'\r', 'CRLF':'\r\n'}
        self._lineEndings = tmp[iep.config.editor.defaultLineEndings]
        
        # modification time to test file change 
        self._modifyTime = 0
        
        # to be able to accept drops
        #self.setAcceptDrops(True)
        
        # to see whether the doc has been changed
        self._dirty = False
        SIGNAL = QtCore.SIGNAL
        self.connect(self, SIGNAL('SCN_SAVEPOINTLEFT()'), self.makeDirty)
        self.connect(self, SIGNAL('SCN_SAVEPOINTREACHED()'), self.makeDirtyNot)
    
    
    def focusInEvent(self, event):
        """ Test whether the file has been changed 'behind our back'
        """
        # act normally to the focus event
        BaseTextCtrl.focusInEvent(self, event)
        
        # get the path
        path = self._filename
        if not os.path.isfile(path):
            # file is deleted from the outside
            return
        
        # test the modification time...
        mtime = os.path.getmtime(path)
        if mtime != self._modifyTime:
            
            # ask user
            dlg = QtGui.QMessageBox(self)
            dlg.setText("File has been modified outside of the editor:\n"+
                        self._filename)
            dlg.setInformativeText("Do you want to reload?")
            t=dlg.addButton("Reload", QtGui.QMessageBox.AcceptRole) #0
            dlg.addButton("Keep this version", QtGui.QMessageBox.RejectRole) #1
            dlg.setDefaultButton(t)
            
            # whatever the result, we will reset the modified time
            self._modifyTime = os.path.getmtime(path)
            
            # get result and act
            result = dlg.exec_()            
            if result == QtGui.QMessageBox.AcceptRole:
                self.reload()
            else:
                pass # when cancelled or explicitly said, do nothing
    
    
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
    
    
    def dropEvent(self, event):
        """ Drop files in the list. """        
        if event.mimeData().hasUrls():
            # file: let the editorstack do the work.
            iep.editors.dropEvent(event)
        else:
            # text: act normal
            BaseTextCtrl.dropEvent(self, event)
    
    
    def showEvent(self, event=None):
        """ Capture show event to change title. """        
        # get root widget
        ob = self
        while ob.parent():
            ob = ob.parent()        
        # compose title
        name, path = self._name, self._filename
        if not path:
            path = 'no location on disk'
        tmp = { 'fileName':name, 'filename':name, 'name':name,
                'fullPath':path, 'fullpath':path, 'path':path}
        title = iep.config.titleText.format(**tmp)
        # set title
        ob.setWindowTitle(title)
    
    
    def save(self, filename=None):
        """ Save the file. No checking is done. """
        
        # get filename
        if filename is None:
            filename = self._filename
        if not filename:
            raise ValueError("No filename specified, and no filename known.")
        
        # get text and convert line endings
        text = self.getString()
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
        self._filename = normalizePath( filename )
        self._name = os.path.split(self._filename)[1]        
        self.makeDirty(False)
        self._modifyTime = os.path.getmtime(self._filename)
        
        # allow item to update its texts (no need: makeDirty call does this)
        #self.somethingChanged.emit()


    def reload(self):
        """ Reload text using the self._filename. 
        We do not have a load method; let's first try to load the file
        and only when we succeed create an editor to show it in...
        This method is only for reloading in case the file was changed
        outside of the editor. """
        
        # we can only load if the filename is known
        if not self._filename:
            return
        filename = self._filename
        
        # load file (as bytes)
        with open(filename, 'rb') as f:
            bb = f.read()
        
        # convert to text
        text = bb.decode('UTF-8')
        
        # process line endings
        self._lineEndings = determineLineEnding(text)
        text = text.replace('\r\n','\n').replace('\r','\n')
        
        # set text
        self.setText(text)
        self.makeDirty(False)
    
    
    def commentCode(self):
        # get locations of the selected text (but whole lines only)
        pos = self.getPosition()
        anch = self.getAnchor()
        line1 = self.getLinenrFromPosition(pos)
        line2 = self.getLinenrFromPosition(anch)
        line1,line2 = min(line1,line2), max(line1,line2)+1
        
        # comment all lines
        for linenr in range(line1,line2):            
            pos2 = self.getPositionFromLinenr(linenr)
            self.setTargetStart(pos2)
            self.setTargetEnd(pos2)
            self.replaceTargetBytes(b"# ")
    
    
    def uncommentCode(self):
        
        # get locations of the selected text (but whole lines only)
        pos = self.getPosition()
        anch = self.getAnchor()
        line1 = self.getLinenrFromPosition(pos)
        line2 = self.getLinenrFromPosition(anch)
        line1,line2 = min(line1,line2), max(line1,line2)+1
        
        # comment all lines
        for linenr in range(line1,line2):            
            pos2 = self.getPositionFromLinenr(linenr)              
            linetext = self.getLineBytes(linenr)
            i = linetext.find(b"#")
            c = linetext[:i].count(b" ") # only spaces before comment
            if i>=0 and i==c:
                self.setTargetStart(pos2+i)
                if i < len(linetext)-1 and linetext[i+1]==b" "[0]:
                    self.setTargetEnd(pos2+i+2) # remove "# "
                else:
                    self.setTargetEnd(pos2+i+1) # remove "#"
                self.replaceTargetBytes(b"")


    
    
    
if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepEditor(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    app.exec_()