import sys, os, time
import threading
import re

from PyQt4 import QtCore, QtGui
import iep 

tool_name = "File browser"
tool_summary = "Browse and search in files."


## Helper functions

def normPath(path):
    """ normPath(path)
    Normalize the path by:
      * making it a string
      * replacing all backslashes to forward slashes
      * prevents multiple slashes
      * makes sure the path ends with a slash.
    """
    
    # Make string
    path = str(path)
    
    # Replace slashes
    path = path.replace('\\', '/')
    
    # Remove double slashes
    while '//' in path:
        path = path.replace('//', '/')
    
    # Ends with one slash
    path = path.rstrip('/') + '/'
    
    # Done
    return path

def checkFileAgainstPattern(pattern, fname):
    """ checkFileAgainstPattern(pattern, fname)
    Check the given filename matches the given pattern.
    """ 
    
    # Count number of wildcards
    parts = pattern.count('*')+1
    
    if not pattern:
        # No pattern
        return True
    
    elif parts == 1:
        # Full match
        if pattern == filename:
            return True
        else:
            return False
    
    else:
        # Harder match (at least one wildcard)
        tmp = pattern.split('*')
        ok = True
        # Test start
        if tmp[0] and not fname.startswith(tmp[0]):
            ok = False
        # Test end
        if tmp[-1] and not fname.endswith(tmp[-1]):
            ok = False
        # Test middle parts
        for t in tmp[1:-1]:
            if t and t not in fname:
                ok = False
        # Done
        return ok


def checkFileAgainstPatterns(patterns, fname):
    """ checkFileAgainstPatterns(patterns, fname)
    Check if the given filename matches any of the given patterns.
    """
    
    # Empty patterns means ok
    if not patterns:
        return True
    
    # Split
    patterns.replace(',', ' ')
    patterns = patterns.strip().split(' ')
    
    # Test all patterns
    for pattern in patterns:
        ok = checkFileAgainstPattern(pattern, fname)
        if ok:
            return True
    
    # Return false by default
    return False


    
class IepCompleter(QtGui.QCompleter):
    """ Completer that normalized the path using forward slashes only.
    """
    
    def pathFromIndex(self, index):
        path = QtGui.QCompleter.pathFromIndex(self, index)
        return normPath(path)
    
    def splitPath(self, path):
        parts = path.split('/')
        if not sys.platform.startswith('win') and not parts[0]:
            parts[0] = '/'
        return parts
    

