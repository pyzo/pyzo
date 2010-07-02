""" MODULE SHELL
Defines the shell to be used in IEP.
This is done in a few inheritance steps:

    - BaseShell inherits BaseTextCtrl and adds the typical shell behaviour.
    
    - PythonShell makes it specific to Python.
"""

from PyQt4 import QtCore, QtGui
import os, sys, time, subprocess
import channels
import iep
from baseTextCtrl import BaseTextCtrl

# todo: color stderr red and prompt blue, and input text Python!

class PositionHelper:
    """ Manages the position of the prompt and the cursor during 
    inserting text to the shell. Provides methods to remember
    and restore the positions. This is a more complex task than
    might seem on first sight; depending on the situation, the 
    position has to be stored relative to the beginning or to
    the end of the text.
    """
    
    def __init__(self):
        self._where1 = ''
        self._where2 = '' 
        self._refPos1 = 0 # position
        self._refPos2 = 0 # anchor
        #
        self._promptRefPos1b = 0 # b for before, a for after 
        self._promptRefPos2b = 0
        self._promptRefPos1a = 0
        self._promptRefPos2a = 0
    
    
    def remember(self, shell):
        """ remember(shell)
        Remember the positions.
        """ 
        
        # Get cursor position
        pos1 = shell.getPosition()
        pos2 = shell.getAnchor()
        
        # Get shell end
        end = shell.length()
        
        # Remember position of prompt for when text is inserted
        # before it and for when text is inserted after it.
        self._promptRefPos1b = end - shell._promptPos1
        self._promptRefPos2b = end - shell._promptPos2
        self._promptRefPos1a = shell._promptPos1
        self._promptRefPos2a = shell._promptPos2
        
        # Determine where each end is and store reference position
        if pos1 >= shell._promptPos2:
            self._where1 = 'input'
            self._refPos1 = end - pos1
        elif pos1 >= shell._promptPos1:
            self._where1 = 'prompt'
            self._refPos1 = end - pos1
        else:
            self._where1 = 'bulk'
            self._refPos1 = pos1
        #
        if pos2 >= shell._promptPos2:
            self._where2 = 'input'
            self._refPos2 = end - pos2
        elif pos2 >= shell._promptPos1:
            self._where2 = 'prompt'
            self._refPos2 = end - pos2
        else:
            self._where2 = 'bulk'
            self._refPos2 = pos2
    
    
    def restore(self, shell, newPromptLength=0):
        """ restore(shell, newPromptLength=0)
        Restore the positions. If newPromptLength is given, it is
        assumed that a prompt was inserted AFTER the previous promptPos2
        with the given number of bytes. If not given, it is assumed
        that the text was inserted BEFORE the previous prompt.
        In other words, all text should be printed before the prompt,
        unless it's a new prompt.
        """ 
        
        # Get shell end
        end = shell.length()
        
        # Restore prompt
        if newPromptLength:
            # Text printed after the prompt
            shell._promptPos1 = self._promptRefPos2a
            shell._promptPos2 = shell._promptPos1 + newPromptLength
        else:
            # Text printed before the prompt
            shell._promptPos1 = end - self._promptRefPos1b
            shell._promptPos2 = end - self._promptRefPos2b
        
        # Obtain new position depending on where the pos was
        if self._where1 == 'input':
            pos1 = end - self._refPos1
        elif self._where1 == 'prompt':
            pos1 = end - self._refPos1
        elif self._where1 == 'bulk':
            pos1 = self._refPos1
        else:
            pos1 = end # error: move to end
        #
        if self._where2 == 'input':
            pos2 = end - self._refPos2
        elif self._where2 == 'prompt':
            pos2 = end - self._refPos2
        elif self._where2 == 'bulk':
            pos2 = self._refPos2
        else:
            pos2 = end # error: move to end
        
        # Set new position
        shell.setPosition(pos1)
        shell.setAnchor(pos2)
        
        # Should we ensure visible?
        # Only if cursor is at input ...
        if self._where1 == 'input' and self._where2 == 'input':
            shell.ensureCursorVisible()
    
    
    def allowedToLimitNumberOfLines(self):
        """ allowedToLimitNumberOfLines()
        Returns a boolean indicating whether it is safe to reduce
        the number of lines. Basically, this is the case if the cursore
        is not in the bulk.
        """ 
        
        if 'bulk' in [self._where1, self._where2]:
            return False
        else:
            return True


