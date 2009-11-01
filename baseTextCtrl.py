""" Module baseTextCtrl.
Defines the base text control to be inherited by the shell and editor
classes. Implements styling, introspection and a bit of other stuff that
is common for both shells and editors.
"""

    
import iep
import os, sys, time
import ssdf

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci
qt = QtGui


# define fontnames
if 'win' in sys.platform:
    FACES = {'serif': 'Times New Roman', 'mono': 'Courier New', 'sans': 'Arial'}
elif 'mac' in sys.platform:
    FACES = {'serif': 'Lucida Grande', 'mono': 'Monaco', 'sans': 'Geneva'}
else:
    FACES = {'serif': 'Times', 'mono': 'Courier', 'sans': 'Helvetica'}


def normalizePath(path):
    """ Normalize the path given. 
    All slashes will be made the same (and doubles removed)
    The real case as stored on the file system is recovered.
    """
    
    # normalize
    path = os.path.abspath(path)  # make sure it is defined from the drive up
    path = os.path.normpath(path).lower() # make all os.sep (slashes \\ on win)
    
    # split in parts
    parts = path.split(os.sep)
    sep = '/'
    
    # make a start
    drive, tmp = os.path.splitdrive(path)
    if drive:
        # windows
        fullpath = drive.upper() + sep
        parts = parts[1:]
    else:
        # posix/mac
        fullpath = sep + parts[1] + sep
        parts = parts[2:] # as '/dev/foo/bar' becomes ['','dev','bar']
    
    for part in parts:
        # print( fullpath,part)
        options = [x for x in os.listdir(fullpath) if x.lower()==part]
        if len(options) > 1:
            raise Exception("Ambiguous path names!")
        elif len(options) < 1:
            raise IOError("Invalid path: "+fullpath+part)
        fullpath += options[0] + sep
    
    # remove last sep
    return fullpath[:-len(sep)]



class StyleManager(QtCore.QObject):
    """ Singleton class for managing the styles of the text control. """
    
    styleUpdate = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self._filename = os.path.join(iep.path, 'styles.ssdf')
        if not os.path.isfile(self._filename):
            raise RuntimeError("The stylefile does not exist: "+self._filename)
        self._filename = normalizePath(self._filename)
        self._styles = None
        self.loadStyles()    
    
    def loadStyles(self, filename=None):
        """ Load the stylefile. """
        
        # get filena,me
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
        self.buildStyleTree()
        self.styleUpdate.emit()
    
    def getStyleNames(self):
        return [name for name in self._styles]
    
    def buildStyleTree(self):
        """ Using the load ssdf file, build a tree such that
        the styles can be applied to the editors easily. """
        
        # a stylefile is an ssdf file which contains styling information
        # for several style types.
        # Each style is identified with a stylename and consists of a 
        # lexer, keywords, extension, several substyle strings (one for 
        # each substylenr) and can be based on any other style. 
        # All styles are automtically based on the style named default.
        
        if self._styles is None:
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
                subStyleString = subStyleString.replace(',', ' ')
                subStyleString = subStyleString.replace(';', ' ')
                
                # split in parts
                subStyleStrings = subStyleString.split(' ')
                
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
                        subStyle['face'] = tmp % FACES
                    if s.startswith('size:'):
                        tmp = s[len('size:'):]
                        subStyle['size'] = int(tmp)
                #print(subStyle)
    
    
    def applyStyle(self, editor, styleName):
        """ Apply the specified style to the specified editor. 
        The stylename can be the name of the style, or the extension
        of the file to be styled (indicated by starting with a dot '.')
        The actual stylename is returned.
        """
        
        # make lower case
        styleName = styleName.lower()
        
        # if styletree was not yet build, return
        if self._styles is None:
            return
        
        # if extension was given, find out which style it belongs to
        if styleName.startswith('.'):
            ext = styleName[1:]
            for styleName in self._styles:
                exts = self._styles[styleName].ext.split(' ')                
                if ext in exts:
                    break
            else:
                tmp = "Unknown extension {}, applying default style."
                print(tmp.format(ext))
                styleName = ''
        
        # first set default style to everything.
        self._applyStyle(editor,'default')
        editor.SendScintilla(editor.SCI_STYLECLEARALL)
        
        # go ...
        if styleName: # else it is plain ...
            self._applyStyle(editor, styleName)
        
        # return actual stylename
        return styleName
    
    def _applyStyle(self, editor, styleName):
        """ Actually apply style """
        
        # get the style (but check if exists first)
        if not styleName in self._styles:
            print("Unknown style %s" % styleName)
            return
        style = self._styles[styleName]
        
        # apply style on which it is based.
        if style.basedon:
            self._applyStyle(editor, style.basedon)
        
        # start ...
        #print("applying style,", styleName)
        
        # set basic stuff first
        if 'lexer' in style:
            editor.SendScintilla(editor.SCI_SETLEXERLANGUAGE, style.lexer)
        if 'keywords' in style:
            editor.SendScintilla(editor.SCI_SETKEYWORDS, style.keywords)
        
        # define dict
        subStyleStuff = {   'face': editor.SCI_STYLESETFONT,
                            'fore': editor.SCI_STYLESETFORE,
                            'back': editor.SCI_STYLESETBACK,
                            'size': editor.SCI_STYLESETSIZE,
                            'bold': editor.SCI_STYLESETBOLD,
                            'italic': editor.SCI_STYLESETITALIC,
                            'underline': editor.SCI_STYLESETUNDERLINE}
        
        # check out the substyle strings (which are of the form 'sxxx')
        for styleNr in style:
            if not (styleNr.startswith('s') and len(styleNr) == 4):
                continue
            
            # get substyle number to tell scintilla
            nr = int(styleNr[1:])
            # get dict
            subStyle = style[styleNr]
            
            # set substyle attributes
            for key in subStyleStuff:
                scintillaCommand = subStyleStuff[key]
                if key in subStyle:
                    value = subStyle[key]
                    editor.SendScintilla(scintillaCommand, nr, value)

    
