import os, sys, time
import code
import traceback
import types

import threading
import inspect


# Init last traceback
sys.last_type = None
sys.last_value = None
sys.last_traceback = None

class IepInterpreter(code.InteractiveConsole):
    """Closely emulate the interactive Python console.
    Almost the same as code.InteractiveConsole, but interact()
    is overriden to change the following:
    - prompts are printed in the err stream, like the default interpreter does
    - uses an asynchronous read using the channels interface.    
    - support for hijacking GUI toolkits
    - can run large pieces of code.
    """
    
    def __init__(self, locals):
        code.InteractiveConsole.__init__(self, locals=locals)
        
        # Store ref of locals that is our main
        self._main_locals = locals
        self._dbFrames = []
        self._dbFrameIndex = 0
        self._dbFrameName = ''
    
    
    def write(self, text):
        """ Write errors and prompts. """
        sys.stderr.write( text )
    
    
    def writeStatus(self):
        """ Write the status (Ready, or Busy, or Debug info). """
        if self._dbFrames:
            # Debug info
            stack = [f.f_code.co_name+': '+str(f.f_lineno)+' in '+f.f_code.co_filename
                for f in self._dbFrames]
            stack.append(str(self._dbFrameIndex))
            sys._status.write('Debug ' + ','.join(stack))
        else:
            sys._status.write('Ready')
    
    
    def interact(self, banner=None):    
        """ Interact! (start the mainloop)
        """
        
        ## INIT
        
        # create list to store codeBlocks that we execute
        self._codeList = []
        
        # Define prompts
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        
        
        ## WELCOME
        
        # Create banner
        cprt =  'Type "help", "copyright", "credits" or "license"'\
                ' for more information.'
        moreBanner = 'This is the IepInterpreter. Type "?" for'\
                     ' a list of *magic* commands.'
        # moreBanner = self.__class__.__name__
        if banner is None:
            sys.stdout.write("Python %s on %s\n%s\n%s\n" %
                       (sys.version, sys.platform, cprt,
                        moreBanner))
        else:
            sys.stdout.write("%s\n" % str(banner))
        
        
        ## PREPARE
        
        # Remove "THIS" directory from the PYTHONPATH
        # to prevent unwanted imports
        thisPath = os.getcwd()
        if thisPath in sys.path:
            sys.path.remove(thisPath)
        
        # Go to start dir
        os.chdir(os.path.expanduser('~/')) # home dir
        # todo: let the user decide where to start
        # os.chdir(sys.exec_prefix) On windows, python starts here
        
        # Execute startup script
        filename = os.environ.get('PYTHONSTARTUP')
        if filename and os.path.isfile(filename):
            execfile(filename, {}, self.locals)
        

#         # hijack tk and wx
#         self.tkapp = tkapp = None#hijack_tk()
#         self.wxapp = wxapp = hijack_wx()
#         self.flapp = flapp = hijack_fl()
#         self.qtapp = qtapp = hijack_qt4()
        
        
        ## MAIN LOOP
        
        guitime = time.clock()        
        more = 0
        self.newPrompt = True
        while True:
            try:
                
                # Set status and prompt?
                # Prompt is allowed to be an object with __str__ method
                if self.newPrompt:
                    self.newPrompt = False
                    # Write prompt
                    preamble = ''
                    if self._dbFrames:
                        preamble = '('+self._dbFrameName+')'
                    if more:
                        self.write(preamble+str(sys.ps2))
                    else:
                        self.write(preamble+str(sys.ps1))
                    # Set status
                    self.writeStatus()
                
                # Wait for a bit at each round
                time.sleep(0.010) # 10 ms
                
                # Are we still connected?
                if sys.stdin.closed:
                    self.write("\n")
                    break
                
                # Read control stream and process
                control = sys._control.readOne(False)
                if control:
                    self.parseControl(control)
                
                # Read a packet and process
                line = sys.stdin.readOne(False)
                if line:
                    # Set busy
                    sys._status.write('Busy')
                    self.newPrompt = True
                    
                    if line.startswith('\n') and len(line)>1:
                        # Execute larger piece of code
                        self.execute_text(line)
                        # Reset more stuff
                        self.resetbuffer()
                        more = False
                    else:
                        # Execute line
                        line = line.rstrip("\n") # this is what push wants
                        more = self.push(line)
                
                # Keep GUI toolkits up to date
                self.updateGUIs()
            
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0
                self.write(sys.ps1)
                # todo: is this still an issue?
