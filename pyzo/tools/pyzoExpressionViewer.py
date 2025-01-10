import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets
from pyzo import translate

tool_name = translate("pyzoExpressionViewer", "Expression viewer")
tool_summary = "View values of expressions."


class ExpressionProxy(QtCore.QObject):
    """ExpressionProxy

    A proxy class to handle the asynchonous behaviour of getting information
    from the shell. The expression viewer tool asks for certain expressions,
    and this class notifies when new data is available using a qt signal.
    """

    haveNewData = QtCore.Signal()

    def __init__(self):
        super().__init__()

        self._expressions = []
        self._response = []

        # Bind to events
        pyzo.shells.currentShellChanged.connect(self._onCurrentShellChanged)
        pyzo.shells.currentShellStateChanged.connect(self._onCurrentShellStateChanged)

    def setExpressions(self, expressions):
        """Set the expressions to be evaluated."""
        self._expressions = list(expressions)

    def getExpressions(self):
        return self._expressions[:]

    def evaluateExpressions(self):
        """trigger evaluation of the expressions

        when finished, signal "haveNewData" will be emitted
        """
        shell = pyzo.shells.getCurrentShell()
        if self._expressions and shell and shell._state.lower() != "busy":
            future = shell._request.evalMultiple(self._expressions)
            future.add_done_callback(self._processResponse)

    def _onCurrentShellChanged(self):
        """When no shell is selected now, update this. In all other cases,
        method _onCurrentShellStateChanged will be fired too.
        """
        shell = pyzo.shells.getCurrentShell()
        if not shell:
            self._response = []
            self.haveNewData.emit()

    def _onCurrentShellStateChanged(self):
        self.evaluateExpressions()

    def _processResponse(self, future):
        """We got a response, save the result and notify the tree."""

        self._response = []

        # Process future
        if future.cancelled():
            pass  # no living kernel
        elif future.exception():
            print("Introspect exception:", future.exception())
        else:
            self._response = future.result()

        self.haveNewData.emit()


class ExpressionManager:
    """This is the single source of truth where all expressions and their values are stored."""

    def __init__(self):
        self._expressions = {}  # key: expression, value: (enabled, stringvalue)

    def _cleanUpExpressionString(self, expression):
        valid = True
        expression = expression.strip()
        if len(expression) == 0:
            valid = False
            print("WARNING: expression is empty")
        elif len(expression.splitlines()) != 1:
            # using len splitlines because checking for \r and \n is not enough:
            #   'xx\u2028yy'.splitlines() --> ['xx', 'yy']
            valid = False
            print(
                "WARNING: expression",
                repr(expression),
                "contains new-line like characters",
            )
        elif expression.startswith("#"):
            valid = False
            print(
                "WARNING: expression",
                repr(expression),
                "starts with a comment character",
            )
        return valid, expression

    def clear(self):
        self._expressions.clear()

    def hasExpression(self, expression):
        return expression in self._expressions

    def getExpressions(self):
        """returns the expressions as a dict

        key: expression
        value: (enabled, stringvalue)
        """
        return self._expressions.copy()

    def addExpression(self, expression, enabled=True, value="[not evaluated yet]"):
        valid, expression = self._cleanUpExpressionString(expression)
        if valid:
            self._expressions[expression.strip()] = (enabled, value)
        success = valid
        return success

    def modifyExpression(
        self, expression, newExpression=None, newEnabled=None, newValue=None
    ):
        success = True
        if newExpression is None:
            if expression in self._expressions:
                enabled, stringvalue = self._expressions[expression]
                if newEnabled is None:
                    newEnabled = enabled
                if newValue is None:
                    newValue = stringvalue
                self._expressions[expression] = (bool(newEnabled), newValue)
        elif newExpression != expression:
            # modify the expression, and keep the order of all expressions in the dict
            oldExpressions = self._expressions.copy()
            self.clear()
            for currentExpression, (enabled, stringvalue) in oldExpressions.items():
                if expression == currentExpression:
                    if newEnabled is None:
                        newEnabled = enabled
                    if newValue is None:
                        newValue = stringvalue
                    if not self.addExpression(newExpression, newEnabled):
                        # update failed --> keep old value
                        self.addExpression(expression, enabled)
                        success = False
                else:
                    self._expressions[currentExpression] = (enabled, stringvalue)
        return success

    def toString(self):
        """converts the expressions to a multi-line string

        Each line contains the expression, and if not enabled, it will be prefixed by "# ".
        The stringvalue (result from evaluating the expression) is ignored.
        """
        ll = []
        for expression, (enabled, stringvalue) in self._expressions.items():
            prefix = "" if enabled else "# "
            ll.append(prefix + expression)
        return "\n".join(ll)

    def fromString(self, text):
        """extracts expressions from a multi-line string

        Each line represents an expression.
        If the line is prefixed by a "#", the expression will be marked as disabled.
        """
        oldExpressions = self._expressions.copy()
        self.clear()
        for line in text.splitlines():
            enabled = True
            line = line.strip()
            while line.startswith("#"):
                enabled = False
                line = line.lstrip("#")
                line = line.lstrip()  # this will also strip non-ascii whitespace
            expression = line
            _, value = oldExpressions.get(expression, (False, "[not evaluated yet]"))
            self.addExpression(expression, enabled, value)


