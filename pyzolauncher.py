#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" pyzolauncher.py script

This is a script used to startup Pyzo. Added for convenience, and also
for running a test on the source version.

Pyzo can be installed as a package, but it does not have to. You can
start Pyzo in a few different ways:
  * execute this script (pyzolauncher.py)
  * execute the pyzo directory (Python will seek out pyzo/__main__.py)
  * execute the pyzo package ("python -m pyzo")

Only in the latter must Pyzo be installed.

"""

import os
import sys
import subprocess


# faulthandler helps debugging hard crashes, it is included in py3.3
try:
    if sys.executable.lower().endswith("pythonw.exe"):
        raise ImportError("Dont use faulthandler in pythonw.exe")
    if sys.platform == "win32":
        raise ImportError("Prevent crash with QFileIconProvider")
        # see https://github.com/pyzo/pyzo/issues/875 for details
    import faulthandler

    faulthandler.enable()
except ImportError:
    pass


if "--test" in sys.argv:
    # Prepare log file
    logfilename = os.path.abspath(os.path.join(__file__, "..", "log.txt"))
    with open(logfilename, "wt") as f:
        f.write("")

    # Run Pyzo
    os.environ["PYZO_LOG"] = logfilename
    subprocess.run([sys.executable, "pyzo", "--test"])

else:
    import pyzo

    pyzo.start()