class PathInput(QtGui.QLineEdit):
    """ Line edit for selecting a path.
    """
    
    dirChanged = QtCore.pyqtSignal(str)
    
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)
        
        # To receive focus events
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        # Set completion mode
        self.setCompleter(IepCompleter())
        c = self.completer()
        c.setMaxVisibleItems(7)
        #c.setCompletionMode(c.InlineCompletion)
        c.setCompletionMode(c.UnfilteredPopupCompletion)
        #c.setCompletionMode(c.PopupCompletion)
        
        # Set dir model to completer
        dirModel = QtGui.QDirModel(c)
        dirModel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        c.setModel(dirModel)
        
        # Set history for going back up
        self._upHistory = []
        
        # Bind
        c.activated.connect(self.onActivated)
    
    
    def init(self, config):
        # Set path of previous time
        self._config = config
        self.setText(config.path)
    
    
    def _firstOfSeries(self):
        """ _firstOfSeries()
        Simple function to prevent multiple keystrokes.
        """
        # Prevent multiple ups
        if hasattr(self, '_uptime') and (time.time() - self._uptime) < 0.2:
            return False
        else:
            self._uptime = time.time()
            return True
    
    
    def setText(self, path):
        """ setText(path)
        Overload setText to ensure the set text is a valid path and that
        only forward slashes are used (yeah also on windows). 
        """
        if os.path.isdir(path):
            path = normPath(path)
            QtGui.QLineEdit.setText(self, path)
            self.dirChanged.emit(path)
            self._config.path = path
        else:
            pass
    
    
    def appendPathPart(self, part):
        """ appendPathPart(part)
        Append a part to the current path, discarting any previous text.
        """
        
        # Get current path
        path = self.text()
        
        if '/' in path:
            # Add to bit after last slash
            path = path.rsplit('/',1)[0]
            path = path + '/' + part + '/'
        else:
            # root: Simple replace
            path = part
        
        # Set path
        self.setText(path)
    
    
    def goDown(self):
        """ goDown()
        Reverse of going up (using history).
        """
        if self._upHistory:
            
            # Get path
            path = self._upHistory.pop()
            
            # Go there
            self.setText(path)
            self.completer().setCompletionPrefix(self.text())
    
    
    def goUp(self):
        """ goUp()
        Go a directory up in the file system.
        """
        
        # Get path
        path = normPath( self.text() )
        
        # Store
        self._upHistory.append(path)
        self._upHistory = self._upHistory[-32:]
        
        # Split to get base
        path = path.rsplit('/',2)[0]
        
        # Update
        self.setText(path)
        self.completer().setCompletionPrefix(self.text())
        #self.completer().complete()
    
    
    def _completeNow(self):
        """ _completeNow()
        Finishe the completion now.
        """        
        # Get part selection in list box
        popup = self.completer().popup()
        if popup:
            newPart = popup.model().data(popup.currentIndex())
            if newPart:
                # Append part and update completer
                self.appendPathPart(newPart)
        else:
            self.setText(self.completer().currentCompletion())
            
        # Update completer
        self.completer().setCompletionPrefix(self.text())
    
    
    def event(self, event):
        """ event(event)
        Overload event to be able to use the tab key for completion.
        """
        if isinstance(event, QtGui.QKeyEvent):
            
            # Get whether control is down
            modifiers = event.modifiers()
            CTRL = modifiers & QtCore.Qt.ControlModifier
            QTK = QtCore.Qt
            key = event.key()
            
            if key in [QTK.Key_Return, QTK.Key_Enter]:
                # Invoke focus out event
                self.parent().setFocus()
                self.setFocus()
            elif key == QTK.Key_Tab:
                # Complete
                if self._firstOfSeries():
                    self._completeNow()
                return True
            elif CTRL and key in [QTK.Key_Backspace, QTK.Key_Left]:
                # Up
                if self._firstOfSeries():
                    self.goUp()
                return True
            elif CTRL and key == QTK.Key_Right:
                # Down
                if self._firstOfSeries():
                    self.goDown()
                return True
        
        # Resort to default behaviour
        return QtGui.QLineEdit.event(self, event)
    
    
    def focusOutEvent(self, event=None):
        """ focusOutEvent(event)
        On focusing out, make sure that the set path is correct.
        """
        
        # Handle normally
        if event is not None:
            QtGui.QLineEdit.focusOutEvent(self, event)
        
        # Get path
        path = normPath( self.text() )
        
        # Remove parts untill it is valid
        while '/' in path and not os.path.isdir(path):
            path = path.rsplit('/',1)[0]
        
        # Update
        if path.rstrip('/') and os.path.isdir(path):
            self.setText(path)
        else:
            self.setText(self._config.path)
    
    
    def focusInEvent(self, event):
        """ focusInEvent(event)
        On focusing in, the dir selection dialog is popped up. 
        """
        QtGui.QLineEdit.focusInEvent(self, event)
        self.selectDown()
    
    
    def onActivated(self):
        """ onActivated()
        When clicked -> set text and show drop down.
        """
        self.focusOutEvent()
        self.selectDown()
    
    
    def selectDown(self):
        """ selectDown()
        Pops up the completer list.
        """
        pass
        #self.completer().setCompletionPrefix(self.text())
        #self.completer().complete()


class SearchTools(QtGui.QWidget):
    
    somethingChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # List of layouts
        layouts = []
        
        # File pattern
