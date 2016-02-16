# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


import time
from pyzolib.qt import QtCore, QtGui
import pyzo

tool_name = "Source structure"
tool_summary = "Shows the structure of your source code."


class PyzoSourceStructure(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Make sure there is a configuration entry for this tool
        # The pyzo tool manager makes sure that there is an entry in
        # config.tools before the tool is instantiated.
        toolId = self.__class__.__name__.lower()        
        self._config = pyzo.config.tools[toolId]
        if not hasattr(self._config, 'showTypes'):
            self._config.showTypes = ['class', 'def', 'cell', 'todo']
        if not hasattr(self._config, 'level'):
            self._config.level = 2
        
        # Create icon for slider
        self._sliderIcon = QtGui.QToolButton(self)
        self._sliderIcon.setIcon(pyzo.icons.text_align_right)
        self._sliderIcon.setIconSize(QtCore.QSize(16,16))
        self._sliderIcon.setStyleSheet("QToolButton { border: none; padding: 0px; }")   
        
        # Create slider
        self._slider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self._slider.setTickPosition(QtGui.QSlider.TicksBelow)
        self._slider.setSingleStep(1)
        self._slider.setPageStep(1)
        self._slider.setRange(1,9)
        self._slider.setValue(self._config.level)
        self._slider.valueChanged.connect(self.updateStructure)
        
        # Create options button
        #self._options = QtGui.QPushButton(self)
        #self._options.setText('Options'))        
        #self._options.setToolTip("What elements to show.")
        self._options = QtGui.QToolButton(self)
        self._options.setIcon(pyzo.icons.filter)
        self._options.setIconSize(QtCore.QSize(16,16))
        self._options.setPopupMode(self._options.InstantPopup)
        self._options.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        
        # Create options menu
        self._options._menu = QtGui.QMenu()
        self._options.setMenu(self._options._menu)
        
        # Create tree widget        
        self._tree = QtGui.QTreeWidget(self)
        self._tree.setHeaderHidden(True)
        self._tree.itemCollapsed.connect(self.updateStructure) # keep expanded
        self._tree.itemClicked.connect(self.onItemClick)
        
        # Create two sizers
        self._sizer1 = QtGui.QVBoxLayout(self)
        self._sizer2 = QtGui.QHBoxLayout()
        self._sizer1.setSpacing(2)
        self._sizer1.setContentsMargins(4,4,4,4)
        
        # Set layout
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._tree, 1)
        self._sizer2.addWidget(self._sliderIcon, 0)
        self._sizer2.addWidget(self._slider, 4)
        self._sizer2.addStretch(1)
        self._sizer2.addWidget(self._options, 2)
        #
        self.setLayout(self._sizer1)
        
        # Init current-file name
        self._currentEditorId = 0
        
        # Bind to events
        pyzo.editors.currentChanged.connect(self.onEditorsCurrentChanged)
        pyzo.editors.parserDone.connect(self.updateStructure)
        
        self._options.pressed.connect(self.onOptionsPress)
        self._options._menu.triggered.connect(self.onOptionMenuTiggered)
        
        # Start
        # When the tool is loaded, the editorStack is already done loading
        # all previous files and selected the appropriate file.
        self.onOptionsPress() # Create menu now
        self.onEditorsCurrentChanged()
    
    
    def onOptionsPress(self):
        """ Create the menu for the button, Do each time to make sure
        the checks are right. """
        
        # Get menu
        menu = self._options._menu
        menu.clear()
        
        for type in ['class', 'def', 'cell', 'todo', 'import', 'attribute']:
            checked = type in self._config.showTypes
            action = menu.addAction('Show %s'%type)
            action.setCheckable(True)
            action.setChecked(checked)
    
    
    def onOptionMenuTiggered(self, action):
        """  The user decides what to show in the structure. """
        
        # What to show
        type = action.text().split(' ',1)[1]
        
        # Swap
        if type in self._config.showTypes:
            while type in self._config.showTypes:
                self._config.showTypes.remove(type)
        else:
            self._config.showTypes.append(type)
        
        # Update
        self.updateStructure()
    
    
    def onEditorsCurrentChanged(self):
        """ Notify that the file is being parsed and make
        sure that not the structure of a previously selected
        file is shown. """
        
        # Get editor and clear list
        editor = pyzo.editors.getCurrentEditor()        
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
        editor = pyzo.editors.getCurrentEditor()
        if not editor:
            return
        
        # If item is attribute, get parent
        if not item.linenr:
            item = item.parent()
        
        # Move to line
        editor.gotoLine(item.linenr)
        
        # Give focus
        pyzo.callLater(editor.setFocus)

    
    def updateStructure(self):
        """ Updates the tree. 
        """
        
        # Get editor
        editor = pyzo.editors.getCurrentEditor()
        if not editor:
            return
        
        # Something to show
        result = pyzo.parser._getResult()
        if result is None:
            return
        
        # Do the ids match?
        id0, id1, id2 = self._currentEditorId, id(editor), result.editorId 
        if id0 != id1 or id0 != id2:
            return
        
        # Get current line number and the structure
        ln = editor.textCursor().blockNumber()
        ln += 1  # is ln as in line number area
        
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
                if type in ('cell', '##', '#%%', '# %%'):
                    type = 'cell:'
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
