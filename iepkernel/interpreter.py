# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module iepRemote2

Implements the IEP interpreter and the introspection thread.
Also GUI hijacking is defined here. This code works on all* python versions.
*: Well, at least from 2.4 and up (including py3k).

Note that this module delibirately has a name that is very unlikely to 
occur in any othe packages to prevent import clashes.

"""

import os, sys, time
import struct
from codeop import CommandCompiler
import traceback
import inspect # Must be in this namespace
import yoton
from iepkernel import guiintegration
from iepkernel.magic import Magician

# Init last traceback information
sys.last_type = None
sys.last_value = None
sys.last_traceback = None

# Set Python version as a float and get some names
PYTHON_VERSION = sys.version_info[0] + sys.version_info[1]/10.0
if PYTHON_VERSION < 3:
    ustr = unicode
    bstr = str
else:
    ustr = str
    bstr = bytes


class IepInterpreter:
    """ Closely emulate the interactive Python console.
    Simular working as code.InteractiveConsole. Some code was copied, but
    the following things are changed:
    - prompts are printed in the err stream, like the default interpreter does
    - uses an asynchronous read using the yoton interface
    - support for hijacking GUI toolkits
    - can run large pieces of code
    - support post mortem debugging
    """
    
    def __init__(self, locals, filename="<console>"):
        
        # Init variables for locals and globals (globals only for debugging)
        self.locals = locals
        self.globals = None
        
        # Store filename
        self.filename = filename
        
        # Store ref of locals that is our main
        self._main_locals = locals
        
        # Information for debugging. If self._dbFrames, we're in debug mode
        # _dbFrameIndex starts from 1 
        self._dbFrames = []
        self._dbFrameIndex = 0
        self._dbFrameName = ''
        
        # Init datase to store source code that we execute
        self._codeCollection = ExecutedSourceCollection()
        
        # Init buffer to deal with multi-line command in the shell
        self.buffer = []
        
        # Create compiler
        self._compile = CommandCompiler()
        
        
        # Define prompts
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
    
    
    ## Base of interpreter
    
    
    def interact(self):    
        """ Interact! (start the mainloop)
        """
        
        # Reset debug status to
        self.writeStatus()
        
        # Get startup info
        while sys._yoton_context._stat_startup.recv() is None:
            time.sleep(0.02)
        startup_info = sys._yoton_context._stat_startup.recv()
        
        
        # Write Python banner
        NBITS = 8 * struct.calcsize("P")
        platform = sys.platform
        if platform.startswith('win'):
            platform = 'Windows'
        platform = '%s (%i bits)' % (platform, NBITS) 
        sys.stdout.write("Python %s on %s.\n" %
            (sys.version.split('[')[0].rstrip(), platform))
        
        # Integrate event loop of GUI toolkit
        self.guiApp = None
        guiName = startup_info['gui']
        guiError = ''
        try:
            if guiName in ['', 'none', 'None']:
                pass
            elif guiName == 'tk':
                self.guiApp = guiintegration.Hijacked_tk()
            elif guiName == 'wx':
                self.guiApp = guiintegration.Hijacked_wx()
            elif guiName == 'qt4':
                self.guiApp = guiintegration.Hijacked_qt4()
            elif guiName == 'fltk':
                self.guiApp = guiintegration.Hijacked_fltk()
            elif guiName == 'gtk':
                self.guiApp = guiintegration.Hijacked_gtk()
            else:
                guiError = 'Unkown gui: %s' % guiName
        except Exception: # Catch any error
            # Get exception info (we do it using sys.exc_info() because
            # we cannot catch the exception in a version independent way.
            type, value, tb = sys.exc_info()
            tb = None
            guiError = 'Failed to integrate event loop for %s: %s' % (
                guiName.upper(), str(value))
        
        # Write IEP part of banner (including what GUI loop is integrated)
        if True:
            iepBanner = 'This is the IEP interpreter'
        if guiError:
            iepBanner += '. ' + guiError + '\n'
        elif self.guiApp:
            iepBanner += ' with integrated event loop for ' 
            iepBanner += guiName.upper() + '.\n'
        else:
            iepBanner += '.\n'
        sys.stdout.write(iepBanner)
        
        # Remove "THIS" directory from the PYTHONPATH
        # to prevent unwanted imports
        thisPath = os.getcwd()
        while thisPath in sys.path:
            sys.path.remove(thisPath)
        projectPath = startup_info['projectPath']
        if projectPath:
            sys.stdout.write('Prepending the project path %r to sys.path\n' % 
                projectPath)
            #Actual prepending is done below, to put it before the script path
        
        # Write tips message
        sys.stdout.write('Type "help" for help, ' + 
                            'type "?" for a list of *magic* commands.\n')
        
        # Get whether we should (and can) run as script
        scriptFilename = startup_info['scriptFile']
        if scriptFilename:
            if not os.path.isfile(scriptFilename):
                sys.stdout.write('Invalid script file: "'+scriptFilename+'"\n')
                scriptFilename = None
        
        # Init script to run on startup
        scriptToRunOnStartup = None
        
        if scriptFilename:
            # RUN AS SCRIPT
            
            # Set __file__  (note that __name__ is already '__main__')
            self.locals['__file__'] = scriptFilename
            # Set command line arguments
            sys.argv[:] = []
            sys.argv.append(scriptFilename)
            # Insert script directory to path
            theDir = os.path.abspath( os.path.dirname(scriptFilename) )
            if theDir not in sys.path:
                sys.path.insert(0, theDir)
            if projectPath is not None:
                sys.path.insert(0,projectPath)
            
            # Go to script dir
            os.chdir( os.path.dirname(scriptFilename) )
            
            # Notify the running of the script
            sys.stdout.write('[Running script: "'+scriptFilename+'"]\n')
            
            # Run script
            scriptToRunOnStartup = scriptFilename
        
        else:
            # RUN INTERACTIVELY
            
            # No __file__ (note that __name__ is already '__main__')
            self.locals.pop('__file__','')
            # Remove all command line arguments, set first to empty string
            sys.argv[:] = []
            sys.argv.append('')
            # Insert current directory to path
            sys.path.insert(0, '')
            if projectPath:
                sys.path.insert(0,projectPath)
                
            # Go to start dir
            startDir = startup_info['startDir']
            if startDir and os.path.isdir(startDir):
                os.chdir(startDir)
            else:
                os.chdir(os.path.expanduser('~')) # home dir 
            
            # Run startup script (if set)
            filename = startup_info['startupScript']
            if filename and os.path.isfile(filename):
                scriptToRunOnStartup = filename
        
        # Get channels
        ctrl_command = sys._yoton_context._ctrl_command
        ctrl_code = sys._yoton_context._ctrl_code
        strm_echo = sys._yoton_context._strm_echo
        strm_prompt = sys._yoton_context._strm_prompt
        stat_interpreter = sys._yoton_context._stat_interpreter
        
        
        # ENTER MAIN LOOP
        magician = Magician()
        guitime = time.time()
        more = 0
        self.newPrompt = True
        while True:
            try:
                
                # Run startup script inside the loop (only the first time)
                # so that keyboard interrupt will work
                if scriptToRunOnStartup:
                    stat_interpreter.send('Busy') 
                    scriptToRunOnStartup, tmp = None, scriptToRunOnStartup
                    self.runfile(tmp)
                
                # Set status and prompt?
                # Prompt is allowed to be an object with __str__ method
                if self.newPrompt:
                    self.newPrompt = False
                    # Write prompt
                    preamble = ''
                    if self._dbFrames:
                        preamble = '('+self._dbFrameName+')'
                    if more:
                        strm_prompt.send(preamble+str(sys.ps2))
                    else:
                        strm_prompt.send(preamble+str(sys.ps1))
                    # Notify ready state
                    stat_interpreter.send('Ready')
                
                # Wait for a bit at each round
                time.sleep(0.05) # 50 ms
                
                # Are we still connected?
                if sys.stdin.closed:
                    # Stop all deamon threads (or we wont really stop in <2.5s)
                    self.introspector.set_mode('off')
                    # Do not stop yoton context, because somehow this can 
                    # cause the exit to hang
                    #sys._yoton_context.close()
                    # Exit from main loop
                    break
                
                # Get channel to take a message from
                ch = yoton.select_sub_channel(ctrl_command, ctrl_code)
                
                if ch is None:
                    pass # No messages waiting
                
                elif ch is ctrl_command:
                    # Read command 
                    line1 = ctrl_command.recv(False) # Command
                    if line1:
                        # Convert command
                        line2, line3 = magician.convert_command(line1)
                        # Notify what we're doing
                        strm_echo.send(line2)
                        stat_interpreter.send('Busy')
                        self.newPrompt = True
                        # Execute actual code
                        if line3:
                            more = self.push(line3)
                        else:
                            more = False
                            self.resetbuffer()
                
                elif ch is ctrl_code:
                    # Read larger block of code (dict)
                    msg = ctrl_code.recv(False)
                    if msg:
                        # Notify what we're doing
                        # (runlargecode() sends on stdin-echo)
                        stat_interpreter.send('Busy')
                        self.newPrompt = True
                        # Execute code
                        self.runlargecode(msg)
                        # Reset more stuff
                        self.resetbuffer()
                        more = False
                
                else:
                    # This should not happen, but if it does, just flush!
                    ch.recv(False)
                
                # Keep GUI toolkit up to date
                if self.guiApp and time.time() - guitime > 0.019:
                    self.guiApp.processEvents()
                    guitime = time.time()
            
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0
            except TypeError:
                # For some reason, when wx is hijacked, keyboard interrupts
                # result in a TypeError.
                # I tried to find the source, but did not find it. If anyone
                # has an idea, please e-mail me!
                if guiName == 'wx':
                    self.write("\nKeyboard Interrupt\n") # space to see difference
                    self.resetbuffer()
                    more = 0
            except SystemExit:
                # Close socket nicely
                # sys._yoton_context.close() # will hang the exit in py3k
                # Exit from interpreter
                return
    
    
    def resetbuffer(self):
        """Reset the input buffer."""
        self.buffer = []
    
    
    def push(self, line):
        """Push a line to the interpreter.
        
        The line should not have a trailing newline; it may have
        internal newlines.  The line is appended to a buffer and the
        interpreter's runsource() method is called with the
        concatenated contents of the buffer as source.  If this
        indicates that the command was executed or invalid, the buffer
        is reset; otherwise, the command is incomplete, and the buffer
        is left as it was after the line was appended.  The return
        value is 1 if more input is required, 0 if the line was dealt
        with in some way (this is the same as runsource()).
        
        """
        self.buffer.append(line)
        source = "\n".join(self.buffer)
        more = self.runsource(source, self.filename)
        if not more:
            self.resetbuffer()
        return more
    
    
    def runsource(self, source, filename="<input>", symbol="single"):
        """Compile and run some source in the interpreter.
        
        Arguments are as for compile_command().
        
        One several things can happen:
        
        1) The input is incorrect; compile_command() raised an
        exception (SyntaxError or OverflowError).  A syntax traceback
        will be printed by calling the showsyntaxerror() method.
        
        2) The input is incomplete, and more input is required;
        compile_command() returned None.  Nothing happens.
        
        3) The input is complete; compile_command() returned a code
        object.  The code is executed by calling self.runcode() (which
        also handles run-time exceptions, except for SystemExit).
        
        The return value is True in case 2, False in the other cases (unless
        an exception is raised).  The return value can be used to
        decide whether to use sys.ps1 or sys.ps2 to prompt the next
        line.
        
        """
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            self.showsyntaxerror(filename)
            return False
        
        if code is None:
            # Case 2
            return True
        
        # Case 3
        self.runcode(code)
        return False
    
    
    def runcode(self, code):
        """Execute a code object.
        
        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.
        
        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.
        
        The globals variable is used when in debug mode.
        """
        try:
            if self._dbFrames:
                exec(code, self.globals, self.locals)
            else:
                exec(code, self.locals)
        except Exception:
            time.sleep(0.2) # Give stdout some time to send data
            self.showtraceback()
    
    
    def runlargecode(self, msg):
        """ To execute larger pieces of code. """
        
        # Get information
        source, fname, lineno = msg['source'], msg['fname'], msg['lineno']
        source += '\n'
        
        # Construct notification message
        lineno1 = lineno + 1
        lineno2 = lineno + source.count('\n')
        fname_show = fname
        if not fname.startswith('<'):
            fname_show = os.path.split(fname)[1]
        if lineno1 == lineno2:
            runtext = '(executing line %i of "%s")\n' % (lineno1, fname_show)
        else:
            runtext = '(executing lines %i to %i of "%s")\n' % (
                                                lineno1, lineno2, fname_show)
        # Notify IDE
        sys._yoton_context._strm_echo.send(runtext)
        
        # Put the line number in the filename (if necessary)
        # Note that we could store the line offset in the _codeCollection,
        # but then we cannot retrieve it for syntax errors.
        if lineno:
            fname = "%s+%i" % (fname, lineno)
        
        # Try compiling the source
        code = None
        try:            
            # Compile
            code = self.compile(source, fname, "exec")          
            
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(fname)
            return
        
        if code:
            # Store the source using the (id of the) code object as a key
            self._codeCollection.storeSource(code, source)
            # Execute the code
            self.runcode(code)
        else:
            # Incomplete code
            self.write('Could not run code because it is incomplete.\n')
    
    
    def runfile(self, fname):
        """  To execute the startup script. """ 
        
        # Get text (make sure it ends with a newline)
        try:
            source = open(fname, 'rb').read().decode('UTF-8')
        except Exception:
            sys.stdout.write('Could not read script (decoding using UTF-8): "' + fname + '"\n')
            return
        try:
            source = source.replace('\r\n', '\n').replace('\r','\n')
            if source[-1] != '\n':
                source += '\n'
        except Exception:        
            sys.stdout.write('Could not execute script: "' + fname + '"\n')
            return
        
        # Try compiling the source
        code = None
        try:            
            # Compile
            code = self.compile(source, fname, "exec")
        except (OverflowError, SyntaxError, ValueError):
            time.sleep(0.2) # Give stdout time to be send
            self.showsyntaxerror(fname)
            return
        
        if code:
            # Store the source using the (id of the) code object as a key
            self._codeCollection.storeSource(code, source)
            # Execute the code
            self.runcode(code)
        else:
            # Incomplete code
            self.write('Could not run code because it is incomplete.\n')
    
    ## Misc
    
    
    def compile(self, source, filename, mode, *args, **kwargs):
        """ Compile source code.
        Will mangle coding definitions on first two lines. 
        
        * This method should be called with Unicode sources.
        * Source newlines should consist only of LF characters.
        """
        
        # This method solves IEP issue 22

        # Split in first two lines and the rest
        parts = source.split('\n', 2)
        
        # Replace any coding definitions
        ci = 'coding is'
        contained_coding = False
        for i in range(len(parts)-1):
            tmp = parts[i]
            if tmp and tmp[0] == '#' and 'coding' in tmp:
                contained_coding = True
                parts[i] = tmp.replace('coding=', ci).replace('coding:', ci)
        
        # Combine parts again (if necessary)
        if contained_coding:
            source = '\n'.join(parts)
        
        # Convert filename to UTF-8 if Python version < 3
        if PYTHON_VERSION < 3:
            filename = filename.encode('utf-8')
        
        # Compile
        return self._compile(source, filename, mode, *args, **kwargs)
    
    
    ## Writing and error handling
    
    
    def write(self, text):
        """ Write errors and prompts. """
        sys.stderr.write( text )
    
    
    def writeStatus(self):
        """ Write the status when in ready state.
        Writes STATE to Ready or Debug and writes DEBUG (info).
        """
        
        # Collect frames info
        frames = []
        for f in self._dbFrames:
            # Get fname and lineno, and correct if required
            fname, lineno = f.f_code.co_filename, f.f_lineno
            fname, lineno = self.correctFilenameAndLineno(fname, lineno)
            if not fname.startswith('<'):
                fname2 = os.path.abspath(fname)
                if os.path.isfile(fname2):
                    fname = fname2
            # Build string
            text = 'File "%s", line %i, in %s' % (
                                    fname, lineno, f.f_code.co_name)
            frames.append(text)
        
        # Send info object
        state = {'index': self._dbFrameIndex, 'frames': frames}
        sys._yoton_context._stat_debug.send(state)
    
    
    def showsyntaxerror(self, filename=None):
        """Display the syntax error that just occurred.
        This doesn't display a stack trace because there isn't one.        
        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).
        
        IEP version: support to display the right line number,
        see doc of showtraceback for details.        
        """
        
        # Get info (do not store)
        type, value, tb = sys.exc_info()
        tb = None
        
        # Work hard to stuff the correct filename in the exception
        if filename and type is SyntaxError:
            try:
                # unpack information
                msg, (dummy_filename, lineno, offset, line) = value
                # correct line-number
                fname, lineno = self.correctFilenameAndLineno(filename, lineno)
            except:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (fname, lineno, offset, line))
                sys.last_value = value
        
        # Show syntax error 
        strList = traceback.format_exception_only(type, value)
        for s in strList:
            self.write(s)
    
    
    def showtraceback(self, useLastTraceback=False):
        """Display the exception that just occurred.
        We remove the first stack item because it is our own code.
        The output is written by self.write(), below.
        
        In the IEP version, before executing a block of code,
        the filename is modified by appending " [x]". Where x is
        the index in a list that we keep, of tuples 
        (sourcecode, filename, lineno). 
        
        Here, showing the traceback, we check if we see such [x], 
        and if so, we extract the line of code where it went wrong,
        and correct the lineno, so it will point at the right line
        in the editor if part of a file was executed. When the file
        was modified since the part in question was executed, the
        fileno might deviate, but the line of code shown shall 
        always be correct...
        """
        # Traceback info:
        # tb_next -> go down the trace
        # tb_frame -> get the stack frame
        # tb_lineno -> where it went wrong
        #
        # Frame info:
        # f_back -> go up (towards caller)
        # f_code -> code object
        # f_locals -> we can execute code here when PM debugging
        # f_globals
        # f_trace -> (can be None) function for debugging? (
        #
        # The traceback module is used to obtain prints from the
        # traceback.
        
        try:
            if useLastTraceback:
                # Get traceback info from buffered
                type = sys.last_type
                value = sys.last_value
                tb = sys.last_traceback
            else:
                # Get exception information and remove first, since that's us
                type, value, tb = sys.exc_info()
                tb = tb.tb_next
                
                # Store for debugging, but only store if not in debug mode
                if not self._dbFrames:
                    sys.last_type = type
                    sys.last_value = value
                    sys.last_traceback = tb
            
            # Get tpraceback to correct all the line numbers
            # tblist = list  of (filename, line-number, function-name, text)
            tblist = traceback.extract_tb(tb)
            
            # Get frames
            frames = []
            while tb:
                frames.append(tb.tb_frame)
                tb = tb.tb_next
            frames.pop(0)
            
            # Walk through the list
            for i in range(len(tblist)):
                tbInfo = tblist[i]                
                # Get filename and line number, init example
                fname, lineno = self.correctFilenameAndLineno(tbInfo[0], tbInfo[1])
                if not isinstance(fname, ustr):
                    fname = fname.decode('utf-8')
                example = tbInfo[3]
                # Get source (if available) and split lines
                source = None
                if i < len(frames):
                    source = self._codeCollection.getSource(frames[i].f_code)
                if source:
                    source = source.splitlines()                
                    # Obtain source from example and select line                    
                    try:
                        example = source[ tbInfo[1]-1 ]
                    except IndexError:
                        pass
                # Reset info
                tblist[i] = (fname, lineno, tbInfo[2], example)
            
            # Format list
            strList = traceback.format_list(tblist)
            if strList:
                strList.insert(0, "Traceback (most recent call last):\n")
            strList.extend( traceback.format_exception_only(type, value) )
            
            # Write traceback
            for s in strList:
                self.write(s)
            
            # Clean up (we cannot combine except and finally in Python <2.5
            tb = None
            frames = None
        
        except Exception:
            self.write('An error occured, but could not write traceback.\n')
            tb = None
            frames = None
    
    
    def correctFilenameAndLineno(self, fname, lineno):
        """ Given a filename and lineno, this function returns
        a modified (if necessary) version of the two. 
        As example:
        "foo.py+7", 22  -> "foo.py", 29
        """
        j = fname.find('+')
        if j>0:
            try:
                lineno += int(fname[j+1:])
                fname = fname[:j]
            except ValueError:
                pass
        return fname, lineno


class ExecutedSourceCollection(dict):
    """ Stores the source of executed pieces of code, so that the right 
    traceback can be reproduced when an error occurs.
    The codeObject produced by compiling the source is used as a 
    reference.
    """
    def _getId(self, codeObject):
        id_ = str(id(codeObject)) + '_' + codeObject.co_filename
    def storeSource(self, codeObject, source):
        self[self._getId(codeObject)] = source
    def getSource(self, codeObject):
        return self.get(self._getId(codeObject), '')
