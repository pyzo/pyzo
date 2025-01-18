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

# Import yoton (absolute import instead of a relative import)
sys.path.insert(0, os.path.dirname(__file__))
import yoton  # noqa

del sys.path[0]

from pyzo.util import paths

# If there already is an instance of Pyzo, and the user is trying a
# Pyzo command, we should send the command to the other process and quit.
# We do this here, where we have not yet loaded Qt, so we are very light.
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

try:
    QtWidgets.QApplication.setDesktopFileName("org.pyzo.Pyzo")
    # --> this name is according to the freedesktop.org standards and
    # will refer to a file "org.pyzo.Pyzo.desktop" in the proper directory
    # e.g. "/usr/share/applications" or "~/.local/share/applications"
    # an example file is located at "./resources/org.pyzo.Pyzo.desktop"
except Exception:
    pass  # fail on older Qt's < 5.7

# Import language/translation tools
from pyzo.util._locale import translate, setLanguage

pyzo.translate = translate
pyzo.setLanguage = setLanguage


class MyApp(QtWidgets.QApplication):
    """So we an open .py files on OSX.
    OSX is smart enough to call this on the existing process.
    """

    def event(self, event):
        if isinstance(event, QtGui.QFileOpenEvent):
            fname = str(event.file())
            if fname and fname != "pyzo":
                sys.argv[1:] = [fname]
                res = commandline.handle_cmd_args()
                if not commandline.is_our_server_running():
                    print(res)
                    sys.exit()
        return super().event(event)


if not sys.platform.startswith("darwin"):
    MyApp = QtWidgets.QApplication


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


def resetConfig(preserveState=True):
    """Deletes the config file to revert to default and prevent Pyzo from storing
    its config on the next shutdown.
    """
    # Get filenames
    configFileName2 = os.path.join(pyzo.appConfigDir, "config.ssdf")
    os.remove(configFileName2)
    pyzo._saveConfigFile = False
    print("Deleted user config file. Restart Pyzo to revert to the default config.")


def loadThemes():
    """Load default and user themes (if exist)"""

    def loadThemesFromDir(dname, isBuiltin=False):
        if not os.path.isdir(dname):
            return
        for fname in [fname for fname in os.listdir(dname) if fname.endswith(".theme")]:
            try:
                theme = ssdf.load(os.path.join(dname, fname))
                assert theme.name.lower() == fname.lower().split(".")[0], (
                    "Theme name does not match filename"
                )
                theme.data = {
                    key.replace("_", "."): val for key, val in theme.data.items()
                }
                theme["builtin"] = isBuiltin
                pyzo.themes[theme.name.lower()] = theme
                print("Loaded theme", repr(theme.name))
            except Exception as ex:
                print("Warning! Error while reading {}: {}".format(fname, ex))

    loadThemesFromDir(os.path.join(pyzo.pyzoDir, "resources", "themes"), True)
    loadThemesFromDir(os.path.join(pyzo.appDataDir, "themes"))


def loadConfig(defaultsOnly=False):
    """Load default and site-wide configuration file(s) and that of the user
    (if it exists).
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
            t = "Error while reading config file {!r}, maybe it's corrupt?"
            print(t.format(fname))
            raise

    # Load user config and inject in pyzo.config
    fname = os.path.join(pyzo.appConfigDir, "config.ssdf")
    if os.path.isfile(fname):
        try:
            userConfig = ssdf.load(fname)
            replaceFields(config, userConfig)
        except Exception:
            t = "Error while reading config file {!r}, maybe it's corrupt?"
            print(t.format(fname))
            raise


def saveConfig():
    """Save all configurations to file."""

    # Let the editorStack save its state
    if pyzo.editors:
        pyzo.editors.saveEditorState()

    # Let the main window save its state
    if pyzo.main:
        pyzo.main.saveWindowState()

    # Store config
    if pyzo._saveConfigFile:
        ssdf.save(os.path.join(pyzo.appConfigDir, "config.ssdf"), pyzo.config)


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
        # We will use a periodic timer instead of a single shot one because of strange
        # problems with the github CI workflow.
        # Combinations of Qt 6.7 and Microsoft Windows Server 2022 sometimes raised
        # error "'KernelBroker' object has no attribute '_reqp_introspect'".
        # The single shot timer callback was called way too early: a few milliseconds
        # after starting the timer instead of the given interval of 5000 ms.
        # This problem did not always result in an error in the CI workflow.
        # When the error occured, re-running the failed test cases of the workflow
        # a few times made the failed test cases finally pass.
        # The following new approach did not have such problems so far.

        import time

        def testrunTimerCallback(*args):
            dt = time.time() - startTime
            print("*** testrunTimerCallback:", dt, "s ***")
            if time.time() - startTime > 5.0:
                timer.stop()
                msg = "Stopping after {} s".format(dt)
                print(msg)
                if os.getenv("PYZO_LOG", ""):
                    with open(os.getenv("PYZO_LOG"), "at") as fd:
                        fd.write(msg + "\n")
                pyzo.main.close()

        startTime = time.time()
        timer = QtCore.QTimer()
        timer.setInterval(500)
        timer.timeout.connect(testrunTimerCallback)
        timer.start()

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
pyzo.appDataDir, pyzo.appConfigDir = paths.prepare_appdata_appconfig_dirs()
pyzo.pyzoDir = os.path.abspath(os.path.dirname(__file__))

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
