import os
import sys
import importlib

_QT_WRAPPERS = ("PySide6", "PyQt6", "PySide2", "PyQt5")


def get_desired_api():
    desired_api = None
    s = os.environ.get("QT_API", "").strip().lower()
    if len(s) > 0:
        for module_name in _QT_WRAPPERS:
            if module_name.lower() == s:
                desired_api = module_name
                break
    return desired_api


def load_modules(desired_api):
    loaded_modules = [s for s in sys.modules if s in _QT_WRAPPERS]
    if desired_api in loaded_modules:
        # use the preferred qt wrapper that is already loaded
        return desired_api
    if len(loaded_modules) > 0:
        # use another qt wrapper that is already loaded
        api = loaded_modules[0]
        print('using Qt binding "{}" because it is already loaded'.format(api))
        return api

    # no qt modules loaded, try to import the preferred one first
    if desired_api is not None:
        order_to_try = [desired_api] + [s for s in _QT_WRAPPERS if s != desired_api]
    else:
        order_to_try = list(_QT_WRAPPERS)

    for api in order_to_try:
        try:
            importlib.import_module(api)
        except ModuleNotFoundError:
            pass
        else:
            if desired_api is not None and api != desired_api:
                print('using Qt binding "{}" instead of "{}"'.format(api, desired_api))
            return api
    raise ImportError("no suitable Qt wrapper found")


API = load_modules(get_desired_api())

def _get_versions():
    """returns the qt and wrapper version as strings"""
    mod = importlib.import_module(API)
    importlib.import_module(API + '.QtCore')
    if API.startswith("PySide"):
        qt_version = mod.QtCore.__version__
        wrapper_version = mod.__version__
    else:
        qt_version = mod.QtCore.QT_VERSION_STR
        wrapper_version = mod.QtCore.PYQT_VERSION_STR
    return qt_version, wrapper_version


QT_VERSION_STR, QT_WRAPPER_VERSION_STR = _get_versions()

from . import qtutils
