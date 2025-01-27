"""Module baseTextCtrl

Defines the base text control to be inherited by the shell and editor
classes. Implements styling, introspection and a bit of other stuff that
is common for both shells and editors.

"""

import pyzo
import os
import sys
import time
from pyzo.core.pyzoLogging import print
import pyzo.codeeditor.parsers.tokens as Tokens
from pyzo.codeeditor import CodeEditor

from pyzo.qt import QtCore, QtGui, QtWidgets


ismacos = sys.platform.startswith("darwin")


def normalizePath(path):
    """Normalize the path given.
    All slashes will be made the same (and doubles removed)
    The real case as stored on the file system is recovered.
    """
    path = os.path.abspath(path)  # make sure it is defined from the drive up
    path = os.path.normpath(path)
    return path


def isFormatStringToken(token):
    """returns True if a StringToken is a format string literal, e.g. f'{1 + 2}'"""
    if not isinstance(token, Tokens.StringToken):
        return False
    s = str(token)
    return "f" in s[: s.index(s[-1])].lower()


def isSimpleExpression(tokens):
    """returns True if the list of tokens is a simple expression

    a "simple expression" is defined as follows:
    - first token is either:
        - an identifier
        - a string token, but not a format string token
    - further tokens are only identifier tokens, with a dot as a separator

    examples for simple expressions, as stringified tokens:
        myvar123
        myvar.myattribute
        "just a string"
        '\n'.join
        b"xyz".foo.bar.z

    Simple expressions can be mostly evaluated without side effects, at least when
    properties and attribute access dunder methods are assumed to not modify any data.
    """
    if len(tokens) == 0:
        return True
    if len(tokens) % 2 != 1:
        return False
    for i, t in enumerate(tokens):
        if i == 0:
            if isinstance(t, Tokens.StringToken) and not isFormatStringToken(t):
                continue
        if i % 2 == 0 and not isinstance(t, Tokens.IdentifierToken):
            return False
        elif i % 2 == 1 and str(t) != ".":
            return False
    return True


def skipNestedTokensRightToLeft(tokens, indClosing):
    """finds the left end of the nested parens expression given the right end

    Parens can be round parentheses, square brackets and curly braces.
    "indClosing" is the index for list "tokens" where the closing paren is located.
    Tokens are examinded from right to left, only testing for correct matching of
    nested parens.

    return value:
        the index of the corresponding token that matches the closing paren
        or None if the paren could not be found or nested parens do not match
    """
    stack = []
    openingParensDict = {")": "(", "]": "[", "}": "{"}
    for i in range(indClosing, -1, -1):
        t = tokens[i]
        s = str(t)
        if s in ")]}":
            stack.append(s)
            continue
        if s in "([{":
            if len(stack) == 0 or openingParensDict[stack.pop()] != s:
                return None  # parens do not match
            if len(stack) == 0:
                break  # finished successfully
    else:
        return None  # matching paren not found
    indOpening = i
    return indOpening


