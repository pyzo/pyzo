"""EditorTabs class

Replaces the earlier EditorStack class.

The editor tabs class represents the different open files. They can
be selected using a tab widget (with tabs placed north of the editor).
It also has a find/replace widget that is at the bottom of the editor.

"""

import os
import sys
import time
import gc
from pyzo.qt import QtCore, QtGui, QtWidgets

import pyzo
from pyzo.core.compactTabWidget import CompactTabWidget
from pyzo.core.editor import createEditor
from pyzo.core.baseTextCtrl import normalizePath
from pyzo.core.pyzoLogging import print
from pyzo.core.icons import EditorTabToolButton
from pyzo import translate


ismacos = sys.platform.startswith("darwin")


def simpleDialog(item, action, question, options, defaultOption):
    """builds and displays a simple dialog

    Options with special buttons
    ----------------------------
    ok, open, save, cancel, close, discard, apply, reset, restoredefaults,
    help, saveall, yes, yestoall, no, notoall, abort, retry, ignore.

    Returns the selected option as a string, or None if canceled.
    """

    # Get filename
    if isinstance(item, FileItem):
        filename = item.id
    else:
        filename = item.id()

    # create button map
    SB = QtWidgets.QMessageBox.StandardButton
    M = {
        "ok": SB.Ok,
        "open": SB.Open,
        "save": SB.Save,
        "cancel": SB.Cancel,
        "close": SB.Close,
        "discard": SB.Discard,
        "apply": SB.Apply,
        "reset": SB.Reset,
        "restoredefaults": SB.RestoreDefaults,
        "help": SB.Help,
        "saveall": SB.SaveAll,
        "yes": SB.Yes,
        "yestoall": SB.YesToAll,
        "no": SB.No,
        "notoall": SB.NoToAll,
        "abort": SB.Abort,
        "retry": SB.Retry,
        "ignore": SB.Ignore,
    }

    # setup dialog
    dlg = QtWidgets.QMessageBox(pyzo.main)
    dlg.setWindowTitle("Pyzo")
    dlg.setText(action + " file:\n{}".format(filename))
    dlg.setInformativeText(question)

    # process options
    buttons = {}
    for option in options:
        option_lower = option.lower()
        # Use standard button?
        if option_lower in M:
            button = dlg.addButton(M[option_lower])
        else:
            button = dlg.addButton(option, dlg.ButtonRole.AcceptRole)
        buttons[button] = option
        # Set as default?
        if option_lower == defaultOption.lower():
            dlg.setDefaultButton(button)

    # get result
    dlg.exec()
    button = dlg.clickedButton()
    return buttons.get(button, None)


def get_shortest_unique_filename(filename, filenames):
    """Get a representation of filename in a way that makes it look
    unique compared to the other given filenames. The most unique part
    of the path is used, and every directory in between that part and the
    actual filename is represented with a slash.
    """

    # Normalize and avoid having filename itself in filenames
    filename1 = filename.replace("\\", "/")
    filenames = [fn.replace("\\", "/") for fn in filenames]
    filenames = [fn for fn in filenames if fn != filename1]

    # Prepare for finding uniqueness
    nameparts1 = filename1.split("/")
    uniqueness = [len(filenames) for i in nameparts1]

    # Establish what parts of the filename are not unique when compared to
    # each entry in filenames.
    for filename2 in filenames:
        nameparts2 = filename2.split("/")
        nonunique_for_this_filename = set()
        for i in range(len(nameparts1)):
            if i < len(nameparts2):
                if nameparts2[i] == nameparts1[i]:
                    nonunique_for_this_filename.add(i)
                if nameparts2[-1 - i] == nameparts1[-1 - i]:
                    nonunique_for_this_filename.add(-i - 1)
        for i in nonunique_for_this_filename:
            uniqueness[i] -= 1

    # How unique is the filename? If its not unique at all, use only base name
    max_uniqueness = max(uniqueness[:-1])
    if max_uniqueness == 0:
        return nameparts1[-1]

    # Produce display name based on base name and last most-unique part
    displayname = nameparts1[-1]
    for i in range(len(uniqueness) - 1)[::-1]:
        displayname = "/" + displayname
        if uniqueness[i] == max_uniqueness:
            displayname = nameparts1[i] + displayname
            break
    return displayname


# todo: some management stuff could (should?) go here
class FileItem:
    """FileItem(editor)

    A file item represents an open file. It is associated with an editing
    component and has a filename.

    """

    def __init__(self, editor):
        # Store editor
        self._editor = editor

        # Init pinned state
        self._pinned = False

    @property
    def editor(self):
        """Get the editor component corresponding to this item."""
        return self._editor

    @property
    def id(self):
        """Get an id of this editor. This is the filename, or for tmp files, the name."""
        if self.filename:
            return self.filename
        else:
            return self.name

    @property
    def filename(self):
        """Get the full filename corresponding to this item."""
        return self._editor.filename

    @property
    def name(self):
        """Get the name corresponding to this item."""
        return self._editor.name

    @property
    def dirty(self):
        """Get whether the file has been changed since it is changed."""
        return self._editor.document().isModified()

    @property
    def pinned(self):
        """Get whether this item is pinned (i.e. will not be closed
        when closing all files.
        """
        return self._pinned


