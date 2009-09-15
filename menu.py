
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
    
    if tip is None, it will use func.__doc__
    """
    def __init__(self, text, func, values=None, tip=None ):
        if tip is None:
            tip = func.__doc__
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
            action.value = None
        elif self.values in [False, True, 0, 1]:
            action = qt.QAction(menu)
            action.func = self.func
            action.value = not self.values
            action.setCheckable(True)
            action.setChecked(self.values)            
        elif isinstance(self.values, list):
            action = qt.QMenu(menu)
            for value in self.values[:-1]:
                sub = qt.Qaction(menu)
                sub.setText(value)
                sub.setStatusTip(self.tip)
                sub.func = self.func
                sub.value = value
                action.addAction(sub)
        else:
            print(self.values)
            raise Exception('Dont know what to do')
        action.setText(self.text)
        action.setStatusTip(self.tip)
        return action


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
        
        addItem( MI('New File', self.fun_new, None) )
        addItem( MI('Open File', self.fun_open, None) )        
        addItem(None)
        addItem( MI('Restart IEP', self.fun_restart, None) )
        addItem( MI('Close IEP', self.fun_close, None) )
    
    
    def fun_new(self, value):
        """ Create a new (or temporary) file. """
        iep.editors.newFile()
    
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
        
        addItem( MI('Cut', self.fun_cut, None) )
        addItem( MI('Copy', self.fun_copy, None) )
        addItem( MI('Paste', self.fun_paste, None) )
        
    
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


class SettingsMenu(BaseMenu):
    def fill(self):
        addItem = self.addItem
        
        value = iep.config.showWhiteSpace
        addItem( MI('Show whitespace', self.fun_whitespace, value) )
        value = iep.config.wrapText
        addItem( MI('Wrap text', self.fun_wrap, value) )
    
    def fun_whitespace(self, value):
        """ Show tabs and spaces in the editor. """
        iep.config.showWhiteSpace = value
        for editor in iep.editors:
            editor.setViewWhiteSpace(value)
    
    def fun_wrap(self, value):
        """ Wrap long lines in the editor. """
        iep.config.wrapText = value
        for editor in iep.editors:
            editor.setWrapMode(int(value))
    
class MenuHelper:
    
    def __init__(self, menubar):
        
       
        menus = [   ('File', FileMenu), 
                    ('Edit', EditMenu), 
                    ('Settings', SettingsMenu)]
        
        for menuName, menuClass in menus:
            menu = menuClass(menuName, menubar)
            menubar.addMenu(menu)
        
        menubar.triggered.connect(self.onTrigger)        
        # menubar.hovered.connect(self.onHover)
    
    def onTrigger(self, action):
        print('trigger:', action.text())
        action.func(action.value)
    
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
    
    