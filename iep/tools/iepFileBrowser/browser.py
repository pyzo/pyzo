import os
import sys

from pyzolib.path import Path
from pyzolib import ssdf
from PySide import QtCore, QtGui

import iep
from iep import translate

from .tree import Tree
from . import proxies


class Browser(QtGui.QWidget):
    """ A browser consists of an address bar, and tree view, and other
    widets to help browse the file system. The browser object is responsible
    for tying the different browser-components together.
    """
    
    def __init__(self, parent, config, path=None):
        QtGui.QWidget.__init__(self, parent)
        
        # Store config
        self.config = config
        
        # Create star button
        self._projects = Projects(self)
        
        # Create up button
        self._up = QtGui.QToolButton(self)
        self._up.setIcon( iep.icons.folder_parent )  # folder_parent bullet_arrow_up
        self._up.setStyleSheet("QToolButton { padding: 0px; }");
        self._up.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._up.setIconSize(QtCore.QSize(18,18))
        
        # Create path input/display lineEdit
        self._pathEdit = PathInput(self)
        
        # Create file system proxy
        self._fsProxy = proxies.NativeFSProxy()
        self.destroyed.connect(self._fsProxy.stop)
        
        # Create tree widget
        self._tree = Tree(self)
        self._tree.setPath(Path(self.config.path))
        
        # Create name filter
        self._nameFilter = NameFilter(self)
        self._nameFilter.lineEdit().setToolTip('File filter pattern')  
        
        # Create search filter
        self._searchFilter = SearchFilter(self)
        self._searchFilter.setToolTip('Search pattern')
        self._searchFilter.setPlaceholderText(self._searchFilter.toolTip())
        
        # Signals to sync path. 
        # Widgets that can change the path transmit signal to _tree
        self._pathEdit.dirChanged.connect(self._tree.setPath)
        self._projects.dirChanged.connect(self._tree.setPath)
        self._up.clicked.connect(self._tree.setPathUp)
        #
        self._nameFilter.filterChanged.connect(self._tree.onChanged) # == update
        self._searchFilter.filterChanged.connect(self._tree.onChanged)
        # The tree transmits signals to widgets that need to know the path
        self._tree.dirChanged.connect(self._pathEdit.setPath)
        self._tree.dirChanged.connect(self._projects.setPath)
        
        self._layout()
        
        # Set and sync path ...
        if path is not None:
            self._tree.SetPath(path)
        self._tree.dirChanged.emit(self._tree.path())
    
    
    def _layout(self):
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        #layout.setSpacing(6)
        self.setLayout(layout)
        #
        layout.addWidget(self._projects)
        #
        subLayout = QtGui.QHBoxLayout()
        subLayout.setSpacing(2)
        subLayout.addWidget(self._up)
        subLayout.addWidget(self._pathEdit)
        layout.addLayout(subLayout)
        #
        layout.addWidget(self._tree)
        #
        layout.addWidget(self._nameFilter)
        #
        layout.addWidget(self._searchFilter)
        
    
    def closeEvent(self, event):
        #print('Closing browser, stopping file system proxy')
        super().closeEvent(event)
        self._fsProxy.stop()
    
    
    def nameFilter(self):
        return self._nameFilter.lineEdit().text()
    
    def searchFilter(self):
        return {'pattern': self._searchFilter.text(),
                'matchCase': self.config.searchMatchCase,
                'regExp': self.config.searchRegExp,
                'subDirs': self.config.searchSubDirs,
                }
    
   
    @property
    def expandedDirs(self):
        """ The list of the expanded directories. 
        """
        return self.parent().config.expandedDirs
    
    
    @property
    def starredDirs(self):
        """ A list of the starred directories (not a copy).
        """
        return [d.path for d in self.parent().config.starredDirs]
    
    
    def test(self, sort=False):
        items = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            items.append(item)
            #self._tree.removeItemWidget(item, 0)
        self._tree.clear()
        
        #items.sort(key=lambda x: x._path)
        items = [item for item in reversed(items)]
        
        for item in items:
            self._tree.addTopLevelItem(item)
    


