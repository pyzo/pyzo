
import os, sys
import unicodedata

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
                sub = qt.QAction(action)
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
    
    def __init__(self, menuname, parent):
        QtGui.QMenu.__init__(self, menuname, parent)
        
        # keep a list at the menubar. We could use weakrefs, but the
        # menu's in the menubar are never destroyed, so don't bother
        if isinstance(parent, QtGui.QMenuBar):
            if not hasattr(parent, '_menus'):
                parent._menus = []
            parent._menus.append(self)
    
    def showEvent(self, event):
        """ Called right before menu is shown. The menu should update
        its contents before actually showing. """
        
        # insert items to show
        self.fill()
        
        # call base show callback
        qt.QMenu.showEvent(self, event)
    
    def addItem(self, item):
        """ Add a MI instance. """
        
        # produce real menu items
        if isinstance(item, MI):
            realitem = item.createRealMenuItem(self)
        else:
            realitem = None
        # append
        if isinstance(realitem, qt.QMenu):
            self.addMenu(realitem)
        elif isinstance(realitem, qt.QAction):
            self.addAction(realitem)
        else:
            self.addSeparator()
    
    def fill(self):
        """ Update the contents. """
        # clear first
        self.clear()
    

class FileMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
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
        BaseMenu.fill(self)
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
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('QT style', self.fun_qtstyle, True) )
        
        addItem( MI('Show whitespace', self.fun_whitespace, True) )
        addItem( MI('Wrap text', self.fun_wrap, True) )
        addItem( MI('Edge column', self.fun_edgecolumn, True) )
        addItem( None )
        addItem( MI('Change key mappings', self.fun_keymap) )
    
    def fun_qtstyle(self, value):
        """ Chose the QT style to use. """
        if value is None:
            tmp = [i for i in QtGui.QStyleFactory.keys()]
            tmp.append(iep.config.qtstyle)
            return tmp
        iep.config.qtstyle = value
        QtGui.qApp.setStyle(value)
    
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
            return [60, 65, 70, 75, 76, 77, 78,79,80,-1, iep.config.edgeColumn]
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
    

def getFullName(action):
    """ Get the full name of the action. 
    This is the key in the iep.config.shortcuts dict
    """
    item = action
    text = action.text()
    if not text:
        text = ''
    while isinstance(item.parent(), QtGui.QMenu):
        item = item.parent()
        try:
            text = item.title() + '__' + text
        except Exception:
            print(text, item.title())
    text = text.replace(' ', '_').replace('.', '').lower()
    return text

def getShortcut( fullName):
    """ Given the full name or an action, get the shortcut
    from the iep.config.shortcuts dict. The shortcut can consist
    of two parts, separated by a comma. """
    if isinstance(fullName, QtGui.QAction):
        fullName = getFullName(fullName)
    tmp = ''
    if fullName in iep.config.shortcuts:
        tmp = iep.config.shortcuts[fullName]
    return tmp
    
class KeyMapModel(QtCore.QAbstractItemModel):
    def __init__(self, *args):
        QtCore.QAbstractListModel.__init__(self,*args)
        self._root = None
    
    def setRootMenu(self, menu):
        """ Call this after starting. """
        menu.fill()
        self._root = menu
    
    
    def data(self, index, role):
        if not index.isValid() or role!=0:
            return None
        
        # get menu or action item
        item = index.internalPointer()
        
        # get text and shortcuts
        key1, key2 = '', ''
        if isinstance(item, QtGui.QMenu):
            value = item.title()
        else:
            value = item.text()
            if not value:
                value = '-'*10
            elif index.column()>0:
                shortcut = getShortcut(item)
                if not shortcut:
                    key1, key2 = '-','-'
                if ',' in shortcut:
                    key1, key2 = tuple(shortcut.split(','))
                else:
                    key1, key2 = shortcut, '-'
        # return
        return {0:value,1:key1,2:key2}[index.column()]
    
    def rowCount(self, parent):
        if parent.isValid():
            menu = parent.internalPointer()
            return len(menu.actions())
        else:
            return len(self._root.actions())
    
    def columnCount(self, parent):
        return 3
    
    def headerData(self, section, orientation, role):
        if role == 0:# and orientation==1:
            return 'lala' + str(section)
    
    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        item = index.internalPointer()
        pitem = item.parent()
        if pitem is self._root:
            return QtCore.QModelIndex()
        else:
            L = pitem.parent().actions()
            row = 0
            if pitem in L:
                row = L.index(pitem)
            return self.createIndex(row, 0, pitem)
    
    def hasChildren(self, index):
        # no items have parents (except the root item)
        
        if index.row()<0:
            return True
        else:
            return isinstance(index.internalPointer(), QtGui.QMenu)
    
    def index(self, row, column, parent):
