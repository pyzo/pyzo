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
baseDir = os.path.abspath('') + '/'
srcDir = baseDir + 'iep/'
distDir = baseDir + 'frozen/'
scriptFiles = [srcDir + '__main__.py']
iconFile = srcDir + 'icons/iep.ico'

# On MAC, build an application bundle
if sys.platform=='darwin':
    contentsDir=distDir+name+'.app/Contents/'
    resourcesDir=contentsDir+'Resources/'
    appDir=distDir
    distDir=contentsDir+'MacOS/'
    applicationBundle=True
else:
    applicationBundle=False

sys.path.append('')


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
PyQtModules = ['PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui',]
PySideModules = ['PySide', 'PySide.QtCore', 'PySide.QtGui']
#
excludes.extend(PyQtModules)
includes = PySideModules


## Freeze

# Clear first
shutil.rmtree(distDir)
os.makedirs(distDir)


executables = {}
for scriptFile in scriptFiles:
    
    if sys.platform.startswith('win'):
        ex = Executable(    scriptFile, 
                            targetName = 'iep.exe',
                            icon=iconFile,
                            appendScriptToExe = True,
                            base = 'Win32GUI', # this is what hides the console
                            includeMSVCR = True,
                            )
    else:
        ex = Executable(    scriptFile, 
                            targetName = 'iep',
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

# taken from pyzo_build:
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
        elif os.path.isdir(fullsub1):
            count += copydir_smart(fullsub1, fullsub2)
        elif os.path.isfile(fullsub1):
            shutil.copy(fullsub1, fullsub2)
            count += 1
    # Return number of copies files
    return count

# Copy the whole IEP package
copydir_smart(os.path.join(srcDir), os.path.join(distDir, 'source', 'iep'))

# Remove dummy executable
tmp1 = os.path.join(distDir,'iep_.exe')
tmp2 = os.path.join(distDir,'iep_')
for fname in [tmp1, tmp2]:
    if os.path.isfile(fname):
        os.remove(fname)

# todo: this is now in cx_Freeze right?
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
    shutil.copy(srcDir+'resources/appicons/ieplogo.icns',resourcesDir+'iep.icns')
    #Copy the Info.plist file
    shutil.copy(baseDir+'Info.plist',contentsDir+'Info.plist')

    #Copy the qt_menu.nib directory (TODO: is this the place to look for it?)
    shutil.copytree('/opt/local/lib/Resources/qt_menu.nib',resourcesDir+'qt_menu.nib')


    #Package in a dmg
    dmgFile=appDir+'iep.dmg'

    # Create the dmg
    if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','create','-fs','HFSX',
        '-format','UDZO',dmgFile, '-imagekey', 'zlib-level=9',
        '-srcfolder',appDir,'-volname', 'iep')!=0:
        raise OSError('creation of the dmg failed')

