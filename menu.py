
import os, sys

from PyQt4 import QtCore, QtGui
qt = QtGui

import iep

class MI:
    """ Menu Item
    A virtual menu item to help producing a menu. 
    It can represent:
    - an action - values is None
    - a boolean - values is True or False, indicating the currents state
    - a choice - values is a list of Strings, ending with the current
    """
    def __init__(self, func, values, text, tip ):
        self.func = func
        self.text = text
        self.tip = tip
        self.values = values


    def createRealMenuItem(self, menu):
        """ From this virtual menu item, create the actual menu
        stuff to show to the user. """
        
        # depending on type ....
        if self.values is None:
            action = qt.QAction(menu)
            action.func = self.func
        elif self.value is True or self.value is False:
            action = qt.QAction(menu)
            action.func = self.func
            action.setCheckable(True)
            action.setChecked(self.value)
        elif isinstance(self.values, list):
            action = qt.QMenu(menu)
            for value in self.values[:-1]:
                sub = qt.Qaction(menu)
                sub.setText(value)
                sub.setStatusTip(self.tip)
                sub.func = self.func
                action.addAction(sub)
        
        action.setText(self.text)
        action.setStatusTip(self.tip)
        return action


# class Menuhelper:
#     """ Menu helper class to transparantly and without duplicating code,
#     automatically produces a nice menu.
#     
#     The methods in this class represent a menu "option", which can be:
#     - an action (like file->new)
#     - a True/False choice (like setting->wrap_text)
#     - a choice of several (string) options (like document->style)
#     (- checkbox like style like for the plugins is realized true a list of
#       true/false items)
#     
#     When such a method is called without argument, it should return a
#     VirtualItem instance, which is then used to create the menu. When
#     a menu-item is pressed, that same method is called, with the choice
#     as a parameter (or simply "True" for actions). If values is a list
#     of VirtualItem instances, the supplied parameter is the text of the
#     clicked instance (which can only be an action or a true/false).
#     """ 
#     
#     def create(self):
#         
#         L = file()
#         menu_file = QMenu()
#         menu_file.triggered.connect(self.onTrigger)
#         for callback in L:
#             
#             tmp = callback(None)
#             shortcut = ''# test for key shortut
#             menu_file.addAction(tmp[0], tmp[1], callback)
#         
#         
#     def onTrigger(self, action):
#         """ Called when an item is clicked. """
#         if action.callback:
#             action.callback(*action.args)
#     
#     def file(self, event=None):
#         if event is None:
#             # prepare list
#             L = []
#             L.append(self.file_new)
#             L.append(self.file_open)
#             L.append(self.file_close)
#             return L
#     
#     def file_new(self, event=None):
#         if event is None:
#             return "New File", "Create a new file"
#         
#         iep.editors.newFile()
#     
#     
#     def file_new(self, event=None):
#         if event is None:
#             return "Open File", "Open an existing file"
#         
#         iep.editors.openFile()
#     
#     
#     def plugins(self):
#         return ??
#         
#     
#     def settings(self):
#         pass # make list like file()
#     
#     def set_wrapText(self, action=None):
#         if isinstance(action, Qaction):
#             action.setText("Wrap text")
#             action.setStatusTip("Wrap text to next line if it does not fit on screen")
#             action.setCheckable(True)
#             action.setChecked(iep.config.wrapText)
#             return action
#         
#         # switch and apply
#         iep.config.wrapText = not iep.config.wrapText
#         for editor in iep.editors:
#             editor.setWrapText(iep.config.wrapText) # or something similar
#         
#     
#     def set_indentWidth(self, action=None):
#         if action is None
#             action = QMenu()
#             action.setText("Default indent width")
#             action.setStatusTip("The indentation width to apply to new files")
#             action.addAction(..., 2)
#             action.addAction(..., 3)
#             action.addAction(..., 4)
#             # added actions are checkable and one is checked
#             return action
#         
#         # apply
#         iep.config.indentWidth = action.value
#     
#     ##
#     
#     def set_indentWidth(self, value=None):
#         if value is None
#             item = VirtualItem()
#             item.text = "Default indent width"
#             item.tip = "The indentation width to apply to new files"
#             item.values = ["2","3","4"]
#             item.current = iep.config.indentWidth
#             return item
#         
#         # apply
#         iep.config.indentWidth = int(value)
#     
#     def set_wrapText(self, value):
#         ...
#             item.values = [True, False]
#             item.current = iep.config.wrapText
#     
#     def file_new(self, value=None):
#         if value is None:
#             item = VirtualItem()
#             item.text = "New File"
#             item.tip = "Create a new file"
#             item.value = True # can be given automatically when value not given
#             return item
#         
#         # apply
#         iep.editors.newFile()
#         
#     def plugins(self, value=None):
#         
#         if value is None:
#             item = VirtualItem()
#             item.text = "Plugins"
#             item.tip = "Plugins are there to help you"
#             item.values = []
#             for plugin in plugins:
#                 tmp = VirtualItem()
#                 tmp.text = plugin.name
#                 tmp.tip = plugin.description
#                 tmp.values =[True, False]
#                 tmp.current = plugin in activePlugins
#                 item.values.append(tmp)
#             return item
#     
#     ##

