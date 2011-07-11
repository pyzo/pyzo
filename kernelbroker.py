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
            self.exe = '"' + self.exe + '"'
        
        # Set default startupScript?
        if self.startupScript == '$PYTHONSTARTUP':
            self.startupScript = os.environ.get('PYTHONSTARTUP','')
        
        # Set default PYTHONPATH
        ENV_PP = os.environ.get('PYTHONPATH','')
        self.PYTHONPATH.replace('$PYTHONPATH', '\n'+ENV_PP+'\n', 1)
        self.PYTHONPATH.replace('$PYTHONPATH', '')
        for i in range(3):
            self.PYTHONPATH.replace('\n\n', '\n')
        self.PYTHONPATH = self.PYTHONPATH.replace('\n', os.pathsep)
    
        
    def getCommand(self, port):
        """ getCommand(port)
        
        Given the port of the socket to connect at, creates the 
        command to execute in order to invoke the remote shell.
        
        """
        
        # Get start script
        startScript = os.path.join( iep.iepDir, 'iepRemote1.py')
        startScript = '"{}"'.format(startScript)
        
        # Build command
        command = self.exe + ' ' + startScript + ' ' + str(port)
        
        if sys.platform.startswith('win'):
            # as the author from Pype writes:
            #if we don't run via a command shell, then either sometimes we
            #don't get wx GUIs, or sometimes we can't kill the subprocesses.
            # And I also see problems with Tk.    
            # The double quotes are important for it to work when the 
            # executable is a path that contaiins spaces.
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
        self._timer = yoton.Timer(self, 0.2, oneshot=False)
        self._timer.bind(self._onTimerIteration)
        
        # Kernel process and connection (these are replaced on restarting)
        self._reset()
        
        # For terminating
        self._killAttempts = 0
        self._killTimer = 0
        
        # For restarting after terminating
        self._restart = False
        self._pending_scriptFile = None
    
    
    def __delete__(self):
        print('KernelBroker cleaned up') # todo: test
    
    
    def _reset(self, destroy=False):
        """ _reset(destroy=False)
        
        Reset state. if destroy, does a full clean up.
        
        """
        
        # Set process and kernel connection to None
        self._process = None
        self._kernelCon = None
        
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
            self._brokerChannel = None
            self._stdoutChannel = None
            self._heartbeatChannel = None
            #
            self._controlChannel = None
            self._controlChannel_pub = None
    
    
    
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
        self._kernelCon = self._context.bind('localhost:IEP', 
                                                max_tries=256, name='kernel')
        
        # Create channels. Stdout is for the C-level stdout/stderr streams.
        self._brokerChannel = yoton.PubChannel(self._context, 'broker-stream')
        self._stdoutChannel = yoton.PubChannel(self._context, 'c-stdout-stderr')
        self._heartbeatChannel = yoton.PubstateChannel(self._context,
                                            'heartbeat-status', yoton.OBJECT)
        
        # The IDE is in control
        self._controlChannel = yoton.SubChannel(self._context, 'control')
        self._controlChannel_pub = yoton.PubChannel(self._context, 'control')
        
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
                                    self._stdoutChannel, self._brokerChannel)
        
        # Start streamreader and timer
        self._streamReader.start()
        self._timer.start()
        
        # Reset some variables
        self._killAttempts = 0
        self._restart = False
        self._pending_scriptFile = None
        
        self._brokerChannel.send('Hi, this is your broker!')
    
    
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
            self._heartbeatChannel.send(False)
        else:
            self._heartbeatChannel.send(True)
    
    
    def _onTimerIteration(self):
        """ _onTimerIteration()
        
        Periodically called.
        
        """
        
        # Is there even a process?
        if self._process is None:
            print('kernel process stop')
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
        
        elif self._process.poll():
            # Test if process is dead
            self._onKernelDied()
            return
        
        
        # Process alive ...
        
        # Are we in the process of terminating?
        if self._killAttempts:
            self._terminating()
        
        # handle control messages
        for msg in self._controlChannel.recv_all():
            if msg == 'INT':
                # Kernel receives and acts
                # todo: On Linux we might interrupt from here. Is only advantegous
                # if this could interrupt extension code
                pass 
            elif msg == 'TERM':
                # Start termination procedure
                # Kernel will receive term and act (if it can). 
                # If it wont, we will act in a second or so.
                if self._killAttempts:
                    # The user gave kill command while the kill process
                    # is running. We could do an emidiate kill now,
                    # or we let the terminate process run its course.
                    pass 
                else:
                    self._killAttempts = 1
            elif msg.startswith('RESTART'):
                # Restart: terminates kernel and then start a new one
                self._restart = True
                scriptFile = None
                if ' ' in msg:
                    scriptFile = msg.split(' ',1)[1]
                self._pending_scriptFile = scriptFile
                # Terminate
                self._controlChannel_pub.send('TERM')
                self._killAttempts = 1
            else:
                pass # Message is not for us
    
    
    def _terminating(self):
        """ _terminating()
        
        The timer callback method when the process is being terminated. 
        Will try to terminate in increasingly more rude ways. 
        
        """
        
        if self._killAttempts == 1:
            # Waiting for process to stop by itself
            if time.time() - self._killTimer > 0.5:
                # Increase counter, next time will interrupt
                self._killAttempts += 1
        
        elif self._killAttempts < 6:
            # Send an interrupt every 100 ms
            if time.time() - self._killTimer > 0.1:
                self._controlChannel_pub.send('INT')
                self._killTimer = time.time()
                self._killAttempts += 1
        
        elif self._killAttempts < 10:
            # Ok, that's it, we're leaving!
            
            # Get pid and signal
            pid = self._kernelCon.pid2
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
                #os.system("TASKKILL /PID " + str(os.getpid()) + " /F")
            #
            self._killAttempts = 10
            self._killTimer = time.time()
    
    
    def _onKernelConnectionClose(self, c, why):
        """ _onKernelConnectionClose(c, why)
        
        Connection with kernel lost. Tell clients why.
        
        """
        # Notify
        self._brokerChannel.send('Connection to kernel lost: {}'.format(why))
    
    
    def _onKernelDied(self):
        """ _onKernelDied()
        
        Kernel process died. Clean up!
        
        """
        
        # Notify
        if self._kernelCon and not self._kernelCon.is_connected:
            self._brokerChannel.send('The process failed to start.')
        else:
            # Determine message
            if self._killAttempts < 0:
                msg = 'Process terminated twice?' # this should not happen
            if self._killAttempts == 0:
                msg = 'Process dropped.'
            elif self._killAttempts == 1:
                msg = 'Process terminated.'
            elif self._killAttempts < 10:
                msg = 'Process interrupted and terminated.'        
            else:
                msg = 'Process killed.'
            #
            self._brokerChannel.send(msg)
        
        # Signal that the connection is gone
        self._killAttempts = -1
    
        # Cleanup (get rid of kernel process references)
        self._reset()
        
        # Restart?
        if self._restart:
            self._restart = False
            self.startKernel()
    

