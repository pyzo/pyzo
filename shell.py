""" MODULE SHELL
Defines the shell to be used in IEP.
This is done in a few inheritance steps:

    - BaseShell inherits BaseTextCtrl and adds the typical shell behaviour.
    
    - PythonShell makes it specific to Python.
"""

from PyQt4 import QtCore, QtGui

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
            print(self._history, c)
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
        
        # go
        self.write('') # resets stuff so we actually move to new line
        self.executeCommand(command)
        
    
    
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
        self._promptPosStart += self._promptPosEnd - Ld
        self.setPosition(p1+L2)
        self.setAnchor(p2+L2)
        
        # make visible
        self.ensureCursorVisible()



class PythonShell(BaseShell):
    """ This class implements the python part of the shell, 
    attaching it to a remote process etc.
    """
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)

    
    def executeCommand(self, text):
        """ executeCommand(text)
        Execute one-line command in the remote Python session. 
        """
        pass
    
    
    def executeCode(self, text):
        """ executeCode(text)
        Execute pieces of code in the remote Python session. 
        These can be a few lines, or the contents of a file of a 
        few thousand lines. """
        pass
    
    
    def poll(self):
        """ Check if we have received anything from the remote
        process that we should write.
        Call this periodically. 
        """
        pass
    
    
    
    
    

if __name__=="__main__":
    app = QtGui.QApplication([])
    win = PythonShell(None)
    win.show()
    app.exec_()