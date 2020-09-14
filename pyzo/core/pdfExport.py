from pyzo.util.qt import QtCore, QtGui, QtWidgets
from pyzo import translate
import pyzo
import os
from pyzo.codeeditor import Manager


class PdfExport(QtWidgets.QDialog):
    """
    This class is used to export an editor to a pdf.
    The content of the editor is copied in another editor,
    and then the options chosen are applied by _print()
    """

    def __init__(self):
        super().__init__()

        from pyzo.util.qt import QtPrintSupport

        self.printer = QtPrintSupport.QPrinter(
            QtPrintSupport.QPrinter.HighResolution,
        )

        # To allow pdf export with color
        self.printer.setColorMode(QtPrintSupport.QPrinter.Color)

        # Default settings
        self.show_line_number = True
        self._enable_syntax_highlighting = True

        # Set title
        self.setWindowTitle(translate("menu dialog", "Pdf Export"))

        # Set dialog size
        size = 1000, 600
        offset = 0
        size2 = size[0], size[1] + offset
        self.resize(*size2)
        # self.setMinimumSize(*size2)

        # Button to export to pdf
        self.validation_button = QtWidgets.QPushButton("Export")
        self.validation_button.clicked.connect(self._export_pdf)

        # Button to update the preview
        self.button_update_preview = QtWidgets.QPushButton("Update preview", self)
        self.button_update_preview.clicked.connect(self._update_preview)

        # Previw widget
        self.preview = QtPrintSupport.QPrintPreviewWidget(self.printer)

        # Lines numbers option
        self.checkbox_line_number = QtWidgets.QCheckBox(
            "Print line number", self, checked=self.show_line_number
        )

        self.checkbox_line_number.stateChanged.connect(self._get_show_line_number)

        # Make of copy of the editor
        self.current_editor = pyzo.editors.getCurrentEditor()
        self.editor_name = self.current_editor.name
        self.editor_filename = self.current_editor.filename
        self.editor = pyzo.core.editor.PyzoEditor(
            pyzo.editors.getCurrentEditor().toPlainText()
        )

        # Zoom
        # The default zoom is the current zoom used by the editor
        self.original_zoom = pyzo.config.view.zoom
        self.zoom_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.zoom_slider.setMinimum(-10)  # Maybe too much ?
        self.zoom_slider.setMaximum(10)
        self.zoom_slider.setTickInterval(1)
        self.zoom_selected = self.original_zoom
        self.zoom_slider.setValue(self.zoom_selected)
        self.zoom_value_label = QtWidgets.QLabel()
        self._zoom_value_changed()
        self.zoom_slider.valueChanged.connect(self._zoom_value_changed)

        # Option for syntax highlighting
        self.checkbox_syntax_highlighting = QtWidgets.QCheckBox(
            "Enable syntax highlighting", self, checked=self._enable_syntax_highlighting
        )

        self.checkbox_syntax_highlighting.stateChanged.connect(
            self._change_syntax_highlighting_option
        )

        self.combobox_file_name = QtWidgets.QComboBox(self)
        self.combobox_file_name.addItem("Do not print the file name", 0)
        self.combobox_file_name.addItem("Print with file name", 1)
        self.combobox_file_name.addItem("Print with file name and absolute path", 2)
        self.combobox_file_name.setCurrentIndex(1)
        self.combobox_file_name.setToolTip("The title at the top of the document")

        # Orientation
        self.combobox_orientation = QtWidgets.QComboBox(self)
        self.combobox_orientation.addItem("Portrait", QtPrintSupport.QPrinter.Portrait)
        self.combobox_orientation.addItem(
            "Landscape", QtPrintSupport.QPrinter.Landscape
        )
        self.combobox_orientation.setToolTip("Orientation of the document")

        # Layout
        self.main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.main_layout)
        self.preview.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.right_layout = QtWidgets.QVBoxLayout()
        self.option_layout = QtWidgets.QFormLayout()
        self.main_layout.addWidget(self.preview)

        self.main_layout.addLayout(self.right_layout)
        self.right_layout.addLayout(self.option_layout)
        self.option_layout.addRow(self.combobox_file_name)
        self.option_layout.addRow(self.checkbox_line_number)
        self.option_layout.addRow(self.checkbox_syntax_highlighting)
        self.option_layout.addRow(self.zoom_value_label, self.zoom_slider)
        self.option_layout.addRow(self.combobox_orientation)
        self.bottom_layout = QtWidgets.QHBoxLayout()
        self.right_layout.addLayout(self.bottom_layout)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.button_update_preview)
        self.bottom_layout.addWidget(self.validation_button)

        self._update_preview()

    def _print(self):
        """Generate the pdf for preview and export"""

        if self.editor is not None:

            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.End, cursor.KeepAnchor)

            cursor.insertText(pyzo.editors.getCurrentEditor().toPlainText())
            self._set_zoom(self.zoom_selected)

            # Print with line numbers
            lines = self.editor.toPlainText().splitlines()
            nzeros = len(str(len(lines)))

            self._apply_syntax_highlighting()
            starting_line = 0

            self._change_orientation()

            # Print name or filename in the editor
            if self.combobox_file_name.currentIndex():
                starting_line = 1
                if self.combobox_file_name.currentIndex() == 1:
                    lines.insert(0, "# " + self.editor_name + "\n")
                elif self.combobox_file_name.currentIndex() == 2:
                    lines.insert(0, "# " + self.editor_filename + "\n")

            # Print line numbers in the editor
            if self.show_line_number:
                for i in range(starting_line, len(lines)):
                    lines[i] = (
                        str(i + 1 - starting_line).rjust(nzeros, "0") + "| " + lines[i]
                    )

            cursor = self.editor.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.End, cursor.KeepAnchor)
            cursor.insertText("\n".join(lines))

            # Highlight line numbers
            if self.show_line_number:
                cursor.movePosition(cursor.Start, cursor.MoveAnchor)
                # Move the cursor down 2 lines if a title is printed
                if starting_line != 0:
                    cursor.movePosition(cursor.NextBlock, cursor.MoveAnchor, 2)
                # Apply background for lines numbers
                for i in range(len(lines)):
                    fmt = QtGui.QTextCharFormat()
                    fmt.setBackground(QtGui.QColor(240, 240, 240))
                    cursor.movePosition(cursor.Right, cursor.KeepAnchor, nzeros)
                    cursor.setCharFormat(fmt)
                    cursor.movePosition(cursor.NextBlock, cursor.MoveAnchor)
                    cursor.movePosition(cursor.StartOfBlock, cursor.MoveAnchor)

    def _update_preview(self):
        """Update the widget preview"""

        self._print()
        self.preview.paintRequested.connect(self.editor.print_)
        self.preview.updatePreview()
        self._set_zoom(self.original_zoom)

    def _export_pdf(self):
        """Exports the code as pdf, and opens file manager"""
        if self.editor is not None:

            if True:
                filename = QtWidgets.QFileDialog.getSaveFileName(
                    None, "Export PDF", os.path.expanduser("~"), "*.pdf *.ps"
                )
                if isinstance(filename, tuple):  # PySide
                    filename = filename[0]
                if not filename:
                    return
                self.printer.setOutputFileName(filename)
            else:
                d = QtWidgets.QPrintDialog(self.printer)
                d.setWindowTitle("Print code")
                d.setOption(d.PrintSelection, self.editor.textCursor().hasSelection())
                d.setOption(d.PrintToFile, True)
                ok = d.exec_()
                if ok != d.Accepted:
                    return

        try:
            self._print()
            self.editor.print_(self.printer)

        except Exception as print_error:
            print(print_error)

    def _get_show_line_number(self, state):
        """Change the show_line_number according to the checkbox"""
        if state == QtCore.Qt.Checked:
            self.show_line_number = True
        else:
            self.show_line_number = False

    def _set_zoom(self, value):
        """Apply zoom setting only to the editor used to generate the pdf
        (and the preview)"""
        self.editor.setZoom(pyzo.config.view.zoom + value)

    def _zoom_value_changed(self):
        """Triggered when the zoom slider is changed"""
        self.zoom_selected = self.zoom_slider.value()
        zoom_level = self.zoom_selected - self.zoom_slider.minimum()
        self.zoom_value_label.setText("Zoom level : {}".format(zoom_level))

    def _change_syntax_highlighting_option(self, state):
        """Used for the syntax highlight checkbox when its state change
        to change the option value"""
        if state == QtCore.Qt.Checked:
            self._enable_syntax_highlighting = True
        else:
            self._enable_syntax_highlighting = False

    def _apply_syntax_highlighting(self):
        """Apply the syntax setting when _print() is used"""
        if self._enable_syntax_highlighting:
            text = pyzo.editors.getCurrentEditor().toPlainText()
            ext = os.path.splitext(pyzo.editors.getCurrentEditor()._filename)[1]
            parser = Manager.suggestParser(ext, text)
            self.editor.setParser(parser)
        else:
            self.editor.setParser(None)

    def _change_orientation(self):
        """Set document in portrait or landscape orientation"""
        self.printer.setOrientation(self.combobox_orientation.currentIndex())
