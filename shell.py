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
import yoton
import iep
from baseTextCtrl import BaseTextCtrl
from iepLogging import print
from kernelbroker import KernelInfo, Kernelmanager


# Register timer to handle yoton event loop
# todo: combine with poll timer? Or maybe better not.
# todo: test process resources on old PC
iep.main._yoton_timer = QtCore.QTimer(iep.main)
iep.main._yoton_timer.setInterval(10)  # ms
iep.main._yoton_timer.setSingleShot(False)
iep.main._yoton_timer.timeout.connect(yoton.process_events)
iep.main._yoton_timer.start()


# Short constants for cursor movement
A_KEEP = QtGui.QTextCursor.KeepAnchor
A_MOVE = QtGui.QTextCursor.MoveAnchor

# Instantiate a local kernel broker upon loading this module
iep.localKernelManager = Kernelmanager(public=False)


# todo: change shell config dialog to create in the new format
def convertToNewKernelInfo(info):
    
    # First the easy ones
    info2 = KernelInfo()
    info2.exe = info.exe
    info2.gui = info.gui
    info2.name = info.name
    info2.startDir = info.startDir
    
    # pythonpath
    info2.PYTHONPATH = '$PYTHONPATH'
    if info.PYTHONSTARTUP_useCustom:
        info2.PYTHONPATH = info.PYTHONPATH_custom
    
    # startup script
    info2.startupScript = '$PYTHONSTARTUP'
    if info.PYTHONSTARTUP_useCustom:
        info2.startupScript = info.PYTHONSTARTUP_custom
    
    # scriptFile is set by shell right after restarting
    info2.scriptFile = ''
    
    #If the project manager is active, and has the check box
    #'add path to Python path' set, set the PROJECTPATH variable
    projectManager = iep.toolManager.getTool('iepprojectmanager')
    if projectManager:
        info2.projectPath = projectManager.getAddToPythonPath()
    
    return info2


