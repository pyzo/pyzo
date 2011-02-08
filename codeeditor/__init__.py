""" CodeEditor 

A full featured code editor component based on QPlainTextEdit.

"""

from .base import CodeEditorBase

from .extensions.appearance import (    HighlightCurrentLine, 
                                        IndentationGuides,
                                        LongLineIndicator,
                                        ShowWhitespace,
                                        ShowLineEndings,
                                        Wrap,
                                        LineNumbers
                                    )
from .extensions.behaviour import (     Indentation,
                                        HomeKey,
                                        EndKey,
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
    
    PythonAutoIndent,
    
    CodeEditorBase):  #CodeEditorBase must be the last one in the list
    """
    CodeEditor with all the extensions
    """
    pass
