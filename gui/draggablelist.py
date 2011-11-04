"""
This module defines the DraggableList widget, which inherits from the 
QtGui.QListView, and allows the user to reorder items by dragging them
"""
from PyQt4 import QtGui

class DraggableList(QtGui.QListView):
    def __init__(self, *args, **kwds):
        QtGui.QListView.__init__(self, *args, **kwds)
        self.draggingRow=None
        
    def mouseMoveEvent(self,event):
        """
        If the user drags an item, swap rows if necessary
        """
        pos=event.pos()
        index=self.indexAt(pos)
        if not index.isValid():
            return
        
        #Find ot the new position of the row
        rect=self.visualRect(index)
        newRow=index.row()
        if pos.y()>rect.y()+rect.height()/2:
            #Below the horizontal center line of the item
            newRow+=1
        if newRow>self.draggingRow:
            #Moving below the original position
            newRow-=1
            
        if newRow!=self.draggingRow:
            self.model().swapRows(newRow,self.draggingRow)
            self.draggingRow=newRow
            
        #TODO: when the order is changed, the ProjectManager should update
        #config.activeproject
    def mousePressEvent(self,event):
        """Register at which row a drag operation starts"""
        self.draggingRow=self.indexAt(event.pos()).row()
        QtGui.QListView.mousePressEvent(self,event) 
    