class BaseShell(BaseTextCtrl):
    """ The BaseShell implements functionality to make a generic shell.
    """

    
    def __init__(self, parent,**kwds):
        super().__init__(parent, wrap=True, showLineNumbers=False, 
            highlightCurrentLine=False, parser='python', **kwds)
        
        self.setUndoRedoEnabled(False)
        
        # variables we need
        self._more = False
        
        # We use two cursors to keep track of where the prompt is
        # cursor1 is in front, and cursor2 is at the end of the prompt.
        # They can be in the same position.
        # Further, we store a cursor that selects the last given command,
        # so it can be styled.
        self._cursor1 = self.textCursor()
        self._cursor2 = self.textCursor()
        self._lastCommandCursor = self.textCursor()
        
        # When inserting/removing text at the edit line (thus also while typing)
        # keep the lineBeginCursor at its place. Only when text is written before
        # the lineBeginCursor (i.e. in write and writeErr), this flag is
        # temporarily set to False
        self._cursor2.setKeepPositionOnInsert(True)
        
        # Similarly, we use the _lastCommandCursor cursor really for pointing.
        self._lastCommandCursor.setKeepPositionOnInsert(True)
        
        # Create the command history.  Commands are added into the
        # front of the list (ie. at index 0) as they are entered.
        self._history = []
        self._historyNeedle = None # None means none, "" means look in all
        self._historyStep = 0
        
        # Set minimum width so 80 lines do fit in smallest font size
        self.setMinimumWidth(200)
        
        # Hard wrapping. QTextEdit allows hard wrapping at a specific column.
        # Unfortunately, QPlainTextEdit does not.
        self.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
        
        # Limit number of lines
        # todo: make customizable
        self.setMaximumBlockCount(10*1000)
        
        # apply style
        # TODO: self.setStyle('')
        self.cursorPositionChanged.connect(self.onCursorPositionChanged)
    
    
    def onCursorPositionChanged(self):
        #If the end of the selection (or just the cursor if there is no selection)
        #is before the beginning of the line. make the document read-only
        if self.textCursor().selectionEnd() < self._cursor2.position():
            self.setReadOnly(True)
        else:
            self.setReadOnly(False)
    
    
    def mousePressEvent(self, event):
        """ Disable right MB and middle MB (which pastes by default). """
        if event.button() != QtCore.Qt.MidButton:
            BaseTextCtrl.mousePressEvent(self, event)
    
    def contextMenuEvent(self, event):
        """ Do not show context menu. """
        pass
    
    
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
            self.calltipCancel()
            
            # reset history needle
            self._historyNeedle = None
            
            # process
            self.processLine()
            return
        
        if event.key() == Qt.Key_Escape:
            # Escape clears command
            if not ( self.autocompleteActive() or self.calltipActive() ): 
                self.clearCommand()
            
        if event.key() == Qt.Key_Home:
            # Home goes to the prompt.
            cursor = self.textCursor()
            if event.modifiers() & Qt.ShiftModifier:
                cursor.setPosition(self._cursor2.position(), A_KEEP)
            else:
                cursor.setPosition(self._cursor2.position(), A_MOVE)
            #
            self.setTextCursor(cursor)
            self.autocompleteCancel()
            return

        if event.key() == Qt.Key_Insert:
            # Don't toggle between insert mode and overwrite mode.
            return True
        
        #Ensure to not backspace / go left beyond the prompt
        if event.key() in [Qt.Key_Backspace, Qt.Key_Left]:
            self._historyNeedle = None
            if self.textCursor().position() == self._cursor2.position():
                if event.key() == Qt.Key_Backspace:
                    self.textCursor().removeSelectedText()
                return  #Ignore the key, don't go beyond the prompt


        if event.key() in [Qt.Key_Up, Qt.Key_Down] and not \
                self.autocompleteActive():
            
            # needle
            if self._historyNeedle is None:
                # get partly-written-command
                #
                # Select text                
                cursor = self.textCursor()
                cursor.setPosition(self._cursor2.position(), A_MOVE)
                cursor.movePosition(cursor.End, A_KEEP)
                # Update needle text
                self._historyNeedle = cursor.selectedText()
                self._historyStep = 0
            
            #Browse through history
            if event.key() == Qt.Key_Up:
                self._historyStep +=1
            else: # Key_Down
                self._historyStep -=1
                if self._historyStep < 1:
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
            
            # Replace text
            cursor = self.textCursor()
            cursor.setPosition(self._cursor2.position(), A_MOVE)
            cursor.movePosition(cursor.End, A_KEEP)
            cursor.insertText(c)
            return
        
        else:
            # Reset needle
            self._historyNeedle = None
        
        #if a 'normal' key is pressed, ensure the cursor is at the edit line
        if event.text():
            self.ensureCursorAtEditLine()
        
        #Default behaviour: BaseTextCtrl
        BaseTextCtrl.keyPressEvent(self,event)
    

    
    ## Cut / Copy / Paste / Drag & Drop
    
    def cut(self):
        """ Reimplement cut to only copy if part of the selected text
        is not at the prompt. """
        
        if self.isReadOnly():
            return self.copy()
        else:
            return BaseTextCtrl.cut(self)
    
    #def copy(self): # no overload needed

    def paste(self):
        """ Reimplement paste to paste at the end of the edit line when
        the position is at the prompt. """
        self.ensureCursorAtEditLine()
        # Paste normally
        return BaseTextCtrl.paste(self)

    def dragEnterEvent(self, event):
        """No dropping allowed"""
        pass
        
    def dropEvent(self,event):
        """No dropping allowed"""
        pass
    
    
    ## Basic commands to control the shell
    
    
    def ensureCursorAtEditLine(self):
        """
        If the text cursor is before the beginning of the edit line,
        move it to the end of the edit line
        """
        cursor = self.textCursor()
        if cursor.position() < self._cursor2.position():
            cursor.movePosition(cursor.End, A_MOVE)
            self.setTextCursor(cursor)
    
    
    def clearScreen(self):
        """ Clear all the previous output from the screen. """
        # Select from beginning of prompt to start of document
        self._cursor1.clearSelection()
        self._cursor1.movePosition(self._cursor1.Start, A_KEEP) # Keep anchor
        self._cursor1.removeSelectedText()
        # Wrap up
        self.ensureCursorAtEditLine()
        self.ensureCursorVisible()
    
    
    def clearCommand(self):
        """ Clear the current command, move the cursor right behind
        the prompt, and ensure it's visible.
        """
        # Select from prompt end to length and delete selected text.
        cursor = self.textCursor()
        cursor.setPosition(self._cursor2.position(), A_MOVE)
        cursor.movePosition(cursor.End, A_KEEP)
        cursor.removeSelectedText()
        # Wrap up
        self.ensureCursorAtEditLine()
        self.ensureCursorVisible()
    
    
    def _handleBackspaces(self, text):
        """ Apply backspaced in the string itself and if there are
        backspaces left at the start of the text, remove the appropriate
        amount of characters from the text.
        
        Returns the new text.
        """
        # take care of backspaces
        if '\b' in text:
            # while NOT a backspace at first position, or none found
            i=9999999999999
            while i>0:
                i = text.rfind('\b',0,i)
                if i>0 and text[i-1]!='\b':
                    text = text[0:i-1] + text[i+1:]
            # how many are left? (they are all at the begining)
            nb = text.count('\b')
            text = text.lstrip('\b')
            #
            if nb:
                # Select what we remove and delete that
                self._cursor1.clearSelection()
                self._cursor1.movePosition(self._cursor1.Left, A_KEEP, nb)
                self._cursor1.removeSelectedText()
        
        # Return result
        return text
    
    
    def write(self, text, prompt=0, color=None):
        """ write(text, prompt=0, color=None)
        
        Write to the shell. 
        
        If prompt is 0 (default) the text is printed before the prompt. If 
        prompt is 1, the text is printed after the prompt, the new prompt
        becomes nul. If prompt is 2, the given text becomes the new prompt.
        
        The color of the text can also be specified (as a hex-string).
        
        """
        
        # From The Qt docs: Note that a cursor always moves when text is 
        # inserted before the current position of the cursor, and it always 
        # keeps its position when text is inserted after the current position 
        # of the cursor.
        
        # Make sure there's text and make sure its a string
        if not text:
            return
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        # Prepare format
        format = QtGui.QTextCharFormat()
        if color:
            format.setForeground(QtGui.QColor(color))
        
        #pos1, pos2 = self._cursor1.position(), self._cursor2.position()
        
        # Just in case, clear any selection of the cursors
        self._cursor1.clearSelection()
        self._cursor2.clearSelection()
        
        if prompt == 0:
            # Insert text behind prompt (normal streams)
            self._cursor1.setKeepPositionOnInsert(False)
            self._cursor2.setKeepPositionOnInsert(False)
            text = self._handleBackspaces(text)
            self._cursor1.insertText(text, format)
        elif prompt == 1:
            # Insert command text after prompt, prompt becomes null (input)
            self._lastCommandCursor.setPosition(self._cursor2.position())
            self._cursor1.setKeepPositionOnInsert(False)
            self._cursor2.setKeepPositionOnInsert(False)
            self._cursor2.insertText(text, format)
            self._cursor1.setPosition(self._cursor2.position(), A_MOVE)
        elif prompt == 2 and text == '\b':
            # Remove prompt
            self._cursor1.setPosition(self._cursor2.position(), A_KEEP)
            self._cursor1.removeSelectedText()
            self._cursor2.setPosition(self._cursor1.position(), A_MOVE)
        elif prompt == 2:
            # Insert text after prompt, inserted text becomes new prompt
            self._cursor1.setPosition(self._cursor2.position(), A_MOVE)
            self._cursor1.setKeepPositionOnInsert(True)
            self._cursor2.setKeepPositionOnInsert(False)
            self._cursor1.insertText(text, format)
        
        #if isinstance(self, PythonShell):
        #    print(prompt, '|', pos1, pos2, '|', self._cursor1.position(), self._cursor2.position(), text)
        
        # Reset cursor states for the user to type his/her commands
        self._cursor1.setKeepPositionOnInsert(False)
        self._cursor2.setKeepPositionOnInsert(True)
        
        # Make sure that cursor is visible (only when cursor is at edit line)
        if not self.isReadOnly():
            self.ensureCursorVisible()
    
    
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
        if self.isReadOnly() and not line:
            return
        
        if line:
            # remove newlines spaces and tabs
            command = line.rstrip()
        else:
            # Select command
            cursor = self.textCursor()
            cursor.setPosition(self._cursor2.position(), A_MOVE)
            cursor.movePosition(cursor.End, A_KEEP)
            
            # Sample the text from the prompt and remove it
            command = cursor.selectedText().replace('\u2029', '\n') .rstrip()
            cursor.removeSelectedText()
            
            # Remember the command (but first remove to prevent duplicates)
            if command:
                if command in self._history:
                    self._history.remove(command)
                self._history.insert(0,command)
        
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
        self.write(">>> ", prompt=2)


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
    
    # Emits when the remote process is terminated
    terminated = QtCore.pyqtSignal(BaseShell) # PythonShell is not yet defd
    
    # Emits when the status string has changed
    stateChanged = QtCore.pyqtSignal(BaseShell)
    debugStateChanged = QtCore.pyqtSignal(BaseShell)
    
    
    def __init__(self, parent, info):
        BaseShell.__init__(self, parent)
        
        # Get standard info if not given. Store info
        if info is None and iep.config.shellConfigs:
            info = iep.config.shellConfigs[0]
        if info:
            info = convertToNewKernelInfo(info)
        else:
            info = KernelInfo(None)
        
        # For the editor to keep track of attempted imports
        self._importAttempts = []
        
        # To keep track of the response for introspection
        self._currentCTO = None
        self._currentACO = None
        
        # Multi purpose time variable and a buffer
        self._t = time.time()
        self._buffer = ''
        
        # Variables to store python version, builtins and keywords 
        self._state = ''
        self._debugState = {}
        self._version = ""
        self._builtins = []
        self._keywords = []
        
