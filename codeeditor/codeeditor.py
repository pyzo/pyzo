"""
Extensible Code Editor


"""

"""
WRITING EXTENSIONS FOR THE CODE EDITOR

The Code Editor extension mechanism works solely based on inheritance.
Extensions can override event handlers (e.g. paintEvent, keyPressEvent). Their
default behaviour should be to call their super() event handler. This way,
events propagate through the extensions following Python's method resolution
order (http://www.python.org/download/releases/2.3/mro/).

A 'fancy' code editor with extensions is created like:

class FancyEditor( Extension1, Extension2, ... CodeEditorBase):
    pass

The order of the extensions does usually matter! If multiple Extensions process
the same key press, the first one has the first chance to consume it.

OVERRIDING __init__

An extensions' __init__ method (if required) should look like this:
class Extension:
    def __init__(self, *args, extensionParam1 = 1, extensionParam2 = 3, **kwds):
        super().__init__(*args, **kwds)
        some_extension_init_stuff()
        
Note the following points:
 - All parameters have default values
 - The use of *args passes all non-named arguments to its super(), which
   will therefore end up at the QPlainTextEdit constructor. As a consequence,
   the parameters of the exentsion can only be specified as named arguments
 - The use of **kwds ensures that parametes that are not defined by this 
   extension, are passed to the next extension(s) in line.
 - The call to super().__init__ is the first thing to do, this ensures that at
   least the CodeEditorBase and QPlainTextEdit, of which the CodeEditorBase is
   derived, are initialized when the initialization of the extension is done

OVERRIDING keyPressEvent

When overriding keyPressEvent, the extension has several options when an event
arrives:
 - Ignore the event
     In this case, call super().keyPressEvent(event) for other extensions or the
     CodeEditorBase to process the event
 - Consume the event
     In order to prevent other next extensions or the CodeEditorBase to react
     on the event, return without calling the super().keyPressEvent
 - Do something based on the event, and do not let the event propagate
     In this case, do whatever action is defined by the extension, and do not
     call the super().keyPressEvent
 - Do something based on the event, and let the event propagate
     In this case, do whatever action is defined by the extension, and do call
     the super().keyEvent

In any case, the keyPressEvent should not return a value (i.e., return None).
Furthermore, an extension may also want to perform some action *after* the
event has been processed by the next extensions and the CodeEditorBase. In this
case, perform that action after calling super().keyPressEvent

OVERRIDING paintEvent

Then overriding the paintEvent, the extension may want to paint either behind or
in front of the CodeEditorBase text. In order to paint behind the text, first
perform the painting, and then call super().paintEvent. In order to paint in
front of the text, first call super().paintEvent, then perform the painting.

As a result, the total paint order is as follows for the example of the
FancyEditor defined above:
- First the extensions that draw behind the text (i.e. paint before calling
  super().paintEvent, in the order Extension1, Extension2, ...
- then the CodeEditorBase, with the text
- then the extensions that draw in front of the text (i.e. call 
  super().paintEvent before painting), in the order ..., Extension2, Extension1
  
OVERRIDING OTHER EVENT HANDLERS

When overriding other event handlers, be sure to call the super()'s event
handler; either before or after your own actions, as appropriate

OTHER ISSUES

In order to avoid namespace clashes among the extensions, take the following
into account:
 - Private members should start with __ to make ensure no clashes will occur
 - Public members / methods should have names that clearly indicate which
   extension they belong to (e.g. not cancel but autocompleteCancel)
 - Arguments of the __init__ method should also have clearly destictive names

"""
import sys
from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt
import keyword
if __name__ == '__main__':
    import python_syntax
    import appearance
    import autocompletion
    import behaviour
    import calltip
else:
    from codeeditor import parsers
    from codeeditor import appearance
    from codeeditor import autocompletion
    from codeeditor import behaviour
    from codeeditor import calltip

class BlockData(QtGui.QTextBlockUserData):
    def __init__(self):
        QtGui.QTextBlockUserData.__init__(self)
        self.indentation = None

    
""" Notes on syntax highlighting.

The syntax highlighting/parsing is performed using three "components".

The base component are the token instances. Each token simply represents
a row of characters in the text the belong to each-other and should
be styled in the same way. There is a token class for each particular
"thing" in the code, such as comments, strings, keywords, etc. Some
tokens are specific to a particular language.

There is a function that produces a set of tokens, when given a line of
text and a state parameter. There is such a function for each language.
These "parsers" are defined in the parsers subpackage.

And lastly, there is the Highlighter class, that applies the parser function
to obtain the set of tokens and using the names of these tokens applies
styling. The styling can be defined by giving a dict that maps token names
to style representations.

"""
# todo: move highlighter to separate module or keep here?

