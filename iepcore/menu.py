# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module menu

Implements a menu that can be edited very easily. Every menu item is 
represented by a class. Also implements a dialog to change keyboard 
shortcuts.

"""

import os, sys, re, time
import unicodedata

from PyQt4 import QtCore, QtGui

import iep
from iepcore.compactTabWidget import CompactTabWidget
from iepcore.iepLogging import print
import webbrowser
from iep import translate



def buildMenus(menuBar):
    """
    Build all the menus
    """
    menus = [FileMenu(menuBar, translate("menu", "File")),
             EditMenu(menuBar, translate("menu", "Edit")),
             ViewMenu(menuBar, translate("menu", "View")),
             SettingsMenu(menuBar, translate("menu", "Settings")),
             ShellMenu(menuBar, translate("menu", "Shell")),
             RunMenu(menuBar, translate("menu", "Run")),
             ToolsMenu(menuBar, translate("menu", "Tools")),
             HelpMenu(menuBar, translate("menu", "Help")),
            ]
    for menu in menus:
        menuBar.addMenu(menu)
    menuBar._menus = menus
    
    # Enable tooltips
    def onHover(action):
        # This ugly bit of code makes sure that the tooltip is refreshed
        # (thus raised above the submenu). This happens only once and after
        # ths submenu has become visible.
        if action.menu():
            if not hasattr(QtGui.QToolTip, '_lastAction'):
                QtGui.QToolTip._lastAction = None
                QtGui.QToolTip._haveRaisedTooltip = False
            if action is QtGui.QToolTip._lastAction:
                if ((not QtGui.QToolTip._haveRaisedTooltip) and 
                            action.menu().isVisible()):
                    QtGui.QToolTip.hideText()
                    QtGui.QToolTip._haveRaisedTooltip = True
            else:
                QtGui.QToolTip._lastAction = action
                QtGui.QToolTip._haveRaisedTooltip = False
        # Set tooltip
        tt = action.statusTip()
        if hasattr(action, '_shortcutsText'):
            tt = tt + ' ({})'.format(action._shortcutsText) # Add shortcuts text in it
        QtGui.QToolTip.showText(QtGui.QCursor.pos(), tt)
    menuBar.hovered.connect(onHover)


# todo: syntax styles now uses a new system. Make dialog for it!
# todo: put many settings in an advanced settings dialog:
# - autocomp use keywords
# - autocomp case sensitive
# - autocomp select chars
# - Default parser / indentation (width and tabsOrSpaces) / line endings
# - Shell wrapping to 80 columns?
# - number of lines in shell
# - more stuff from iep.config.advanced?


def getShortcut(fullName):
    """ Given the full name or an action, get the shortcut
    from the iep.config.shortcuts dict. A tuple is returned
    representing the two shortcuts. """
    if isinstance(fullName, QtGui.QAction):
        fullName = fullName.menuPath # the menuPath property is set in Menu._addAction
    shortcut = '', ''
    if fullName in iep.config.shortcuts:
        shortcut = iep.config.shortcuts[fullName]
        if shortcut.count(','):
            shortcut = tuple(shortcut.split(','))
        else:
            shortcut = shortcut, ''
    return shortcut


def translateShortcutToOSNames(shortcut):
    """
    Translate Qt names to OS names (e.g. Ctrl -> cmd symbol for Mac,
    Meta -> Windows for windows
    """
    
    if sys.platform == 'darwin':
        replace = (('Ctrl+','\u2318'),('Shift+','\u21E7'),
                    ('Alt+','\u2325'),('Meta+','^'))
    else:
        replace = ()
    
    for old, new in replace:
        shortcut = shortcut.replace(old, new)
        
    return shortcut
    


class KeyMapper(QtCore.QObject):
    """
    This class is accessable via iep.keyMapper
    iep.keyMapper.keyMappingChanged is emitted when keybindings are changed
    """
    
    keyMappingChanged = QtCore.pyqtSignal()
    
    def setShortcut(self, action):
        """
        When an action is created or when keymappings are changed, this method
        is called to set the shortcut of an action based on its menuPath
        (which is the key in iep.config.shortcuts, e.g. shell__clear_screen)
        """
        if action.menuPath in iep.config.shortcuts:
            # Set shortcut so Qt can do its magic
            shortcuts = iep.config.shortcuts[action.menuPath]
            action.setShortcuts(shortcuts.split(','))
            # Also store shortcut text (used in display of tooltip
            shortcuts = shortcuts.replace(',',', ').replace('  ', ' ')
            action._shortcutsText = shortcuts.rstrip(', ')


def unwrapText(text):
    """ Unwrap text to display in message boxes. This just removes all
    newlines. If you want to insert newlines, use \\r."""
    
    # Removes newlines
    text = text.replace('\n', '')
    
    # Remove double/triple/etc spaces
    text = text.lstrip()
    for i in range(10):
        text = text.replace('  ', ' ')
    
    # Convert \\r newlines 
    text = text.replace('\r', '\n')
    
    # Remove spaces after newlines
    text = text.replace('\n ', '\n')
    
    return text



class Menu(QtGui.QMenu):
    """ Menu(parent=None, name=None)
    
    Base class for all menus. Has methods to add actions of all sorts.
    
    The add* methods all have the name and icon as first two arguments.
    This is not so consistent with the Qt API for addAction, but it allows
    for cleaner code to add items; the first item can be quite long because
    it is a translation. In the current API, the second and subsequent 
    arguments usually fit nicely on the second line.
    
    """
    def __init__(self, parent=None, name=None):
        QtGui.QMenu.__init__(self, parent)
        
        # Make sure that the menu has a title
        if name:
            self.setTitle(name)
        else:
            raise ValueError
        
        # Set tooltip too?
        if hasattr(name, 'tt'):
            self.setStatusTip(name.tt)
        
        # Action groups within the menu keep track of the selected value
        self._groups = {}
        
        # menuPath is used to bind shortcuts, it is ,e.g. shell__clear_screen
        if hasattr(parent,'menuPath'):
            self.menuPath = parent.menuPath + '__'
        else:
            self.menuPath = '' #This is a top-level menu
        
        # Get key for this menu
        key = name
        if hasattr(name, 'key'):
            key = name.key
        self.menuPath += self._createMenuPathName(key)
                
        # Build the menu. Happens only once
        self.build()
    
    
    def _createMenuPathName(self, name):
        """
        Convert a menu title into a menuPath component name
        e.g. Interrupt current shell -> interrupt_current_shell
        """
        # hide anything between brackets
        name = re.sub('\(.*\)', '', name)
        # replace invalid chars
        name = name.replace(' ', '_')
        if name[0] in '0123456789_':
            name = "_" + name
        name = re.sub('[^a-zA-z_0-9]','',name)
        return name.lower()
    
    
    def _addAction(self, text, icon, selected=None):
        """ Convenience function that makes the right call to addAction().
        """
        
        # Add the action
        if icon is None:
            a = self.addAction(text)
        else:
            a = self.addAction(icon, text)
        
        # Checkable?
        if selected is not None:
            a.setCheckable(True)
            a.setChecked(selected)
        
         # Set tooltip if we can find it
        if hasattr(text, 'tt'):
            a.setStatusTip(text.tt)
        
        # Find the key (untranslated name) for this menu item
        key = a.text()
        if hasattr(text, 'key'):
            key = text.key
        a.menuPath = self.menuPath + '__' + self._createMenuPathName(key)
        
        # Register the action so its keymap is kept up to date
        iep.keyMapper.keyMappingChanged.connect(lambda: iep.keyMapper.setShortcut(a))
        iep.keyMapper.setShortcut(a)
        
        return a
    
    
    def build(self):
        """ 
        Add all actions to the menu. To be overridden.
        """
        raise NotImplementedError
    
    
    def addMenu(self, menu, icon=None):
        """
        Add a (sub)menu to this menu.
        """
        
        # Add menu in the conventional way
        a = QtGui.QMenu.addMenu(self, menu)
        a.menuPath = menu.menuPath
        
        # Set icon
        if icon is not None:
            a.setIcon(icon)
        
        return menu
    
    def addItem(self, text, icon=None, callback=None, value=None):
        """
        Add an item to the menu. If callback is given and not None,
        connect triggered signal to the callback. If value is None or not
        given, callback is called without parameteres, otherwise it is called
        with value as parameter
        """
        
        # Add action 
        a = self._addAction(text, icon)
        
        # Connect the menu item to its callback
        if callback:
            if value is not None:
                a.triggered.connect(lambda b, v = value: callback(v))
            else:
                a.triggered.connect(lambda b: callback())
        
        return a
    
    
    def addGroupItem(self, text, icon=None, callback=None, value=None, group=None):
        """
        Add a 'select-one' option to the menu. Items with equal group value form
        a group. If callback is specified and not None, the callback is called 
        for the new active item, with the value for that item as parameter
        whenever the selection is changed
        """
        
        # Init action
        a = self._addAction(text, icon)
        a.setCheckable(True)
        
        # Connect the menu item to its callback (toggled is a signal only
        # emitted by checkable actions, and can also be called programmatically,
        # e.g. in QActionGroup)
        if callback:
            def doCallback(b, v):
                if b:
                    callback(v)
            a.toggled.connect(lambda b, v = value: doCallback(b, v))
        
        # Add the menu item to a action group
        if group is None:
            group = 'default'
        if group not in self._groups:
            #self._groups contains tuples (actiongroup, dict-of-actions)
            self._groups[group] = (QtGui.QActionGroup(self), {})
        
        actionGroup,actions = self._groups[group]
        actionGroup.addAction(a)
        actions[value]=a
        
        return a
    
    
    def addCheckItem(self, text, icon=None, callback=None, value=None, selected=False):
        """
        Add a true/false item to the menu. If callback is specified and not 
        None, the callback is called when the item is changed. If value is not
        specified or None, callback is called with the new state as parameter.
        Otherwise, it is called with the new state and value as parameters
        """
        
        # Add action 
        a = self._addAction(text, icon, selected)
        
        # Connect the menu item to its callback
        if callback:
            if value is not None:
                a.triggered.connect(lambda b, v = value: callback(b,v))
            else:
                a.triggered.connect(lambda b: callback(b))
        
        return a
    
    
    def setCheckedOption(self, group, value):
        """ 
        Set the selected value of a group. This will also activate the
        callback function of the item that gets selected.
        if group is None the default group is used.
        """
        if group is None:
            group = 'default'
        actionGroup, actions = self._groups[group]
        if value in actions:
            actions[value].setChecked(True)


class GeneralOptionsMenu(Menu):
    """ GeneralOptionsMenu(parent, name, callback, options=None)
    
    Menu to present the user with a list from which to select one item.
    We need this a lot.
    
    """
    
    def __init__(self, parent=None, name=None, callback=None, options=None):
        Menu.__init__(self, parent, name)
        self._options_callback = callback
        if options:
            self.setOptions(options)
    
    def build(self):
        pass # We build when the options are given
    
    def setOptions(self, options, values=None):
        """ 
        Set the list of options, clearing any existing options. The options
        are added ad group items and registered to the callback given 
        at initialization.
        """
        # Init
        self.clear()
        cb = self._options_callback
        # Get values
        if values is None:
            values = options
        for option, value in zip(options, values):
            self.addGroupItem(option, None, cb, value)


class IndentationMenu(Menu):
    """
    Menu for the user to control the type of indentation for a document:
    tabs vs spaces and the amount of spaces.
    Part of the File menu.
    """
        
    def build(self):
        self._items = [
            self.addGroupItem(translate("menu", "Use tabs"), 
                None, self._setStyle, False, group="style"),
            self.addGroupItem(translate("menu", "Use spaces"), 
                None, self._setStyle, True, group="style")
            ]
        self.addSeparator()
        spaces = translate("menu", "spaces", "plural of spacebar character")
        self._items += [
            self.addGroupItem("%d %s" % (i, spaces), None, self._setWidth, i, group="width")
            for i in range(2,9)
            ]
    
    def _setWidth(self, width):
        editor = iep.editors.getCurrentEditor()
        if editor is not None:
            editor.setIndentWidth(width)

    def _setStyle(self, style):
        editor = iep.editors.getCurrentEditor()
        if editor is not None:
            editor.setIndentUsingSpaces(style)


class FileMenu(Menu):
    def build(self):
        icons = iep.icons
        
        self._items = []
        
        # Create indent menu
        t = translate("menu", "Indentation ::: The indentation used of the current file.")
        self._indentMenu = IndentationMenu(self, t)
        
        # Create parser menu
        import codeeditor
        t = translate("menu", "Syntax parser ::: The syntax parser of the current file.")
        self._parserMenu = GeneralOptionsMenu(self, t, self._setParser)
        self._parserMenu.setOptions(['None'] + codeeditor.Manager.getParserNames())
        
        # Create line ending menu
        t = translate("menu", "Line endings ::: The line ending character of the current file.")
        self._lineEndingMenu = GeneralOptionsMenu(self, t, self._setLineEndings)
        self._lineEndingMenu.setOptions(['LF', 'CR', 'CRLF'])
        
        # Create encoding menu
        t = translate("menu", "Encoding ::: The character encoding of the current file.")
        self._encodingMenu = GeneralOptionsMenu(self, t, self._setEncoding)
        
        # Bind to signal
        iep.editors.currentChanged.connect(self.onEditorsCurrentChanged)
        
        
        # Build menu file management stuff
        self.addItem(translate('menu', 'New ::: Create a new (or temporary) file.'),
            icons.page_add, iep.editors.newFile)
        self.addItem(translate("menu", "Open... ::: Open an existing file from disk."),
            icons.folder_page, iep.editors.openFile)
        #
        self._items += [ 
            self.addItem(translate("menu", "Save ::: Save the current file to disk."),
                icons.disk, iep.editors.saveFile),
            self.addItem(translate("menu", "Save as... ::: Save the current file under another name."),
                icons.disk_as, iep.editors.saveFileAs),
            self.addItem(translate("menu", "Save all ::: Save all open files."),
                icons.disk_multiple, iep.editors.saveAllFiles),
            self.addItem(translate("menu", "Close ::: Close the current file."),
                icons.page_delete, iep.editors.closeFile),
            self.addItem(translate("menu", "Close all ::: Close all files."),
                icons.page_delete_all, iep.editors.closeAllFiles),  
            ]
        
        # Build file properties stuff
        self.addSeparator()
        self._items += [
                    self.addMenu(self._indentMenu, icons.page_white_gear),
                    self.addMenu(self._parserMenu, icons.page_white_gear),
                    self.addMenu(self._lineEndingMenu, icons.page_white_gear), 
                    self.addMenu(self._encodingMenu, icons.page_white_gear),
                    ]
        
        # Closing of app
        self.addSeparator()
        self.addItem(translate("menu", "Restart IEP ::: Restart the application."), 
            icons.arrow_rotate_clockwise, iep.main.restart)
        self.addItem(translate("menu","Quit IEP ::: Close the application."), 
            icons.cancel, iep.main.close)
        
        # Start disabled
        self.setEnabled(False)
    
    
    def setEnabled(self, enabled):
        """ Enable or disable all items. If disabling, also uncheck all items """
        for child in self._items:
            child.setEnabled(enabled)
    
    def onEditorsCurrentChanged(self):
        editor = iep.editors.getCurrentEditor()
        if editor is None:
            self.setEnabled(False) #Disable / uncheck all editor-related options
        else:
            self.setEnabled(True)
            # Update indentation
            self._indentMenu.setCheckedOption("style", editor.indentUsingSpaces())
            self._indentMenu.setCheckedOption("width", editor.indentWidth())
            # Update parser
            parserName = 'None'
            if editor.parser():
                parserName = editor.parser().name()
            self._parserMenu.setCheckedOption(None, parserName )
            # Update line ending
            self._lineEndingMenu.setCheckedOption(None, editor.lineEndingsHumanReadable)
            # Update encoding
            self._updateEncoding(editor)
    
    def _setParser(self, value):
        editor = iep.editors.getCurrentEditor()
        if value.lower() == 'none':
            value = None
        if editor is not None:
            editor.setParser(value)
    
    def _setLineEndings(self, value):
        editor = iep.editors.getCurrentEditor()
        editor.lineEndings = value
    
    def _updateEncoding(self, editor):
        # Dict with encoding aliases (official to aliases)        
        D  = {  'cp1250':  ('windows-1252', ),
                'cp1251':  ('windows-1251', ),
                'latin_1': ('iso-8859-1', 'iso8859-1', 'cp819', 'latin', 'latin1', 'L1')}
        # Dict with aliases mapping to "official value"
        Da = {}
        for key in D:
            for key2 in D[key]:
                Da[key2] = key
        
        # Encodings to list
        encodings = [   'utf-8','ascii', 'latin_1',
                        'cp1250', 'cp1251']
        
        # Get current encoding (add if not present)
        editorEncoding = editor.encoding
        if editorEncoding in Da:
            editorEncoding = Da[editorEncoding]
        if editorEncoding not in encodings:
            encodings.append(editorEncoding)
        
        # Handle aliases
        encodingNames, encodingValues = [], []
        for encoding in encodings:
            encodingValues.append(encoding)
            if encoding in D:
                name = '%s (%s)' % (encoding, ', '.join(D[encoding]))
                encodingNames.append(name)
            else:
                encodingNames.append(encoding)
        
        # Update
        self._encodingMenu.setOptions(encodingNames, encodingValues)
        self._encodingMenu.setCheckedOption(None, editorEncoding)
    
    def _setEncoding(self, value):
        editor = iep.editors.getCurrentEditor()
        if editor is not None:
            editor.encoding = value


# todo: move to matching brace
class EditMenu(Menu):
    def build(self):
        icons = iep.icons
        
        self.addItem(translate("menu", "Undo ::: Undo the latest editing action."),
            icons.arrow_undo, self._editItemCallback, "undo")
        self.addItem(translate("menu", "Redo ::: Redo the last undone editong action."), 
            icons.arrow_redo, self._editItemCallback, "redo")
        self.addSeparator()
        self.addItem(translate("menu", "Cut ::: Cut the selected text."), 
            icons.cut, self._editItemCallback, "cut")
        self.addItem(translate("menu", "Copy ::: Copy the selected text to the clipboard."), 
            icons.page_white_copy, self._editItemCallback, "copy")
        self.addItem(translate("menu", "Paste ::: Paste the text that is now on the clipboard."), 
            icons.paste_plain, self._editItemCallback, "paste")
        self.addItem(translate("menu", "Select all ::: Select all text."), 
            icons.sum, self._editItemCallback, "selectAll")
        self.addSeparator()
        self.addItem(translate("menu", "Indent ::: Indent the selected line."), 
            icons.text_indent, self._editItemCallback, "indentSelection")
        self.addItem(translate("menu", "Dedent ::: Unindent the selected line."), 
            icons.text_indent_remove, self._editItemCallback, "dedentSelection")
        self.addItem(translate("menu", "Comment ::: Comment the selected line."), 
            icons.comment_add, self._editItemCallback, "commentCode")
        self.addItem(translate("menu", "Uncomment ::: Uncomment the selected line."), 
            icons.comment_delete, self._editItemCallback, "uncommentCode")
        self.addItem(translate("menu", "Delete line ::: Delete the selected line."), 
            None, self._editItemCallback, "deleteLines")
        self.addSeparator()
        self.addItem(translate("menu", "Find or replace ::: Show find/replace widget. Initialize with selected text."), 
            icons.find, iep.editors._findReplace.startFind)
        self.addItem(translate("menu", "Find selection ::: Find the next occurance of the selected text."), 
            None, iep.editors._findReplace.findSelection)
        self.addItem(translate("menu", "Find selection backward ::: Find the previous occurance of the selected text."), 
            None, iep.editors._findReplace.findSelectionBw)
        self.addItem(translate("menu", "Find next ::: Find the next occurance of the search string."), 
            None, iep.editors._findReplace.findNext)
        self.addItem(translate("menu", "Find previous ::: Find the previous occurance of the search string."), 
            None, iep.editors._findReplace.findPrevious)
    
    
    def _editItemCallback(self, action):
        widget = QtGui.qApp.focusWidget()
        #If the widget has a 'name' attribute, call it
        if hasattr(widget, action):
            getattr(widget, action)()


class ZoomMenu(Menu):
    """
    Small menu for the zooming. Part of the view menu.
    """
    def build(self):
        self.addItem(translate("menu", 'Zoom in'), None, self._setZoom, +1)
        self.addItem(translate("menu", 'Zoom out'), None, self._setZoom, -1)
        self.addItem(translate("menu", 'Zoom reset'), None, self._setZoom, 0)
    
    def _setZoom(self, value):
        if not value:
            iep.config.view.zoom = 0
        else:
            iep.config.view.zoom += value
        # Apply
        for editor in iep.editors:
            iep.config.view.zoom = editor.setZoom(iep.config.view.zoom)


# todo: brace matching
# todo: code folding?
# todo: maybe move qt theme to settings
class ViewMenu(Menu):
    def build(self):
        icons = iep.icons
        
        # Create edge column menu
        t = translate("menu", "Edge Column ::: The location of the long-line-indicator.")
        self._edgeColumMenu = GeneralOptionsMenu(self, t, self._setEdgeColumn)
        values = [0] + [i for i in range(60,130,10)]
        names = ["None"] + [str(i) for i in values[1:]]
        self._edgeColumMenu.setOptions(names, values)
        self._edgeColumMenu.setCheckedOption(None, iep.config.view.edgeColumn)
        
        # Create qt theme menu
        t = translate("menu", "Qt theme ::: The styling of the user interface widgets.")
        self._qtThemeMenu = GeneralOptionsMenu(self, t, self._setQtTheme)
        styleNames = list(QtGui.QStyleFactory.keys()) + ['Cleanlooks+']
        styleNames.sort()
        titles = [name for name in styleNames]
        styleNames = [name.lower() for name in styleNames]
        for i in range(len(titles)):
            if titles[i].lower() == iep.defaultQtStyleName.lower():
                titles[i] += " (default)"
        self._qtThemeMenu.setOptions(titles, styleNames)
        self._qtThemeMenu.setCheckedOption(None, iep.config.view.qtstyle.lower())
        
        # Build menu
        self.addItem(translate("menu", "Select shell ::: Focus the cursor on the current shell."), 
            icons.application_shell, self._selectShell)
        self.addItem(translate("menu", "Select editor ::: Focus the cursor on the current editor."), 
            icons.application_edit, self._selectEditor)
        self.addItem(translate("menu", "Select previous file ::: Select the previously selected file."), 
            icons.application_double, iep.editors._tabs.selectPreviousItem)
        self.addSeparator()
        self.addEditorItem(translate("menu", "Show whitespace ::: Show spaces and tabs."), 
            None, "showWhitespace")
        self.addEditorItem(translate("menu", "Show line endings ::: Show the end of each line."), 
            None, "showLineEndings")
        self.addEditorItem(translate("menu", "Show indentation guides ::: Show vertical lines to indicate indentation."), 
            None, "showIndentationGuides")
        self.addSeparator()
        self.addEditorItem(translate("menu", "Wrap long lines ::: Wrap lines that do not fit on the screen (i.e. no horizontal scrolling)."), 
            None, "wrap")
        self.addEditorItem(translate("menu", "Highlight current line ::: Highlight the line where the cursor is."), 
            None, "highlightCurrentLine")
        self.addSeparator()
        self.addMenu(self._edgeColumMenu, icons.text_padding_right)
        self.addMenu(ZoomMenu(self, translate("menu", "Zooming")), icons.magnifier)
        self.addMenu(self._qtThemeMenu, icons.application_view_tile)
    
    def addEditorItem(self, name, icon, param):
        """ 
        Create a boolean item that reperesents a property of the editors,
        whose value is stored in iep.config.view.param 
        """
        if hasattr(iep.config.view, param):
            default = getattr(iep.config.view, param)
        else:
            default = True
            
        self.addCheckItem(name, icon, self._configEditor, param, default)
    
    def _configEditor(self, state, param):
        """
        Callback for addEditorItem items
        """
        # Store this parameter in the config
        setattr(iep.config.view, param, state)
        # Apply to all editors, translate e.g. showWhitespace to setShowWhitespace
        setter = 'set' + param[0].upper() + param[1:]
        for editor in iep.editors:
            getattr(editor,setter)(state)
    
    def _selectShell(self):
        shell = iep.shells.getCurrentShell()
        if shell:
            shell.setFocus()
            
    def _selectEditor(self):
        editor = iep.editors.getCurrentEditor()
        if editor:
            editor.setFocus()
    
    def _setEdgeColumn(self, value):
        iep.config.view.edgeColumn = value
        for editor in iep.editors:
            editor.setLongLineIndicatorPosition(value)
    
    def _setQtTheme(self, value):
        iep.config.view.qtstyle = value
        iep.main.setQtStyle(value)


class ShellMenu(Menu):
    
    def __init__(self, parent=None, name="Shell", *args, **kwds):
        self._shellCreateActions = []
        self._shellActions = []
        Menu.__init__(self, parent, name, *args, **kwds)
        iep.shells.currentShellChanged.connect(self.onCurrentShellChanged)
        
    def onCurrentShellChanged(self):
        """ Enable/disable shell actions based on wether a shell is available """
        for shellAction in self._shellActions:
            shellAction.setEnabled(bool(iep.shells.getCurrentShell()))
    
    def buildShellActions(self):
        """ Create the menu items which are also avaliable in the
        ShellTabContextMenu
        
        Returns a list of all items added"""
        icons = iep.icons
        return [
            self.addItem(translate("menu", 'Interrupt ::: Interrupt the current running code (does not work for extension code).'), 
                icons.application_lightning, self._shellAction, "interrupt"),
            self.addItem(translate("menu", 'Terminate ::: Terminate the interpreter, leaving the shell open.'), 
                icons.application_delete, self._shellAction, "terminate"),
            self.addItem(translate("menu", 'Close ::: Terminate the interpreter and close the shell.'), 
                icons.cancel, self._shellAction, "closeShell"),
            self.addItem(translate("menu", 'Restart ::: Terminate and restart the interpreter.'), 
                icons.application_refresh, self._shellAction, "restart"),
            self.addItem(translate("menu", 'Clear screen ::: Clear the screen.'), 
                icons.application_eraser, self._shellAction, "clearScreen"),
            ]
    
    def getShell(self):
        """ Returns the shell on which to apply the menu actions. Default is
        the current shell, this is overridden in the shell/shell tab context
        menus"""
        return iep.shells.getCurrentShell()
        
    def build(self):
        """ Create the items for the shells menu """
        self._shellActions = self.buildShellActions()
        
        self.addSeparator()
        self.addItem(translate("menu", 'Edit shell configurations... ::: Add new shell configs and edit interpreter properties.'), 
            iep.icons.application_wrench, self._editConfig2)
        self.addSeparator()
        
        # Add shell configs
        self._updateShells()    
    
    def _updateShells(self):
        """ Remove, then add the items for the creation of each shell """
        for action in self._shellCreateActions:
            self.removeAction(action)
        
        self._shellCreateActions = []
        for i, config in enumerate(iep.config.shellConfigs2):
            name = 'Create shell %s: (%s)' % (i+1, config.name)
            action = self.addItem(name, 
                iep.icons.application_add, iep.shells.addShell, config)
            self._shellCreateActions.append(action)
    
    def _shellAction(self, action):
        """ Call the method specified by 'action' on the current shell.
        """
        shell = self.getShell()
        if shell:
            # Call the specified action
            getattr(shell,action)()
    
    def _editConfig(self):
        """ Edit, add and remove configurations for the shells. """
        from iepcore.shellTabs import ShellConfigDialog 
        d = ShellConfigDialog()
        d.exec_()
        # Update the shells items in the menu
        self._updateShells()
    
    def _editConfig2(self):
        """ Edit, add and remove configurations for the shells. """
        from iepcore.shellInfoDialog import ShellInfoDialog 
        d = ShellInfoDialog()
        d.exec_()
        # Update the shells items in the menu
        self._updateShells()



class ShellContextMenu(ShellMenu):
    """ This is the context menu for the shell """
    def __init__(self, shell, *args, **kwds):
        ShellMenu.__init__(self, *args, **kwds)
        self._shell = shell
    
    def build(self):
        """ Build menu """
        self.buildShellActions()
        icons = iep.icons
        
        # This is a subset of the edit menu. Copied manually.
        self.addSeparator()
        self.addItem(translate("menu", "Cut ::: Cut the selected text."), 
            icons.cut, self._editItemCallback, "cut")
        self.addItem(translate("menu", "Copy ::: Copy the selected text to the clipboard."), 
            icons.page_white_copy, self._editItemCallback, "copy")
        self.addItem(translate("menu", "Paste ::: Paste the text that is now on the clipboard."), 
            icons.paste_plain, self._editItemCallback, "paste")
        self.addItem(translate("menu", "Select all ::: Select all text."), 
            icons.sum, self._editItemCallback, "selectAll")
    
    def getShell(self):
        """ Shell actions of this menu operate on the shell specified in the constructor """
        return self._shell
    
    def _editItemCallback(self, action):
        #If the widget has a 'name' attribute, call it
        getattr(self._shell, action)()


class ShellTabContextMenu(ShellContextMenu):
    """ The context menu for the shell tab is similar to the shell context menu,
    but only has the shell actions defined in ShellMenu.buildShellActions()"""
    def build(self):
        """ Build menu """
        self.buildShellActions()
        


class EditorTabContextMenu(Menu):
    def __init__(self, *args, **kwds):
        Menu.__init__(self, *args, **kwds)
        self._index = -1
    
    def setIndex(self, index):
        self._index = index
    
    def build(self):
        """ Build menu """
        icons = iep.icons
        
        # Copied (and edited) manually from the File memu
        self.addItem(translate("menu", "Save ::: Save the current file to disk."),
            icons.disk, self._fileAction, "saveFile")
        self.addItem(translate("menu", "Save as... ::: Save the current file under another name."),
            icons.disk_as, self._fileAction, "saveFileAs")
        self.addItem(translate("menu", "Close ::: Close the current file."),
            icons.page_delete, self._fileAction, "closeFile")
        self.addItem(translate("menu", "Close others::: Close all files but this one."),
            None, self._fileAction, "close_others")
        self.addItem(translate("menu", "Close all ::: Close all files."),
            icons.page_delete_all, self._fileAction, "close_all")
        self.addItem(translate("menu", "Rename ::: Rename this file."),
            None, self._fileAction, "rename")
        
        self.addSeparator()
        # todo: remove feature to pin files?
        self.addItem(translate("menu", "Pin/Unpin ::: Pinned files get closed less easily."), 
            None, self._fileAction, "pin")
        self.addItem(translate("menu", "Set/Unset as MAIN file ::: The main file can be run while another file is selected."), 
            icons.star, self._fileAction, "main")
        
        self.addSeparator()
        self.addItem(translate("menu", "Run ::: Run the code in this file."), 
            icons.run_file, self._fileAction, "run")
        self.addItem(translate("menu", "Run as script ::: Run this file as a script (restarts the interpreter)."), 
            icons.run_file_script, self._fileAction, "run_script")
    
    
    def _fileAction(self, action):
        """ Call the method specified by 'action' on the selected shell """
        
        item = iep.editors._tabs.getItemAt(self._index)
        
        if action in ["saveFile", "saveFileAs", "closeFile"]:
            getattr(iep.editors, action)(item.editor)
        elif action == "close_others" or action == "close_all":
            if action == "close_all":
                item = None #The item not to be closed is not there
            items = iep.editors._tabs.items()
            for i in reversed(range(iep.editors._tabs.count())):
                if items[i] is item or items[i].pinned:
                    continue
                iep.editors._tabs.tabCloseRequested.emit(i)
            
        elif action == "rename":
            filename = item.filename
            iep.editors.saveFileAs(item.editor)
            if item.filename != filename:
                try:
                    os.remove(filename)
                except Exception:
                    pass
        elif action == "pin":
            item._pinned = not item._pinned
        elif action == "main":
            if iep.editors._tabs._mainFile == item.id:
                iep.editors._tabs._mainFile = None
            else:
                iep.editors._tabs._mainFile = item.id
        elif action == "run":
            menu = iep.main.menuBar().findChild(RunMenu)
            if menu:
                menu._runFile((False, False), item.editor)
        elif action == "run_script":
            menu = iep.main.menuBar().findChild(RunMenu)
            if menu:
                menu._runFile((True, False), item.editor)
            
        iep.editors._tabs.updateItems()


class RunMenu(Menu):       
    def build(self):
        icons = iep.icons
        
        self.addItem(translate("menu", 'Run selected lines ::: Run the selected editor\'s selected lines in the current shell.'), 
            icons.run_lines, self._runSelected)
        self.addItem(translate("menu", 'Run cell ::: Run the current editors\'s cell in the current shell.'), 
            icons.run_cell, self._runCell)
        #In the _runFile calls, the parameter specifies (asScript, mainFile)
        self.addItem(translate("menu", 'Run file ::: Run the current file in the current shell.'), 
            icons.run_file, self._runFile,(False, False))
        self.addItem(translate("menu", 'Run main file ::: Run the main file in the current shell.'), 
            icons.run_mainfile, self._runFile,(False, True))
        self.addSeparator()
        self.addItem(translate("menu", 'Run file as script ::: Run the current file as a script.'), 
            icons.run_file_script, self._runFile, (True, False))
        self.addItem(translate("menu", 'Run main file as script ::: Run the main file as a script.'), 
            icons.run_mainfile_script, self._runFile, (True, True))
        self.addSeparator()
        self.addItem(translate("menu", 'Help on running code ::: Open the tutorial at the section about running code.'), 
            icons.information, self._showHelp)

    
    def _showHelp(self):
        """ Show more information about ways to run code. """
        
        # todo: use cell header to goto right line. 
        # Or make another way to show information on a subject.
        # Get file item
        fileItem = iep.editors.loadFile(
                        os.path.join(iep.iepDir, 'resources', 'tutorial.py'))
        
        # Select line number
        if fileItem:
            linenr = 77
            editor = fileItem._editor
            editor.gotoLine(linenr)
            iep.editors.getCurrentEditor().setFocus()
    
    
    def _getShellAndEditor(self, what, mainEditor=False):
        """ Get the shell and editor. Shows a warning dialog when one of
        these is not available.
        """
        # Init empty error message
        msg = ''
        # Get shell
        shell = iep.shells.getCurrentShell()
        if shell is None:
            msg += "No shell to run code in. "
        # Get editor
        if mainEditor:
            editor = iep.editors.getMainEditor()
            if editor is None:
                msg += "The is no main file selected."
        else:
            editor = iep.editors.getCurrentEditor()
            if editor is None:
                msg += "No editor selected."
        # Show error dialog
        if msg:
            m = QtGui.QMessageBox(self)
            m.setWindowTitle(translate("menu dialog", "Could not run"))
            m.setText("Could not run " + what + ":\n\n" + msg)
            m.setIcon(m.Warning)
            m.exec_()
        # Return
        return shell, editor
        

    def _runSelected(self):
        """ Run the selected whole lines in the current shell. 
        """
        # Get editor and shell
        shell, editor = self._getShellAndEditor('selected lines')
        if not shell or not editor:
            return
        
        # Get position to sample between (only sample whole lines)
        screenCursor = editor.textCursor() #Current selection in the editor
        runCursor = editor.textCursor() #The part that should be run
        
        runCursor.setPosition(screenCursor.selectionStart())
        runCursor.movePosition(runCursor.StartOfBlock) #This also moves the anchor
        lineNumber = runCursor.blockNumber()
        
        runCursor.setPosition(screenCursor.selectionEnd(),runCursor.KeepAnchor)
        if not runCursor.atBlockStart():
            #If the end of the selection is at the beginning of a block, don't extend it
            runCursor.movePosition(runCursor.EndOfBlock,runCursor.KeepAnchor)
        
        # Get source code
        code = runCursor.selectedText().replace('\u2029', '\n')
        # Notify user of what we execute
        self._showWhatToExecute(editor, runCursor)
        # Get filename and run code
        fname = editor.id() # editor._name or editor._filename
        shell.executeCode(code, fname, lineNumber)
    
    def _runCell(self):
        """ Run the code between two cell separaters ('##'). 
        """
        #TODO: ignore ## in multi-line strings
        # Maybe using source-structure information?
        
        # Get editor and shell
        shell, editor = self._getShellAndEditor('cell')
        if not shell or not editor:
            return 
        
        # Get current cell
        # Move up until the start of document 
        # or right after a line starting with '##'  
        runCursor = editor.textCursor() #The part that should be run
        runCursor.movePosition(runCursor.StartOfBlock)
        while True:
            if runCursor.block().text().lstrip().startswith('##'):
                # ## line, move to the line following this one
                if not runCursor.block().next().isValid():
                    #The user tried to execute the last line of a file which
                    #started with ##. Do nothing
                    return
                runCursor.movePosition(runCursor.NextBlock)
                break
            if not runCursor.block().previous().isValid():
                break #Start of document
            runCursor.movePosition(runCursor.PreviousBlock)
        
        # This is the line number of the start
        lineNumber = runCursor.blockNumber()
        
        # Move down until a line before one starting with'##' 
        # or to end of document
        while True:
            if runCursor.block().text().lstrip().startswith('##'):
                #This line starts with ##, move to the end of the previous one
                runCursor.movePosition(runCursor.Left,runCursor.KeepAnchor)
                break
            if not runCursor.block().next().isValid():
                #Last block of the document, move to the end of the line
                runCursor.movePosition(runCursor.EndOfLine,runCursor.KeepAnchor)
                break
            runCursor.movePosition(runCursor.NextBlock,runCursor.KeepAnchor)
        
        # Get source code
        code = runCursor.selectedText().replace('\u2029', '\n')
        # Notify user of what we execute
        self._showWhatToExecute(editor, runCursor)
        # Get filename and run code
        fname = editor.id() # editor._name or editor._filename
        shell.executeCode(code, fname, lineNumber)
    
    def _showWhatToExecute(self, editor, runCursor=None):
        # Get runCursor for whole document if not given
        if runCursor is None:
            runCursor = editor.textCursor()
            runCursor.movePosition(runCursor.Start)
            runCursor.movePosition(runCursor.End, 1)
        
        editor.showRunCursor(runCursor)

    
    def _getCodeOfFile(self, editor):
        # Obtain source code
        text = editor.toPlainText()
        # Show what we execute
        self._showWhatToExecute(editor)
        # Get filename and return 
        fname = editor.id() # editor._name or editor._filename
        return fname, text
    
    def _runFile(self, runMode, givenEditor=None):
        """ Run a file
         runMode is a tuple (asScript, mainFile)
         """
        asScript, mainFile = runMode
         
        # Get editor and shell
        description = 'main file' if mainFile else 'file'
        if asScript:
            description += ' (as script)'
        
        shell, editor = self._getShellAndEditor(description, mainFile)
        if givenEditor:
            editor = givenEditor
        if not shell or not editor:
            return        
        
        if asScript:
            # Go
            self._runScript(editor, shell)
        else:
            # Obtain source code and fname
            fname, text = self._getCodeOfFile(editor)
            shell.executeCode(text, fname, -1)
    
    def _runScript(self, editor, shell):
        # Obtain fname and try running
        err = ""
        if editor._filename:
            saveOk = iep.editors.saveFile(editor) # Always try to save
            if saveOk or not editor.document().isModified():
                self._showWhatToExecute(editor)
                shell.restart(editor._filename)
            else:
                err = "Could not save the file."
        else:
            err = "Can only run scripts that are in the file system."
        # If not success, notify
        if err:
            m = QtGui.QMessageBox(self)
            m.setWindowTitle(translate("menu dialog", "Could not run script."))
            m.setText(err)
            m.setIcon(m.Warning)
            m.exec_()


class ToolsMenu(Menu):
    
    def __init__(self, *args, **kwds):
        self._toolActions = []
        Menu.__init__(self, *args, **kwds)
    
    def build(self):
        self.addItem(translate("menu", 'Reload tools ::: For people who develop tools.'), 
            iep.icons.plugin_refresh, iep.toolManager.reloadTools)
        self.addSeparator()

        self.onToolInstanceChange() # Build initial menu
        iep.toolManager.toolInstanceChange.connect(self.onToolInstanceChange)

        
    def onToolInstanceChange(self):
        # Remove all exisiting tools from the menu
        for toolAction in self._toolActions:
            self.removeAction(toolAction)
        
        # Add all tools, with checkmarks for those that are active
        self._toolActions = []
        for tool in iep.toolManager.getToolInfo():
            action = self.addCheckItem(tool.name, iep.icons.plugin, 
                tool.menuLauncher, selected=bool(tool.instance))
            self._toolActions.append(action)


class HelpMenu(Menu):
    
    def build(self):
        icons = iep.icons
        
        self.addUrlItem(translate("menu", "Website ::: Open the IEP website in your browser."), 
            icons.help, "http://iep.pyzo.org")
        self.addUrlItem(translate("menu", "Ask a question ::: Need help?"), 
            icons.comments, "http://groups.google.com/group/iep_")
        self.addUrlItem(translate("menu", "Report an issue ::: Did you found a bug in IEP, or do you have a feature request?"), 
            icons.error_add, "http://code.google.com/p/iep/issues/list")
        self.addSeparator()
        self.addItem(translate("menu", "Tutorial ::: Get started quickly."), 
            icons.report, lambda: iep.editors.loadFile(os.path.join(iep.iepDir,"resources","tutorial.py")))
        self.addItem(translate("menu", "View license ::: Legal stuff."), 
            icons.script, lambda: iep.editors.loadFile(os.path.join(iep.iepDir,"license.txt")))
        
        self.addItem(translate("menu", "Check for updates ::: Are you using the latest version?"), 
            icons.application_go, self._checkUpdates)
        self.addItem(translate("menu", "About IEP ::: More information about IEP."), 
            icons.information, self._aboutIep)
    
    def addUrlItem(self, name, icon, url):
        self.addItem(name, icon, lambda: webbrowser.open(url))
    
    def _checkUpdates(self):
        """ Check whether a newer version of IEP is available. """
        # Get versions available
        import urllib.request, re
        url = "http://code.google.com/p/iep/downloads/list"
        text = str( urllib.request.urlopen(url).read() )
        results = []
        for pattern in ['iep-(.{1,9}?)\.source\.zip' ]:
            results.extend( re.findall(pattern, text) )
        # Produce single string with all versions ...
        versions = ', '.join(set(results))
        if not versions:
            versions = '?'
        # Define message
        text = "Your version of IEP is: {}\n" 
        text += "Available versions are: {}\n\n"         
        text = text.format(iep.__version__, versions)
        # Show message box
        m = QtGui.QMessageBox(self)
        m.setWindowTitle(translate("menu dialog", "Check for the latest version."))
        if versions == '?':
            text += "Oops, could not determine available versions.\n\n"    
        if True:
            text += "Do you want to open the download page?\n"    
            m.setStandardButtons(m.Yes | m.Cancel)
            m.setDefaultButton(m.Cancel)
        m.setText(text)
        m.setIcon(m.Information)
        result = m.exec_()
        # Goto webpage if user chose to
        if result == m.Yes:
            import webbrowser
            webbrowser.open("http://code.google.com/p/iep/downloads/list")
    
    def _aboutIep(self):
        aboutText = """
        <h2>IEP: the Interactive Editor for Python</h2>
        
        <b>Version info</b><br>
        IEP version: <u>{}</u><br>
        Platform: {}<br>
        Python version: {}<br>
        Qt version: {}<br>
        PyQt version: {}<br>
        <br>
        
        <b>IEP directories</b><br>
        IEP source directory: {}<br>
        IEP userdata directory: {}<br>
        <br>
        
        <b>Acknowledgements</b><br>
        IEP is written in Python 3 and uses the Qt4 widget
        toolkit. IEP uses code and concepts that are inspired by 
        IPython, Pype, and Spyder.
        IEP uses a (modified) subset of the silk icon set, 
        by Mark James (http://www.famfamfam.com/lab/icons/silk/).
        <br><br>
        
        <b>License</b><br>
        Copyright (C) 2012, the IEP development team<br>
        IEP is distributed under the terms of the (new) BSD License.<br>
        The full license can be found in 'license.txt'.
        <br><br>
        
        <b>Developers</b><br>
        Almar Klein<br>
        Rob Reilink<br>
        Ludo Visser<br>
        
        """
        # Insert information texts
        if iep.isFrozen():
            versionText = iep.__version__ + ' (binary)'
        else:
            versionText = iep.__version__ + ' (source)'
        aboutText = aboutText.format(versionText, 
                        sys.platform, sys.version.split(' ')[0],
                        QtCore.QT_VERSION_STR, QtCore.PYQT_VERSION_STR,
                        iep.iepDir, iep.appDataDir)
        
        # Define icon and text
        im = QtGui.QPixmap( os.path.join(iep.iepDir,'icons/iep48.png') )         
        # Show message box
        m = QtGui.QMessageBox(self)
        m.setTextFormat(QtCore.Qt.RichText)
        m.setWindowTitle(translate("menu dialog", "About IEP"))
        m.setText(unwrapText(aboutText))
        m.setIconPixmap(im)
        m.exec_()



class SettingsMenu(Menu):
    def build(self):
        icons = iep.icons
        
        self.addBoolSetting(translate("menu", 'Automatically indent ::: Indent when pressing enter after a colon.'),
            'autoIndent', lambda state, key: [e.setAutoIndent(state) for e in iep.editors])
        self.addBoolSetting(translate("menu", 'Enable calltips ::: Show calltips with function signatures.'), 
            'autoCallTip')
        self.addBoolSetting(translate("menu", 'Enable autocompletion ::: Show autocompletion with known names.'), 
            'autoComplete')
        self.addBoolSetting(translate("menu", 'Autocomplete keywords ::: The autocompletion list includes keywords.'), 
            'autoComplete_keywords')
        
        self.addSeparator()
        self.addItem(translate("menu", 'Edit key mappings... ::: Edit the shortcuts for menu items.'), 
            icons.keyboard, lambda: KeymappingDialog().exec_())
        self.addItem(translate("menu", 'Edit syntax styles... ::: Change the coloring of your code.'), 
            icons.style, self._editStyles)
        self.addItem(translate("menu", 'Advanced settings... ::: Configure IEP even further.'), 
            icons.cog, self._advancedSettings)
    
    def _editStyles(self):
        """ Edit the style file. """
        text = """
        In this beta release, editing style files is not yet possible.
        You're stuck with the one we selected. It's based on the solarized
        theme (http://ethanschoonover.com/solarized) isn't it pretty?
        """
        m = QtGui.QMessageBox(self)
        m.setWindowTitle(translate("menu dialog", "Edit syntax styling"))
        m.setText(unwrapText(text))
        m.setIcon(m.Information)
        m.setStandardButtons(m.Ok | m.Cancel)
        m.setDefaultButton(m.Ok)
        result = m.exec_()
    
    def _advancedSettings(self):
        """ How to edit the advanced settings. """
        text = """
        More settings are available via the logger-tool:
        \r\r
        - Advanced settings are stored in the struct "iep.config.advanced".
          Type "print(iep.config.advanced)" to view all advanced settings.\r
        - Call "iep.resetConfig()" to reset all settings.\r
        - Call "iep.resetConfig(True)" to reset all settings and state.\r
        \r\r
        Note that most settings require a restart for the change to
        take effect.
        """
        m = QtGui.QMessageBox(self)
        m.setWindowTitle(translate("menu dialog", "Advanced settings"))
        m.setText(unwrapText(text))
        m.setIcon(m.Information)
        m.exec_()
    
    def addBoolSetting(self, name, key, callback = None):
        def _callback(state, key):
            setattr(iep.config.settings, key, state)
            if callback is not None:
                callback(state, key)
                
        self.addCheckItem(name, None, _callback, key, 
            getattr(iep.config.settings,key)) #Default value
    

# Remains of old settings menu. Leave here because some settings should some day be 
# accessible via a dialog (advanced settings).
BaseMenu=object
class xSettingsMenu(BaseMenu):
    def fill(self):
        BaseMenu.fill(self)
        addItem = self.addItem
        
        addItem( MI('Autocomplete case sensitive', self.fun_autoComplete_case, []) )
        addItem( MI('Autocomplete select chars', self.fun_autoComplete_fillups, []) )
        addItem( None )
        addItem( MI('Default style', self.fun_defaultStyle, []) )
        addItem( MI('Default indentation width', self.fun_defaultIndentWidth, []) )
        addItem( MI('Default indentation style', self.fun_defaultIndentStyle, []) )
        addItem( MI('Default line endings', self.fun_defaultLineEndings, []) )
 
    def fun_defaultStyle(self, value):
        """ The style used for new files. """
        if value is None:
            current = iep.config.settings.defaultStyle
            options = iep.styleManager.getStyleNames()
            options.append(current)
            return options
        else:
            # store
            iep.config.settings.defaultStyle = value
    
    def fun_defaultIndentWidth(self, value):
        """ The indentation used for new files and in the shells. """
        
        if value is None:
            current = iep.config.settings.defaultIndentWidth
            options = [2,3,4,5,6,7,8, current]           
            return ['%d' % i for i in options]
        
        # parse value
        try:
            val = int(value[:2])
        except ValueError:
            val = 4      
        # store
        iep.config.settings.defaultIndentWidth = val
        # Apply to shells
        for shell in iep.shells:
            shell.setIndentWidth(val)
            
    def fun_defaultIndentStyle(self,value):
        """Whether to use tabs or spaces for indentation in the shells and in new files"""
        # get editor
        
        if value is None:
            options = ['Spaces', 'Tabs']        
            return options + [options[0 if iep.config.settings.defaultIndentUsingSpaces else 1]]
        else:
            # parse value
            val = None

            try:
                val = {'Spaces': True, 'Tabs': False}[value]
            except KeyError:
                val = True
            # apply
            iep.config.settings.defaultIndentUsingSpaces = val
            
    def fun_defaultLineEndings(self, value):
        """ The line endings used for new files. """
        if value is None:
            current = iep.config.settings.defaultLineEndings
            return ['LF', 'CR', 'CRLF', current]
        else:
            # store
            iep.config.settings.defaultLineEndings = value
    
    
    def fun_autoComplete_case(self, value):
        """ Whether the autocompletion is case sensitive or not. """
        if value is None:
            return bool(iep.config.settings.autoComplete_caseSensitive)
        else:
            value = not bool(iep.config.settings.autoComplete_caseSensitive)
            iep.config.settings.autoComplete_caseSensitive = value
            # Apply
            for e in iep.getAllScintillas():
                e.SendScintilla(e.SCI_AUTOCSETIGNORECASE, not value)
    
    def fun_autoComplete_fillups(self, value):
        """ Selected autocomp item is inserted when typing these chars. """
        if value is None:
            # Show options
            options = ['Tab', 'Tab and Enter', 'Tab, Enter and " .(["']
            if '.' in iep.config.settings.autoComplete_fillups:
                options.append( options[2] )
            elif '\n' in iep.config.settings.autoComplete_fillups:
                options.append( options[1] )
            else:
                options.append( options[0] )
            return options
        else:
            # Process selection
            if '.' in value:
                iep.config.settings.autoComplete_fillups = '\n .(['
            elif 'enter' in value.lower():
                iep.config.settings.autoComplete_fillups = '\n'
            else:
                iep.config.settings.autoComplete_fillups = ''
            # Apply
            tmp = iep.config.settings.autoComplete_fillups
            for e in iep.getAllScintillas():                
                e.SendScintilla(e.SCI_AUTOCSETFILLUPS, tmp)
 

## Classes to enable editing the key mappings


class KeyMapModel(QtCore.QAbstractItemModel):
    """ The model to view the structure of the menu and the shortcuts
    currently mapped. """
    
    def __init__(self, *args):
        QtCore.QAbstractListModel.__init__(self,*args)
        self._root = None
    
    def setRootMenu(self, menu):
        """ Call this after starting. """
        self._root = menu

    def data(self, index, role):
        if not index.isValid() or role not in [0, 8]:
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
                key1, key2 = '<>','<>'
                shortcuts = getShortcut(item)
                if shortcuts[0]:
                    key1 = shortcuts[0]
                if shortcuts[1]:
                    key2 = shortcuts[1]
        # translate to text for the user
        key1 = translateShortcutToOSNames(key1)
        key2 = translateShortcutToOSNames(key2)
        
        # obtain value
        value = [value,key1,key2][index.column()]
        
        # return
        if role == 0:
            # display role
            return value
        else:
            return None
#             # 8: BackgroundRole
#             brush = QtGui.QBrush(QtGui.QColor(240,255,240))
#             if value and index.column()>0:
#                 return brush
#             else:
#                 return None
            
    
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
            tmp = ['Menu action','Shortcut 1','Shortcut 2']
            return tmp[section]
    
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


# Key to string mappings
k = QtCore.Qt
keymap = {k.Key_Enter:'Enter', k.Key_Return:'Return', k.Key_Escape:'Escape', 
    k.Key_Tab:'Tab', k.Key_Backspace:'Backspace', k.Key_Pause:'Pause', 
    k.Key_Backtab: 'Tab', #Backtab is actually shift+tab
    k.Key_F1:'F1', k.Key_F2:'F2', k.Key_F3:'F3', k.Key_F4:'F4', k.Key_F5:'F5',
    k.Key_F6:'F6', k.Key_F7:'F7', k.Key_F8:'F8', k.Key_F9:'F9', 
    k.Key_F10:'F10', k.Key_F11:'F11', k.Key_F12:'F12', k.Key_Space:'Space',
    k.Key_Delete:'Delete', k.Key_Insert:'Insert', k.Key_Home:'Home', 
    k.Key_End:'End', k.Key_PageUp:'PageUp', k.Key_PageDown:'PageDown',
    k.Key_Left:'Left', k.Key_Up:'Up', k.Key_Right:'Right', k.Key_Down:'Down' }


class KeyMapLineEdit(QtGui.QLineEdit):
    """ A modified version of a lineEdit object that catches the key event
    and displays "Ctrl" when control was pressed, and similarly for alt and
    shift, function keys and other keys.
    """
    
    textUpdate = QtCore.pyqtSignal()
    
    def __init__(self, *args, **kwargs):
        QtGui.QLineEdit.__init__(self, *args, **kwargs)
        self.clear()

        
        # keep a list of native keys, so that we can capture for example
        # "shift+]". If we would use text(), we can only capture "shift+}"
        # which is not a valid shortcut.
        self._nativeKeys = {}

    # Override setText, text and clear, so as to be able to set shortcuts like
    # Ctrl+A, while the actually displayed value is an OS shortcut (e.g. on Mac
    # Cmd-symbol + A)
    def setText(self, text):
        QtGui.QLineEdit.setText(self, translateShortcutToOSNames(text))
        self._shortcut = text
    def text(self):
        return self._shortcut
    def clear(self):
        QtGui.QLineEdit.setText(self, '<enter key combination here>')
        self._shortcut = ''
            
    def focusInEvent(self, event):
        #self.clear()
        QtGui.QLineEdit.focusInEvent(self, event)
    
    def event(self,event):
        # Override event handler to enable catching the Tab key
        # If the event is a KeyPress or KeyRelease, handle it with
        # self.keyPressEvent or keyReleaseEvent
        if event.type()==event.KeyPress:
            self.keyPressEvent(event)
            return True #Mark as handled
        if event.type()==event.KeyRelease:
            self.keyReleaseEvent(event)
            return True #Mark as handled
        #Default: handle events as usual
        return QtGui.QLineEdit.event(self,event)
        
    def keyPressEvent(self, event):
        # get key codes
        key = event.key()
        nativekey = event.nativeVirtualKey()
        
        # try to get text
        if nativekey < 128 and sys.platform != 'darwin':
            text = chr(nativekey).upper()
        elif key<128:
            text = chr(key).upper()
        else:
            text = ''
        
        # do we know this specic key or this native key?
        if key in keymap:
            text = keymap[key]
        elif nativekey in self._nativeKeys:
            text = self._nativeKeys[nativekey]
        
        # apply!
        if text:
            storeNativeKey, text0 = True, text       
            if QtGui.qApp.keyboardModifiers() & k.AltModifier:
                text  = 'Alt+' + text
            if QtGui.qApp.keyboardModifiers() & k.ShiftModifier:
                text  = 'Shift+' + text
                storeNativeKey = False
            if QtGui.qApp.keyboardModifiers() & k.ControlModifier:
                text  = 'Ctrl+' + text
            if QtGui.qApp.keyboardModifiers() & k.MetaModifier:
                text  = 'Meta+' + text
            self.setText(text)
            if storeNativeKey and nativekey:
                # store native key if shift was not pressed.
                self._nativeKeys[nativekey] = text0
        
        # notify listeners
        self.textUpdate.emit()


class KeyMapEditDialog(QtGui.QDialog):
    """ The prompt that is shown when double clicking 
    a keymap in the tree. 
    It notifies the user when the entered shortcut is already used
    elsewhere and applies the shortcut (removing it elsewhere if
    required) when the apply button is pressed.
    """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle(translate("menu dialog", 'Edit shortcut mapping'))
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 400,140
        offset = 5
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*size2)
        
        self._label = QtGui.QLabel("", self)
        self._label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._label.resize(size[0]-20, 80)
        self._label.move(10,2)
        
        self._line = KeyMapLineEdit('', self)
        self._line.resize(size[0]-80, 20)
        self._line.move(10,90)
        
        self._clear = QtGui.QPushButton("Clear", self)
        self._clear.resize(50, 20)
        self._clear.move(size[0]-60,90)
        
        self._apply = QtGui.QPushButton("Apply", self)
        self._apply.resize(50, 20)
        self._apply.move(size[0]-120,120)
        
        self._cancel = QtGui.QPushButton("Cancel", self)
        self._cancel.resize(50, 20)
        self._cancel.move(size[0]-60,120)
        
        # callbacks
        self._line.textUpdate.connect(self.onEdit)
        self._clear.clicked.connect(self.onClear)
        self._apply.clicked.connect(self.onAccept)
        self._cancel.clicked.connect(self.close)
        
        # stuff to fill in later
        self._fullname = ''
        self._intro = ''
        self._isprimary = True
        
    def setFullName(self, fullname, isprimary):
        """ To be called right after initialization to let the user
        know what he's updating, and show the current shortcut for that
        in the line edit. """
        
        # store
        self._isprimary = isprimary
        self._fullname = fullname
        # create intro to show, and store + show it
        tmp = fullname.replace('__',' -> ').replace('_', ' ')
        primSec = ['secondary', 'primary'][int(isprimary)]
        self._intro = "Set the {} shortcut for:\n{}".format(primSec,tmp)
        self._label.setText(self._intro)
        # set initial value
        if fullname in iep.config.shortcuts:
            current = iep.config.shortcuts[fullname]
            if ',' not in current:
                current += ','
            current = current.split(',')
            self._line.setText( current[0] if isprimary else current[1] )
            
        
    def onClear(self):
        self._line.clear()
        self._line.setFocus()
    
    def onEdit(self):
        """ Test if already in use. """
        
        # init
        shortcut = self._line.text()
        if not shortcut:
            self._label.setText(self._intro)
            return
        
        for key in iep.config.shortcuts:
            # get shortcut and test whether it corresponds with what's pressed
            shortcuts = getShortcut(key)
            primSec = ''
            if shortcuts[0].lower() == shortcut.lower():
                primSec = 'primary'
            elif shortcuts[1].lower() == shortcut.lower():
                primSec = 'secondary'
            # if a correspondence, let the user know
            if primSec:
                tmp = "WARNING: combo already in use "
                tmp += "as "+primSec+" shortcut for:\n" 
                tmp += key.replace('__',' -> ').replace('_', ' ')
                self._label.setText(self._intro + '\n\n' + tmp)
                break
        else:
            self._label.setText(self._intro)
    
    
    def onAccept(self):
        shortcut = self._line.text()
        
        # remove shortcut if present elsewhere
        keys = [key for key in iep.config.shortcuts] # copy
        for key in keys:
            # get shortcut, test whether it corresponds with what's pressed
            shortcuts = getShortcut(key)
            tmp = list(shortcuts)
            needUpdate = False
            if shortcuts[0].lower() == shortcut.lower():
                tmp[0] = ''
                needUpdate = True
            if shortcuts[1].lower() == shortcut.lower():
                tmp[1] = ''
                needUpdate = True
            if needUpdate:
                tmp = ','.join(tmp)
                tmp = tmp.replace(' ','')
                if len(tmp)==1:
                    del iep.config.shortcuts[key]
                else:
                    iep.config.shortcuts[key] = tmp
        
        # insert shortcut
        if self._fullname:
            # get current and make list of size two
            if self._fullname in iep.config.shortcuts:
                current = list(getShortcut(self._fullname))
            else:
                current = ['', '']
            # update the list
            current[int(not self._isprimary)] = shortcut
            iep.config.shortcuts[self._fullname] = ','.join(current)
        
        # close
        self.close()
    

class KeymappingDialog(QtGui.QDialog):
    """ The main keymap dialog, it has tabs corresponding with the
    different menus and each tab has a tree representing the structure
    of these menus. The current shortcuts are displayed. 
    On double clicking on an item, the shortcut can be edited. """
    
    def __init__(self, *args):
        QtGui.QDialog.__init__(self, *args)
        
        # set title
        self.setWindowTitle(translate("menu dialog", 'Shortcut mappings'))
        self.setWindowIcon(iep.icon)
        
        # set size
        size = 600,400
        offset = 0
        size2 = size[0], size[1]+offset
        self.resize(*size2)
        self.setMaximumSize(*size2)
        self.setMinimumSize(*   size2)
        
        self.tab = CompactTabWidget(self, padding=(4,4,6,6))
        self.tab.resize(*size)
        self.tab.move(0,offset)
        self.tab.setMovable(False)
        
        # fill tab
        self._models = []
        self._trees = []
        for menu in iep.main.menuBar()._menus:
            # create treeview and model
            model = KeyMapModel()
            model.setRootMenu(menu)
            tree = QtGui.QTreeView(self.tab) 
            tree.setModel(model)
            # configure treeview
            tree.clicked.connect(self.onClickSelect)
            tree.doubleClicked.connect(self.onDoubleClick)
            tree.setColumnWidth(0,150)
            # append to lists
            self._models.append(model)
            self._trees.append(tree)
            self.tab.addTab(tree, menu.title())
        
        self.tab.currentChanged.connect(self.onTabSelect)

    
    def closeEvent(self, event):
        # update key setting
        iep.keyMapper.keyMappingChanged.emit()
        
        event.accept()
    
    def onTabSelect(self):
        pass
    
    
    def onClickSelect(self, index):
        # should we show a prompt?
        if index.column():
            self.popupItem(index.internalPointer(), index.column())
    
    
    def onDoubleClick(self, index):        
        if not index.column():
            self.popupItem(index.internalPointer())
    
    
    def popupItem(self, item, shortCutId=1):
        """ Popup the dialog to change the shortcut. """
        if isinstance(item, QtGui.QAction) and item.text():
            # create prompt dialog
            dlg = KeyMapEditDialog(self)
            dlg.setFullName( item.menuPath, shortCutId==1 )
            # show it
            dlg.exec_()
