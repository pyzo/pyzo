""" EditorStack class (implemented in qt)
"""

import os, sys, time, gc

from PyQt4 import QtCore, QtGui
qt = QtGui

import iep
from editor import createEditor
from baseTextCtrl import normalizePath
from baseTextCtrl import styleManager

barwidth = iep.config.editorStackBarWidth



class Item(qt.QLabel):
    """ Base Item class, items for a list of files and projects.
    Some of the styling is implemented here. An item instance 
    directly represents the file or project, but also its 
    asociated widget (and thus appearance).
    """
    
    def __init__(self, parent):
        qt.QLabel.__init__(self,parent)
       
        # indicate height and spacing
        self._itemHeight = 15
        self._itemSpacing = iep.config.editorStackBarSpacing
        
        # set indent and size        
        self._indent = 1
        self._y = 1
        self.resize(barwidth-self._indent, self._itemHeight)
        
        # test framewidths when raised
        self.setLineWidth(1)
        self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
        self._frameWidth = self.frameWidth() + 3 # correction        
    
    
    def setIndent(self, indent):
        """ Set the indentation of the item. """
        self._indent = indent
        self.resize(barwidth-self._indent, self._itemHeight)
    
    def updateTexts(self):
        raise NotImplemented()
        
    def updateStyle(self):
        raise NotImplemented()
    
    def enterEvent(self, event):
        self.updateStyle()
    def leaveEvent(self, event):        
        self.updateStyle()
    
    def mouseMoveEvent(self, event):
        self.parent().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self.parent().mouseReleaseEvent(event)
    

class ProjectItem(Item):
    """ An item representing a project. """
    
    def __init__(self, parent, name):
        Item.__init__(self, parent)
        
        # projects have more spacing
        self._itemSpacing = 2 + iep.config.editorStackBarSpacing
        
        # set name and tooltip
        self._name = name
        
        # each project can have one main file
        self._mainfile = ''
        
        # collapsed?
        self._collapsed = False
        self._ncollapsed = 0
        
        # update
        self.setStyleSheet("ProjectItem { font:bold; background:#999; }")
        self.updateTexts()
        self.updateStyle()
    
    
    def updateTexts(self):
        """ Update the text and tooltip """        
        if self._collapsed:
            self.setText('- {} ({})'.format(self._name, self._ncollapsed))
        else:
            self.setText('+ {}'.format(self._name))
        self.setToolTip('project: '+ self._name)
    
    
    def updateStyle(self):
        """ Update the style. Automatically detects whether the mouse
        is over the label. Depending on the type and whether the file is
        selected, sets its appearance and redraw! """
        if self._collapsed:#self.underMouse():
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Plain)
            self.move(self._indent,self._y)
        else:
            self.setFrameStyle(0)
            #self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Plain)
            self.move(self._indent,self._y)
    
    def mousePressEvent(self, event):
        """ Collapse/expand item, or show context menu. """
        
        if event.button() == QtCore.Qt.LeftButton:
            # collapse/expand
            self._collapsed = not self._collapsed
            self.parent().updateMe()
        
        elif event.button() == QtCore.Qt.RightButton:
            # popup menu
            menu = QtGui.QMenu(self)
            menu.addAction('New file (in project)', self.context_new)
            menu.addAction('Open file (in project)', self.context_open)
            menu.addSeparator()       
            menu.addAction('Rename project', self.context_rename)
            menu.addAction('Remove project', self.context_remove)
            menu.addSeparator()
            menu.addAction('Move project up', self.context_up)
            menu.addAction('Move project down', self.context_down)
            menu.popup(event.globalPos())
    
    def context_new(self, event=None):
        self.parent().parent().newFile(self._name)
    def context_open(self, event=None):
        self.parent().parent().openFile(self._name)
    def context_rename(self, event=None):
        title = "Project name"
        label = "Give the new project name"
        name, ok = QtGui.QInputDialog.getText(self, title, label)
        if ok and name:
            self._name = name
            self.updateTexts()
    def context_remove(self, event=None):
        self.parent().removeProject(self)
    def context_up(self, event=None):
        self.upDownHelper(-1)            
    def context_down(self, event=None):
        self.upDownHelper(1)
    
    def upDownHelper(self, direction):
        """" move project up (-1) or down (+1)
        """
        projectBefore, projectAfter, itemsToMove = None, None, []
        phase = 0
        for item in self.parent()._items:
            if phase == 0:
                if item is self:
                    phase = 1
                elif isinstance(item, ProjectItem):
                    projectBefore = item
            elif phase == 1:
                if isinstance(item, ProjectItem):                    
                    phase = 2
                else:
                    itemsToMove.append(item)
            elif phase == 2:
                if isinstance(item, ProjectItem):
                    projectAfter = item
                    break
        
        if direction<0 and not projectBefore:
            return # no need, already at top
        
        # finish up list of items to move and get parent list object
        itemsToMove.reverse()
        itemsToMove.append(self)        
        items = self.parent()._items
        
        # remove all items from the list 
        for item in itemsToMove:
            while item in items:
                items.remove(item)
        
        # determine index to insert
        if direction < 0:
            i = items.index(projectBefore)
        elif direction > 0:
            if projectAfter:
                i = items.index(projectAfter)
            else:
                i = len(items) # put at the end
        
        # insert them again at the new position
        for item in itemsToMove:
            items.insert(i, item)
        
        # update
        self.parent().updateMe()


