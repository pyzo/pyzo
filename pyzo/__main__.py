#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the 2-Clause BSD License.
# The full license can be found in 'license.txt'.

""" Pyzo __main__ module

This module takes enables starting Pyzo via either "python3 -m pyzo" or
"python3 path/to/pyzo".

In the first case it simply imports pyzo. In the latter case, that import
will generally fail, in which case the parent directory is added to sys.path
and the import is tried again. Then "pyzo.start()" is called.

"""

import os
import sys


class SourceImporter:
    def __init__(self, dir):
        self.module_names = {"pyzo", "yoton"}
        for name in os.listdir(dir):
            self.module_names.add(name)

    def find_spec(self, fullname, path, target=None):
        if fullname.split(".")[0] in self.module_names:
            return sys.meta_path[-1].find_spec(fullname, path, target)
        else:
            return None


if getattr(sys, "frozen", False):
    # Allow importing from the source dir, and install spec finder to overload
    # PyInstaller's finder when appropriate.
    source_dir = os.path.join(sys._MEIPASS, "source")
    sys.path.insert(0, source_dir)
    sys.meta_path.insert(0, SourceImporter(source_dir))
    # Import
    import pyzo

else:
    # Try importing
    try:
        import pyzo
    except ImportError:
        # Very probably run as a script, either the package or the __main__
        # directly. Add parent directory to sys.path and try again.
        thisDir = os.path.abspath(os.path.dirname(__file__))
        sys.path.insert(0, os.path.split(thisDir)[0])
        try:
            import pyzo
        except ImportError:
            raise ImportError("Could not import Pyzo in either way.")


def main():
    pyzo.start()


if __name__ == "__main__":
    main()
