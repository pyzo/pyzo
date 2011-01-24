# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" EditorTabs class

Replaces the earlier EditorStack class.

The editor tabs class represents the different open files. They can
be selected using a tab widget (with tabs placed north of the editor).
It also has a find/replace widget that is at the bottom of the editor.

"""

import os, sys, time, gc
from PyQt4 import QtCore, QtGui

import iep
from compactTabWidget import CompactTabWidget
from editor import createEditor
from baseTextCtrl import normalizePath
from baseTextCtrl import styleManager
from iepLogging import print

# Constants for the alignments of tabs
MIN_NAME_WIDTH = 50
MAX_NAME_WIDTH = 200


def simpleDialog(item, action, question, options, defaultOption):
    """ simpleDialog(editor, action, question, options, defaultOption)
    
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
    mb = QtGui.QMessageBox
    M = {   'ok':mb.Ok, 'open':mb.Open, 'save':mb.Save, 'cancel':mb.Cancel,
            'close':mb.Close, 'discard':mb.Discard, 'apply':mb.Apply, 
            'reset':mb.Reset, 'restoredefaults':mb.RestoreDefaults, 
            'help':mb.Help, 'saveall':mb.SaveAll, 'yes':mb.Yes, 
            'yestoall':mb.YesToAll, 'no':mb.No, 'notoall':mb.NoToAll, 
            'abort':mb.Abort, 'retry':mb.Retry, 'ignore':mb.Ignore}
    
    # setup dialog
    dlg = QtGui.QMessageBox(iep.main)
    dlg.setWindowTitle('IEP')
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
            button = dlg.addButton(option, dlg.AcceptRole)
        buttons[button] = option
        # Set as default?
        if option_lower == defaultOption:
            dlg.setDefaultButton(button)
    
    # get result
    result = dlg.exec_()
    button = dlg.clickedButton()
    if button in buttons:
        return buttons[button]
    else:
        return None
    
    