#         if not self.hasIndex(row, column, parent):
#             return QtCore.QModelIndex()
        # establish parent
        if not parent.isValid():
            parentMenu = self._root
        else:
            parentMenu = parent.internalPointer()
        # produce index and make menu if the action represents a menu
        childAction = parentMenu.actions()[row]
        if childAction.menu():
            childAction = childAction.menu()        
        return self.createIndex(row, column, childAction)
        # This is the trick. The internal pointer is the way to establish
        # correspondence between ModelIndex and underlying data.
    
#     def flags(self, index):
#         base = QtCore.QAbstractItemModel
#         item = index.internalPointer()
#         if index.isValid() and index.column()==1 and not item.children:
#             return base.flags(self, index) | QtCore.Qt.ItemIsEditable
#         else:
#             return base.flags(self, index)
#     
#     def setData(self, index, value, role):
#         if index.isValid() and role==QtCore.Qt.EditRole:
#             item = index.internalPointer()
#             item.value += value
#         return True


k = QtCore.Qt
keymap = {k.Key_Enter:'Enter', k.Key_Return:'Return', k.Key_Escape:'Escape', 
    k.Key_Tab:'Tab', k.Key_Backspace:'Backspace', k.Key_Pause:'Pause', 
    k.Key_F1:'F1', k.Key_F2:'F2', k.Key_F3:'F3', k.Key_F4:'F4', k.Key_F5:'F5',
    k.Key_F6:'F6', k.Key_F7:'F7', k.Key_F8:'F8', k.Key_F9:'F9', 
    k.Key_F10:'F10', k.Key_F11:'F11', k.Key_F12:'F12', k.Key_Space:'Space',
    k.Key_Delete:'Delete', k.Key_Insert:'Insert', k.Key_Home:'Home', 
    k.Key_End:'End', k.Key_PageUp:'PageUp', k.Key_PageDown:'PageDown',
    k.Key_Left:'Left', k.Key_Up:'Up', k.Key_Right:'Right', k.Key_Down:'Down' }


class KeyMapLineEdit(QtGui.QLineEdit):
    
    textUpdate = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        self.setText('<enter key combination here>')
    
    def focusInEvent(self, event):
        self.clear()
        QtGui.QLineEdit.focusInEvent(self, event)
    
    def keyPressEvent(self, event):
        #text = event.text()
        key = event.key()
        try:
            text = chr(event.nativeVirtualKey()).upper()
        except Exception:
            pass        
        if key in keymap:
            text = keymap[key]
        if text:
            if QtGui.qApp.keyboardModifiers() & k.AltModifier:
                text  = 'Alt+' + text
            if QtGui.qApp.keyboardModifiers() & k.ShiftModifier:
                text  = 'Shift+' + text
            if QtGui.qApp.keyboardModifiers() & k.ControlModifier:
                text  = 'Control+' + text
            self.setText(text)
        
        # notify listeners
        self.textUpdate.emit()