styleManager = StyleManager()
iep.styleManager = styleManager

# todo: i think this can go
class InteractiveAPI(Qsci.QsciAPIs):
    """ API that will query introspection information
    from the current session.
    """
    def __init__(self, lexer):
        Qsci.QsciAPIs.__init__(self, lexer)
        
        self.add("foo(lala)")
        self.add("bar")
        #self.prepare()


class KeyEvent:
    """ A simple class for easier key events. """
    def __init__(self, key):
        self.key = key
        try:
            self.char = chr(key)        
        except ValueError:
            self.char = ""


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
    


class BaseTextCtrl(Qsci.QsciScintilla):
    """ The base text control class.
    Inherited by the shell class and the IEP editor.
    The class implements autocompletion, calltips, and auto-help,
    as well as styling and stuff like autoindentation.
    Inherits from QsciScintilla, cannot inherit from QsciScintillaBase
    because every sendscintilla method that should return a string
    does not work, so there is no way to get text.
    """
        
    def __init__(self, parent):
        Qsci.QsciScintillaBase.__init__(self,parent)
        
        # be notified of style updates
        self._styleName = ''
        styleManager.styleUpdate.connect(self.setStyle)
        
        # SET PREFERENCES
        # Inherited classes may override some of these settings. Indentation
        # guides are not nice in shells for instance...
        
        # things I might want to make optional/settable
        #
        
        # use unicode
        self.SendScintilla(self.SCI_SETCODEPAGE, self.SC_CP_UTF8)
        self.SendScintilla(self.SCI_SETKEYSUNICODE, 1) # does not seem to do anything
        
        # edge indicator        
        self.SendScintilla(self.SCI_SETEDGEMODE, self.EDGE_LINE)
        self.setEdgeColumn(iep.config.edgeColumn)
        # indentation        
        self.setIndentation(iep.config.defaultIndentation)
        self.setTabWidth(iep.config.tabWidth)  
        self.setIndentationGuides(iep.config.showIndentGuides)
        self.setViewWhiteSpace(iep.config.showWhiteSpace)
        # wrapping
        if iep.config.wrapText:
            self.setWrapMode(2) # 0:None, 1:Word, 2:Character 
        else:
            self.setWrapMode(0)
        self.SendScintilla(self.SCI_SETWRAPVISUALFLAGS, 
            self.SC_WRAPVISUALFLAG_NONE)
        # line endings
        self.setEolMode(self.SC_EOL_LF) # lf is default
        
        # things we fix
        #
        
        # line numbers        
        self.SendScintilla(self.SCI_SETMARGINWIDTHN, 1, 30)
        self.SendScintilla(self.SCI_SETMARGINTYPEN, 1, self.SC_MARGIN_NUMBER)
        # tab stuff        
        self.SendScintilla(self.SCI_SETBACKSPACEUNINDENTS, True)
        self.SendScintilla(self.SCI_SETTABINDENTS, True)
        
        # clear all command keys
        # self.SendScintilla(self.SCI_CLEARALLCMDKEYS)
        # No, that even removes the arrow keys and suchs
        
        # clear some command keys
        ctrl, shift = self.SCMOD_CTRL<<16, self.SCMOD_SHIFT<<16
        # these we all map via the edit menu
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('X')+ ctrl)
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('C')+ ctrl)
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('V')+ ctrl)
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('Z')+ ctrl)
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('Y')+ ctrl)
        self.SendScintilla(self.SCI_CLEARCMDKEY, ord('A')+ ctrl)
