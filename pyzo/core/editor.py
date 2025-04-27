"""Module editor

Defines the PyzoEditor class which is used to edit documents.
This module/class also implements all the relatively low level
file loading/saving /reloading stuff.

"""

import os
import sys
import re
import codecs

from pyzo.qt import QtCore, QtGui, QtWidgets

from pyzo.codeeditor import Manager
from pyzo.core.menu import EditorContextMenu
from pyzo.core.baseTextCtrl import BaseTextCtrl, normalizePath
from pyzo.core.pyzoLogging import print
import pyzo


"""
Handling of encodings and byte-order-marks
==========================================

When loading text from a file, the encoding is determined as follows, similar to PEP 263:
    1) If there is a known BOM, the encoding is defined by the BOM.
    2) Otherwise, if there is a magic comment with a known encoding name,
       then this encoding name will be used.  e.g.: "# -*- coding: latin-1 -*-"
    3) Otherwise utf-8 will be used.

    If decoding fails, other encoding candidates from 2) or 3) will be tried as well.
    If decoding still fails, ascii with backslashreplace will be used, a warning will
    be displayed, and the document will be marked as modified after loading.

And when saving text to a file:
    1) If there is a magic comment with a known encoding name in the unsaved text,
       that encoding will be used for saving the file.
    2) Otherwise utf-8 encoding will be used.

    If there was a BOM_UTF8 present when originally loading the file, that BOM will
    only be written to the file if the encoding for saving is utf-8 or utf-8-sig.
    Other BOMs, such as BOM_UTF16_LE, will always be discarded when writing a file.

"""


def getEncodingFromMagic(text):
    """reads the encoding name from the file header
    according to https://peps.python.org/pep-0263/
    returns 'utf-8' if no or an unknown encoding name was found
    """
    encoding = "utf-8"
    for line in text.splitlines()[:2]:
        mo = re.match(r"^[ \t\f]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+)", line)
        if mo:
            try:
                encoding = codecs.lookup(mo[1]).name
            except LookupError:
                pass
            break
        if line.split("#", 1)[0].lstrip():
            break  # line is not just whitespace and/or comment
    return encoding


def getEncodingFromBom(databytes):
    """detects the byte order mark and returns the encoding name or None"""
    bom2enc = {
        codecs.BOM_UTF8: "utf-8-sig",
        codecs.BOM_UTF16_BE: "utf-16-be",
        codecs.BOM_UTF16_LE: "utf-16-le",
        codecs.BOM_UTF32_BE: "utf-32-be",
        codecs.BOM_UTF32_LE: "utf-32-le",
    }
    for bom, encoding in bom2enc.items():
        if databytes[:4].startswith(bom):
            break
    else:
        encoding = None
    return encoding


# Set default line ending (if not set)
if not pyzo.config.settings.defaultLineEndings:
    if sys.platform.startswith("win"):
        pyzo.config.settings.defaultLineEndings = "CRLF"
    else:
        pyzo.config.settings.defaultLineEndings = "LF"


def determineLineEnding(text):
    """Get the line ending style used in the text.
    \n, \r, \r\n,
    The EOLmode is determined by counting the occurrences of each
    line ending...
    """
    text = text[:32768]  # Limit search for large files

    # test line ending by counting the occurrence of each
    c_win = text.count("\r\n")
    c_mac = text.count("\r") - c_win
    c_lin = text.count("\n") - c_win
    # set the appropriate style
    if c_win > c_mac and c_win > c_lin:
        mode = "\r\n"
    elif c_mac > c_win and c_mac > c_lin:
        mode = "\r"
    else:
        mode = "\n"

    # return
    return mode


def determineIndentation(text):
    return determineIndentationAndTrailingWS(text)[0]


