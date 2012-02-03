# -*- coding: utf-8 -*-
# Copyright (c) 2010, the IEP development team
#
# IEP is distributed under the terms of the (new) BSD License.
# The full license can be found in 'license.txt'.

""" 
Magic commands for the IEP kernel.
"""

import sys
import os

MESSAGE = """List of *magic* commands:
    ?               - show this message
    ?X or X?        - show docstring of X
    ??X or X??      - help(X)
    cd              - show current directory
    cd X            - change directory
    ls              - list current directory
    who             - list variables in current workspace
    whos            - list variables plus their class and representation
    timeit X        - times execution of command X
    db start        - start post mortem debugging
    db stop         - stop debugging
    db up/down      - go up or down the stack frames
    db frame X      - go to the Xth stack frame
    db where        - print the stack trace and indicate the current stack
    db focus        - open the file and show the line of the stack frame
"""

# TODO: reimplement:
"""
open X          - open file, module, or file that defines X
opendir Xs      - open all files in directory X      
"""   

TIMEIT_MESSAGE = """Time execution duration. Usage:
    timeit fun  # where fun is a callable
    timeit 'expression'
    timeit 20 fun  # tests 20 passes
    For more advanced use, see the timeit module.
"""

# todo: either not allow changing the echo command, or do any printing via print statement. The only way I think it may be useful is in reliably passing a filename for the ide to open (db focus, open X)

