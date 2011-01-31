# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module editor

Defines the IepEditor class which is used to edit documents.
This module/class also implements all the relatively low level
file loading/saving /reloading stuff.

"""

import os, sys
import re, codecs

from PyQt4 import QtCore, QtGui
qt = QtGui

from baseTextCtrl import BaseTextCtrl, normalizePath
import iep
from iepLogging import print


# Set default line ending (if not set)
if not iep.config.settings.defaultLineEndings:
    if sys.platform.startswith('win'):
        iep.config.settings.defaultLineEndings = 'CRLF'
    else:
        iep.config.settings.defaultLineEndings = 'LF'


def determineEncoding(bb):
    """ Get the encoding used to encode a file.
    Accepts the bytes of the file. Returns the codec name. If the
    codec could not be determined, uses UTF-8.
    """
    
    # Get first two lines
    parts = bb.split(b'\n', 2)
    
    # Init to default encoding
    encoding = 'UTF-8'
    
    # Determine encoding from first two lines
    for i in range(len(parts)-1):
        
        # Get line
        try:
            line = parts[i].decode('ASCII')
        except Exception:
            continue 
        
        # Search for encoding directive
        
        # Has comment?
        if line and line[0] == '#':
            
            # Matches regular expression given in PEP 0263?
            expression = "coding[:=]\s*([-\w.]+)"
            result = re.search(expression, line)
            if result:
                
                # Is it a known encoding? Correct name if it is
                candidate_encoding = result.group(1)
                try:
                    c = codecs.lookup(candidate_encoding)
                    candidate_encoding = c.name
                except Exception:
                    pass
                else:
                    encoding = candidate_encoding
    
    # Done
    return encoding


def determineLineEnding(text):
    """ Get the line ending style used in the text.
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
        editor.document().setModified(True)
        
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
        encoding = determineEncoding(bb)
        text = bb.decode(encoding,'replace')
        
        # process line endings
        lineEndings = determineLineEnding(text)
        
        # if we got here safely ...
        
        # create editor and set text
        editor = IepEditor(parent)
        editor.setPlainText(text)
        editor.lineEndings = lineEndings
        editor.encoding = encoding
        editor.document().setModified(False)
        
        # store name and filename
        editor._filename = filename
        editor._name = os.path.split(filename)[1]
        
        # process indentation
        indentWidth = determineIndentation(text)
        if indentWidth == -1: #Tabs
            editor.tabSize = 4 #TODO: configurable
            editor.indentation = 0
        elif indentWidth:
            editor.tabSize = indentWidth
            editor.indentation = indentWidth
    
    # clear undo history and modify time
    #TODO: editor.SendScintilla(editor.SCI_EMPTYUNDOBUFFER)
    if editor._filename:
        editor._modifyTime = os.path.getmtime(editor._filename)
    
    # set style
    #TODO:
    #if editor._filename:
    #    ext = os.path.splitext(editor._filename)[1]
    #    editor.setStyle(ext)
    #else:
    #    editor.setStyle(iep.config.settings.defaultStyle)
    
    
    # return
    return editor

