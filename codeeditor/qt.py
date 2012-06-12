try:
    from PySide import QtGui, QtCore
except ImportError:
    from PyQt4 import QtCore, QtGui
    QtCore.Signal = QtCore.pyqtSignal
