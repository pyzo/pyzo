import weakref

import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets
from pyzo import translate

tool_name = translate("pyzoSourceStructure", "Source structure")
tool_summary = "Shows the structure of your source code."


class Navigation:
    def __init__(self):
        self.back = []
        self.forward = []


class PyzoSourceStructure(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        # Make sure there is a configuration entry for this tool
        # The pyzo tool manager makes sure that there is an entry in
        # config.tools before the tool is instantiated.
        toolId = self.__class__.__name__.lower()
        self._config = pyzo.config.tools[toolId]
        if not hasattr(self._config, "showTypes"):
            self._config.showTypes = ["class", "def", "cell", "todo"]
        if not hasattr(self._config, "level"):
            self._config.level = 2

        # Keep track of clicks so we can "go back"
        self._nav = {}  # editor-reference -> Navigation object

        # Init color theme
        self._colors = {}
        self._color_theme = ""

        # Init parsed code lists for line look-up
        self._lineItemList = []
        self._pathList = []

        # Init reference to previous tree item for restoring the background color
        self._prevSelectedItem = None

        # Create buttons for navigation
        self._navbut_back = QtWidgets.QToolButton(self)
        self._navbut_back.setIcon(pyzo.icons.arrow_left)
        self._navbut_back.setIconSize(QtCore.QSize(16, 16))
        self._navbut_back.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        self._navbut_back.clicked.connect(self.onNavBack)
        #
        self._navbut_forward = QtWidgets.QToolButton(self)
        self._navbut_forward.setIcon(pyzo.icons.arrow_right)
        self._navbut_forward.setIconSize(QtCore.QSize(16, 16))
        self._navbut_forward.setStyleSheet(
            "QToolButton { border: none; padding: 0px; }"
        )
        self._navbut_forward.clicked.connect(self.onNavForward)

        # # Create icon for slider
        # self._sliderIcon = QtWidgets.QToolButton(self)
        # self._sliderIcon.setIcon(pyzo.icons.text_align_right)
        # self._sliderIcon.setIconSize(QtCore.QSize(16, 16))
        # self._sliderIcon.setStyleSheet("QToolButton { border: none; padding: 0px; }")

        # Create slider
        self._slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self._slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setRange(1, 5)
        self._slider.setValue(self._config.level)
        self._slider.valueChanged.connect(self.updateStructure)

        # Create options button
        # self._options = QtWidgets.QPushButton(self)
        # self._options.setText("Options"))
        # self._options.setToolTip("What elements to show.")
        self._options = QtWidgets.QToolButton(self)
        self._options.setIcon(pyzo.icons.filter)
        self._options.setIconSize(QtCore.QSize(16, 16))
        self._options.setPopupMode(self._options.ToolButtonPopupMode.InstantPopup)
        self._options.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )

        # Create options menu
        self._options._menu = QtWidgets.QMenu()
        self._options.setMenu(self._options._menu)

        # Create tree widget
        self._tree = QtWidgets.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.itemCollapsed.connect(self.updateStructure)  # keep expanded
        self._tree.itemClicked.connect(self.onItemClick)

        # Create two sizers
        self._sizer1 = QtWidgets.QVBoxLayout(self)
        self._sizer2 = QtWidgets.QHBoxLayout()
        self._sizer1.setSpacing(2)
        # set margins
        margin = pyzo.config.view.widgetMargin
        self._sizer1.setContentsMargins(margin, margin, margin, margin)

        # Set layout
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._tree, 1)
        # self._sizer2.addWidget(self._sliderIcon, 0)
        self._sizer2.addWidget(self._navbut_back, 0)
        self._sizer2.addWidget(self._navbut_forward, 0)
        self._sizer2.addStretch(1)
        self._sizer2.addWidget(self._slider, 6)
        self._sizer2.addStretch(1)
        self._sizer2.addWidget(self._options, 0)
        #
        self.setLayout(self._sizer1)

        # Init weak reference to editor
        self._curEditorRef = None

        # Bind to events
        pyzo.editors.currentChanged.connect(self.onEditorsCurrentChanged)
        pyzo.editors.parserDone.connect(self.updateStructure)

        self._options.pressed.connect(self.onOptionsPress)
        self._options._menu.triggered.connect(self.onOptionMenuTiggered)

        # Start
        # When the tool is loaded, the editorStack is already done loading
        # all previous files and selected the appropriate file.
        self.onOptionsPress()  # Create menu now
        self.onEditorsCurrentChanged()

    def _getCurEditorFromRef(self):
        if self._curEditorRef is not None:
            editor = self._curEditorRef()
            if not pyzo.qt.qtutils.isDeleted(editor):
                return editor
        return None

    def onOptionsPress(self):
        """Create the menu for the button, Do each time to make sure
        the checks are right."""

        # Get menu
        menu = self._options._menu
        menu.clear()

        for type in ["class", "def", "cell", "todo", "import", "attribute"]:
            checked = type in self._config.showTypes
            action = menu.addAction("Show {}".format(type))
            action.setCheckable(True)
            action.setChecked(checked)

    def onOptionMenuTiggered(self, action):
        """The user decides what to show in the structure."""

        # What to show
        type = action.text().split(" ", 1)[1]

        # Swap
        if type in self._config.showTypes:
            while type in self._config.showTypes:
                self._config.showTypes.remove(type)
        else:
            self._config.showTypes.append(type)

        # Update
        self.updateStructure()

    def onEditorsCurrentChanged(self):
        """Notify that the file is being parsed and make
        sure that not the structure of a previously selected
        file is shown."""

        prevEditor = self._getCurEditorFromRef()
        if prevEditor is not None:
            prevEditor.cursorPositionChanged.disconnect(self.callbackPosChanged)
            prevEditor.fontChanged.disconnect(self.updateStructure)
        self._curEditorRef = None

        # Get editor and clear list
        editor = pyzo.editors.getCurrentEditor()
        self._tree.clear()

        if editor is not None:
            self._curEditorRef = weakref.ref(editor)

            # Notify
            text = translate("pyzoSourceStructure", "Parsing ") + editor._name + " ..."
            item = QtWidgets.QTreeWidgetItem(self._tree, [text])
            item.linenr = 1  # avoid error in the callback when someone clicks this item

            # Try getting the structure right now
            self.updateStructure()

            editor.cursorPositionChanged.connect(self.callbackPosChanged)

            # Update when code editor font changes
            editor.fontChanged.connect(self.updateStructure)

    def callbackPosChanged(self, *args):
        self.updateSelection()

    def _getCurrentNav(self):
        editor = self._getCurEditorFromRef()
        if editor is None:
            return None
        if editor not in self._nav:
            self._nav[editor] = Navigation()
        return self._nav[editor]

    def onNavBack(self):
        nav = self._getCurrentNav()
        if not nav or not nav.back:
            return
        linenr = nav.back.pop(-1)
        old_linenr = self._navigate_to_line(linenr)
        if old_linenr is not None:
            nav.forward.append(old_linenr)

    def onNavForward(self):
        nav = self._getCurrentNav()
        if not nav or not nav.forward:
            return
        linenr = nav.forward.pop(-1)
        old_linenr = self._navigate_to_line(linenr)
        if old_linenr is not None:
            nav.back.append(old_linenr)

    def onItemClick(self, item):
        """Go to the right line in the editor and give focus."""

        # If item is attribute, get parent
        if not item.linenr:
            item = item.parent()

        old_linenr = self._navigate_to_line(item.linenr)

        if old_linenr is not None:
            nav = self._getCurrentNav()
            if nav and (not nav.back or nav.back[-1] != old_linenr):
                nav.back.append(old_linenr)
                nav.forward = []

    def _navigate_to_line(self, linenr):
        # Get editor
        editor = pyzo.editors.getCurrentEditor()
        if not editor:
            return None
        # Keep current line nr
        old_linenr = editor.textCursor().blockNumber() + 1
        # Move to line
        editor.gotoLine(linenr)
        # Give focus
        pyzo.callLater(editor.setFocus)
        return old_linenr

    def _updateColors(self):
        """gets the colors from the color theme resp. from the cache"""
        try:
            theme = pyzo.themes[pyzo.config.settings.theme.lower()]["data"]
            if theme is self._color_theme:
                return

            self._color_theme = theme

            def get_color(name, sub="fore"):
                parts = [part.split(":", 1) for part in theme[name].split(",")]
                colors = {k.strip(): v.strip() for k, v in parts}
                return colors[sub]

            self._colors = {
                "cell": get_color("syntax.python.cellcomment"),
                "class": get_color("syntax.classname"),
                "def": get_color("syntax.functionname"),
                "attribute": get_color("syntax.comment"),
                "import": get_color("syntax.keyword"),
                "todo": get_color("syntax.todocomment"),
                "nameismain": get_color("syntax.keyword"),
                "background": get_color("editor.text", "back"),
                "currentline": get_color("editor.highlightcurrentline", "back"),
            }
        except Exception as err:
            print("Reverting to defaut source structure colors:", str(err))
            self._colors = {
                "cell": "#b58900",
                "class": "#cb4b16",
                "def": "#073642",
                "attribute": "#657b83",
                "import": "#268bd2",
                "todo": "#d33682",
                "nameismain": "#859900",
                "background": "#fff",
                "currentline": "#ccc",
            }

    def updateStructure(self):
        """Updates the tree."""

        # Get editor
        newEditor = pyzo.editors.getCurrentEditor()
        if newEditor is None:
            return

        # Something to show
        result = pyzo.parser._getResult(newEditor)
        if result is None:
            return

        # Do the editors match?
        curEditor = self._getCurEditorFromRef()
        if newEditor is not curEditor or id(curEditor) != result.editorId:
            return

        # Get colors
        self._updateColors()
        colors = self._colors

        # Define what to show
        showTypes = self._config.showTypes

        # Define to what level to show (now is also a good time to save)
        showLevel = int(self._slider.value())
        self._config.level = showLevel
        showLevel = showLevel if showLevel < 5 else 99

        self._lineItemList = lineItemList = []
        self._pathList = pathList = []
        currentPath = []

        def SetItems(parentItem, fictiveObjects, level):
            level += 1
            currentPath.append(None)  # append placeholder value
            for object in fictiveObjects:
                type = object.type
                if type not in showTypes and type != "nameismain":
                    continue
                # Construct text
                if type == "import":
                    text = "→ {} ({})".format(object.name, object.text)
                elif type == "todo":
                    text = object.name
                elif type == "nameismain":
                    text = object.text
                elif type == "class":
                    text = object.name
                elif type == "def":
                    text = object.name + "()"
                elif type == "attribute":
                    text = "- " + object.name
                elif type in ("cell", "##", "#%%", "# %%"):
                    type = "cell"
                    # pad to length 120 with whitespaces so that the
                    # whole line is underlined
                    text = "## {:<120}".format(object.name)
                else:
                    text = "{} {}".format(type, object.name)

                # Create item
                thisItem = QtWidgets.QTreeWidgetItem(parentItem, [text])
                color = QtGui.QColor(colors[object.type])
                thisItem.setForeground(0, QtGui.QBrush(color))
                font = curEditor.font()  # Same font as code editor
                font.setBold(True)
                if type == "cell":
                    font.setUnderline(True)
                thisItem.setFont(0, font)
                thisItem.linenr = object.linenr

                currentPath[-1] = (type, text)
                lineItemList.append((object.linenr, object.linenr2, thisItem))
                if type in ("class", "def"):
                    pathList.append((object.linenr, object.linenr2, tuple(currentPath)))

                # Any children that we should display?
                if object.children:
                    SetItems(thisItem, object.children, level)
                # Set visibility
                thisItem.setExpanded(bool(level < showLevel))

            currentPath.pop()

        # Go
        self._tree.setStyleSheet(
            "QTreeWidget {background-color: " + colors["background"] + ";}"
        )
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        SetItems(self._tree, result.rootItem.children, 0)
        self._tree.setUpdatesEnabled(True)

        self.updateSelection()

    def updateSelection(self):
        editor = self._getCurEditorFromRef()

        if editor is not None and len(self._lineItemList) > 0:
            # Get current line number and the structure
            lineNum = editor.textCursor().blockNumber() + 1
            selectedItem = self._getObjectForLine(self._lineItemList, lineNum)
            path = self._getObjectForLine(self._pathList, lineNum)

            # clear selection and restore background color of previously selected item
            self._tree.clearSelection()
            if self._prevSelectedItem is not None:
                if not pyzo.qt.qtutils.isDeleted(self._prevSelectedItem):
                    self._prevSelectedItem.setBackground(
                        0, QtGui.QBrush(QtGui.QColor(self._colors["background"]))
                    )
            self._prevSelectedItem = selectedItem

            # select the new item
            if selectedItem is not None:
                if not pyzo.qt.qtutils.isDeleted(selectedItem):
                    selectedItem.setBackground(
                        0, QtGui.QBrush(QtGui.QColor(self._colors["currentline"]))
                    )
                    # instead of changing the background color we could also change the selection
                    # # self._tree.setCurrentItem(selectedItem)
                    self._tree.scrollToItem(
                        selectedItem
                    )  # ensure that the item is visible

            if path is not None:
                s = " --> ".join("{} {}".format(type, text) for type, text in path)
            else:
                s = "top level"
            pyzo.main.statusBar().showMessage("Source structure:    " + s)
        else:
            pyzo.main.statusBar().showMessage("")

    @staticmethod
    def _getObjectForLine(objectList, lineNum):
        foundObject = None
        for start, end, payload in objectList:
            if start > lineNum:
                break
            if start <= lineNum < end:
                foundObject = payload
        return foundObject
