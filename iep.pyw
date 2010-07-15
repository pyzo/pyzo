#!/usr/bin/env python3.1

import os, sys, time
import threading, thread, Queue

from PyQt4 import QtCore, QtGui, Qsci

# Determine if frozen
ex = os.path.split(sys.executable)[1]
ex = os.path.splitext(ex)[0]
if ex.lower().startswith('python'): # because can be python3 on Linux
    isFrozen = False
else:
    isFrozen = True

# Go to the iep dir
if isFrozen:
    iepDir =  os.path.abspath( os.path.dirname(sys.executable) )

if os.path.isfile( os.path.join(os.path.getcwd '')

try:
    exec("import iep")
except Exception:
    # Frozen
    

iep.startIep()