def determineIndentationAndTrailingWS(text):
    """Get the indentation used in this document and whether there is
    any trailing whitespace.
    The text is analyzed to find the most used indentations.
    The result is -1 if tab indents are most common.
    A positive result means spaces are used; the amount
    signifies the amount of spaces per indentation.
    0 is returned if the indentation could not be determined.
    The second return value is the number of lines with trailing ws.
    """

    text = text[:32768]  # Limit search for large files

    # create dictionary of indents, -1 means a tab
    indents = {}
    indents[-1] = 0
    trailing = 0

    lines = text.splitlines()
    lines.insert(0, "")  # so the lines start at 1
    for i, line in enumerate(lines):
        # remove indentation
        lineA = line.lstrip()
        lineB = line.rstrip()
        lineC = lineA.rstrip()
        indent = len(line) - len(lineA)
        if len(lineB) < len(line):
            trailing += 1

        line = lineC
        if line.startswith("#"):
            continue
        else:
            # remove everything after the #
            line = line.split("#", 1)[0].rstrip()
        if not line:
            # continue of no line left
            continue

        # a colon means there will be an indent
        # check the next line (or the one thereafter)
        # and calculate the indentation difference with THIS line.
        if line.endswith(":"):
            if len(lines) > i + 2:
                line2 = lines[i + 1]
                tmp = line2.lstrip()
                if not tmp:
                    line2 = lines[i + 2]
                    tmp = line2.lstrip()
                if tmp:
                    ind2 = len(line2) - len(tmp)
                    ind3 = ind2 - indent
                    if line2.startswith("\t"):
                        indents[-1] += 1
                    elif ind3 > 0:
                        if ind3 not in indents:
                            indents[ind3] = 1
                        indents[ind3] += 1

    # find which was the most common tab width.
    indent, maxvotes = 0, 0
    for nspaces in indents:
        if indents[nspaces] > maxvotes:
            indent, maxvotes = nspaces, indents[nspaces]
    # print("found tabwidth", indent)
    return indent, trailing


# To give each new file a unique name
newFileCounter = 0


def createEditor(parent, filename=None):
    """Tries to load the file given by the filename and
    if succesful, creates an editor instance to put it in,
    which is returned.
    If filename is None, an new/unsaved/temp file is created.
    """

    if filename is None:
        # Increase counter
        global newFileCounter
        newFileCounter += 1

        # Create editor
        editor = PyzoEditor(parent)
        editor.document().setModified(True)
        editor.removeTrailingWS = True

        # Set name
        editor._name = "<tmp {}>".format(newFileCounter)

    else:
        # check and normalize
        if not os.path.isfile(filename):
            raise IOError("File does not exist '{}'.".format(filename))

        # create editor
        editor = PyzoEditor(parent)

        text = editor._loadTextFromFile(filename)

        # store name and filename
        editor._filename = filename
        editor._name = os.path.split(filename)[1]

    if editor._filename:
        editor._modifyTime = os.path.getmtime(editor._filename)

    # Set parser
    if editor._filename:
        ext = os.path.splitext(editor._filename)[1]
        parser = Manager.suggestParser(ext, text)
        editor.setParser(parser)
    else:
        # todo: rename style -> parser
        editor.setParser(pyzo.config.settings.defaultStyle)

    # return
    return editor


