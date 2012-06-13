
# Simple module to allow using both PySide and PyQt4

# Try PyQt4 first, until IEP runs stable in PySide
try:
    from PyQt4 import QtCore, QtGui
    QtCore.Signal = QtCore.pyqtSignal # Define signal as pyqtSignal
except ImportError:
    try:
        from PySide import QtCore, QtGui
    except ImportError:
        raise ImportError("Both PySide and PyQt4 could not be imported.")

Qt = QtCore.Qt
