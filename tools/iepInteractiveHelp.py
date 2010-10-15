import sys, os, time
from PyQt4 import QtCore, QtGui
import iep 

tool_name = "Interactive Help"
tool_summary = "Shows help on an object when using up/down in autocomplete."


htmlWrap = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html>
<head><meta name="qrichtext" content="1" /><style type="text/css">
p, li {{ white-space: pre-wrap; }}
</style>
</head>
<body style=" font-family:'Sans Serif'; font-size:9pt; font-weight:400; font-style:normal;">
<p style="-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;">{}
</p>
</body></html>
"""

initText =  """
Help information is queried from the current shell<br />
when moving up/down in the autocompletion list<br />
and when double clicking on a name.
"""


class IepInteractiveHelp(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        
        # Create text field, checkbox, and button
        self._text = QtGui.QLineEdit(self)
        self._check = QtGui.QCheckBox("Smart newlines", )        
        self._but = QtGui.QPushButton("Print", self)
        #
        toolId =  self.__class__.__name__.lower()
        config = iep.config.tools[toolId]
        if not hasattr(config, 'smartNewlines'):
            config.smartNewlines = True
        self._check.setChecked(config.smartNewlines)
        
        # Create browser
        self._browser = QtGui.QTextBrowser(self)        
        self._browser.setHtml(initText)
        
        
        
        # Create two sizers
        self._sizer1 = QtGui.QVBoxLayout(self)
        self._sizer2 = QtGui.QHBoxLayout()
        
        # Put the elements together
        self.setLayout(self._sizer1)
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._browser, 1)
        self._sizer2.addWidget(self._text, 1)
        self._sizer2.addWidget(self._check, 0)
        self._sizer2.addWidget(self._but, 0)
        
        # Create callbacks
        self._text.returnPressed.connect(self.queryDoc)
        self._but.clicked.connect(self.printDoc)
        self._check.stateChanged.connect(self._onCheckChanged)
    
    
    def _onCheckChanged(self):
        # Store
        toolId =  self.__class__.__name__.lower()         
        iep.config.tools[toolId].smartNewlines = self._check.isChecked()
        # Update text
        self.queryDoc()
    
    
    def setObjectName(self, name):
        """ Set the object name programatically
        and query documentation for it. """
        self._text.setText(name)
        self.queryDoc()
    
    
    def printDoc(self):
        """ Print the doc for the text in the line edit. """
        # Get name
        name = self._text.text()
        # Tell shell to print doc
        shell = iep.shells.getCurrentShell()
        if shell and name:
            shell.processLine('print({}.__doc__)'.format(name))
    
    def queryDoc(self):
        """ Query the doc for the text in the line edit. """
        # Get name
        name = self._text.text()
        # Get shell and ask for the documentation
        shell = iep.shells.getCurrentShell()
        if shell and name:
            req = "HELP " + name
            shell.postRequest(req, self.queryDoc_response)
    
    
    def queryDoc_response(self, response, id):
        """ Process the response from the shell. """
        
        if not response:
            return
        
        try:
            # Get parts
            parts = response.split('\n')                
            objectName, h_class, h_fun, h_repr = tuple(parts[:4])                
            h_text = '\n'.join(parts[4:])
            
            # Obtain newlines that we hid
            h_repr.replace('/r', '/n')
            
            # Init text
            text = ''
            
            # These signs will fool the html
            h_repr = h_repr.replace("<","&lt;") 
            h_repr = h_repr.replace(">","&gt;")
            h_text = h_text.replace("<","&lt;") 
            h_text = h_text.replace(">","&gt;")
            
            if self._check.isChecked():
                # Dont replace single newlines, but wrap the text. New paragraphs
                # do need to be new paragraphs though...
                #h_text = h_text.replace("\n\n","<br /><br />")  
                h_text = self.smartFormat(h_text)
            else:
                # Make newlines html
                h_text = h_text.replace("\n","<br />")  
            
            # Compile rich text
            text += '<h1>{}</h1>'.format(objectName)
            text += '<b>CLASS:</b> {}<br />'.format(h_class)
            if h_fun:
                text += '<b>SIGNATURE:</b> {}<br />'.format(h_fun)
            text += '<b>REPR:</b> {}'.format(h_repr)
            text += '<h2>Docstring:</h2>{}<br />'.format(h_text)
        
        except Exception:
            text = response
        
        # Done
        self._browser.setHtml(htmlWrap.format(text))
    
    
    def smartFormat(self, text):
        
        # Get lines
        lines = text.splitlines()
        
        # Test minimal indentation
        minIndent = 9999
        for line in lines[1:]:
            line_ = line.lstrip()
            indent = len(line) - len(line_)
            if line_:
                minIndent = min(minIndent, indent)
        
        # Remove minimal indentation
        lines2 = [lines[0]]
        for line in lines[1:]:            
            lines2.append( line[minIndent:] )
        
        # Prepare        
        prevLine_ = ''
        prevIndent = 0
        prevWasHeader = False
        inExample = False
        forceNewline = False
        
        # Format line by line
        lines3 = []
        for line in lines2:
            
            
            # Get indentation
            line_ = line.lstrip()
            indent = len(line) - len(line_)
            #indentPart = line[:indent-minIndent]
            indentPart = line[:indent]
            
            if not line_:
                lines3.append("<br />")
                forceNewline = True
                continue
            
            # Indent in html
            line = "&nbsp;" * len(indentPart) + line
            
            # Determine if we should introduce a newline
            isHeader = False
            if ("---" in line or "===" in line) and indent == prevIndent:
                # Header
                lines3[-1] = '<b>' + lines3[-1] + '</b>'
                line = ''#'<br /> ' + line
                isHeader = True
                inExample = False
                # Special case, examples
                if prevLine_.lower().startswith('example'):
                    inExample = True
                else:
                    inExample = False
            elif ' : ' in line:
                tmp = line.split(' : ',1)
                line = '<br /> <u>' + tmp[0] + '</u> : ' + tmp[1]
            elif line_.startswith('* '):
                line = '<br />&nbsp;&nbsp;&nbsp;&#8226;' + line_[2:]
            elif prevWasHeader or inExample or forceNewline:
                line = '<br /> ' + line
            else:
                line = " " + line_
            
            # Force next line to be on a new line if using a colon
            if ' : ' in line:
                forceNewline = True
            else:
                forceNewline = False
            
            # Prepare for next line
            prevLine_ = line_
            prevIndent = indent
            prevWasHeader = isHeader
            
            # Done with line
            lines3.append(line)
        
        # Done formatting
        return ''.join(lines3)
    
