#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Module editor
Defines the IepEditor class which is used to edit documents.
This module/class also implements all the relatively low level
file loading/saving /reloading stuff.
"""

import os, sys


from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui

from baseTextCtrl import BaseTextCtrl, normalizePath
import iep
from iepLogging import print


# Set default line ending (if not set)
if not iep.config.settings.defaultLineEndings:
    if 'win' in sys.platform:
        iep.config.settings.defaultLineEndings = 'CRLF'
    elif 'mac' in sys.platform:
        iep.config.settings.defaultLineEndings = 'CR'
    else:
        iep.config.settings.defaultLineEndings = 'LF'


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
    0 is returned if the indentation could not be determined.
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


def removeComment(text):    
    """Remove comments from a one-line comment,
    but if the text is just spaces, leave it alone.
    """
    
    # Bytes and bytearray objects, being "strings of bytes", have all 
    # methods found on strings, with the exception of encode(), format() 
    # and isidentifier(), which do not make sense with these types.
    
    # remove everything after first #    
    i = text.find(b'#')
    if i>0:
        text = text[:i] 
    text2 = text.rstrip() # remove lose spaces
    if len(text2)>0:        
        return text2  
    else:
        return text

# To give each new file a unique name
newFileCounter = 0

def createEditor(parent, filename=None):
    """ Tries to load the file given by the filename and
    if succesful, creates an editor instance to put it in, 
    which is returned.
    If filename is None, an new/unsaved/temp file is created. 
    """
    
    if filename is None:
        
        # Increase counter
        global newFileCounter
        newFileCounter  += 1
        
        # Create editor
        editor = IepEditor(parent)
        editor.makeDirty(True)
        
        # Set name
        editor._name = "<tmp {}>".format(newFileCounter)
    
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
        
        # if we got here safely ...
        
        # create editor and set text
        editor = IepEditor(parent)
        editor.setText(text)
        editor.setLineEndings(lineEndings)
        editor.makeDirty(False)
        
        # store name and filename
        editor._filename = filename
        editor._name = os.path.split(filename)[1]
        
        # process indentation
        indentWidth = determineIndentation(text)
        if indentWidth:
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
        editor.setStyle(iep.config.settings.defaultStyle)
    
    
    # return
    return editor


class IepEditor(BaseTextCtrl):
    
    # called when dirty changed or filename changed, etc
    somethingChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, *args, **kwargs):
        BaseTextCtrl.__init__(self, parent, *args, **kwargs)
        
        # View settings
        view = iep.config.view
        self.setViewWhiteSpace(view.showWhiteSpace)
        self.setViewWrapSymbols(view.showWrapSymbols)
        self.setViewEOL(view.showLineEndings)
        self.setIndentationGuides(view.showIndentGuides) 
        #
        self.setWrapMode( int(view.wrapText)*2 )
        self.setHighlightCurrentLine(view.highlightCurrentLine)
        self.setFolding( int(view.codeFolding)*5 )
        self.setEdgeColumn(view.edgeColumn)
        # bracematch is set in baseTextCtrl, since it also applies to shells
        # dito for zoom and tabWidth
        
        # Init filename ane name
        self._filename = ''
        self._name = '<TMP>'
        
        # Set line endings to default
        self.setLineEndings(iep.config.settings.defaultLineEndings)
        
        # Modification time to test file change 
        self._modifyTime = 0
        
        # Enable scrolling beyond last line
        self.SendScintilla(self.SCI_SETENDATLASTLINE, False)
        
        # To see whether the doc has been changed
        self._dirty = False
        SIGNAL = QtCore.SIGNAL
        self.connect(self, SIGNAL('SCN_SAVEPOINTLEFT()'), self.makeDirty)
        self.connect(self, SIGNAL('SCN_SAVEPOINTREACHED()'), self.makeDirtyNot)
        
        # To see whether the doc has changed, in a slightly different
        # way to update the parser. SCN_MODIFIED might make more sense, but
        # produces errors.
        self.SCN_UPDATEUI.connect(self._onModified)
    
    
    def id(self):
        """ Get an id of this editor. This is the filename, 
        or for tmp files, the name. """
        if self._filename:
            return self._filename
        else:
            return self._name
    
    
    def focusInEvent(self, event):
        """ Test whether the file has been changed 'behind our back'
        """
        # Act normally to the focus event        
        BaseTextCtrl.focusInEvent(self, event)
        # Test file change
        self.testWhetherFileWasChanged()
    
    
    def testWhetherFileWasChanged(self):
        """ testWhetherFileWasChanged()
        Test to see whether the file was changed outside our backs,
        and let the user decide what to do.
        Returns True if it was changed.
        """
        
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
            dlg.setWindowTitle('File was changed')
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
            
            # Return that indeed the file was changes
            return True
        
    
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
    
    
    def _onModified(self):
        iep.parser.parseThis(self)
    
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
        # Act normally
        if event:
            BaseTextCtrl.showEvent(self, event)
        
        # Set title to display filename of this file
        self.setTitleInMainWindow()
        
        # Make parser update
        iep.parser.parseThis(self)
    
    
    def setTitleInMainWindow(self):
        """ set the title  text in the main window to show filename. """
        
        # compose title
        name, path = self._name, self._filename
        if not path:
            path = 'no location on disk'
        tmp = { 'fileName':name, 'filename':name, 'name':name,
                'fullPath':path, 'fullpath':path, 'path':path}
        title = iep.config.advanced.titleText.format(**tmp)
        
        # set title
        iep.main.setWindowTitle(title)
    
    
    def setLineEndings(self, le=None):
        """  Set the line ending style used in this editor.
        le can be '\n', 'LF', '\r', 'CR', '\r\n', 'CRLF'.
        If le is None, all line endings in the document are converted
        to the current line ending style.
        """ 
        tmp = { 'LF':self.SC_EOL_LF, '\n':self.SC_EOL_LF, 
                'CR':self.SC_EOL_CR, '\r':self.SC_EOL_CR, 
                'CRLF':self.SC_EOL_CRLF, '\r\n':self.SC_EOL_CRLF} 
        
        # If le given, set new style
        if le:
            if le in tmp:
                eol = tmp[le]
                self.SendScintilla(self.SCI_SETEOLMODE, eol)
            else:
                raise ValueError('Unknown line ending style: ' + str(le))
        
        # Always convert
        if True:
            eol = self.SendScintilla(self.SCI_GETEOLMODE)
            self.SendScintilla(self.SCI_CONVERTEOLS, eol)
    
    
    def getLineEndings(self):
        """ Return the line ending style in use.
        Returns a tuple, the first element is one of LF, CR, CRLF,
        the second is/are the line ending character(s),
        """ 
        tmp = { self.SC_EOL_LF: ('LF', '\n'), 
                self.SC_EOL_CR: ('CR', '\r'), 
                self.SC_EOL_CRLF: ('CRLF', '\r\n')} 
        return tmp[self.SendScintilla(self.SCI_GETEOLMODE)]
    
    
    def save(self, filename=None):
        """ Save the file. No checking is done. """
        
        # get filename
        if filename is None:
            filename = self._filename
        if not filename:
            raise ValueError("No filename specified, and no filename known.")
        
        # Test whether it was changed without us knowing. If so, dont save now.
        if self.testWhetherFileWasChanged():
            return
        
        # Make sure all line endings are the same
        self.setLineEndings()
        
        # Get text and make bytes
        text = self.getString()
        bb = text.encode('UTF-8')
        
        # Store
        f = open(filename, 'wb')
        try:
            f.write(bb)
        finally:
            f.close()
        
        # Update stats
        self._filename = normalizePath( filename )
        self._name = os.path.split(self._filename)[1]        
        self.makeDirty(False)
        self._modifyTime = os.path.getmtime(self._filename)
        
        # update title (in case of a rename)
        self.setTitleInMainWindow()
        
        # allow item to update its texts (no need: makeDirty call does this)
        #self.somethingChanged.emit()


    def reload(self):
        """ Reload text using the self._filename. 
        We do not have a load method; we first try to load the file
        and only when we succeed create an editor to show it in...
        This method is only for reloading in case the file was changed
        outside of the editor. """
        
        # We can only load if the filename is known
        if not self._filename:
            return
        filename = self._filename
        
        # Remember where we are
        linenr, index = self.getLinenrAndIndex()
        
        # Load file (as bytes)
        with open(filename, 'rb') as f:
            bb = f.read()
        
        # Convert to text
        text = bb.decode('UTF-8')
        
        # Process line endings (before setting the text)
        self.setLineEndings( determineLineEnding(text) )
        
        # Set text
        self.setText(text)
        self.makeDirty(False)
        
        # Go where we were (approximately)
        pos = self.getPositionFromLinenr(linenr) + index
        self.setPositionAndAnchor(pos)
        self.ensureCursorVisible()
    
    
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

    
    def keyPressHandler_always(self, event):
        """ keyPressHandler_always(event)
        Called when the autocomp list is NOT active and when the event
        was not handled by the "always" handler. If returns True,
        will not process the event further.
        """
        
        # Use base first
        if BaseTextCtrl.keyPressHandler_always(self, event):
            return True
        
        if event.key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            # Auto indentation
            
            # Remove autocomp if shown
            self.autoCompCancel()
            
            # Get some data
            indentWidth = self.getIndentation()
            indent = ' '
            if indentWidth == 0:
                # This once could occur due to a bug which is now solved,
                # this code made it self-solving, and there's no harm in
                # keeping it.
                indentWidth = iep.config.settings.defaultIndentation
                self.setIndentation(indentWidth)
            if indentWidth<0:
                indentWidth = 1
                indent = '\t'
            
            if iep.config.settings.autoIndent:                
                # check if style is ok...
                pos = self.getPosition()
                curstyle = self.getStyleAt(self.getPosition())
                if curstyle in [0,10]: # default, operator
                    styleOk = True
                else:
                    styleOk = False
                # auto indent!
                linenr,index = self.getLinenrAndIndex()
                line = self.getLineBytes(linenr)
                if not line:
                    return False
                text = removeComment( line )
                ind = len(text) - len(text.lstrip())
                ind = int(round(ind/indentWidth))
                dummy, leChar = self.getLineEndings()
                if styleOk and len(text)>0 and text[-1] == 58: # or b':'[0]
                    text2insert = leChar+indent*((ind+1)*indentWidth)
                else:                
                    text2insert = leChar+indent*(ind*indentWidth)
                # Make bytes and insert
                text2insert = bytes(text2insert, 'utf-8')
                self.insertText(pos, text2insert)
                pos = self.getPosition()
                self.setPositionAndAnchor( pos + len(text2insert) )
                return True
    
    
    ## Introspection processing methods
    
    def processCallTip(self, cto):
        """ Processes a calltip request using a CallTipObject instance. 
        """
        # Try using buffer first
        if cto.tryUsingBuffer():
            return
        
        # Try obtaining calltip from the source
        sig = iep.parser.getFictiveSignature(cto.name, self, True)
        if sig:
            # Done
            cto.finish(sig)
        else:
            # Try the shell
            shell = iep.shells.getCurrentShell()
            if shell:
                shell.processCallTip(cto)
    
    
    def processAutoComp(self, aco):
        """ Processes an autocomp request using an AutoCompObject instance. 
        """
        
        # Try using buffer first
        if aco.tryUsingBuffer():
            return
        
        # Init name to poll by remote process (can be changed!)
        nameForShell = aco.name
        
        # Get normal fictive namespace
        fictiveNS = iep.parser.getFictiveNameSpace(self)
        fictiveNS = set(fictiveNS)
        
        # Add names
        if not aco.name:
            # "root" names
            aco.addNames(fictiveNS)
            # imports
            importNames, importLines = iep.parser.getFictiveImports(self)
            aco.addNames(importNames)
        else:
            # Prepare list of class names to check out
            classNames = [aco.name]
            handleSelf = True
            # Unroll supers
            while classNames:
                className = classNames.pop(0)
                if not className:
                    continue
                if handleSelf or (className in fictiveNS):
                    # Only the self list (only first iter)
                    fictiveClass = iep.parser.getFictiveClass(
                        className, self, handleSelf)
                    handleSelf = False
                    if fictiveClass:
                        aco.addNames( fictiveClass.members )
                        classNames.extend(fictiveClass.supers)
                else:
                    nameForShell = className
                    break
        
        # If there's a shell, let it finish the autocompletion
        shell = iep.shells.getCurrentShell()
        if shell:
            aco.name = nameForShell # might be the same or a base class
            shell.processAutoComp(aco)
        else:
            # Otherwise we finish it ourselves
            aco.finish()
        
    
if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepEditor(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    app.exec_()
    
