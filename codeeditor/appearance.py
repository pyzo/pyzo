"""
Code editor extensions that change its appearance
"""

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

class HighlightCurrentLine:
    """
    Highlight the current line
    """
    def __init__(self, highlightCurrentLine = False, **kwds):
        super().__init__(**kwds)
        self.setHighlightCurrentLine(highlightCurrentLine)

    def highlightCurrentLine(self):
        return self.__highlightCurrentLine
    
    def setHighlightCurrentLine(self,value):
        self.__highlightCurrentLine = bool(value)
        self.update()
        
    def paintEvent(self,event):
        """ paintEvent(event)
        
        Paints a rectangle spanning the current block (in case of line wrapping, this
        means multiple lines)
        
        Paints behind its super()
        """
        if not self.highlightCurrentLine():
            super().paintEvent(event)
            return
        
        #Find the top of the current block, and the height
        cursor = self.textCursor()
        cursor.movePosition(cursor.StartOfBlock)
        top = self.cursorRect(cursor).top()
        cursor.movePosition(cursor.EndOfBlock)
        height = self.cursorRect(cursor).bottom() - top + 1
        
        margin = self.document().documentMargin()
        painter = QtGui.QPainter()
        painter.begin(self.viewport())
        painter.fillRect(QtCore.QRect(margin, top, 
            self.viewport().width() - 2*margin, height),
            QtGui.QColor(Qt.yellow).lighter(160))
        painter.end()
        
        super().paintEvent(event)

class IndentationGuides:
    def __init__(self, showIndentationGuides = False, **kwds):
        super().__init__(**kwds)
        self.setShowIndentationGuides(showIndentationGuides)

    def showIndentationGuides(self):
        return self.__showIndentationGuides
    
    def setShowIndentationGuides(self,value):
        self.__showIndentationGuides = bool(value)
        self.update()  
        
    def paintEvent(self,event):
        """ paintEvent(event)
        
        Paint the indentation guides, using the indentation info calculated
        by the highlighter.
        """ 
        super().paintEvent(event)

        if not self.showIndentationGuides():
            return
        
        # Get doc and viewport
        doc = self.document()
        viewport = self.viewport()
        
        # Get which part to paint. Just do all to avoid glitches
        w = self.getLineNumberAreaWidth()
        y1, y2 = 0, self.height()
        #y1, y2 = event.rect().top()-10, event.rect().bottom()+10
        
        # Get cursor
        cursor = self.cursorForPosition(QtCore.QPoint(0,y1))
        
        # Get multiplication factor and indent width
        indentWidth = self.indentWidth()
        if self.indentUsingSpaces():
            factor = 1 
        else:
            factor = indentWidth
        
        # Init painter
        painter = QtGui.QPainter()
        painter.begin(viewport)
        painter.setPen(QtGui.QColor('#DDF'))
        
        #Repainting always starts at the first block in the viewport,
        #regardless of the event.rect().y(). Just to keep it simple
        while True:
            blockNumber=cursor.block().blockNumber()
            y3=self.cursorRect(cursor).top()
            y4=self.cursorRect(cursor).bottom()            
            
            bd = cursor.block().userData()            
            if bd.indentation:
                for x in range(indentWidth, bd.indentation * factor, indentWidth):
                    w = self.fontMetrics().width('i'*x) + doc.documentMargin()
                    w += 1 # Put it more under the block

                    painter.drawLine(QtCore.QLine(w, y3, w, y4))
 
            if y4>y2:
                break #Reached end of the repaint area
            if not cursor.block().next().isValid():
                break #Reached end of the text
            
            cursor.movePosition(cursor.NextBlock)
        
        # Done
        painter.end()

class LongLineIndicator:
    def __init__(self, longLineIndicatorPosition = 0, **kwds):
        super().__init__(**kwds)
        self.setLongLineIndicatorPosition(longLineIndicatorPosition)

    def longLineIndicatorPosition(self):
        """ The position of the long line indicator 
        (0 means not visible). 
        """
        return self.__longLineIndicatorPosition
    
    def setLongLineIndicatorPosition(self, value):
        self.__longLineIndicatorPosition = int(value)
        self.update()
        
    def paintEvent(self, event):    
        """ paintEvent(event)
        
        Paint the long line indicator. Paints behind its super()
        """    
        if self.longLineIndicatorPosition()<=0:
            super().paintEvent(event)
            return
            
        # Get doc and viewport
        doc = self.document()
        viewport = self.viewport()

        # Get position of long line
        fm = self.fontMetrics()
        # width of ('i'*length) not length * (width of 'i') b/c of
        # font kerning and rounding
        x = fm.width('i' * self.longLineIndicatorPosition()) + doc.documentMargin()
        x += 1 # Move it a little next to the cursor
        
        # Draw long line indicator
        painter = QtGui.QPainter()
        painter.begin(viewport)                
        painter.setPen(QtGui.QColor('#bbb'))
        painter.drawLine(QtCore.QLine(x, 0, x, viewport.height()) )
        painter.end()
        
        super().paintEvent(event)