class Highlighter(QtGui.QSyntaxHighlighter):
    formats=(
        (parsers.StringToken,(0x7F007F,'')), 
        (parsers.CommentToken,(0x007F00,'')),
        (parsers.UnterminatedToken,(0,'')),
        (parsers.KeywordToken,(0x00007F,'B')),
        (parsers.NumberToken,(0x007F7F,'')),
        (parsers.MethodNameToken,(0x007F7F,'B')),
        (parsers.ClassNameToken,(0x0000FF,'B')),
        (parsers.CellCommentToken,(0x009F00,'B'))
        )
    def __init__(self,codeEditor,*args):
        QtGui.QSyntaxHighlighter.__init__(self,*args)
        #Init properties
        self._codeEditor = codeEditor
        
    ## Methods
    def getCurrentBlockUserData(self):
        """ getCurrentBlockUserData()
        
        Gets the BlockData object. Creates one if necesary.
        
        """
        bd = self.currentBlockUserData()
        if not isinstance(bd, BlockData):
            bd = BlockData()
            self.setCurrentBlockUserData(bd)
        return bd
    
    def highlightBlock(self,line): 
        
        previousState=self.previousBlockState()
        
        # todo: choose dynamically
        tokenizeLine = parsers.tokenizeLinePython
        #tokenizeLine = parsers.tokenizeLineStupid
        
        self.setCurrentBlockState(0)
        for token in tokenizeLine(line,previousState):
            for tokenType,format in self.formats:
                if isinstance(token,tokenType):
                    color,style=format
                    format=QtGui.QTextCharFormat()
                    format.setForeground(QtGui.QColor(color))
                    if 'B' in style:
                        format.setFontWeight(QtGui.QFont.Bold)
                    #format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
                    #format.setUnderlineColor(QtCore.Qt.red)
                    self.setFormat(token.start,token.end-token.start,format)
                    
            #Handle line or string continuation
            if isinstance(token,parsers.ContinuationToken):
                self.setCurrentBlockState(token.state)
        
        #Get the indentation setting of the editor
        indentUsingSpaces = self._codeEditor.indentUsingSpaces()
        
        # Get user data
        bd = self.getCurrentBlockUserData()
        
        leadingWhitespace=line[:len(line)-len(line.lstrip())]
        if '\t' in leadingWhitespace and ' ' in leadingWhitespace:
            #Mixed whitespace
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.red)
            format.setToolTip('Mixed tabs and spaces')
            self.setFormat(0,len(leadingWhitespace),format)
        elif ('\t' in leadingWhitespace and indentUsingSpaces) or \
            (' ' in leadingWhitespace and not indentUsingSpaces):
            #Whitespace differs from document setting
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.blue)
            format.setToolTip('Whitespace differs from document setting')
            self.setFormat(0,len(leadingWhitespace),format)
        else:
            # Store info for indentation guides
            # amount of tabs or spaces
            bd.indentation = len(leadingWhitespace)