#         # these are mostly not used ...
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('D')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('L')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('L')+ ctrl+shift)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('T')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('T')+ ctrl+shift)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('U')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('U')+ ctrl+shift)
        
        # In QT, the vertical scroller is always shown        
        
        # set brace matchin on
        #self.setBraceMatching(self.SloppyBraceMatch)
        
        # calltips, I dont know what this exactly does
        #self.setCallTipsStyle(self.CallTipsNoContext)
        
        # autocompletion setting
#         self.setAutoCompletionThreshold(1) # 0 means disabled
        self.SendScintilla(self.SCI_AUTOCSETCHOOSESINGLE, False)
        self.SendScintilla(self.SCI_AUTOCSETDROPRESTOFWORD, False)
        self.SendScintilla(self.SCI_AUTOCSETIGNORECASE, True)
        
        # calltip colours...
        self.SendScintilla(self.SCI_CALLTIPSETBACK, qt.QColor('#FFFFB8'))
        self.SendScintilla(self.SCI_CALLTIPSETFORE, qt.QColor('#404040'))
        self.SendScintilla(self.SCI_CALLTIPSETFOREHLT, qt.QColor('#0000FF'))
        
        # selection colours...
#         self.SendScintilla(self.SCI_SETSELFORE, qt.QColor('#CCCCCC'))
#         self.SendScintilla(self.SCI_SETSELBACK, qt.QColor('#333366'))
    
    
    ## Methods that (closely) wrap a call using SendScintilla
    # and that are not implemented by QScintilla
    
    def setIndentation(self, value):
        """ Set the used indentation. If a number larger than 0,
        tabs are disabled and the number is the amount of spaces for
        an indent. If the number is negative, tabs are used for 
        indentation. """
        if value < 0:
            self.SendScintilla(self.SCI_SETUSETABS, True)
            self.SendScintilla(self.SCI_SETINDENT, 0)
        else:
            self.SendScintilla(self.SCI_SETUSETABS, False)
            self.SendScintilla(self.SCI_SETINDENT, value)
    
    def getIndentation(self):
        if self.SendScintilla(self.SCI_GETUSETABS):
            return -1
        else:
            return self.SendScintilla(self.SCI_GETINDENT)
    
    def setTabWidth(self, width):
        """ Set the tab width """
        self.SendScintilla(self.SCI_SETTABWIDTH, width)    
    
    def getTabWidth(self):
        return self.SendScintilla(self.SCI_GETTABWIDTH)
    
    def setViewWhiteSpace(self, value):
        """ Set the white space visibility, can be True or False, 
        or 0, 1, or 2, where 2 means show after indentation. """
        value = int(value)
        self.SendScintilla(self.SCI_SETVIEWWS, value)
    
    def getCurrentPos(self):
        """ Get the position (as an int) of the cursor. 
        getCursorPosition() returns a (linenr, index) tuple.
        """        
        return self.SendScintilla(self.SCI_GETCURRENTPOS)
    
    def setCurrentPos(self, pos):
        """ Set the position of the cursor. """
        self.SendScintilla(self.SCI_SETCURRENTPOS, pos)
    
    def getLine(self, linenr):
        """ Get the bytes on the given line number. """
        len = self.SendScintilla(self.SCI_LINELENGTH)+1
        bb = QtCore.QByteArray(len,'0')
        N = self.SendScintilla(self.SCI_GETLINE, len, bb)
        return bytes(bb)[:-1]
    # todo: when to return bytes and when a string?
    
    def getCurLine(self):
        """ Get the current line (as a string) and the 
        position of the cursor in it. """
        linenr, index = self.getCursorPosition()
        line = self.getLine(linenr).decode('utf-8')
        return line, index
    
    def getAnchor(self):
        """ Get the anchor (as int) of the cursor. If this is
        different than the position, than text is selected."""
        return self.SendScintilla(self.SCI_GETANCHOR)
    
    def setAnchor(self, pos):
        """ Set the position of the anchor. """
        self.SendScintilla(self.SCI_SETANCHOR, pos)
    
    def lineFromPosition(self, pos):
        """ Get the line number, given the position. """
        return self.SendScintilla(self.SCI_LINEFROMPOSITION, pos)
    
    def positionFromLine(self, linenr):
        """ Get the position, given the line number. """
        return self.SendScintilla(self.SCI_POSITIONFROMLINE , linenr)
    
    
    def setTargetStart(self, pos):
        """ Set the start of selection target. """
        self.SendScintilla(self.SCI_SETTARGETSTART, pos)
    
    def setTargetEnd(self, pos):
        """ Set the end of selection target. """
        self.SendScintilla(self.SCI_SETTARGETEND, pos)
    
    def replaceTarget(self, value):
        """ Set the start of selection. """
        value = value.encode('utf-8')
        self.SendScintilla(self.SCI_REPLACETARGET, len(value), value)
    
    
    def styleAt(self, pos):
        """ Get the style at the given position."""
        return self.SendScintilla(self.SCI_GETSTYLEAT,pos)
        
    def charAt(self,pos):
        """ Get the characted at the current position. """
        char = self.SendScintilla(self.SCI_GETCHARAT, pos)
        if char == 0:
            return ""
        elif char < 0:
            return chr(char + 256)
        else:
            return chr(char)
    
    def autoCompActive(self):         
        return self.SendScintilla(self.SCI_AUTOCACTIVE)
    
    
    ## Other methods
    
    def Introspect_isValidPython(self):
        """ Check if the code at the cursor is valid python:
        - the active lexer is the python lexer
        - the style at the cursor is "default"
        """
        
        # only complete if lexer is python
        if ~isinstance(self.lexer(), Qsci.QsciLexerPython):
            return False
        
        # the style must be "default"
        curstyle = self.styleAt(self.getCurrentPos())
        if curstyle not in [self._lexer.Default, self._lexer.Operator]:
            return False
        
        # all good
        return True  
    
    ## Callbacks
    
    
    def keyPressEvent(self, event):
        # create simple keyevent class
        keyevent = KeyEvent( event.key() )
        # set modifiers
        modifiers = event.modifiers()
        keyevent.controldown = modifiers & QtCore.Qt.ControlModifier
        keyevent.altdown = modifiers & QtCore.Qt.AltModifier
        keyevent.shiftdown = modifiers & QtCore.Qt.ShiftModifier
        # dispatch event
        handled = self.keyPressEvent2( keyevent )
        if not handled:
            Qsci.QsciScintillaBase.keyPressEvent(self, event)
        
        # todo: I need these commands to deal with encoding
        i0 = self.getCurrentPos()
        i1 = self.SendScintilla(self.SCI_POSITIONBEFORE, i0)
        i2 = self.SendScintilla(self.SCI_POSITIONAFTER, i0)
        #print(i1, i0, i2) 
    
    def keyPressEvent2(self, event):
        """ A slightly easier keypress event. 
        
         For the autocomplete.
        - put it on if we enter a char (by OnCharDown callback)
        - if pressing backspace
        - selecting by double clicking
        
        - If the style is not good
        - put it off when clicking outside or using arrows
        - when window loses focus
        - when pressing escape
        - when an invalid character occurs.
        
        This one is called last...
        """
        
        self.SendScintilla(self.SCI_CALLTIPSHOW, "hallo")
        
        indentWidth = self.getIndentation()
        indent = ' '
        if indentWidth<0:
            indentWidth = 1
            indent = '\t'
        
        if event.key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            # auto indentation
            
            # check if style is ok...
            curstyle = self.styleAt(self.getCurrentPos())
            if curstyle in [0,10]: # default, operator
                styleOk = True
            else:
                styleOk = False
            # auto indent!
            linenr,index = self.getCursorPosition()
            text = self.getLine(linenr)
            if not text:
                return False
            line = self.getLine(linenr)
            print(type(line))
            text = removeComment( line )
            ind = len(text) - len(text.lstrip())
            ind = int(round(ind/indentWidth))
            if styleOk and len(text)>0 and text[-1] == ':':
                text2insert = "\n"+indent*((ind+1)*indentWidth)                
            else:                
                text2insert = "\n"+indent*(ind*indentWidth)            
            self.insertAt(text2insert, linenr, index)
            pos = self.getCurrentPos()
            self.setCurrentPos( pos + len(text2insert) )
            self.setAnchor( pos + len(text2insert) )
            return True
            #self.StopIntrospecting()
        
        if event.key == QtCore.Qt.Key_Escape:
            # clear signature of current object 
            self._introspect_signature = ("","")
            
        if event.key == QtCore.Qt.Key_Backspace:
            pass
            #wx.CallAfter(self.Introspect_autoComplete)
            #wx.CallAfter(self.Introspect_signature)
            
        if event.key in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
            # show signature also when moving inside it
            pass
            #wx.CallAfter(self.Introspect_signature)
            
        updown = [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]
        if event.key in updown and self.autoCompActive():
            # show help!
            pass
            