#         # Define queue of requestObjects and insert a few requests
#         self._requestQueue = []
#         tmp = "','.join(__builtins__.__dict__.keys())"
#         self.postRequest('EVAL sys.version', self._setVersion)
#         self.postRequest('EVAL ' + tmp, self._setBuiltins)
#         self.postRequest("EVAL ','.join(keyword.kwlist)", self._setKeywords)
        
        # Create timer to keep polling any results
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(50)  # ms
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        
        # Initialize timer callback
        self._pollMethod = None
        
        # Install different highlighter
        self._setHighlighter(PythonShellHighlighter)
        
        # Start!
        self.connectToKernel(info)
        self.start()
        
    
    
    def start(self):
        """ Start the remote process. """
        
        # Reset read state
        self.setReadOnly(False)
        
        # (re)set import attempts
        self._importAttempts[:] = []
        
        # Set timer callback
        self._pollMethod = self.poll_running
    
    
    def connectToKernel(self, info):
        """ connectToKernel()
        
        Create kernel and connect to it.
        
        """
        
        # Create yoton context
        self._context = ct = yoton.Context()
        
        # Create stream channels        
        self._strm_out = yoton.SubChannel(ct, 'strm-out')
        self._strm_err = yoton.SubChannel(ct, 'strm-err')
        self._strm_raw = yoton.SubChannel(ct, 'strm-raw')
        self._strm_echo = yoton.SubChannel(ct, 'strm-echo')
        self._strm_prompt = yoton.SubChannel(ct, 'strm-prompt')
        self._strm_broker = yoton.SubChannel(ct, 'strm-broker')
        
        # Create control channels
        self._ctrl_command = yoton.PubChannel(ct, 'ctrl-command')
        self._ctrl_code = yoton.PubChannel(ct, 'ctrl-code', yoton.OBJECT)
        self._ctrl_broker = yoton.PubChannel(ct, 'ctrl-broker')
        
        # Create status channels
        self._stat_heartbeat = yoton.SubstateChannel(ct, 'stat-heartbeat', yoton.OBJECT)
        self._stat_interpreter = yoton.SubstateChannel(ct, 'stat-interpreter', yoton.OBJECT)
        self._stat_debug = yoton.SubstateChannel(ct, 'stat-debug', yoton.OBJECT)
        
        # Create introspection channel
        self._request = yoton.ReqChannel(ct, 'reqp-introspect')
        
        # Connect! The broker will only start the kernel AFTER
        # we connect, so we do not miss out on anything.
        slot = iep.localKernelManager.createKernel(info)
        self._brokerConnection = ct.connect('localhost:%i'%slot)
        self._brokerConnection.closed.bind(self._onConnectionClose)
        
        
        # Ask for python version
        def _setVersion(future):
            version = future.result()
            if isinstance(version, str):
                self._version = version.split(' ',1)[0]
            self.stateChanged.emit(self)
        future = self._request.eval('sys.version')
        future.add_done_callback(_setVersion)
        
        # Ask for builtins
        def _setKeywords(future):
            L = future.result()
            if isinstance(L, list):
                self._keywords = L
        future = self._request.eval('keyword.kwlist')
        future.add_done_callback(_setKeywords)
        
        # Ask for builtins
        def _setBuiltins(future):
            L = future.result()
            if isinstance(L, list):
                self._builtins = L
        future = self._request.eval('dir(__builtins__)')
        future.add_done_callback(_setBuiltins)
    
    
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
        future = self._request.signature(cto.name)
        future.add_done_callback(self._processCallTip_response)
        future.cto = cto
    
    
    def _processCallTip_response(self, future):
        """ Process response of shell to show signature. 
        """
        
        # Process future
        if future.exception():
            print('Introspect-exception: ', future.exception())
            return 
        elif future.cancelled():
            print('Introspect cancelled')
            return
        else:
            response = future.result()
            cto = future.cto
        
        # First see if this is still the right editor (can also be a shell)
        editor1 = iep.editors.getCurrentEditor()
        editor2 = iep.shells.getCurrentShell()
        if cto.textCtrl not in [editor1, editor2]:
            # The editor or shell starting the autocomp is no longer active
            aco.textCtrl.autocompleteCancel()
            return
        
        # Invalid response
        if response is None:
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
        
        # Post request
        future = self._request.dir(aco.name)
        future.add_done_callback(self._processAutoComp_response)
        future.aco = aco
    
    
    def _processAutoComp_response(self, future):
        """ Process the response of the shell for the auto completion. 
        """ 
        
        # Process future
        if future.exception():
            print('Introspect-exception: ', future.exception())
            return
        elif future.cancelled():
            print('Introspect cancelled')
            return
        else:
            response = future.result()
            aco = future.aco
        
        # First see if this is still the right editor (can also be a shell)
        editor1 = iep.editors.getCurrentEditor()
        editor2 = iep.shells.getCurrentShell()
        if aco.textCtrl not in [editor1, editor2]:
            # The editor or shell starting the autocomp is no longer active
            aco.textCtrl.autocompleteCancel()
            return
        
        # Add result to the list
        foundNames = []
        if response is not None:
            foundNames = response
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
                    future = self._request.signature(aco.name)
                    future.add_done_callback(self._processAutoComp_response)
                    future.aco = aco
        else:
            # If still required, show list, otherwise only store result
            if self._currentACO is aco:
                aco.finish()
            else:
                aco.setBuffer()
    
    
    ## Methods for executing code
    
    
    def executeCommand(self, text):
        """ executeCommand(text)
        Execute one-line command in the remote Python session. 
        """
        self._ctrl_command.send(text)
    
    
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
        
        # Copy all proper lines to a new list, 
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
        
