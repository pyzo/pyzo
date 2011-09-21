#!/usr/bin/env python3.1
# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" iep.pyw

Startup Script.

"""

import os, sys
pjoin = os.path.join

# Make sure __file__ exists
try:
    __file__
except NameError:
    __file__ = ''

# Determine whether we're in a frozen app
ex = os.path.split(sys.executable)[1]
ex = os.path.splitext(ex)[0]
if ex.lower().startswith('python'): # because can be python3 on Linux
    isFrozen = False
else:    
    isFrozen = True

# Get four possible directories where this file is located. 

# 1. The 1st entry of system path; is set when a script is run.
#    Make sure it is indeed a dir (Can also be the frozen executable)
#    On Linux, when a link is made to the frozen iep executable, dir1
#    will be correct, while dir2 will point to the location of the link.
dir1 = os.path.abspath( sys.path[0] )
if os.path.isfile(dir1):
    dir1 = os.path.split(dir1)[0]

# 2. The executable name (when frozen)
dir2 = os.path.abspath( os.path.dirname(sys.executable) )

# 3. the directory of __file__.  Note that it does not necesarrily represent
#    the location of this file, for instance when a linux link is made of this
#    file and put on the desktop.
dir3 = os.path.abspath( os.path.dirname(__file__) )

# 4. The current working directory (as a last resort)
dir4 = os.path.abspath( os.getcwd() )



# Test all the dirs and make sure the iep path is on the sys.path
if isFrozen:
    # Try possible dirs where the source is. In most cases they're the same.
    # When found, add the source directory to the sys.path.
    for iepDir in [dir1, dir2, dir4]:
        iepDir = pjoin(iepDir, 'source')
        if os.path.isdir( iepDir ):
            sys.path.insert(0, iepDir)
            break
    else:
        # Mmm, I'm in the dark
        raise RuntimeError("Could not detect iep source directory.")

else:
    # Try possible dirs where iep.py is. 
    # When found, add the source directory to the sys.path.
    for iepDir in [dir1, dir3, dir4]:
        if os.path.isfile( pjoin(iepDir, 'iep.py') ):
            if sys.path[0] != iepDir:
                sys.path.insert(0, iepDir)
            break
    else:
        # Mmm, I'm in the dark
        raise RuntimeError("Could not detect iep directory.")


# Start iep. Do an import that cx_freeze won't detect, so we can make
# a frozen app that uses plain source code.
exec("import iep")
iep.startIep()
