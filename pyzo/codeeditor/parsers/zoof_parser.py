"""
Don't mind this; it just helps me with some experimental stuff.
"""

from .python_parser import PythonParser

keywords = ('import', 'export',
            'type', 'func', 'return', 'end',
            'for', 'while', 'if', 'elseif', 'with', 'do', 'done', 'continue', 'break',
            'try', 'catch', 'finally', 'throw', 'assert',
            'in', 'as',
            'true', 'false',
            )

maybe_keywords = 'none', 'has', 'const', 'global', 'nonlocal', 'local', 'switch'


class ZoofParser(PythonParser):
    """ Parser for Experimemtal Zoof lang.
    """
    _extensions = ['.zf', '.zoof']
    
    _keywords = keywords + maybe_keywords
