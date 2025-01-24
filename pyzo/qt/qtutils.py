from . import API

if API in ("PySide2", "PySide6"):
    if API == "PySide2":
        import shiboken2 as _shiboken
    else:
        import shiboken6 as _shiboken

    def isDeleted(qtObj):
        return not _shiboken.isValid(qtObj)

    def isOwnedByPython(qtObj):
        try:
            # for shiboken6 >= 6.8.0 and shiboken2 5.15.2.1
            return _shiboken.ownedByPython(qtObj)
        except AttributeError:
            pass
        return _shiboken.isOwnedByPython(qtObj)

elif API in ("PyQt5", "PyQt6"):
    if API == "PyQt5":
        import PyQt5.sip as _sip
    else:
        import PyQt6.sip as _sip

    def isDeleted(qtObj):
        return _sip.isdeleted(qtObj)

    def isOwnedByPython(qtObj):
        return _sip.ispyowned(qtObj)
