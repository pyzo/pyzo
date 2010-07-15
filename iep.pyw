#!/usr/bin/env python3.1

import os, sys
print( os.getcwd())

# Determine the location of this file (also when frozen)
ex = os.path.split(sys.executable)[1]
ex = os.path.splitext(ex)[0]
if ex.lower().startswith('python'): # because can be python3 on Linux
    thisDir = os.path.abspath( os.path.dirname(__file__) ) # Not frozen
else:    
	thisDir = os.path.abspath( os.path.dirname(sys.executable) ) # Frozen

# Go there!
os.chdir(thisDir)

sys.path.insert(0, '')
print(thisDir, __file__, sys.executable)
# Now we should have an iep.py, or a source dir
if os.path.isdir('source'):
    os.chdir('source')
if os.path.isfile('iep.py'):
    exec("import iep")
else:
    exec("import iep")
    #raise RuntimeError("Could not locate iep.py!")

print(sys.path)

# Start
iep.startIep()

