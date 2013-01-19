import sys
# Simple module to allow using both PySide and PyQt4

try:
    if sys.platform == 'darwin':
        raise ImportError # PySide causes crashes on Mac OS X
        
    from PySide import QtCore, QtGui
except ImportError:
    try:
        from PyQt4 import QtCore, QtGui
        QtCore.Signal = QtCore.pyqtSignal # Define signal as pyqtSignal
    except ImportError:
        raise ImportError("Both PySide and PyQt4 could not be imported.")