class PathInput(QtGui.QLineEdit):
    """ Line edit for selecting a path.
    """
    
    dirChanged = QtCore.Signal(Path) # Emitted when the user changes the path (and is valid)
    
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)
        
        # To receive focus events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        # Set completion mode
        self.setCompleter(QtGui.QCompleter())
        c = self.completer()
        c.setCompletionMode(c.InlineCompletion)
        
        # Set dir model to completer
        dirModel = QtGui.QDirModel(c)
        dirModel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        c.setModel(dirModel)
        
        # Connect signals
        #c.activated.connect(self.onActivated)
        self.textEdited.connect(self.onTextEdited)
        #self.textChanged.connect(self.onTextEdited)
        #self.cursorPositionChanged.connect(self.onTextEdited)
    
    def setPath(self, path):
        """ Set the path to display. Does nothing if this widget has focus.
        """
        if not self.hasFocus():
            self.setText(path)
            self.checkValid() # Reset style if it was invalid first
    
    
    def checkValid(self):
        # todo: This kind of violates the abstraction of the file system
        # ok for now, but we should find a different approach someday
        # Check
        text = self.text()
        dir = Path(text)
        isvalid = text and dir.isdir and os.path.isabs(dir)
        # Apply styling
        if isvalid:
            self.setStyleSheet('')
        else:
            self.setStyleSheet('QLineEdit {font-style:italic;}')
        # Return
        return isvalid
    
    
    def event(self, event):
        # Capture key events to explicitly apply the completion and
        # invoke checking whether the current text is a valid directory.
        if isinstance(event, QtGui.QKeyEvent):
            qt = QtCore.Qt
            if event.key() in [qt.Key_Tab, qt.Key_Enter, qt.Key_Return]:
                self.setText(self.text()) # Apply completion
                self.onTextEdited() # Check if this is a valid dir
                return True
        return super().event(event)
            
    
    
    def onTextEdited(self, dummy=None):
        text = self.text()
        if self.checkValid():
            self.dirChanged.emit(Path(text))
    
    
    def focusOutEvent(self, event=None):
        """ focusOutEvent(event)
        On focusing out, make sure that the set path is correct.
        """
        if event is not None:
            QtGui.QLineEdit.focusOutEvent(self, event)
        
        path = self.parent()._tree.path()
        self.setPath(path)



