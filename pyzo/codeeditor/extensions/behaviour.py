"""
Code editor extensions that change its behaviour (i.e. how it reacts to keys)
"""

from ..qt import QtGui, QtCore

Qt = QtCore.Qt

from ..misc import ce_option
from ..parsers.tokens import (
    CommentToken,
    IdentifierToken,
    NonIdentifierToken,
    StringToken,
    UnterminatedStringToken,
)
from ..parsers.python_parser import MultilineStringToken, stringLiteralPrefixes


class MoveLinesUpDown:
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and (
            Qt.KeyboardModifier.ControlModifier & event.modifiers()
            and Qt.KeyboardModifier.ShiftModifier & event.modifiers()
        ):
            cursor = self.textCursor()
            cursor.beginEditBlock()
            try:
                self._swaplines(cursor, event.key())
            finally:
                cursor.endEditBlock()

        else:
            super().keyPressEvent(event)

    def _swaplines(self, cursor, key):
        # Get positions of selection
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # Get text of selected blocks
        cursor.setPosition(start, cursor.MoveMode.MoveAnchor)
        cursor.movePosition(
            cursor.MoveOperation.StartOfBlock, cursor.MoveMode.MoveAnchor
        )
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        text1 = cursor.selectedText()
        cursor.removeSelectedText()
        pos1 = cursor.position()

        # Move up/down
        other = [
            cursor.MoveOperation.NextBlock,
            cursor.MoveOperation.PreviousBlock,
        ][key == Qt.Key.Key_Up]
        cursor.movePosition(other, cursor.MoveMode.MoveAnchor)

        # Select text of other block
        cursor.movePosition(
            cursor.MoveOperation.StartOfBlock, cursor.MoveMode.MoveAnchor
        )
        cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
        text2 = cursor.selectedText()
        cursor.removeSelectedText()
        pos2 = cursor.position()

        # Insert text
        cursor.insertText(text1)
        pos3 = cursor.position()

        # Move back
        if key == Qt.Key.Key_Up:
            cursor.movePosition(
                cursor.MoveOperation.NextBlock, cursor.MoveMode.MoveAnchor
            )
        else:
            cursor.setPosition(pos1, cursor.MoveMode.MoveAnchor)
            pos2 += len(text2)
            pos3 += len(text2)

        # Replace text
        cursor.insertText(text2)

        # Leave original lines selected for continued movement
        cursor.setPosition(pos2, cursor.MoveMode.MoveAnchor)
        cursor.setPosition(pos3, cursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)


class ScrollWithUpDownKeys:
    def keyPressEvent(self, event):
        if (
            event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down)
            and Qt.KeyboardModifier.ControlModifier == event.modifiers()
        ):
            s = self.verticalScrollBar()
            # h = self.cursorRect(self.textCursor()).height()
            if event.key() == Qt.Key.Key_Up:
                s.setValue(s.value() + 1)
            else:
                s.setValue(s.value() - 1)

        else:
            super().keyPressEvent(event)


class HomeKey:
    def keyPressEvent(self, event):
        # Home or shift + home
        if event.key() == Qt.Key.Key_Home and event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.KeyboardModifier.ShiftModifier
            moveMode = [cursor.MoveMode.MoveAnchor, cursor.MoveMode.KeepAnchor][
                shiftDown
            ]
            # Get leading whitespace
            text = cursor.block().text()
            leadingWhitespace = text[: len(text) - len(text.lstrip())]
            # Get current position and move to start of whitespace
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.MoveOperation.StartOfBlock, moveMode)
            cursor.movePosition(
                cursor.MoveOperation.Right, moveMode, len(leadingWhitespace)
            )
            # If we were alread there, move to start of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.MoveOperation.StartOfBlock, moveMode)
            # Done
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)


class EndKey:
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_End and event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.KeyboardModifier.ShiftModifier
            moveMode = [cursor.MoveMode.MoveAnchor, cursor.MoveMode.KeepAnchor][
                shiftDown
            ]
            # Get current position and move to end of line
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.MoveOperation.EndOfLine, moveMode)
            # If alread at end of line, move to end of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, moveMode)
            # Done
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)


