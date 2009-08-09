""" Module editor
"""


import iep
import time
import os

import ssdf

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci

qt = QtGui


# todo: faces depend on platform
FACES = { 'serif' : 'Times New Roman',  'mono' : 'Courier New',
              'sans' : 'Arial',  'other' : 'Comic Sans MS' }

class StyleManager(QtCore.QObject):
    """ Singleton class for managing the styles of the text control. """
    
    #styleUpdate = QtCore.pyqtSignal()
    
    def __init__(self):
        self._styles = None
        self.loadStyles()
    
    
    def loadStyles(self, filename='styles.ssdf'):
        """ Load the stylefile. """
        
        # check file
        if not os.path.isfile(filename):
            filename = os.path.join( os.path.dirname(__file__), filename )
        if not os.path.isfile(filename):
            print "warning: style file not found."
            return
        # load file
        import ssdf
        self._styles = ssdf.load(filename)
        self.buildStyleTree()
        #styleUpdate.emit()
    
    
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
            
            # make sure lexer and keywords are present
            if not 'lexer' in style:
                style.lexer = ''            
            # set keywords
            if not 'keywords' in style:
                style.keywords = ''            
            # make based on correct            
            if not 'basedon' in style:
                style.basedon = ''
            # extensions
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
        #                 self._setStyleElement(subStyle, 'bold', s)
        #                 self._setStyleElement(subStyle, 'italic', s)
        #                 self._setStyleElement(subStyle, 'underline', s)
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
                
                print subStyle
    
    def _setStyleElement(self, styleDict, styleElementName, styleString):
        """ Check if the string styleElementName is present in styleString.
        If so, make styleDict[styleElementName] True. Othersise False.
        """
        if styleString.count(styleElementName):
            styleDict[styleElementName] = True
        else:
            styleDict[styleElementName] = False
    
    
    def applyStyle(self, editor, styleName):
        """ Apply a style. """
        # todo: also allow setting using extension
        # todo: process basedon first
        if self._styles is None:
            return
        
        if not hasattr(self._styles, styleName):
            print "Unknown style %s" % styleName
            return
        
        print "applying style,", styleName
        
        # get style attributes
        style = self._styles[styleName]
        
        # set basic stuff first
        editor.SendScintilla(editor.SCI_SETLEXERLANGUAGE, style['lexer'])
        editor.SendScintilla(editor.SCI_SETKEYWORDS, style['keywords'])
        
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
            

class IepTextCtrl(Qsci.QsciScintillaBase):
    """ The base text control class.
    Inherited by the shell class and the IEP editor.
    The class implements autocompletion, calltips, and auto-help.
    """
    
    def __init__(self, parent):
        Qsci.QsciScintillaBase.__init__(self,parent)
        
        # SET PREFERENCES
        # Inherited classes may override some of these settings. Indentation
        # guides are not nice in shells for instance...
        
        # things I might want to make optional/settable
        #
        
        # edge indicator
        self.SendScintilla(self.SCI_SETEDGECOLUMN, iep.config.edgeColumn)
        self.SendScintilla(self.SCI_SETEDGEMODE, self.EDGE_LINE)
        # indentation        
        self.setIndentationWidth(iep.config.indentWidth)        
        self.setIndentationGuides(iep.config.showIndentGuides)
        self.setViewWhiteSpace(iep.config.showWhiteSpace)
        # line numbers        
        self.SendScintilla(self.SCI_SETMARGINWIDTHN, 1, 30)
        self.SendScintilla(self.SCI_SETMARGINTYPEN, 1, self.SC_MARGIN_NUMBER)
        # wrapping
        if True: #iep.config.wrapText:
            self.setWrapMode(1)
        else:
            self.setWrapMode(0)
        self.SendScintilla(self.SCI_SETWRAPVISUALFLAGS, 
            self.SC_WRAPVISUALFLAG_NONE)
        # line endings
        self.setEolMode(self.SC_EOL_LF) # lf is default
        
        # things I'm pretty sure about...        
        #
        
        # tab stuff        
        self.SendScintilla(self.SCI_SETUSETABS, False)
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
       
        self.connect(self, QtCore.SIGNAL('SCN_SAVEPOINTLEFT()'), self.onTextChanged)
        
        # calltip colours...
        self.SendScintilla(self.SCI_CALLTIPSETBACK, qt.QColor('#FFFFB8'))
        self.SendScintilla(self.SCI_CALLTIPSETFORE, qt.QColor('#404040'))
        self.SendScintilla(self.SCI_CALLTIPSETFOREHLT, qt.QColor('#0000FF'))
        
        # selection colours...