def getExpressionTokensRightToLeft(tokens, indRightStart):
    """finds the start of an "expression" in a list of tokens, starting at indRightStart

    In this case, an "expression" is a list of one or more tokens that are a subsequence
    of the given list "tokens", with the last token at given index "indRightStart", that
    is the rightmost part of the "expression".

    return value:
        the index of the corresponding token where the "expression" ends on the left
        or None if no expression could be found or nested parens do not match

    An "expression" consists of a sequence of token groups.
    A token group can be:
        - an identifier
        - a dot
        - a string token
        - a (nested) parens group of tokens
    A dot is only allowed on the left of an identifier (i.e. on the left of the attribute).
    A curly parens group can only be the first token group (on the left of the expression).
    Dots can not be placed at the very left or very right of the expression, only in between.

    examples for "expressions", as stringified tokens:
        b"x".hex()
        'abc'.join([])
        (1, 2)[0].bit_length().__dir__()[0].upper()
        f'{3 + 4}'.join
        myvar
        (1, 2)[0].bit_length
        [11, 33].count
        [11, 33].count(5)
        (2).bit_length()
        {'a': 1}[b]
        {'a': 1}.get(x)

    Evaluating the values of such "expressions" during introspection could trigger a
    series of calculations and modify data during introspection, for example when
    consuming values of an iterator, or when inspecting code like "mylist.pop()['abc']".
    """
    i = indRightStart + 1
    exprTokens = []  # this will grow to the right when when decreasing the token index (reversed order)
    containsCurly = False
    while i > 0:
        i -= 1
        t = tokens[i]
        s = str(t)
        if s in ")]}":
            indOpening = skipNestedTokensRightToLeft(tokens, i)
            if indOpening is None:
                return None  # parens do not match
            if s == "}":
                if containsCurly:
                    return None  # curly braces encountered more than once
                containsCurly = True
            exprTokens.extend(tokens[indOpening : i + 1][::-1])
            i = indOpening
        elif s == ".":
            if len(exprTokens) == 0 or not isinstance(
                exprTokens[-1], Tokens.IdentifierToken
            ):
                return None  # dot is not on the left of an attribute
            exprTokens.append(t)
        elif isinstance(t, Tokens.IdentifierToken):
            if len(exprTokens) > 0 and isinstance(
                exprTokens[-1], (Tokens.IdentifierToken, Tokens.StringToken)
            ):
                return None  # an identifier cannot be directly on the left of a string literal or another identifier
            exprTokens.append(t)
        elif isinstance(t, Tokens.StringToken):
            if len(exprTokens) > 0 and isinstance(
                exprTokens[-1], Tokens.IdentifierToken
            ):
                return None  # a string literal cannot be directly on the left of an identifier
            exprTokens.append(t)
        else:
            indLeftEnd = i + 1
            break
    else:
        indLeftEnd = 0

    if len(exprTokens) == 0:
        return None  # no expression found

    if containsCurly and str(exprTokens[-1]) != "{":
        return None  # curly braces can only occur at the very left

    if str(exprTokens[-1]) == ".":
        return None  # a dot cannot occur at the very left

    return indLeftEnd


def parseLine_autocomplete(tokens):
    """gets the name part and the attribute part of an expression in tokens

    The tokens of the expression are located at the very right in the token list.

    return value:
        tuple (nameTokens, needleToken) where "needleToken" is the attribute part
            needleToken will be None if the last token is "."
            nameTokens will be an empty list if there is no dot in the expression
        or tuple (None, None) if no valid expression could be found

    examples with stringified input tokens and result tokens:
        abc = (myfunc(x + ((y + 2) + otherfunc(1, 2).
            name: otherfunc(1, 2)
            needle: None

        abc = (myfunc(x + ((y + 2) + otherfunc(1, 2).xy
            name: otherfunc(1, 2)
            needle: xy

        myvar
            name: [empty list]
            needle: myvar

        eat = food.fruit.ban
            name: food.fruit
            needle: ban

        >>> enu
            name: [empty list]
            needle: enumerate
    """
    retvalInvalid = (None, None)
    if len(tokens) == 0:
        return retvalInvalid

    needleToken = tokens[-1]
    if str(needleToken) == ".":
        needleToken = None
        if len(tokens) == 1:
            return retvalInvalid
        indRightStart = len(tokens) - 1 - 1
    else:
        if not isinstance(needleToken, Tokens.IdentifierToken):
            return retvalInvalid
        if len(tokens) == 1 or str(tokens[-2]) != ".":
            nameTokens = []
            return nameTokens, needleToken
        indRightStart = len(tokens) - 1 - 2

    indLeftEnd = getExpressionTokensRightToLeft(tokens, indRightStart)
    if indLeftEnd is None:
        return retvalInvalid
    nameTokens = tokens[indLeftEnd : indRightStart + 1]
    return nameTokens, needleToken


