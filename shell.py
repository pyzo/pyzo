# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" Module shell

Defines the shell to be used in IEP.
This is done in a few inheritance steps:
  - BaseShell inherits BaseTextCtrl and adds the typical shell behaviour.    
  - PythonShell makes it specific to Python.
This module also implements ways to communicate with the shell and to run
code in it.

"""

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
import os, sys, time, subprocess
import channels
import iep
from baseTextCtrl import BaseTextCtrl
from iepLogging import print

# todo: color stderr red and prompt blue, and input text Python!



class BaseShell(BaseTextCtrl):
    """ The BaseShell implements functionality to make a generic shell.
    """

    
    def __init__(self, parent):
        BaseTextCtrl.__init__(self, parent)
        
        self.setUndoRedoEnabled(False)
#         # Tweak settings specific for shell
#         self.setIndentationGuides(False)
#         self.setMarginWidth(1,3)
#         self.setWrapMode(self.WrapCharacter)
#         self.setMarginLineNumbers(1,False)
#         self.setEdgeMode(self.EDGE_LINE)
#         self.setEdgeColumn(80)
#         self.setHighlightCurrentLine(False)
#         self.setEolMode(self.SC_EOL_LF)
#         
#         # Disable specif editing commands
#         ctrl, shift = self.SCMOD_CTRL<<16, self.SCMOD_SHIFT<<16
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('D')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('L')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('L')+ ctrl+shift)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('T')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('T')+ ctrl+shift)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('U')+ ctrl)
#         self.SendScintilla(self.SCI_CLEARCMDKEY, ord('U')+ ctrl+shift)
        
#         # Set shortcut
#         keyseq = QtGui.QKeySequence('Ctrl+C')
#         self._interruptShortcut = QtGui.QShortcut(keyseq, self)
#         self._interruptShortcut.setContext(QtCore.Qt.WidgetShortcut)
#         self._interruptShortcut.activated.connect(self.interrupt2)
#         self._interruptShortcut.activatedAmbiguously.connect(self.interrupt2)
        
        # variables we need
        self._more = False
        self._promptPos1 = 0
        self._promptPos2 = 0
        self.stdoutCursor = self.textCursor() #Stays at the place where stdout is printed
        self.lineBeginCursor = self.textCursor() #Stays at the beginning of the edit line
        
        # When inserting/removing text at the edit line (thus also while typing)
        # keep the lineBeginCursor at its place. Only when text is written before
        # the lineBeginCursor (i.e. in write and writeErr), this flag is
        # temporarily set to False
        self.lineBeginCursor.setKeepPositionOnInsert(True)
        
        
        # Create the command history.  Commands are added into the
        # front of the list (ie. at index 0) as they are entered.
        # self.+historyIndex is the current position in the history; it
        # gets incremented as you retrieve the previous command,
        # decremented as you retrieve the next, and reset when you hit
        # Enter.  self._historyIndex == -1 means you're on the current
        # command, not in the history.
        self._history = []
        self._historyIndex = -1
        self._historyNeedle = None # None means none, "" means look in all
        self._historyStep = 0
        
        # Set minimum width so 80 lines do fit in smallest font size
        self.setMinimumWidth(200)
        
        # apply style
        # TODO: self.setStyle('')
    


    def resizeEvent(self, event):
        """ When resizing the fontsize nust be kept right. """
        BaseTextCtrl.resizeEvent(self, event)        
        self.updateFontSizeToMatch80Columns()
    
    
    def mousePressEvent(self, event):
        """ Disable right MB and middle MB (which pastes by default). """
        if event.button() != QtCore.Qt.MidButton:
            BaseTextCtrl.mousePressEvent(self, event)
    
    def contextMenuEvent(self, event):
        """ Do not show context menu. """
        pass
    
    
    def updateWidgetSizeToMatch80Columns(self):
        """ updateWidgetSizeToMatch80Columns()
        (not used)
        """
        
        # Get size it should be (but font needs to be monospaced!)
        w = self.textWidth(32, "-"*80)
        w += 21 # add scrollbar and margin
        
        # fix the width
        self.setMinimumWidth(w)
    
    
    def updateFontSizeToMatch80Columns(self, event=None):
        """ updateFontSizeToMatch80Columns()
        Tries to conform to the correct font size as dictated by
        the style and zooming, but decreases the size as necessary
        to fit 80 columns on screen.
        """
        return #TODO: re-implement
        # Are we hidden?
        if not self.isVisible():
            return
        
        # Init zooming to users choice
        zoom = iep.config.view.zoom
        self.zoomTo(zoom)
        
        # Should we do this?
        if not iep.config.settings.shellFit80:
            return
        
        # Init variables
        width = self.width()
        w = width*2
        
        # Decrease size untill 80 columns fits
        while w > width:
            
            # Get size it should be (but font needs to be monospaced!)
            w = self.textWidth(32, "-"*80)
            w += 26 # add scrollbar and margin
            
            # zoom out if necessary
            if w > width:
                zoom -= 1
                self.zoomTo(zoom)
            
            # impose lower limit
            if zoom < -10:
                break
    
    def onAutoComplete(self,text):
        #Keep the lineBeginCursor at its place when auto-completing
        pos=self.lineBeginCursor.position()
        BaseTextCtrl.onAutoComplete(self,text)
        self.lineBeginCursor.setPosition(pos)
    ##Indentation: override code editor behaviour
    def indentSelection(self):
        pass
    def dedentSelection(self):
        pass
        
    ## Key handlers
    def keyPressEvent(self,event):
        if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            # Enter: execute line
            # Remove calltip and autocomp if shown
            self.autocompleteCancel()
            self.callTipCancel()
            
            # reset history needle
            self._historyNeedle = None
            self._historyIndex = -1
            
            # process
            self.processLine()
            return
            
        if event.key() == Qt.Key_Home:
            # Home goes to the prompt.
            cursor=self.textCursor()
            shift = event.modifiers() & Qt.ShiftModifier
            cursor.setPosition(self.lineBeginCursor.position(),
                cursor.KeepAnchor if shift else cursor.MoveAnchor)
            
            self.setTextCursor(cursor)
            self.autocompleteCancel()
            return

        if event.key() in [Qt.Key_Up, Qt.Key_Down] and not \
                self.autocompleteActive():
            #TODO: searching with needle
            #Browse through history
            if event.key() == Qt.Key_Up:
                if self._historyIndex + 1 >= len(self._history):
                    return #On top of history, ignore
                self._historyIndex += 1
            else: # Key_Down
                if self._historyIndex < 0:
                    return #On bottom of history (allow -1 which will be an empty line)
                self._historyIndex -= 1
            
            cursor = self.textCursor()
            cursor.setPosition(self.lineBeginCursor.position())
            cursor.movePosition(cursor.End,cursor.KeepAnchor)
            #print (cursor.selectedText())
            if self._historyIndex == -1:
                cursor.removeSelectedText()
            else:
                cursor.insertText(self._history[self._historyIndex])
            return
        
        #Default behaviour: BaseTextCtrl
        BaseTextCtrl.keyPressEvent(self,event)
     
        #TODO: escape to clear the current line? (Only if not handled by the
        #default editor behaviour)
    
    def keyPressHandler_normal(self, event):
        """ keyPressHandler_normal(event)
        Called when the autocomp list is NOT active and when the event
        was not handled by the "always" handler. If returns True,
        will not process the event further.
        """
        qc = QtCore.Qt
        
        if event.key == qc.Key_Escape:
            # Clear autocomp and calltip, goto end, clear
            
            if self.autoCompActive() or self.callTipActive():
                # Note that the autocomp is already removed on escape by
                # scintilla, but I leave it for clarity
                self.autoCompCancel()             
                self.callTipCancel()
            elif self.getPosition() < self._promptPos2:
                self.setPositionAndAnchor(self.length())
            else:
                self.clearCommand()
                self._historyNeedle = None
            return True
        
        elif event.key in [qc.Key_Up, qc.Key_Down]:
            # Command history
            
            # _historyStep is 0 by default, but the first history element
            # is at _historyStep=1.
            
            # needle
            if self._historyNeedle == None:
                # get partly-command, result of method is tuple, 
                # then we skip ">>> "
                pos1, pos2 = self._promptPos2, self.length()
                self._historyNeedle = self.getRangeString(pos1, pos2)
                self._historyStep = 0
            
            # step
            if event.key==qc.Key_Up:
                self._historyStep +=1
            if event.key==qc.Key_Down:
                self._historyStep -=1
                if self._historyStep<1:
                    self._historyStep = 1
            
            # find the command
            count = 0
            for c in self._history:
                if c.startswith(self._historyNeedle):
                    count+=1
                    if count >= self._historyStep:
                        break
            else:
                # found nothing-> reset
                self._historyStep = 0
                c = self._historyNeedle  
            
            # apply
            self.setAnchor(self._promptPos2)
            self.setPosition(self.length())
            self.ensureCursorVisible()
            self.replaceSelection(c) # replaces the current selection
            return True
        
        else:
            #TODO: if not event.controldown:
            cursor=self.textCursor()
            if cursor.position() < self.lineBeginCursor.position():
                # go back to prompt if not there..
                cursor.move(cursor.End)
                self.setTextCursor(cursor)

                # Proceed as normal though!
    
    ## Cut / Copy / Paste / Undo / Redo
    
    def cut(self):
        """ Reimplement cut to only copy if part of the selected text
        is not at the prompt. """
        
        # get cursor and begin of the edit line
        cursor = self.textCursor()
        lineBegin = self.lineBeginCursor.position()
        if cursor.position() < lineBegin or cursor.anchor() < lineBegin:
            return self.copy()
        else:
            return BaseTextCtrl.cut(self)
    
    #def copy(self): # no overload needed
    
    
    def paste(self):
        """ Reimplement paste to only paste when the position is at
        the prompt. """
        
        # get cursor and begin of the edit line
        cursor = self.textCursor()
        lineBegin = self.lineBeginCursor.position()
        if cursor.position() < lineBegin or cursor.anchor() < lineBegin:
            #Move cursor to end of edit line
            cursor.movePosition(cursor.End)
            self.setTextCursor(cursor)
        # Paste normally
        return BaseTextCtrl.paste(self)

    
    
    def ensureCursorAtEditLine(self):
        """
        If the text cursor is before the beginning of the edit line,
        move it to the end of the edit line
        """
        cursor = self.textCursor()
        if cursor.position() < self.lineBeginCursor.position():
            cursor.movePosition(cursor.End)
            self.setTextCursor(cursor)
    
    ## Basic commands to control the shell
    
    
    def clearScreen(self):
        """ Clear all the previous output from the screen. """
        #Select from current stdout cursor (begin of prompt) to start of document
        self.stdoutCursor.movePosition(self.stdoutCursor.Start,
            self.stdoutCursor.KeepAnchor)
        self.stdoutCursor.removeSelectedText()
        self.ensureCursorAtEditLine()
        self.ensureCursorVisible()
    
    
    def clearCommand(self):
        """ Clear the current command, move the cursor right behind
        the prompt, and ensure it's visible.
        """
        # Select from prompt end to length and delete selected text.
        self.setPosition(self._promptPos2)
        self.setAnchor(self.length())
        self.removeSelectedText()
        # Go to end and ensure visible
        self.setPositionAndAnchor(self._promptPos2)
        self.ensureCursorVisible()  
    
    
    def _handleBackspaces(self, text):
        """ Apply backspaced in the string itself and if there are
        backspaces left at the start of the text, remove the appropriate
        amount of characters from the text.
        
        Note that before running this function, the position and anchor
        should be set to the right position!
        
        Returns the new text.
        """
        # take care of backspaces
        if text.count('\b'):
            # while NOT a backspace at first position, or none found
            i=9999999999999
            while i>0:
                i = text.rfind('\b',0,i)
                if i>0 and text[i-1]!='\b':
                    text = text[0:i-1] + text[i+1:]
            # how many are left? (they are all at the begining)
            nb = text.count('\b')
            text = text.lstrip('\b')
            for i in range(nb):
                self.SendScintilla(self.SCI_DELETEBACK)
        
        return text
    
    
    def _wrapLines(self, text):
        """ Peform hard wrapping of the text to 80 characters.
        We do this because Qscintilla becomes very slow when 
        long lines are displayed.
        The cursor should be at the position to add the text.
        """
    
        # Should we do this?
        if not iep.config.settings.shellWrap80:
            return text
        
        # Check how many chars are left at the line right now
        linenr, index =  self.getLinenrAndIndex()
        charsLeft = 80-index # Is reset to 80 as soon as we are on a next line
        
        # Perform hard-wrap
        lines = text.split('\n')
        lines2 = []
        for line in lines:
            while len(line)>charsLeft:
                lines2.append(line[:charsLeft])
                line = line[charsLeft:]
                charsLeft = 80
            lines2.append(line)
            charsLeft = 80
        text = '\n'.join(lines2)
        return text
       
    
    def _limitNumberOfLines(self):
        """ Reduces the amount of lines by 50% if above a certain threshold.
        Does not reset the position of prompt or current position. 
        """ 
        L = self.length()
        N = self.getLinenrFromPosition( L )
        limit = iep.config.advanced.shellMaxLines
        if N > limit:
            # reduce text
            pos = self.getPositionFromLinenr( int(N/2) )
            self.setPosition(pos)
            self.setAnchor(0)
            self.removeSelectedText()
    
    
    def write(self, text):
        """ write(text)
        Write normal text (stdout) to the shell. The text is printed
        before the prompt.
        """
        # Make sure there's text and make sure its a string
        if not text:
            return
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        #print (text)
        #self.stdoutCursor.setKeepPositionOnInsert(False)
        
        self.lineBeginCursor.setKeepPositionOnInsert(False)
        self.stdoutCursor.insertText(text) #TODO: backspacing
        self.lineBeginCursor.setKeepPositionOnInsert(True)

        self.ensureCursorVisible()#TODO: only when cursor is at last line
    
    def writeErr(self, text):
        """ writeErr(text)
        Writes error messages (stderr) to the shell. If the text
        does not end with a newline, the text is considered a
        prompt and is printed behind the old prompt position
        rather than befor it.
        """
        # Make sure there's text and make sure its a string
        if not text:
            return
        if isinstance(text, bytes):
            text = text.decode('utf-8')

        #While we're writing text, the lineBeginCursor should move with the
        #inserted text
        self.lineBeginCursor.setKeepPositionOnInsert(False)

        if text.endswith('\n'):
            # Normal error message
            self.stdoutCursor.insertText(text) #TODO: backspacing
        else:
            # Prompt
            # This shifts the lineBeginCursor appropriately 
            # Keep the stdout cursor before the prompt
            stdoutPos = self.stdoutCursor.position()
            #Since the lineBeginCursor keeps its position on insert, but the
            #anchor may move, clear the selection (i.e. place anchor at the cursor)
            self.lineBeginCursor.clearSelection()
            self.lineBeginCursor.insertText(text) #TODO: backspacing
            self.stdoutCursor.setPosition(stdoutPos)
            
        # Revert keepPositionOnInsert to True
        self.lineBeginCursor.setKeepPositionOnInsert(True)
        
        self.ensureCursorVisible()#TODO: only when cursor is at last line

    
    
    ## Executing stuff
    def processLine(self, line=None, execute=True):
        """ processLine(self, line=None, execute=True)
        Process the given line or the current line at the prompt if not given.
        Called when the user presses enter.        
        
        If execute is False will not execute the command. This way 
        a message can be written while other ways are used to process
        the command.
        """
        
        # Can we do this?
        if self.isReadOnly():
            return
        
        #Create cursor to modify the text document starting at start of edit line
        commandCursor = self.textCursor()
        commandCursor.setPosition(self.lineBeginCursor.position())
        
        if line:
            # remove newlines spaces and tabs
            command = line.rstrip()
        else:
            #create a selection from begin of the edit line to end of the document
            commandCursor.movePosition(commandCursor.End,commandCursor.KeepAnchor)
            
            #Sample the text from the prompt and remove it
            command = commandCursor.selectedText()
            commandCursor.removeSelectedText()
            
            # remove newlines spaces and tabs
            command = command.rstrip()
            
            # Remember the command (but first remove to prevent duplicates)
            if command:
                if command in self._history:
                    self._history.remove(command)
                self._history.insert(0,command)
        
        # TODO:# Limit text to add to 80 chars 
        #self.setPositionAndAnchor(self._promptPos2)
        #tmp = self._wrapLines(command) + '\n'
        
        commandCursor.insertText(command + '\n')
        
        #Resulting stdout text and the next edit-line are at end of document
        self.stdoutCursor.movePosition(self.stdoutCursor.End)
        self.lineBeginCursor.movePosition(self.lineBeginCursor.End)
        
        
        if execute:
            # Maybe modify the text given...
            command = self.modifyCommand(command)
            # Execute        

            self.executeCommand(command+'\n')
    
    
    def modifyCommand(self, command):
        """ Give the inheriting shell the change to modify/replace the
        command, enabling magic commands. 
        Should be overridden. 
        """
        return command
    
    
    def executeCommand(self, command):
        """ Execute the given command. 
        Should be overridden. 
        """
        # this is a stupid simulation version
        self.write("you executed: "+command+'\n')
        self.writeErr(">>> ")


class RequestObject:
    def __init__(self, request, callback, id=None):
        self._request = request
        self._callback = callback
        self._id = id
        self._posted = False


class ShellInfo:
    """ Helper class to build the command to start the remote python
    process. 
    """
    def __init__(self, info=None):
        
        # Set defaults
        self.exe = 'python'
        self.gui = 'none'
        self.PYTHONPATH = os.environ.get('PYTHONPATH','')            
        self.PYTHONSTARTUP = os.environ.get('PYTHONSTARTUP','')
        self.startDir = ''
        
        # Set info if given
        if info:
            try:
                self.exe = info.exe
                self.gui = info.gui
                if info.PYTHONPATH_useCustom:
                    self.PYTHONPATH = info.PYTHONPATH_custom.replace('\n',os.pathsep)
                if info.PYTHONSTARTUP_useCustom:
                    self.PYTHONSTARTUP = info.PYTHONSTARTUP_custom
                self.startDir = info.startDir
            except Exception:
               pass
        
        # Correct path when it contains spaces
        if self.exe.count(' '):
            self.exe = '"' + self.exe + '"'
    
    
    def getCommand(self, port):
        """ Given the port of the channels interface, creates the 
        command to execute in order to invoke the remote shell.
        """
        startScript = os.path.join( iep.iepDir, 'iepRemote1.py')
        startScript = '"{}"'.format(startScript)
        
        # Build command
        command = self.exe + ' ' + startScript + ' ' + str(port)
        
        if sys.platform.startswith('win'):
            # as the author from Pype writes:
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses.
            # And I also see problems with Tk.    
            # The double quotes are important for it to work when the 
            # executable is a path that contaiins spaces.
            command = 'cmd /c "{}"'.format(command)
        
        # Done
        return command
    
    
    def getEnviron(self, scriptFilename=None):
        """  Gets the environment to give to the remote process,
        such that it can start up as the user wants to. 
        If ScriptFilename is given, use that as the script file
        to execute.
        """ 
        
        # Prepare environment, remove references to tk libraries, 
        # since they're wrong when frozen. Python will insert the
        # correct ones if required.
        env = os.environ.copy()
        #
        env.pop('TK_LIBRARY','') 
        env.pop('TCL_LIBRARY','')
        env['PYTHONPATH'] = self.PYTHONPATH
        
        # Insert iep specific variables
        env['iep_gui'] = self.gui
        env['iep_startDir'] = self.startDir
        
        # Depending on mode (interactive or script)
        if scriptFilename:
            env['iep_scriptFile'] = scriptFilename
        else:
            env['iep_scriptFile'] = ''
            env['PYTHONSTARTUP'] = self.PYTHONSTARTUP
        
        # Done
        return env


class PythonShell(BaseShell):
    """ The PythonShell class implements the python part of the shell
    by connecting to a remote process that runs a Python interpreter.
    """
    
    # Emits when the remote process is terminated
    terminated = QtCore.pyqtSignal(BaseShell) # PythonShell is not yet defd
    
    # Emits when the status string has changed
    stateChanged = QtCore.pyqtSignal(BaseShell)
    debugStateChanged = QtCore.pyqtSignal(BaseShell)
    
    
    def __init__(self, parent, info):
        BaseShell.__init__(self, parent)
        
        # Apply Python shell style
        #TODO: self.setStyle('pythonshell')
        
        # Store info 
        if info is None and iep.config.shellConfigs:
            info = iep.config.shellConfigs[0]
        self._shellInfo = ShellInfo(info)
        
        # For the editor to keep track of attempted imports
        self._importAttempts = []
        
        # To keep track of the response for introspection
        self._currentCTO = None
        self._currentACO = None
        
        # Multi purpose time variable and a buffer
        self._t = time.time()
        self._buffer = ''
        
        # Variables to store python version, builtins and keywords 
        self._version = ""
        self._builtins = []
        self._keywords = []
        
        # Variables to buffer shell status (updated every time 
        # a prompt is generated, and when it is asked for).
        self._state = ''
        self._debugState = ''
        
        # Define queue of requestObjects and insert a few requests
        self._requestQueue = []
        tmp = "','.join(__builtins__.__dict__.keys())"
        self.postRequest('EVAL sys.version', self._setVersion)
        self.postRequest('EVAL ' + tmp, self._setBuiltins)
        self.postRequest("EVAL ','.join(keyword.kwlist)", self._setKeywords)
        
        # Create timer to keep polling any results
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(20)  # ms
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        
        # Initialize timer callback
        self._pollMethod = None
        
        # File to execute on startup (in script mode)
        self._pendingScriptFilename = None
        
        # Start!
        self.start()
    
    
    def start(self):
        """ Start the remote process. """
        
        # (re)set style
        #TODO: self.setStyle('pythonshell')
        self.setReadOnly(False)
        
        # (re)set state and debug state
        self._debugState = ''
        self._state = 'Initializing'
        self.stateChanged.emit(self)
        self.debugStateChanged.emit(self)
        
        # (re)set restart vatiable and a callback
        self._restart = False 
        
        # (re)set import attempts
        self._importAttempts[:] = []
        
        # (re)set variable to terminate the process in increasingly rude ways
        self._killAttempts = 0
        
        # Create multi channel connection
        # Note that the request and response channels are reserved and should
        # not be read/written by "anyone" other than the introspection thread.
        self._channels = c = channels.Channels(3)
        c.disconnectCallback = self._onDisconnect
        # Standard streams
        self._stdin = c.get_sending_channel(0)
        self._stdout = c.get_receiving_channel(0)
        self._stderr = c.get_receiving_channel(1)
        # Control and status of interpreter
        self._control = c.get_sending_channel(1)
        self._status = c.get_receiving_channel(2)
        # For introspection
        self._request = c.get_sending_channel(2)
        self._response = c.get_receiving_channel(3)
        
        # Host it (tries several port numbers, staring from 'IEP')
        port = c.host('IEP', hostLocal=True)
        
        # Start process (open PYPES to detect errors when starting up)
        command = self._shellInfo.getCommand(port)
        env = self._shellInfo.getEnviron(self._pendingScriptFilename)
        self._process = subprocess.Popen(command, 
                                shell=True, env=env, cwd=iep.iepDir,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)  
        
        # Reset pending script
        self._pendingScriptFilename = None
        
        # Set timer callback
        self._pollMethod = self.poll_running
    
    
    def _setVersion(self, response, id):
        """ Process the request for the version. """
        self._version = response.split(' ',1)[0]
    
    def _setBuiltins(self, response, id):
        """ Process the request for the list of buildins. """
        self._builtins = response.split(',')
    
    def _setKeywords(self, response, id):
        """ Process the request for the list of keywords. """
        self._keywords = response.split(',')
    
    
    def _setStatus(self, status):
        """ Handle a new status. Store the state and notify listeners. """
        
        if status.startswith('STATE '):
            state = status.split(' ',1)[1]
            
            # Store status and emit signal if necessary
            if state != self._state:
                self._state = state
                self.stateChanged.emit(self)
        
        elif status.startswith('DEBUG '):
            debugState = status.split(' ',1)[1]
            
            # Store status and emit signal if necessary
            if debugState != self._debugState:
                self._debugState = debugState
                self.debugStateChanged.emit(self)
    
    
    ## Introspection processing methods
    
    def processCallTip(self, cto):
        """ Processes a calltip request using a CallTipObject instance. 
        """
        
        # Try using buffer first (not if we're not the requester)
        if self is cto.textCtrl:
            if cto.tryUsingBuffer():
                return
        
        # Clear buffer to prevent doing a second request
        # and store cto to see whether the response is still wanted.
        cto.setBuffer('')
        self._currentCTO = cto
        
        # Post request
        req = "SIGNATURE " + cto.name
        self.postRequest(req, self._processCallTip_response, cto)
    
    
    def _processCallTip_response(self, response, cto):
        """ Process response of shell to show signature. 
        """
        
        # First see if this is still the right editor (can also be a shell)
        editor1 = iep.editors.getCurrentEditor()
        editor2 = iep.shells.getCurrentShell()
        if cto.textCtrl not in [editor1, editor2]:
            # The editor or shell starting the autocomp is no longer active
            aco.textCtrl.autocompleteCancel()
            return
        
        # Invalid response
        if response == '<error>':
            cto.textCtrl.autocompleteCancel()
            return
        
        # If still required, show tip, otherwise only store result
        if cto is self._currentCTO:
            cto.finish(response)
        else:
            cto.setBuffer(response)
    
    
    def processAutoComp(self, aco):
        """ Processes an autocomp request using an AutoCompObject instance. 
        """
        
        # Try using buffer first (not if we're not the requester)
        if self is aco.textCtrl:
            if aco.tryUsingBuffer():
                return
        
        # Include builtins and keywords?
        if not aco.name:
            aco.addNames(self._builtins)
            if iep.config.settings.autoComplete_keywords:
                aco.addNames(self._keywords)
        
        # Set buffer to prevent doing a second request
        # and store aco to see whether the response is still wanted.
        aco.setBuffer()
        self._currentACO = aco
        # Poll name
        req = "ATTRIBUTES " + aco.name
        self.postRequest(req, self._processAutoComp_response, aco)
    
    
    def _processAutoComp_response(self, response, aco):
        """ Process the response of the shell for the auto completion. 
        """ 
        
        # First see if this is still the right editor (can also be a shell)
        editor1 = iep.editors.getCurrentEditor()
        editor2 = iep.shells.getCurrentShell()
        if aco.textCtrl not in [editor1, editor2]:
            # The editor or shell starting the autocomp is no longer active
            aco.textCtrl.autocompleteCancel()
            return
        
        # Add result to the list
        foundNames = []
        if response != '<error>':
            foundNames = response.split(',')
        aco.addNames(foundNames)
        
        # Process list
        if aco.name and not foundNames:
            # No names found for the requested name. This means
            # it does not exist, let's try to import it
            importNames, importLines = iep.parser.getFictiveImports(editor1)
            baseName = aco.nameInImportNames(importNames)
            if baseName:
                line = importLines[baseName].strip()
                if line not in self._importAttempts:
                    # Do import
                    self.processLine(line + ' # auto-import')
                    self._importAttempts.append(line)
                    # Wait a barely noticable time to increase the chances
                    # That the import is complete when we repost the request.
                    time.sleep(0.2)
                    # To be sure, decrease the experiration date on the buffer
                    aco.setBuffer(timeout=1)
                    # Repost request
                    req = "ATTRIBUTES " + aco.name
                    self.postRequest(req, self._processAutoComp_response, aco)
        else:
            # If still required, show list, otherwise only store result
            if self._currentACO is aco:
                aco.finish()
            else:
                aco.setBuffer()
    
    
    ## Methods for communication and executing code
    
    def postRequest(self, request, callback, id=None):
        """ postRequest(request, callback, id=None)
        Post a request as a string. The given callback is called
        when a response is received, with the response and id as 
        arguments.
        """
        req = RequestObject(request, callback, id)
        self._requestQueue.append(req)
    
    
    def postRequestAndReceive(self, request):
        """ postRequestAndReceive(request)
        Post a message and wait for it to be received.
        Returns the response. If you can, use postRequest
        and catch the response by specifying a callback.
        """
        
        # If there's an item being processed right now ...
        if self._requestQueue:
            # ... make it be reposted when we're done.  
            self._requestQueue[0]._posted = False
            # Wait for any leftover messages to arrive
            self._response.read_one(block=2.0)
        
        # Do request
        self._request.write(request)
        
        # Wait for it to arrive
        tmp = self._response.read_last(block=1.0)
        if tmp is None:
            raise RuntimeError('Request interrupted.')
        else:
            return tmp
    
    
    def executeCommand(self, text):
        """ executeCommand(text)
        Execute one-line command in the remote Python session. 
        """
        self._stdin.write(text)
    
    
    def executeCode(self, text, fname, lineno=0):
        """ executeCode(text, fname, lineno)
        Execute (run) a large piece of code in the remote shell.
        text: the source code to execute
        filename: the file from which the source comes
        lineno: the first lineno of the text in the file, where 0 would be
        the first line of the file...
        
        The text (source code) is first pre-processed:
        - convert all line-endings to \n
        - remove all empty lines at the end
        - remove commented lines at the end
        - convert tabs to spaces
        - dedent so minimal indentation is zero        
        """ 
        
        # Convert tabs to spaces
        text = text.replace("\t"," "*4)
        
        # Make sure there is always *some* text
        if not text:
            text = ' '
        
        # Examine the text line by line...
        # - check for empty/commented lined at the end
        # - calculate minimal indentation
        lines = text.splitlines()        
        lastLineOfCode = 0
        minIndent = 99
        for linenr in range(len(lines)):
            # Get line
            line = lines[linenr]
            # Check if empty (can be commented, but nothing more)
            tmp = line.split("#",1)[0]  # get part before first #
            if tmp.count(" ") == len(tmp):
                continue  # empty line, proceed
            else:
                lastLineOfCode = linenr
            # Calculate indentation
            tmp = line.lstrip(" ")
            indent = len(line) - len(tmp)
            if indent < minIndent:
                minIndent = indent 
        
        # Copy all proper lines to a new array, 
        # remove minimal indentation, but only if we then would only remove 
        # spaces (in the case of commented lines)
        lines2 = []
        for linenr in range(lastLineOfCode+1):
            line = lines[linenr]
            # Remove indentation, 
            if line[:minIndent].count(" ") == minIndent:
                line = line[minIndent:]
            else:
                line = line.lstrip(" ")
            lines2.append( line )
        
        # Running while file?
        runWholeFile = False
        if lineno<0:
            lineno = 0
            runWholeFile = True
        
        # Append info line, than combine
        lines2.insert(0,'') # code is recognized because starts with newline
        lines2.append('') # The code needs to end with a newline
        lines2.append(fname)
        lines2.append(str(lineno))
        #
        text = "\n".join(lines2)
        
        # Get last bit of filename to print in "[executing ...."
        if not fname.startswith('<'):
            fname = os.path.split(fname)[1]
        
        # Write to shell to let user know we are running...
        lineno1 = lineno + 1
        lineno2 = lineno + len(lines)
        if runWholeFile:
            runtext = '[executing "{}"]\n'.format(fname)
        elif lineno1 == lineno2:
            runtext = '[executing line {} of "{}"]\n'.format(lineno1, fname)
        else:
            runtext = '[executing lines {} to {} of "{}"]\n'.format(
                                            lineno1, lineno2, fname)
        self.processLine(runtext, False)
        
        # Run!
        self._stdin.write(text)
    
    
    def modifyCommand(self, text):
        """ To implement magic commands. """
        
        message = """ *magic* commands that are evaluated in the IEP shell, 
        before sending the command to the remote process:
        ?               - show this message
        ?X or X?        - print(X.__doc__)
        ??X or X??      - help(X)
        cd              - import os; print(os.getcwd())
        cd X            - import os; os.chdir("X"); print(os.getcwd())
        ls              - import os; print(os.popen("dir").read())
        open X          - open file, module, or file that defines X
        opendir Xs      - open all files in directory X 
        timeit X        - times execution of command X
        who             - list variables in current workspace
        whos            - list variables plus their class and representation
        db start        - start post mortem debugging
        db stop         - stop debugging
        db up/down      - go up or down the stack frames
        db frame X      - go to the Xth stack frame
        db where        - print the stack trace and indicate the current stack
        db focus        - open the file and show the line of the stack frame"""
        
        
        message = message.replace('\n','\\n')
        message = message.replace('"','\"')
        
        # Define convenience functions
        def remoteEval(command):
            return self.postRequestAndReceive('EVAL ' + command)
        def justify(text, width, margin):
            if len(text)>width:
                text = text[:width-3]+'...'
            text = text.ljust(width+margin, ' ')
            return text
        def prepareTextForRemotePrinting(text):
            # Escape backslah, quotes and newlines
            text = text.replace("\\",  "\\\\")
            text = text.replace("'", "\\'").replace('"', '\\"')
            text = text.replace("\n", "\\n")
            return text
        
        if text=="?":
            text = "print('{}')".format(message)
        
        elif text.startswith("??"):
            text = 'help({})'.format(text[2:])
            
        elif text.endswith("??"):
            text = 'help({})'.format(text[:-2])
            
        elif text.startswith("?"):
            text = 'print({}.__doc__)'.format(text[1:])
            
        elif text.endswith("?"):
            text = 'print({}.__doc__)'.format(text[:-1])
        
        elif text == "timeit":
            text = 'print("Time execution duration, usage:\\n'
            text += 'timeit fun # where fun is a callable\\n'
            text += 'timeit \'expression\' # where fun is a callable\\n'
            text += 'timeit 20 fun # tests 20 passes\\n'
            text += 'For more advanced use, see the timeit module.")\n'
            
        elif text.startswith("timeit "):
            command = text[7:]
            # Get number of iterations
            N = 1
            tmp =  command.split(' ',1)
            if len(tmp)==2:
                try:
                    N = int(tmp[0])
                    command = tmp[1]
                except Exception:
                    pass
            # Compile command
            text = 'import timeit; t=timeit.Timer({}); '.format(command)
            text += 'print(str( t.timeit({})/{} ) '.format(N,N)
            text += '+" seconds on average for {} iterations." )'.format(N)
        
        elif text=='cd' or text.startswith("cd ") and '=' not in text:
            tmp = text[3:].strip()
            if tmp:
                text = 'import os;os.chdir("{}");print(os.getcwd())'.format(tmp)
            else:
                text = 'import os;print(os.getcwd())'
                
        elif text=='ls':
            if sys.platform.startswith('win'):
                text = 'import os;print(os.popen("dir").read())'
            else:
                text = 'import os;print(os.popen("ls").read())'
        
        elif text == 'db start':
            text = ''
            self._control.write('DEBUG START')
        elif text == 'db stop':
            text = ''
            self._control.write('DEBUG STOP')
        elif text == 'db up':
            text = ''
            self._control.write('DEBUG UP')
        elif text == 'db down':
            text = ''
            self._control.write('DEBUG DOWN')
        elif text.startswith('db frame '):
            index = text.split(' ',2)[2]
            try:
                index = int(index)
            except Exception:
                return text
            text = ''
            self._control.write('DEBUG INDEX ' + str(index))
        elif text == 'db where':
            text = ''
            self._control.write('DEBUG WHERE')
        elif text == 'db focus':
            # If not debugging, cant focus
            if not self._debugState:
                return 'print("Not in debug mode.")'
            # Get line from state
            debugState = self._debugState.split(';')
            i = int(debugState[0])
            # Focus
            error = iep.shells._tabs.cornerWidget().debugFocus(debugState[i])
            if error:
                text = 'print "{}"'.format(error)
            else:
                text = ''
        
        elif text.startswith('open ') or text.startswith('opendir '):
            # get what to open            
            objectName = text.split(' ',1)[1]
            # query
            pn = remoteEval('os.getcwd()')
            fn = os.path.join(pn,objectName) # will also work if given abs path
            if text.startswith('opendir '):                
                iep.editors.loadDir(fn)
                msg = "Opening dir '{}'."
            elif os.path.isfile(fn):
                # Load file
                iep.editors.loadFile(fn)
                msg = "Opening file '{}'."
            elif remoteEval(objectName) == '<error>':
                # Given name is not an object
                msg = "Not a valid object: '{}'.".format(objectName)
            else:   
                # Try loading file in which object is defined
                fn = remoteEval('{}.__file__'.format(objectName))
                if fn == '<error>':
                    # Get module                    
                    moduleName = remoteEval('{}.__module__'.format(objectName))
                    tmp = 'sys.modules["{}"].__file__'
                    fn = remoteEval(tmp.format(moduleName))                    
                if fn != '<error>':
                    # Make .py from .pyc
                    if fn.endswith('.pyc'):
                        fn = fn[:-1]
                    # Try loading
                    iep.editors.loadFile(fn)
                    msg = "Opening file that defines '{}'.".format(objectName)
                else:
                    msg = "Could not open the file for that object."
            # ===== Post process
            if msg and '{}' in msg:
                msg = msg.format(fn.replace('\\', '/'))
            if msg:
                text = 'print("{}")'.format(msg)
        
        elif text == 'who':
            # Get list of names
            names = remoteEval('",".join(dir())')
            names = names.split(',')
            # Compile list
            text = ''
            for name in names:
                if name.startswith('__'):
                    continue
                # Make right length                
                name = justify(name, 18, 2)
                # Add to text
                text += name  
            if text:            
                text = 'print("Your variables are:\\n{}")'.format(text)
            else:
                text = 'print("There are no variables defined in this scope.")'
        
        elif text == 'whos':
            # Get list of names
            names = remoteEval('",".join(dir())')
            names = names.split(',')
            # Select names
            names = [name for name in names if not name.startswith('__')]
            # Get class and repr for all names at once
            if names:
                # Define list comprehensions (the one for the class is huge!)
                nameString = ','.join(names)
                classGetter = '[str(c) for c in '
                classGetter += '[a[1] or a[0].__class__.__name__ for a in '
                classGetter += '[(b, not hasattr(b,"__class__")) for b in [{}]'
                classGetter += ']]]'
                reprGetter = '[repr(name) for name in [{}]]'
                #
                classGetter = classGetter.format(nameString)
                reprGetter = reprGetter.format(nameString)
                # Use special seperator that is unlikely to be used, ever.
                namesClass = remoteEval('"##IEP##".join({})'.format(classGetter))
                namesRepr = remoteEval('"##IEP##".join({})'.format(reprGetter))
                namesClass = namesClass.split('##IEP##')
                namesRepr = namesRepr.split('##IEP##')
            # Compile list
            text = ''
            for name, nameClass, nameRepr in zip(names, namesClass, namesRepr):
                # Post process nameclass
                if nameClass == 'True':
                    nameClass = ''
                # Make right length
                name = justify(name, 18, 2)
                nameClass = justify(nameClass, 18, 2)
                nameRepr = justify(nameRepr, 38, 2)
                # Add to text
                text += name + nameClass + nameRepr + '\n'
            if text:
                # Define header
                preamble = "VARIABLE: ".ljust(20,' ') + "TYPE: ".ljust(20,' ') 
                preamble += "REPRESENTATION: ".ljust(20,' ') + '\n'
                # Combine and print
                text = preamble + text[:-2]
                text = 'print("{}")'.format(prepareTextForRemotePrinting(text))
            else:
                text = 'print("There are no variables defined in this scope.")'
            
        # Return modified version (or original)
        return text
    
    
    ## The polling methods and terminating methods
    
    def poll(self):
        """ poll()
        To keep the shell up-to-date
        Call this periodically. 
        """
        if self._pollMethod:
            self._pollMethod()
    
    
    def poll_running(self):
        """  The timer callback method when the process is running.
        Check if we have received anything from the remote
        process that we should write.
        """
        
        # Check stdout
        # Fill the buffer and release it at regular intervals, this will
        # update scintilla much faster if multiple messages are printed
        # When printing a single message, self._t is very old, and the
        # message is printed emidiately
        text = self._stdout.read(False)
        if text:
            self._buffer += text
        if self._buffer and (time.time()-self._t) > 0.2:
            self.write(self._buffer)
            self._buffer = ''
            self._t = time.time()
        
        # Check stderr
        text = self._stderr.read_one(False)
        if text:
            self.writeErr(text)
        
        # Process responses
        if self._requestQueue:
            response = self._response.read_last()
            if response:
                req = self._requestQueue.pop(0)
                req._callback(response, req._id)
        
        # Process requests
        # Post from the bottom of the queue and only if it's not posted.
        # This way there's always only one request being processed. 
        if self._requestQueue:
            req = self._requestQueue[0]
            if not req._posted:
                self._request.write( req._request )
                req._posted = True
        
        # Check status
        if self._version:
            status = 'dummy'
            while status:
                status = self._status.read_one()
                if status:
                    self._setStatus(status)
        else:
            # The version has not been set, poll the process to
            # check whether it's still there
            if self._process.poll():
                self._restart = False
                print('Process stdout:', self._process.stdout.read())
                print('Process stderr:', self._process.stderr.read())
                self._afterDisconnect('The process failed to start.')
    
    
    def poll_terminating(self):
        """ The timer callback method when the process is being terminated. 
        IEP will try to terminate in increasingly more rude ways. 
        """
        
        if self._channels.is_connected:
            if self._killAttempts == 1:
                # Waiting for process to stop by itself
                
                if time.time() - self._t > 0.5:
                    # Increase counter, next time will interrupt
                    self._killAttempts += 1
            
            elif self._killAttempts < 6:
                # Send an interrupt every 100 ms
                if time.time() - self._t > 0.1:
                    self.interrupt()
                    self._t = time.time()
                    self._killAttempts += 1
            
            elif self._killAttempts < 10:
                # Ok, that's it, we're leaving!
                self._channels.kill()
                self._killAttempts = 10
                self._t = time.time()
            else:
                if time.time()-self._t >0.5:
                    self._process.kill()

    
    
    
    def poll_terminated(self):
        """ The timer callback method when the process is terminated.
        Will wait for the focus to be removed and close the shell widget.
        """
        
        if not self.hasFocus():            
            
            # Remove from tab widget
            tabWidget = iep.shells._tabs
            index = tabWidget.indexOf(self)
            if index >= 0:
                tabWidget.removeTab(index)
            
            # close
            self._pollMethod = None
            self.close()
    
    
    def interrupt(self):
        """ interrupt()
        Send a Keyboard interrupt signal to the main thread of the 
        remote process. 
        """
        self._channels.interrupt()
    
    
    def restart(self, scriptFilename=None):
        """ restart(scriptFilename=None)
        Terminate the shell, after which it is restarted. 
        Args can be a filename, to execute as a script as soon as the
        shell is back up.
        """
        if scriptFilename:
            self._pendingScriptFilename = scriptFilename
        self._restart = True
        self.terminate()
    
    
    def terminate(self):
        """ terminate()
        Terminates the python process. It will first try gently, but 
        if that does not work, the process shall be killed.
        To be notified of the termination, connect to the "terminated"
        signal of the shell.
        """
        
        if self._killAttempts != 0:
            # Alreay in the process of terminating, or done terminating
            return
        
        # Try closing the process gently: by closing stdin
        self._stdin.close()
        self._request.close()
        self._killAttempts = 1
        self._t = time.time()
        
        # Keep track using an alternative polling function
        self._pollMethod = self.poll_terminating
    
    
    def terminateNow(self):
        """ terminateNow()
        Terminates the python process. Will terminate the shell in maximally
        1 second. When this function returns, the shell will have been
        terminated.
        """
        # Try closing the process gently: by closing stdin
        self._stdin.close()
        self._request.close()
        self._killAttempts = 1
        self._t = time.time()
        
        # Terminate
        while self._channels.is_connected:
            time.sleep(0.02)
            
            if self._killAttempts == 1:
                if time.time() - self._t > 0.5:
                    self._killAttempts += 1
            elif self._killAttempts < 5:
                if time.time() - self._t > 0.1:
                    self.interrupt()
                    self._t = time.time()
                    self._killAttempts += 1
            elif self._killAttempts == 9:
                # Ok, that's it, we're leaving!
                self._channels.kill()
                self._killAttempts = 10
            else:
                break
    
    
    def _onDisconnect(self, why):
        """ Called when the connection is lost.
        """
        
        # Determine message
        if self._killAttempts < 0:
            msg = 'Process terminated twice?' # this should not happen
        if self._killAttempts == 0:
            msg = why#'Process dropped.'
        elif self._killAttempts == 1:
            msg = 'Process terminated.'
        elif self._killAttempts < 10:
            msg = 'Process interrupted and terminated.'        
        else:
            msg = 'Process killed.'
        
        # signal that the connection is gone
        self._killAttempts = -1
        
        # We're now in a different thread, so use callLater to
        # defer the timer to closing-mode
        iep.callLater(self._afterDisconnect, msg)
    
    
    def _afterDisconnect(self, msg= ''):
        """ To be called after disconnecting (because that is detected
        from another thread.
        Replaces the timeout callback for the timer to go in closing mode.
        """
        # New (empty prompt)
        self.stdoutCursor.movePosition(self.stdoutCursor.End)
        self.lineBeginCursor.movePosition(self.lineBeginCursor.End)

        self.write('\n\n');
        
        # Build second message
        if self._restart:
            msg2 = "Restarting ..."
        else:
            msg2 = "Waiting for focus to be removed."
        
        # Notify via logger and in shell
        msg3 = "===== {} {} ".format(msg, msg2).ljust(80, '=') + '\n\n'
        print(msg)
        self.write(msg3)
        
        # Set style to indicate dead-ness
        self.setStyle('pythonshell_dead')
        self.setReadOnly(True)
        
        # Goto end such that the closing message is visible
        cursor = self.textCursor()
        cursor.movePosition(cursor.End)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
        # Replace timer callback
        self._pollMethod = self.poll_terminated
        
        # Notify listeners
        self.terminated.emit(self)
        
        # Should we restart?
        if self._restart:            
            self.start()
   
