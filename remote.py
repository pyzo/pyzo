from remote2 import IepInterpreter, IntroSpectionThread
from channels import Channels
import sys, os
import __main__ # we will run code in the __main__.__dict__ namespace

## Process input args

# Acquire information to run
port = int(sys.argv[1])
gui = sys.argv[2]
runsus = int(sys.argv[3])
startdir = sys.argv[4]

# Set no input arguments (do keep the first)
sys.argv[1:] = []


## Make connection object and get channels

# Create channels instance
c = Channels(4)

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
__iep__ = IepInterpreter( __main__.__dict__, 
                            '<console>', gui, runsus, startdir)
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
del c, port, gui, runsus, startdir 
del os, sys

# Delete stuff we do not want 
del __file__
# Enter the interpreter
__iep__.ithread.start()
__iep__.interact()
