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


class StyleManager(QtCore.QObject):
    """ Singleton class for managing the styles of the text control. """
    
    styleUpdate = QtCore.pyqtSignal()
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self._filename = os.path.join(iep.path, 'styles.ssdf')
        self._styles = None
        self.loadStyles()    
    
    def loadStyles(self, filename=None):
        """ Load the stylefile. """
        
        # get filena,me
        if not filename:
            filename = self._filename
        else:
            self._filename = filename
        
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
                print("Unknown extension %s" % ext)
                return
        
        # first set default style to everything.
        self._applyStyle(editor,'default')
        editor.SendScintilla(editor.SCI_STYLECLEARALL)
        
        # go ...
        if styleName: # else it is plain ...
            self._applyStyle(editor, styleName)
    
    
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
        print("applying style,", styleName)
        
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
    # remove everything after first #    
    i = text.find('#')
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
    dirtyChange = QtCore.pyqtSignal()
    
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
        
        # edge indicator        
        self.SendScintilla(self.SCI_SETEDGEMODE, self.EDGE_LINE)
        self.setEdgeColumn(iep.config.edgeColumn)
        # indentation        
        self.setIndentationWidth(iep.config.indentWidth)        
        self.setIndentationGuides(iep.config.showIndentGuides)
        self.setViewWhiteSpace(iep.config.showWhiteSpace)
        # line numbers        
        self.SendScintilla(self.SCI_SETMARGINWIDTHN, 1, 30)
        self.SendScintilla(self.SCI_SETMARGINTYPEN, 1, self.SC_MARGIN_NUMBER)
        # wrapping
        if iep.config.wrapText:
            self.setWrapMode(1)
        else:
            self.setWrapMode(0)
        self.SendScintilla(self.SCI_SETWRAPVISUALFLAGS, 
            self.SC_WRAPVISUALFLAG_NONE)
        # line endings
        self.setEolMode(self.SC_EOL_LF) # lf is default
        
        # todo: tabs
        self.SendScintilla(self.SCI_SETUSETABS, False)
        
        # things I'm pretty sure about...        
        #
        
        # tab stuff        
        self.SendScintilla(self.SCI_SETBACKSPACEUNINDENTS, True)
        self.SendScintilla(self.SCI_SETTABINDENTS, True)
        
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
        
        # to see whether the doc has been changed
        self._dirty = False
        SIGNAL = QtCore.SIGNAL
        self.connect(self, SIGNAL('SCN_SAVEPOINTLEFT()'), self.makeDirty)
        
        # calltip colours...
        self.SendScintilla(self.SCI_CALLTIPSETBACK, qt.QColor('#FFFFB8'))
        self.SendScintilla(self.SCI_CALLTIPSETFORE, qt.QColor('#404040'))
        self.SendScintilla(self.SCI_CALLTIPSETFOREHLT, qt.QColor('#0000FF'))
        
        # selection colours...
#         self.SendScintilla(self.SCI_SETSELFORE, qt.QColor('#CCCCCC'))
#         self.SendScintilla(self.SCI_SETSELBACK, qt.QColor('#333366'))
    
    
    ## Methods that (closely) wrap a call using SendScintilla
    # and that are not implemented by QScintilla
    
    def setIndentationWidth(self, width):
        """ Set the indentation width and tab width simultaniously. """
        self.SendScintilla(self.SCI_SETINDENT, width)
        self.SendScintilla(self.SCI_SETTABWIDTH, width)    
    
    def getIndentationWidth(self):
        return self.SendScintilla(self.SCI_GETINDENT)
    
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
        """ Get the text on the given line number. """
        return self.text(linenr)
    
    def getCurLine(self):
        """ Get the current line (as a string) and the 
        position of the cursor in it. """
        linenr, index = self.getCursorPosition()
        line = self.getLine(linenr)
        return line, index
    
    def getAnchor(self):
        """ Get the anchor (as int) of the cursor. If this is
        different than the position, than text is selected."""
        return self.SendScintilla(self.SCI_GETANCHOR)
    
    def setAnchor(self, pos):
        """ Set the position of the anchor. """
        self.SendScintilla(self.SCI_SETANCHOR, pos)
    
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
    
    def makeDirty(self, value=True): 
        """ Handler of the callback for SAVEPOINTLEFT,
        and used as a way to tell scintilla we just saved. """
        self._dirty = value
        if not value:
            self.SendScintilla(self.SCI_SETSAVEPOINT)
        self.dirtyChange.emit()
    
    
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
        
        indentWidth = self.getIndentationWidth()
        
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
            text = removeComment( self.getLine(linenr) )
            ind = len(text) - len(text.lstrip())
            ind = int(round(ind/indentWidth))
            if styleOk and len(text)>0 and text[-1] == ':':
                text2insert = "\n"+" "*((ind+1)*indentWidth)                
            else:                
                text2insert = "\n"+" "*(ind*indentWidth)            
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
    
    def setText(self, value):
        self.SendScintilla(self.SCI_SETTEXT, value)
    
    def getText(self):
        return self.text()
    
    def setStyle(self, styleName=None):
        # remember style or use remebered style
        if styleName is None:
            styleName = self._styleName
        else:
            self._styleName = styleName
        # apply
        styleManager.applyStyle(self,styleName)


if __name__=="__main__":
    app = QtGui.QApplication([])
    win = BaseTextCtrl(None)
    win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    styleManager.loadStyles() # this is not required (but do now for testing)
    app.exec_()
    
