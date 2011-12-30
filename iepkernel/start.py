# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" iepRemote1.py

Starting script for remote processes in iep.
This script connects to the IEP ide using the yoton interface
and imports remote2 to start the interpreter and introspection thread.

Channels
--------
There are four groups of channels. The ctrl channels are streams from 
the ide to the kernel and/or broker. The strm channels are streams to 
the ide. The stat channels are status channels to the ide. The reqp 
channels are req/rep channels. All channels are TEXT except for a
few OBJECT channels.

#TODO:
ctrl-in: the stdin to give commands (and also raw_input) to the interpreter  
ctrl-command: to give magic/debug etc. commands to the interpreter

ctrl-code (OBJECT): to let the interpreter execute blocks of code
ctrl-broker: to control the broker (restarting etc)

strm-out: the stdout of the interpreter
strm-err: the stderr of the interpreter
strm-raw: the C-level stdout and stderr of the interpreter (caputred by broker)
strm-echo: the interpreters echos commands here
strm-prompt: to send the prompts explicitly
strm-broker: for the broker to send messages to the ide

stat-interpreter (OBJECT): status of the interpreter (ready, busy, more)
stat-debug (OBJECT): debug status
stat-heartbeat (OBJECT): whether the broker receives heartbeat signals from the kernel

reqp-introspect (OBJECT): To query information from the kernel (and for interruping)

"""

# First go down one directory ...
import os
os.chdir('..')

import sys
import time
import yoton
import __main__ # we will run code in the __main__.__dict__ namespace


## Make connection object and get channels

# Create a yoton context
ct = yoton.Context()
sys._yoton_context = ct

# Create control channels
ct._ctrl_command = yoton.SubChannel(ct, 'ctrl-command')
ct._ctrl_code = yoton.SubChannel(ct, 'ctrl-code', yoton.OBJECT)

# Create stream channels
ct._strm_out = yoton.PubChannel(ct, 'strm-out')
ct._strm_err = yoton.PubChannel(ct, 'strm-err')
ct._strm_echo = yoton.PubChannel(ct, 'strm-echo')
ct._strm_prompt = yoton.PubChannel(ct, 'strm-prompt')

# Create status channels
ct._stat_interpreter = yoton.PubstateChannel(ct, 'stat-interpreter', yoton.OBJECT)
ct._stat_debug = yoton.PubstateChannel(ct, 'stat-debug', yoton.OBJECT)

# Create file objects for stdin, stdout, stderr
sys.stdin = yoton.FileWrapper( ct._ctrl_command )
sys.stdout = yoton.FileWrapper( ct._strm_out )
sys.stderr = yoton.FileWrapper( ct._strm_err )

# Connect (port number given as command line argument)
port = int(sys.argv[1])
ct.connect('localhost:'+str(port), timeout=1.0)


## Set Excepthook

def iep_excepthook(type, value, tb):
    def writeErr(err):
        sys.__stderr__.write(str(err)+'\n')
        sys.__stderr__.flush()
    writeErr("Uncaught exception in interpreter:")
    writeErr(value)
    if not isinstance(value, (OverflowError, SyntaxError, ValueError)):
        while tb:
            writeErr("-> line %i of %s." % (
                        tb.tb_frame.f_lineno, tb.tb_frame.f_code.co_filename) )
            tb = tb.tb_next
    import time
    time.sleep(0.3) # Give some time for the message to be send

# Uncomment to detect error in the interpreter itself
# sys.excepthook = iep_excepthook


## Init interpreter and introspector request channel

# Delay import, so we can detect syntax errors using the except hook
from iepkernel.interpreter import IepInterpreter, IepIntrospector

# Create interpreter instance and give dict in which to run all code
__iep__ = IepInterpreter( __main__.__dict__, '<console>')

# Create introspection req channel
__iep__.introspector = IepIntrospector(ct, 'reqp-introspect')


## Clean up

# Store interpreter and channels on sys
sys._iepInterpreter = __iep__
__iep__.os = os #For magic commands that need os access

# Delete local variables
del yoton, IepInterpreter, IepIntrospector, iep_excepthook
del ct, port
del os, sys, time

# Delete stuff we do not want 
del __file__

# Start introspector and enter the interpreter
__iep__.introspector.set_mode('thread')
__iep__.interact()
