import importlib as _importlib


_QT_WRAPPERS = ("PySide6", "PyQt6", "PySide2", "PyQt5")


def _get_desired_api():
    import os

    desired_api = None
    s = os.environ.get("QT_API", "").strip().lower()
    if len(s) > 0:
        for module_name in _QT_WRAPPERS:
            if module_name.lower() == s:
                desired_api = module_name
                break
    return desired_api


def _load_modules(desired_api):
    import sys

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
            _importlib.import_module(api)
        except ModuleNotFoundError:
            pass
        else:
            if desired_api is not None and api != desired_api:
                print('using Qt binding "{}" instead of "{}"'.format(api, desired_api))
            return api
    raise ImportError("no suitable Qt wrapper found")


API = _load_modules(_get_desired_api())


def _get_versions():
    """returns the qt and wrapper version as strings"""
    mod = _importlib.import_module(API)
    _importlib.import_module(API + ".QtCore")
    if API.startswith("PySide"):
        qt_version = mod.QtCore.__version__
        wrapper_version = mod.__version__
    else:
        qt_version = mod.QtCore.QT_VERSION_STR
        wrapper_version = mod.QtCore.PYQT_VERSION_STR
    return qt_version, wrapper_version


QT_VERSION_STR, QT_WRAPPER_VERSION_STR = _get_versions()

from . import qtutils as qtutils  # we have to write it like this to satisfy ruff

del _get_versions, _load_modules, _get_desired_api


## Qt components

QtCore = _importlib.import_module(API + ".QtCore")
QtGui = _importlib.import_module(API + ".QtGui")
QtWidgets = _importlib.import_module(API + ".QtWidgets")
QtPrintSupport = _importlib.import_module(API + ".QtPrintSupport")


## QtCore fixes

if API in ("PyQt5", "PyQt6"):
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.SignalInstance = QtCore.pyqtBoundSignal
    QtCore.Slot = QtCore.pyqtSlot
    QtCore.Property = QtCore.pyqtProperty

if API in ("PySide2", "PyQt5"):
    QtCore.QLibraryInfo.path = QtCore.QLibraryInfo.location
    QtCore.QLibraryInfo.LibraryPath = QtCore.QLibraryInfo

## QtGui fixes

if API in ("PySide2", "PyQt5"):
    QtGui.QAction = QtWidgets.QAction
    QtGui.QActionGroup = QtWidgets.QActionGroup

    _QPointF = QtCore.QPointF
    QtGui.QMouseEvent.position = lambda self: _QPointF(self.pos())
    QtGui.QDropEvent.position = lambda self: _QPointF(self.posF())

    # For Qt5 we need something like QFontDatabase = QFontDatabase()
    # but with instance creation just when first accessing the class.
    def _getFontDatabase(name):
        if not hasattr(_QFontDatabaseWrapper, "_instance"):
            _QFontDatabaseWrapper._instance = _QFontDatabaseWrapper._original()
        return getattr(_QFontDatabaseWrapper._instance, name)

    class _QFontDatabaseWrapper:
        _original = QtGui.QFontDatabase

        def __getattribute__(self, name):
            return _getFontDatabase(name)

    QtGui.QFontDatabase = _QFontDatabaseWrapper()

## QtWidgets fixes

if API == "PyQt6":
    QtWidgets.QFileSystemModel = QtGui.QFileSystemModel

    import inspect

    QtWidgets.QPlainTextEdit.print_ = inspect.getattr_static(
        QtWidgets.QPlainTextEdit, "print"
    )
    QtWidgets.QMenu.exec_ = inspect.getattr_static(QtWidgets.QMenu, "exec")
    del inspect

## QtPrintSupport fixes

if API == "PyQt6":
    QtPrintSupport.QPrintPreviewWidget.print_ = QtPrintSupport.QPrintPreviewWidget.print
