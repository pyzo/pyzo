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
        pluginName = self.__class__.__name__.lower()
        if not hasattr( iep.config.plugins, pluginName ):
            config = ssdf.new()
            config.showTypes = ['class', 'def', 'cell', 'todo']
            config.level = 2
            iep.config.plugins[pluginName] = config
        
        # Load configuration for easier access
        self._config = iep.config.plugins[pluginName]
        
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
        self._button.setText('Options ...')
        self._button.pressed.connect(self.updateStructure)
        
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
        self._sizer2.addWidget(self._button, 1)
    
    
    def onItemClick(self, item):
        
        # Get editor
        editor = iep.editors.getCurrentEditor()
        if not editor:
            return
        
        # Move to line
        pos1 = editor.getPositionFromLinenr(item.linenr+30)
        pos2 = editor.getPositionFromLinenr(item.linenr-10)
        pos3 = editor.getPositionFromLinenr(item.linenr-1)
        editor.setPositionAndAnchor(pos1)
        editor.setPositionAndAnchor(pos2)
        editor.setPositionAndAnchor(pos3)
        # todo: ensure visible?
        
        # Give focus
        iep.callLater(editor.setFocus, True)

    
    def updateStructure(self):
        """ Updates the tree. 
        """
        
        # Get editor
        editor = iep.editors.getCurrentEditor()
        if not editor:
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
                if object.children and level < showLevel:
                    SetItems(thisItem, object.children, level)
                # Set visibility
                thisItem.setExpanded(True)
        
        # Go and return
        self._tree.clear()
        SetItems(self._tree, iep.parser.rootitem.children, 0)
        return selectedItem[0]
    



