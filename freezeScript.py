#!/usr/bin/env python3
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" FREEZING Pyzo WITH CX_FREEZE
This script can be run as a script (no need to do distutils stuff...)

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

import sys, os, stat, shutil, struct
import subprocess
from cx_Freeze import Executable, Freezer, setup  # noqa


# Notes to self:
# - I used to build the Windows binaries on a WinXP VM, but newer versions
#   of Python (3.5 and up) do not work on XP anymore. So we stick to 3.4.
# - This is not so bad, since with newer versions of Python I have not been
#   able to ship the MSVC runtime in the correct way (see win7 VM).
# - The conda executable on my winXP seems broken, but can still use "python -m conda".
# - For Linux, use the Pingulin VM, and PySide from conda-forge.
# - For OS X, use Python and PySide from macports (since cx_Freeze does not work
#   from conda env).

# SELECT BACKEND
QT_API = 'PySide'


# Define app name and such
name = "pyzo"
baseDir = os.path.abspath('') + '/'
srcDir = baseDir + 'pyzo/'
distDir = baseDir + 'frozen/'
scriptFiles = [srcDir + '__main__.py']
iconFile = srcDir + 'resources/appicons/pyzologo.ico'

# On MAC, build an application bundle
if sys.platform=='darwin':
    contentsDir=distDir+name+'.app/Contents/'
    resourcesDir=contentsDir+'Resources/'
    appDir=distDir
    distDir=contentsDir+'MacOS/'
    applicationBundle=True
    createDmg=True  # for dev
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

# Excludes for Qt
qt_excludes = ['QtNetwork', 'QtOpenGL', 'QtXml', 'QtTest', 'QtSql', 'QtSvg',  # 'QtHelp'
               'QtBluetooth', 'QtDBus', 'QtDesigner', 'QtLocation', 'QtPositioning',
               'QtMultimedia', 'QtMultimediaWidgets', 'QtQml', 'QtQuick',
               'QtSql', 'QtSvg', 'QtTest', 'QtWebKit', 'QtXml', 'QtXmlPatterns',
               'QtDeclarative', 'QtScript', 'QtScriptTools', 'QtUiTools',
               'QtQuickWidgets', 'QtSensors', 'QtSerialPort', 'QtWebChannel',
               'QtWebKitWidgets', 'QtWebSockets',
               ]

for qt_ver in ['PyQt5', 'PyQt4', 'PySide']:
    for excl in qt_excludes:
        excludes.append(qt_ver + '.' + excl)

# For qt to work
PyQt5Modules = ['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtHelp', 'PyQt5.QtPrintSupport']
PyQt4Modules = ['PyQt4', 'PyQt4.QtCore', 'PyQt4.QtGui', 'PyQt4.QtHelp']  # QtPrintSupport is in QtGui
PySideModules = ['PySide', 'PySide.QtCore', 'PySide.QtGui', 'PySide.QtHelp']  


if QT_API == 'PyQt5':
    includes = PyQt5Modules
elif QT_API == 'PyQt4':
    includes = PyQt4Modules
elif QT_API == 'PySide':
    includes = PySideModules
else:
    raise RuntimeError('Unknown QT_API %r' % QT_API)

excludes.extend(PySideModules)
excludes.extend(PyQt4Modules)
excludes.extend(PyQt5Modules)

for mod in includes:
    if mod in excludes:
        excludes.remove(mod)

# More includes
includes.extend(['code'])


## Freeze

# Clear first
if os.path.isdir(baseDir+'frozen'):
    shutil.rmtree(baseDir+'frozen')
os.makedirs(distDir)


executables = {}
for scriptFile in scriptFiles:
    
    if sys.platform.startswith('win'):
        ex = Executable(    scriptFile, 
                            targetName = 'pyzo.exe',
                            icon=iconFile,
                            # appendScriptToExe = True,
                            base = 'Win32GUI', # this is what hides the console                            
                            )
    else:
        ex = Executable(    scriptFile, 
                            targetName = 'pyzo',
                        )
    executables[ex] = True


f = Freezer(    executables, 
                includes = includes,
                binIncludes = ['libssl.so', 'libcrypto.so'],
                excludes = excludes,
                targetDir = distDir,
                # copyDependentFiles = True,
                includeMSVCR = True,  # Let cx_Freeze find it for us
#                 appendScriptToExe=True,
#                 optimizeFlag=1, 
                compress=False,
                silent=True,
            )

f.Freeze()


## Process source code and other resources



