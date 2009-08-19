""" EditorBook class (implemented in qt)
"""

import os, sys, time, gc

from PyQt4 import QtCore, QtGui
qt = QtGui

from editor import IepEditor
from baseTextCtrl import styleManager
barwidth = 120


def normalizePath(path):
    """ Normalize the path given. 
    All slashes will be made the same (and doubles removed)
    The real case as stored on the file system is recovered.
    """
    
    # normalize
    path = os.path.abspath(path)  # make sure it is defined from the drive up
    path = os.path.normpath(path).lower() # make all os.sep (slashes \\ on win)
    
    # split in parts
    parts = path.split(os.sep)
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
            raise Exception("Ambiguous path names!")
        elif len(options) < 1:
            raise Exception("Invalid path!")
        fullpath += options[0] + sep
    
    # remove last sep
    return fullpath[:-len(sep)]


def determineLineEnding(text):
    """get the line ending style used in the text.
    \n, \r, \r\n,
    The EOLmode is determined by counting the occurances of each
    line ending...    
    """
    # test line ending by counting the occurances of each
    c_win = text.count("\r\n")
    c_mac = text.count("\r") - c_win
    c_lin = text.count("\n") - c_win
    
    # set the appropriate style
    if c_win > c_mac and c_win > c_lin:
        mode = '\r\n'
    elif c_mac > c_win and c_mac > c_lin:            
        mode = '\r'
    else:
        mode = '\n'
    
    # return
    return mode


class Item(qt.QLabel):
    """ Base Item class, items for a list of files and projects.
    Some of the styling is implemented here. An item instance 
    directly represents the file or project, but also its 
    asociated widget (and thus appearance).
    """
    
    def __init__(self, parent):
        qt.QLabel.__init__(self,parent)
       
        # init name
        self._name = ''
        
        # set indent and size        
        self._indent = 1
        self._y = 1
        self.resize(barwidth-self._indent, self.parent()._itemSpacing)
        
        # test framewidths when raised
        self.setLineWidth(1)
        self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
        self._frameWidth = self.frameWidth() + 3 # correction        

    
    
    def setIndent(self, indent):
        """ Set the indentation of the item. """
        self._indent = indent
        self.resize(barwidth-self._indent, self.parent()._itemSpacing)
        
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
        
        # set name and tooltip
        self._name = name
        self.setText(name)
        self.setToolTip('project: '+ name)
        
        # collapsed?
        self._collapsed = False
        
        # update
        self.setStyleSheet("ProjectItem { font:bold; background:#999; }")
        self.updateStyle()
    
    
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
        if event.button() == QtCore.Qt.LeftButton:
            self._collapsed = not self._collapsed
            self.parent().updateMe()


