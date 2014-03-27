
import os
import ctypes
import sys
import string

# todo: also include available remote file systems
def getMounts():
    if sys.platform.startswith('win'):
        return getDrivesWin()
    elif sys.platform.startswith('darwin'):
        return '/'
    elif sys.platform.startswith('linux'):
        return ['/'] + [os.path.join('/media', e) for e in os.listdir('/media')]
    else:
        return '/'


def getDrivesWin():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter)
        bitmask >>= 1
    return [drive+':\\' for drive in drives]


def hasHiddenAttribute(path):
    """ Test (on Windows) whether a file should be hidden.
    """
    if not sys.platform.startswith('win'):
        return False
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
        assert attrs != -1
        return bool(attrs & 2)
    except (AttributeError, AssertionError):
        result = False
