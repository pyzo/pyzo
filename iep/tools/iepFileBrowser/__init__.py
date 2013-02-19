# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

tool_name = "File browser"
tool_summary = "Browse the files in your projects."


""" File browser tool

Config
======

The config consists of three fields:

  * list expandedDirs, with each element a directory 
  * list starredDirs, with each element a dict with fields:
      * str path, the directory that is starred
      * str name, the name of the project (path.basename by default)
      * bool addToPythonpath
  * searchMatchCase, searchRegExp, searchSubDirs
  * nameFilter

"""

# todo: List!
"""
  * see easily which files are opened (so it can be used as a secondary tab bar)
    maybe even use same icon, maybe not.
  * make visible the "current file" (if applicable)
  * single click on an file that is open selects it in the editor?
  * context menu to: create files/dirs, rename/delete files, run scripts?, etc.
  * More stuff to make it a proper file manager.
  * if in a subdir of a project, is the project active?
  * Only remember expanded dirs when a subdir of a starred dir?
  * Support for multiple browsers.
  
"""

import os
import sys

from pyzolib import ssdf
from pyzolib.path import Path

from iep.codeeditor.qt import QtCore, QtGui
import iep

from .browser import Browser



class IepFileBrowser(QtGui.QWidget):
    """ The main tool widget. An instance of this class contains one or
    more Browser instances. If there are more, they can be selected
    using a tab bar.
    """
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Get config
        toolId =  self.__class__.__name__.lower() + '2'  # This is v2 of the file browser
        if toolId not in iep.config.tools:
            iep.config.tools[toolId] = ssdf.new()
        self.config = iep.config.tools[toolId]
        
        # Ensure three main attributes in config
        for name in ['expandedDirs', 'starredDirs']:
            if name not in self.config:
                self.config[name] = []
        
        # Ensure path in config
        if 'path' not in self.config or not os.path.isdir(self.config.path):
            self.config.path = os.path.expanduser('~')
        
        # Check expandedDirs and starredDirs. 
        # Make Path instances and remove invalid dirs. Also normalize case, 
        # should not be necessary, but maybe the config was manually edited.
        expandedDirs, starredDirs = [], []
        for p in set([str(p) for p in self.config.expandedDirs]):
            if os.path.isdir(p):
                expandedDirs.append( Path(p).normcase() )
        for d in self.config.starredDirs:
            if 'path' in d and 'name' in d and 'addToPythonpath' in d:
                if os.path.isdir(d.path):
                    d.path = Path(d.path).normcase()
                    starredDirs.append(d)
        self.config.expandedDirs, self.config.starredDirs = expandedDirs, starredDirs
        
        # Create browser(s).
        self._browsers = []
        for i in [0]:
            self._browsers.append( Browser(self, self.config) )
        
        # Layout
        layout = QtGui.QVBoxLayout(self)
        self.setLayout(layout)
        layout.addWidget(self._browsers[0])
        layout.setSpacing(0)
        layout.setContentsMargins(4,4,4,4)
    
    
    def closeEvent(self, event):
        # Close all browsers so they can clean up the file system proxies
        for browser in self._browsers:
            browser.close()
        return QtGui.QWidget.closeEvent(self, event)
