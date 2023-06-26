import os
import sys
import pyzo
from pyzo import translate
from pyzo.qt import QtCore, QtGui, QtWidgets, QtPrintSupport


class PdfExport(QtWidgets.QDialog):
    """
    This class is used to export an editor to a pdf.
    The content of the editor is copied in another editor,
    and then the options chosen are applied by _updateTemporaryEditor()
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle(translate("menu dialog", "Pdf Export"))

        self.resize(1000, 600)

        self._printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
        self._printer.setColorMode(QtPrintSupport.QPrinter.Color)

        self._preview = QtPrintSupport.QPrintPreviewWidget(self._printer)
        self._preview.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        self._chkLineNumbers = QtWidgets.QCheckBox(
            "Print line number", self, checked=True
        )

        self._currentEditor = pyzo.editors.getCurrentEditor()
        self._editor = pyzo.core.editor.PyzoEditor("")

        self._sliderZoom = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._sliderZoom.setMinimum(-10)
        self._sliderZoom.setMaximum(10)
        self._sliderZoom.setTickInterval(1)
        self._sliderZoom.setValue(pyzo.config.view.zoom)
        self._lblZoom = QtWidgets.QLabel()
        self._updateZoomLabel()
        self._sliderZoom.valueChanged.connect(self._updateZoomLabel)

        self._chkSyntaxHighlighting = QtWidgets.QCheckBox(
            "Enable syntax highlighting", self, checked=True
        )

        self._cmbFileName = QtWidgets.QComboBox(self)
        self._cmbFileName.addItem("Do not print the file name", 0)
        self._cmbFileName.addItem("Print with file name", 1)
        self._cmbFileName.addItem("Print with file name and absolute path", 2)
        self._cmbFileName.setCurrentIndex(1)
        self._cmbFileName.setToolTip("The title at the top of the document")

        self._cmbPageOrientation = QtWidgets.QComboBox(self)
        self._cmbPageOrientation.addItem("Portrait", 0)
        self._cmbPageOrientation.addItem("Landscape", 1)
        self._cmbPageOrientation.setToolTip("Orientation of the document")

        self._btnUpdatePreview = QtWidgets.QPushButton("Update preview", self)
        self._btnUpdatePreview.clicked.connect(self._updatePreview)
        self._btnExport = QtWidgets.QPushButton("Export")
        self._btnExport.clicked.connect(self._exportPdf)
        self._btnDone = QtWidgets.QPushButton("Done", self)
        self._btnDone.clicked.connect(self.close)

        self._mainLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self._mainLayout)
        self._rightLayout = QtWidgets.QVBoxLayout()
        self._mainLayout.addWidget(self._preview)
        self._mainLayout.addLayout(self._rightLayout)

        self._optionLayout = QtWidgets.QFormLayout()
        self._rightLayout.addLayout(self._optionLayout)
        self._optionLayout.addRow(self._cmbFileName)
        self._optionLayout.addRow(self._chkLineNumbers)
        self._optionLayout.addRow(self._chkSyntaxHighlighting)
        self._optionLayout.addRow(self._lblZoom, self._sliderZoom)
        self._optionLayout.addRow(self._cmbPageOrientation)

        self._bottomLayout = QtWidgets.QHBoxLayout()
        self._rightLayout.addLayout(self._bottomLayout)
        self._bottomLayout.addStretch()
        self._bottomLayout.addWidget(self._btnUpdatePreview)
        self._bottomLayout.addWidget(self._btnExport)
        self._bottomLayout.addWidget(self._btnDone)

        self._preview.paintRequested.connect(self._editor.print_)

        self._updatePreview()

    def _updateTemporaryEditor(self):
        """update the temporary editor for preview and export"""

        self._editor.setZoom(pyzo.config.view.zoom + self._sliderZoom.value())

        if self._chkSyntaxHighlighting.isChecked():
            parser = self._currentEditor.parser().name()
        else:
            parser = None
        self._editor.setParser(parser)

        self._updateOrientation()

        # Print name or filename in the editor
        headerLines = []
        if self._cmbFileName.currentIndex() == 1:
            headerLines = ["# " + self._currentEditor.name, ""]
        elif self._cmbFileName.currentIndex() == 2:
            headerLines = ["# " + self._currentEditor.filename, ""]

        editorLines = self._currentEditor.toPlainText().splitlines()

        # Print line numbers in the editor
        showLineNumbers = self._chkLineNumbers.isChecked()
        if showLineNumbers:
            numDigits = len(str(len(editorLines)))
            for i, s in enumerate(editorLines):
                editorLines[i] = str(i + 1).rjust(numDigits, "0") + "| " + s

        self._editor.clear()
        cursor = self._editor.textCursor()
        cursor.beginEditBlock()
        cursor.insertText("\n".join(headerLines + editorLines))

        # Highlight line numbers
        if showLineNumbers:
            fmt = QtGui.QTextCharFormat()
            fmt.setBackground(QtGui.QColor(240, 240, 240))
            cursor.movePosition(cursor.Start, cursor.MoveAnchor)
            notAtLastBlock = cursor.movePosition(
                cursor.NextBlock, cursor.MoveAnchor, len(headerLines)
            )
            while notAtLastBlock:
                cursor.movePosition(cursor.Right, cursor.KeepAnchor, numDigits)
                cursor.setCharFormat(fmt)
                notAtLastBlock = cursor.movePosition(
                    cursor.NextBlock, cursor.MoveAnchor
                )

        cursor.endEditBlock()

    def _updatePreview(self):
        """Update the widget preview"""
        self._updateTemporaryEditor()
        self._preview.updatePreview()

    def _exportPdf(self):
        """Exports the code as pdf, and opens file manager"""
        options = QtWidgets.QFileDialog.Option(0)
        if not pyzo.config.advanced.useNativeFileDialogs:
            options |= QtWidgets.QFileDialog.Option.DontUseNativeDialog
        filename = QtWidgets.QFileDialog.getSaveFileName(
            None, "Export PDF", os.path.expanduser("~"), "*.pdf", options=options
        )
        if isinstance(filename, tuple):  # PySide
            filename = filename[0]
        if not filename:
            return

        self._printer.setOutputFileName(filename)
        self._updateTemporaryEditor()
        self._editor.print_(self._printer)

        if self._printer.printerState() == self._printer.Error:
            # Notify in logger
            msg = 'could not export PDF file to "{}"'.format(filename)
            print(msg)
            # Make sure the user knows
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle("Error exporting PDF file")
            m.setText(msg)
            m.setIcon(m.Warning)
            m.exec_()

    def _updateZoomLabel(self):
        self._lblZoom.setText("Zoom level: {}".format(self._sliderZoom.value()))

    def _updateOrientation(self):
        """Set document in portrait or landscape orientation"""
        index = self._cmbPageOrientation.currentIndex()
        if hasattr(self._printer, "setOrientation"):  # PySide5, PyQt5
            base = QtPrintSupport.QPrinter
            orientation = [base.Portrait, base.Landscape][index]
            self._preview.setOrientation(orientation)
            self._printer.setOrientation(orientation)
        else:  # PySide6, PyQt6
            base = QtGui.QPageLayout
            orientation = [base.Portrait, base.Landscape][index]

            self._preview.setOrientation(orientation)
            if sys.platform == "win32":
                self._preview.setOrientation(
                    orientation
                )  # calling this a second time is a
                # workaround, otherwise the preview in Qt6 is wrong when switching orientation
                # on Windows 10 with Qt 6.5.0

            layout = QtGui.QPageLayout()
            layout.setOrientation(orientation)
            self._printer.setPageLayout(layout)