#             # get current selected name in autocomp list
#             try:                
#                 i = self.AutoCompGetCurrent()
#                 i += {wx.WXK_UP:-1, wx.WXK_DOWN:+1}[key]
#                 if i< 0: 
#                     i=0
#                 if i>=len(self._introspect_list):
#                     i = len(self._introspect_list) -1 
#                 name = self._introspect_list[ i ]
#             except IndexError:
#                 name = ""
#             # add base part
#             if self._introspect_baseObject:
#                 name = self._introspect_baseObject + "." + name
#             
#             # aply
#             self.Introspect_help(name,True)
        
        # never accept event
        return False
    
    ## Public methods
    
    # todo: note that I just as well might give the undecoded bytes!
    
    def setBytes(self, value):
        """ Set the text as utf-8 encoded bytes. """
        self.SendScintilla(self.SCI_SETTEXT, value)
    
    def getBytes(self):
        """ Get the text as bytes (utf-8 encoded). This is how
        the data is stored internally. """
        len = self.SendScintilla(self.SCI_GETLENGTH)+1
        bb = QtCore.QByteArray(len,'0')
        N = self.SendScintilla(self.SCI_GETTEXT, len, bb)
        return bytes(bb)[:-1]
    
    def setText(self, value):
        """ Set the text as a unicode string. """
        bb = value.encode('utf-8')
        self.SendScintilla(self.SCI_SETTEXT, bb)
    
    def getText(self):
        """ Get the text as a unicode string. """
        value = self.getBytes().decode('utf-8')
        # print (value) printing can give an error because the console font
        # may not have all unicode characters
        return value
    
    def setStyle(self, styleName=None):
        # remember style or use remebered style
        if styleName is None:
            styleName = self._styleName        
        # apply and remember
        self._styleName = styleManager.applyStyle(self,styleName)
    
    def getStyleName(self):
        """ Get the name of the currently applied style. """
        return self._styleName
    

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
    
