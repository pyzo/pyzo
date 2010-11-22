# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" iepRemote1.py

Starting script for remote processes in iep.
This script connects to the IEP ide using the channles interface
and imports remote2 to start the interpreter and introspection thread.

"""

from channels import Channels
import sys, os, time
import __main__ # we will run code in the __main__.__dict__ namespace


## Make connection object and get channels

# Acquire port number (given as command line argument)
port = int(sys.argv[1])

# Create channels instance that can be both interrupted and killed
c = Channels(4, True, True)

# Create all channels
sys.stdin = c.get_receiving_channel(0)
sys.stdout = c.get_sending_channel(0)
sys.stderr = c.get_sending_channel(1)
sys._control = c.get_receiving_channel(1)
sys._status = c.get_sending_channel(2)

# Connect
#c.connect(port, timeOut=1, host='sas-p4-40') # Testing
c.connect(port, timeOut=1)


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
# sys.excepthook = iep_excepthook


## Init interpreter and introspection tread

# Delay import, so we can detect syntax errors using the except hook
from iepRemote2 import IepInterpreter, IntroSpectionThread

# Create interpreter instance and give dict in which to run all code
__iep__ = IepInterpreter( __main__.__dict__, '<console>')

# Create introspection thread instance
# Make it a deamon thread, which implies that the program exits
# even if its running.
__iep__.ithread = IntroSpectionThread(  
    c.get_receiving_channel(2), c.get_sending_channel(3), __iep__)
__iep__.ithread.daemon = True


## Clean up

# Store interpreter and channels on sys
sys._iepInterpreter = __iep__
sys._channels = c

# Delete local variables
del Channels, IntroSpectionThread, IepInterpreter, iep_excepthook
del c, port
del os, sys, time

# Delete stuff we do not want 
del __file__

# Enter the interpreter
__iep__.ithread.start()
__iep__.interact()
