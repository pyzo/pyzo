# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module kernelBroker

This module implements the interface between IEP and the kernel.

"""

import os, sys, time
import subprocess
import signal
import threading
import ctypes

import ssdf
import yoton
import iep # local IEP (can be on a different box than where the user is


# Important: the yoton event loop should run somehow!

class KernelInfo(ssdf.Struct):
    """ KernelInfo
    
    Describes all information for a kernel. This class can be used at 
    the IDE as well as the kernelbroker.
    
    """
    def __init__(self, info=None):
        
        # ----- Fixed parameters that define a shell -----
        
        # Set defaults
        self.exe = 'python'  # The executable
        self.gui = 'none'    # The GUI toolkit to embed the event loop of
        self.startDir = ''   # The initial directory (for interactive-mode)
        
        # The Python path. Paths should be separated by newlines.
        # '$PYTHONPATH' is replaced by environment variable by broker
        self.PYTHONPATH = ''
        
        # The Startup script (for interactive-mode).
        # - '$PYTHONSTARTUP' uses the code in that file. Broker replaces this.
        # - Empty string means run nothing, 
        # - Single line means file name, multiple lines means source code.
        self.startupScript = ''
        
        # The full filename of the script to run. 
        # If given, the kernel should run in script-mode.
        # The kernel will check whether this file exists, and will
        # revert to interactive mode if it doesn't.
        self.scriptFile = ''
        
        # The path of the current project, the kernel will prepend this 
        # to the sys.path.
        self.projectPath = ''
        
        
        # Load info from ssdf struct. Make sure they are all strings
        if info:
            # Get struct
            if ssdf.isstruct(info):
                s = info
            elif isinstance(info, str):
                s = ssdf.loads(info)
            else:
                raise ValueError('Kernel info should be a string or ssdf struct.')
            # Inject values
            for key in s:
                val = s[key]
                if not val:
                    val = ''
                self[key] = val
    
    
    def tostring(self):
        return ssdf.saves(self)


class KernelInfoPlus(KernelInfo):
    """ KernelInfoPlus
    
    Helps build the command to start the remote python process.
    
    """
    
    def __init__(self, info):
        KernelInfo.__init__(self, info)
        
        # Correct path when it contains spaces
        if self.exe.count(' ') and self.exe[0] != '"':
            self.exe = '"{}"'.format(self.exe)
        
        # Set default startupScript?
        if self.startupScript == '$PYTHONSTARTUP':
            self.startupScript = os.environ.get('PYTHONSTARTUP','')
        
        # Set default PYTHONPATH
        ENV_PP = os.environ.get('PYTHONPATH','')
        self.PYTHONPATH = self.PYTHONPATH.replace('$PYTHONPATH', '\n'+ENV_PP+'\n', 1)
        self.PYTHONPATH = self.PYTHONPATH.replace('$PYTHONPATH', '')
        for i in range(3):
            self.PYTHONPATH = self.PYTHONPATH.replace('\n\n', '\n')
        self.PYTHONPATH = self.PYTHONPATH.replace('\n', os.pathsep)
    
    
    def getCommand(self, port):
        """ getCommand(port)
        
        Given the port of the socket to connect at, creates the 
        command to execute in order to invoke the remote shell.
        
        """
        
        # Get start script
        startScript = os.path.join( iep.iepDir, 'iepkernel', 'start.py')
        startScript = '"{}"'.format(startScript)
        
        # Build command
        command = self.exe + ' ' + startScript + ' ' + str(port)
        
        if sys.platform.startswith('win'):
            # as the author from Pype writes:
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses.
            # And I also see problems with Tk.                
            command = 'cmd /c "{}"'.format(command)
        
        # Done
        return command
    
    
    def getEnviron(self):
        """  getEnviron()
        
        Gets the environment to give to the remote process,
        such that it can start up as the user wants to. 
        
        """ 
        
        # Prepare environment, remove references to tk libraries, 
        # since they're wrong when frozen. Python will insert the
        # correct ones if required.
        env = os.environ.copy()
        #
        env.pop('TK_LIBRARY','') 
        env.pop('TCL_LIBRARY','')
        env['PYTHONPATH'] = self.PYTHONPATH
        
        # Insert iep specific variables
        env['iep_gui'] = self.gui
        env['iep_startDir'] = self.startDir
        env['iep_projectPath'] = self.projectPath
        env['iep_scriptFile'] = self.scriptFile
        env['iep_startupScript'] = self.startupScript
        
        # Done
        return env


class KernelBroker:
    """ KernelBroker(info)
    
    This class functions as a broker between a kernel process and zero or
    more IDE's (clients).
    
    This class has a single context assosiated with it, that lives as long
    as this object. It is used to connect to a kernel process and to
    0 or more IDE's (clients). The kernel process can be "restarted", meaning
    that it is terminated and a new process started.
    
    If there is no kernel process AND no connections, this object is
    destroyed.
    
    
    """
    
    def __init__(self, manager, info, name=''):
        self._manager = manager
        
        # Store info
        if not isinstance(info, KernelInfoPlus):
            info = KernelInfoPlus(info)
        self._info = info
        
        # Store name
        self._name = name
        
        # Create context for the connection to the kernel and IDE's
        # This context is persistent (it stays as long as this KernelBroker
        # instance is alive).
        self._context = yoton.Context()
        
        # Create yoton-based timer
        self._timer = yoton.Timer(0.2, oneshot=False)
        self._timer.bind(self._onTimerIteration)
        
        # Kernel process and connection (these are replaced on restarting)
        self._reset()
        
        # For restarting after terminating
        self._restart = False
        self._pending_scriptFile = None
    
    
    def _create_channels(self):
        ct = self._context
        
        # Close any existing channels first
        for channelName in ['strm-broker', 'strm-raw', 'strm-prompt',
                            'ctrl-broker', 'stat-heartbeat', 'reqp-introspect']:
            attrName = '_' + channelName.lower().replace('-', '_')
            if hasattr(self, attrName):
                getattr(self, attrName).close()
        
        # Create stream channels. 
        # Stdout is for the C-level stdout/stderr streams.
        self._strm_broker = yoton.PubChannel(ct, 'strm-broker')
        self._strm_raw = yoton.PubChannel(ct, 'strm-raw')
        self._strm_prompt = yoton.PubChannel(ct, 'strm-prompt')
        
        # Create control channel so that the IDE can control restarting etc.
        self._ctrl_broker = yoton.SubChannel(ct, 'ctrl-broker')
        
        # Create status channel for heartbeat to detect running extension code
        self._stat_heartbeat = yoton.PubstateChannel(ct, 'stat-heartbeat', yoton.OBJECT)
        
        # Create introspect channel so we can interrupt and terminate
        self._reqp_introspect = yoton.ReqChannel(ct, 'reqp-introspect')
    
    
    def _reset(self, destroy=False):
        """ _reset(destroy=False)
        
        Reset state. if destroy, does a full clean up.
        
        """
        
        # Set process and kernel connection to None
        self._process = None
        self._kernelCon = None
        self._terminator = None
        self._streamReader = None
        
        if destroy == True:
            
            # Stop timer
            self._timer.unbind(self._onTimerIteration)
            self._timer = None
            
            # Clean up this kernelbroker instance
            L = self._manager._kernels
            while self in L:
                L.remove(self)
            
            # Remove references
            #
            self._context.destroy()
            self._context = None
            #
            self._strm_broker = None
            self._strm_raw = None
            self._stat_heartbeat = None
            self._strm_prompt = None
            #
            self._ctrl_broker = None
            self._reqp_introspect = None
    
    
    def startKernelIfConnected(self, timeout=10.0):
        """ startKernelIfConnected(timout=10.0)
        
        Start the kernel as soon as there is a connection.
        
        """
        self._process = time.time() + timeout
        self._timer.start()
    
    
    def startKernel(self):
        """ startKernel()
        
        Launch the kernel in a subprocess, and connect to it via the
        context and two Pypes.
        
        """
        
        # Create channels
        self._create_channels()
        
        # Set scriptFile in info
        info = KernelInfoPlus(self._info)
        if self._pending_scriptFile:
            info.scriptFile = self._pending_scriptFile
        else:
            info.scriptFile = ''
        
        # Get environment to use
        env = info.getEnviron()
        
        # Get directory to start process in
        cwd = iep.iepDir
        
        # Host connection for the kernel to connect
        # (tries several port numbers, staring from 'IEP')
        self._kernelCon = self._context.bind('localhost:IEP2', 
                                                max_tries=256, name='kernel')
       
        # Get command to execute
        command = info.getCommand(self._kernelCon.port)
        
        # Start process
        self._process = subprocess.Popen(   command, shell=True, 
                                            env=env, cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        # Set timeout
        self._kernelCon.timeout = 0.5
        
        # Bind to events
        self._kernelCon.closed.bind(self._onKernelConnectionClose)
        self._kernelCon.timedout.bind(self._onKernelTimedOut)
        
        # Create reader for stream
        self._streamReader = StreamReader(self._process,
                                    self._strm_raw, self._strm_broker)
        
        # Start streamreader and timer
        self._streamReader.start()
        self._timer.start()
        
        # Reset some variables
        self._restart = False
        self._pending_scriptFile = None
    
    
    def host(self, address='localhost'):
        """ host()
        
        Host a connection for an IDE to connect to. Returns the port to which
        the ide can connect.
        
        """
        c = self._context.bind(address+':IEP+256', max_tries=32)
        return c.port
    
    
    def _onKernelTimedOut(self, c, timedout):
        """ _onKernelTimedOut(c, timeout)
        
        The kernel timed out (i.e. did not send heartbeat messages for
        a while. It is probably running extension code.
        
        """
        if timedout:
            self._stat_heartbeat.send(False)
        else:
            self._stat_heartbeat.send(True)
    
    
    def _onTimerIteration(self):
        """ _onTimerIteration()
        
        Periodically called.
        
        """
        
        # Is there even a process?
        if self._process is None:
            self._context.close()
            #self._context.flush
            self._reset(True)
            return
        
        # Waiting to get started; waiting for client to connect
        if isinstance(self._process, float):
            if self._context.connection_count:
                self.startKernel()
            elif self._process > time.time():
                self._process = None
            return
        
        # Test if process is dead
        process_returncode = self._process.poll()
        if process_returncode is not None:
            self._onKernelDied(process_returncode)
            return
        
        
        # Process alive ...
        
        # Are we in the process of terminating?
        if self._terminator:
            self._terminator.next()
        
        # handle control messages
        for msg in self._ctrl_broker.recv_all():
            if msg == 'INT':
                # Kernel receives and acts
                self._reqp_introspect.interrupt()
            elif msg == 'TERM':
                # Start termination procedure
                # Kernel will receive term and act (if it can). 
                # If it wont, we will act in a second or so.
                if self._terminator:
                    # The user gave kill command while the kill process
                    # is running. We could do an immediate kill now,
                    # or we let the terminate process run its course.
                    pass 
                else:
                    self.terminate('by user')
            elif msg.startswith('RESTART'):
                # Restart: terminates kernel and then start a new one
                self._restart = True
                scriptFile = None
                if ' ' in msg:
                    scriptFile = msg.split(' ',1)[1]
                self._pending_scriptFile = scriptFile
                self.terminate('for restart')
            else:
                pass # Message is not for us
    
    
    def terminate(self, reason='by user', action='TERM', timeout=0.0):
        """ terminate(reason='by user', action='TERM', timeout=0.0)
        
        Terminate kernel. 
        
        """
        self._terminator = KernelTerminator(self, reason, action, timeout)
    
    
    def _onKernelConnectionClose(self, c, why):
        """ _onKernelConnectionClose(c, why)
        
        Connection with kernel lost. Tell clients why.
        
        """
        # The only reasonable way that the connection
        # can be lost without the kernel closing, is if the yoton context 
        # crashed or was stopped somehow. In both cases, we lost control,
        # and should put it down!
        if not self._terminator:
            self._terminator = self.terminate('connecton lost', 'KILL', 1.0)
    
    
    def _onKernelDied(self, returncode=0):
        """ _onKernelDied()
        
        Kernel process died. Clean up!
        
        """
        
        # If the kernel did not start yet, probably the command is invalid
        if self._kernelCon and self._kernelCon.is_waiting:
            msg = 'The process failed to start (invalid command?).'        
        elif not self._terminator:
            msg = 'Kernel process exited.'        
        else:
            msg = self._terminator.getMessage('Kernel process')
        
        # Notify
        returncodeMsg = '\n%s (%s)\n\n' % (msg, str(returncode))
        self._strm_broker.send(returncodeMsg)
        
        # Empty prompt
        self._strm_prompt.send('\b') 
        self._context.flush()
        
        # Cleanup (get rid of kernel process references)
        self._reset()
            
        # Restart?
        if self._restart:
            self._restart = False
            self.startKernel()


class KernelTerminator:
    """ KernelTerminator(broker, reason='user terminated', action='TERM', timeout=0.0)
    
    Simple class to help terminating the kernel. It has a next() method 
    that should be periodically called. It keeps track whether the timeout
    has passed and will undertake increaslingly ruder actions to terminate
    the kernel.
    
    """
    def __init__(self, broker, reason='by user', action='TERM', timeout=0.0):
        
        # Init/store
        self._broker = broker
        self._reason = reason
        self._next_action = ''
        
        # Go
        self._do(action, timeout)    
    
    
    def _do(self, action, timeout):
        self._prev_action = self._next_action
        self._next_action = action
        self._timeout = time.time() + timeout
        if not timeout:
            self.next() 
    
    
    def next(self):
        
        # Get action
        action = self._next_action
        
        if time.time() < self._timeout:
            # Time did not pass yet
            pass
        
        elif action == 'TERM':
            self._broker._reqp_introspect.terminate()
            self._do('INT', 0.5)
        
        elif action == 'INT':
            # Count
            if not hasattr(self, '_count'):
                self._count = 0
            self._count +=1
            # Handle
            if self._count < 5:
                self._broker._reqp_introspect.interrupt()
                self._do('INT', 0.1)
            else:
                self._do('KILL', 0)
        
        elif action == 'KILL':
            # Get pid and signal
            pid = self._broker._kernelCon.pid2
            sigkill = signal.SIGTERM
            if hasattr(signal,'SIGKILL'):
                sigkill = signal.SIGKILL
            # Kill
            if hasattr(os,'kill'):
                os.kill(pid, sigkill)
            elif sys.platform.startswith('win'):
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1, 0, pid)
                kernel32.TerminateProcess(handle, 0)
                #os.system("TASKKILL /PID " + str(pid) + " /F")
            # Set what we did
            self._do('NOTHING', 9999999999999999)
    
    
    def getMessage(self, what):
        # Get last performed action 
        action = self._prev_action
        
        # Get nice string of that
        D = {   '':     'exited',
                'TERM': 'terminated', 
                'INT':  'terminated (after interrupting)',
                'KILL': 'killed'}
        actionMsg = D.get(self._prev_action, 'stopped for unknown reason')
        
        # Compile stop-string
        return '{} {} {}.'.format( what, actionMsg, self._reason)



class StreamReader(threading.Thread):
    """ StreamReader(process, channel)
    
    Reads stdout of process and send to a yoton channel.
    This needs to be done in a separate thread because reading from
    a PYPE blocks.
    
    """
    def __init__(self, process, strm_raw, strm_broker):
        threading.Thread.__init__(self)
        
        self._process = process
        self._strm_raw = strm_raw
        self._strm_broker = strm_broker
        self.deamon = True
    
    def run(self):
        while True:
            # Read any stdout/stderr messages and route them via yoton.
            msg = self._process.stdout.readline() # <-- Blocks here
            if not isinstance(msg, str):
                msg = msg.decode('utf-8', 'ignore')
            self._strm_raw.send(msg)
            # Process dead?
            if not msg:# or self._process.poll() is not None:
                break
            # Sleep
            time.sleep(0.1)
        #self._strm_broker.send('streamreader exit\n')
    

class Kernelmanager:
    """ Kernelmanager
    
    This class manages a set of kernels. These kernels run on the 
    same machine as this broker. IDE's can ask which kernels are available
    and can connect to them via this broker.
    
    The IEP process runs an instance of this class that connects at 
    localhost. At a later stage, we may make it possible to create 
    a kernel-server at a remote machine.
    
    """
    
    def __init__(self, public=False):
        
        # Set whether other machines in this network may connect to our kernels
        self._public = public
        
        # Init list of kernels
        self._kernels = []
    
    
    def createKernel(self, info, name=None):
        """ create_kernel(info, name=None)
        
        Create a new kernel. Returns the port number to connect to the
        broker's context. 
        
        """
        
        # Set name if not given
        if not name:
            i = len(self._kernels) + 1
            name = 'kernel %i' % i
        
        # Create kernel
        kernel = KernelBroker(self, info, name)
        self._kernels.append(kernel)
        
        # Host a connection for the ide
        port = kernel.host()
        
        # Tell broker to start as soon as the IDE connects with the broker
        kernel.startKernelIfConnected()
        
        # Done
        return port
    
    
    def getKernelList(self):
        
        # Get info of each kernel as an ssdf struct
        infos = []
        for kernel in self._kernels:
            info = kernel._info
            info = ssdf.loads(info.tostring())
            info.name = kernel._name
            infos.append(info)
        
        # Done
        return infos
    
    
    def terminateAll(self):
        """ terminateAll()
        
        Terminates all kernels. Required when shutting down IEP. 
        When this function returns, all kernels will be terminated.
        
        """
        for kernel in [kernel for kernel in self._kernels]:
            
            # Try closing the process gently: by closing stdin
            terminator = KernelTerminator(kernel, 'for closing down')
            
            # Terminate
            while (kernel._kernelCon.is_connected and 
                    kernel._process and (kernel._process.poll() is None) ):
                time.sleep(0.02)
                terminator.next()
            
            # Clean up
            kernel._reset(True)
