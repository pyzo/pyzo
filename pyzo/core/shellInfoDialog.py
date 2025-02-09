"""Module shellInfoDialog

Implements shell configuration dialog.

"""

import os
import sys
from pyzo.qt import QtCore, QtGui, QtWidgets  # noqa

import pyzo
from pyzo.core.pyzoLogging import print
from pyzo.core.kernelbroker import KernelInfo
from pyzo import translate


## Implement widgets that have a common interface


class ShellInfoLineEdit(QtWidgets.QLineEdit):
    def setTheText(self, value):
        self.setText(value)

    def getTheText(self):
        return self.text()


class ShellInfo_name(ShellInfoLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editingFinished.connect(self.onValueChanged)
        t = translate("shell", "name ::: The name of this configuration.")
        self.setPlaceholderText(t.tt)

    def setTheText(self, value):
        super().setTheText(value)
        self.onValueChanged()

    def onValueChanged(self):
        self.parent().parent().parent().setShellconfigTitle(self.getTheText())


class ShellInfo_exe(QtWidgets.QComboBox):
    def __init__(self, *args):
        super().__init__(*args)

    def _interpreterName(self, p):
        if p.is_conda:
            return "{}  [v{}, conda]".format(p.path, p.version)
        else:
            return "{}  [v{}]".format(p.path, p.version)

    def setTheText(self, value):
        # Init
        self.clear()
        self.setEditable(True)
        self.setInsertPolicy(self.InsertPolicy.InsertAtTop)

        # Get known interpreters from shellDialog (which are sorted by version)
        shellDialog = self
        while not isinstance(shellDialog, ShellInfoDialog):
            shellDialog = shellDialog.parent()
        interpreters = shellDialog.interpreters
        exes = [p.path for p in interpreters]

        # Hande current value
        if value in exes:
            value = self._interpreterName(interpreters[exes.index(value)])
        else:
            self.addItem(value)

        # Add all found interpreters
        for p in interpreters:
            self.addItem(self._interpreterName(p))

        # Set current text
        self.setEditText(value)

    def getTheText(self):
        # return self.currentText().split('(')[0].rstrip()
        value = self.currentText()
        if value.endswith("]") and "[" in value:
            value = value.rsplit("[", 1)[0]
        return value.strip()


class ShellInfo_ipython(QtWidgets.QCheckBox):
    def __init__(self, parent):
        super().__init__(parent)
        t = translate("shell", "ipython ::: Use IPython shell if available.")
        self.setText(t.tt)
        self.setChecked(False)

    def setTheText(self, value):
        self.setChecked(value.lower() not in ("", "no", "false"))

    def getTheText(self):
        return "yes" if self.isChecked() else "no"


class ShellInfo_gui(QtWidgets.QComboBox):
    # GUI names
    GUIS = [
        ("None", "no GUI support"),
        ("Auto", "Use what is available (recommended)"),
        ("Asyncio", "Python's builtin event loop"),
        ("PySide6", "LGPL licensed wrapper to Qt6"),
        ("PySide2", "LGPL licensed wrapper to Qt5"),
        ("PyQt6", "GPL/commercial licensed wrapper to Qt6"),
        ("PyQt5", "GPL/commercial licensed wrapper to Qt5"),
        ("Tornado", "Tornado asynchronous networking library"),
        ("Tk", "Tk widget toolkit"),
        ("WX", "wxPython"),
        ("FLTK", "The fast light toolkit"),
        ("GTK", "GIMP Toolkit"),
    ]

    # GUI descriptions

    def setTheText(self, value):
        # Process value
        value = value.upper()

        # Set options
        ii = 0
        self.clear()
        for i, (gui, des) in enumerate(self.GUIS):
            if value == gui.upper():
                ii = i
            self.addItem("{}  -  {}".format(gui, des))

        # Set current text
        self.setCurrentIndex(ii)

    def getTheText(self):
        text = self.currentText().lower()
        return text.partition("-")[0].strip()


class ShellinfoWithSystemDefault(QtWidgets.QVBoxLayout):
    DISABLE_SYSTEM_DEFAULT = sys.platform == "darwin"
    SYSTEM_VALUE = ""

    def __init__(self, parent, widget):
        # Do not pass parent, because is a sublayout
        super().__init__()

        # Layout
        self.setSpacing(1)
        self.addWidget(widget)

        # Create checkbox widget
        if not self.DISABLE_SYSTEM_DEFAULT:
            t = translate("shell", "Use system default")
            self._check = QtWidgets.QCheckBox(t, parent)
            self._check.stateChanged.connect(self.onCheckChanged)
            self.addWidget(self._check)

        # The actual value of this shell config attribute
        self._value = ""

        # A buffered version, so that clicking the text box does not
        # remove the value at once
        self._bufferedValue = ""

    def onEditChanged(self):
        if self.DISABLE_SYSTEM_DEFAULT or not self._check.isChecked():
            self._value = self.getWidgetText()

    def onCheckChanged(self, state):
        if state:
            self._bufferedValue = self._value
            self.setTheText(self.SYSTEM_VALUE)
        else:
            self.setTheText(self._bufferedValue)

    def setTheText(self, value):
        if self.DISABLE_SYSTEM_DEFAULT:
            # Just set the value
            self._edit.setReadOnly(False)
            self.setWidgetText(value)

        elif value != self.SYSTEM_VALUE:
            # Value given, enable edit
            self._check.setChecked(False)
            self._edit.setReadOnly(False)
            # Set the text
            self.setWidgetText(value)

        else:
            # Use system default, disable edit widget
            self._check.setChecked(True)
            self._edit.setReadOnly(True)
            # Set text using system environment
            self.setWidgetText(None)

        # Store value
        self._value = value

    def getTheText(self):
        return self._value


class ShellInfo_pythonPath(ShellinfoWithSystemDefault):
    SYSTEM_VALUE = "$PYTHONPATH"

    def __init__(self, parent):
        # Create sub-widget
        self._edit = QtWidgets.QPlainTextEdit(parent)
        self._edit.zoomOut(1)
        self._edit.setMaximumHeight(60)
        self._edit.setMinimumWidth(200)
        self._edit.textChanged.connect(self.onEditChanged)

        # Instantiate
        super().__init__(parent, self._edit)

    def getWidgetText(self):
        return self._edit.toPlainText()

    def setWidgetText(self, value=None):
        if value is None:
            pp = os.environ.get("PYTHONPATH", "")
            pp = pp.replace(os.pathsep, "\n").strip()
            value = "$PYTHONPATH:\n{}\n".format(pp)
        self._edit.setPlainText(value)


class ShellInfo_startupScript(QtWidgets.QVBoxLayout):
    DISABLE_SYSTEM_DEFAULT = sys.platform == "darwin"
    SYSTEM_VALUE = "$PYTHONSTARTUP"
    RUN_BEFORE_AFTER_GUI_TEXT = (
        "... Python code to run before integrating the GUI ...\n"
        "# AFTER_GUI\n"
        "... Python code to run after integrating the GUI ..."
    )

    def __init__(self, parent):
        # Do not pass parent, because is a sublayout
        super().__init__()

        # Create sub-widget
        self._edit1 = QtWidgets.QLineEdit(parent)
        self._edit1.textEdited.connect(self.onEditChanged)
        if sys.platform.startswith("win"):
            self._edit1.setPlaceholderText(r"C:\path\to\script.py")
        else:
            self._edit1.setPlaceholderText("/path/to/script.py")
        #
        self._edit2 = QtWidgets.QPlainTextEdit(parent)
        self._edit2.zoomOut(1)
        self._edit2.setMinimumWidth(200)
        self._edit2.textChanged.connect(self.onEditChanged)
        self._edit2.setPlaceholderText(self.RUN_BEFORE_AFTER_GUI_TEXT)

        # Layout
        self.setSpacing(1)
        self.addWidget(self._edit1)
        self.addWidget(self._edit2)

        # Create radio widget for system default
        t = translate("shell", "Use system default")
        self._radio_system = QtWidgets.QRadioButton(t, parent)
        self._radio_system.toggled.connect(self.onCheckChanged)
        self.addWidget(self._radio_system)
        if self.DISABLE_SYSTEM_DEFAULT:
            self._radio_system.hide()

        # Create radio widget for file
        t = translate("shell", "File to run at startup")
        self._radio_file = QtWidgets.QRadioButton(t, parent)
        self._radio_file.toggled.connect(self.onCheckChanged)
        self.addWidget(self._radio_file)

        # Create radio widget for code
        t = translate("shell", "Code to run at startup")
        self._radio_code = QtWidgets.QRadioButton(t, parent)
        self._radio_code.toggled.connect(self.onCheckChanged)
        self.addWidget(self._radio_code)

        # The actual value of this shell config attribute
        self._value = ""

        # A buffered version, so that clicking the text box does not
        # remove the value at once
        self._valueFile = ""
        self._valueCode = "\n"

    def onEditChanged(self):
        if self._radio_file.isChecked():
            self._value = self._valueFile = self._edit1.text().strip()
        elif self._radio_code.isChecked():
            # ensure newline!
            self._value = self._valueCode = self._edit2.toPlainText().strip() + "\n"

    def onCheckChanged(self, state):
        if self._radio_system.isChecked():
            self.setWidgetText(self.SYSTEM_VALUE)
        elif self._radio_file.isChecked():
            self.setWidgetText(self._valueFile)
        elif self._radio_code.isChecked():
            self.setWidgetText(self._valueCode)

    def setTheText(self, value):
        self.setWidgetText(value, True)
        self._value = value

    def setWidgetText(self, value, init=False):
        self._value = value

        if value == self.SYSTEM_VALUE and not self.DISABLE_SYSTEM_DEFAULT:
            # System default
            if init:
                self._radio_system.setChecked(True)
            pp = os.environ.get("PYTHONSTARTUP", "").strip()
            if pp:
                value = '$PYTHONSTARTUP: "{}"'.format(pp)
            else:
                value = "$PYTHONSTARTUP: None"
            #
            self._edit1.setReadOnly(True)
            self._edit1.show()
            self._edit2.hide()
            self._edit1.setText(value)

        elif "\n" not in value:
            # File
            if init:
                self._radio_file.setChecked(True)
            self._edit1.setReadOnly(False)
            self._edit1.show()
            self._edit2.hide()
            self._edit1.setText(value)

        else:
            # Code
            if init:
                self._radio_code.setChecked(True)
            self._edit1.hide()
            self._edit2.show()
            if not value.strip():
                value = ""  # this will display the placeholder text
            self._edit2.setPlainText(value)

    def getTheText(self):
        return self._value


class ShellInfo_startDir(ShellInfoLineEdit):
    def __init__(self, parent):
        super().__init__(parent)
        if sys.platform.startswith("win"):
            self.setPlaceholderText(r"C:\path\to\your\python\modules")
        else:
            self.setPlaceholderText("/path/to/your/python/modules")


class ShellInfo_argv(ShellInfoLineEdit):
    def __init__(self, parent):
        super().__init__(parent)
        self.setPlaceholderText('arg1 arg2 "arg with spaces"')


class ShellInfo_environ(QtWidgets.QPlainTextEdit):
    EXAMPLE = "PYZO_PROCESS_EVENTS_WHILE_DEBUGGING=1\nEXAMPLE_VAR1=value1"

    def __init__(self, parent):
        super().__init__(parent)
        self.zoomOut(1)
        self.setPlaceholderText(self.EXAMPLE)

    def _cleanText(self, txt):
        return "\n".join([line.strip() for line in txt.splitlines()])

    def setTheText(self, value):
        value = self._cleanText(value)
        self.setPlainText(value)

    def getTheText(self):
        value = self.toPlainText()
        value = self._cleanText(value)
        return value


## The dialog class and container with pages


class ShellInfoPage(QtWidgets.QScrollArea):
    INFO_KEYS = [
        translate("shell", "name ::: The name of this configuration."),
        translate("shell", "exe ::: The Python executable."),
        translate("shell", "ipython ::: Use IPython shell if available."),
        translate(
            "shell",
            "gui ::: The GUI toolkit to integrate (for interactive plotting, etc.).",
        ),
        translate(
            "shell",
            "pythonPath ::: A list of directories to search for modules and packages. Write each path on a new line, or separate with the default seperator for this OS.",
        ),
        translate(
            "shell",
            "startupScript ::: The script to run at startup (not in script mode).",
        ),
        translate("shell", "startDir ::: The start directory (not in script mode)."),
        translate("shell", "argv ::: The command line arguments (sys.argv)."),
        translate("shell", "environ ::: Extra environment variables (os.environ)."),
    ]

    def __init__(self, parent):
        super().__init__(parent)

        # Init the scroll area
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        # Create widget and a layout
        self._content = QtWidgets.QWidget(parent)
        self._formLayout = QtWidgets.QFormLayout(self._content)

        # Collect classes of widgets to instantiate
        classes = []
        for t in self.INFO_KEYS:
            className = "ShellInfo_" + t.key
            cls = globals()[className]
            classes.append((t, cls))

        # Instantiate all classes
        self._shellInfoWidgets = {}
        for t, cls in classes:
            # Instantiate and store
            instance = cls(self._content)
            self._shellInfoWidgets[t.key] = instance
            # Create label
            label = QtWidgets.QLabel(t, self._content)
            label.setToolTip(t.tt)
            # Add to layout
            self._formLayout.addRow(label, instance)

        # Apply layout
        self._formLayout.setSpacing(15)
        self._content.setLayout(self._formLayout)
        self.setWidget(self._content)

        # Create a list item for switching pages via a QListWidget
        self._listItem = QtWidgets.QListWidgetItem()

    @property
    def listItem(self):
        return self._listItem

    def setShellconfigTitle(self, name):
        self._listItem.setText(name)

    def setInfo(self, info=None):
        """Set the shell info struct, and use it to update the widgets.
        Not via init, because this function also sets the page name.
        """

        # If info not given, use default as specified by the KernelInfo struct
        if info is None:
            info = KernelInfo()
            # Name
            n = self.parent().count()
            if n > 1:
                info.name = "Shell config {}".format(n)

        # Store info
        self._info = info

        # Set widget values according to info
        try:
            for key in info:
                widget = self._shellInfoWidgets.get(key, None)
                if widget is not None:
                    widget.setTheText(info[key])

        except Exception as why:
            print("Error setting info in shell config:", why)
            print(info)

    def getInfo(self):
        info = self._info

        # Set struct values according to widgets
        try:
            for key, widget in self._shellInfoWidgets.items():
                info[key] = widget.getTheText()

        except Exception as why:
            print("Error getting info in shell config:", why)
            print(info)

        # Return the original (but modified) ssdf Dict object
        return info


class MyQListWidgetDragDropCopy(QtWidgets.QListWidget):
    """
    This derived class is only necessary to make drag'n'drop
    copying of list entries with signalling of original and new
    items possible.
    """

    dragDropRowCopied = QtCore.Signal(int, int)

    def __init__(self, *args):
        super().__init__(*args)

        # Setup drag'n'drop for the list
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setDragDropMode(self.DragDropMode.DragDrop)
        self._indexDragStart = None
        self._itemsAtDragStart = None

    def dragEnterEvent(self, event):
        if event.source() is self:
            self._indexDragStart = self.row(self.currentItem())
            self._itemsAtDragStart = [self.item(i) for i in range(self.count())]
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.source() is self:
            super().dropEvent(event)
        else:
            event.ignore()
        self._indexDragStart = None
        self._itemsAtDragStart = None

    def rowsInserted(self, parentIndex, start, end):
        """find out which item was copied and where the new item was inserted"""
        super().rowsInserted(parentIndex, start, end)
        indsOfNewItems = [
            i for i in range(self.count()) if self.item(i) not in self._itemsAtDragStart
        ]
        if len(indsOfNewItems) == 1:
            (indNewRow,) = indsOfNewItems
            indOriginalRow = self._indexDragStart
            if indNewRow <= indOriginalRow:
                indOriginalRow += 1
            self.dragDropRowCopied.emit(indOriginalRow, indNewRow)


class ShellInfoDialog(QtWidgets.QDialog):
    """Dialog to edit the shell configurations."""

    def __init__(self, *args):
        super().__init__(*args)
        self.setModal(True)

        # Set title
        self.setWindowTitle(pyzo.translate("shell", "Shell configurations"))

        # Create a page-stack for all configs and a list for switching pages
        self._stack = QtWidgets.QStackedWidget()
        self._list = MyQListWidgetDragDropCopy()
        self._list.currentItemChanged.connect(self._onListItemChanged)
        self._list.dragDropRowCopied.connect(self._onDragDropRowCopied)

        # Get known interpreters (sorted them by version)
        # Do this here so we only need to do it once ...
        from pyzo.util.interpreters import get_interpreters

        self.interpreters = list(reversed(get_interpreters("2.7")))

        cfgSelLayout = QtWidgets.QVBoxLayout()
        cfgSelLayout.addWidget(self._list)

        # Add add-config button
        t = translate("shell", "Add config ::: Add a new shell configuration")
        btn = QtWidgets.QPushButton(pyzo.icons.add, t)
        btn.setToolTip(t.tt)
        btn.clicked.connect(self._onBtnAddConfigPressed)
        cfgSelLayout.addWidget(btn)

        # Add duplicate button
        t = translate("shell", "Duplicate ::: Duplicate this shell configuration")
        btn = QtWidgets.QPushButton(pyzo.icons.page_white_copy, t)
        btn.setToolTip(t.tt)
        btn.clicked.connect(self._onBtnCopyConfigPressed)
        cfgSelLayout.addWidget(btn)

        # Add delete button
        t = translate("shell", "Delete ::: Delete this shell configuration")
        btn = QtWidgets.QPushButton(pyzo.icons.cancel, t)
        btn.setToolTip(t.tt)
        btn.clicked.connect(self._deleteConfig)
        cfgSelLayout.addWidget(btn)

        # Create dialog buttons
        cancelBut = QtWidgets.QPushButton("Cancel", self)
        okBut = QtWidgets.QPushButton("Done", self)
        cancelBut.clicked.connect(self.close)
        okBut.clicked.connect(self._applyAndClose)
        # Layout for dialog buttons
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(cancelBut)
        buttonLayout.addSpacing(10)
        buttonLayout.addWidget(okBut)

        # Layout the widgets
        configLayout = QtWidgets.QHBoxLayout()
        configLayout.addLayout(cfgSelLayout, 1)
        configLayout.addWidget(self._stack, 4)

        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addSpacing(8)
        mainLayout.addLayout(configLayout)
        mainLayout.addLayout(buttonLayout, 0)
        self.setLayout(mainLayout)

        self.setMinimumSize(800, 600)
        self.resize(1024, 768)

        # Add an entry if there's none
        if not pyzo.config.shellConfigs2:
            self._addConfig()

        # Fill config pages
        for item in pyzo.config.shellConfigs2:
            self._addConfig(item)

        self._list.setCurrentRow(0)

        self.show()

    def _addConfig(self, shellConfig=None, atIndex=-1, select=False):
        if atIndex == -1:
            atIndex = self._list.count()
        w = ShellInfoPage(self._stack)
        self._stack.addWidget(w)

        # QSignalBlocker has a context manager, but not in old PySide2
        try:
            blocker = QtCore.QSignalBlocker(self._list.model())
            self._list.insertItem(atIndex, w.listItem)
        finally:
            blocker.unblock()
        w.setInfo(shellConfig)
        if select:
            self._list.setCurrentItem(w.listItem)
            w.setFocus()

    def _getPageWidget(self, listItem):
        for i in range(self._stack.count()):
            w = self._stack.widget(i)
            if w.listItem is listItem:
                return w
        else:
            raise ValueError("item not found: " + repr(listItem))

    def _onListItemChanged(self, curItem, prevItem):
        if curItem is None:
            # last remaining item was deleted
            return
        w = self._getPageWidget(curItem)
        self._stack.setCurrentWidget(w)

    def _onBtnAddConfigPressed(self):
        self._addConfig(select=True)

    def _deleteConfig(self):
        w = self._stack.currentWidget()
        self._stack.removeWidget(w)
        self._list.takeItem(self._list.row(w.listItem))

        # make sure that there is at least one config
        if self._stack.count() == 0:
            self._addConfig(select=True)

    def _onBtnCopyConfigPressed(self):
        self._copyConfig()

    def _copyConfig(self, w0=None, index=None):
        if w0 is None:
            # Get original widget
            w0 = self._stack.currentWidget()
        # Build new info
        info = w0.getInfo().copy()
        info.name += " (2)"
        if index is None:
            index = self._list.row(w0.listItem) + 1
        self._addConfig(info, index, select=True)

    def _onDragDropRowCopied(self, indOriginalRow, indNewRow, later=False):
        if not later:
            # This is called when we are still in the "rowsInserted" event.
            # We need to let the insertion process finish before we modify anything.
            # Otherwise our change to the list entry text would be overwritten.
            pyzo.callLater(self._onDragDropRowCopied, indOriginalRow, indNewRow, True)
            return

        w0 = self._getPageWidget(self._list.item(indOriginalRow))

        # remove the item that was added via drag'n'drop copy and do our own copy
        self._list.takeItem(indNewRow)
        self._copyConfig(w0, indNewRow)

    def _applyAndClose(self, event=None):
        self._apply()
        self.close()

    def _apply(self):
        """Apply changes for all configs."""

        # Clear
        pyzo.config.shellConfigs2 = []

        # Set new versions. Note that although we recreate the list,
        # the list is filled with the orignal structs, so having a
        # reference to such a struct (as the shell has) will enable
        # you to keep track of any made changes.
        for i in range(self._list.count()):
            w = self._getPageWidget(self._list.item(i))
            pyzo.config.shellConfigs2.append(w.getInfo())
