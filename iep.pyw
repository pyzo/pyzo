#!/usr/bin/env python3.1
#
#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
# 1. The 1st entry of system path; is set when a script is run
# 2. The executable name (when frozen)
# 3. the directory of __file__.  Note that it does not necesarrily represent
#    the location of this file, for instance when a linux link is made of this
#    file and put on the desktop.
# 4. The current working directory (as a last resort)
dir1 = os.path.abspath( sys.path[0] )
dir2 = os.path.abspath( os.path.dirname(sys.executable) )
dir3 = os.path.abspath( os.path.dirname(__file__) )
dir4 = os.path.abspath( os.getcwd() )

# Test all the dirs and make sure the iep path is on the sys.path
if isFrozen:
    # Get possible dirs where the source is. In most cases they're the same
    iepDir1 = pjoin(dir1, 'source')
    iepDir2 = pjoin(dir2, 'source')
    iepDir4 = pjoin(dir4, 'source')
    # Add the source directory to the sys.path
    if os.path.isdir( iepDir1 ):
        sys.path.insert(0, iepDir1)
    elif os.path.isdir( iepDir2 ):
        sys.path.insert(0, iepDir2)
    elif os.path.isdir( iepDir4 ):
        sys.path.insert(0, iepDir4)
    else:
        # Mmm, I'm in the dark
        raise RuntimeError("Could not detect iep source directory.")

else:
    # Get directory name where the source is
    iepDir1 = dir1
    iepDir3 = dir3
    iepDir4 = dir4
    # Add the source directory to the sys.path
    if os.path.isfile( pjoin(iepDir1, 'iep.py') ):
        pass # already on sys.path
    elif os.path.isfile( pjoin(iepDir3, 'iep.py') ):
        sys.path.insert(0, iepDir3)
    elif os.path.isfile( pjoin(iepDir4, 'iep.py') ):
        sys.path.insert(0, iepDir4)
    else:
        raise RuntimeError("Could not detect iep directory.")

# Start iep. Do an import that cx_freeze won't detect, so we can make
# a frozen app that uses plain source code.
exec("import iep")
iep.startIep()
