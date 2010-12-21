"""  editorTabs

A tab widget for editors.

An IepFile has no visualization purpose, but represents the document and editor.
The FileItem represents the visual appearance of a document in the tab widget.
Multiple FileItems can reference a single IepFile. The order of the documents
is determined by the files. The items are sorted on each draw to match the
order.

"""

import os, sys, time, gc
from PyQt4 import QtCore, QtGui

# todo: make dynamic
barwidth = 120

PROJECT_ALL = "PROJECT_ALL"
PROJECT_LOOSE = "PROJECT_LOOSE"


def normalizePath(path):
    """ Normalize the path given. 
    All slashes will be made the same (and doubles removed)
    The real case as stored on the file system is recovered.
    Returns None on error.
    """
    
    # normalize
    path = os.path.abspath(path)  # make sure it is defined from the drive up
    path = os.path.normpath(path)
    
    # If does not exist, return as is.
    # This also happens if the path's case is incorrect and the
    # file system is case sensitive. That's ok, because the stuff we 
    # do below is intended to get the path right on case insensitive
    # file systems.
    if not (os.path.isfile(path) or os.path.isdir(path)):
        print("Path does not exist:", path)
        return None
    
    # make lowercase and split in parts    
    parts = path.lower().split(os.sep)
    sep = '/'
    
    # make a start
    drive, tmp = os.path.splitdrive(path)
    if drive:
        # windows
        fullpath = drive.upper() + sep
        parts = parts[1:]
    else:
        # posix/mac
        fullpath = sep + parts[1] + sep
        parts = parts[2:] # as '/dev/foo/bar' becomes ['','dev','bar']
    
    for part in parts:
        # print( fullpath,part)
        options = [x for x in os.listdir(fullpath) if x.lower()==part]
        if len(options) > 1:
            print("Error normalizing path: Ambiguous path names!")
            return None
        elif len(options) < 1:
            print("Invalid path: "+fullpath+part)
            return None
        fullpath += options[0] + sep
    
    # remove last sep
    return fullpath[:-len(sep)]

# 
# 
# class IepPath:
#     def __init__(self, path):
#         
#         # Normalize and check success
#         self._path = normalizePath(path)
#         if self._path is None:
#             raise ValueError("Invalid path")
#     
#     @property
#     def path(self):
#         """ The full (normalized) path of this file or project. 
#         """
#         return self._path
# 
# 
# # todo: OR DO I ONLY NEED AN EDITOR FOR THIS???
# class IepFile(IepPath):
#     """ IepFile()
#     
#     Represents an open document.
#     The file is initially not read from disk (lazy loading).
#     """ 
#     
#     def __init__(self, path):
#         IepPath.__init__(self, path)
#         
#         self._editor = None
#         # todo: store stuff that editor stores here.
#         # Also methods such as save etc?
#     
#     
#     @property
#     def editor(self):
#         """ The editor in which this file is loaded. 
#         """
#         return self._editor
# 
# 
# 
# class IepProject:
#     """ IepProject(path)
#     
#     represents a project to group files. 
#     In most cases, this represents a directory.
#     """
#     
#     def __init__(self, path):
#         IepPath.__init__(self, path)
#         
#         # Store
#         self._normal = True
#         
#         # todo: make subclasses for these special cases
#         # Check
#         if path in [PROJECT_ALL, PROJECT_LOOSE]:
#             # lists of all files or list of files not in any other project
#             self._normal = False
#         elif not os.path.isdir(path):
#             raise ValueError('Invalid directory')
#     
#     
#     



class Item(qt.QLabel):
    """ Base Item class, items for a list of files and projects.
    Some of the styling is implemented here. An item instance 
    directly represents the file or project, but also its 
    asociated widget (and thus appearance).
    """
    
    def __init__(self, parent):
        qt.QLabel.__init__(self, parent)
       
        # indicate height and spacing
        self._itemHeight = 16
        self._itemSpacing = iep.config.advanced.editorStackBarSpacing
        
        # set indent and size        
        self._indent = 1
        self._y = 1
        self.resize(barwidth-self._indent, self._itemHeight)
        
        # test framewidths when raised
        self.setLineWidth(1)
        self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
        self._frameWidth = self.frameWidth() + 3 # correction        
        
        # Enable receiving the mouse move event always
        self.setMouseTracking(True)
        
        # To accept dropping
        self.setAcceptDrops(True)
    
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """ Drop files in the list. """
        # let the editorstack do the work.
        event._y = self._y + event.pos().y()
        self.parent().dropEvent(event)
    
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
        if not event.buttons():
            QtGui.QToolTip.showText(QtGui.QCursor.pos(), self.toolTip())
        else:
            self.parent().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.parent().mouseReleaseEvent(event)
    