class PyzoExpressionViewer(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # create proxy
        self._proxy = ExpressionProxy()
        self._proxy.haveNewData.connect(self._processResults)

        # create expression manager
        self._em = ExpressionManager()

        # create tool buttons
        self._btnRefresh = QtWidgets.QToolButton(self)
        self._btnRefresh.setIcon(pyzo.icons.arrow_refresh)
        self._btnRefresh.setIconSize(QtCore.QSize(16, 16))
        self._btnRefresh.setToolTip(
            "manually refresh expressions (e.g. for code running in the event loop)\n"
            "this will also refresh the Workspace tool, if open"
        )
        self._btnRefresh.pressed.connect(self._onButtonRefresh)

        # create edit toggle button
        self._btnEdit = QtWidgets.QToolButton(self)
        self._btnEdit.setIcon(pyzo.icons.application_edit)
        self._btnEdit.setIconSize(QtCore.QSize(16, 16))
        self._btnEdit.setCheckable(True)
        self._btnEdit.setToolTip("toggle edit mode")
        self._btnEdit.toggled.connect(self._onButtonEditToggled)

        # create add-from-editor button
        self._btnAddFromEditor = QtWidgets.QToolButton(self)
        self._btnAddFromEditor.setIcon(pyzo.icons.add)
        self._btnAddFromEditor.setIconSize(QtCore.QSize(16, 16))
        self._btnAddFromEditor.setToolTip("add selected expression from current editor")
        self._btnAddFromEditor.pressed.connect(self._onButtonAddFromEditor)

        # create clear button
        self._btnRemoveAll = QtWidgets.QToolButton(self)
        self._btnRemoveAll.setIcon(pyzo.icons.application_eraser)
        self._btnRemoveAll.setIconSize(QtCore.QSize(16, 16))
        self._btnRemoveAll.setToolTip("remove all expressions")
        self._btnRemoveAll.pressed.connect(self._onButtonRemoveAll)

        # create monospaced text input
        self._textEdit = QtWidgets.QPlainTextEdit()
        font = self._textEdit.font()
        font.setFamily(pyzo.config.view.fontname)
        self._textEdit.setFont(font)

        # set the top bar layout
        self._topBarLayout = QtWidgets.QHBoxLayout()
        self._topBarLayout.addWidget(self._btnRefresh)
        self._topBarLayout.addWidget(self._btnEdit)
        self._topBarLayout.addWidget(self._btnAddFromEditor)
        self._topBarLayout.addWidget(self._btnRemoveAll)
        self._topBarLayout.addStretch()

        # create the tree widget (but only used as a multi-column list)
        tree = self._tree = QtWidgets.QTreeWidget(self)

        # set header stuff
        tree.setHeaderHidden(False)
        tree.setColumnCount(2)
        tree.setHeaderLabels(["Expression", "Result"])
        tree.header().setStretchLastSection(True)

        # setup context menu for the tree widget
        tree.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._onTreeContextMenuRequested)
        self._treeContextMenu = QtWidgets.QMenu()
        self._treeContextMenu.triggered.connect(self._onTreeContextMenuTriggered)

        # nice rows
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)

        tree.itemChanged.connect(self._onTreeItemChanged)

        # set the main layout
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.setSpacing(2)
        mainLayout.addLayout(self._topBarLayout)
        mainLayout.addWidget(self._tree)
        mainLayout.addWidget(self._textEdit)

        # set margins
        margin = pyzo.config.view.widgetMargin
        mainLayout.setContentsMargins(margin, margin, margin, margin)

        self.setLayout(mainLayout)

        # add example entries
        self._em.addExpression("1 + 1", False)
        self._em.addExpression("len(dir())", False)
        self._em.addExpression("repr('\\n'.join(globals())[:30])", False)
        self._textEdit.setPlainText(self._em.toString())

        self._setEditMode(False)

    def _onTreeContextMenuRequested(self, pos):
        """Show the context menu."""

        # get the selected item
        item = self._tree.currentItem()
        if not item:
            return

        # create menu
        self._treeContextMenu.clear()
        commands = [
            ("ShowInEditMode", "Show in edit mode"),
            ("ToggleRepr", "Toggle repr"),
            ("EvaluateInShell", "Evaluate in shell"),
        ]
        for request, display in commands:
            action = self._treeContextMenu.addAction(display)
            action._what = request
            action._item = item

        # show the context menu
        self._treeContextMenu.popup(QtGui.QCursor.pos())

    def _onTreeContextMenuTriggered(self, action):
        """Process a request from the context menu."""
        self._performTreeItemCommand(action._what, action._item)

    def _performTreeItemCommand(self, cmd, item):
        assert not self._inEditMode()
        expr = item.text(0)
        if cmd == "ToggleRepr":
            prefix, postfix = "repr(", ")"
            if expr.startswith(prefix) and expr.endswith(postfix):
                expr = expr[len(prefix) : len(expr) - len(postfix)]
            else:
                expr = prefix + expr + postfix
            item.setText(0, expr)
        elif cmd == "ShowInEditMode":
            # select the whole corresponding line in the text widget
            ind = self._tree.indexOfTopLevelItem(item)  # -1 if not found
            self._btnEdit.toggle()
            cursor = self._textEdit.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.NextBlock,
                cursor.MoveMode.MoveAnchor,
                ind,
            )
            cursor.movePosition(
                cursor.MoveOperation.EndOfBlock,
                cursor.MoveMode.KeepAnchor,
            )
            self._textEdit.setTextCursor(cursor)
        elif cmd == "EvaluateInShell":
            shell = pyzo.shells.getCurrentShell()
            if shell is not None:
                pyzo.command_history.append(expr)
                shell.executeCommand(expr + "\n")

    def addExpression(self, expression):
        if self._inEditMode():
            text = self._textEdit.toPlainText()
            if expression not in text.splitlines():
                if text != "" and not text.endswith("\n"):
                    text += "\n"
                text += expression + "\n"
                self._textEdit.setPlainText(text)
        else:
            self._em.addExpression(expression, True)
            self._updateTree()
            self._sendExpressionsToProxy()

    def _inEditMode(self):
        return self._btnEdit.isChecked()

    def _setEditMode(self, enabled):
        self._btnRefresh.setEnabled(not enabled)
        if enabled:
            self._proxy.setExpressions([])
            text = self._em.toString()
            if len(text) > 0:
                text += "\n"
            self._textEdit.setPlainText(text)
            self._tree.hide()

            # move to the empty last line -- for immediately entering a new expression
            cursor = self._textEdit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self._textEdit.setTextCursor(cursor)

            self._textEdit.show()
            self._textEdit.setFocus()
        else:
            self._em.fromString(self._textEdit.toPlainText())
            self._updateTree()
            self._sendExpressionsToProxy()
            self._proxy.evaluateExpressions()
            self._textEdit.hide()
            self._tree.show()
            self._tree.setFocus()

    def _sendExpressionsToProxy(self):
        self._proxy.setExpressions(
            [
                expr
                for expr, (enabled, v) in self._em.getExpressions().items()
                if enabled
            ]
        )

    def _onButtonEditToggled(self, enabled):
        self._setEditMode(enabled)

    def _onButtonRefresh(self):
        self.manualRefresh()
        ws = pyzo.toolManager.getTool("pyzoworkspace")
        if ws is not None:
            ws.manualRefresh()

    def _onButtonAddFromEditor(self):
        ed = pyzo.editors.getCurrentEditor()
        if ed is not None:
            expr = ed.textCursor().selectedText().strip()
            self.addExpression(expr)
            self.manualRefresh()

    def _onButtonRemoveAll(self):
        self._em.clear()
        self._sendExpressionsToProxy()
        if self._inEditMode():
            self._textEdit.setPlainText("")
        else:
            self._updateTree()

    def manualRefresh(self):
        """manually refresh the expressions"""
        self._proxy.evaluateExpressions()

    def _onTreeItemChanged(self, item, column):
        self._tree.blockSignals(True)
        try:
            if column == 1:
                # restore original value (tool tip text is the same as the original value)
                item.setText(1, item.toolTip(1))
            elif column == 0:
                if item.text(0) != item.toolTip(0):
                    # update the expression
                    origExpr = item.toolTip(0)
                    newExpr = item.text(0)
                    if not self._em.modifyExpression(origExpr, newExpression=newExpr):
                        item.setText(0, origExpr)
                    else:
                        item.setToolTip(0, newExpr)

                # update the enabled status, no matter if it was changed or not
                enabled = item.checkState(0) == QtCore.Qt.CheckState.Checked
                self._em.modifyExpression(item.text(0), newEnabled=enabled)

                self._sendExpressionsToProxy()
                self._proxy.evaluateExpressions()
        finally:
            self._tree.blockSignals(False)

    def _updateTree(self):
        tree = self._tree
        CS = QtCore.Qt.CheckState

        tree.blockSignals(True)
        try:
            # The widget is not cleared to keep its current scroll bar position.
            i = -1
            for expr, (enabled, stringvalue) in self._em.getExpressions().items():
                i += 1
                item = tree.topLevelItem(i)
                if item is None:
                    # Create item
                    item = QtWidgets.QTreeWidgetItem((expr, stringvalue))
                    tree.addTopLevelItem(item)
                    item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setText(0, expr)
                    item.setText(1, stringvalue)
                    item.setSelected(False)

                item.setCheckState(0, CS.Checked if enabled else CS.Unchecked)
                item.setToolTip(0, expr)
                item.setToolTip(1, stringvalue)

            for _ in range(i + 1, tree.topLevelItemCount()):
                tree.takeTopLevelItem(i + 1)  # delete remaining entries

        finally:
            tree.blockSignals(False)

    def _processResults(self):
        # assign the results to the corresponding expressions in the expression manager
        for expression, success, stringvalue in self._proxy._response:
            if self._em.hasExpression(expression):
                if not success:
                    stringvalue = "[ERROR: " + stringvalue + "]"
                self._em.modifyExpression(expression, newValue=stringvalue)

        if not self._inEditMode():
            self._updateTree()
