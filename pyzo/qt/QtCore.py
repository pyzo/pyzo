from . import API

if API == "PySide6":
    from PySide6.QtCore import *
elif API == "PyQt6":
    from PyQt6.QtCore import *
    from PyQt6.QtCore import pyqtSignal as Signal
    from PyQt6.QtCore import pyqtBoundSignal as SignalInstance
    from PyQt6.QtCore import pyqtSlot as Slot
    from PyQt6.QtCore import pyqtProperty as Property
elif API == "PySide2":
    from PySide2.QtCore import *
elif API == "PyQt5":
    from PyQt5.QtCore import *
    from PyQt5.QtCore import pyqtSignal as Signal
    from PyQt5.QtCore import pyqtBoundSignal as SignalInstance
    from PyQt5.QtCore import pyqtSlot as Slot
    from PyQt5.QtCore import pyqtProperty as Property

if API in ("PySide2", "PyQt5"):
    QLibraryInfo.path = QLibraryInfo.location
    QLibraryInfo.LibraryPath = QLibraryInfo
