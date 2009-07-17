""" Module editor
"""


import iep
import time
import os

from PyQt4 import QtCore, QtGui
from PyQt4 import Qsci

qt = QtGui


# todo: faces depend on platform
FACES = { 'times' : 'Times New Roman',  'mono' : 'Courier New',
              'helv' : 'Arial',  'other' : 'Comic Sans MS' }

class StyleManager(QtCore.QObject):
    """ Singleton class for managing the styles of the text control. """
    
    #styleUpdate = QtCore.pyqtSignal()
    
    def __init__(self):
        self._s = None
        self.loadStyles()
    
    
    def loadStyles(self, filename='styles.ssdf'):
        # check file
        if not os.path.isfile(filename):
            filename = os.path.join( os.path.dirname(__file__), filename )
        if not os.path.isfile(filename):
            print "warning: style file not found."
            return
        # load file
        import ssdf
        self._s = ssdf.load(filename)
        #styleUpdate.emit()
    
    def buildStyleTree(self):
        """ Using the load ssdf file, build a tree such that
        the styles can be applied to the editors easily. """
        
        if self._s is None:
            return
        
        # do for each defined style
        for stylename in self._s:
            
            # get style attributes
            styles = s[styleName]
            
            # make sure lexer and keywords are present
            if not 'lexer' in styles:
                styles.lexer = ''
            # set keywords
            if not 'keywords' in styles:
                styles.keywords = ''
        
        # check out the styling
        for styleNr in styles:
            if not (styleNr.startswith('s') and len(styleNr) == 4):
                continue
            
            # get element string that contains several style attributes
            # We will extract these attributes and organise them nicely
            # in a dict.
            style = styles[styleNr]
            styleDict = ssdf.new()
            
            i=0
            while True:
                i = 
            
            
            # extract different portions
        
    
    def applyStyle(self, editor, styleName):
        s = self._s
        if s is None:
            return
        
        if not hasattr(s, styleName):
            print "Unknown style %s" % styleName
            return
        
        print "applying style,", styleName
        
        # get style attributes
        atts = s[styleName]
        
        # set lexer 
        if 'lexer' in atts:
            editor.SendScintilla(editor.SCI_SETLEXERLANGUAGE, atts['lexer'])
            #editor.SendScintilla(editor.SCI_SETLEXER, editor.SCLEX_PYTHON)
        # set keywords
        if 'keywords' in atts:
            editor.SendScintilla(editor.SCI_SETKEYWORDS, atts['keywords'])
        
        # set other stuff
        for attName in atts:
            att = atts[attName]
            if not (attName.startswith('s') and len(attName) == 4):
                continue
            # extract style number
            nr = int(attName[1:])
            print 'style', attName, nr
            # extract different portions
            
            # bold
            if att.count('bold'):
                editor.SendScintilla(editor.SCI_STYLESETBOLD, nr, 1)
            # foreground color
            i = att.find('fore:')
            if i>=0:
                i += len('fore:')
                clr = qt.QColor( att[i:i+7] )
                editor.SendScintilla(editor.SCI_STYLESETFORE, nr, clr )
            # font name
            i = att.find('face:')
            if i>= 0:
                i += len('face:')
                I = [att.find(c,i) for c in ' ,;\n\r' if att.find(c,i) > 0]
                i2 = int(min(I))
                if not I: i2 = -1 # up to last char
                facename = att[i:i2] % FACES
                #print "FACE",facename
                editor.SendScintilla(editor.SCI_STYLESETFONT, nr, facename )
            # font size
            i = att.find('size:')
            
    
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
    