def parseLine_signature(tokens, paren="("):
    """gets the expression before the open paren on the right side in a token list

    Processes the tokens from right to left till it finds an open paren that is
    preceded by an "expression" consisting of one or more tokens. Also gets the index
    of the token that is the open paren.
    Paren groups that are encountered while moving from right to left must be properly
    matched by the opposite paren token, also for nested paren groups.
    Parens that are only open to the right and not preceded by an expression, are ignored.

    return value:
        tuple (fullNameTokens, indOfOpenParen)
        or tuple (None, None) if not found or invalid parens groups encountered

    examples with stringified input tokens and result tokens:
        abc = (myfunc(x + ((y + 2) + otherfunc(1, 2) -
            fullName: myfunc
            indOfOpenParen: 4

        abc = (getfunc('aa')(x + ((y + 2) + otherfunc(1, 2) -
            fullName: getfunc('aa')
            indOfOpenParen: 7
    """
    retvalInvalid = (None, None)
    i = len(tokens)
    while i > 0:
        i -= 1
        t = tokens[i]
        s = str(t)
        if s in ")]}":
            indOpening = skipNestedTokensRightToLeft(tokens, i)
            if indOpening is None:
                return retvalInvalid  # nested paren group is not complete
            i = indOpening
            continue
        if s == paren:
            indLeftEnd = getExpressionTokensRightToLeft(tokens, i - 1)
            if indLeftEnd is not None:
                fullNameTokens, indParenToken = tokens[indLeftEnd:i], i
                return fullNameTokens, indParenToken

    return retvalInvalid  # no open paren preceded by an expression found


## examples for running tests:
if False:
    ##
    p = pyzo.shells.getCurrentShell().parser()

    # tokens = p.parseLine("abc = (myfunc(x + ((y + 2) + otherfunc(1, 2).xy")
    # res = pyzo.core.baseTextCtrl.parseLine_autocomplete(tokens)

    tokens = p.parseLine("abc = (getfunc('aa')(x + ((y + 2) + otherfunc(1, 2) -")
    res = pyzo.core.baseTextCtrl.parseLine_signature(tokens)

    print(repr(res))
    if res != (None, None):
        print("".join(str(t) for t in res[0]))
        print(res[1])
##


