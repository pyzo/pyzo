"""
Code editor extensions that change its behaviour (i.e. how it reacts to keys)
"""


from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

class HomeKey:
    def keyPressEvent(self,event):
        # Home or shift + home
        if event.key() == Qt.Key_Home and \
                event.modifiers() in (Qt.NoModifier, Qt.ShiftModifier):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.ShiftModifier
            # Get leading whitespace
            text = cursor.block().text()            
            leadingWhitespace = text[:len(text)-len(text.lstrip())]
            # Get current position and move to start of whitespace
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.StartOfBlock, shiftDown)
            cursor.movePosition(cursor.Right, shiftDown, len(leadingWhitespace))
            # If we were alread there, move to start of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.StartOfBlock, shiftDown)
            # Done
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

class EndKey:
    def keyPressEvent(self,event):
        if event.key() == Qt.Key_End and \
                event.modifiers() in (Qt.NoModifier, Qt.ShiftModifier):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.ShiftModifier
            # Get current position and move to end of line
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.EndOfLine, shiftDown)
            # If alread at end of line, move to end of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.EndOfBlock, shiftDown)
            # Done
            self.setTextCursor(cursor)
        else:
            super().keyPressEvent(event)

class Indentation:
    def __cursorIsInLeadingWhitespace(self,cursor = None):
        """
        Checks wether the given cursor is in the leading whitespace of a block, i.e.
        before the first non-whitespace character. The cursor is not modified.
        If the cursor is not given or is None, the current textCursor is used
        """
        if cursor is None:
            cursor = self.textCursor()
        
        # Get the text of the current block up to the cursor
        textBeforeCursor = cursor.block().text()[:cursor.positionInBlock()]
        return textBeforeCursor.lstrip() == '' #If we trim it and it is empty, it's all whitespace
    def keyPressEvent(self,event):
        key = event.key()
        modifiers = event.modifiers()
        #Tab key
        if key == Qt.Key_Tab:
            if modifiers == Qt.NoModifier:
                if self.textCursor().hasSelection(): #Tab pressed while some area was selected
                    self.indentSelection()
                    return
                elif self.__cursorIsInLeadingWhitespace():
                    #If the cursor is in the leading whitespace, indent and move cursor to end of whitespace
                    cursor = self.textCursor()
                    self.indentBlock(cursor)
                    self.setTextCursor(cursor)
                    return
                    
                elif self.indentUsingSpaces():
                    #Insert space-tabs
                    cursor=self.textCursor()
                    w = self.indentWidth()
                    cursor.insertText(' '*(w-((cursor.positionInBlock() + w ) % w)))
                    return
                #else: default behaviour, insert tab character
            else: #Some other modifiers + Tab: ignore
                return

        # If backspace is pressed in the leading whitespace, (except for at the first 
        # position of the line), and there is no selection
        # dedent that line and move cursor to end of whitespace
        if key == Qt.Key_Backspace and modifiers == Qt.NoModifier and \
                self.__cursorIsInLeadingWhitespace() and not self.textCursor().atBlockStart() \
                and not self.textCursor().hasSelection():
            # Create a cursor, dedent the block and move screen cursor to the end of the whitespace
            cursor = self.textCursor()
            self.dedentBlock(cursor)
            self.setTextCursor(cursor)
            return
        
        # todo: Same for delete, I think not (what to do with the cursor?)
        
        super().keyPressEvent(event)
        
        
        
class PythonAutoIndent:
    def keyPressEvent(self,event):
        super().keyPressEvent(event)
        
        #This extension code is run *after* key is processed by QPlainTextEdit
        if event.key() in (Qt.Key_Enter,Qt.Key_Return):
            cursor=self.textCursor()
            previousBlock=cursor.block().previous()
            if previousBlock.isValid():
                line=previousBlock.text()
                indent=line[:len(line)-len(line.lstrip())]
                if line.endswith(':'): #TODO: (multi-line) strings, comments
                    #TODO: check correct identation (no mixed space/tabs)
                    if self.spaceTabs:
                        indent+=' '*self.tabWidth
                    else:
                        indent+='\t'
                cursor.insertText(indent)