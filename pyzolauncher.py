#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2016, the Pyzo development team
#
# Pyzo is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" pyzolauncher.py script

This is a script used to startup Pyzo. Added for convenience.

Pyzo can be installed as a package, but it does not have to. You can
start Pyzo in a few different ways:
  * execute this script (pyzolauncher.py)
  * execute the pyzo directory (Python will seek out pyzo/__main__.py)
  * execute the pyzo package ("python -m pyzo")

Only in the latter must Pyzo be installed.

"""

import sys

# faulthandler helps debugging hard crashes, it is included in py3.3
try:
    if sys.executable.lower().endswith('pythonw.exe'):
        raise ImportError('Dont use faulthandler in pythonw.exe')
    import faulthandler
    faulthandler.enable()
except ImportError:
    pass


import pyzo
pyzo.start()
