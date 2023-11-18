#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Development Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides QtGui classes and functions.
"""
from . import PYQT6, PYQT5, PYSIDE2, PYSIDE6, PythonQtError


if PYQT6:
    from PyQt6.QtGui import *

    import inspect

    QFontMetrics.width = inspect.getattr_static(QFontMetrics, "horizontalAdvance")

    # Map missing/renamed methods
    QDrag.exec_ = inspect.getattr_static(QDrag, "exec")
    QGuiApplication.exec_ = inspect.getattr_static(QGuiApplication, "exec")
    QTextDocument.print_ = inspect.getattr_static(QTextDocument, "print")
    QTextDocument.FindFlags = lambda: QTextDocument.FindFlag(0)

    from .enums_compat import promote_enums

    from PyQt6 import QtGui

    QtGui.QMouseEvent.x = lambda self: int(self.position().x())
    QtGui.QMouseEvent.y = lambda self: int(self.position().y())
    if not hasattr(QtGui.QMouseEvent, "pos"):
        QtGui.QMouseEvent.pos = lambda self: self.position().toPoint()
    promote_enums(QtGui)

    # in Qt6 use QtGui.QFontDatabase.families() instead of QtGui.QFontDatabase().families()
    # https://doc.qt.io/qt-6/qfontdatabase-obsolete.html#QFontDatabase
    QtGui.QFontDatabase.__new__ = lambda cls: cls

    del QtGui
    del inspect
elif PYQT5:
    from PyQt5.QtGui import *
elif PYSIDE2:
    from PySide2.QtGui import *
elif PYSIDE6:
    from PySide6 import QtGui
    from PySide6.QtGui import *

    QFontMetrics.width = QFontMetrics.horizontalAdvance

    # Map DeprecationWarning methods
    QDrag.exec_ = QDrag.exec
    QGuiApplication.exec_ = QGuiApplication.exec
    QtGui.QMouseEvent.x = lambda self: int(self.position().x())
    QtGui.QMouseEvent.y = lambda self: int(self.position().y())
    QtGui.QMouseEvent.pos = lambda self: self.position().toPoint()

    from .enums_compat import promote_enums

    promote_enums(QtGui)
else:
    raise PythonQtError("No Qt bindings could be found")
