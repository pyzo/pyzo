# -*- coding: utf-8 -*-
# Copyright (C) 2012, the codeeditor development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" CodeEditor 

A full featured code editor component based on QPlainTextEdit.

"""

from .manager import Manager
from .base import CodeEditorBase

from .extensions.appearance import (    HighlightCurrentLine, 
                                        FullUnderlines,
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
                                        NumpadPeriodKey,
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
    FullUnderlines,
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
    NumpadPeriodKey,
    
    AutoIndent,
    PythonAutoIndent,
    
    SyntaxHighlighting,
    
    CodeEditorBase):  #CodeEditorBase must be the last one in the list
    """
    CodeEditor with all the extensions
    """
    pass
