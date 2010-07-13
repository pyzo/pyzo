""" FREEZING WITH CX_FREEZE
This script can be run as a script (no need to do distutils stuff...)
"""

import sys, os, shutil
from cx_Freeze import Executable, Freezer, setup

# define app name and such
name = "iep"
baseDir = ''
srcDir = ''
distDir = baseDir+'../frozen/'
scriptFile = srcDir + 'iep.pyw'
iconFile = srcDir + 'icon.ico'

## Includes and excludes

# We do not need these
excludes = ['_ssl', 'pyreadline', 'pdb', "email", 
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

# Plugins are dynamically loaded so need copying or included explicitly
includes = ['plugins.iepSourceStructure']


## Go!
# See http://cx-freeze.sourceforge.net/cx_Freeze.html for docs.

# NOTE: I had to add "import sys" to freezer.py for it to work and prevent
# the "None object has no atribute modules" error message
# The statement should be added right before "sys.modules[__name__] = m".

sys.path.append('')

if sys.platform.lower().count('win'):
    ex = Executable(    scriptFile, 
                        icon=iconFile,
                        appendScriptToExe = True,
                        base = 'Win32GUI', # this is what hides the console
                        )
else:
    ex = Executable(    scriptFile, 
                    )


f = Freezer(    {ex:True}, 
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

# Copy resource files
shutil.copy(srcDir+'styles.ssdf', distDir+'styles.ssdf')
for icon in ['icon16.png', 'icon32.png', 'icon48.png', 'icon.ico']:
    shutil.copy(srcDir+icon, distDir+icon)
for mod in ['channels.py', 'remote.py', 'remote2.py']:
    shutil.copy(srcDir+mod, distDir+mod)
# todo: also need remote3.py?