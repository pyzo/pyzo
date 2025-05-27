"""
Code editor extensions that provides autocompleter functionality
"""

from ..qt import QtGui, QtCore, QtWidgets

Qt = QtCore.Qt

import keyword

import os

"""
On a Ubuntu 22.04 like Linux distribution with Wayland, gdm3 and Qt6, Pyzo crashes
when using the autocompletion popup list, sometimes immediately, other times when
rapidly opening and cancelling the popup list several times in a row.
After the crash the following error message is displayed in the terminal:
"The Wayland connection experienced a fatal error: Protocol error"

The following workaround was elaborated via educated guesses and trial & error:
Setting the Qt window type of the autocompletion list to ToolTip avoids the crash.
But Key_Up and Key_Down will not move the list selection anymore, so we have to catch
these key events and decrement/increment the selected index in our own event handler.
To avoid any side effects for other operating systems and environments (for example X11),
we only use this workaround on Linux computers with Wayland. We can detect this by
checking environment variable "XDG_SESSION_TYPE".
"""
USE_WAYLAND_WORKAROUND = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


# TODO: use this CompletionListModel to style the completion suggestions (class names, method names, keywords etc)
class CompletionListModel(QtCore.QStringListModel):
    def data(self, index, role):
        if role == Qt.ForegroundRole:
            # data = str(QtWidgets.QStringListModel.data(self, index, QtCore.Qt.DisplayRole))
            # return QtGui.QBrush(Qt.red)
            return None
        else:
            return super().data(index, role)


