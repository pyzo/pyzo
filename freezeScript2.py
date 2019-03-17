#!/usr/bin/env python3

""" FREEZING Pyzo WITH PYINSTALLER

Pyzo is frozen in such a way that it still uses the plain source code.
This is achieved by putting the Pyzo package in a subdirectory called
"source". This source directory is added to sys.path by __main__.py.

For distribution:
  * Write release notes
  * Update __version__
  * Build binaries for Windows, Linux and Mac
  * Upload binaries to pyzo website
  * Upload source to pypi
  * Announce

  * Add tag to released commit
  * Incease version number to dev

"""

import os
import sys
import shutil

import PyInstaller.__main__


# Define app name and such
name = "pyzo"
baseDir = os.path.abspath('') + '/'
srcDir = baseDir + 'pyzo/'
distDir = baseDir + 'frozen/'
iconFile = srcDir + 'resources/appicons/pyzologo.ico'

sys.path.insert(0, '')


## Includes and excludes

# The Qt toolkit that we use
QT_API = 'PyQt5'

# All known Qt toolkits, mainly to exlcude them
qt_kits = {"PySide", "PySide2", "PyQt4", "PyQt5"}

# Imports that PyInstaller may have missed, or that are simply common/useful
# and may be used by some tools.
includes = ['code', 'shutil']

# Exclude stuff that somehow gets, or may get, selected by PyInstaller
excludes = ['numpy', 'scipy', 'win32com', 'conda', 'pip', 'IPython']

# Excludes for tk
tk_excludes = ["pywin", "pywin.debugger", "pywin.debugger.dbgcon",
               "pywin.dialogs", "pywin.dialogs.list",
               "Tkconstants", "Tkinter", "tcl"]
excludes.extend(tk_excludes)

# Excludes for Qt
qt_excludes = ['QtNetwork', 'QtOpenGL', 'QtXml', 'QtTest', 'QtSql', 'QtSvg',
               'QtBluetooth', 'QtDBus', 'QtDesigner', 'QtLocation', 'QtPositioning',
               'QtMultimedia', 'QtMultimediaWidgets', 'QtQml', 'QtQuick',
               'QtSql', 'QtSvg', 'QtTest', 'QtWebKit', 'QtXml', 'QtXmlPatterns',
               'QtDeclarative', 'QtScript', 'QtScriptTools', 'QtUiTools',
               'QtQuickWidgets', 'QtSensors', 'QtSerialPort', 'QtWebChannel',
               'QtWebKitWidgets', 'QtWebSockets',
               ]

for qt_ver in qt_kits:
    for excl in qt_excludes:
        excludes.append(qt_ver + '.' + excl)

excludes.extend(qt_kits.difference([QT_API]))


## Freeze

# Clear first
if os.path.isdir(distDir):
    shutil.rmtree(distDir)
os.makedirs(distDir)


cmd = ["--clean", "--onedir", "--name", name, "--distpath", distDir]

for m in includes:
    cmd.extend(["--hidden-import", m])
for m in excludes:
    cmd.extend(["--exclude-module", m])

if sys.platform.startswith("win"):
    cmd.append("--windowed")  # not a console app
    cmd.extend(["--icon", iconFile])
elif sys.platform.startswith("darwin"):
    cmd.append("--windowed")  # makes a .app bundle
    cmd.extend(["--icon", iconFile[:-3] + "icns"])

cmd.append(srcDir + "__main__.py")
PyInstaller.__main__.run(cmd)

os.remove(baseDir + "pyzo.spec")


## Process source code and other resources


def copydir_smart(path1, path2):
    """ like shutil.copytree, but ...
      * ignores __pycache__directories
      * ignores hg, svn and git directories
    """
    # Ensure destination directory does exist
    if not os.path.isdir(path2):
        os.makedirs(path2)
    # Itereate over elements
    count = 0
    for sub in os.listdir(path1):
        fullsub1 = os.path.join(path1, sub)
        fullsub2 = os.path.join(path2, sub)
        if sub in ['__pycache__', '.hg', '.svn', '.git']:
            continue
        elif sub.endswith('.pyc') and os.path.isfile(fullsub1[:-1]):
            continue
        elif os.path.isdir(fullsub1):
            count += copydir_smart(fullsub1, fullsub2)
        elif os.path.isfile(fullsub1):
            shutil.copy(fullsub1, fullsub2)
            count += 1
    # Return number of copies files
    return count


SETTINGS_TEXT = """
Portable settings folder
------------------------
This folder can be used to let the application and the libaries that
it uses to store configuration files local to the executable. One use
case is having this app on a USB drive that you use on different
computers.

This functionality is enabled if the folder is named "settings" and is
writable by the application (i.e. should not be in "c:\program files\..."
or "/usr/..."). This functionality can be deactivated by renaming
it (e.g. prepending an underscore). To reset config files, clear the
contents of this folder (but do not remove the folder itself).

Note that some libraries may ignore this functionality and use the
normal system configuration directory instead.

This "standard" was discussed between the authors of WinPython,
PortablePython and Pyzo. Developers can use the appdata_dir() function
from https://bitbucket.org/pyzo/pyzolib/src/tip/paths.py to
use this standard. For more info, contact either of us.

""".lstrip()

# Post process the frozen dir (and the frozen app-dir on OS X)
frozenDirs = [os.path.join(distDir, 'pyzo')]
if sys.platform.startswith("darwin"):
    frozenDirs.append(os.path.join(distDir, 'pyzo.app', 'Contents', 'MacOS'))

for frozenDir in frozenDirs:

    # Copy the whole Pyzo package
    copydir_smart(os.path.join(srcDir), os.path.join(frozenDir, 'source', 'pyzo'))

    # Create settings folder and put in a file
    os.mkdir(os.path.join(frozenDir, '_settings'))
    with open(os.path.join(frozenDir, '_settings', 'README.txt'), 'wb') as file:
        file.write(SETTINGS_TEXT.encode('utf-8'))


## Package things up

# On Windows we have the iss script that we run manually, and we can zip easily.
# On Linux we can compress the dir easily.
# On OS X we want a DMG and this is what we do below.

if sys.platform.startswith("darwin"):
    print("Packing up into dmg ...")
    appDir = distDir + "pyzo.app"
    dmgFile = distDir + 'pyzo.dmg'

    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','create','-fs','HFSX',
                '-format','UDZO', dmgFile, '-imagekey', 'zlib-level=9',
                '-srcfolder', appDir, '-volname', 'pyzo') != 0:
        raise OSError('creation of the dmg failed')
