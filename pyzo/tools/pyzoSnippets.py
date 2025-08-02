import os
import re
import shutil
import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets  # noqa
from pyzo import translate

tool_name = translate("snippets", "Snippets")
tool_summary = "source code and text snippets"

Qt = QtCore.Qt


class PyzoSnippets(QtWidgets.QWidget):
    _searchOptions = {  # value: config_name, default_value, label
        "name": ("searchName", True, translate("snippets", "Search name")),
        "description": (
            "searchDescription",
            True,
            translate("snippets", "Search description"),
        ),
        "code": ("searchCode", True, translate("snippets", "Search code")),
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        toolId = self.__class__.__name__.lower()
        self._config = pyzo.config.tools[toolId]

        self._loadSnippets()

        # setup layout
        self._layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(self._layout)
        self._hlayout = QtWidgets.QHBoxLayout(self)
        self._layout.addLayout(self._hlayout)

        # create tree widget
        self._tree = QtWidgets.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.itemSelectionChanged.connect(self._onSelectionChanged)
        self._tree.itemDoubleClicked.connect(self._onItemDoubleClicked)
        self._layout.addWidget(self._tree)

        # create context menu for tree widget
        self._menu = pyzo.core.menu.Menu(self, "Snippets")
        self._menu.addItem(
            translate(
                "snippets",
                "Insert into editor ::: Insert code snippet at the cursor in the current editor",
            ),
            pyzo.icons.paste_plain,
            self._onMenuChosen,
            "insert",
        )
        self._menu.addItem(
            translate("snippets", "Edit ::: Open snippet file in Pyzo"),
            pyzo.icons.application_edit,
            self._onMenuChosen,
            "edit",
        )
        self._tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(
            self._onCustomContextMenuRequested
        )

        # create search line edit
        self._searchText = QtWidgets.QLineEdit(self)
        self._searchText.textChanged.connect(self._updateTreeWidget)
        self._hlayout.addWidget(self._searchText)

        # create menu button
        btn = QtWidgets.QToolButton(self)
        self._menuButton = btn
        self._hlayout.addWidget(btn)
        btn.setIcon(pyzo.icons.application_view_list)
        btn.setIconSize(QtCore.QSize(16, 16))
        btn.setPopupMode(btn.ToolButtonPopupMode.InstantPopup)
        btn.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn._menu = QtWidgets.QMenu()
        btn.setMenu(btn._menu)
        btn.setToolTip(
            'Type "SNIP." in the editor to insert snippets via autocompletion\n'
            "or double-click an entry to insert it at the cursor position.\n"
            'Right-click an entry and select "Edit" to open the file of the snippet.\n'
            "Open the example snippet file for more information.\n"
        )
        btn.pressed.connect(self._onSearchOptionsPress)
        btn._menu.triggered.connect(self._onSearchOptionMenuTiggered)
        self._onSearchOptionsPress()  # create menu now and init default config values

        # set margins
        margin = pyzo.config.view.widgetMargin
        self._layout.setContentsMargins(margin, margin, margin, margin)

        self._updateTreeWidget()
        self._updateSearchPlaceHolderText()

    def _onSearchOptionsPress(self):
        """create the menu for the button

        Do each time to make sure the check boxes have correct values.
        """
        menu = self._menuButton._menu
        menu.clear()

        for name, default, label in self._searchOptions.values():
            action = menu.addAction(label)
            action._what = name
            action.setCheckable(True)
            action.setChecked(self._config.setdefault(name, default))

        menu.addSeparator()

        menuEntries = [
            ("reloadSnippets", translate("snippets", "Reload snippets")),
            (
                "openSnippetsDir",
                translate("snippets", "Open snippets directory outside Pyzo"),
            ),
        ]

        for name, label in menuEntries:
            action = menu.addAction(label)
            action._what = name

    def _onSearchOptionMenuTiggered(self, action):
        name = action._what
        if name in ("searchName", "searchDescription", "searchCode"):
            self._config[name] ^= True
            self._updateTreeWidget()
            self._updateSearchPlaceHolderText()
        elif name == "reloadSnippets":
            self._loadSnippets()
            self._updateTreeWidget()
        elif name == "openSnippetsDir":
            pyzo.util.open_directory_outside_pyzo(self._snippetsDir)

    def _updateSearchPlaceHolderText(self):
        searchKeys = []
        for name, (configName, default, label) in self._searchOptions.items():
            if getattr(self._config, configName):
                searchKeys.append(name)
        if searchKeys:
            t = "search: " + ", ".join(searchKeys)
        else:
            t = "[Please activate at least one search option]"
        self._searchText.setPlaceholderText(t)

    def _onCustomContextMenuRequested(self, pos):
        """Called when context menu is clicked"""

        # get item that was clicked on
        item = self._tree.itemAt(pos)
        if item is None or not hasattr(item, "_snip"):
            return

        self._menu.popup(self._tree.viewport().mapToGlobal(pos + QtCore.QPoint(3, 3)))

    def _onMenuChosen(self, arg):
        item = self._tree.selectedItems()[0]
        snip = getattr(item, "_snip", None)
        if snip is None:
            return

        if arg == "insert":
            ed = pyzo.editors.getCurrentEditor()
            if ed:
                cur = ed.textCursor()
                self._insertSnippet(cur, snip)
                ed.setFocus()
        elif arg == "edit":
            res = pyzo.editors.loadFile(item._snip["filepath"])
            linenr = item._snip["indLine"] + 1
            if res:
                ed = res._editor
                ed.gotoLine(linenr)
                ed.setFocus()

    def _addTreeElems(self, parentItem, snippetsPath):
        snip = self._snippetsFlatTreeFiltered[snippetsPath]
        if isinstance(snip, list):
            for name in snip:
                item = QtWidgets.QTreeWidgetItem(parentItem, [name])
                item.setExpanded(True)
                snippetsPath2 = snippetsPath + (name,)
                self._addTreeElems(item, snippetsPath2)
                snip2 = self._snippetsFlatTreeFiltered[snippetsPath2]
                if isinstance(snip2, dict):
                    item._snip = snip2
                    tt = "filepath: {}\nline number: {}".format(
                        snip2["filepath"], snip2["indLine"] + 1
                    )
                    if snip2["description"]:
                        tt += "\n\n{}".format(snip2["description"])
                    item.setToolTip(0, tt)

    def _onSelectionChanged(self):
        selectedItems = self._tree.selectedItems()
        if selectedItems:
            (item,) = selectedItems
            snip = getattr(item, "_snip", None)
        else:
            # nothing selected or empty list
            snip = None
        self.showHelpForSnip(snip)

    def _onItemDoubleClicked(self, item, column):
        snip = getattr(item, "_snip", None)
        if snip:
            ed = pyzo.editors.getCurrentEditor()
            if ed:
                cur = ed.textCursor()
                self._insertSnippet(cur, snip)
                ed.setFocus()

    def _filterTree(self):
        searchKeys = []
        for name, (configName, default, label) in self._searchOptions.items():
            if getattr(self._config, configName):
                searchKeys.append(name)
        needle = self._searchText.text().casefold()

        flatTree = {(): []}
        for treePath, snip in self._snippetsFlatTree.items():
            if isinstance(snip, dict):
                if any(needle in snip[k].casefold() for k in searchKeys):
                    flatTree[treePath] = snip
                    while True:
                        name = treePath[-1]
                        treePath = treePath[:-1]
                        if treePath in flatTree:
                            flatTree[treePath].append(name)
                            break
                        else:
                            flatTree[treePath] = [name]
        self._snippetsFlatTreeFiltered = flatTree

    def _updateTreeWidget(self):
        self._tree.clear()
        self._filterTree()
        self._addTreeElems(self._tree, ())

    def getAutocompleteNames(self, name):
        # name has to be "SNIP" or "SNIP.something" or "SNIP.something.otherthing" ...
        # returns None or a list of names
        namesOrSnippet = self._snippetsNameLookUp.get(name, [])
        if isinstance(namesOrSnippet, list) and namesOrSnippet:
            return namesOrSnippet
        return None

    def isSnipName(self, name):
        return name.startswith("SNIP.")

    def showHelpForSnip(self, nameOrSnip):
        helpTool = pyzo.toolManager.getTool("pyzointeractivehelp")
        if helpTool:
            if isinstance(nameOrSnip, dict):
                snip = nameOrSnip
            else:
                snip = self._snippetsNameLookUp.get(nameOrSnip, None)
            if isinstance(snip, dict):
                helpTool.helpForCodeSnippet(snip)
            else:
                helpTool.helpForCodeSnippet(None)

    def _insertSnippet(self, textCursor, snip):
        cur = textCursor
        if cur.hasSelection():
            posInBlock = cur.selectionStart() - cur.block().position()
        else:
            posInBlock = cur.positionInBlock()

        textBefore = cur.block().text()[:posInBlock]
        code = snip["code"]
        if textBefore.isspace():
            lines = code.split("\n")
            code = "\n".join(lines[:1] + [(textBefore + s).rstrip() for s in lines[1:]])
        cur.insertText(code)

    def applyAutoCompletion(self, textCursor):
        cur = textCursor
        line = cur.block().text()
        posInBlock = cur.positionInBlock()

        mo = re.fullmatch(r"(.*?\s+|^)(SNIP(?:\.\w+)+)", line[:posInBlock])
        if mo:
            name = mo[2]
            snip = self._snippetsNameLookUp.get(name, None)
            if isinstance(snip, dict):
                cur.setPosition(cur.position() - len(name), cur.MoveMode.KeepAnchor)
                self._insertSnippet(cur, snip)

    def _loadSnippets(self):
        if not hasattr(self._config, "customSnippetsPath"):
            self._config.customSnippetsPath = ""

        if self._config.customSnippetsPath:
            self._snippetsDir = self._config.customSnippetsPath
        else:
            self._snippetsDir = os.path.join(pyzo.appDataDir, "snippets")

        if not self._config.customSnippetsPath:
            if os.path.isdir(os.path.dirname(self._snippetsDir)) and not os.path.isdir(
                self._snippetsDir
            ):
                os.makedirs(self._snippetsDir)
                fpSrc = os.path.join(
                    pyzo.pyzoDir, "resources", "code_examples", "snippets_example.py"
                )
                fpDst = os.path.join(self._snippetsDir, "snippets_example.py")
                shutil.copyfile(fpSrc, fpDst)

        flatTree = {(): []}
        if os.path.isdir(self._snippetsDir):
            stack = [()]
            while stack:
                treePath = stack.pop()
                dirpath = os.path.join(self._snippetsDir, *treePath)
                for s in os.listdir(dirpath):
                    fp = os.path.join(dirpath, s)
                    dirNames = []
                    if os.path.isdir(fp):
                        if _NAME_PATTERN.fullmatch(s):
                            dirNames.append(s)
                        else:
                            print(
                                f'WARNING: ignoring folder "{fp}" because its name is not valid'
                            )
                    elif os.path.isfile(fp):
                        if s.endswith(".py"):
                            for snip in _extractSnippetsFromFile(fp):
                                name = snip["name"]
                                treePath2 = treePath + (name,)

                                if treePath2 in flatTree:
                                    print(
                                        f'WARNING: ignoring snippet "{name}" in file "{fp}" because the name is already used in another snippet'
                                    )
                                    continue

                                flatTree[treePath2] = snip
                                while True:
                                    name2 = treePath2[-1]
                                    treePath2 = treePath2[:-1]
                                    if treePath2 in flatTree:
                                        flatTree[treePath2].append(name2)
                                        break
                                    else:
                                        flatTree[treePath2] = [name2]

                        else:
                            print(
                                f'WARNING: ignoring file "{fp}" because name has no ending ".py"'
                            )

                    for s in dirNames:
                        treePath2 = treePath + (s,)
                        if treePath2 in flatTree:
                            fp = os.path.join(dirpath, s)
                            print(
                                f'WARNING: ignoring folder "{fp}" because there is already a snippet with the same name'
                            )
                        else:
                            stack.append(treePath2)

        self._snippetsFlatTree = flatTree
        self._snippetsNameLookUp = {
            ".".join(("SNIP",) + treePath): v for treePath, v in flatTree.items()
        }


_NAME_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z_0-9]*")
_SNIP_TITLE_PATTERN = re.compile(r"^\s*\#\#\s*SNIP:\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*$")


