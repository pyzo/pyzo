# -*- coding: utf-8 -*-
# Copyright (C) 2013, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

tool_name = "File browser"
tool_summary = "Browse the files in your projects."


""" File browser tool

A powerfull tool for managing your projects in a lightweight manner.
It has a few file management utilities as well.


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
  * make visible the "current file" (if applicable)
  * single click on an file that is open selects it in the editor?
  * context menu items to run scripts  
  * Support for multiple browsers.
  
"""

import os
import sys

from pyzolib import ssdf
from pyzolib.path import Path

from pyzolib.qt import QtCore, QtGui
import pyzo

from .browser import Browser



class PyzoFileBrowser(QtGui.QWidget):
    """ The main tool widget. An instance of this class contains one or
    more Browser instances. If there are more, they can be selected
    using a tab bar.
    """
    
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        
        # Get config
        toolId =  self.__class__.__name__.lower() + '2'  # This is v2 of the file browser
        if toolId not in pyzo.config.tools:
            pyzo.config.tools[toolId] = ssdf.new()
        self.config = pyzo.config.tools[toolId]
        
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
        for d in self.config.starredDirs:
            if 'path' in d and 'name' in d and 'addToPythonpath' in d:
                if os.path.isdir(d.path):
                    d.path = Path(d.path).normcase()
                    starredDirs.append(d)
        for p in set([str(p) for p in self.config.expandedDirs]):
            if os.path.isdir(p):
                p = Path(p).normcase()
                # Add if it is a subdir of a starred dir
                for d in starredDirs:
                    if p.startswith(d.path):
                        expandedDirs.append(p)
                        break
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
    
    
    def getAddToPythonPath(self):
        """
        Returns the path to be added to the Python path when starting a shell
        If a project is selected, which has the addToPath checkbox selected,
        returns the path of the project. Otherwise, returns None
        """
        # Select browser
        browser = self._browsers[0]
        # Select active project
        d = browser.currentProject()
        if d and d.addToPythonpath:
            return d.path
        return None
    
    
    def getDefaultSavePath(self):
        """
        Returns the path to be used as default when saving a new file in pyzo.
        Or None if the no path could be determined
        """
        # Select current browser
        browser = self._browsers[0]
        # Select its path
        path = browser._tree.path()
        # Return
        if os.path.isabs(path) and os.path.isdir(path):
            return path
    
    
    def closeEvent(self, event):
        # Close all browsers so they can clean up the file system proxies
        for browser in self._browsers:
            browser.close()
        return QtGui.QWidget.closeEvent(self, event)
