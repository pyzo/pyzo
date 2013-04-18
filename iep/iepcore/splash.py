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
from iep.codeeditor.qt import QtCore, QtGui

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
    background: #46abf2;
    border-radius:20px;
}
"""

license_text1 = """
<b>This is the Interactive Editor for Python</b>
<p>
Your current license: <i>free license</i><br />
Licensed to: <i>unregistered</i>
</p>

<p>
IEP is open source software and is available for everyone for free.
If you like IEP and would like to support its development,
consider purchasing a license at 
<a href='http://pyzo.org/license.html'>http://pyzo.org</a>.
</p>
"""

license_text2 = """
<b>This is the Interactive Editor for Python</b>
<p>
Your current license: <i>basic license</i><br />
Licensed to: <i>Almar Klein</i>
</p>

"""


class LogoWidget(QtGui.QFrame):
    def __init__(self, parent):
        QtGui.QFrame.__init__(self, parent)
        self.setMinimumSize(256, 256)
        self.setMaximumSize(256, 256)


class LabelWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Create label widget and costumize
        self._label = QtGui.QLabel(self)
        self._label.setTextFormat(QtCore.Qt.RichText)
        self._label.setOpenExternalLinks(True)
        self._label.setWordWrap(True)
        self._label.setMargin(20)
        
        # Set font a wee bit larger
        font = self._label.font()
        font.setPointSize(font.pointSize()+1)
        self._label.setFont(font)
        
        # Set text
        self._label.setText(license_text1)
        
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addStretch(1)
        layout.addWidget(self._label, 0)
        layout.addStretch(1)
        
        
        

class SplashWidget(QtGui.QWidget):
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        self._left = LogoWidget(self)
        self._right = LabelWidget(self)
        
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
        iconImage = 'pyzologo256.png' if iep.pyzo_mode else 'ieplogo256.png'
        iconImage = os.path.join(iep.iepDir, 'resources','appicons', iconImage)
        iconImage = iconImage.replace(os.path.sep, '/') # Fix for Windows
        self.setStyleSheet( STYLESHEET % iconImage)

w = SplashWidget(None)
w.resize(500,300)
w.show()
