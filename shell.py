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

# todo: list:
# - on closing, destroy process
# - reimplement cut, copy and paste
# - bind process interrupt via menu


class BaseShell(BaseTextCtrl):
    
    def __init__(self, parent):
        BaseTextCtrl.__init__(self, parent)
        
        # turn off some settings
        self.setIndentationGuides(False)
        self.setMarginWidth(1,3)
        self.setWrapMode(self.WrapCharacter)
        self.setMarginLineNumbers(1,False)
        self.setEdgeMode(self.EdgeNone)
        
        # no lexer
        self.setLexer()
        
        # variables we need
        self._more = False
        self._promptPosStart = 0
        self._promptPosEnd = 0
        
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
        self.setStyle('pythonconsole')
        
    
    def keyPressEvent2(self, keyevent):
        e = keyevent
        qc = QtCore.Qt
        
#         # If the auto-complete window is up let it do its thing.
#         if self.AutoCompActive():
#             if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
#                 # we shall interupt autocompletion and
#                 # do the action a few lines below...
#                 self.cancelList()
#                 pass
#             else:
#                 # give control to autocompleter
#                 return
                
                
        if e.key in [qc.Key_Return, qc.Key_Enter]:            
            # enter: execute line
            
            # first cancel autocomp and calltip
            if self.isListActive():
                self.cancelList()
            if self.isCallTipActive():
                pass # todo: how to hide it?
                
            # reset history needle
            self._historyNeedle = None
            
            # process
            self.processLine()
        
        elif e.controldown and e.key == qc.Key_Cancel:
            # todo: ok, is this the break key?
            print("I can interrupt the process here!")
        
        
        elif e.key == qc.Key_Escape:
            # Clear the current, unexecuted command.
            if not ( self.isListActive() or self.isCallTipActive() ):
                self.cancelList()
                self.clearCommand()
                self.setPositionAndAnchor(self._promptPosEnd)
                self.ensureCursorVisible()
                self._historyNeedle = None            
        
        elif e.key in [qc.Key_Up, qc.Key_Down]:
            
            # needle
            if self._historyNeedle == None:
                # get partly-command, result of method is tuple, 
                # then we skip ">>> "
                pos1, pos2 = self._promptPosEnd, self.length()
                self._historyNeedle = self.getRangeString(pos1, pos2)
                self._historyStep = 0
            
            # step
            if e.key==qc.Key_Up:
                self._historyStep +=1
            if e.key==qc.Key_Down:
                self._historyStep -=1
            
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
            self.setAnchor(self._promptPosEnd)
            self.setPosition(self.length())
            self.ensureCursorVisible()
            self.replaceSelection(c) # replaces the current selection
        
        elif e.key == qc.Key_Home:
            # Home goes to the prompt.
            home = self._promptPosEnd
            if e.shiftdown:
                self.setPosition(home)
            else:
                self.setPositionAndAnchor(home)
            self.ensureCursorVisible()
        
        elif e.key == qc.Key_Insert:
            # Don't toggle between insert mode and overwrite mode.
            pass
        
        elif e.key in [qc.Key_Backspace, qc.Key_Left]:
            # do not backspace past prompt
            # nor with arrow key
            home = self._promptPosEnd
            if self.getPosition() > home:
                return False # process normally
        
        else:
            if not e.controldown:
                # go back to prompt if not there...
                home = self._promptPosEnd 
                pend = self.length()
                if self.getPosition() < home or self.getAnchor() < home:
                    self.setPositionAndAnchor(pend)
                    self.ensureCursorVisible()                
            
            # act normal
            return False
            # todo: skip here? where elso should I skip?
        
        # Stop handling by default
        return True
    
    
    def clearCommand(self):
        """ Clear the current command. """
        self.setPosition(self._promptPosEnd)
        self.setAnchor(self.length())
        self.removeSelectedText()
        self.ensureCursorVisible()  
    
    
    def limitNumberOfLines(self):
        """ Reduces the amount of lines by 50% if above a certain threshold.
        Does not reset the position of prompt or current position. 
        """ 
        L = self.length()
        N = self.getLinenrFromPosition( L )
        limit = iep.config.shellMaxLines
        if N > limit:
            # reduce text
            pos = self.getPositionFromLinenr( int(N/2) )
            bb = self.getBytes()
            self.setText( bb[pos:] )
    
    
    def processLine(self):
        """ Process the current line, actived when user presses enter.
        """
        # get command on the line
        self.setPosition(self._promptPosEnd)
        self.setAnchor(self.length())
        command = self.getSelectedString()
        command = command.rstrip() # remove newlines spaces and tabs
        
        # remember it (but first remove to prevent duplicates)
        if command:
            if command in self._history:
                self._history.remove(command)
            self._history.insert(0,command)
        
        # maybe modify the text given...
        command = self.modifyCommand(command)
        
        # prepare to execute
        self.appendText('\n')
        self._promptPosStart = self._promptPosEnd = self.length()
        self.setPositionAndAnchor(self.length())
        
        # go
        self.write('') # resets stuff so we actually move to new line
        self.executeCommand(command+'\n')
        
    
    
    def modifyCommand(self, command):
        return command
    
    
    def executeCommand(self, command):
        """ Execute the given command. """
        # this is a stupid simulation version
        prompt = ">>> "
        self.write("you executed: "+command+'\n')
        self.writeErr(prompt)
    
    
    def write(self, text):
        """ Write normal stream. """
        
        if not text:
            return
        
        # make text be a string
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        # get offsets
        L1 = self.length()
        offsetStart = L1 - self._promptPosStart
        offsetEnd = L1 - self._promptPosEnd
        offsetPos = L1 - self.getPosition()
        offsetAnchor = L1 - self.getAnchor()
        # make sure they're not negative
        if offsetStart<0: offsetStart = 0
        if offsetEnd<0: offsetEnd = 0
        if offsetPos<0: offsetPos = 0
        if offsetAnchor<0: offsetAnchor = 0
        
        # put cursor in position to add (or delete) text
        self.setPositionAndAnchor(self._promptPosStart)
        
        # take care of backspaces
        if text.count('\b'):
            # while NOT a backspace at first position, or non found
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
        
        # insert text at current pos
        self.addText(text)
        
        # limit number of lines
        self.limitNumberOfLines()
        
        # shift the prompt position and current position
        L2 = self.length()
        self._promptPosStart = L2 - offsetStart
        self._promptPosEnd = L2 - offsetEnd
        self.setPosition(L2-offsetPos)
        self.setAnchor(L2-offsetAnchor)
        
        # make visible
        self.ensureCursorVisible()
        #self.scroll(0,999999)
    
    
    def writeErr(self, text):
        """ Write error stream (and prompt). """
        
        # todo: or should we have a writePrompt method?
        
        # if our prompt is valid, insert text normally
        if self._promptPosEnd > self._promptPosStart:
            self.write(text)
        
        # get position and anchor
        p1 = self.getPosition()
        p2 = self.getAnchor()
        
        # insert text and calculate how many chars were inserted
        L1 = self.length()        
        self.insertText(self._promptPosEnd, text)
        L2 = self.length()
        Ld = L2-L1
        
        # shift the prompt
        self._promptPosEnd += Ld
        self._promptPosStart = self._promptPosEnd - Ld
        self.setPosition(p1+L2)
        self.setAnchor(p2+L2)
        
        # make visible
        print('stderr')
        self.ensureCursorVisible()
        #self.scroll(0,999999)
        