class PyzoEditor(BaseTextCtrl):
    # called when dirty changed or filename changed, etc
    somethingChanged = QtCore.Signal()

    def __repr__(self):
        return "<{} - {}, {}>".format(self.__class__.__qualname__, id(self), self.name)

    def __init__(self, parent, **kwds):
        super().__init__(parent, showLineNumbers=True, **kwds)

        # Init filename and name
        self._filename = ""
        self._name = "<TMP>"

        # View settings
        # TODO: self.setViewWrapSymbols(view.showWrapSymbols)
        self.setShowLineEndings(pyzo.config.view.showLineEndings)
        self.setShowIndentationGuides(pyzo.config.view.showIndentationGuides)
        #
        self.setWrap(bool(pyzo.config.view.wrap))
        self.setHighlightCurrentLine(pyzo.config.view.highlightCurrentLine)
        self.setLongLineIndicatorPosition(pyzo.config.view.edgeColumn)
        # TODO: self.setFolding( int(view.codeFolding)*5 )
        # bracematch is set in baseTextCtrl, since it also applies to shells
        # dito for zoom and tabWidth

        # Set line endings to default
        self.lineEndings = pyzo.config.settings.defaultLineEndings

        # Do not use utf-8-sig byte order mark as a default
        self.useBom = False

        # Modification time to test file change
        self._modifyTime = 0
        self._binaryDataFromFile = None  # the binary data as it was loaded or saved

        self.modificationChanged.connect(self._onModificationChanged)

        # To see whether the doc has changed to update the parser.
        self.textChanged.connect(self._onModified)

        # This timer is used to hide the marker that shows which code is executed
        self._showRunCursorTimer = QtCore.QTimer()

        # Add context menu
        self._menu = EditorContextMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._onContextMenu)

        # Update status bar
        self.cursorPositionChanged.connect(self._updateStatusBar)

    def closeEvent(self, event):
        # free some memory to mitigate memory leak losses
        del self._binaryDataFromFile

    ## Properties

    @property
    def name(self):
        return self._name

    @property
    def filename(self):
        return self._filename

    @property
    def lineEndings(self):
        """Line-endings style of this file.

        Setter accepts machine-readable (e.g. '\r') and human-readable (e.g. 'CR') input
        """
        return self._lineEndings

    @lineEndings.setter
    def lineEndings(self, value):
        if value in ("\r", "\n", "\r\n"):
            self._lineEndings = value
            return
        try:
            self._lineEndings = {"CR": "\r", "LF": "\n", "CRLF": "\r\n"}[value]
        except KeyError:
            raise ValueError("Invalid line endings style {!r}".format(value))

    @property
    def lineEndingsHumanReadable(self):
        """Current line-endings style, human readable (e.g. 'CR')"""
        return {"\r": "CR", "\n": "LF", "\r\n": "CRLF"}[self.lineEndings]

    ##

    def _loadTextFromFile(self, filepath):
        with open(filepath, "rb") as f:
            bb = f.read()

        # determine encoding from byte order mark and PEP 263 magic comment
        encBom = getEncodingFromBom(bb)
        encMagic = getEncodingFromMagic(bb[:200].decode("ascii", "replace"))

        self.useBom = encBom == "utf-8-sig" and encMagic.startswith("utf-8")

        encMagic2 = encMagic
        if encMagic2 == "utf-8":
            encMagic2 = "utf-8-sig"  # utf-8-sig also works for utf-8 encoded text

        encodingsToTry = []
        if encBom:
            encodingsToTry.append(encBom)
        if encMagic2 not in encodingsToTry:
            encodingsToTry.append(encMagic2)
        if "utf-8-sig" not in encodingsToTry:
            encodingsToTry.append("utf-8-sig")

        ok = False
        for encoding in encodingsToTry:
            try:
                text = bb.decode(encoding)
                ok = True
                break
            except ValueError:
                pass

        if not ok:
            text = bb.decode("ascii", "backslashreplace")

            msg = (
                'Error decoding contents of file "{}". '
                "Already tried {} without success. "
                "--> now using ascii with backslashreplace".format(
                    filepath, encodingsToTry
                )
            )

            print(msg)
            m = QtWidgets.QMessageBox(self)
            m.setWindowTitle("Error while loading text")
            m.setText(msg)
            m.setIcon(m.Icon.Warning)
            m.exec()

        # process line endings
        self.lineEndings = determineLineEnding(text)

        # process indentation and trailing
        indentWidth, trailing = determineIndentationAndTrailingWS(text)
        self.removeTrailingWS = trailing < 10  # not too much for ugly diffs
        if indentWidth == -1:  # Tabs
            self.setIndentWidth(pyzo.config.settings.defaultIndentWidth)
            self.setIndentUsingSpaces(False)
        elif indentWidth:
            self.setIndentWidth(indentWidth)
            self.setIndentUsingSpaces(True)

        # set text
        self.setPlainText(text)
        self.document().setModified(not ok)
        self._binaryDataFromFile = bb
        return text

    def _saveTextToFile(self, filepath):
        text = self.toPlainText().replace("\n", self.lineEndings)
        encoding = getEncodingFromMagic(text[:200])
        if encoding == "utf-8" and self.useBom:
            encoding = "utf-8-sig"

        bb = text.encode(encoding)
        with open(filepath, "wb") as f:
            f.write(bb)

        if not encoding.startswith("utf-8"):
            self.useBom = False

        self._binaryDataFromFile = bb

        print(
            "saved file: {} ({}, {})".format(
                filepath, encoding, self.lineEndingsHumanReadable
            )
        )

    ##

    def justifyText(self):
        """Overloaded version of justifyText to make it use our
        configurable justificationwidth.
        """
        super().justifyText(pyzo.config.settings.justificationWidth)

    def showRunCursor(self, cursor):
        """Momentarily highlight a piece of code to show that this is being executed"""

        extraSelection = QtWidgets.QTextEdit.ExtraSelection()
        extraSelection.cursor = cursor
        extraSelection.format.setBackground(QtCore.Qt.GlobalColor.gray)
        self.setExtraSelections([extraSelection])

        self._showRunCursorTimer.singleShot(200, lambda: self.setExtraSelections([]))

    def id(self):
        """Get an id of this editor. This is the filename, or for tmp files, the name."""
        if self._filename:
            return self._filename
        else:
            return self._name

    def focusInEvent(self, event):
        """Test whether the file has been changed 'behind our back'"""
        pyzo.callLater(self._checkAndHandleExternalFileModifications)
        return super().focusInEvent(event)

    def _checkAndHandleExternalFileModifications(self):
        if not self._checkFileModified():
            return

        if self.document().isModified():
            # ask user
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("File was changed")
            dlg.setText(
                "File has also been modified outside of the editor:\n" + self._filename
            )
            dlg.setInformativeText("Do you want to reload?")
            btnReload = dlg.addButton(
                "Reload", QtWidgets.QMessageBox.ButtonRole.AcceptRole
            )
            dlg.addButton(
                "Keep this version", QtWidgets.QMessageBox.ButtonRole.RejectRole
            )
            dlg.setDefaultButton(btnReload)

            # get user's decision
            dlg.exec()
            doReload = dlg.clickedButton() == btnReload
        else:
            if pyzo.config.advanced.autoReloadFilesInEditor:
                doReload = True
                print("auto-reloading file", self._filename)
            else:
                # ask user
                dlg = QtWidgets.QMessageBox(self)
                dlg.setWindowTitle("File was changed")
                dlg.setText(
                    "File has been modified outside of the editor:\n" + self._filename
                )
                dlg.setInformativeText("Do you want to reload?")
                btnAlwaysReload = dlg.addButton(
                    "Always reload", QtWidgets.QMessageBox.ButtonRole.NoRole
                )
                btnReloadThisTime = dlg.addButton(
                    "Reload", QtWidgets.QMessageBox.ButtonRole.AcceptRole
                )
                dlg.addButton(
                    "Keep this version", QtWidgets.QMessageBox.ButtonRole.RejectRole
                )
                dlg.setDefaultButton(btnReloadThisTime)

                # get user's decision
                dlg.exec()
                if dlg.clickedButton() == btnReloadThisTime:
                    doReload = True
                elif dlg.clickedButton() == btnAlwaysReload:
                    doReload = True
                    pyzo.config.advanced.autoReloadFilesInEditor = 1

                    QtWidgets.QMessageBox.information(
                        self,
                        "Always reload",
                        'Files that are marked as "unchanged" in the editor will now '
                        "always be reloaded automatically. You can change this setting "
                        '"autoReloadFilesInEditor" in the "Advanced settings" dialog.',
                    )
                else:
                    doReload = False

        if doReload:
            self.reload()
        else:
            self.document().setModified(True)

    def _checkFileModified(self):
        """Test if the file was externally changed since it was last loaded/saved by Pyzo.
        Returns True if it was changed, False if not changed or unknown.
        """

        filepath = self._filename
        if not os.path.isfile(filepath):
            # file is deleted from the outside
            return False

        # test the modification time...
        mtime = os.path.getmtime(filepath)

        if mtime == self._modifyTime:
            return False

        # whatever the user will decide, we will reset the modified time
        self._modifyTime = mtime

        try:
            with open(filepath, "rb") as f:
                bb = f.read()
            if bb == self._binaryDataFromFile:
                print(
                    "modification time of file {} changed, but content is the same".format(
                        filepath
                    )
                )
                return False
        except Exception:
            pass

        return True

    def _onModificationChanged(self, changed):
        """Handler for the modificationChanged signal. Emit somethingChanged
        for the editorStack to update the modification notice."""
        self.somethingChanged.emit()

    def _onModified(self):
        pyzo.parser.parseThis(self)

    def _onContextMenu(self, point):
        cur = self.textCursor()
        curFromEvent = self.cursorForPosition(point)
        moveTextCursor = True
        if cur.hasSelection():
            i1 = cur.selectionStart()
            i2 = cur.selectionEnd()
            if i1 <= curFromEvent.position() <= i2:
                moveTextCursor = False
        if moveTextCursor:
            self.setTextCursor(curFromEvent)
        # the offset is to prevent accidental auto-clicking
        self._menu.popup(self.mapToGlobal(point) + QtCore.QPoint(0, 3))

    def _updateStatusBar(self):
        editor = pyzo.editors.getCurrentEditor()
        sb = pyzo.main.statusBar()
        sb.updateCursorInfo(editor)

    def dragMoveEvent(self, event):
        """Otherwise cursor can get stuck.
        https://bitbucket.org/iep-project/iep/issue/252
        https://qt-project.org/forums/viewthread/3180
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def dropEvent(self, event):
        """Drop files in the list."""
        if event.mimeData().hasUrls():
            # file: let the editorstack do the work.
            pyzo.editors.dropEvent(event)
        else:
            # text: act normal
            super().dropEvent(event)

    def showEvent(self, event=None):
        """Capture show event to change title."""
        # Act normally
        if event:
            super().showEvent(event)

        # Make parser update
        pyzo.parser.parseThis(self)

    def setTitleInMainWindow(self):
        """set the title text in the main window to show filename."""
        name, path = self._name, self._filename
        pyzo.main.setMainTitle(path or name)

    def save(self, filename=None):
        """Save the file. No checking is done."""

        # get filename
        if filename is None:
            filename = self._filename
        if not filename:
            raise ValueError("No filename specified, and no filename known.")

        # Test whether it was changed without us knowing. If so, don't save now.
        if self._checkFileModified():
            # ask user
            dlg = QtWidgets.QMessageBox(self)
            dlg.setWindowTitle("File was changed")
            dlg.setText(
                "File has also been modified outside of the Pyzo editor:\n"
                + self._filename
            )
            dlg.setInformativeText("Do you want to reload?")
            btnOverwrite = dlg.addButton(
                "Overwrite file", QtWidgets.QMessageBox.ButtonRole.AcceptRole
            )
            btnCancel = dlg.addButton(
                "Cancel saving", QtWidgets.QMessageBox.ButtonRole.RejectRole
            )
            dlg.setDefaultButton(btnCancel)

            # get user's decision
            dlg.exec()
            if dlg.clickedButton() != btnOverwrite:
                # cancel saving
                self.document().setModified(True)
                return

        # Remove whitespace in a single undo-able action
        if (
            self.removeTrailingWS
            or pyzo.config.settings.removeTrailingWhitespaceWhenSaving
        ):
            # Original cursor to put state back at the end
            oricursor = self.textCursor()
            # Screen cursor to select document
            screenCursor = self.textCursor()
            screenCursor.movePosition(screenCursor.MoveOperation.Start)
            screenCursor.movePosition(
                screenCursor.MoveOperation.End,
                screenCursor.MoveMode.KeepAnchor,
            )
            # Cursor for doing the editor
            editCursor = self.textCursor()
            # Go!
            editCursor.beginEditBlock()

            try:
                editCursor.setPosition(screenCursor.selectionStart())
                editCursor.movePosition(editCursor.MoveOperation.StartOfBlock)
                while (
                    editCursor.position() < screenCursor.selectionEnd()
                    or editCursor.position() <= screenCursor.selectionStart()
                ):
                    editCursor.movePosition(editCursor.MoveOperation.StartOfBlock)
                    editCursor.movePosition(
                        editCursor.MoveOperation.EndOfBlock,
                        editCursor.MoveMode.KeepAnchor,
                    )
                    text1 = editCursor.selectedText()
                    text2 = text1.rstrip()
                    if len(text1) != len(text2):
                        editCursor.insertText(text2)
                    if not editCursor.block().next().isValid():
                        break
                    editCursor.movePosition(editCursor.MoveOperation.NextBlock)
            finally:
                # Setting the textcursor might scroll to another place
                # To prevent this, we store and then restore the position
                # of the vertical scrollbar
                sb = self.verticalScrollBar()
                scrollbarPos = sb.value()
                self.setTextCursor(oricursor)
                editCursor.endEditBlock()
                sb.setValue(scrollbarPos)

        self._saveTextToFile(filename)

        # Update stats
        self._filename = normalizePath(filename)
        self._name = os.path.split(self._filename)[1]
        self.document().setModified(False)
        self._modifyTime = os.path.getmtime(self._filename)

        # update title (in case of a rename)
        self.setTitleInMainWindow()

        # allow item to update its texts (no need: onModifiedChanged does this)
        # self.somethingChanged.emit()

    def saveCopy(self, filepath):
        """Creates a backup of the current editor's contents. No checking is done."""
        self._saveTextToFile(filepath)

    def reload(self):
        """Reload text using the self._filename.
        We do not have a load method; we first try to load the file
        and only when we succeed create an editor to show it in...
        This method is only for reloading in case the file was changed
        outside of the editor."""

        # We can only load if the filename is known
        if not self._filename:
            return
        filename = self._filename

        # Remember where we are
        cursor = self.textCursor()
        linenr = cursor.blockNumber() + 1

        self._loadTextFromFile(filename)

        # Go where we were (approximately)
        self.gotoLine(linenr)

        # Trigger update of indentation and line ending in the "File" menu
        pyzo.editors.onCurrentChanged()

    def _expandSelectionToWholeBlocks(self):
        """expands the selection of the current text cursor to whole blocks

        The selection will be expanded so that it starts at the beginning of the block
        and so that it ends at the beginning of the next block, including the new-block
        special character.
        If there is no new block after the end of the expanded selection, which can only
        occur at the end of the document, then "endsAtNextBlock" will be set to False.

        If no text is selected, the whole block will be selected.

        return value:
            cursor, endsAtNextBlock
        """
        cursor = self.textCursor()
        # Find start and end of selection
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        # Expand selection to the start of the first block
        cursor.setPosition(start)
        cursor.movePosition(cursor.MoveOperation.StartOfBlock)

        # Expand selection to the start of the next block if there is no selection at all
        # or if there is at least one character selected in the last selected block.
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        if not cursor.atBlockStart() or not cursor.hasSelection():
            endsAtNextBlock = cursor.movePosition(
                cursor.MoveOperation.NextBlock,
                cursor.MoveMode.KeepAnchor,
            )
            if not endsAtNextBlock:
                # Could not move to the beginning of the next block because the end of the
                # document was reached. Therefore move till the end of the document.
                cursor.movePosition(
                    cursor.MoveOperation.End, cursor.MoveMode.KeepAnchor
                )
        else:
            # There is selected text and the cursor is at the beginning of the block.
            endsAtNextBlock = True
        return cursor, endsAtNextBlock

    def deleteLines(self):
        cursor, endsAtNextBlock = self._expandSelectionToWholeBlocks()
        cursor.removeSelectedText()

    def duplicateLines(self):
        cursor, endsAtNextBlock = self._expandSelectionToWholeBlocks()
        text = cursor.selectedText()
        if not endsAtNextBlock:
            text += "\u2029"
        cursor.setPosition(cursor.selectionStart())
        cursor.insertText(text)

    def commentCode(self):
        """
        Comment the lines that are currently selected
        """
        indents = []
        indentChar = " " if self.indentUsingSpaces() else "\t"

        def getIndent(cursor):
            text = cursor.block().text().rstrip()
            if text:
                indents.append(len(text) - len(text.lstrip()))

        def commentBlock(cursor):
            blockText = cursor.block().text()
            numMissingIndentChars = minindent - (
                len(blockText) - len(blockText.lstrip(indentChar))
            )
            if numMissingIndentChars > 0:
                # Prevent setPosition from leaving bounds of the current block
                # if there are too few indent characters (e.g. an empty line)
                cursor.insertText(indentChar * numMissingIndentChars)
            cursor.setPosition(cursor.block().position() + minindent)
            cursor.insertText("# ")

        self.doForSelectedBlocks(getIndent)
        minindent = min(indents, default=0)
        self.doForSelectedBlocks(commentBlock)

    def uncommentCode(self):
        """Uncomment the lines that are currently selected"""
        # TODO: this should not be applied to lines that are part of a multi-line string

        # Define the uncomment function to be applied to all blocks
        def uncommentBlock(cursor):
            """Find the first # on the line; if there is just whitespace before it,
            remove the # and if it is followed by a space remove the space, too
            """
            text = cursor.block().text()
            commentStart = text.find("#")
            if commentStart == -1:
                return  # No comment on this line
            if text[:commentStart].strip() != "":
                return  # Text before the #
            # Move the cursor to the beginning of the comment
            cursor.setPosition(cursor.block().position() + commentStart)
            cursor.deleteChar()
            if text[commentStart:].startswith("# "):
                cursor.deleteChar()

        # Apply this function to all blocks
        self.doForSelectedBlocks(uncommentBlock)

    def toggleCommentCode(self):
        def toggleComment():
            """Toggles comments for the seclected text in editor, most of the code is
            taken from commentCode and uncommentCode
            """
            text_block = []

            def getBlocks(cursor):
                text = cursor.block().text()
                text_block.append(text)

            def commentBlock(cursor):
                cursor.setPosition(cursor.block().position())
                cursor.insertText("# ")

            def uncommentBlock(cursor):
                """Find the first # on the line; if there is just whitespace before it,
                remove the # and if it is followed by a space remove the space, too
                """
                cursor.setPosition(cursor.block().position())
                cursor.deleteChar()
                cursor.deleteChar()

            self.doForSelectedBlocks(getBlocks)
            commented = [item for item in text_block if item.startswith("# ")]
            if len(commented) == len(text_block):
                self.doForSelectedBlocks(uncommentBlock)
            else:
                self.doForSelectedBlocks(commentBlock)

        toggleComment()

    def gotoDef(self):
        """Goto the definition for the word under the cursor"""

        # Get name of object to go to
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.SelectionType.WordUnderCursor)
        word = cursor.selection().toPlainText()

        # Send the open command to the shell
        s = pyzo.shells.getCurrentShell()
        if s is not None:
            if word and word.isidentifier():
                s.executeCommand("open {}\n".format(word))
            else:
                s.write("Invalid identifier {!r}\n".format(word))

    ## Introspection processing methods

    def processCallTip(self, cto):
        """Processes a calltip request using a CallTipObject instance."""
        # Try using buffer first
        if cto.tryUsingBuffer():
            return

        # Try obtaining calltip from the source
        sig = pyzo.parser.getFictiveSignature(cto.name, self, True)
        if sig:
            # Done
            cto.finish(sig)
        else:
            # Try the shell
            shell = pyzo.shells.getCurrentShell()
            if shell:
                shell.processCallTip(cto)

    def processAutoComp(self, aco):
        """Processes an autocomp request using an AutoCompObject instance."""

        # Try using buffer first
        if aco.tryUsingBuffer():
            return

        # Get normal fictive namespace
        fictiveNS = pyzo.parser.getFictiveNameSpace(self)
        fictiveNS = set(fictiveNS)

        # Add names
        if not aco.name:
            # "root" names
            aco.addNames(fictiveNS)
            # imports
            importNames, importLines = pyzo.parser.getFictiveImports(self)
            aco.addNames(importNames)
        else:
            # Prepare list of class names to check out
            classNames = [aco.name]
            handleSelf = True
            # Unroll supers
            while classNames:
                className = classNames.pop(0)
                if not className:
                    continue
                if handleSelf or (className in fictiveNS):
                    # Only the self list (only first iter)
                    fictiveClass = pyzo.parser.getFictiveClass(
                        className, self, handleSelf
                    )
                    handleSelf = False
                    if fictiveClass:
                        aco.addNames(fictiveClass.members)
                        classNames.extend(fictiveClass.supers)
                        if className in classNames:
                            # avoid infinite loop if the parent class is the same as the
                            # current class, see https://github.com/pyzo/pyzo/issues/944
                            break
                else:
                    break

        # If there's a shell, let it finish the autocompletion
        shell = pyzo.shells.getCurrentShell()
        if shell:
            shell.processAutoComp(aco)
        else:
            # Otherwise we finish it ourselves
            aco.finish()


if __name__ == "__main__":
    # Do some stubbing to run this module as a unit separate from pyzo
    # TODO: untangle pyzo from this module where possible
    class DummyParser:
        def parseThis(self, x):
            pass

    pyzo.parser = DummyParser()
    EditorContextMenu = QtWidgets.QMenu
    app = QtWidgets.QApplication([])
    win = PyzoEditor(None)
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+C"), win).activated.connect(win.copy)
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+X"), win).activated.connect(win.cut)
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+V"), win).activated.connect(win.paste)
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Shift+V"), win).activated.connect(
        win.pasteAndSelect
    )
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Z"), win).activated.connect(win.undo)
    QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Y"), win).activated.connect(win.redo)

    tmp = "foo(bar)\nfor bar in range(5):\n  print bar\n"
    tmp += "\nclass aap:\n  def monkey(self):\n    pass\n\n"
    win.setPlainText(tmp)
    win.show()
    app.exec()
