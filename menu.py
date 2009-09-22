
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
    
    - func.__doc__ is used as statustip
    - if isChoice, func(None) should give the 'values' property.
    """
    def __init__(self, text, func, isChoice=False):        
        self.text = text
        self.func = func
        self.tip = func.__doc__
        if isChoice:
            self.values = func(None)
        else:
            self.values = None


    def createRealMenuItem(self, menu):
        """ From this virtual menu item, create the actual menu
        stuff to show to the user. """
        
        # depending on type ....
        if self.values is None:
            action = qt.QAction(menu)
            action.func = self.func
            action.value = True
        elif self.values in [True, False, 0, 1]:
            action = qt.QAction(menu)
            action.func = self.func
            action.value = not self.values
            action.setCheckable(True)
            action.setChecked(self.values)            
        elif isinstance(self.values, list):
            action = qt.QMenu(menu)
            for value in self.values[:-1]:
                sub = qt.QAction(menu)
                sub.setText(str(value))
                sub.setStatusTip(self.tip)
                sub.func = self.func
                sub.value = value
                sub.setCheckable(True)
                if value == self.values[-1]:
                    sub.setChecked(True)
                action.addAction(sub)
        else:
            print(self.values)
            raise Exception('Dont know what to do')
        
        if hasattr(action,'setText'):
            action.setText(self.text)
        else:
            action.setTitle(self.text)
        action.setStatusTip(self.tip)
        return action


class BaseMenu(qt.QMenu):
    """ Base class for the menus File, Edit, Settings, etc. """
    
    def showEvent(self, event):
        """ Called right before menu is shown. The menu should update
        its contents before actually showing. """
        
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
        """ Update the contents. """
        raise NotImplementedError()
    

class FileMenu(BaseMenu):
    def fill(self):
        addItem = self.addItem
        
        addItem( MI('New file', self.fun_new) )
        addItem( MI('Open file', self.fun_open) )
        addItem( MI('Save file', self.fun_save) )
        addItem( MI('Save file as ...', self.fun_saveAs) )
        addItem( MI('Close file', self.fun_closeFile) )
        addItem(None)
        addItem( MI('Restart IEP', self.fun_restart) )
        addItem( MI('Close IEP', self.fun_close) )
    
    
    def fun_new(self, value):
        """ Create a new (or temporary) file. """
        iep.editors.newFile()
    
    def fun_open(self, value):
        """ Open an existing file. """
        iep.editors.openFile()
    
    def fun_save(self, value):
        """ Save the current file. """
        iep.editors.saveFile()
    
    def fun_saveAs(self, value):
        """ Save the current file under another name. """
        iep.editors.saveFileAs()
    
    def fun_closeFile(self, value):
        """ Close the current file. """
        iep.editors.closeFile()
    
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
        
        addItem( MI('Cut', self.fun_cut) )
        addItem( MI('Copy', self.fun_copy) )
        addItem( MI('Paste', self.fun_paste) )
        
    
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
        
        addItem( MI('Show whitespace', self.fun_whitespace, True) )
        addItem( MI('Wrap text', self.fun_wrap, True) )
        addItem( MI('Edge column', self.fun_edgecolumn, True) )
        addItem( None )
        addItem( MI('Change key mappings', self.fun_keymap) )
    
    def fun_whitespace(self, value):
        """ Show tabs and spaces in the editor. """
        if value is None:
            return bool(iep.config.showWhiteSpace)
        iep.config.showWhiteSpace = value
        for editor in iep.editors:
            editor.setViewWhiteSpace(value)
    
    def fun_wrap(self, value):
        """ Wrap long lines in the editor. """
        if value is None:
            return bool(iep.config.wrapText)
        iep.config.wrapText = value
        for editor in iep.editors:
            editor.setWrapMode(int(value))
    
    def fun_edgecolumn(self, value):
        """ The position of the edge column indicator. """
        if value is None:
            return [60, 65, 70, 75, 76, 77, 78,79,80, iep.config.edgeColumn]
        iep.config.edgeColumn = value
        for editor in iep.editors:
            editor.setEdgeColumn(value)
    
    def fun_keymap(self, value):
        """ Change the keymappings for the menu. """
        dialog = KeymappingDialog()
        dialog.exec_()
        
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
    

class KeyMapModel(QtCore.QAbstractItemModel):
    def __init__(self, *args):
        QtCore.QAbstractListModel.__init__(self,*args)
        self._list = ['hai', 'nou', 'omg']
    
    def data(self, index, role):
        if index.isValid() and role==0: # displayrole 
            if index.column()==0:
                return self._list[ index.row() ]
            else:
                return '<edit>'
    
    def rowCount(self, parent):
        return len(self._list)
    
    def columnCount(self, parent):
        return 2
    
    def headerData(self, section, orientation, role):
        if role == 0:# and orientation==1:
            return 'lala' + str(section)
    
    def parent(self, index):
        return QtCore.QModelIndex()
    
    def hasChildren(self, index):
        # no items have parents (except the root item)
        if index.row()<0:
            return True
        return False 
    
    def index(self, row, column, parent):
        return self.createIndex(row, column, None)
    
    def flags(self, index):
        base = QtCore.QAbstractItemModel
        if index.isValid() and index.column()==1:
            return base.flags(self, index) | QtCore.Qt.ItemIsEditable
        else:
            return base.flags(self, index)
    
    def setData(self, index, value, role):
        if index.isValid() and role==QtCore.Qt.EditRole:
            self._list[index.row()] = value
            return True
        else:
            return False
    
class KeymappingDialog(QtGui.QDialog):
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP keyboard mappings')
        
        # set size
        size = 400,400
        self.resize(*size)
        self.setMaximumSize(*size)
        self.setMinimumSize(*size)
        
        self.model = KeyMapModel()
        self.tab = QtGui.QTabWidget(self)
        self.tab.resize(*size)
        for name in ['File', 'Edit', 'Settings']:
            w = QtGui.QTreeView(self.tab)
            w.setModel(self.model)
            self.tab.addTab(w, name)
        
        