#             except TypeError, err:
#                 # For some reason, when wx is hijacked, keyboard interrupts
#                 # result in a TypeError on "time.sleep(0.010)".
#                 # I tried to find the source, but did not find it. If anyone
#                 # has an idea, please mail me!
#                 if err.message == "'int' object is not callable":
#                     self.write("\nKeyboardInterrupt\n")
#                     self.resetbuffer()
#                     more = 0
#                     self.write(sys.ps1)
#                 else:
#                     raise err
    
    def updateGUIs(self):
        pass
        #                 # update tk and wx 50 times per second
    #                 if time.time() - guitime > 0.019: # a bit sooner for sync
    #                     if tkapp:
    #                         tkapp.update()
    #                     if wxapp:
    #                         wxapp.ProcessPendingEvents()
    #                         wxapp.ProcessIdle() # otherwise frames do not close
    #                     if flapp:
    #                         flapp.wait(0)
    #                     if qtapp:
    #                         qtapp.processEvents()
    #                     guitime = time.time()
    
    
    def parseControl(self, control):
        
        if control == 'STATUS':
            self.writeStatus()
        
        elif control == 'DEBUG START':
            # Collect frames from the traceback
            tb = sys.last_traceback
            frames = []
            while tb:
                frames.append(tb.tb_frame)
                tb = tb.tb_next
            # Enter debug mode if there was an error
            if frames:
                self._dbFrames = frames
                self._dbFrameIndex = len(self._dbFrames)-1
                frame = self._dbFrames[self._dbFrameIndex]
                self._dbFrameName = frame.f_code.co_name
                self.locals = frame.f_locals
                # Notify IEP
                self.writeStatus()
            else:
                self.write("No debug information available.\n")
        
        elif control.startswith('DEBUG') and not self._dbFrames:
            # Ignoire other debug commands when not debugging
            return
        
        elif control.startswith('DEBUG INDEX'):
            # Set frame index
            self._dbFrameIndex = int(control.rsplit(' ',1)[-1])
            if self._dbFrameIndex < 0:
                self._dbFrameIndex = 0
            elif self._dbFrameIndex >= len(self._dbFrames):
                self._dbFrameIndex = len(self._dbFrames) - 1
            # Set name and locals
            frame = self._dbFrames[self._dbFrameIndex]
            self._dbFrameName = frame.f_code.co_name
            self.locals = frame.f_locals
        
        elif control == 'DEBUG DOWN':
            # Decrease frame index
            self._dbFrameIndex -= 1
            if self._dbFrameIndex < 0:
                self._dbFrameIndex = 0
            # Set name and locals
            frame = self._dbFrames[self._dbFrameIndex]
            self._dbFrameName = frame.f_code.co_name
            self.locals = frame.f_locals
        
        elif control == 'DEBUG UP':
            # Increase frame index
            self._dbFrameIndex += 1
            if self._dbFrameIndex >= len(self._dbFrames):
                self._dbFrameIndex = len(self._dbFrames) - 1
            # Set name and locals
            frame = self._dbFrames[self._dbFrameIndex]
            self._dbFrameName = frame.f_code.co_name
            self.locals = frame.f_locals
        
        elif control == 'DEBUG END':
            self.locals = self._main_locals
            self._dbFrames = []
    
    
    def execute_text(self, text):
        """ To execute larger pieces of code. """
        
        # Split information
        # (The last line contains filename + lineOffset about the code)
        tmp = text.rsplit('\n', 2)
        source = tmp[0]
        fname = tmp[1]
        lineno = int(tmp[2]) -1 # because we do not remove the first newline
        
        # Put the index of the codeBlock in the filename
        fname = "%s [%i]" % (fname, len(self._codeList))
        # Store the information
        self._codeList.append( (source, fname, lineno) )
        
        # Try compiling the source
        code = None
        try:            
            code = self.compile(source, fname, "exec")
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(fname)
        
        # Execute the code
        if code:            
            try:
                exec code in self.locals
            except SystemExit:
                raise
            except:
                #self.write('oops!')
                self.showtraceback()
    
    
    def showsyntaxerror(self, filename=None):
        """Display the syntax error that just occurred.
        This doesn't display a stack trace because there isn't one.        
        If a filename is given, it is stuffed in the exception instead
        of what was there before (because Python's parser always uses
        "<string>" when reading from a string).
        
        IEP version: support to display the right line number,
        see doc of showtraceback for details.        
        """
        
        type, value, sys.last_traceback = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                # unpack information
                msg, (dummy_filename, lineno, offset, line) = value
                # correct line-number
                codenr = filename.rsplit("[",1)[-1].split("]",1)[0]
                try:
                    codeblock = self._codeList[int(codenr)]
                    lineno = lineno + int(codeblock[2])
                except (ValueError, IndexError):
                    pass
            except:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        list = traceback.format_exception_only(type, value)
        map(self.write, list)
        
        
    def showtraceback(self):
        """Display the exception that just occurred.
        We remove the first stack item because it is our own code.
        The output is written by self.write(), below.
        
        In the IEP version, before executing a block of code,
        the filename is modified by appending " [x]". Where x is
        the index in a list that we keep, of tuples 
        (sourcecode, filename, lineno). 
        
        Here, showing the traceback, we check if we see such [x], 
        and if so, we extract the line of code where it went wrong,
        and correct the lineno, so it will point at the right line
        in the editor if part of a file was executed. When the file
        was modified since the part in question was executed, the
        fileno might deviate, but the line of code shown shall 
        always be correct...
        """
        # Traceback info:
        # tb_next -> go down the trace
        # tb_frame -> get the stack frame
        # tb_lineno -> where it went wrong
        #
        # Frame info:
        # f_back -> go up (towards caller)
        # f_code -> code object
        # f_locals -> we can execute code here when PM debugging
        # f_globals
        # f_trace -> (can be None) function for debugging? (
        #
        # The traceback module is used to obtain prints from the
        # traceback.
        
        try:
            # Get exception information and remove first, since that's us
            type, value, tb = sys.exc_info()
            tb = tb.tb_next
            
            # Store for debugging, but only store if not in debug mode
            if not self._dbFrames:
                sys.last_type = type
                sys.last_value = value
                sys.last_traceback = tb
            
            # Get frame
            frame = tb.tb_frame
            
            # Get traceback to correct all the line numbers
            # tblist = list  of (filename, line-number, function-name, text)
            tblist = traceback.extract_tb(tb)
            
            # Walk through the list
            for i in range(len(tblist)):
                tb = tblist[i]
                # get codeblock number: piece between []                
                codenr = tb[0].rsplit("[",1)[-1].split("]",1)[0]
                try:
                    source, fname, lineno = self._codeList[int(codenr)]
                except (ValueError, IndexError):
                    continue
                # Add info to traceback and correct line number             
                example = source.splitlines()
                try:
                    example = example[ tb[1]-1 ]
                except IndexError:
                    example = ""
                lineno = tb[1] + lineno
                tblist[i] = ( tb[0], lineno, tb[2], example)
            
            # Format list
            list = traceback.format_list(tblist)
            if list:
                list.insert(0, "Traceback (most recent call last):\n")
            list[len(list):] = traceback.format_exception_only(type, value)
        finally:
            tblist = tb = None
        
        # Write traceback
        map(self.write, list)



