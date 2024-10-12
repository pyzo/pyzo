import os
import sys
import time
import platform
import traceback
import importlib

import dialite


TESTING = "--test" in sys.argv


# %% Utils


def write(*msg):
    print(*msg)
    if os.getenv("PYZO_LOG", ""):
        with open(os.getenv("PYZO_LOG"), "at") as f:
            f.write(" ".join(msg) + "\n")


class SourceImporter:
    def __init__(self, dir):
        self.module_names = set()
        for name in os.listdir(dir):
            fullname = os.path.join(dir, name)
            if name.endswith(".py"):
                self.module_names.add(name)
            elif os.path.isdir(fullname):
                if os.path.isfile(os.path.join(fullname, "__init__.py")):
                    self.module_names.add(name)

    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] in self.module_names:
            return sys.meta_path[1].find_spec(fullname, path, target)
        else:
            return None


def error_handler(cls, err, tb, action=""):
    title = "Application aborted"
    if action:
        title += f" while {action}"
    msg = f"{cls.__name__}: {err}"
    # Try writing traceback to stderr
    try:
        tb_info = "".join(traceback.format_list(traceback.extract_tb(tb)))
        write(f"{title}\n{msg}\n{tb_info}")
    except Exception:
        pass
    # Use dialite to show error in modal window
    if not TESTING:
        dialite.fail(title, msg)


class BootAction:
    def __init__(self, action):
        self._action = action
        try:
            write(action)
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, cls, err, tb):
        if err:
            if not isinstance(err, SystemExit) or err.code:
                error_handler(cls, err, tb, self._action)
                if not isinstance(err, SystemExit):
                    sys.exit(1)


# %% Boot

if TESTING:
    dt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    write(f"Testing Pyzo binary ({dt} UTC)")
    write(platform.platform())
    write(sys.version)


with BootAction("Setting up source importer"):
    if sys._MEIPASS.strip("/").endswith(
        (".app/Contents/MacOS", ".app/Contents/Frameworks")
    ):
        # Note: it looks like the source dir IS available just after we froze it,
        # so the test_frozen run passes. However, the packaged versions only
        # have the source dir in Contents/Resources.
        # Not sure why, maybe related to symlinks?
        source_dir = os.path.join(sys._MEIPASS, "..", "Resources", "source")
    else:
        source_dir = os.path.join(sys._MEIPASS, "source")
    source_dir = os.path.abspath(source_dir)
    if TESTING:
        write(f"Source dir: {source_dir} {os.path.isdir(source_dir)}")
    sys.path.insert(0, source_dir)
    sys.meta_path.insert(0, SourceImporter(source_dir))


with BootAction("Applying pre-import Qt tweaks"):
    importlib.import_module("pyzo.pre_qt_import")


# let Pyzo fail early if there are problems with Qt
with BootAction("Importing Qt"):
    importlib.import_module("pyzo.qt")


with BootAction("Running Pyzo"):
    pyzo = importlib.import_module("pyzo")
    write(f"Pyzo {pyzo.__version__}")
    pyzo.start()
    write("Stopped")  # may be written to log twice because Pyzo defers stdout
