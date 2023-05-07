#
# Copyright © 2014-2015 Colin Duquesnoy
# Copyright © 2009- The Spyder Developmet Team
#
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""
Provides widget classes and functions.
"""
from . import PYQT5, PYQT6, PYSIDE2, PYSIDE6, PythonQtError


if PYQT6:
    from PyQt6 import QtWidgets
    from PyQt6.QtWidgets import *
    from PyQt6.QtGui import QAction, QActionGroup, QShortcut, QFileSystemModel
    from PyQt6.QtOpenGLWidgets import QOpenGLWidget

    # Map missing/renamed methods
    import inspect
    QTextEdit.setTabStopWidth = inspect.getattr_static(QTextEdit, 'setTabStopDistance')
    QTextEdit.tabStopWidth = inspect.getattr_static(QTextEdit, 'tabStopDistance')
    QTextEdit.print_ = inspect.getattr_static(QTextEdit, 'print')
    QPlainTextEdit.setTabStopWidth = inspect.getattr_static(QPlainTextEdit, 'setTabStopDistance')
    QPlainTextEdit.tabStopWidth = inspect.getattr_static(QPlainTextEdit, 'tabStopDistance')
    QPlainTextEdit.print_ = inspect.getattr_static(QPlainTextEdit, 'print')
    QApplication.exec_ = inspect.getattr_static(QApplication, 'exec')
    QDialog.exec_ = inspect.getattr_static(QDialog, 'exec')
    QMenu.exec_ = inspect.getattr_static(QMenu, 'exec')

    from .enums_compat import promote_enums
    promote_enums(QtWidgets)
    del QtWidgets
    del inspect
elif PYQT5:
    from PyQt5.QtWidgets import *
elif PYSIDE6:
    from PySide6 import QtWidgets
    from PySide6.QtWidgets import *
    from PySide6.QtGui import QAction, QActionGroup, QShortcut
    from PySide6.QtOpenGLWidgets import QOpenGLWidget

    # Map missing/renamed methods
    QTextEdit.setTabStopWidth = QTextEdit.setTabStopDistance
    QTextEdit.tabStopWidth = QTextEdit.tabStopDistance
    QPlainTextEdit.setTabStopWidth = QPlainTextEdit.setTabStopDistance
    QPlainTextEdit.tabStopWidth = QPlainTextEdit.tabStopDistance

    # Map DeprecationWarning methods
    QApplication.exec_ = QApplication.exec
    QDialog.exec_ = QDialog.exec
    QMenu.exec_ = QMenu.exec

    from .enums_compat import promote_enums
    promote_enums(QtWidgets)
    del QtWidgets
elif PYSIDE2:
    from PySide2.QtWidgets import *
else:
    raise PythonQtError("No Qt bindings could be found")
