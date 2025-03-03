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
        self.cursor_pos.setFixedWidth(190)
        self.insertPermanentWidget(1, self.cursor_pos, 0)

    def updateCursorInfo(self, editor):
        # Get current line number
        nrow = 0
        ncol = 0
        if editor:
            nrow = editor.textCursor().blockNumber() + 1
            ncol = editor.textCursor().positionInBlock() + 1

        position_txt = "Line: {}, Column: {} ".format(nrow, ncol)
        self.cursor_pos.setText(position_txt)