# Python script to invoke (We need to use double quotes to 
# surround the path, singles wont work.)
remotePath = os.path.join(iep.path, 'remote.py')



class PythonShell(BaseShell):
    """ This class implements the python part of the shell, 
    attaching it to a remote process etc.
    """
    
    def __init__(self, parent, pythonExecutable='python'):
        BaseShell.__init__(self, parent)
        
        # screate multi channel connection
        c = channels.Channels(2)
        self._stdin = c.getSendingChannel(0)        
        self._stdout = c.getReceivingChannel(0)
        self._stderr = c.getReceivingChannel(1)
        self._status = c.getReceivingChannel(2)
        self._request = c.getSendingChannel(1)
        self._response = c.getReceivingChannel(3)
        
        
        # host it!
        port = c.host() # todo: port with range
        
        # build command to create process
        command = '{} "{}" {}'.format(pythonExecutable, remotePath, str(port))
        
        if sys.platform.count('win'):
            # as the author from Pype writes:
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses.
            # And I also see problems with Tk.    
            command = "cmd /c " + command
        
        # where to start
        cwd = os.getcwd() # PYTHONPATH
        
        # start process
        self._process = subprocess.Popen(command, shell=False, cwd=cwd)
        
        # is the process busy?
        self._state = -1 # initializing
        
        # wich installed version
        self._pythonExecutable = pythonExecutable
        # which python version (for example 2.5.2), we set this in init2        
        self._version = ""
        # the builtins list of the process, we set this in init2
        self._builtins =[]
        
        # for the editor to keep track of attempted imports
        self._importAttempts = []
        
        # create timer to keep polling any results
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(100)  # 100 ms
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self.poll)
        self._timer.start()
        
        # time var to pump messages in one go
        self._t = time.time()
        self._buffer = ''
    
    
    def _Init2(self,event=None):
        """ Initialize the process... Call only after the process
        has started up. (by detecting a prompt)
        """
        
        # it is possible that the process is destroyed already...
        if self.stdin.closed:
            return
        