class FileItem(Item):
    """ An item representing a file. This class does the loading 
    and saving of that file, but without any checks, that is up to
    the editorStack. """
    
    def __init__(self, parent, editor):
        Item.__init__(self, parent)
        
        # set editor
        #if isinstance(editor, ??) (why should we care?)
        self._editor = editor
        
        # to keep name and tooltip up to date
        editor.somethingChanged.connect(self.updateTexts)
        
        # each file item can belong to a project, or to the root project (None)
        self._project = None
        
        # set style
        self.setAutoFillBackground(True)
        
        # update
        self.updateTexts()
        self.updateStyle()
    
    
    def updateTexts(self):
        """ Updates the text of the label and tooltip. Called when 
        the editor's dirty status changed or when saved as another file. 
        """
        # get texts
        name = self._editor._name
        filename = self._editor._filename
        style = ''
        # prepare texts
        if self._editor._dirty:
            name = '*' + name
            style += "color:#603000;"
        if self._project and self._project._mainfile == self._editor._filename:
            style += 'font-weight:bold;'
        if not filename: 
            filename = 'None'
        # set texts
        self.setText( name )
        self.setStyleSheet("QLabel{" + style + "}")
        self.setToolTip('file: '+ filename)
    
    
    def updateStyle(self):
        """ Update the style. To indicate selected file or hoovering over one.
        Need to update position, because the frame width is different for
        the different scenarios."""
        if self is self.parent()._currentItem:
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Sunken)
            self.move(self._indent ,self._y)
        elif self.underMouse():
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
            self.move(self._indent ,self._y)
        else:
            self.setFrameStyle(0)
            self.move(self._frameWidth+self._indent,self._y)
    
    
    def mouseDoubleClickEvent(self, event):
        self.parent().parent().saveFile(self._editor)
        #self.parent().parent().closeFile(self._editor)
    
    
    def mousePressEvent(self, event):
        """ Item selected. """
        
        # select this item! 
        self.parent().setCurrentItem(self)
        
        if event.button() == QtCore.Qt.LeftButton:
            # change stuff at parent to get the dragging right
            x, y = event.globalX(), event.globalY()
            self.parent()._dragStartPos = QtCore.QPoint(x,y)
        
        elif event.button() == QtCore.Qt.RightButton:
            # popup menu
            menu = QtGui.QMenu(self)
            menu.addAction('Save file', self.context_save)
            menu.addAction('Save file as', self.context_saveAs)
            menu.addAction('Close file', self.context_close)
            menu.addAction('Make main file', self.context_makeMain)
            menu.popup(event.globalPos())
    
    def context_save(self, event=None):
        self.parent().parent().saveFile(self._editor)
    def context_saveAs(self, event=None):
        self.parent().parent().saveFileAs(self._editor)
    def context_close(self, event=None):
        self.parent().parent().closeFile(self._editor)
    def context_makeMain(self, event=None):
        if self._project:
            self._project._mainfile = self._editor._filename
        for item in self.parent()._items:
            if isinstance(item, FileItem):
                item.updateTexts()
    
    

