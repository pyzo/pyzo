"""Subpackage parsers

This subpackage contains all the syntax parsers for the
different languages.

"""

""" CREATING PARSERS

Making a parser requires these things:
  * Place a module in the parsers directory, which has a name
    ending in "_parser.py"
  * In the module implement one or more classes that inherit
    from ..parsers.Parser (or a derived class), and
    implement the parseLine method.
  * The module should import all the tokens in whiches to use
    from ..parsers.tokens. New tokens can also be
    defined by subclassing one of the token classes.
  * In codeeditor/parsers/__init__.py, add the new module to the
    list of imported parsers.

"""

import sys

from dataclasses import dataclass
from collections import defaultdict
import re

from . import tokens


class BlockState:
    """BlockState(state=0, info=None)

    The blockstate object should be used by parsers to
    return the block state of the processed line.

    This would typically be the last token in a line, but this might also
    be before the last token in a line. Even multiple BlockState objects
    can be present in a line, in which case the last one is considered valid.
    """

    isToken = False

    def __init__(self, state=0, info=None):
        self._state = int(state)
        self._info = info

    @property
    def state(self):
        """The integer value representing the block state."""
        return self._state

    @property
    def info(self):
        """Get the information corresponding to the block."""
        return self._info


# Base parser class (needs to be defined before importing parser modules)
class Parser:
    """Base parser class.
    All parsers should inherit from this class.
    This base class generates a 'TextToken' for each line
    """

    _extensions = []
    _shebangKeywords = []
    _keywords = []

    @classmethod
    def getParserName(cls):
        name = cls.__name__
        if name.endswith("Parser") and len(name) >= 6:
            name = name[:-6].lower()
        return name

    @classmethod
    def disambiguate(cls, text):
        return cls.getParserName()

    def parseLine(self, line, previousState=0):
        """The method that should be implemented by the parser. The
        previousState argument can be used to determine how
        the previous block ended (e.g. for multiline comments). It
        is an integer, the meaning of which is only known to the
        specific parser.

        This method should reaturn a list of token instances. The
        last token can be a BlockState to specify the previousState
        for the next block.
        """

        return [tokens.TextToken(line, 0, len(line))]

    def name(self):
        """Get the name of the parser."""
        name = self.__class__.__name__.lower()
        if name.endswith("parser"):
            name = name[:-6]
        return name

    def __repr__(self):
        """String representation of the parser."""
        return '<Parser for "{}">'.format(self.name())

    def keywords(self):
        """Get a list of keywords valid for this parser."""
        return self._keywords[:]

    def filenameExtensions(self):
        """Get a list of filename extensions for which this parser is appropriate."""
        return ["." + e.lstrip(".").lower() for e in self._extensions]

    def shebangKeywords(self):
        """Get a list of shebang keywords for which this parser is appropriate."""
        return self._shebangKeywords.copy()

    def getStyleElementDescriptions(cls):
        """This method returns a list of the StyleElementDescription
        instances used by this parser.
        """
        descriptions = {}
        for token in cls.getUsedTokens(cls):
            descriptions[token.description.key] = token.description

        return list(descriptions.values())

    def getUsedTokens(self):
        """Get a a list of token instances used by this parser."""

        # Get module object of the parser
        try:
            mod = sys.modules[self.__module__]
        except KeyError:
            return []

        # Get token classes from module
        tokenClasses = []
        for name in mod.__dict__:
            member = mod.__dict__[name]
            if isinstance(member, type) and issubclass(member, tokens.Token):
                if member is not tokens.Token:
                    tokenClasses.append(member)

        # Return as instances
        return [t() for t in tokenClasses]

    def _isTodoItem(self, text):
        """Get whether the given text (which should be a comment) represents
        a todo item. Todo items start with "todo", "2do" or "fixme",
        optionally with a colon at the end.
        """
        # Get first word
        word = text.lstrip().split(" ", 1)[0].rstrip(":")
        # Test
        if word.lower() in ["todo", "2do", "fixme"]:
            return True
        else:
            return False


# Utils for regex parser
def bygroups(*args):
    return tuple(args)


@dataclass
class from_list:
    list: list[str]
    ttype: tokens.Token
    prefix: str = ""
    suffix: str = ""

    def to_pattern(self):
        return [
            (self.prefix + word + self.suffix, self.ttype, None) for word in self.list
        ]


@dataclass
class include:
    state_name: str


def combination(*states):
    name = "-".join(states)
    return {name: [include(state) for state in states]}


def default(next_state):
    # Always matches, doesn't yield a token and go to next_state
    return ("", tuple(), next_state)


