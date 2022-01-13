import os
import sys
import ctypes
import locale
import traceback

import pyzo

# Import this module that applies some tweaks that need to be applied
# before import qt. This is a separate module, so that the frozen app
# can import before checking the qt import.
from . import pre_qt_import  # noqa: F401

# Import yoton as an absolute package
from pyzo import yotonloader  # noqa
from pyzo.util import paths

# If there already is an instance of Pyzo, and the user is trying an
# Pyzo command, we should send the command to the other process and quit.
# We do this here, were we have not yet loaded Qt, so we are very light.
from pyzo.core import commandline

if commandline.is_our_server_running():
    print("Started our command server")
else:
    # Handle command line args now
    res = commandline.handle_cmd_args()
    if res:
        print(res)
        sys.exit()
    else:
        # No args, proceed with starting up
        print("Our command server is *not* running")


from pyzo.util import zon as ssdf  # zon is ssdf-light
from pyzo.qt import QtCore, QtGui, QtWidgets

# Enable high-res displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass  # fail on non-windows
try:
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
except Exception:
    pass  # fail on older Qt's

# Import language/translation tools
from pyzo.util._locale import translate, setLanguage  # noqa

pyzo.translate = translate
pyzo.setLanguage = setLanguage

# Set environ to let kernel know some stats about us
os.environ["PYZO_PREFIX"] = sys.prefix
_is_pyqt4 = hasattr(QtCore, "PYQT_VERSION_STR")
os.environ["PYZO_QTLIB"] = "PyQt4" if _is_pyqt4 else "PySide"


class MyApp(QtWidgets.QApplication):
    """So we an open .py files on OSX.
    OSX is smart enough to call this on the existing process.
    """

    def event(self, event):
        if isinstance(event, QtGui.QFileOpenEvent):
            fname = str(event.file())
            if fname and fname != "pyzo":
                sys.argv[1:] = []
                sys.argv.append(fname)
                res = commandline.handle_cmd_args()
                if not commandline.is_our_server_running():
                    print(res)
                    sys.exit()
        return QtWidgets.QApplication.event(self, event)


if not sys.platform.startswith("darwin"):
    MyApp = QtWidgets.QApplication  # noqa


## Install excepthook
# In PyQt5 exceptions in Python will cause an abort
# http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html


def pyzo_excepthook(type, value, tb):
    out = "Uncaught Python exception: " + str(value) + "\n"
    out += "".join(traceback.format_list(traceback.extract_tb(tb)))
    out += "\n"
    sys.stderr.write(out)


sys.excepthook = pyzo_excepthook


## Define some functions


# todo: move some stuff out of this module ...


def getResourceDirs():
    """getResourceDirs()
    Get the directories to the resources: (pyzoDir, appDataDir, appConfigDir).
    Also makes sure that the appDataDir has a "tools" directory and
    a style file.
    """

    pyzoDir = os.path.abspath(os.path.dirname(__file__))
    if ".zip" in pyzoDir:
        raise RuntimeError("The Pyzo package cannot be run from a zipfile.")

    # Get where the application data is stored (use old behavior on Mac)
    appDataDir, appConfigDir = paths.appdata_dir("pyzo", roaming=True, macAsLinux=True)

    # Create tooldir if necessary
    toolDir = os.path.join(appDataDir, "tools")
    os.makedirs(toolDir, exist_ok=True)

    return pyzoDir, appDataDir, appConfigDir


def resetConfig(preserveState=True):
    """resetConfig()
    Deletes the config file to revert to default and prevent Pyzo from storing
    its config on the next shutdown.
    """
    # Get filenames
    configFileName2 = os.path.join(pyzo.appConfigDir, "config.ssdf")
    os.remove(configFileName2)
    pyzo._saveConfigFile = False
    print("Deleted user config file. Restart Pyzo to revert to the default config.")


def loadThemes():
    """
    Load default and user themes (if exist)
    """

    def loadThemesFromDir(dname, isBuiltin=False):
        if not os.path.isdir(dname):
            return
        for fname in [fname for fname in os.listdir(dname) if fname.endswith(".theme")]:
            try:
                theme = ssdf.load(os.path.join(dname, fname))
                assert (
                    theme.name.lower() == fname.lower().split(".")[0]
                ), "Theme name does not match filename"
                theme.data = {
                    key.replace("_", "."): val for key, val in theme.data.items()
                }
                theme["builtin"] = isBuiltin
                pyzo.themes[theme.name.lower()] = theme
                print("Loaded theme %r" % theme.name)
            except Exception as ex:
                print("Warning ! Error while reading %s: %s" % (fname, ex))

    loadThemesFromDir(os.path.join(pyzo.pyzoDir, "resources", "themes"), True)
    loadThemesFromDir(os.path.join(pyzo.appDataDir, "themes"))


