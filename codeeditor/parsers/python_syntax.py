import re
import keyword
from codeeditor.parsers import how_to_call_this
from codeeditor.parsers.how_to_call_this import *



# This regexp is used to find special stuff, such as comments, numbers and
# strings.
tokenProg = re.compile(
    '#|' +						# Comment or
    '([' + ALPHANUM + '_]+)|' +	# Identifiers/numbers (group 1) or
    '(' +  						# Begin of string group (group 2)
    '([bB]|[uU])?' +			# Possibly bytes or unicode (py2.x)
    '[rR]?' +					# Possibly a raw string
    '("""|\'\'\'|"|\')' +		# String start (triple qoutes first, group 4)
    ')'							# End of string group
    )	


#For a given type of string ( ', " , ''' , """ ),get  the RegExp
#program that matches the end. (^|[^\\]) means: start of the line
#or something that is not \ (since \ is supposed to escape the following
#quote) (\\\\)* means: any number of two slashes \\ since each slash will
#escape the next one
endProgs = {
    "'": re.compile(r"(^|[^\\])(\\\\)*'"),
    '"': re.compile(r'(^|[^\\])(\\\\)*"'),
    "'''": re.compile(r"(^|[^\\])(\\\\)*'''"),
    '"""': re.compile(r'(^|[^\\])(\\\\)*"""')
    }


def tokenizeLinePython(line, previousState=0):
    """ tokenizeLinePython(line, previousState=0)
    
    Tokenize a line of Python code, yielding tokens.
    previousstate is the state of the previous block, and is used
    to handle line continuation and multiline strings.
    
    """ 
    
    pos = 0 # Position following the previous match
    
    #Handle line continuation after def or class
    #identifierState is 3 or 4 if the previous identifier was 3 or 4
    if previousState == 3 or previousState == 4: 
        identifierState = previousState
    else:
        identifierState = 0
    
    # identifierState and previousstate values:
    # 0: nothing special
    # 1: multiline comment single qoutes
    # 2: multiline comment double quotes
    # 3: a def keyword
    # 4: a class keyword
    
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
            
            # Do checks for line continuation and identifierState
            # Is the last non-whitespace a line-continuation character?
            if strippedNonIdentifier.endswith('\\'):
                lineContinuation = True
                # If there are non-whitespace characters after def or class,
                # cancel the identifierState
                if strippedNonIdentifier != '\\':
                    identifierState = 0
            else:
                lineContinuation = False
                # If there are non-whitespace characters after def or class,
                # cancel the identifierState
                if strippedNonIdentifier != '':
                    identifierState = 0
            
            # If no match, we are done processing the line
            if not match:
                if lineContinuation:
                    yield LineContinuationToken(line,identifierState)
                return
            
            # The rest is to establish what identifier we are dealing with
            
            # Comment
            if match.group() == '#':
                matchStart = match.start()
                if ( line[matchStart:].startswith('##') and 
                        not line[:matchStart].strip() ):
                    yield CellCommentToken(line,matchStart,len(line))
                else:
                    yield CommentToken(line,matchStart,len(line))
                if lineContinuation:
                    yield LineContinuationToken(line,identifierState)
                return
            
            # If there are non-whitespace characters after def or class,
            # cancel the identifierState (this time, also if there is just a \
            # since apparently it was not on the end of a line)
            if strippedNonIdentifier != '':
                identifierState = 0
            
            # Identifier ("a word or number") Find out whether it is a key word
            if match.group(1) is not None:
                identifier = match.group(1)
                tokenArgs = line, match.start(), match.end()
                
                #TODO: also include python2.x keywords
                if identifier in keyword.kwlist: 
                    if identifier == 'def':
                        identifierState = 3
                    elif identifier == 'class':
                        identifierState = 4
                    else:
                        identifierState = 0
                    yield KeywordToken(*tokenArgs)
                elif identifier[0] in '0123456789':
                    identifierState = 0
                    yield NumberToken(*tokenArgs)
                else:
                    if identifierState == 3:
                        yield MethodNameToken(*tokenArgs)
                    elif identifierState == 4:
                        yield ClassNameToken(*tokenArgs)
                    else:
                        yield IdentifierToken(*tokenArgs)
                    identifierState = 0
                
                # Goto next round
                previousIdentifier = identifier
                pos = match.end()
                continue
            
            else:
                # We have matched a string-start
                # Find the string style ( ' or " or ''' or """)
                style = match.group(4) # The style is in match group 4
                matchStart, matchEnd = match.start(), match.end()
        
        
        # If we get here, we are inside a string and should find the end,
        # using the style that we stored.
        
        # Reset states.
        previousState = 0 
        identifierState = 0
        
        # Find the matching end in the rest of the line
        # Do not use the start parameter of search, since ^ does not work then
        endMatch = endProgs[style].search(line[matchEnd:])
        
        if not endMatch:
            # The string does not end on this line
            if style == "'''":
                yield StringToken(line,matchStart,len(line))
                yield StringContinuationToken(line,1)
            elif style == '"""':
                yield StringToken(line,matchStart,len(line))
                yield StringContinuationToken(line,2)
            else:
                yield UnterminatedToken(line,matchStart,len(line))
            return
        else:
            # The string does end on this line
            yield (StringToken(line,matchStart,matchEnd+endMatch.end()))
            pos = matchEnd + endMatch.end()


# identifierChars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'
# identifierProg=re.compile("["+identifierChars+"]+")
# notIdentifierProg=re.compile("[^"+identifierChars+"]+")
#     
    
if __name__=='__main__':
    print(list(tokenizeLine('this is "String" #Comment')))
    print(list(tokenizeLine('this is "String\' #Comment')))
    print(list(tokenizeLine('this is "String\' #Commen"t')))
    print(list(tokenizeLine(r'this "test\""')))
        
    import random
    stimulus=''
    expect=[]
    for i in range(10):
        #Create a string with lots of ' and "
        s=''.join("'\"\\ab#"[random.randint(0,5)] for i in range(10)  )
        stimulus+=repr(s)
        expect.append('S:'+repr(s))
        stimulus+='test'
        expect.append('I:test')
    result=list(tokenizeLine(stimulus))
    print (stimulus)
    print (expect)
    print (result)
    
    assert repr(result) == repr(expect)
