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

from iepRemote2 import IepInterpreter, IntroSpectionThread
from channels import Channels
import sys, os
import __main__ # we will run code in the __main__.__dict__ namespace


## Make connection object and get channels

# Acquire port number (given as command line argument)
port = int(sys.argv[1])

# Create channels instance that can be both interrupted and killed
c = Channels(4, True, True)

# Create all channels
sys.stdin = c.getReceivingChannel(0)
sys.stdout = c.getSendingChannel(0)
sys.stderr = c.getSendingChannel(1)
sys._control = c.getReceivingChannel(1)
sys._status = c.getSendingChannel(2)

# Connect
c.connect(port, timeOut=1)


## Init interpreter and introspection tread

# Create interpreter instance and give dict in which to run all code
__iep__ = IepInterpreter( __main__.__dict__, '<console>')
__iep__.channels = c

# Create introspection thread instance
# Make it a deamon thread, which implies that the program exits
# even if its running.
__iep__.ithread = IntroSpectionThread(  
    c.getReceivingChannel(2), c.getSendingChannel(3), __iep__)
__iep__.ithread.daemon = True


## Clean up

# Delete local variables
del Channels, IntroSpectionThread, IepInterpreter
del c, port
del os, sys

# Delete stuff we do not want 
del __file__
# Enter the interpreter
__iep__.ithread.start()
__iep__.interact()