class Projects(QtGui.QWidget):
    
    dirChanged = QtCore.Signal(Path) # Emitted when the user changes the project
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Init variables
        self._path = ''
        
        # Create combo button
        self._combo = QtGui.QComboBox(self)
        self._combo.setEditable(False)
        self.updateProjectList()
        
        # Create star button
        self._but = QtGui.QToolButton(self)
        self._but.setIcon( iep.icons.star3 )
        self._but.setStyleSheet("QToolButton { padding: 0px; }");
        self._but.setIconSize(QtCore.QSize(18,18))
        self._but.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self._but.setPopupMode(self._but.InstantPopup)
        #
        self._menu = QtGui.QMenu(self._but)
        self._menu.triggered.connect(self.onMenuTriggered)
        self.buildMenu()
        
        # Connect signals
        self._but.pressed.connect(self.onButtonPressed)
        self._combo.activated .connect(self.onProjectSelect)
        
        # Layout
        layout = QtGui.QHBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self._but)
        layout.addWidget(self._combo)
        layout.setSpacing(2)
        layout.setContentsMargins(0,0,0,0)
    
    
    def _currentDict(self):
        """ Return the current project-dict, or None.
        """ 
        path = self._combo.itemData(self._combo.currentIndex())
        if not path:
            return None
        for d in self.parent().config.starredDirs:
            if d['path'] == path:
                return d
        else:
            return None
    
    
    def setPath(self, path):
        self._path = path
        # Find project index
        projectIndex, L = 0, 0
        pathn = path.normcase()
        for i in range(self._combo.count()):
            projectPath = self._combo.itemData(i)
            if pathn.startswith(projectPath) and len(projectPath) > L:
                projectIndex, L = i, len(projectPath)
        # Select project or not ...
        self._combo.setCurrentIndex(projectIndex)
        if projectIndex:
            self._but.setIcon( iep.icons.star2 )
            self._but.setMenu(self._menu)
        else:
            self._but.setIcon( iep.icons.star3 )
            self._but.setMenu(None)
    
    
    def updateProjectList(self):
        # Get sorted version of starredDirs
        starredDirs = [d for d in self.parent().config.starredDirs]
        starredDirs.sort(key=lambda d:d.name.lower())
        # Refill the combo box
        self._combo.clear()
        for d in starredDirs:
            self._combo.addItem(d.name, d['path'])
        # Insert dummy item
        if starredDirs:
            self._combo.insertItem(0, 'Bookmarks:', '') # No-project item
        else:
            self._combo.addItem('Click the star to bookmark the current dir', '')
    
    
    def buildMenu(self):
        menu = self._menu
        menu.clear()
        
        # Add action to remove bookmark
        action = menu.addAction(translate('filebrowser', 'Remove project'))
        action._id = 'remove'
        action.setCheckable(False)
        
        # Add action to change name
        action = menu.addAction(translate('filebrowser', 'Change project name ...'))
        action._id = 'name'
        action.setCheckable(False)
        
        # Add check action for adding to Pythonpath
        action = menu.addAction(translate('filebrowser', 'Add path to Python path'))
        action._id = 'pythonpath'
        d = self._currentDict()
        action.setCheckable(True)
        checked = bool( d and d['addToPythonpath'] )
        action.setChecked(checked)
    
    
    def onMenuTriggered(self, action):
        d = self._currentDict()
        if not d:
            return
        
        if action._id == 'remove':
            # Remove this project
            starredDirs = self.parent().config.starredDirs
            for d in starredDirs:
                if self._path.normcase() == d.path:
                    starredDirs.remove(d)
                    break
        
        elif action._id == 'name':
            # Open dialog to ask for name
            name = QtGui.QInputDialog.getText(self.parent(), 
                                translate('filebrowser', 'Project name'),
                                translate('filebrowser', 'New project name:'),
                                text=d['name'],
                            )
            if isinstance(name, tuple):
                name = name[0] if name[1] else ''
            if name:
                d['name'] = name
        
        elif action._id == 'pythonpath':
            # Flip add-to-pythonpath flag
            d['addToPythonpath'] = not d['addToPythonpath']
    
    
    def onButtonPressed(self):
        if self._but.menu():
            # The directory is starred and has a menu. The user just
            # used the menu (or not). Update so it is up-to-date next time.
            self.buildMenu()
        else:
            # Not starred right now, create new project!
            newProject = ssdf.new()
            newProject.path = self._path.normcase() # Normalize case!
            newProject.name = self._path.basename
            newProject.addToPythonpath = False
            self.parent().config.starredDirs.append(newProject)
        # Update
        self.updateProjectList()
        self.setPath(self._path)
    
    
    def onProjectSelect(self, index):
        path = self._combo.itemData(index)
        if path:
            # Go to dir
            self.dirChanged.emit(Path(path))
        else:
            # Dummy item, reset
            self.setPath(self._path)



class NameFilter(QtGui.QComboBox):
    """ Combobox to filter by name.
    """
    
    filterChanged = QtCore.Signal()
    
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)
        
        # Set properties
        self.setEditable(True)
        self.setCompleter(None)
        self.setInsertPolicy(self.NoInsert)
        
        # Add common patterns
        for pattern in ['*', '!*.pyc', 
                        '*.py *.pyw', '*.py *.pyw *.pyx *.pxd', 
                        '*.h *.c *.cpp']:
            self.addItem(pattern)
        
        # Emit signal when value is changed
        self._lastValue = ''
        self.lineEdit().editingFinished.connect(self.checkFilterValue)
        self.lineEdit().returnPressed.connect(self.checkFilterValue)
        self.activated.connect(self.checkFilterValue)
        
        # Ensure the namefilter is in the config and initialize 
        config = self.parent().config
        if 'nameFilter' not in config:
            config.nameFilter = '!*.pyc'
        self.setText(config.nameFilter)
    
    def setText(self, value):
        """ To initialize the name filter.
        """ 
        self.lineEdit().setText(value)
        self._lastValue = value
    
    def checkFilterValue(self):
        value = self.lineEdit().text()
        if value != self._lastValue:
            self.parent().config.nameFilter = value
            self._lastValue = value
            self.filterChanged.emit()


