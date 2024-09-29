from . import API

if API == "PySide6":
    from PySide6.QtGui import *
elif API == "PyQt6":
    from PyQt6.QtGui import *
elif API == "PySide2":
    from PySide2.QtGui import *
    from PySide2.QtWidgets import QAction, QActionGroup
    from PySide2.QtCore import QPointF as _QPointF
elif API == "PyQt5":
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import QAction, QActionGroup
    from PyQt5.QtCore import QPointF as _QPointF

if API in ("PySide2", "PyQt5"):
    QMouseEvent.position = lambda self: _QPointF(self.pos())
    QDropEvent.position = lambda self: _QPointF(self.posF())

    # For Qt5 we need something like QFontDatabase = QFontDatabase()
    # but with instance creation just when first accessing the class.
    def _getFontDatabase(name):
        if not hasattr(_QFontDatabaseWrapper, "_instance"):
            _QFontDatabaseWrapper._instance = _QFontDatabaseWrapper._original()
        return getattr(_QFontDatabaseWrapper._instance, name)

    class _QFontDatabaseWrapper:
        _original = QFontDatabase
        def __getattribute__(self, name): return _getFontDatabase(name)

    QFontDatabase = _QFontDatabaseWrapper()
