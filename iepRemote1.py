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
    
sys.excepthook = iep_excepthook


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
