""" TOOL SOURCE STRUCTURE


"""

import time
from PyQt4 import QtCore, QtGui, QtWebKit
import iep
ssdf = iep.ssdf

tool_name = "Web browser"
tool_summary = "A simple web browser."


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
            
        # Get style object (for icons)
        style = QtGui.QApplication.style()
        
        # Create some buttons
        self._back = QtGui.QToolButton(self)
        self._back.setIcon(style.standardIcon(style.SP_ArrowBack))
        #
        self._forward = QtGui.QToolButton(self)
        self._forward.setIcon(style.standardIcon(style.SP_ArrowForward))
        #
        self._home = QtGui.QToolButton(self)
        #self._home.setIcon(style.standardIcon(style.SP_DirHomeIcon))
        self._home.setText('G')
        
        # Create address bar
        self._address = QtGui.QLineEdit(self)
        
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
        self._sizer2.addWidget(self._home, 0)
        self._sizer2.addWidget(self._address, 1)
        #
        self._sizer1.addLayout(self._sizer2, 0)
        self._sizer1.addWidget(self._view, 1)
        self.setLayout(self._sizer1)
        
        # Bind signals
        self._back.clicked .connect(self.onBack)
        self._forward.clicked .connect(self.onForward)
        self._home.clicked .connect(self.onHome)
        self._address.returnPressed.connect(self.go)
        self._view.loadFinished.connect(self.onLoad)
        
        # Start
        self._view.show()
        self.onHome()
    
    
    def parseAddress(self, address):
        if not address.startswith('http'):
            address = 'http://' + address
        return QtCore.QUrl(address, QtCore.QUrl.TolerantMode)
    
    def go(self):
        address = self._address.text()
        self._view.load( self.parseAddress(address) )
    
    def onLoad(self):
        url = self._view.url()
        address = str(url.toString())
        self._address.setText(str(address))
    
    def onBack(self):
        self._view.back()
    
    def onForward(self):
        self._view.forward()
    
    def onHome(self):
        self._view.load( self.parseAddress("www.google.com") )
    
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
            