class IntroSpectionThread(threading.Thread):
    """ IntroSpectionThread
    Communicates with the IEP GUI, even if the main thread is busy.
    """
    
    def __init__(self, requestChannel, responseChannel, interpreter):
        threading.Thread.__init__(self)
        
        # store the two channel objects
        self.request = requestChannel
        self.response = responseChannel
        self.interpreter = interpreter
    
    
    def run(self):
        """ This is the "mainloop" of our introspection thread.
        """ 
        
        while True:
            
            # sleep for a bit
            time.sleep(0.01)
            
            # read code (wait here)
            line = self.request.readOne(True)
            if not line or self.request.closed:
                break # from thread
            
            # get request and arg
            tmp = line.split(" ",1)
            req = tmp[0]
            arg = tmp[1]
            
            # process request
            
            if req == "EVAL":
                self.enq_eval( arg )
                
            elif req == "KEYS":
                self.enq_keys(arg)
            
            elif req == "SIGNATURE":
                self.enq_signature(arg)
                
            elif req == "ATTRIBUTES":
                self.enq_attributes(arg)
            
            elif req == "HELP":
                self.enq_help(arg)

            else:
                self.response.write('<not a valid request>')
                
        print('IntrospectionThread stopped')
    
    
    def getSignature(self,objectName):
        """ Get the signature of builtin, function or method.
        Returns a tuple (signature_string, kind), where kind is a string
        of one of the above. When none of the above, both elements in
        the tuple are an empty string.
        """
        
        # if a class, get init
        # not if an instance! -> try __call__ instead        
        # what about self?
        
        # find out what kind of function, or if a function at all!
        NS = self.interpreter.locals
        fun1 = eval("inspect.isbuiltin(%s)"%(objectName), None, NS)
        fun2 = eval("inspect.isfunction(%s)"%(objectName), None, NS)
        fun3 = eval("inspect.ismethod(%s)"%(objectName), None, NS)
        fun4 = False
        fun5 = False
        if not (fun1 or fun2 or fun3):
            # Maybe it's a class with an init?
            if eval("isinstance(%s,type)"%(objectName), None, NS):
                if eval("hasattr(%s,'__init__')"%(objectName), None, NS):
                    objectName += ".__init__"
                    fun4 = eval("inspect.ismethod(%s)"%(objectName), None, NS)
            #  Or a callable object?
            elif eval("hasattr(%s,'__call__')"%(objectName), None, NS):
                objectName += ".__call__"
                fun5 = eval("inspect.ismethod(%s)"%(objectName), None, NS)
                
        if fun1:
            # the first line in the docstring is usually the signature
            kind = 'builtin'
            tmp = eval("%s.__doc__"%(objectName), {}, NS )
            sigs = tmp.splitlines()[0]
            if not ( sigs.count("(") and sigs.count(")") ):
                sigs = ""
                kind = ''            
            
        elif fun2 or fun3 or fun4 or fun5:
            
            if fun2:
                kind = 'function'
            elif fun3:
                kind = 'method'
            elif fun4:
                kind = 'class'
            elif fun5:
                kind = 'callable'
            
            # collect
            tmp = eval("inspect.getargspec(%s)"%(objectName), None, NS)
            args, varargs, varkw, defaults = tmp
            
            # prepare defaults
            if defaults == None:
                defaults = ()
            defaults = list(defaults)
            defaults.reverse()
            # make list (back to forth)
            args2 = []
            for i in range(len(args)-fun4):
                arg = args.pop()
                if i < len(defaults):
                    args2.insert(0, "%s=%s" % (arg, defaults[i]) )
                else:
                    args2.insert(0, arg )
            # append varargs and kwargs
            if varargs:
                args2.append( "*"+varargs )
            if varkw:
                args2.append( "**"+varkw )
            
            # append the lot to our  string
            funname = objectName.split('.')[-1]
            sigs = "%s(%s)" % ( funname, ", ".join(args2) )
            
        else:
            sigs = ""
            kind = ""
        
        return sigs, kind
    
    
    def enq_signature(self, objectName):
        
        try:
            text, kind = self.getSignature(objectName)
        except Exception:
            text = None
            
        # respond
        if text:
            self.response.write( text)
        else:
            self.response.write( "<error>" )
    
    
    def enq_attributes(self, objectName):
        
        # Get namespace
        NS = self.interpreter.locals
        
        # Init names
        names = set()
        
        # Obtain all attributes of the class
        try:
            command = "dir(%s.__class__)" % (objectName)
            d = eval(command, {}, NS)
        except Exception:            
            pass
        else:
            names.update(d)
        
        # Obtain instance attributes
        try:
            command = "%s.__dict__.keys()" % (objectName)
            d = eval(command, {}, NS)
        except Exception:            
            pass
        else:
            names.update(d)
            
        # That should be enough, but in case __dir__ is overloaded,
        # query that as well
        try:
            command = "dir(%s)" % (objectName)
            d = eval(command, {}, NS)
        except Exception:            
            pass
        else:
            names.update(d)
        
        # Respond
        if names:
            self.response.write( ",".join(list(names)) )
        else:
            self.response.write( "<error>" )
    
    
    def enq_keys(self, objectName):
        
        # Get namespace
        NS = self.interpreter.locals
        
        # get dir
        command = "%s.keys()" % (objectName)
        try:
            d = eval(command, {}, NS)
        except Exception:            
            d = None
       
        # respond
        if d:
            self.response.write( ",".join(d) )
        else:
            self.response.write( "<error>" )
    
    
    def enq_help(self,objectName):
        """ get help on an object """
        
        # Get namespace
        NS = self.interpreter.locals
        
        try:
            # collect data            
            h_text = eval("%s.__doc__"%(objectName), {}, NS )            
            h_repr = eval("repr(%s)"%(objectName), {}, NS )
            try:
                h_class = eval("%s.__class__.__name__"%(objectName), {}, NS )
            except:
                h_class = "unknown"
            
            # docstring can be None, but should be empty then
            if not h_text:
                h_text = ""
            
            # get and correct signature
            h_fun, kind = self.getSignature(objectName)
            if kind == 'builtin' or not h_fun:
                h_fun = ""  # signature already in docstring or not available
            
            # cut repr if too long
            if len(h_repr) > 200:
                h_repr = h_repr[:200] + "..."                
            # replace newlines so we can separates the different parts
            h_repr = h_repr.replace('\n', '\r')
            
            # build final text
            text = '\n'.join([objectName, h_class, h_fun, h_repr, h_text])
        
        except Exception, why:
            text = "No help available: " + str(why)
        
        # Done
        self.response.write( text )
    
    
    def enq_eval(self, command):
        """ do a command and send "str(result)" back. """
        
        # Get namespace
        NS = self.interpreter.locals
        
        try:
            # here globals is None, so we can look into sys, time, etc...
            d = eval(command, None, NS)
#             d = eval(command, {}, self.locals)
        except Exception, why:            
            d = None
        
        # respond
        if d:
            self.response.write( str(d) )
        else:
            self.response.write( str(why) )
       