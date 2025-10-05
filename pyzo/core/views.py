"""
Views

When starting Pyzo, the window and panel geometries, and the loaded tool panels
are automatically restored. And when closing Pyzo, these geometry and state
values are automatically stored to the configuration file. This view is defined
as the "[NORMAL]" view.

The ViewManager class makes it possible to have more than a single view setup
and to quickly switch between these defined views.

To switch between views, the "Views" dialog must be started, either via Pyzo's
menu, or by pressing the assigned key combination.

When invoked via a key combination that contains a modifier key (e.g. Ctrl),
the dialog will only remain open as long as at least one of these modifier keys
is kept pressed. A repeated press of the non-modifier key (e.g. the 'A' in
Ctrl+Shift+A) will advance the selection to the next entry in the dialog's list
widget, similar to the Pyzo editor's tab switching via Ctrl+Tab.
When releasing all modifier keys, the dialog will be closed and the selected
view in the dialog's list will be activated.

When invoked via the menu or a key shortcut without modifier key, the dialog
will stay open like a normal dialog window.

The list widget contains all defined views, ordered by how recently they were
used, with the currently active view on top. This makes it easier to switch
between two recently used views via the key combinations.

The state of the "[NORMAL]" view is always saved automatically before switching
to another view. All other views must be manually updated by pressing the
"Update view" button in the dialog (with the correct list entry selected).
"""

import sys
import base64

import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets  # noqa


ismacos = sys.platform.startswith("darwin")


class ViewManager:
    NORMAL_VIEW_NAME = "[NORMAL]"

    def __init__(self):
        self._currentViewName = self.NORMAL_VIEW_NAME

        # create entry for normal view, if not present
        self._getViewData(self.NORMAL_VIEW_NAME, True)

        self._bringViewNameToTopOfHistory()

    def getViewNameHistory(self):
        """returns the view names, with recently used views first"""
        return [v["name"] for v in pyzo.config.state.views]

    def _getViewData(self, viewName, createIfNotFound=False):
        for viewData in pyzo.config.state.views:
            if viewData["name"] == viewName:
                break
        else:
            if createIfNotFound:
                viewData = {"name": viewName}
                pyzo.config.state.views.append(viewData)
            else:
                viewData = None

        if viewData:
            if viewName == self.NORMAL_VIEW_NAME:
                viewData = {
                    "name": viewName,
                    "loadedTools": pyzo.config.state.loadedTools,
                    "windowGeometry": pyzo.config.state.windowGeometry,
                    "windowState": pyzo.config.state.windowState,
                }
            return viewData

        raise KeyError("view not found: {}".format(repr(viewName)))

    def getCurrentViewName(self):
        return self._currentViewName

    def isNormalViewActive(self):
        return self._currentViewName == self.NORMAL_VIEW_NAME

    def _bringViewNameToTopOfHistory(self):
        """move current view to front of view list, and keep order of other elements"""
        viewName = self._currentViewName
        pyzo.config.state.views.sort(key=lambda v: v["name"] != viewName)

    def selectView(self, viewName):
        if self.isNormalViewActive() and viewName != self.NORMAL_VIEW_NAME:
            pyzo.main.saveWindowState()

        # Restoring views in Qt is tricky. I had to come up with the following
        # workarounds to make it work with all Qt5 and Qt6 wrappers.
        # There is no guarantee that this will always work. If the geometries are
        # not properly restored, try again by switching to another view and back.
        # The following code worked fine all the time during my tests.
        # Altered versions of the code might also work but with a lower success
        # rate, so do many tests with the new version after "optimizing" the code.

        if self._currentViewName != viewName:
            viewData = self._getViewData(viewName)

            pyzo.main.restoreTools(viewData["loadedTools"])

            def doLater():
                pyzo.main.restoreGeometry(base64.b64decode(viewData["windowGeometry"]))
                pyzo.main.restoreState(base64.b64decode(viewData["windowState"]))
                pyzo.main.paintNow()
                pyzo.main.restoreGeometry(base64.b64decode(viewData["windowGeometry"]))
                pyzo.main.restoreState(base64.b64decode(viewData["windowState"]))

            self._timer = QtCore.QTimer()
            self._timer.singleShot(200, doLater)

        self._currentViewName = viewName
        self._bringViewNameToTopOfHistory()

    def saveView(self, viewName):
        if viewName == self.NORMAL_VIEW_NAME:
            pyzo.main.saveWindowState()
        else:
            viewData = self._getViewData(viewName, createIfNotFound=True)
            viewData.update(pyzo.main.getWindowState())

    def removeView(self, viewName):
        if viewName == self.NORMAL_VIEW_NAME:
            return False

        for v in pyzo.config.state.views[:]:
            if v["name"] == viewName:
                pyzo.config.state.views.remove(v)
        if viewName == self._currentViewName:
            self.selectView(self.NORMAL_VIEW_NAME)

        return True

    def renameView(self, oldName, newName):
        if oldName == self.NORMAL_VIEW_NAME:
            return False
        if newName in self.getViewNameHistory():
            return False
        for v in pyzo.config.state.views:
            if v["name"] == oldName:
                v["name"] = newName
                if oldName == self._currentViewName:
                    self._currentViewName = newName
                break


class QListWidgetModified(QtWidgets.QListWidget):
    def changeSelection(self, delta):
        row = self.currentRow()
        if row == -1:
            row = 0
        self.setCurrentRow((row + delta) % self.count())

    def wheelEvent(self, event):
        # change the list selection by moving the mouse wheel
        degrees = event.angleDelta().y() / 8.0
        delta = -1 if degrees > 0 else (1 if degrees < 0 else 0)
        if delta == 0:
            return
        self.changeSelection(delta)


