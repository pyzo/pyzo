"""
Vendored version of qtpy/__init__.py, but modified to prefer the installed
version of qtpy instead.
"""

try:
    
    # Try to use qtpy rather than our vendored version. Throughout Pyzo
    # we only use from ...qt import QtXxx, i.e. not from ..qt.QtXxx import yy,
    # so this all we need.
    # Note that QtHelp and QtPrintSupport are loaded from the vendored version,
    # but these are only imported when needed.
    from qtpy import *
    from qtpy import QtCore, QtGui, QtWidgets

except ImportError:

    import os
    
    # Version of QtPy
    from ._version import __version__
    
    #: Qt API environment variable name
    QT_API = 'QT_API'
    #: names of the expected PyQt5 api
    PYQT5_API = ['pyqt5']
    #: names of the expected PyQt4 api
    PYQT4_API = [
        'pyqt',  # name used in IPython.qt
        'pyqt4'  # pyqode.qt original name
    ]
    #: names of the expected PySide api
    PYSIDE_API = ['pyside']
    
    os.environ.setdefault(QT_API, 'pyqt5')
    API = os.environ[QT_API].lower()
    assert API in (PYQT5_API + PYQT4_API + PYSIDE_API)
    
    is_old_pyqt = is_pyqt46 = False
    PYQT5 = True
    PYQT4 = PYSIDE = False
    
    
    class PythonQtError(Exception):
        """Error raise if no bindings could be selected"""
        pass
    
    
    if API in PYQT5_API:
        try:
            from PyQt5.Qt import PYQT_VERSION_STR as PYQT_VERSION  # analysis:ignore
            from PyQt5.Qt import QT_VERSION_STR as QT_VERSION  # analysis:ignore
            PYSIDE_VERSION = None
        except ImportError:
            API = os.environ['QT_API'] = 'pyqt'
    
    if API in PYQT4_API:
        try:
            import sip
            try:
                sip.setapi('QString', 2)
                sip.setapi('QVariant', 2)
                sip.setapi('QDate', 2)
                sip.setapi('QDateTime', 2)
                sip.setapi('QTextStream', 2)
                sip.setapi('QTime', 2)
                sip.setapi('QUrl', 2)
            except AttributeError:
                # PyQt < v4.6
                pass
            from PyQt4.Qt import PYQT_VERSION_STR as PYQT_VERSION  # analysis:ignore
            from PyQt4.Qt import QT_VERSION_STR as QT_VERSION  # analysis:ignore
            PYSIDE_VERSION = None
            PYQT5 = False
            PYQT4 = True
        except ImportError:
            API = os.environ['QT_API'] = 'pyside'
        else:
            is_old_pyqt = PYQT_VERSION.startswith(('4.4', '4.5', '4.6', '4.7'))
            is_pyqt46 = PYQT_VERSION.startswith('4.6')
    
    if API in PYSIDE_API:
        try:
            from PySide import __version__ as PYSIDE_VERSION  # analysis:ignore
            from PySide.QtCore import __version__ as QT_VERSION  # analysis:ignore
            PYQT_VERSION = None
            PYQT5 = False
            PYSIDE = True
        except ImportError:
            raise PythonQtError('No Qt bindings could be found')
    
    API_NAME = {'pyqt5': 'PyQt5', 'pyqt': 'PyQt4', 'pyqt4': 'PyQt4',
                'pyside': 'PySide'}[API]
    if PYQT4:
            import sip
            try:
                API_NAME += (" (API v{0})".format(sip.getapi('QString')))
            except AttributeError:
                pass
