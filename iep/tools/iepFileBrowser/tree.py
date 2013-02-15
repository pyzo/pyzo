# -*- coding: utf-8 -*-
# Copyright (C) 2012 Almar Klein

""" 
Defines the tree widget to display the contents of a selected directory.
"""


import os
import sys
import fnmatch
from pyzolib.path import Path

from PySide import QtCore, QtGui
import iep
from iep import translate

from .tasks import SearchTask, DocstringTask
from .utils import hasHiddenAttribute, getMounts

# How to name the list of drives/mounts (i.e. 'my computer')
MOUNTS = 'drives'


# Create icon provider
iconprovider = QtGui.QFileIconProvider()


def addIconOverlays(icon, *overlays, offset=8):
    """ Create an overlay for an icon.
    """
    # Create painter and pixmap
    pm0 = QtGui.QPixmap(24,16)#icon.pixmap(16+offset,16)
    pm0.fill(QtGui.QColor(0,0,0,0))
    painter = QtGui.QPainter()
    painter.begin(pm0)
    # Draw original icon
    painter.drawPixmap(offset, 0, icon.pixmap(16,16))
    # Draw overlays
    for overlay in overlays:
        pm1 = overlay.pixmap(16,16)
        painter.drawPixmap(0,0, pm1)
    # Finish
    painter.end()
    # Done (return resulting icon)
    return QtGui.QIcon(pm0)



def _filterFileByName(basename, filter):
    
    # Get the current filter spec and split it into separate filters
    filters = filter.replace(',', ' ').split()
    filters = [f for f in filters if f]
    
    # Init default; return True if there are no filters
    default = True
    
    for filter in filters:
        # Process filters in order
        if filter.startswith('!'):
            # If the filename matches a filter starting with !, hide it
            if fnmatch.fnmatch(basename,filter[1:]):
                return False
            default = True
        else:
            # If the file name matches a filter not starting with!, show it
            if fnmatch.fnmatch(basename, filter):
                return True
            default = False
    
    return default


def createMounts(browser, tree):
    """ Create items for all known mount points (i.e. drives on Windows).
    """
    fsProxy = browser._fsProxy
    
    mountPoints = getMounts()
    mountPoints.sort(key=lambda x: x.lower())
    for entry in mountPoints:
        entry = Path(entry)
        item = DriveItem(tree, fsProxy.dir(entry))


def createItemsFun(browser, parent):
    """ Create the tree widget items for a Tree or DirItem.
    """
    
    # Get file system proxy and dir proxy for which we shall create items
    fsProxy = browser._fsProxy
    dirProxy = parent._proxy
    
    # Get meta information from browser
    nameFilter = browser.nameFilter()
    searchFilter = browser.searchFilter()
    searchFilter = searchFilter if searchFilter['pattern'] else None
    expandedDirs = browser.expandedDirs
    starredDirs = browser.starredDirs
    
    
    # Filter the contents of this folder
    try:
        dirs = []
        for entry in dirProxy.dirs():
            entry = Path(entry)
            if entry.basename.startswith('.'):
                continue # Skip hidden files
            if hasHiddenAttribute(entry):
                continue # Skip hidden files on Windows
            if entry.basename == '__pycache__':
                continue
            dirs.append(entry)
        
        files = []
        for entry in dirProxy.files():
            entry = Path(entry)
            if entry.basename.startswith('.'):
                continue # Skip hidden files
            if hasHiddenAttribute(entry):
                continue # Skip hidden files on Windows
            if not _filterFileByName(entry.basename, nameFilter):
                continue
            files.append(entry)
    
    except (OSError, IOError) as err:
        ErrorItem(parent, str(err))
        return 
    
    # Sort dirs (case insensitive)
    dirs.sort(key=lambda x: x.lower())
    
    # Sort files 
    # (first by name, then by type, so finally they are by type, then name)
    files.sort(key=lambda x: x.lower())
    files.sort(key=lambda x: x.ext.lower())
        
    
    if not searchFilter:
        
        # Create dirs 
        for path in dirs:
            starred = path.normcase() in starredDirs
            item = DirItem(parent, fsProxy.dir(path), starred)
            # Set hidden, we can safely expand programmatically when hidden
            item.setHidden(True)
            # Set expanded and visibility
            if path.normcase() in expandedDirs:
                item.setExpanded(True)
            item.setHidden(False)
        
        # Create files        
        for path in files:
            item = FileItem(parent, fsProxy.file(path))
    
    else:
        
        # If searching, inject everything in the tree
        # And every item is hidden at first
        parent = browser._tree
        if parent.topLevelItemCount():
            searchInfoItem = parent.topLevelItem(0)
        else:
            searchInfoItem = SearchInfoItem(parent)
        
        # Increase number of found files
        searchInfoItem.increaseTotal(len(files))
        
        # Create temporary file items
        for path in files:
            item = TemporaryFileItem(parent, fsProxy.file(path))
            item.search(searchFilter)
        
        # Create temporary dir items
        if searchFilter['subDirs']:
            for path in dirs:
                item = TemporaryDirItem(parent, fsProxy.dir(path))
    
    
    # Return number of files added
    return len(dirs) + len(files)



