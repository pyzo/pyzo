import re
import os
import sys
import subprocess

from pyzo.qt import QtCore


def parse_version_crudely(version_string):
    """extracts the leading number parts of a version string to a tuple
    e.g.: "123.45ew6.7x.dev8" --> (123, 45, 7)
    """
    return tuple(int(s) for s in re.findall(r"\.(\d+)", "." + version_string))


def open_directory_outside_pyzo(dirpath, filename=None):
    """open the directory in the operating system's file browser.

    If possible, also select a specific filename (only supported in MS Windows).
    """
    if not os.path.isdir(dirpath):
        return

    if filename is not None:
        filepath = os.path.join(dirpath, filename)
        if not os.path.isfile(filepath):
            filepath = None
    else:
        filepath = None

    if sys.platform.startswith("darwin"):
        subprocess.call(("open", dirpath))
    elif sys.platform.startswith("win"):
        if filepath is not None:
            subprocess.call('explorer.exe /select,"{}"'.format(filepath))
        else:
            subprocess.call('explorer.exe "{}"'.format(dirpath))
    elif sys.platform.startswith("linux"):
        subprocess.call(("xdg-open", dirpath))


class CalmedFunc:
    """Class for delayed execution of a function so that newer calls will replace the
    not yet executed older calls.

    If there is no newer call within a certain amount of time ("delay_ms"), the function
    will be executed with the arguments from the newest call.

    The first call after a longer break (after "delay_ms" or after initialization)
    will be executed immediately. The next execution will not happen before "delay_ms"
    since the previous execution, unless method "clear_pending" is called before.
    """

    def __init__(self, func, delay_ms):
        self._func = func
        self._t = QtCore.QTimer(singleShot=True)
        self._t.timeout.connect(self._timer_callback)
        self._quick_start = False
        self._wait_after_quick_start = False
        self.set_delay(delay_ms)

    def set_delay(self, delay_ms):
        self._delay_ms = delay_ms

    def clear_pending(self):
        self._t.stop()

    def __call__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._wait_after_quick_start = False
        if self._t.isActive():
            self._t.start(self._delay_ms)
        else:
            self._quick_start = True
            self._t.start(1)

    def _timer_callback(self):
        if self._wait_after_quick_start:
            self._wait_after_quick_start = False
            return

        self._func(*self._args, **self._kwargs)

        if self._quick_start:
            self._wait_after_quick_start = True
            self._t.start(self._delay_ms)
