""" Module logging
Functionality for logging and a logger shell.
"""

import sys, os, time
import code
import iep
from shell import BaseShell

# todo: enable logging to a file?

original_print = print
def print(*args, **kwargs):
    t = time.localtime()
    preamble = "{:02g}-{:02g}-{:04g} {:02g}:{:02g}:{:02g}: "
    preamble = preamble.format( t.tm_mday, t.tm_mon, t.tm_year, 
                                t.tm_hour, t.tm_min, t.tm_sec)
    args = [preamble] + list(args)
    original_print(*tuple(args),**kwargs)


def splitConsole(stdoutFun=None, stderrFun=None):
    """ splitConsole(stdoutFun=None, stderrFun=None)
    Splits the stdout and stderr streams. On each call
    to their write methods, in addition to the original
    write method being called, will call the given 
    functions.
    Returns the history of the console (combined stdout 
    and stderr).
    Used by the logger shell.
    """
    
    # Split stdout and stderr
    sys.stdout = OutputStreamSplitter(sys.stdout)
    sys.stderr = OutputStreamSplitter(sys.stderr)
    
    # Make them share their history
    sys.stderr._history = sys.stdout._history
    
    # Set defer functions
    if stdoutFun:
        sys.stdout._deferFunction = stdoutFun
    if stderrFun:
        sys.stderr._deferFunction = stderrFun
    
    # Return history 
    return ''.join(sys.stdout._history)


class OutputStreamSplitter:
    """ This class is used to replace stdout and stderr output
    streams. It defers the stream to the original and to
    a function that can be registered.
    Used by the logger shell.
    """
    
    def __init__(self, fileObject):
        
        # Init, copy properties if it was already a splitter
        if isinstance(fileObject, OutputStreamSplitter):
            self._original = fileObject._original
            self._history = fileObject._history
            self._deferFunction = fileObject._deferFunction
        else:
            self._original = fileObject
            self._history = []
            self._deferFunction = self.dummyDeferFunction
    
    def dummyDeferFunction(self, text):
        pass
    
    def write(self, text):
        """ Write method. """
        self._original.write(text)
        self._history.append(text)
        self._deferFunction(text)
    
    def flush(self):
        return self._original.flush()
    
    def closed(self):
        return self._original.closed()
    
    def close(self):
        return self._original.close()
    
    def encoding(self):
        return self._original.encoding()

# Split now, with no defering
splitConsole()


class LoggerShell(BaseShell):
    """ Shell that logs all messages produced by IEP. It also 
    allows to look inside IEP, which can be handy for debugging
    and developing.
    """
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)
        
        # apply style        
        self.setStyle('loggerShell')
        #self._reduceFontSizeToMatch80Columns = False
        
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
        
        # Goto end
        self.setPositionAndAnchor(self.length())
        
        # Create interpreter to run code        
        locals = {'iep':iep, 'sys':sys, 'os':os}
        self._interpreter = code.InteractiveConsole(locals, "<logger>")
    
    
    def executeCommand(self, command):
        """ Execute the command here! """
        # Use writeErr rather than sys.stdout.write. This prevents
        # the prompts to be logged by the history. Because if they
        # are, the text does not look good due to missing newlines
        # when loading the history.
        more = self._interpreter.push(command.rstrip('/n'))
        if more:
            self.writeErr(sys.ps2)
        else:            
            self.writeErr(sys.ps1)  
    
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
            names = eval(command, {}, self._interpreter.locals)
            aco.addNames(names)
        
        # Query list of names
        command = "dir({})".format(aco.name)
        names = eval(command, {}, self._interpreter.locals)
        aco.addNames(names)
        aco.finish()
