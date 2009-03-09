""" MODULE SHELL
Defines the shell to be used in IEP.
This is done in a few inheritance steps:

    - IepShell inherits IepTextCtrl and adds the typical shell behaviour.
    
    - IepPythonShell makes it specific to Python.
"""

import iep

from PyQt4 import QtCore, QtGui
qt = QtGui

from editor import IepTextCtrl

class IepShell(IepTextCtrl):
    
    def __init__(self, parent):
        IepTextCtrl.__init__(self, parent)
        
        # set off some settings
        self.setIndentationGuides(False)
        self.setMarginWidth(1,3)
        self.setWrapMode(self.WrapCharacter)
        self.setMarginLineNumbers(1,False)
        self.setEdgeMode(self.EdgeNone)
        
        # no lexer
        self.setLexer()
        
        # get main window
        self._root = iep.GetMainFrame(self)
        
        # variables we need
        self._more = False
        self._promptPosEnd = 0
        self._promptPosStart = 0
        
        # Create the command history.  Commands are added into the
        # front of the list (ie. at index 0) as they are entered.
        # self.historyIndex is the current position in the history; it
        # gets incremented as you retrieve the previous command,
        # decremented as you retrieve the next, and reset when you hit
        # Enter.  self.historyIndex == -1 means you're on the current
        # command, not in the history.
        self._history = []
        self._historyIndex = -1
        self._historyNeedle = None # None means none, "" means look in all
        self._historyStep = 0
    
    
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
            print "I can interrupt the process here!"
        
        
        elif e.controldown and e.char == 'X':
            # If text is selected, copy it, if passed prompt also remove text
            pos, anch = self.getCurrentPos(), self.getAnchor()
            if pos != anch:
                if pos >= self._promptPosEnd and anch >= self._promptPosEnd:
                    self.cut()
                else:
                    self.copy()
        
        elif e.controldown and e.char == 'C':
            # If text is selected, copy it, otherwise...
            # INTERRUPT process 
            if self.getCurrentPos() == self.getAnchor() and self.session:
                self.session.interrupt()
            else:
                self.copy()
            
        elif e.controldown and e.char == 'V':
            # past nicely:  when not at promt go there
            if self.getCurrentPos() < self._promptPosEnd:
                self.setCurrentPos(endpos)
                self.setAnchor(endpos)            
            # handle paste event
            self.paste()
        
        
        elif e.key == qc.Key_Escape:
            # Clear the current, unexecuted command.
            if not ( self.isListActive() or self.isCallTipActive() ):
                self.cancelList()
                self.clearCommand()
                self.setCurrentPos(self._promptPosEnd)
                self.setAnchor(self._promptPosEnd)                
                self.ensureCursorVisible()
                self._historyNeedle = None            
            # skip?
        
        # todo: command history
        
        elif e.key == qc.Key_Home:
            # Home goes to the prompt.
            home = self._promptPosEnd
            if e.shiftdown:
                self.setCurrentPos(home)
            else:
                self.setCurrentPos(home)
                self.setAnchor(home)
            self.ensureCursorVisible()
        
        elif e.key == qc.Key_Insert:
            # Don't toggle between insert mode and overwrite mode.
            pass
        
        elif e.key in [qc.Key_Backspace, qc.Key_Left]:
            # do not backspace past prompt
            # nor with arrow key
            home = self._promptPosEnd
            if self.getCurrentPos() > home:
                return False # process normally
        
        else:
            if not e.controldown:
                # go back to prompt if not there...
                home = self._promptPosEnd 
                pend = len(self.text())
                if self.getCurrentPos() < home or self.getAnchor() < home:
                    self.setCurrentPos(pend)
                    self.setAnchor(pend)
                    self.ensureCursorVisible()                
            
            # act normal
            return False
            # todo: skip here? where elso should I skip?
        
        # Stop handling by default
        return True
    
    
    def clearCommand(self):
        """ Clear the current command. """
        pass
    
    
    def processLine(self):
        """ Process the current line, actived when user presses enter.
        """
        # this is a stupid simulation version
        print ":",
        self.append("\n>>> ")
        l = len(self.text())
        self._promptPosStart = l - 4
        self._promptPosEnd = l
        self.setCurrentPos(l)
        self.setAnchor(l)

if __name__=="__main__":
    app = QtGui.QApplication([])
    win = IepShell(None)
    win.show()
    app.exec_()