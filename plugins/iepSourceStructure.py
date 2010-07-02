""" PLUGIN SOURCE STRUCTURE


"""

import time
from PyQt4 import QtCore, QtGui
import iep
ssdf = iep.ssdf

plugin_name = "Source Structure"
plugin_summary = "Shows the structure of your source code"


class IepSourceStructure(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Make sure there is a configuration entry for this plugin
        # The IEP tool manager makes sure that there is an entry in
        # config.plugins before the tool is instantiated.
        pluginId = self.__class__.__name__.lower()        
        self._config = iep.config.plugins[pluginId]
        if not hasattr(self._config, 'showTypes'):
            self._config.showTypes = ['class', 'def', 'cell', 'todo']
        if not hasattr(self._config, 'level'):
            self._config.level = 2
        
        # Create slider
        self._slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self._slider.setTickPosition(QtGui.QSlider.TicksBelow)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setRange(1,9)
        self._slider.setValue(self._config.level)
        self._slider.valueChanged.connect(self.updateStructure)
        
        # Create button
        self._button = QtGui.QPushButton(self)
        self._button.setText('Show ...')
        self._button.pressed.connect(self.onButtonPress)
        
        # Create tree widget        
        self._tree = QtGui.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.itemCollapsed.connect(self.updateStructure) # keep expanded
        self._tree.itemClicked.connect(self.onItemClick)
        
        # Create two sizers
        self._sizer1 = QtGui.QVBoxLayout(self)
        self._sizer2 = QtGui.QHBoxLayout()
        # self._sizer1.setSpacing()
        
        # Set layout
        self.setLayout(self._sizer1)
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._tree, 1)
        self._sizer2.addWidget(self._slider, 1)
        self._sizer2.addWidget(self._button, 0)
        
        # Init current-file name and listen to selection changes
        self._currentEditorId = 0
        iep.editors.changedSelected.connect(self.onSelectedEditorChanged)
        iep.editors.parserDone.connect(self.updateStructure)
        
        # When the plugin is loaded, the editorStack is already done loading
        # all previous files and selected the appropriate file.
        self.onSelectedEditorChanged()
    
    
    def onButtonPress(self):
        """  Let the user decide what to show in the structure. """
        
        # Prepare lists
        allTypes = ['class', 'def', 'cell', 'todo', 'import']
        callBacks = [   self.onMenu_class, self.onMenu_def, self.onMenu_cell,
                        self.onMenu_todo, self.onMenu_import]
        
        # Prepare menu
        menu = QtGui.QMenu(self)
        for type, callback in zip(allTypes, callBacks):
            checked = type in self._config.showTypes
            action = menu.addAction(type, callback)
            action.setCheckable(True)
            action.setChecked(checked)
        
        # Show menu
        menu.popup(QtGui.QCursor.pos())
        self._slider.setFocus(True)
    
    
    def onMenu_class(self):
        self.onMenu_swap('class')
    def onMenu_def(self):
        self.onMenu_swap('def')
    def onMenu_cell(self):
        self.onMenu_swap('cell')
    def onMenu_todo(self):
        self.onMenu_swap('todo')
    def onMenu_import(self):
        self.onMenu_swap('import')
    def onMenu_swap(self, type):
        # Save
        if type in self._config.showTypes:
            while type in self._config.showTypes:
                self._config.showTypes.remove(type)
        else:
            self._config.showTypes.append(type)
        # Update
        self.updateStructure()
    
    
    def onSelectedEditorChanged(self):
        """ Notify that the file is being parsed and make
        sure that not the structure of a previously selected
        file is shown. """
        
        # Get editor and clear list
        editor = iep.editors.getCurrentEditor()        
        self._tree.clear()
        
        if editor is None:
            # Set editor id
            self._currentEditorId = 0
        
        if editor is not None:
            # Set editor id
            self._currentEditorId = id(editor)
            
            # Notify
            text = 'Parsing ' + editor._name + ' ...'
            thisItem = QtGui.QTreeWidgetItem(self._tree, [text])
            
            # Try getting the  structure right now
            self.updateStructure()
    
    
    def onItemClick(self, item):
        """ Go to the right line in the editor and give focus. """
        
        # Get editor
        editor = iep.editors.getCurrentEditor()
        if not editor:
            return
        
        # Move to line
        editor.gotoLine(item.linenr+30)
        editor.gotoLine(item.linenr-10)
        editor.gotoLine(item.linenr-1)
        
        # Give focus
        iep.callLater(editor.setFocus, True)

    
    def updateStructure(self):
        """ Updates the tree. 
        """
        
        # Get editor
        editor = iep.editors.getCurrentEditor()
        if not editor:
            return
        
        # Something to show
        result = iep.parser._getResult()
        if result is None:
            return
        
        # Do the ids match?
        id0, id1, id2 = self._currentEditorId, id(editor), result.editorId 
        if id0 != id1 or id0 != id2:
            return
        
        # Get current line number and the structure
        ln, index = editor.getLinenrAndIndex()
        ln += 1  # is ln as in margin
        
        # Define colours
        colours = {'cell':'#007F00', 'class':'#0000FF', 'def':'#007F7F', 
                    'var':'#444444', 'import':'#8800BB', 'todo':'#FF3333'}
        
        # Define what to show
        showTypes = self._config.showTypes
        
        # Define to what level to show (now is also a good time to save)
        showLevel = int( self._slider.value() )
        self._config.level = showLevel
        
        # Define function to set items
        selectedItem = [None]
        def SetItems(parentItem, fictiveObjects, level):
            level += 1
            for object in fictiveObjects:
                type = object.type
                if not type in showTypes:
                    continue
                # Construct text
                if type=='cell':
                    type = '##'
                if type == 'import':                   
                    text = "%s (%s)" % (object.name, object.text)
                elif type=='todo':
                    text = object.name                    
                else:
                    text = "%s %s" % (type, object.name)
                # Create item
                thisItem = QtGui.QTreeWidgetItem(parentItem, [text])
                color = QtGui.QColor(colours[object.type])
                thisItem.setForeground(0, QtGui.QBrush(color))
                font = thisItem.font(0)
                font.setBold(True)
                thisItem.setFont(0, font)
                thisItem.linenr = object.linenr
                # Is this the current item?
                if ln and object.linenr <= ln and object.linenr2 > ln:
                    selectedItem[0] = thisItem                    
                # Any children that we should display?
                if object.children:
                    SetItems(thisItem, object.children, level)
                # Set visibility 
                thisItem.setExpanded( bool(level < showLevel) )
        
        # Go
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        SetItems(self._tree, result.rootItem.children, 0)
        self._tree.setUpdatesEnabled(True)
        
        # Handle selected item
        selectedItem = selectedItem[0]
        if selectedItem:
            selectedItem.setBackground(0, QtGui.QBrush(QtGui.QColor('#CCC')))
            self._tree.scrollToItem(selectedItem) # ensure visible
        