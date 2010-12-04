from PyQt4 import QtCore, QtGui
import iep
import os.path
import ssdf

tool_name = "Project manager"
tool_summary = "Manage project directories."

class Project(ssdf.Struct):
    def __init__(self,name,path):
        self.name=name
        self.path=path
    def __repr__(self):
        return "Project %s at %s" % (self.name,self.path)

class ProjectsList(QtGui.QComboBox):
    """
    Combobox showing the projects
    Allows adding/renaming/removing projects using context menu
    """
    #Signal emitted when a different project is selected
    projectChanged=QtCore.pyqtSignal(str)
    def __init__(self):
        QtGui.QComboBox.__init__(self)
        
        self.config=object()
        self.projectsList=[]
        self.currentIndexChanged.connect(self.currentIndexChangedEvent)
        
    def setConfig(self,config):
        self.config=config
        self.projectsList=self.config.projects
        self.fill()
        self.setCurrentIndex(config.activeproject)
        self.currentIndexChangedEvent(config.activeproject)

    
    def fill(self):
        self.clear()
        if not self.projectsList:
            self.insertItem(0,"<Right-click to add projects>",None)
        else:
            for i,project in enumerate(self.projectsList):
                self.insertItem(i,project.name,project)
                
        
    def currentIndexChangedEvent(self,newIndex):
        self.config.activeproject=newIndex
        project=self.itemData(self.currentIndex())
        if project is None:
            self.projectChanged.emit('')
        else:
            self.projectChanged.emit(project.path)
        
    def contextMenuEvent(self,evt):
        project=self.itemData(self.currentIndex())
        
    
        contextMenu=QtGui.QMenu()
        contextMenu.addAction("Add project",self.addProject)
        if project is not None:
            contextMenu.addAction("Rename '%s'" % project.name,self.renameProject)
            contextMenu.addAction("Remove '%s'" % project.name,self.removeProject)
        contextMenu.exec_(evt.globalPos())

    def addProject(self):
        dir=QtGui.QFileDialog.getExistingDirectory(None,'Select project directory')
        _,projectName=os.path.split(dir)
        self.projectsList.append(Project(projectName,dir))
        self.fill()
        
    def renameProject(self):
        project=self.itemData(self.currentIndex())
        oldName=project.name
        newName,ok=QtGui.QInputDialog.getText(None,"Rename project",
            "Rename '%s' to:" % oldName,text=oldName)
        if not ok:
            return
        
        project.name=newName
        self.fill()
        
    def removeProject(self):
        project=self.itemData(self.currentIndex())
        
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
        
        self.projectsList.remove(project)
        
        self.fill()
        
    def _currentProject(self):
        """Use the currentIndex to find the reference to the project in the
        self.projectsList"""
        
        #Somehow, self.itemData() returns a copy
        
        
        

        

class IepProjectManager(QtGui.QWidget):
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self._config = iep.config.tools[toolId]
        if not hasattr(self._config, 'projects'):
            self._config.projects=[]
        if not hasattr(self._config,'activeproject'):
            self._config.activeproject=-1

        #Init dir model
        self.dirModel=QtGui.QDirModel()
        self.dirModel.setSorting(QtCore.QDir.DirsFirst)
                
                
        #Init widgets and layout
        self.layout=QtGui.QBoxLayout(2,self)
        
        self.comboBox=ProjectsList()
        self.dirList=QtGui.QTreeView()

        

        self.layout.addWidget(self.comboBox)
        self.layout.addWidget(self.dirList,1)
        
        #Load projects in the list
        
        self.comboBox.show()

        #Connect signals
        self.comboBox.projectChanged.connect(self.projectChanged)
        self.dirList.doubleClicked.connect(self.itemDoubleClicked)
        
        #Load projects and active project from config
        #This needs to be done after the signals have been connected!
        self.comboBox.setConfig(self._config)
        
    def projectChanged(self,path):
        if path == '':
            self.dirList.setModel(None)
            return
        
        self.dirList.setModel(self.dirModel)
        self.dirList.setColumnHidden(1,True)
        self.dirList.setColumnHidden(2,True)
        self.dirList.setColumnHidden(3,True)
        
        self.dirList.setRootIndex(self.dirList.model().index(path))
    
    def itemDoubleClicked(self,item):
        info=self.dirList.model().fileInfo(item)
        if info.isFile():
            #TODO: check extension associations
            if info.suffix() in ['py','c','pyw','pyx','pxd','h','cpp','hpp']:
                iep.editors.loadFile(info.absoluteFilePath())
