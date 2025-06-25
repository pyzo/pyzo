import re
from . import Parser, BlockState

# Import tokens in module namespace
from .tokens import (
    CommentToken,
    StringToken,
    UnterminatedStringToken,
    IdentifierToken,
    NonIdentifierToken,
    KeywordToken,
    BuiltinsToken,
    InstanceToken,
    NumberToken,
    FunctionNameToken,
    ClassNameToken,
    TodoCommentToken,
    OpenParenToken,
    CloseParenToken,
    IllegalToken,
)

# Keywords sets

# Source: import keyword; keyword.kwlist (Python 2.7)
python2Keywords = set(
    [
        "and",
        "as",
        "assert",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "exec",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "not",
        "or",
        "pass",
        "print",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    ]
)

# Source: import keyword; keyword.kwlist (Python 3.12)
python3Keywords = set(
    [
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        "async",
        "await",
    ]
)

# Merge the two sets to get a general Python keyword list
pythonKeywords = python2Keywords | python3Keywords

# Builtins sets

# Source: dir (__builtins__) (Python 2.7.12)
python2Builtins = set(
    [
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BaseException",
        "BufferError",
        "BytesWarning",
        "DeprecationWarning",
        "EOFError",
        "Ellipsis",
        "EnvironmentError",
        "Exception",
        "False",
        "FloatingPointError",
        "FutureWarning",
        "GeneratorExit",
        "IOError",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "IndexError",
        "KeyError",
        "KeyboardInterrupt",
        "LookupError",
        "MemoryError",
        "NameError",
        "None",
        "NotImplemented",
        "NotImplementedError",
        "OSError",
        "OverflowError",
        "PendingDeprecationWarning",
        "ReferenceError",
        "RuntimeError",
        "RuntimeWarning",
        "StandardError",
        "StopIteration",
        "SyntaxError",
        "SyntaxWarning",
        "SystemError",
        "SystemExit",
        "TabError",
        "True",
        "TypeError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "UnicodeWarning",
        "UserWarning",
        "ValueError",
        "Warning",
        "ZeroDivisionError",
        "__debug__",
        "__doc__",
        "__import__",
        "__name__",
        "__package__",
        "abs",
        "all",
        "any",
        "apply",
        "basestring",
        "bin",
        "bool",
        "buffer",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "cmp",
        "coerce",
        "compile",
        "complex",
        "copyright",
        "credits",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "execfile",
        "exit",
        "file",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "intern",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "license",
        "list",
        "locals",
        "long",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "quit",
        "range",
        "raw_input",
        "reduce",
        "reload",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "unichr",
        "unicode",
        "vars",
        "xrange",
        "zip",
    ]
)

# Source: import builtins; dir(builtins) (Python 3.12)
# Note: Removed 'False', 'None', 'True'. They are keyword in Python 3
python3Builtins = set(
    [
        "ArithmeticError",
        "AssertionError",
        "AttributeError",
        "BaseException",
        "BaseExceptionGroup",
        "BlockingIOError",
        "BrokenPipeError",
        "BufferError",
        "BytesWarning",
        "ChildProcessError",
        "ConnectionAbortedError",
        "ConnectionError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "DeprecationWarning",
        "EOFError",
        "Ellipsis",
        "EncodingWarning",
        "EnvironmentError",
        "Exception",
        "ExceptionGroup",
        "FileExistsError",
        "FileNotFoundError",
        "FloatingPointError",
        "FutureWarning",
        "GeneratorExit",
        "IOError",
        "ImportError",
        "ImportWarning",
        "IndentationError",
        "IndexError",
        "InterruptedError",
        "IsADirectoryError",
        "KeyError",
        "KeyboardInterrupt",
        "LookupError",
        "MemoryError",
        "ModuleNotFoundError",
        "NameError",
        "NotADirectoryError",
        "NotImplemented",
        "NotImplementedError",
        "OSError",
        "OverflowError",
        "PendingDeprecationWarning",
        "PermissionError",
        "ProcessLookupError",
        "RecursionError",
        "ReferenceError",
        "ResourceWarning",
        "RuntimeError",
        "RuntimeWarning",
        "StopAsyncIteration",
        "StopIteration",
        "SyntaxError",
        "SyntaxWarning",
        "SystemError",
        "SystemExit",
        "TabError",
        "TimeoutError",
        "TypeError",
        "UnboundLocalError",
        "UnicodeDecodeError",
        "UnicodeEncodeError",
        "UnicodeError",
        "UnicodeTranslateError",
        "UnicodeWarning",
        "UserWarning",
        "ValueError",
        "Warning",
        "ZeroDivisionError",
        "_",
        "__build_class__",
        "__debug__",
        "__doc__",
        "__import__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
        "abs",
        "aiter",
        "all",
        "anext",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "copyright",
        "credits",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "exit",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "license",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "quit",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
    ]
)


