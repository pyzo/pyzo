"""
The base code editor class.


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

if __name__ == '__main__':
    from misc import DEFAULT_OPTION_NAME, DEFAULT_OPTION_NONE, ce_option, ustr
    from highlighter import Highlighter
    from extensions import appearance
    from extensions import appearance
    from extensions import autocompletion
    from extensions import behaviour
    from extensions import calltip
else:
    from .misc import DEFAULT_OPTION_NAME, DEFAULT_OPTION_NONE, ce_option, ustr
    from .highlighter import Highlighter
    from .extensions import appearance
    from .extensions import autocompletion
    from .extensions import behaviour
    from .extensions import calltip


class CodeEditorBase(QtGui.QPlainTextEdit):
    def __init__(self,*args, **kwds):
        super(CodeEditorBase, self).__init__(*args)
        
        # Set font (always monospace)
        self.setFont()
        
        # Create highlighter class 
        # (no double spaces, as we may need to acces it from other extensions)
        self.__highlighter = Highlighter(self, self.document())
        
        #Default options
        option = self.document().defaultTextOption()
        option.setFlags(    option.flags() | option.IncludeTrailingSpaces |
                            option.AddSpaceForLineAndParagraphSeparators )
        self.document().setDefaultTextOption(option)
        
        # When the cursor position changes, invoke an update, so that
        # the hihghlighting etc will work
        self.cursorPositionChanged.connect(self.viewport().update) 
        
        # Init options now
        self.__initOptions(kwds)
    
    
    def __getOptionMethods(self):
        """ Get a list of methods that are options. Each element in the
        returned list is a two-element tuple with the setter and getter
        method.
        """
        
        # Collect members by walking the class bases
        members = []
        def collectMembers(cls, iter=1):
            # Valid class?
            if cls is object or cls is QtGui.QPlainTextEdit:
                return
            # Check members
            for member in cls.__dict__.values():
                if hasattr(member, DEFAULT_OPTION_NAME):
                    members.append((cls, member))
            # Recurse
            for c in cls.__bases__:
                collectMembers(c, iter+1)
        collectMembers(self.__class__)
        
        # Check if setter and getter are present 
        methods = []
        for cls, member in members:
            # Get name without set
            name = member.__name__
            if name.lower().startswith('set'):
                name = name[3:]
            # Get setter and getter name
            name_set = 'set' + name[0].upper() + name[1:]
            name_get = name[0].lower() + name[1:]
            # Check if exists
            D = cls.__dict__
            if not (name_set in D and name_get in D):
                continue
            # Get members and set default on both
            member_set, member_get = D[name_set], D[name_get]
            defaultValue = member.__dict__[DEFAULT_OPTION_NAME]
            member_set.__dict__[DEFAULT_OPTION_NAME] = defaultValue
            member_get.__dict__[DEFAULT_OPTION_NAME] = defaultValue
            # Add to list
            methods.append((member_set, member_get))
        
        # Done
        return methods
    
    
    def __setOptions(self, methods, options):
        """ Sets the options, given the list-of-tuples methods and an
        options dict.
        """
        for member_set, member_get in methods:
            
            # Determine whether the value was given in options
            valueIsGiven = False
            valToSet = None
            if member_set.__name__ in options:
                valToSet = options[member_set.__name__]
                valueIsGiven = True
            elif member_get.__name__ in options:
                valToSet = options[member_get.__name__]
                valueIsGiven = True
            
            # Use given value
            if valueIsGiven:
                member_set(self, valToSet)
    
    
    def __initOptions(self, options=None):
        """ Init the options with their default values.
        Also applies the docstrings of one to the other.
        """
        
        # Make options an empty dict if not given
        if not options:
            options = {}
        
        # Get methods
        methods = self.__getOptionMethods()
        
        
        for member_set, member_get in methods:
            
            # Correct docstring if we can and should
            if member_set.__doc__ and not member_get.__doc__:
                doc = member_set.__doc__
                doc = doc.replace('set', 'get').replace('Set', 'Get')
                member_get.__doc__ = doc
            elif member_get.__doc__ and not member_set.__doc__:
                doc = member_get.__doc__
                doc = doc.replace('get', 'set').replace('Get', 'Set')
                member_set.__doc__ = doc
            
            # Set default value
            defaultVal = member_set.__dict__[DEFAULT_OPTION_NAME]
            if defaultVal != DEFAULT_OPTION_NONE:
                member_set(self, defaultVal)
        
        # Also set using given opions?
        if options:
            self.__setOptions(methods, options)
    
    
    def setOptions(self, options=None, **kwargs):
        """ setOptions(options=None, **kwargs)
        
        Set the code editor options (e.g. highlightCurrentLine) using
        a dict-like object, or using keyword arguments (options given
        in the latter overrule opions in the first).
        
        """
        
        # Process options
        if options:
            D = {}            
            for key in options:
                D[key] = options[key]
            D.update(kwargs)
        else:
            D = kwargs
        
        # Get methods
        methods = self.__getOptionMethods()
        
        # Go
        self.__setOptions(methods, D)
    
    
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
    
    
    ## Syntax / styling
    
    # todo: registerStyleElement, or register to class using decorators?
    def registerStyleElement(self, styleElementDescription):
        pass
    
    
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
    
    
    @ce_option(4)
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
    
    
    @ce_option(False)
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
        text = ustr(cursor.block().text())
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
           
            super(TestEditor, self).keyPressEvent(event)
    
    e=TestEditor(highlightCurrentLine = True, longLineIndicatorPosition = 20,
        showIndentationGuides = True, showWhitespace = True, 
        showLineEndings = True, wrap = True, showLineNumbers = True)
    e.show()
    s=QtGui.QSplitter()
    s.addWidget(e)
    s.addWidget(QtGui.QLabel('test'))
    s.show()
    app.exec_()

