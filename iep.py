#!/usr/bin/python3.1
#   $Author: almar $
#   $Date: 2008-09-30 10:26:38 +0200 (Tue, 30 Sep 2008) $
#   $Rev: 557 $
#
#   Copyright 2008 Almar Klein
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" IEP - Interactive Editor for Python
This is the main module, where I define some stuff to be used in the other
modules.

"""

import sys, os
import ssdf  # import ssdf or the suplied copy if not available
from PyQt4 import QtCore, QtGui

# Set version number
__version__ = '2.0.1a'


## Define some functions


def isFrozen():
    """ isFrozen()
    Find out whether this IEP is a frozen application
    (using cx_freeze, bbfreeze, py2exe) by finding out what was
    the executable name to start the application.
    """
    ex = os.path.split(sys.executable)[1]
    ex = os.path.splitext(ex)[0]
    if ex.lower().startswith('python'): # because can be python3 on Linux
        return False
    else:
        return True


def getResourceDirs():
    """ getResourceDirs()
    Get the directories to the resources: (iepDir, userDir, appDataDir).
    Also makes sure that the appDataDir has a "tools" directory and
    a style file.
    """
    
    # Get directory where IEP is located
    if isFrozen():
        iepDir =  os.path.abspath( os.path.dirname(sys.executable) )
    else:
        iepDir = os.path.abspath( os.path.dirname(__file__) )

    # Define user dir and appDataDir
    userDir = os.path.expanduser('~')    
    appDataDir = os.path.join(userDir, '.iep')
    if sys.platform.startswith('win') and 'APPDATA' in os.environ:
        appDataDir = os.path.join( os.environ['APPDATA'], 'iep' )
    
    # Make sure it exists, as well as the tools directory
    if not os.path.isdir(appDataDir):
        os.mkdir(appDataDir)
    toolDir = os.path.join(appDataDir, 'tools')
    if not os.path.isdir(toolDir):
        os.mkdir(toolDir)
    
    # Make sure the style file is there
    styleFileName1 = os.path.join(iepDir, 'defaultStyles.ssdf')
    styleFileName2 = os.path.join(appDataDir, 'styles.ssdf')
    if not os.path.isfile(styleFileName2):
        import shutil        
        shutil.copy(styleFileName1, styleFileName2)
    
    # Done
    return iepDir, userDir, appDataDir


def startIep():
    """ startIep()
    Run IEP.
    """
    
    # Do some imports
    import logging # to start logging asap
    from main import MainWindow
    
    # Set to use pure QT drawing (for consistent looks)
    QtGui.QApplication.setDesktopSettingsAware(False)
    
    # Instantiate the application, and the main window
    QtGui.qApp = QtGui.QApplication([])
    frame=MainWindow()
    
    # Enter the main loop
    QtGui.qApp.exec_()


def loadConfig(defaultsOnly=False):
    """ loadConfig(defaultsOnly=False)
    Load default configuration file and that of the user (if it exists).
    Any missing fields in the user config are set to the defaults. 
    """
    
    # Function to insert names from one config in another
    def replaceFields(base, new):
        for key in new:
            if key in base and isinstance(base[key], ssdf.Struct):                
                replaceFields(base[key], new[key])
            else:
                base[key] = new[key]
    
    # Reset our iep.config structure
    ssdf.clear(config)
    
    # Load default and inject in the iep.config
    fname = os.path.join(iepDir, "defaultConfig.ssdf")
    defaultConfig = ssdf.load(fname)
    replaceFields(config, defaultConfig)
    
    # Load user config and inject in iep.config
    fname = os.path.join(appDataDir, "config.ssdf")
    if os.path.isfile(fname):
        userConfig = ssdf.load(fname)
        replaceFields(config, userConfig)
    

def saveConfig():
    """ saveConfig()
    Save all configureations to file. 
    """ 
    
    # Let the editorStack save its state 
    if editors:
        editors.saveEditorState()
    
    # Let the main window save its state 
    if main:
        main.saveWindowState()
    
    # Store config
    ssdf.save( os.path.join(appDataDir, "config.ssdf"), config )


## Init

# List of names that are later overriden (in main.py)
editors = None # The editor stack instance
shells = None # The shell stack instance
main = None # The mainwindow
icon = None # The icon 
parser = None # The source parser
status = None # The statusbar (or None)
styleManager = None # Object that manages syntax styles

# Get the paths
iepDir, userDir, appDataDir = getResourceDirs()

# Create ssdf in module namespace, and fill it
config = ssdf.new()
loadConfig()

# Init default style name (set in main.restoreIepState())
defaultQtStyleName = ''


if __name__ == "__main__":
    startIep()