# class IepSourceStructure(wx.Panel):
#     def __init__(self, parent):
#         wx.Panel.__init__(self, parent, -1)
#         
#         # set double buffering for this control,
#         # which will significantly reduce flicker.
#         self.SetDoubleBuffered(True)
#         
#         self.tree = wx.TreeCtrl(self,-1, 
#             style= wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT) # wx.TR_HAS_BUTTONS
#         self.slider = wx.Slider(self,-1,2,1,8, style=wx.SL_AUTOTICKS)        
#         self.text = wx.StaticText(self, style=wx.ALIGN_LEFT)
#         self.menubut = wx.Button(self,-1,"show...")
#         
#         # create and fill sizer1
#         self.sizer1 = wx.BoxSizer(wx.HORIZONTAL)
#         self.sizer1.Add(self.slider,2,wx.EXPAND)
#         self.sizer1.Add(self.text,1,wx.EXPAND )
#         self.sizer1.Add(self.menubut,1,wx.EXPAND )        
#         
#         # create and fill sizer2        
#         self.sizer2 = wx.BoxSizer(wx.VERTICAL)        
#         self.sizer2.Add(self.sizer1,0,wx.EXPAND)
#         self.sizer2.Add(self.tree,1,wx.EXPAND)  
#         
#         # item to highlight
#         self.selectedItem = None        
#         self.root = iep.GetMainFrame(self) 
#         self.editor = self.root.editors.GetCurrentEditor()
#         
#         # apply sizer
#         self.SetSizer(self.sizer2) # 1
#         self.SetAutoLayout(True)  # 2
#         self.Layout()             # 3
#         
#         # add events
#         self.tree.Bind( wx.EVT_LEFT_DOWN, self.OnClick )        
#         self.Bind( wx.EVT_TREE_SEL_CHANGING, self.OnSelecting ) # to disable it
#         self.slider.Bind( wx.EVT_SCROLL_CHANGED, self.UpdateMe )
#         self.slider.Bind( wx.EVT_SCROLL_THUMBTRACK, self.UpdateMe )
#         self.root.Bind( iep.EVT_SOURCE_PARSED, self.UpdateStructure)
#         self.menubut.Bind( wx.EVT_BUTTON, self.ShowMenu )
#         self.Bind(wx.EVT_MENU, self.ChangeShown)
#         
#         # test for configuration
#         pluginName = self.__class__.__name__.lower()
#         if not hasattr( iep.config.plugins, pluginName ):
#             config = strux.new()
#             config.showtypes = ['class', 'def', 'cell', 'todos']
#             config.level = 2
#             iep.config.plugins.__dict__[pluginName] = config
#         
#         # load configuration for easier access
#         self.config = iep.config.plugins.__dict__[pluginName]
#         self.slider.SetValue(self.config.level)
#         
#         # start...
#         self.lastSelectTime = 0
#         self.Show()
#         self.UpdateMe()
#         
#         
#     def UpdateStructure(self, event):
#         """ Update the structure itself 
#         Event should have a "rootitem" and "linenr" attribute
#         """        
#         self.editor = event.GetEventObject()
#         self.UpdateMe()
#         
#     
#     def EnsureVisible(self, event=None):
#         """ Ensure the current location is visible """
#         
#         try:
#             if self.selectedItem:                
#                 self.tree.EnsureVisible(self.selectedItem)                
#                 #self.tree.ScrollWindow(-999, 0, None) # werkt niet!
#         except Exception, why:
#             #print why, why.message
#             pass 
#     
#     
#     def UpdateMe(self, event=None):
#         """ Update the list.
#         The actual updating is done in UpdateMe2.
#         This method makes sure to freeze and thaw and to maintain the 
#         scroll position.        
#         """
#         if event:
#             event.Skip()
#             
#         t0 = time.clock()
#         
#         self.Freeze()
#         selectedItem = None
#         try:
#             # what is the scrollpos now?
#             scrollpos = self.tree.GetScrollPos(wx.VERTICAL)
#             # update list
#             selectedItem = self.UpdateMe2()            
#             # set position
#             self.tree.SetScrollPos(wx.VERTICAL, scrollpos, False)
#             if selectedItem:
#                 # do not select (will scroll), but highlight
#                 self.tree.SetItemBackgroundColour(selectedItem,'#AAAAAA')
#                 wx.CallAfter(self.EnsureVisible)
#             self.selectedItem = selectedItem
#         except Exception, why:
#             # this plugins sometimes hangs, I hope it happens here...
#             print why, why.message
#         finally:
#             self.Thaw()
#             self.Refresh()
#             
#         t1 = time.clock()
#         
#         # show text
#         timestr = ""
#         if self.editor:
#             timestr = "%3.0f ms" % self.editor._analysisTime
#         text = "level %i\n%s" % ( self.slider.GetValue(), timestr)
#         self.text.SetLabel(text)
#         # t1-t0 is mostly around 1/3 of the analysis time...
#         
#         # update config
#         self.config.level = self.slider.GetValue()
#         
#     
#     def UpdateMe2(self):
#         """ Fill the list with elements from self.items.
#         if linenr>0, the corresponding TreeItemId is returned.
#         """
#         
#         if not self.editor:
#             return
#         
#         # get current line number and the structure
#         ln = self.editor.GetCurrentLine()+1 # is ln as in margin
#         rootitem = self.editor.parser.rootitem
#         
#         colours = {'cell':'#007F00', 'class':'#0000FF', 'def':'#007F7F', 
#                     'var':'#444444', 'import':'#8800BB', 'todo':'#FF3333'}
#                 
#         selectedItem = [None]
#         def SetItems(itemid, fictiveObjects, level):
#             level += 1
#             for object in fictiveObjects:
#                 type = object.type
#                 if not type in self.config.showtypes:
#                     continue
#                 if type=='cell':
#                     type = '##'
#                 # create item
#                 if type == 'import':                   
#                     text = "%s (%s)" % (object.name, object.text)
#                 elif type=='todo':
#                     text = object.name                    
#                 else:
#                     text = "%s %s" % (type, object.name)               
#                 thisitem = self.tree.AppendItem(itemid, text)
#                 self.tree.SetItemTextColour(thisitem, colours[object.type])
#                 self.tree.SetItemBold(thisitem)
#                 self.tree.SetPyData(thisitem, object.linenr) # attach linenr
#                 # is this the current item?
#                 #if linenr and type!='##' and object.linenr < linenr:
#                 if ln and object.linenr <= ln and object.linenr2 > ln:
#                     selectedItem[0] = thisitem                    
#                 # any children that we should display?
#                 if object.children and level < self.slider.GetValue():
#                     SetItems(thisitem,object.children, level)
#                 self.tree.Expand(thisitem)
#                 
#         self.tree.DeleteAllItems()
#         try:
#             rootid = self.tree.AddRoot("root")
#         except:
#             rootid = self.tree.GetRoot()
#         SetItems(rootid, rootitem.children, 0)
#         
#         # return        
#         return selectedItem[0]        
#       
#         
#     def ShowMenu(self,event=None):
#         m = wx.Menu("")
#         
#         id = wx.NewId()        
#         m.Append(id,"classes", "", kind=wx.ITEM_CHECK)
#         m.Check(id,True)
#         m.Enable(id,False)
#         
#         id = wx.NewId()
#         m.Append(id,"defs", "", kind=wx.ITEM_CHECK)
#         m.Check(id,True)
#         m.Enable(id,False)
#         
#         m.Append(ID_SHOW_CELL, "cells", "", kind=wx.ITEM_CHECK)
#         if "cell" in self.config.showtypes:
#             m.Check(ID_SHOW_CELL,True)
#         
#         m.Append(ID_SHOW_IMPORT, "imports", "", kind=wx.ITEM_CHECK)        
#         if "import" in self.config.showtypes:
#             m.Check(ID_SHOW_IMPORT,True)
#             
#         m.Append(ID_SHOW_TODO, "todos", "", kind=wx.ITEM_CHECK)        
#         if "todo" in self.config.showtypes:
#             m.Check(ID_SHOW_TODO,True)
#         
#         # show
#         self.PopupMenu(m)
#         # clean up
#         m.Destroy()
#         # update
#         self.UpdateMe()
#         
#         
#     def ChangeShown(self,event):
#         """ Change the shown types, called when using the drop down menu
#         """
#         # get that list
#         showtypes = self.config.showtypes
#         
#         if event.Id == ID_SHOW_CELL:
#             name = 'cell'        
#         elif event.Id == ID_SHOW_IMPORT:
#             name = 'import'                
#         elif event.Id == ID_SHOW_TODO:
#             name = 'todo'
#         else:
#             name = ''
#             
#         if name and name in showtypes:
#             showtypes.remove(name)
#         elif name:
#             showtypes.append(name)
# 
#     
#     def OnClick(self, event):
#         """ When the user clicks. We use the mouse callback 
#         rather than the selected callback, because the latter
#         also fires when items are (programatically) expanded, 
#         which caused me a lot of trouble. This is a simple and
#         nice solution. 
#         """
#         
#         # get item under the mouse
#         pos = event.GetPosition()        
#         id = self.tree.HitTest(pos)[0]
#         
#         if not id.IsOk():
#             return
#         
#         # get the line nr stored in it...                
#         linenr = self.tree.GetPyData(id)
#         
#         # set the editors linenr!
#         if self.editor:
#             self.editor.GotoLine(linenr+30)
#             self.editor.GotoLine(linenr-10)
#             self.editor.GotoLine(linenr-1)
#             
#             #self.editor.SetFocus()
#             wx.CallAfter(self.editor.SetFocus)
#             wx.CallLater(100,self.UpdateMe) # give the select event some time
#     
#     
#     def OnSelecting(self, event):
#         """ Prevent selecting """    
#         event.Veto()
#         
# if False:
#     class ThisClassShouldBeInRoot:
#         pass
#     if True:
#         pass
#         ## and this cell should be sibling to that class
