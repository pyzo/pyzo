from . import PYQT6, PYQT5, PYSIDE2, PYSIDE6, PythonQtError


if PYSIDE2 or PYSIDE6:

    if PYSIDE2:
        import shiboken2 as _shiboken
    else:
        import shiboken6 as _shiboken

    def isDeleted(qtObj):
        return not _shiboken.isValid(qtObj)

    def isOwnedByPython(qtObj):
        return _shiboken.isOwnedByPython(qtObj)


elif PYQT5 or PYQT6:

    if PYQT5:
        import PyQt5.sip as _sip
    elif PYQT6:
        import PyQt6.sip as _sip

    def isDeleted(qtObj):
        return _sip.isdeleted(qtObj)

    def isOwnedByPython(qtObj):
        return _sip.ispyowned(qtObj)
