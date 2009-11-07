""" EditorStack class (implemented in qt)
"""

import os, sys, time, gc

from PyQt4 import QtCore, QtGui
qt = QtGui

from editor import createEditor
from baseTextCtrl import normalizePath
from baseTextCtrl import styleManager
barwidth = 120



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
        self._itemSpacing = 0
        
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
        self._itemSpacing = 2
        
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
    
    

class FileListCtrl(qt.QWidget):
    """ Control that displays a list of files using Labels.
    """
    # - make buttons if not all labels fit
    # - when removing a file, go to previously selected
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        #self.barwidth,300)
        self.setMinimumWidth(barwidth)
        self.setMaximumWidth(barwidth)
        
        # create list of items
        self._items = []        
        self._currentItem = None
        self._itemHistory = []
        
        # enable dragging/dropping
        self.setAcceptDrops(True)
        self._draggedItem = None
        self._dragStartPos = QtCore.QPoint(0,0)
        
        #self.updateMe()
    
    
    def updateMe(self):
        
        project = None
        ncollapsed = 0
        itemsToUpdate = []
        
        y = 10  # initial y position
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
            self.parent().showEditor(self._currentItem._editor)
        else:
            # no files present
            self._currentItem = None
            self.parent().showEditor(None)
        
        # finish and focus
        self.updateMe()
        if self._currentItem:
            self._currentItem._editor.setFocus()
    
    
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
        self.parent().newFile()
    def context_openFile(self, event=None):
        self.parent().openFile()
    def context_newProject(self, event=None):
        title = "Create new project"
        label = "Give the new project's name"
        name, ok = QtGui.QInputDialog.getText(self, title, label)
        if ok and name:
            self.appendProject(name)
        self.updateMe()
    def context_openProject(self, event=None):
        self.parent().openDir()
    
    
    def appendFile(self, editor, projectname=None):
        """ Create file item. """
        
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
        self._currentItem = item
        self.parent().showEditor(editor)
        
        # update
        self.updateMe()
    
    
    def appendProject(self, projectname):
        """ Create project Item. 
        Return True if all went well."""
        
        # stop if already a project with that name
        for item in self._items:            
            if isinstance(item,ProjectItem) and item._name == projectname:
                print("Cannot load dir: a project with that name "\
                    "already exists!" )                  
                return False
                
        # create project at the end
        self._items.append(ProjectItem(self, projectname))
        #print("Creating project: %s" % (projectname))
        return True
    
    
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
            ok = self.parent().closeFile(item._editor)
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
        
        yy = 0
        self._stext = qt.QLabel("Find / Replace", self)
        self._stext.setFont( qt.QFont('helvetica',8,qt.QFont.Bold) ) 
        self._stext.move(5,yy)
        
        self._hidebut = qt.QPushButton("hide", self)
        self._hidebut.setFont( qt.QFont('helvetica',7) )
        self._hidebut.setToolTip("Escape")
        self._hidebut.setGeometry(barwidth-25,yy,24,16)
        
        yy+=18
        self._caseCheck = qt.QCheckBox("Match case", self)
        self._caseCheck.move(1,yy)
        
        yy += 20
        self._findText = qt.QLineEdit(self)
        self._findText.setGeometry(1,yy,barwidth-2,20)
        yy += 22
        self._findPrev = qt.QPushButton("Previous", self) 
        self._findPrev.setGeometry(1,yy, ww,20)
        self._findNext = qt.QPushButton("Next", self)
        self._findNext.setGeometry(ww+1,yy, ww,20)
        
        yy += 25
        self._replaceText = qt.QLineEdit(self)
        self._replaceText.setGeometry(1,yy,barwidth-2,20)
        yy += 22
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
        
        # create callbacks
        self._hidebut.clicked.connect(self.hideMe)
        self._findNext.clicked.connect(self.findNext)
        
    
    def hideMe(self):
        """ Hide the find/replace widget. """
        self.hide()
        es = self.parent() # editor stack
        es._boxLayout.update()
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
        #self.parent()._boxLayout.update()        
        
        # get needle
        editor = self.parent().getCurrentEditor()
        if editor:
            needle = editor.selectedText() # is utf-8 proof
            if needle:
                self._findText.setText( needle ) #
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
        """ The main find method. """
        
        # get editor
        editor = self.parent().getCurrentEditor()
        if not editor:
            return        
        
        # matchCase
        matchCase = self._caseCheck.isChecked()
        
        # focus
        self.selectFindText()
        
        # get text to find
        needle = self._findText.text()
        if not matchCase:
            needle = needle.lower()
        
        # estblish start position
        pos1 = editor.getCurrentPos()
        pos2 = editor.getAnchor()
        if forward:
            pos = max([pos1,pos2])
        else:
            pos = min([pos1,pos2])
        line = editor.lineFromPosition(pos)
        index = pos-editor.positionFromLine(line)
        
        # use Qscintilla's implementation
        ok = editor.findFirst(needle, False, matchCase, False, False, 
                            forward, line, index, True)
        
        # wrap and notify
        if not ok:
            self.notifyPassBeginEnd()
            if forward:
                line, index = 0,0
            else:
                pos = editor.getTextLength()
                line = editor.lineFromPosition(pos)
                index = pos-editor.positionFromLine(line)
            editor.findFirst(needle, False, matchCase, False, False, 
                                forward, line, index, True)
    
    
    def replaceThis(self,event=None):
        
        # matchCase
        matchCase = self.caseCheck.GetValue()
        
        # get needle
        needle = self.findText.GetValue()        
        if not matchCase:
            needle = needle.lower()
            
        # get replacement
        replacement = self.replaceText.GetValue()
                    
        # get text to replace
        editor = self.book.GetCurrentEditor()
        if editor:
            original = editor.GetSelectedText()            
            if not matchCase:
                original = original.lower()
            
            # replace
            if original and original == needle:
                editor.ReplaceSelection( replacement )
                
            # next!
            self.Find()
    
    def replaceAll(self,event=None):
        # matchCase
        matchCase = self.caseCheck.GetValue()
        
        # get needle
        needle = self.findText.GetValue()        
        if not matchCase:
            needle = needle.lower()
            
        # get replacement
        replacement = self.replaceText.GetValue()
        
        # get text to replace
        editor = self.parent().getCurrentEditor()
        if editor:
            # get text from editor
            text2 = text = editor.GetText()            
            if not matchCase:
                text2 = text2.lower()
                
            # replace untill done
            pos = 0
            while not pos<0:
                pos = text2.find(needle, pos)
                if pos >= 0:
                    endpos = pos + len(needle)
                    # replace both text and searchtext!
                    text = text[:pos] + replacement + text[endpos:]
                    text2 = text2[:pos] + replacement + text2[endpos:]
                    pos = len(replacement)             
            
            # finish up
            editor.SetText(text)   
    
    
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
        
        # put some files in 
        self.loadFile(r'C:\projects\PYTHON\iep2\iep.py')
        self.loadFile(r'C:\projects\PYTHON\iep2\shell.py')
        self.loadFile(r'C:\projects\PYTHON\test.py')
        self.loadDir(r'C:\projects\PYTHON\tools')
        self.loadDir(r'C:\projects\PYTHON\tools\visvis')
        self.newFile('tools')
        #self.openDir()
    
    
    def showEditor(self, editor=None):
        """ Show the given editor. 
        This also performs a check on the contents of the stack, 
        cleaning up editors that weren't cleaned up properly. (this
        is not supposed to happen, but if it ever does, it will be
        nicely removed here.)"""
        
        # always do a check here ...
        tmp = self._list._items
        tmp = [item._editor for item in tmp if isinstance(item,FileItem)]
        foundIt = False
        for i in range(self._stack.count()):
            widget = self._stack.widget(i)
            if widget not in tmp:
                print('removing stuck widget:', widget)
                self._stack.removeWidget(widget)
                widget.hide()
                widget.destroy()
            if widget is editor:
                foundIt = True
        
        if editor:            
            # if not already in stack, add it now
            if True:#not foundIt:
                self._stack.addWidget(editor)            
            # make current
            self._stack.setCurrentWidget(editor)
    
    
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
        """ Load the specified file. """
        
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
            return
        
        # create editor
        try:
            editor = createEditor(self, filename)
        except Exception as err:
            print("Error loading file: ", err)
            return
        
        # create list item
        self._list.appendFile(editor, projectname)
        
        # store the path
        self._lastpath = os.path.dirname(editor._filename)
    
    
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
        window = None
        
        # open all qualified files...
        self._list.setUpdatesEnabled(False)
        try:
            filelist = os.listdir(path)
            for filename in filelist:
                filename = os.path.join(path,filename)
                ext = os.path.splitext(filename)[1]            
                if str(ext) in extensions:
                    window = self.loadFile(filename,projectname)
        finally:
            self._list.setUpdatesEnabled(True)
            self._list.updateMe()
        
        # return lastopened window
        return window
    
    
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
    
    
    def closeFile(self, editor=None):
        """ Close the selected (or current) editor. 
        Returns True if all went well, False if the user pressed cancel
        when asked to save an modified file. """
        
        # get editor
        if editor is None:
            editor = self.getCurrentEditor()
        if editor is None:
            return
        
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
            elif result == tmp.Discard:
                pass # do not save
            else: # cancel
                return False
        
        # ok, close...
        self._stack.removeWidget(editor)
        self._list.removeFile(editor)        
        return True
        

if __name__ == "__main__":
    #qt.QApplication.setDesktopSettingsAware(False)
    app = QtGui.QApplication([])
    app.setStyle("windows") # plastique, windows, cleanlooks
    win = EditorStack(None)
    win.show()
    app.exec_()
