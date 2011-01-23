#!/usr/bin/env python3.1
# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" iep.py

This is the entry module, it servers as a root for the other modules.

"""

import sys, os
import ssdf  # import ssdf or the suplied copy if not available
from PyQt4 import QtCore, QtGui

# Set version number
__version__ = '2.3'


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
        iepDir = os.path.join(iepDir, 'source')
    else:
        iepDir = os.path.abspath( os.path.dirname(__file__) )

    # Define user dir and appDataDir
    userDir = os.path.expanduser('~')    
    appDataDir = os.path.join(userDir, '.iep')
    if sys.platform.startswith('win') and 'APPDATA' in os.environ:
        appDataDir = os.path.join( os.environ['APPDATA'], 'iep' )
    
    # Make sure it exists, as well as a tools directory
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


def resetStyles():
    """ resetStyles()
    Replaces the style file with the default and re-applies the styles.
    """
    import shutil
    # Copy file
    styleFileName1 = os.path.join(iepDir, 'defaultStyles.ssdf')
    styleFileName2 = os.path.join(appDataDir, 'styles.ssdf')        
    shutil.copy(styleFileName1, styleFileName2)
    # Apply
    try:
        styleManager.loadStyles()
    except NameError:
        pass


def resetConfig(preserveState=True):
    """ resetConfig()
    Replaces the config fyle with the default and prevent IEP from storing
    its config on the next shutdown.
    """ 
    # Get filenames
    configFileName1 = os.path.join(iepDir, 'defaultConfig.ssdf')
    configFileName2 = os.path.join(appDataDir, 'config.ssdf')        
    # Read, edit, write
    tmp = ssdf.load(configFileName1)
    if preserveState:
        tmp.state = config.state
    ssdf.save(configFileName2, tmp)    
    global _saveConfigFile
    _saveConfigFile = False
    print("Replaced config file. Restart IEP to revert to the default config.")


def startIep():
    """ startIep()
    Run IEP.
    """
    
    # Do some imports
    import iepLogging # to start logging asap
    from main import MainWindow
    
    # Set to use pure QT drawing. 
    # On GTK this makes the fonts look better, on KDE or Mac not
    # On Windows it does not matter
    if not os.environ.get('KDE_FULL_SESSION') and sys.platform != 'darwin':
        QtGui.QApplication.setDesktopSettingsAware(False)
   
    #Prevent loading plugins form the users' plugin dir since
    #this may cause multiple versions of the Qt library to be loaded
    #at once, which will conflict
    QtGui.QApplication.setLibraryPaths([])

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
    if _saveConfigFile:
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

# Whether the config file should be saved
_saveConfigFile = True

# Get the paths
iepDir, userDir, appDataDir = getResourceDirs()

# Create ssdf in module namespace, and fill it
config = ssdf.new()
loadConfig()

# Init default style name (set in main.restoreIepState())
defaultQtStyleName = ''

def big():
    for e in editors:
        f=e.font()
        f.setPointSize(25)
        e.setFont(f)
        e.showLineNumbers = False
        e.showLineNumbers = True
    for s in shells:
        f=s.font()
        f.setPointSize(25)
        s.setFont(f)


if __name__ == "__main__":
    startIep()
