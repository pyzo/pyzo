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
    
    
    def processLine(self):
        """ Process the current line, actived when user presses enter.
        """
        # get command on the line
        self.setPosition(self._promptPosEnd)
        self.setAnchor(self.length())
        command = self.getSelectedString()
        
        # remember it
        self._history.insert(0,command)
        
        # this is a stupid simulation version
        prompt = ">>> "
        self.write("\n"+prompt)
        l = len(self.text())
        self._promptPosStart = l - len(prompt)
        self._promptPosEnd = l
        self.setPositionAndAnchor(l)
    
    def write(self, text):
        """ Write the text. """
        self.appendText(text)
    

class PythonShell(BaseShell):
    """ This class implements the python part of the shell, 
    attaching it to a remote process etc.
    """
    
    def __init__(self, parent):
        BaseShell.__init__(self, parent)



if __name__=="__main__":
    app = QtGui.QApplication([])
    win = PythonShell(None)
    win.show()
    app.exec_()