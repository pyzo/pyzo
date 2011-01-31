from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt

class Calltip:
    class __CalltipLabel(QtGui.QLabel):
        def __init__(self):
            QtGui.QLabel.__init__(self)
            
            # Start hidden
            self.hide()
            # Accept rich text
            self.setTextFormat(QtCore.Qt.RichText)
            # Set appearance
            self.setStyleSheet("QLabel { background:#ff9; border:1px solid #000; }")
            # Show as tooltip
            self.setWindowFlags(QtCore.Qt.ToolTip)
        
        def enterEvent(self, event):
            # Act a bit like a tooltip
            self.hide()
            
    def __init__(self, **kwds):
        super().__init__(**kwds)
        # Create label for call tips
        self.__calltipLabel = self.__CalltipLabel()
        
    def calltipShow(self, offset=0, richText='', highlightFunctionName=True):
        """ calltipShow(offset=0, richText='', highlightFunctionName=True)
        
        Shows the given calltip.
        
        """
        
        # Process calltip text?
        if highlightFunctionName:
            i = richText.find('(')
            if i>0:
                richText = '<b>{}</b>{}'.format(richText[:i], richText[i:])
        
        # Get a cursor to establish the position to show the calltip
        startcursor=self.textCursor()
        startcursor.movePosition(startcursor.Left, n=offset)
        
        # Get position in pixel coordinates
        rect = self.cursorRect(startcursor)
        pos = rect.topLeft()
        pos.setY( pos.y() - rect.height() )
        #pos.setX( pos.x() + self.viewport().pos().x() + 1 )
        pos = self.viewport().mapToGlobal(pos)
        
        # Set text and update font
        self.__calltipLabel.setText(richText)
        self.__calltipLabel.setFont(self.font())
        
        # Use a qt tooltip to show the calltip
        if richText:
            self.__calltipLabel.move(pos)
            self.__calltipLabel.show()
        else:
            self.__calltipLabel.hide()
    
    
    def calltipCancel(self):
        """ calltipCancel()
        
        Hides the calltip.
        
        """
        self.__calltipLabel.hide()
    
    def calltipActive(self):
        """ calltipActive()
        
        Get whether the calltip is currently active.
        
        """
        return self.__calltipLabel.isVisible()
    
    
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.__calltipLabel.hide()

    def keyPressEvent(self,event):
        # If the user presses Escape and the calltip is active, hide it
        if event.key() == Qt.Key_Escape and event.modifiers() == Qt.NoModifier \
                and self.calltipActive():
            self.calltipCancel()
            return
            
        super().keyPressEvent(event)