class BrowserItem(QtGui.QTreeWidgetItem):
    """ Abstract item in the tree widget.
    """
    
    def __init__(self, parent, pathProxy, *args):
        self._proxy = pathProxy
        QtGui.QTreeWidgetItem.__init__(self, parent, [], *args)
        # Set pathname to show, and icon
        strippedParentPath = parent.path().rstrip('/\\')
        if self.path().startswith(strippedParentPath):
            basename = self.path()[len(strippedParentPath)+1:]
        else:
            basename = self.path() #  For mount points
        self.setText(0, basename)
        self.setFileIcon()
        # Setup interface with proxy
        self._proxy.changed.connect(self.onChanged)
        self._proxy.deleted.connect(self.onDeleted)
        self._proxy.errored.connect(self.onErrored)
    
    def path(self):
        return self._proxy.path()
    
    def _createDummyItem(self, txt):
        ErrorItem(self, txt)
        #QtGui.QTreeWidgetItem(self, [txt])
    
    def onDestroyed(self):
        self._proxy.cancel()
    
    def clear(self):
        """ Clear method that calls onDestroyed on its children.
        """
        for i in reversed(range(self.childCount())):
            item = self.child(i)
            if hasattr(item, 'onDestroyed'):
                item.onDestroyed()
            self.removeChild(item)
    
    
    # To overload ...
    
    def onChanged(self):
        pass
    
    def onDeleted(self):
        pass
    
    def onErrored(self, err):
        self.clear()
        self._createDummyItem('Error: ' + err)



class DriveItem(BrowserItem):
    """ Tree widget item for directories.
    """
    
    def __init__(self, parent, pathProxy):
        BrowserItem.__init__(self, parent, pathProxy)
        # Item is not expandable
    
    def setFileIcon(self):
        # Use folder icon
        self.setIcon(0, iep.icons.drive)


class DirItem(BrowserItem):
    """ Tree widget item for directories.
    """
    
    def __init__(self, parent, pathProxy, starred=False):
        self._starred = starred
        BrowserItem.__init__(self, parent, pathProxy)
        
        # Create dummy item so that the dir is expandable
        self._createDummyItem('Loading contents ...')
    
    def setFileIcon(self):
        # Use folder icon
        icon = iconprovider.icon(iconprovider.Folder)
        overlays = []
        if self._starred:
            overlays.append(iep.icons.overlay_star)
        icon = addIconOverlays(icon, *overlays)
        self.setIcon(0, icon)
    
    def onExpanded(self):
        # Update list of expanded dirs
        expandedDirs = self.treeWidget().parent().expandedDirs
        p = self.path().normcase()  # Normalize case!
        if p not in expandedDirs:
            expandedDirs.append(p) 
        # Keep track of changes in our contents
        self._proxy.track()
        self._proxy.push()
    
    def onCollapsed(self):
        # Update list of expanded dirs
        expandedDirs = self.treeWidget().parent().expandedDirs
        p = self.path().normcase()   # Normalize case!
        while p in expandedDirs:
            expandedDirs.remove(p)
        # Stop tracking changes in our contents
        self._proxy.cancel()
        # Clear contents and create a single placeholder item
        self.clear()
        self._createDummyItem('Loading contents ...')
    
    
    # No need to implement onDeleted: the parent will get a changed event.
    
    def onChanged(self):
        """ Called when a change in the contents has occured, or when
        we just activated the proxy. Update our items!
        """
        if not self.isExpanded():
            return
        tree = self.treeWidget()
        tree.createItems(self)