class ViewManagerDialog(QtWidgets.QDialog):
    @classmethod
    def registerMenuAction(cls, action):
        cls._menuAction = action

    def __init__(self, parent):
        super().__init__(parent)

        self._finished = False
        self._modifiersWerePressedWhenStarted = None

        self.setWindowTitle("Views")

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layoutLeft = QtWidgets.QVBoxLayout()
        layoutRight = QtWidgets.QVBoxLayout()
        layout.addLayout(layoutLeft, 1)
        layout.addLayout(layoutRight, 1)

        # right layout column
        layout = layoutRight

        w = self._btnUpdateView = QtWidgets.QPushButton("Update view")
        w.clicked.connect(self._btnUpdateViewClicked)
        w.setToolTip(
            "Save the current view to the selected view.\n"
            'The "[NORMAL]" view is automatically updated before activating another view.'
        )
        layout.addWidget(w)

        w = self._btnRenameView = QtWidgets.QPushButton("Rename view")
        w.clicked.connect(self._btnRenameViewClicked)
        w.setToolTip(
            'Rename the selected view.\nThe "[NORMAL]" view cannot be renamed.'
        )
        layout.addWidget(w)

        w = self._btnRemoveView = QtWidgets.QPushButton("Remove view")
        w.clicked.connect(self._btnRemoveViewClicked)
        w.setToolTip(
            'Remove the selected view.\nThe "[NORMAL]" view cannot be removed.'
        )
        layout.addWidget(w)

        w = self._btnAddView = QtWidgets.QPushButton("Add view")
        w.clicked.connect(self._btnAddViewClicked)
        w.setToolTip("Add a new view and activate it.")
        layout.addWidget(w)

        w = self._btnRenameView = QtWidgets.QPushButton("Activate view")
        w.clicked.connect(self._btnActivateViewClicked)
        w.setToolTip("Activate the selected view.")
        layout.addWidget(w)

        w = self._btnRenameView = QtWidgets.QPushButton("Cancel")
        w.clicked.connect(self.close)
        layout.addWidget(w)

        layout.addStretch()

        # left layout column
        layout = layoutLeft

        lw = self._lw = QListWidgetModified()
        layout.addWidget(lw)

        # set up the list widget
        self._entries = pyzo.viewManager.getViewNameHistory()

        lw = self._lw
        lw.clear()
        for s in self._entries:
            label = s
            lw.addItem(QtWidgets.QListWidgetItem(label))

        lw.setCurrentRow(0)
        lw.setMinimumWidth(
            lw.sizeHintForColumn(0) + lw.verticalScrollBar().sizeHint().width() + 10
        )

        lw.setToolTip(
            "list of available views, ordered by how recently they were used\n"
            "with the currently active view on top"
        )
        lw.itemDoubleClicked.connect(self._listItemDoubleClicked)

    def _inputNewName(self, initialText):
        text, ok = QtWidgets.QInputDialog.getText(
            self,
            "Pyzo views",
            "Enter new view name:",
            QtWidgets.QLineEdit.EchoMode.Normal,
            initialText,
        )
        return text, ok

    def _makeUniqueName(self, name):
        hist = pyzo.viewManager.getViewNameHistory()
        while name in hist:
            name += " (2)"
        return name

    def _btnRemoveViewClicked(self):
        viewName = self._lw.currentItem().text()
        if viewName == ViewManager.NORMAL_VIEW_NAME:
            return
        self.close()
        self._finished = True
        pyzo.viewManager.removeView(viewName)

    def _btnRenameViewClicked(self):
        oldName = self._lw.currentItem().text()
        if oldName == ViewManager.NORMAL_VIEW_NAME:
            return
        newName, ok = self._inputNewName(oldName)
        if not ok:
            return
        self.close()
        self._finished = True
        newName = self._makeUniqueName(newName)
        pyzo.viewManager.renameView(oldName, newName)

    def _btnAddViewClicked(self):
        newName, ok = self._inputNewName("")
        if not ok:
            return
        newName = self._makeUniqueName(newName)
        self.close()
        self._finished = True
        pyzo.viewManager.saveView(newName)
        pyzo.viewManager.selectView(newName)

    def _btnUpdateViewClicked(self):
        viewName = self._lw.currentItem().text()
        self.close()
        self._finished = True
        pyzo.viewManager.saveView(viewName)

    def _btnActivateViewClicked(self):
        self._finishSelection()

    def _listItemDoubleClicked(self, item):
        self._finishSelection()

    def _finishSelection(self):
        viewName = self._lw.currentItem().text()
        self.close()
        self._finished = True
        pyzo.viewManager.selectView(viewName)

    def keyPressEvent(self, event):
        if self._modifiersWerePressedWhenStarted is None:
            self._modifiersWerePressedWhenStarted = False

        shortcuts = self._menuAction.shortcut()
        if self._finished:
            return

        if pyzo.qt.QT_VERSION_STR.startswith("5."):
            kc = event.key() + int(event.modifiers())  # int
        else:
            kc = event.keyCombination()  # QKeyCombination
        for sc in shortcuts:
            if kc == sc:
                self._lw.changeSelection(1)
                return  # consume event
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self._modifiersWerePressedWhenStarted is None:
            if event.modifiers():
                self._modifiersWerePressedWhenStarted = True

        if self._modifiersWerePressedWhenStarted:
            if not event.modifiers():
                self._finishSelection()
                return  # consume event

        super().keyReleaseEvent(event)
