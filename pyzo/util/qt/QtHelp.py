from . import PYQT5, PYQT4, PYSIDE, PythonQtError


if PYQT5:
    from PyQt5.QtHelp import *
elif PYQT4:
    from PyQt4.QtHelp import *
elif PYSIDE:
    from PySide.QtHelp import *
else:
    raise PythonQtError('No Qt bindings could be found')
