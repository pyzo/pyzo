"""Module statusbar

Functionality for status bar in pyzo.

"""

from pyzo.qt import QtWidgets


class StatusBar(QtWidgets.QStatusBar):
    """
    Add a statusbar to main window

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Cursor position
        self.cursor_pos = QtWidgets.QLabel(self)
        self.addPermanentWidget(self.cursor_pos)

    def updateCursorInfo(self, editor):
        # Get current line number
        nrow = 0
        ncol = 0
        sel = 0
        if editor:
            cur = editor.textCursor()
            nrow = cur.blockNumber() + 1
            ncol = cur.positionInBlock() + 1
            sel = cur.selectionEnd() - cur.selectionStart()

        position_txt = "Line: {}, Column: {}, Sel.: {} ".format(nrow, ncol, sel)
        self.cursor_pos.setText(position_txt)
