from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

from . import parsers
from .misc import ustr


class BlockData(QtGui.QTextBlockUserData):
    """ Class to represent the data for a block.
    """
    def __init__(self):
        QtGui.QTextBlockUserData.__init__(self)
        self.indentation = None


# The highlighter should be part of the base class, because 
# some extensions rely on them (e.g. the indent guuides).
class Highlighter(QtGui.QSyntaxHighlighter):
    
    def __init__(self,codeEditor,*args):
        QtGui.QSyntaxHighlighter.__init__(self,*args)
        
        #Init properties
        self._codeEditor = codeEditor
        self._nameToFormat = {}
        self._parser = parsers.ParserManager.getParserByName('python')
        if self._parser:            
            self.createFormats( self._parser.getDefaultStyle() )
        
#         pp = parsers.ParserManager.getParserByName('python')
#         print('-- token names --')
#         for info in pp.getStyleInfo():
#             print(info[0])
#         print('-- end token names --')
    
    
    def _getColorSafe(self, color, default='#777'):
        try:
            return QtGui.QColor(color)
        except Exception:
            print('Invalid color', color)
            return QtGui.QColor(default)
    
    
    def createFormats(self, style):
        
        # Init dict
        self._nameToFormat = {}
        
        # For each style (i.e. token)
        for name in style:
            styleFormat = style[name]
            
            # Init format
            format = QtGui.QTextCharFormat()
            self._nameToFormat[name] = format
            
            for key, val in styleFormat:
                
                # Process, be forgiving with names
                if key == 'fore':
                    format.setForeground( self._getColorSafe(val) )
                elif key == 'back':
                    format.setBackground( self._getColorSafe(val) )
                elif key == 'bold':
                    if val == 'yes':
                        format.setFontWeight(QtGui.QFont.Bold)
                elif key == 'underline':
                    if val=='yes':
                        format.setUnderlineStyle (format.SingleUnderline)
                    elif val in ['dotted', 'dots', 'dotline']: 
                        format.setUnderlineStyle (format.DotLine)
                    elif val=='wave': 
                        format.setUnderlineStyle (format.WaveUnderline)
                elif key == 'italic':
                    if val=='yes':
                        format.setFontItalic(True)
                else:
                    print('Warning: unknown style element part "%s" in "%s".' % 
                                                    (key, str(styleFormat)))
    
    
    def getCurrentBlockUserData(self):
        """ getCurrentBlockUserData()
        
        Gets the BlockData object. Creates one if necesary.
        
        """
        bd = self.currentBlockUserData()
        if not isinstance(bd, BlockData):
            bd = BlockData()
            self.setCurrentBlockUserData(bd)
        return bd
    
    
    def highlightBlock(self,line): 
        
        # Mae sure this is a Unicode Python string
        line = ustr(line)
        
        previousState=self.previousBlockState()
        
        # todo: choose parser dynamically
        
        if self._parser:
            self.setCurrentBlockState(0)
            for token in self._parser.parseLine(line,previousState):
                #Handle line or string continuation
                if isinstance(token, parsers.tokens.ContinuationToken):
                    self.setCurrentBlockState(token.state)
                else:
                    # Get format
                    try:
                        format = self._nameToFormat[token.name]
                    except KeyError:
                        continue
                    # Set format
                    self.setFormat(token.start,token.end-token.start,format)
                
        
        #Get the indentation setting of the editors
        indentUsingSpaces = self._codeEditor.indentUsingSpaces()
        
        # Get user data
        bd = self.getCurrentBlockUserData()
        
        leadingWhitespace=line[:len(line)-len(line.lstrip())]
        if '\t' in leadingWhitespace and ' ' in leadingWhitespace:
            #Mixed whitespace
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.red)
            format.setToolTip('Mixed tabs and spaces')
            self.setFormat(0,len(leadingWhitespace),format)
        elif ('\t' in leadingWhitespace and indentUsingSpaces) or \
            (' ' in leadingWhitespace and not indentUsingSpaces):
            #Whitespace differs from document setting
            bd.indentation = 0
            format=QtGui.QTextCharFormat()
            format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)
            format.setUnderlineColor(QtCore.Qt.blue)
            format.setToolTip('Whitespace differs from document setting')
            self.setFormat(0,len(leadingWhitespace),format)
        else:
            # Store info for indentation guides
            # amount of tabs or spaces
            bd.indentation = len(leadingWhitespace)