class FileItem(BrowserItem):
    """ Tree widget item for files.
    """
    
    def __init__(self, parent, pathProxy):
        BrowserItem.__init__(self, parent, pathProxy)
        self._proxy.taskFinished.connect(self.onTaskFinished)
    
    def setFileIcon(self):
        # Create dummy file in iep user dir
        dummy_filename = Path(iep.appDataDir) / 'dummyFiles' / 'dummy' + self.path().ext
        # Create file?
        if not dummy_filename.isfile:
            if not dummy_filename.dirname.isdir:
                os.makedirs(dummy_filename.dirname)
            f = open(dummy_filename, 'wb')
            f.close()
        # Use that file
        icon = iconprovider.icon(QtCore.QFileInfo(dummy_filename))
        icon = addIconOverlays(icon)
        self.setIcon(0, icon)
    
    def searchContents(self, needle, **kwargs):
        self.setHidden(True)
        self._proxy.setSearch(needle, **kwargs)
    
    def onClicked(self):
        if self.path().lower().endswith('.py'):
            self._proxy.pushTask(DocstringTask())
    
    def onChanged(self):
        pass
    
    def onTaskFinished(self, task):
        if isinstance(task, DocstringTask):
            result = task.result()
            if result:
                #self.setToolTip(0, result)
                # Show tooltip *now* if mouse is still over this item
                tree = self.treeWidget()
                pos = tree.mapFromGlobal(QtGui.QCursor.pos())
                if tree.itemAt(pos) is self:
                    QtGui.QToolTip.showText(QtGui.QCursor.pos(), result)


class SearchItem(QtGui.QTreeWidgetItem):
    """ Tree widget item for search items.
    """
    def __init__(self, parent, text):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.setText(0, text)
    
    def path(self):
        return self.parent().path()



class ErrorItem(QtGui.QTreeWidgetItem):
    """ Tree widget item for errors and information.
    """
    def __init__(self, parent, info):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.setText(0, info)
        self.setFlags(QtCore.Qt.NoItemFlags)
        font = self.font(0)
        font.setItalic(True)
        self.setFont(0, font)
    


class SearchInfoItem(ErrorItem):
    """ Tree widget item that displays info on the search.
    """
    def __init__(self, parent):
        ErrorItem.__init__(self, parent, 'Searching ...')
        self._totalCount = 0
        self._checkCount = 0
        self._hitCount = 0
    
    def increaseTotal(self, c):
        self._totalCount += c
        self.updateCounts()
    
    def addFile(self, hit):
        self._checkCount += 1
        if hit:
            self._hitCount += 1
        # Update appearance
        self.updateCounts()
    
    def updateCounts(self):
        counts = self._checkCount, self._totalCount, self._hitCount
        self.setText(0, 'Searched {}/{} files: {} hits'.format(*counts))



class TemporaryDirItem:
    """ Created when searching. This object posts a requests for its contents
    which are then processed, after which this object disbands itself.
    """
    __slots__ = ['_tree', '_proxy', '__weakref__']
    
    def __init__(self, tree, pathProxy):
        self._tree = tree
        self._proxy = pathProxy
        self._proxy.changed.connect(self.onChanged)        
        # Process asap, but do not track
        self._proxy.push()
        # Store ourself
        tree._temporaryItems.add(self)
    
    def clear(self):
        pass  # tree.createItems() calls this ...
    
    def onChanged(self):
        # Disband
        self._tree._temporaryItems.discard(self)
        # Process contents
        self._tree.createItems(self)



