import os
import sys
import platform
import traceback
import importlib

import dialite


TEST = "--test" in sys.argv


# %% Utils


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
        sys.stderr.write(f"{title}\n{msg}\n{tb_info}\n")
    except Exception:
        pass
    # Use dialite to show error in modal window
    if not TEST:
        dialite.fail(title, msg)


class BootAction:
    def __init__(self, action):
        self._action = action
        try:
            sys.stdout.write(action + "\n")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, cls, err, tb):
        if err:
            error_handler(cls, err, tb, self._action)
            sys.exit(1)


# %% Boot

if TEST:
    print("Checking Pyzo container")
    print(platform.platform())
    print(sys.version)


with BootAction("setting up source importer"):
    source_dir = os.path.join(sys._MEIPASS, "source")
    sys.path.insert(0, source_dir)
    sys.meta_path.insert(0, SourceImporter(source_dir))


with BootAction("applying pre-import Qt tweaks"):
    importlib.import_module("pyzo.pre_qt_import")


with BootAction("importing Qt"):
    QtCore = importlib.import_module("pyzo.qt." + "QtCore")
    QtGui = importlib.import_module("pyzo.qt." + "QtGui")
    QtWidgets = importlib.import_module("pyzo.qt." + "QtWidgets")


with BootAction("running Pyzo"):
    pyzo = importlib.import_module("pyzo")
    pyzo.start()
