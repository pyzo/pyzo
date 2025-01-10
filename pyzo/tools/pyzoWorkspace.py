import re

import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets

tool_name = pyzo.translate("pyzoWorkspace", "Workspace")
tool_summary = pyzo.translate(
    "pyzoWorkspace", "Lists the variables in the current shell's namespace."
)


def splitName(name):
    """Split an object name in parts, taking dots and indexing into account."""
    parts = name.replace("[", ".[").split(".")
    return [p for p in parts if p]


def joinName(parts):
    """Join the parts of an object name, taking dots and indexing into account."""
    return ".".join(parts).replace(".[", "[")


def wildcardsToRegExp(searchText):
    """converts a search text with wildcards to a regular expression string

    e.g.: 'ab)c*de?f??gh*' --> 'ab\\)c.*?de.f..gh.*?'
    """
    ll = []
    for s in re.split(r"(\*|\?)", searchText):
        if s == "*":
            ll.append(".*?")
        elif s == "?":
            ll.append(".")
        else:
            ll.append(re.escape(s))
    return "".join(ll)


class WorkspaceProxy(QtCore.QObject):
    """WorkspaceProxy

    A proxy class to handle the asynchonous behaviour of getting information
    from the shell. The workspace tool asks for a certain name, and this
    class notifies when new data is available using a qt signal.

    """

    haveNewData = QtCore.Signal()

    def __init__(self):
        super().__init__()

        # Variables
        self._variables = []

        # Element to get more info of
        self._name = ""

        # Bind to events
        pyzo.shells.currentShellChanged.connect(self._onCurrentShellChanged)
        pyzo.shells.currentShellStateChanged.connect(self._onCurrentShellStateChanged)

        # Initialize
        self._onCurrentShellStateChanged()

    def addNamePart(self, part):
        """Add a part to the name."""
        parts = splitName(self._name)
        parts.append(part)
        self.setName(joinName(parts))

    def setName(self, name):
        """Set the name that we want to know more of."""
        self._name = name

        shell = pyzo.shells.getCurrentShell()
        if shell:
            future = shell._request.dir2(self._name)
            future.add_done_callback(self._processResponse)

    def goUp(self):
        """Cut the last part off the name."""
        parts = splitName(self._name)
        if parts:
            parts.pop()
        self.setName(joinName(parts))

    def _onCurrentShellChanged(self):
        """When no shell is selected now, update this. In all other cases,
        the _onCurrentShellStateChanged will be fired too.
        """
        shell = pyzo.shells.getCurrentShell()
        if not shell:
            self._variables = []
            self.haveNewData.emit()

    def _onCurrentShellStateChanged(self):
        """Do a request for information!"""
        self.updateVariables()

    def updateVariables(self):
        shell = pyzo.shells.getCurrentShell()
        if not shell:
            self._variables = []
        elif shell._state.lower() != "busy":
            future = shell._request.dir2(self._name)
            future.add_done_callback(self._processResponse)

    def _processResponse(self, future):
        """We got a response, update our list and notify the tree."""

        response = []

        # Process future
        if future.cancelled():
            pass  # print('Introspect cancelled') # No living kernel
        elif future.exception():
            print("Introspect-queryDoc-exception: ", future.exception())
        else:
            response = future.result()

        self._variables = response
        self.haveNewData.emit()


class WorkspaceItem(QtWidgets.QTreeWidgetItem):
    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            return float(self.text(column).strip("[]")) > float(
                otherItem.text(column).strip("[]")
            )
        except ValueError:
            return self.text(column) > otherItem.text(column)


