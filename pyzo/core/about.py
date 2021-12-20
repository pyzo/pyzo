import os
import sys

from pyzo.qt import QtCore, QtGui, QtWidgets
from pyzo import qt

import pyzo
from pyzo.util import paths


class AboutDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle(pyzo.translate("menu dialog", "About Pyzo"))
        self.resize(600, 500)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # Create image and title
        im = QtGui.QPixmap(
            os.path.join(pyzo.pyzoDir, "resources", "appicons", "pyzologo64.png")
        )
        imlabel = QtWidgets.QLabel(self)
        imlabel.setPixmap(im)
        textlabel = QtWidgets.QLabel(self)
        textlabel.setText("<h3>Pyzo: the Interactive Editor for Python</h3>")
        #
        titleLayout = QtWidgets.QHBoxLayout()
        titleLayout.addWidget(imlabel, 0)
        titleLayout.addWidget(textlabel, 1)
        #
        layout.addLayout(titleLayout, 0)

        # Create tab bar
        self._tabs = QtWidgets.QTabWidget(self)
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs, 1)

        # Create button box
        self._butBox = QtWidgets.QDialogButtonBox(self)
        self._butBox.setOrientation(QtCore.Qt.Horizontal)
        self._butBox.setStandardButtons(self._butBox.Close)
        layout.addWidget(self._butBox, 0)

        # Signals
        self._butBox.rejected.connect(self.close)

        # Create tabs
        self.createGeneralTab()

    def addTab(self, title, text, rich=True):
        # Create label to show info
        label = QtWidgets.QTextEdit(self)
        label.setLineWrapMode(label.WidgetWidth)
        label.setReadOnly(True)
        # Set text
        if rich:
            label.setHtml(text)
        else:
            label.setText(text)
        # Add to tab bar
        self._tabs.addTab(label, title)
        # Done
        return label

    def createGeneralTab(self):
        aboutText = """
        {}<br><br>

        <b>Version info</b><br>
        Pyzo version: <u>{}</u><br>
        Platform: {}<br>
        Python version: {}<br>
        Qt version: {}<br>
        {} version: {}<br>
        <br>

        <b>Pyzo directories</b><br>
        Pyzo source directory: {}<br>
        Pyzo config directory: {}<br>
        Pyzo userdata directory: {}<br>
        <br>

        <b>License</b><br>
        Pyzo is open source, it's code is distributed under the 2-Clause BSD license.
        <br><br>

        <b>Contributors</b><br>
        Pyzo is coded with ♥ by Almar Klein and over 30 contributors:<br>
        https://github.com/pyzo/pyzo/graphs/contributors
        <br><br>

        <b>Acknowledgements</b><br>
        Pyzo is written in Python 3 and uses the Qt widget
        toolkit. Pyzo uses code and concepts that are inspired by
        IPython, Pype, and Spyder.
        Pyzo uses a (modified) subset of the silk icon set,
        by Mark James (http://www.famfamfam.com/lab/icons/silk/).
        """
        # Determine if this is PyQt or Pyside
        qtWrapper = qt.API_NAME
        qtVersion = qt.QT_VERSION
        qtWrapperVersion = qt.PYSIDE_VERSION or qt.PYQT_VERSION
        # Insert information texts
        if paths.is_frozen():
            versionText = pyzo.__version__ + " (binary)"
        else:
            versionText = pyzo.__version__ + " (source)"
        aboutText = aboutText.format(
            "Pyzo - Python to the people!",
            versionText,
            sys.platform,
            sys.version.split(" ")[0],
            qtVersion,
            qtWrapper,
            qtWrapperVersion,
            pyzo.pyzoDir,
            pyzo.appConfigDir,
            pyzo.appDataDir,
        )

        self.addTab("General", aboutText)


if __name__ == "__main__":
    # pyzo.license = {'name': 'AK', 'company': ''}
    m = AboutDialog(None)
    m.show()
