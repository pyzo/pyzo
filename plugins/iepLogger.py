
# iep imports will work, I guess because the plugins dir 
# is a package inside ieps dir...
from PyQt4 import QtCore, QtGui
import iep 
import sys

plugin_name = "Logger"
plugin_summary = "Logs messaged, warnings and errors within IEP"


class IepLogger(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        but = QtGui.QPushButton(self)
        but.setText('testing logger!')
#         
# #class Logger(wx.stc.StyledTextCtrl):
# class IepLogger(wx.TextCtrl):
#     """ A logging device. It reroutes stdout and stderr.
#     It has a timer so it flushes the written text every 200 ms.
#     This is to create a big speedup if a lot of small pieces of    
#     text are written (like when loading IEP and a lot of files 
#     are loaded)
#     """
#     
#     def __init__(self, parent ):        
#         wx.TextCtrl.__init__(self, parent, -1, 
#             style=wx.TE_MULTILINE | wx.TE_READONLY )    
#         #wx.stc.StyledTextCtrl.__init__(self,parent,-1)
#         
#         # store original
#         self._stdout = sys.stdout
#         self._stderr = sys.stderr
#         
#         # set output
#         sys.stdout = sys.stderr = self
#         
#         # to set it back
#         self.Bind(wx.EVT_WINDOW_DESTROY, self.SetBack)
#         
#         # buffer
#         self.buffer = []
#         
#         # root
#         self.root = iep.GetMainFrame(self)
#         
#         # start timer
#         self.timer = wx.Timer(self, wx.NewId())
#         self.Bind(wx.EVT_TIMER, self.FlushMe, self.timer)
#         self.timer.Start(200, wx.TIMER_CONTINUOUS)
#         
#         print "Logger started..."
# 
# 
#     def FlushMe(self, event=None):
#         if self.buffer:
#             text = "".join(self.buffer)
#             # append text on text ctlr
#             self.AppendText( text )            
#             # show latest message
#             stb = self.root.GetStatusBar()
#             if stb:
#                 text = text.replace("\n","\\n").rstrip('\\n')
#                 stb.SetStatusText(text, 2)
#             # clear
#             self.buffer = []
#             
#     def write(self, text):
#         if text:
#             self.buffer.append( text )
#         
#     def SetBack(self,event=None):
#         """We should call this somewere"""        
#         sys.stdout = self._stdout
#         sys.stderr = self._stderr
#         if event and hasattr(event,'Skip'):
#             event.Skip() # this is important
# 