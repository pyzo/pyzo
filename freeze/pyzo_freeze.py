#!/usr/bin/env python3

"""PyInstaller script

You can build a binary executable of Pyzo yourself:

* Install the dependencies, for example by typing the following line in a shell in Pyzo:
pip install --upgrade pip pyside6 pyinstaller dialite

* Run this script.

* The result is in the "dist" folder, in the same directory as this script.

"""

import os
import sys
import shutil
import inspect

# Definitions
name = "pyzo"
qt_api = os.getenv("PYZO_QT_API", "PySide6")
this_dir = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))
exe_script = os.path.join(this_dir, "boot.py")
dist_dir = os.path.join(this_dir, "dist")
icon_file = os.path.abspath(
    os.path.join(this_dir, "..", "pyzo", "resources", "appicons", "pyzologo.ico")
)

# Run the script from the freeze dir
os.chdir(this_dir)


## Utils


def get_pyzo_version():
    """Get Pyzo's version."""
    filename = os.path.join(dist_dir, "..", "..", "pyzo", "__init__.py")
    NS = {}
    with open(filename, "rb") as fd:
        data = fd.read()
    for line in data.decode().splitlines():
        if line.startswith("__version__"):
            exec(line.strip(), NS, NS)
    if not NS.get("__version__", 0):
        raise RuntimeError("Could not find __version__")
    return NS["__version__"]


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


def get_python_stdlib_path():
    # This code is extracted from distutils.sysconfig.get_python_lib (distutils is deprecated in 3.12)
    stdlib_path = None
    prefix = os.path.normpath(sys.base_prefix)
    if os.name == "posix":
        libdir = sys.platlibdir
        foldername = "python{}.{}".format(*sys.version_info[:2])
        stdlib_path = os.path.join(prefix, libdir, foldername)
    elif os.name == "nt":
        stdlib_path = os.path.join(prefix, "Lib")
    else:
        raise Exception("unknown operating system")
    return stdlib_path


def get_stdlib_modules():
    """Return a list of all module names that are part of the Python Standard Library."""
    stdlib_path = get_python_stdlib_path()
    extensions = {"py", "so", "dll", "pyd"}
    skip = {
        "site-packages",  # not stdlib
        "idlelib",  # irrelevant for us
        "lib2to3",  # irrelevant for us
        "test",  # irrelevant for us
        "turtledemo",  # irrelevant for us
        "tkinter",  # not needed
        "tk",
        "tcl",
        "unittest",  # not needed
        "distutils",  # not needed - also must be avoided*
    }
    # On distutils: one distutils submodule causes IPython to be included,
    # and with that, a sloth of libs like matplotlib and multiple Qt libs.
    return list(_find_modules(stdlib_path, extensions, skip))


# All known Qt toolkits, excluded the one we will use
other_qt_kits = {"PySide2", "PySide6", "PyQt5", "PyQt6"}
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
with open(os.path.join(this_dir, "frozen_libs.txt"), "rb") as fd:
    includes += fd.read().decode().split()

# Include a subset of Qt modules
qt_includes = [
    "QtCore",  # Standard
    "QtGui",  # Standard
    "QtWidgets",  # Standard
    "QtPrintSupport",  # For PDF export
]
includes += [f"{qt_api}.{sub}" for sub in qt_includes]


# There is a tendency to include tk modules
excludes += ["tkinter", "tk", "tcl"]

# Also exclude other Qt toolkits just to be sure
excludes += list(other_qt_kits)

# PySide tends to include *all* qt modules, resulting in a 300MB or so folder,
# so we mark them as unwanted, getting us at around 120MB.
qt_excludes = [
    "QtNetwork",
    "QtOpenGL",
    "QtOpenGLWidgets",
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
    "QtHelp",
]
excludes += [f"{qt_api}.{sub}" for sub in qt_excludes]

## Data

# Specify additional "data" that we want to copy over.
# Better to let PyInstaller copy it rather than copying it after the fact.

data1 = {}  # Applied via PyInstaller
data2 = {}  # Manyally copied at the end

data1["_settings"] = "_settings"

# Anything that has .py files should be in data2 on MacOS,
# see https://github.com/pyzo/pyzo/issues/830
if sys.platform.startswith("darwin"):
    data2["../pyzo"] = "source/pyzo"
else:
    data1["../pyzo"] = "source/pyzo"

# Good to first clean up
count = 0
for data_dir in set(data1.keys()) | set(data2.keys()):
    data_dir = os.path.abspath(os.path.join(this_dir, data_dir))
    if os.path.isdir(data_dir):
        for root, dirnames, filenames in os.walk(data_dir):
            for dirname in dirnames:
                if dirname == "__pycache__":
                    shutil.rmtree(os.path.join(root, dirname))
                    count += 1
print(f"removed {count} __pycache__ dirs")


## Create spec

import PyInstaller.__main__
import PyInstaller.utils.cliutils.makespec

entrypoint_pyinstaller = PyInstaller.__main__.run
entrypoint_makespec = PyInstaller.utils.cliutils.makespec.run


# Clear first
if os.path.isdir(dist_dir):
    shutil.rmtree(dist_dir)
os.makedirs(dist_dir)

# Build command
cmd = ["--onedir", "--name", name]

for m in includes:
    cmd.extend(["--hidden-import", m])
for m in excludes:
    cmd.extend(["--exclude-module", m])
for src, dst in data1.items():
    cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

if sys.platform.startswith("win"):
    cmd.append("--windowed")  # not a console app
    cmd.extend(["--icon", icon_file])
elif sys.platform.startswith("darwin"):
    cmd.append("--windowed")  # makes a .app bundle
    cmd.extend(["--icon", icon_file[:-3] + "icns"])
    cmd.extend(["--osx-bundle-identifier", "org.pyzo.app"])

cmd.append(exe_script)

sys.argv[1:] = cmd
entrypoint_makespec()


## Fix spec

specfilename = os.path.join(this_dir, f"{name}.spec")
with open(specfilename, "rb") as f:
    spec = f.read().decode()

if sys.platform.startswith("darwin"):
    i = spec.find("bundle_identifier=")
    assert i > 0
    spec = spec[:i] + f"version='{get_pyzo_version()}',\n             " + spec[i:]

with open(specfilename, "wb") as f:
    f.write(spec.encode())


## Freeze

entrypoint_pyinstaller(["--clean", "--distpath", dist_dir, specfilename])

# try:
#     os.remove(specfilename)
# except Exception:
#     pass


## Copy data after freezing

if sys.platform.startswith("darwin"):
    source_dir = os.path.join(dist_dir, "pyzo.app", "Contents", "Resources")
else:
    source_dir = os.path.join(dist_dir, "pyzo")

for dir1, dir2 in data2.items():
    shutil.copytree(
        os.path.abspath(os.path.join(this_dir, dir1)),
        os.path.abspath(os.path.join(source_dir, dir2)),
    )
    print("Copied", dir1, "->", dir2)


# In the GH Action we perform a sign again
