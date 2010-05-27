import os

os.chdir("..")

import wx
import iep

class IepFindInFiles(wx.Panel):
    def __init__(self, parent ):        
        wx.Panel.__init__(self, parent, -1)
        
        stext = wx.StaticText(self,-1)
        stext.SetLabel(str(os.getcwd()))
        wx.Slider(self)
    