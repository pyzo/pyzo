import re
from . import RegexParser, BlockState, from_list, default, include, bygroups

# Import tokens in module namespace
from .tokens import (
    CommentToken,
    StringToken,
    UnterminatedStringToken,
    WhitespaceToken,
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

# Make list of valid operators
operator_list = [
    re.escape(p)
    for p in (
    r'+ - * / % * ** / // @ & | ^ ~ >> << == = := += -= *= /= %= *= **='
    r'@= &= |= ^= >>= <<= >= <= != < >'.split(' ')
    )
]

# Instance sets
python2Instance = set(["self"])

python3Instance = set(["self"])

pythonInstance = python2Instance | python3Instance


class MultilineStringToken(StringToken):
    """Characters representing a multi-line string."""

    defaultStyle = "fore:#7F0000"

class FStringToken(StringToken):
    """Characters representing a f-string token"""

class MultilineFStringToken(MultilineStringToken):
    """Characters representing a multi-line f-string."""


class CellCommentToken(CommentToken):
    """Characters representing a cell separator comment: "##"."""

    defaultStyle = "bold:yes, underline:yes"

xid_continue = '0-9A-Z_a-z\xaa\xb5\xb7\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0300-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u0483-\u0487\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u0591-\u05bd\u05bf\u05c1-\u05c2\u05c4-\u05c5\u05c7\u05d0-\u05ea\u05ef-\u05f2\u0610-\u061a\u0620-\u0669\u066e-\u06d3\u06d5-\u06dc\u06df-\u06e8\u06ea-\u06fc\u06ff\u0710-\u074a\u074d-\u07b1\u07c0-\u07f5\u07fa\u07fd\u0800-\u082d\u0840-\u085b\u0860-\u086a\u0870-\u0887\u0889-\u088e\u0898-\u08e1\u08e3-\u0963\u0966-\u096f\u0971-\u0983\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bc-\u09c4\u09c7-\u09c8\u09cb-\u09ce\u09d7\u09dc-\u09dd\u09df-\u09e3\u09e6-\u09f1\u09fc\u09fe\u0a01-\u0a03\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a3c\u0a3e-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a51\u0a59-\u0a5c\u0a5e\u0a66-\u0a75\u0a81-\u0a83\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abc-\u0ac5\u0ac7-\u0ac9\u0acb-\u0acd\u0ad0\u0ae0-\u0ae3\u0ae6-\u0aef\u0af9-\u0aff\u0b01-\u0b03\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3c-\u0b44\u0b47-\u0b48\u0b4b-\u0b4d\u0b55-\u0b57\u0b5c-\u0b5d\u0b5f-\u0b63\u0b66-\u0b6f\u0b71\u0b82-\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bbe-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcd\u0bd0\u0bd7\u0be6-\u0bef\u0c00-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3c-\u0c44\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c58-\u0c5a\u0c5d\u0c60-\u0c63\u0c66-\u0c6f\u0c80-\u0c83\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbc-\u0cc4\u0cc6-\u0cc8\u0cca-\u0ccd\u0cd5-\u0cd6\u0cdd-\u0cde\u0ce0-\u0ce3\u0ce6-\u0cef\u0cf1-\u0cf3\u0d00-\u0d0c\u0d0e-\u0d10\u0d12-\u0d44\u0d46-\u0d48\u0d4a-\u0d4e\u0d54-\u0d57\u0d5f-\u0d63\u0d66-\u0d6f\u0d7a-\u0d7f\u0d81-\u0d83\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0dca\u0dcf-\u0dd4\u0dd6\u0dd8-\u0ddf\u0de6-\u0def\u0df2-\u0df3\u0e01-\u0e3a\u0e40-\u0e4e\u0e50-\u0e59\u0e81-\u0e82\u0e84\u0e86-\u0e8a\u0e8c-\u0ea3\u0ea5\u0ea7-\u0ebd\u0ec0-\u0ec4\u0ec6\u0ec8-\u0ece\u0ed0-\u0ed9\u0edc-\u0edf\u0f00\u0f18-\u0f19\u0f20-\u0f29\u0f35\u0f37\u0f39\u0f3e-\u0f47\u0f49-\u0f6c\u0f71-\u0f84\u0f86-\u0f97\u0f99-\u0fbc\u0fc6\u1000-\u1049\u1050-\u109d\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u135d-\u135f\u1369-\u1371\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u1715\u171f-\u1734\u1740-\u1753\u1760-\u176c\u176e-\u1770\u1772-\u1773\u1780-\u17d3\u17d7\u17dc-\u17dd\u17e0-\u17e9\u180b-\u180d\u180f-\u1819\u1820-\u1878\u1880-\u18aa\u18b0-\u18f5\u1900-\u191e\u1920-\u192b\u1930-\u193b\u1946-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u19d0-\u19da\u1a00-\u1a1b\u1a20-\u1a5e\u1a60-\u1a7c\u1a7f-\u1a89\u1a90-\u1a99\u1aa7\u1ab0-\u1abd\u1abf-\u1ace\u1b00-\u1b4c\u1b50-\u1b59\u1b6b-\u1b73\u1b80-\u1bf3\u1c00-\u1c37\u1c40-\u1c49\u1c4d-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1cd0-\u1cd2\u1cd4-\u1cfa\u1d00-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u200c-\u200d\u203f-\u2040\u2054\u2071\u207f\u2090-\u209c\u20d0-\u20dc\u20e1\u20e5-\u20f0\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2ce4\u2ceb-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d7f-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u2de0-\u2dff\u3005-\u3007\u3021-\u302f\u3031-\u3035\u3038-\u303c\u3041-\u3096\u3099-\u309a\u309d-\u309f\u30a1-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31bf\u31f0-\u31ff\u3400-\u4dbf\u4e00-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua62b\ua640-\ua66f\ua674-\ua67d\ua67f-\ua6f1\ua717-\ua71f\ua722-\ua788\ua78b-\ua7ca\ua7d0-\ua7d1\ua7d3\ua7d5-\ua7d9\ua7f2-\ua827\ua82c\ua840-\ua873\ua880-\ua8c5\ua8d0-\ua8d9\ua8e0-\ua8f7\ua8fb\ua8fd-\ua92d\ua930-\ua953\ua960-\ua97c\ua980-\ua9c0\ua9cf-\ua9d9\ua9e0-\ua9fe\uaa00-\uaa36\uaa40-\uaa4d\uaa50-\uaa59\uaa60-\uaa76\uaa7a-\uaac2\uaadb-\uaadd\uaae0-\uaaef\uaaf2-\uaaf6\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab69\uab70-\uabea\uabec-\uabed\uabf0-\uabf9\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe00-\ufe0f\ufe20-\ufe2f\ufe33-\ufe34\ufe4d-\ufe4f\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff10-\uff19\uff21-\uff3a\uff3f\uff41-\uff5a\uff65-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U000101fd\U00010280-\U0001029c\U000102a0-\U000102d0\U000102e0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U0001037a\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104a0-\U000104a9\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010570-\U0001057a\U0001057c-\U0001058a\U0001058c-\U00010592\U00010594-\U00010595\U00010597-\U000105a1\U000105a3-\U000105b1\U000105b3-\U000105b9\U000105bb-\U000105bc\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010780-\U00010785\U00010787-\U000107b0\U000107b2-\U000107ba\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00-\U00010a03\U00010a05-\U00010a06\U00010a0c-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a38-\U00010a3a\U00010a3f\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae6\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d27\U00010d30-\U00010d39\U00010e80-\U00010ea9\U00010eab-\U00010eac\U00010eb0-\U00010eb1\U00010efd-\U00010f1c\U00010f27\U00010f30-\U00010f50\U00010f70-\U00010f85\U00010fb0-\U00010fc4\U00010fe0-\U00010ff6\U00011000-\U00011046\U00011066-\U00011075\U0001107f-\U000110ba\U000110c2\U000110d0-\U000110e8\U000110f0-\U000110f9\U00011100-\U00011134\U00011136-\U0001113f\U00011144-\U00011147\U00011150-\U00011173\U00011176\U00011180-\U000111c4\U000111c9-\U000111cc\U000111ce-\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U00011237\U0001123e-\U00011241\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112ea\U000112f0-\U000112f9\U00011300-\U00011303\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133b-\U00011344\U00011347-\U00011348\U0001134b-\U0001134d\U00011350\U00011357\U0001135d-\U00011363\U00011366-\U0001136c\U00011370-\U00011374\U00011400-\U0001144a\U00011450-\U00011459\U0001145e-\U00011461\U00011480-\U000114c5\U000114c7\U000114d0-\U000114d9\U00011580-\U000115b5\U000115b8-\U000115c0\U000115d8-\U000115dd\U00011600-\U00011640\U00011644\U00011650-\U00011659\U00011680-\U000116b8\U000116c0-\U000116c9\U00011700-\U0001171a\U0001171d-\U0001172b\U00011730-\U00011739\U00011740-\U00011746\U00011800-\U0001183a\U000118a0-\U000118e9\U000118ff-\U00011906\U00011909\U0001190c-\U00011913\U00011915-\U00011916\U00011918-\U00011935\U00011937-\U00011938\U0001193b-\U00011943\U00011950-\U00011959\U000119a0-\U000119a7\U000119aa-\U000119d7\U000119da-\U000119e1\U000119e3-\U000119e4\U00011a00-\U00011a3e\U00011a47\U00011a50-\U00011a99\U00011a9d\U00011ab0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c36\U00011c38-\U00011c40\U00011c50-\U00011c59\U00011c72-\U00011c8f\U00011c92-\U00011ca7\U00011ca9-\U00011cb6\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d36\U00011d3a\U00011d3c-\U00011d3d\U00011d3f-\U00011d47\U00011d50-\U00011d59\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d8e\U00011d90-\U00011d91\U00011d93-\U00011d98\U00011da0-\U00011da9\U00011ee0-\U00011ef6\U00011f00-\U00011f10\U00011f12-\U00011f3a\U00011f3e-\U00011f42\U00011f50-\U00011f59\U00011fb0\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00012f90-\U00012ff0\U00013000-\U0001342f\U00013440-\U00013455\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016a60-\U00016a69\U00016a70-\U00016abe\U00016ac0-\U00016ac9\U00016ad0-\U00016aed\U00016af0-\U00016af4\U00016b00-\U00016b36\U00016b40-\U00016b43\U00016b50-\U00016b59\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f4a\U00016f4f-\U00016f87\U00016f8f-\U00016f9f\U00016fe0-\U00016fe1\U00016fe3-\U00016fe4\U00016ff0-\U00016ff1\U00017000-\U000187f7\U00018800-\U00018cd5\U00018d00-\U00018d08\U0001aff0-\U0001aff3\U0001aff5-\U0001affb\U0001affd-\U0001affe\U0001b000-\U0001b122\U0001b132\U0001b150-\U0001b152\U0001b155\U0001b164-\U0001b167\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001bc9d-\U0001bc9e\U0001cf00-\U0001cf2d\U0001cf30-\U0001cf46\U0001d165-\U0001d169\U0001d16d-\U0001d172\U0001d17b-\U0001d182\U0001d185-\U0001d18b\U0001d1aa-\U0001d1ad\U0001d242-\U0001d244\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001d7ce-\U0001d7ff\U0001da00-\U0001da36\U0001da3b-\U0001da6c\U0001da75\U0001da84\U0001da9b-\U0001da9f\U0001daa1-\U0001daaf\U0001df00-\U0001df1e\U0001df25-\U0001df2a\U0001e000-\U0001e006\U0001e008-\U0001e018\U0001e01b-\U0001e021\U0001e023-\U0001e024\U0001e026-\U0001e02a\U0001e030-\U0001e06d\U0001e08f\U0001e100-\U0001e12c\U0001e130-\U0001e13d\U0001e140-\U0001e149\U0001e14e\U0001e290-\U0001e2ae\U0001e2c0-\U0001e2f9\U0001e4d0-\U0001e4f9\U0001e7e0-\U0001e7e6\U0001e7e8-\U0001e7eb\U0001e7ed-\U0001e7ee\U0001e7f0-\U0001e7fe\U0001e800-\U0001e8c4\U0001e8d0-\U0001e8d6\U0001e900-\U0001e94b\U0001e950-\U0001e959\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U0001fbf0-\U0001fbf9\U00020000-\U0002a6df\U0002a700-\U0002b739\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002ebf0-\U0002ee5d\U0002f800-\U0002fa1d\U00030000-\U0003134a\U00031350-\U000323af\U000e0100-\U000e01ef'

xid_start = 'A-Z_a-z\xaa\xb5\xba\xc0-\xd6\xd8-\xf6\xf8-\u02c1\u02c6-\u02d1\u02e0-\u02e4\u02ec\u02ee\u0370-\u0374\u0376-\u0377\u037b-\u037d\u037f\u0386\u0388-\u038a\u038c\u038e-\u03a1\u03a3-\u03f5\u03f7-\u0481\u048a-\u052f\u0531-\u0556\u0559\u0560-\u0588\u05d0-\u05ea\u05ef-\u05f2\u0620-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06e5-\u06e6\u06ee-\u06ef\u06fa-\u06fc\u06ff\u0710\u0712-\u072f\u074d-\u07a5\u07b1\u07ca-\u07ea\u07f4-\u07f5\u07fa\u0800-\u0815\u081a\u0824\u0828\u0840-\u0858\u0860-\u086a\u0870-\u0887\u0889-\u088e\u08a0-\u08c9\u0904-\u0939\u093d\u0950\u0958-\u0961\u0971-\u0980\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09bd\u09ce\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u09fc\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0-\u0ae1\u0af9\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b35-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b71\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb9\u0bd0\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c39\u0c3d\u0c58-\u0c5a\u0c5d\u0c60-\u0c61\u0c80\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cbd\u0cdd-\u0cde\u0ce0-\u0ce1\u0cf1-\u0cf2\u0d04-\u0d0c\u0d0e-\u0d10\u0d12-\u0d3a\u0d3d\u0d4e\u0d54-\u0d56\u0d5f-\u0d61\u0d7a-\u0d7f\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32\u0e40-\u0e46\u0e81-\u0e82\u0e84\u0e86-\u0e8a\u0e8c-\u0ea3\u0ea5\u0ea7-\u0eb0\u0eb2\u0ebd\u0ec0-\u0ec4\u0ec6\u0edc-\u0edf\u0f00\u0f40-\u0f47\u0f49-\u0f6c\u0f88-\u0f8c\u1000-\u102a\u103f\u1050-\u1055\u105a-\u105d\u1061\u1065-\u1066\u106e-\u1070\u1075-\u1081\u108e\u10a0-\u10c5\u10c7\u10cd\u10d0-\u10fa\u10fc-\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1288\u128a-\u128d\u1290-\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12d6\u12d8-\u1310\u1312-\u1315\u1318-\u135a\u1380-\u138f\u13a0-\u13f5\u13f8-\u13fd\u1401-\u166c\u166f-\u167f\u1681-\u169a\u16a0-\u16ea\u16ee-\u16f8\u1700-\u1711\u171f-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17d7\u17dc\u1820-\u1878\u1880-\u18a8\u18aa\u18b0-\u18f5\u1900-\u191e\u1950-\u196d\u1970-\u1974\u1980-\u19ab\u19b0-\u19c9\u1a00-\u1a16\u1a20-\u1a54\u1aa7\u1b05-\u1b33\u1b45-\u1b4c\u1b83-\u1ba0\u1bae-\u1baf\u1bba-\u1be5\u1c00-\u1c23\u1c4d-\u1c4f\u1c5a-\u1c7d\u1c80-\u1c88\u1c90-\u1cba\u1cbd-\u1cbf\u1ce9-\u1cec\u1cee-\u1cf3\u1cf5-\u1cf6\u1cfa\u1d00-\u1dbf\u1e00-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u2071\u207f\u2090-\u209c\u2102\u2107\u210a-\u2113\u2115\u2118-\u211d\u2124\u2126\u2128\u212a-\u2139\u213c-\u213f\u2145-\u2149\u214e\u2160-\u2188\u2c00-\u2ce4\u2ceb-\u2cee\u2cf2-\u2cf3\u2d00-\u2d25\u2d27\u2d2d\u2d30-\u2d67\u2d6f\u2d80-\u2d96\u2da0-\u2da6\u2da8-\u2dae\u2db0-\u2db6\u2db8-\u2dbe\u2dc0-\u2dc6\u2dc8-\u2dce\u2dd0-\u2dd6\u2dd8-\u2dde\u3005-\u3007\u3021-\u3029\u3031-\u3035\u3038-\u303c\u3041-\u3096\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312f\u3131-\u318e\u31a0-\u31bf\u31f0-\u31ff\u3400-\u4dbf\u4e00-\ua48c\ua4d0-\ua4fd\ua500-\ua60c\ua610-\ua61f\ua62a-\ua62b\ua640-\ua66e\ua67f-\ua69d\ua6a0-\ua6ef\ua717-\ua71f\ua722-\ua788\ua78b-\ua7ca\ua7d0-\ua7d1\ua7d3\ua7d5-\ua7d9\ua7f2-\ua801\ua803-\ua805\ua807-\ua80a\ua80c-\ua822\ua840-\ua873\ua882-\ua8b3\ua8f2-\ua8f7\ua8fb\ua8fd-\ua8fe\ua90a-\ua925\ua930-\ua946\ua960-\ua97c\ua984-\ua9b2\ua9cf\ua9e0-\ua9e4\ua9e6-\ua9ef\ua9fa-\ua9fe\uaa00-\uaa28\uaa40-\uaa42\uaa44-\uaa4b\uaa60-\uaa76\uaa7a\uaa7e-\uaaaf\uaab1\uaab5-\uaab6\uaab9-\uaabd\uaac0\uaac2\uaadb-\uaadd\uaae0-\uaaea\uaaf2-\uaaf4\uab01-\uab06\uab09-\uab0e\uab11-\uab16\uab20-\uab26\uab28-\uab2e\uab30-\uab5a\uab5c-\uab69\uab70-\uabe2\uac00-\ud7a3\ud7b0-\ud7c6\ud7cb-\ud7fb\uf900-\ufa6d\ufa70-\ufad9\ufb00-\ufb06\ufb13-\ufb17\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufc5d\ufc64-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdf9\ufe71\ufe73\ufe77\ufe79\ufe7b\ufe7d\ufe7f-\ufefc\uff21-\uff3a\uff41-\uff5a\uff66-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc\U00010000-\U0001000b\U0001000d-\U00010026\U00010028-\U0001003a\U0001003c-\U0001003d\U0001003f-\U0001004d\U00010050-\U0001005d\U00010080-\U000100fa\U00010140-\U00010174\U00010280-\U0001029c\U000102a0-\U000102d0\U00010300-\U0001031f\U0001032d-\U0001034a\U00010350-\U00010375\U00010380-\U0001039d\U000103a0-\U000103c3\U000103c8-\U000103cf\U000103d1-\U000103d5\U00010400-\U0001049d\U000104b0-\U000104d3\U000104d8-\U000104fb\U00010500-\U00010527\U00010530-\U00010563\U00010570-\U0001057a\U0001057c-\U0001058a\U0001058c-\U00010592\U00010594-\U00010595\U00010597-\U000105a1\U000105a3-\U000105b1\U000105b3-\U000105b9\U000105bb-\U000105bc\U00010600-\U00010736\U00010740-\U00010755\U00010760-\U00010767\U00010780-\U00010785\U00010787-\U000107b0\U000107b2-\U000107ba\U00010800-\U00010805\U00010808\U0001080a-\U00010835\U00010837-\U00010838\U0001083c\U0001083f-\U00010855\U00010860-\U00010876\U00010880-\U0001089e\U000108e0-\U000108f2\U000108f4-\U000108f5\U00010900-\U00010915\U00010920-\U00010939\U00010980-\U000109b7\U000109be-\U000109bf\U00010a00\U00010a10-\U00010a13\U00010a15-\U00010a17\U00010a19-\U00010a35\U00010a60-\U00010a7c\U00010a80-\U00010a9c\U00010ac0-\U00010ac7\U00010ac9-\U00010ae4\U00010b00-\U00010b35\U00010b40-\U00010b55\U00010b60-\U00010b72\U00010b80-\U00010b91\U00010c00-\U00010c48\U00010c80-\U00010cb2\U00010cc0-\U00010cf2\U00010d00-\U00010d23\U00010e80-\U00010ea9\U00010eb0-\U00010eb1\U00010f00-\U00010f1c\U00010f27\U00010f30-\U00010f45\U00010f70-\U00010f81\U00010fb0-\U00010fc4\U00010fe0-\U00010ff6\U00011003-\U00011037\U00011071-\U00011072\U00011075\U00011083-\U000110af\U000110d0-\U000110e8\U00011103-\U00011126\U00011144\U00011147\U00011150-\U00011172\U00011176\U00011183-\U000111b2\U000111c1-\U000111c4\U000111da\U000111dc\U00011200-\U00011211\U00011213-\U0001122b\U0001123f-\U00011240\U00011280-\U00011286\U00011288\U0001128a-\U0001128d\U0001128f-\U0001129d\U0001129f-\U000112a8\U000112b0-\U000112de\U00011305-\U0001130c\U0001130f-\U00011310\U00011313-\U00011328\U0001132a-\U00011330\U00011332-\U00011333\U00011335-\U00011339\U0001133d\U00011350\U0001135d-\U00011361\U00011400-\U00011434\U00011447-\U0001144a\U0001145f-\U00011461\U00011480-\U000114af\U000114c4-\U000114c5\U000114c7\U00011580-\U000115ae\U000115d8-\U000115db\U00011600-\U0001162f\U00011644\U00011680-\U000116aa\U000116b8\U00011700-\U0001171a\U00011740-\U00011746\U00011800-\U0001182b\U000118a0-\U000118df\U000118ff-\U00011906\U00011909\U0001190c-\U00011913\U00011915-\U00011916\U00011918-\U0001192f\U0001193f\U00011941\U000119a0-\U000119a7\U000119aa-\U000119d0\U000119e1\U000119e3\U00011a00\U00011a0b-\U00011a32\U00011a3a\U00011a50\U00011a5c-\U00011a89\U00011a9d\U00011ab0-\U00011af8\U00011c00-\U00011c08\U00011c0a-\U00011c2e\U00011c40\U00011c72-\U00011c8f\U00011d00-\U00011d06\U00011d08-\U00011d09\U00011d0b-\U00011d30\U00011d46\U00011d60-\U00011d65\U00011d67-\U00011d68\U00011d6a-\U00011d89\U00011d98\U00011ee0-\U00011ef2\U00011f02\U00011f04-\U00011f10\U00011f12-\U00011f33\U00011fb0\U00012000-\U00012399\U00012400-\U0001246e\U00012480-\U00012543\U00012f90-\U00012ff0\U00013000-\U0001342f\U00013441-\U00013446\U00014400-\U00014646\U00016800-\U00016a38\U00016a40-\U00016a5e\U00016a70-\U00016abe\U00016ad0-\U00016aed\U00016b00-\U00016b2f\U00016b40-\U00016b43\U00016b63-\U00016b77\U00016b7d-\U00016b8f\U00016e40-\U00016e7f\U00016f00-\U00016f4a\U00016f50\U00016f93-\U00016f9f\U00016fe0-\U00016fe1\U00016fe3\U00017000-\U000187f7\U00018800-\U00018cd5\U00018d00-\U00018d08\U0001aff0-\U0001aff3\U0001aff5-\U0001affb\U0001affd-\U0001affe\U0001b000-\U0001b122\U0001b132\U0001b150-\U0001b152\U0001b155\U0001b164-\U0001b167\U0001b170-\U0001b2fb\U0001bc00-\U0001bc6a\U0001bc70-\U0001bc7c\U0001bc80-\U0001bc88\U0001bc90-\U0001bc99\U0001d400-\U0001d454\U0001d456-\U0001d49c\U0001d49e-\U0001d49f\U0001d4a2\U0001d4a5-\U0001d4a6\U0001d4a9-\U0001d4ac\U0001d4ae-\U0001d4b9\U0001d4bb\U0001d4bd-\U0001d4c3\U0001d4c5-\U0001d505\U0001d507-\U0001d50a\U0001d50d-\U0001d514\U0001d516-\U0001d51c\U0001d51e-\U0001d539\U0001d53b-\U0001d53e\U0001d540-\U0001d544\U0001d546\U0001d54a-\U0001d550\U0001d552-\U0001d6a5\U0001d6a8-\U0001d6c0\U0001d6c2-\U0001d6da\U0001d6dc-\U0001d6fa\U0001d6fc-\U0001d714\U0001d716-\U0001d734\U0001d736-\U0001d74e\U0001d750-\U0001d76e\U0001d770-\U0001d788\U0001d78a-\U0001d7a8\U0001d7aa-\U0001d7c2\U0001d7c4-\U0001d7cb\U0001df00-\U0001df1e\U0001df25-\U0001df2a\U0001e030-\U0001e06d\U0001e100-\U0001e12c\U0001e137-\U0001e13d\U0001e14e\U0001e290-\U0001e2ad\U0001e2c0-\U0001e2eb\U0001e4d0-\U0001e4eb\U0001e7e0-\U0001e7e6\U0001e7e8-\U0001e7eb\U0001e7ed-\U0001e7ee\U0001e7f0-\U0001e7fe\U0001e800-\U0001e8c4\U0001e900-\U0001e943\U0001e94b\U0001ee00-\U0001ee03\U0001ee05-\U0001ee1f\U0001ee21-\U0001ee22\U0001ee24\U0001ee27\U0001ee29-\U0001ee32\U0001ee34-\U0001ee37\U0001ee39\U0001ee3b\U0001ee42\U0001ee47\U0001ee49\U0001ee4b\U0001ee4d-\U0001ee4f\U0001ee51-\U0001ee52\U0001ee54\U0001ee57\U0001ee59\U0001ee5b\U0001ee5d\U0001ee5f\U0001ee61-\U0001ee62\U0001ee64\U0001ee67-\U0001ee6a\U0001ee6c-\U0001ee72\U0001ee74-\U0001ee77\U0001ee79-\U0001ee7c\U0001ee7e\U0001ee80-\U0001ee89\U0001ee8b-\U0001ee9b\U0001eea1-\U0001eea3\U0001eea5-\U0001eea9\U0001eeab-\U0001eebb\U00020000-\U0002a6df\U0002a700-\U0002b739\U0002b740-\U0002b81d\U0002b820-\U0002cea1\U0002ceb0-\U0002ebe0\U0002ebf0-\U0002ee5d\U0002f800-\U0002fa1d\U00030000-\U0003134a\U00031350-\U000323af'

# Regex for possible syntax for an identifier using unicode
uni_name = f"[{xid_start}][{xid_continue}]*"

class Python3Parser(RegexParser):

    _extensions = ['.py', '.pyw']
    _shebangKeywords = ["python3"]
    _keywords = python3Keywords
    _builtins = python3Builtins
    _instance = python3Instance

    states = {
        "root": [
            # for speed: immediate match on empty lines
            (r"\Z", WhitespaceToken),
            (r"\A#!.+$", CommentToken), # Hashbang
            (r"#[ \t]*(?i:todo|2do|fixme).*$", TodoCommentToken),
            (r"#.*$", CommentToken),  # Simple comment
            (r"^[ \t]*##.*$", CellCommentToken),  # Comment cell
            (
                rf"(def)([ \t]+)({uni_name})",
                bygroups(KeywordToken, WhitespaceToken, FunctionNameToken),
            ),
            (
                rf"(class)([ \t]+)({uni_name})",
                bygroups(KeywordToken, WhitespaceToken, ClassNameToken),
            ),
            (rf"(@)({uni_name})", bygroups(NonIdentifierToken, IdentifierToken)), # Decorator
            include("expression"),
        ],
        "expression": [
            # Parenthesis
            (r"[\(\{\[]", OpenParenToken),
            (r"[\)\}\]]", CloseParenToken),
            # Strings
            include("string"),
            # Numbers
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', NumberToken), # Float
            (r'0[oO](?:_?[0-7])+', NumberToken), # Oct
            (r'0[bB](?:_?[01])+', NumberToken), # Bin
            (r'0[xX](?:_?[a-fA-F0-9])+', NumberToken), # Hex
            (r'\d(?:_?\d)*', NumberToken), # Int
            # Builtins
            from_list(_builtins, BuiltinsToken, suffix=r"\b"),
            # Keywords
            from_list(
                _keywords,
                KeywordToken,
                suffix=r"\b",
            ),
            from_list(["True", "False", "None"], KeywordToken, suffix=r"\b"),
            # Soft-Keywords (ignore _ for simplicity)
            (
                r"^([ \t]*)(match|case)\b",
                bygroups(WhitespaceToken, KeywordToken),
            ),  # TODO improve this
            # # Type hints
            # (r'(->)([ \t]*)(.+?)([ \t]*)(:)', bygroups(NonIdentifierToken, Whitespace, TypeHint, Punctuation)),
            # (r'(:)([ \t]*)(.+?)(?:[=\),])',bygroups(Punctuation, Whitespace, TypeHint)),
            # Operators
            from_list(operator_list, NonIdentifierToken),
            # Regular name
            from_list(_instance, InstanceToken, suffix=r"\b"), # find "self"
            (uni_name, IdentifierToken),
            # Punctuation
            (re.escape("..."), NonIdentifierToken), # Elipsis
            (rf"(\.)({uni_name})", bygroups(NonIdentifierToken, IdentifierToken)),

            (r"[;:,\\]", NonIdentifierToken),
            (r"[ \t]+", WhitespaceToken),
            # Invalid specifiers
            (r".+?", IllegalToken),  # Default in case nothing else matches
        ],
        "string":[
            include("string-multiline-dispatcher"),
            include("string-oneline-dispatcher"),
            include("fstring-multiline-dispatcher"),
            include("fstring-oneline-dispatcher"),
        ],
        "string-multiline-dispatcher": [
            (r"([uUrRbB]{,2})(?=''')", NonIdentifierToken, "string-single-multiline"), # String literal
            (r'([uUrRbB]{,2})(?=""")', NonIdentifierToken, "string-double-multiline"), # string literal
        ],
        "string-oneline-dispatcher": [
            (r"([uUrRbB]{,2})(?=')", NonIdentifierToken, "string-single-oneline"), # String literal
            (r'([uUrRbB]{,2})(?=")', NonIdentifierToken, "string-double-oneline"), # String literal
        ],
        "fstring-multiline-dispatcher":[
            (r"([uUrRbBfFtT]{1,2})(?=''')", NonIdentifierToken, "fstring-single-multiline"), # String literal
            (r'([uUrRbBfFtT]{1,2})(?=""")', NonIdentifierToken, "fstring-double-multiline"), # String literal
        ],
        "fstring-oneline-dispatcher": [
            (r"([uUrRbBfFtT]{1,2})(?=')", NonIdentifierToken, "fstring-single-oneline"), # String literal
            (r'([uUrRbBfFtT]{1,2})(?=")', NonIdentifierToken, "fstring-double-oneline"), # String literal
        ],
        "string-single-multiline": [
            # Search for begining and end of string
            (r"'''.*?'''", MultilineStringToken, "#pop"),
            # Search for begining and end of line
            (r"'''.*?\Z", MultilineStringToken),
            # Search for end of string
            (r".*?'''", MultilineStringToken, "#pop"),
            # If previous do not match, whole line is string. Keep going.
            (r".*?\Z", MultilineStringToken),
        ],
        "string-double-multiline": [
            # Same as string-single-multiline
            (r'""".*?"""', MultilineStringToken, "#pop"),
            (r'""".*?\Z', MultilineStringToken),
            (r'.*?"""', MultilineStringToken, "#pop"),
            (r".*?\Z", MultilineStringToken),
        ],
        "string-single-oneline": [
            # Search for begining and end of string
            (r"'.*?'", StringToken, "#pop"),
            # Search for begining and end of line with line continuation \
            (r"'.*?\\[ \t]*\Z", StringToken),
            # Search for begining and end of line without line continuation
            (r"'.*?\Z", UnterminatedStringToken, "#pop"),
            # Search for end of string (continue from line continuation)
            (r".*?'", StringToken, "#pop"),
            # If previous do not match, unterminated string.
            (r".*?\Z", UnterminatedStringToken, "#pop"),
        ],
        "string-double-oneline": [
            # Same as string-single-oneline
            (r'".*?"', StringToken, "#pop"),
            (r'".*?\\[ \t]*\Z', StringToken),
            (r'".*?\Z', UnterminatedStringToken, "#pop"),
            (r'.*?"', StringToken, "#pop"),
            (r".*?\Z", UnterminatedStringToken, "#pop"),
        ],
        "expression-fstring": [
            (r"![ars]", NonIdentifierToken),  # !r !s or !a
            # (r":.*?(?=\})", NonIdentifierToken, "#pop"),  # {... :.2f}
            (
                r"(?=\})",
                None,
                "#pop",
            ),  # todo this could be better : f"{{}}" is an issue
            include("expression"),
        ],
        "fstring-single-multiline": [
            # Search for formatting cell
            # ((?!''').)* is here to ensure that a cell isn't found out
            # of the string
            (r"'''((?!''').)*?\{", MultilineFStringToken, "expression-fstring"),
            # In case of multiple formatting cells, or cell after new line
            (r"\}?((?!''').)*?\{", MultilineFStringToken, "expression-fstring"),
            # Search for end of cell and end of string
            (r"\}.*?'''", MultilineFStringToken, "#pop"),
            # Search for end of cell and no end of string
            (r"\}.*?\Z", MultilineFStringToken),
            # Search for beginning and end of string (no formatting cell)
            (r"'''.*?'''", MultilineFStringToken, "#pop"),
            # If previous do not match, whole line is string. Keep going.
            (r".*?\Z", MultilineFStringToken),
        ],
        "fstring-double-multiline": [
            # Same as fstring-single-multiline
            (r'"""((?!""").)*?\{', MultilineFStringToken, "expression-fstring"),
            (r'\}?((?!""").)*?\{', MultilineFStringToken, "expression-fstring"),
            (r'\}.*?"""', MultilineFStringToken, "#pop"),
            (r"\}.*?\Z", MultilineFStringToken),
            (r'""".*?"""', MultilineFStringToken, "#pop"),
            (r".*?\Z", MultilineFStringToken),
        ],
        "fstring-single-oneline": [
            # Search for formatting cell
            (r"'((?!').)*?\{", FStringToken, "expression-fstring"),
            # In case of multiple formatting cells
            (r"\}((?!').)*?\{", FStringToken, "expression-fstring"),
            # Search for begining and end of string
            (r"'.*?'", FStringToken, "#pop"),
            # Search for end of string
            (r".*?'", FStringToken, "#pop"),
            # Search for line continuation
            (r".*?\\[ \t]*\Z", FStringToken),
            # If previous do not match, whole line is string. pop.
            (r".*?\Z", FStringToken, "#pop"),
        ],
        "fstring-double-oneline": [
            # Same as fstring-single-oneline
            (r'"((?!").)*?\{', FStringToken, "expression-fstring"),
            (r'\}((?!").)*?\{', FStringToken, "expression-fstring"),
            (r'.*?"', FStringToken, "#pop"),
            (r".*?\\[ \t]*\Z", FStringToken),
            (r".*?\Z", FStringToken, "#pop"),
        ],
    }




# class PythonParser(Parser):
#     """Parser for Python in general."""
#
#     _extensions = []
#     _shebangKeywords = []
#     # The list of keywords is overridden by the Python2/3 specific parsers
#     _keywords = set()
#     # The list of builtins and instances is overridden by the Python2/3 specific parsers
#     _builtins = set()
#     _instance = set()
#
#     def _identifierState(self, identifier=None):
#         """Given an identifier returns the identifier state:
#         3 means the current identifier can be a function.
#         4 means the current identifier can be a class.
#         0 otherwise.
#
#         This method enables storing the state during the line,
#         and helps the Cython parser to reuse the Python parser's code.
#         """
#         if identifier is None:
#             # Explicit get/reset
#             try:
#                 state = self._idsState
#             except Exception:
#                 state = 0
#             self._idsState = 0
#             return state
#         elif identifier == "def":
#             # Set function state
#             self._idsState = 3
#             return 3
#         elif identifier == "class":
#             # Set class state
#             self._idsState = 4
#             return 4
#         else:
#             # This one can be func or class, next one can't
#             state = self._idsState
#             self._idsState = 0
#             return state
#
#     def parseLine(self, line, previousState=0):
#         """Parse a line of Python code, returning a list of tokens.
#         previousState is the state of the previous block, and is used
#         to handle line continuation and multiline strings.
#         """
#
#         # Init
#         pos = 0  # Position following the previous match
#
#         tokensForLine = []
#
#         # identifierState and previousState values:
#         # 0: nothing special
#         # 1: multiline comment single qoutes
#         # 2: multiline comment double quotes
#         # 3: a def keyword
#         # 4: a class keyword
#         # 5: a single quote string literal (non-multiline) line-continued by a backslash
#         # 6: a double quote string literal (non-multiline) line-continued by a backslash
#
#         # Handle line continuation after def or class
#         # identifierState is 3 or 4 if the previous identifier was 3 or 4
#         if previousState == 3 or previousState == 4:
#             self._identifierState({3: "def", 4: "class"}[previousState])
#         else:
#             self._identifierState(None)
#
#         if previousState in [1, 2, 5, 6]:
#             if previousState <= 2:
#                 token = MultilineStringToken(line, 0, 0)
#             else:
#                 token = StringToken(line, 0, 0)
#             token._style = ["", "'''", '"""', None, None, "'", '"'][previousState]
#             tokens = self._findEndOfString(line, token)
#             # Process tokens
#             for token in tokens:
#                 tokensForLine.append(token)
#                 if isinstance(token, BlockState):
#                     return tokensForLine
#             pos = token.end
#
#         # Enter the main loop that iterates over the tokens and skips strings
#         while True:
#             # Get next tokens
#             tokens = self._findNextToken(line, pos)
#             if not tokens:
#                 self._promoteMatchCaseSoftKeywords(tokensForLine)
#                 return tokensForLine
#             elif isinstance(tokens[-1], StringToken):
#                 moreTokens = self._findEndOfString(line, tokens[-1])
#                 tokens = tokens[:-1] + moreTokens
#
#             # Process tokens
#             for token in tokens:
#                 tokensForLine.append(token)
#                 if isinstance(token, BlockState):
#                     return tokensForLine
#             pos = token.end
#
#     @staticmethod
#     def _promoteMatchCaseSoftKeywords(tokens):
#         """promotes identifier tokens "match" and "case" to keyword tokens if appropriate
#
#         list "tokens" contains the tokens of the current line
#
#         A simple algorithm will be used that only knows about the tokens of the current
#         line, but not about the lines before or after.
#         If "match" or "case" is a keyword, its token in list "tokens" will be replaced by
#         a keyword token.
#
#         "match" or "case" will be considered a keyword if one of the two patterns is found:
#
#         1.
#             optional whitespace
#             identifier token "match" or "case"
#             all parenthesis like tokens ([{}]) must be properly closed
#             colon (with optional whitespace)
#             optional comment
#
#         2.
#             optional whitespace
#             identifier token "match" or "case"
#             parenthesis like tokens ([{}]) can be still open on the right side,
#                 assuming that they will be closed in the following lines
#             optional comment
#
#
#         single line examples where match or case is promoted to a keyword:
#             match x:  # random comment
#             match (x):
#             match(
#             case []:
#             case {"x": x,
#             case {"x": x,  # another comment
#             case (0, 0):
#
#         single line examples where match or case is NOT promoted to a keyword:
#             match x
#             case [(]:
#             case {"x": x,}
#             case {"x": x,)
#             case (0, 0)
#
#         False positives, i.e. promoting an identifier to a keyword erroneously, are very
#         unlikely. One example is the line "match(" because it could be either followed by
#         line "x)" and make it a normal function call, or it could be followed by line
#         "x):" and make it a match statement.
#         """
#
#         indMatchCase = None
#         closingParens = {"(": ")", "[": "]", "{": "}"}
#         parensStack = []
#         for i, token in enumerate(tokens):
#             if i == 0 and isinstance(token, NonIdentifierToken):
#                 if str(token).isspace():
#                     continue  # ignore whitespace before match or case identifiers
#                 else:
#                     return
#             elif indMatchCase is None:
#                 if isinstance(token, IdentifierToken) and str(token) in (
#                     "match",
#                     "case",
#                 ):
#                     indMatchCase = i
#                 else:
#                     return
#             elif isinstance(token, OpenParenToken):
#                 parensStack.append(closingParens[str(token)])
#             elif isinstance(token, CloseParenToken):
#                 if len(parensStack) > 0 and parensStack[-1] == str(token):
#                     parensStack.pop()
#                 else:
#                     return  # invalid parentheses (or square brackets or curly brackets)
#
#         if indMatchCase is None:
#             return
#         i2 = -1  # index of the last token, not counting comment tokens
#         if isinstance(tokens[i2], CommentToken):
#             i2 = -2  # ignore the comment token at the end
#             if len(tokens) < 3:
#                 return
#
#         if len(parensStack) > 0:
#             pass  # probably a match or case keyword, depending on the lines that follow
#         elif (
#             isinstance(tokens[i2], NonIdentifierToken)
#             and str(tokens[i2]).strip() == ":"
#         ):
#             pass  # very likely a match or case keyword
#         else:
#             return  # not a match or case keyword
#
#         t = tokens[indMatchCase]
#         tokens[indMatchCase] = KeywordToken(t.line, t.start, t.end)
#
#     def _findEndOfString(self, line, token):
#         """Find the end of a string. Returns (token, endToken). The first
#         is the given token or a replacement (UnterminatedStringToken).
#         The latter is None, or the BlockState. If given, the line is
#         finished.
#
#         """
#
#         # Set state
#         self._identifierState(None)
#
#         # Find the matching end in the rest of the line
#         # Do not use the start parameter of search, since ^ does not work then
#         style = token._style
#         endMatch = endProgs[style].search(line[token.end :])
#
#         if endMatch:
#             # The string does end on this line
#             tokenArgs = line, token.start, token.end + endMatch.end()
#             if style in ['"""', "'''"]:
#                 token = MultilineStringToken(*tokenArgs)
#             else:
#                 token.end = token.end + endMatch.end()
#             return [token]
#         else:
#             # The string does not end on this line
#             tokenArgs = line, token.start, token.end + len(line)
#             if style == "'''":
#                 return [MultilineStringToken(*tokenArgs), BlockState(1)]
#             elif style == '"""':
#                 return [MultilineStringToken(*tokenArgs), BlockState(2)]
#             else:
#                 lineContMatch = stringLineContinuation.search(line[token.end :])
#                 if lineContMatch:
#                     return [
#                         StringToken(*tokenArgs),
#                         BlockState(5 if style == "'" else 6),
#                     ]
#                 return [UnterminatedStringToken(*tokenArgs)]
#
#     def _findNextToken(self, line, pos):
#         """Returns a token or None if no new tokens can be found."""
#
#         # Init tokens, if pos too large, we are done
#         if pos > len(line):
#             return None
#         tokens = []
#
#         # Find the start of the next string or comment
#         match = tokenProg.search(line, pos)
#
#         # Process the Non-Identifier between pos and match.start()
#         # or end of line
#         nonIdentifierEnd = match.start() if match else len(line)
#
#         # Return the Non-Identifier token if non-null
#         # todo: here it goes wrong (allow returning more than one token?)
#         token = NonIdentifierToken(line, pos, nonIdentifierEnd)
#         strippedNonIdentifier = str(token).strip()
#         if token:
#             tokens.append(token)
#
#         # Do checks for line continuation and identifierState
#         # Is the last non-whitespace a line-continuation character?
#         if strippedNonIdentifier.endswith("\\"):
#             lineContinuation = True
#             # If there are non-whitespace characters after def or class,
#             # cancel the identifierState
#             if strippedNonIdentifier != "\\":
#                 self._identifierState(None)
#         else:
#             lineContinuation = False
#             # If there are non-whitespace characters after def or class,
#             # cancel the identifierState
#             if strippedNonIdentifier != "":
#                 self._identifierState(None)
#
#         # If no match, we are done processing the line
#         if not match:
#             if lineContinuation:
#                 tokens.append(BlockState(self._identifierState()))
#             return tokens
#
#         # The rest is to establish what identifier we are dealing with
#
#         # Comment
#         if match.group() == "#":
#             matchStart = match.start()
#             if not line[:matchStart].strip() and (
#                 line[matchStart:].startswith(("##", "#%%", "# %%"))
#             ):
#                 tokens.append(CellCommentToken(line, matchStart, len(line)))
#             elif self._isTodoItem(line[matchStart + 1 :]):
#                 tokens.append(TodoCommentToken(line, matchStart, len(line)))
#             else:
#                 tokens.append(CommentToken(line, matchStart, len(line)))
#             if lineContinuation:
#                 tokens.append(BlockState(self._identifierState()))
#             return tokens
#
#         # If there are non-whitespace characters after def or class,
#         # cancel the identifierState (this time, also if there is just a \
#         # since apparently it was not on the end of a line)
#         if strippedNonIdentifier != "":
#             self._identifierState(None)
#
#         # Identifier ("a word or number") Find out whether it is a key word
#         if match.group(4) is not None:
#             identifier = match.group(4)
#             tokenArgs = line, match.start(), match.end()
#
#             # Set identifier state
#             identifierState = self._identifierState(identifier)
#
#             if identifier in self._keywords:
#                 tokens.append(KeywordToken(*tokenArgs))
#             elif identifier in self._builtins and (
#                 "." + identifier not in line and "def " + identifier not in line
#             ):
#                 tokens.append(BuiltinsToken(*tokenArgs))
#             elif identifier in self._instance:
#                 tokens.append(InstanceToken(*tokenArgs))
#             elif identifier[0] in "0123456789":
#                 self._identifierState(None)
#                 tokens.append(NumberToken(*tokenArgs))
#             else:
#                 if identifierState == 3 and line[match.end() :].lstrip().startswith(
#                     "("
#                 ):
#                     tokens.append(FunctionNameToken(*tokenArgs))
#                 elif identifierState == 4:
#                     tokens.append(ClassNameToken(*tokenArgs))
#                 else:
#                     tokens.append(IdentifierToken(*tokenArgs))
#
#         elif match.group(3) is not None:
#             # We have matched a string-start
#             # Find the string style ( ' or " or ''' or """)
#             token = StringToken(line, match.start(), match.end())
#             token._style = match.group(3)  # The style is in match group 3
#             tokens.append(token)
#         elif match.group(5) is not None:
#             token = OpenParenToken(line, match.start(), match.end())
#             token._style = match.group(5)
#             tokens.append(token)
#         elif match.group(6) is not None:
#             token = CloseParenToken(line, match.start(), match.end())
#             token._style = match.group(6)
#             tokens.append(token)
#         elif match.group(7) is not None:
#             token = IllegalToken(line, match.start(), match.end())
#             token._style = match.group(7)
#             tokens.append(token)
#         # Done
#         return tokens
#
#


class PythonParser(Python3Parser):
    """Parser for either Python2 or Python3, and we do not know which."""

    @classmethod
    def disambiguate(cls, text):
        # try to look into the source...
        # or ... well, ppl should use Python3. Use a shebang to annotate
        # a Python file as Python 2
        return "python3"



class Python2Parser(RegexParser):
    """Parser for Python 2.x code."""

    # The application should choose whether to set the Py 2 specific parser
    _extensions = []
    _shebangKeywords = ["python2"]
    _keywords = python2Keywords
    _builtins = python2Builtins
    _instance = python2Instance

    # Same as for python3, but use proper builtins / keywords and remove
    # fstring parts

    states = {
        "root": [
            # for speed: immediate match on empty lines
            (r"\Z", WhitespaceToken),
            (r"\A#!.+$", CommentToken), # Hashbang
            (r"#[ \t]*(?i:todo|2do|fixme).*$", TodoCommentToken),
            (r"#.*$", CommentToken),  # Simple comment
            (r"^[ \t]*##.*$", CellCommentToken),  # Comment cell
            (
                rf"(def)([ \t]+)({uni_name})",
                bygroups(KeywordToken, WhitespaceToken, FunctionNameToken),
            ),
            (
                rf"(class)([ \t]+)({uni_name})",
                bygroups(KeywordToken, WhitespaceToken, ClassNameToken),
            ),
            (rf"(@)({uni_name})", bygroups(NonIdentifierToken, IdentifierToken)), # Decorator
            include("expression"),
        ],
        "expression": [
            # Parenthesis
            (r"[\(\{\[]", OpenParenToken),
            (r"[\)\}\]]", CloseParenToken),
            # Strings
            include("string"),
            # Numbers
            (r'(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)'
             r'([eE][+-]?\d(?:_?\d)*)?', NumberToken), # Float
            (r'0[oO](?:_?[0-7])+', NumberToken), # Oct
            (r'0[bB](?:_?[01])+', NumberToken), # Bin
            (r'0[xX](?:_?[a-fA-F0-9])+', NumberToken), # Hex
            (r'\d(?:_?\d)*', NumberToken), # Int
            # Builtins
            from_list(_builtins, BuiltinsToken, suffix=r"\b"),
            # Keywords
            from_list(
                _keywords,
                KeywordToken,
                suffix=r"\b",
            ),
            from_list(["True", "False", "None"], KeywordToken, suffix=r"\b"),
            # Operators
            from_list(operator_list, NonIdentifierToken),
            # Regular name
            from_list(_instance, InstanceToken, suffix=r"\b"), # find "self"
            (uni_name, IdentifierToken),
            # Punctuation
            (re.escape("..."), NonIdentifierToken), # Elipsis
            (rf"(\.)({uni_name})", bygroups(NonIdentifierToken, IdentifierToken)),

            (r"[;:,\\]", NonIdentifierToken),
            (r"[ \t]+", WhitespaceToken),
            # Invalid specifiers
            (r".+?", IllegalToken),  # Default in case nothing else matches
        ],
        "string":[
            include("string-multiline-dispatcher"),
            include("string-oneline-dispatcher"),
        ],
        "string-multiline-dispatcher": [
            (r"([uUrRbB]{,2})(?=''')", NonIdentifierToken, "string-single-multiline"), # String literal
            (r'([uUrRbB]{,2})(?=""")', NonIdentifierToken, "string-double-multiline"), # string literal
        ],
        "string-oneline-dispatcher": [
            (r"([uUrRbB]{,2})(?=')", NonIdentifierToken, "string-single-oneline"), # String literal
            (r'([uUrRbB]{,2})(?=")', NonIdentifierToken, "string-double-oneline"), # String literal
        ],
        "string-single-multiline": [
            # Search for begining and end of string
            (r"'''.*?'''", MultilineStringToken, "#pop"),
            # Search for begining and end of line
            (r"'''.*?\Z", MultilineStringToken),
            # Search for end of string
            (r".*?'''", MultilineStringToken, "#pop"),
            # If previous do not match, whole line is string. Keep going.
            (r".*?\Z", MultilineStringToken),
        ],
        "string-double-multiline": [
            # Same as string-single-multiline
            (r'""".*?"""', MultilineStringToken, "#pop"),
            (r'""".*?\Z', MultilineStringToken),
            (r'.*?"""', MultilineStringToken, "#pop"),
            (r".*?\Z", MultilineStringToken),
        ],
        "string-single-oneline": [
            # Search for begining and end of string
            (r"'.*?'", StringToken, "#pop"),
            # Search for begining and end of line with line continuation \
            (r"'.*?\\[ \t]*\Z", StringToken),
            # Search for begining and end of line without line continuation
            (r"'.*?\Z", UnterminatedStringToken, "#pop"),
            # Search for end of string (continue from line continuation)
            (r".*?'", StringToken, "#pop"),
            # If previous do not match, unterminated string.
            (r".*?\Z", UnterminatedStringToken, "#pop"),
        ],
        "string-double-oneline": [
            # Same as string-single-oneline
            (r'".*?"', StringToken, "#pop"),
            (r'".*?\\[ \t]*\Z', StringToken),
            (r'".*?\Z', UnterminatedStringToken, "#pop"),
            (r'.*?"', StringToken, "#pop"),
            (r".*?\Z", UnterminatedStringToken, "#pop"),
        ],
    }