# todo: some management stuff could (should?) go here
class FileItem:
    """ FileItem(editor)
    
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
        """ Get the editor component corresponding to this item.
        """
        return self._editor
    
    @property
    def id(self):
        """ Get an id of this editor. This is the filename, 
        or for tmp files, the name. """
        if self.filename:
            return self.filename
        else:
            return self.name 
    
    @property
    def filename(self):
        """ Get the full filename corresponding to this item.
        """
        return self._editor.filename
    
    @property
    def name(self):
        """ Get the name corresponding to this item.
        """
        return self._editor.name
    
    @property
    def dirty(self):
        """ Get whether the file has been changed since it is changed.
        """
        return self._editor.document().isModified()
    
    @property
    def pinned(self):
        """ Get whether this item is pinned (i.e. will not be closed
        when closing all files.
        """
        return self._pinned


# todo: when this works with the new editor, put in own module.
class FindReplaceWidget(QtGui.QFrame):
    """ A widget to find and replace text. """
    
    def __init__(self, *args):
        QtGui.QWidget.__init__(self, *args)
        
        # init layout
        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # create widgets
        
        if True:
            # Create sub layouts
            vsubLayout = QtGui.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)
            
            # Add button
            self._hidebut = QtGui.QToolButton(self)
            self._hidebut.setFont( QtGui.QFont('helvetica',7) )
            self._hidebut.setToolTip("Hide search widget (Escape)")
            self._hidebut.setIcon( iep.icons.cross )
            self._hidebut.setIconSize(QtCore.QSize(16,16))
            vsubLayout.addWidget(self._hidebut, 0)
            
            vsubLayout.addStretch(1)
        
        layout.addSpacing(10)
        
        if True:
            
            # Create sub layouts
            vsubLayout = QtGui.QVBoxLayout()
            hsubLayout = QtGui.QHBoxLayout()
            vsubLayout.setSpacing(0)
            hsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)
            
            # Add find text
            self._findText = QtGui.QLineEdit(self)
            vsubLayout.addWidget(self._findText, 0)
            
            vsubLayout.addLayout(hsubLayout)
            
            # Add previous button
            self._findPrev = QtGui.QToolButton(self) 
            self._findPrev.setText('Previous')
            hsubLayout.addWidget(self._findPrev, 0)
            
            hsubLayout.addStretch(1)
            
            # Add next button
            self._findNext = QtGui.QToolButton(self)
            self._findNext.setText('Next')
            #self._findNext.setDefault(True)
            hsubLayout.addWidget(self._findNext, 0)
        
        layout.addSpacing(10)
        
        if True:
            
            # Create sub layouts
            vsubLayout = QtGui.QVBoxLayout()
            hsubLayout = QtGui.QHBoxLayout()
            vsubLayout.setSpacing(0)
            hsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)
            
            # Add replace text
            self._replaceText = QtGui.QLineEdit(self)
            vsubLayout.addWidget(self._replaceText, 0)
            
            vsubLayout.addLayout(hsubLayout)
            
            # Add replace-all button
            self._replaceAll = QtGui.QToolButton(self) 
            self._replaceAll.setText("Repl. all")
            hsubLayout.addWidget(self._replaceAll, 0)
            
            hsubLayout.addStretch(1)
            
            # Add replace button
            self._replace = QtGui.QToolButton(self)
            self._replace.setText("Replace")
            hsubLayout.addWidget(self._replace, 0)
        
        
        layout.addSpacing(10)
        
        if True:
            
            # Create sub layouts
            vsubLayout = QtGui.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)
            
            # Add match-case checkbox
            self._caseCheck = QtGui.QCheckBox("Match case", self)
            vsubLayout.addWidget(self._caseCheck, 0)
            
            # Add regexp checkbox
            self._regExp = QtGui.QCheckBox("RegExp", self)
            vsubLayout.addWidget(self._regExp, 0)
        
        if True:
            
            # Create sub layouts
            vsubLayout = QtGui.QVBoxLayout()
            vsubLayout.setSpacing(0)
            layout.addLayout(vsubLayout, 0)
            
            # Add whole-word checkbox
            self._wholeWord = QtGui.QCheckBox("Whole words", self)
            self._wholeWord.resize(60, 16)
            vsubLayout.addWidget(self._wholeWord, 0)
            
            vsubLayout.addStretch(1)
       
        layout.addStretch(1)
        
        # create timer object
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect( self.resetAppearance )
        
        # init case and regexp
        self._caseCheck.setChecked( bool(iep.config.state.find_matchCase) )
        self._regExp.setChecked( bool(iep.config.state.find_regExp) )
        self._wholeWord.setChecked(  bool(iep.config.state.find_wholeWord) )
        
        # create callbacks
        self._findText.returnPressed.connect(self.findNext)
        self._hidebut.clicked.connect(self.hideMe)
        self._findNext.clicked.connect(self.findNext)
        self._findPrev.clicked.connect(self.findPrevious)
        self._replace.clicked.connect(self.replaceOne)
        self._replaceAll.clicked.connect(self.replaceAll)
        
        # show or hide?
        if bool(iep.config.state.find_show):
            self.show()
        else:
            self.hide()
    
    
    def hideMe(self):
        """ Hide the find/replace widget. """
        self.hide()
        es = self.parent() # editor stack
        #es._boxLayout.activate()
        editor = es.getCurrentEditor()
        if editor:
            editor.setFocus()
    
    def keyPressEvent(self, event):
        """ To capture escape. """
        
        if event.key() == QtCore.Qt.Key_Escape:
            self.hideMe()
            event.ignore()
        else:
            event.accept()
    
    
    def startFind(self,event=None):
        """ Use this rather than show(). It will check if anything is 
        selected in the current editor, and if so, will set that as the
        initial search string
        """
        # show
        self.show()
        es = self.parent()
        #es._boxLayout.activate()        
        
        # get needle
        editor = self.parent().getCurrentEditor()
        if editor:
            needle = editor.textCursor().selectedText()
            if needle:
                self._findText.setText( needle )
        # select the find-text
        self.selectFindText()
        
        
    def notifyPassBeginEnd(self):
        self.setStyleSheet("QFrame { background:#f00; }")
        self._timer.start(300)
    
    def resetAppearance(self):
        self.setStyleSheet("QFrame {}")
    
    def selectFindText(self):
        """ Select the textcontrol for the find needle,
        and the text in it """
        # select text
        self._findText.selectAll()
        # focus
        self._findText.setFocus()
    
    def findNext(self, event=None):
        self.find()
        #self._findText.setFocus()
    
    def findPrevious(self, event=None):
        self.find(False)
        # self._findText.setFocus()
    
    def find(self, forward=True):
        """ The main find method.
        Returns True if a match was found. """
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return        
        
        # find flags
        flags = QtGui.QTextDocument.FindFlags()
        if self._caseCheck.isChecked():
            flags |= QtGui.QTextDocument.FindCaseSensitively

        if self._wholeWord.isChecked():
            flags |= QtGui.QTextDocument.FindWholeWords
        
        if not forward:
            flags |= QtGui.QTextDocument.FindBackward

        
        # focus
        self.selectFindText()
        
        # get text to find
        needle = self._findText.text()
        if self._regExp.isChecked():
            #Make needle a QRegExp; speciffy case-sensitivity here since the
            #FindCaseSensitively flag is ignored when finding using a QRegExp
            needle = QtCore.QRegExp(needle,
                QtCore.Qt.CaseSensitive if self._caseCheck.isChecked() else
                QtCore.Qt.CaseInsensitive)
        
        # estblish start position
        cursor = editor.textCursor()
        result = editor.document().find(needle, cursor, flags)
        
        if not result.isNull():
            editor.setTextCursor(result)
        else:
            self.notifyPassBeginEnd()
            #Move cursor to start or end of document
            if forward:
                cursor.movePosition(cursor.Start)
            else:
                cursor.movePosition(cursor.End)
            #Try again
            result = editor.document().find(needle, cursor, flags)
            if not result.isNull():
                editor.setTextCursor(result)
            
        # done
        editor.setFocus(True)
        return not result.isNull()
    
    
    def replaceOne(self,event=None):
        """ If the currently selected text matches the find string,
        replaces that text. Then it finds and selects the next match.
        Returns True if a next match was found.
        """
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return
        
        #Create a cursor to do the editing
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
        original = cursor.selectedText()
        if not original:
            original = ''
        if not matchCase:
            original = original.lower()
        
        # replace
        #TODO: this line does not work for regexp-search!
        if original and original == needle:
            cursor.insertText( replacement )
        
        # next!
        return self.find()
    
    
    def replaceAll(self,event=None):
        #TODO: share a cursor between all replaces, in order to 
        #make this one undo/redo-step
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return 
        
        # get current position
        originalPosition = editor.textCursor()
        
        # move to beginning of text and replace all
        cursor = editor.textCursor()
        cursor.movePosition(cursor.Start)
        editor.setTextCursor(cursor)
        while self.replaceOne():
            pass
        
        # reset position
        editor.setTextCursor(cursor)


class TabToolButton(QtGui.QToolButton):
    def __init__(self, icon):
        QtGui.QToolButton.__init__(self)
        
        # Init
        self.setIconSize(QtCore.QSize(16,16))
        self.setStyleSheet("QToolButton{ border: none; }")                
        
        # Set icon now
        self.setIcon(icon)
    
    def mousePressEvent(self, event):
        # Ignore event so that the tabbar will change to that tab
        event.ignore()
    

    
class FileTabWidget(CompactTabWidget):
    """ FileTabWidget(parent)
    
    The tab widget that contains the editors and lists all open files.
    
    """
    
    def __init__(self, parent):
        CompactTabWidget.__init__(self, parent, padding=(2,1,0,4))
        
        # Init main file
        self._mainFile = ''
        
        # Init item history
        self._itemHistory = []
        
        # Create a corner widget
        but = QtGui.QToolButton()
        but.setIcon( iep.icons.cross )
        but.clicked.connect(self.onClose)
        self.setCornerWidget(but)
        
        # Create context menu
        self._menu = QtGui.QMenu()
        self._menu.triggered.connect(self.contextMenuTriggered)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        
        # Bind signal to update items and keep track of history
        self.currentChanged.connect(self.updateItems)
        self.currentChanged.connect(self.trackHistory)
    
    
    ## Context menu
    
    def contextMenuEvent(self, event):
    
        # Get which tab to show the context menu of
        tabBar = self.tabBar()
        index = tabBar.tabAt(event.pos())
        
        # Define actions
        generalActions = [ None, 'New file', 'Open file' ]
        fileActions = [ 'Close file', 'Close all but this (and pinned)',
                        'Save file', 'Save file as', 
                        'Rename file', 'Delete file (from file system)', 
                        None,                        
                        'Pin file', 'Make this the MAIN file', None,
                        'Run file', 'Run file as script'
                        ] 
        
        # Get item and actions
        actions = generalActions
        if index<0:
            item = None
        else:
            item = self.items()[index]
            actions = fileActions + actions
        
        # Create menu
        self._menu.clear()
        for a in actions:
            if not a:
                self._menu.addSeparator()
            else:
                al = a.lower()
                
                # Tweak names
                if 'main' in al and item.id == self._mainFile:
                    a = 'Unm' + a[1:]
                if 'pin file' in al and item.pinned:
                    a = 'Unp' + a[1:]
                
                # Create action
                action = self._menu.addAction(a)                
                action._item = item
                action._index = index
                
                # Set icon?
                if 'close file' in a.lower():
                    action.setIcon( iep.icons.cross )
        
        # Show
        
        if item:
            pos = tabBar.mapToGlobal( tabBar.tabRect(index).bottomLeft() )
        else:
            pos = event.globalPos()
            # Putting it below the tabbar seems a bit as if its wrongly placed
        
        self._menu.exec_(pos)
    
    
    def contextMenuTriggered(self, action):
        
        # Get request and item
        request = action.text().lower()
        item = action._item
        index = action._index
        
        # Parse
        if 'new file' in request:
            iep.editors.newFile()
        elif 'open file' in request:
            iep.editors.openFile()
        
        elif 'save file as' in request:
            iep.editors.saveFileAs(item.editor)
        elif 'save file' in request:
            iep.editors.saveFile(item.editor)
        elif 'rename' in request:
            filename = item.filename
            iep.editors.saveFileAs(item.editor)
            try:
                os.remove(filename)
            except Exception:
                pass
        
        elif 'run' in request and 'script' in request:
            menu = iep.main._menuhelper._menus['Run']
            menu.fun_runFileAsScript(None, item.editor)
        elif 'run' in request:
            menu = iep.main._menuhelper._menus['Run']
            menu.fun_runFile(None, item.editor)
        
        elif 'pin file' in request:
            item._pinned = not item._pinned
        elif 'main' in request:
            if self._mainFile == item.id:
                self._mainFile = None
            else:
                self._mainFile = item.id
        
        elif 'close all' in request:
            items = self.items()
            for i in reversed(range(self.count())):
                if items[i] is item or items[i].pinned:
                    continue
                self.tabCloseRequested.emit(i)
        elif 'close' in request:
            self.tabCloseRequested.emit(index)
        elif 'delete' in request:
            result = simpleDialog(item, "Delete", 
                "Are you sure you want to delete the file from your file system?",
                ['Delete', 'Cancel'], 'Cancel')
            if result=='Delete':
                filename = item.filename            
                self.tabCloseRequested.emit(index)
                try:
                    os.remove(filename)
                except Exception:
                    pass
        
        # Update
        self.updateItems()
    
    
    ## Item management
    
    
    def items(self):
        """ Get the items in the tab widget. These are Item instances, and
        are in the order in which they are at the tab bar.
        """
        tabBar = self.tabBar()
        items = []
        for i in range(tabBar.count()):
            item = tabBar.tabData(i)
            if item is None:
                continue
            if not isinstance(item, FileItem):
                item = item.toPyObject() # Older version of Qt
            items.append(item)
        return items
   
    
    def currentItem(self):
        """ Get the item corresponding to the currently active tab.
        """
        i = self.currentIndex()
        if i>=0:
            item = self.tabBar().tabData(i)
            if (item is not None) and (not isinstance(item, FileItem)):
                item = item.toPyObject() # Older version of Qt
            return item
    
    
    def mainItem(self):
        """ Get the item corresponding to the "main" file. Returns None
        if there is no main file.
        """
        for item in self.items():
            if item.id == self._mainFile:
                return item
        else:
            return None
    
    
    def trackHistory(self, index):
        """ trackHistory(index)
        
        Called when a tab is changed. Puts the current item on top of
        the history.
        
        """
        
        # Valid index?
        if index<0 or index>=self.count():
            return
        
        # Remove current item from history
        currentItem = self.currentItem()
        while currentItem in self._itemHistory:
            self._itemHistory.remove(currentItem)
        
        # Add current item to history
        self._itemHistory.insert(0, currentItem)
        
        # Limit history size
        self._itemHistory[10:] = []
    
    
    def setCurrentItem(self, item):
        """ _setCurrentItem(self, item)
        
        Set a FileItem instance to be the current. If the given item
        is not in the list, no action is taken.
        
        item can be an int, FileItem, or file name.
        """
        
        if isinstance(item, int):
            self.setCurrentIndex(i)
            
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
            raise ValueError('item should be int, FileItem or file name.')
    
    
    def selectPreviousItem(self):
        """ Select the previously selected item. """
        
        # make an old item history
        if len(self._itemHistory)>1:
            item = self._itemHistory[1]
            self.setCurrentItem(item)
        
        # just select first one then ...
        elif item is None and self.count():
            item = 0
            self.setCurrentItem(item)
    
    
    ## Closing, adding and updating
    
    def onClose(self):
        """ onClose()
        
        Request to close the current tab.
        
        """
        
        self.tabCloseRequested.emit(self.currentIndex())
    
    
    def removeTab(self, which):
        """ removeTab(which)
        
        Removes the specified tab. which can be an integer, an item,
        or an editor.
        
        """
        
        # Init
        items = self.items()
        theIndex = -1
        
        # Find index
        if isinstance(which, int) and which>=0 and which<len(items):
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
        
        elif hasattr(which, '_filename'):
            for i in range(self.count()):
                if items[i].filename == which._filename:
                    theIndex = i
                    break
        
        else:
            raise ValueError('removeTab accepts a FileItem, integer, file name, or editor.')
        
        
        if theIndex >= 0:
            
            # Close tab
            CompactTabWidget.removeTab(self, theIndex)
            
            # Delete editor
            items[theIndex].editor.destroy()
            gc.collect()
    
    
    def addItem(self, item, update=True):
        """ addItem(item, update=True)
        
        Add item to the tab widget. Set update to false if you are
        calling this method many times in a row. Then use updateItemsFull()
        to update the tab widget.
        
        """
        
        # Add tab and widget
        i = self.addTab(item.editor, item.name)
        
        # Keep informed about changes
        item.editor.somethingChanged.connect(self.updateItems)
        
        # Store the item at the tab
        self.tabBar().setTabData(i, item)
        
        # Update
        if update:
            self.updateItems()
    
    
    def updateItemsFull(self):
        """ updateItemsFull()
        
        Update the appearance of the items and also updates names and 
        re-aligns the items.
        
        """
        self.updateItems()
        self.tabBar().alignTabs()
    
    
    def updateItems(self):
        """ updateItems()
        
        Update the appearance of the items.
        
        """
        
        # Get items and tab bar
        items = self.items()
        tabBar = self.tabBar()
        
        for i in range(len(items)):
            
            # Get item
            item = items[i]
            if item is None:
                continue
            
            # Update name and tooltip
            if item.dirty:
                tabBar.setTabText(i, '*'+item.name)
                tabBar.setTabToolTip(i, item.filename + ' [modified]')
            else:
                tabBar.setTabText(i, item.name)
                tabBar.setTabToolTip(i, item.filename)
            
            # Determine text color. Is main file? Is current?
            if self._mainFile == item.id:
                tabBar.setTabTextColor(i, QtGui.QColor('#008'))
            elif i == self.currentIndex():
                tabBar.setTabTextColor(i, QtGui.QColor('#000'))
            else:
                tabBar.setTabTextColor(i, QtGui.QColor('#444'))
            
            # Update appearance of icon
            if True:
                
                # Select base pixmap and pen color
                if item.dirty:
                    pm0 = iep.icons.page_white_dirty.pixmap(16,16)
                    penColor = '#f00'
                else:
                    pm0 = iep.icons.page_white.pixmap(16,16)
                    penColor = '#444'
                
                # Create painter
                painter = QtGui.QPainter()
                painter.begin(pm0)
                
                # Paint lines
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(penColor))
                painter.setPen(pen)
                for y in range(4,13,2):
                    end = 9
                    if y>6: end = 12
                    painter.drawLine(4,y,end,y)
                
                # Add star-overlay?
                if self._mainFile == item.id:
                    pm1 = iep.icons.overlay_star.pixmap(16,16)
                    painter.drawPixmap(0,0, pm1)
                
                # Add pin-overlay?
                if item.pinned:
                    #pm1 = iep.icons.overlay_link.pixmap(16,16)
                    pm1 = iep.icons.overlay_thumbnail.pixmap(16,16)
                    painter.drawPixmap(0,0, pm1)
                
                # Finish
                painter.end()
                
                # Show icon using tool button. That will make the space
                # between icon and text much smaller for some reason.
                #tabBar.setTabIcon(i, QtGui.QIcon(pm0))
                but = TabToolButton(QtGui.QIcon(pm0))
                tabBar.setTabButton(i, 0, but)
                
 
class EditorTabs(QtGui.QWidget):
    """ The EditorTabs instance manages the open files and corresponding
    editors. It does the saving loading etc.
    """ 
    
    # Signal to notify that a different file was selected
    changedSelected = QtCore.pyqtSignal()
    
    # Signal to notify that the parser has parsed the text (emit by parser)
    parserDone = QtCore.pyqtSignal()
    
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self,parent)
        
        # keep a booking of opened directories
        self._lastpath = ''
        
        # create tab widget
        self._tabs = FileTabWidget(self)       
        self._tabs.tabCloseRequested.connect(self.closeFile)
        self._tabs.currentChanged.connect(self.onCurrentChanged)
        
        # Create find/replace widget
        self._findReplace = FindReplaceWidget(self)
        
        # create box layout control and add widgets
        self._boxLayout = QtGui.QVBoxLayout(self)
        self._boxLayout.addWidget(self._tabs, 1)
        self._boxLayout.addWidget(self._findReplace, 0)
        # spacing of widgets
        self._boxLayout.setSpacing(0)
        # apply
        self.setLayout(self._boxLayout)
        
        #self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips,True)
        
        # accept drops
        self.setAcceptDrops(True)
        
        # restore state
        self.restoreEditorState()
    
    
    def onCurrentChanged(self):
        self.changedSelected.emit()
    
    
    def getCurrentEditor(self):
        """ Get the currently active editor. """
        item = self._tabs.currentItem()
        if item:
            return item.editor
        else:
            return None
    
    
    def getMainEditor(self):
        """ Get the editor that represents the main file, or None if
        there is no main file. """
        item = self._tabs.mainItem()
        if item:
            return item.editor
        else:
            return None
    
    
    def __iter__(self):
        tmp = [item.editor for item in self._tabs.items()]
        return tmp.__iter__()
    
    
    ## Loading ad saving files
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """ Drop files in the list. """
        for qurl in event.mimeData().urls():
            path = str( qurl.path() )
            if sys.platform.startswith('win'):
                path = path[1:]
            if os.path.isfile(path):
                self.loadFile(path)
            elif os.path.isdir(path):
                self.loadDir(path)
            else:
                pass
    
    
    def newFile(self):
        """ Create a new (unsaved) file. """
        
        # create editor
        editor = createEditor(self, None)
        
        # add to list
        item = FileItem(editor)
        self._tabs.addItem(item)
        self._tabs.setCurrentItem(item)
        
        return item
    
    
    def openFile(self):
        """ Create a dialog for the user to select a file. """
        
        # determine start dir
        # todo: better selection of dir, using project manager
        editor = self.getCurrentEditor()
        if editor and editor._filename:
            startdir = os.path.split(editor._filename)[0]
        else:
            startdir = self._lastpath            
        if not os.path.isdir(startdir):
            startdir = ''
        
        # show dialog
        msg = "Select one or more files to open"        
        filter =  "Python (*.py *.pyw);;"
        filter += "Pyrex (*.pyi *.pyx *.pxd);;"
        filter += "C (*.c *.h *.cpp *.c++);;"
        #filter += "Py+Cy+C (*.py *.pyw *.pyi *.pyx *.pxd *.c *.h *.cpp);;"
        filter += "All (*.*)"
        if True:
            filenames = QtGui.QFileDialog.getOpenFileNames(self,
                msg, startdir, filter)
        else:
            # Example how to preselect files, can be used when the users
            # opens a file in a project to select all files currently not
            # loaded.
            d = QtGui.QFileDialog(self, msg, startdir, filter)
            d.setFileMode(d.ExistingFiles)
            d.selectFile('"codeparser.py" "editorStack.py"')
            d.exec_()
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
        """ Create a dialog for the user to select a directory. """
        
        # determine start dir
        editor = self.getCurrentEditor()
        if editor and editor._filename:
            startdir = os.path.split(editor._filename)[0]
        else:
            startdir = self._lastpath            
        if not os.path.isdir(startdir):
            startdir = ''
        
        # show dialog
        msg = "Select a directory to open"
        dirname = QtGui.QFileDialog.getExistingDirectory(self, msg, startdir)
        
        # was a dir selected?
        if not dirname:
            return
        
        # load
        self.loadDir(dirname)
    
    
    def loadFile(self, filename, updateTabs=True):
        """ Load the specified file. 
        On success returns the item of the file, also if it was
        already open."""
        
        # Note that by giving the name of a tempfile, we can select that
        # temp file.
        
        # normalize path
        if filename[0] != '<':
            filename = normalizePath(filename)
        if not filename:
            return None
        
        # if the file is already open...
        for item in self._tabs.items():
            if item.id == filename:
                # id gets _filename or _name for temp files
                break
        else:
            item = None
        if item:
            self._tabs.setCurrentItem(item)
            print("File already open: '{}'".format(filename))
            return item
        
        # create editor
        try:
            editor = createEditor(self, filename)
        except Exception as err:
            # Notify in logger
            print("Error loading file: ", err)
            # Make sure the user knows
            m = QtGui.QMessageBox(self)
            m.setWindowTitle("Error loading file")
            m.setText(str(err))
            m.setIcon(m.Warning)
            m.exec_()
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
        """ Create a project with the dir's name and add all files
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
        extensions = iep.config.advanced.fileExtensionsToLoadFromDir
        extensions = extensions.replace(',',' ').replace(';',' ')
        extensions = ["."+a.lstrip(".").strip() for a in extensions.split(" ")]
        
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
    
    
    def saveFileAs(self, editor=None):
        """ Create a dialog for the user to select a file. 
        """
        
        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
        if editor is None:
            return
        
        # get startdir
        if editor._filename:
            startdir = os.path.dirname(editor._filename)
        else:
            startdir = self._lastpath            
        if not os.path.isdir(startdir):
            startdir = ''
        
        # show dialog
        msg = "Select the file to save to"        
        filter =  "Python (*.py *.pyw);;"
        filter += "Pyrex (*.pyi *.pyx *.pxd);;"
        filter += "C (*.c *.h *.cpp);;"
        #filter += "Py+Cy+C (*.py *.pyw *.pyi *.pyx *.pxd *.c *.h *.cpp);;"
        filter += "All (*.*)"
        filename = QtGui.QFileDialog.getSaveFileName(self,
            msg, startdir, filter)
        
        # give python extension if it has no extension
        head, tail = os.path.split(filename)
        if tail and '.' not in tail:
            filename += '.py'
        
        # proceed or cancel
        if filename:
            self.saveFile(editor, filename)
        else:
            pass
    
    
    def saveFile(self, editor=None, filename=None):
        """ Save the file. 
        """
        
        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
        if editor is None:
            return
        
        # get filename
        if filename is None:
            filename = editor._filename
        if not filename:
            self.saveFileAs(editor)
            return
        
        # let the editor do the low level stuff...
        try:
            editor.save(filename)
        except Exception as err:
            # Notify in logger
            print("Error saving file:",err)
            # Make sure the user knows
            m = QtGui.QMessageBox(self)
            m.setWindowTitle("Error saving file")
            m.setText(str(err))
            m.setIcon(m.Warning)
            m.exec_()
            # Return now            
            return
        
        # get actual normalized filename
        filename = editor._filename
        
        # notify
        # TODO: message concerining line endings
        print("saved file: {} ({})".format(filename, editor.lineEndingsHumanReadable))
        self._tabs.updateItems()
        
        # special case, we edited the style file!
        if filename == styleManager._filename:
            # reload styles
            styleManager.loadStyles()
            # editors are send a signal by the style manager
        
        # Notify done
        return True
    
    
    ## Closing files / closing down
    
    def askToSaveFileIfDirty(self, editor):
        """ askToSaveFileIfDirty(editor)
        
        If the given file is not saved, pop up a dialog
        where the user can save the file
        . 
        Returns 1 if file need not be saved.
        Returns 2 if file was saved.
        Returns 3 if user discarded changes.
        Returns 0 if cancelled.
        
        """ 
        
        # should we ask to save the file?
        if editor.document().isModified():
            
            # Ask user what to do
            result = simpleDialog(editor, "Closing", "Save modified file?", 
                                    ['Discard', 'Cancel', 'Save'], 'Save')
            result = result.lower()
            
            # Get result and act            
            if result == 'save':
                self.saveFile(editor)
                return 2
            elif result == 'discard':
                return 3
            else: # cancel
                return 0
        
        return 1
    
    
    def closeFile(self, editor=None):
        """ Close the selected (or current) editor. 
        Returns same result as askToSaveFileIfDirty() """
        
        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
            item = self._tabs.currentItem()
        elif isinstance(editor, int):
            index = editor
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
        if result and item.pinned:
            result = simpleDialog(editor, "Closing pinned", 
                "Are you sure you want to close this pinned file?",
                ['Close', 'Cancel'], 'Cancel')
            result = result == 'Close'
        
        # ok, close...
        if result:
            self._tabs.removeTab(editor)
        return result
     
    
    def saveEditorState(self):
        """ Save the editor's state configuration.
        """
        fr = self._findReplace
        iep.config.state.find_matchCase = fr._caseCheck.isChecked()
        iep.config.state.find_regExp = fr._regExp.isChecked()
        iep.config.state.find_wholeWord = fr._wholeWord.isChecked()
        iep.config.state.find_show = fr.isVisible()
        #
        iep.config.state.editorState = self._getCurrentOpenFilesAsString()
    
    
    def restoreEditorState(self):
        """ Restore the editor's state configuration.
        """
        
        # Restore opened editors
        if iep.config.state.editorState:
            self._setCurrentOpenFilesAsString(iep.config.state.editorState)
        else:
            #self.newFile()
            self.loadFile(os.path.join(iep.iepDir,'tutorial.py'))
        
        # The find/replace state is set in the corresponding class during init
    
    
    def _getCurrentOpenFilesAsString(self):
        """ Get the state as it currently is as a string.
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
            # Add filename and line number
            info.append(ed._filename)
            info.append(str(ed.textCursor().position()))
            # Add whether pinned or main file
            if item.pinned:
                info.append('pinned')
            if item.id == self._tabs._mainFile:
                info.append('main')
            
            # Add to state
            state.append( '>'.join(info) )
        
        # Get history
        history = [item for item in self._tabs._itemHistory]
        history.reverse() # Last one is current
        for item in history:
            if isinstance(item, FileItem):
                ed = item._editor
                if ed._filename:
                    state.append( 'hist>'+ed._filename )
        
        # Done
        return ",".join(state)
    
    
    def _setCurrentOpenFilesAsString(self, state):
        """ Set the state of the editor in terms of opened files.
        The input should be a string as returned by 
        ._getCurrentOpenFilesAsString().
        """
        
        # Make list
        state = state.split(",")
        fileItems = {}
        
        # Process items
        for item in state:
            parts = item.split('>')
            if item[0] in '+-':
                continue # Was a project
            elif item.startswith('hist'):
                # select item (to make the history right)
                if parts[1] in fileItems:
                    self._tabs.setCurrentItem( fileItems[parts[1]] )
            elif parts[0]:
                # a file item
                itm = self.loadFile(parts[0])
                if itm:
                    # set position and make sure it is visible
                    ed = itm.editor
                    pos = int(parts[1])
                    cursor = ed.textCursor()
                    cursor.setPosition(pos)
                    ed.setTextCursor(cursor)
                    ed.centerCursor() #TODO: this does not work yet
                    
                    # set main and/or pinned?
                    if 'main' in parts:
                        self._tabs._mainFile = itm.id
                    if 'pinned' in parts:
                        itm._pinned = True
                    # store item
                    fileItems[parts[0]] = itm
    
    
    def closeAll(self):
        """ Close all files (well technically, we don't really close them,
        so that they are all stil there when the user presses cancel).
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
    