# todo: when this works with the new editor, put in own module.
class FindReplaceWidget(QtWidgets.QFrame):
    """A widget to find and replace text."""

    def __init__(self, *args):
        super().__init__(*args)

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

        # init layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        margin = 0
        layout.setContentsMargins(margin, margin, margin, margin)
        self.setLayout(layout)

        # Create some widgets first to realize a correct tab order
        self._hidebut = QtWidgets.QToolButton(self)
        self._findText = QtWidgets.QLineEdit(self)
        self._replaceText = QtWidgets.QLineEdit(self)

        if True:
            # Create sub layouts
            vsubLayout = QtWidgets.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)

            # Add button
            self._hidebut.setFont(QtGui.QFont("helvetica", 7))
            self._hidebut.setToolTip(translate("search", "Hide search widget (Escape)"))
            self._hidebut.setIcon(pyzo.icons.cancel)
            self._hidebut.setIconSize(QtCore.QSize(16, 16))
            vsubLayout.addWidget(self._hidebut, 0)

            vsubLayout.addStretch(1)

        layout.addSpacing(10)

        if True:
            # Create sub layouts
            vsubLayout = QtWidgets.QVBoxLayout()
            hsubLayout = QtWidgets.QHBoxLayout()
            vsubLayout.setSpacing(0)
            hsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)

            # Add find text
            self._findText.setToolTip(translate("search", "Find pattern"))
            vsubLayout.addWidget(self._findText, 0)

            vsubLayout.addLayout(hsubLayout)

            # Add previous button
            self._findPrev = QtWidgets.QToolButton(self)
            t = translate(
                "search", "Previous ::: Find previous occurrence of the pattern."
            )
            self._findPrev.setText(t)
            self._findPrev.setToolTip(t.tt)

            hsubLayout.addWidget(self._findPrev, 0)

            hsubLayout.addStretch(1)

            # Add next button
            self._findNext = QtWidgets.QToolButton(self)
            t = translate("search", "Next ::: Find next occurrence of the pattern.")
            self._findNext.setText(t)
            self._findNext.setToolTip(t.tt)
            # self._findNext.setDefault(True) # Not possible with tool buttons
            hsubLayout.addWidget(self._findNext, 0)

        layout.addSpacing(10)

        if True:
            # Create sub layouts
            vsubLayout = QtWidgets.QVBoxLayout()
            hsubLayout = QtWidgets.QHBoxLayout()
            vsubLayout.setSpacing(0)
            hsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)

            # Add replace text
            self._replaceText.setToolTip(translate("search", "Replace pattern"))
            vsubLayout.addWidget(self._replaceText, 0)

            vsubLayout.addLayout(hsubLayout)

            # Add replace button
            t = translate("search", "Replace ::: Replace this match.")
            self._replaceBut = QtWidgets.QToolButton(self)
            self._replaceBut.setText(t)
            self._replaceBut.setToolTip(t.tt)
            hsubLayout.addWidget(self._replaceBut, 0)

            hsubLayout.addStretch(1)

            # Add replace kind combo
            self._replaceKind = QtWidgets.QComboBox(self)
            self._replaceKind.addItem(translate("search", "one"))
            self._replaceKind.addItem(translate("search", "all in this file"))
            self._replaceKind.addItem(translate("search", "all in all files"))
            hsubLayout.addWidget(self._replaceKind, 0)

        layout.addSpacing(10)

        if True:
            # Create sub layouts
            vsubLayout = QtWidgets.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)

            # Add match-case checkbox
            t = translate("search", "Match case ::: Find words that match case.")
            self._caseCheck = QtWidgets.QCheckBox(t, self)
            self._caseCheck.setToolTip(t.tt)
            vsubLayout.addWidget(self._caseCheck, 0)

            # Add regexp checkbox
            t = translate("search", "RegExp ::: Find using regular expressions.")
            self._regExp = QtWidgets.QCheckBox(t, self)
            self._regExp.setToolTip(t.tt)
            vsubLayout.addWidget(self._regExp, 0)

        if True:
            # Create sub layouts
            vsubLayout = QtWidgets.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)

            # Add whole-word checkbox
            t = translate("search", "Whole words ::: Find only whole words.")
            self._wholeWord = QtWidgets.QCheckBox(t, self)
            self._wholeWord.setToolTip(t.tt)
            self._wholeWord.resize(60, 16)
            vsubLayout.addWidget(self._wholeWord, 0)

            # Add autohide dropbox
            t = translate(
                "search", "Auto hide ::: Hide search/replace when unused for 10 s."
            )
            self._autoHide = QtWidgets.QCheckBox(t, self)
            self._autoHide.setToolTip(t.tt)
            self._autoHide.resize(60, 16)
            vsubLayout.addWidget(self._autoHide, 0)

        layout.addStretch(1)

        # Set placeholder texts
        for lineEdit in [self._findText, self._replaceText]:
            if hasattr(lineEdit, "setPlaceholderText"):
                lineEdit.setPlaceholderText(lineEdit.toolTip())
            lineEdit.textChanged.connect(self.autoHideTimerReset)

        # Set focus policy
        for but in [
            self._findPrev,
            self._findNext,
            self._replaceBut,
            self._caseCheck,
            self._wholeWord,
            self._regExp,
        ]:
            # but.setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)
            but.clicked.connect(self.autoHideTimerReset)

        # create timer objects
        self._timerBeginEnd = QtCore.QTimer(self)
        self._timerBeginEnd.setSingleShot(True)
        self._timerBeginEnd.timeout.connect(self.resetAppearance)
        #
        self._timerAutoHide = QtCore.QTimer(self)
        self._timerAutoHide.setSingleShot(False)
        self._timerAutoHide.setInterval(500)  # ms
        self._timerAutoHide.timeout.connect(self.autoHideTimerCallback)
        self._timerAutoHide_t0 = time.time()
        self._timerAutoHide.start()

        # create callbacks
        self._findText.returnPressed.connect(self.findNext)
        self._hidebut.clicked.connect(self.hideMe)
        self._findNext.clicked.connect(self.findNext)
        self._findPrev.clicked.connect(self.findPrevious)
        self._replaceBut.clicked.connect(self.replace)
        #
        self._regExp.stateChanged.connect(self.handleReplacePossible)

        # init case and regexp
        self._caseCheck.setChecked(bool(pyzo.config.state.find_matchCase))
        self._regExp.setChecked(bool(pyzo.config.state.find_regExp))
        self._wholeWord.setChecked(bool(pyzo.config.state.find_wholeWord))
        self._autoHide.setChecked(bool(pyzo.config.state.find_autoHide))

        # show or hide?
        if pyzo.config.state.find_show:
            self.show()
        else:
            self.hide()

    def autoHideTimerReset(self):
        self._timerAutoHide_t0 = time.time()

    def autoHideTimerCallback(self):
        """Check whether we should hide the tool."""
        timeout = pyzo.config.advanced.find_autoHide_timeout
        if self._autoHide.isChecked():
            if time.time() - self._timerAutoHide_t0 > timeout:  # seconds
                # Hide if editor has focus
                self._replaceKind.setCurrentIndex(0)  # set replace to "one"
                es = self.parent()  # editor stack
                editor = es.getCurrentEditor()
                if editor and editor.hasFocus():
                    self.hide()

    def hideMe(self):
        """Hide the find/replace widget."""
        self.hide()
        self._replaceKind.setCurrentIndex(0)  # set replace to "one"
        es = self.parent()  # editor stack
        # es._boxLayout.activate()
        editor = es.getCurrentEditor()
        if editor:
            editor.setFocus()

    def event(self, event):
        """Handle tab key and escape key. For the tab key we need to
        overload event instead of KeyPressEvent.
        """
        if isinstance(event, QtGui.QKeyEvent):
            if event.key() in (QtCore.Qt.Key.Key_Tab, QtCore.Qt.Key.Key_Backtab):
                event.accept()  # focusNextPrevChild is called by Qt
                return True
            elif event.key() == QtCore.Qt.Key.Key_Escape:
                self.hideMe()
                event.accept()
                return True
        # Otherwise ... handle in default manner
        return super().event(event)

    def handleReplacePossible(self, state):
        """Disable replacing when using regular expressions."""
        for w in [self._replaceText, self._replaceBut, self._replaceKind]:
            w.setEnabled(not state)

    def startFind(self, event=None):
        """Use this rather than show(). It will check if anything is
        selected in the current editor, and if so, will set that as the
        initial search string
        """
        # show
        self.show()
        self.autoHideTimerReset()

        # get needle
        editor = self.parent().getCurrentEditor()
        if editor:
            needle = editor.textCursor().selectedText().replace("\u2029", "\n")
            if needle:
                self._findText.setText(needle)
        # select the find-text
        self.selectFindText()

    def notifyPassBeginEnd(self):
        self.setStyleSheet("QFrame { background:#f00; }")
        self._timerBeginEnd.start(300)

    def resetAppearance(self):
        self.setStyleSheet("QFrame {}")

    def selectFindText(self):
        """Select the textcontrol for the find needle, and the text in it"""
        # select text
        self._findText.selectAll()
        # focus
        self._findText.setFocus()

    def findNext(self, event=None):
        self.find()
        # self._findText.setFocus()

    def findPrevious(self, event=None):
        self.find(False)
        # self._findText.setFocus()

    def findSelection(self, event=None):
        self.startFind()
        self.findNext()

    def findSelectionBw(self, event=None):
        self.startFind()
        self.findPrevious()

    def find(self, forward=True, wrapAround=True, editor=None):
        """The main find method. Returns True if a match was found."""

        # Reset timer
        self.autoHideTimerReset()

        # get editor
        if not editor:
            editor = self.parent().getCurrentEditor()
            if not editor:
                return

        # find flags
        flags = QtGui.QTextDocument.FindFlag(0)
        if self._caseCheck.isChecked():
            flags |= QtGui.QTextDocument.FindFlag.FindCaseSensitively
        if not forward:
            flags |= QtGui.QTextDocument.FindFlag.FindBackward
        # if self._wholeWord.isChecked():
        #    flags |= QtGui.QTextDocument.FindFlag.FindWholeWords

        # focus
        self.selectFindText()

        # get text to find
        needle = self._findText.text()

        QRE = QtCore.QRegularExpression
        PatternOption = QRE.PatternOption
        regexFlags = PatternOption.NoPatternOption
        if not self._caseCheck.isChecked():
            regexFlags |= PatternOption.CaseInsensitiveOption

        if self._regExp.isChecked():
            needle = QRE(needle, regexFlags)
        elif self._wholeWord.isChecked():
            # Use regexp, because the default behaviour does not find
            # whole words correctly, see issue #276
            # it should *not* find this in this_word
            needle = QRE(r"\b" + QRE.escape(needle) + r"\b", regexFlags)

        # establish start position
        cursor = editor.textCursor()
        result = editor.document().find(needle, cursor, flags)

        if not result.isNull():
            editor.setTextCursor(result)
        elif wrapAround:
            self.notifyPassBeginEnd()
            # Move cursor to start or end of document
            if forward:
                cursor.movePosition(cursor.MoveOperation.Start)
            else:
                cursor.movePosition(cursor.MoveOperation.End)
            # Try again
            result = editor.document().find(needle, cursor, flags)
            if not result.isNull():
                editor.setTextCursor(result)

        # done
        editor.setFocus()
        return not result.isNull()

    def replace(self, event=None):
        i = self._replaceKind.currentIndex()
        if i == 0:
            self.replaceOne(event)
        elif i == 1:
            self.replaceAll(event)
        elif i == 2:
            self.replaceInAllFiles(event)
        else:
            raise RuntimeError("Unexpected kind of replace {}".format(i))

    def replaceOne(self, event=None, wrapAround=True, editor=None):
        """If the currently selected text matches the find string,
        replaces that text. Then it finds and selects the next match.
        Returns True if a next match was found.
        """

        # get editor
        if not editor:
            editor = self.parent().getCurrentEditor()
            if not editor:
                return

        # Create a cursor to do the editing
        cursor = editor.textCursor()

        # matchCase
        matchCase = self._caseCheck.isChecked()

        # get text to find
        needle = self._findText.text()
        if not matchCase:
            needle = needle.lower()

        # get replacement
        replacement = self._replaceText.text()

        # get original text
        original = cursor.selectedText().replace("\u2029", "\n")
        if not original:
            original = ""
        if not matchCase:
            original = original.lower()

        # replace
        # TODO: < line does not work for regexp-search!
        if original and original == needle:
            cursor.insertText(replacement)

        # next!
        return self.find(wrapAround=wrapAround, editor=editor)

    def replaceAll(self, event=None, editor=None):
        # TODO: share a cursor between all replaces, in order to
        # make this one undo/redo-step

        # get editor
        if not editor:
            editor = self.parent().getCurrentEditor()
            if not editor:
                return

        # get current position
        originalPosition = editor.textCursor()

        # Move to beginning of text and replace all
        # Make this a single undo operation
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.movePosition(cursor.MoveOperation.Start)
            editor.setTextCursor(cursor)
            while self.replaceOne(wrapAround=False, editor=editor):
                pass
        finally:
            cursor.endEditBlock()

        # reset position
        editor.setTextCursor(originalPosition)

    def replaceInAllFiles(self, event=None):
        for editor in pyzo.editors:
            self.replaceAll(event, editor)