# Merge the two sets to get a general Python builtins list
pythonBuiltins = python2Builtins | python3Builtins

# Instance sets
python2Instance = set(["self"])

python3Instance = set(["self"])

pythonInstance = python2Instance | python3Instance


class MultilineStringToken(StringToken):
    """Characters representing a multi-line string."""

    defaultStyle = "fore:#7F0000"


class CellCommentToken(CommentToken):
    """Characters representing a cell separator comment: "##"."""

    defaultStyle = "bold:yes, underline:yes"


stringLiteralPrefixes = frozenset("u|r|b|f|rb|br|rf|fr|t|rt|tr".split("|"))

# This regexp is used to find special stuff, such as comments, numbers and
# strings.
tokenProg = re.compile(
    "#|"  # Comment or
    + "("  # Begin of string group (group 1)
    + "("
    + "|".join(stringLiteralPrefixes)
    + ")?"  # (group 2)
    + "(\"\"\"|'''|\"|')"  # String start (triple quotes first, group 3)
    + ")|"  # End of string group
    + "([a-z0-9_]+)|"  # Identifiers/numbers (group 4) or
    + r"(\(|\[|\{)|"  # Opening parenthesis (gr 5)
    + r"(\)|\]|\})|"  # Closing parenthesis (gr 6)
    + "("
    + chr(160)  # non-breaking space (gr 7)
    + ")",
    re.IGNORECASE,
)


# For a given type of string ( ', " , ''' , """ ), get the RegExp
# program that matches the end. (^|[^\\]) means: start of the line
# or something that is not \ (since \ is supposed to escape the following
# quote) (\\\\)* means: any number of two slashes \\ since each slash will
# escape the next one
endProgs = {
    "'": re.compile(r"(^|[^\\])(\\\\)*'"),
    '"': re.compile(r'(^|[^\\])(\\\\)*"'),
    "'''": re.compile(r"(^|[^\\])(\\\\)*'''"),
    '"""': re.compile(r'(^|[^\\])(\\\\)*"""'),
}

# A string can also be line-continued with a backslash at the very end of a line.
# In that case one single or double quote sign can span more than a line.
stringLineContinuation = re.compile(r"(^|[^\\])(\\\\)*\\$")


