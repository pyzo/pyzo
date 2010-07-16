import sys, os, time
from PyQt4 import QtCore, QtGui
import iep 

plugin_name = "Interactive Help"
plugin_summary = "Shows help on an object when using up/down in autocomplete."


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
        self._check = QtGui.QCheckBox("No newlines", )        
        self._but = QtGui.QPushButton("Print", self)
        #
        pluginId =  self.__class__.__name__.lower()
        config = iep.config.plugins[pluginId]
        if not hasattr(config, 'noNewlines'):
            config.noNewlines = True
        self._check.setChecked(config.noNewlines)
        
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
        pluginId =  self.__class__.__name__.lower()         
        iep.config.plugins[pluginId].noNewlines = self._check.isChecked()
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
                h_text = h_text.replace("\n\n","<br /><br />")  
            else:
                # Make newlines html
                h_text = h_text.replace("\n","<br />")  
            
            # Compile rich text
            text += '<h2>{}</h2>'.format(objectName)
            text += '<b>CLASS:</b> {}<br />'.format(h_class)
            if h_fun:
                text += '<b>SIGNATURE:</b> {}<br />'.format(h_fun)
            text += '<b>REPR:</b> {}<br />'.format(h_repr)
            text += '<br />'
            text += '<b>DOC:</b><br />{}<br />'.format(h_text)
        
        except Exception:
            text = response
        
        # Done
        self._browser.setText(text)
        
        
        
