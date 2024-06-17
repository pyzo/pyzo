from . import API

if API == "PySide6":
    from PySide6.QtHelp import *
elif API == "PyQt6":
    from PyQt6.QtHelp import *
elif API == "PySide2":
    from PySide2.QtHelp import *
elif API == "PyQt5":
    from PyQt5.QtHelp import *