class FileTabWidget(CompactTabWidget):
    """FileTabWidget(parent)

    The tab widget that contains the editors and lists all open files.

    """

    # Signal to indicate that file tabs were added, updated or removed
    fileTabsChanged = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent, padding=(2, 1, 0, 4))

        # Init main file
        self._mainFile = ""

        # Init item history
        self._itemHistory = []

        #         # Create a corner widget
        #         but = QtWidgets.QToolButton()
        #         but.setIcon( pyzo.icons.cross )
        #         but.setIconSize(QtCore.QSize(16,16))
        #         but.clicked.connect(self.onClose)
        #         self.setCornerWidget(but)

        # Bind signal to update items and keep track of history
        self.currentChanged.connect(self.updateItems)
        self.currentChanged.connect(self.trackHistory)
        self.currentChanged.connect(self.setTitleInMainWindowWhenTabChanged)
        self.setTitleInMainWindowWhenTabChanged(-1)

    def setTitleInMainWindowWhenTabChanged(self, index):
        # Valid index?
        if not (0 <= index < self.count()):
            pyzo.main.setMainTitle()  # No open file

        currentItem = self.currentItem()
        if currentItem:
            currentItem.editor.setTitleInMainWindow()

    ## Item management

    def items(self):
        """Get the items in the tab widget. These are Item instances, and
        are in the order in which they are at the tab bar.
        """
        tabBar = self.tabBar()
        items = []
        for i in range(tabBar.count()):
            item = tabBar.tabData(i)
            if item is not None:
                items.append(item)
        return items

    def currentItem(self):
        """Get the item corresponding to the currently active tab."""
        i = self.currentIndex()
        return self.tabBar().tabData(i) if i >= 0 else None

    def getItemAt(self, i):
        return self.tabBar().tabData(i)

    def mainItem(self):
        """Get the item corresponding to the "main" file.

        Returns None if there is no main file.
        """
        for item in self.items():
            if item.id == self._mainFile:
                return item
        return None

    def tabRemoved(self, i):
        super().tabRemoved(i)
        self.trackHistory(None)

    def trackHistory(self, index):
        """Called when a tab is changed. Puts the current item on top of the history."""

        # remove closed editors from history
        existingItems = {self.getItemAt(i) for i in range(self.count())}
        self._itemHistory = [
            item for item in self._itemHistory if item in existingItems
        ]

        # add/move current editor to the start of the history
        hist = self._itemHistory
        curItem = self.currentItem()
        if curItem is not None and hist[:1] != [curItem]:
            try:
                hist.remove(curItem)
            except ValueError:
                pass
            hist.insert(0, curItem)

    def getItemHistory(self):
        return tuple(self._itemHistory)

    def setCurrentItem(self, item):
        """Set a FileItem instance to be the current.

        If the given item is not in the list, no action is taken.
        item can be an int, FileItem, or file name.
        """

        if isinstance(item, int):
            self.setCurrentIndex(item)

        elif isinstance(item, FileItem):
            items = self.items()
            for i in range(self.count()):
                if item is items[i]:
                    self.setCurrentIndex(i)
                    break

        elif isinstance(item, str):
            items = self.items()
            for i in range(self.count()):
                if item == items[i].filename:
                    self.setCurrentIndex(i)
                    break

        else:
            raise ValueError("item should be int, FileItem or file name.")

    ## Closing, adding and updating

    def onClose(self):
        """Request to close the current tab."""

        self.tabCloseRequested.emit(self.currentIndex())

    def removeTab(self, which):
        """Removes the specified tab. which can be an integer, an item, or an editor."""

        # Init
        items = self.items()
        theIndex = -1

        # Find index
        if isinstance(which, int) and 0 <= which < len(items):
            theIndex = which

        elif isinstance(which, FileItem):
            for i in range(self.count()):
                if items[i] is which:
                    theIndex = i
                    break

        elif isinstance(which, str):
            for i in range(self.count()):
                if items[i].filename == which:
                    theIndex = i
                    break

        elif hasattr(which, "_filename"):
            for i in range(self.count()):
                if items[i].filename == which._filename:
                    theIndex = i
                    break

        else:
            raise ValueError(
                "removeTab accepts a FileItem, integer, file name, or editor."
            )

        if theIndex >= 0:
            # Close tab
            super().removeTab(theIndex)

            # Delete editor
            items[theIndex].editor.destroy()
            gc.collect()

            self.fileTabsChanged.emit()

    def addItem(self, item, update=True):
        """Add item to the tab widget. Set update to False if you are
        calling this method many times in a row. Then use updateItemsFull()
        to update the tab widget.
        """

        # Add tab and widget
        i = self.addTab(item.editor, item.name)
        tabBut = EditorTabToolButton(self.tabBar())
        self.tabBar().setTabButton(i, QtWidgets.QTabBar.ButtonPosition.LeftSide, tabBut)

        # Keep informed about changes
        item.editor.somethingChanged.connect(self.updateItems)
        item.editor.blockCountChanged.connect(self.updateItems)
        item.editor.breakPointsChanged.connect(self.parent().updateBreakPoints)

        # Store the item at the tab
        self.tabBar().setTabData(i, item)

        # Emit the currentChanged again (already emitted on addTab), because
        # now the itemdata is actually set
        self.currentChanged.emit(self.currentIndex())

        # Update
        if update:
            self.updateItems()

    def updateItemsFull(self):
        """Update the appearance of the items and also updates names and
        re-aligns the items.
        """
        self.updateItems()
        self.tabBar().alignTabs()

    def updateItems(self):
        """Update the appearance of the items."""

        # Get items and tab bar
        items = self.items()
        tabBar = self.tabBar()

        # Check whether we have name clashes, which we can try to resolve
        namecounts = {}
        for i, item in enumerate(items):
            if item is None:
                continue
            namecounts.setdefault(item.name, []).append(item)

        for i, item in enumerate(items):
            if item is None:
                continue

            # Get display name
            items_with_this_name = namecounts[item.name]
            if len(items_with_this_name) <= 1:
                display_name = item.name
            else:
                filenames = [j.filename for j in items_with_this_name]
                try:
                    display_name = get_shortest_unique_filename(
                        item.filename, filenames
                    )
                except Exception as err:
                    # Catch this, just in case ...
                    print("could not get unique name for:\n{!r}".format(filenames))
                    print(err)
                    display_name = item.name

            tabBar.setTabText(i, display_name)

            # Update name and tooltip
            if item.dirty:
                tabBar.setTabToolTip(i, item.filename + " [modified]")
            else:
                tabBar.setTabToolTip(i, item.filename)

            # Determine text color. Is main file? Is current?
            if self._mainFile == item.id:
                color = "#0cf" if pyzo.darkQt else "#008"
            elif i == self.currentIndex():
                color = "#fff" if pyzo.darkQt else "#000"
            else:
                color = "#ddd" if pyzo.darkQt else "#444"
            tabBar.setTabTextColor(i, QtGui.QColor(color))

            # Get number of blocks
            nBlocks = item.editor.blockCount()
            if nBlocks == 1 and not item.editor.toPlainText():
                nBlocks = 0

            # Update appearance of icon
            but = tabBar.tabButton(i, QtWidgets.QTabBar.ButtonPosition.LeftSide)
            but.updateIcon(item.dirty, self._mainFile == item.id, item.pinned, nBlocks)

        self.fileTabsChanged.emit()

    def keyPressEvent(self, event):
        # prevent the QTabBar widget from consuming keypress events
        event.ignore()


