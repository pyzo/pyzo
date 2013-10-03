# -*- coding: utf-8 -*-
# Copyright (C) 2013, the codeeditor development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

"""
Code editor extensions that change its behaviour (i.e. how it reacts to keys)
"""


from ..qt import QtGui,QtCore
Qt = QtCore.Qt

from ..misc import ustr, ce_option
from ..parsers.tokens import (CommentToken,UnterminatedStringToken)
from ..parsers import BlockState

class HomeKey(object):
    
    def keyPressEvent(self,event):
        # Home or shift + home
        if event.key() == Qt.Key_Home and \
                event.modifiers() in (Qt.NoModifier, Qt.ShiftModifier):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.ShiftModifier
            moveMode = [cursor.MoveAnchor, cursor.KeepAnchor][shiftDown]
            # Get leading whitespace
            text = ustr(cursor.block().text())
            leadingWhitespace = text[:len(text)-len(text.lstrip())]
            # Get current position and move to start of whitespace
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.StartOfBlock, moveMode)
            cursor.movePosition(cursor.Right, moveMode, len(leadingWhitespace))
            # If we were alread there, move to start of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.StartOfBlock, moveMode)
            # Done
            self.setTextCursor(cursor)
        else:
            super(HomeKey, self).keyPressEvent(event)

class EndKey(object):
    
    def keyPressEvent(self,event):
        if event.key() == Qt.Key_End and \
                event.modifiers() in (Qt.NoModifier, Qt.ShiftModifier):
            # Prepare
            cursor = self.textCursor()
            shiftDown = event.modifiers() == Qt.ShiftModifier
            moveMode = [cursor.MoveAnchor, cursor.KeepAnchor][shiftDown]
            # Get current position and move to end of line
            i = cursor.positionInBlock()
            cursor.movePosition(cursor.EndOfLine, moveMode)
            # If alread at end of line, move to end of block
            if cursor.positionInBlock() == i:
                cursor.movePosition(cursor.EndOfBlock, moveMode)
            # Done
            self.setTextCursor(cursor)
        else:
            super(EndKey, self).keyPressEvent(event)

class NumpadPeriodKey(object):
    """
    If the numpad decimal separator key is pressed, always insert
    a period (.) even if due to localization that key is mapped to a
    comma (,). When editing code, period is the decimal separator
    independent of localization
    """
    def keyPressEvent(self,event):
        # Check for numpad comma
        if event.key() == QtCore.Qt.Key_Comma and \
                event.modifiers() & QtCore.Qt.KeypadModifier:
                    
            # Create a new QKeyEvent to substitute the original one
            event = QtGui.QKeyEvent(event.type(), QtCore.Qt.Key_Period,
                event.modifiers(), '.', event.isAutoRepeat(), event.count())
            
        super(NumpadPeriodKey, self).keyPressEvent(event)


class Indentation(object):
    
    def __cursorIsInLeadingWhitespace(self,cursor = None):
        """
        Checks wether the given cursor is in the leading whitespace of a block, i.e.
        before the first non-whitespace character. The cursor is not modified.
        If the cursor is not given or is None, the current textCursor is used
        """
        if cursor is None:
            cursor = self.textCursor()
        
        # Get the text of the current block up to the cursor
        textBeforeCursor = ustr(cursor.block().text())[:cursor.positionInBlock()]
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
        
        # Auto-unindent
        if event.key() == Qt.Key_Delete:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                cursor.movePosition(cursor.EndOfBlock, cursor.KeepAnchor)
                if not cursor.hasSelection() and cursor.block().next().isValid():
                    cursor.beginEditBlock()
                    cursor.movePosition(cursor.NextBlock)
                    self.indentBlock(cursor, -99)  # dedent as much as we can
                    cursor.deletePreviousChar()
                    cursor.endEditBlock()
                    return
        
        super(Indentation, self).keyPressEvent(event)
        
class AutoIndent(object):
    """
    Auto indentation. This extension only adds the autoIndent property, for the
    actual indentation, the editor should derive from some AutoIndenter object
    """
    
    def autoIndent(self):
        """ autoIndent()
        
        Get whether auto indentation is enabled.
        
        """
        return self.__autoIndent
    
    @ce_option(True)
    def setAutoIndent(self,value):
        """ setAutoIndent(value)
        
        Set whether to enable auto indentation.  
        
        """
        self.__autoIndent = bool(value)
        
        
class PythonAutoIndent(object):
    
    def keyPressEvent(self,event):
        super(PythonAutoIndent, self).keyPressEvent(event)
        if not self.autoIndent():
            return
        
        #This extension code is run *after* key is processed by QPlainTextEdit
        
        if event.key() in (Qt.Key_Enter,Qt.Key_Return):
            cursor=self.textCursor()
            previousBlock=cursor.block().previous()
            if previousBlock.isValid():
                line = ustr(previousBlock.text())
                indent=line[:len(line)-len(line.lstrip())]
                if line.endswith(':'): 
                    # We only need to add indent if the : is not in a (multiline)
                    # string or comment. Therefore, find out what the syntax
                    # highlighter thinks of the previous line.
                    ppreviousBlock = previousBlock.previous() # the block before previous
                    ppreviousState = ppreviousBlock.userState() if previousBlock.isValid() else 0
                    lastElementToken = list(self.parser().parseLine(previousBlock.text(),ppreviousState))[-1]
                        # Because there's at least a : on that line, the list is never empty
                    
                    if (not isinstance(lastElementToken, (CommentToken, UnterminatedStringToken, BlockState))):
                        #TODO: check correct identation (no mixed space/tabs)
                        if self.indentUsingSpaces():
                            indent+=' '*self.indentWidth()
                        else:
                            indent+='\t'
                cursor.insertText(indent)
                #This prevents jump to start of line when up key is pressed
                self.setTextCursor(cursor)