class NumpadPeriodKey:
    """
    If the numpad decimal separator key is pressed, always insert
    a period (.) even if due to localization that key is mapped to a
    comma (,). When editing code, period is the decimal separator
    independent of localization
    """

    # NOTE: THIS PLUGIN IS DISABLED, see issue #720

    def keyPressEvent(self, event):
        # Check for numpad comma
        if (
            event.key() == QtCore.Qt.Key.Key_Comma
            and event.modifiers() & QtCore.Qt.KeyboardModifier.KeypadModifier
        ):
            # Create a new QKeyEvent to substitute the original one
            event = QtGui.QKeyEvent(
                event.type(),
                QtCore.Qt.Key.Key_Period,
                event.modifiers(),
                ".",
                event.isAutoRepeat(),
                event.count(),
            )

        super().keyPressEvent(event)


class Indentation:
    def __cursorIsInLeadingWhitespace(self, cursor=None):
        """
        Checks wether the given cursor is in the leading whitespace of a block, i.e.
        before the first non-whitespace character. The cursor is not modified.
        If the cursor is not given or is None, the current textCursor is used
        """
        if cursor is None:
            cursor = self.textCursor()

        # Get the text of the current block up to the cursor
        textBeforeCursor = cursor.block().text()[: cursor.positionInBlock()]
        return (
            textBeforeCursor.lstrip() == ""
        )  # If we trim it and it is empty, it's all whitespace

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        # Tab key
        if key == Qt.Key.Key_Tab:
            if modifiers == Qt.KeyboardModifier.NoModifier:
                if (
                    self.textCursor().hasSelection()
                ):  # Tab pressed while some area was selected
                    self.indentSelection()
                    return
                elif self.__cursorIsInLeadingWhitespace():
                    # If the cursor is in the leading whitespace, indent and move cursor to end of whitespace
                    cursor = self.textCursor()
                    self.indentBlock(cursor)
                    self.setTextCursor(cursor)
                    return

                elif self.indentUsingSpaces():
                    # Insert space-tabs
                    cursor = self.textCursor()
                    w = self.indentWidth()
                    cursor.insertText(" " * (w - ((cursor.positionInBlock() + w) % w)))
                    return

        # If backspace is pressed in the leading whitespace, (except for at the first
        # position of the line), and there is no selection
        # dedent that line and move cursor to end of whitespace
        elif (
            key == Qt.Key.Key_Backspace
            and modifiers == Qt.KeyboardModifier.NoModifier
            and self.__cursorIsInLeadingWhitespace()
            and not self.textCursor().atBlockStart()
            and not self.textCursor().hasSelection()
        ):
            # Create a cursor, dedent the block and move screen cursor to the end of the whitespace
            cursor = self.textCursor()
            self.dedentBlock(cursor)
            self.setTextCursor(cursor)
            return

        # todo: Same for delete, I think not (what to do with the cursor?)

        # Auto-unindent
        elif key == Qt.Key.Key_Delete:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                cursor.movePosition(
                    cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor
                )
                if not cursor.hasSelection() and cursor.block().next().isValid():
                    cursor.beginEditBlock()
                    cursor.movePosition(cursor.MoveOperation.NextBlock)
                    self.indentBlock(cursor, -99)  # dedent as much as we can
                    cursor.deletePreviousChar()
                    cursor.endEditBlock()
                    return

        super().keyPressEvent(event)


class AutoIndent:
    """
    Auto indentation. This extension only adds the autoIndent property, for the
    actual indentation, the editor should derive from some AutoIndenter object
    """

    def autoIndent(self):
        """Get whether auto indentation is enabled."""
        return self.__autoIndent

    @ce_option(True)
    def setAutoIndent(self, value):
        """Set whether to enable auto indentation."""
        self.__autoIndent = bool(value)


class PythonAutoIndent:
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if not self.autoIndent():
            return

        # This extension code is run *after* key is processed by QPlainTextEdit

        if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            cursor = self.textCursor()

            # Prevent in-block newlines (issue #482)
            if not cursor.atBlockStart() and not cursor.hasSelection():
                cursor.deletePreviousChar()
                cursor.insertBlock()
                cursor = self.textCursor()

            previousBlock = cursor.block().previous()
            if previousBlock.isValid():
                line = previousBlock.text()
                indent = line[: len(line) - len(line.lstrip())]
                if ":" in line:
                    # We only need to add indent if the : is not in a (multiline)
                    # string or comment. Therefore, find out what the syntax
                    # highlighter thinks of the previous line.
                    ppreviousBlock = (
                        previousBlock.previous()
                    )  # the block before previous
                    ppreviousState = (
                        ppreviousBlock.userState() if previousBlock.isValid() else 0
                    )
                    tokens = self.parser().parseLine(
                        previousBlock.text(), ppreviousState
                    )
                    # because of the ":" on that line, there is at least one token
                    t = tokens[-1]
                    if isinstance(t, CommentToken):
                        t = tokens[-2] if len(tokens) >= 2 else None
                    if isinstance(t, NonIdentifierToken) and str(t).strip() == ":":
                        # there is no need to check if the previous indent is the same
                        # style as the added one, because we could not fix that anyways
                        if self.indentUsingSpaces():
                            indent += " " * self.indentWidth()
                        else:
                            indent += "\t"
                cursor.insertText(indent)
                # This prevents jump to start of line when up key is pressed
                self.setTextCursor(cursor)


