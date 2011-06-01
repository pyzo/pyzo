""" CodeEditor 

A full featured code editor component based on QPlainTextEdit.

"""

from .manager import Manager
from .base import CodeEditorBase

from .extensions.appearance import (    HighlightCurrentLine, 
                                        IndentationGuides,
                                        LongLineIndicator,
                                        ShowWhitespace,
                                        ShowLineEndings,
                                        Wrap,
                                        LineNumbers,
                                        SyntaxHighlighting
                                    )
from .extensions.behaviour import (     Indentation,
                                        HomeKey,
                                        EndKey,
                                        AutoIndent,
                                        PythonAutoIndent
                                   )
from .extensions.autocompletion import AutoCompletion
from .extensions.calltip import Calltip

 
# Order of superclasses: first the extensions, then CodeEditorBase
# The first superclass is the first extension that gets to handle each key
# 
class CodeEditor(
    HighlightCurrentLine, 
    IndentationGuides, 
    LongLineIndicator,
    ShowWhitespace, 
    ShowLineEndings, 
    Wrap,
    LineNumbers, 

    AutoCompletion, #Escape: first remove autocompletion,
    Calltip,               #then calltip
    
    Indentation,
    HomeKey,
    EndKey,
    
    AutoIndent,
    PythonAutoIndent,
    
    SyntaxHighlighting,
    
    CodeEditorBase):  #CodeEditorBase must be the last one in the list
    """
    CodeEditor with all the extensions
    """
    pass
