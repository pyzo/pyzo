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


def selectIconForDir(path):
    if os.path.isdir(os.path.join(path, '.hg')):
        return iep.icons['folder_hg']
    elif os.path.isdir(os.path.join(path, '.svn')):
        return iep.icons['folder_svn']
    else:
        return iep.icons['folder_normal']
    
def selectIconForFile(path):
    
    # Get extention
    ext = os.path.splitext(path)[1]
    
    # Select
    if ext in ['.py', '.pyw']:
        return iep.icons['file_py']
    elif ext in ['.pyx', '.pxd']:
        return iep.icons['file_pyx']
    elif ext in ['.txt', '.2do', '.xml', '.html', '.htm', 
                    '.c', '.h', '.cpp', '.m']:
        return iep.icons['file_text']
    else:
        return iep.icons['file_normal']


## Classes for the path selection widget


class IconProvider(QtGui.QFileIconProvider):
    def icon(self, arg):
        if isinstance(arg, QtCore.QFileInfo):
            return selectIconForDir(arg.filePath())
        else:
            return iep.icons['folder_normal']
        #return QtGui.QFileIconProvider.icon(self, arg)


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
        c.setMaxVisibleItems(12)
        #c.setCompletionMode(c.InlineCompletion)
        c.setCompletionMode(c.UnfilteredPopupCompletion)
        #c.setCompletionMode(c.PopupCompletion)
        
        # Set dir model to completer
        dirModel = QtGui.QDirModel(c)
        dirModel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.NoDotAndDotDot)
        dirModel.setIconProvider(IconProvider())
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
            self._config.path = path
            if path != self.text():
                QtGui.QLineEdit.setText(self, path)
                self.dirChanged.emit(path)
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


