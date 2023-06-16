import pyzo
from pyzo.qt import QtCore, QtGui, QtWidgets  # noqa
from pyzo import translate

tool_name = translate("pyzoEditorList", "Editor list")
tool_summary = "Display and manage editor tabs via a list."


class MyQListWidget(QtWidgets.QListWidget):
    listEntryDragStart = QtCore.Signal()
    listEntryDragEnd = QtCore.Signal()
    middleButtonClicked = QtCore.Signal(QtCore.QPoint)
    doubleClicked = QtCore.Signal(QtCore.QPoint)

    def dragEnterEvent(self, event):
        super().dragEnterEvent(event)
        self.listEntryDragStart.emit()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.listEntryDragEnd.emit()

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.doubleClicked.emit(event.pos())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MiddleButton:
            self.middleButtonClicked.emit(event.pos())
            return
        super().mousePressEvent(event)


class PyzoEditorList(QtWidgets.QWidget):
    """
    The EditorList is similar to the editor's tab widget:
     - right click on a list entry opens the context menu
     - double click on a list entry activates the corresponding editor tab
     - double click below the last list entry opens a new editor tab
     - middle click on a list entry closes the corresponding editor tab
     - drag and drop to sort list entries, synchronized with the editor tabs
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Widgets
        self._list = MyQListWidget(self)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self._list)

        # set margins
        margin = pyzo.config.view.widgetMargin
        layout.setContentsMargins(margin, margin, margin, margin)

        # Drag/drop
        self._indexMoveStart = None
        self._list.setDragEnabled(True)
        self._list.setDragDropMode(self._list.DragDropMode.InternalMove)
        self._list.listEntryDragStart.connect(self._onListEntryMoveStart)
        self._list.listEntryDragEnd.connect(self._onListEntryMoveEnd)

        # Context menu
        self._menu = pyzo.core.menu.EditorTabContextMenu(self, "EditorTabMenu")
        self._list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(
            self._onCustomContextMenuRequested
        )

        self._list.middleButtonClicked.connect(self._onMiddleButtonClicked)
        self._list.doubleClicked.connect(self._onDoubleClicked)

        pyzo.editors._tabs.tabBar().currentChanged.connect(self._onCurrentTabChanged)
        pyzo.editors._tabs.fileTabsChanged.connect(self._onFileTabsChanged)

        self.updateList()

    def updateList(self):
        tabs = pyzo.editors._tabs
        tabBar = tabs.tabBar()
        self._list.clear()
        for i, tabItem in enumerate(tabs.items()):
            shortName = tabBar.tabText(i)
            longName = tabItem.filename
            shortLongInfo = []
            if tabItem.dirty:
                shortLongInfo.append(("MOD.", "MODIFIED"))
            if tabItem.pinned:
                shortLongInfo.append(("PIN.", "PINNED"))
            if tabItem.id == tabs._mainFile:
                shortLongInfo.append(("MAINF.", "MAINFILE"))
            if len(shortLongInfo) > 0:
                shortName += " [{}]".format(", ".join(sl[0] for sl in shortLongInfo))
                longName += " [{}]".format(", ".join(sl[1] for sl in shortLongInfo))
            listItem = QtWidgets.QListWidgetItem(shortName)
            listItem.setToolTip(longName)
            self._list.addItem(listItem)
        self.selectListRow(tabs.currentIndex())

    def selectListRow(self, index):
        if index >= 0:
            self._list.setCurrentRow(index)
            self._list.scrollToItem(self._list.currentItem())

    ## Keep track of tab bar changes

    def _onCurrentTabChanged(self, index):
        self.selectListRow(index)

    def _onFileTabsChanged(self):
        self.updateList()

    ## User actions

    def _onListEntryMoveStart(self):
        item = self._list.currentItem()
        self._indexMoveStart = self._list.indexFromItem(item).row()

    def _onListEntryMoveEnd(self):
        item = self._list.currentItem()
        newIndex = self._list.indexFromItem(item).row()
        oldIndex = self._indexMoveStart
        self._indexMoveStart = None
        pyzo.editors._tabs.tabBar().moveTab(oldIndex, newIndex)
        pyzo.editors._tabs.setCurrentIndex(newIndex)

    def _onCustomContextMenuRequested(self, pos):
        """Called when context menu is clicked"""
        item = self._list.itemAt(pos)
        if item is not None:
            index = self._list.indexFromItem(item).row()
            self._menu.setIndex(index)
            self._menu.popup(self._list.viewport().mapToGlobal(pos))

    def _onDoubleClicked(self, pos):
        item = self._list.itemAt(pos)
        if item is None:
            # there was no list entry under the cursor
            pyzo.editors.newFile()
        else:
            # list entry was double clicked
            index = self._list.indexFromItem(item).row()
            pyzo.editors._tabs.setCurrentIndex(index)

    def _onMiddleButtonClicked(self, pos):
        item = self._list.itemAt(pos)
        if item is not None:
            index = self._list.indexFromItem(item).row()
            pyzo.editors._tabs.tabCloseRequested.emit(index)