class FileItem(Item):
    """ An item representing a file. This class does the loading 
    and saving of that file, but without any checks, that is up to
    the editorbook. """
    
    def __init__(self, parent, filename=None):
        Item.__init__(self, parent)
        
        # get editorbook
        editorBook = parent.parent()
        
        # init stuff
        self._lineEndings = '\n' # line ending on disk (internally all's \n)
        self._name = '' # the displayed name
        self._filename = '' # the full path to the file on disk
        self._editor = None # wait with creating it untill we loaded the file
        
        if filename:
            # check
            if not os.path.isfile(filename):
                raise IOError("File does not exist '%s'." % filename)
            
            # load file
            with open(filename, 'rb') as f:
                bb = f.read()
                f.close()
            
            # convert to text
            text = bb.decode('UTF-8')
            
            # process line endings
            self._lineEndings = determineLineEnding(text)
            text = text.replace('\r\n','\n').replace('\r','\n')
            
            # create edior and set text
            self._editor = editorBook.createEditor()
            self._editor.setText(text)
            self._editor.makeDirty(False)
            self._editor.dirtyChange.connect(self.parent().updateMe)
            
            # set name and tooltip
            self._filename = filename
            self._name = os.path.split(filename)[1]
            self.setText(self._name)
            self.setToolTip('file: '+ filename)
        else:
            # create editor
            self._editor = editorBook.createEditor()
            # set name and tooltip
            self._filename = None
            self._name = '*<TMP>'  
            self.setText(self._name)          
            self.setToolTip('file: None')
        
        # set style
        self.setAutoFillBackground(True)
        
        # update
        self.updateStyle()
    
    
    def makeMain(self, main):
        """ Make the file appear as a main file """
        if main:       
            self.setStyleSheet("QLabel { font:bold ; color:blue }")
        else:
            self.setStyleSheet("QLabel { font: ; color: }")
    
    
    def updateStyle(self):
        """ Update the style. Automatically detects whether the mouse
        is over the label. Depending on the type and whether the file is
        selected, sets its appearance and redraw! """
        if self._editor._dirty:
            self.setText( "*"+self._name )
            self.setStyleSheet("QLabel { color:#603000 }")
        else:
            self.setText( self._name )
            self.setStyleSheet("")
        #
        if self is self.parent()._currentItem:
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Sunken)
            self.move(self._indent ,self._y)
        elif self.underMouse():
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
            self.move(self._indent ,self._y)
        else:
            self.setFrameStyle(0)
            self.move(self._frameWidth+self._indent,self._y)
    
    
    def mousePressEvent(self, event):
        
        # select this item! 
        self.parent().setCurrentItem(self)
        
        if event.button() == QtCore.Qt.LeftButton:
            # change stuff at parent to get the dragging right
            x, y = event.globalX(), event.globalY()
            self.parent()._dragStartPos = QtCore.QPoint(x,y)
        
        elif event.button() == QtCore.Qt.RightButton:
            # popup menu
            menu = QtGui.QMenu(self)
            menu.addAction('save file', self.receiver)
            menu.addAction('save file as', self.receiver)
            menu.popup(event.globalPos())
    
    def receiver(self, event=None):
        print( "woohaa", event)
        
    def mouseDoubleClickEvent(self, event):
        #self.parent().parent().saveFile(self)
        self.parent().parent().closeFile(self)
    
    
    def save(self, filename):
        """ Save the file. No checking is done. """
        
        # get text and convert line endings
        text = self._editor.getText()
        text = text.replace('\n', self._lineEndings)
        
        # make bytes
        bb = text.encode('UTF-8')
        
        # store
        f = open(filename, 'wb')
        try:
            f.write(bb)
        finally:
            f.close()
        
        # update stats
        self._filename = normalizePath(filename)
        self._name = os.path.split(filename)[1]
        self.setText(self._name)
        self.setToolTip('file: '+ filename)
        self._editor.makeDirty(False)
    
    
    def close(self):
        """ Destroy myself. """        
        # hide
        self.hide()
        self._editor.hide()        
        # clear from parent        
        for items in [self.parent()._items, self.parent()._itemHistory]:
            while self in items:  
                items.remove(self)
        # select other editor (also removes from editorbook's boxlayout)
        if self.parent()._currentItem is self:
            self.parent().setCurrentItem(None, False)        
        # destroy...
        self._editor.destroy()
        self.destroy()
        gc.collect()
    

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
        self._itemSpacing = 15
        
        # enable dragging/dropping
        self.setAcceptDrops(True)
        self._draggedItem = None
        self._dragStartPos = QtCore.QPoint(0,0)
        
        #self.updateMe()
    
    
    def updateMe(self):
        
        project = None
        ncollapsed = 0
        
        y = 10  # initial y position
        for item in self._items:            
            item._y = y
            if isinstance(item, ProjectItem):
                # handle previous collapsed project?
                if project and project._collapsed:
                    project.setText('- %s (%i)' % (project._name, ncollapsed))
                project = item
                if project._collapsed:
                    ncollapsed = 0
                    # give text at the end
                else:
                    item.setText('+ '+item._name)
            elif isinstance(item, FileItem):
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
            
            # update item
            y += self._itemSpacing # next item
            item.updateStyle()
            item.show()
        
        # handle last collapsed project
        if project and project._collapsed:
            project.setText('- %s (%i)' % (project._name, ncollapsed))
        
        # update screen
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
        
        # finish
        self.updateMe()
    
    
    def mouseReleaseEvent(self, event):
        # stop dragging
        self._draggedItem = None
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
        y2 = self._itemSpacing/2
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
   
   
    def appendFile(self, filename=None, projectname=None):
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
        item = FileItem(self, filename)
        self._items.insert(i_insert,item)
        
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
    

