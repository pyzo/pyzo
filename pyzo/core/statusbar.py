""" Module statusbar

Functionality for status bar in pyzo.

"""
from pyzo.util.qt import QtWidgets


class StatusBar(QtWidgets.QStatusBar):
    """
    Add a statusbar to main window

    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # File encoding
        self.file_encoding = QtWidgets.QLabel(self)
        self.file_encoding.setFixedWidth(100)
        self.insertPermanentWidget(0, self.file_encoding, 0)

        # Cursor position
        self.cursor_pos = QtWidgets.QLabel(self)
        self.cursor_pos.setFixedWidth(190)
        self.insertPermanentWidget(1, self.cursor_pos, 0)

    def updateCursorInfo(self, editor):

        # Get current line number
        nrow = 0
        ncol = 0
        if editor:
            nrow = editor.textCursor().blockNumber()
            nrow += 1  # is ln as in line number area
            ncol = editor.textCursor().positionInBlock()
            ncol += 1

        position_txt = "Line: {}, Column: {} ".format(str(nrow), str(ncol))
        self.cursor_pos.setText(position_txt)

    def updateFileEncodingInfo(self, editor):

        fe_txt = ""
        if editor:
            fe_txt = editor.encoding.upper()

        self.file_encoding.setText(fe_txt)
