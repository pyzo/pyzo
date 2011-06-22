# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" Module kernelBroker

This module implements the interface between IEP and the kernel.

"""

import os
import subprocess
import ssdf
import yoton
import iep # local IEP (can be on a different box than where the user is


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
        
        # ----- Dynamic parameters used when restarting -----
        
        # The full filename of the script to run. 
        # If given, the kernel should run in script-mode.
        # The kernel will check whether this file exists, and will
        # revert to interactive mode if it doesn't.
        self.scriptFile = ''
        
        # The path of the current project, the kernel will prepend this 
        # to the sys.path
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
    
    helps build the command to start the remote python process.
    
    """
    
    def __init__(self, info):
        KernelInfo.__init__(self, info)
        
        # Correct path when it contains spaces
        if self.exe.count(' '):
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
        
        Given the port of the channels interface, creates the 
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
        
        # Store project path
        if self.projectPath is not None:
            env['iep_projectPath'] = self.projectPath
        
        # Insert iep specific variables
        env['iep_gui'] = self.gui
        env['iep_startDir'] = self.startDir
        env['iep_scriptFile'] = self.scriptFile
        env['iep_startupScript'] = self.startupScript
        
        # Done
        return env


class KernelBroker:
    """ KernelBroker(info)
    
    This class functions as a broker between a kernel process and zero or
    more IDE's (clients).
    
    """
    
    def __init__(self, info, name=''):
        
        # Store info
        if not isinstance(info, KernelInfoPlus):
            info = KernelInfoPlus(info)
        self._info = info
        
        # Store name
        self._name = name
        
        # Create context for the connection to the kernel and IDE's
        self._context = yoton.Context()
    
    
    def startKernel(self):
        """ startKernel()
        
        Launch the kernel in a subprocess, and connect to it via the
        context and two Pypes.
        
        """
        
        # Get environment to use
        env = self._info.getEnviron()
        
        # Host connection for the kernel to connect
        # (tries several port numbers, staring from 'IEP')
        c = self._context.bind('localhost:IEPKERNEL', max_tries=32, name='kernel')
        
        # Create channels. Stdout is for the C-level stdout/stderr streams.
        self._brokerChannel = yoton.PubChannel(self._context, 'broker-stream')
        self._stdoutChannel = yoton.PubChannel(self._context, 'c-stdout')
        self._statusChannel = yoton.PubstateChannel(self._context, 'status')
        # todo: status -> kernel also has a status channel?
        
        # Get command to execute
        command = self._info.getCommand(c.port)
        
        # Start process
        self._process = subprocess.Popen(command, shell=True, 
                                env=env, cwd=startDir,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)  
        
        # Set timeout
        c.timeout = 0.5
        
        # Bind to events
        c.closed.bind(self._onKernelClose)
        c.timedout.bind(self._onKernelTimedOut)
    
    
    def host(self, address='localhost'):
        """ host()
        
        Host a connection for an IDE to connect to. Returns the port to which
        the ide can connect.
        
        """
        c = self._context.bind(address+':IEPBROKER', max_tries=32)
        return c.port
    
    
    def _onKernelClose(self, c, why):
        """ Connection with kernel lost. Tell clients why.
        """
        self._brokerChannel.send('Connection to kernel lost: {}'.format(why))
    
    def _onKernelTimedOut(self, c, timedout):
        """ The kernel timed out (i.e. did not send heartbeat messages for
        a while. It is probably running extension code.
        """
        if timedout:
            self._statusChannel.send('Ext')
        else:
            self._statusChannel.send('Normal')
    
    


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
    
    
    def create_kernel(self, info, name=None):
        """ create_kernel(info, name=None)
        
        Create a new kernel. Returns the port number to connect to the
        broker's context. 
        
        """
        
        # Set name if not given
        if not name:
            i = len(self._kernels) + 1
            name = 'kernel %i' % i
        
        # Create kernel
        kernel = KernelBroker(info, name)
        self._kernels.append(kernel)
        
        # Start kernel and host a connection for the ide
        kernel.startKernel()
        port = kernel.host()
        
        # Done
        return port
    
    
    def get_kernel_list(self):
        
        # Get info of each kernel as an ssdf struct
        infos = []
        for kernel in self._kernels:
            info = kernel._info
            info = ssdf.loads(info.tostring())
            info.name = kernel._name
            infos.append(info)
        
        # Done
        return infos
    