class PythonParser(Parser):
    """Parser for Python in general."""

    _extensions = []
    _shebangKeywords = []
    # The list of keywords is overridden by the Python2/3 specific parsers
    _keywords = set()
    # The list of builtins and instances is overridden by the Python2/3 specific parsers
    _builtins = set()
    _instance = set()

    def _identifierState(self, identifier=None):
        """Given an identifier returns the identifier state:
        3 means the current identifier can be a function.
        4 means the current identifier can be a class.
        0 otherwise.

        This method enables storing the state during the line,
        and helps the Cython parser to reuse the Python parser's code.
        """
        if identifier is None:
            # Explicit get/reset
            try:
                state = self._idsState
            except Exception:
                state = 0
            self._idsState = 0
            return state
        elif identifier == "def":
            # Set function state
            self._idsState = 3
            return 3
        elif identifier == "class":
            # Set class state
            self._idsState = 4
            return 4
        else:
            # This one can be func or class, next one can't
            state = self._idsState
            self._idsState = 0
            return state

    def parseLine(self, line, previousState=0):
        """Parse a line of Python code, returning a list of tokens.
        previousState is the state of the previous block, and is used
        to handle line continuation and multiline strings.
        """

        # Init
        pos = 0  # Position following the previous match

        tokensForLine = []

        # identifierState and previousState values:
        # 0: nothing special
        # 1: multiline comment single qoutes
        # 2: multiline comment double quotes
        # 3: a def keyword
        # 4: a class keyword
        # 5: a single quote string literal (non-multiline) line-continued by a backslash
        # 6: a double quote string literal (non-multiline) line-continued by a backslash

        # Handle line continuation after def or class
        # identifierState is 3 or 4 if the previous identifier was 3 or 4
        if previousState == 3 or previousState == 4:
            self._identifierState({3: "def", 4: "class"}[previousState])
        else:
            self._identifierState(None)

        if previousState in [1, 2, 5, 6]:
            if previousState <= 2:
                token = MultilineStringToken(line, 0, 0)
            else:
                token = StringToken(line, 0, 0)
            token._style = ["", "'''", '"""', None, None, "'", '"'][previousState]
            tokens = self._findEndOfString(line, token)
            # Process tokens
            for token in tokens:
                tokensForLine.append(token)
                if isinstance(token, BlockState):
                    return tokensForLine
            pos = token.end

        # Enter the main loop that iterates over the tokens and skips strings
        while True:
            # Get next tokens
            tokens = self._findNextToken(line, pos)
            if not tokens:
                self._promoteMatchCaseSoftKeywords(tokensForLine)
                return tokensForLine
            elif isinstance(tokens[-1], StringToken):
                moreTokens = self._findEndOfString(line, tokens[-1])
                tokens = tokens[:-1] + moreTokens

            # Process tokens
            for token in tokens:
                tokensForLine.append(token)
                if isinstance(token, BlockState):
                    return tokensForLine
            pos = token.end

    @staticmethod
    def _promoteMatchCaseSoftKeywords(tokens):
        """promotes identifier tokens "match" and "case" to keyword tokens if appropriate

        list "tokens" contains the tokens of the current line

        A simple algorithm will be used that only knows about the tokens of the current
        line, but not about the lines before or after.
        If "match" or "case" is a keyword, its token in list "tokens" will be replaced by
        a keyword token.

        "match" or "case" will be considered a keyword if one of the two patterns is found:

        1.
            optional whitespace
            identifier token "match" or "case"
            all parenthesis like tokens ([{}]) must be properly closed
            colon (with optional whitespace)
            optional comment

        2.
            optional whitespace
            identifier token "match" or "case"
            parenthesis like tokens ([{}]) can be still open on the right side,
                assuming that they will be closed in the following lines
            optional comment


        single line examples where match or case is promoted to a keyword:
            match x:  # random comment
            match (x):
            match(
            case []:
            case {"x": x,
            case {"x": x,  # another comment
            case (0, 0):

        single line examples where match or case is NOT promoted to a keyword:
            match x
            case [(]:
            case {"x": x,}
            case {"x": x,)
            case (0, 0)

        False positives, i.e. promoting an identifier to a keyword erroneously, are very
        unlikely. One example is the line "match(" because it could be either followed by
        line "x)" and make it a normal function call, or it could be followed by line
        "x):" and make it a match statement.
        """

        indMatchCase = None
        closingParens = {"(": ")", "[": "]", "{": "}"}
        parensStack = []
        for i, token in enumerate(tokens):
            if i == 0 and isinstance(token, NonIdentifierToken):
                if str(token).isspace():
                    continue  # ignore whitespace before match or case identifiers
                else:
                    return
            elif indMatchCase is None:
                if isinstance(token, IdentifierToken) and str(token) in (
                    "match",
                    "case",
                ):
                    indMatchCase = i
                else:
                    return
            elif isinstance(token, OpenParenToken):
                parensStack.append(closingParens[str(token)])
            elif isinstance(token, CloseParenToken):
                if len(parensStack) > 0 and parensStack[-1] == str(token):
                    parensStack.pop()
                else:
                    return  # invalid parentheses (or square brackets or curly brackets)

        if indMatchCase is None:
            return
        i2 = -1  # index of the last token, not counting comment tokens
        if isinstance(tokens[i2], CommentToken):
            i2 = -2  # ignore the comment token at the end
            if len(tokens) < 3:
                return

        if len(parensStack) > 0:
            pass  # probably a match or case keyword, depending on the lines that follow
        elif (
            isinstance(tokens[i2], NonIdentifierToken)
            and str(tokens[i2]).strip() == ":"
        ):
            pass  # very likely a match or case keyword
        else:
            return  # not a match or case keyword

        t = tokens[indMatchCase]
        tokens[indMatchCase] = KeywordToken(t.line, t.start, t.end)

    def _findEndOfString(self, line, token):
        """Find the end of a string. Returns (token, endToken). The first
        is the given token or a replacement (UnterminatedStringToken).
        The latter is None, or the BlockState. If given, the line is
        finished.

        """

        # Set state
        self._identifierState(None)

        # Find the matching end in the rest of the line
        # Do not use the start parameter of search, since ^ does not work then
        style = token._style
        endMatch = endProgs[style].search(line[token.end :])

        if endMatch:
            # The string does end on this line
            tokenArgs = line, token.start, token.end + endMatch.end()
            if style in ['"""', "'''"]:
                token = MultilineStringToken(*tokenArgs)
            else:
                token.end = token.end + endMatch.end()
            return [token]
        else:
            # The string does not end on this line
            tokenArgs = line, token.start, token.end + len(line)
            if style == "'''":
                return [MultilineStringToken(*tokenArgs), BlockState(1)]
            elif style == '"""':
                return [MultilineStringToken(*tokenArgs), BlockState(2)]
            else:
                lineContMatch = stringLineContinuation.search(line[token.end :])
                if lineContMatch:
                    return [
                        StringToken(*tokenArgs),
                        BlockState(5 if style == "'" else 6),
                    ]
                return [UnterminatedStringToken(*tokenArgs)]

    def _findNextToken(self, line, pos):
        """Returns a token or None if no new tokens can be found."""

        # Init tokens, if pos too large, we are done
        if pos > len(line):
            return None
        tokens = []

        # Find the start of the next string or comment
        match = tokenProg.search(line, pos)

        # Process the Non-Identifier between pos and match.start()
        # or end of line
        nonIdentifierEnd = match.start() if match else len(line)

        # Return the Non-Identifier token if non-null
        # todo: here it goes wrong (allow returning more than one token?)
        token = NonIdentifierToken(line, pos, nonIdentifierEnd)
        strippedNonIdentifier = str(token).strip()
        if token:
            tokens.append(token)

        # Do checks for line continuation and identifierState
        # Is the last non-whitespace a line-continuation character?
        if strippedNonIdentifier.endswith("\\"):
            lineContinuation = True
            # If there are non-whitespace characters after def or class,
            # cancel the identifierState
            if strippedNonIdentifier != "\\":
                self._identifierState(None)
        else:
            lineContinuation = False
            # If there are non-whitespace characters after def or class,
            # cancel the identifierState
            if strippedNonIdentifier != "":
                self._identifierState(None)

        # If no match, we are done processing the line
        if not match:
            if lineContinuation:
                tokens.append(BlockState(self._identifierState()))
            return tokens

        # The rest is to establish what identifier we are dealing with

        # Comment
        if match.group() == "#":
            matchStart = match.start()
            if not line[:matchStart].strip() and (
                line[matchStart:].startswith(("##", "#%%", "# %%"))
            ):
                tokens.append(CellCommentToken(line, matchStart, len(line)))
            elif self._isTodoItem(line[matchStart + 1 :]):
                tokens.append(TodoCommentToken(line, matchStart, len(line)))
            else:
                tokens.append(CommentToken(line, matchStart, len(line)))
            if lineContinuation:
                tokens.append(BlockState(self._identifierState()))
            return tokens

        # If there are non-whitespace characters after def or class,
        # cancel the identifierState (this time, also if there is just a \
        # since apparently it was not on the end of a line)
        if strippedNonIdentifier != "":
            self._identifierState(None)

        # Identifier ("a word or number") Find out whether it is a key word
        if match.group(4) is not None:
            identifier = match.group(4)
            tokenArgs = line, match.start(), match.end()

            # Set identifier state
            identifierState = self._identifierState(identifier)

            if identifier in self._keywords:
                tokens.append(KeywordToken(*tokenArgs))
            elif identifier in self._builtins and (
                "." + identifier not in line and "def " + identifier not in line
            ):
                tokens.append(BuiltinsToken(*tokenArgs))
            elif identifier in self._instance:
                tokens.append(InstanceToken(*tokenArgs))
            elif identifier[0] in "0123456789":
                self._identifierState(None)
                tokens.append(NumberToken(*tokenArgs))
            else:
                if identifierState == 3 and line[match.end() :].lstrip().startswith(
                    "("
                ):
                    tokens.append(FunctionNameToken(*tokenArgs))
                elif identifierState == 4:
                    tokens.append(ClassNameToken(*tokenArgs))
                else:
                    tokens.append(IdentifierToken(*tokenArgs))

        elif match.group(3) is not None:
            # We have matched a string-start
            # Find the string style ( ' or " or ''' or """)
            token = StringToken(line, match.start(), match.end())
            token._style = match.group(3)  # The style is in match group 3
            tokens.append(token)
        elif match.group(5) is not None:
            token = OpenParenToken(line, match.start(), match.end())
            token._style = match.group(5)
            tokens.append(token)
        elif match.group(6) is not None:
            token = CloseParenToken(line, match.start(), match.end())
            token._style = match.group(6)
            tokens.append(token)
        elif match.group(7) is not None:
            token = IllegalToken(line, match.start(), match.end())
            token._style = match.group(7)
            tokens.append(token)
        # Done
        return tokens


class PythonParser(PythonParser):  # Ambiguous Python parser
    """Parser for either Python2 or Python3, and we do not know which."""

    _extensions = [".py", ".pyw"]
    _shebangKeywords = ["python"]
    # The list of keywords is overridden by the Python2/3 specific parsers
    _keywords = pythonKeywords
    # The list of builtins and instances is overridden by the Python2/3 specific parsers
    _builtins = pythonBuiltins
    _instance = pythonInstance

    @classmethod
    def disambiguate(cls, text):
        # try to look into the source...
        # or ... well, ppl should use Python3. Use a shebang to annotate a Python file as Python 2
        return "python3"


class Python2Parser(PythonParser):
    """Parser for Python 2.x code."""

    # The application should choose whether to set the Py 2 specific parser
    _extensions = []
    _shebangKeywords = ["python2"]
    _keywords = python2Keywords
    _builtins = python2Builtins
    _instance = python2Instance


class Python3Parser(PythonParser):
    """Parser for Python 3.x code."""

    # The application should choose whether to set the Py 3 specific parser
    _extensions = []
    _shebangKeywords = ["python3"]
    _keywords = python3Keywords
    _builtins = python3Builtins
    _instance = python3Instance