class BaseMenu(qt.QMenu):
    
    def showEvent(self, event):
        
        # clear
        self.clear()
        
        # insert items to show
        self.fill()
        
        # call base show callback
        qt.QMenu.showEvent(self, event)
    
    def addItem(self, item):
        """ Add a MI instance. """
        # produce real menu items
        if isinstance(item, MI):
            item = item.createRealMenuItem(self)
        else:
            item = None
        # append
        if isinstance(item, qt.QMenu):
            self.addMenu(item)
        elif isinstance(item, qt.QAction):
            self.addAction(item)
        else:
            self.addSeparator()
    
    def fill(self):
        raise NotImplementedError()
    

class FileMenu(BaseMenu):
    def fill(self):
        addItem = self.addItem
        
        des = self.fun_new.__doc__
        addItem( MI(self.fun_new, None, 'New File', des) )
        
        des = self.fun_open.__doc__
        addItem( MI(self.fun_open, None, 'Open File', des) )
        
        addItem(None)
        
        des = self.fun_restart.__doc__
        addItem( MI(self.fun_restart, None, 'Restart IEP', des) )
        
        des = self.fun_close.__doc__
        addItem( MI(self.fun_close, None, 'Exit IEP', des) )
    
    
    def fun_new(self, value):
        """ Create a new (or temporary) file. """
        iep.editors.newFile()
        print('yeah')
    
    def fun_open(self, value):
        """ Open an existing file. """
        iep.editors.openFile()
    
    def fun_close(self, value):
        """ Close the application. """
        iep.main.close()
    
    def fun_restart(self, value):
        """ Restart the application. """
        # close first
        self.fun_close(None)
        
        # put a space in front of all args
        args = []
        for i in sys.argv:
            args.append(" "+i)
        
        # replace the process!                
        os.execv(sys.executable, args)


class EditMenu(BaseMenu):
    def fill(self):
        addItem = self.addItem
        
        des = self.fun_cut.__doc__
        addItem( MI(self.fun_cut, None, 'Cut', des) )
        
        des = self.fun_copy.__doc__
        addItem( MI(self.fun_copy, None, 'Copy', des) )
        
        des = self.fun_paste.__doc__
        addItem( MI(self.fun_paste, None, 'Paste', des) )
        
    
    def fun_cut(self, value):
        """ Cut the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'cut'):
            widget.cut()
        
    def fun_copy(self, value):
        """ Copy the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'copy'):
            widget.copy()
    
    def fun_paste(self, value):
        """ Paste the text/object. """
        widget = QtGui.qApp.focusWidget()
        if hasattr(widget,'paste'):
            widget.paste()
    
    def fun_selectAll(self, value):
        """ Open an existing file. """
        iep.editors.openFile()
    
    def fun_undo(self, value):
        """ Open an existing file. """
        iep.editors.openFile()
    
    def fun_redo(self, value):
        """ Open an existing file. """
        iep.editors.openFile()


class MenuHelper:
    
    def __init__(self, menubar):
        
        menus = ['File', 'Session', 'wooter']
        
#         menus.append( menubar.addMenu("File") )
#         menus.append( menubar.addMenu("Session") )
#         menus.append( menubar.addMenu("Plugins") )
#         menus.append( menubar.addMenu("Document") )
#         menus.append( menubar.addMenu("Settings") )
#         menus.append( menubar.addMenu("Help") )
        
        
#         for menuName in menus:
#             menu = BaseMenu(menuName, menubar)
#             menu.contentFunc = self.file
#             menubar.addMenu(menu)
        menus = [('File', FileMenu), ('Edit', EditMenu)]
        
        for menuName, menuClass in menus:
            menu = menuClass(menuName, menubar)
            menubar.addMenu(menu)
            
        
#         menubar.addMenu( FileMenu("File", menubar) )
#         menubar.addMenu( EditMenu("Edit", menubar) )
        
        menubar.triggered.connect(self.onTrigger)        
#         menubar.hovered.connect(self.onHover)
    
    def onTrigger(self, action):
        print('trigger:', action.text())
        action.func(action.text())
    
    def onHover(self, action):
        print('hover:', action.text())
    
    
    def file(self):
        
        items = []
        
        des = self.file_new.__doc__
        items.append( MI(self.file_new, None, 'New File', des) )
        
        des = self.file_open.__doc__
        items.append( MI(self.file_open, None, 'Open File', des) )
        
        return items
    
    
    def plugins(self):
        items = []
        
        des = ""
        items.append( MI(self.pluginsCb, None, 'Refresh plugins', doc) )
        
        for plugin in plugins:
            active = plugin in activePlugins
            des = plugin.description
            items.append( MI(self.pluginsCb, active, plugin.name, des) )
        
        return items
    
    
    def pluginsCb(self, pluginName):
        pass
    
    