class ShowWhitespace:
    def __init__(self, showWhitespace = False, **kwds):
        super().__init__(**kwds)
        self.setShowWhitespace(showWhitespace)
    def showWhitespace(self):
        """Show or hide whitespace markers"""
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowTabsAndSpaces)
        
    def setShowWhitespace(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~option.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(option)

class ShowLineEndings:
    def __init__(self, showLineEndings = False, **kwds):
        super().__init__(**kwds)
        self.setShowLineEndings(showLineEndings)

    def showLineEndings(self):
        """Show or hide line ending markers"""
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowLineAndParagraphSeparators)
        
    def setShowLineEndings(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowLineAndParagraphSeparators)
        else:
            option.setFlags(option.flags() & ~option.ShowLineAndParagraphSeparators)
        self.document().setDefaultTextOption(option)

class LineNumbers:
    class __LineNumberArea(QtGui.QWidget):
        """ This is the widget reponsible for drawing the line numbers.
        """
        
        def __init__(self, codeEditor):
            QtGui.QWidget.__init__(self, codeEditor)

        def paintEvent(self, event):
            editor = self.parent()

                
            if not editor.showLineNumbers():
                return
            
            # Get doc and viewport
            doc = editor.document()
            viewport = editor.viewport()
            
            # Init painter
            painter = QtGui.QPainter()
            painter.begin(self)
            
            # Get which part to paint. Just do all to avoid glitches
            w = editor.getLineNumberAreaWidth()
            y1, y2 = 0, editor.height()
            #y1, y2 = event.rect().top()-10, event.rect().bottom()+10
    
            # Get offset        
            tmp = self.mapToGlobal(QtCore.QPoint(0,0))
            offset = viewport.mapFromGlobal(tmp).y()
            
            #Draw the background        
            painter.fillRect(QtCore.QRect(0, y1, w, y2), QtGui.QColor('#DDD'))
            
            # Get cursor
            cursor = editor.cursorForPosition(QtCore.QPoint(0,y1))
            
            # Init painter
            painter.setPen(QtGui.QColor('#222'))
            painter.setFont(editor.font())
            
            #Repainting always starts at the first block in the viewport,
            #regardless of the event.rect().y(). Just to keep it simple
            while True:
                blockNumber=cursor.block().blockNumber()
                
                y=editor.cursorRect(cursor).y()#+self.viewport().pos().y()+1 #Why +1?
                painter.drawText(0,y-offset,editor.getLineNumberAreaWidth()-3,50,
                    Qt.AlignRight,str(blockNumber+1))
                
                if y>y2:
                    break #Reached end of the repaint area
                if not cursor.block().next().isValid():
                    break #Reached end of the text
                
                cursor.movePosition(cursor.NextBlock)
            
            # Done
            painter.end()
            
    def __init__(self, showLineNumbers = False, **kwds):
        super().__init__(**kwds)
        # Create widget that draws the line numbers
        self.__lineNumberArea = self.__LineNumberArea(self)
        
        self.setShowLineNumbers(showLineNumbers)
        # Issue an update when the amount of line numbers changes
        self.blockCountChanged.connect(self.__onBlockCountChanged)
                
    def showLineNumbers(self):
        return self.__showLineNumbers
    
    def setShowLineNumbers(self,value):
        self.__showLineNumbers = bool(value)
        if self.__showLineNumbers:
            self.__onBlockCountChanged()
            self.__lineNumberArea.show()
        else:
            self.setViewportMargins(0,0,0,0)
            self.__lineNumberArea.hide()
            
    def getLineNumberAreaWidth(self):
        """
        Count the number of lines, compute the length of the longest line number
        (in pixels)
        """
        if not self.__showLineNumbers:
            return 0
        lastLineNumber = self.blockCount() 
        return self.fontMetrics().width(str(lastLineNumber)) + 6 # margin
        
    def __onBlockCountChanged(self,count = None):
        """
        Update the line number area width. This requires to set the 
        viewport margins, so there is space to draw the linenumber area
        """
        if self.__showLineNumbers:
            self.setViewportMargins(self.getLineNumberAreaWidth(),0,0,0)
    
    def resizeEvent(self,event):
        super().resizeEvent(event)
        
        #On resize, resize the lineNumberArea, too
        rect=self.contentsRect()

        self.__lineNumberArea.setGeometry(rect.x(),rect.y(),
            self.getLineNumberAreaWidth(),rect.height())
            
    def paintEvent(self,event):
        super().paintEvent(event)
        #On repaint, update the complete line number area
        self.__lineNumberArea.update(0, 0, 
                self.getLineNumberAreaWidth(), self.height() )
    

class Wrap:
    def __init__(self, wrap = False, **kwds):
        super().__init__(**kwds)
        self.setWrap(wrap)
        
    def wrap(self):
        """Enable or disable wrapping"""
        option=self.document().defaultTextOption()
        return not bool(option.wrapMode() == option.NoWrap)
        
    def setWrap(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setWrapMode(option.WrapAtWordBoundaryOrAnywhere)
        else:
            option.setWrapMode(option.NoWrap)
        self.document().setDefaultTextOption(option)