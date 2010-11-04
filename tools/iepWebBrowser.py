""" TOOL SOURCE STRUCTURE


"""

import time
from PyQt4 import QtCore, QtGui, QtWebKit
import iep
ssdf = iep.ssdf

tool_name = "Web browser"
tool_summary = "A simple web browser."


default_bookmarks = [   'google.com', 
                        'docs.python.org', 
                        'doc.qt.nokia.com/4.5/',
                        'code.google.com/p/iep', 
                        'm.xkcd.com' ]


class WebView(QtWebKit.QWebView):
    """ Inherit the webview class to implement zooming using
    the mouse wheel. 
    """
    def wheelEvent(self, event):
        if QtCore.Qt.ControlModifier & QtGui.qApp.keyboardModifiers():
            self.parent().wheelEvent(event)
        else:
            QtWebKit.QWebView.wheelEvent(self, event)


class IepWebBrowser(QtGui.QFrame):
    """ The main window, containing buttons, address bar and
    browser widget.
    """
    
    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)
        
        # Init config
        toolId =  self.__class__.__name__.lower()
        self._config = iep.config.tools[toolId]
        if not hasattr(self._config, 'zoomFactor'):
            self._config.zoomFactor = 1.0
        if not hasattr(self._config, 'bookMarks'):
            self._config.bookMarks = default_bookmarks
            
        # Get style object (for icons)
        style = QtGui.QApplication.style()
        
        # Create some buttons
        self._back = QtGui.QToolButton(self)
        self._back.setIcon(style.standardIcon(style.SP_ArrowBack))
        #
        self._forward = QtGui.QToolButton(self)
        self._forward.setIcon(style.standardIcon(style.SP_ArrowForward))
        
        # Create address bar
        #self._address = QtGui.QLineEdit(self)
        self._address = QtGui.QComboBox(self)
        self._address.setEditable(True)
        self._address.setInsertPolicy(self._address.NoInsert)
        #
        for a in self._config.bookMarks:
            self._address.addItem(a)
        self._address.setEditText('') 
        
        # Create web view
        self._view = WebView()
        #
        self._view.setZoomFactor(self._config.zoomFactor)
        settings = self._view.settings()
        settings.setAttribute(settings.JavascriptEnabled, True)
        settings.setAttribute(settings.PluginsEnabled, True)
        
        # Layout
        self._sizer1 = QtGui.QVBoxLayout(self)
        self._sizer2 = QtGui.QHBoxLayout()
        #
        self._sizer2.addWidget(self._back, 0)
        self._sizer2.addWidget(self._forward, 0)
        self._sizer2.addWidget(self._address, 1)
        #
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._view, 1)
        self.setLayout(self._sizer1)
        
        # Bind signals
        self._back.clicked .connect(self.onBack)
        self._forward.clicked .connect(self.onForward)
        self._address.lineEdit().returnPressed.connect(self.go)
        self._address.activated.connect(self.go)
        self._view.loadFinished.connect(self.onLoadEnd)
        self._view.loadStarted.connect(self.onLoadStart)
        
        # Start
        self._view.show()
        self.go('www.google.com')
    
    
    def parseAddress(self, address):
        if not address.startswith('http'):
            address = 'http://' + address
        return QtCore.QUrl(address, QtCore.QUrl.TolerantMode)
    
    def go(self, address=None):
        if not isinstance(address, str):
            address = self._address.currentText()
        self._view.load( self.parseAddress(address) )
    
    def onLoadStart(self):
        self._address.setEditText('<loading>')
    
    def onLoadEnd(self, ok):
        if ok:
            url = self._view.url()
            address = str(url.toString())
        else:
            address = '<could not load page>'
        self._address.setEditText(str(address))
    
    def onBack(self):
        self._view.back()
    
    def onForward(self):
        self._view.forward()
    
    def wheelEvent(self, event):
        if QtCore.Qt.ControlModifier & QtGui.qApp.keyboardModifiers():
            # Get amount of scrolling
            degrees = event.delta() / 8.0
            steps = degrees / 15.0      
            # Set factor
            factor = self._view.zoomFactor() + steps/10.0
            if factor < 0.25:
                factor = 0.25
            if factor > 4.0:
                factor = 4.0
            # Store and apply
            self._config.zoomFactor = factor
            self._view.setZoomFactor(factor)
        else:
            QtGui.QFrame.wheelEvent(self, event)
            