def _stripLines(lines):
    """removes empty or whitespace-only lines at the start and end of list lines"""
    i = 0
    for i, line in enumerate(lines):
        if line.strip():
            break
    lines = lines[i:]
    i = 0
    for i, line in enumerate(lines[::-1]):
        if line.strip():
            break
    lines = lines[: len(lines) - i]
    return lines


def _extractSnippetsFromFile(filepath):
    snippets = []

    try:
        with open(filepath, "rt", encoding="utf-8") as fd:
            lines = fd.read().split("\n")
    except Exception:
        print("WARNING: could not read snippets from file:", repr(filepath))
    else:
        curName = None
        curStartLineInd = None
        curDescriptionLines = []
        curCodeLines = []
        for indLine, line in enumerate(lines + ["## SNIP: END_OF_FILE"]):
            mo = _SNIP_TITLE_PATTERN.fullmatch(line)
            if mo:
                if curName is not None:
                    curCodeLines = _stripLines(curCodeLines)
                    if len(curCodeLines) > 1:
                        # add a linebreak if there is more than 1 line
                        curCodeLines.append("")
                    snippets.append(
                        {
                            "name": curName,
                            "indLine": curStartLineInd,
                            "description": "\n".join(curDescriptionLines),
                            "code": "\n".join(curCodeLines),
                            "filepath": filepath,
                        }
                    )
                curName = mo[1]
                curStartLineInd = indLine
                curDescriptionLines = []
                curCodeLines = []
            else:
                if not curCodeLines:
                    line2 = line.lstrip()
                    if line2.startswith("#"):
                        line2 = line2[1:]
                        if line2[:1] == " ":
                            line2 = line2[1:]
                        curDescriptionLines.append(line2)
                    else:
                        curCodeLines.append(line)
                else:
                    curCodeLines.append(line)

    return snippets