class RegexParser(Parser):
    # states must be defined in class inheriting from this one. Default
    # is a TextToken per line.
    # Must be ordered. Since
    states = {"root": ("$.*\n", None)}

    def __init__(self):
        self.process_states()

    def _stack_from_blockstate(self, block_state_val):
        """Get the parser stack from a given block_state's value. This is
        basically just a number in base N, where N is the number of
        states of the parser.

        For instance, if a parser has 2 states ("root" and "other") and
        the block state is 5 = 0b101, then the stack is:
        stack = [
            "root", # Always starts with root
            "other", # Since 5 = 0b101
            "root", # Since 5 = Ob101
            "other, # Since 5 = Ob101
        ]
        """
        if block_state_val == -1:
            return ["root"]

        N = len(self.states)
        stack = ["root"]  # stack is always root first

        while block_state_val != 0:
            n = block_state_val % N
            stack.append(self._state_names[n])
            block_state_val //= N
        return stack

    def _blockstate_from_stack(self, stack):
        """See _stack_from_blockstate's docstring"""

        N = len(self.states)
        block_state_val = 0
        # Ignore first element since it is "root"
        for state in reversed(stack[1:]):
            n = self._state_names.index(state)
            block_state_val = block_state_val * N + n
        return BlockState(block_state_val)

    def parseLine(self, line, previousState):
        # Initialize
        pos = 0
        stack = self._stack_from_blockstate(previousState)
        toks = []

        # While the end of the line isn't reached:
        while pos < len(line):

            # Find a match in the possible matches
            match, token_type, next_state = self.find_match(line, stack[-1], pos)

            # If no match, go to next char
            if match is None:
                pos += 1

            # If match, process match:
            else:
                # If a token exists for the match,
                if token_type is not None:
                    # Process the case where multiple groups are in the
                    # regex:

                    if isinstance(token_type, tuple):
                        for i, ttype in enumerate(token_type):
                            if match.group(i + 1) != "":
                                toks.append(
                                    ttype(
                                        line,
                                        pos + match.start(i + 1),
                                        pos + match.end(i + 1),
                                    )
                                )

                    # Only one group:
                    else:
                        if match.group(0) != "":
                            toks.append(token_type(line, pos, pos + match.end(0)))

                # In any case, go to the next state if provided
                if next_state is not None:
                    if next_state == "#pop":
                        # Remove last state from the stack
                        stack.pop()
                    elif next_state == "#push":
                        # Add current state to the stack again
                        stack.append(stack[-1])
                    else:
                        stack.append(next_state)

                # Go the the end of the match, since everything until
                # there is processed.
                # Increment pos at minimum
                pos += match.end(0)


        # Process empty line: nothing to tokenize, but stack might change
        if line == "":
            _, _, next_state = self.find_match(line, stack[-1], pos)

            if next_state is not None:
                if next_state == "#pop":
                    # Remove last state from the stack
                    stack.pop()
                elif next_state == "#push":
                    # Add current state to the stack again
                    stack.append(stack[-1])
                else:
                    stack.append(next_state)


        return toks + [self._blockstate_from_stack(stack)]

    def find_match(self, line, current_state, pos):
        """Return first match in current state as well as the
        corresponding token. If no match occures, return None.
        """
        for pattern, token_type, next_state in self.processed_states[current_state]:
            match = re.match(pattern, line[pos:])
            if match is not None:
                return (match, token_type, next_state)
        return (None, None, None)

    def process_states(self):
        """Prepare raw states into usable states by the parser:
        - pad each case to len 3 using None,
        - process lists of words,
        - process includes.
        """
        temp = defaultdict(list)
        includes = set()
        state_needs_include = set()
        for state in self.states.keys():
            for case in self.states[state]:
                # Inludes are memorized to be dealt with at the end
                if isinstance(case, include):
                    temp[state].append(case)

                # Create from lists of possible words
                elif isinstance(case, from_list):
                    temp[state].extend(case.to_pattern())

                # Pad states to len 3 with None
                else:
                    if len(case) == 1:
                        temp[state].append((re.compile(case[0]), None, None))
                    elif len(case) == 2:
                        temp[state].append((re.compile(case[0]), case[1], None))
                    elif len(case) == 3:
                        temp[state].append(
                            (
                                re.compile(case[0]),
                                case[1],
                                case[2],
                            )
                        )
                    else:
                        raise ValueError()

        # Process includes at the end, to prevent partial copies
        self.processed_states = {}
        for state in temp:
            self.processed_states[state] = process_includes(state, temp)

        # keep a list of state names in memory
        self._state_names = list(self.processed_states)


def process_includes(state, d):
    L = []
    for case in d[state]:
        if isinstance(case, include):
            if case.state_name in d:
                L.extend(process_includes(case.state_name, d))
            else:
                raise KeyError("Unknown included state")
        else:
            L.append(case)
    return L


## Import parsers statically
# We could load the parser dynamically from the source files in the
# directory, but this takes quite some effort to get right when apps
# are frozen. This is doable (I do it in Visvis) but it requires the
# user to specify the parser modules by hand when freezing an app.
#
# In summary: it takes a lot of trouble, which can be avoided by just
# listing all parsers here.

from . import python_parser  # noqa
from . import cython_parser  # noqa
from . import c_parser  # noqa
from . import s_expr_parser  # noqa