class EditorTabs(QtWidgets.QWidget):
    """The EditorTabs instance manages the open files and corresponding
    editors. It does the saving loading etc.
    """

    # Signal to indicate that a breakpoint has changed, emits dict
    breakPointsChanged = QtCore.Signal(object)

    # Signal to notify that a different file was selected
    currentChanged = QtCore.Signal()

    # Signal to notify that the parser has parsed the text (emit by parser)
    parserDone = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent)

        # keep a booking of opened directories
        self._lastpath = ""

        # keep track of all breakpoints
        self._breakPoints = {}

        # create tab widget
        self._tabs = FileTabWidget(self)
        self._tabs.tabCloseRequested.connect(self.closeFile)
        self._tabs.currentChanged.connect(self.onCurrentChanged)

        # Double clicking a tab saves the file, clicking on the bar opens a new file
        self._tabs.tabBar().tabDoubleClicked.connect(self.saveFile)
        self._tabs.tabBar().barDoubleClicked.connect(self.newFile)

        # Create find/replace widget
        self._findReplace = FindReplaceWidget(self)

        # create box layout control and add widgets
        self._boxLayout = QtWidgets.QVBoxLayout(self)
        self._boxLayout.addWidget(self._tabs, 1)
        self._boxLayout.addWidget(self._findReplace, 0)
        # spacing of widgets
        self._boxLayout.setSpacing(0)
        # set margins
        margin = pyzo.config.view.widgetMargin
        self._boxLayout.setContentsMargins(margin, margin, margin, margin)
        # apply
        self.setLayout(self._boxLayout)

        # self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips,True)

        # accept drops
        self.setAcceptDrops(True)

        # restore state (call later so that the menu module can bind to the
        # currentChanged signal first, in order to set tab/indentation
        # checkmarks appropriately)

        # self.restoreEditorState should be called from outside after the paintNow call
        # otherwise the horizontal scrollbar would be set for a too small widget size

    @property
    def _fileDialogOptions(self):
        options = QtWidgets.QFileDialog.Option(0)
        if not pyzo.config.advanced.useNativeFileDialogs:
            options |= QtWidgets.QFileDialog.Option.DontUseNativeDialog
        return options

    def addContextMenu(self):
        """Adds a context menu to the tab bar"""

        from pyzo.core.menu import EditorTabContextMenu

        self._menu = EditorTabContextMenu(self, "EditorTabMenu")
        self._tabs.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self._tabs.customContextMenuRequested.connect(self.contextMenuTriggered)

    def contextMenuTriggered(self, p):
        """Called when context menu is clicked"""

        # Get index of current tab
        index = self._tabs.tabBar().tabAt(p)
        self._menu.setIndex(index)

        # Show menu if item is available
        if index >= 0:
            p = self._tabs.tabBar().tabRect(index).bottomLeft()
            self._menu.popup(self._tabs.tabBar().mapToGlobal(p))

    def onCurrentChanged(self):
        self.currentChanged.emit()
        # Update status bar
        editor = pyzo.editors.getCurrentEditor()
        sb = pyzo.main.statusBar()
        sb.updateCursorInfo(editor)

    def getCurrentEditor(self):
        """Get the currently active editor."""
        item = self._tabs.currentItem()
        if item:
            return item.editor
        else:
            return None

    def getMainEditor(self):
        """Get the editor that represents the main file, or None if
        there is no main file.
        """
        item = self._tabs.mainItem()
        if item:
            return item.editor
        else:
            return None

    def __iter__(self):
        tmp = [item.editor for item in self._tabs.items()]
        return tmp.__iter__()

    def updateBreakPoints(self, editor=None):
        # Get list of editors to update keypoints for
        if editor is None:
            editors = self
            self._breakPoints = {}  # Full reset
        else:
            editors = [editor]

        # Update our keypoints dict
        for editor in editors:
            fname = editor._filename or editor._name
            if not fname:
                continue
            linenumbers = editor.breakPoints()
            if linenumbers:
                self._breakPoints[fname] = linenumbers
            else:
                self._breakPoints.pop(fname, None)

        # Emit signal so shells can update the kernel
        self.breakPointsChanged.emit(self._breakPoints)

    def setDebugLineIndicators(self, *filename_linenr):
        """Set the debug line indicator. There is one indicator
        global to pyzo, corresponding to the last shell for which we
        received the indicator.
        """
        if len(filename_linenr) and filename_linenr[0] is None:
            filename_linenr = []

        # Normalize case
        filename_linenr = [(os.path.normcase(i[0]), int(i[1])) for i in filename_linenr]

        for item in self._tabs.items():
            # Prepare
            editor = item._editor
            fname = editor._filename or editor._name
            fname = os.path.normcase(fname)
            # Reset
            editor.setDebugLineIndicator(None)
            # Set
            for filename, linenr in filename_linenr:
                if fname == filename:
                    active = (filename, linenr) == filename_linenr[-1]
                    editor.setDebugLineIndicator(linenr, active)

    ## Loading and saving files

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Drop files in the list."""
        for qurl in event.mimeData().urls():
            path = str(qurl.toLocalFile())
            if os.path.isfile(path):
                self.loadFile(path)
            elif os.path.isdir(path):
                self.loadDir(path)
            else:
                pass

    def newFile(self):
        """Create a new (unsaved) file."""

        # create editor
        editor = createEditor(self, None)
        editor.document().setModified(False)  # Start out as OK
        # add to list
        item = FileItem(editor)
        self._tabs.addItem(item)
        self._tabs.setCurrentItem(item)
        # set focus to new file
        editor.setFocus()

        return item

    def openFile(self):
        """Create a dialog for the user to select a file."""

        # determine start dir
        editor = self.getCurrentEditor()
        if editor and editor._filename:
            startdir = os.path.split(editor._filename)[0]
        else:
            startdir = self._lastpath
        if (not startdir) or (not os.path.isdir(startdir)):
            startdir = ""

        # show dialog
        msg = translate("editorTabs", "Select one or more files to open")
        filter = "Python (*.py *.pyw);;"
        filter += "Pyrex (*.pyi *.pyx *.pxd);;"
        filter += "C (*.c *.h *.cpp *.c++);;"
        # filter += "Py+Cy+C (*.py *.pyw *.pyi *.pyx *.pxd *.c *.h *.cpp);;"
        filter += "All (*)"
        if True:
            filenames, selectedFilter = QtWidgets.QFileDialog.getOpenFileNames(
                self, msg, startdir, filter, options=self._fileDialogOptions
            )
        else:
            # Example how to preselect files, can be used when the users
            # opens a file in a project to select all files currently not
            # loaded.
            d = QtWidgets.QFileDialog(
                self, msg, startdir, filter, options=self._fileDialogOptions
            )
            d.setFileMode(d.ExistingFiles)
            d.selectFile('"codeparser.py" "editorStack.py"')
            d.exec()
            if d.result():
                filenames = d.selectedFiles()
            else:
                filenames = []

        # were some selected?
        if not filenames:
            return

        # load
        for filename in filenames:
            self.loadFile(filename)

    def openDir(self):
        """Create a dialog for the user to select a directory."""

        # determine start dir
        editor = self.getCurrentEditor()
        if editor and editor._filename:
            startdir = os.path.split(editor._filename)[0]
        else:
            startdir = self._lastpath
        if not os.path.isdir(startdir):
            startdir = ""

        # show dialog
        msg = "Select a directory to open"
        dirname = QtWidgets.QFileDialog.getExistingDirectory(
            self, msg, startdir, options=self._fileDialogOptions
        )

        # was a dir selected?
        if not dirname:
            return

        # load
        self.loadDir(dirname)

    def _findEditorOfFile(self, filepath):
        """returns the editor of file 'filepath' or None if not opened (yet)

        filepath can also be '<tmp 1>' etc.
        """

        def getFileStats(fp):
            if fp and not fp.startswith("<"):
                try:
                    return os.stat(fp)
                except (OSError, ValueError):
                    pass
            return None

        s1 = getFileStats(filepath)
        for item in self._tabs.items():
            if item.id == filepath:
                # id gets _filename or _name for temp files
                return item

            if not s1:
                continue

            s2 = getFileStats(item.filename)
            if s2 and os.path.samestat(s1, s2):
                # both filepaths refer to the same file (like os.path.samefile(...))

                # mapped WebDAV drives do not support os.path.samefile and os.path.samestat
                #   see https://github.com/python/cpython/issues/74665
                if sys.platform == "win32" and (s1.st_dev, s1.st_ino) == (0, 0):
                    # the file is probably located in a mapped WebDAV drive
                    if os.path.normcase(filepath) != os.path.normcase(item.filename):
                        # probably not the same file, even if os.path.samefile says so
                        continue

                # file is already open, but with a different filepath
                # this could be, for example:
                # - a symbolic link to the other file
                # - or r"\\localhost\c$\temp\abc.py" and r"C:\temp\abc.py"
                return item
        return None  # file is not opened in any of the editor tabs

    def loadFile(self, filename, updateTabs=True, ignoreFail=False):
        """Load the specified file.
        On success returns the item of the file, also if it was
        already open.
        """

        # Note that by giving the name of a tempfile, we can select that
        # temp file.

        # normalize path
        if filename[0] != "<":
            filename = normalizePath(filename)
        if not filename:
            return None

        item = self._findEditorOfFile(filename)
        if item:
            self._tabs.setCurrentItem(item)
            if filename.lower() != item.filename.lower() and item.filename != "":
                # only print the message if something unexpected happened
                if filename == item.filename:
                    print("File already open: '{}'".format(filename))
                else:
                    print(
                        "File '{}' already open as '{}'".format(filename, item.filename)
                    )
            return item

        # create editor
        try:
            editor = createEditor(self, filename)
        except Exception as err:
            # Notify in logger
            print("Error loading file: ", err)
            # Make sure the user knows
            if not ignoreFail:
                m = QtWidgets.QMessageBox(self)
                m.setWindowTitle("Error loading file")
                m.setText(str(err))
                m.setIcon(m.Icon.Warning)
                m.exec()
            return None

        # create list item
        item = FileItem(editor)
        self._tabs.addItem(item, updateTabs)
        if updateTabs:
            self._tabs.setCurrentItem(item)

        # store the path
        self._lastpath = os.path.dirname(item.filename)

        return item

    def loadDir(self, path):
        """Create a project with the dir's name and add all files
        contained in the directory to it.
        extensions is a komma separated list of extenstions of files
        to accept...
        """

        # if the path does not exist, stop
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            print("ERROR loading dir: the specified directory does not exist!")
            return

        # get extensions
        extensions = pyzo.config.advanced.fileExtensionsToLoadFromDir
        extensions = extensions.replace(",", " ").replace(";", " ")
        extensions = ["." + a.lstrip(".").strip() for a in extensions.split(" ")]

        # init item
        item = None

        # open all qualified files...
        self._tabs.setUpdatesEnabled(False)
        try:
            filelist = os.listdir(path)
            for filename in filelist:
                filename = os.path.join(path, filename)
                ext = os.path.splitext(filename)[1]
                if str(ext) in extensions:
                    item = self.loadFile(filename, False)
        finally:
            self._tabs.setUpdatesEnabled(True)
            self._tabs.updateItems()

        # return lastopened item
        return item

    def reloadFile(self, editor=None):
        if editor is None:
            editor = self.getCurrentEditor()
            if editor is None:
                return
        if editor.name.startswith("<tmp"):
            return

        if editor.document().isModified():
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("Reload file with unsaved changes?")
            dlg.setText(
                'Do you want to reload file\n"{}"\nand lose unsaved changes?'.format(
                    editor.filename
                )
            )
            btnReload = dlg.addButton(
                "Reload", QtWidgets.QMessageBox.ButtonRole.AcceptRole
            )
            btnKeep = dlg.addButton(
                "Keep this version", QtWidgets.QMessageBox.ButtonRole.RejectRole
            )
            dlg.setDefaultButton(btnKeep)
            dlg.exec()
            if dlg.clickedButton() != btnReload:
                return  # cancel reloading

        editor.reload()
        self._tabs.updateItems()

    def saveFileAs(self, editor=None, saveCopyAs=False):
        """Create a dialog for the user to select a file.
        If saveCopyAs is True, only a backup of the editor's contents will be saved.
        returns: True if succesfull, False if fails
        """

        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
        if editor is None:
            return False

        # get startdir
        if editor._filename:
            startdir, startfilename = os.path.split(editor._filename)
        else:
            startdir, startfilename = self._lastpath, None
            # Try the file browser to suggest a path
            fileBrowser = pyzo.toolManager.getTool("pyzofilebrowser")
            if fileBrowser:
                startdir = fileBrowser.getDefaultSavePath()
            if not startdir:
                startdir = os.path.expanduser("~")

        if not os.path.isdir(startdir):
            startdir = ""

        # show dialog
        msg = translate("editorTabs", "Select the file to save to")
        filter = "Python (*.py *.pyw);;"
        filter += "Pyrex (*.pyi *.pyx *.pxd);;"
        filter += "C (*.c *.h *.cpp);;"
        # filter += "Py+Cy+C (*.py *.pyw *.pyi *.pyx *.pxd *.c *.h *.cpp);;"
        filter += "All (*.*)"
        if startfilename is None:
            startfilepath = startdir
        else:
            startfilepath = os.path.join(startdir, startfilename)
        filename, selectedFilter = QtWidgets.QFileDialog.getSaveFileName(
            self, msg, startfilepath, filter, options=self._fileDialogOptions
        )

        # give python extension if it has no extension
        head, tail = os.path.split(filename)
        if tail and "." not in tail:
            filename += ".py"

        # proceed or cancel
        if filename:
            if saveCopyAs:
                return self.saveFileCopy(editor, filename)
            return self.saveFile(editor, filename)
        else:
            return False  # Cancel was pressed

    def saveFile(self, editor=None, filename=None):
        """Save the file.
        returns: True if succesfull, False if fails
        """

        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
        elif isinstance(editor, int):
            index = editor
            editor = None
            if index >= 0:
                item = self._tabs.items()[index]
                editor = item.editor
        if editor is None:
            return False

        # get filename
        if filename is None:
            filename = editor._filename
        if not filename:
            return self.saveFileAs(editor)

        # let the editor do the low level stuff...
        try:
            editor.save(filename)
        except Exception as err:
            # Notify in logger
            print("Error saving file:", err)
            # Make sure the user knows
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle("Error saving file")
            m.setText(str(err))
            m.setIcon(m.Icon.Warning)
            m.exec()
            # Return now
            return False

        # get actual normalized filename
        filename = editor._filename

        self._tabs.updateItems()

        # todo: this is where we once detected whether the file being saved was a style file.

        return True

    def saveFileCopy(self, editor, filename):
        """Save the contents of the editor to a file, as a backup.
        returns: True if succesfull, False if fails
        """

        # let the editor do the low level stuff...
        try:
            editor.saveCopy(filename)
        except Exception as err:
            # Notify in logger
            print("Error saving file:", err)
            # Make sure the user knows
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle("Error saving file")
            m.setText(str(err))
            m.setIcon(m.Icon.Warning)
            m.exec()
            # Return now
            return False

        return True

    def saveAllFiles(self):
        """Save all files"""
        for editor in self:
            self.saveFile(editor)

    ## Closing files / closing down

    def _get_action_texts(self):
        options = translate("editor", "Close, Discard, Cancel, Save").split(",")
        options = [i.strip() for i in options]
        try:
            close_txt, discard_txt, cancel_txt, save_txt = options
        except Exception:
            print("error in translation for close, discard, cancel, save.")
            close_txt, discard_txt, cancel_txt, save_txt = (
                "Close",
                "Discard",
                "Cancel",
                "Save",
            )
        return close_txt, discard_txt, cancel_txt, save_txt

    def askToSaveFileIfDirty(self, editor):
        """If the given file is not saved, pop up a dialog
        where the user can save the file

        Returns 1 if file need not be saved.
        Returns 2 if file was saved.
        Returns 3 if user discarded changes.
        Returns 0 if cancelled.
        """

        # should we ask to save the file?
        if editor.document().isModified():
            # Ask user what to do
            close_txt, discard_txt, cancel_txt, save_txt = self._get_action_texts()
            result = simpleDialog(
                editor,
                translate("editor", "Closing"),
                translate("editor", "Save modified file?"),
                [discard_txt, cancel_txt, save_txt],
                save_txt,
            )

            # Get result and act
            if result == save_txt:
                return 2 if self.saveFile(editor) else 0
            elif result == discard_txt:
                return 3
            else:  # cancel
                return 0

        return 1

    def closeFile(self, editor=None):
        """Close the selected (or current) editor.

        Returns same result as askToSaveFileIfDirty()
        """

        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
            item = self._tabs.currentItem()
        elif isinstance(editor, int):
            index = editor
            editor, item = None, None
            if index >= 0:
                item = self._tabs.items()[index]
                editor = item.editor
        else:
            item = None
            for i in self._tabs.items():
                if i.editor is editor:
                    item = i
        if editor is None or item is None:
            return

        # Ask if dirty
        result = self.askToSaveFileIfDirty(editor)

        # Ask if closing pinned file
        close_txt, discard_txt, cancel_txt, save_txt = self._get_action_texts()
        if result and item.pinned:
            result = simpleDialog(
                editor,
                translate("editor", "Closing pinned"),
                translate("editor", "Are you sure you want to close this pinned file?"),
                [close_txt, cancel_txt],
                cancel_txt,
            )
            result = result == close_txt

        # ok, close...
        if result:
            if editor._name.startswith("<tmp"):
                # Temp file, try to find its index
                for i in range(len(self._tabs.items())):
                    if self._tabs.getItemAt(i).editor is editor:
                        self._tabs.removeTab(i)
                        break
            else:
                self._tabs.removeTab(editor)
            editor.close()  # close event of the editor will do some clean-up

        # Clear any breakpoints that it may have had
        self.updateBreakPoints()

        return result

    def closeAllFiles(self):
        """Close all files"""
        for editor in self:
            self.closeFile(editor)

    def saveEditorState(self):
        """Save the editor's state configuration."""
        fr = self._findReplace
        pyzo.config.state.find_matchCase = fr._caseCheck.isChecked()
        pyzo.config.state.find_regExp = fr._regExp.isChecked()
        pyzo.config.state.find_wholeWord = fr._wholeWord.isChecked()
        pyzo.config.state.find_autoHide = fr._autoHide.isChecked()
        pyzo.config.state.find_show = fr.isVisible()
        #
        pyzo.config.state.editorState2 = self._getCurrentOpenFilesAsSsdfList()

    def restoreEditorState(self):
        """Restore the editor's state configuration."""

        # Restore opened editors
        if pyzo.config.state.editorState2:
            ok = self._setCurrentOpenFilesAsSsdfList(pyzo.config.state.editorState2)
            if not ok:
                self.newFile()
        else:
            self.newFile()
        self._tabs.updateItems()  # without this, a single restored editor will not have
        # correct PINNED/MAINFILE symbols

        # The find/replace state is set in the corresponding class during init

    def _getCurrentOpenFilesAsSsdfList(self):
        """Get the state as it currently is as an ssdf list.

        The state entails all open files and their structure in the
        projects. The being collapsed of projects and their main files.
        The position of the cursor in the editors.
        """

        # Init
        state = []

        # Get items
        for item in self._tabs.items():
            # Get editor
            ed = item.editor
            if not ed._filename:
                continue

            # Init info
            info = []
            # Add filename, line number, and scroll distance
            info.append(ed._filename)
            info.append(int(ed.textCursor().position()))
            info.append(int(ed.verticalScrollBar().value()))
            # Add whether pinned or main file
            if item.pinned:
                info.append("pinned")
            if item.id == self._tabs._mainFile:
                info.append("main")

            # Add to state
            state.append(tuple(info))

        # assert self._tabs.count() == len(self._tabs._itemHistory)
        for item in self._tabs._itemHistory[::-1]:
            # assert isinstance(item, FileItem)
            ed = item._editor
            if ed._filename:
                state.append((ed._filename, "hist"))

        # Done
        return state

    def _setCurrentOpenFilesAsSsdfList(self, state):
        """Set the state of the editor in terms of opened files.

        The input should be a list object as returned by
        ._getCurrentOpenFilesAsSsdfList().
        """

        # Init dict
        fileItems = {}

        # Process items
        for item in state:
            fname = item[0]
            if os.path.exists(fname):
                if item[1] == "hist":
                    # select item (to make the history right)
                    if fname in fileItems:
                        self._tabs.setCurrentItem(fileItems[fname])
                elif fname:
                    # a file item, create editor-item and store
                    itm = self.loadFile(fname, ignoreFail=True)
                    # set position
                    if itm:
                        fileItems[fname] = itm
                        try:
                            ed = itm.editor
                            cursor = ed.textCursor()
                            cursor.setPosition(int(item[1]))
                            ed.setTextCursor(cursor)
                            # set scrolling
                            ed.verticalScrollBar().setValue(int(item[2]))
                            # ed.centerCursor() #TODO: this does not work properly yet
                            # set main and/or pinned?
                            if "main" in item:
                                self._tabs._mainFile = itm.id
                            if "pinned" in item:
                                itm._pinned = True
                        except Exception as err:
                            print("Could not set position for", fname, err)

        return len(fileItems) != 0

    def closeAll(self):
        """Close all files

        Well technically, we don't really close them, so that they
        are all stil there when the user presses cancel.
        Returns False if the user pressed cancel when asked for
        saving an unsaved file.
        """

        # try closing all editors.
        for editor in self:
            result = self.askToSaveFileIfDirty(editor)
            if not result:
                return False

        # we're good to go closing
        return True

    def processKeyPressFromMainWindow(self, event):
        consumed = False
        if HistList.processKeyPress(event):
            histList = HistList(self, self._tabs, event)
            if histList.valid:
                histList.exec()
            ed = self.getCurrentEditor()
            if ed:
                ed.setFocus()
            consumed = True
        return consumed


