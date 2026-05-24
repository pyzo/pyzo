"""
This is a short tutorial on how to create a parser for syntax
highlighting in Pyzo using the RegexParser base class.

The RegexParseer is *heavily* inspired by the Pyments module. The
Pygments documentation of the RegexParser is available at
https://pygments.org/docs/lexerdevelopment/#regexlexer

While the pyzo implementation of RegexParser differs slightly from the
Pygments one, most of the same principles are applicable. The main
features that are not available are the "using" function and the
"combined" state. In addition, the few behaviour differences are due
to the integration into pyzo.
"""

## Import relevant libraries

from pyzo.codeeditor.parsers import RegexParser, from_list, default, include, bygroups
from pyzo.codeeditor.parsers.tokens import (
    Token,
    TextToken,
    WhitespaceToken,
    OpenParenToken,
    CloseParenToken,
    KeywordToken,
)


## Simple example
# In essence, a regex parser keeps track of a stack of states. The
# current state, which is on top of the stack, contains a number of
# possible cases, which are regex patterns that can be matched to
# Tokens. Every parser has to have a "root" state, which will always
# be at the bottom of the stack.

# Here is the official documentation of the re module, which is used
# for regex matching: https://docs.python.org/3/library/re.html


class PunctuationToken(Token):
    pass


class SimpleWordParser(RegexParser):
    """Here is a very simple example of a parser to find words,
    whitespaces and some punctuation in a sentence, with a single state
    "root".
    """

    states = {
        "root": [
            (r"\w+\b", TextToken),  # words
            (r"\s+\b", WhitespaceToken),
            (r"[\.\',;\?]", PunctuationToken),  # punctuation
        ]
    }


simpleWordParser = SimpleWordParser()

for tok in simpleWordParser.parseLine("It's over Anakin, I have the high ground.", 0):
    print(tok.__repr__())


## Slightly more complex example with two states
class InParenToken(TextToken):
    pass


class ParenParser(RegexParser):
    """Now this is a slightly more complex parser with two states,
    designed to tokenize any text in parenthesis as a InParenToken, and
    find opening and closing parenthesis.
    """

    states = {
        "root": [
            (
                r"\(",
                OpenParenToken,
                "in-paren",
            ),  # Add 'in-paren' state to stack if match
            (r"\w+\b", TextToken),
            (r"\s+\b", WhitespaceToken),
            (r"[\.,;\?]", PunctuationToken),
        ],
        "in-paren": [
            (r"\)", CloseParenToken, "#pop"),  # Remove current state from stack
            (r"\w+\b", InParenToken),
            (r"\s+\b", InParenToken),
        ],
    }


ParenParser = ParenParser()

for tok in ParenParser.parseLine("It's over Anakin, (I have the high ground)", 0):
    print(tok.__repr__())

## Contrived example for the sake of showing off helper functions


class ContrivedParser(RegexParser):
    """A parser that does not serve any practical application but to
    show off some of the helper functions of the RegexParser
    """

    states = {
        "root": [
            (r"Anakin", TextToken, "find-skaywalker"),
            # Add "key\b" and "word\b" as possible cases
            from_list(["key", "word"], KeywordToken, suffix=r"\b"),
            # Assign each given token to the corresponding group if a
            # match is found.
            (r"(high)(\s+)(ground)", bygroups(TextToken, WhitespaceToken, TextToken)),
            # Add "whitespace" cases into "root"
            include("whitespace"),
            (r"\w+\b", TextToken),
        ],
        "find-skaywalker": [
            include("whitespace"),
            (r"Skywalker\b", TextToken, "#pop"),
            # Go to given state if nothing else matches. Here "#pop"
            # means that the current state will be removed from the
            # stack if no match is found.
            default("#pop"),
        ],
        "whitespace": [
            (r"\s+\b", WhitespaceToken),
        ],
    }

contrivedParser = ContrivedParser()
for tok in contrivedParser.parseLine("It's key Anakin, I word the high ground.", 0):
    print(tok.__repr__())