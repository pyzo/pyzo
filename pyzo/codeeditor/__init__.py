"""CodeEditor

A full featured code editor component based on QPlainTextEdit.

"""

# ruff: noqa: F401

from .manager import Manager
from .base import CodeEditorBase

from .extensions.appearance import (
    HighlightMatchingBracket,
    HighlightMatchingOccurrences,
    HighlightCurrentLine,
    FullUnderlines,
    IndentationGuides,
    CodeFolding,
    LongLineIndicator,
    ShowWhitespace,
    ShowLineEndings,
    Wrap,
    LineNumbers,
    SyntaxHighlighting,
    BreakPoints,
)
from .extensions.behaviour import (
    Indentation,
    HomeKey,
    EndKey,
    NumpadPeriodKey,
    AutoIndent,
    PythonAutoIndent,
    SmartCopyAndPaste,
    MoveLinesUpDown,
    ScrollWithUpDownKeys,
    AutoCloseQuotesAndBrackets,
)
from .extensions.autocompletion import AutoCompletion
from .extensions.calltip import Calltip


# Order of superclasses: first the extensions, then CodeEditorBase
# The first superclass is the first extension that gets to handle each key and
# the first to receive paint events.
class CodeEditor(
    HighlightCurrentLine,
    HighlightMatchingOccurrences,
    HighlightMatchingBracket,
    FullUnderlines,
    IndentationGuides,
    CodeFolding,
    LongLineIndicator,
    ShowWhitespace,
    ShowLineEndings,
    Wrap,
    BreakPoints,
    LineNumbers,
    AutoCompletion,  # Escape: first remove autocompletion,
    Calltip,  # then calltip
    Indentation,
    MoveLinesUpDown,
    ScrollWithUpDownKeys,
    HomeKey,
    EndKey,
    # NumpadPeriodKey,  -> disabled, see issue #720
    AutoIndent,
    PythonAutoIndent,
    AutoCloseQuotesAndBrackets,
    SyntaxHighlighting,
    SmartCopyAndPaste,  # overrides cut(), copy(), paste()
    CodeEditorBase,  # CodeEditorBase must be the last one in the list
):
    """
    CodeEditor with all the extensions
    """

    pass
