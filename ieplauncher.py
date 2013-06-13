#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" ieplauncher.py script

This is a script used to startup IEP. Added for convenience.

IEP can be installed as a package, but it does not have to. You can
start IEP in a few different ways:
  * execute this script (ieplauncher.py)
  * execute the iep directory (Python will seek out iep/__main__.py)
  * execute the iep package ("python -m iep")

Only in the latter must IEP be installed.

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


import iep
iep.startIep()
