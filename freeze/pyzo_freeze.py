#!/usr/bin/env python3

""" PyInstaller script
"""

import os
import sys
import shutil
from distutils.sysconfig import get_python_lib

import PyInstaller.__main__


# Definitions
name = "pyzo"
qt_api = os.getenv("PYZO_QT_API", "PySide6")
this_dir = os.path.abspath(os.path.dirname(__file__)) + "/"
exe_script = this_dir + "boot.py"
dist_dir = this_dir + "dist/"
icon_file = os.path.abspath(
    os.path.join(this_dir, "..", "pyzo", "resources", "appicons", "pyzologo.ico")
)


## Utils


def _find_modules(root, extensions, skip, parent=""):
    """Yield all modules and packages and their submodules and subpackages found at `root`.
    Nested folders that do _not_ contain an __init__.py file are assumed to also be on sys.path.
    `extensions` should be a set of allowed file extensions (without the .). `skip` should be
    a set of file or folder names to skip. The `parent` argument is for internal use only.
    """
    for filename in os.listdir(root):
        if filename.startswith("_"):
            continue
        if filename in skip:
            continue
        path = os.path.join(root, filename)
        if os.path.isdir(path):
            if filename.isidentifier() and os.path.exists(
                os.path.join(path, "__init__.py")
            ):
                if parent:
                    packageName = parent + "." + filename
                else:
                    packageName = filename
                for module in _find_modules(path, extensions, skip, packageName):
                    yield module
            elif not parent:
                for module in _find_modules(path, extensions, skip, ""):
                    yield module
        elif "." in filename:
            moduleName, ext = filename.split(".", 1)
            if ext in extensions and moduleName.isidentifier():
                if parent and moduleName == "__init__":
                    yield parent
                elif parent:
                    yield parent + "." + moduleName
                else:
                    yield moduleName


def get_stdlib_modules():
    """Return a list of all module names that are part of the Python Standard Library."""
    stdlib_path = get_python_lib(standard_lib=True)
    extensions = {"py", "so", "dll", "pyd"}
    skip = {
        "site-packages",  # not stdlib
        "idlelib",  # irrelevant for us
        "lib2to3",  # irrelevant for us
        "test",  # irrelevant for us
        "turtledemo",  # irrelevant for us
        "tkinter",  # not needed
        "unittest",  # not needed
        "distutils",  # not needed - also must be avoided*
    }
    # On distutils: one distutils submodule causes IPython to be included,
    # and with that, a sloth of libs like matplotlib and multiple Qt libs.
    return list(_find_modules(stdlib_path, extensions, skip))


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


# All known Qt toolkits, excluded the one we will use
other_qt_kits = {"PySide", "PySide2", "PySide6", "PyQt4", "PyQt5", "PyQt6"}
other_qt_kits.remove(qt_api)


## Includes and excludes

# We don't really make use of PySides detection mechanism, but instead specify
# explicitly what our binaries need. We include almost the whole stdlib, and
# a small subset of Qt. This way, future versions of Pyzo can work in the same
# container, and we still have a relatively small footprint.

includes = []
excludes = []

# Include almost all stdlib modules
includes += get_stdlib_modules()

# Include a few 3d party packages, e.g. deps of qtpy
includes += open(os.path.join(this_dir, "frozen_libs.txt"), "rt").read().split()

# Include a subset of Qt modules
qt_includes = [
    "QtCore",  # Standard
    "QtGui",  # Standard
    "QtWidgets",  # Standard
    "QtHelp",  # For docs
    "QtOpenGLWidgets",  # Because qtpy imports QOpenGLQWidget into QtWidgets
]
includes += [f"{qt_api}.{sub}" for sub in qt_includes]


# PySide tends to include *all* qt modules, resulting in a 300MB or so folder,
# so we mark them as unwanted, getting us at around 120MB.
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
excludes += [f"{qt_api}.{sub}" for sub in qt_excludes]


## Freeze

# Clear first
if os.path.isdir(dist_dir):
    shutil.rmtree(dist_dir)
os.makedirs(dist_dir)


cmd = ["--clean", "--onedir", "--name", name, "--distpath", dist_dir]

for m in includes:
    cmd.extend(["--hidden-import", m])
for m in excludes:
    cmd.extend(["--exclude-module", m])

if sys.platform.startswith("win"):
    cmd.append("--windowed")  # not a console app
    cmd.extend(["--icon", icon_file])
elif sys.platform.startswith("darwin"):
    cmd.append("--windowed")  # makes a .app bundle
    cmd.extend(["--icon", icon_file[:-3] + "icns"])
    cmd.extend(["--osx-bundle-identifier", "org.pyzo.app"])

cmd.append(exe_script)

PyInstaller.__main__.run(cmd)

try:
    os.remove(os.path.join(this_dir, f"{name}.spec"))
except Exception:
    pass


## Add Pyzo source

if sys.platform.startswith("darwin"):
    target_dir = os.path.join(dist_dir, "pyzo.app", "Contents", "MacOS")
else:
    target_dir = os.path.join(dist_dir, name)

copydir_smart(
    os.path.join(this_dir, "..", "pyzo"), os.path.join(target_dir, "source", "pyzo")
)


## Add portable settings dir

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
""".lstrip()

# Create settings folder and put in a file
os.mkdir(os.path.join(target_dir, "_settings"))
os.mkdir(os.path.join(target_dir, "_settings", "pyzo"))
with open(os.path.join(target_dir, "_settings", "README.txt"), "wb") as file:
    file.write(SETTINGS_TEXT.encode("utf-8"))
