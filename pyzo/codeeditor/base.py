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

class FancyEditor(Extension1, Extension2, ... CodeEditorBase):
    pass

The order of the extensions does usually matter! If multiple Extensions process
the same key press, the first one has the first chance to consume it.

OVERRIDING __init__

An extensions' __init__ method (if required) should look like this:
class Extension:
    def __init__(self, *args, extensionParam1=1, extensionParam2=3, **kwds):
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
 - Private members should start with __ to make sure no clashes will occur
 - Public members / methods should have names that clearly indicate which
   extension they belong to (e.g. not cancel but autocompleteCancel)
 - Arguments of the __init__ method should also have clearly destinctive names

"""

from .qt import QtGui, QtCore, QtWidgets

Qt = QtCore.Qt

from .misc import DEFAULT_OPTION_NAME, DEFAULT_OPTION_NONE, ce_option
from .misc import callLater
from .manager import Manager
from .highlighter import Highlighter
from .style import StyleElementDescription


class CodeEditorBase(QtWidgets.QPlainTextEdit):
    """The base code editor class. Implements some basic features required
    by the extensions.

    """

    # Style element for default text and editor background
    _styleElements = [
        (
            "Editor.text",
            "The style of the default text. "
            + "One can set the background color here.",
            "fore:#000,back:#fff",
        )
    ]

    # Signal emitted after style has changed
    styleChanged = QtCore.Signal()

    # Signal emitted after font (or font size) has changed
    fontChanged = QtCore.Signal()

    # Signal to indicate a change in breakpoints. Only emitted if the
    # appropriate extension is in use
    breakPointsChanged = QtCore.Signal(object)

    def __init__(self, *args, **kwds):
        super().__init__(*args)

        # Set font (always monospace)
        self.__zoom = 0
        self.setFont()

        # Create highlighter class
        self.__highlighter = Highlighter(self, self.document())

        # Set some document options
        # Setting this option breaks the showWhitespace and showLineEndings options in PySyde6.4
        option = QtGui.QTextOption()  # self.document().defaultTextOption()
        # option.setFlags(
        #     option.flags()
        #     | option.Flag.IncludeTrailingSpaces
        #     | option.Flag.AddSpaceForLineAndParagraphSeparators
        # )
        self.document().setDefaultTextOption(option)

        # When the cursor position changes, invoke an update, so that
        # the highlighting etc will work
        self.cursorPositionChanged.connect(self.viewport().update)

        # Init styles to default values
        self.__style = {
            element.key: element.defaultFormat
            for element in self.getStyleElementDescriptions()
        }

        # Connext style update
        self.styleChanged.connect(self.__afterSetStyle)
        self.__styleChangedPending = False

        # Init margins
        self._leftmargins = []

        # Init options now.
        # NOTE TO PEOPLE DEVELOPING EXTENSIONS:
        # If an extension has an __init__ in which it first calls the
        # super().__init__, this __initOptions() function will be called,
        # while the extension's init is not yet finished.
        self.__initOptions(kwds)

        # Define colors from Solarized theme
        base03 = "#002b36"
        base02 = "#073642"
        base01 = "#586e75"
        base00 = "#657b83"
        base0 = "#839496"
        base1 = "#93a1a1"
        base2 = "#eee8d5"
        base3 = "#fdf6e3"
        yellow = "#b58900"
        orange = "#cb4b16"
        red = "#dc322f"  # noqa
        magenta = "#d33682"
        violet = "#6c71c4"
        blue = "#268bd2"
        cyan = "#2aa198"
        green = "#859900"  # noqa

        if True:  # Light vs dark
            # back1, back2, back3 = base3, base2, base1 # real solarised
            back1, back2, back3 = "#fff", base2, base1  # crispier
            fore1, fore2, fore3, fore4 = base00, base01, base02, base03
        else:
            back1, back2, back3 = base03, base02, base01
            fore1, fore2, fore3, fore4 = base0, base1, base2, base3  # noqa

        # Define style using "Solarized" colors
        S = {}
        S["Editor.text"] = "back:{}, fore:{}".format(back1, fore1)
        S["Syntax.identifier"] = "fore:{}, bold:no, italic:no, underline:no".format(
            fore1
        )
        S["Syntax.nonidentifier"] = "fore:{}, bold:no, italic:no, underline:no".format(
            fore2
        )
        S["Syntax.keyword"] = "fore:{}, bold:yes, italic:no, underline:no".format(fore2)

        S["Syntax.builtins"] = "fore:{}, bold:no, italic:no, underline:no".format(fore1)
        S["Syntax.instance"] = "fore:{}, bold:no, italic:no, underline:no".format(fore1)

        S["Syntax.functionname"] = "fore:{}, bold:yes, italic:no, underline:no".format(
            fore3
        )
        S["Syntax.classname"] = "fore:{}, bold:yes, italic:no, underline:no".format(
            orange
        )

        S["Syntax.string"] = "fore:{}, bold:no, italic:no, underline:no".format(violet)
        S["Syntax.unterminatedstring"] = (
            "fore:{}, bold:no, italic:no, underline:dotted".format(violet)
        )
        S["Syntax.python.multilinestring"] = (
            "fore:{}, bold:no, italic:no, underline:no".format(blue)
        )

        S["Syntax.number"] = "fore:{}, bold:no, italic:no, underline:no".format(cyan)
        S["Syntax.comment"] = "fore:{}, bold:no, italic:no, underline:no".format(yellow)
        S["Syntax.todocomment"] = "fore:{}, bold:no, italic:yes, underline:no".format(
            magenta
        )
        S["Syntax.python.cellcomment"] = (
            "fore:{}, bold:yes, italic:no, underline:full".format(yellow)
        )

        S["Editor.Long line indicator"] = "linestyle:solid, fore:{}".format(back2)
        S["Editor.Highlight current line"] = "back:{}".format(back2)
        S["Editor.Indentation guides"] = "linestyle:solid, fore:{}".format(back2)
        S["Editor.Line numbers"] = "back:{}, fore:{}".format(back2, back3)

        # Apply a good default style
        self.setStyle(S)

    # see https://bugreports.qt.io/browse/QTBUG-57552?focusedCommentId=469402&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-469402
    # and https://code.qt.io/cgit/qt/qtbase.git/tree/src/gui/text/qtextdocument.cpp#n1183
    # and https://doc.qt.io/qt-5/qchar.html
    _plainTextTrans = str.maketrans(
        {"\u2029": "\n", "\u2028": "\n", "\ufdd0": "\n", "\ufdd1": "\n"}
    )

    def toPlainText(self):
        cursor = self.textCursor()
        cursor.select(QtGui.QTextCursor.SelectionType.Document)
        return cursor.selectedText().translate(self._plainTextTrans)

    def _setHighlighter(self, highlighterClass):
        # PySide 2 and 6 do not remove the previous highlighter automatically
        self.__highlighter.setDocument(None)

        self.__highlighter = highlighterClass(self, self.document())

    ## Options

    def __getOptionSetters(self):
        """Get a dict that maps (lowercase) option names to the setter
        methods.
        """

        # Get all names that can be options
        allNames = set(dir(self))
        nativeNames = set(dir(QtWidgets.QPlainTextEdit))
        names = allNames.difference(nativeNames)

        # Init dict of setter members
        setters = {}

        for name in names:
            # Get name without set
            if name.lower().startswith("set"):
                name = name[3:]
            # Get setter and getter name
            name_set = "set" + name[0].upper() + name[1:]
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
        """Sets the options, given the list-of-tuples methods and an
        options dict.
        """

        # List of invalid keys
        invalidKeys = []

        # Set options
        for key1 in options:
            key2 = key1.lower()
            # Allow using the setter name
            if key2.startswith("set"):
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
            print("Warning, invalid options given: " + ", ".join(invalidKeys))

    def __initOptions(self, options=None):
        """Init the options with their default values.
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
                try:
                    member_set(defaultVal)
                except Exception:
                    print("Error initing option ", member_set.__name__)

        # Also set using given opions?
        if options:
            self.__setOptions(setters, options)

    def setOptions(self, options=None, **kwargs):
        """Set the code editor options (e.g. highlightCurrentLine) using
        a dict-like object, or using keyword arguments (options given
        in the latter overrule opions in the first).

        The keys in the dict are case insensitive and one can use the
        option's setter or getter name.
        """

        # Process options
        if options:
            D = dict(options)
            D.update(kwargs)
        else:
            D = kwargs

        # Get setters
        setters = self.__getOptionSetters()

        # Go
        self.__setOptions(setters, D)

    ## Font

    def setFont(self, font=None):
        """Set the font for the editor. Should be a monospace font.

        If not, Qt will select the best matching monospace font.
        """

        defaultFont = Manager.defaultFont()

        # Get font object
        if font is None:
            font = defaultFont
        elif isinstance(font, QtGui.QFont):
            pass
        elif isinstance(font, str):
            font = QtGui.QFont(font)
        else:
            raise ValueError("setFont accepts None, QFont or string.")

        # Hint Qt that it should be monospace
        font.setStyleHint(font.StyleHint.TypeWriter, font.StyleStrategy.PreferDefault)

        # Get family, fall back to default if qt could not produce monospace
        fontInfo = QtGui.QFontInfo(font)
        if fontInfo.fixedPitch():
            family = fontInfo.family()
        else:
            family = defaultFont.family()

        # Get size: default size + zoom
        size = defaultFont.pointSize() + self.__zoom

        # Create font instance
        font = QtGui.QFont(family, size)

        # Set, emit and return
        super().setFont(font)
        self.fontChanged.emit()
        return font

    def setZoom(self, zoom):
        """Set the zooming of the document. The font size is always the default
        font size + the zoom factor.

        The final zoom is returned, this may not be the same as the given
        zoom factor if the given factor is too small.
        """
        # Set zoom (limit such that final pointSize >= 1)
        size = Manager.defaultFont().pointSize()
        self.__zoom = int(max(1 - size, zoom))
        # Set font
        self.setFont(self.fontInfo().family())
        # Return zoom
        return self.__zoom

    ## Syntax / styling

    @classmethod
    def getStyleElementDescriptions(cls):
        """Returns a list of the StyleElementDescription
        instances used by this class.

        This includes the descriptions for the syntax highlighting of all parsers.
        """

        # Collect members by walking the class bases
        elements = []

        def collectElements(cls, iter=1):
            # Valid class?
            if cls is object or cls is QtWidgets.QPlainTextEdit:
                return
            # Check members
            if hasattr(cls, "_styleElements"):
                for element in cls._styleElements:
                    elements.append(element)
            # Recurse
            for c in cls.__bases__:
                collectElements(c, iter + 1)

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
                print("Warning: invalid element: " + repr(element))
            # Store using the name as a key to prevent duplicates
            elements2[element.key] = element

        # Done
        return list(elements2.values())

    def getStyleElementFormat(self, name):
        """Get the style format for the style element corresponding with
        the given name. The name is case insensitive and invariant to
        the use of spaces.
        """
        key = name.replace(" ", "").lower()
        try:
            return self.__style[key]
        except KeyError:
            raise KeyError('Not a known style element name: "{}".'.format(name))

    def setStyle(self, style=None, **kwargs):
        """Updates the formatting per style element.

        The style consists of a dictionary that maps style names to
        style formats. The style names are case insensitive and invariant
        to the use of spaces.

        For convenience, keyword arguments may also be used. In this case,
        underscores are interpreted as dots.

        This function can also be called without arguments to force the
        editor to restyle (and rehighlight) itself.

        Use getStyleElementDescriptions() to get information about the
        available styles and their default values.

        Examples
        --------
        # To make the classname in underline, but keep the color and boldness:
        setStyle(syntax_classname='underline')
        # To set all values for function names:
        setStyle(syntax_functionname='#883,bold:no,italic:no')
        # To set line number and indent guides colors
        setStyle({  'editor.LineNumbers':'fore:#000,back:#777',
                    'editor.indentationGuides':'#f88' })
        """

        # Combine user input
        D = {}
        if style:
            D = dict(style)
        if True:
            for key in kwargs:
                D[key.replace("_", ".")] = kwargs[key]

        # List of given invalid style element names
        invalidKeys = []

        # Set style elements
        for key in D:
            normKey = key.replace(" ", "").lower()
            if normKey in self.__style:
                # self.__style[normKey] = StyleFormat(D[key])
                self.__style[normKey].update(D[key])
            else:
                invalidKeys.append(key)

        # Give warning for invalid keys
        if invalidKeys:
            print("Warning, invalid style names given: " + ",".join(invalidKeys))

        # Notify that style changed, adopt a lazy approach to make loading
        # quicker.
        if self.isVisible():
            callLater(self.styleChanged.emit)
            self.__styleChangedPending = False
        else:
            self.__styleChangedPending = True

    def showEvent(self, event):
        super().showEvent(event)
        # Does the style need updating?
        if self.__styleChangedPending:
            callLater(self.styleChanged.emit)
            self.__styleChangedPending = False

    def __afterSetStyle(self):
        """Method to call after the style has been set."""

        # Set text style using editor style sheet
        format = self.getStyleElementFormat("editor.text")
        ss = "QPlainTextEdit{{ color:{}; background-color:{}; }}".format(
            format["fore"],
            format["back"],
        )
        self.setStyleSheet(ss)

        # Make sure the style is applied
        self.viewport().update()

        # Re-highlight
        callLater(self.__highlighter.rehighlight)

    ## Some basic options

    @ce_option(4)
    def indentWidth(self):
        """Get the width of a tab character, and also the amount of spaces
        to use for indentation when indentUsingSpaces() is True.
        """
        return self.__indentWidth

    def setIndentWidth(self, value):
        value = int(value)
        if value <= 0:
            raise ValueError("indentWidth must be >0")
        self.__indentWidth = value
        self.setTabStopDistance(
            self.fontMetrics().horizontalAdvance("i" * self.__indentWidth)
        )

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

    def gotoLine(self, lineNumber, keepHorizontalPos=False):
        """Move the cursor to the (beginning of the) block given by the line number
        (first line is number 1) and show that line.

        Optionally, the horizontal position of the cursor can be kept.
        """
        return self.gotoBlock(lineNumber - 1, keepHorizontalPos)

    def gotoBlock(self, blockNumber, keepHorizontalPos=False):
        """Move the cursor to the (beginning of the) block given by the block number
        (first block is number 0) and show that line.

        Optionally, the horizontal position of the cursor can be kept.
        """
        cursor = self.textCursor()
        if keepHorizontalPos:
            hPos = cursor.verticalMovementX()

        # Two implementatios. I know that the latter works, so lets
        # just use that.

        # block = self.document().findBlockByNumber( blockNumber )
        # cursor.setPosition(block.position())
        cursor.movePosition(cursor.MoveOperation.Start)  # move to begin of the document
        cursor.movePosition(
            cursor.MoveOperation.NextBlock, n=blockNumber
        )  # n blocks down

        if keepHorizontalPos:
            if cursor.movePosition(cursor.MoveOperation.Up):
                backToRow = cursor.MoveOperation.Down
            else:
                cursor.movePosition(cursor.MoveOperation.Down)
                backToRow = cursor.MoveOperation.Up
            cursor.setVerticalMovementX(hPos)
            cursor.movePosition(backToRow)

        try:
            self.setTextCursor(cursor)
        except Exception:
            pass  # File is smaller then the caller thought

        # TODO make this user configurable (setting relativeMargin to anything above
        # 0.5 will cause cursor to center on each move)
        relativeMargin = 0.2  # 20% margin on both sides of the window
        margin = self.height() * relativeMargin
        cursorRect = self.cursorRect(cursor)
        if cursorRect.top() < margin or cursorRect.bottom() + margin > self.height():
            self.centerCursor()

    def doForSelectedBlocks(self, function):
        """Call the given function(cursor) for all blocks in the current selection
        A block is considered to be in the current selection if a part of it is in
        the current selection

        The supplied cursor will be located at the beginning of each block. This
        cursor may be modified by the function as required
        """

        # Note: a 'TextCursor' does not represent the actual on-screen cursor, so
        # movements do not move the on-screen cursor

        # Note 2: when the text is changed, the cursor and selection start/end
        # positions of all cursors are updated accordingly, so the screenCursor
        # stays in place even if characters are inserted at the editCursor

        screenCursor = self.textCursor()  # For maintaining which region is selected
        editCursor = self.textCursor()  # For inserting the comment marks

        # Use beginEditBlock / endEditBlock to make this one undo/redo operation
        editCursor.beginEditBlock()

        try:
            editCursor.setPosition(screenCursor.selectionStart())
            editCursor.movePosition(editCursor.MoveOperation.StartOfBlock)
            # < :if selection end is at beginning of the block, don't include that
            # one, except when the selectionStart is same as selectionEnd
            while (
                editCursor.position() < screenCursor.selectionEnd()
                or editCursor.position() <= screenCursor.selectionStart()
            ):
                # Create a copy of the editCursor and call the user-supplied function
                editCursorCopy = QtGui.QTextCursor(editCursor)
                function(editCursorCopy)

                # Move to the next block
                if not editCursor.block().next().isValid():
                    break  # We reached the end of the document
                editCursor.movePosition(editCursor.MoveOperation.NextBlock)
        finally:
            editCursor.endEditBlock()

    def doForVisibleBlocks(self, function):
        """Call the given function(cursor) for all blocks that are currently
        visible. This is used by several appearence extensions that
        paint per block.

        The supplied cursor will be located at the beginning of each block. This
        cursor may be modified by the function as required
        """

        # Start cursor at top line.
        cursor = self.cursorForPosition(QtCore.QPoint(0, 0))
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)

        if not self.isVisible():
            return

        while True:
            # Call the function with a copy of the cursor
            function(QtGui.QTextCursor(cursor))

            # Go to the next block (or not if we are done)
            y = self.cursorRect(cursor).bottom()
            if y > self.height():
                break  # Reached end of the repaint area
            if not cursor.block().next().isValid():
                break  # Reached end of the text
            cursor.movePosition(cursor.MoveOperation.NextBlock)

    def indentBlock(self, cursor, amount=1):
        """Indent the block given by cursor.

        The cursor specified is used to do the indentation; it is positioned
        at the beginning of the first non-whitespace position after completion
        May be overridden to customize indentation.
        """
        text = cursor.block().text()
        leadingWhitespace = text[: len(text) - len(text.lstrip())]

        # Select the leading whitespace
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)
        cursor.movePosition(
            cursor.MoveOperation.Right,
            cursor.MoveMode.KeepAnchor,
            len(leadingWhitespace),
        )

        # Compute the new indentation length, expanding any existing tabs
        indent = len(leadingWhitespace.expandtabs(self.indentWidth()))
        if self.indentUsingSpaces():
            # Determine correction, so we can round to multiples of indentation
            correction = indent % self.indentWidth()
            if correction and amount < 0:
                correction = -(self.indentWidth() - correction)  # Flip
            # Add the indentation tabs
            indent += (self.indentWidth() * amount) - correction
            cursor.insertText(" " * max(indent, 0))
        else:
            # Convert indentation to number of tabs, and add one
            indent = (indent // self.indentWidth()) + amount
            cursor.insertText("\t" * max(indent, 0))

    def dedentBlock(self, cursor):
        """Dedent the block given by cursor.

        Calls indentBlock with amount = -1.
        May be overridden to customize indentation.
        """
        self.indentBlock(cursor, amount=-1)

    def indentSelection(self):
        """Called when the current line/selection is to be indented.
        Calls indentLine(cursor) for each line in the selection.
        May be overridden to customize indentation.

        See also doForSelectedBlocks and indentBlock.
        """
        self.doForSelectedBlocks(self.indentBlock)

    def dedentSelection(self):
        """Called when the current line/selection is to be dedented.
        Calls dedentLine(cursor) for each line in the selection.
        May be overridden to customize indentation.

        See also doForSelectedBlocks and dedentBlock.
        """
        self.doForSelectedBlocks(self.dedentBlock)

    def justifyText(self, linewidth=70):
        from .textutils import TextReshaper

        # Get cursor
        cursor = self.textCursor()

        # Make selection include whole lines
        pos1, pos2 = cursor.position(), cursor.anchor()
        if pos2 < pos1:
            pos1, pos2 = pos2, pos1
        cursor.setPosition(pos1, cursor.MoveMode.MoveAnchor)
        cursor.movePosition(
            cursor.MoveOperation.StartOfBlock, cursor.MoveMode.MoveAnchor
        )
        cursor.setPosition(pos2, cursor.MoveMode.KeepAnchor)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)

        # Use reshaper to create replacement text
        reshaper = TextReshaper(linewidth)
        reshaper.pushText(cursor.selectedText())
        newText = reshaper.popText()

        # Update the selection
        # self.setTextCursor(cursor) for testing
        cursor.insertText(newText)

    def _getMarginBeforeLeftBar(self, handle):
        """gets the width of all bars before the bar specified by handle

        to be used by extensions; see also _setLeftBarMargin
        """
        return sum(self._leftmargins[:handle])

    def _setLeftBarMargin(self, handle, width):
        """sets the margin on the left needed by extensions and updates the viewport

        In the first call from the extension, pass handle=None and
        remember the returned handle.
        For each update of the bar width, pass that handle.

        returns the handle resp. the new handle if handle was None
        """
        if handle is None:
            handle = len(self._leftmargins)
            self._leftmargins.append(0)
        self._leftmargins[handle] = width

        leftmargin = sum(self._leftmargins)
        self.setViewportMargins(leftmargin, 0, 0, 0)
        return handle

    def toggleCase(self):
        """Change selected text to lower or upper case."""

        # Get cursor
        cursor = self.textCursor()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()

        # Get selected text
        selection = cursor.selectedText()

        if selection.islower():
            newText = selection.upper()
        elif selection.isupper():
            newText = selection.lower()
        else:
            newText = selection.lower()

        # Update the selection
        cursor.insertText(newText)
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QtGui.QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)
