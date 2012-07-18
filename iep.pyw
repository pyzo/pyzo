#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" iep.pyw

Startup Script.

"""

import os, sys
from pyzolib import paths

# Determine the directory of the application
iepDir = paths.application_dir()

# If frozen, we will actually load IEP from source, which is in a
# subdirectory. Set the iepDir accordingly and add to sys.path
if paths.is_frozen():
    iepDir = os.path.join(iepDir, 'source')
    sys.path.insert(0, iepDir)

# Start iep. Do an import that cx_freeze won't detect, so we can make
# a frozen app that uses plain source code.
exec("import iep")
iep.startIep()
