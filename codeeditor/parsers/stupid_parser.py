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
    '(' +  						# Begin of string group (group 2)
    '([bB]|[uU])?' +			# Possibly bytes or unicode (py2.x)
    '[rR]?' +					# Possibly a raw string
    '("|\')' +		            # String start
    ')'							# End of string group
    )	


#For a given type of string ( ', " ),get  the RegExp
#program that matches the end. (^|[^\\]) means: start of the line
#or something that is not \ (since \ is supposed to escape the following
#quote) (\\\\)* means: any number of two slashes \\ since each slash will
#escape the next one
endProgs = {
    "'": re.compile(r"(^|[^\\])(\\\\)*'"),
    '"': re.compile(r'(^|[^\\])(\\\\)*"'),
    }


class StupidParser(Parser):
    """ A stupid test parser.
    """

    def parseLine(self, line, previousState=0):
        """ parseLine(line, previousState=0)
        
        Parses a line of Stupid code, yielding tokens.
        This will only tokenize numbers and strings.
        
        """ 
        
        pos = 0 # Position following the previous match
        
        # We do not do previous stae
        
        # Enter the main loop that iterates over the tokens and skips strings
        previousIdentifier = ''
        while True:
            
            # First determine whether we should look for the end of a string,
            # or if we should process a token.
            
            if True:
                
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
                
                # Comment
                if match.group() == '#':
                    yield CommentToken(line,match.start(),len(line))
                    return
                
                # Identifier ("a word or number") Find out whether it is a key word
                if match.group(1) is not None:
                    identifier = match.group(1)
                    tokenArgs = line, match.start(), match.end()
                    
                    if identifier in ['aap', 'noot', 'mies', 'boom', 'roos', 'vis', 'vuur']: 
                        yield KeywordToken(*tokenArgs)
                    elif identifier[0] in '0123456789':
                        identifierState = 0
                        yield NumberToken(*tokenArgs)
                    else:
                        yield IdentifierToken(*tokenArgs)
                    
                    # Goto next round
                    pos = match.end()
                    continue
                
                else:
                    # We have matched a string-start
                    # Find the string style ( ' or " )
                    style = match.group(4) # The style is in match group 4
                    matchStart, matchEnd = match.start(), match.end()
            
            
            # If we get here, we are inside a string and should find the end,
            # using the style that we stored.
            
            # Find the matching end in the rest of the line
            # Do not use the start parameter of search, since ^ does not work then
            endMatch = endProgs[style].search(line[matchEnd:])
            
            if not endMatch:
                # The string does not end on this line
                yield UnterminatedStringToken(line,matchStart,len(line))
                return
            else:
                # The string does end on this line
                yield (StringToken(line,matchStart,matchEnd+endMatch.end()))
                pos = matchEnd + endMatch.end()