class EditorBook(QtGui.QWidget):
    
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        # keep a booking of opened directories
        self._lastpath = ''
        
        # create widgets
        self._list = FileListCtrl(self)
        self._panel = QtGui.QFrame(self)
        
        # create box layout control and add widgets
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout.addWidget(self._list, 0)
        self._boxLayout.addWidget(self._panel, 1)
        
        # make the box layout the layout manager
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
    
    def createEditor(self):
        """ Create and return an editor instance. """
        editor = IepEditor(self)
        editor.hide()
        self._boxLayout.addWidget(editor, 1)
        return editor
    
    
    def showEditor(self, editor=None):
        """ Show the given editor. """
        
        # clear all but the left list
        while self._boxLayout.count() > 1:
            thing = self._boxLayout.takeAt(self._boxLayout.count()-1)
            thing.widget().hide()
        
        # show new thing
        if editor is None:
            editor = self._panel
        self._boxLayout.addWidget(editor,1)
        editor.show()
    
    
    def getCurrentItem(self):
        """ Get the currently active file item. """
        return self._list._currentItem
    
    def getCurrentEditor(self):
        """ Get the currently active editor. """
        item = self._list._currentItem
        if item:
            return item._editor
    
    
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
        self._list.appendFile(None, projectname)
    
    
    def openFile(self, projectname=None):
        """ Create a dialog for the user to select a file. """
        
        # determine start dir
        item = self.getCurrentItem()
        if item and item._filename:
            startdir = os.path.split(item._filename)[0]
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
        item = self.getCurrentItem()
        if item and item._filename:
            startdir = os.path.split(item._filename)[0]
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
        
        # get real path name
        filename = normalizePath(filename)
        
        # store the path
        self._lastpath = os.path.dirname(filename)
        
        # create item
        self._list.appendFile(filename, projectname)
    
    
    def loadDir(self, path, extensions="py,pyw"):
        """ Create a project with the dir's name and add all files
        contained in the directory to it.
        extensions is a komma separated list of extenstions of files
        to accept...        
        """
        
        # if the path does not exist, stop        
        if not os.path.isdir(path):
            print("ERROR loading dir: the specified directory does not exist!")
            return
        
        # normalize path name and get extensions
        path = normalizePath(path)
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
    
    
    def saveFileAs(self, item=None):
        """ Create a dialog for the user to select a file. """
        
        # get item
        if item is None:
            item = self.getCurrentItem()
        if item is None:
            return
        
        # get startdir
        if item._filename:
            startdir = os.path.dirname(item._filename)
        else:
            startdir = self._lastpath            
        if not os.path.isdir(startdir):
            startdir = ''
        
        # show dialog
        msg = "Select the file to save to"
        filter = "Python (*.py *.pyw);;Pyrex (*.pyi,*.pyx);;All (*.*)"
        filename = QtGui.QFileDialog.getSaveFileName(self,
            msg, startdir, filter)
        
        # proceed
        self.saveFile(item, filename)
    
    
    def saveFile(self, item=None, filename=None):
        
        # get item
        if item is None:
            item = self.getCurrentItem()
        if item is None:
            return
        
        # get filename
        if filename is None:
            filename = item._filename
        if not filename:
            self.saveFileAs(item)
            return
        
        # let the item do the low level stuff...
        try:
            item.save(filename)
        except IOError as err:
            print("Could not save file:",err)
            return
        
        # notify
        tmp = {'\n':'LF', '\r':'CR', '\r\n':'CRLF'}[item._lineEndings]
        print("saved file: {} ({})".format(filename, tmp))
        
        # special case, we edited the style file!
        if item._filename == styleManager._filename:
            # reload styles
            styleManager.loadStyles()
            # editors are send a signal by the style manager
    
    
    def closeFile(self, item=None):
        """ Close the selected (or current) item. 
        Returns True if all went well, False if the user pressed cancel
        when asked to save an modified file. """
        
        # get item
        if item is None:
            item = self.getCurrentItem()
        if item is None or not isinstance(item, FileItem):
            return
        
        # should we ask to save the file?
        if item._editor._dirty:
            
            # setup dialog
            dlg = QtGui.QMessageBox(self)
            dlg.setText("Closing file:\n{}".format(item._filename))
            dlg.setInformativeText("Save modified file?")
            tmp = QtGui.QMessageBox
            dlg.setStandardButtons(tmp.Save| tmp.Discard | tmp.Cancel)
            dlg.setDefaultButton(tmp.Cancel)
            
            # get result and act
            result = dlg.exec_() 
            if result == tmp.Save:
                self.saveFile(item)
            elif result == tmp.Cancel:
                return False
        
        # ok, close...
        item.close()
        self._list.updateMe()
        return True
        

if __name__ == "__main__":
    #qt.QApplication.setDesktopSettingsAware(False)
    app = QtGui.QApplication([])
    app.setStyle("windows") # plastique, windows, cleanlooks
    win = EditorBook(None)
    win.show()
    app.exec_()