class FileListCtrl(QtGui.QFrame):
    """ Control that displays a list of files using Labels.
    """
    # - make buttons if not all labels fit
    # - when removing a file, go to previously selected
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        # store editorstack
        self._editorStack = parent
        
        # set width
        self.setMinimumWidth(barwidth)
        self.setMaximumWidth(barwidth)
        
        # set label
        self._label = QtGui.QLabel(" File list", self)
        self._label.setFont( qt.QFont('helvetica',8,qt.QFont.Bold) ) 
        self._label.resize(barwidth, 15)
        self._label.move(0,0)
        #self._label.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
        self._label.setAutoFillBackground(True)
        #self._label.setBackgroundRole(QtGui.QPalette.color('#999'))
        self._label.setStyleSheet("QLabel { font:bold; background:#999; }")
        
        # create scrollbar to scroll
        self._scroller = QtGui.QScrollBar(self)
        self._scroller.setOrientation(QtCore.Qt.Horizontal)
        self._scroller.resize(barwidth, 15)
        self._scroller.setRange(0,200)
        self._scroller.setSingleStep(10)
        self._scroller.setValue(0)
        
        # create list of items
        self._items = []        
        self._currentItem = None
        self._itemHistory = []
        
        # enable dragging/dropping
        self.setAcceptDrops(True)
        self._draggedItem = None
        self._dragStartPos = QtCore.QPoint(0,0)
        
        # set callbacks
        self._scroller.valueChanged.connect(self.updateMe)
        
        #self.updateMe()
    
    def resizeEvent(self, event):
        QtGui.QFrame.resizeEvent(self, event)
        self.updateMe()
    
    def updateMe(self):
        project = None
        ncollapsed = 0
        itemsToUpdate = []
        
        h1 = self._label.height() + 2
        
        offset = h1-self._scroller.value()
        y = offset  # initial y position
        spacing = 0
        for item in self._items:            
            if isinstance(item, ProjectItem):
                # handle previous collapsed project?
                if project and project._collapsed:
                    project._ncollapsed = ncollapsed
                project = item
                if project._collapsed:
                    ncollapsed = 0
            elif isinstance(item, FileItem):
                item._project = project
                if project and project._collapsed:
                    item.hide()
                    ncollapsed += 1
                    continue
                elif project:
                    item.setIndent(10)
                else:
                    item.setIndent(1)
            else:
                continue
            
            # add spacing to y and update item's position
            y = y + max(spacing, item._itemSpacing)
            item._y = y
            
            # list item
            itemsToUpdate.append(item)
            
            # next item
            y += item._itemHeight
            spacing = item._itemSpacing 
        
        # handle last collapsed project
        if project and project._collapsed:
            project._ncollapsed = ncollapsed
        
        # update scroller
        h = y-offset
        h0 = self.height()
        h1 = self._label.height()
        h2 = self._scroller.height()
        self._scroller.setRange(0, h-h0+h1+h2 + 10)
        self._scroller.setPageStep(self.height())
        self._scroller.move(0,h0-h2)
        if self._scroller.maximum()==0:
            self._scroller.hide()
        else:
            self._scroller.show()
            self._scroller.raise_()
        
        # and label
        self._label.raise_()
        
        # update
        for item in itemsToUpdate:
            item.updateTexts()
            item.updateStyle()
            item.show()
        #self.update()
    
    
    def setCurrentItem(self, item, remember=True):
        """ Make the given item current. 
        If item is None, select previous item. 
        If remember, store the current item in the history. """
        
        if item is self._currentItem:
            return # no need to change
        
        if item is None:
            # make an old item history
            if self._itemHistory:
                item = self._itemHistory[0]
        
        if item is None:
            # just select first one then ...
            if self._items:
                item = self._items[0]
        
        if item and isinstance(item, FileItem):
            # store old item
            if remember:
                while self._currentItem in self._itemHistory:
                    self._itemHistory.remove(self._currentItem)
                self._itemHistory.insert(0,self._currentItem)
                self._itemHistory[10:] = []
            # make the item current and show...
            self._currentItem = item
            self._editorStack.showEditor(self._currentItem._editor)
        else:
            # no files present
            self._currentItem = None
            self._editorStack.showEditor(None)
        
        # finish and focus
        self.updateMe()
        if self._currentItem:
            self._currentItem._editor.setFocus()
    
    
    def selectPreviousItem(self):
        """ Select the previously selected item. """
        self.setCurrentItem(None)
    
    
    def mouseReleaseEvent(self, event):
        # stop dragging
        self._draggedItem = None        
        # update
        self.updateMe()
    
    
    def mouseMoveEvent(self, event):
        # check for mouse and moved enough
        
        if not event.buttons() & QtCore.Qt.LeftButton:
            pass
        th = QtGui.qApp.startDragDistance()
        
        if self._draggedItem:
            # do drag now
            self._doDrag(event)
        
        elif (event.globalPos() - self._dragStartPos).manhattanLength() > th:
            # start drag
            
            # determine which item to drag
            theitem = None
            yref = self._dragStartPos.y()
            for item in self._items:
                if item.underMouse():
                    theitem = item  
                    break
            
            # is the item a file?
            if isinstance(theitem, FileItem):
                theitem.raise_() # make it the front-most item
                theitem._yStart = theitem._y
                self._draggedItem = theitem
    
    
    def _doDrag(self, event):
        
        # determine new pisition
        diffY = event.globalY() - self._dragStartPos.y()
        self._draggedItem._y = self._draggedItem._yStart+ diffY
        
        # determine if we should swap items
        i_to_put = None
        y2 = self._draggedItem._itemHeight/2
        for i in range(len(self._items)):
            item = self._items[i]
            if item is self._draggedItem:
                continue
            dy = item._y - self._draggedItem._y
            if item.isVisible() and abs(dy) < y2:                    
                if dy < 0 and self._draggedItem._y < item._y + y2:
                    i_to_put = i
                if dy > 0 and self._draggedItem._y > item._y - y2:
                    i_to_put = i
                break
            
        if i_to_put is not None:
            # first remove item being dragged
            self._items.remove(self._draggedItem)
            # determine where to put it
            if i_to_put > len(self._items):
                # at the end
                self._items.insert(i_to_put, self._draggedItem)
            else:
                # somewhere in between
                for i in range(i_to_put-1,-1,-1):
                    item = self._items[i]
                    if isinstance(item, ProjectItem) and item._collapsed:
                        continue
                    if self._items[i].isVisible():
                        self._items.insert(i+1, self._draggedItem)
                        break
                else:
                    # at the beginning
                    self._items.insert(0, self._draggedItem)
            
            # update list, but disable drawing to prevent flicker
            self.setUpdatesEnabled(False)
            try:
                tmp = self._draggedItem._y
                self.updateMe()
                self._draggedItem._y = tmp
            finally:
                self.setUpdatesEnabled(True)
        
        # update position
        self._draggedItem.updateStyle()
        self._draggedItem.show()
        self.update()
   
   
    def mousePressEvent(self, event):
        """ Context menu """        
        if event.button() == QtCore.Qt.RightButton:
            # popup menu
            menu = QtGui.QMenu(self)
            menu.addAction('New file', self.context_newFile)
            menu.addAction('Open file', self.context_openFile)
            menu.addSeparator()   
            menu.addAction('Create new project', self.context_newProject)
            menu.addAction('Open dir as project', self.context_openProject)
            menu.popup(event.globalPos())
    
    def context_newFile(self, event=None):
        self._editorStack.newFile()
    def context_openFile(self, event=None):
        self._editorStack.openFile()
    def context_newProject(self, event=None):
        title = "Create new project"
        label = "Give the new project's name"
        name, ok = QtGui.QInputDialog.getText(self, title, label)
        if ok and name:
            self.appendProject(name)
        self.updateMe()
    def context_openProject(self, event=None):
        self._editorStack.openDir()
    
    
    def appendFile(self, editor, projectname=None):
        """ Create file item. 
        Returns the created file item on success."""
        
        # if project name was given
        i_insert = 0        
        insertInThisProject = True
        i = 0
        for i in range(len(self._items)):
            item = self._items[i]
            if isinstance(item,ProjectItem):                
                if insertInThisProject:
                    i_insert = i
                if projectname and item._name == projectname:
                    # yuppy, rember to insert at right before the next project
                    insertInThisProject = True
                else:
                    insertInThisProject = False
        
        # finish
        if insertInThisProject:
            i_insert = len(self._items)
        
        # create item
        item = FileItem(self, editor)
        self._items.insert(i_insert,item)
        
        # make it current
        self.setCurrentItem(item)
        
        return item
    
    
    def appendProject(self, projectname):
        """ Create project Item. 
        Return the project item if all went well."""
        
        # stop if already a project with that name
        for item in self._items:            
            if isinstance(item,ProjectItem) and item._name == projectname:
                print("Cannot load dir: a project with that name "\
                    "already exists!" )                  
                return None
                
        # create project at the end
        item = ProjectItem(self, projectname)
        self._items.append(item)
        #print("Creating project: %s" % (projectname))
        return item
    
    
    def removeFile(self, editor):
        """ Remove file item from the list. """
        
        # get item corresonding to that editor
        for item in self._items:
            if isinstance(item, FileItem) and item._editor is editor:
                break
        else:
            tmp = editor._name
            print("Could not remove listItem for file '{}'.".format(tmp))
            return
        
        # clear from lists        
        for items in [self._items, self._itemHistory]:
            while item in items:  
                items.remove(item)
        # select other editor (also removes from editorStack's boxlayout)
        if self._currentItem is item:
            self.setCurrentItem(None, False)        
        
        # destroy...   
        item.hide()
        editor.hide()     
        item.destroy()
        editor.destroy()
        gc.collect()
        
        # update
        self.updateMe()
    
    
    def removeProject(self, project):
        """ Remove a project.
        project should be a ProjectItem instance or the name of the project. 
        """
        
        # get project
        if isinstance(project, str):
            for item in self._items:
                if isinstance(item, ProjectItem) and item._name == project:
                    project = item
                    break
            else:
                print("Cannot remove project: no project with that name.")
                return
        
        # get list of files to remove first
        itemsToRemove = []
        phase = 0
        for item in self._items:
            if phase == 0:
                if item is project:
                    phase = 1
            elif phase == 1:
                if isinstance(item, ProjectItem):
                    break
                else:
                    itemsToRemove.append(item)
        
        # remove these items.
        for item in itemsToRemove:
            ok = self._editorStack.closeFile(item._editor)
            if not ok:
                break
        else:
            # we get here if the user did not press cancel
            # remove project item
            while project in self._items:
                self._items.remove(project)
            project.hide()
            project.destroy()
        
        # update
        self.updateMe()