class Browser(QtGui.QTreeWidget):
    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)
        
        # Store tools
        self._tools = parent
        self._tools.somethingChanged.connect(self.refreshList)
        
        # Init path
        self._path = 'Nonsensethisstringshouldbe'
        
        # Init searcher thread
        self._searchThread = None
        
        # Set headers        
        if False:
            self.setColumnCount(2)
            self.setHeaderLabels(['Name', 'Size'])
            self.setColumnWidth(0, 200)        
            #self.setSortingEnabled(True)
        else:
            self.setHeaderHidden(True)
        
        # Bind
        self.itemDoubleClicked.connect(self.onDoubleClicked)
    
    
    def onDoubleClicked(self, item):
        """ Take action! 
        """
        
        # Prevent expanding/collapsing the item
        item.setExpanded(not item.isExpanded())
        
        if hasattr(item, '_dir'):
            # A directory, change path
            if item._dir.endswith('..'):
                self._tools._path.goUp()
            else:
                self._tools._path.setText(item._dir)
        
        elif hasattr(item, '_fname'):
            # A filename, open file
            fileItem = iep.editors.loadFile(item._fname)
            
            # Select a line number?
            if fileItem and hasattr(item, '_linenr'):
                linenr = item._linenr - 1
                editor = fileItem._editor
                pos = editor.getPositionFromLinenr(linenr)
                editor.setPositionAndAnchor(pos)
                editor.ensureCursorVisible()
        
        # Give focus
        iep.editors.getCurrentEditor().setFocus()
    
    
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
    
    
    def _listDir(self, path):
        """ _listDir(path)
        List all files and directories in the given dir. Ignores
        names starting with a dot and returns only names that 
        match the file pattern.
        """
        
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
        
        # Sort and return
        files.sort()
        dirs.sort()
        return files, dirs
    
    
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
        
        # Get files and directories
        files, dirs = self._listDir(path)
        
        # Get search pattern
        searchPattern = self._tools._searchPattern.text()
        regExp = self._tools._searchIsRegExp.isChecked()
        
        
        if searchPattern and self._tools._searchButton.isChecked():
            # Apply a search
            
            # Expand subdirs?
            if self._tools._searchInSubdirs.isChecked():
                while dirs:
                    dirName = dirs.pop(0)
                    ff, dd = self._listDir(os.path.join(path, dirName))
                    files.extend([os.path.join(dirName,f) for f in ff])
                    dirs.extend([os.path.join(dirName,d) for d in dd])
            
            # Start thread
            self._startSearch(path, files, searchPattern, regExp)
        
        else:
            # Show directories now
            self._showFilesAndDirs(path, files, dirs)
    
    
    def _showFilesAndDirs(self, path, files, dirs):
        """ _showFilesAndDirs(files, dirs)
        Display the given files and directories in the list right now.
        """
        
        # Show parent directory
        #dirs.insert(0, '..')
        
        # Init list
        self.clear()
        self.setRootIsDecorated(False)
        
        # Show dirs
        if self._tools._showDirs.isChecked():
            for fname in dirs:
                ffname = os.path.join(path,fname)
                item = QtGui.QTreeWidgetItem([fname, ''], 1)
                item._dir = ffname
                item.setIcon(0, selectIconForDir(ffname))
                self.addTopLevelItem(item)
        
        # Show files
        if True:
            for fname in files:
                ffname = os.path.join(path,fname)
                size = self._getFileSize(ffname)
                item = QtGui.QTreeWidgetItem([fname, size], 0)
                item._fname = ffname
                item.setIcon(0, selectIconForFile(fname))
                item.setToolTip(0,'%s (%s)'%(ffname, size))
                self.addTopLevelItem(item)
    
    
    def _startSearch(self, path, files, pattern, regExp):
        """ _startSearch(path, files, pattern, regExp)
        Start a search with the given parameters.
        """
        
        # Stop old thread
        if self._searchThread is not None:
            self._searchThread._stop_me = True
        
        # Init progress bar
        self._tools._searchProgress.setRange(0,len(files))
        
        # Init list
        self.clear()
        self.setRootIsDecorated(True)
        
        # Create new thread and start it
        args = path, files, pattern, regExp
        self._searchThread = SearchThread(self._updateSearchResults, *args)
        self._searchThread.start()
    
    
    def _updateSearchResults(self, result):
        """ _updateSearchResults(result)
        Add new search results to the list.
        """ 
        
        # Check if result is valid for last search
        if not result.check(self._searchThread):
            return
        
        # Update progress bar
        self._tools._searchProgress.setValue(result.count)
        
        # Do not list the result if no matches were found
        if not result.lines:
            return
        
        # Get path, fname, and full filename
        path, fname = result.path, result.fname
        ffname = os.path.join(path,fname)
        
        # Insert item in list
        size = self._getFileSize(ffname)
        item = QtGui.QTreeWidgetItem([fname, size], 0)
        item._fname = ffname
        item.setIcon(0, selectIconForFile(fname))
        item.setToolTip(0,'%s (%s)'%(ffname, size))
        item.setChildIndicatorPolicy(item.ShowIndicator)
        self.addTopLevelItem(item)
        
        # Add sub items
        for linenr, line in result.lines:
            name = 'line %i: %s' % (linenr, line)
            subItem = QtGui.QTreeWidgetItem(item, [name, ''], 0)
            subItem._fname = ffname
            subItem._linenr = linenr
            item.addChild(subItem)


class SearchResult:
    def __init__(self, thread, path, fname, lines, count):
        self.id = id(thread)
        self.path = path
        self.fname = fname
        self.lines = lines        
        self.count = count
    
    def check(self, thread):
        """ check(thread)
        Check if this result came from the given thread.
        """
        if id(thread) == self.id:
            return True
        else:
            return False


class SearchThread(threading.Thread):
    """ This is the worker that searches the files in a directory for
    a specific search pattern.    
    """
    
    def __init__(self, callback, path, files, pattern, regExp):
        threading.Thread.__init__(self)
        
        # Store callback
        self._callback = callback
        
        # Store search parameters
        self._params = path, files, pattern, regExp
        
        # Flag to indicate it should stop
        self._stop_me = False
        
