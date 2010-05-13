import wx, wx.stc
import iep 
import sys

plugin_name = "Interactive Help"
plugin_summary = "Shows help on an object when using up/down in autocomplete."

from wx.html import HtmlWindow

#class Logger(wx.stc.StyledTextCtrl):
class IepInteractiveHelp(wx.Panel):
    """ A logging device. It reroutes stdout and stderr.
    It has a timer so it flushes the written text every 200 ms.
    This is to create a big speedup if a lot of small pieces of    
    text are written (like when loading IEP and a lot of files 
    are loaded)
    """
    
    def __init__(self, parent ):        
        wx.Panel.__init__(self, parent, -1 )    
        
        # create html window
        self.window = HtmlWindow(self, -1)
        
        # create sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)        
        self.sizer.Add(self.window,1,wx.EXPAND)        
        
        # apply sizer
        self.SetSizer(self.sizer) # 1
        self.SetAutoLayout(True)  # 2
        self.Layout()             # 3 
        
        # init text
        text =  "Help information is queried from the current session<br />"\
                "when moving up/down in the autocompletion list<br />"\
                "and when double clicking on a name."                
        self.SetContent(text)
        
    def SetContent(self, text):
        self.window.SetPage(text)
    
    def Clear(self):
        self.window.SetPage("")
        
        