class SmartCopyAndPaste:
    """
    Smart copy and paste allows copying and pasting blocks

    """

    @staticmethod
    def __setCursorPositionAndAnchor(cursor, position, anchor):
        cursor.setPosition(anchor)
        cursor.setPosition(position, cursor.MoveMode.KeepAnchor)

    @classmethod
    def __ensureCursorBeforeAnchor(cls, cursor):
        """
        Given a cursor, modify it such that the cursor.position() is before or
        at cursor.anchor() and not the other way around.

        Returns: anchorBeforeCursor, i.e. whether originally the anchor was
        before the cursor
        """
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        # Remember whether the cursor is before or after the anchor
        anchorBeforeCursor = cursor.anchor() < cursor.position()

        cls.__setCursorPositionAndAnchor(cursor, start, end)

        # Return wheter originally the cursor was before the anchor
        return anchorBeforeCursor

    def copy(self):
        """Smart copy: if selection is multi-line and in front of the start of the
        selection there is only whitespace, extend the selection to include only
        whitespace
        """
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # For our convenience, ensure that position is at start and
        # anchor is at the end, but remember whether originally the
        # anchor was before the cursor or the other way around
        anchorBeforeCursor = self.__ensureCursorBeforeAnchor(cursor)

        # Check if we have multi-line selection.
        block = cursor.block()
        # Use > not >= to ensure we don't count it as multi-line if the cursor
        # is just at the beginning of the next block (consistent with 'CodeEditor.doForSelectedLines')
        if end > (block.position() + block.length()):
            # Now check if there is only whitespace before the start of selection
            # If so, include this whitespace in the selection and update the
            # selection of the editor
            textBeforeSelection = block.text()[: cursor.positionInBlock()]
            if len(textBeforeSelection.strip()) == 0:
                start = block.position()  # Move start to include leading whitespace

                # Update the textcursor of our editor. If originally the
                # anchor was before the cursor, restore that situation
                if anchorBeforeCursor:
                    self.__setCursorPositionAndAnchor(cursor, end, start)
                else:
                    self.__setCursorPositionAndAnchor(cursor, start, end)

                # Setting the textcursor might scroll to another place
                # (e.g. Ctrl+A, Ctrl+C would scroll to the very bottom).
                # To prevent this, we store and then restore the position
                # of the vertical scrollbar
                sb = self.verticalScrollBar()
                scrollbarPos = sb.value()
                self.setTextCursor(cursor)
                sb.setValue(scrollbarPos)

        # Call our supers copy slot to do the actual copying
        super().copy()

    def cut(self):
        """Cutting with smart-copy: the part that is copied is the same as self.copy(),
        but the part that is removed is only the original selection

        see: Qt qtextcontrol.cpp, cut()
        """
        if (
            self.textInteractionFlags() & QtCore.Qt.TextInteractionFlag.TextEditable
        ) and self.textCursor().hasSelection():
            cursor = self.textCursor()
            self.copy()
            # Restore original cursor
            self.setTextCursor(cursor)
            cursor.removeSelectedText()

    def paste(self):
        """Smart paste
        If you paste on a position that has only whitespace in front of it,
        remove the whitespace before pasting. Combined with smart copy,
        this ensure indentation of the
        """
        self._paste(keepSelection=False)

    def pasteAndSelect(self):
        """Smart paste
        Like paste(), but keep the part that was pasted selected. This allows
        you to change the indentation after pasting using tab / shift-tab
        """
        self._paste(keepSelection=True)

    def _paste(self, keepSelection):
        # Create a cursor of the current selection
        cursor = self.textCursor()

        # Ensure that position is at start and anchor is at the end.
        # This is required to ensure that with keepPositionOnInsert
        # set, the cursor will equal the pasted text after the pasting
        self.__ensureCursorBeforeAnchor(cursor)

        # Change this cursor to let the position() stay at its place upon
        # inserting the new code; the anchor will move to the end of the insertion
        cursor.setKeepPositionOnInsert(True)
        super().paste()

        block = cursor.block()

        # Check if the thing to be pasted is multi-line. Use > not >=
        # to ensure we don't count it as multi-line if the cursor
        # is just at the beginning of the next block (consistent with
        # 'CodeEditor.doForSelectedLines')
        if cursor.selectionEnd() > block.position() + block.length():
            # Now, check if in front of the current selection there is only whitespace
            if len(block.text()[: cursor.positionInBlock()].strip()) == 0:
                # Note that this 'smart pasting' will be a separate item on the
                # undo stack. This is intentional: the user can undo the 'smart paste'
                # without undoing the paste
                cursor2 = QtGui.QTextCursor(cursor)
                cursor2.setPosition(
                    cursor2.position()
                )  # put the anchor where the cursor is

                # Move cursor2 to beginning of the line (selecting the whitespace)
                # and remove the selection
                cursor2.movePosition(
                    cursor2.MoveOperation.StartOfBlock, cursor2.MoveMode.KeepAnchor
                )
                cursor2.removeSelectedText()

        # Set the textcursor of this editor to the just-pasted selection
        if keepSelection:
            cursor.setKeepPositionOnInsert(False)
            self.setTextCursor(cursor)


