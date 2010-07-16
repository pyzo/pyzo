""" Package PLugins of iep

A plugin consists of a module which contains a class. The id of 
a plugin is its module name made lower case. The module should 
contain a class corresponding to its id. We advise to follow the
common python style and start the class name with a capital 
letter, case does not matter for the plugin to work though.
For instance, plugin "ieplogger" is the class "IepLogger" found 
in module "iepLogger"

The module may contain the following extra variables (which should
be placed within the first 50 lines of code):

plugin_name - A readable name for the plugin (may contain spaces, 
will be shown in the tab)

plugin_summary - A single line short summary of the plugin. To be
displayed in the statusbar.
"""

# plugins I'd like:
# - logger
# - find in files
# - interactive help
# - workspace
# - source tree
# - snipet manager
# - file browser
# - pythonpath editor, startupfile editor (or as part of IEP?)

import os, sys, imp
from PyQt4 import QtCore, QtGui
import iep

ssdf = iep.ssdf


class PluginDockWidget(QtGui.QDockWidget):
    """ A dock widget that holds a plugin.
    It sets all settings, initializes the plugin widget, and notifies the
    plugin manager on closing.
    """
    
    def __init__(self, parent, pluginManager):
        QtGui.QDockWidget.__init__(self, parent)
        
        # Store stuff
        self._pluginManager = pluginManager
        
        # Allow docking anywhere, othwerise restoring state wont work properly
        
        # Set other settings
        self.setFeatures(   QtGui.QDockWidget.DockWidgetMovable |
                            QtGui.QDockWidget.DockWidgetClosable |
                            QtGui.QDockWidget.DockWidgetFloatable
                            #QtGui.QDockWidget.DockWidgetVerticalTitleBar
                            )
    
    
    def setPlugin(self, pluginId, pluginName, pluginClass):
        """ Set the plugin information. Call this right after
        initialization. """
        
        # Store id and set object name to enable saving/restoring state
        self._pluginId = pluginId
        self.setObjectName(pluginId)
        
        # Set name
        self.setWindowTitle(pluginName)
        
        # Create plugin widget
        self.reload(pluginClass)
    
    
    def closeEvent(self, event):
        if self._pluginManager:
            self._pluginManager.onPluginClose(self._pluginId)
            self._pluginManager = None
        event.accept()
    
    
    def reload(self, pluginClass):
        """ Reload the widget with a new widget class. """
        old = self.widget()
        new = pluginClass(iep.main)
        self.setWidget(new)
        if old:
            old.close()
    

class PluginDescription:
    """ Provides a description of a plugin and has a reference to
    the plugin dock instance if it is loaded.
    """
    
    def __init__(self, moduleName, name='', description=''):
        # Set names
        self.moduleName = moduleName
        self.id = moduleName.lower()
        if name:
            self.name = name
        else:
            self.name = self.id
        # Set description
        self.description = description
        # Init instance to None, will be set when loaded
        self.instance = None
    
    def menuLauncher(self, value):
        """ Function that is called by the menu whet this plugin is selected.
        """
        if value is None:
            return bool(self.instance)
            #return self.id in iep.pluginManager._activePlugins
        elif value:
            iep.pluginManager.loadPlugin(self.id)
        else:
            iep.pluginManager.closePlugin(self.id)


