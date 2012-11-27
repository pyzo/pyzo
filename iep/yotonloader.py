""" This is a bit awkward, but yoton is a package that is designed to
work from Python 2.4 to Python 3.x. As such, it does not have relative
imports and must be imported as an absolte package. That is what this
module does...
""" 

import os
import sys

# Prepare
prev_cwd = os.getcwd()
sys.path.insert(0, '')

# Import yoton 
os.chdir(os.path.dirname(__file__))
import yoton

# Reset
os.chdir(prev_cwd)
sys.path.pop(0)