class BaseShell(BaseTextCtrl):
    """ The BaseShell implements functionality to make a generic shell.
    """
    
    # Here's a list of positions used:
    # position - of the cursor
    # anchor - of the other end when text is selected
    # _promptPos1 - start of the prompt
    # _promptPos2 - end of the prompt
    # length - the end of the text.
    
    def __init__(self, parent):
        BaseTextCtrl.__init__(self, parent)
        
        # turn off some settings
        self.setIndentationGuides(False)
        self.setMarginWidth(1,3)
        self.setWrapMode(self.WrapCharacter)
        self.setMarginLineNumbers(1,False)
        self.setEdgeMode(self.EDGE_LINE)
        self.setEdgeColumn(80)
        
        # variables we need
        self._more = False
        self._promptPos1 = 0
        self._promptPos2 = 0
        
        # variable to see whether we should resize to match 80 columns
        self._reduceFontSizeToMatch80Columns = True
        
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
        
        # apply style
        self.setStyle('')
    
    
    def resizeEvent(self, event):
        """ When resizing the fontsize nust be kept right. """
        BaseTextCtrl.resizeEvent(self, event)
        if self._reduceFontSizeToMatch80Columns:
            self.updateFontSizeToMatch80Columns()
    
    
    def updateFontSizeToMatch80Columns(self, event=None):
        """ updateFontSizeToMatch80Columns()
        Tries to conform to the correct font size as dictated by
        the style and zooming, but decreases the size as necessary
        to fit 80 columns on screen.
        """
        
        # Are we hidden?
        if not self.isVisible():
            return
        
        # Init zooming to users choice
        zoom = iep.config.editor.zoom
        self.zoomTo(zoom)
        
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
    
    
    ## Key handlers
    
    def keyPressHandler_always(self, event):
        """ keyPressHandler_always(event)
        Is always called. If returns True, will not proceed.
        If return False or None, keyPressHandler_autoComp or 
        keyPressHandler_normal is called, depending on whether the
        autocompletion list is active.
        """
        
        # Use base first
        if BaseTextCtrl.keyPressHandler_always(self, event):
            return True
        
        qc = QtCore.Qt
        
        if event.key in [qc.Key_Return, qc.Key_Enter]:            
            # Enter: execute line
            
            # Remove calltip and autocomp if shown
            self.autoCompCancel()
            self.callTipCancel()
            
            # reset history needle
            self._historyNeedle = None
            
            # process
            self.processLine()
            return True
        
        elif event.key == qc.Key_Home:
            # Home goes to the prompt.
            home = self._promptPos2
            if event.shiftdown:
                self.setPosition(home)
            else:
                self.setPositionAndAnchor(home)
            self.ensureCursorVisible()
            self.autoCompCancel()
            return True
        
        elif event.key == qc.Key_Insert:
            # Don't toggle between insert mode and overwrite mode.
            return True
        
        elif event.key in [qc.Key_Backspace, qc.Key_Left]:
            # do not backspace past prompt
            # nor with arrow key
            home = self._promptPos2
            if self.getPosition() > home:
                return False # process normally
            return True
    
    
    def keyPressHandler_normal(self, event):
        """ keyPressHandler_normal(event)
        Called when the autocomp list is NOT active and when the event
        was not handled by the "always" handler. If returns True,
        will not process the event further.
        """
        qc = QtCore.Qt
        
        if event.key == qc.Key_Escape:
            # Clear the current, unexecuted command.
            
            self.clearCommand()
            self.setPositionAndAnchor(self._promptPos2)
            self.ensureCursorVisible()
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
            if not event.controldown:
                # go back to prompt if not there...
                home = self._promptPos2 
                pend = self.length()
                if self.getPosition() < home or self.getAnchor() < home:
                    self.setPositionAndAnchor(pend)
                    self.ensureCursorVisible()                
                    # Proceed as normal though!
    
    ## Cut / Copy / Paste
    
    def cut(self):
        """ Reimplement cut to only copy if part of the selected text
        is not at the prompt. """
        
        # Get position and anchor
        pos1, pos2 = self.getPosition(), self.getAnchor()
        
        # Depending on position, cut or copy
        if pos1 < self._promptPos2 or pos2 < self._promptPos2:
            self.copy()
        else:
            BaseTextCtrl.cut(self)
    
    #def copy() > can stay the same
    
    def paste(self):
        """ Reimplement paste to only paste when the position is at
        the prompt. """
        
        # Get position and anchor
        pos1, pos2 = self.getPosition(), self.getAnchor()
        
        # If not at prompt, go there
        if pos1 < self._promptPos2 or pos2 < self._promptPos2:
            self.setPositionAndAnchor(self.length())
        
        # Paste normally
        BaseTextCtrl.paste(self)
    
    
    ## Basic commands to control the shell
    
    def clearCommand(self):
        """ Clear the current command, move the cursor right behind
        the prompt, and ensure it's visible.
        """
        # Select from prompt end to length and delete selected text.
        self.setPosition(self._promptPos2)
        self.setAnchor(self.length())
        self.removeSelectedText()
        # Ensure cursor visible
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
        """
        # Perform hard-wrap, because Qscintilla becomes very slow 
        # when long lines are displayed.
        lines = text.split('\n')
        lines2 = []
        for line in lines:
            while len(line)>80:
                lines2.append(line[:80])
                line = line[80:]
            lines2.append(line)
        text = '\n'.join(lines2)
        return text
    
    
    def _limitNumberOfLines(self):
        """ Reduces the amount of lines by 50% if above a certain threshold.
        Does not reset the position of prompt or current position. 
        """ 
        L = self.length()
        N = self.getLinenrFromPosition( L )
        limit = iep.config.shellMaxLines
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
        
        # Remember position of prompt and cursor
        positionHelper = PositionHelper()
        positionHelper.remember(self)
        
        # Put cursor in position to add (or delete) text
        self.setPositionAndAnchor(self._promptPos1)
        L = self.length()
        
        # Handle backspaces and wrap lines
        text = self._handleBackspaces(text)
        text = self._wrapLines(text)
        
        # Insert text at current pos
        self.addText(text)
        
        # Limit number of lines (if cursor not in bulk)
        if positionHelper.allowedToLimitNumberOfLines():
            self._limitNumberOfLines()
        
        # Restore position of prompt and cursor
        positionHelper.restore(self)
    
    
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
        
        # Remember position of prompt and cursor
        positionHelper = PositionHelper()
        positionHelper.remember(self)
        
        # Put cursor in position to add text
        if text[-1] == '\n':
            # Normal error message
            self.setPositionAndAnchor(self._promptPos1)
        else:
            # A prompt
            self.setPositionAndAnchor(self._promptPos2)
        
        # Wrap lines (no need to handle backspaces)
        text = self._wrapLines(text)
        
        # Insert text at current pos
        L1 = self.length()
        self.addText(text)
        L2 = self.length()
        
        # Limit number of lines (if cursor not in bulk)
        if positionHelper.allowedToLimitNumberOfLines():
            self._limitNumberOfLines()
        
        # Restore position of prompt and cursor
        if text[-1] == '\n':
            positionHelper.restore(self)
        else:
            positionHelper.restore(self, L2-L1)
    
    
    
    ## Executing stuff
    def processLine(self, line=None, execute=True):
        """ processLine(self, line=None, execute=True)
        Process the given line or the current line at the prompt if not given.
        Called when the user presses enter.        
        
        If execute is False will not execute the command. This way 
        a message can be written while other ways are used to process
        the command.
        """
        
        # Remember position
        curPos = self.getPosition()
        
        if line:
            # remove newlines spaces and tabs
            command = line.rstrip()            
        else:
            # Sample the text from the prompt
            self.setPosition(self._promptPos2)
            self.setAnchor(self.length())
            command = self.getSelectedString()
            self.replaceSelection('')
            
            # remove newlines spaces and tabs
            command = command.rstrip()            
            
            # Remember the command (but first remove to prevent duplicates)
            if command:
                if command in self._history:
                    self._history.remove(command)
                self._history.insert(0,command)
        
        # Limit text to add to 80 chars
        preamble = self._promptPos2-self._promptPos1
        tmp = ' '*preamble + command        
        tmp = self._wrapLines(tmp)[preamble:] + '\n'
        
        # Add the command text
        self.setPositionAndAnchor(self._promptPos2)
        self.addText(tmp)
        self._promptPos1 = self._promptPos2 = self._promptPos2 + len(tmp)
        
        # Restore position
        curPos += len(tmp)
        if curPos < self._promptPos2:
            curPos = self.length()        
        self.setPositionAndAnchor(curPos)
        
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


# Python script to invoke (We need to use double quotes to 
# surround the path, singles wont work.)
remotePath = os.path.join(iep.path, 'remote.py')

class RequestObject:
    def __init__(self, request, callback, id=None):
        self._request = request
        self._callback = callback
        self._id = id
        self._posted = False


class PythonShell(BaseShell):
    """ The PythonShell class implements the python part of the shell
    by connecting to a remote process that runs a Python interpreter.
    """
    
    # called when the remote process is terminated
    terminated = QtCore.pyqtSignal()
    
    def __init__(self, parent, pythonExecutable=None):
        BaseShell.__init__(self, parent)
        
        # apply Python shell style
        self.setStyle('pythonshell')
        
        # set executable
        if pythonExecutable is None:
            pythonExecutable = 'python'
        self._pythonExecutable = pythonExecutable
        
        # variable to terminate the process in increasingly pressing ways
        self._killAttempts = 0
        
        # which python version is this?
        self._version = ""
        
        # the builtins list of the process
        self._builtins =[]
        
        # for the editor to keep track of attempted imports
        self._importAttempts = []
        
        # to keep track of the response for introspection
        self._currentCTO = None
        self._currentACO = None
        
        # Create multi channel connection
        # Note that the request and response channels are reserved and should
        # not be read/written by "anyone" other than the introspection thread.
        self._channels = c = channels.Channels(3)
        c.disconnectCallback = self._onDisconnect
        # Standard streams
        self._stdin = c.getSendingChannel(0)
        self._stdout = c.getReceivingChannel(0)
        self._stderr = c.getReceivingChannel(1)
        # Control and status of interpreter
        self._control = c.getSendingChannel(1)
        self._status = c.getReceivingChannel(2)
        # For introspection
        self._request = c.getSendingChannel(2)
        self._response = c.getReceivingChannel(3)
        
        # host it (tries several port numbers, staring from 'IEP')
        port = c.host('IEP')
        
        # build command to create process
        command = '{} "{}" {}'.format(pythonExecutable, remotePath, str(port))
        
        if sys.platform.count('win'):
            # as the author from Pype writes:
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses.
            # And I also see problems with Tk.    
            command = "cmd /c " + command
        
        # start process
        self._process = subprocess.Popen(command, shell=True, cwd=os.getcwd())
        
        
        # Define queue of requestObjects and insert two requests
        self._requestQueue = []
        self.postRequest('EVAL sys.version', self._setVersion)
        self.postRequest('KEYS __builtins__.__dict__', self._setBuiltins)
        
        # time var to pump messages in one go
        self._t = time.time()
        self._buffer = ''
        
        # create timer to keep polling any results
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(20)  # 100 ms
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        
    
    def _setVersion(self, response, id):
        """ Process the request for the version. """
        self._version = response[:5]
    
    
    def _setBuiltins(self, response, id):
        """ Process the request for the list of buildins. """
        self._builtins = response.split(',')
    
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
            aco.textCtrl.autoCompCancel()
            return
        
        # Invalid response
        if response == '<error>':
            cto.textCtrl.autoCompCancel()
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
        
        # Include builtins?
        if not aco.name:
            aco.addNames(self._builtins)
        
        # Clear buffer to prevent doing a second request
        # and store cto to see whether the response is still wanted.
        aco.setBuffer([])
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
            aco.textCtrl.autoCompCancel()
            return
        
        # Add result to the list
        foundNames = []
        if response != '<error>':
            foundNames = response.split(',')
        aco.addNames(foundNames)
        
        # Process list
        if aco.name and not aco.names and aco.textCtrl is editor1:
            # No names found for the requested name. This means
            # it does not exist, let's try to import it
            importNames, importLines = iep.parser.getFictiveImports(editor1)
            if aco.name in importNames:
                line = importLines[aco.name].strip()
                if line not in self._importAttempts:
                    self.processLine(line)
                    self._importAttempts.append(line)
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
    
    
    ## The polling method and terminating methods
    
    def poll(self):
        """ poll()
        Check if we have received anything from the remote
        process that we should write.
        Call this periodically. 
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
        text = self._stderr.readOne(False)
        if text:
            self.writeErr(text)
        
        # Process responses
        if self._requestQueue:
            response = self._response.readLast()
            if response:
                req = self._requestQueue.pop(0)
                req._callback(response, req._id)
        
        # Process requests
        if self._requestQueue:
            req = self._requestQueue[0]
            if not req._posted:
                self._request.write( req._request )
                req._posted = True
        
        # Check status
        if self._version:
            status = self._status.readLast()
            if status:
                # Get debug control
                dbc = iep.shells._tabs.cornerWidget()
                # Update it and obtain status text
                if status.startswith('Debug'):
                    dbc.setTrace( status[6:].split(',') )
                    status = 'Python v{} ({})'.format(self._version, 'Debug')
                elif status == 'Ready':
                    dbc.setTrace(None)
                    status = 'Python v{}'.format(self._version)
                else:
                    dbc.setTrace(None)
                    status = 'Python v{} ({})'.format(self._version, status)
                # Show status in tab text
                tabWidget = self.parent().parent()
                i = tabWidget.indexOf(self)
                tabWidget.setTabText(i, status)
    
    
    def interrupt(self):
        """ interrupt()
        Send a Keyboard interrupt signal to the main thread of the 
        remote process. 
        """
        self._channels.interrupt()
    
    
    def terminate(self):
        """ terminate()
        Terminates the python process. It will first try gently, but 
        if that does not work, the process shall be killed.
        After this function returns, it might take a bit of time before
        the kill signal is send to the other process and executed.
        """
        
        # Try closing the process gently: by closing stdin
        self._killAttempts = 1
        self._stdin.close()
        
        # Wait one second
        t0 = time.time() + 1.0
        while time.time() < t0:
            time.sleep(0.1)
            if not self._channels.isConnected():
                break
        else:
            # We waited long enough, kill it!
            self._killAttempts = 2
            self._channels.kill()
    
    
    def _onDisconnect(self, why):
        """ Called when the connection is lost, and why.
        """
        
        # Determine message
        if self._killAttempts == 0:
            msg = 'Python process dropped.'
        elif self._killAttempts == 1:
            msg = 'Python process gently terminated.'
        elif self._killAttempts >= 2:
            msg = 'Python process killed.'
        else:
            msg = 'Python process terminated twice?'
        
        # signal that the connection is gone
        self._killAttempts = -1
        
        # New (empty prompt)
        self.writeErr(' ') 
        self.write('\n\n');
        
        # Notify
        print(msg)        
        self.write('===== {} =====\n'.format(msg))
        self.terminated.emit()
        
        # We're now in a different thread, so use callLater to
        # defer the timer to closing-mode
        self._disconnectTime = 0
        self._disconnectPhase = 3+1
        iep.callLater(self._afterDisconnect)
    
    
    def _afterDisconnect(self):
        """ To be called after disconnecting (because that is detected
        from another thread.
        Replaces the timeout callback for the timer to go in closing mode.
        """
        # Goto end such that the closing messages are visible
        self.setPositionAndAnchor(self.length())
        # Replace timer callback
        self._timer.timeout.disconnect(self.poll)
        self._timer.timeout.connect(self._afterDisconnect_poll)
    
    
    def _afterDisconnect_poll(self):
        """ Poll method for when in closing mode. """
        
        # if self._disconnectPhase is 0, the time's up and we should
        # close as soon as focus is removed.
        
        if self._disconnectPhase and time.time() - self._disconnectTime > 1.0:
            # Count down            
            self._disconnectTime = time.time()
            self._disconnectPhase -= 1
            
            # Notify
            if self._disconnectPhase:
                msg = 'Closing in {} seconds.\n'
                self.write(msg.format(self._disconnectPhase)) 
            elif self.hasFocus():
                self.write('Waiting for focus to be removed.')
        
        if self._disconnectPhase <=0 and not self.hasFocus():
            # Close
            
            # Remove from tab widget
            tabWidget = iep.shells._tabs
            index = tabWidget.indexOf(self)
            if index >= 0:
                tabWidget.removeTab(index)
            
            # close
            self._timer.timeout.disconnect(self._afterDisconnect_poll)
            self.close()


if __name__=="__main__":
    app = QtGui.QApplication([])
    win = PythonShell(None)
    win.show()
    app.exec_()