class IepEditor(BaseTextCtrl):
    
    # called when dirty changed or filename changed, etc
    somethingChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent, *args, **kwargs):
        BaseTextCtrl.__init__(self, parent, *args, **kwargs)
        self.showLineNumbers = True

        
        # View settings
        self.showWhitespace = iep.config.view.showWhiteSpace
        #TODO: self.setViewWrapSymbols(view.showWrapSymbols)
        self.showLineEndings = iep.config.view.showLineEndings
        self.showIndentationGuides  = iep.config.view.showIndentGuides
        #
        self.wrap = iep.config.view.wrapText
        self.highlightCurrentLine = iep.config.view.highlightCurrentLine
        self.longLineIndicator = iep.config.view.edgeColumn
        #TODO: self.setFolding( int(view.codeFolding)*5 )        
        # bracematch is set in baseTextCtrl, since it also applies to shells
        # dito for zoom and tabWidth
        
        # Init filename and name
        self._filename = ''
        self._name = '<TMP>'
        
        # Set line endings to default
        self.lineEndings = iep.config.settings.defaultLineEndings
        
        # Set encoding to default
        self.encoding = 'UTF-8'
        
        # Modification time to test file change 
        self._modifyTime = 0
        
        self.modificationChanged.connect(self._onModificationChanged)
        
        # To see whether the doc has changed to update the parser.
        self.textChanged.connect(self._onModified)
    
    
    ## Properties
    
    @property
    def name(self):
        return self._name
    
    @property
    def filename(self):
        return self._filename
        
    @property
    def lineEndings(self):
        """
        Line-endings style of this file. Setter accepts machine-readable (e.g. '\r') and human-readable (e.g. 'CR') input
        """
        return self._lineEndings
        
    @lineEndings.setter
    def lineEndings(self,value):
        if value in ('\r','\n','\r\n'):
            self._lineEndings = value
            return
        try:
            self._lineEndings = {'CR': '\r', 'LF': '\n', 'CRLF': '\r\n'}[value]
        except KeyError:
            raise ValueError('Invalid line endings style %r' % value)
    
    @property 
    def lineEndingsHumanReadable(self):
        """
        Current line-endings style, human readable (e.g. 'CR')
        """
        return {'\r': 'CR', '\n': 'LF', '\r\n': 'CRLF'}[self.lineEndings]
    
    
    @property
    def encoding(self):
        """ Encoding used to convert the text of this file to bytes.
        """
        return self._encoding
    
    
    @encoding.setter
    def encoding(self, value):
        # Test given value, correct name if it exists
        try:
            c = codecs.lookup(value)
            value = c.name
        except Exception:
            value = codecs.lookup('UTF-8').name
        # Store
        self._encoding = value
    
    
    ##
    def gotoLine(self,lineNumber):
        """Move the cursor to the given lineNumber (0-based) and center
        the cursor vertically"""
        cursor=self.textCursor()
        cursor.movePosition(cursor.Start) #move to begin of the document
        cursor.movePosition(cursor.NextBlock,n=lineNumber) #n lines down
        self.setTextCursor(cursor)
        
        self.centerCursor()
    
    
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
        
    def _onModificationChanged(self,changed):
        """Handler for the modificationChanged signal. Emit somethingChanged
        for the editorStack to update the modification notice."""
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
                'fullPath':path, 'fullpath':path, 'path':path }
        title = iep.config.advanced.titleText.format(**tmp)
        
        # set title
        iep.main.setWindowTitle(title)
    
    
    
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
        
        # Get text, convert line endings
        text = self.toPlainText()
        text = text.replace('\n', self.lineEndings)
        
        # Make bytes
        bb = text.encode(self.encoding)
        
        # Store
        f = open(filename, 'wb')
        try:
            f.write(bb)
        finally:
            f.close()
        
        # Update stats
        self._filename = normalizePath( filename )
        self._name = os.path.split(self._filename)[1]
        self.document().setModified(False)
        self._modifyTime = os.path.getmtime(self._filename)
        
        # update title (in case of a rename)
        self.setTitleInMainWindow()
        
        # allow item to update its texts (no need: onModifiedChanged does this)
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
        self.lineEndings= determineLineEnding(text)
        
        # Set text
        self.setPlainText(text)
        self.document().setModified(False)
        
        # Go where we were (approximately)
        #TODO:
        #pos = self.getPositionFromLinenr(linenr) + index
        #self.setPositionAndAnchor(pos)
        #self.ensureCursorVisible()
    
    
    def commentCode(self):
        """
        Comment the lines that are currently selected
        """
        self.doForSelectedBlocks(
            lambda cursor: cursor.insertText('# ') )
     
    
    def uncommentCode(self):
        """
        Uncomment the lines that are currently selected
        """
        #TODO: this should not be applied to lines that are part of a multi-line string
        
        #Define the uncomment function to be applied to all blocks
        def uncommentBlock(cursor):
            """
            Find the first # on the line; if there is just whitespace before it,
            remove the # and if it is followed by a space remove the space, too
            """
            text = cursor.block().text()
            commentStart = text.find('#')
            if commentStart == -1:
                return #No comment on this line
            if text[:commentStart].strip() != '':
                return #Text before the #
            #Move the cursor to the beginning of the comment
            cursor.setPosition(cursor.block().position() + commentStart)
            cursor.deleteChar()
            if text[commentStart:].startswith('# '):
                cursor.deleteChar()
                
        #Apply this function to all blocks
        self.doForSelectedBlocks(uncommentBlock)


    
    
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
    win.setPlainText(tmp)    
    win.show()
    app.exec_()
    
