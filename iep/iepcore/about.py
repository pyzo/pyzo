
import os
import sys

from pyzolib import paths
import iep
from pyzolib.qt import QtCore, QtGui


class AboutDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(iep.translate("menu dialog", "About IEP"))
        self.resize(600,500)
        
        # Layout
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        
        # Create image and title
        im = QtGui.QPixmap( os.path.join(iep.iepDir, 
                            'resources', 'appicons', 'ieplogo64.png') )
        imlabel = QtGui.QLabel(self)
        imlabel.setPixmap(im)
        textlabel = QtGui.QLabel(self)
        textlabel.setText('<h3>IEP: the Interactive Editor for Python</h3>')
        #
        titleLayout = QtGui.QHBoxLayout()
        titleLayout.addWidget(imlabel, 0)
        titleLayout.addWidget(textlabel, 1)
        #
        layout.addLayout(titleLayout, 0)
        
        # Create tab bar
        self._tabs = QtGui.QTabWidget(self)
        self._tabs.setDocumentMode(True)
        layout.addWidget(self._tabs, 1)
        
        # Create button box
        self._butBox = QtGui.QDialogButtonBox(self)
        self._butBox.setOrientation(QtCore.Qt.Horizontal)
        self._butBox.setStandardButtons(self._butBox.Close)
        layout.addWidget(self._butBox, 0)
        
        # Signals
        self._butBox.rejected.connect(self.close)
        
        # Create tabs
        self.createGeneralTab()
        self.createContributorsTab()
        self.createLicenseTab()
        #
        from iep.iepcore.license import LicenseManager
        self._tabs.addTab(LicenseManager(self._tabs), 'Your licenses')
    
    
    def addTab(self, title, text, rich=True):
        # Create label to show info
        label = QtGui.QTextEdit(self)
        label.setLineWrapMode(label.WidgetWidth)
        label.setReadOnly(True)
        # Set text
        if rich:
            label.setHtml(text)
        else:
            label.setText(text)
        # Add to tab bar
        self._tabs.addTab(label, title)
        # Done
        return label
    
    
    def createGeneralTab(self):
        aboutText = """
        {}<br><br>
        
        <b>Version info</b><br>
        IEP version: <u>{}</u><br>
        Platform: {}<br>
        Python version: {}<br>
        Qt version: {}<br>
        {} version: {}<br>
        <br>
        
        <b>IEP directories</b><br>
        IEP source directory: {}<br>
        IEP userdata directory: {}<br>
        <br>
        
        <b>Acknowledgements</b><br>
        IEP is written in Python 3 and uses the Qt widget
        toolkit. IEP uses code and concepts that are inspired by 
        IPython, Pype, and Spyder.
        IEP uses a (modified) subset of the silk icon set, 
        by Mark James (http://www.famfamfam.com/lab/icons/silk/).
        """
        # Determine license text
        licenseText = 'This copy of IEP is not registered (using the free license).'
        if iep.license:
            if iep.license['company']:
                licenseText = 'This copy of IEP is registered to {name} of {company}.'
            else:
                licenseText = 'This copy of IEP is registered to {name}.'
            licenseText = licenseText.format(**iep.license)
        # Determine if this is PyQt4 or Pyside
        if hasattr(QtCore, 'PYQT_VERSION_STR'):
            qtWrapper = 'PyQt4'
            qtVersion = QtCore.QT_VERSION_STR
            qtWrapperVersion = QtCore.PYQT_VERSION_STR
        else:
            import PySide
            qtWrapper = 'PySide'
            qtVersion = QtCore.__version__
            qtWrapperVersion = PySide.__version__
        # Insert information texts
        if paths.is_frozen():
            versionText = iep.__version__ + ' (binary)'
        else:
            versionText = iep.__version__ + ' (source)'
        aboutText = aboutText.format(licenseText, versionText, 
                        sys.platform, sys.version.split(' ')[0],
                        qtVersion, qtWrapper, qtWrapperVersion,
                        iep.iepDir, iep.appDataDir)
        
        self.addTab("General", aboutText)
    
    
    def createContributorsTab(self):
        fname = os.path.join(iep.iepDir, 'contributors.txt')
        try:
            with open(fname, 'rb') as f:
                text = f.read().decode('utf-8', 'ignore').strip()
        except Exception as err:
            text = str(err)
        label = self.addTab('Contributors', text, False)
        # Decrease font
        font = label.font()
        font.setPointSize(int(font.pointSize()*0.9))
        label.setFont(font)
    
    
    def createLicenseTab(self):
        fname = os.path.join(iep.iepDir, 'license.txt')
        try:
            with open(fname, 'rb') as f:
                text = f.read().decode('utf-8', 'ignore').strip()
        except Exception as err:
            text = str(err)
        label = self.addTab('BSD license', text, False)
        # Decrease font
        font = label.font()
        font.setPointSize(int(font.pointSize()*0.9))
        label.setFont(font)
        

if __name__ == '__main__':
    #iep.license = {'name': 'AK', 'company': ''}
    m = AboutDialog(None)
    m.show()
    