#         label = QtGui.QLabel(self)
#         label.setText('File pattern:')
        #
        self._filePattern = w = QtGui.QLineEdit(self)
        self._filePattern.setText('*.py')
        self._filePattern.setToolTip('File pattern')
        #
        self._fileShowDirs = w = QtGui.QCheckBox(self)
        self._fileShowDirs.setText('Show dirs')
        #
        self._searchButton = QtGui.QCheckBox(self)
        self._searchButton.setText('SEARCH')
        self._searchButton.setStyleSheet("QCheckBox{background:#99F;}")
        #
        layout = QtGui.QHBoxLayout()
        #layout.addWidget(label, 0)
        layout.addWidget(self._filePattern, 0)
        layout.addWidget(self._fileShowDirs, 0)
        layout.addStretch(1)
        layout.addWidget(self._searchButton, 0)
        layouts.append(layout)
        
        # Search pattern
        #label = QtGui.QLabel(self)
        #label.setText('Search pattern:')
        #
        self._searchProgress = QtGui.QProgressBar(self)
        self._searchProgress.setMaximumHeight(10)
        #
        self._searchPattern = QtGui.QLineEdit(self)
        self._searchPattern.setText('')
        #
        self._searchIsRegExp = QtGui.QCheckBox(self) 
        self._searchIsRegExp.setText('RegExp')
        #
        self._searchInSubdirs = QtGui.QCheckBox(self) 
        self._searchInSubdirs.setText('Subdirs')
        #
        layout = QtGui.QHBoxLayout()
        #layout.addWidget(label, 0)
        layout.addWidget(self._searchPattern, 1)
        layout.addWidget(self._searchIsRegExp, 0)
        layout.addWidget(self._searchInSubdirs, 0)
        layouts.append(self._searchProgress)
        layouts.append(layout)
        
        # Set layout
        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.setSpacing(2)
        for layout in layouts:
            if isinstance(layout, QtGui.QLayout):
                layout.setSpacing(2)
                mainLayout.addLayout(layout)
            else:
                mainLayout.addWidget(layout)
        #
        self.setLayout(mainLayout)
        
        # Bind to signals
        self._filePattern.editingFinished.connect(self.onSomethingChanged)
        self._fileShowDirs.released.connect(self.onSomethingChanged)
        self._searchPattern.editingFinished.connect(self.onSomethingChanged)
        self._searchIsRegExp.released.connect(self.onSomethingChanged)
        #
        self._searchButton.released.connect(self.onSearchButtonPressed)
        self.onSearchButtonPressed()
    
    
    def onSomethingChanged(self):
        self.somethingChanged.emit()
    
    
    def onSearchButtonPressed(self):
        
        #if self._searchButton.isDown():
        #if self._searchButton.text().endswith('\\'):
        if self._searchButton.isChecked():
            # Expand
            self._searchPattern.show()
            self._searchIsRegExp.show()
            self._searchProgress.show()
            self._searchInSubdirs.show()
            #self._searchButton.setText('Search /\\')
            #self._searchButton.setDown(True)
            #pal = QtGui.QPalette.AlternateBase
            #self._searchButton.setBackgroundRole(pal)
            #self._searchButton.setAutoFillBackground(True)
            #self._searchButton.setFlat(True)
            #self._searchButton.setStyleSheet("QPushButton{background:#99C;}")
        else:
            # Collapse
            self._searchPattern.hide()
            self._searchIsRegExp.hide()
            self._searchProgress.hide()
            self._searchInSubdirs.hide()
            #self._searchButton.setText('Search \\/')
            #self._searchButton.setStyleSheet("QPushButton{background:#559;}")
        


class Browser(QtGui.QTreeWidget):
    def __init__(self, parent, tools):
        QtGui.QTreeWidget.__init__(self, parent)
        
        # Store tools
        self._tools = tools
        self._tools.somethingChanged.connect(self.refreshList)
        
        # Init path
        self._path = 'Nonsensethisstringshouldbe'
        
        # Init searcher
        self._searcher = SearcherThread(tools)
        self._searcher.start()
        
        # Set headers
        self.setColumnCount(2)
        self.setHeaderLabels(['File name', 'Size'])
        self.setColumnWidth(0, 200)
        
        # Do not show lines for top level items
        self.setRootIsDecorated(False)
        #self.setSortingEnabled(True)
        
        # Bind
        self.itemDoubleClicked.connect(self.onDoubleClicked)
    
    
    def onDoubleClicked(self, item):
        """ Take action! 
        """
        if hasattr(item, '_dir'):
            if item._dir.endswith('..'):
                self.parent()._path.goUp()
            else:
                self.parent()._path.setText(item._dir)
        elif hasattr(item, '_fname'):
            iep.editors.loadFile(item._fname)
    
    
    def _getFileSize(self, fname):
        """ getFileSize(fname)
        Get the size of a file as a string expressed nicely using KiB figures.
        """
        
        # Get size
        size = float( os.path.getsize(fname) )
        
        # Make strings
        if size > 2**30:
            size = '%1.1f GiB' % (size / 2**30)
        elif size > 2**20:
            size = '%1.1f MiB' % (size / 2**20)
        elif size > 2**10:
            size = '%1.1f KiB' % (size / 2**10)
        else:
            size = '%1.0f B' % (size)
        
        # Done
        return size
    
    
    def showDir(self, path):
        """ showDir(path)
        Show the given dir.
        """
        self._path = path
        self.refreshList()
    
    
    def refreshList(self):
        """ refreshList()
        Refresh the list of files.
        """
        
        # Get path
        path = self._path
        
        # Check
        if not os.path.isdir(path):
            return
        
        # Search in this path?
        if self._tools._searchPattern.text():
            self._searcher._runCounter += 1
        
        # Prepare for searching files
        patterns = self._tools._filePattern.text()
        files = []
        dirs = []
        
        # Search files                
        for fname in os.listdir(path):
            if fname.startswith('.'):
                continue
            ffname = os.path.join(path,fname)
            if os.path.isdir(ffname):
                dirs.append(fname)
            if os.path.isfile(ffname):
                if checkFileAgainstPatterns(patterns, fname):
                    files.append(fname)
        
        # todo: use different icons for .py and .pyx files
        # Get file icon
        style = QtGui.qApp.style()
        fileIcon = style.standardIcon(style.SP_FileIcon)
        dirIcon = style.standardIcon(style.SP_DirIcon)
        
        # Sort
        files.sort()
        dirs.sort()
        #dirs.insert(0, '..')
        
        # Make entries
        self.clear()
        if self._tools._fileShowDirs.isChecked():
            for fname in dirs:
                ffname = os.path.join(path,fname)
                item = QtGui.QTreeWidgetItem([fname, ''], 1)
                item._dir = ffname
                item.setIcon(0, dirIcon)
                self.addTopLevelItem(item)
        if True:
            for fname in files:
                ffname = os.path.join(path,fname)
                size = self._getFileSize(ffname)
                item = QtGui.QTreeWidgetItem([fname, size], 0)
                item._fname = ffname
                item.setIcon(0, fileIcon)
                self.addTopLevelItem(item)