class WorkspaceTree(QtWidgets.QTreeWidget):
    """WorkspaceTree

    The tree that displays the items in the current namespace.
    I first thought about implementing this using the mode/view
    framework, but it is so much work and I can't seem to fully
    understand how it works :(

    The QTreeWidget is so very simple and enables sorting very
    easily, so I'll stick with that ...

    """

    def __init__(self, parent):
        super().__init__(parent)

        self._config = parent._config
        self._compiledRegExp = re.compile(r".*")

        # Set header stuff
        self.setHeaderHidden(False)
        self.setColumnCount(3)
        self.setHeaderLabels(
            [
                pyzo.translate("pyzoWorkspace", "Name"),
                pyzo.translate("pyzoWorkspace", "Type"),
                pyzo.translate("pyzoWorkspace", "Repr"),
            ]
        )
        # self.setColumnWidth(0, 100)
        self.setSortingEnabled(True)

        # Nice rows
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)

        # Create proxy
        self._proxy = WorkspaceProxy()
        self._proxy.haveNewData.connect(self.fillWorkspace)

        # For menu
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self._menu = QtWidgets.QMenu()
        self._menu.triggered.connect(self._contextMenuTriggered)

        # Bind to events
        self.itemActivated.connect(self.onItemExpand)

        self._startUpVariables = frozenset(("In", "Out", "exit", "get_ipython", "quit"))

        self.setToolTip(
            "keyboard shortcuts for selected variable:\n"
            "h ... show variable info in Interactive help tool\n"
            "v ... add variable to Expression viewer tool\n"
            "p ... print(variable)\n"
            "r ... print(repr(variable))\n"
            "RETURN/ENTER ... show namespace\n"  # this is done via signal itemActivated
            "BACKSPACE ... switch to parent namespace\n"
            "DEL ... del variable"
        )

    def keyPressEvent(self, event):
        key = event.key()
        item = self.currentItem()
        if item is not None and not event.modifiers():
            if key == QtCore.Qt.Key.Key_Delete:
                self._performCommand("Delete", item)
                return
            if key == QtCore.Qt.Key.Key_H:
                self._performCommand("Show help", item)
                return
            if key == QtCore.Qt.Key.Key_V:
                self._performCommand("Add to Expr Viewer", item)
                return
            if key == QtCore.Qt.Key.Key_P:
                self._performCommand("str", item)
                return
            if key == QtCore.Qt.Key.Key_R:
                self._performCommand("repr", item)
                return
            if key == QtCore.Qt.Key.Key_Backspace:
                self._proxy.goUp()
                return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """Show the context menu."""

        QtWidgets.QTreeView.contextMenuEvent(self, event)

        # Get if an item is selected
        item = self.currentItem()
        if not item:
            return

        # Create menu
        self._menu.clear()
        commands = [
            ("Show namespace", pyzo.translate("pyzoWorkspace", "Show namespace")),
            ("Show help", pyzo.translate("pyzoWorkspace", "Show help")),
            (
                "Add to Expr Viewer",
                pyzo.translate("pyzoWorkspace", "Add to Expression viewer tool"),
            ),
            ("str", "print(variable)"),
            ("repr", "print(repr(variable))"),
            ("Delete", pyzo.translate("pyzoWorkspace", "Delete")),
        ]
        for request, display in commands:
            action = self._menu.addAction(display)
            action._what = request
            action._item = item

        # Show
        self._menu.popup(QtGui.QCursor.pos() + QtCore.QPoint(3, 3))

    def _contextMenuTriggered(self, action):
        """Process a request from the context menu."""
        self._performCommand(action._what, action._item)

    def _performCommand(self, cmd, item):
        objectName = joinName(splitName(self._proxy._name) + [item.text(0)])
        if cmd == "Show namespace":
            # Go deeper
            self.onItemExpand(item)
        elif cmd == "Show help":
            # Show help in help tool (if loaded)
            hw = pyzo.toolManager.getTool("pyzointeractivehelp")
            if hw:
                hw.setObjectName(objectName, addToHist=True)
        elif cmd == "Add to Expr Viewer":
            self._addExpressionToViewer(objectName)
        elif cmd in ("str", "repr"):
            shell = pyzo.shells.getCurrentShell()
            if shell is not None:
                if cmd == "str":
                    shell.executeCommand("print({})\n".format(objectName))
                else:
                    shell.executeCommand("print(repr({}))\n".format(objectName))
        elif cmd == "Delete":
            # Delete the variable
            shell = pyzo.shells.getCurrentShell()
            if shell is not None:
                shell.processLine("del " + objectName)

    def _addExpressionToViewer(self, expr, doRefresh=True):
        """add an expression to Expression viewer tool (if loaded)"""
        ev = pyzo.toolManager.getTool("pyzoexpressionviewer")
        if ev:
            ev.addExpression(expr)
            ev.manualRefresh()

    def onItemExpand(self, item):
        """Inspect the attributes of that item."""
        self._proxy.addNamePart(item.text(0))

    def setCompiledRegExp(self, compiledRegExp_or_errorstring):
        """Set the name filter for variables via a compiled regular expression."""
        self._compiledRegExp = compiledRegExp_or_errorstring

    def fillWorkspace(self):
        """Update the workspace tree."""

        try:
            selectedName = self.selectedItems()[0].text(0)
        except Exception:
            selectedName = None
        newSelectedItem = None

        if isinstance(self._compiledRegExp, str):
            errorMessage = self._compiledRegExp
            self.parent().displayEmptyWorkspace(True, errorMessage)
            return

        # Set name
        line = self.parent()._line
        line.setText(self._proxy._name)

        self.setSortingEnabled(False)

        # Add elements
        # The widget is not cleared to keep its current scroll bar position.
        i = -1
        for name, typeName, kind, repres in self._proxy._variables:
            # <kludge 2>
            # the typeTranslation dictionary contains "synonyms" for types that will be hidden
            kind = self._config.typeTranslation.get(kind, kind)
            # </kludge 2>
            if kind in self._config.hideTypes:
                continue
            if name.startswith("_") and "private" in self._config.hideTypes:
                continue
            if "startup" in self._config.hideTypes and name in self._startUpVariables:
                continue
            if not self._compiledRegExp.fullmatch(name):
                continue

            i += 1
            item = self.topLevelItem(i)
            if item is None:
                # Create item
                item = WorkspaceItem((name, typeName, repres), 0)
                self.addTopLevelItem(item)
            else:
                item.setText(0, name)
                item.setText(1, typeName)
                item.setText(2, repres)
                item.setSelected(False)

            if name == selectedName:
                newSelectedItem = item

            # Set tooltip
            tt = "{}: {}".format(name, repres)
            item.setToolTip(0, tt)
            item.setToolTip(1, tt)
            item.setToolTip(2, tt)

        for _ in range(i + 1, self.topLevelItemCount()):
            self.takeTopLevelItem(i + 1)  # delete remaining entries

        self.setSortingEnabled(True)
        if newSelectedItem is not None:
            newSelectedItem.setSelected(True)
            self.setCurrentItem(newSelectedItem)

        self.parent().displayEmptyWorkspace(
            self.topLevelItemCount() == 0 and self._proxy._name == ""
        )

    def _addAllToViewer(self):
        """add all expressions to the Expression viewer tool (if loaded)"""
        n = self.topLevelItemCount()
        for i in range(n):
            item = self.topLevelItem(i)
            if item is not None:
                objectName = joinName(splitName(self._proxy._name) + [item.text(0)])
                self._addExpressionToViewer(objectName, doRefresh=(i == n - 1))


