import sys
import time
import code
import traceback
import types

import threading
import inspect

class IepInterpreter(code.InteractiveConsole):
    """Closely emulate the interactive Python console.
    Almost the same as code.InteractiveConsole, but interact()
    is overriden to change the following:
    - prompts are printed in the err stream, like the default interpreter does
    - uses an asynchronous read() function
    - this read() function may return tuples (sourceCode, filename, lineno)
      to execute blocks of code. The showtraceback method is modified such
      that the linenr is given the proper offset (when part of a file is
      executed) and that the correct line (where it went wrong) is displayed.
    - support for tk
    Note: the sys.stdin needs to have a .readline2() method, which does not 
          block, but returns "" when nothing is available.
    """
    
    def __init__(self, *args, **kwargs):
        code.InteractiveConsole.__init__(self, *args, **kwargs)
        
        self._status = 'a status string that is never used'
    
    
    def write(self, text):
        sys.stderr.write( text )
    
    def setStatus(self, status):
        if self._status != status:
            self._status = status
            sys._status.write(status)
    
    
    def interact(self, banner=None):    
        """ interact! (start the mainloop)
        """
        
        # prompts
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
            
        # banner
        cprt =  'Type "help", "copyright", "credits" or "license"'\
                ' for more information.'
        moreBanner = 'This is the IepInterpreter. Type "?" for'\
                     ' a list of *magic* commands.'
        # moreBanner = self.__class__.__name__
        if banner is None:
            self.write("Python %s on %s\n%s\n%s\n" %
                       (sys.version, sys.platform, cprt,
                        moreBanner))
        else:
            self.write("%s\n" % str(banner))
        self.write(str(sys.ps1))
    
#         # hijack tk and wx
#         self.tkapp = tkapp = None#hijack_tk()
#         self.wxapp = wxapp = hijack_wx()
#         self.flapp = flapp = hijack_fl()
#         self.qtapp = qtapp = hijack_qt4()
        
        # create list to store codeBlocks that we execute
        self._codeList = []
        
        guitime = time.clock()        
        more = 0
        while True:
            try:
                # set status
                if more:
                    self.setStatus('More')
                else:
                    self.setStatus('Ready')
                
                # wait for a bit
                time.sleep(0.010) # 10 ms
                
                # are we still connected?
                if sys.stdin.closed:
                    self.write("\n")
                    break
                
                # read a packet
                line = sys.stdin.readOne(False)
                
                # process the line
                if line:
                    # set busy
                    self.setStatus('Busy')
                    
                    if isinstance(line,tuple):
                        # EXECUTE MODE
                        more = False
                        fname = line[1]
                        code = None
                        try:
                            # put the index of the codeBlock in the filename
                            fname = "%s [%i]" %(fname, len(self._codeList))
                            # put the information in the filename
                            self._codeList.append( line )
                            # compile the code
                            code = self.compile(line[0], fname, "exec")
                        except (OverflowError, SyntaxError, ValueError):
                            self.showsyntaxerror(fname)
                        if code:
                            self.runcode(code)
                    else:
                        # NORMAL MODE
                        line = line.rstrip("\n") # this is what push wants
                        more = self.push(line)
                    
                    if more:                        
                        self.write(str(sys.ps2))  # write writes to stderr
                    else:
                        # prompt is allowed to be an object with __str__ method
                        self.write(str(sys.ps1)) 
                
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
                    
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0
                self.write(sys.ps1)
            except TypeError, err:
                # For some reason, when wx is hijacked, keyboard interrupts
                # result in a TypeError on "time.sleep(0.010)".
                # I tried to find the source, but did not find it. If anyone
                # has an idea, please mail me!
                if err.message == "'int' object is not callable":
                    self.write("\nKeyboardInterrupt\n")
                    self.resetbuffer()
                    more = 0
                    self.write(sys.ps1)
                else:
                    raise err
    
    
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
        try:         
            type, value, tb = sys.exc_info()
            frame = tb.tb_frame            
            sys.last_type = type
            sys.last_value = value
            sys.last_traceback = tb
            
            # get traceback and correct all the line numbers,
            # adding context information from what we stored...
            # The x in "c:\...\filename.py [x]" is the index to the list
            # of blocks of info.
            tblist = traceback.extract_tb(tb)            
            del tblist[:1]
            for i in range(len(tblist)):
                tb = tblist[i]
                # get codeblock number: piece between []                
                codenr = tb[0].rsplit("[",1)[-1].split("]",1)[0]
                try:
                    codeblock = self._codeList[int(codenr)]
                except (ValueError, IndexError):
                    continue
                # add info to traceback and correct line number             
                example = codeblock[0].splitlines()
                try:
                    example = example[ tb[1]-1 ]
                except IndexError:
                    example = ""
                lineno = tb[1] + int(codeblock[2])
                tblist[i] = ( tb[0], lineno, tb[2], example)
            
            # format list
            list = traceback.format_list(tblist)
            if list:
                list.insert(0, "Traceback (most recent call last):\n")
            list[len(list):] = traceback.format_exception_only(type, value)
        finally:
            tblist = tb = None
        map(self.write, list)