def loadConfig(defaultsOnly=False):
    """loadConfig(defaultsOnly=False)
    Load default and site-wide configuration file(s) and that of the user (if it exists).
    Any missing fields in the user config are set to the defaults.
    """

    # Function to insert names from one config in another
    def replaceFields(base, new):
        for key in new:
            if key in base and isinstance(base[key], ssdf.Struct):
                replaceFields(base[key], new[key])
            else:
                base[key] = new[key]

    config = pyzo.config

    # Reset our pyzo.config structure
    ssdf.clear(config)

    # Load default and inject in the pyzo.config
    fname = os.path.join(pyzo.pyzoDir, "resources", "defaultConfig.ssdf")
    defaultConfig = ssdf.load(fname)
    replaceFields(config, defaultConfig)

    # Platform specific keybinding: on Mac, Ctrl+Tab (actually Cmd+Tab) is a system shortcut
    if sys.platform == "darwin":
        config.shortcuts2.view__select_previous_file = "Alt+Tab,"

    # Load site-wide config if it exists and inject in pyzo.config
    fname = os.path.join(pyzo.pyzoDir, "resources", "siteConfig.ssdf")
    if os.path.isfile(fname):
        try:
            siteConfig = ssdf.load(fname)
            replaceFields(config, siteConfig)
        except Exception:
            t = "Error while reading config file %r, maybe its corrupt?"
            print(t % fname)
            raise

    # Load user config and inject in pyzo.config
    fname = os.path.join(pyzo.appConfigDir, "config.ssdf")
    if os.path.isfile(fname):
        try:
            userConfig = ssdf.load(fname)
            replaceFields(config, userConfig)
        except Exception:
            t = "Error while reading config file %r, maybe its corrupt?"
            print(t % fname)
            raise


def saveConfig():
    """saveConfig()
    Save all configureations to file.
    """

    # Let the editorStack save its state
    if pyzo.editors:
        pyzo.editors.saveEditorState()

    # Let the main window save its state
    if pyzo.main:
        pyzo.main.saveWindowState()

    # Store config
    if pyzo._saveConfigFile:
        ssdf.save(os.path.join(pyzo.appConfigDir, "config.ssdf"), pyzo.config)


pyzo.getResourceDirs = getResourceDirs
pyzo.resetConfig = resetConfig
pyzo.loadThemes = loadThemes
pyzo.saveConfig = saveConfig


def start():
    """Run Pyzo."""

    # Do some imports
    import pyzo
    from pyzo.core import pyzoLogging  # noqa - to start logging asap
    from pyzo.core.main import MainWindow

    # Apply users' preferences w.r.t. date representation etc
    # this is required for e.g. strftime("%c")
    # Just using '' does not seem to work on OSX. Thus
    # this odd loop.
    # locale.setlocale(locale.LC_ALL, "")
    for x in ("", "C", "en_US", "en_US.utf8", "en_US.UTF-8"):
        try:
            locale.setlocale(locale.LC_ALL, x)
            break
        except Exception:
            pass

    # # Set to be aware of the systems native colors, fonts, etc.
    # QtWidgets.QApplication.setDesktopSettingsAware(True)

    # Instantiate the application
    QtWidgets.qApp = MyApp(sys.argv)  # QtWidgets.QApplication([])

    # Choose language, get locale
    appLocale = setLanguage(pyzo.config.settings.language)

    # Create main window, using the selected locale
    MainWindow(None, appLocale)

    # In test mode, we close after 5 seconds
    # We also write "Closed" to the log (if a filename is provided) which we use
    # in our tests to determine that Pyzo did a successful run.
    if "--test" in sys.argv:
        close_signal = lambda: print("Stopping")
        if os.getenv("PYZO_LOG", ""):
            close_signal = lambda: open(os.getenv("PYZO_LOG"), "at").write("Stopping\n")
        pyzo.test_close_timer = t = QtCore.QTimer()
        t.setInterval(5000)
        t.setSingleShot(True)
        t.timeout.connect(lambda: [close_signal(), pyzo.main.close()])
        t.start()

    # Enter the main loop
    if hasattr(QtWidgets.qApp, "exec"):
        QtWidgets.qApp.exec()
    else:
        QtWidgets.qApp.exec_()


## Init

# List of names that are later overriden (in main.py)
pyzo.editors = None  # The editor stack instance
pyzo.shells = None  # The shell stack instance
pyzo.main = None  # The mainwindow
pyzo.icon = None  # The icon
pyzo.parser = None  # The source parser
pyzo.status = None  # The statusbar (or None)

# Get directories of interest
pyzo.pyzoDir, pyzo.appDataDir, pyzo.appConfigDir = getResourceDirs()

# Whether the config file should be saved
pyzo._saveConfigFile = True

# Create ssdf in module namespace, and fill it
pyzo.config = ssdf.new()
loadConfig()

try:
    # uses the fact that float("") raises ValueError to be NOP when qtscalefactor setting is not set
    os.environ["QT_SCREEN_SCALE_FACTORS"] = str(
        float(pyzo.config.settings.qtscalefactor)
    )
except Exception:
    pass

# Create style dict and fill it
pyzo.themes = {}
loadThemes()
# Init default style name (set in main.restorePyzoState())
pyzo.defaultQtStyleName = ""
