
class Menuhelper:
    """ Menu helper class to transparantly and without duplicating code,
    automatically produces a nice menu.
    Still a work in progress. """ 
    
    def create(self):
        
        L = file()
        menu_file = QMenu()
        menu_file.triggered.connect(self.onTrigger)
        for callback in L:
            
            tmp = callback(None)
            shortcut = ''# test for key shortut
            menu_file.addAction(tmp[0], tmp[1], callback)
        
        
    def onTrigger(self, action):
        """ Called when an item is clicked. """
        if action.callback:
            action.callback(*action.args)
    
    def file(self, event=None):
        if event is None:
            # prepare list
            L = []
            L.append(self.file_new)
            L.append(self.file_open)
            L.append(self.file_close)
            return L
    
    def file_new(self, event=None):
        if event is None:
            return "New File", "Create a new file"
        
        iep.editors.newFile()
    
    
    def file_new(self, event=None):
        if event is None:
            return "Open File", "Open an existing file"
        
        iep.editors.openFile()
    
    
    def plugins(self):
        return ??
        
    
    def settings(self):
        pass # make list like file()
    
    def set_wrapText(self, action=None):
        if isinstance(action, Qaction):
            action.setText("Wrap text")
            action.setStatusTip("Wrap text to next line if it does not fit on screen")
            action.setCheckable(True)
            action.setChecked(iep.config.wrapText)
            return action
        
        # switch and apply
        iep.config.wrapText = not iep.config.wrapText
        for editor in iep.editors:
            editor.setWrapText(iep.config.wrapText) # or something similar
        
    
    def set_indentWidth(self, action=None):
        if action is None
            action = QMenu()
            action.setText("Default indent width")
            action.setStatusTip("The indentation width to apply to new files")
            action.addAction(..., 2)
            action.addAction(..., 3)
            action.addAction(..., 4)
            # added actions are checkable and one is checked
            return action
        
        # apply
        iep.config.indentWidth = action.value
    
    ##
    
    def set_indentWidth(self, value=None):
        if value is None
            item = VirtualItem()
            item.text = "Default indent width"
            item.tip = "The indentation width to apply to new files"
            item.values = ["2","3","4"]
            item.current = iep.config.indentWidth
            return item
        
        # apply
        iep.config.indentWidth = int(value)
    
    def set_wrapText(self, value):
        ...
            item.values = [True, False]
            item.current = iep.config.wrapText
    
    def file_new(self, value=None):
        if value is None:
            item = VirtualItem()
            item.text = "New File"
            item.tip = "Create a new file"
            item.value = True # can be given automatically when value not given
            return item
        
        # apply
        iep.editors.newFile()
        
    def plugins(self, value=None):
        
        if value is None:
            item = VirtualItem()
            item.text = "Plugins"
            item.tip = "Plugins are there to help you"
            item.values = []
            for plugin in plugins:
                tmp = VirtualItem()
                tmp.text = plugin.name
                tmp.tip = plugin.description
                tmp.values =[True, False]
                tmp.current = plugin in activePlugins
                item.values.append(tmp)
            return item
    