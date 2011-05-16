import os
import subprocess
import ssdf
import yoton
import iep # local IEP


class KernelInfo:
    """ KernelInfo
    
    Describes all information for a kernel. This class can be used at 
    the IDE as well.
    
    """
    def __init__(self):
        
        # ----- Fixed parameters that define a shell -----
        
        # Set defaults
        self.exe = 'python'  # The executable
        self.gui = 'none'    # The GUI toolkit to embed the event loop of
        self.startDir = ''   # The initial directory (when run not as script)
        
        # The Python path. None means use default from environment.
        # Paths should be separated by newlines.
        self.PYTHONPATH = None
        
        # The Startup script (when not run in script-mode). None means use 
        # PYTHONSTARTUP from environment. Empty string means run nothing, 
        # single line means file name, multiple line means source code.
        self.startupScript = None
        
        # ----- Dynamic parameters used when restarting -----
        
        # The full filename of the script to run. 
        # If given, the kernel should run in script-mode.
        self.scriptFile = None
        
        # The path of the current project, the kernel will prepend this 
        # to the sys.path
        self.projectPath = None
    
    
    def tostring(self):
        return ssdf.saves(self.__dict__)


class KernelInfoPlus(KernelInfo):
    """ KernelInfoPlus
    
    helps build the command to start the remote python process.
    
    """
    
    def __init__(self, ss):
        KernelInfo.__init__(self)
        
        # Load info from ssdf struct
        s = ssdf.loads(ss)
        for key in s:
            self.__dict__[key] = s[key]
        
        # Correct path when it contains spaces
        if self.exe.count(' '):
            self.exe = '"' + self.exe + '"'
        
        # Set default startupScript?
        if self.startupScript is None:
            self.startupScript = os.environ.get('PYTHONSTARTUP','')
        
        # Set default PYTHONPATH
        if self.PYTHONPATH is None:
            self.PYTHONPATH = os.environ.get('PYTHONPATH','')
        else:
            self.PYTHONPATH = self.PYTHONPATH.replace('\n',os.pathsep)
    
    
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
        
        # Depending on mode (interactive or script)
        if self.scriptFile:
            env['iep_scriptFile'] = self.scriptFile
        else:
            env['iep_scriptFile'] = ''
            env['iep_startupScript'] = self.startupScript
        
        # Done
        return env


class KernelBroker:
    """ KernelBroker
    
    This class functions as a broker between a kernel process and zero or
    more IDE's (clients).
    
    """
    
    def __init__(self, info):
        
        # Create context for the connection to the kernel and IDE's
        self._context = yoton.Context()
        
        # Store info
        if not isinstance(info, KernelInfoPlus):
            info = KernelInfoPlus(info)
        self._info = info
    
    
    def startKernel(self):
        """ startKernel()
        
        Launch the kernel in a subprocess, and connect to it via the
        context and two Pypes.
        
        """
        
        # Get environment to use
        env = self._info.getEnviron()
        
        # Host connection for the kernel to connect
        # (tries several port numbers, staring from 'IEP')
        c = self._context.bind('localhost:IEP', max_tries=32, name='kernel')
        
        # Create channels. Stdout and stderr are the original (C-level) streams.
        self._brokerChannel = yoton.PubChannel(self._context, 'stdBroker')
        self._stdoutChannel = yoton.PubChannel(self._context, '_stdout')
        self._stderrChannel = yoton.PubChannel(self._context, '_stderr')
        self._statusChannel = yoton.PubstateChannel(self._context, 'status')
        # todo: status -> kernel also has a status channel?
        
        # Get command to execute
        command = self._info.getCommand(c.port)
        
        # Start process (open PYPES to detect errors when starting up)
        self._process = subprocess.Popen(command, shell=True, 
                                env=env, cwd=startDir,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)  
        
        # Set timeout
        c.timeout = 0.5
        
        # Bind to events
        c.closed.bind(self._onKernelClose)
        c.timedout.bind(self._onKernelTimedOut)
    
    
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
    localhost. At a later stage, we may provide binaries to create 
    a kernel-server at a remote machine.
    
    """
    
    def __init__(self, public=0):
        
        self._public = public
    
    
    def create_kernel(self):
        
    
    def get_kernel_list(self):
        
    
    def 
    