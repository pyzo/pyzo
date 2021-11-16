import os

from pyzo.util.qt import QtCore, QtGui, QtWidgets

import pyzo
from pyzo.util import zon as ssdf
from pyzo.core.pyzoLogging import print  # noqa
import pyzo.core.baseTextCtrl
from pyzo.codeeditor.style import StyleFormat


SAMPLE = """
## Foo class
# This is a comment
class Foo:
''' This class does nothing. '''
    #TODO: be amazing
        def baz(self, arg1):
            return max(arg1, 42)
    bar = "Hello wor
""" + chr(
    160
)


class FakeEditor(pyzo.core.baseTextCtrl.BaseTextCtrl):
    """This "fake" editor emits a signal when
    the user clicks on a word with a token:
    a click on the word "class" emits with arg "syntax.keyword".

    It may be improved by adding text with specific token
    like Editor.text which are not present by default
    """

    tokenClicked = QtCore.Signal(str)

    def __init__(self, text=""):
        super().__init__()

        # set parser to enable syntaxic coloration
        self.setParser("python3")
        self.setReadOnly(False)
        self.setLongLineIndicatorPosition(30)
        self.setPlainText(SAMPLE)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        # get the text position of the click
        pos = self.textCursor().columnNumber()
        tokens = self.textCursor().block().userData().tokens

        # Find the token which contains the click pos
        for tok in tokens:
            if tok.start <= pos <= tok.end:
                self.tokenClicked.emit(tok.description.key)
                break


class TitledWidget(QtWidgets.QWidget):
    """A litle helper class to "name" a widget :
    it displays a QLabel to left of the given widget"""

    def __init__(self, name, other):
        super().__init__()
        self.widget = other
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel(text=name.capitalize().strip() + " :"))
        layout.addWidget(other)

        self.setLayout(layout)

    def setFocus(self, val):
        self.widget.setFocus(val)


class ColorLineEdit(QtWidgets.QLineEdit):
    """A subclass of the QLineEdit that can open
    a QColorDialog on click of a button
    """

    def __init__(self, name, *args, **kwargs):
        """The name is displayed in the QColorDialog"""
        super().__init__(*args, **kwargs)
        self.name = name
        self.button = QtWidgets.QToolButton(self)
        self.button.setIcon(QtGui.QIcon(pyzo.icons.cog))
        self.button.setStyleSheet("border: 0px; padding: 0px")
        self.button.clicked.connect(self.openColorDialog)

        frameWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        buttonSize = self.button.sizeHint()

        self.setStyleSheet(
            "QLineEdit {padding-right: %dpx; }" % (buttonSize.width() + frameWidth + 1)
        )
        # self.setMinimumSize(max(100, buttonSize.width() + frameWidth*2 + 2),
        #                     max(self.minimumSizeHint().height(), buttonSize.height() + frameWidth*2 + 2))

    def openColorDialog(self):
        """A simple function that opens a QColorDialog
        and link the dialog current color selection
        to the QLineEdit text
        """
        dlg = QtWidgets.QColorDialog(self)
        dlg.setWindowTitle("Pick a color for the " + self.name.lower())
        dlg.setCurrentColor(QtGui.QColor(self.text()))
        dlg.currentColorChanged.connect(lambda clr: self.setText(clr.name()))
        dlg.setModal(False)
        dlg.exec_()

    def resizeEvent(self, event):
        buttonSize = self.button.sizeHint()
        frameWidth = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        self.button.move(
            int(self.rect().right() - frameWidth - buttonSize.width()),
            int(self.rect().bottom() - buttonSize.height() + 1) // 2,
        )
        super().resizeEvent(event)


