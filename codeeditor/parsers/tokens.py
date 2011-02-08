""" Module tokens

Defines the base Token class and a few generic tokens.
Tokens are used by parsers to identify for groups of characters
what they represent. This is in turn used by the highlighter
to determine how these characters should be styled.

"""

# todo: define tokens in style.py?

# Many parsers need this
ALPHANUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'


from ..style import StyleFormat, StyleElementDescription
from ..misc import ustr, bstr


class Token(object):
    """ Token(line, start, end)
    
    Base token class.
    
    A token is a group of characters representing "something".
    What is represented, is specified by the subclass.
    
    Each token class has a (static) member 'defaultStyle' indicating 
    the default style of the token. For the formatting see this example:
    "fore:#000, back:#fff, bold:yes, underline:no"
    
    Each token class should also have a docstring describing the meaning
    of the characters it is applied to.
    
    """ 
    
    def __init__(self, line='', start=0, end=0):
        self.line = ustr(line)
        self.start = start
        self.end = end
        self._name = self.__class__.__name__[:-5].lower() 
    
    def __str__(self):
        return self.line[self.start:self.end]
    
    def __repr__(self):
        return repr('%s:%s' % (self.name, self))
    
    def __len__(self):
        # Defining a length also gives a Token a boolean value: True if there
        # are any characters (len!=0) and False if there are none
        return self.end - self.start
    
    @property
    def name(self):
        """ The name of this token. Used to identify it and attach a style.
        """
        return self._name


class ContinuationToken(Token):
    """ Used to pass a number to the next block to process multi-line
    comments etc. The meaning of the state is specific for the parser.
    """
    def __init__(self, line='', state=0):
        Token.__init__(self, line, len(line), len(line))
        self.state = state


# The name is default token because it represents the default character format
# The name of the class is used as the name of the style element description
class DefaultToken(Token):
    """ The default style of all characters. """
    defaultStyle = 'fore:#000, bold:no, underline:no, italic:no'
    
    def getDefaultStyleFormat(self):
        elements = []
        def collect(cls):
            if hasattr(cls, 'defaultStyle'):
                elements.append(cls.defaultStyle)
                for c in cls.__bases__:
                    collect(c)
        collect(self.__class__)
        se = StyleFormat()
        for e in reversed(elements):
            se.update(e)
        return se
    
    def description(self):
        """ description()
        
        Returns a StyleElementDescription instance that describes the
        style element that this token represents.
        
        """
        format = self.getDefaultStyleFormat()
        des = 'syntax: ' + self.__doc__
        return StyleElementDescription(self.name, str(format), des)


class CommentToken(DefaultToken):
    """ Characters representing a comment in the code. """
    defaultStyle = 'fore:#007F00'

class TodoCommentToken(CommentToken):
    """ Characters representing a comment in the code. """
    defaultStyle = 'italic'

class StringToken(DefaultToken):
    """ Characters representing a textual string in the code. """
    defaultStyle = 'fore:#7F007F'

class UnterminatedStringToken(StringToken):
    """ Characters belonging to an unterminated string. """
    #defaultStyle = 'fore:#fff,back:#7F007F'
    defaultStyle = 'underline:dotted'


class TextToken(DefaultToken):
    """ Anything that is not a string or comment. """ 
    defaultStyle = 'fore:#000'

class IdentifierToken(TextToken):
    """ Characters representing normal text (i.e. words). """ 
    defaultStyle = ''

class NonIdentifierToken(TextToken):
    """ Not a word (operators, whitespace, etc.). """
    defaultStyle = ''

class KeywordToken(IdentifierToken):
    """ A keyword is a word with a special meaning to the language. """
    defaultStyle = 'fore:#00007F, bold:yes'

class NumberToken(IdentifierToken):
    """ Characters represening a number. """
    defaultStyle = 'fore:#007F7F'

class FunctionNameToken(IdentifierToken):
    """ Characters represening the name of a function. """
    defaultStyle = 'fore:#007F7F, bold:yes'

class ClassNameToken(IdentifierToken):
    """ Characters represening the name of a class. """
    defaultStyle = 'fore:#0000FF, bold:yes'

