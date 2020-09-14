#!/usr/bin/env python3

""" FREEZING Pyzo WITH PYINSTALLER

Pyzo is frozen in such a way that it still uses the plain source code.
This is achieved by putting the Pyzo package in a subdirectory called
"source". This source directory is added to sys.path by __main__.py.

In case we need better support for older MacOS:
https://gist.github.com/phfaist/a5b8a895b003822df5397731f4673042

"""

import os
import re
import sys
import shutil
import zipfile
import tarfile
import subprocess

import PyInstaller.__main__


# Define app name and such
name = "pyzo"
thisDir = os.path.abspath(os.path.dirname(__file__))
baseDir = os.path.abspath(os.path.join(thisDir, "..")) + "/"
srcDir = baseDir + "pyzo/"
distDir = baseDir + "frozen/"
iconFile = srcDir + "resources/appicons/pyzologo.ico"

sys.path.insert(0, baseDir)


## Includes and excludes

# The Qt toolkit that we use
QT_API = "PyQt5"

# All known Qt toolkits, mainly to exclude them
qt_kits = {"PySide", "PySide2", "PyQt4", "PyQt5"}

# Imports that PyInstaller may have missed, or that are simply common/useful
# and may be used by some tools.
includes = ["code", "shutil"]

# Exclude stuff that somehow gets, or may get, selected by PyInstaller
excludes = ["numpy", "scipy", "win32com", "conda", "pip", "IPython"]

# Excludes for tk
tk_excludes = [
    "pywin",
    "pywin.debugger",
    "pywin.debugger.dbgcon",
    "pywin.dialogs",
    "pywin.dialogs.list",
    "Tkconstants",
    "Tkinter",
    "tcl",
]
excludes.extend(tk_excludes)

# Excludes for Qt
qt_excludes = [
    "QtNetwork",
    "QtOpenGL",
    "QtXml",
    "QtTest",
    "QtSql",
    "QtSvg",
    "QtBluetooth",
    "QtDBus",
    "QtDesigner",
    "QtLocation",
    "QtPositioning",
    "QtMultimedia",
    "QtMultimediaWidgets",
    "QtQml",
    "QtQuick",
    "QtSql",
    "QtSvg",
    "QtTest",
    "QtWebKit",
    "QtXml",
    "QtXmlPatterns",
    "QtDeclarative",
    "QtScript",
    "QtScriptTools",
    "QtUiTools",
    "QtQuickWidgets",
    "QtSensors",
    "QtSerialPort",
    "QtWebChannel",
    "QtWebKitWidgets",
    "QtWebSockets",
]

for qt_ver in qt_kits:
    for excl in qt_excludes:
        excludes.append(qt_ver + "." + excl)

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
    cmd.extend(["--osx-bundle-identifier", "org.pyzo.pyzo4"])

cmd.append(srcDir + "__main__.py")

PyInstaller.__main__.run(cmd)

try:
    os.remove(os.path.join(thisDir, "pyzo.spec"))
except Exception:
    pass


## Process source code and other resources

with open(srcDir + "__init__.py") as fh:
    __version__ = re.search(r"__version__ = \"(.*?)\"", fh.read()).group(1)

bitness = "32" if sys.maxsize <= 2 ** 32 else "64"


def copydir_smart(path1, path2):
    """like shutil.copytree, but ...
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
        if sub in ["__pycache__", ".hg", ".svn", ".git"]:
            continue
        elif sub.endswith(".pyc") and os.path.isfile(fullsub1[:-1]):
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
contents of the "pyzo" sub-folder (but do not remove the folder itself).

Note that some libraries may ignore this functionality and use the
normal system configuration directory instead.

This "standard" was discussed between the authors of WinPython,
PortablePython and Pyzo. Developers can use the appdata_dir() function
from https://bitbucket.org/pyzo/pyzolib/src/tip/paths.py to
use this standard. For more info, contact either of us.

""".lstrip()

# Post process the frozen dir (and the frozen app-dir on OS X)
frozenDirs = [os.path.join(distDir, "pyzo")]
if sys.platform.startswith("darwin"):
    frozenDirs.append(os.path.join(distDir, "pyzo.app", "Contents", "MacOS"))

