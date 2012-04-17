#!/usr/bin/env python3
# Copyright (C) 2012, the IEP development team
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

import sys, os, stat, shutil
import subprocess
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
    "PyQt4.uic.port_v2"#, "PyQt4.QtWebKit"
    ]

# Excludes for tk
tk_excludes = [ "pywin", "pywin.debugger", "pywin.debugger.dbgcon",
                "pywin.dialogs", "pywin.dialogs.list",
                "Tkconstants", "Tkinter", "tcl" ]
excludes.extend(tk_excludes)
excludes.append('numpy')

# For qt to work
# todo: remove Qsci, enable pyside?
includes = []
#includes.append('PyQt4.uic')

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

#TODO: remove the repetition here!
#TODO: prevent copying '.xxx' files

# Create source dir in frozen app
srcDir2 = distDir + 'source/'

#Copy all the source files
for dir in ['','iepkernel/', 'iepcore/', 'tools/',
    'codeeditor/', 'codeeditor/extensions/', 'codeeditor/parsers/',
    'yoton/', 'yoton/channels/']:
    if not os.path.isdir(srcDir2+dir):
        os.mkdir(srcDir2+dir)

    for fname in os.listdir(srcDir+dir):
        if os.path.isfile(srcDir+dir+fname) and not fname.endswith('.pyc') and not fname.startswith('.'):
            shutil.copy(srcDir+dir+fname, srcDir2+dir+fname)


# Create icons dir in frozen app
iconsDir  = srcDir + 'icons/'
iconsDir2 = srcDir2 + 'icons/'
if not os.path.isdir(iconsDir2):
    os.mkdir(iconsDir2)

# Create gui dir in frozen app
#guiDir  = srcDir + 'gui/'
#guiDir2 = srcDir2 + 'gui/'
#if not os.path.isdir(guiDir2):
#    os.mkdir(guiDir2)

# Create resources dir in frozen app
resDir = srcDir + 'resources/'
resDir2 = srcDir2 + 'resources/'

if not os.path.isdir(resDir2):
    os.mkdir(resDir2)

for fname in os.listdir(iconsDir):
    shutil.copy(iconsDir+fname, iconsDir2+fname)
#for fname in os.listdir(guiDir):
#    if not os.path.isdir(guiDir+fname):
#        shutil.copy(guiDir+fname, guiDir2+fname)
for fname in os.listdir(resDir):
    shutil.copy(resDir+fname, resDir2+fname)

# Remove dummy executable
tmp1 = os.path.join(distDir,'iep_.exe')
tmp2 = os.path.join(distDir,'iep_')
for fname in [tmp1, tmp2]:
    if os.path.isfile(fname):
        os.remove(fname)

if applicationBundle:
    #Change the absolute paths in all library files to relative paths
    #This should be a cx_freeze task, but cx_freeze doesn't do it
    
    shippedfiles=os.listdir(distDir)

    for file in shippedfiles:
        #Do the processing for any found file or dir, the tools will just
        #fail for files for which it does not apply
        filepath=os.path.join(distDir,file)
        
        #Ensure write permissions
        mode = os.stat(filepath).st_mode
        if not (mode & stat.S_IWUSR):
            os.chmod(filepath, mode | stat.S_IWUSR)
            
        #Let the library itself know its place
        subprocess.call(('install_name_tool','-id','@executable_path/'+file,filepath))

        #Find the references
        otool=subprocess.Popen(('otool','-L', filepath),stdout=subprocess.PIPE)
        libs=otool.stdout.readlines()

        for lib in libs:
            #For each referenced library, chech if it is in the set of
            #files that we ship. If so, change the reference to a path
            #relative to the executable path
            lib=lib.decode()
            filename,_,_=lib.strip().partition(' ')
            prefix,name=os.path.split(filename)
            if name in shippedfiles:
                newfilename='@executable_path/'+name
                print ('%s => %s' % (name,newfilename))
                subprocess.call(('install_name_tool','-change',filename,newfilename,filepath))

    #Copy the icon
    if not os.path.isdir(resourcesDir):
        os.mkdir(resourcesDir)
    shutil.copy(srcDir+'Icons/iep.icns',resourcesDir+'iep.icns')
    #Copy the Info.plist file
    shutil.copy(srcDir+'Info.plist',contentsDir+'Info.plist')

    #Copy the qt_menu.nib directory (TODO: is this the place to look for it?)
    shutil.copytree('/opt/local/lib/Resources/qt_menu.nib',resourcesDir+'qt_menu.nib')


    #Package in a dmg
    dmgFile=appDir+'iep.dmg'

    # Create the dmg
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','create','-fs','HFSX',
        '-format','UDZO',dmgFile, '-imagekey', 'zlib-level=9',
        '-srcfolder',appDir,'-volname', 'iep')!=0:
        raise OSError('creation of the dmg failed')

