

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

import keyword
#from . import python_syntax
import python_syntax

	
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
		self.spaceTabs = False
	## Properties
	@property
	def spaceTabs(self):
		return self._spaceTabs
	
	@spaceTabs.setter
	def spaceTabs(self,value):
		self._spaceTabs = bool(value)
		self.rehighlight()
	
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
		self.codeEditor.lineNumberAreaPaintEvent(event)
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
		self.setViewportMargins(self.getLineNumberAreaWidth(),0,0,0)
		self.lineNumberArea=LineNumberArea(self)
		
		#Autocompleter
		self.completerModel=QtGui.QStringListModel(keyword.kwlist)
		self.completer=QtGui.QCompleter(self.completerModel, self)
		self.completer.setCaseSensitivity(Qt.CaseInsensitive)
		self.completer.setWidget(self)
		self.completerNames=[]
		self.recentCompletions=[] #List of recently selected completions
		
		# Text position corresponding to first charcter of the word being completed
		self._autocompleteStart=None
		
		# Create label for call tips
		self._calltipLabel = CalltipLabel()
		
		#Connect signals
		self.connect(self.completer,QtCore.SIGNAL("activated(QString)"),self.onAutoComplete)
		self.cursorPositionChanged.connect(self.updateCurrentLineHighlight)
		self.blockCountChanged.connect(self.updateLineNumberAreaWidth)

			
		#Default options
		option=self.document().defaultTextOption()
		option.setFlags(option.IncludeTrailingSpaces|option.AddSpaceForLineAndParagraphSeparators)
		self.document().setDefaultTextOption(option)
		
		#Init properties
		self.wrap = True
		self.showWhitespace = False
		self.showLineEndings = False
		self.highlightCurrentLine = False
		
		self.spaceTabs = False
		self.tabSize = 4

	
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
	def tabSize(self):
		"""Size of a tab stop in characters"""
		return self._tabSize
		
	@tabSize.setter
	def tabSize(self,value):
		self._tabSize = int(value)
		fontMetrics=QtGui.QFontMetrics(self.font())
		self.setTabStopWidth(fontMetrics.width('i')*self._tabSize)
	
	#space tabs
	@property
	def spaceTabs(self):
		"""Wether or not to use spaces instead of tabs"""
		return self._spaceTabs
	
	@spaceTabs.setter
	def spaceTabs(self,value):
		self._spaceTabs=bool(value)
		self.highlighter.spaceTabs = self._spaceTabs
	
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
	## MISC
	def setStyle(self,style):
		#TODO: to be implemented
		pass
		
	def lineNumberAreaPaintEvent(self,event):
		painter = QtGui.QPainter(self.lineNumberArea)
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
			self.completer.popup().show()
		

		if names is not None:
			#TODO: a more intelligent implementation that adds new items and removes
			#old ones
			if names != self.completerNames:
				self.completerModel.setStringList(names)
				self.completerNames = names

		self._updateAutocompleterPrefix()
	def autocompleteAccept(self):
		pass
	def autocompleteCancel(self):
		self.completer.popup().hide()
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
		if text in self.recentCompletions:
			self.recentCompletions.remove(text)
		self.recentCompletions.append(text)
		
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
		self.completer.popup().move(self.mapToGlobal(position))
		
		#Set size
		geometry = self.completer.popup().geometry()
		geometry.setWidth(100)
		geometry.setHeight(100)
		self.completer.popup().setGeometry(geometry)
	
	def _updateAutocompleterPrefix(self):
		"""
		Find the autocompletion prefix (the part of the word that has been 
		entered) and send it to the completer
		"""
		prefix=self.toPlainText()[self._autocompleteStart:
		self.textCursor().position()]

		self.completer.setCompletionPrefix(prefix)
		model = self.completer.completionModel()
		if model.rowCount():
			#Iterate over the matches, find the one that was most recently used
			#print (self.recentCompletions)
			recentFound = -1
			recentFoundRow = 0 #If no recent match, just select the first match
			
			for row in range(model.rowCount()):
				data = model.data(model.index(row,0),self.completer.completionRole())
				if not data in self.recentCompletions:
					continue
				
				index = self.recentCompletions.index(data)
				if index > recentFound: #Later in the list = more recent
					recentFound, recentFoundRow = index, row

			
			self.completer.popup().setCurrentIndex(model.index(row,0));

				
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
		self.lineNumberArea.setGeometry(rect.x(),rect.y(),
			self.getLineNumberAreaWidth(),rect.height())

	def paintEvent(self,event):
		#Draw the default QTextEdit, then update the lineNumberArea 
		QtGui.QPlainTextEdit.paintEvent(self,event)
		self.lineNumberArea.update(0,event.rect().y(),50,event.rect().height())
		

		

	def keyPressEvent(self,event):
		key=event.key()
		if key == Qt.Key_Escape:
			self.autocompleteCancel()
			self._calltipLabel.hide()
		elif key == Qt.Key_Tab:
			if self.autocompleteActive():
				#Let the completer handle this one!
				event.ignore()
				return
			elif self.spaceTabs:
				#Insert space-tabs
				cursor=self.textCursor()
				cursor.insertText(' '*(self.tabSize-((cursor.columnNumber() + self.tabSize )%self.tabSize)))
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
		
		self.calltipShow(0, 'test(foo, bar)')


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
			
			CodeEditor.keyPressEvent(self,event)
		
	e=TestEditor()
	e.show()
	s=QtGui.QSplitter()
	s.addWidget(e)
	s.addWidget(QtGui.QLabel('test'))
	s.show()
	app.exec_()
	