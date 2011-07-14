# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" iepRemote1.py

Starting script for remote processes in iep.
This script connects to the IEP ide using the yoton interface
and imports remote2 to start the interpreter and introspection thread.

"""

import yoton
import sys, os, time
import __main__ # we will run code in the __main__.__dict__ namespace


## Make connection object and get channels

# Create a yoton context
ct = yoton.Context()
sys._yoton_context = ct

# Create std channels
sys.stdin = yoton.FileWrapper( yoton.SubChannel(ct, 'stdin') )
sys.stdout = yoton.FileWrapper( yoton.PubChannel(ct, 'stdout') )
sys.stderr = yoton.FileWrapper( yoton.PubChannel(ct, 'stderr') )

# Create all other channels
ct._ch_stdin_echo = yoton.PubChannel(ct, 'stdin-echo')
ct._ch_status = yoton.PubstateChannel(ct, 'status')
ct._ch_debug_status = yoton.PubstateChannel(ct, 'debug-status')
#
ct._ch_control = yoton.SubChannel(ct, 'control')
ct._ch_introspect = yoton.RepChannel(ct, 'introspect')

# Connect (port number given as command line argument)
port = int(sys.argv[1])
ct.connect('localhost:'+str(port), timeout=1.0)


## Set Excepthook

def iep_excepthook(type, value, tb):
    print("Uncaught exception in interpreter:")
    print(value)
    if not isinstance(value, (OverflowError, SyntaxError, ValueError)):
        while tb:
            print("-> line %i of %s." % (
                        tb.tb_frame.f_lineno, tb.tb_frame.f_code.co_filename) )
            tb = tb.tb_next
    import time
    time.sleep(0.3) # Give some time for the message to be send

# Uncomment to detect error in the interpreter itself
sys.excepthook = iep_excepthook


## Init interpreter and introspection tread

# Delay import, so we can detect syntax errors using the except hook
from iepRemote2 import IepInterpreter, IntroSpectionThread

# Create interpreter instance and give dict in which to run all code
__iep__ = IepInterpreter( __main__.__dict__, '<console>')

# Create introspection thread instance
# Make it a deamon thread, which implies that the program exits
# even if its running.
__iep__.ithread = IntroSpectionThread(ct, None, __iep__)
__iep__.ithread.daemon = True


## Clean up

# Store interpreter and channels on sys
sys._iepInterpreter = __iep__

# Delete local variables
del yoton, IntroSpectionThread, IepInterpreter, iep_excepthook
del ct, port
del os, sys, time

# Delete stuff we do not want 
del __file__

# Enter the interpreter
# __iep__.ithread.start()
__iep__.interact()