for d in (os.path.join(distDir, 'PyQt5'), distDir):
    if os.path.isdir(d):
        for fname in os.listdir(d):
            filename = os.path.join(d, fname)
            for e in qt_excludes:
                if fname.startswith(e + '.'):
                    if os.path.isfile(filename):
                        os.remove(filename)


MANIFEST_TEMPLATE = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<noInheritable/>
<assemblyIdentity
    type="win32"
    name="Microsoft.VC90.CRT"
    version="9.0.21022.8"
    processorArchitecture="{PROC_ARCH}"
    publicKeyToken="1fc8b3b9a1e18e3b"
/>
<file name="msvcr90.dll" />
<file name="msvcp90.dll" />
<file name="msvcm90.dll" />
</assembly>
""".lstrip().replace('\r\n', '\n').replace('\n', '\r\n')


def install_c_runtime(targetDir):
    """ install_c_runtime(targetDir)
    Install the Windows C runtime version 100. So we aim at python3
    specifically. We needed this because cx_freeze seems to do it wrong.
    """
    for fname in ['msvcp100.dll', 'msvcr100.dll']:
        filename = os.path.join('C:\\', 'Windows', 'System32', fname)
        if os.path.isfile(filename):
            shutil.copy(filename, os.path.join(distDir, fname))
    
    ISWIN32 = sys.platform.startswith('win') and struct.calcsize('P')==4
    # Copy manifest for msvcr90 on win32... why o why do we need this?
    if ISWIN32:
        t = MANIFEST_TEMPLATE
        t = t.replace('{PROC_ARCH}', 'x86') # {4:'x86', 8:'amd64'}
        manifest_filename = os.path.join(distDir,'Microsoft.VC90.CRT.manifest')
        open(manifest_filename, 'wb').write(t.encode('utf-8'))


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
        elif sub.endswith('.pyc') and os.path.isfile(fullsub1[:-1]):
            continue
        elif os.path.isdir(fullsub1):
            count += copydir_smart(fullsub1, fullsub2)
        elif os.path.isfile(fullsub1):
            shutil.copy(fullsub1, fullsub2)
            count += 1
    # Return number of copies files
    return count

# Install MS C runtime, cx_freeze does not seem to find mscvp100.dll
if sys.platform.startswith('win'):
    install_c_runtime(distDir)

# Copy the whole Pyzo package
copydir_smart(os.path.join(srcDir), os.path.join(distDir, 'source', 'pyzo'))

# Remove dummy executable
tmp1 = os.path.join(distDir,'pyzo_.exe')
tmp2 = os.path.join(distDir,'pyzo_')
for fname in [tmp1, tmp2]:
    if os.path.isfile(fname):
        os.remove(fname)

# Create settings folder and put in a file
os.mkdir(os.path.join(distDir, '_settings'))

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
with open(os.path.join(distDir, '_settings', 'README.txt'), 'wb') as file:
    file.write(SETTINGS_TEXT.encode('utf-8'))



## Post processing


# Copy Qt platform plugins
if sys.platform.startswith('win') and QT_API == 'PyQt5':
    src_dir = os.path.join(sys.prefix, 'Library', 'plugins', 'platforms')
    for fname in os.listdir(src_dir):
        if fname.endswith('.dll'):
            shutil.copy2(os.path.join(src_dir, fname),
                         os.path.join(distDir, fname))

# Set search path of dynamic libraries
import dllutils
if sys.platform.startswith('linux'):
    
    libs2fix = []  # (filename, rpaths) tuples
    
    # Exe
    rpaths = '', 'lib'
    libs2fix.append((os.path.join(distDir, 'pyzo'), rpaths))
    
    # Libs
    if not os.path.isdir(os.path.join(distDir, 'lib')):
        os.mkdir(os.path.join(distDir, 'lib'))
    for entry in os.listdir(distDir):
        filename = os.path.join(distDir, entry)
        if not (os.path.isfile(filename ) and (entry.endswith('.so') or '.so.' in entry)):
            continue
        rpaths = '', 'lib'
        if entry.startswith('lib') and not 'python' in entry:  # move lib
            filename = os.path.join(distDir, 'lib', entry)
            shutil.move(os.path.join(distDir, entry), filename)
            rpaths = '', '..'
        libs2fix.append((filename, rpaths))
    
    # Libs further (newer version of cx_freeze puts libs in /lib/python3.5
    lib_py_dir = os.path.join(distDir, 'lib', 'python' + sys.version[:3])
    for entry in os.listdir(lib_py_dir):
        filename = os.path.join(lib_py_dir, entry)
        if not (os.path.isfile(filename ) and (entry.endswith('.so') or '.so.' in entry)):
            continue
        rpaths = '', '..', '../..'
        libs2fix.append((filename, rpaths))
    
    # Libs further (newer version of cx_freeze puts libs in /lib/python3.5
    qt_platform_dir = os.path.join(distDir, 'platforms')
    if not os.path.isdir(qt_platform_dir):
        print('Could not find Qt platform dir')
    else:
        for entry in os.listdir(qt_platform_dir):
            filename = os.path.join(qt_platform_dir, entry)
            if not (os.path.isfile(filename ) and (entry.endswith('.so') or '.so.' in entry)):
                continue
            rpaths = '', '..', '../lib', '../lib/python' + sys.version[:3]
        libs2fix.append((filename, rpaths))
    
    # Apply
    for filename, rpaths in libs2fix:
        try:
            dllutils.set_search_path(filename, *rpaths)
        except Exception as err:
            print('Cannot set search path of %s:\n%s' % 
                    (os.path.basename(entry), str(err)))


if sys.platform.startswith('linux'):
    
    # Set qt.conf
    # Prevent loading plugins form the system plugin dir, which
    # may cause incompatibility conflicts. This complements the call
    # QApplication.setLibraryPaths([]), it does not replace it.
    # See issue 138 and issue 198.
    with open(os.path.join(distDir, 'qt.conf'), 'wb') as file:
        file.write("[Paths]\nPlugins = '.'\n".encode('utf-8'))

# Remove imageforma dir. These libs hook into the original
# Qt libs, giving rise to these nasty mixed binaries errors.
# This happened on OSX, but Linux may also be affected
imformatsdir = os.path.join(distDir, 'imageformats')
if os.path.isdir(imformatsdir):
    shutil.rmtree(imformatsdir)


OSX_INSTALL_NOTES = """Pyzo installation:
- Move or copy the "pyzo" app to your Applications folder.
- Run it.
- If OS X says something about the app being from an unidentified
  developer, right-click or control-click the app, select open,
  and then confirm. This should only be needed once.