class PyzoWorkspace(QtWidgets.QWidget):
    """PyzoWorkspace

    The main widget for this tool.

    """

    def __init__(self, parent):
        super().__init__(parent)

        # Make sure there is a configuration entry for this tool
        # The pyzo tool manager makes sure that there is an entry in
        # config.tools before the tool is instantiated.
        toolId = self.__class__.__name__.lower()
        self._config = pyzo.config.tools[toolId]
        self._config.setdefault("hideTypes", [])
        self._config.setdefault(
            "typeTranslation",
            {
                "method": "function",
                "builtin_function_or_method": "function",
            },
        )

        # Create tool buttons
        self._refresh = QtWidgets.QToolButton(self)
        self._refresh.setIcon(pyzo.icons.arrow_refresh)
        self._refresh.setIconSize(QtCore.QSize(16, 16))
        self._refresh.setToolTip(
            "manually refresh variables (e.g. for code running in the event loop)\n"
            "this will also refresh the Expression viewer tool, if open"
        )

        self._up = QtWidgets.QToolButton(self)
        self._up.setIcon(pyzo.icons.arrow_left)
        self._up.setIconSize(QtCore.QSize(16, 16))
        self._up.setToolTip("switch to parent namespace")

        self._btnAddAllToViewer = QtWidgets.QToolButton(self)
        self._btnAddAllToViewer.setIcon(pyzo.icons.magnifier_zoom_in)
        self._btnAddAllToViewer.setIconSize(QtCore.QSize(16, 16))
        self._btnAddAllToViewer.setToolTip(
            "add all visible entries to the Expression viewer tool"
        )

        # Create "path" line edit
        self._line = QtWidgets.QLineEdit(self)
        self._line.setReadOnly(True)
        self._line.setStyleSheet(
            "QLineEdit {{ background:{}; }}".format("#888" if pyzo.darkQt else "#ddd")
        )
        self._line.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Create options menu
        self._options = QtWidgets.QToolButton(self)
        self._options.setIcon(pyzo.icons.filter)
        self._options.setIconSize(QtCore.QSize(16, 16))
        self._options.setPopupMode(self._options.ToolButtonPopupMode.InstantPopup)
        self._options.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        #
        self._options._menu = QtWidgets.QMenu()
        self._options.setMenu(self._options._menu)
        self._onOptionsPress()  # create menu now

        # Create tree
        self._tree = WorkspaceTree(self)

        # Create message for when tree is empty
        self._no_results_text = pyzo.translate(
            "pyzoWorkspace",
            "Lists the variables in the current shell's namespace."
            "\n\n"
            "Currently, there are none. Some of them may be hidden because of the filters you configured.",
        )
        self._noResultsLabel = QtWidgets.QLabel(self._no_results_text, self)
        self._noResultsLabel.setVisible(False)
        self._noResultsLabel.setWordWrap(True)

        # Create search line edit
        self._searchText = QtWidgets.QLineEdit(self)

        # Create search options button
        self._searchOptions = QtWidgets.QToolButton(self)
        self._searchOptions.setIcon(pyzo.icons.magnifier)
        self._searchOptions.setIconSize(QtCore.QSize(16, 16))
        self._searchOptions.setPopupMode(
            self._searchOptions.ToolButtonPopupMode.InstantPopup
        )
        self._searchOptions.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        #
        self._searchOptions._menu = QtWidgets.QMenu()
        self._searchOptions.setMenu(self._searchOptions._menu)
        self._onSearchOptionsPress()  # create menu now and init default config values
        self._updateSearchPlaceHolderText()

        # We put the tooltip text to the search options button instead of the
        # search text widget to make it less annoying.
        self._searchOptions.setToolTip(
            "Enter one or multiple space-separated search expressions.\n"
            "A variable name will be displayed if it matches at least one of the expressions.\n"
            "\n"
            "Depending on the settings, search expressions are either\n"
            "\n"
            "texts with wildcards:\n"
            "    a single question mark (?) matches exactly one character\n"
            "    an asterisk (*) matches zero or multiple characters\n"
            '    example: "a* b*" ... matches all variables beginning with "a" or "b"\n'
            "\n"
            "or regular expressions:\n"
            '    example: "myvar[0-5].* obj\\d+ x.*"'
        )

        # Set layout
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._refresh, 0)
        layout.addWidget(self._up, 0)
        layout.addWidget(self._line, 1)
        layout.addWidget(self._btnAddAllToViewer, 0)
        layout.addWidget(self._options, 0)
        #
        searchLayout = QtWidgets.QHBoxLayout()
        searchLayout.addWidget(self._searchText, 1)
        searchLayout.addWidget(self._searchOptions, 0)
        #
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addLayout(layout, 0)
        mainLayout.addWidget(self._noResultsLabel, 1)
        mainLayout.addWidget(self._tree, 2)
        mainLayout.setSpacing(2)
        mainLayout.addLayout(searchLayout, 0)

        # set margins
        margin = pyzo.config.view.widgetMargin
        mainLayout.setContentsMargins(margin, margin, margin, margin)
        self.setLayout(mainLayout)

        # Bind events
        self._up.pressed.connect(self._tree._proxy.goUp)
        self._refresh.pressed.connect(self._onButtonRefresh)
        self._options.pressed.connect(self._onOptionsPress)
        self._options._menu.triggered.connect(self._onOptionMenuTiggered)
        self._searchOptions.pressed.connect(self._onSearchOptionsPress)
        self._searchOptions._menu.triggered.connect(self._onSearchOptionMenuTiggered)
        self._searchText.textChanged.connect(self._onSearchTextUpdated)
        self._btnAddAllToViewer.pressed.connect(self._tree._addAllToViewer)

    def displayEmptyWorkspace(self, empty, customMessage=None):
        if customMessage is None:
            customMessage = self._no_results_text
        self._tree.setVisible(not empty)
        self._noResultsLabel.setText(customMessage)
        self._noResultsLabel.setVisible(empty)

    def _onButtonRefresh(self):
        self.manualRefresh()
        ev = pyzo.toolManager.getTool("pyzoexpressionviewer")
        if ev:
            ev.manualRefresh()

    def manualRefresh(self):
        """manually refresh the variables"""
        self._tree._proxy.updateVariables()

    def _onOptionsPress(self):
        """Create the menu for the button, Do each time to make sure
        the checks are right."""

        # Get menu
        menu = self._options._menu
        menu.clear()

        hideables = [
            ("type", pyzo.translate("pyzoWorkspace", "Hide types")),
            ("function", pyzo.translate("pyzoWorkspace", "Hide functions")),
            ("module", pyzo.translate("pyzoWorkspace", "Hide modules")),
            ("private", pyzo.translate("pyzoWorkspace", "Hide private identifiers")),
            (
                "startup",
                pyzo.translate("pyzoWorkspace", "Hide the shell's startup variables"),
            ),
        ]

        for type, display in hideables:
            checked = type in self._config.hideTypes
            action = menu.addAction(display)
            action._what = type
            action.setCheckable(True)
            action.setChecked(checked)

    def _onOptionMenuTiggered(self, action):
        """The user decides what to hide in the workspace."""

        # What to show
        type = action._what.lower()

        self._config.hideTypes = list(set(self._config.hideTypes) ^ {type})

        # Update
        self._tree.fillWorkspace()

    def _onSearchOptionsPress(self):
        """Create the menu for the button, Do each time to make sure
        the checks are right."""

        menu = self._searchOptions._menu
        menu.clear()

        searchOptions = [
            ("searchMatchCase", True, pyzo.translate("pyzoWorkspace", "Match case")),
            ("searchRegExp", False, pyzo.translate("pyzoWorkspace", "RegExp")),
            (
                "searchStartsWith",
                True,
                pyzo.translate("pyzoWorkspace", "Starts with ..."),
            ),
        ]

        for name, default, label in searchOptions:
            action = menu.addAction(label)
            action._what = name
            action.setCheckable(True)
            action.setChecked(self._config.setdefault(name, default))

    def _onSearchOptionMenuTiggered(self, action):
        name = action._what
        self._config[name] ^= True

        # Update
        self._onSearchTextUpdated()
        self._tree.fillWorkspace()
        self._updateSearchPlaceHolderText()

    def _onSearchTextUpdated(self):
        needles = self._searchText.text().split()
        flags = re.IGNORECASE if not self._config.searchMatchCase else 0
        if len(needles) == 0:
            regExpList = [r".*"]
        elif self._config.searchRegExp:
            if self._config.searchStartsWith:
                needles = [s + ".*" for s in needles]
            regExpList = needles
        else:
            if self._config.searchStartsWith:
                needles = [s + "*" for s in needles]
            regExpList = [wildcardsToRegExp(s) for s in needles]

        pattern = "(?:" + ")|(?:".join(regExpList) + ")"
        try:
            compiledRegExp = re.compile(pattern, flags)
        except Exception as e:
            compiledRegExp = "invalid regular expression:\n" + pattern + "\n" + str(e)

        self._tree.setCompiledRegExp(compiledRegExp)
        self._tree.fillWorkspace()

    def _updateSearchPlaceHolderText(self):
        # Update
        self._searchText.setPlaceholderText(
            "[{} mode, case {}]".format(
                "RegExp" if self._config.searchRegExp else "wildcards",
                "sensitive" if self._config.searchMatchCase else "insensitive",
            )
        )
