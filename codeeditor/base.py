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

from .misc import DEFAULT_OPTION_NAME, DEFAULT_OPTION_NONE, ce_option, ustr
from .highlighter import Highlighter
from .style import StyleFormat, StyleElementDescription


class CodeEditorBase(QtGui.QPlainTextEdit):
    """ The base code editor class. Implements some basic features required
    by the extensions.
    
    """
    
    def __init__(self,*args, **kwds):
        super(CodeEditorBase, self).__init__(*args)
        
        # Set font (always monospace)
        self.setFont()
        
        # Create highlighter class 
        self.__highlighter = Highlighter(self, self.document())
        
        # Set some document options
        option = self.document().defaultTextOption()
        option.setFlags(    option.flags() | option.IncludeTrailingSpaces |
                            option.AddSpaceForLineAndParagraphSeparators )
        self.document().setDefaultTextOption(option)
        
        # When the cursor position changes, invoke an update, so that
        # the hihghlighting etc will work
        self.cursorPositionChanged.connect(self.viewport().update) 
        
        # Init styles to default values
        self.__style = {}
        for element in self.getStyleElementDescriptions():
            self.__style[element.key] = element.defaultFormat
        
        # Init options now. 
        # NOTE TO PEOPLE DEVELOPING EXTENSIONS:
        # If an extension has an __init__ in which it first calls the 
        # super().__init__, this __initOptions() function will be called, 
        # while the extension's init is not yet finished.        
        self.__initOptions(kwds)
        
    
    
    ## Options
    
    def __getOptionSetters(self):
        """ Get a dict that maps (lowercase) option names to the setter
        methods.
        """
        
        # Get all names that can be options
        allNames = set(dir(self))
        nativeNames = set(dir(QtGui.QPlainTextEdit))
        names = allNames.difference(nativeNames)
        
        # Init dict of setter members
        setters = {}
        
        for name in names:
            # Get name without set
            if name.lower().startswith('set'):
                name = name[3:]
            # Get setter and getter name
            name_set = 'set' + name[0].upper() + name[1:]
            name_get = name[0].lower() + name[1:]
            # Check if both present
            if not (name_set in names and name_get in names):
                continue
            # Get members
            member_set = getattr(self, name_set)
            member_get = getattr(self, name_get)
            # Check if option decorator was used and get default value
            for member in [member_set, member_get]:
                if hasattr(member, DEFAULT_OPTION_NAME):
                    defaultValue = member.__dict__[DEFAULT_OPTION_NAME]
                    break
            else:
                continue
            # Set default on both
            member_set.__dict__[DEFAULT_OPTION_NAME] = defaultValue
            member_get.__dict__[DEFAULT_OPTION_NAME] = defaultValue
            # Add to list
            setters[name.lower()] = member_set
        
        # Done
        return setters
    
    
    def __setOptions(self, setters, options):
        """ Sets the options, given the list-of-tuples methods and an
        options dict.
        """
        
        # List of invalid keys
        invalidKeys = []
        
        # Set options
        for key1 in options:
            key2 = key1.lower()
            # Allow using the setter name
            if key2.startswith('set'):
                key2 = key2[3:]
            # Check if exists. If so, call!
            if key2 in setters:
                fun = setters[key2]
                val = options[key1]
                fun(val)
            else:
                invalidKeys.append(key1)
        
        # Check if invalid keys were given
        if invalidKeys:
            print("Warning, invalid options given: " + ', '.join(invalidKeys))
    
    
    def __initOptions(self, options=None):
        """ Init the options with their default values.
        Also applies the docstrings of one to the other.
        """
        
        # Make options an empty dict if not given
        if not options:
            options = {}
        
        # Get setters
        setters = self.__getOptionSetters()
        
        # Set default value
        for member_set in setters.values():
            defaultVal = member_set.__dict__[DEFAULT_OPTION_NAME]
            if defaultVal != DEFAULT_OPTION_NONE:
                member_set(defaultVal)
        
        # Also set using given opions?
        if options:
            self.__setOptions(setters, options)
    
    
    def setOptions(self, options=None, **kwargs):
        """ setOptions(options=None, **kwargs)
        
        Set the code editor options (e.g. highlightCurrentLine) using
        a dict-like object, or using keyword arguments (options given
        in the latter overrule opions in the first).
        
        The keys in the dict are case insensitive and one can use the
        option's setter or getter name.
        
        """
        
        # Process options
        if options:
            D = {}            
            for key in options:
                D[key] = options[key]
            D.update(kwargs)
        else:
            D = kwargs
        
        # Get setters
        setters = self.__getOptionSetters()
        
        # Go
        self.__setOptions(setters, D)
    
    
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
    
    
    @classmethod
    def getStyleElementDescriptions(cls):
        """ getStyleElementDescriptions()
        
        This classmethod returns a list of StyleElementDescription instances. 
        
        """ 
        
        # Collect members by walking the class bases
        elements = []
        def collectElements(cls, iter=1):
            # Valid class?
            if cls is object or cls is QtGui.QPlainTextEdit:
                return
            # Check members
            if hasattr(cls, '_styleElements'):
                for element in cls._styleElements:
                    elements.append(element)
            # Recurse
            for c in cls.__bases__:
                collectElements(c, iter+1)
        collectElements(cls)
        
        # Make style element descriptions
        # (Use a dict to ensure there are no duplicate keys)
        elements2 = {}
        for element in elements:
            # Check
            if isinstance(element, StyleElementDescription):
                pass
            elif isinstance(element, tuple):
                element = StyleElementDescription(*element)
            else:
                print('Warning: invalid element: ' + repr(element))
            # Store using the name as a key to prevent duplicates
            elements2[element.key] = element
        
        # Done
        return elements2.values()
    
    
    def getStyleElementFormat(self, name):
        """ getStyleElementFormat(name)
        
        Get the style format for the style element corresponding with
        the given name. The name is case insensitive and invariant to
        the use of spaces.
        
        """
        key = name.replace(' ','').lower()
        try:
            return self.__style[key]
        except KeyError:
            raise KeyError('Not a known style element name: "%s".' % name)
    
    # todo: set style on instance or on class?
    def setStyle(self, style=None, **kwargs):
        """ setStyle(style)
        
        Set the formatting per style element.
        
        The style consists of a dictionary that maps style names to
        style formats. The style names are case insensitive and invariant 
        to the use of spaces.
        
        For convenience, keyword arguments may also be used. In this case,
        underscores are interpreted as dots.
        
        Use getStyleElementDescriptions() to get information about the
        available styles and their default values.
        
        """
        
        # Combine user input
        D = {}
        if style:
            for key in style:
                D[key] = style[key]
        if True:
            for key in kwargs:
                key2 = key.replace('_', '.')
                D[key2] = kwargs[key]
        
        # List of given invalid style element names
        invalidKeys = []
        
        # Set style elements
        for key in D:
            normKey = key.replace(' ', '').lower()
            if normKey in self.__style:
                self.__style[normKey] = StyleFormat(D[key])
            else:
                invalidKeys.append(key)
        
        # Give warning for invalid keys
        if invalidKeys:
            print("Warning, invalid style names given: " + ', '.join(invalidKeys))
        
        # Make sure the style is applied
        self.viewport().update()
    
    
    ## Some basic options
    
    
    @ce_option(4)
    def indentWidth(self):
        """ Get the width of a tab character, and also the amount of spaces
        to use for indentation when indentUsingSpaces() is True.
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
        """Get whether to use spaces (if True) or tabs (if False) to indent
        when the tab key is pressed
        """
        return self.__indentUsingSpaces
    
    def setIndentUsingSpaces(self, value):
        self.__indentUsingSpaces = bool(value)
        self.__highlighter.rehighlight()
 
    
    ## Misc
        
    def gotoLine(self, lineNumber):
        """ gotoLine(lineNumber)
        
        Move the cursor to the block given by the line number 
        (first line is line number 1) and show that line.
        
        """
        cursor = self.textCursor()
        block = self.document().findBlockByNumber( lineNumber + 1)
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
    
        
    def doForSelectedBlocks(self, function):
        """ doForSelectedBlocks(function)
        
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
    
    
    def indentBlock(self, cursor, amount=1):
        """ indentBlock(cursor, amount=1)
        
        Indent the block given by cursor.
        
        The cursor specified is used to do the indentation; it is positioned
        at the beginning of the first non-whitespace position after completion
        May be overridden to customize indentation.
        
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
    
    
    def dedentBlock(self, cursor):
        """ dedentBlock(cursor)
        
        Dedent the block given by cursor.
        
        Calls indentBlock with amount = -1.
        May be overridden to customize indentation.
        
        """
        self.indentBlock(cursor, amount = -1)
    
    
    def indentSelection(self):
        """ indentSelection()
        
        Called when the current line/selection is to be indented.
        Calls indentLine(cursor) for each line in the selection.
        May be overridden to customize indentation.
        
        See also doForSelectedBlocks and indentBlock.
        
        """
        self.doForSelectedBlocks(self.indentBlock)
    
    
    def dedentSelection(self):
        """ dedentSelection()
        
        Called when the current line/selection is to be dedented.
        Calls dedentLine(cursor) for each line in the selection.
        May be overridden to customize indentation.
        
        See also doForSelectedBlocks and dedentBlock.
        
        """
        self.doForSelectedBlocks(self.dedentBlock)
    

