# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module baseTextCtrl

Defines the base text control to be inherited by the shell and editor
classes. Implements styling, introspection and a bit of other stuff that
is common for both shells and editors.

"""

import iep
import os, sys, time
import weakref
import ssdf
from iepLogging import print

from PyQt4 import QtCore, QtGui
qt = QtGui


# Define style stuff
subStyleStuff = {}

#subStyleStuff = {   'face': Qsci.QsciScintillaBase.SCI_STYLESETFONT ,
#                    'fore': Qsci.QsciScintillaBase.SCI_STYLESETFORE,
#                    'back': Qsci.QsciScintillaBase.SCI_STYLESETBACK,
#                    'size': Qsci.QsciScintillaBase.SCI_STYLESETSIZE,
#                    'bold': Qsci.QsciScintillaBase.SCI_STYLESETBOLD,
#                    'italic': Qsci.QsciScintillaBase.SCI_STYLESETITALIC,
#                    'underline': Qsci.QsciScintillaBase.SCI_STYLESETUNDERLINE}


def normalizePath(path):
    """ Normalize the path given. 
    All slashes will be made the same (and doubles removed)
    The real case as stored on the file system is recovered.
    Returns None on error.
    """
    
    # normalize
    path = os.path.abspath(path)  # make sure it is defined from the drive up
    path = os.path.normpath(path)
    sep = os.sep
    
    # If does not exist, return as is.
    # This also happens if the path's case is incorrect and the
    # file system is case sensitive. That's ok, because the stuff we 
    # do below is intended to get the path right on case insensitive
    # file systems.
    if not os.path.isfile(path):
        return path
    
    # split drive name from the rest
    drive, rest = os.path.splitdrive(path)
    fullpath = drive.upper() + sep
    
    # make lowercase and split in parts    
    parts = rest.lower().split(os.sep)
    parts = [part for part in parts if part]
    
    for part in parts:
        # print( fullpath,part)
        options = [x for x in os.listdir(fullpath) if x.lower()==part]
        if len(options) > 1:
            print("Error normalizing path: Ambiguous path names!")
            return path
        elif len(options) < 1:
            print("Invalid path: "+fullpath+part)
            return path
        fullpath += options[0] + sep
    
    # remove last sep
    return fullpath[:-len(sep)]


# valid chars to make a name
namechars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789"
namekeys = [ord(i) for i in namechars]


# todo: a regexp on the reverse string? Only for beauty, 
# this is no performance bottleneck or anything
def parseLine_autocomplete(text):
    """ Given a line of code (from start to cursor position) 
    returns a tuple (base, name).    
    autocomp_parse("eat = banan") -> "", "banan"
      ...("eat = food.fruit.ban") -> "food.fruit", "ban"
    When no match found, both elements are an empty string.
    """
    #TODO: use the syntax tokens to do this processing
    
    # is the line commented? The STC_P is 0 in commented lines...
    i = text.rfind("#")
    if i>=0 and text[:i].count("\"") % 2==0 and text[:i].count("\'") % 2==0:
        return "",""
    
    # Helper variable
    in_list = 0
    
    i_base = 0
    for i in range(len(text)-1,-1,-1):
        c = text[i]
        
        if c=='.':
            if i_base==0:
                i_base = i        
        elif c in ["'", '"']:
            # a string                
            if i_base == i+1: # dot after it
                return "''", text[i_base+1:]
            else:
                return "",""
        elif c==']':
            # may be a list
            if i_base == i+1 and i>0 and text[i-1]=='[': 
                return "[]", text[i_base+1:]
            else:
                in_list += 1
        elif c == '[':
            # Allow looking in lists, if using simple indexing
            if in_list > 0:
                in_list  -= 1
            else:
                break
        elif not c in namechars:
            break
    else:
        # we need to decrease this extra bit when the loop fully unrolled
        i-=1 
        
    # almost done...
    if i_base == 0:
        return "", text[i+1:]
    else:
        return text[i+1:i_base], text[i_base+1:]



def parseLine_signature(text):
    """ Given a line of code (from start to cursor position) 
    returns a tuple (name, needle, stats).
    stats is another tuple: 
    - location of end bracket
    - amount of kommas till cursor (taking nested brackets into account)
    """
    #TODO: use the syntax tokens to do this processing
    # find braces
    level = 1  # for braces    
    for i in range(len(text)-1,-1,-1):
        c = text[i]
        if c == ")": level += 1
        elif c == "(": level -= 1        
        if level == 0:
            break
            
    if not i>0:
        return "","",(0,0)
    
    # now find the amount of valid komma's to calculate which element at cursor
    kommaCount = 0
    l1 = 1  # for braces
    l2=l3=l4=l5 = 0 # square brackets, curly brackets, qoutes, double quotes    
    for ii in range(i+1,len(text)):
        c = text[ii:ii+1]
        if c == "'": l4 = (not l4)
        elif c == '"': l5 = (not l5) 
        if l4 or l5:
            continue
        if c == ",":
            if l1 == 1 and l2==0 and l3==0:
                kommaCount += 1        
        elif c == "(": l1 += 1
        elif c == ")": l1 -= 1        
        elif c in "[": l2 += 1
        elif c in "]": l2 -= 1
        elif c in "{": l3 += 1
        elif c in "}": l3 -= 1               
    
    # found it?
    if i>0:
        name, needle = parseLine_autocomplete(text[:i])
        return name, needle, (i, kommaCount)
    else:
        return "","", (0,0)


class StyleManager(QtCore.QObject):
    """ Singleton class for managing the styles of the text control. """
    
    styleUpdate = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        
        # Init filename and test if it exists
        self._filename = os.path.join(iep.appDataDir, 'styles.ssdf')
        if not os.path.isfile(self._filename):
            raise RuntimeError("The stylefile does not exist: "+self._filename)
        self._filename = normalizePath(self._filename)
        
        # Init default fonts dicts
        self._faces = {}
        
        # Init style structure and load it 
        self._styles = None
        self.loadStyles()
    
    
    def loadStyles(self, filename=None):
        """ Load the stylefile. """
        
        # get filename
        if not filename:
            filename = self._filename
        else:
            self._filename = normalizePath(filename)
        
        # check file
        if not os.path.isfile(filename):
            filename = os.path.join( os.path.dirname(__file__), filename )
        if not os.path.isfile(filename):
            print("warning: style file not found.")
            return
        # load file
        import ssdf
        self._styles = ssdf.load(filename)
        # Try building style tree and emit signal on success
        if self.buildStyleTree():
            self.styleUpdate.emit() 
    
    
    def getStyleNames(self):
        """ Get a list of style names. """
        return [name for name in self._styles]
    
    
    def selectDefaultFonts(self, editor):
        """ Selects the default font by trying their existance.
        This method has to be executed only once. It is called
        automatically from applyStyle if _faces is not set.
        """
        
        # Preferences for monospace fonts
        if sys.platform=='darwin':
            monoFaces = ['Monaco','Courier New']
        elif sys.platform.startswith('win'):
            monoFaces = ['Courier New', 'Lucida Console']
        else:
            monoFaces = ['Courier New', 'Liberation Mono', 'Monospace', 'Fixed']
        # Most important, select monospace font
        for fontName in monoFaces:    
            # Set font (scintilla will usyally use a default non-monospace
            # font if the given font name is not available)
            editor.SendScintilla(editor.SCI_STYLESETFONT, 32, fontName)
            # Get widths of a short and a long character
            w1 = editor.textWidth(32, "i"*10)
            w2 = editor.textWidth(32, "w"*10)
            # Compare, stop if ok
            if w1 == w2:
                self._faces['mono'] = fontName
                #print('found mono:',fontName)
                break
        else:
            print('Oops, could not detect a suitable monospace font!')
            self._faces['mono'] = 'Courier New' # just set this
        
        # Sans font, is also selected if scintilla does not know the given font
        self._faces['sans'] = 'Helvetica'
        
        # Serif font, I'm not sure whether this works on all OS's
        self._faces['serif'] = 'Times'
        
        # Try building style tree now
        self.buildStyleTree()
    
    
    def buildStyleTree(self):
        """ Using the load ssdf file, build a tree such that
        the styles can be applied to the editors easily. 
        Requires _faces to be set. 
        Returns True on success.
        """
        
        # a stylefile is an ssdf file which contains styling information
        # for several style types.
        # Each style is identified with a stylename and consists of a 
        # lexer, keywords, extension, several substyle strings (one for 
        # each substylenr) and can be based on any other style. 
        # All styles are automtically based on the style named default.
        
        if self._styles is None or not self._faces:
            return
        
        # do for each defined style
        for styleName in self._styles:
            
            # get style attributes
            style = self._styles[styleName]
            
            # make sure basedon and extensions are defined
            # keywords and lexer are only defined if they are in the file...     
            if not 'basedon' in style:
                style.basedon = ''
            if not 'ext' in style:
                style.ext = ''
            # dont do lexer or keywords, because they can be overridden to be
            # empty!
            
            # check out the substyle strings (which are of the form 'sxxx')
            for styleNr in style:
                if not (styleNr.startswith('s') and len(styleNr) == 4):
                    continue
                
                # get substyle number to tell scintilla
                nr = int(styleNr[1:])
                
                # Get string that contains several substyle attributes.
                # We will extract these attributes and organise them nicely
                # in a dict. 
                subStyleString = style[styleNr].lower()
                subStyleString = subStyleString.split(' # ')[0] # remove comments
                subStyleString = subStyleString.replace(',', ';')
                
                # split in parts (strip each part of leading+trailing spaces)
                subStyleStrings = subStyleString.split(';')                
                subStyleStrings = [s.strip() for s in subStyleStrings]
                
                # store results in here
                subStyle = style[styleNr] = ssdf.new()
                
                # analyze
                for s in subStyleStrings:
                    if s.startswith('bold'):
                        subStyle['bold'] = 1
                    if s.startswith('italic'):
                        subStyle['italic'] = 1
                    if s.startswith('underline'):
                        subStyle['underline'] = 1
                    if s.startswith('fore:'):
                        tmp = s[len('fore:'):]
                        subStyle['fore'] = qt.QColor(tmp)
                    if s.startswith('back:'):
                        tmp = s[len('back:'):]
                        subStyle['back'] = qt.QColor(tmp)
                    if s.startswith('face:'):
                        tmp = s[len('face:'):]
                        subStyle['face'] = tmp.format(**self._faces)
                    if s.startswith('size:'):
                        tmp = s[len('size:'):]
                        subStyle['size'] = int(tmp)
                #print(subStyle)
        
        # Done
        return True
    
    
    def applyStyleNumber(self, editor, nr, subStyle):
        """ Apply a certain a numbered style to the given editor. """
        
        # special case first
        if nr > 255:
            
            def tryApplyColor(command, extraArg=None, key=None):
                if key in subStyle:
                    c = qt.QColor(subStyle[key])
                    if extraArg is not None:
                        editor.SendScintilla(command, extraArg, c)
                    else:
                        editor.SendScintilla(command, c)
            
            if nr == 301:  # highlighting current line
                tryApplyColor(editor.SCI_SETCARETFORE, None, 'fore')
                tryApplyColor(editor.SCI_SETCARETLINEBACK, None, 'back')
            elif nr == 302:  # selection colors...
                tryApplyColor(editor.SCI_SETSELFORE, 1, 'fore')
                tryApplyColor(editor.SCI_SETSELBACK, 1, 'back')
            elif nr == 303:  # calltip colors
                tryApplyColor(editor.SCI_CALLTIPSETFORE, None, 'fore')
                tryApplyColor(editor.SCI_CALLTIPSETBACK, None, 'back')
                tryApplyColor(editor.SCI_CALLTIPSETFOREHLT, None, 'forehlt')
        
        else:
        
            for key in subStyleStuff:
                scintillaCommand = subStyleStuff[key]
                if key in subStyle:
                    value = subStyle[key]
                    editor.SendScintilla(scintillaCommand, nr, value)
    
    def collectStyle(self, styleStruct, styleName):
        """ Collect the styleStruct, taking style inheritance
        into account. 
        """
        
        # get the style (but check if exists first)
        if not styleName in self._styles:
            print("Unknown style %s" % styleName)
            return
        style = self._styles[styleName]
        
        # First collect style on which it is based. 
        # A style is always based on default. 
        if style.basedon:
            self.collectStyle(styleStruct, style.basedon)
        elif styleName!='default':
            self.collectStyle(styleStruct, 'default')
        
        # collect all fields
        for field in style:
            styleStruct[field] = style[field]
    
    
    def applyStyle(self, editor, styleName):
        """ Apply the specified style to the specified editor. 
        The stylename can be the name of the style, or the extension
        of the file to be styled (indicated by starting with a dot '.')
        The actual stylename is returned.
        """
        
        # Are the default fonts set?
        if not self._faces:
            self.selectDefaultFonts(editor)
		
        # make lower case
        styleName = styleName.lower()
        if not styleName:
            styleName = 'default'
        
        # if styletree was not yet build, return
        if self._styles is None:
            return
        
        # if extension was given, find out which style it belongs to
        if styleName.startswith('.'):
            ext = styleName[1:]
            
            # Collect styles that correspond to this extension
            validStyles = []
            for styleName in self._styles:
                exts = self._styles[styleName].ext.split(' ')                
                if ext in exts:
                    validStyles.append(styleName)
            
            # Select style
            defaultStyle = iep.config.settings.defaultStyle
            if defaultStyle in validStyles:
                styleName = defaultStyle
            elif validStyles:
                styleName = validStyles[0]
            else:
                # Unknown extension. Apply 'default' style, not defaultStyle:
                # this file is probably best viewed as plaint text.
                styleName = 'default'
        
        # get style struct
        styleStruct = ssdf.new()
        self.collectStyle(styleStruct, styleName)
        
        # clear all formatting
        editor.SendScintilla(subStyleStuff['bold'], 32, 0)
        editor.SendScintilla(subStyleStuff['italic'], 32, 0)
        editor.SendScintilla(subStyleStuff['underline'], 32, 0)
        editor.SendScintilla(editor.SCI_CLEARDOCUMENTSTYLE)
        
        if True: # apply always
            
            # short for sendscintilla
            send = editor.SendScintilla
            
            # First set default style to everything. The StyleClearAll command
            # makes that all styles are initialized as style 032. So it would
            # be more beautiful to look up that style and only apply that. But
            # it should always be defined in 'default', so this will work ...
            if 's032' in styleStruct:
                self.applyStyleNumber(editor, 32, styleStruct['s032'])
            send(editor.SCI_STYLECLEARALL)
            
            # set basic stuff first
            if 'lexer' in styleStruct:
                send(editor.SCI_SETLEXERLANGUAGE, styleStruct.lexer)
            if 'keywords' in styleStruct:
                send(editor.SCI_SETKEYWORDS, styleStruct.keywords)
            
            # check out the substyle strings (which are of the form 'sxxx')
            for styleNr in styleStruct:
                if not (styleNr.startswith('s') and len(styleNr) == 4):
                    continue
                # get substyle number to tell scintilla
                nr = int(styleNr[1:])
                # set substyle attributes
                self.applyStyleNumber(editor, nr, styleStruct[styleNr])
        
        # force scintilla to update the whole document
        editor.SendScintilla(editor.SCI_STARTSTYLING, 0, 32)
        
        # return actual stylename        
        return styleName

    
styleManager = StyleManager()
iep.styleManager = styleManager


class KeyEvent:
    """ A simple class for easier key events. """
    def __init__(self, key):
        self.key = key
        try:
            self.char = chr(key)        
        except ValueError:
            self.char = ""

    

def makeBytes(text):
    """ Make sure the argument is bytes, converting with UTF-8 encoding
    if it is a string. """
    if isinstance(text, bytes):
        return text
    elif isinstance(text, str):
        return text.encode('utf-8')
    else:
        raise ValueError("Expected str or bytes!")


_allScintillas = []
def getAllScintillas():
    """ Get a list of all the scintialla editing components that 
    derive from BaseTextCtrl. Used mainly by the menu.
    """
    for i in reversed(range(len(_allScintillas))):
        e = _allScintillas[i]()
        if e is None:
            _allScintillas.pop(i)
        else:
            yield e
iep.getAllScintillas = getAllScintillas

import codeeditor


class BaseTextCtrl(codeeditor.CodeEditor):
    """ The base text control class.
    Inherited by the shell class and the IEP editor.
    The class implements autocompletion, calltips, and auto-help
    
    Inherits from QsciScintilla. I tried to clean up the rather dirty api
    by using more sensible names. Hereby I apply the following rules:
    - if you set something, the method starts with "set"
    - if you get something, the method starts with "get"
    - a position is the integer position fron the start of the document
    - a linenr is the number of a line, an index the position on that line
    - all the above indices apply to the bytes (encoded utf-8) in which the
      text is stored. If you have unicode text, they do not apply!
    - the method name mentions explicityly what you get. getBytes() returns the
      bytes of the document, getString() gets the unicode string that it 
      represents. This applies to the get-methods. the set-methods use the
      term text, and automatically convert to bytes using UTF-8 encoding
      when a string is given. 
    """
        
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        # Create timer for autocompletion delay
        self._delayTimer = QtCore.QTimer(self)
        self._delayTimer.setSingleShot(True)
        self._delayTimer.timeout.connect(self._introspectNow)
        
        # For buffering autocompletion and calltip info
        self._callTipBuffer_name = ''
        self._callTipBuffer_time = 0
        self._callTipBuffer_result = ''
        self._autoCompBuffer_name = ''
        self._autoCompBuffer_time = 0
        self._autoCompBuffer_result = []
        
        # The string with names given to SCI_AUTOCSHOW
        self._autoCompNameString = ''

        self.completer().highlighted.connect(self.updateHelp)
        self.setIndentUsingSpaces(iep.config.settings.defaultIndentUsingSpaces)
        self.setIndentWidth(iep.config.settings.defaultIndentWidth)
        
    
    def callTipShow(self, pos, text, hl1=0, hl2=0):
        """ callTipShow(pos, text, hl1, hl2)
        Show text in a call tip at position pos. the text between hl1 and hl2
        is highlighted. If hl2 is -1, highlights all untill the first '('.
        """
        return

    
    def callTipCancel(self):
        """ Hide call tip. """
        return

    
    def callTipActive(self):
        """ Hide call tip. """
        return

    
    
    def _isValidPython(self):
        """ _isValidPython()
        Check if the code at the cursor is valid python:
        - the active lexer is the python lexer
        - the style at the cursor is "default"
        """
        #TODO:
        return True
        # The lexer should be Python
        lexlang = self.SendScintilla(self.SCI_GETLEXER)
        if lexlang != self.SCLEX_PYTHON:
            return False
        
        # The style must be "default"
        curstyle = self.getStyleAt(self.getPosition())
        if curstyle not in [0,10,11]:
            return False
        
        # When at the end of a comment, _isValidPython will fail, but 
        # parseLine_autocomplete will still detect this
        
        # all good
        return True  
    
    
    def introspect(self, tryAutoComp=False):
        """ introspect(tryAutoComp=False)
        
        The starting point for introspection (autocompletion and calltip). 
        It will always try to produce a calltip. If tryAutoComp is True,
        will also try to produce an autocompletion list (which, on success,
        will hide the calltip).
        
        This method will obtain the line and (re)start a timer that will
        call _introspectNow() after a short while. This way, if the
        user types a lot of characters, there is not a stream of useless
        introspection attempts; the introspection is only really started
        after he stops typing for, say 0.1 or 0.5 seconds (depending on
        iep.config.autoCompDelay).
        
        The method _introspectNow() will parse the line to obtain
        information required to obtain the autocompletion and signature
        information. Then it calls processCallTip and processAutoComp
        which are implemented in the editor and shell classes.
        """
        
        # Only proceed if valid python
        if not self._isValidPython():
            self.callTipCancel()
            self.autoCompCancel()
            return
        
        # Get line up to cursor
        cursor = self.textCursor()
        position = cursor.position()
        cursor.setPosition(cursor.position()) #Move the anchor to the cursor pos
        cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)
        text = cursor.selectedText().replace('\u2029', '\n') 
        
        # Is the char valid for auto completion?
        if tryAutoComp:
            if not text or not ( text[-1] in namechars or text[-1]=='.' ):
                self.autocompleteCancel()
                tryAutoComp = False
        
        # Store line and (re)start timer
        self._delayTimer._line = text
        self._delayTimer._pos = position
        self._delayTimer._tryAutoComp = tryAutoComp
        self._delayTimer.start(iep.config.advanced.autoCompDelay)
    
    
    def _introspectNow(self):
        """ This methos is called a short while after introspect() 
        by the timer. It parses the line and calls the specific methods
        to process the callTip and autoComp.
        """ 
        
        # Retrieve the line of text that we stored
        line = self._delayTimer._line
        if not line:
            return
        
        if iep.config.settings.autoCallTip:
            # Parse the line, to get the name of the function we should calltip
            # if the name is empty/None, we should not show a signature
            name, needle, stats = parseLine_signature(line)
            
            if needle:
                # Compose actual name
                fullName = needle
                if name:
                    fullName = name + '.' + needle
                # Calculate position
                pos = self._delayTimer._pos - len(line) + stats[0] - len(needle)
                # Process
                cto = CallTipObject(self, fullName, pos)
                self.processCallTip(cto)
            else: 
                self.callTipCancel()
        
        if self._delayTimer._tryAutoComp and iep.config.settings.autoComplete:
            # Parse the line, to see what (partial) name we need to complete
            name, needle = parseLine_autocomplete(line)
            
            if name or needle:
                # Try to do auto completion
                aco = AutoCompObject(self, name, needle)
                self.processAutoComp(aco)
    
    
    def processCallTip(self, cto):
        """ Dummy processing. """
        pass
    
    
    def processAutoComp(self, aco):
        """ Dummy processing. """
        pass
    
    
    def _onDoubleClick(self):
        """ When double clicking on a name, autocomplete it. """
        self.processHelp()
    
    
    def processHelp(self, name=None, showError=False):
        """ Show help on the given full object name.
        - called when going up/down in the autocompletion list.
        - called when double clicking a name     
        """
        # uses parse_autocomplete() to find baseName and objectName
        
        # Get help tool
        hw = iep.toolManager.getTool('iepinteractivehelp')
        # Get the shell
        shell = iep.shells.getCurrentShell()        
        # Both should exist
        if not hw or not shell:
            return
        
        if not name:
            # Obtain name from current cursor position
            
            # Is this valid python?
            if self._isValidPython():
                # Obtain line from text
                cursor = self.textCursor()
                line = cursor.block().text()
                text = line[:cursor.positionInBlock()]
                # Obtain             
                nameBefore, name = parseLine_autocomplete(text)
                if nameBefore:
                    name = "%s.%s" % (nameBefore, name)
        
        if name:
            hw.setObjectName(name)
        
    
    ## Callbacks
    def updateHelp(self,name):
        """A name has been highlighted, show help on that name"""
        
        if self._autoCompBuffer_name:
            name = self._autoCompBuffer_name + '.' + name
            
        # Apply
        self.processHelp(name,True)
   
   
    def event(self,event):
        """ event(event)
        
        Overload main event handler so we can pass Ctrl-C Ctr-v etc, to the main
        window.
        
        """
        if isinstance(event, QtGui.QKeyEvent):
            # Ignore CTRL+{A-Z} since those keys are handled through the menu
            if (event.modifiers() & QtCore.Qt.ControlModifier) and \
                (event.key()>=QtCore.Qt.Key_A) and (event.key()<=QtCore.Qt.Key_Z):
                    event.ignore()
                    return False
        
        # Default behavior
        codeeditor.CodeEditor.event(self, event)
        return True
    
    
    def keyPressEvent(self, event):
        """ Receive qt key event. 
        From here we'l dispatch the event to perform autocompletion
        or other stuff...
        """
        
        # Get ordinal key
        ordKey = -1
        if event.text():
            ordKey = ord(event.text()[0])
        
        # Cancel any introspection in progress
        self._delayTimer._line = ''
        
        # Also invalidate introspection for when a response gets back
        # These are set again when the timer runs out. If the response
        # is received before the timer runs out, the results are buffered
        # but not shown. When the timer runs out shortly after, the buffered
        # results are shown. If the timer runs out before the response is
        # received, a new request is done, although the response of the old
        # request will show the info if it's still up to date. 
        self._autoComp_bufBase = None
        self._callTip_bufName = None
        

        codeeditor.CodeEditor.keyPressEvent(self, event)
        # Analyse character/key to determine what introspection to fire
        if ordKey:
            if ordKey >= 48 or ordKey in [8, 46]:
                # If a char that allows completion or backspace or dot was pressed
                self.introspect(True)
            elif ordKey >= 32: 
                # Printable chars, only calltip
                self.introspect()
        elif event.key() in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
            self.introspect()
    
    
    





class CallTipObject:
    """ Object to help the process of call tips. 
    An instance of this class is created for each call tip action.
    """
    def __init__(self, textCtrl, name, pos):
        self.textCtrl = textCtrl        
        self.name = name        
        self.bufferName = name
        self.pos = pos
    
    def tryUsingBuffer(self):
        """ tryUsingBuffer()
        Try performing this callTip using the buffer. 
        Returns True on success.
        """
        bufferName = self.textCtrl._callTipBuffer_name
        t = time.time() - self.textCtrl._callTipBuffer_time
        if ( self.bufferName == bufferName and t < 0 ):
            self._finish(self.textCtrl._callTipBuffer_result)
            return True
        else:
            return False
    
    def finish(self, callTipText):
        """ finish(callTipText)
        Finish the introspection using the given calltipText.
        Will also automatically call setBuffer.
        """
        self.setBuffer(callTipText)
        self._finish(callTipText)
    
    def setBuffer(self, callTipText, timeout=4):
        """ setBuffer(callTipText)        
        Sets the buffer with the provided text. """
        self.textCtrl._callTipBuffer_name = self.bufferName
        self.textCtrl._callTipBuffer_time = time.time() + timeout
        self.textCtrl._callTipBuffer_result = callTipText
    
    def _finish(self, callTipText):
        self.textCtrl.callTipShow(self.pos, callTipText, 0, -1)


class AutoCompObject:
    """ Object to help the process of auto completion. 
    An instance of this class is created for each auto completion action.
    """
    def __init__(self, textCtrl, name, needle):
        self.textCtrl = textCtrl        
        self.bufferName = name # name to identify with 
        self.name = name  # object to find attributes of
        self.needle = needle # partial name to look for
        self.names = set() # the names (use a set to prevent duplicates)
        self.importNames = []
        self.importLines = {}
    
    def addNames(self, names):  
        """ addNames(names)
        Add a list of names to the collection. 
        Duplicates are removed."""      
        self.names.update(names)
    
    def tryUsingBuffer(self):
        """ tryUsingBuffer()
        Try performing this auto-completion using the buffer. 
        Returns True on success.
        """
        bufferName = self.textCtrl._autoCompBuffer_name
        t = time.time() - self.textCtrl._autoCompBuffer_time
        if ( self.bufferName == bufferName and t < 0 ):
            self._finish(self.textCtrl._autoCompBuffer_result)
            return True
        else:
            return False
    
    def finish(self):
        """ finish()
        Finish the introspection using the collected names.
        Will automatically call setBuffer.
        """
        # Remember at the object that started this introspection
        # and get sorted names
        names = self.setBuffer(self.names)
        # really finish        
        self._finish(names)
    
    def setBuffer(self, names=None, timeout=None):
        """ setBuffer(names=None)        
        Sets the buffer with the provided names (or the collected names).
        Also returns a list with the sorted names. """
        # Determine timeout
        # Global namespaces change more often than local one, plus when
        # typing a xxx.yyy, the autocompletion buffer changes and is thus
        # automatically refreshed.
        # I've once encountered a wrong autocomp list on an object, but
        # haven' been able to reproduce it. It was probably some odity.
        if timeout is None:
            if self.bufferName:
                timeout = 5 
            else:
                timeout = 1
        # Get names
        if names is None:
            names = self.names
        # Make list and sort
        names = list(names)
        names.sort(key=str.upper)
        # Store
        self.textCtrl._autoCompBuffer_name = self.bufferName
        self.textCtrl._autoCompBuffer_time = time.time() + timeout
        self.textCtrl._autoCompBuffer_result = names
        # Return sorted list
        return names
    
    def _finish(self, names):
        # Show completion list if required. 
        self.textCtrl.autocompleteShow(len(self.needle), names)
    
    def nameInImportNames(self, importNames):
        """ nameInImportNames(importNames)
        Test whether the name, or a base part of it is present in the
        given list of names. Returns the (part of) the name that's in
        the list, or None otherwise.
        """
        baseName = self.name
        while baseName not in importNames:
            if '.' in baseName:
                baseName = baseName.rsplit('.',1)[0]
            else:
                baseName = None
                break
        return baseName
    
    
if __name__=="__main__":
    app = QtGui.QApplication([])
    win = BaseTextCtrl(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    tmp += "a\u20acb\n"
    win.setText(tmp)    
    win.show()
    styleManager.loadStyles() # this is not required (but do now for testing)
    app.exec_()
    
