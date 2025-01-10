"""Module highlighter

Defines the highlighter class for the base code editor class. It will do
the styling when syntax highlighting is enabled. If it is not, will only
check out indentation.

"""

from .qt import QtGui, QtCore

Qt = QtCore.Qt

from . import parsers


class BlockData(QtGui.QTextBlockUserData):
    """Class to represent the data for a block."""

    def __init__(self):
        super().__init__()
        self.indentation = None
        self.fullUnderlineFormat = None
        self.tokens = []


# The highlighter should be part of the base class, because
# some extensions rely on them (e.g. the indent guides).
class Highlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, codeEditor, *args):
        super().__init__(*args)

        # Store reference to editor
        self._codeEditor = codeEditor

    def getCurrentBlockUserData(self):
        """Gets the BlockData object. Creates one if necesary."""
        bd = self.currentBlockUserData()
        if not isinstance(bd, BlockData):
            bd = BlockData()
            self.setCurrentBlockUserData(bd)
        return bd

    def highlightBlock(self, line):
        """This method is automatically called when a line must be re-highlighted.

        If the code editor has an active parser. This method will use
        it to perform syntax highlighting. If not, it will only
        check out the indentation.
        """

        # Get previous state
        previousState = self.previousBlockState()

        # Get parser
        parser = None
        if hasattr(self._codeEditor, "parser"):
            parser = self._codeEditor.parser()

        # Get function to get format
        nameToFormat = self._codeEditor.getStyleElementFormat

        fullLineFormat = None
        tokens = []
        if parser:
            self.setCurrentBlockState(0)
            tokens = parser.parseLine(line, previousState)
            for token in tokens:
                # Handle block state
                if isinstance(token, parsers.BlockState):
                    self.setCurrentBlockState(token.state)
                else:
                    # Get format
                    try:
                        styleFormat = nameToFormat(token.name)
                        charFormat = styleFormat.textCharFormat
                    except KeyError:
                        # print(repr(nameToFormat(token.name)))
                        continue
                    # Set format
                    self.setFormat(token.start, token.end - token.start, charFormat)
                    # Is this a cell?
                    if (fullLineFormat is None) and styleFormat._parts.get(
                        "underline", ""
                    ) == "full":
                        fullLineFormat = styleFormat

        # Get user data
        bd = self.getCurrentBlockUserData()

        # Store token list for future use (e.g. brace matching)
        bd.tokens = tokens

        # Handle underlines
        bd.fullUnderlineFormat = fullLineFormat

        # Get the indentation setting of the editors
        indentUsingSpaces = self._codeEditor.indentUsingSpaces()

        leadingWhitespace = line[: len(line) - len(line.lstrip())]
        US = QtGui.QTextCharFormat.UnderlineStyle
        if "\t" in leadingWhitespace and " " in leadingWhitespace:
            # Mixed whitespace
            bd.indentation = 0
            format = QtGui.QTextCharFormat()
            format.setUnderlineStyle(US.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.GlobalColor.red)
            format.setToolTip("Mixed tabs and spaces")
            self.setFormat(0, len(leadingWhitespace), format)
        elif ("\t" in leadingWhitespace and indentUsingSpaces) or (
            " " in leadingWhitespace and not indentUsingSpaces
        ):
            # Whitespace differs from document setting
            bd.indentation = 0
            format = QtGui.QTextCharFormat()
            format.setUnderlineStyle(US.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.GlobalColor.blue)
            format.setToolTip("Whitespace differs from document setting")
            self.setFormat(0, len(leadingWhitespace), format)
        else:
            # Store info for indentation guides
            # amount of tabs or spaces
            bd.indentation = len(leadingWhitespace)