class SearcherThread(threading.Thread):
    """ This is the worker that searches the files in a directory for
    a specific search pattern.    
    """
    
    def __init__(self, tools):
        threading.Thread.__init__(self)
        
        # Store tools
        self._tools = tools
        
        # Make deamon
        self.deamon = True
        
        # Flag to indicate new data
        self._runCounter = 0
    
    
    
    def run(self):
        
        while True:
            
            # Wait untill counter increases
            counter = self._runCounter
            while counter == self._runCounter:
                time.sleep(0.1)
            
            # Run
            self.performSearch()
    
    
    def performSearch(self):
        
        # Get counter as it is now
        runCounter = self._runCounter
        
        # Get params
        path = self._tools.parent()._path.text()
        pattern = self._tools._searchPattern.text()
        regExp = self._tools._searchIsRegExp.isChecked()
        if regExp:
            pattern = '({})'.format(pattern)
        
        # Check
        if not os.path.isdir(path):
            return
        
        # Get file list
        patterns = self._tools._filePattern.text()
        files = []
        for fname in os.listdir(path):
            if fname.startswith('.'):
                continue
            ffname = os.path.join(path,fname)
            if os.path.isfile(ffname):
                if checkFileAgainstPatterns(patterns, fname):
                    files.append(fname)
        
        
        # Enter loop
        for fname in files:
            
            # Test if still good
            if runCounter != self._runCounter:
                break
            
            # Read file
            data = open(os.path.join(path, fname), 'rb').read()
            
            # Convert to text
            try:
                text = data.decode('utf-8')
                del data
            except UnicodeDecodeError:
                continue
            
            # Search
            lines = []
            for match in re.finditer(pattern, text):
                i = match.start()
                line = text[:i].count('\n') + 1
                if line == 1:
                    line = text[:i].count('\r') + 1
                lines.append(line)
            
            if lines:
                pass
                #print(fname, lines)


# todo: enable making bookmarks

class IepFileBrowser(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self._config = iep.config.tools[toolId]
        if not hasattr(self._config, 'path'):
            self._config.path = os.path.expanduser('~')
        
        # Create current-directory-tool
        self._path = path = PathInput(self)
        self._up = QtGui.QToolButton(self)
        #self._up.setText('up')
        style = QtGui.qApp.style()
        self._up.setIcon( style.standardIcon(style.SP_ArrowUp) )
        
        # Create tool
        self._tools = SearchTools(self)
        
        # Create browser
        self._browser = Browser(self, self._tools)
        
        # Set layout
        layout2 = QtGui.QHBoxLayout()
        layout2.addWidget(self._up,0)
        layout2.addWidget(path,1)
        #
        layout = QtGui.QVBoxLayout(self)
        layout.addLayout(layout2)
        #layout.addSpacing(10)
        layout.addWidget(self._tools)
        layout.addWidget(self._browser)
        #layout.addStretch(1)        
        #
        layout.setSpacing(1)
        self.setLayout(layout)
        
        self._up.pressed.connect(self._path.goUp)
        self._path.dirChanged.connect(self._browser.showDir)
        
        # Start
        self._path.init(self._config)
        
