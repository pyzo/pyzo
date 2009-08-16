""" EditorBook class (implemented in qt)
"""

import os, sys, time

from PyQt4 import QtCore, QtGui
qt = QtGui

from editor import IepEditor

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

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            x, y = event.globalX(), event.globalY()
            self.parent()._dragStartPos = QtCore.QPoint(x,y)
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
    and saving of that file. """
    
    def __init__(self, parent, filename):
        Item.__init__(self, parent)
        
        # check
        if not os.path.isfile(filename):
            raise IOError("File does not exist '%s'." % filename)
        
        # load file
#         f = open(filename, 'rb')
#         bb = f.read()
#         f.close()
#         
#         # convert to text
#         text = bb.decode('UTF-8')
        # todo: newlines and tabs etc
        #self._editor = scintilla()
        
        # set name and tooltip
        self._filename = filename
        self._name = os.path.split(filename)[1]
        self.setText(self._name)
        self.setToolTip('file: '+ filename)
        
        # set style
        self.setAutoFillBackground(True)
        
        # update
        self.updateStyle()
    
    
    def makeDirty(self, dirty):        
        """ Indicate that the file is dirty """
        self.setText( "*"+self.text() )
        self.setStyleSheet("QLabel { color:#603000 }")
    
    
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
        if self is self.parent()._currentItem:
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Sunken)
            self.move(self._indent ,self._y)
        elif self.underMouse():
            self.setFrameStyle(qt.QFrame.Panel | qt.QFrame.Raised)
            self.move(self._indent ,self._y)
        else:
            self.setFrameStyle(0)
            self.move(self._frameWidth+self._indent,self._y)


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
        self._itemSpacing = 15
        
        # enable dragging/dropping
        self.setAcceptDrops(True)
        self._draggedItem = None
        self._dragStartPos = QtCore.QPoint(0,0)
        
        # put some files in 
        self.loadFile(r'C:\projects\PYTHON\iep2\iep.py')
        self.loadFile(r'C:\projects\PYTHON\iep2\shell.py')
        self.loadDir(r'C:\projects\PYTHON\tools')
        self.loadDir(r'C:\projects\PYTHON\tools\visvis')
        self.updateMe()
    
    
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
    
    
    def mousePressEvent(self, event):
        pass
    
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
    
    
    def openFile(self):
        print("open file")
        
       
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
        #path = str( qurl.path()[1:] )
        
        #print("you dropped something!", qurls, qurls[-1])
    
    
    def loadFile(self, filename, projectname=None):
        """ Load the specified file. """
        # get real path name
        filename = normalizePath(filename)
        
        # create item
        item = FileItem(self, filename)
        self._items.append(item)
        
        # update
        self.updateMe()
    
    
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
        
        # get dirname -> is projectname 
        projectname = str( os.path.basename(path) )
        # stop if already a project with that name
        for item in self._items:            
            if isinstance(item,ProjectItem) and item._name == projectname:
                print("Cannot load dir: a project with that name "\
                    "already exists!" )                  
                return
                
        # create project at the end
        self._items.append(ProjectItem(self, projectname))
        #print("Creating project: %s" % (projectname))
        
        window = None
        
        # open all qualified files...
        self.setUpdatesEnabled(False)
        try:
            filelist = os.listdir(path)
            for filename in filelist:
                filename = os.path.join(path,filename)
                ext = os.path.splitext(filename)[1]            
                if str(ext) in extensions:
                    window = self.loadFile(filename,projectname)
        finally:
            self.setUpdatesEnabled(True)
            self.updateMe()
        return window
    

class EditorBook(QtGui.QWidget):
    
    def __init__(self, parent):
        qt.QWidget.__init__(self,parent)
        
        # create widgets
        self._list = FileListCtrl(self)
        editor = IepEditor(self)
        editor.setStyle('.py')
        
        # create box layout control and add widgets
        self._boxLayout = QtGui.QHBoxLayout(self)
        self._boxLayout.addWidget(self._list, 0)
        self._boxLayout.addWidget(editor, 1)
        
        # make the box layout the layout manager
        self.setLayout(self._boxLayout)
        
        #self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips,True)
    
    
if __name__ == "__main__":
    #qt.QApplication.setDesktopSettingsAware(False)
    app = QtGui.QApplication([])
    app.setStyle("cleanlooks") # plastique, windows
    win = EditorBook(None)
    win.show()
    app.exec_()
