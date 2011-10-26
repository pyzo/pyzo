# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


import sys, os, code
from PyQt4 import QtCore, QtGui
import iep
from iepcore.shell import BaseShell
from iepcore.iepLogging import splitConsole


tool_name = "Logger"
tool_summary = "Logs messages, warnings and errors within IEP."
 

class IepLogger(BaseShell):
    """ Shell that logs all messages produced by IEP. It also 
    allows to look inside IEP, which can be handy for debugging
    and developing.
    """
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)
        
        # apply style        
        #self.setStyle('loggerShell')
        
        # Create interpreter to run code        
        locals = {'iep':iep, 'sys':sys, 'os':os}
        self._interpreter = code.InteractiveConsole(locals, "<logger>")
        
        # Show welcome text
        moreBanner = "This is the IEP logger shell." 
        self.write("Python %s on %s - %s\n\n" %
                       (sys.version[:5], sys.platform, moreBanner))
        self.writeErr(sys.ps1)
        
        # Split console
        history = splitConsole(self.write, self.writeErr)
        self.write(history)
    
    
    def executeCommand(self, command):
        """ Execute the command here! """
        # Use writeErr rather than sys.stdout.write. This prevents
        # the prompts to be logged by the history. Because if they
        # are, the text does not look good due to missing newlines
        # when loading the history.
        more = self._interpreter.push(command.rstrip('/n'))
        if more:
            BaseShell.write(self, sys.ps2)
        else:            
            BaseShell.write(self, sys.ps1)  
    
    
    def writeErr(self, text):
        """ Overload so that when an error is printed, we can  
        insert a new prompt. """
        # Write normally
        BaseShell.write(self, text)
        # Goto end
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)
        
        
    # Note that I did not (yet) implement calltips
    
    def processAutoComp(self, aco):
        """ Processes an autocomp request using an AutoCompObject instance. 
        """
        
        # Try using buffer first
        if aco.tryUsingBuffer():
            return
        
        # Include buildins?
        if not aco.name:
            command = "__builtins__.keys()"
            try:
                names = eval(command, {}, self._interpreter.locals)
                aco.addNames(names)
            except Exception:
                pass
        
        # Query list of names
        command = "dir({})".format(aco.name)
        try:
            names = eval(command, {}, self._interpreter.locals)
            aco.addNames(names)
        except Exception:
            pass
        
        # Done
        aco.finish()