class IntroSpectionThread(threading.Thread):
    """ IntroSpectionThread
    Communicates with the IEP GUI, even if the main thread is busy.
    """
    
    def __init__(self, requestChannel, responseChannel, locals):
        threading.Thread.__init__(self)
        
        # store the two channel objects
        self.request = requestChannel
        self.response = responseChannel
        self.locals = locals
    
    
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
        ns = self.locals
        fun1 = eval("inspect.isbuiltin(%s)"%(objectName), None, ns)
        fun2 = eval("inspect.isfunction(%s)"%(objectName), None, ns)
        fun3 = eval("inspect.ismethod(%s)"%(objectName), None, ns)
        fun4 = False
        fun5 = False
        if not (fun1 or fun2 or fun3):
            # Maybe it's a class with an init?
            if eval("isinstance(%s,type)"%(objectName), None, ns):
                if eval("hasattr(%s,'__init__')"%(objectName), None, ns):
                    objectName += ".__init__"
                    fun4 = eval("inspect.ismethod(%s)"%(objectName), None, ns)
            #  Or a callable object?
            elif eval("hasattr(%s,'__call__')"%(objectName), None, ns):
                objectName += ".__call__"
                fun5 = eval("inspect.ismethod(%s)"%(objectName), None, ns)
                
        if fun1:
            # the first line in the docstring is usually the signature
            kind = 'builtin'
            tmp = eval("%s.__doc__"%(objectName), {}, ns )
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
            tmp = eval("inspect.getargspec(%s)"%(objectName), None, ns)
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
        
        # obtain list using dir function
        command = "dir(%s)" % (objectName)
        try:
            d = eval(command, {}, self.locals)
        except Exception:            
            d = None
       
        # todo: check for dir method to provide autocomp for pydicom
        
        # respond
        if d:
            self.response.write( ",".join(d) )
        else:
            self.response.write( "<error>" )
    
    
    def enq_keys(self, objectName):
        
        # get dir
        command = "%s.keys()" % (objectName)
        try:
            d = eval(command, {}, self.locals)
        except Exception:            
            d = None
       
        # respond
        if d:
            self.response.write( ",".join(d) )
        else:
            self.response.write( "<error>" )
    
    
    def enq_help(self,objectName):
        """ get help on an object """
        try:
            # collect data
            ns = self.locals
            h_text = eval("%s.__doc__"%(objectName), {}, ns )            
            h_repr = eval("repr(%s)"%(objectName), {}, ns )
            try:
                h_class = eval("%s.__class__.__name__"%(objectName), {}, ns )
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
        
        self.response.write( text )
    
    
    def enq_eval(self, command):
        """ do a command and send "str(result)" back. """
         
        try:
            # here globals is None, so we can look into sys, time, etc...
            d = eval(command, None, self.locals)
#             d = eval(command, {}, self.locals)
        except Exception, why:            
            d = None
        
        # respond
        if d:
            self.response.write( str(d) )
        else:
            self.response.write( str(why) )
       