import re
from codeeditor.parsers import tokens, Parser, BlockState
from codeeditor.parsers.tokens import ALPHANUM

from codeeditor.parsers.tokens import (CommentToken, StringToken, 
    UnterminatedStringToken, IdentifierToken, NonIdentifierToken, KeywordToken,
    NumberToken)


class MultilineCommentToken(CommentToken):
    """ Characters representing a multi-line comment. """
    defaultStyle = 'fore:#007F00'


# This regexp is used to find special stuff, such as comments, numbers and
# strings.
tokenProg = re.compile(
    '([' + ALPHANUM + '_]+)|' +	# Identifiers/numbers (group 1) or
    '(\/\/)|' +                   # Single line comment (group 2)
    '(\/\*)|' +                   # Comment (group 3) or
    '(\')|(\")'                 # Char / string (group 4/5)
    )


#For a string, get the RegExp
#program that matches the end. (^|[^\\]) means: start of the line
#or something that is not \ (since \ is supposed to escape the following
#quote) (\\\\)* means: any number of two slashes \\ since each slash will
#escape the next one
stringEndProg = re.compile(r'(^|[^\\])(\\\\)*"')
commentEndProg = re.compile(r'\*/')

class CParser(Parser):
    """ A C parser.
    """
    _extensions = ['.c', '.h', '.cpp', 'cxx', 'hxx']
    _keywords = ['int', 'const', 'char', 'void', 'short', 'long', 'case']
    
    def parseLine(self, line, previousState=0):
        """ parseLine(line, previousState=0)
        
        Parses a line of C code, yielding tokens.
        
        """ 
        
        pos = 0 # Position following the previous match
        
        # identifierState and previousstate values:
        # 0: nothing special
        # 1: string
        # 2: multiline comment /* */
        
        # First determine whether we should look for the end of a string,
        # or if we should process a token.
        if previousState == 1:
            token = StringToken(line, 0, 0)
            endToken = self._findEndOfString(line, token)
            # Yield token, finished?
            yield token
            if endToken:
                yield endToken
                return
            else:
                pos += token.end
        elif previousState == 2:
            token = MultilineCommentToken(line, 0, 0)
            endToken = self._findEndOfComment(line, token)
            # Yield token, finished?
            yield token
            if endToken:
                yield endToken
                return
            else:
                pos += token.end
        
        # Enter the main loop that iterates over the tokens and skips strings
        while True:
            
            # Get next token and maybe an end token
            token = self._findNextToken(line, pos)
            if not token:
                return
            elif isinstance(token, StringToken):
                endToken = self._findEndOfString(line, token)
            elif isinstance(token, MultilineCommentToken):
                endToken = self._findEndOfComment(line, token)
            else:
                endToken = None
            
            # Yield token, finished?
            yield token
            if endToken:
                yield endToken
                return
            else:
                pos += token.end
    
    
    def _findEndOfComment(self, line, token):
        """ Find the matching comment end in the rest of the line
        """
        
        # Do not use the start parameter of search, since ^ does not work then
        
        endMatch = commentEndProg.search(line, token.end)
        
        if endMatch:
            # The comment does end on this line
            token.end = endMatch.end()
        else:
            # The comment does not end on this line
            token.end = len(line)
            return BlockState(2)
    
    
    def _findEndOfString(self, line, token):
        """ Find the matching string end in the rest of the line
        """
        
        # todo: distinguish between single and double quote strings
        # todo: why would you need the ^ in regexp
        # todo: C and C++ do not have multilinge strings afaik, or do they?
        
        # Find the matching end in the rest of the line
        # Do not use the start parameter of search, since ^ does not work then
        endMatch = stringEndProg.search(line[token.end:])
        
        if endMatch:
            # The string does end on this line
            token.end = token.end + endMatch.end()
        else:
            # The string does not end on this line
            token.end = len(line)
            return BlockState(1)
    
    
    def _findNextToken(self, line, pos):
        """ _findNextToken(line, pos):
        
        Returns a token or None if no new tokens can be found.
        
        """
        if pos > len(line):
            return None
        
        # Find the start of the next string or comment
        match = tokenProg.search(line, pos)
        
        # Process the Non-Identifier between pos and match.start() 
        # or end of line
        nonIdentifierEnd = match.start() if match else len(line)
        
        # Return the Non-Identifier token if non-null
        token = NonIdentifierToken(line,pos,nonIdentifierEnd)
        if token:
            return token
        
        # If no match, we are done processing the line
        if not match:
            return None
        
        # The rest is to establish what identifier we are dealing with
        
        # Identifier ("a word or number") Find out whether it is a key word
        if match.group(1) is not None:
            identifier = match.group(1)
            tokenArgs = line, match.start(), match.end()
            
            if identifier in self._keywords: 
                return KeywordToken(*tokenArgs)
            elif identifier[0] in '0123456789':
                identifierState = 0
                return NumberToken(*tokenArgs)
            else:
                return IdentifierToken(*tokenArgs)
        
        # Single line comment
        elif match.group(2) is not None:
            return CommentToken(line,match.start(),len(line))
        elif match.group(3) is not None:
            return MultilineCommentToken(line,match.start(),match.end())
        else:
            # We have matched a string-start
            return StringToken(line,match.start(),match.end())


if __name__=='__main__':
    parser = CParser()
    for token in parser.parseLine('void test(int i=2) /* test '):
        print ("%s %s" % (token.name, token))