class StyleEdit(QtWidgets.QWidget):
    """The StyleLineEdit is a line that allows the edition
    of one style (i.e. "Editor.Text" or  "Syntax.identifier")
    with a given StyleElementDescription it find the editable
    parts and display the adaptated widgets for edition
    (checkbok for bold and italic, combo box for linestyles...).
    """

    styleChanged = QtCore.Signal(str, str)

    def __init__(self, defaultStyle, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The styleKey is sent with the styleChanged signal for easy identification
        self.styleKey = defaultStyle.key

        self.layout = layout = QtWidgets.QHBoxLayout()
        # The setters are used when setting the style
        self.setters = {}

        # TODO: the use of StyleFormat._parts should be avoided
        # We use the StyleFormat._parts keys, to find the elements
        # Useful to edits, because the property may return a value
        # Even if they were not defined in the defaultFormat
        fmtParts = defaultStyle.defaultFormat._parts

        # Add the widgets corresponding to the fields
        if "fore" in fmtParts:
            self.__add_clrLineEdit("fore", "Foreground")
        if "back" in fmtParts:
            self.__add_clrLineEdit("back", "Background")
        if "bold" in fmtParts:
            self.__add_checkBox("bold", "Bold")
        if "italic" in fmtParts:
            self.__add_checkBox("italic", "Italic")
        if "underline" in fmtParts:
            self.__add_comboBox(
                "underline", "Underline", "No", "Dotted", "Wave", "Full", "Yes"
            )
        if "linestyle" in fmtParts:
            self.__add_comboBox("linestyle", "Linestyle", "Dashed", "Dotted", "Full")

        self.setLayout(layout)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

    def __add_clrLineEdit(self, key, name):
        """this is a helper method to create a ColorLineEdit
        it adds the created widget (as a TitledWidget) to the layout and
        register a setter and listen to changes
        """
        clrEdit = ColorLineEdit(name)
        clrEdit.textChanged.connect(lambda txt, key=key: self.__update(key, txt))
        self.setters[key] = clrEdit.setText
        self.layout.addWidget(TitledWidget(name, clrEdit), 0)

    def __add_checkBox(self, key, name):
        """this is a helper method to create a QCheckBox
        it adds the created widget (as a TitledWidget) to the layout and
        register a setter and listen to changes
        """

        checkBox = QtWidgets.QCheckBox()

        self.setters[key] = lambda val, check=checkBox: check.setCheckState(
            val == "yes"
        )

        checkBox.stateChanged.connect(
            lambda state, key=key: self.__update(key, "yes" if state else "no")
        )

        self.layout.addWidget(TitledWidget(name, checkBox))

    def __add_comboBox(self, key, name, *items):

        """this is a helper method to create a comboBox
        it adds the created widget (as a TitledWidget) to the layout and
        register a setter and listen to changes
        """

        combo = QtWidgets.QComboBox()
        combo.addItems(items)
        combo.currentTextChanged.connect(lambda txt, key=key: self.__update(key, txt))

        # Note: those setters may become problematic if
        # someone use the synonyms (defined in codeeditor/style.py)
        # i.e. a stylement is of form "linestyle:dashline"
        # instead of the "linestyle:dashed"
        self.setters[key] = lambda txt, cmb=combo: cmb.setCurrentText(txt.capitalize())
        self.layout.addWidget(TitledWidget(name, combo))

    def __update(self, key, value):
        """this function is called everytime one of the children
        widget data has been modified by the user"""
        self.styleChanged.emit(self.styleKey, key + ":" + value)

    def setStyle(self, text):
        """updates every children to match the StyleFormat(text) fields"""
        style = StyleFormat(text)
        for key, setter in self.setters.items():
            setter(style[key])

    def setFocus(self, val):
        self.layout.itemAt(0).widget().setFocus(True)


class ThemeEditorWidget(QtWidgets.QWidget):
    """The ThemeEditorWidgets allows to edits themes,
    it has one StyleEdit widget per StyleElements ("Editor.Text",
    "Syntax.string"). It emits a signal on each style changes

    It also manages basic theme I/O :
        - adding new theme
        - renaming theme

    """

    styleChanged = QtCore.Signal(dict)
    done = QtCore.Signal(int)

    def __init__(self, themes, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)

        # dict of themes, a deep copy of pyzo.themes
        self.themes = themes
        # We store the key name separate so we can easier track renames
        self.cur_theme_key = ""
        # The current theme being changed
        self.cur_theme = None

        # If an editor is given, connect to it
        self.editor = editor
        if self.editor is not None:
            self.editor.tokenClicked.connect(self.focusOnStyle)
            self.styleChanged.connect(self.editor.setStyle)

        # Display editables style formats in a scroll area
        self.scrollArea = scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)

        formLayout = QtWidgets.QFormLayout()
        self.styleEdits = {}

        # Add one pair of label and StyleEdit per style element description
        # to the formLayout and connect the StyleEdit signals to the updatedStyle method
        for styleDesc in pyzo.codeeditor.CodeEditor.getStyleElementDescriptions():
            label = QtWidgets.QLabel(text=styleDesc.name, toolTip=styleDesc.description)
            label.setWordWrap(True)
            styleEdit = StyleEdit(styleDesc, toolTip=styleDesc.description)
            styleEdit.styleChanged.connect(self.updatedStyle)
            self.styleEdits[styleDesc.key] = styleEdit
            formLayout.addRow(label, styleEdit)

        wrapper = QtWidgets.QWidget()
        wrapper.setLayout(formLayout)
        wrapper.setMinimumWidth(650)
        scrollArea.setWidget(wrapper)

        # Basic theme I/O

        curThemeLbl = QtWidgets.QLabel(text="Themes :")

        self.curThemeCmb = curThemeCmb = QtWidgets.QComboBox()
        current_index = -1
        for i, themeName in enumerate(self.themes.keys()):
            # We store the themeName in data in case the user renames one
            curThemeCmb.addItem(themeName, userData=themeName)
            if themeName == pyzo.config.settings.theme.lower():
                current_index = i
        curThemeCmb.addItem("New...")

        loadLayout = QtWidgets.QHBoxLayout()
        loadLayout.addWidget(curThemeLbl)
        loadLayout.addWidget(curThemeCmb)

        self.saveBtn = saveBtn = QtWidgets.QPushButton(text="Save")
        saveBtn.clicked.connect(self.saveTheme)
        exitBtn = QtWidgets.QPushButton(text="Apply theme")
        exitBtn.clicked.connect(self.ok)

        exitLayout = QtWidgets.QHBoxLayout()
        exitLayout.addWidget(exitBtn)
        exitLayout.addWidget(saveBtn)

        # Packing it up
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addLayout(loadLayout)
        mainLayout.addWidget(scrollArea)
        mainLayout.addLayout(exitLayout)
        self.setLayout(mainLayout)

        curThemeCmb.currentIndexChanged.connect(self.indexChanged)
        curThemeCmb.currentTextChanged.connect(self.setTheme)

        # Init
        if current_index >= 0:
            curThemeCmb.setCurrentIndex(current_index)
            self.setTheme(pyzo.config.settings.theme)

    def createTheme(self):
        """Create a new theme based on the current
        theme selected.
        """

        index = self.curThemeCmb.currentIndex()
        if index != self.curThemeCmb.count() - 1:
            return self.curThemeCmb.setCurrentIndex(self.curThemeCmb.count() - 1)

        # Select a new name
        t = "new_theme_x"
        i = 1
        themeName = t.replace("x", str(i))
        while themeName in self.themes:
            i += 1
            themeName = t.replace("x", str(i))

        # Create new theme
        new_theme = {"name": themeName, "data": {}, "builtin": False}
        if self.cur_theme:
            new_theme["data"] = self.cur_theme["data"].copy()
        self.cur_theme_key = themeName
        self.cur_theme = new_theme
        self.themes[themeName] = new_theme

        self.curThemeCmb.setItemText(index, themeName)
        self.curThemeCmb.setItemData(index, themeName)

        self.curThemeCmb.setEditable(True)
        self.curThemeCmb.lineEdit().setCursorPosition(0)
        self.curThemeCmb.lineEdit().selectAll()

        self.saveBtn.setEnabled(True)

        self.curThemeCmb.addItem(
            "New...",
        )

    def setTheme(self, name):
        """Set the theme by its name. The combobox becomes editable only
        if the theme is not builtin. This method is connected to the signal
        self.curThemeCmb.currentTextChanged ; so it also filters
        parasites events"""

        name = name.lower()

        if name != self.curThemeCmb.currentText():
            # An item was added to the comboBox
            # But it's not a user action so we quit
            print(" -> Cancelled because this was not a user action")
            return

        if self.cur_theme_key == self.curThemeCmb.currentData():
            # The user renamed an existing theme
            self.cur_theme["name"] = name
            return

        if name not in self.themes:
            return

        # Sets the curent theme key
        self.cur_theme_key = name
        self.cur_theme = self.themes[name]

        if self.cur_theme["builtin"]:
            self.saveBtn.setEnabled(False)
            self.saveBtn.setText("Cannot save builtin style")
        else:
            self.saveBtn.setEnabled(True)
            self.saveBtn.setText("Save")
        self.curThemeCmb.setEditable(not self.cur_theme["builtin"])

        for key, le in self.styleEdits.items():
            if key in self.cur_theme["data"]:
                try:
                    le.setStyle(self.cur_theme["data"][key])
                except Exception as e:
                    print(
                        "Exception while setting style", key, "for theme", name, ":", e
                    )

    def saveTheme(self):
        """Saves the current theme to the disk, in appDataDir/themes"""

        if self.cur_theme["builtin"]:
            return
        themeName = self.curThemeCmb.currentText().strip()
        if not themeName:
            return

        # Get user theme dir and make sure it exists
        dir = os.path.join(pyzo.appDataDir, "themes")
        os.makedirs(dir, exist_ok=True)

        # Try to delete the old file if it exists (useful if it was renamed)
        try:
            os.remove(os.path.join(dir, self.cur_theme_key + ".theme"))
        except Exception:
            pass

        # This is the needed because of the SSDF format:
        # it doesn't accept dots, so we put underscore instead
        data = {x.replace(".", "_"): y for x, y in self.cur_theme["data"].items()}

        fname = os.path.join(dir, themeName + ".theme")
        ssdf.save(fname, {"name": themeName, "data": data})
        print("Saved theme '%s' to '%s'" % (themeName, fname))

    def ok(self):
        """On user click saves the cur_theme if modified
        and restart pyzo if the theme changed"""
        prev = pyzo.config.settings.theme
        new = self.cur_theme["name"]

        self.saveTheme()

        if prev != new:
            pyzo.config.settings.theme = new
            # This may be better
            pyzo.main.restart()
        else:
            self.done.emit(1)

    def indexChanged(self, index):
        # User selected the "new..." button
        if index == self.curThemeCmb.count() - 1:
            self.createTheme()

    def focusOnStyle(self, key):
        self.styleEdits[key].setFocus(True)
        self.scrollArea.ensureWidgetVisible(self.styleEdits[key])

    def updatedStyle(self, style, text):
        fmt = StyleFormat(self.cur_theme["data"][style])
        fmt.update(text)
        self.cur_theme["data"][style] = str(fmt)
        self.styleChanged.emit({style: text})


class EditColorDialog(QtWidgets.QDialog):
    """This dialog allows to edit color schemes,
    it is composed of two main components :
        - a "fake" editor to visualize the changes
        - a theme editor to make the edits
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Color scheme")
        size = 1200, 800
        offset = 0
        size2 = size[0], size[1] + offset
        self.resize(*size2)

        # Make a deep copy
        themes = {}
        for name, theme in pyzo.themes.items():
            theme = theme.copy()
            theme["data"] = theme["data"].copy()
            themes[name] = theme

        self.editor = FakeEditor()
        self.editColor = ThemeEditorWidget(themes=themes, editor=self.editor)
        self.editColor.done.connect(self.done)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.editColor, 2)
        self.setLayout(layout)
