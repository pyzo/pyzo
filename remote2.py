import sys
import time
import code
import traceback
import types

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
    
    def write(self, text):
        sys.stderr.write(text)
    
    
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
        self.write(sys.ps1)
    
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
#                 if mmfile:
#                     if more:
#                         mmfile[5] = '2'
#                     else:
#                         mmfile[5] = '1'
                
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
#                     if mmfile:
#                         mmfile[5] = '0'
                    
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
                        self.write(sys.ps2)  # write writes to stderr
                    else:
                        self.write(sys.ps1)                    
                
#                 # update tk and wx 50 times per second
#                 if time.clock() - guitime > 0.019: # a bit sooner for sync
#                     if tkapp:
#                         tkapp.update()
#                     if wxapp:
#                         wxapp.ProcessPendingEvents()
#                         wxapp.ProcessIdle() # otherwise frames do not close
#                     if flapp:
#                         flapp.wait(0)
#                     if qtapp:
#                         qtapp.processEvents()
#                     guitime = time.clock()
                    
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
        