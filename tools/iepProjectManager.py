from PyQt4 import QtCore, QtGui
import iep
import os
import sys
import ssdf
import fnmatch

tool_name = "Project manager"
tool_summary = "Manage project directories."

# todo: desired changes:
# - Make project settings a separate dialog (add/delete/move/rename/preped project dir to python path)
# - Search using separate search tool
# - Popup menu with usefull actions

class ProjectManagerMenu(QtGui.QMenu):
    def __init__(self, parent):
        QtGui.QMenu.__init__(self, parent)
        
        action = self.addAction('Add project')
        action.setIcon(iep.icons.add)
#         action.triggered.connect(self._add)
        
        action = self.addAction('Manage projects')
        action.setIcon(iep.icons.star)
#         action.triggered.connect(self._add)


class Project(ssdf.Struct):
    def __init__(self,name,path):
        self.name=name
        self.path=path
        self.addToPath=False
    def __repr__(self):
        return "Project %s at %s" % (self.name,self.path)
    

class ProjectsModel(QtCore.QAbstractListModel):
    def __init__(self,config):
        QtCore.QAbstractListModel.__init__(self)
        self.config=config
    def rowCount(self,parent):
        return len(self.config.projects)
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return self.projectFromIndex(index).name
        elif role == QtCore.Qt.UserRole:
            return self.projectFromIndex(index)
        elif role == QtCore.Qt.DecorationRole:
            return iep.icons.star
    
    def setData(self,index,value,role):
        """Change the name of a project"""
        if not index.isValid():
            return False
        elif role == QtCore.Qt.EditRole:
            self.projectFromIndex(index).name=value
            self.dataChanged.emit(index,index)
            return True
        return False
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction
    def flags(self,index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        else:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | \
                QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | \
                QtCore.Qt.ItemIsDropEnabled
                
    def add(self,project):
        self.config.projects.append(project)
        self.reset()
        return self.config.projects.index(project)
    def remove(self,project):
        self.config.projects.remove(project)
        self.reset()
    def projectFromIndex(self,index):
        return self.config.projects[index.row()]
    def projectFromRow(self,row):
        if row<0 or row>=len(self.config.projects):
            return None
        return self.config.projects[row]
    def swapRows(self,row1,row2):
        if row1==row2:
            return
            
        #Ensure row1<row2
        if row2>row1:
            row1,row2=row2,row1
            
        self.beginMoveRows(QtCore.QModelIndex(),row1,row1,QtCore.QModelIndex(),row2)
        project1=self.config.projects[row1]
        self.config.projects[row1]=self.config.projects[row2]
        self.config.projects[row2]=project1
        self.endMoveRows()


class ProjectItemMenu(QtGui.QMenu):
    def __init__(self, parent):
        QtGui.QMenu.__init__(self, parent)
        
        action = self.addAction('Add project')
        action.setIcon(iep.icons.add)
        action.triggered.connect(self._add)
        
        self.addSeparator()
        
        action = self.addAction('Move project up')
        action.setIcon(iep.icons.arrow_redo)
        action.triggered.connect(self._up)
        
        action = self.addAction('Move project down')
        action.setIcon(iep.icons.arrow_undo)
        action.triggered.connect(self._down)
        
        self.addSeparator()
        
        action = self.addAction('Rename project')
        action.setIcon(iep.icons.text_replace)
        action.triggered.connect(self._rename)
       
        action = self.addAction('Remove project')
        action.setIcon(iep.icons.delete)
        action.triggered.connect(self._delete)
    
    def _add(self):
        self.parent().parent().addProjectClicked()
    
    def _up(self, dummy=None, delta=-1):
        index = self.parent().currentIndex()
        nprojects = len(self.parent().parent().config.projects)
        if index.isValid():
            row1 = index.row()
            row2 = row1 + delta
            if row2 >= 0 and row2 < nprojects:
                self.parent().model().swapRows(row1,row2)
    
    def _down(self):
        self._up(delta=1)
    
    def _rename(self):
        self.parent().edit(self.parent().currentIndex())    
    
    def _delete(self):
        self.parent().parent().removeProjectClicked()


class ProjectsList(QtGui.QListView):
    def __init__(self):
        QtGui.QListView.__init__(self)
        self.draggingRow=None
        
    def mouseMoveEvent(self,event):
        """
        If the user drags an item, swap rows if necessary
        """
        pos=event.pos()
        index=self.indexAt(pos)
        if not index.isValid():
            return
        
        #Find ot the new position of the row
        rect=self.visualRect(index)
        newRow=index.row()
        if pos.y()>rect.y()+rect.height()/2:
            #Below the horizontal center line of the item
            newRow+=1
        if newRow>self.draggingRow:
            #Moving below the original position
            newRow-=1
            
        if newRow!=self.draggingRow:
            self.model().swapRows(newRow,self.draggingRow)
            self.draggingRow=newRow
            
        #TODO: when the order is changed, the ProjectManager should update
        #config.activeproject
    def mousePressEvent(self,event):
        """Register at which row a drag operation starts"""
        self.draggingRow=self.indexAt(event.pos()).row()
        QtGui.QListView.mousePressEvent(self,event) 
    
    def contextMenuEvent(self, event):
        menu = ProjectItemMenu(self)
        menu.move(event.globalX(), event.globalY())
        menu.show()


class DirSortAndFilter(QtGui.QSortFilterProxyModel):
    """
    Proxy model to filter a directory tree based on filename patterns,
    sort directories before files and sort dirs/files on name, case-insensitive 
    """
    def __init__(self):
        QtGui.QSortFilterProxyModel.__init__(self)
        self.filter=''
        
        # Specify sorting behaviour when comparing of two dirs or two files
        # Sorting dirs before files is none in the lessThan function 
        self.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        
        # todo: does it now work everywhere??
        # Not sure why, but on Windows & Linux it should be different than Mac
        if sys.platform == 'darwin':
            self.sort(0)
        else:
            self.setDynamicSortFilter(True)
    
    def lessThan(self,left,right):
        if self.sourceModel().isDir(left) and \
                not self.sourceModel().isDir(right):
            return True
        # Comparing two dirs or two files: default behaviour
        return QtGui.QSortFilterProxyModel.lessThan(self,left,right)
        
    def filterAcceptsRow(self,sourceRow,sourceParent):
        #Overridden method to determine wether a row should be
        #shown or not. Check wether the item matches the filter
        
        #Get the fileinfo of the item
        item=self.sourceModel().index(sourceRow,0,sourceParent)
        fileInfo=self.sourceModel().fileInfo(item)
        fileName=fileInfo.fileName()
        
        # Explicitlty hide files/dirs starting with a dot.
        if fileName.startswith('.'):
            return False
        
        #Show everything that's not a file
        if not fileInfo.isFile():
            return True
        
        #'default' is the return value when no filter matches. A 'hide' filter
        #(i.e. starting with '!') sets the default to 'show', a 'show' filter
        #(i.e. not starting with '!') sets the default to 'hide'
        
        default=True #Return True if there are no filters
        
        #Get the current filter spec and split it into separate filters
        filters=self.filter.replace(',',' ').split()          
        for filter in filters:
            #Process filters in order
            if filter.startswith('!'):
                #If the filename matches a filter starting with !, hide it
                if fnmatch.fnmatch(fileName,filter[1:]):
                    return False
                default=True
            else:
                #If the file name matches a filter not starting with!, show it
                if fnmatch.fnmatch(fileName,filter):
                    return True
                default=False
                    
        #No filter matched, return True
        return default
        
    def setFilter(self,filter):
        """Set and apply the filter"""
        self.filter=filter
        self.invalidateFilter()
        


class IconProviderWindows(QtGui.QFileIconProvider):
    """ IconProvider that will give icons for files without any overlays.
    (Because the overlays will be wrong)
    It does this by creating dummy files with a corresponding extension and
    obtaining the icon for that file.
    """
    def icon(self, type_or_info):
        class MyFileInfo(QtCore.QFileInfo):
            def __getattr__(self,attr):
                print (attr)
                return getattr(QtCore.QFileInfo,attr)
        if isinstance(type_or_info, QtCore.QFileInfo):
            if type_or_info.isDir():
                # Use folder icon
                icon = QtGui.QFileIconProvider.icon(self, self.Folder)
                # Add overlay?
                path = type_or_info.absoluteFilePath()
                if os.path.isdir(os.path.join(path, '.hg')):
                    icon = self._addOverlays(icon, iep.icons.overlay_hg)
                elif os.path.isdir(os.path.join(path, '.svn')):
                    icon = self._addOverlays(icon, iep.icons.overlay_svn)
                # Done
                return icon
            else:
                # Get extension
                root, ext = os.path.splitext(type_or_info.fileName())
                # Create dummy file in iep user dir
                dir = os.path.join(iep.appDataDir, 'dummyFiles')
                path = os.path.join(dir, 'dummy' + ext)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                f = open(path, 'wb')
                f.close()
                # Use that file
                type_or_info = QtCore.QFileInfo(path)
        
        # Call base method
        return QtGui.QFileIconProvider.icon(self, type_or_info)
    
    
    def _addOverlays(self, icon, *overlays):
        
        # Get pixmap
        pm0 = icon.pixmap(16,16)
        
        # Create painter
        painter = QtGui.QPainter()
        painter.begin(pm0)
        
        for overlay in overlays:
            pm1 = overlay.pixmap(16,16)
            painter.drawPixmap(0,0, pm1)
        
        # Finish
        painter.end()
        
        # Done (return resulting icon)
        return QtGui.QIcon(pm0)


class IepProjectManager(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self.config = iep.config.tools[toolId]
        if not hasattr(self.config, 'projects'):
            self.config.projects=[]
        if not hasattr(self.config,'activeproject'):
            self.config.activeproject=-1
        if not hasattr(self.config,'filter'):
            self.config.filter='!*.pyc'
        if not hasattr(self.config,'listdisclosed'):
            self.config.listdisclosed=True
        
        #Init projects model
        self.projectsModel=ProjectsModel(self.config)

        #Init dir model and filtered dir model
        self.dirModel=QtGui.QFileSystemModel()
        #TODO: using the default IconProvider bugs on mac, restoring window state fails
        
        self.dirModel.setIconProvider(IconProviderWindows())
        #TODO: self.dirModel.setSorting(QtCore.QDir.DirsFirst)
        # todo: huh? QFileSystemModel.setSorting Does not exist
        self.filteredDirModel=DirSortAndFilter()
        self.filteredDirModel.setSourceModel(self.dirModel)
                
        #Init widgets and layout
        self.buttonLayout=QtGui.QVBoxLayout()
#         self.listDisclosureButton=QtGui.QPushButton('...')
        self.listDisclosureButton = QtGui.QPushButton(self)
        self.listDisclosureButton.setCheckable(True)
#         self.listDisclosureButton.setMenu(ProjectManagerMenu(self))
        self.listDisclosureButton.setIcon(iep.icons.wrench)
        self.listDisclosureButton.setIconSize(QtCore.QSize(16,16))
        
        #The following two buttons are only added when the list is disclosed
        self.addProjectButton=QtGui.QPushButton('+')
        self.removeProjectButton=QtGui.QPushButton('-')
        
        self.buttonLayout.addWidget(self.listDisclosureButton,0)
        self.buttonLayout.addStretch(1)

        self.projectsCombo=QtGui.QComboBox()
        self.projectsCombo.setModel(self.projectsModel)
        
        self.hLayout=QtGui.QHBoxLayout()
        self.hLayout.addWidget(self.projectsCombo,1)
        self.hLayout.addLayout(self.buttonLayout,0)
  
        self.projectsList=ProjectsList()
        self.projectsList.setModel(self.projectsModel)
        
        self.addToPathCheck=QtGui.QCheckBox('Prepend project dir to Python path')
        self.addToPathCheck.setToolTip('Takes effect when the shell is restarted')
        self.dirList=QtGui.QTreeView()
        
        # The lessThan function in DirSortAndFilter ensures dirs are before files
        self.dirList.sortByColumn(0)
        self.filterCombo=QtGui.QComboBox()

        self.layout=QtGui.QVBoxLayout()
        self.layout.addLayout(self.hLayout)
        self.layout.addWidget(self.addToPathCheck)
        self.layout.addWidget(self.dirList,10)
        self.layout.addWidget(self.filterCombo)
        
        self.setLayout(self.layout)
        
        #Load projects in the list
        self.projectsCombo.show()
        
        #Load default filters
        self.filterCombo.setEditable(True)
        self.filterCombo.setCompleter(None)
        self.filterCombo.setInsertPolicy(self.filterCombo.NoInsert)
        for pattern in ['*', '!*.pyc','*.py *.pyw *.pyx *.pxd', '*.h *.c *.cpp']:
            self.filterCombo.addItem(pattern)
        self.filterCombo.editTextChanged.connect(self.filterChanged)
        
        # Set file pattern line edit (in combobox)
        self.filterPattern = self.filterCombo.lineEdit()
        self.filterPattern.setText(self.config.filter)
        self.filterPattern.setToolTip('File filter pattern')        

        #Connect signals
        self.projectsCombo.currentIndexChanged.connect(self.comboChangedEvent)
        self.projectsList.selectionModel().currentChanged.connect(self.listChangedEvent)
        self.dirList.doubleClicked.connect(self.itemDoubleClicked)
        
        self.listDisclosureButton.toggled.connect(self.listDisclosed)
        self.addProjectButton.clicked.connect(self.addProjectClicked)
        self.removeProjectButton.clicked.connect(self.removeProjectClicked)
        self.addToPathCheck.stateChanged.connect(self.addToPathStateChanged)
        
        #Apply previous selected project
        self.activeProject = None
        self.projectChanged(self.config.activeproject)
        if self.config.listdisclosed:
            self.listDisclosureButton.toggle()
    ## Methods
    def getAddToPythonPath(self):
        """
        Returns the path to be added to the Python path when starting a shell
        If a project is selected, which has the addToPath checkbox selected,
        returns the path of the project. Otherwise, returns None
        """
        if self.activeProject and self.activeProject.addToPath:
            return self.activeProject.path
        else:
            return None
        
    ## Project changed handlers
    def comboChangedEvent(self,newIndex):
        self.projectChanged(newIndex)
            
    def listChangedEvent(self,current,previous):
        if not current.isValid():
            self.projectChanged(-1)
        else:
            self.projectChanged(current.row())
        
    def projectChanged(self,projectIndex):
        """Handler for when the project is changed
        projectIndex: -1 or None for no project or 0..len(projects)
        """
        if projectIndex==-1 or projectIndex is None:
            #This happens when the model is reset
            self.dirList.setModel(None)
            self.addToPathCheck.setEnabled(False)
            self.activeProject = None
            return
        
        #Remember the previous selected project
        self.config.activeproject=projectIndex
    
        #Sync list and combo boxes
        self.projectsCombo.setCurrentIndex(projectIndex)
        self.projectsList.selectionModel().setCurrentIndex(self.projectsModel.index(projectIndex), 
                QtGui.QItemSelectionModel.ClearAndSelect)
    
        #Sync the dirList
        project=self.projectsModel.projectFromRow(projectIndex)
        if project is None:
            self.addToPathCheck.setEnabled(False)
            return #Invalid project index
        self.activeProject = project
        
        self.addToPathCheck.setEnabled(True)
        if not hasattr(project,"addToPath"):
            project.addToPath = False
    
        self.addToPathCheck.setChecked(project.addToPath)
    
        path=project.path
    
        self.dirList.setModel(self.filteredDirModel)
        self.dirList.setColumnHidden(1,True)
        self.dirList.setColumnHidden(2,True)
        self.dirList.setColumnHidden(3,True)
        
        self.dirModel.setRootPath(path)
        self.dirList.setRootIndex(self.filteredDirModel.mapFromSource(self.dirModel.index(path)))
        
    def addToPathStateChanged(self,state):
        if not self.activeProject:
            return
        self.activeProject.addToPath = self.addToPathCheck.isChecked()
 
    ## Add/remove buttons
    def addProjectClicked(self):
        dir=QtGui.QFileDialog.getExistingDirectory(None,'Select project directory')
        if dir=='':
            return #Cancel was pressed
        _,projectName=os.path.split(dir)
        index=self.projectsModel.add(Project(projectName,dir))
        self.projectChanged(index)
        
    def removeProjectClicked(self):
        if not self.projectsList.currentIndex().isValid():
            return
        
        projectIndex=self.projectsList.currentIndex()
        projectRow=projectIndex.row()
        project=self.projectsModel.projectFromIndex(projectIndex)
  
        confirm=QtGui.QMessageBox(QtGui.QMessageBox.Warning,
            "Remove project?",
            "Remove project '%s'?" % project.name)
            
        confirm.addButton("Remove",QtGui.QMessageBox.DestructiveRole)
        cancel=confirm.addButton("Cancel",QtGui.QMessageBox.RejectRole)
        confirm.setDefaultButton(cancel)
        confirm.setEscapeButton(cancel)
        
        confirm.setInformativeText("The project contents will not be removed.")
        confirm.exec_()
        
        if confirm.result()!=0: #Cancel button pressed
            return
        
        
        self.projectsModel.remove(project)
        
        #Select another project (try the one before)
        if projectRow>0:
            projectRow-=1
            
        if self.projectsModel.projectFromRow(projectRow) is None:
            #If we deleted the last project
            projectRow=-1

        self.projectChanged(projectRow)

    def listDisclosed(self):
        """Handler for when disclosure button toggled"""
        if self.listDisclosureButton.isChecked():   
            self.hLayout.insertWidget(0,self.projectsList,1)
            self.hLayout.removeWidget(self.projectsCombo)
            self.buttonLayout.addWidget(self.addProjectButton,0)
            self.buttonLayout.addWidget(self.removeProjectButton,0)
            self.projectsCombo.hide()
            self.projectsList.show()
            self.addProjectButton.show()
            self.removeProjectButton.show()
        else:
            self.hLayout.insertWidget(0,self.projectsCombo,1)
            self.hLayout.removeWidget(self.projectsList)
            self.projectsList.hide()
            self.buttonLayout.removeWidget(self.addProjectButton)
            self.buttonLayout.removeWidget(self.removeProjectButton)
            self.addProjectButton.hide()
            self.removeProjectButton.hide()
            self.projectsCombo.show()
            
        self.config.listdisclosed=self.listDisclosureButton.isChecked()
        
    
    def filterChanged(self):
        """Handler for when the filter is changed"""
        filter=self.filterCombo.lineEdit().text()
        self.config.filter=filter
        self.filteredDirModel.setFilter(filter)
        
   
    def itemDoubleClicked(self,item):
        """Handler for if an item is double-clicked"""
        info=self.dirModel.fileInfo(self.filteredDirModel.mapToSource(item))
        if info.isFile():
            # todo: maybe open the file, read some bytes and see if there
            # is an encoding tag or if it correctly decodes with utf-8.
            # we could even do that in the filter, and simply not list binary
            # files.
            
            # The user should be able to read in any reabable file. We can
            # never specify all extension of readable files beforehand. So
            # better specify reading the files of which we know to be binary.
            #if info.suffix() in ['py','c','pyw','pyx','pxd','h','cpp','hpp']:
            if info.suffix() not in ['pyc','pyo','png','jpg','ico']:
                iep.editors.loadFile(info.absoluteFilePath())
            
