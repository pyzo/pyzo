"""
Code editor extensions that change its appearance
"""

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

from ..misc import ce_option

# todo: what about calling all extensions. CE_HighlightCurrentLine, 
# or EXT_HighlightcurrentLine?

class HighlightCurrentLine(object):
    """
    Highlight the current line
    """
    
    def highlightCurrentLine(self):
        """ highlightCurrentLine()
        
        Get whether to highlight the current line.
        
        """
        return self.__highlightCurrentLine
    
    @ce_option(True)
    def setHighlightCurrentLine(self,value):
        """ setHighlightCurrentLine(value)
        
        Set whether to highlight the current line.  
        
        """
        self.__highlightCurrentLine = bool(value)
        self.viewport().update()
    
    
    def paintEvent(self,event):
        """ paintEvent(event)
        
        Paints a rectangle spanning the current block (in case of line wrapping, this
        means multiple lines)
        
        Paints behind its super()
        """
        if not self.highlightCurrentLine():
            super(HighlightCurrentLine, self).paintEvent(event)
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
        
        super(HighlightCurrentLine, self).paintEvent(event)
        
        # for debugging paint events
        #if 'log' not in self.__class__.__name__.lower():
        #    print(height, event.rect().width())


class IndentationGuides(object):
    
    def showIndentationGuides(self):
        """ showIndentationGuides()
        
        Get whether to show indentation guides. 
        
        """
        return self.__showIndentationGuides
    
    @ce_option(True)
    def setShowIndentationGuides(self, value):
        """ setShowIndentationGuides(value)
        
        Set whether to show indentation guides.
        
        """
        self.__showIndentationGuides = bool(value)
        self.viewport().update() 
    
    
    def paintEvent(self,event):
        """ paintEvent(event)
        
        Paint the indentation guides, using the indentation info calculated
        by the highlighter.
        """ 
        super(IndentationGuides, self).paintEvent(event)

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
            if bd and bd.indentation:
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

class LongLineIndicator(object):
    
    def longLineIndicatorPosition(self):
        """ longLineIndicatorPosition()
        
        Get the position of the long line indicator (aka edge column).
        A value of 0 or smaller means that no indicator is shown.
        
        """
        return self.__longLineIndicatorPosition
    
    @ce_option(80)
    def setLongLineIndicatorPosition(self, value):
        """ setLongLineIndicatorPosition(value)
        
        Set the position of the long line indicator (aka edge column).
        A value of 0 or smaller means that no indicator is shown.
        
        """ 
        self.__longLineIndicatorPosition = int(value)
        self.viewport().update()
    
    
    def paintEvent(self, event):    
        """ paintEvent(event)
        
        Paint the long line indicator. Paints behind its super()
        """    
        if self.longLineIndicatorPosition()<=0:
            super(LongLineIndicator, self).paintEvent(event)
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
        
        super(LongLineIndicator, self).paintEvent(event)


class ShowWhitespace(object):
    
    def showWhitespace(self):
        """Show or hide whitespace markers"""
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowTabsAndSpaces)
    
    @ce_option(False)
    def setShowWhitespace(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~option.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(option)


class ShowLineEndings(object):
    
    @ce_option(False)
    def showLineEndings(self):
        """ Get whether line ending markers are shown. 
        """
        option=self.document().defaultTextOption()
        return bool(option.flags() & option.ShowLineAndParagraphSeparators)
    
    
    def setShowLineEndings(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setFlags(option.flags() | option.ShowLineAndParagraphSeparators)
        else:
            option.setFlags(option.flags() & ~option.ShowLineAndParagraphSeparators)
        self.document().setDefaultTextOption(option)

class LineNumbers(object):
    # todo: Rob, ik weet niet hoor, maar dit vind ik best lelijk! :)
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
            
    def __init__(self, *args, **kwds):
        self.__lineNumberArea = None
        super(LineNumbers, self).__init__(*args, **kwds)
        # Create widget that draws the line numbers
        self.__lineNumberArea = self.__LineNumberArea(self)
        # Issue an update when the amount of line numbers changes
        self.blockCountChanged.connect(self.__onBlockCountChanged)
        
    
    def showLineNumbers(self):
        return self.__showLineNumbers
    
    @ce_option(True)
    def setShowLineNumbers(self, value):
        self.__showLineNumbers = bool(value)
        # Note that this method is called before the __init__ is finished,
        # so that the __lineNumberArea is not yet created.
        if self.__lineNumberArea:
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
        super(LineNumbers, self).resizeEvent(event)
        
        #On resize, resize the lineNumberArea, too
        rect=self.contentsRect()

        self.__lineNumberArea.setGeometry(rect.x(),rect.y(),
            self.getLineNumberAreaWidth(),rect.height())
            
    def paintEvent(self,event):
        super(LineNumbers, self).paintEvent(event)
        #On repaint, update the complete line number area
        self.__lineNumberArea.update(0, 0, 
                self.getLineNumberAreaWidth(), self.height() )
    

class Wrap(object):
    
    def wrap(self):
        """Enable or disable wrapping"""
        option=self.document().defaultTextOption()
        return not bool(option.wrapMode() == option.NoWrap)
    
    @ce_option(True)
    def setWrap(self,value):
        option=self.document().defaultTextOption()
        if value:
            option.setWrapMode(option.WrapAtWordBoundaryOrAnywhere)
        else:
            option.setWrapMode(option.NoWrap)
        self.document().setDefaultTextOption(option)



class SyntaxHighlighting(object):
    """ Notes on syntax highlighting.

    The syntax highlighting/parsing is performed using three "components".
    
    The base component are the token instances. Each token simply represents
    a row of characters in the text the belong to each-other and should
    be styled in the same way. There is a token class for each particular
    "thing" in the code, such as comments, strings, keywords, etc. Some
    tokens are specific to a particular language.
    
    There is a function that produces a set of tokens, when given a line of
    text and a state parameter. There is such a function for each language.
    These "parsers" are defined in the parsers subpackage.
    
    And lastly, there is the Highlighter class, that applies the parser function
    to obtain the set of tokens and using the names of these tokens applies
    styling. The styling can be defined by giving a dict that maps token names
    to style representations.
    
    """
    
    _styleElements = [  ('syntax.test1','#ddd,bold', 'this is a test'),
                        ('syntax.test2','#ddd,bold', 'this is another test')]
    
    # todo: underlying __parser is string or Parser instance?
    @ce_option('')
    def parser(self):
        """ Get the parser currently in use to parse the code for syntax
        highlighting and source structure.
        """
        return self.__parser
    
    def setParser(self, parserName=''):
        self.__parser = parserName
    
    
    