for frozenDir in frozenDirs:

    # Copy the whole Pyzo package
    copydir_smart(os.path.join(srcDir), os.path.join(frozenDir, "source", "pyzo"))

    # Create settings folder and put in a file
    os.mkdir(os.path.join(frozenDir, "_settings"))
    os.mkdir(os.path.join(frozenDir, "_settings", "pyzo"))
    with open(os.path.join(frozenDir, "_settings", "README.txt"), "wb") as file:
        file.write(SETTINGS_TEXT.encode("utf-8"))


# Patch info.plist
if sys.platform.startswith("darwin"):
    extra_plist_info = """
    <key>CFBundleShortVersionString</key>
    <string>X.Y.Z</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    """.strip()
    extra_plist_info = "\n\t".join(
        line.strip() for line in extra_plist_info.splitlines()
    )
    extra_plist_info = extra_plist_info.replace("X.Y.Z", __version__)
    plist_filename = os.path.join(distDir, "pyzo.app", "Contents", "Info.plist")
    text = open(plist_filename, "rb").read().decode()
    i1 = text.index("<key>CFBundleShortVersionString</key")
    i2 = text.index("</string>", i1) + len("</string>")
    text = text[:i1] + extra_plist_info + text[i2:]
    with open(plist_filename, "wb") as f:
        f.write(text.encode())


## Package things up

# Linux: .tar.gz
# Windows: zip and exe installer
# MacOS: DMG


if sys.platform.startswith("linux"):
    print("Packing up into tar.gz ...")

    oridir = os.getcwd()
    os.chdir(distDir)
    try:
        tarfilename = "pyzo-" + __version__ + "-linux" + bitness + ".tar.gz"
        tf = tarfile.open(tarfilename, "w|gz")
        with tf:
            tf.add("pyzo", arcname="pyzo-" + __version__)
    finally:
        os.chdir(oridir)


if sys.platform.startswith("win"):
    print("Packing up into zip ...")

    zipfilename = "pyzo-" + __version__ + "-win" + bitness + ".zip"
    zf = zipfile.ZipFile(
        os.path.join(distDir, zipfilename), "w", compression=zipfile.ZIP_DEFLATED
    )
    with zf:
        for root, dirs, files in os.walk(os.path.join(distDir, "pyzo")):
            for fname in files:
                filename1 = os.path.join(root, fname)
                filename2 = os.path.relpath(filename1, os.path.join(distDir, "pyzo"))
                filename2 = os.path.join("pyzo-" + __version__, filename2)
                zf.write(filename1, filename2)


if sys.platform.startswith("win") and bitness == "64":
    # Note: for some reason the 32bit installer is broken. Ah well, the zip works.
    print("Packing up into exe installer (via Inno Setup) ...")

    exes = [
        r"c:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"c:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    ]
    for exe in exes:
        if os.path.isfile(exe):
            break
    else:
        raise RuntimeError("Could not find Inno Setup exe")

    # Set inno file
    innoFile1 = os.path.join(thisDir, "installerBuilderScript.iss")
    innoFile2 = os.path.join(thisDir, "installerBuilderScript2.iss")
    text = open(innoFile1, "rb").read().decode()
    text = text.replace("X.Y.Z", __version__).replace("64", bitness)
    if bitness == "32":
        text = text.replace("ArchitecturesInstallIn64BitMode = x64", "")
    with open(innoFile2, "wb") as f:
        f.write(text.encode())
    try:
        subprocess.check_call([exe, "/Qp", innoFile2])
    finally:
        os.remove(innoFile2)


if sys.platform.startswith("darwin"):
    print("Packing up into DMG ...")

    appDir = distDir + "pyzo.app"
    dmgFile = distDir + "pyzo-" + __version__ + "-macos.dmg"

    if (
        os.spawnlp(
            os.P_WAIT,
            "hdiutil",
            "hdiutil",
            "create",
            "-fs",
            "HFSX",
            "-format",
            "UDZO",
            dmgFile,
            "-imagekey",
            "zlib-level=9",
            "-srcfolder",
            appDir,
            "-volname",
            "pyzo",
        )
        != 0
    ):
        raise OSError("creation of the dmg failed")
