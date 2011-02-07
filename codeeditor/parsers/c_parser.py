import re
from codeeditor.parsers import tokens, Parser
from codeeditor.parsers.tokens import ALPHANUM

from codeeditor.parsers.tokens import (CommentToken, StringToken, 
    UnterminatedStringToken, IdentifierToken, NonIdentifierToken, KeywordToken,
    NumberToken, ContinuationToken)


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

    def parseLine(self, line, previousState=0):
        """ parseLine(line, previousState=0)
        
        Parses a line of C code, yielding tokens.
        
        """ 
        
        pos = 0 # Position following the previous match
        
        # identifierState and previousstate values:
        # 0: nothing special
        # 1: string
        # 2: multiline comment /* */
                
        # Enter the main loop that iterates over the tokens and skips strings
        previousIdentifier = ''
        while True:
            
            # First determine whether we should look for the end of a string,
            # or if we should process a token.
            if previousState == 1:
                style = "'''"
                matchStart, matchEnd = 0, 0
            elif previousState == 2:
                style = '"""'
                matchStart, matchEnd = 0, 0
            else:
                
                # Find the start of the next string or comment
                match = tokenProg.search(line,pos)
                
                # Process the Non-Identifier between pos and match.start() 
                # or end of line
                nonIdentifierEnd = match.start() if match else len(line)
                
                # Yield the Non-Identifier token if non-null
                token = NonIdentifierToken(line,pos,nonIdentifierEnd)
                strippedNonIdentifier = str(token).strip()
                if token:
                    yield token
                
                # If no match, we are done processing the line
                if not match:
                    return
                
                # The rest is to establish what identifier we are dealing with
                
               
                # Identifier ("a word or number") Find out whether it is a key word
                if match.group(1) is not None:
                    identifier = match.group(1)
                    tokenArgs = line, match.start(), match.end()
                    
                    if identifier in ['int', 'const', 'char', 'void', 'short', 'long', 'case']: 
                        yield KeywordToken(*tokenArgs)
                    elif identifier[0] in '0123456789':
                        identifierState = 0
                        yield NumberToken(*tokenArgs)
                    else:
                        yield IdentifierToken(*tokenArgs)
                    
                    # Goto next round
                    pos = match.end()
                    continue
                    
                # Single line comment
                elif match.group(2) is not None:
                    yield CommentToken(line,match.start(),len(line))
                    return
                    
                elif match.group(3) is not None:
                    token = CommentToken
                    endProg = commentEndProg
                                    
                else:
                    # We have matched a string-start
                    # Find the string style ( ' or " )
                    style = match.group(4) # The style is in match group 4
                    token = StringToken


                matchStart, matchEnd = match.start(), match.end()
            
            
            # If we get here, we are inside a string or comment and should find 
            # the end, using the endProg that we have.
            
            # Find the matching end in the rest of the line
            # Do not use the start parameter of search, since ^ does not work then
            endMatch = endProg.search(line[matchEnd:])
            
            if not endMatch:
                # The string does not end on this line
                yield UnterminatedStringToken(line,matchStart,len(line))
                return
            else:
                # The string does end on this line
                yield (token(line,matchStart,matchEnd+endMatch.end()))
                pos = matchEnd + endMatch.end()

if __name__=='__main__':
    parser = CParser()
    for token in parser.parseLine('void test(int i=2) /* test '):
        print ("%s %s" % (token.name, token))