#         # get builtins
#         tmp = self.Introspect_keys("__builtins__")
#         if tmp:
#             self.builtins = tmp
#         
#         # get keywords
#         tmp = self.Enquire("EXEC", "import keyword")
#         tmp = self.Enquire2("EVAL", "','.join(keyword.kwlist)")
#         if tmp is not None:            
#             self.keywords = tmp.split(',')
#             
#         # get version
#         tmp = self.Enquire2("EVAL", "sys.version")
#         if tmp is not None:            
#             self.version = str(tmp[0:5])
        
        
        
        # fire event
        self._state = 9999 # so it is always different
        #self.UpdateState()
    
    
    def Enquire(self, type, args=""):
        """ Enquire(type, args="")
        Send an enquiry to the remote process, do not wait.
        CAREFULL, debugging is hard when something goes wrong...
        """         
        self._request.write(type+' '+args)
    
    
    def Enquire2(self, type, args="", text2send=''):
        """ Enquire2(type, args="", text2send=None)
        Send an enquiry to the remote process, and waiting (max 0.5 sec) 
        for the other side to respond.
        Returns None if timeout
        CAREFULL, debugging is hard when something goes wrong...
        """
        
        # build enquiry and send       
        self.Enquire(type, args+' '+text2send)        
        
        # wait for response
        t0 = time.clock()
        while time.clock() - t0 < 0.500:
            time.sleep(0.010)
            if self.mmfile[0] == "0":
                break
        
        if self.mmfile[0] == "0":
            # success
            L = bytes2int( self.mmfile[1:5] )
            if L>0:
                text = self.mmfile[10:L+10]
            else:
                text = ""
        else:
            text = None
        
        return text
    
    
    def executeCommand(self, text):
        """ executeCommand(text)
        Execute one-line command in the remote Python session. 
        """
        self._stdin.write(text)
    
    
    def executeCode(self, text):
        """ executeCode(text)
        Execute pieces of code in the remote Python session. 
        These can be a few lines, or the contents of a file of a 
        few thousand lines. """
        pass
        
    
    def poll(self):
        """ poll()
        Check if we have received anything from the remote
        process that we should write.
        Call this periodically. 
        """
        
        # todo: why is it so slow???
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
        
        # check stderr
        text = self._stderr.read(False)
        if text:
            self.writeErr(text)
        
        # get response
        response = self._response.readOne()
        
        # check status
        if self._version:
            status = self._status.readLast()
            if status:
                tabWidget = self.parent().parent()
                i = tabWidget.indexOf(self)
                if status == 'Ready':
                    status = 'Python v{}'.format(self._version)
                else:
                    status = 'Python v{} ({})'.format(self._version, status)
                tabWidget.setTabText(i, status)
        elif response:
            if not self._builtins:
                self._builtins = response.split(',')
            else:
                self._version = response[:5]
    

if __name__=="__main__":
    app = QtGui.QApplication([])
    win = PythonShell(None)
    win.show()
    app.exec_()