#         # Init info list
#         self._info = []
#         
#         # Init lock
#         self._lock = threading.RLock()
#     
#     
#     def addInfo(self, newInfo):
#         """ To add info in a thread safe way. 
#         """ 
#         self._lock.acquire()
#         try:
#             self._info.append(newInfo)
#         finally:
#             self._lock.release()
#     
#     
#     def getInfo(self):
#         """ To get info in a thread safe way. 
#         """ 
#         self._lock.acquire()
#         try:
#             tmp = [i for i in self._info]
#             self._info[:] = []
#             return tmp
#         finally:
#             self._lock.release()
    
    
    def run(self):
        
        # Get params
        path, files, pattern, regExp = self._params
        
        # Prepare counters
        count = 0
        maxCount = len(files)
        
        
        # For each file
        for fname in files:
            count += 1
            
            # Test if still good
            if self._stop_me:
                break
            
            # Get full file name and check whether it exists
            ffname = os.path.join(path, fname)
            if not os.path.isfile(ffname):
                result = SearchResult(self, path, fname, [], count)
                iep.callLater(self._callback, result)
                continue
            
            # Sleep a tiny bit
            time.sleep(0.001)
            
            # Read file and convert to text
            data = open(ffname, 'rb').read()
            try:
                text = data.decode('utf-8')
                del data
            except UnicodeDecodeError:
                result = SearchResult(self, path, fname, [], count)
                iep.callLater(self._callback, result)
                continue
            
            # Search indices where the pattern occurs
            indices = []
            if regExp:
                for match in re.finditer(pattern, text):
                    indices.append( match.start() )
            else:
                i = 0
                while i>=0:
                    i = text.find(pattern,i+1)
                    if i>=0:
                        indices.append(i)
            
            # Obtain line and line numbers
            lines = []
            for i in indices:
                # Get linenr and index of the line
                linenr = text.count('\n',0,i) + 1
                if linenr > 1:
                    i1 = text.rfind('\n',0,i)
                    i2 = text.find('\n',i)
                else:
                    linenr = text.count('\r',0,i) + 1
                    i1 = text.rfind('\r',0,i)
                    i2 = text.find('\r',i)
                # Get line and strip
                if i1<0:
                    i1 = 0
                line = text[i1:i2].strip()[:80]
                # Store
                lines.append( (linenr, line) )
            
            # Make result object and send
            result = SearchResult(self, path, fname, lines, count)
            iep.callLater(self._callback, result)


# todo: enable making bookmarks