#         # Running while file?
#         runWholeFile = False
#         if lineno<0:
#             lineno = 0
#             runWholeFile = True
#         
#         # Append info line, than combine
#         lines2.insert(0,'') # code is recognized because starts with newline
#         lines2.append('') # The code needs to end with a newline
#         lines2.append(fname)
#         lines2.append(str(lineno))
        #
        text = "\n".join(lines2)
        
#         # Get last bit of filename to print in "[executing ...."
#         if not fname.startswith('<'):
#             fname = os.path.split(fname)[1]
#         
#         # Write to shell to let user know we are running...
#         lineno1 = lineno + 1
#         lineno2 = lineno + len(lines)
#         if runWholeFile:
#             runtext = '[executing "{}"]\n'.format(fname)
#         elif lineno1 == lineno2:
#             runtext = '[executing line {} of "{}"]\n'.format(lineno1, fname)
#         else:
#             runtext = '[executing lines {} to {} of "{}"]\n'.format(
#                                             lineno1, lineno2, fname)
#         self.processLine(runtext, False)
        
        # Send message
        msg = {'source':text, 'fname':fname, 'lineno':lineno}
        self._ctrl_code.send(msg)
    
    # todo: implement most magic commands in kernel
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
        
        
        return text
        
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
            self._ctrl_broker.write('DEBUG START')
        elif text == 'db stop':
            text = ''
            self._ctrl_broker.write('DEBUG STOP')
        elif text == 'db up':
            text = ''
            self._ctrl_broker.write('DEBUG UP')
        elif text == 'db down':
            text = ''
            self._ctrl_broker.write('DEBUG DOWN')
        elif text.startswith('db frame '):
            index = text.split(' ',2)[2]
            try:
                index = int(index)
            except Exception:
                return text
            text = ''
            self._ctrl_broker.write('DEBUG INDEX ' + str(index))
        elif text == 'db where':
            text = ''
            self._ctrl_broker.write('DEBUG WHERE')
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
        
        # Check what subchannel has the latest message pending
        sub = yoton.select_sub_channel(self._strm_out, self._strm_err, 
                                self._strm_echo, self._strm_raw,
                                self._strm_broker, self._strm_prompt )
        
        # Write alle pending messages that are later than any other message
        if sub:
            # Get how to deal with prompt
            prompt = 0
            if sub is self._strm_echo:
                prompt = 1 
            elif sub is  self._strm_prompt:
                prompt = 2
            # Get color
            color = None
            if sub is self._strm_broker:
                color = '#000'
            elif sub is self._strm_raw:
                color = '#888888' # Halfway
            elif sub is self._strm_err:
                color = '#F00'
            # insert text
            text = ''.join(sub.recv_selected())
            self.write(text, prompt, color)
            #self.write(sub.recv(False))
        
        # Update status
        # todo: include heartbeat info
        state = self._stat_interpreter.recv()
        if state != self._state:
            self._state = state
            self.stateChanged.emit(self)
        
        state = self._stat_debug.recv()        
        if state != self._debugState:
            self._debugState = state
            self.debugStateChanged.emit(self)
    
    
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
        self._ctrl_broker.send('INT')
    
    
    def restart(self, scriptFilename=None):
        """ restart(scriptFilename=None)
        Terminate the shell, after which it is restarted. 
        Args can be a filename, to execute as a script as soon as the
        shell is back up.
        """
        msg = 'RESTART'
        if scriptFilename:
            msg += ' ' + str(scriptFilename)
        self._ctrl_broker.send(msg)
    
    
    def terminate(self):
        """ terminate()
        Terminates the python process. It will first try gently, but 
        if that does not work, the process shall be killed.
        To be notified of the termination, connect to the "terminated"
        signal of the shell.
        """
        self._ctrl_broker.send('TERM')
    
    
    def _onConnectionClose(self, c, why):
        """ To be called after disconnecting (because that is detected
        from another thread.
        Replaces the timeout callback for the timer to go in closing mode.
        """
        
        # Stop context
        self._context.destroy()
        
        # New (empty prompt)
        self._cursor1.movePosition(self._cursor1.End, A_MOVE)
        self._cursor2.movePosition(self._cursor2.End, A_MOVE)
        
        self.write('\n\n');
        self.write(why)
        self.write('\n\n')
        
        # Notify via logger and in shell
        msg = "Waiting for focus to be removed."
        msg3 = "===== {} ".format(msg).ljust(80, '=') + '\n\n'
        self.write(msg3)
        
        # Set style to indicate dead-ness
        #self.setStyle('pythonshell_dead')
        self.setReadOnly(True)
        
        # Goto end such that the closing message is visible
        cursor = self.textCursor()
        cursor.movePosition(cursor.End, A_MOVE)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
        # Replace timer callback
        self._pollMethod = self.poll_terminated
        
        # Notify listeners
        self.terminated.emit(self)