class PluginManager:
    """ Manages the plugins. """
    
    
    def __init__(self):
        
        # list of tuples: moduleName, plugin_name, plugin_summary
        self._pluginInfo = None
        self._activePlugins = {}
    
    
    def loadPluginInfo(self):
        """ (re)load the plugin information. 
        """
        
        # Get path
        plugindir = os.path.dirname( os.path.abspath(__file__) )
        
        # Get list of files, also when we're in a zip file.
        i = plugindir.find('.zip')
        if i>0:
            # Get list of files from zipfile
            plugindir = plugindir[:i+4]
            import zipfile
            z = zipfile.ZipFile(plugindir)
            pluginfiles = [os.path.split(i)[1] for i in z.namelist() 
                        if i.startswith('visvis') and i.count('functions')]
        else:
            # Get list of files from file system
            pluginfiles = os.listdir(plugindir)
        
        # Iterate over plugin modules
        newlist = []
        for file in pluginfiles:
            if file.startswith('__'):
                continue
            if file.endswith('.py'):            
                pluginModule = file[:-3]
                pluginName = ""
                pluginSummary = ""
                # read file to find name or summary
                linecount = 0
                for line in open(os.path.join(plugindir,file)):
                    linecount += 1
                    if linecount > 50:
                        break
                    if line.startswith("plugin_name"):
                        i = line.find("=")
                        if i<0: continue
                        line = line.rstrip("\n").rstrip("\r")      
                        line = line[i+1:].strip(" ")
                        pluginName = line.strip("'").strip('"')
                    elif line.startswith("plugin_summary"):
                        i = line.find("=")
                        if i<0: continue
                        line = line.rstrip("\n").rstrip("\r")
                        line = line[i+1:].strip(" ")
                        pluginSummary = line.strip("'").strip('"')
                    else:
                        pass
                
                # Add stuff
                tmp = PluginDescription(pluginModule, pluginName, pluginSummary)
                newlist.append(tmp)
        
        # Store and return
        self._pluginInfo = sorted( newlist, key=lambda x:x.id )
        self.updatePluginInstances()
        return self._pluginInfo
    
    
    def updatePluginInstances(self):
        """ Make plugin instances up to date, so that it can be seen what
        plugins are now active. """
        for pluginDes in self._pluginInfo:
            if pluginDes.id in self._activePlugins:
                pluginDes.instance = self._activePlugins[pluginDes.id]
            else:
                pluginDes.instance = None
    
    
    def getPluginInfo(self):
        """ Like loadPluginInfo(), but use buffered instance if available.
        """
        if self._pluginInfo is None:
            self.loadPluginInfo()
        return self._pluginInfo
    
    
    def getPluginClass(self, pluginId):
        """ Get the class of the plugin.
        It will import (and reload) the module and get the class.
        Some checks are performed, like whether the class inherits 
        from QWidget.
        Returns the class or None if failed...
        """
        
        # Make sure we have the info
        if self._pluginInfo is None:
            self.loadPluginInfo()
        
        # Get module name
        for pluginDes in self._pluginInfo:
            if pluginDes.id == pluginId:
                moduleName = pluginDes.moduleName
                break
        else:
            print("WARNING: could not find module for plugin", repr(pluginId))
            return None
            
        # Load module (and reload)
        try:
            mod = __import__("plugins."+moduleName, fromlist='NOn_ExIsTEnt_dUMmY' )
            imp.reload(mod)
        except ImportError:
            print("Invalid plugin (%s), module does not exist!" % (moduleName))
            return None
        
        # Is the expected class present?
        className = ""
        for member in dir(mod):
            if member.lower() == pluginId:
                className = member
                break
        else:       
            print("Invalid plugin, Classname must match module name!")
            return None
        
        # Does it inherit from QWidget?
        plug = mod.__dict__[className]
        if not (isinstance(plug,type) and issubclass(plug,QtGui.QWidget)):
            print("Invalid plugin, plugin class must inherit from QWidget!")
            return None
        
        # Succes!
        return plug
    
    
    def loadPlugin(self, pluginId):
        """ Load a plugin by creating a dock widget containing the plugin
        widget.
        """
        
        # A plugin id should always be lower case
        pluginId = pluginId.lower()
        
        # Get plugin class (returns None on failure)
        pluginClass = self.getPluginClass(pluginId)
        if pluginClass is None:
            return
        
        # Already loaded? reload!
        if pluginId in self._activePlugins:
            self._activePlugins[pluginId].reload(pluginClass)
            return
        
        # Obtain name from buffered list of names
        for pluginDes in self._pluginInfo:
            if pluginDes.id == pluginId:
                name = pluginDes.name
                break
        else:
            name = pluginId
        
        # Make sure there is a confi entry for this plugin
        if not hasattr(iep.config.plugins, pluginId):
            iep.config.plugins[pluginId] = ssdf.new()
        
        # Create dock widget and add in the main window
        dock = PluginDockWidget(iep.main, self)
        dock.setPlugin(pluginId, name, pluginClass)
        iep.main.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        
        # Add to list
        self._activePlugins[pluginId] = dock
        self.updatePluginInstances()
    
    
    def reloadPlugins(self):
        """ Reload all plugins. """
        for id in self.getLoadedPlugins():
            self.loadPlugin(id)
    
    
    def closePlugin(self, pluginId):
        """ Close the plugin with specified id.
        """
        if pluginId in self._activePlugins:
            dock = self._activePlugins[pluginId]
            dock.close()
    
    def getPlugin(self, pluginId):
        """ Get the plugin widget instance, or None
        if not available. """
        if pluginId in self._activePlugins:
            return self._activePlugins[pluginId].widget()
        else:
            return None
    
    def onPluginClose(self, pluginId):
        # Remove from dict
        self._activePlugins.pop(pluginId, None)
        # Set instance to None
        self.updatePluginInstances()
    
    
    def getLoadedPlugins(self):
        """ Get a list with id's of loaded plugins. """
        tmp = []
        for pluginDes in self._pluginInfo:
            if pluginDes.id in self._activePlugins:
                tmp.append(pluginDes.id)
        return tmp


