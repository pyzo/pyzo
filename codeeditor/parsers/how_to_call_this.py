
# todo: move to __init__?

# Many parsers need this
ALPHANUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

class Token(object):
    """ Token(line, start, end)
    
    A token is a group of characters representing "something".
    What is represented, is specified by the subclass.
    
    """ 
    defaultStyle = '#000'
    def __init__(self, line, start, end):
        self.line=line
        self.start=start
        self.end=end
    
    def __str__(self):
        return self.line[self.start:self.end]
    
    def __len__(self):
        # Defining a length also gives a Token a boolean value: True if there
        # are any characters (len!=0) and False if there are none
        return self.end - self.start
    
    def __repr__(self):
        return repr('%s:%s' % (self.name, self))
    
    @property
    def name(self):
        """ The name of this token. Used to identify it and attach a style.
        """
        return self.__class__.__name__[:-5].lower() 
    
    # todo: do we need this if we specify default styles anyway?
    @property
    def names(self):
        """ A list of names of this token, obtained by looking how this
        token inherits from other tokens. If no style can be found for
        the actual name, we can try one of the alternatives.
        """
        names = []
        def collectClassNames(cls):
            if cls.__name__.endswith('Token'):
                names.append(cls.__name__[:-5].lower())
                for c in cls.__bases__:
                    collectClassNames(c)
        collectClassNames(self.__class__)
        return names


class TextToken(Token):
    pass

class StringToken(Token):
    defaultStyle = '#7F007F'

class MultilineStringToken(StringToken):
    defaultStyle = '#7F0000'
    pass

class CommentToken(Token):
    pass
class CellCommentToken(CommentToken): # todo: move to python
    pass

class UnterminatedToken(Token):
    pass
    
class ContinuationToken(Token):
    """ Used to pass a number to the next block to process multi-line
    comments etc. The meaning of the state is specific for the parser.
    """
    type = 'E'
    def __init__(self,line,state):
        Token.__init__(self,line,len(line),len(line))
        self.state=state
# todo: The String and line continuation are Python specific, do we need them?
class StringContinuationToken(ContinuationToken):
    pass

class LineContinuationToken(ContinuationToken):
    pass

class IdentifierToken(TextToken):
    pass # Basically: a word

class NonIdentifierToken(TextToken):
    pass # For example whitespace or line continuation characters and operators

class KeywordToken(IdentifierToken):
    pass

class NumberToken(IdentifierToken):
    pass

class MethodNameToken(IdentifierToken):
    pass
    
class ClassNameToken(IdentifierToken):
    pass