# todo: clean this up a bit
ustr = str
from codeeditor.highlighter import Highlighter
from codeeditor import parsers
#
class PythonShellHighlighter(Highlighter):
    def highlightBlock(self, line): 
        
        t0 = time.time()
        
        # Make sure this is a Unicode Python string
        line = ustr(line)
        
        # Get previous state
        previousState = self.previousBlockState()
        
        # Get parser
        parser = None
        if hasattr(self._codeEditor, 'parser'):
            parser = self._codeEditor.parser()
        
        # Get function to get format
        nameToFormat = self._codeEditor.getStyleElementFormat
        
        # Last line?
        cursor1 = self._codeEditor._cursor1
        cursor2 = self._codeEditor._cursor2
        commandCursor = self._codeEditor._lastCommandCursor
        curBlock = self.currentBlock()
        #
        atLastPrompt, atCurrentPrompt = False, False
        if curBlock.position() == 0:
            pass
        elif curBlock.position() == commandCursor.block().position():
            atLastPrompt = True
        elif curBlock.position() >= cursor1.block().position():
            atCurrentPrompt = True
        
        
        if (atLastPrompt or atCurrentPrompt) and parser:
            if atCurrentPrompt:
                pos1, pos2 = cursor1.positionInBlock(), cursor2.positionInBlock()
            else:
                pos1, pos2 = 0, commandCursor.positionInBlock()
            
            self.setCurrentBlockState(0)
            for token in parser.parseLine(line, previousState):
                # Handle block state
                if isinstance(token, parsers.BlockState):
                    self.setCurrentBlockState(token.state)
                else:
                    # Get format
                    try:
                        format = nameToFormat(token.name).textCharFormat
                    except KeyError:
                        #print(repr(nameToFormat(token.name)))
                        continue
                    # Set format                    
                    #format.setFontWeight(99)
                    if token.start >= pos2:
                        self.setFormat(token.start,token.end-token.start,format)
                
            # Set prompt to bold
            if atCurrentPrompt:
                format = QtGui.QTextCharFormat()
                format.setFontWeight(99)
                self.setFormat(pos1, pos2-pos1 ,format)
        
        #Get the indentation setting of the editors
        indentUsingSpaces = self._codeEditor.indentUsingSpaces()
        
        # Get user data
        bd = self.getCurrentBlockUserData()
        
        leadingWhitespace=line[:len(line)-len(line.lstrip())]
        if '\t' in leadingWhitespace and ' ' in leadingWhitespace:
            #Mixed whitespace
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.red)
            format.setToolTip('Mixed tabs and spaces')
            self.setFormat(0,len(leadingWhitespace),format)
        elif ('\t' in leadingWhitespace and indentUsingSpaces) or \
            (' ' in leadingWhitespace and not indentUsingSpaces):
            #Whitespace differs from document setting
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.blue)
            format.setToolTip('Whitespace differs from document setting')
            self.setFormat(0,len(leadingWhitespace),format)
        else:
            # Store info for indentation guides
            # amount of tabs or spaces
            bd.indentation = len(leadingWhitespace)
    
    