class AutoCloseQuotesAndBrackets:
    """
    Automatic insertion of quotes, parenthesis, braces and brackets

    """

    def autoClose_Brackets(self):
        return self.__autoClose_Brackets

    @ce_option(False)
    def setAutoClose_Brackets(self, value):
        self.__autoClose_Brackets = value

    def autoClose_Quotes(self):
        return self.__autoClose_Quotes

    @ce_option(False)
    def setAutoClose_Quotes(self, value):
        self.__autoClose_Quotes = value

    def _get_token_at_cursor(self, cursor=None, relpos=0):
        """Get token at the (current or given) cursor position. Can be None."""
        if cursor is None:
            cursor = self.textCursor()
        pos = cursor.positionInBlock() + relpos
        tokenAtCursor = None
        for token in cursor.block().userData().tokens:
            if hasattr(token, "start"):
                if token.start > pos:
                    break
                if token.start <= pos < token.end:
                    tokenAtCursor = token
                    break
            if isinstance(token, MultilineStringToken):
                # multiline string tokens can have a length
                # of zero if the whole line is an empty comment
                if token.start == token.end == 0:
                    tokenAtCursor = token
                    break
        return tokenAtCursor

    def keyPressEvent(self, event):
        try:
            self.__keyPressEvent(event)
        except Exception as err:
            # When there is a bug in our fancy autoclosing stuff, better print and
            # and have the plain behavior instead of not working ...
            print(err)
            super().keyPressEvent(event)

    def __keyPressEvent(self, event):
        quotes = "'", '"'
        openBrackets = "{", "[", "("
        closeBrackets = "}", "]", ")"
        brackets = openBrackets + closeBrackets

        cursor = self.textCursor()
        char = event.text()

        #  brackets
        if char in brackets and self.__autoClose_Brackets:
            # Don't autobracket inside comments and strings
            if isinstance(
                self._get_token_at_cursor(cursor),
                (
                    CommentToken,
                    StringToken,
                    MultilineStringToken,
                    UnterminatedStringToken,
                ),
            ):
                super().keyPressEvent(event)
                return

            if char in openBrackets:
                idx = openBrackets.index(char)
                next_char = self.__getNextCharacter()
                if cursor.selectedText():
                    # Surround selection with brackets
                    new_text = (
                        openBrackets[idx] + cursor.selectedText() + closeBrackets[idx]
                    )
                    cursor.setKeepPositionOnInsert(True)
                    cursor.insertText(new_text)
                    cursor.setKeepPositionOnInsert(False)
                    self.setTextCursor(cursor)
                elif (
                    next_char.strip() and next_char not in closeBrackets
                ):  # str.strip() conveniently removes all kinds of whitespace
                    # Only autoclose if the char on the right is whitespace
                    cursor.insertText(char)  # == super().keyPressEvent(event)
                else:
                    # Auto-close bracket
                    insert_txt = "{}{}".format(openBrackets[idx], closeBrackets[idx])
                    cursor.insertText(insert_txt)
                    self._moveCursorLeft(1)

            elif char in closeBrackets:
                idx = closeBrackets.index(char)
                next_char = self.__getNextCharacter()
                if cursor.selectedText():
                    # Replace
                    cursor.insertText(char)
                elif next_char == char:
                    # Skip
                    self._moveCursorRight(1)
                else:
                    # Normal
                    cursor.insertText(char)  # == super().keyPressEvent(event)

        # quotes
        elif char in quotes and self.__autoClose_Quotes:
            next_char = self.__getNextCharacter()

            # Don't autoquote inside comments and multiline strings
            # Only allow "doing our thing" when we're at the end of a normal string
            token = self._get_token_at_cursor(cursor)
            if isinstance(token, (CommentToken, MultilineStringToken)):
                super().keyPressEvent(event)
                return
            elif isinstance(token, StringToken) and char != next_char:
                super().keyPressEvent(event)
                return

            if cursor.selectedText() in ('"', "'"):
                # Skip over char if it's one char and a quote
                self._moveCursorRight(1)
            elif cursor.selectedText():
                # Surround selection with quotes, maybe even multi-line
                new_text = char + cursor.selectedText() + char
                if "\u2029" in new_text and "python" in self.parser().name().lower():
                    new_text = char * 2 + new_text + char * 2
                cursor.setKeepPositionOnInsert(True)
                cursor.insertText(new_text)
                cursor.setKeepPositionOnInsert(False)
                self.setTextCursor(cursor)
            elif next_char == char:
                # Skip
                self._moveCursorRight(1)
            else:
                # Only autoquote if we're next to whitespace, operator, quote
                tokenL = self._get_token_at_cursor(cursor, -1)
                tokenR = self._get_token_at_cursor(cursor, -0)

                if (
                    isinstance(tokenR, IdentifierToken)
                    or isinstance(
                        tokenL, StringToken
                    )  # don't add a fourth " when typing " after two "
                    or (
                        isinstance(tokenL, IdentifierToken)
                        and str(tokenL).lower() not in stringLiteralPrefixes
                    )
                ):
                    super().keyPressEvent(event)
                    return
                # Auto-close
                cursor.insertText(char * 2)
                self._moveCursorLeft(1)
                # # Maybe handle triple quotes (add 2 more if we now have 3 on the left)
                # Disabled: this feature too easily gets in the way
                # if 'python' in self.parser().name().lower():
                #     cursor = self.textCursor()
                #     cursor.movePosition(cursor.MoveOperation.PreviousCharacter, cursor.MoveMode.KeepAnchor, 3)
                #     if cursor.selectedText() == char * 3:
                #         edit_cursor = self.textCursor()
                #         edit_cursor.insertText(char * 2)
                #         self._moveCursorLeft(2)

        # remove whole couple of brackets when hitting backspace
        elif event.key() == Qt.Key.Key_Backspace and self.__autoClose_Brackets:
            if isinstance(
                self._get_token_at_cursor(cursor),
                (
                    CommentToken,
                    StringToken,
                    MultilineStringToken,
                    UnterminatedStringToken,
                ),
            ):
                super().keyPressEvent(event)
                return

            else:
                prev_char = self.__getPreviousCharacter()
                next_char = self.__getNextCharacter()

                if prev_char == "(" and next_char == ")":
                    cursor.deleteChar()
                elif prev_char == "[" and next_char == "]":
                    cursor.deleteChar()
                elif prev_char == "{" and next_char == "}":
                    cursor.deleteChar()

                super().keyPressEvent(event)

        else:
            super().keyPressEvent(event)

    def __getNextCharacter(self):
        cursor = self.textCursor()
        cursor.movePosition(
            cursor.MoveOperation.NoMove, cursor.MoveMode.MoveAnchor
        )  # rid selection
        cursor.movePosition(
            cursor.MoveOperation.NextCharacter, cursor.MoveMode.KeepAnchor
        )
        next_char = cursor.selectedText()
        return next_char

    def __getPreviousCharacter(self):
        cursor = self.textCursor()
        cursor.movePosition(
            cursor.MoveOperation.NoMove, cursor.MoveMode.MoveAnchor
        )  # rid selection
        cursor.movePosition(
            cursor.MoveOperation.PreviousCharacter, cursor.MoveMode.KeepAnchor
        )
        previous_char = cursor.selectedText()
        return previous_char

    def _moveCursorLeft(self, n):
        """Move cursor left between eg. brackets"""
        cursor2 = self.textCursor()
        cursor2.movePosition(cursor2.MoveOperation.Left, cursor2.MoveMode.MoveAnchor, n)
        self.setTextCursor(cursor2)

    def _moveCursorRight(self, n):
        """Move cursor out of eg. brackets"""
        cursor2 = self.textCursor()
        cursor2.movePosition(
            cursor2.MoveOperation.Right, cursor2.MoveMode.MoveAnchor, n
        )
        self.setTextCursor(cursor2)