class KeyMapEditDialog(QtGui.QDialog):
    """ The prompt that is shown when double clicking 
    a keymap in the tree. """
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP - Edit shortcut mapping')
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 300,120
        offset = 35
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*size2)
        
        self._label = QtGui.QLabel("", self)
        self._label.resize(size[0]-20, 60)
        self._label.move(10,2)
        
        self._line = KeyMapLineEdit('', self)
        self._line.resize(size[0]-80, 20)
        self._line.move(10,70)
        
        self._clear = QtGui.QPushButton("Clear", self)
        self._clear.resize(50, 20)
        self._clear.move(size[0]-60,70)
        
        self._apply = QtGui.QPushButton("Apply", self)
        self._apply.resize(50, 20)
        self._apply.move(size[0]-110,100)
        
        self._cancel = QtGui.QPushButton("Cancel", self)
        self._cancel.resize(50, 20)
        self._cancel.move(size[0]-60,100)
        
        # callbacks
        self._clear.clicked.connect(self.onClear)
        self._line.textUpdate.connect(self.onEdit)
        
    def setFullName(self, fullname):
        tmp = fullname.replace('__',' -> ').replace('_', ' ')
        self._intro = "Set the shortcut for:\n" + tmp
        self._label.setText(self._intro)
        
    def onClear(self):
        self._line.clear()
        self._line.setFocus()
    
    def onEdit(self):
        # test if already in use
        shortcut = self._line.text()
        for key in iep.config.shortcuts:
            if iep.config.shortcuts[key].count(fullname):
                tmp = fullname.replace('__',' -> ').replace('_', ' ')
                tmp = "WARNING: shortcut already in use for:/n" + tmp
                self._label.setText(self._intro + '\n\n' + tmp)
                break
        else:
            self._label.setText(self._intro)
        

class KeymappingDialog(QtGui.QDialog):
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle('IEP - Shortcut mappings')
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 400,400
        offset = 35
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*size2)
        
        self._selectedIndex = None
        
        self.tab = QtGui.QTabWidget(self)
        self.tab.resize(*size)
        self.tab.move(0,offset)
        
        # fill tab
        self._models = []
        self._trees = []
        for menu in iep.main.menuBar()._menus:
            w = QtGui.QTreeView(self.tab)
            tmp = KeyMapModel()
            tmp.setRootMenu(menu)
            self._models.append(tmp)
            self._trees.append(w)
            w.setModel(tmp)
            self.tab.addTab(w, menu.title())
            w.clicked.connect(self.onClickSelect)
            w.doubleClicked.connect(self.onDoubleClick)
        
        self._editBox = KeyMapLineEdit(self)
        self._but1 = QtGui.QPushButton('Apply key combination', self)
        self._but2 = QtGui.QPushButton('Clear', self)
        self._editBox.move(10,5)
        self._editBox.resize(180,25)
        self._but1.move(200,5)
        self._but1.resize(140,25)
        self._but2.move(350,5)
        self._but2.resize(40,25)
        
        self.tab.currentChanged.connect(self.onTabSelect)
        #self._but1.clicked.connect(self.onClickApply)
    
    def onTabSelect(self):
        self._selectedIndex = None
        self._editBox.setText('')
        
    def onClickSelect(self, index):
        pass
        #item = index.internalPointer()
        #self._editBox.setText( item.getShortcut() )
        #self._selectedIndex = index
    
    def onDoubleClick(self, index):
        dlg = KeyMapEditDialog(self)
        dlg.setFullName( getFullName(index.internalPointer()) )
        dlg.exec_()
        
#     def onClickApply(self):
#         if self._selectedIndex is None:
#             return
#         index = self._selectedIndex
#         item = index.internalPointer()
#         name = item.getFullName()
#         key = self._editBox.text()
#         if key.startswith("<"):
#             key = ''
#         if key:
#             iep.config.shortcuts[name] = key
#             print(name, key)
#         index.model().dataChanged.emit(index,index)
#         #for tree in self._trees:
#         #    tree.update()
#             
        