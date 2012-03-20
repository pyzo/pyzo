# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.


""" iepkernel/start.py

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

ctrl-command: to give simple commands to the interpreter (ala stdin)
ctrl-code (OBJECT): to let the interpreter execute blocks of code
ctrl-broker: to control the broker (restarting etc)

strm-out: the stdout of the interpreter
strm-err: the stderr of the interpreter
strm-raw: the C-level stdout and stderr of the interpreter (caputred by broker)
strm-echo: the interpreters echos commands here
strm-prompt: to send the prompts explicitly
strm-broker: for the broker to send messages to the ide
strm-action (OBJECT): for the kernel to push actions to the ide

stat-interpreter (OBJECT): status of the interpreter (ready, busy, more)
stat-debug (OBJECT): debug status
stat-heartbeat (OBJECT): whether the broker receives heartbeat signals from the kernel

reqp-introspect (OBJECT): To query information from the kernel (and for interruping)

"""

# This file is executed with the active directory one up from this file.

import os
import sys
import time
import yoton
import __main__ # we will run code in the __main__.__dict__ namespace

# todo: bug that on IEP startup the shell sometimes says 
# "The kernel process exited. (1)" We know this:
# - The kernel has successfully connected to the context, otherwise we
#   would have gotten an "process failed to start message"
# - There is an error code, so the kernel exited with an error
# - Arg, the excepthook did not work after the variables are cleaned up,
#   because it has a reference to sys! Added import statement, so that
#   from now on a trace should be printed.
   

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
ct._strm_action = yoton.PubChannel(ct, 'strm-action', yoton.OBJECT)

# Create status channels
ct._stat_startup = yoton.StateChannel(ct, 'stat-startup', yoton.OBJECT)
ct._stat_interpreter = yoton.StateChannel(ct, 'stat-interpreter', yoton.OBJECT)
ct._stat_debug = yoton.StateChannel(ct, 'stat-debug', yoton.OBJECT)

# Connect (port number given as command line argument)
# Important to do this *before* replacing the stdout etc, because if an
# error occurs here, it will be printed in the shell.
port = int(sys.argv[1])
ct.connect('localhost:'+str(port), timeout=1.0)

# Create file objects for stdin, stdout, stderr
sys.stdin = yoton.FileWrapper( ct._ctrl_command )
sys.stdout = yoton.FileWrapper( ct._strm_out )
sys.stderr = yoton.FileWrapper( ct._strm_err )


## Set Excepthook

def iep_excepthook(type, value, tb):
    import sys
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

# Uncomment to detect error in the interpreter itself.
# But better not use it by default. For instance errors in qt events
# are also catched by this function. I think that is because it would
# allow you to show such exceptions in an error dialog.
#sys.excepthook = iep_excepthook


## Init interpreter and introspector request channel

# Delay import, so we can detect syntax errors using the except hook
from iepkernel.interpreter import IepInterpreter
from iepkernel.introspection import IepIntrospector

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