class ProjectItem(Item):
    """ An item representing a project. """
    
    def __init__(self, parent, iepProject):
        Item.__init__(self, parent)
        
        # Projects have more spacing
        self._itemSpacing = 2 + iep.config.advanced.editorStackBarSpacing
        
        # Store iepProject instance and its name
        self._iepProject = iepProject
        self._name = os.path.split(IepProject.path)[1]
        
        # Set of file items
        self._items = set()
        
        # The main iepFile instance
        self._mainFile = None
        
        # collapsed?
        self._collapsed = False
        
        # update
        self.setStyleSheet("ProjectItem { font:bold; background:#999; }")
        self.updateTexts()
        self.updateStyle()
    
    
    def updateTexts(self):
        """ Update the text and tooltip """        
        if self._collapsed:
            self.setText('- {} ({})'.format(self._name, len(self._items)))
        else:
            self.setText('+ {}'.format(self._name))
        self.setToolTip('project '+ self._name + ': ' + self._iepProject.path)
    
    
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
    
    
    def selectFiles(self, iepFiles):
        """ selectFiles(self, iepFiles)
        
        Given a set of iepFiles, returns the subset of files that belong
        to this project.
        """
        
        # Fill subset
        subSet = set()
        for file in iepFiles:
            if file.path.startswith(self.path):
                subSet.add(file)
        
        # Done
        return subSet
    
    
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
        """ move project up (-1) or down (+1)
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
    
    def __init__(self, parent, projectItem, iepFile):
        Item.__init__(self, parent)
        
        # Store iepFile instance
        self._iepFile = iepFile
        
        # To keep name and tooltip up to date
        self._iepFile.editor.somethingChanged.connect(self.updateTexts)
        
        # each file item belongs to a project item
        self._projectItem = projectItem
        
        # set style
        self.setAutoFillBackground(True)
        
        # update
        self.updateTexts()
        self.updateStyle()
    
    
    def isMainFile(self):
        """ Returns whether this is the main file of a project. """ 
        return self._projectItem._mainFile is self._iepFile
    
    
    def updateTexts(self):
        """ Updates the text of the label and tooltip. Called when 
        the editor's dirty status changed or when saved as another file. 
        """
        # get texts
        name = self._iepFile._editor._name
        filename = self._iepFile._editor._filename
        # prepare texts
        if self._editor._dirty:
            name = '*' + name
        if not filename: 
            filename = '<temporary file>'        
        # get whether this is the project main file
        if self.isMainFile():
            toolTipText = "project's main file: " + filename
        else:
            toolTipText = 'file: '+ filename
        # apply
        self.setText(name)
        self.setToolTip(toolTipText)
        self.updateStyle()
    
    
    def updateStyle(self):
        """ Update the style. To indicate selected file or hoovering over one.
        Need to update position, because the frame width is different for
        the different scenarios."""
        
        # Init style
        style = ''
        
        isMain = self.isMainFile()
        isCurrent = self is self.parent()._currentItem
        
        # Set style to handle dirty and mainfile
        if self._editor._dirty:
            style += "color:#603000;"
        if isMain:
            style += 'font: bold;'
        if isCurrent:
            style += 'background:#CEC;'
        
        # Set frames sunken or raised
        if isCurrent:
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Sunken)
            self.move(self._indent ,self._y)
        elif self.underMouse():
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
            self.move(self._indent ,self._y)
            # Can flicker on gtk if isMain, but solving by correcting
            # indentation makes it flicker on windows :)
        else:
            self.setFrameStyle(0)
            self.move(self._frameWidth+self._indent,self._y)
        
        # Set style
        self.setStyleSheet("QLabel{" + style + "}")
    
    
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
            if self.isMainFile():
                menu.addAction('Unmake main file', self.context_makeMain)
            else:
                menu.addAction('Make main file', self.context_makeMain)
            menu.popup(event.globalPos())
    
    def context_save(self, event=None):
        self.parent().parent().saveFile(self._editor)
    def context_saveAs(self, event=None):
        self.parent().parent().saveFileAs(self._editor)
    def context_close(self, event=None):
        self.parent().parent().closeFile(self._editor)
    def context_makeMain(self, event=None):
        if self._projectItem:
            if self.isMainFile():
                self._projectItem._mainFile = None
            else:
                self._projectItem._mainFile = self._iepFile
        else:
            m = QtGui.QMessageBox(self)
            m.setWindowTitle("Project main file")
            m.setText(  "Cannot make this the project main file, " +
                        "because this file is not in a project.")
            m.setIcon(m.Information)
            m.exec_()
        #
        for item in self.parent()._items:
            if isinstance(item, FileItem):
                item.updateTexts()
    

class FileListCtrl(QtGui.QFrame):
    """ Control that displays a list of files using Labels.
    """
    
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        # store editorstack
        self._editorStack = parent
        
        # set width
        self.setMinimumWidth(barwidth)
        self.setMaximumWidth(barwidth)
        
        # create scrollbar to scroll
        self._scroller = QtGui.QScrollBar(self)
        self._scroller.setOrientation(QtCore.Qt.Horizontal)
        self._scroller.resize(barwidth, 15)
        self._scroller.setRange(0,200)
        self._scroller.setSingleStep(10)
        self._scroller.setValue(0)
        
        # create list of iep docs and matching items
        # todo: _items or _docs?
        self._files = []
        self._projectItems = []
        self._currentItem = None
        self._itemHistory = []
        
        # enable dragging/dropping
        self.setAcceptDrops(True)
        # for dragging file items
        self._draggedItem = None
        self._dragStartPos = QtCore.QPoint(0,0)
        # for dropping files
        self._droppedIndex = 0
        self._droppedTime = time.time()-1.0
        
        # set callbacks
        self._scroller.valueChanged.connect(self.updateMe)
    
    
    
    ## Events and dragging
    
    def resizeEvent(self, event):
        QtGui.QFrame.resizeEvent(self, event)
        self.updateMe()
    
    
    def wheelEvent(self, event):
        """ Allow the user to scroll the file list. """
        # Determine amount of pixels to scroll
        degrees = event.delta() / 8
        steps = degrees / 15
        deltaPixels = steps * 16
        self._scroller.setValue( self._scroller.value() - deltaPixels)
    
    
    def mouseReleaseEvent(self, event):
        # stop dragging
        self._draggedItem = None        
        # update
        self.updateMe()
    
    
    def mouseMoveEvent(self, event):
        # check for mouse and moved enough
        
        if not event.buttons() & QtCore.Qt.LeftButton:
            return
            
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
    
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    
    def dropEvent(self, event):
        """ Drop files/directories in the list. """
        
        # get y position
        if hasattr(event, '_y'):
            yd = event._y
        else:
            yd = event.pos().y()
        
        # determine where to place the item
        i_to_put = None
        for i in range(len(self._items)):
            item = self._items[i]
            y = item._y + item._itemHeight + item._itemSpacing
            if item.isVisible() and y > yd:
                i_to_put = i
                break
        
        # post process
        if yd < self._items[0]._y:
            i_to_put = 0
        elif i_to_put is None:
            # put at the end
            i_to_put = len(self._items)
        elif isinstance(self._items[i_to_put], ProjectItem):
            # if a project item, insert as first item in that project.
            if i_to_put < len(self._items) -1:
                i_to_put += 1
        
        # make the item be inserted here
        self._droppedIndex = i_to_put
        self._droppedTime = time.time()
        
        # let the editorstack do the loading,
        # which calls our appendFile, where we can put it in the
        # right place.
        self._editorStack.dropEvent(event)
    
    
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
    
    
    def _doDrag(self, event):
        
        # determine new position
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
   
    
    ## Updating etc.
    
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
                project = item
                if project._collapsed:
                    ncollapsed = 0
            elif isinstance(item, FileItem):
                item._projectItem = project
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
    
    
    def appendFile(self, editor):
        """ Create file item. 
        Returns the created file item on success."""
        
        # default insert position is at the end
        i_insert = len(self._files)
        
        # should we put it at the dropped position?
        if time.time() - self._droppedTime < 0.25:
            i_insert = self._droppedIndex
            self._droppedTime = time.time() # when multiple files are inserted
        
        # create document
        iepFile = IepFile(editor)
        self._docs.insert(i_insert, iepFile)
        
        # make it current
        self.setCurrentItem(item)
        
        return iepFile
    
    
    def _createItemForFile(self, iepFile):
        
        
    
    def appendProject(self, projectname):
        """ Create project Item. 
        Return the project item if all went well."""
        
        # stop if already a project with that name
        for item in self._items:            
            if isinstance(item,ProjectItem) and item._name == projectname:
                print("Cannot load dir: a project with that name "\
                    "already exists!" )                  
                return None
        
        # disable the insert location for dropping
        self._droppedTime = time.time()-1.0
        
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
    
    
    ## Context menu 
        
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
    
    
    


class EditorTabs:
    pass


if __name__ == '__main__':
    
    app = QtGui.QApplication([])
    flc = FileListCtrl()
    flc.show()
    app.exec_()
    