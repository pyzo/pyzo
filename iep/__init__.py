#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2012, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Package iep

IEP (pronounced as 'eep') is a cross-platform Python IDE focused on
interactivity and introspection, which makes it very suitable for
scientific computing. Its practical design is aimed at simplicity and
efficiency.

IEP is written in Python 3 and Qt. Binaries are available for Windows,
Linux, and Mac. For questions, there is a discussion group.

Two components + tools
----------------------

IEP consists of two main components, the editor and the shell, and uses
a set of pluggable tools to help the programmer in various ways. Some
example tools are source structure, project manager, interactive help,
and workspace.

Some key features
-----------------

  * Powerful *introspection* (autocompletion, calltips, interactive help)
  * Allows various ways to *run code interactively* or to run a file as a
    script.
  * The shells runs in a *subprocess* and can therefore be interrupted or
    killed.
  * *Multiple shells* can be used at the same time, and can be of different
    Python versions (from v2.4 to 3.x, including pypy)
  * Support for using several *GUI toolkits* interactively: PySide, PyQt4,
    wx, fltk, GTK, Tk.
  * Supports *magic commands* similar to IPython.
  * *Full Unicode support* in both editor and shell.
  * Various handy *tools*, plus the ability to make your own.
  * Matlab-style *cell notation* to mark code sections (by starting a line
    with '##').
  * Highly customizable using the menu.

"""

# Set version number
__version__ = '3.1.dev'


 # Fix for issue 137 (apply before importing PySide, just to be safe)
import os
os.environ['LIBOVERLAY_SCROLLBAR'] = '0'

import sys
from pyzolib import ssdf, paths
from iep.codeeditor.qt import QtCore, QtGui

# Import yoton as an absolute package
from iep import yotonloader

# Import language/translation tools
from iep.util.locale import translate, setLanguage


## Define some functions


# todo: move some stuff out of this module ...

def getResourceDirs():
    """ getResourceDirs()
    Get the directories to the resources: (iepDir, appDataDir).
    Also makes sure that the appDataDir has a "tools" directory and
    a style file.
    """
    
#     # Get root of the IEP code. If frozen its in a subdir of the app dir 
#     iepDir = paths.application_dir()
#     if paths.is_frozen():
#         iepDir = os.path.join(iepDir, 'source')
    iepDir = os.path.abspath(os.path.dirname(__file__))
    if '.zip' in iepDir:
        raise RuntimeError('The IEP package cannot be run from a zipfile.')
    
    # Get where the application data is stored (use old behavior on Mac)
    # todo: quick solution until I release a new pyzolib
    try:
        appDataDir = paths.appdata_dir('iep', roaming=True, macAsLinux=True)
    except Exception:
        appDataDir = paths.appdata_dir('iep', roaming=True)
    
    # Create tooldir if necessary
    toolDir = os.path.join(appDataDir, 'tools')
    if not os.path.isdir(toolDir):
        os.mkdir(toolDir)
    
    return iepDir, appDataDir


def resetConfig(preserveState=True):
    """ resetConfig()
    Replaces the config fyle with the default and prevent IEP from storing
    its config on the next shutdown.
    """ 
    # Get filenames
    configFileName1 = os.path.join(iepDir, 'resources', 'defaultConfig.ssdf')
    configFileName2 = os.path.join(appDataDir, 'config.ssdf')        
    # Read, edit, write
    tmp = ssdf.load(configFileName1)
    if preserveState:
        tmp.state = config.state
    ssdf.save(configFileName2, tmp)    
    global _saveConfigFile
    _saveConfigFile = False
    print("Replaced config file. Restart IEP to revert to the default config.")


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
    fname = os.path.join(iepDir, 'resources', 'defaultConfig.ssdf')
    defaultConfig = ssdf.load(fname)
    replaceFields(config, defaultConfig)
    
    # Platform specific keybinding: on Mac, Ctrl+Tab (actually Cmd+Tab) is a system shortcut
    if sys.platform == 'darwin':
        config.shortcuts2.view__select_previous_file = 'Alt+Tab,'
    
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





def startIep():
    """ startIep()
    Run IEP.
    """
    
    # Do some imports
    from iep.iepcore import iepLogging # to start logging asap
    from iep.iepcore.main import MainWindow
    
    # Set to be aware of the systems native colors, fonts, etc.
    QtGui.QApplication.setDesktopSettingsAware(True)
    
    #Prevent loading plugins form the users' plugin dir since
    #this may cause multiple versions of the Qt library to be loaded
    #at once, which will conflict
    QtGui.QApplication.setLibraryPaths([])
    
    # Instantiate the application
    QtGui.qApp = QtGui.QApplication([])
    
    # Choose language, get locale
    locale = setLanguage(config.settings.language)
    
    # Create main window, using the selected locale
    frame = MainWindow(None, locale)
    
    # Enter the main loop
    QtGui.qApp.exec_()


## Init

# List of names that are later overriden (in main.py)
editors = None # The editor stack instance
shells = None # The shell stack instance
main = None # The mainwindow
icon = None # The icon 
parser = None # The source parser
status = None # The statusbar (or None)

# Get directories of interest
iepDir, appDataDir = getResourceDirs()

# Whether the config file should be saved
_saveConfigFile = True

# Create ssdf in module namespace, and fill it
config = ssdf.new()
loadConfig()

# Init default style name (set in main.restoreIepState())
defaultQtStyleName = ''

# Init pyzo_mode. In pyzo_mode, IEP will use a different logo and possibly
# expose certain features in the future.
pyzo_mode = False

# Init default exe for the executable (can be set, e.g. by Pyzo)
_defaultInterpreterExe = None
_defaultInterpreterGui = None
def setDefaultInterpreter(exe, gui=None):
    global _defaultInterpreterExe
    global _defaultInterpreterGui
    assert isinstance(exe, str)
    _defaultInterpreterExe = exe
    _defaultInterpreterGui = gui
def defaultInterpreterExe():
    global _defaultInterpreterExe
    if _defaultInterpreterExe is None and sys.platform.startswith('win'):
        try:
            from pyzolib.interpreters import get_interpreters
            interpreters = list(reversed(get_interpreters('2.4')))
            if interpreters:
                _defaultInterpreterExe = interpreters[0].path
        except Exception as err:
            print(err)
    if _defaultInterpreterExe is None:
        _defaultInterpreterExe = 'python'
    return _defaultInterpreterExe
def defaultInterpreterGui():
    global _defaultInterpreterGui 
    return _defaultInterpreterGui