# class PluginWindow(wx.Panel):
#     """ Window that contains two notebooks with plugins.
#     """
#     def __init__(self, parent, id=-1):
#         wx.Panel.__init__(self,parent,id)
#         
#         # border sizer in pixels
#         borderwidth = 10
#         
#         # create splitter and two notebooks
#         self.splitter2 = wx.SplitterWindow(self, wx.HORIZONTAL)
#         self.book1 = wx.Notebook(self.splitter2, style=wx.NB_TOP)
#         self.book2 = wx.Notebook(self.splitter2, style=wx.NB_TOP)
#         
#         # split splitter        
#         self.splitter2.SetWindowStyle(wx.SP_NOBORDER | wx.WANTS_CHARS)
#         self.splitter2.SplitHorizontally(self.book1,self.book2)
#         self.splitter2.SetMinimumPaneSize(100)
#         # sash position is set in the main
#         
#         # create sizer and blanc panel
#         self.panel = wx.Panel(self,-1)
#         self.panel.SetMinSize((borderwidth,1))
#         self.sizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.sizer.Add(self.panel,0,wx.EXPAND)
#         self.sizer.Add(self.splitter2,1,wx.EXPAND)
#         
#         # apply sizer
#         self.SetSizer(self.sizer) # 1
#         self.SetAutoLayout(True)  # 2
#         self.Layout()             # 3 
#         
#         # get root
#         self.root = iep.GetMainFrame(self)
#         
#         # init a var
#         self._pluginfiles = {}
#         
#         # hook to events
#         self.root.Bind(wx.EVT_MENU, self.OnMenuSelect)
#         self.root.Bind(wx.EVT_MENU, self.RefreshPlugins, id=ID_REFRESH)
#         
#         
#     def FillPluginMenu(self, menu):
#         """ fills the given menu with the available plugins        
#         """
#         # clear all items
#         items = menu.GetMenuItems()
#         for item in items:
#             menu.RemoveItem(item)
#             
#         # create list            
#         pluginfiles = getAvailablePlugins()
#         
#         # get plugins now in use
#         plugs1, plugs2 = [],[]
#         for i in range(self.book1.GetPageCount()):
#             id = self.book1.GetPage(i).__class__.__name__.lower()            
#             plugs1.append( id )
#         for i in range(self.book2.GetPageCount()):
#             id = self.book2.GetPage(i).__class__.__name__.lower()            
#             plugs2.append( id )            
#             
#         # and a new dict list for later reference.
#         # each entry (based on id) is a tuple (int, pluginModule)
#         # the int indicates which notebook
#         self._pluginfiles = {}
#         
#         # Refresh plugins        
#         menu.Append(ID_REFRESH, "Refresh plugins", 
#             "For plugin development: refresh all plugins.")
#         
#         menu.AppendSeparator()
#         
#         for file, name, summary in pluginfiles:
#             id = wx.NewId() # this is a wx id (integer)           
#             self._pluginfiles[id] = (0, file)
#             menustring = file.lower()
#             if name:
#                 #menustring = "%s (%s)" %(name,file.lower())
#                 menustring = name
#             summary = '%s: %s' % (file.lower(), summary)
#             # add to menu
#             menu.Append(id, menustring, summary, kind=wx.ITEM_CHECK)
#             if file.lower() in plugs1:
#                 menu.Check(id,True)
#                 
#         menu.AppendSeparator()
#         
#         for file, name, summary in pluginfiles:
#             id = wx.NewId()                
#             self._pluginfiles[id] = (1, file)
#             menustring = file.lower()
#             if name:
#                 #menustring = "%s (%s)" %(name,file.lower())
#                 menustring = name
#             summary = '%s: %s' % (file.lower(), summary)
#             # add to menu
#             menu.Append(id, menustring, summary, kind=wx.ITEM_CHECK)
#             if file.lower() in plugs2:
#                 menu.Check(id,True)
#         
#     
#     def OnMenuSelect(self,event):
#         """ Toggle plugin when selected from the menu """        
#         
#         # is the event ment for us?
#         if event.Id not in self._pluginfiles:
#             event.Skip()
#             return
#             
#         # gather info        
#         bookNr, moduleName = self._pluginfiles[event.Id]        
#         # load...
#         self.PluginToggle(bookNr, moduleName) 
#         
#     
#     def PluginToggle(self, bookNr, pluginId):
#         """ Load/toggle a plugin by its id name
#         Remove plugin if it is there...
#         """
#         if not pluginId:
#             return
#         
#         # make lowercase just to be sure
#         pluginId = pluginId.lower()
#         
#         # gather info        
#         Plug = getPlugin( pluginId )
#         book = [self.book1,self.book2][bookNr]
#         if not Plug:
#             return  # fail
#         
#         # remove any plugins currently in use
#         removedFrom = []
#         for i in range(self.book1.GetPageCount()-1,-1,-1):
#             page = self.book1.GetPage(i)
#             id = page.__class__.__name__.lower()
#             if pluginId == id:                
#                 self.book1.RemovePage(i)
#                 page.Destroy()
#                 removedFrom.append(0)
#         for i in range(self.book2.GetPageCount()-1,-1,-1):
#             page = self.book2.GetPage(i)
#             id = page.__class__.__name__.lower()
#             if pluginId == id:                
#                 self.book2.RemovePage(i)
#                 page.Destroy()
#                 removedFrom.append(1)
#         
#         # create plugin if we must
#         if not bookNr in removedFrom:
#             plug = Plug(book)
#             plugMod = sys.modules[ plug.__module__ ]
#             name = pluginId
#             if hasattr(plugMod, 'plugin_name'):
#                 name = plugMod.plugin_name            
#             book.AddPage(plug,name,True)
#             
#         # refresh
#         self.book1.Refresh()
#         self.book2.Refresh()
#         
#         
#     def ClearPlugins(self):
#         "Clear all plugins"
#         for i in range(self.book1.GetPageCount()-1,-1,-1):
#             page = self.book1.GetPage(i)
#             self.book1.RemovePage(i)
#             page.Destroy()
#         for i in range(self.book2.GetPageCount()-1,-1,-1):
#             page = self.book2.GetPage(i)
#             self.book2.RemovePage(i)
#             page.Destroy()
#         
# 
#     def LoadPluginsFromConfig(self):
#         "Load the previous plugins from the config file"
#         # clear first
#         self.ClearPlugins()
#         # get plugins
#         top = [i for i in iep.config.plugins.top]
#         bot = [i for i in iep.config.plugins.bottom]    
#         if not top: top = ['']
#         if not bot: bot = ['']
#         # get selected plugins (last in the list)
#         topSelected = top.pop()
#         if not topSelected in top:
#             top.append(topSelected)
#         botSelected = bot.pop()
#         if not botSelected in bot:
#             bot.append(botSelected)
#         # load plugins
#         for id in top:
#             self.PluginToggle(0,id)
#         for id in bot:
#             self.PluginToggle(1,id)
#         # select the ones
#         self.SelectPluginWindow(topSelected)
#         self.SelectPluginWindow(botSelected)
#         
#         self.Refresh()
#         self.book1.Refresh()
#         self.book2.Refresh()
#         
# 
#     def SavePluginsToConfig(self):
#         "Save the current plugins from the config file"
#          # get lists of plugins
#         plugs_top, plugs_bot = [],[]
#         for i in range(self.book1.GetPageCount()):
#             page = self.book1.GetPage(i)
#             plugs_top.append( page.__class__.__name__.lower() )
#         for i in range(self.book2.GetPageCount()):
#             page = self.book2.GetPage(i)
#             plugs_bot.append( page.__class__.__name__.lower() )
#         # add selected to the list
#         topSelected = self.book1.GetCurrentPage()
#         botSelected = self.book2.GetCurrentPage()
#         if topSelected:
#             plugs_top.append( topSelected.__class__.__name__.lower() )        
#         if botSelected:
#             plugs_bot.append( botSelected.__class__.__name__.lower() )
#         # store
#         iep.config.plugins.top = plugs_top
#         iep.config.plugins.bottom = plugs_bot
#         
#         
#     def RefreshPlugins(self, event=None):
#         " Remove all plugins and put them back"
#         self.SavePluginsToConfig()
#         self.ClearPlugins()
#         self.LoadPluginsFromConfig()
#         
#           
#     def SelectPluginWindow(self, id):
#         """ Select this plugin, does nothing
#         if the plugin is not shown """
#         if not id:
#             return
#         for i in range(self.book1.GetPageCount()):
#             page = self.book1.GetPage(i) 
#             id2 = page.__class__.__name__.lower()
#             if id == id2:
#                 self.book1.SetSelection(i)    
#         for i in range(self.book2.GetPageCount()):
#             page = self.book2.GetPage(i) 
#             id2 = page.__class__.__name__.lower()
#             if id == id2:
#                 self.book2.SetSelection(i)
#         
#         
#     def GetPluginWindow(self, pluginId):
#         """ Get the window of the given plugin.
#         Returns None if it is not loaded
#         """
#         pluginId = pluginId.lower()
#         window = None        
#         for i in range(self.book1.GetPageCount()):
#             page = self.book1.GetPage(i) 
#             id = page.__class__.__name__.lower()
#             if pluginId == id:
#                 window = page
#         for i in range(self.book2.GetPageCount()):
#             page = self.book2.GetPage(i) 
#             id = page.__class__.__name__.lower()
#             if pluginId == id:
#                 window = page
#         return window
        
        
    