class HistList(QtWidgets.QDialog):
    def __init__(self, parent, tabs, startEvent):
        super().__init__(parent)

        lw = QtWidgets.QListWidget()
        self._lw = lw
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(lw)

        self._margin = m = 0
        self.setContentsMargins(m, m, m, m)
        layout.setContentsMargins(m, m, m, m)

        self._tabs = tabs
        self._entries = None
        self.setWindowTitle("Editor tab history")
        self.valid = True

        self._entries = self._tabs.getItemHistory()
        if len(self._entries) <= 1:
            self.valid = False
            return

        lw = self._lw
        lw.clear()
        for item in self._entries:
            flags = []
            if item.dirty:
                flags.append("MOD.")
            if item.pinned:
                flags.append("PIN.")
            if item.id == self._tabs._mainFile:
                flags.append("MAINF.")
            if flags:
                label = "[{}] {}".format(", ".join(flags), item.id)
            else:
                label = item.id

            lw.addItem(QtWidgets.QListWidgetItem(label))

        w = (
            lw.sizeHintForColumn(0)
            + lw.frameWidth() * 2
            + lw.verticalScrollBar().sizeHint().width()
        )
        h = (
            lw.sizeHintForRow(0) * lw.count()
            + 2 * lw.frameWidth()
            + lw.horizontalScrollBar().sizeHint().height()
        )
        w = max(w, 400)
        self.resize(w, h)
        self.keyPressEvent(startEvent)

    def _finishSelection(self):
        lw = self._lw
        if self._entries is not None:
            ind = lw.currentRow()
            if 0 <= ind < len(self._entries):
                self._tabs.setCurrentItem(self._entries[ind])
        self._entries = None
        self.close()

    @staticmethod
    def processKeyPress(event):
        key = event.key()
        modifiers = event.modifiers()
        tab_pressed = key == QtCore.Qt.Key.Key_Tab
        backtab_pressed = key == QtCore.Qt.Key.Key_Backtab
        KM = QtCore.Qt.KeyboardModifier
        control_like_modifier = KM.AltModifier if ismacos else KM.ControlModifier
        fwd = modifiers == control_like_modifier
        bwd = modifiers == control_like_modifier | KM.ShiftModifier
        if (tab_pressed and fwd) or (backtab_pressed and bwd):
            k = -1 if bwd else 1
            return k
        return None

    def keyPressEvent(self, event):
        k = self.processKeyPress(event)
        if k is not None:
            lw = self._lw
            row = lw.currentRow()
            if row == -1:
                row = 0
            lw.setCurrentRow((row + k) % lw.count())
            return  # consume event
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        KM = QtCore.Qt.KeyboardModifier
        modifiers = event.modifiers()
        control_like_modifier = KM.AltModifier if ismacos else KM.ControlModifier
        if not (modifiers & control_like_modifier):
            self._finishSelection()
            return  # consume event
        super().keyReleaseEvent(event)
