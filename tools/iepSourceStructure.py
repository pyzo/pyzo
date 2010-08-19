""" TOOL SOURCE STRUCTURE


"""

import time
from PyQt4 import QtCore, QtGui
import iep
ssdf = iep.ssdf

tool_name = "Source Structure"
tool_summary = "Shows the structure of your source code."


class IepSourceStructure(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Make sure there is a configuration entry for this tool
        # The IEP tool manager makes sure that there is an entry in
        # config.tools before the tool is instantiated.
        toolId = self.__class__.__name__.lower()        
        self._config = iep.config.tools[toolId]
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
        self._button = QtGui.QToolButton(self)
        self._button.setText('   Show    ')
        self._button.setToolTip("What elements to show.")
        self._button.setPopupMode(self._button.InstantPopup)
        self._button.pressed.connect(self.onButtonPress)
        self._button.triggered.connect(self.onButtonMenuTiggered)
        self.onButtonPress() # Create menu
        
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
        
        # When the tool is loaded, the editorStack is already done loading
        # all previous files and selected the appropriate file.
        self.onSelectedEditorChanged()
    
    
    def onButtonPress(self):
        """ Create the menu for the button, Do each time to make sure
        the checks are right. """
        menu = QtGui.QMenu(self)
        self._button.setMenu(menu)
        for type in ['class', 'def', 'cell', 'todo', 'import', 'attribute']:
            checked = type in self._config.showTypes
            action = menu.addAction(type)
            action.setCheckable(True)
            action.setChecked(checked)
    
    def onButtonMenuTiggered(self, action):
        """  The user decides what to show in the structure. """
        
        # What to show
        type = action.text()
        
        # Swap
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
        
        # If item is attribute, get parent
        if not item.linenr:
            item = item.parent()
        
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
                    'attribute':'#444444', 'import':'#8800BB', 'todo':'#FF3333'}
        
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
                elif type=='attribute':
                    type = 'attr'
                #
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
                # Any variable members that we should display?
#                 if object.type == 'class':
#                     for att in object.attributes:
#                         subItem = QtGui.QTreeWidgetItem(thisItem, [att])
#                         color = QtGui.QColor(colours['var'])
#                         subItem.setForeground(0, QtGui.QBrush(color))
#                         font = thisItem.font(0)
#                         font.setBold(False)
#                         subItem.setFont(0, font)
#                         subItem.linenr = 0 # no linenr
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