class IepFileBrowser(QtGui.QWidget):
    
    somethingChanged = QtCore.pyqtSignal()
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self._config = iep.config.tools[toolId]
        if not hasattr(self._config, 'path'):
            self._config.path = os.path.expanduser('~')
        
        # Create current-directory-tool, and up button
        self._path = path = PathInput(self)
        #
        self._up = QtGui.QToolButton(self)
        #self._up.setText('up')
        #style = QtGui.qApp.style()
        #self._up.setIcon( style.standardIcon(style.SP_ArrowUp) )
        self._up.setIcon( iep.icons['folder_parent'] )
        
        
        # File pattern line edit
        self._filePattern = w = QtGui.QLineEdit(self)
        self._filePattern.setText('*.py *.pyw, *.pyx, *.pxd')
        self._filePattern.setToolTip('File pattern')        
        
        # Show dirs check box
        self._showDirs = QtGui.QCheckBox(self)
        self._showDirs.setText('Show dirs')
        self._showDirs.setChecked(True)
        
        # Search toggle button
        self._searchButton = QtGui.QCheckBox(self)
        self._searchButton.setText('SEARCH')
        self._searchButton.setStyleSheet("QCheckBox{background:#aad;}")
        
        # Search progress bar
        self._searchProgress = QtGui.QProgressBar(self)
        self._searchProgress.setMaximumHeight(15)
        self._searchProgress.setFormat('%v/%m')
        
        # Search pattern line edit
        self._searchPattern = QtGui.QLineEdit(self)
        self._searchPattern.setToolTip('Search pattern')
        
        # Search reg-exp check box
        self._searchIsRegExp = QtGui.QCheckBox(self) 
        self._searchIsRegExp.setText('RegExp')
        
        # Search in subdirs check button
        self._searchInSubdirs = QtGui.QCheckBox(self) 
        self._searchInSubdirs.setText('Subdirs')
        
        # Create browser
        self._browser = Browser(self)
        
        
        # Set placeholder texts (Requires Qt 4.7)
        for lineEdit in [self._filePattern, self._searchPattern]:
            if hasattr(lineEdit, 'setPlaceholderText'):
                lineEdit.setPlaceholderText(lineEdit.toolTip())
        
        
        # Bind to signals
        self._filePattern.editingFinished.connect(self.onSomethingMaybeChanged)
        self._searchPattern.editingFinished.connect(self.onSomethingMaybeChanged)
        self._filePattern.returnPressed.connect(self.onSomethingChanged)
        self._searchPattern.returnPressed.connect(self.onSomethingChanged)
        #
        self._showDirs.released.connect(self.onSomethingChanged)
        self._searchIsRegExp.released.connect(self.onSomethingChanged)
        self._searchInSubdirs.released.connect(self.onSomethingChanged)
        self._searchButton.released.connect(self.onSearchButtonPressed)
        #
        self._up.pressed.connect(self._path.goUp)
        self._path.dirChanged.connect(self._browser.showDir)
        
        # Start
        self.init_layout()
        self.restoreFromConfig()
        self.onSearchButtonPressed()
        self._path.init(self._config)
    
    
    def init_layout(self):
        """ init_layout()
        Set the layout of all items in this widget.
        """
        
        # List of layouts
        layouts = []
        
        # First row
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self._up, 0)
        layout.addWidget(self._path, 1)
        layouts.append(layout)
        
        # Second row
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self._filePattern, 4)
        layout.addWidget(self._showDirs, 0)
        layout.addStretch(1)
        layout.addWidget(self._searchButton, 0)
        layouts.append(layout)
        
        # Third row
        layouts.append(self._searchProgress)
        
        # Fourth row
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self._searchPattern, 1)
        layout.addWidget(self._searchIsRegExp, 0)
        layout.addWidget(self._searchInSubdirs, 0)
        layouts.append(layout)
        
        # Last row
        layouts.append(self._browser)
        
        
        # Set layout
        mainLayout = QtGui.QVBoxLayout(self)
        mainLayout.setSpacing(2)
        #
        for layout in layouts:
            if isinstance(layout, QtGui.QLayout):
                #layout.setSpacing(2)
                mainLayout.addLayout(layout)
            else:
                mainLayout.addWidget(layout)
        #
        self.setLayout(mainLayout)
    
    
    def restoreFromConfig(self):
        """ restoreFromConfig()
        Restore all user inputs from previous session. 
        """
        
        # Set line edits
        # Note that the path maintains its own value in the config
        for name in ['filePattern', 'searchPattern']:
            if name in self._config:
                lineEdit = self.__dict__['_'+name]
                text = self._config[name]
                lineEdit.setText(text)
        
        # Set check boxes
        for name in ['showDirs', 'searchIsRegExp', 'searchInSubdirs', 'searchButton']:
            if name in self._config:
                checkBox = self.__dict__['_'+name]
                state = bool(self._config[name])
                checkBox.setChecked(state)
    
    
    def updateConfig(self):
        """ updateConfig()
        Store all user inputs for next session. 
        """
        
        # Set line edits
        for name in ['filePattern', 'searchPattern']:
            lineEdit = self.__dict__['_'+name]
            self._config[name] = lineEdit.text()
        
        # Set check boxes
        for name in ['showDirs', 'searchIsRegExp', 'searchInSubdirs', 'searchButton']:
            checkBox = self.__dict__['_'+name]
            self._config[name] = checkBox.isChecked()
    
    
    def onSomethingChanged(self):
        """ onSomethingChanged()
        Updates the config and emits the signal that invokes the browser
        to update its contents.
        """
        self.updateConfig()
        self.somethingChanged.emit()
    
    
    def onSomethingMaybeChanged(self):
        """ onSomethingMaybeChanged()
        Call onSomethingChanged if the file pattern or search pattern
        content has changed.
        """
        for name in ['filePattern', 'searchPattern']:
            lineEdit = self.__dict__['_'+name]
            text = self._config[name]
            if text != lineEdit.text():
                self.onSomethingChanged()
                break
    
    
    def onSearchButtonPressed(self):
        """ onSearchButtonPressed()
        When the search toggle button is pressed, we need to show
        or hide the search widgets.
        """
        
        # Clear search text
        self._searchPattern.setText('')
        self._searchProgress.reset()
        
        if self._searchButton.isChecked():
            # Expand
            self._searchPattern.show()
            self._searchIsRegExp.show()
            self._searchProgress.show()
            self._searchInSubdirs.show()
        else:
            # Collapse
            self._searchPattern.hide()
            self._searchIsRegExp.hide()
            self._searchProgress.hide()
            self._searchInSubdirs.hide()
        
        # Update
        self.onSomethingChanged()
