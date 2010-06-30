
# iep imports will work, I guess because the plugins dir 
# is a package inside ieps dir...
import sys, os, code
from PyQt4 import QtCore, QtGui
import iep
from shell import BaseShell, splitConsole


plugin_name = "Logger"
plugin_summary = "Logs messaged, warnings and errors within IEP"



class LoggerShell(BaseShell):
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)
        
        # apply style        
        self.setStyle('loggerShell')
        
        # make sure sys has prompts
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        
        # Show welcome text
        moreBanner = "This is the IEP logger shell." 
        self.write("Python %s on %s - %s\n\n" %
                       (sys.version[:5], sys.platform, moreBanner))
        self.writeErr(sys.ps1)
        
        # Split console
        history = splitConsole(self.write, self.writeErr)
        self.write(history)
        
        # Create interpreter to run code        
        locals = {'iep':iep, 'sys':sys, 'os':os}
        self._interpreter = code.InteractiveConsole(locals, "<logger>")
        
        
    
    def executeCommand(self, command):
        """ Execute the command here! """
        more = self._interpreter.push(command.rstrip('/n'))
        if more:
            self.writeErr(sys.ps2)
        else:            
            self.writeErr(sys.ps1)


class IepLogger(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        self._sizer1 = QtGui.QVBoxLayout(self)
        self._shell = LoggerShell(self)
        self._sizer1.addWidget(self._shell, 1)
        
        self.setLayout(self._sizer1)
