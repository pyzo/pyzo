from . import API

if API == "PySide6":
    from PySide6.QtWidgets import *
elif API == "PyQt6":
    from PyQt6.QtWidgets import *
    from PyQt6.QtGui import QFileSystemModel
    import inspect
    QPlainTextEdit.print_ = inspect.getattr_static(QPlainTextEdit, "print")
    QMenu.exec_ = inspect.getattr_static(QMenu, "exec")
    del inspect
elif API == "PySide2":
    from PySide2.QtWidgets import *
elif API == "PyQt5":
    from PyQt5.QtWidgets import *
