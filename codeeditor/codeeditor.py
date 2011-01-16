

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

import keyword
if __name__ == '__main__':
	import python_syntax
else:
	from . import python_syntax

	
class Highlighter(QtGui.QSyntaxHighlighter):
	formats=(
		(python_syntax.StringToken,(0x7F007F,'')), 
		(python_syntax.CommentToken,(0x007F00,'')),
		(python_syntax.UnterminatedToken,(0,'')),
		(python_syntax.KeywordToken,(0x00007F,'B')),
		(python_syntax.NumberToken,(0x007F7F,'')),
		(python_syntax.MethodNameToken,(0x007F7F,'B')),
		(python_syntax.ClassNameToken,(0x0000FF,'B'))
		)
	def __init__(self,*args):
		QtGui.QSyntaxHighlighter.__init__(self,*args)
		#Init properties
		self.indentation = False
	## Properties
	@property
	def indentation(self):
		"""
		The number of spaces for each indentation level, or
		0 when tabs are used for indentation
		"""
		return self._indentation
	
	@indentation.setter
	def indentation(self,value):
		if (not value):
			value = 0
		self._indentation = int(value)
		self.rehighlight()
	
	@property
	def spaceTabs(self):
		"""
		True when spaces are used and False when tabs are used
		"""
		return bool(self.indentation)
	
	## Methods
	def highlightBlock(self,line):
		previousState=self.previousBlockState()
	
		self.setCurrentBlockState(0)
		for token in python_syntax.tokenizeLine(line,previousState):
			for tokenType,format in self.formats:
				if isinstance(token,tokenType):
					color,style=format
					format=QtGui.QTextCharFormat()
					format.setForeground(QtGui.QColor(color))
					if 'B' in style:
						format.setFontWeight(QtGui.QFont.Bold)
					#format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
					#format.setUnderlineColor(QtCore.Qt.red)
					self.setFormat(token.start,token.end-token.start,format)
					
			#Handle line or string continuation
			if isinstance(token,python_syntax.ContinuationToken):
				self.setCurrentBlockState(token.state)
		
		leadingWhitespace=line[:len(line)-len(line.lstrip())]
		if '\t' in leadingWhitespace and ' ' in leadingWhitespace:
			#Mixed whitespace
			format=QtGui.QTextCharFormat()
			format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
			format.setUnderlineColor(QtCore.Qt.red)
			format.setToolTip('Mixed tabs and spaces')
			self.setFormat(0,len(leadingWhitespace),format)
		elif ('\t' in leadingWhitespace and self.spaceTabs) or \
			(' ' in leadingWhitespace and not self.spaceTabs):
			#Whitespace differs from document setting
			format=QtGui.QTextCharFormat()
			format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
			format.setUnderlineColor(QtCore.Qt.blue)
			format.setToolTip('Whitespace differs from document setting')
			self.setFormat(0,len(leadingWhitespace),format)
			
class LineNumberArea(QtGui.QWidget):
	def __init__(self,codeEditor):
		QtGui.QWidget.__init__(self,codeEditor)
		self.codeEditor=codeEditor
	def paintEvent(self,event):
		self.codeEditor._lineNumberAreaPaintEvent(event)
#	def sizeHint(self):
#		return QtCore.QSize(50,0)