class Magician:
    
    def _eval(self, command):
        
        # Get namespace
        NS1 = sys._iepInterpreter.locals
        NS2 = sys._iepInterpreter.globals
        if not NS2:
            NS = NS1
        else:
            NS = NS2.copy()
            NS.update(NS1)
        
        # Evaluate in namespace
        return eval(command, {}, NS)
    
    
    def convert_command(self, line):
        """ convert_command(line)
        
        Convert a given command from a magic command to Python code.
        Returns a two element tuple that contains the command to display
        and the command to execute.
        
        """
        # Make robust, converted functions can pass None to use the original
        res = self._convert_command(line)
        
        if isinstance(res, tuple):
            return res[0], res[1]  # Pass shown line and command
        elif res:
            return line, res # Pass only the command
        else:
            return line, line # Pass nothing
    
    
    def _convert_command(self, line):
        
        # Get interpreter
        interpreter = sys._iepInterpreter
        
        # Clean and make case insensitive
        command = line.upper().rstrip()
        
        if not command:
            return line  # Empty line; return original line
        
        elif command == '?':
            return 'print(%s)' % repr(MESSAGE)
        
        elif command.startswith("??"):
            return 'help(%s)' % line[2:].rstrip()
        elif command.endswith("??"):
            return 'help(%s)' % line.rstrip()[:-2]
        
        elif command.startswith("?"):
            return 'print(%s.__doc__)' % line[1:].rstrip()
            
        elif command.endswith("?"):
            return 'print(%s.__doc__)' % line.rstrip()[:-1]
        
        elif command.startswith('CD'):
            return self.cd(line, command)
        
        elif command.startswith('LS'):
            return self.ls(line, command)
        
        elif command.startswith('DB '):
            return self.debug(line, command)
        
        elif command.startswith('TIMEIT'):
            return self.timeit(line, command)
        
        elif command == 'WHO':
            return self.who(line, command)
        
        elif command == 'WHOS':
            return self.whos(line, command)
    
    
    def debug(self, line, command):
        
        # Get interpreter
        interpreter = sys._iepInterpreter
        
        if command == 'DB START':
            # Collect frames from the traceback
            tb = sys.last_traceback
            frames = []
            while tb:
                frames.append(tb.tb_frame)
                tb = tb.tb_next
            # Enter debug mode if there was an error
            if frames:
                interpreter._dbFrames = frames
                interpreter._dbFrameIndex = len(interpreter._dbFrames)
                frame = interpreter._dbFrames[interpreter._dbFrameIndex-1]
                interpreter._dbFrameName = frame.f_code.co_name
                interpreter.locals = frame.f_locals
                interpreter.globals = frame.f_globals
                # Notify IEP
                interpreter.writeStatus() # todo: debug status?
            else:
                interpreter.write("No debug information available.\n")
        
        elif command.startswith('DB FRAME '):
            if not interpreter._dbFrames:
                interpreter.write("Not in debug mode.\n")
            else:
                # Set frame index
                interpreter._dbFrameIndex = int(command.rsplit(' ',1)[-1])
                if interpreter._dbFrameIndex < 1:
                    interpreter._dbFrameIndex = 1
                elif interpreter._dbFrameIndex > len(interpreter._dbFrames):
                    interpreter._dbFrameIndex = len(interpreter._dbFrames)
                # Set name and locals
                frame = interpreter._dbFrames[interpreter._dbFrameIndex-1]
                interpreter._dbFrameName = frame.f_code.co_name
                interpreter.locals = frame.f_locals
                interpreter.globals = frame.f_globals
                interpreter.writeStatus()
        
        elif command == 'DB UP':
            if not interpreter._dbFrames:
                interpreter.write("Not in debug mode.\n")
            else:
                # Decrease frame index
                interpreter._dbFrameIndex -= 1
                if interpreter._dbFrameIndex < 1:
                    interpreter._dbFrameIndex = 1
                # Set name and locals
                frame = interpreter._dbFrames[interpreter._dbFrameIndex-1]
                interpreter._dbFrameName = frame.f_code.co_name
                interpreter.locals = frame.f_locals
                interpreter.globals = frame.f_globals
                interpreter.writeStatus()
        
        elif command == 'DB DOWN':
            if not interpreter._dbFrames:
                interpreter.write("Not in debug mode.\n")
            else:
                # Increase frame index
                interpreter._dbFrameIndex += 1
                if interpreter._dbFrameIndex > len(interpreter._dbFrames):
                    interpreter._dbFrameIndex = len(interpreter._dbFrames)
                # Set name and locals
                frame = interpreter._dbFrames[interpreter._dbFrameIndex-1]
                interpreter._dbFrameName = frame.f_code.co_name
                interpreter.locals = frame.f_locals
                interpreter.globals = frame.f_globals
                interpreter.writeStatus()
        
        elif command == 'DB STOP':
            if not interpreter._dbFrames:
                interpreter.write("Not in debug mode.\n")
            else:
                interpreter.locals = interpreter._main_locals
                interpreter.globals = None
                interpreter._dbFrames = []
                interpreter.writeStatus()
        
        elif command == 'DB WHERE':
            if not interpreter._dbFrames:
                interpreter.write("Not in debug mode.\n")
            else:
                lines = []
                for i in range(len(interpreter._dbFrames)):
                    frameIndex = i+1
                    f = interpreter._dbFrames[i]
                    # Get fname and lineno, and correct if required
                    fname, lineno = f.f_code.co_filename, f.f_lineno
                    fname, lineno = interpreter.correctFilenameAndLineno(fname, lineno)
                    # Build string
                    text = 'File "%s", line %i, in %s' % (
                                            fname, lineno, f.f_code.co_name)
                    if frameIndex == interpreter._dbFrameIndex:
                        lines.append('-> %i: %s'%(frameIndex, text))
                    else:
                        lines.append('   %i: %s'%(frameIndex, text))
                lines.append('')
                sys.stdout.write('\n'.join(lines))
        
        # Done (no code to execute)
        return line, ''
    
    
    def cd(self, line, command):
        if command == 'CD' or command.startswith("CD ") and '=' not in command:
            path = line[3:].strip()
            if path:
                os.chdir(path)
                newPath = os.getcwd()
            else:
                newPath = os.getcwd()
            return 'print(%s)\n' % repr(newPath)
    
    def ls(self, line, command):
        if command == 'LS' or command.startswith("LS ") and '=' not in command:
            path = line[3:].strip()
            if not path:
                path = os.getcwd()
            L = [p for p in os.listdir(path) if not p.startswith('.')]
            text = '\n'.join(sorted(L))
            return 'print(%s)\n' % repr(text)
    
    
    def timeit(self, line, command):
        if command == "TIMEIT":
            return line, 'print(%s)' % repr(TIMEIT_MESSAGE)
        elif command.startswith("TIMEIT "):
            expression = line[7:]
            # Get number of iterations
            N = 1
            tmp = expression.split(' ',1)
            if len(tmp)==2:
                try:
                    N = int(tmp[0])
                    expression = tmp[1]
                except Exception:
                    pass
            # Compile expression
            line2 = 'import timeit; t=timeit.Timer(%s);' % expression
            line2 += 'print(str( t.timeit(%i)/%i ) ' % (N, N)
            line2 += '+" seconds on average for %i iterations." )' % N
            #
            return line2
    
    
    def who(self, line, command):
        L = self._eval('dir()\n')
        L = [k for k in L if not k.startswith('__')]
        if L:
            text = ', '.join(L)
        else:
            text = "There are no variables defined in this scope."
        return 'print(%s)\n' % repr(text)
    
    
    def _justify(self, line, width, offset):
        realWidth = width - offset
        if len(line) > realWidth:
            line = line[:realWidth-3] + '...'
        return line.ljust(width)
    
    
    def whos(self, line, command):
        # Get list of variables
        L = self._eval('dir()\n')
        L = [k for k in L if not k.startswith('__')]
        # Anny variables?
        if not L:
            text = "There are no variables defined in this scope."
            return 'print(%s)\n' % repr(text)
        else:
            text = "VARIABLE: ".ljust(20,' ') + "TYPE: ".ljust(20,' ') 
            text += "REPRESENTATION: ".ljust(20,' ') + '\n'
        # Create list item for each variablee
        for name in L:
            ob = self._eval(name)
            cls = ''
            if hasattr(ob, '__class__'):
                cls = ob.__class__.__name__
            rep = repr(ob)
            text += self._justify(name,20,2) + self._justify(cls,20,2)
            text += self._justify(rep,40,2) + '\n'
        # Done
        return 'print(%s)\n' % repr(text)
