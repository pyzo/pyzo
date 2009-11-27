""" FREEZING WITH CX_FREEZE
This script can be run as a script (no need to do distutils stuff...)
"""

import sys, os, shutil
from cx_Freeze import Executable, Freezer, setup

# define app name and such
name = "iep"
baseDir = ''
srcDir = ''
distDir = baseDir+'frozen/'
scriptFile = srcDir + 'iep.pyw'
iconFile = srcDir + 'icon.ico'

## includes and excludes

# you usually do not need these
excludes = ['_ssl', 'pyreadline', 'pdb', "email", 
     "matplotlib", 'doctest', 
    "scipy.linalg", "scipy.special", "Pyrex", 
    "numpy.core._dotblas",
    ]
# excludes for tk
tk_excludes = [ "pywin", "pywin.debugger", "pywin.debugger.dbgcon",
                "pywin.dialogs", "pywin.dialogs.list",
                "Tkconstants","Tkinter","tcl" ]
excludes.extend(tk_excludes)
excludes.append('numpy')


includes = ['sip', "PyQt4.QtCore", "PyQt4.QtGui", 'PyQt4.Qsci'] # for qt to work


## Go!
# see http://cx-freeze.sourceforge.net/cx_Freeze.html for docs.

# NOTE: I had tp add "import sys" to freezer.py for it to work and prevent
# the "None object has no atribute modules" error message
# The statement should be added right before "sys.modules[__name__] = m".

sys.path.append('')

ex = Executable(    scriptFile, 
                    icon=iconFile,
                    appendScriptToExe = True,
                    base = 'Win32GUI', # this is what hides the console
                    )

f = Freezer(    {ex:True}, 
                includes = includes,
                excludes = excludes,
                targetDir = distDir,
#                 copyDependentFiles = True,
#                 appendScriptToExe=True,
#                 optimizeFlag=1, 
                compress=False,
                silent=True,
            )

f.Freeze()

# copy resource files
shutil.copy(srcDir+'styles.ssdf', distDir+'styles.ssdf')
for icon in ['icon16.png', 'icon32.png', 'icon48.png', 'icon.ico']:
    shutil.copy(srcDir+icon, distDir+icon)