class CodeEditorBase(QtGui.QPlainTextEdit):
    def __init__(self,*args, indentUsingSpaces = False, indentWidth = 4, **kwds):
        super().__init__(*args,**kwds)
        
        # Set font (always monospace)
        self.setFont()
        
        # Create highlighter class
        # todo: attribute is not private
        self.__highlighter = Highlighter(self, self.document())
        
        #Default options
        option=self.document().defaultTextOption()
        option.setFlags(option.flags()|option.IncludeTrailingSpaces|option.AddSpaceForLineAndParagraphSeparators)
        self.document().setDefaultTextOption(option)
        
        #Init properties
        self.setIndentUsingSpaces(indentUsingSpaces)
        self.setIndentWidth(indentWidth)
        
        # When the cursor position changes, invoke an update, so that
        # the hihghlighting etc will work
        self.cursorPositionChanged.connect(self.viewport().update) 
    
    
    ## Font
    
    def fontNames(self):
        """ fontNames()
        
        Get a list of all monospace fonts available on this system.
        
        """
        db = QtGui.QFontDatabase()
        QFont, QFontInfo = QtGui.QFont, QtGui.QFontInfo
        # fn = font_name (str)
        return [fn for fn in db.families() if QFontInfo(QFont(fn)).fixedPitch()]
    
    
    def defaultFont(self):
        """ defaultFont()
        
        Get the default (monospace font) for this system. Returns a QFont
        object. 
        
        """
        
        # Get font size
        f = QtGui.QFont()
        size = f.pointSize()
        
        # Get font family
        f = QtGui.QFont('this_font_name_must_not exist')
        f.setStyleHint(f.TypeWriter, f.PreferDefault)
        fi = QtGui.QFontInfo(f)
        family = fi.family()
        
        # The default family seems to be Courier new on Mac
        if sys.platform == 'darwin':            
            family = 'Monaco'
        
        # Done
        return QtGui.QFont(family, size)
    
    
    def setFont(self, font=None):
        """ setFont(font=None)
        
        Set the font for the editor. Should be a monospace font. If not,
        Qt will select the best matching monospace font.
        
        """
        
        # Check
        if font is None:
            font = self.defaultFont()
        elif isinstance(font, QtGui.QFont):
            pass
        elif isinstance(font, str):
            font = QtGui.QFont(font, self.defaultFont().pointSize())
        else:
            raise ValueError("setFont accepts None, QFont or string.")
        
        # Make sure it's monospace
        font.setStyleHint(font.TypeWriter, font.PreferDefault)
        # todo: can be done smarter, return resulting font, implement zooming
        
        # Set
        QtGui.QPlainTextEdit.setFont(self, font)
    
    
    ## Syntax
    
    def setSyntaxParser(self, parserName):
        """ setSyntaxParser(parserName)
        
        Set the parser to apply syntax highlighting, using
        the parser name.
        
        """
        raise NotImplementedError()
    
    def syntaxParser(self):
        """ syntaxParser(parserName)
        
        Get the name of the parser used to apply syntax highlighting.
        
        """
        raise NotImplementedError() 
    
    def setSyntaxStyle(self, style):
        """ setSyntaxStyle(style)
        
        Set the syntax style. style is a dict with keys corresponding 
        to the token names and values representing the styling for that
        token.
        
        Keywords are passed ....? With special attribute name, or using
        setSyntaxKeywords?
        
        """
        raise NotImplementedError() 
    
    
    def getSyntaxStyleInfo(self, parserName):
        """ Returns for the given parser info about syntax styles.
        It should give a list of all token names used, their default
        style values, and description (token docstrings).
        That way, making a dialog to set styles should be relatively easy.
        
        How? Maybe each syntax parser should only import the tokens that
        it uses. A syntax-parser-manager could easily figure out what
        tokens classes are present in the parses's module namespace.
        """
        # todo: this function, together with the fontNames() function 
        # and maybe others should move to a separate module and be 
        # exposed as loose functions to the end user. 
        raise NotImplementedError() 
    ## Properties


    def indentWidth(self):
        """
        The width of a tab character, and also the amount of spaces to use for
        indentation when indentUsingSpaces() is True
        """
        return self.__indentWidth

    def setIndentWidth(self, value):
        value = int(value)
        if value<=0:
            raise ValueError("indentWidth must be >0")
        self.__indentWidth = value
        self.setTabStopWidth(self.fontMetrics().width('i'*self.__indentWidth))
        
    def indentUsingSpaces(self):
        """
        Selects whether to use spaces (if True) or tabs (if False) to indent
        when the tab key is pressed
        """
        return self.__indentUsingSpaces
 
    def setIndentUsingSpaces(self, value):
        self.__indentUsingSpaces = bool(value)
        self.__highlighter.rehighlight()
 
    
    ## MISC
        
    def gotoLine(self,lineNumber):
        """
        Move the cursor to the block given by the line number (first line is line number 1) and show that line
        """
        cursor = self.textCursor()
        block = self.document().findBlockByNumber( lineNumber + 1)
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
    
        
    def doForSelectedBlocks(self,function):
        """
        Call the given function(cursor) for all blocks in the current selection
        A block is considered to be in the current selection if a part of it is in
        the current selection 
        
        The supplied cursor will be located at the beginning of each block. This
        cursor may be modified by the function as required
        """
        
        #Note: a 'TextCursor' does not represent the actual on-screen cursor, so
        #movements do not move the on-screen cursor
        
        #Note 2: when the text is changed, the cursor and selection start/end
        #positions of all cursors are updated accordingly, so the screenCursor
        #stays in place even if characters are inserted at the editCursor
        
        screenCursor = self.textCursor() #For maintaining which region is selected
        editCursor = self.textCursor()   #For inserting the comment marks
    
        #Use beginEditBlock / endEditBlock to make this one undo/redo operation
        editCursor.beginEditBlock()
            
        editCursor.setPosition(screenCursor.selectionStart())
        editCursor.movePosition(editCursor.StartOfBlock)
        # < :if selection end is at beginning of the block, don't include that
        #one, except when the selectionStart is same as selectionEnd
        while editCursor.position()<screenCursor.selectionEnd() or \
                editCursor.position()<=screenCursor.selectionStart(): 
            #Create a copy of the editCursor and call the user-supplied function
            editCursorCopy = QtGui.QTextCursor(editCursor)
            function(editCursorCopy)
            
            #Move to the next block
            if not editCursor.block().next().isValid():
                break #We reached the end of the document
            editCursor.movePosition(editCursor.NextBlock)
            
        editCursor.endEditBlock()
    
    def indentBlock(self,cursor,amount = 1):
        """
        Indent the block given by cursor
        The cursor specified is used to do the indentation; it is positioned
        at the beginning of the first non-whitespace position after completion
        May be overridden to customize indentation
        """
        text = cursor.block().text()
        leadingWhitespace = text[:len(text)-len(text.lstrip())]
        
        #Select the leading whitespace
        cursor.movePosition(cursor.StartOfBlock)
        cursor.movePosition(cursor.Right,cursor.KeepAnchor,len(leadingWhitespace))
        
        #Compute the new indentation length, expanding any existing tabs
        indent = len(leadingWhitespace.expandtabs(self.indentWidth()))
        if self.indentUsingSpaces():            
            # Determine correction, so we can round to multiples of indentation
            correction = indent % self.indentWidth()
            if correction and amount<0:
                correction = - (self.indentWidth() - correction) # Flip
            # Add the indentation tabs
            indent += (self.indentWidth() * amount) - correction
            cursor.insertText(' '*max(indent,0))
        else:
            # Convert indentation to number of tabs, and add one
            indent = (indent // self.indentWidth()) + amount
            cursor.insertText('\t' * max(indent,0))
            
    def dedentBlock(self,cursor):
        """
        Dedent the block given by cursor
        Calls indentBlock with amount = -1
        May be overridden to customize indentation
        """
        self.indentBlock(cursor, amount = -1)
        
    def indentSelection(self):
        """
        Called when the current line/selection is to be indented.
        Calls indentLine(cursor) for each line in the selection
        May be overridden to customize indentation
        
        See also doForSelectedBlocks and indentBlock
        """
        
        self.doForSelectedBlocks(self.indentBlock)
    def dedentSelection(self):
        """
        Called when the current line/selection is to be dedented.
        Calls dedentLine(cursor) for each line in the selection
        May be overridden to customize indentation
        
        See also doForSelectedBlocks and dedentBlock
        """
        
        self.doForSelectedBlocks(self.dedentBlock)
        
    def setStyle(self,style):
        #TODO: to be implemented
        pass

    



                

# Order of superclasses: first the extensions, then CodeEditorBase
# The first superclass is the first extension that gets to handle each key
# 
class CodeEditor(
    appearance.HighlightCurrentLine, 
    appearance.IndentationGuides, 
    appearance.LongLineIndicator, 
    appearance.ShowWhitespace,
    appearance.ShowLineEndings,
    appearance.Wrap,
    appearance.LineNumbers, 

    autocompletion.AutoCompletion, #Escape: first remove autocompletion,
    calltip.Calltip,               #then calltip
    
    behaviour.Indentation,
    behaviour.HomeKey,
    behaviour.EndKey,
    
    behaviour.PythonAutoIndent,
    
    CodeEditorBase):  #CodeEditorBase must be the last one in the list
    """
    CodeEditor with all the extensions
    """
    pass

        

if __name__=='__main__':
    app=QtGui.QApplication([])
    class TestEditor(CodeEditor):
        def keyPressEvent(self,event):
            key = event.key()
            if key == Qt.Key_F1:
                self.autocompleteShow()
                return
            elif key == Qt.Key_F2:
                self.autocompleteCancel()
                return
            elif key == Qt.Key_F3:
                self.calltipShow(0, 'test(foo, bar)')
                return
            elif key == Qt.Key_Backtab: #Shift + Tab
                self.dedentSelection()
                return
           
            super().keyPressEvent(event)
            
        
    e=TestEditor(highlightCurrentLine = True, longLineIndicatorPosition = 20,
        showIndentationGuides = True, showWhitespace = True, 
        showLineEndings = True, wrap = True, showLineNumbers = True)
    e.show()
    s=QtGui.QSplitter()
    s.addWidget(e)
    s.addWidget(QtGui.QLabel('test'))
    s.show()
    app.exec_()

