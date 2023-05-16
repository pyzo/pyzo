"""
Don't mind this; it just helps me with some experimental stuff.
"""

from pyzo.codeeditor.parsers import Parser, BlockState
from pyzo.codeeditor.parsers.tokens import (
    CommentToken,
    StringToken,
    UnterminatedStringToken,
    IdentifierToken,
    ClassNameToken,
    KeywordToken,
    NumberToken,
    OpenParenToken,
    CloseParenToken,
)

keywords = ('import', 'export',
            'type', 'fun', 'func', 'proc', 'return', 'end',
            'loop', 'for', 'while', 'if', 'then', 'elseif', 'else', 'with', 'do', 'done', 'continue', 'break',
            'in', 'as',
            'true', 'false',
            )


class CellCommentToken(CommentToken):
    """Comments that divide code in chunks/cells."""
    defaultStyle = "bold:yes, underline:yes"


class ZoofParser(Parser):
    """Little parser for experiment with syntax for Zoof."""

    _extensions = ['.zf']

    _keywords = keywords

    def parseLine(self, line, previousState=0):
        """parseLine(line, previousState=0)

        Parse a line of code, yielding tokens.
        previousstate is the state of the previous block, and is used
        to handle line continuation and multiline strings.

        """
        line = str(line)

        pos = 0
        while pos < len(line):
            pos = self._skip_whitespace(line, pos)
            if pos >= len(line):
                break

            if line[pos] == "(":
                token = OpenParenToken(line, pos, pos + 1)
                token._style = "("
                yield token
                pos += 1
            elif line[pos] == ")":
                token = CloseParenToken(line, pos, pos + 1)
                token._style = ")"
                yield token
                pos += 1
            elif line[pos] == '"':
                # Strings
                i0 = pos
                esc = False
                for i in range(i0 + 1, len(line)):
                    if not esc and line[i] == '"':
                        pos = i + 1
                        yield StringToken(line, i0, pos)
                        break
                    esc = line[i] == "\\"
                else:
                    yield UnterminatedStringToken(line, i0, len(line))
                    pos = len(line)
            elif line[pos] == "'":
                # Strings alt
                i0 = pos
                esc = False
                for i in range(i0 + 1, len(line)):
                    if not esc and line[i] == "'":
                        pos = i + 1
                        yield StringToken(line, i0, pos)
                        break
                    esc = line[i] == "\\"
                else:
                    yield UnterminatedStringToken(line, i0, len(line))
                    pos = len(line)
            elif line[pos] == "|":
                # Multiline strings
                yield StringToken(line, pos, len(line))
                pos = len(line)
            elif line[pos] == "#":
                # Pythonic comment
                if pos < len(line) - 1 and line[pos + 1] == "#":
                    yield CellCommentToken(line, pos, len(line))
                else:
                    yield CommentToken(line, pos, len(line))
                pos = len(line)
            elif line[pos] == "/" and pos < len(line) - 1 and line[pos + 1] == "/":
                # C-like comment
                if pos < len(line) - 2 and line[pos + 2] == "/":
                    yield CellCommentToken(line, pos, len(line))
                else:
                    yield CommentToken(line, pos, len(line))
                pos = len(line)
            else:
                # Compose word
                pos0 = pos
                is_alnum = line[pos].isalnum()
                while pos < len(line) and line[pos].isalnum() == is_alnum and line[pos] not in " \t\r\n":
                    pos += 1
                word = line[pos0:pos]
                # What does the word look like?
                if is_alnum:
                    if word in keywords:
                        token = KeywordToken(line, pos0, pos)
                        yield token
                    else:
                        try:
                            float(word)
                        except:
                            token = IdentifierToken(line, pos0, pos)
                            yield token
                        else:
                            token = NumberToken(line, pos0, pos)
                            yield token
                else:
                    token = IdentifierToken(line, pos0, pos)
                    yield token

        yield BlockState(0)

    def _skip_whitespace(self, line, pos):
        while pos < len(line):
            if line[pos] not in " \t\r\n":
                break
            pos += 1
        return pos


if __name__ == "__main__":
    p = ZoofParser()

    line = "type Foo {}"
    tokens = [t for t in p.parseLine(line)]
    for token in tokens:
        print(repr(token))

