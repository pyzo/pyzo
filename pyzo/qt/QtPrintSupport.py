from . import API

if API == "PySide6":
    from PySide6.QtPrintSupport import *
elif API == "PyQt6":
    from PyQt6.QtPrintSupport import *
    QPrintPreviewWidget.print_ = QPrintPreviewWidget.print
elif API == "PySide2":
    from PySide2.QtPrintSupport import *
elif API == "PyQt5":
    from PyQt5.QtPrintSupport import *