class SearchFilter(QtGui.QLineEdit):
    """ Line edit to do a search in the files.
    """ 
    
    OFFSET = 0
    
    filterChanged = QtCore.Signal()
    
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)
        
        # Load two icons
        self._defaultIcon = iep.icons['magnifier']
        self._clearIcon = iep.icons['cancel']
        
        # Create tool button
        self._button = button = QtGui.QToolButton(self)
        button.setIcon(self._defaultIcon)
        button.setIconSize(QtCore.QSize(16,16))
        button.setCursor(QtCore.Qt.ArrowCursor)
        button.setStyleSheet("QToolButton { border: none; padding: 0px; }");
        #button.setStyleSheet("QToolButton { border: none; padding: 0px; background-color:red;}");
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setPopupMode(button.InstantPopup)
        #
        self._menu = QtGui.QMenu(button)
        self._menu.triggered.connect(self.onMenuTriggered)
        button.setMenu(self._menu)
        self.buildMenu()
        
        # Connect signals
        button.pressed.connect(self.onButtonPressed)
        self.textChanged.connect(self.updateCloseButton)                
        
        # Set padding of line edit
        fw = QtGui.qApp.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        padding =  button.sizeHint().width() + fw + 1 + self.OFFSET
        self.setStyleSheet("QLineEdit { padding-right: %ipx; } " % padding);
        
        # Set minimum size
        msz = self.minimumSizeHint()
        w = max(msz.width(), button.sizeHint().width()*2 + fw * 2 + 2 + self.OFFSET)
        h = max(msz.height(), button.sizeHint().height() + fw * 2 + 2)
        self.setMinimumSize(w,h)
        
        self._lastValue = '' # The search filer is always initialized empty
        self.returnPressed.connect(self.checkFilterValue)
        self.editingFinished.connect(self.checkFilterValue)
    
    def onButtonPressed(self):
        """ Clear text or build menu.
        """
        if self.text():
            QtGui.QLineEdit.clear(self)
            self.checkFilterValue()
        else:
            self.buildMenu()
    
    def checkFilterValue(self):
        value = self.text()
        if value != self._lastValue:
            self._lastValue = value
            self.filterChanged.emit()
    
    def resizeEvent(self, event):
        QtGui.QLineEdit.resizeEvent(self, event)
        
        sz = self._button.sizeHint()
        fw = QtGui.qApp.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        rect = self.rect()
        self._button.move(  rect.right() - fw -sz.width() - self.OFFSET,
                            (rect.bottom() + 1 - sz.height())/2)
    
    def updateCloseButton(self, text):
        if self.text():
            self._button.setIcon(self._clearIcon)
            self._button.setMenu(None)
        else:
            self._button.setIcon(self._defaultIcon)
            self._button.setMenu(self._menu)
    
    def buildMenu(self):
        config = self.parent().config
        menu = self._menu
        menu.clear()
        
        map = [ ('searchMatchCase', False, translate("search", "Match case")),
                ('searchRegExp', False, translate("search", "RegExp")),
                ('searchSubDirs', True, translate("search", "Search in subdirs"))
              ]
        
        # Fill menu
        for option, default, description in map:
            if option is None:
                menu.addSeparator()
            else:
                # Make sure the option exists
                if option not in config:
                    config[option] = default
                # Make action in menu
                action = menu.addAction(description)
                action._option = option
                action.setCheckable(True)
                action.setChecked( bool(config[option]) )
    
    def onMenuTriggered(self, action):
        config = self.parent().config
        option = action._option
        # Swap this option
        if option in config:
            config[option] = not config[option]
        else:
            config[option] = True