# todo: use keywords from the parser
class AutoCompletion:
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        # Autocompleter
        self.__completerModel = QtCore.QStringListModel(keyword.kwlist)
        self.__completer = QtWidgets.QCompleter(self)
        self.__completer.setModel(self.__completerModel)
        self.__completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.__completer.setWidget(self)
        self.__completerNames = []
        self.__recentCompletions = []  # List of recently selected completions
        self.__completerWindow = self.__completer.popup()
        if USE_WAYLAND_WORKAROUND:
            self.__completerWindow.setWindowFlags(QtCore.Qt.WindowType.ToolTip)

        self.__finishedCallback = None

        # geometry
        self.__popupSize = 300, 100

        # Text position corresponding to first character of the word being completed
        self.__autocompleteStart = None

        # We show the popup when this many chars have been input
        self.__autocompleteMinChars = 3
        self.__autocompleteFromObject = False
        self.__autocompleteVisible = False

        self.__autocompleteDebug = False

        self.__autocompletionAcceptKeys = (Qt.Key.Key_Tab,)

        # Connect signals
        self.__highlightedCompletion = None
        self.__completer.activated.connect(self.onAutoComplete)
        self.__completer.highlighted.connect(self._setHighlightedCompletion)

    def _setHighlightedCompletion(self, value):
        """Keeping track of the highlighted item allows us
        to 'manually' perform an autocompletion.
        """
        self.__highlightedCompletion = value

    ## Properties
    def recentCompletionsList(self):
        """The list of recent auto-completions. This property may be set to a
        list that is shared among several editors, in order to share the notion
        of recent auto-completions
        """
        return self.__recentCompletions

    def setRecentCompletionsList(self, value):
        self.__recentCompletions = value

    def completer(self):
        return self.__completer

    def setAutoCompletionAcceptKeys(self, *keys):
        """Set the keys (Qt enums) that can accept an autocompletion.
        Like Tab, or Enter. Defaut Tab.
        """
        self.__autocompletionAcceptKeys = keys

    def setAutocompleteFinishedCallback(self, cb):
        self.__finishedCallback = cb

    ## Autocompletion

    def setAutocompletPopupSize(self, width, height):
        """Set the size (width, heigth) of the automcompletion popup window."""
        self.__popupSize = width, height

    def setAutocompleteCaseSensitive(self, b):
        """Set the case sensitivity for autocompletion."""
        cs = Qt.CaseSensitive if b else Qt.CaseSensitivity.CaseInsensitive
        self.__completer.setCaseSensitivity(cs)

    def setAutocompleteMinChars(self, n):
        """Set the number of chars where we show the popup."""
        self.__autocompleteMinChars = n

    def autocompleteShow(self, offset=0, names=None, fromObject=False):
        """Pop-up the autocompleter (if not already visible) and position it at current
        cursor position minus offset. If names is given and not None, it is set
        as the list of possible completions.
        """
        # Pop-up the autocompleteList
        startcursor = self.textCursor()
        startcursor.movePosition(startcursor.MoveOperation.Left, n=offset)
        self.__autocompleteFromObject = fromObject

        if self.__autocompleteDebug:
            print("autocompleteShow called")

        if names is not None:
            # TODO: a more intelligent implementation that adds new items and removes
            # old ones
            if names != self.__completerNames:
                self.__completerModel.setStringList(names)
                self.__completerNames = names

        if (
            not self.autocompleteActive()
            or startcursor.position() != self.__autocompleteStart.position()
            or not self.autocompleteVisible()
        ):
            self.__autocompleteStart = startcursor
            self.__autocompleteStart.setKeepPositionOnInsert(True)

            # Popup the autocompleter. Don't use .complete() since we want to
            # position the popup manually
            self.__positionAutocompleter()
            if self.__updateAutocompleterPrefix():
                self.__autocompleteVisible = True
                self.__completerWindow.show()
            if self.__autocompleteDebug:
                print("self.__completerWindow.show() called")

        else:
            self.__updateAutocompleterPrefix()

    def autocompleteAccept(self):
        self.__completerWindow.hide()
        self.__autocompleteStart = None
        self.__autocompleteVisible = False
        if self.__finishedCallback is not None:
            self.__finishedCallback()

    def autocompleteCancel(self):
        self.__completerWindow.hide()
        self.__autocompleteStart = None
        self.__autocompleteVisible = False
        if self.__finishedCallback is not None:
            self.__finishedCallback()

    def onAutoComplete(self, text=None):
        if text is None:
            text = self.__highlightedCompletion
        # Select the text from autocompleteStart until the current cursor
        cursor = self.textCursor()
        cursor.setPosition(
            self.__autocompleteStart.position(), cursor.MoveMode.KeepAnchor
        )
        # Replace it with the selected text
        cursor.insertText(text)
        self.autocompleteAccept()  # Reset the completer

        # get the characters to the left and right of the cursor after autocompletion
        line = cursor.block().text()
        i = cursor.positionInBlock()
        charLeft = line[i - 1 : i]
        charRight = line[i : i + 1]

        isKeyAutocompletion = False
        if charLeft in "'\")":
            isKeyAutocompletion = True
            # key autocompletion with string literal or tuple
            if charLeft == charRight:
                # remove the duplicated closing quote resp. closing parenthesis
                # ... during key autocompletion with a string literal or tuple
                cursor.deleteChar()
                i += 1
                charRight = line[i : i + 1]

        if not text.isidentifier():
            # e.g. key autocompletion with list index
            isKeyAutocompletion = True

        if isKeyAutocompletion and charRight == "]":
            # move the cursor after the closing bracket after key autocompletion
            cursor.movePosition(cursor.MoveOperation.Right)
            self.setTextCursor(cursor)

        # Update the recent completions list
        if text in self.__recentCompletions:
            self.__recentCompletions.remove(text)
        self.__recentCompletions.append(text)

    def autocompleteActive(self):
        """Returns whether an autocompletion list is currently started."""
        return self.__autocompleteStart is not None

    def autocompleteVisible(self):
        """Returns whether an autocompletion list is currently shown."""
        return self.__autocompleteVisible

    def __positionAutocompleter(self):
        """Move the autocompleter list to a proper position"""
        # Find the start of the autocompletion and move the completer popup there
        cur = QtGui.QTextCursor(self.__autocompleteStart)  # Copy __autocompleteStart

        # Set size
        geometry = self.__completerWindow.geometry()
        geometry.setWidth(self.__popupSize[0])
        geometry.setHeight(self.__popupSize[1])
        self.__completerWindow.setGeometry(geometry)

        # Initial choice for position of the completer
        position = self.cursorRect(cur).bottomLeft() + self.viewport().pos()

        # Check if the completer is going to go off the editor/shell widget
        if (
            position.y() + geometry.height()
            > self.viewport().pos().y() + self.viewport().height()
        ):
            # Move the completer to above the current line
            position = self.cursorRect(cur).topLeft() + self.viewport().pos()
            global_position = self.mapToGlobal(position)
            global_position -= QtCore.QPoint(0, int(geometry.height()))
        else:
            global_position = self.mapToGlobal(position)

        self.__completerWindow.move(global_position)

    def __updateAutocompleterPrefix(self):
        """Find the autocompletion prefix (the part of the word that has been
        entered) and send it to the completer. Update the selected completion
        (out of several possiblilties) which is best suited
        """
        if not self.autocompleteActive():
            self.__completerWindow.hide()  # TODO: why is this required?
            self.__autocompleteVisible = False
            return False

        # Select the text from autocompleteStart until the current cursor
        cursor = self.textCursor()
        cursor.setPosition(
            self.__autocompleteStart.position(), cursor.MoveMode.KeepAnchor
        )

        prefix = cursor.selectedText()
        if (
            not self.__autocompleteFromObject
            and len(prefix) < self.__autocompleteMinChars
        ):
            self.__completer.setCompletionPrefix("")
            self.autocompleteCancel()
            return False
        else:
            self.__completer.setCompletionPrefix(prefix)
            model = self.__completer.completionModel()
            if model.rowCount():
                # Create a list of all possible completions, and select the one
                # which is best suited. Use the one which is highest in the
                # __recentCompletions list, but prefer completions with matching
                # case if they exists

                # Create a list of (row, value) tuples of all possible completions
                completions = [
                    (
                        row,
                        model.data(
                            model.index(row, 0), self.__completer.completionRole()
                        ),
                    )
                    for row in range(model.rowCount())
                ]

                # Define a function to get the position in the __recentCompletions
                def completionIndex(data):
                    try:
                        return self.__recentCompletions.index(data)
                    except ValueError:
                        return -1

                # Sort twice; the last sort has priority over the first

                # Sort on most recent completions
                completions.sort(key=lambda c: completionIndex(c[1]), reverse=True)
                # Sort on matching case (prefer matching case)
                completions.sort(key=lambda c: c[1].startswith(prefix), reverse=True)

                # apply the best match
                bestMatchRow = completions[0][0]
                self.__completerWindow.setCurrentIndex(model.index(bestMatchRow, 0))

                return True

            else:
                # No match, just hide
                self.autocompleteCancel()
                return False

    def potentiallyAutoComplete(self, event):
        """Given a keyEvent, check if we should perform an autocompletion.

        Returns 0 if no autocompletion was performed. Return 1 if
        autocompletion was performed, but the key event should be processed
        as normal. Return 2 if the autocompletion was performed, and the key
        should be consumed.
        """
        if self.autocompleteActive():
            if event.key() in self.__autocompletionAcceptKeys:
                if event.key() <= 128:
                    self.onAutoComplete()  # No arg: select last highlighted
                    event.ignore()
                    return 1  # Let key have effect as normal
                elif event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    # The key
                    self.onAutoComplete()  # No arg: select last highlighted
                    return 2  # Key should be consumed
        return 0

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if (
            key == Qt.Key.Key_Escape
            and modifiers == Qt.KeyboardModifier.NoModifier
            and self.autocompleteActive()
        ):
            self.autocompleteCancel()
            return  # Consume the key

        if self.potentiallyAutoComplete(event) > 1:
            return  # Consume

        if USE_WAYLAND_WORKAROUND and self.autocompleteActive():
            deltaRow = 0
            if key == Qt.Key.Key_Up:
                deltaRow = -1
            elif key == Qt.Key.Key_Down:
                deltaRow = 1
            if deltaRow != 0:
                row = self.__completerWindow.currentIndex().row() + deltaRow
                model = self.__completerWindow.model()
                self.__completerWindow.setCurrentIndex(
                    model.index(row % model.rowCount(), 0)
                )
                return  # consume the key

        # Allowed keys that do not close the autocompleteList:
        # alphanumeric and _ and shift
        # Backspace (until start of autocomplete word)
        if (
            self.autocompleteActive()
            and not event.text().isalnum()
            and event.text() != "_"
            and key != Qt.Key.Key_Shift
            and not (
                (key == Qt.Key.Key_Backspace)
                and self.textCursor().position() > self.__autocompleteStart.position()
            )
        ):
            self.autocompleteCancel()

        # Apply the key that was pressed
        super().keyPressEvent(event)

        if self.autocompleteActive():
            # While we type, the start of the autocompletion may move due to line
            # wrapping, so reposition after every key stroke
            self.__positionAutocompleter()
            self.__updateAutocompleterPrefix()

    def mousePressEvent(self, event):
        if self.autocompleteActive():
            self.autocompleteCancel()
        super().mousePressEvent(event)