class FindReplaceWidget(QtGui.QFrame):
    """ A widget to find and replace text. """
    def __init__(self, *args):
        QtGui.QWidget.__init__(self, *args)
        
        # width hint
        ww = barwidth//2 - 1
        
        # create widgets
        
        yy = 2
        self._stext = qt.QLabel("Find / Replace", self)
        self._stext.setFont( qt.QFont('helvetica',8,qt.QFont.Bold) ) 
        self._stext.move(5,yy)
        
        self._hidebut = qt.QPushButton("hide", self)
        self._hidebut.setFont( qt.QFont('helvetica',7) )
        self._hidebut.setToolTip("Escape")
        self._hidebut.setGeometry(barwidth-25,yy,24,16)
        
        yy+=16
        self._caseCheck = qt.QCheckBox("Match case", self)
        self._caseCheck.move(1,yy)
        yy+=16
        self._regExp = qt.QCheckBox("RegExp", self)
        self._regExp.move(1,yy)
        
        yy += 18
        self._findText = qt.QLineEdit(self)
        self._findText.setGeometry(1,yy,barwidth-2,20)
        yy += 20
        self._findPrev = qt.QPushButton("Previous", self) 
        self._findPrev.setGeometry(1,yy, ww,20)
        self._findNext = qt.QPushButton("Next", self)
        self._findNext.setGeometry(ww+1,yy, ww,20)
        self._findNext.setDefault(True)
        
        yy += 22
        self._replaceText = qt.QLineEdit(self)
        self._replaceText.setGeometry(1,yy,barwidth-2,20)
        yy += 20
        self._replaceAll = qt.QPushButton("Replace all", self) 
        self._replaceAll.setGeometry(1,yy, ww,20)
        self._replace = qt.QPushButton("Replace", self)
        self._replace.setGeometry(ww+1,yy,ww,20)
        
        # set size        
        yy += 21
        self.setMinimumHeight(yy)
        self.setMaximumHeight(yy)
        
        # create timer object
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect( self.resetAppearance )
        
        # init case and regexp
        self._caseCheck.setChecked( bool(iep.config.find_matchCase) )
        self._regExp.setChecked( bool(iep.config.find_regExp) )
        
        # create callbacks
        self._findText.returnPressed.connect(self.findNext)
        self._hidebut.clicked.connect(self.hideMe)
        self._findNext.clicked.connect(self.findNext)
        self._findPrev.clicked.connect(self.findPrevious)
        self._replace.clicked.connect(self.replaceOne)
        self._replaceAll.clicked.connect(self.replaceAll)
    
    def closeEvent(self, event):
        iep.config.find_matchCase = 0#self._caseCheck.isChecked()
        iep.config.find_regExp = self._regExp.isChecked()
        print('aaa'*20)
        # proceed normally
        QtGui.QFrame.closeEvent(self, event)
    
    def hideMe(self):
        """ Hide the find/replace widget. """
        self.hide()
        es = self.parent() # editor stack
        #es._boxLayout.activate()
        #es._list.updateMe()
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
        #es._list.updateMe()
        
        # get needle
        editor = self.parent().getCurrentEditor()
        if editor:
            needle = editor.getSelectedString()
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
        
        # matchCase and regExp
        matchCase = self._caseCheck.isChecked()
        regExp = self._regExp.isChecked()
        wholeWord = False
        
        # focus
        self.selectFindText()
        
        # get text to find
        needle = self._findText.text()
        if not matchCase:
            needle = needle.lower()
        
        # estblish start position
        pos1 = editor.getPosition()
        pos2 = editor.getAnchor()
        if forward:
            pos = max([pos1,pos2])
        else:
            pos = min([pos1,pos2])
        line = editor.getLinenrFromPosition(pos)
        index = pos-editor.getPositionFromLinenr(line)
        
        # use Qscintilla's implementation
        ok = editor.findFirst(needle, regExp, matchCase, wholeWord, False, 
                            forward, line, index, True)
        
        # wrap and notify
        if not ok:
            self.notifyPassBeginEnd()
            if forward:
                line, index = 0,0
            else:
                pos = len(editor)
                line = editor.getLinenrFromPosition(pos)
                index = pos-editor.getPositionFromLinenr(line)
            ok = editor.findFirst(needle, regExp, matchCase, wholeWord, False, 
                                forward, line, index, True)
        
        # done
        return ok
    
    
    def replaceOne(self,event=None):
        """ If the currently selected text matches the find string,
        replaces that text. Then it finds and selects the next match.
        Returns True if a next match was found.
        """
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return        
        
        # matchCase
        matchCase = self._caseCheck.isChecked()
        
        # get text to find
        needle = self._findText.text()
        if not matchCase:
            needle = needle.lower()
        
        # get replacement
        replacement = self._replaceText.text()
        
        # get original text
        original = editor.getSelectedString()
        if not original:
            original = ''
        if not matchCase:
            original = original.lower()
        
        # replace
        if original and original == needle:
            editor.replace( replacement )
        
        # next!
        return self.find()
    
    
    def replaceAll(self,event=None):
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return 
        
        # get current position
        line, index = editor.getLineAndIndex()
        
        # replace all
        editor.setPosition(0)
        while self.replaceOne():
            pass
        
        # reset position
        pos = editor.getPositionFromLine(line)
        editor.setPositionAndAnchor(pos+index)
    
    