class TemporaryFileItem:
    """ Created when searching. This object posts a requests to search
    its contents which are then processed, after which this object
    disbands itself, passin the proxy object to a real FileItem if the
    search had results.
    """
    __slots__ = ['_tree', '_proxy', '__weakref__']
    
    def __init__(self, tree, pathProxy):
        self._tree = tree
        self._proxy = pathProxy   
        self._proxy.taskFinished.connect(self.onSearchResult)
        # Store ourself
        tree._temporaryItems.add(self)
        
    def search(self, searchFilter):
        self._proxy.pushTask(SearchTask(searchFilter))
    
    def onSearchResult(self, task):
        # Disband now
        self._tree._temporaryItems.discard(self)
        
        # Get result. May raise an error
        result = task.result()
        # Process contents
        if result:
            item = FileItem(self._tree, self._proxy)
            for r in result:
                SearchItem(item, 'Line %i: %s'%r)
        # Update counter
        searchInfoItem = self._tree.topLevelItem(0)
        if isinstance(searchInfoItem, SearchInfoItem):
            searchInfoItem.addFile(bool(result))



class Tree(QtGui.QTreeWidget):
    """ Representation of the tree view.
    Instances of this class are responsible for keeping the contents
    up-to-date. The Item classes above are dumb objects.
    """
    
    dirChanged = QtCore.Signal(Path) # Emitted when user goes into a subdir
    
    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        
        # Initialize
        self.setMinimumWidth(150)
        self.setMinimumHeight(150)
        #
        self.setColumnCount(1)
        self.setHeaderHidden(True)
        self.setIconSize(QtCore.QSize(24,16))
       
        # Connecy signals
        self.itemExpanded.connect(self.onItemExpanded)
        self.itemCollapsed.connect(self.onItemCollapsed)
        self.itemClicked.connect(self.onItemClicked)
        self.itemActivated.connect(self.onItemActivated)
        
        # Variables for restoring the view after updating
        self._selectedPath = '' # To restore a selection after updating
        self._selectedScrolling = 0
        
        # Set of temporary items
        self._temporaryItems = set()
        
        # Define context menu
        self._menu = QtGui.QMenu(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuTriggered)  
        
        # Initialize proxy (this is where the path is stored)
        self._proxy = None
    
    
    def path(self):
        """ Get the current path shown by the treeview.
        """
        return self._proxy.path()
    
    
    def setPath(self, path):
        """ Set the current path shown by the treeview.
        """
        # Close old proxy        
        if self._proxy is not None:
            self._proxy.cancel()        
            self._proxy.changed.disconnect(self.onChanged)
            self._proxy.deleted.disconnect(self.onDeleted)
            self._proxy.errored.disconnect(self.onErrored)
            self.destroyed.disconnect(self._proxy.cancel)
        # Create new proxy
        if True:
            self._proxy = self.parent()._fsProxy.dir(path)
            self._proxy.changed.connect(self.onChanged)
            self._proxy.deleted.connect(self.onDeleted)
            self._proxy.errored.connect(self.onErrored)
            self.destroyed.connect(self._proxy.cancel)
        # Activate the proxy, we'll get a call at onChanged() asap.
        if path.lower() == MOUNTS.lower():
            self.clear()
            createMounts(self.parent(), self)
        else:
            self._proxy.track()
            self._proxy.push()
        # Store dir in config
        self.parent().config.path = path
        # Signal that the dir has changed 
        # Note that our contents may not be visible yet.
        self.dirChanged.emit(self.path())
    
    
    def setPathUp(self):
        """ Go one directory up.
        """
        newPath = self.path().dirname
        
        if newPath == self.path():
            self.setPath(Path(MOUNTS))
        else:
            self.setPath(newPath)
    
    
    def clear(self):
        """ Overload the clear method to remove the items in a nice
        way, alowing the pathProxy instance to be closed correctly.
        """
        # Clear temporary (invisible) items
        for item in self._temporaryItems:
            item._proxy.cancel()
        self._temporaryItems.clear()
        # Clear visible items
        for i in reversed(range(self.topLevelItemCount())):
            item = self.topLevelItem(i)
            if hasattr(item, 'clear'):
                item.clear()
            if hasattr(item, 'onDestroyed'):
                item.onDestroyed()
        QtGui.QTreeWidget.clear(self)
    
    
    def mouseDoubleClickEvent(self, event):
        """ Bypass expanding an item when double-cliking it.
        Only activate the item.
        """
        item = self.itemAt(event.x(), event.y())
        if item is not None:
            self.onItemActivated(item)
    
    
    def onChanged(self):
        """ Called when our contents change or when we just changed directories.
        """
        self.createItems(self)
    
    
    def createItems(self, parent):
        """ High level method to create the items of the tree or a DirItem.
        This method will handle the restoring of state etc.
        The actual filtering of entries and creation of tree widget items
        is done in the createItemsFun() function.
        """
        # Store state and clear
        self._storeSelectionState()
        parent.clear()
        # Create sub items
        count = createItemsFun(self.parent(), parent)
        if not count and isinstance(parent, QtGui.QTreeWidgetItem):
            ErrorItem(parent, 'Empty directory')
        # Restore state
        self._restoreSelectionState()
    
    
    def onErrored(self, err='...'):
        self.clear()
        ErrorItem(self, 'Error: ' + err)
    
    def onDeleted(self):
        self.setPathUp()
    
    def onItemExpanded(self, item):
        if hasattr(item, 'onExpanded'):
            item.onExpanded()
    
    def onItemCollapsed(self, item):
        if hasattr(item, 'onCollapsed'):
            item.onCollapsed()
    
    def onItemClicked(self, item):
        if hasattr(item, 'onClicked'):
            item.onClicked()
    
    def onItemActivated(self, item):
        """ When an item is "activated", make that the new directory,
        or open that file.
        """
        if isinstance(item, (DriveItem, DirItem)):
            self.setPath(item.path())
        elif isinstance(item, FileItem):
            # todo: someday we should be able to simply pass the proxy object to the editors
            # so that we can open files on any file system
            path = item.path()
            if path.ext not in ['.pyc','.pyo','.png','.jpg','.ico']:
                iep.editors.loadFile(path)
    
    
    def _storeSelectionState(self):
        # Store selection
        items = self.selectedItems()
        self._selectedPath = items[0].path() if items else ''
        # Store scrolling
        self._selectedScrolling = self.verticalScrollBar().value()
    
    
    def _restoreSelectionState(self):
        # First select the first item 
        # (otherwise the scrolling wont work for some reason)
        if self.topLevelItemCount():
            self.setCurrentItem(self.topLevelItem(0))       
        # Restore selection
        if self._selectedPath:
            items = self.findItems(self._selectedPath.basename, QtCore.Qt.MatchExactly, 0)
            items = [item for item in items if item.path() == self._selectedPath]
            if items:
                self.setCurrentItem(items[0])
        # Restore scrolling
        self.verticalScrollBar().setValue(self._selectedScrolling)
        self.verticalScrollBar().setValue(self._selectedScrolling)
    
    
    def contextMenuTriggered(self, p):
        """ Called when context menu is clicked """
        # Init
        # todo: call showMenu on the item, which uses IEP's menus, so first put what we have now in IEP
        menu = self._menu
        item = self.itemAt(p)
        
        if not item:
            return
        elif isinstance(item, FileItem):
            menu.clear()
            action = menu.addAction(translate('filebrowser', 'Open with native application'))
            action = menu.addAction(translate('filebrowser', 'Copy path'))
            action = menu.addAction(translate('filebrowser', 'Rename file'))
            action = menu.addAction(translate('filebrowser', 'Delete file'))
        elif isinstance(item, DirItem):
            menu.clear()
            action = menu.addAction(translate('filebrowser', 'Rename directory'))
            action = menu.addAction(translate('filebrowser', 'Delete directory'))
        
        # Show menu
        menu.exec_(self.mapToGlobal(p))
