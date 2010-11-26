#!/usr/bin/env python3.1
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" FREEZING IEP WITH CX_FREEZE
This script can be run as a script (no need to do distutils stuff...)

Iep is frozen in such a way that it still uses the plain source code.
Therefore iep.pyw imports iep.py using the "exec" function. We create
two executables, one from iep.pyw, and one from iep_.pyw, that does
import iep.py explcitily and is therefore completely frozen. The effect
is that all modules that iep uses, are all available without having to
explicitly include them in this script.

Note that .pyc files are created even if the frozen app is inside the 
program files directory of windows7.

The frozen application is created in a sibling directory of the source.

"""

import sys, os, shutil
from cx_Freeze import Executable, Freezer, setup

# Define app name and such
name = "iep"
baseDir = './'
srcDir = './'
distDir = baseDir+'../frozen/'
scriptFiles = [srcDir + 'iep.pyw', srcDir + 'iep_.pyw']
iconFile = srcDir + 'icons/iep.ico'

#On MAC, build an application bundle
if sys.platform=='darwin':
    contentsDir=distDir+name+'.app/Contents/'
    resourcesDir=contentsDir+'Resources/'
    appDir=distDir
    distDir=contentsDir+'MacOS/'
    applicationBundle=True
else:
    applicationBundle=False
	


## Includes and excludes

# We do not need these
excludes = ['_ssl', 'pyreadline', 'pdb', 
     "matplotlib", 'doctest', 
    "scipy.linalg", "scipy.special", "Pyrex", 
    "numpy.core._dotblas",
    ]

# Excludes for tk
tk_excludes = [ "pywin", "pywin.debugger", "pywin.debugger.dbgcon",
                "pywin.dialogs", "pywin.dialogs.list",
                "Tkconstants", "Tkinter", "tcl" ]
excludes.extend(tk_excludes)
excludes.append('numpy')

# For qt to work
includes = ['sip', "PyQt4.QtCore", "PyQt4.QtGui", 'PyQt4.Qsci'] 


## Go!
# See http://cx-freeze.sourceforge.net/cx_Freeze.html for docs.

# NOTE: I had to add "import sys" to freezer.py for it to work and prevent
# the "None object has no atribute modules" error message
# The statement should be added right before "sys.modules[__name__] = m".

sys.path.append('')

executables = {}
for scriptFile in scriptFiles:
    
    if sys.platform.startswith('win'):
        ex = Executable(    scriptFile, 
                            icon=iconFile,
                            appendScriptToExe = True,
                            base = 'Win32GUI', # this is what hides the console
                            )
    else:
        ex = Executable(    scriptFile, 
                        )
    executables[ex] = True


f = Freezer(    executables, 
                includes = includes,
                excludes = excludes,
                targetDir = distDir,
                copyDependentFiles = True,
#                 appendScriptToExe=True,
#                 optimizeFlag=1, 
                compress=False,
                silent=True,
            )

f.Freeze()


## Process source code and other resources

# Create source dir in frozen app
srcDir2 = distDir + 'source/'
if not os.path.isdir(srcDir2):
    os.mkdir(srcDir2)

# Create tools dir in frozen app
toolsDir  = srcDir + 'tools/'
toolsDir2 = srcDir2 + 'tools/'
if not os.path.isdir(toolsDir2):
    os.mkdir(toolsDir2)

# Create icons dir in frozen app
iconsDir  = srcDir + 'icons/'
iconsDir2 = srcDir2 + 'icons/'
if not os.path.isdir(iconsDir2):
    os.mkdir(iconsDir2)
    
# Copy all source files
for fname in os.listdir(srcDir):
    if os.path.isfile(srcDir+fname) and not fname.endswith('.pyc'):
        shutil.copy(srcDir+fname, srcDir2+fname)
for fname in os.listdir(toolsDir):    
    if os.path.isfile(toolsDir+fname) and not fname.endswith('.pyc'):
        shutil.copy(toolsDir+fname, toolsDir2+fname)
for fname in os.listdir(iconsDir):
    shutil.copy(iconsDir+fname, iconsDir2+fname)


# Remove dummy executable
tmp1 = os.path.join(distDir,'iep_.exe')
tmp2 = os.path.join(distDir,'iep_')
for fname in [tmp1, tmp2]:
    if os.path.isfile(fname):
        os.remove(fname)

if applicationBundle:
    #Copy the icon
    if not os.path.isdir(resourcesDir):
        os.mkdir(resourcesDir)
    shutil.copy(srcDir+'Icons/iep.icns',resourcesDir+'iep.icns')
	#Copy the Info.plist file
    shutil.copy(srcDir+'Info.plist',contentsDir+'Info.plist')

    #Package in a dmg
    dmgFile=appDir+'iep.dmg'
    dmgTemp=appDir+'temp.dmg'

    tempDir=appDir+'temp'
    os.mkdir(tempDir)
    #Create the dmg
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','create','-fs','HFSX','-layout','SPUD','-megabytes','50',dmgTemp,'-srcfolder',tempDir,'-format','UDRW','-volname','iEP')!=0:
	    sys.exit(1)

    #Mount the dmg
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','attach',dmgTemp,'-noautoopen','-quiet','-mountpoint',tempDir)!=0:
	    sys.exit(1)

    #Copy the app
    shutil.copytree(appDir+'iep.app',tempDir+'/iep.app')

    #Unount the dmg
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','detach',tempDir,'-force')!=0:
        sys.exit(1)
    os.rmdir(tempDir)

	#Convert the dmg to compressed, read=only
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','convert',dmgTemp,'-format','UDZO','-imagekey','zlib-level=9','-o',dmgFile)!=0:
        sys.exit(1)
    os.unlink(dmgTemp)

