import re
import keyword

class Token:
    def __init__(self,line,start,end):
        self.line=line
        self.start=start
        self.end=end
        #The type of the class is the lower case class name minus 'Token'
        self.type = self.__class__.__name__[:-5].lower() 
    def __str__(self):
        return self.line[self.start:self.end]
    def __len__(self):
        # Defining a length also gives a Token a boolean value: True if there
        # are any characters (len!=0) and False if there are none
        return self.end - self.start
    def __repr__(self):
        return repr('%s:%s' % (self.type, self))

class TextToken(Token):
    type = 'T'
        
class StringToken(Token):
    type = 'S'

class CommentToken(Token):
    type = 'C'

class UnterminatedToken(Token):
    type = 'U'
    
class ContinuationToken(Token):
    type = 'E'
    def __init__(self,line,state):
        Token.__init__(self,line,len(line),len(line))
        self.state=state
class StringContinuationToken(ContinuationToken):
    pass

class LineContinuationToken(ContinuationToken):
    pass

class IdentifierToken(TextToken):
    pass

class NonIdentifierToken(TextToken):
    pass

class KeywordToken(IdentifierToken):
    pass

class NumberToken(IdentifierToken):
    pass

class MethodNameToken(IdentifierToken):
    pass
    
class ClassNameToken(IdentifierToken):
    pass

alphanum='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

tokenProg=re.compile(
    '#|' +						# Comment or
    '([' + alphanum + '_]+)|' +	# Identifiers/numbers (group 1) or
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
endProgs={
    "'": re.compile(r"(^|[^\\])(\\\\)*'"),
    '"': re.compile(r'(^|[^\\])(\\\\)*"'),
    "'''": re.compile(r"(^|[^\\])(\\\\)*'''"),
    '"""': re.compile(r'(^|[^\\])(\\\\)*"""')
    }

def tokenizeLine(line,previousState=0):
    pos = 0 # Position following the previous match
    
    #Handle line continuation after def or class
    #identifierState is 3 or 4 if the previous identifier was 3 or 4
    if previousState == 3 or previousState == 4: 
        identifierState = previousState
    else:
        identifierState = 0
        
    
    previousIdentifier = ''
    while True:
        if previousState == 1:
            style = "'''"
            matchStart,matchEnd=0,0
        elif previousState == 2:
            style = '"""'
            matchStart,matchEnd=0,0
        else:
            #Find the start of the next string or comment
            match=tokenProg.search(line,pos)
            
            #Process the Non-Identifier between pos and match.start() or end of line
            nonIdentifierEnd = match.start() if match else len(line)
            
            token = NonIdentifierToken(line,pos,nonIdentifierEnd)
            strippedNonIdentifier = str(token).strip()
            if token:
                yield token

            #Is the last non-whitespace a line-continuation character?
            if strippedNonIdentifier.endswith('\\'):
                lineContinuation=True
                # If there are non-whitespace characters after def or class,
                # cancel the identifierState
                if strippedNonIdentifier!='\\':
                    identifierState = 0
            else:
                lineContinuation = False
                # If there are non-whitespace characters after def or class,
                # cancel the identifierState
                if strippedNonIdentifier != '':
                    identifierState = 0
                    
            if not match:
                if lineContinuation:
                    yield LineContinuationToken(line,identifierState)
                return
            
            if match.group() == '#':
                #Comment
                yield CommentToken(line,match.start(),len(line))
                if lineContinuation:
                    yield LineContinuationToken(line,identifierState)
                return
            
            # If there are non-whitespace characters after def or class,
            # cancel the identifierState (this time, also if there is just a \
            # since apparently it was not on the end of a line)
            if strippedNonIdentifier != '':
                identifierState = 0
                    
            if match.group(1) is not None:
                #Identifier
                identifier=match.group(1)
                tokenArgs=line,match.start(),match.end()
                
                if identifier in keyword.kwlist: #TODO: also include python2.x keywords
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

                previousIdentifier=identifier
                pos=match.end()
                continue
            
            #We have matched a string-start
            
            #Find the string style ( ' or " or ''' or """)
            style=match.group(4) #The style is in match group 4
            matchStart,matchEnd=match.start(),match.end()
            
        previousState = 0 
        
        identifierState = 0
        
        #Find the matching end in the rest of the line
        #Do not use the start parameter of search, since ^ does not work then
        endMatch=endProgs[style].search(line[matchEnd:])
        
        if not endMatch:
            if style == "'''":
                yield StringToken(line,matchStart,len(line))
                yield StringContinuationToken(line,1)
            elif style == '"""':
                yield StringToken(line,matchStart,len(line))
                yield StringContinuationToken(line,2)
            else:
                yield UnterminatedToken(line,matchStart,len(line))
            return
        
        yield (StringToken(line,matchStart,matchEnd+endMatch.end()))
        pos=matchEnd+endMatch.end()

identifierChars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'
identifierProg=re.compile("["+identifierChars+"]+")
notIdentifierProg=re.compile("[^"+identifierChars+"]+")
    
    
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
