import re
import os
import sys
import subprocess


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