class BaseTextCtrl(CodeEditor):
    """The base text control class.
    Inherited by the shell class and the Pyzo editor.
    The class implements autocompletion, calltips, and auto-help
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        # Set style/theme
        try:
            theme = pyzo.themes[pyzo.config.settings.theme.lower()]["data"]
            self.setStyle(theme)
            # autocomplete popup theme
            if pyzo.config.view.get("autoComplete_withTheme", False):
                editor_text_theme = theme["editor.text"].split(",")
                popup_background = editor_text_theme[1].split(":")[1]
                popup_text = editor_text_theme[0].split(":")[1]
                autoComplete_theme = "color: {}; background-color:{};".format(
                    popup_text, popup_background
                )
                self.completer().popup().setStyleSheet(autoComplete_theme)
        except Exception as err:
            print("Could not load theme: " + str(err))

        # Set font and zooming
        self.setFont(pyzo.config.view.fontname)
        self.setZoom(pyzo.config.view.zoom)
        self.setShowWhitespace(pyzo.config.view.showWhitespace)
        self.setHighlightMatchingBracket(pyzo.config.view.highlightMatchingBracket)

        # Create timer for autocompletion delay
        self._delayTimer = QtCore.QTimer(self)
        self._delayTimer.setSingleShot(True)
        self._delayTimer.timeout.connect(self._introspectNow)

        # For buffering autocompletion and calltip info
        self._callTipBuffer_name = ""
        self._callTipBuffer_intermediateResultName = None
        self._callTipBuffer_time = 0
        self._callTipBuffer_result = ""
        self._autoCompBuffer_name = ""
        self._autoCompBuffer_intermediateResultName = None
        self._autoCompBuffer_time = 0
        self._autoCompBuffer_result = []

        self.setAutoCompletionAcceptKeysFromStr(
            pyzo.config.settings.autoComplete_acceptKeys
        )

        self.completer().highlighted.connect(self.updateHelpFromAutocomplete)
        self.setIndentUsingSpaces(pyzo.config.settings.defaultIndentUsingSpaces)
        self.setIndentWidth(pyzo.config.settings.defaultIndentWidth)
        self.setAutocompletPopupSize(*pyzo.config.view.autoComplete_popupSize)
        self.setAutocompleteCaseSensitive(
            pyzo.config.settings.autoComplete_caseSensitive
        )
        self.setAutocompleteMinChars(pyzo.config.settings.autoComplete_minChars)
        self.setAutoClose_Quotes(pyzo.config.settings.autoClose_Quotes)
        self.setAutoClose_Brackets(pyzo.config.settings.autoClose_Brackets)
        self.setAutocompleteFinishedCallback(lambda: self.restoreHelp("autocomplete"))
        self.setCalltipFinishedCallback(lambda: self.restoreHelp("calltip"))

    def setAutoCompletionAcceptKeysFromStr(self, keys):
        """Set the keys that can accept an autocompletion from a comma delimited string."""
        # Set autocomp accept key to default if necessary.
        # We force it to be string (see issue 134)
        if not isinstance(keys, str):
            keys = "Tab"
        # Split
        keys = keys.replace(",", " ").split(" ")
        keys = [key for key in keys if key]
        # Set autocomp accept keys
        qtKeys = []
        for key in keys:
            if len(key) > 1:
                key = "Key_" + key[0].upper() + key[1:].lower()
                qtkey = getattr(QtCore.Qt.Key, key, None)
            else:
                qtkey = ord(key)
            if qtkey:
                qtKeys.append(qtkey)

        if QtCore.Qt.Key.Key_Enter in qtKeys and QtCore.Qt.Key.Key_Return not in qtKeys:
            qtKeys.append(QtCore.Qt.Key.Key_Return)
        self.setAutoCompletionAcceptKeys(*qtKeys)

    def getTokensUpToCursor(self, cursor):
        # In order to find the tokens, we need the userState from the highlighter
        if cursor.block().previous().isValid():
            previousState = cursor.block().previous().userState()
        else:
            previousState = 0

        text = cursor.block().text()[: cursor.positionInBlock()]

        return (
            text,
            [
                t for t in self.parser().parseLine(text, previousState) if t.isToken
            ],  # filter to remove BlockStates
        )

    def introspect(self, tryAutoComp=False, delay=True, advanced=False):
        """The starting point for introspection (autocompletion and calltip).
        It will always try to produce a calltip. If tryAutoComp is True,
        will also try to produce an autocompletion list (which, on success,
        will hide the calltip). If advanced is True, introspection will also
        evaluate more complexe expressions that contain function calls and/or
        indexing operations, and this will create cache variables in the
        shell's current scope.

        This method will obtain the line and (re)start a timer that will
        call _introspectNow() after a short while. This way, if the
        user types a lot of characters, there is not a stream of useless
        introspection attempts; the introspection is only really started
        after he stops typing for, say 0.1 or 0.5 seconds (depending on
        pyzo.config.autoCompDelay).

        The method _introspectNow() will parse the line to obtain
        information required to obtain the autocompletion and signature
        information. Then it calls processCallTip and processAutoComp
        which are implemented in the editor and shell classes.
        """

        # Find the tokens up to the cursor
        cursor = self.textCursor()

        text, tokensUptoCursor = self.getTokensUpToCursor(cursor)

        # TODO: Only proceed if valid python (no need to check for comments/
        # strings, this is done by the processing of the tokens). Check for python style

        # Is the char valid for auto completion?
        if tryAutoComp:
            if not text:
                self.autocompleteCancel()
                tryAutoComp = False

        # Store line and (re)start timer
        cursor.setKeepPositionOnInsert(True)
        self._delayTimer._tokensUptoCursor = tokensUptoCursor
        self._delayTimer._cursor = cursor
        self._delayTimer._tryAutoComp = tryAutoComp
        self._delayTimer._advanced = advanced

        if delay:
            self._delayTimer.start(pyzo.config.advanced.autoCompDelay)
        else:
            self._delayTimer.start(1)  # self._introspectNow()

    def _introspectNow(self):
        """This method is called a short while after introspect()
        by the timer. It parses the line and calls the specific methods
        to process the callTip and autoComp.
        """

        tokens = self._delayTimer._tokensUptoCursor
        advanced = self._delayTimer._advanced

        if pyzo.config.settings.autoCallTip:
            # Parse the line, to get the name of the function we should calltip
            # if the name is empty/None, we should not show a signature
            fullNameTokens, indParenToken = parseLine_signature(tokens)

            useIntermediateResult = False
            if advanced:
                self._callTipBuffer_time = 0  # clear buffer

            fullName = ""
            if fullNameTokens is not None:
                # Compose actual name
                fullName = "".join([str(t) for t in fullNameTokens])
                if not isSimpleExpression(fullNameTokens):
                    if advanced or fullName == self._callTipBuffer_name:
                        useIntermediateResult = True
                    else:
                        fullName = ""

            if fullName:
                # Process
                indOfOpenParen = tokens[indParenToken].start
                offset = (
                    self._delayTimer._cursor.positionInBlock()
                    - indOfOpenParen
                    + len(str(fullNameTokens[-1]))
                )
                cto = CallTipObject(self, fullName, offset, useIntermediateResult)
                self.processCallTip(cto)
            else:
                self.calltipCancel()

        if self._delayTimer._tryAutoComp and pyzo.config.settings.autoComplete:
            # Parse the line, to see what name or attribute we need to auto-complete
            nameTokens, needleToken = parseLine_autocomplete(tokens)
            keyLookUp = False

            if not nameTokens and not str(needleToken).isidentifier():
                # nameTokens could be None or []
                nameTokens = (
                    None  # force key-auto-completion (for indices, and numeric keys)
                )

            if nameTokens is None:
                # no auto-completion for a name or attribute found --> try key-auto-completion instead
                keyLookUp = True
                nameTokens, indParenToken = parseLine_signature(tokens, paren="[")
                if indParenToken is not None:
                    needleToken = "".join([str(t) for t in tokens[indParenToken + 1 :]])
                else:
                    needleToken = None

            useIntermediateResult = False
            if advanced:
                self._autoCompBuffer_time = 0  # clear buffer

            name = ""
            needle = str(needleToken) if needleToken is not None else ""
            if nameTokens is not None:
                name = "".join([str(t) for t in nameTokens])
                if keyLookUp:
                    name += "["
                if not isSimpleExpression(nameTokens):
                    if advanced or name == self._autoCompBuffer_name:
                        useIntermediateResult = True
                    else:
                        name, needle = "", ""

            if name or needle:
                # Try to do auto completion
                aco = AutoCompObject(self, name, needle, useIntermediateResult)
                self.processAutoComp(aco)

    def processCallTip(self, cto):
        """Overridden in derive class"""
        pass

    def processAutoComp(self, aco):
        """Overridden in derive class"""
        pass

    def helpOnText(self, pos):
        hw = pyzo.toolManager.getTool("pyzointeractivehelp")
        if not hw:
            return
        name = self.textCursor().selectedText().strip()
        if name == "":
            cursor = self.cursorForPosition(pos - self.mapToGlobal(QtCore.QPoint(0, 0)))
            line = cursor.block().text()
            limit = cursor.positionInBlock()
            while limit < len(line) and (
                line[limit].isalnum() or line[limit] in (".", "_")
            ):
                limit += 1
                cursor.movePosition(cursor.MoveOperation.Right)
            _, tokens = self.getTokensUpToCursor(cursor)
            nameTokens, needleToken = parseLine_autocomplete(tokens)
            if nameTokens:
                name = "{}.{}".format(
                    "".join([str(t) for t in nameTokens]), needleToken
                )
            elif needleToken:
                name = str(needleToken)

        if name != "":
            hw.setObjectName(name, True)

    @staticmethod
    def processHelp(name, source, addToHist=False):
        """Show help on the given full object name.
        - called when going up/down in the autocompletion list or showing calltips.
        """
        assert source in ("autocomplete", "calltip")
        # uses parse_autocomplete() to find baseName and objectName

        # Get help tool
        hw = pyzo.toolManager.getTool("pyzointeractivehelp")
        # Get the shell
        shell = pyzo.shells.getCurrentShell()
        # Both should exist
        if not hw or not shell:
            return

        if name:
            hw.helpFromExtension(name, source, addToHist)

    ## Callbacks
    def updateHelpFromAutocomplete(self, name):
        """A name has been highlighted, show help on that name"""

        if self._autoCompBuffer_intermediateResultName is not None:
            s = self._autoCompBuffer_intermediateResultName
            if self._autoCompBuffer_name.endswith("["):
                name = "{}[{}]".format(s, name)  # key auto-completion
            else:
                name = s + "." + name  # attribute auto-completion
        elif self._autoCompBuffer_name:
            s = self._autoCompBuffer_name
            if s.endswith("["):
                name = s + name + "]"  # key auto-completion
            else:
                name = s + "." + name  # attribute auto-completion
        elif not self.completer().completionPrefix():
            # Don't update help if there is no dot or prefix;
            # the choice would be arbitrary
            return

        # Apply
        self.processHelp(name, "autocomplete")

    @staticmethod
    def restoreHelp(source):
        assert source in ("autocomplete", "calltip")
        hw = pyzo.toolManager.getTool("pyzointeractivehelp")
        if hw:
            hw.helpFromExtension(None, source)

    def event(self, event):
        """Overload main event handler so we can pass Ctrl-C Ctr-V etc, to the main
        window.
        """
        if isinstance(event, QtGui.QKeyEvent):
            # AltModifier maps to the option key on MacOS, and an alternative to control in some cases
            has_control = event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
            has_alt = event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier
            # Ignore CTRL+{A-Z} since those keys are handled through the menu
            if (
                (has_control or has_alt)
                and (event.key() >= QtCore.Qt.Key.Key_A)
                and (event.key() <= QtCore.Qt.Key.Key_Z)
            ):
                event.ignore()
                return False

        # Default behavior
        super().event(event)
        return True

    def keyPressEvent(self, event):
        """Receive qt key event.
        From here we will dispatch the event to perform autocompletion
        or other stuff...
        """

        KM = QtCore.Qt.KeyboardModifier

        # Get ordinal key
        ordKey = -1
        if event.text():
            ordKey = ord(event.text()[0])

        # Cancel any introspection in progress
        self._delayTimer._line = ""

        # Detect "control". This is awkward:
        # Command Key ⌘ -> ControlModifier -> mostly what Windows uses Control for.
        # Option key ⌥  -> AltModifier     -> For stuff that we cannot use Command key for.
        # Control key ^ -> MetaModifier    -> I guess most uses maps to what Windows uses Alt for.
        has_control_like = event.modifiers() & (
            KM.AltModifier if ismacos else KM.ControlModifier
        )

        # Leave tab events to editor tabs
        # FIXME: this is probably just a workaround for another problem
        # FIXME: ... somewhere in a keyPressEvent in a codeeditor extension
        if (
            ismacos
            and has_control_like
            and event.key()
            in (
                QtCore.Qt.Key.Key_Tab,
                QtCore.Qt.Key.Key_Backtab,
            )
        ):
            event.ignore()
            return

        # Invoke advanced autocomplete/calltips Ctrl+Space key combination?
        if has_control_like and event.key() == QtCore.Qt.Key.Key_Space:
            cursor = self.textCursor()
            if cursor.position() == cursor.anchor():
                text = cursor.block().text()[: cursor.positionInBlock()]
                if text:
                    self.introspect(True, False, advanced=True)
                    return

        # Invoke autocomplete via tab key?
        elif (
            event.modifiers() == KM.NoModifier and event.key() == QtCore.Qt.Key.Key_Tab
        ):
            if pyzo.config.settings.autoComplete and not self.autocompleteActive():
                cursor = self.textCursor()
                if cursor.position() == cursor.anchor():
                    text = cursor.block().text()[: cursor.positionInBlock()]
                    if text and (text[-1] in (Tokens.ALPHANUM + "._")):
                        self.introspect(True, False)
                        return

        super().keyPressEvent(event)

        # Analyse character/key to determine what introspection to fire
        if ordKey:
            if (
                ordKey >= 32 or ordKey == 8  # 8: '\b'
            ) and pyzo.config.settings.autoComplete == 1:
                # If a char that allows completion or backspace or dot was pressed
                self.introspect(True)
            elif ordKey >= 32:
                # Printable chars, only calltip
                self.introspect()
        elif event.key() in [QtCore.Qt.Key.Key_Left, QtCore.Qt.Key.Key_Right]:
            self.introspect()


class CallTipObject:
    """Object to help the process of call tips.
    An instance of this class is created for each call tip action.
    """

    def __init__(self, textCtrl, name, offset, useIntermediateResult=False):
        self.textCtrl = textCtrl
        self.name = name
        self.bufferName = name
        self.offset = offset
        self.useIntermediateResult = useIntermediateResult

    def tryUsingBuffer(self):
        """Try performing this callTip using the buffer.

        Returns True on success.
        """
        bufferName = self.textCtrl._callTipBuffer_name
        t = time.time() - self.textCtrl._callTipBuffer_time
        if self.bufferName == bufferName and t < 0:
            self._finish(self.textCtrl._callTipBuffer_result)
            return True
        else:
            return False

    def finish(self, callTipText):
        """Finish the introspection using the given calltipText.

        Will also automatically call setBuffer.
        """
        if self.useIntermediateResult:
            self.setBuffer(callTipText, 1e10)  # almost infinite timeout for the buffer
        else:
            self.setBuffer(callTipText)
        self._finish(callTipText)

    def setBuffer(self, callTipText, timeout=4):
        """Sets the buffer with the provided text."""
        self.textCtrl._callTipBuffer_name = self.bufferName
        self.textCtrl._callTipBuffer_intermediateResultName = (
            "__pyzo__calltip" if self.useIntermediateResult else None
        )
        self.textCtrl._callTipBuffer_time = time.time() + timeout
        self.textCtrl._callTipBuffer_result = callTipText

    def _finish(self, callTipText):
        highlightFunctionName = not self.useIntermediateResult
        # ... because "foo().bar().func(" would only highlight "foo"
        self.textCtrl.calltipShow(self.offset, callTipText, highlightFunctionName)
        BaseTextCtrl.processHelp(self.name, "calltip")


class AutoCompObject:
    """Object to help the process of auto completion.
    An instance of this class is created for each auto completion action.
    """

    def __init__(self, textCtrl, name, needle, useIntermediateResult=False):
        self.textCtrl = textCtrl
        self.bufferName = name  # name to identify with
        self.name = name  # object to find attributes of
        self.needle = needle  # partial name to look for
        self.names = set()  # the names (use a set to prevent duplicates)
        self.useIntermediateResult = useIntermediateResult

    def addNames(self, names):
        """Add a list of names to the collection. Duplicates are removed."""
        self.names.update(names)

    def tryUsingBuffer(self):
        """Try performing this auto-completion using the buffer.

        Returns True on success.
        """
        bufferName = self.textCtrl._autoCompBuffer_name
        t = time.time() - self.textCtrl._autoCompBuffer_time
        if self.bufferName == bufferName and t < 0:
            self._finish(self.textCtrl._autoCompBuffer_result)
            return True
        else:
            return False

    def finish(self):
        """Finish the introspection using the collected names.

        Will automatically call setBuffer.
        """
        # Remember at the object that started this introspection
        # and get sorted names
        timeout = (
            1e10 if self.useIntermediateResult else None
        )  # almost infinite timeout for the buffer
        names = self.setBuffer(self.names, timeout)
        # really finish
        self._finish(names)

    def setBuffer(self, names=None, timeout=None):
        """Sets the buffer with the provided names (or the collected names).

        Also returns a list with the sorted names.
        """
        # Determine timeout
        # Global namespaces change more often than local one, plus when
        # typing a xxx.yyy, the autocompletion buffer changes and is thus
        # automatically refreshed.
        # I've once encountered a wrong autocomp list on an object, but
        # haven't been able to reproduce it. It was probably some odity.
        if timeout is None:
            if self.bufferName:
                timeout = 5
            else:
                timeout = 1
        # Get names
        if names is None:
            names = self.names
        # Make list and sort
        names = list(names)
        names.sort(key=str.upper)
        # Store
        self.textCtrl._autoCompBuffer_name = self.bufferName
        self.textCtrl._autoCompBuffer_intermediateResultName = (
            "__pyzo__autocomp" if self.useIntermediateResult else None
        )
        self.textCtrl._autoCompBuffer_time = time.time() + timeout
        self.textCtrl._autoCompBuffer_result = names
        # Return sorted list
        return names

    def _finish(self, names):
        # Show completion list if required.
        self.textCtrl.autocompleteShow(len(self.needle), names, self.name != "")

    def nameInImportNames(self, importNames):
        """Test whether the name, or a base part of it is present in the
        given list of names. Returns the (part of) the name that's in
        the list, or None otherwise.
        """
        baseName = self.name
        while baseName not in importNames:
            if "." in baseName:
                baseName = baseName.rsplit(".", 1)[0]
            else:
                baseName = None
                break
        return baseName


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    win = BaseTextCtrl(None)
    #     win.setStyle('.py')
    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    tmp += "a\u20acb\n"
    win.setPlainText(tmp)
    win.show()
    app.exec()