"""

# todo: this is now in cx_Freeze right?
if applicationBundle:
    #Change the absolute paths in all library files to relative paths
    #This should be a cx_freeze task, but cx_freeze doesn't do it
    
    # Move PyQt4 libs into subdir
    # This gets us a similar dir structure as installed so
    # we dont have to fix paths ...
    if False:  # IF FREEZING FROM CONDA
        os.makedirs(distDir+'source/more/' + QT_API)
        open(distDir+'source/more/' + QT_API + '/__init__.py', 'wb').close()
        for fname in os.listdir(distDir):
            if fname.startswith(QT_API):
                filename = distDir+'source/more/' + QT_API + '/' + fname[6:]
            elif fname.startswith('sip'):
                filename = distDir+'source/more/' + fname
            else:
                continue
            shutil.move(distDir+fname, filename)
    
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

    #Copy the icons
    if not os.path.isdir(resourcesDir):
        os.mkdir(resourcesDir)
    shutil.copy(srcDir+'resources/appicons/pyzologo.icns',resourcesDir+'pyzo.icns')
    shutil.copy(srcDir+'resources/appicons/py.icns',resourcesDir+'py.icns')
    
    #Write qt.conf in the Resources dir
    with open(os.path.join(resourcesDir, 'qt.conf'), 'wb') as file:
        file.write("[Paths]\nPlugins = '.'\n".encode('utf-8'))
    
    #Copy the Info.plist file
    shutil.copy(baseDir+'Info.plist',contentsDir+'Info.plist')
    
    #Copy the qt_menu.nib directory (TODO: is this the place to look for it?)
    potential_dirs = ['/opt/local/libexec/qt4/Library/Frameworks/QtGui.framework/Versions/4/Resources/',
                      '/opt/local/Library/Frameworks/QtGui.framework/Versions/4/Resources/']
    for d in potential_dirs:
        if os.path.isdir(d + 'qt_menu.nib'):
            shutil.copytree(d + 'qt_menu.nib', resourcesDir+'qt_menu.nib')
            break
    else:
        raise RuntimeError('Could not find qt_menu.nib')

    
    # Add notes
    with open(os.path.join(appDir, 'install.txt'), 'wb') as f:
        f.write(OSX_INSTALL_NOTES.encode())
    
    #Package in a dmg
    dmgFile=appDir+'pyzo.dmg'

    # Create the dmg
    if createDmg:
        if os.spawnlp(os.P_WAIT,'hdiutil','hdiutil','create','-fs','HFSX',
                    '-format','UDZO',dmgFile, '-imagekey', 'zlib-level=9',
                    '-srcfolder',appDir,'-volname', 'pyzo')!=0:
            raise OSError('creation of the dmg failed')