class EditorStack(QtGui.QWidget):
    
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        # keep a booking of opened directories
        self._lastpath = ''
        
        # create widgets
        self._list = FileListCtrl(self)        
        self._findReplace = FindReplaceWidget(self)
        self._stack = QtGui.QStackedWidget(self)
        
        # create box layout control and add widgets
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout2 = QtGui.QVBoxLayout()        
        # fill layouts
        #self._boxLayout2.addWidget(self._list, 1)
        self._boxLayout2.addWidget(self._list, 1)
        self._boxLayout2.addWidget(self._findReplace, 0)
        self._boxLayout.addLayout(self._boxLayout2, 0)
        self._boxLayout.addWidget(self._stack, 1)
        # spacing of widgets
        self._boxLayout.setSpacing(2)
        self._boxLayout2.setSpacing(0)
        
        # make the horizontal box layout the layout manager
        self.setLayout(self._boxLayout)
        
        #self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips,True)
        
        # put the last opened files in 
        if iep.config.editorState:
            self.setCurrentState(iep.config.editorState)
    
    
    def showEditor(self, editor=None):
        """ Show the given editor. 
        This also performs a check on the contents of the stack, 
        cleaning up editors that weren't cleaned up properly. (this
        is not supposed to happen, but if it ever does, it will be
        nicely removed here.)"""
        
        # remove all from stack
        while self._stack.count():
            widget = self._stack.widget(0)
            widget.hide()
            self._stack.removeWidget(widget)
        
        # add the one!
        if editor:
            self._stack.addWidget(editor)
            editor.show()
    
    def getCurrentEditor(self):
        """ Get the currently active editor. """
        item = self._list._currentItem
        if item:
            return item._editor
        else:
            return None
    
    def __iter__(self):
        tmp = self._list._items
        tmp = [item._editor for item in tmp if isinstance(item,FileItem)]
        return tmp.__iter__()
    
    ## methods for managing files 
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        
    def dropEvent(self, event):
        """ Drop files in the list. """
        for qurl in event.mimeData().urls():
            path = str( qurl.path()[1:] )
            if os.path.isfile(path):
                self.loadFile(path)
            elif os.path.isdir(path):
                self.loadDir(path)
            else:
                pass
    
    
    def newFile(self, projectname=None):
        """ Create a new (unsaved) file. """
        
        # create editor
        editor = createEditor(self, None)
        
        # add to list
        self._list.appendFile(editor, projectname)
    
    
    def openFile(self, projectname=None):
        """ Create a dialog for the user to select a file. """
        
        # determine start dir
        editor = self.getCurrentEditor()
        if editor and editor._filename:
            startdir = os.path.split(editor._filename)[0]
        else:
            startdir = self._lastpath            
        if not os.path.isdir(startdir):
            startdir = ''
        
        # show dialog
        msg = "Select one or more files to open"
        filter = "Python (*.py *.pyw);;Pyrex (*.pyi,*.pyx);;All (*.*)"
        filenames = QtGui.QFileDialog.getOpenFileNames(self,
            msg, startdir, filter)
        
        # were some selected?
        if not filenames:
            return
        
        # load
        for filename in filenames:
            self.loadFile(filename, projectname)
    
    
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
    
    
    def loadFile(self, filename, projectname=None):
        """ Load the specified file. 
        On success returns the item of the file, also if it was
        already open."""
        
        # normalize path
        filename = normalizePath(filename)
        
        # if the file is already open...
        for item in self._list._items:
            if isinstance(item, FileItem):
                if item._editor._filename == filename:
                    break
        else:
            item = None
        if item:
            self._list.setCurrentItem(item)
            print("File already open: '{}'".format(filename))
            return item
        
        # create editor
        try:
            editor = createEditor(self, filename)
        except Exception as err:
            print("Error loading file: ", err)
            return None
        
        # create list item
        item = self._list.appendFile(editor, projectname)
        
        # store the path
        self._lastpath = os.path.dirname(editor._filename)
        
        return item
    
    
    def loadDir(self, path, extensions="py,pyw"):
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
        extensions = ["."+a.lstrip(".").strip() for a in extensions.split(",")]
        
        # create project        
        projectname = str( os.path.basename(path) )
        ok = self._list.appendProject(projectname)
        if not ok:
            return
        
        # init window
        item = None
        
        # open all qualified files...
        self._list.setUpdatesEnabled(False)
        try:
            filelist = os.listdir(path)
            for filename in filelist:
                filename = os.path.join(path,filename)
                ext = os.path.splitext(filename)[1]            
                if str(ext) in extensions:
                    item = self.loadFile(filename,projectname)
        finally:
            self._list.setUpdatesEnabled(True)
            self._list.updateMe()
        
        # return lastopened window
        return item
    
    
    def saveFileAs(self, editor=None):
        """ Create a dialog for the user to select a file. """
        
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
        filter = "Python (*.py *.pyw);;Pyrex (*.pyi,*.pyx);;All (*.*)"
        filename = QtGui.QFileDialog.getSaveFileName(self,
            msg, startdir, filter)
        
        # proceed or cancel
        if filename:
            self.saveFile(editor, filename)
        else:
            pass
    
    
    def saveFile(self, editor=None, filename=None):
        
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
        
        # normalize
        filename = normalizePath(filename)
        
        # let the editor do the low level stuff...
        try:
            editor.save(filename)
        except Exception as err:
            print("Error saving file:",err)
            return
        
        # get actual normalized filename
        filename = editor._filename
        
        # notify
        tmp = {'\n':'LF', '\r':'CR', '\r\n':'CRLF'}[editor._lineEndings]
        print("saved file: {} ({})".format(filename, tmp))
        
        # special case, we edited the style file!
        if filename == styleManager._filename:
            # reload styles
            styleManager.loadStyles()
            # editors are send a signal by the style manager
    
    
    def askToSaveFileIfDirty(self, editor):
        """ If the given file is not saved, pop up a dialog
        where the user can save the file. 
        Returns 1 if file need not be saved.
        Returns 2 if file was saved.
        Returns 3 if user discarded changes.
        Returns 0 if cancelled.
        """
        
        # should we ask to save the file?
        if editor._dirty:
            
            # get filename
            filename = editor._filename
            if not filename:
                filename = '<TMP>'
            
            # setup dialog
            dlg = QtGui.QMessageBox(self)
            dlg.setText("Closing file:\n{}".format(filename))
            dlg.setInformativeText("Save modified file?")
            tmp = QtGui.QMessageBox
            dlg.setStandardButtons(tmp.Save| tmp.Discard | tmp.Cancel)
            dlg.setDefaultButton(tmp.Cancel)
            
            # get result and act
            result = dlg.exec_() 
            if result == tmp.Save:
                self.saveFile(editor)
                return 2
            elif result == tmp.Discard:
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
        if editor is None:
            return
        
        result = self.askToSaveFileIfDirty(editor)
        
        # ok, close...
        if result:
            self._stack.removeWidget(editor)
            self._list.removeFile(editor)
        return result
    
    
    def getCurrentState(self):
        """ Get the state as it currently is as a string.
        The state entails all open files and their structure in the
        projects. The being collapsed of projects and their main files.
        The position of the cursor in the editors.
        """
        
        collapsed = {True:'+', False:'-'}
        
        # get items
        state = []
        for item in self._list._items:
            info = ''
            if isinstance(item, ProjectItem):
                info = collapsed[item._collapsed]+item._name, item._mainfile
            elif isinstance(item, FileItem):
                ed = item._editor
                if ed._filename:
                    info = ed._filename, str(ed.getPosition())
            if info:
                state.append( '>'.join(info) )
        
        # get history
        history = [item for item in self._list._itemHistory]
        history.reverse()
        history.append(self._list._currentItem)
        for item in history:
            if isinstance(item, FileItem):
                ed = item._editor
                if ed._filename:
                    state.append( 'hist>'+ed._filename )
        
        return ",".join(state)
    
    
    def setCurrentState(self,state):
        """ Set the state of the editor in terms of opened files.
        The input should be a string as returned by 
        .GetCurrentState().
        """
        
        # make list
        state = state.split(",")
        currentProject = ''
        fileItems = {}
        
        for item in state:
            parts = item.split('>')
            if item[0] in '+-':
                # a project item
                tmp = self._list.appendProject(parts[0][1:])
                tmp._collapsed = item[0]=='+'
                tmp._mainfile = parts[1]
                currentProject = tmp._name
            elif item.startswith('hist'):
                # select item (to make the history right)
                if parts[1] in fileItems:
                    self._list.setCurrentItem( fileItems[parts[1]] )
            elif parts[0]:
                # a file item
                tmp = self.loadFile(parts[0], currentProject)
                ed = tmp._editor
                # set position and make sure it is visible
                pos = int(parts[1])
                linenr = ed.getLinenrFromPosition(pos)
                ed.setPositionAndAnchor(pos)
                ed.SendScintilla(ed.SCI_LINESCROLL, 0, linenr-10)
                fileItems[parts[0]] = tmp
    
    
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
    
    
    def storeSettings(self):
        """ Go finish up, save settings, store files, etc. 
        """
        
        # store settings
        fr = self._findReplace
        iep.config.find_matchCase = fr._caseCheck.isChecked()
        iep.config.find_regExp = fr._regExp.isChecked()
        iep.config.editorState = self.getCurrentState()
    

if __name__ == "__main__":
    #qt.QApplication.setDesktopSettingsAware(False)
    app = QtGui.QApplication([])
    app.setStyle("windows") # plastique, windows, cleanlooks
    win = EditorStack(None)
    win.show()
    app.exec_()
