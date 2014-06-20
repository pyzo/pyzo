# -*- coding: utf-8 -*-
# Copyright (C) 2014, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module to deal with command line arguments. 

In specific, this allows doing "iep some_file.py" and the file will be
opened in an existing IEP window (if available) or a new IEP process
is started to open the file. 

This module is used at the very early stages of starting IEP, and also
in main.py to apply any command line args for the current process, and
to closse down the server when IEP is closed.
"""

import sys

from yoton.clientserver import RequestServer, do_request
import iep

# Local address to host on. we use yoton's port hash to have an arbitrary port
ADDRESS = 'localhost:iepserver'


class Server(RequestServer):
    """ Server that listens on a port for commands.
    The commands can be send by executing the IEP executable with
    command line arguments.
    """
    
    def handle_request(self, request):
        """ This is where the requests enter.
        """
        # Get command
        request = request.strip()
        command, _, arg = request.partition(' ')
        
        # Handle command
        try:
            return handle_command(command, arg)
        except Exception as err:
            return 'Error handling request %r:\n%s' % (request, str(err))


def handle_command(command, arg):
    """ Function that handles all IEP commands.
    This gets called either from the server, or from the code that 
    processed command line args.
    """
    if command == 'stopserver':
        # For efficiently stopping the server
        if server:
            server.stop()
            return 'Stopped the server'

    elif command == 'echo':
        # For testing
        return 'echo %r' % arg
    
    elif command == 'open':
        # Open a file in the editor
        if not arg:
            return 'The open command requires a filename.'
        iep.callLater(iep.editors.loadFile, arg)
        return 'Opened file %r' % arg
    
    elif command == 'new':
        # Open a new (temp) file in the editor 
        iep.callLater(iep.editors.newFile)
        return 'Created new file'
    
    elif command == 'close':
        # Close IEP
        iep.callLater(iep.main.close)
        return 'Closing IEP'
    
    else:
        # Assume the user wanted to open a file
        fname = command + ' ' + arg
        iep.callLater(iep.editors.loadFile, fname)
        return 'Try opening file %r' % fname
    
    # We should always return. So if we get here, it is a bug.
    # Return something so that we can be aware.
    return 'echo ' + request


def handle_cmd_args():
    """ Handle command line arguments by sending them to the server.
    Returns a result string if any commands were processed, and None
    otherwise.
    """
    args = sys.argv[1:]
    if not args:
        return None
    else:
        # Always send to server, even if we are the ones that run the server
        request = ' '.join(args)
        try:
            return do_request(ADDRESS, request, 0.2).rstrip()
        except Exception as err:
            print('Could not process command line args:\n%s' % str(err))
            return None


def stop_our_server():
    """ Stop our server, for shutting down nicely.
    This is faster than calling server.stop(), because in the latter
    case the server will need to timeout (0.25 s) before it sees that
    it needs to stop.
    """
    if server is not None:
        do_request(ADDRESS, 'stopserver', 0.1)
        server.stop()  # make really sure it stops
        print('Stopped our command server.')


def is_our_server_running():
    """ Return True if our server is running. If it is, this process
    is the main IEP; the first IEP that was started. If the server is
    not running, this is probably not the first IEP, but there might
    also be problem with starting the server.
    """
    return server is not None


def is_iep_server_running():
    """ Test whether the IEP server is running *somewhere* (not
    necesarily in this process).
    """
    try:
        res = do_request(ADDRESS, 'echo', 0.2)
        return res.startswith('echo')
    except Exception:
        return False


# Shold we start the server?
_try_start_server = True
if sys.platform.startswith('win'):
    _try_start_server = not is_iep_server_running()


# Create server
server_err = None
server = None
#
try:
    if _try_start_server:
        server = Server(ADDRESS)
        server.start()
except OSError as err:
    server_err = err
    server = None