#         self.SendScintilla(self.SCI_SETSELFORE, qt.QColor('#CCCCCC'))
#         self.SendScintilla(self.SCI_SETSELBACK, qt.QColor('#333366'))
    
    
    ## Methods that (closely) wrap a call using SendScintilla
    
    def setIndentationWidth(self, width):
        """ Set the indentation width and tab width simultaniously. """
        self.SendScintilla(self.SCI_SETINDENT, width)
        self.SendScintilla(self.SCI_SETTABWIDTH, width)    
    
    def getIndentationWidth(self):
        return self.SendScintilla(self.SCI_GETINDENT)
    
    def setIndentationGuides(self, value):
        """ Set indentation guides visibility. """
        self.SendScintilla(self.SCI_SETINDENTATIONGUIDES, value)
    
    def setViewWhiteSpace(self, value):
        """ Set the white space visibility, can be True or False, 
        or 0, 1, or 2, where 2 means show after indentation. """
        value = int(value)
        self.SendScintilla(self.SCI_SETVIEWWS, value)
    
    def setWrapMode(self, value):
        """ Set the way that text is wrapped for long lines.
        value can be 0, 1, 2 for none, word and char respectively.
        """
        value = int(value)
        self.SendScintilla(self.SCI_SETWRAPMODE, value)
    
    def setEolMode(self, value):
        """ Set the end-of-line mode. 
        value can be 0,1,2 for CRLF, CR, LF respectively.
        """
        self.SendScintilla(self.SCI_SETEOLMODE, value)
    
    def getCurrentPos(self):
        """ Get the position (as an int) of the cursor. 
        getCursorPosition() returns a (line, index) tuple.
        """        
        return self.SendScintilla(self.SCI_GETCURRENTPOS)
    
    def setCurrentPos(self, pos):
        """ Set the position of the cursor. """
        self.SendScintilla(self.SCI_SETCURRENTPOS, pos)
        
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
    
    def positionFromLineIndex(self, line, index):
        """ Method to convert line and index to an absolute position.
        """
        pos = self.SendScintilla(self.SCI_POSITIONFROMLINE, line)
        # Allow for multi-byte characters
        for i in range(index):
            pos = self.SendScintilla(self.SCI_POSITIONAFTER, pos)
        return pos
    
    
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
    
    def onTextChanged(self):        
        print "yeah"
        #self.autoCompleteFromAPIs()        
        #self.callTip()
    
    
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
    
    def keyPressEvent2(self, keyevent):
        """ A slightly easier keypress event. """
        self.SendScintilla(self.SCI_CALLTIPSHOW, "hallo")
    
    
    ## Public methods
    
    def setText(self, value):
        self.SendScintilla(self.SCI_SETTEXT, value)
    
    def getText(self):
        return self.SendScintilla(self.SCI_GETTEXT)
    
    def loadStyles(self, filename='styles.ssdf'):        
        pass
        
        
    def setFileType(self, extension):
        #self.SendScintilla(self.SCI_SETLEXERLANGUAGE, 'python')
        #self.SendScintilla(self.SCI_SETKEYWORDS, 'for print and is raise')
        styleManager.applyStyle(self,'default')
        self.SendScintilla(self.SCI_STYLECLEARALL)
        styleManager.applyStyle(self,'python')

if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepTextCtrl(None)
    win.setFileType('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setText(tmp)    
    win.show()
    app.exec_()
    