class StreamReader(threading.Thread):
    """ StreamReader(process, channel)
    
    Reads stdout of process and send to a yoton channel.
    This needs to be done in a separate thread because reading from
    a PYPE blocks.
    
    """
    def __init__(self, process, stdoutChannel, brokerChannel):
        threading.Thread.__init__(self)
        
        self._process = process
        self._stdoutChannel = stdoutChannel
        self._brokerChannel = brokerChannel
        self.deamon = True
    
    def run(self):
        count = 4
        while count>0:
            # Read any stdout/stderr messages and route them via yoton.
            msg = self._process.stdout.read() # <-- Blocks here
            if not isinstance(msg, str):
                msg = msg.decode('utf-8', 'ignore')
            self._stdoutChannel.send(msg)
            # Process dead?
            if self._process.poll():
                count -= 1
            # Sleep
            time.sleep(0.1)
        print('exit streamreader')
    

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
        
        # Tell broker to hstart
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
        for kernel in self._kernels:
            
            # Try closing the process gently: by closing stdin
            kernel._controlChannel_pub.send('TERM')
            kernel._killAttempts = 1
            
            # Terminate
            while kernel._kernelCon.is_connected and kernel._killAttempts<10:
                time.sleep(0.02)
                kernel._terminating()
            
            # Clean up
            kernel._reset(True)
