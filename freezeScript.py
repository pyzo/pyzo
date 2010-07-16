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
"""

import sys, os, shutil
from cx_Freeze import Executable, Freezer, setup

# define app name and such
name = "iep"
baseDir = './'
srcDir = './'
distDir = baseDir+'../frozen/'
scriptFiles = [srcDir + 'iep.pyw', srcDir + 'iep_.pyw']
iconFile = srcDir + 'icons/iep.ico'

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
                "Tkconstants","Tkinter","tcl" ]
excludes.extend(tk_excludes)
excludes.append('numpy')

# For qt to work
includes = ['sip', "PyQt4.QtCore", "PyQt4.QtGui", 'PyQt4.Qsci'] 

# For IEP to work
includes.extend(['threading', '_thread', 'queue', 'socket', 
                'base64', 'ssdf', 'code', ])

## Go!
# See http://cx-freeze.sourceforge.net/cx_Freeze.html for docs.

# NOTE: I had to add "import sys" to freezer.py for it to work and prevent
# the "None object has no atribute modules" error message
# The statement should be added right before "sys.modules[__name__] = m".

sys.path.append('')

executables = {}
for scriptFile in scriptFiles:
    
    if sys.platform.lower().count('win'):
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
os.remove( os.path.join(distDir,'iep_.exe') )