class CalltipLabel(QtGui.QLabel):
	
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

	
class CodeEditor(QtGui.QPlainTextEdit):
	def __init__(self,*args,**kwds):
		QtGui.QPlainTextEdit.__init__(self,*args,**kwds)
		
		self.highlighter=Highlighter(self.document())
		font=QtGui.QFont('Monaco',15)
		self.setFont(font)
		#print (QtGui.QFontInfo(self.font()).fixedPitch())
		


		
		#Line numbers
		self._lineNumberArea=LineNumberArea(self) #Create line number area widget
		
		#Autocompleter
		self._completerModel=QtGui.QStringListModel(keyword.kwlist)
		self._completer=QtGui.QCompleter(self._completerModel, self)
		self._completer.setCaseSensitivity(Qt.CaseInsensitive)
		self._completer.setWidget(self)
		self._completerNames=[]
		self._recentCompletions=[] #List of recently selected completions
		
		# Text position corresponding to first charcter of the word being completed
		self._autocompleteStart=None
		
		# Create label for call tips
		self._calltipLabel = CalltipLabel()
		
			
		#Default options
		option=self.document().defaultTextOption()
		option.setFlags(option.IncludeTrailingSpaces|option.AddSpaceForLineAndParagraphSeparators)
		self.document().setDefaultTextOption(option)
		
		#Init properties
		self.wrap = True
		self.showWhitespace = False
		self.showLineEndings = False
		self.showLineNumbers = False
		self.highlightCurrentLine = False
		self.indentation = 4
		self.tabWidth = 4

		#Connect signals
		self.connect(self._completer,QtCore.SIGNAL("activated(QString)"),self.onAutoComplete)
		self.cursorPositionChanged.connect(self.updateCurrentLineHighlight)
		self.blockCountChanged.connect(self.updateLineNumberAreaWidth)

	
	def focusOutEvent(self, event):
		QtGui.QPlainTextEdit.focusOutEvent(self, event)
		self._calltipLabel.hide()
	
	## Properties
	
	#wrap
	@property
	def wrap(self):
		option=self.document().defaultTextOption()
		return not bool(option.wrapMode() == option.NoWrap)
		
	@wrap.setter
	def wrap(self,value):
		option=self.document().defaultTextOption()
		if value:
			option.setWrapMode(option.WrapAtWordBoundaryOrAnywhere)
		else:
			option.setWrapMode(option.NoWrap)
		self.document().setDefaultTextOption(option)
	
	#show line numbers
	@property
	def showLineNumbers(self):
		return self._showLineNumbers
	
	@showLineNumbers.setter
	def showLineNumbers(self,value):
		self._showLineNumbers = bool(value)
		if self._showLineNumbers:
			self.setViewportMargins(self.getLineNumberAreaWidth(),0,0,0)
			self._lineNumberArea.show()
		else:
			self.setViewportMargins(0,0,0,0)
			self._lineNumberArea.hide()

	
	#show whitespace
	@property
	def showWhitespace(self):
		"""Show or hide whitespace markers"""
		option=self.document().defaultTextOption()
		return bool(option.flags() & option.ShowTabsAndSpaces)
		
	@showWhitespace.setter
	def showWhitespace(self,value):
		option=self.document().defaultTextOption()
		if value:
			option.setFlags(option.flags() | option.ShowTabsAndSpaces)
		else:
			option.setFlags(option.flags() & ~option.ShowTabsAndSpaces)
		self.document().setDefaultTextOption(option)
	
	#show line endings
	@property
	def showLineEndings(self):
		"""Show or hide line ending markers"""
		option=self.document().defaultTextOption()
		return bool(option.flags() & option.ShowLineAndParagraphSeparators)
		
	@showLineEndings.setter
	def showLineEndings(self,value):
		option=self.document().defaultTextOption()
		if value:
			option.setFlags(option.flags() | option.ShowLineAndParagraphSeparators)
		else:
			option.setFlags(option.flags() & ~option.ShowLineAndParagraphSeparators)
		self.document().setDefaultTextOption(option)
	
	#tab size
	@property
	def tabWidth(self):
		"""Size of a tab stop in characters"""
		return self._tabWidth
		
	@tabWidth.setter
	def tabWidth(self,value):
		self._tabWidth = int(value)
		fontMetrics=QtGui.QFontMetrics(self.font())
		self.setTabStopWidth(fontMetrics.width('i')*self._tabWidth)
		
	@property
	def spaceTabs(self):
		"""
		True when spaces are used and False when tabs are used
		"""
		return bool(self.indentation)
	#indentation
	@property
	def indentation(self):
		"""
		Number of spaces to insert when the tab key is pressed, or 
		0 to insert tabs
		"""
		return self._indentation
	
	@indentation.setter
	def indentation(self,value):
		if (not value): #Also support assignment by None or False etc
			value = 0
		self._indentation = int(value)
		self.highlighter.indentation = self._indentation
	
	#highlight current line
	@property
	def highlightCurrentLine(self):
		return self._highlightCurrentLine
	
	@highlightCurrentLine.setter
	def highlightCurrentLine(self,value):
		self._highlightCurrentLine = bool(value)
		if self._highlightCurrentLine:
			self.updateCurrentLineHighlight()
		else:
			self.setExtraSelections([])
	
	#Completer
	@property
	def completer(self):
		return self._completer
	
	#Recent completions
	@property
	def recentCompletions(self):
		""" 
		The list of recent auto-completions. This property may be set to a
		list that is shared among several editors, in order to share the notion
		of recent auto-completions
		"""
		return self._recentCompletions
	
	@recentCompletions.setter
	def recentCompletions(self,value):
		self._recentCompletions = value
		
	## MISC
	def doForSelectedBlocks(self,function):
		"""
		Call the given function(cursor) for all blocks in the current selection
		A block is considered to be in the current selection if a part of it is in
		the current selection 
		
		The supplied cursor will be located at the beginning of each block. This
		cursor may be modified by the function as required
		"""
		
		#Note: a 'TextCursor' does not represent the actual on-screen cursor, so
		#movements do not move the on-screen cursor
		
		#Note 2: when the text is changed, the cursor and selection start/end
		#positions of all cursors are updated accordingly, so the screenCursor
		#stays in place even if characters are inserted at the editCursor
		
		screenCursor = self.textCursor() #For maintaining which region is selected
		editCursor = self.textCursor()   #For inserting the comment marks
	
		#Use beginEditBlock / endEditBlock to make this one undo/redo operation
		editCursor.beginEditBlock()
			
		editCursor.setPosition(screenCursor.selectionStart())
		editCursor.movePosition(editCursor.StartOfBlock)
		# < : if selection end is at beginning of the block, don't include that one
		while editCursor.position()<screenCursor.selectionEnd(): 
			#Create a copy of the editCursor and call the user-supplied function
			editCursorCopy = QtGui.QTextCursor(editCursor)
			function(editCursorCopy)
			
			#Move to the next block
			if not editCursor.block().next().isValid():
				break #We reached the end of the document
			editCursor.movePosition(editCursor.NextBlock)
			
		editCursor.endEditBlock()
	
	def indentBlock(self,cursor,amount = 1):
		"""
		Indent the block given by cursor
		May be overridden to customize indentation
		"""
		text = cursor.block().text()
		leadingWhitespace = text[:len(text)-len(text.lstrip())]
		
		#Select the leading whitespace
		cursor.movePosition(cursor.StartOfBlock)
		cursor.movePosition(cursor.Right,cursor.KeepAnchor,len(leadingWhitespace))
		
		#Compute the new indentation length, expanding any existing tabs
		indent = len(leadingWhitespace.expandtabs(self.tabWidth))
		if self.spaceTabs:
			# Add the indentation tabs, and round to multiples of indentation
			indent += (self.indentation * amount) - (indent % self.indentation)
			cursor.insertText(' '*max(indent,0))
		else:
			# Convert indentation to number of tabs, and add one
			indent = (indent // self.tabWidth) + amount
			cursor.insertText('\t' * max(indent,0))
			
	def dedentBlock(self,cursor):
		"""
		Dedent the block given by cursor
		Calls indentBlock with amount = -1
		May be overridden to customize indentation
		"""
		self.indentBlock(cursor, amount = -1)
		
	def indentSelection(self):
		"""
		Called when the current line/selection is to be indented.
		Calls indentLine(cursor) for each line in the selection
		May be overridden to customize indentation
		
		See also doForSelectedBlocks and indentBlock
		"""
		
		self.doForSelectedBlocks(self.indentBlock)
	def dedentSelection(self):
		"""
		Called when the current line/selection is to be dedented.
		Calls dedentLine(cursor) for each line in the selection
		May be overridden to customize indentation
		
		See also doForSelectedBlocks and dedentBlock
		"""
		
		self.doForSelectedBlocks(self.dedentBlock)
		
	def setStyle(self,style):
		#TODO: to be implemented
		pass
		
	def _lineNumberAreaPaintEvent(self,event):
		painter = QtGui.QPainter(self._lineNumberArea)
		cursor = self.cursorForPosition(self.viewport().pos())
		
		#Draw the background
		painter.fillRect(event.rect(),Qt.lightGray)
		
		#Repainting always starts at the first block in the viewport,
		#regardless of the event.rect().y(). Just to keep it simple
		while True:
			blockNumber=cursor.block().blockNumber()
			painter.setPen(Qt.black)
			y=self.cursorRect(cursor).y()+self.viewport().pos().y()+1 #Why +1?
			painter.drawText(0,y,self.getLineNumberAreaWidth(),50,
				Qt.AlignRight,str(blockNumber+1))
			
			if y>event.rect().bottom():
				break #Reached end of the repaint area
			if not cursor.block().next().isValid():
				break #Reached end of the text

			cursor.movePosition(cursor.NextBlock)
	
	def getLineNumberAreaWidth(self):
		"""
		Count the number of lines, compute the length of the longest line number
		(in pixels)
		"""
		lastLineNumber = self.blockCount() 
		return QtGui.QFontMetrics(self.font()).width(str(lastLineNumber))

		
	##Custom signal handlers
	def updateCurrentLineHighlight(self):
		"""Create a selection region that shows the current line"""
		#Taken from the codeeditor.cpp example
		if not self.highlightCurrentLine:
			return
		
		selection = QtGui.QTextEdit.ExtraSelection()
		lineColor = QtGui.QColor(Qt.yellow).lighter(160);

		selection.format.setBackground(lineColor);
		selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
		selection.cursor = self.textCursor();
		selection.cursor.clearSelection();
		self.setExtraSelections([selection])
	def updateLineNumberAreaWidth(self,count):
		if self.showLineNumbers:
			self.setViewportMargins(self.getLineNumberAreaWidth(),0,0,0)
	## Autocompletion
	def autocompleteShow(self,offset = 0,names = None):
		"""
		Pop-up the autocompleter (if not already visible) and position it at current
		cursor position minus offset. If names is given and not None, it is set
		as the list of possible completions.
		"""
		#Pop-up the autocompleteList
		startcursor=self.textCursor()
		startcursor.movePosition(startcursor.Left, n=offset)
		
		if not self.autocompleteActive() or \
			startcursor.position() != self._autocompleteStart:

			self._autocompleteStart=startcursor.position()

			#Popup the autocompleter. Don't use .complete() since we want to
			#position the popup manually
			self._positionAutocompleter()
			self._updateAutocompleterPrefix()
			self._completer.popup().show()
		

		if names is not None:
			#TODO: a more intelligent implementation that adds new items and removes
			#old ones
			if names != self._completerNames:
				self._completerModel.setStringList(names)
				self._completerNames = names

		self._updateAutocompleterPrefix()
	def autocompleteAccept(self):
		pass
	def autocompleteCancel(self):
		self._completer.popup().hide()
		self._autocompleteStart = None
		
	def onAutoComplete(self,text):
		#Select the text from autocompleteStart until the current cursor
		cursor=self.textCursor()
		cursor.setPosition(self._autocompleteStart,cursor.KeepAnchor)
		#Replace it with the selected text 
		cursor.insertText(text)
		self._autocompleteStart=None
		self.autocompleteCancel() #Reset the completer
		
		#Update the recent completions list
		if text in self._recentCompletions:
			self._recentCompletions.remove(text)
		self._recentCompletions.append(text)
		
	def autocompleteActive(self):
		""" Returns whether an autocompletion list is currently shown. 
		"""
		return self._autocompleteStart is not None
	
		
	def _positionAutocompleter(self):
		"""Move the autocompleter list to a proper position"""
		#Find the start of the autocompletion and move the completer popup there
		cur=self.textCursor()
		cur.setPosition(self._autocompleteStart)
		position = self.cursorRect(cur).bottomLeft() + \
			self.viewport().pos() #self.geometry().topLeft() +
		self._completer.popup().move(self.mapToGlobal(position))
		
		#Set size
		geometry = self._completer.popup().geometry()
		geometry.setWidth(100)
		geometry.setHeight(100)
		self._completer.popup().setGeometry(geometry)
	
	def _updateAutocompleterPrefix(self):
		"""
		Find the autocompletion prefix (the part of the word that has been 
		entered) and send it to the completer
		"""
		prefix=self.toPlainText()[self._autocompleteStart:
		self.textCursor().position()]

		self._completer.setCompletionPrefix(prefix)
		model = self._completer.completionModel()
		if model.rowCount():
			#Iterate over the matches, find the one that was most recently used
			#print (self._recentCompletions)
			recentFound = -1
			recentFoundRow = 0 #If no recent match, just select the first match
			
			for row in range(model.rowCount()):
				data = model.data(model.index(row,0),self._completer.completionRole())
				if not data in self._recentCompletions:
					continue
				
				index = self._recentCompletions.index(data)
				if index > recentFound: #Later in the list = more recent
					recentFound, recentFoundRow = index, row

			
			self._completer.popup().setCurrentIndex(model.index(recentFoundRow,0));

				
		else:
			#No match, just hide
			self.autocompleteCancel()
	
	
	## Calltips
	
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
		self._calltipLabel.setText(richText)
		self._calltipLabel.setFont(self.font())
		
		# Use a qt tooltip to show the calltip
		if richText:
			self._calltipLabel.move(pos)
			self._calltipLabel.show()
		else:
			self._calltipLabel.hide()
	
	
	def calltipCancel(self):
		""" calltipCancel()
		
		Hides the calltip.
		
		"""
		self._calltipLabel.hide()
	
	def calltipActive(self):
		""" calltipActive()
		
		Get whether the calltip is currently active.
		
		"""
		return self._calltipLabel.isVisible()
	
	
	##Overridden Event Handlers
	def resizeEvent(self,event):
		QtGui.QPlainTextEdit.resizeEvent(self,event)
		rect=self.contentsRect()
		#On resize, resize the lineNumberArea, too
		self._lineNumberArea.setGeometry(rect.x(),rect.y(),
			self.getLineNumberAreaWidth(),rect.height())

	def paintEvent(self,event):
		#Draw the default QTextEdit, then update the lineNumberArea 
		QtGui.QPlainTextEdit.paintEvent(self,event)
		self._lineNumberArea.update(0,event.rect().y(),50,event.rect().height())
		


	def keyPressEvent(self,event):
		#TODO: backspacing over tabs
		key = event.key()
		modifiers = event.modifiers()
		
		if key == Qt.Key_Escape and modifiers == Qt.NoModifier:
			self.autocompleteCancel()
			self._calltipLabel.hide()
			return
		
		#Tab key
		if key == Qt.Key_Tab:
			if modifiers == Qt.NoModifier:
				if self.autocompleteActive():
					#Let the completer handle this one!
					event.ignore()
					return
					
				elif self.textCursor().hasSelection(): #Tab pressed while some area was selected
					self.indentSelection()
					return
				
				elif self.indentation:
					#Insert space-tabs
					cursor=self.textCursor()
					cursor.insertText(' '*(self.indentation-((cursor.columnNumber() + self.indentation )%self.indentation)))
					return
				#else: default behaviour, insert tab character
			else: #Some other modifiers + Tab: ignore
				return
		

			
			#self.testTokenize()
		#Allowed keys that do not close the autocompleteList:
		# alphanumeric and _
		# Backspace (until start of autocomplete word)
		if self.autocompleteActive() and \
			not event.text().isalnum() and event.text != '_' and not (
			(key==Qt.Key_Backspace) and self.textCursor().position()>self._autocompleteStart):
			self.autocompleteCancel()
			
		#Apply the key
		QtGui.QPlainTextEdit.keyPressEvent(self,event)

		#Auto-indent
		if key in (Qt.Key_Enter,Qt.Key_Return):
			cursor=self.textCursor()
			previousBlock=cursor.block().previous()
			if previousBlock.isValid():
				line=previousBlock.text()
				indent=line[:len(line)-len(line.lstrip())]
				if line.endswith(':'): #TODO: (multi-line) strings, comments
					#TODO: check correct identation (no mixed space/tabs)
					if self.spaceTabs:
						indent+=' '*self.tabSize
					else:
						indent+='\t' #TODO: tabs or spaces
				cursor.insertText(indent)
				
				
		if self.autocompleteActive():
			#While we type, the start of the autocompletion may move due to line
			#wrapping, so reposition after every key stroke
			self._positionAutocompleter()
			
			self._updateAutocompleterPrefix()
		


if __name__=='__main__':
	app=QtGui.QApplication([])
	class TestEditor(CodeEditor):
		def keyPressEvent(self,event):
			key = event.key()
			if key == Qt.Key_F1:
				self.autocompleteShow()
				return
			elif key == Qt.Key_F2:
				self.autocompleteCancel()
				return
			elif key == Qt.Key_Backtab: #Shift + Tab
				self.dedentSelection()
			return
			
			CodeEditor.keyPressEvent(self,event)
			self.calltipShow(0, 'test(foo, bar)')
		
	e=TestEditor()
	e.showLineNumbers = True
	e.showWhitespace = True
	e.show()
	s=QtGui.QSplitter()
	s.addWidget(e)
	s.addWidget(QtGui.QLabel('test'))
	s.show()
	app.exec_()
	