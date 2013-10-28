# -*- coding: utf-8 -*-
# Copyright (C) 2013, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module splash

Defines splash window shown during startup.

"""

import os, sys, time

import iep
from pyzolib.qt import QtCore, QtGui


STYLESHEET = """
QWidget { 
    background-color: #268bd2;
}
QFrame {
    background-image: url("%s");
    background-repeat: no-repeat;
    background-position: center;
}
QLabel { 
    color: #222;
    background: #46abf2;
    border-radius:20px;
}
"""

license_text1 = """
<p>
This is the <b>Interactive Editor for Python</b>
%s
</p>
<p>
Your current license: <i>LICENSE_TYPE</i><br />
Licensed to: <i>LICENSE_NAME</i>
</p>

"""

license_ad_text = """
<p>
IEP is open source software and freely available for everyone. If you
like IEP and want to support its development, consider purchasing a
license.
</p>
<p>
Read more at
<a href='http://www.iep-project.org/contributing.html'>http://iep-project.org</a>
</p>
"""


class LogoWidget(QtGui.QFrame):
    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)
        self.setMinimumSize(256, 256)
        self.setMaximumSize(256, 256)



class LabelWidget(QtGui.QWidget):
    def __init__(self, parent, distro=None):
        QtGui.QWidget.__init__(self, parent)
        self.setMinimumSize(360, 256)  # Ensure title fits nicely
        
        # Create label widget and costumize
        self._label = QtGui.QLabel(self)
        self._label.setTextFormat(QtCore.Qt.RichText)
        self._label.setOpenExternalLinks(True)
        self._label.setWordWrap(True)
        self._label.setMargin(20)
        
        # Set font size (absolute value)
        font = self._label.font()
        font.setPointSize(11)  #(font.pointSize()+1)
        self._label.setFont(font)
        
        # Build
        text = license_text1
        if distro:
            text = text % '<br />brought to you by %s.' % distro
        else:
            text = text % ''
        if not iep.license:
            text = text.replace('LICENSE_TYPE', 'free license')
            text = text.replace('LICENSE_NAME', 'unregistered')
            text += license_ad_text
        else:
            text = text.replace('LICENSE_TYPE', iep.license['product'])
            text = text.replace('LICENSE_NAME', iep.license['name'])
        
        # Set text
        self._label.setText(text)
        
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addStretch(1)
        layout.addWidget(self._label, 0)
        layout.addStretch(1)



class SplashWidget(QtGui.QWidget):
    """ A splash widget that shows the license text.
    """
    def __init__(self, parent, **kwargs):
        QtGui.QWidget.__init__(self, parent)
        
        self._left = LogoWidget(self)
        self._right = LabelWidget(self, **kwargs)
        
        # Layout
        layout = QtGui.QHBoxLayout(self)
        self.setLayout(layout)
        #layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(25)
        layout.addStretch(1)
        layout.addWidget(self._left, 0)
        layout.addWidget(self._right, 0)
        layout.addStretch(1)
        
        # Change background of main window to create a splash-screen-efefct
        iconImage = 'ieplogo256.png'
        iconImage = os.path.join(iep.iepDir, 'resources','appicons', iconImage)
        iconImage = iconImage.replace(os.path.sep, '/') # Fix for Windows
        self.setStyleSheet(STYLESHEET % iconImage)
        
        



if __name__ == '__main__':
    iep.license = {'name': 'John Doe', 'product': 'IEP pro license XL'}
    w = SplashWidget(None, distro='some arbitrary distro')
    w.resize(800,600)
    w.show()
