#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" IEP __main__ module

This module takes enables staring IEP via either "python3 -m iep" or 
"python3 path/to/iep".

In the first case it simply imports iep. In the latter case, that import
will generally fail, in which case the parent directory is added to sys.path
and the import is tried again. Then "iep.startIep()" is called.

"""

import os
import sys


# Imports that are maybe not used in IEP, but are/can be in the tools.
# Import them now, so they are available in the frozen app.
import shutil


try:
    import iep
except ImportError:
    # Very probably run as a script, either the package or the __main__
    # directly. Add parent directory to sys.path and try again.
    thisDir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, os.path.split(thisDir)[0])
    try:
        import iep
    except ImportError:
        raise ImportError('Could not import IEP in either way.')

# Start IEP
iep.startIep()
