from ..qt import QtCore, QtGui, QtWidgets  # noqa

Qt = QtCore.Qt


class Calltip:
    _styleElements = [
        (
            "Editor.calltip",
            "The style of the calltip. ",
            "fore:#555, back:#ff9, border:1",
        )
    ]

    class __CalltipLabel(QtWidgets.QLabel):
        def __init__(self, parent):
            super().__init__(parent)

            # Start hidden
            self.hide()
            # Accept rich text
            self.setTextFormat(QtCore.Qt.TextFormat.RichText)
            # Show as tooltip
            self.setIndent(2)
            self.setWindowFlags(QtCore.Qt.WindowType.ToolTip)

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        # Create label for call tips  -- it needs a parent, otherwise it will cause a crash on Linux with Wayland
        self.__calltipLabel = self.__CalltipLabel(self)
        # Be notified of style updates
        self.styleChanged.connect(self.__afterSetStyle)

        self.cursorPositionChanged.connect(self.__onCursorPositionChanged)

        # Prevents calltips from being shown immediately after pressing
        # the escape key.
        self.__noshow = False

        self.__startcursor = None

    def __afterSetStyle(self):
        format = self.getStyleElementFormat("editor.calltip")
        ss = "QLabel {{ color:{}; background:{}; border:{}px solid {}; }}".format(
            format["fore"],
            format["back"],
            int(format["border"]),
            format["fore"],
        )
        self.__calltipLabel.setStyleSheet(ss)

    def setCalltipFinishedCallback(self, cb):
        self.__finishedCallback = cb

    def calltipShow(self, offset=0, richText="", highlightFunctionName=False):
        """Shows the given calltip.

        Parameters
        ----------
        offset : int
            The character offset to show the tooltip.
        richText : str
            The text to show (may contain basic html for markup).
        highlightFunctionName : bool
            If True the text before the first opening brace is made bold.
            default False.
        """

        # Do not show the calltip if it was deliberately hidden by the
        # user.
        if self.__noshow:
            return

        # Process calltip text?
        if highlightFunctionName:
            i = richText.find("(")
            if i > 0:
                richText = "<b>{}</b>{}".format(richText[:i], richText[i:])

        # Get a cursor to establish the position to show the calltip
        startcursor = self.textCursor()
        startcursor.movePosition(startcursor.MoveOperation.Left, n=offset)
        self.__startcursor = startcursor

        # Get position in pixel coordinates
        rect = self.cursorRect(startcursor)
        pos = rect.topLeft()
        pos.setY(pos.y() - rect.height() - 1)  # Move one above line
        pos.setX(pos.x() - 3)  # Correct for border and indent
        pos = self.viewport().mapToGlobal(pos)

        label = self.__calltipLabel
        textChanged = richText != label.text()

        # Set text and update font
        label.setText(richText)
        label.setFont(self.font())

        # Use a qt tooltip to show the calltip
        if richText:
            if textChanged and label.isVisible():
                # When the tooltip label is still shown and we update the text, the
                # rectangle of the label is not updated. This leads to truncated text
                # or to empty space on the right of the label.
                # As a workaround, we hide and then show the label again.
                label.hide()

            label.move(pos)
            label.show()
        else:
            label.hide()

    def calltipCancel(self):
        """Hides the calltip."""
        self.__calltipLabel.hide()
        self.__startcursor = None

        if self.__finishedCallback is not None:
            self.__finishedCallback()

    def calltipActive(self):
        """Get whether the calltip is currently active."""
        return self.__calltipLabel.isVisible()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.__calltipLabel.hide()

    def keyPressEvent(self, event):
        # If the user presses Escape and the calltip is active, hide it
        if (
            event.key() == Qt.Key.Key_Escape
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
            and self.calltipActive()
        ):
            self.calltipCancel()
            self.__noshow = True
            return

        if event.text() == "(":
            self.__noshow = False
        elif event.text() == ")":
            self.calltipCancel()

        # Proceed processing the keystrike
        super().keyPressEvent(event)

    def __onCursorPositionChanged(self, *args):
        if self.calltipActive():
            if self.__startcursor is not None:
                if self.__startcursor.blockNumber() != self.textCursor().blockNumber():
                    self.calltipCancel()
