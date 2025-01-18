import os
import sys
import time
import bdb
import traceback


class Debugger(bdb.Bdb):
    """Debugger for the pyzo kernel, based on bdb."""

    def __init__(self):
        self._wait_for_mainpyfile = False  # from pdb, do we need this?
        bdb.Bdb.__init__(self)
        self._debugmode = 0  # 0: no debug,  1: postmortem,  2: full debug
        self._files_with_offset = set()
        if hasattr(sys, "breakpointhook"):
            self._original_breakpointhook = sys.breakpointhook
            sys.breakpointhook = self.custom_breakpointhook
        self._last_db_command = None

    def custom_breakpointhook(self, *args, **kwargs):
        """handle "breakpoint()" commands
        see https://docs.python.org/3/library/sys.html#sys.breakpointhook
        """
        s = os.environ.get("PYTHONBREAKPOINT", None)
        if s == "0":
            pass  # deactivated
        elif s is None or s == "":
            self.set_trace()
        else:
            self._original_breakpointhook(*args, **kwargs)

    def clear_all_breaks(self):
        bdb.Bdb.clear_all_breaks(self)
        self._files_with_offset.clear()

    def trace_dispatch(self, frame, event, arg):
        # Overload to deal with offset in filenames
        # (cells or lines being executed)
        ori_filename = frame.f_code.co_filename

        if "+" in ori_filename and ori_filename not in self._files_with_offset:
            clean_filename, offset = ori_filename.rsplit("+", 1)
            try:
                offset = int(offset)
            except Exception:
                offset = None
            if offset is not None:
                # This is a cell or selected lines being executed
                self._files_with_offset.add(ori_filename)
                if clean_filename.startswith("<"):
                    self.fncache[ori_filename] = ori_filename
                for i in self.breaks.get(clean_filename, []):
                    self.set_break(ori_filename, i - offset)

        return bdb.Bdb.trace_dispatch(self, frame, event, arg)

    def interaction(self, frame, traceback=None, pm=False, framesBefore=None):
        """Enter an interaction-loop for debugging. No GUI events are
        processed here. We leave this event loop at some point, after
        which the control flow will proceed.

        This is called to enter debug-mode at a breakpoint, or to enter
        post-mortem debugging.

        Special case for frames where f_back is None, e.g. in a generator expression:
            For post mortem debugging we will allow to continue at the
            frame before, e.g. before the generator expression.
            see https://stackoverflow.com/a/51867843
        """
        interpreter = sys._pyzoInterpreter

        if framesBefore is None:
            framesBefore = []
        else:
            framesBefore = framesBefore[:]

        # Collect frames
        frames = []
        while frame:
            if frame is self.botframe:
                break
            co_filename = frame.f_code.co_filename
            if "pyzokernel" in co_filename:
                break  # pyzo kernel
            if "interactiveshell.py" in co_filename:
                break  # IPython kernel
            frames.insert(0, frame)
            if frame.f_back is None and pm and len(framesBefore) > 0:
                frame = framesBefore.pop()
            else:
                frame = frame.f_back

        # Tell interpreter our stack
        if frames:
            interpreter._dbFrames = frames
            interpreter._dbFrameIndex = len(interpreter._dbFrames)
            frame = interpreter._dbFrames[interpreter._dbFrameIndex - 1]
            interpreter._dbFrameName = frame.f_code.co_name
            interpreter.locals = frame.f_locals
            interpreter.globals = frame.f_globals

        # Let the IDE know
        self._debugmode = 1 if pm else 2
        self.writestatus()

        # Enter interact loop. We may hang in here for a while ...
        self._interacting = True
        while self._interacting:
            try:
                time.sleep(0.05)
                interpreter.process_commands()
                pe = os.getenv("PYZO_PROCESS_EVENTS_WHILE_DEBUGGING", "").lower()
                if pe in ("1", "true", "yes"):
                    interpreter.guiApp.process_events()
            except KeyboardInterrupt:
                self.message("KeyboardInterrupt")

        # Reset
        self._debugmode = 0
        interpreter.locals = interpreter._main_locals
        interpreter.globals = None
        interpreter._dbFrames = []
        self.writestatus()

    def stopinteraction(self):
        """Stop the interaction loop."""
        self._interacting = False
        sys.settrace(None)

    def set_on(self):
        """To turn debugging on right before executing code."""
        # Reset and set bottom frame
        self.reset()
        self.botframe = sys._getframe().f_back
        # Don't stop except at breakpoints or when finished
        self._set_stopinfo(self.botframe, None, -1)
        self._last_db_command = None

    def message(self, msg):
        """Alias for interpreter.write(), but appends a newline.
        Writes to stderr.
        """
        sys._pyzoInterpreter.write(msg + "\n")

    def error(self, msg):
        """method used in some code that we copied from pdb."""
        raise self.message("*** " + msg)

    def writestatus(self):
        """Write the debug status so the IDE can take action."""

        interpreter = sys._pyzoInterpreter

        # Collect frames info
        frames = []
        for f in interpreter._dbFrames:
            # Get fname and lineno, and correct if required
            fname, lineno = f.f_code.co_filename, f.f_lineno
            fname, lineno = interpreter.correctfilenameandlineno(fname, lineno)
            if not fname.startswith("<"):
                fname2 = os.path.abspath(fname)
                if os.path.isfile(fname2):
                    fname = fname2
            frames.append((fname, lineno, f.f_code.co_name))
            # Build string
            # text = 'File "%s", line %i, in %s' % (
            #                        fname, lineno, f.f_code.co_name)
            # frames.append(text)

        # Send info object
        state = {
            "index": interpreter._dbFrameIndex,
            "frames": frames,
            "debugmode": self._debugmode,
        }
        interpreter.context._stat_debug.send(state)

    ## Stuff that we need to overload

    # Overload set_break to also allow non-existing filenames like "<tmp 1"
    def set_break(self, filename, lineno, temporary=False, cond=None, funcname=None):
        filename = self.canonic(filename)
        list = self.breaks.setdefault(filename, [])
        if lineno not in list:
            list.append(lineno)
        bdb.Breakpoint(filename, lineno, temporary, cond, funcname)

    # Prevent stopping in bdb code or pyzokernel code
    def stop_here(self, frame):
        result = bdb.Bdb.stop_here(self, frame)
        if result:
            return ("bdb.py" not in frame.f_code.co_filename) and (
                "pyzokernel" not in frame.f_code.co_filename
            )

    def do_clear(self, arg):
        """ """  # this docstring is a single space on purpose
        # Clear breakpoints, we need to overload from Bdb,
        # but do not expose this command to the user.
        """cl(ear) filename:lineno\ncl(ear) [bpnumber [bpnumber...]]
        With a space separated list of breakpoint numbers, clear
        those breakpoints.  Without argument, clear all breaks (but
        first ask confirmation).  With a filename:lineno argument,
        clear all breaks at that line in that file.
        """
        if not arg:
            bplist = [bp for bp in bdb.Breakpoint.bpbynumber if bp]
            self.clear_all_breaks()
            for bp in bplist:
                self.message("Deleted %s" % bp)
            return
        if ":" in arg:
            # Make sure it works for "clear C:\foo\bar.py:12"
            i = arg.rfind(":")
            filename = arg[:i]
            arg = arg[i + 1 :]
            try:
                lineno = int(arg)
            except ValueError:
                err = "Invalid line number (%s)" % arg
            else:
                bplist = self.get_breaks(filename, lineno)
                err = self.clear_break(filename, lineno)
            if err:
                self.error(err)
            else:
                for bp in bplist:
                    self.message("Deleted %s" % bp)
            return
        numberlist = arg.split()
        for i in numberlist:
            try:
                bp = self.get_bpbynumber(i)
            except ValueError:
                self.error("Cannot get breakpoint by number.")
            else:
                self.clear_bpbynumber(i)
                self.message("Deleted %s" % bp)

    def user_call(self, frame, argument_list):
        """This method is called when there is the remote possibility
        that we ever need to stop in this function."""
        if self._wait_for_mainpyfile:
            return
        if self.stop_here(frame):
            self.message("--Call--")
            self.interaction(frame, None)

    def user_line(self, frame):
        """This function is called when we stop or break at this line."""
        if self._wait_for_mainpyfile:
            if (
                self.mainpyfile != self.canonic(frame.f_code.co_filename)
                or frame.f_lineno <= 0
            ):
                return
            self._wait_for_mainpyfile = False
        if True:  # self.bp_commands(frame):  from pdb
            self.interaction(frame, None)

    def user_return(self, frame, return_value):
        """This function is called when a return trap is set here."""
        if self._wait_for_mainpyfile:
            return
        frame.f_locals["__return__"] = return_value
        self.message("--Return--")
        self.interaction(frame, None)

    def user_exception(self, frame, exc_info):
        """This function is called if an exception occurs,
        but only if we are to stop at or just below this level."""
        if self._wait_for_mainpyfile:
            return
        exc_type, exc_value, exc_traceback = exc_info
        frame.f_locals["__exception__"] = exc_type, exc_value
        self.message(traceback.format_exception_only(exc_type, exc_value)[-1].strip())
        self.interaction(frame, exc_traceback)

    ## Commands

    def do_help(self, arg):
        """Get help on debug commands."""
        # Collect docstrings
        docs = {}
        for name in dir(self):
            if name.startswith("do_"):
                doc = getattr(self, name).__doc__
                if doc and doc != " ":
                    docs[name[3:]] = doc.strip()

        if not arg:
            print("All debug commands:")
            # Show docs in order
            for name in [
                "start",
                "stop",
                "frame",
                "up",
                "down",
                "next",
                "step",
                "return",
                "jump",
                "continue",
                "where",
                "events",
            ]:
                doc = docs.pop(name)
                name = name.rjust(10)
                print(" %s - %s" % (name, doc))
            # Show rest
            for name in docs:
                doc = docs[name]
                name = name.rjust(10)
                print(" %s - %s" % (name, doc))

        else:
            # Show specific doc
            name = arg.lower()
            doc = docs.get(name, None)
            if doc is not None:
                print("%s - %s" % (name, doc))
            else:
                print("Unknown debug command: %s" % name)

    def _get_traceback_combinations(self):
        """get all possible combinations for tracebacks

        If the exception is an ExceptionGroup, it can consist of sub-exeptions
        and even nested ExceptionGroup objects. We identify a branch via the
        sub-exception numbers that are printed in the traceback ("---- 1 ----" etc.).

        A tuple (3, 2) addresses the ValueError sub-sub-exception in the following example.
        ExceptionGroup  --> ()
            ---- 1 ----  --> (1,)
            ZeroDivisionError
            ---- 2 ----  --> (2,)
            KeyError
            ---- 3 ----  --> (3,)
            ExceptionGroup
                ---- 1 ----  --> (3, 1)
                TypeError
                ---- 2 ----  --> (3, 2)
                ValueError

        return value: tb_combs, first_nongroup
            tb_combs ... a dictionary of kv-pairs
                key: the tuple branch-identifier
                value: the traceback of that (sub-)exception
            first_nongroup ... the key to the tb_combs dict to the first traceback of an
                non-ExceptionGroup -- useful as a default selection
        """
        tb_combs = {}
        first_nongroup = None
        try:
            value = sys.last_value
            # Python 2.7 exceptions have no __traceback__ attribute
            tb = sys.last_traceback
        except AttributeError:
            tb = None

        if tb is not None:
            # add all combinations for nested exception groups
            p = ()
            stack = [(value, p)]
            nongroup_exceptions = []
            tb_combs[p] = tb
            while len(stack) > 0:
                e, p = stack.pop()
                if e.__class__.__name__ == "ExceptionGroup":
                    for num, e2 in enumerate(e.exceptions, 1):
                        p2 = p + (num,)
                        stack.append((e2, p2))
                        tb_combs[p2] = e2.__traceback__
                else:
                    nongroup_exceptions.append(p)
            if nongroup_exceptions:
                first_nongroup = min(nongroup_exceptions)
        return tb_combs, first_nongroup

    def _get_selected_traceback(self, arg):
        """get the current traceback, and in case of ExceptionGroup, select one of many"""
        tb_combs, first_nongroup = self._get_traceback_combinations()
        tb = tb_combs.get((), None)
        if len(tb_combs) > 1:
            # there is at least one ExceptionGroup
            user_selected_comb = None
            selected_comb = None
            if arg != "":
                try:
                    user_selected_comb = tuple([int(s) for s in arg.split()])
                    # Selecting the root-ExceptionGroup would normally be done with
                    # an empty tuple. But we want the empty tuple, which is args == "",
                    # to be the "automatic" selection option.
                    # So we use "DB START 0" to get the root-ExceptionGroup
                    # and "DB START" to automatically select the traceback.
                    if user_selected_comb == (0,):
                        user_selected_comb = ()
                    if user_selected_comb not in tb_combs:
                        user_selected_comb = None
                except Exception:
                    user_selected_comb = None

                if user_selected_comb is None:
                    self.message(
                        "invalid parameter " + repr(arg) + " -- will be ignored"
                    )
                else:
                    selected_comb = user_selected_comb

            if selected_comb is None:
                # automatically select the traceback
                if first_nongroup is not None:
                    selected_comb = first_nongroup
                else:
                    selected_comb = ()

            tb = tb_combs[selected_comb]

            if user_selected_comb is None:
                cw = 16
                msg_lines = [
                    "There is at least one ExceptionGroup. To select the traceback of a specific group,",
                    "stop the debugger and type the magic command DB START with (nested) group numbers.",
                    "Possible commands for the last traceback are:",
                    "db stop".ljust(cw) + "<-- stops the debugger",
                    "db traceback".ljust(cw) + "<-- prints the last traceback again",
                    "db start".ljust(cw)
                    + "<-- this will automatically choose the first non-ExceptionGroup",
                ]
                for comb in sorted(tb_combs.keys()):
                    comment = ""
                    if comb == selected_comb:
                        if selected_comb == first_nongroup:
                            comment = "<-- currently used (automatically chosen -- first non-exc-group)"
                        else:
                            comment = (
                                "<-- currently used (automatically chosen -- fallback)"
                            )

                    if comb == ():
                        comb_string = "0"
                        if comment == "":
                            comment = "<-- zero means: explicitly choose the root ExceptionGroup"
                    else:
                        comb_string = " ".join([str(a) for a in comb])
                    msg_lines.append(("db start " + comb_string).ljust(cw) + comment)
                self.message("\n".join(msg_lines))
        return tb

    def do_start(self, arg):
        """Start postmortem debugging from the last uncaught exception."""

        # Since the introduction of ExceptionGroup, there could be multiple tracebacks
        # of interest. A specific one can be selected using the "arg" parameter.
        tb = self._get_selected_traceback(arg)

        # Get top frame
        frame = None
        framesBefore = []
        while tb:
            framesBefore.append(frame)
            frame = tb.tb_frame
            tb = tb.tb_next

        # Interact, or not
        if self._debugmode:
            self.message("Already in debug mode.")
        elif frame:
            self.interaction(frame, None, pm=True, framesBefore=framesBefore)
        else:
            self.message("No debug information available.")

    def do_frame(self, arg):
        """Go to the i'th frame in the stack."""
        interpreter = sys._pyzoInterpreter

        if not self._debugmode:
            self.message("Not in debug mode.")
        else:
            # Set frame index
            interpreter._dbFrameIndex = int(arg)
            if interpreter._dbFrameIndex < 1:
                interpreter._dbFrameIndex = 1
            elif interpreter._dbFrameIndex > len(interpreter._dbFrames):
                interpreter._dbFrameIndex = len(interpreter._dbFrames)
            # Set name and locals
            frame = interpreter._dbFrames[interpreter._dbFrameIndex - 1]
            interpreter._dbFrameName = frame.f_code.co_name
            interpreter.locals = frame.f_locals
            interpreter.globals = frame.f_globals
            self.writestatus()

    def do_up(self, arg):
        """Go one frame up the stack."""
        interpreter = sys._pyzoInterpreter

        if not self._debugmode:
            self.message("Not in debug mode.")
        else:
            # Decrease frame index
            interpreter._dbFrameIndex -= 1
            if interpreter._dbFrameIndex < 1:
                interpreter._dbFrameIndex = 1
            # Set name and locals
            frame = interpreter._dbFrames[interpreter._dbFrameIndex - 1]
            interpreter._dbFrameName = frame.f_code.co_name
            interpreter.locals = frame.f_locals
            interpreter.globals = frame.f_globals
            self.writestatus()

    def do_down(self, arg):
        """Go one frame down the stack."""
        interpreter = sys._pyzoInterpreter

        if not self._debugmode:
            self.message("Not in debug mode.")
        else:
            # Increase frame index
            interpreter._dbFrameIndex += 1
            if interpreter._dbFrameIndex > len(interpreter._dbFrames):
                interpreter._dbFrameIndex = len(interpreter._dbFrames)
            # Set name and locals
            frame = interpreter._dbFrames[interpreter._dbFrameIndex - 1]
            interpreter._dbFrameName = frame.f_code.co_name
            interpreter.locals = frame.f_locals
            interpreter.globals = frame.f_globals
            self.writestatus()

    def do_stop(self, arg):
        """Stop debugging, terminate process execution."""
        # Can be done both in postmortem and normal debugging
        if not self._debugmode:
            self.message("Not in debug mode.")
        else:
            self.set_quit()
            self.stopinteraction()

    def do_where(self, arg):
        """Print the stack trace and indicate the current frame."""
        interpreter = sys._pyzoInterpreter

        if not self._debugmode:
            self.message("Not in debug mode.")
        else:
            lines = []
            for i in range(len(interpreter._dbFrames)):
                frameIndex = i + 1
                f = interpreter._dbFrames[i]
                # Get fname and lineno, and correct if required
                fname, lineno = f.f_code.co_filename, f.f_lineno
                fname, lineno = interpreter.correctfilenameandlineno(fname, lineno)
                # Build string
                text = 'File "%s", line %i, in %s' % (fname, lineno, f.f_code.co_name)
                if frameIndex == interpreter._dbFrameIndex:
                    lines.append("-> %i: %s" % (frameIndex, text))
                else:
                    lines.append("   %i: %s" % (frameIndex, text))
            lines.append("")
            sys.stdout.write("\n".join(lines))

    def do_continue(self, arg):
        """Continue the program execution."""
        if self._debugmode == 0:
            self.message("Not in debug mode.")
        elif self._debugmode == 1:
            self.message("Cannot use 'continue' in postmortem debug mode.")
        else:
            # the following line is a workaround for a specific problem:
            sys._pyzoInterpreter.apply_breakpoints()

            # run the following code without any breakpoints:
            """
            [breakpoint() for _ in range(1)]
            # [breakpoint()]  # this does not cause any problem
            x = 1
            y = 2  # set a breakpoint in this line once stopped in the upper breakpoint()
            """
            # The breakpoint at the line above would be ignored if:
            # a) the interruption is inside a list comprehension
            # and b) the Python interpreter version is >= 3.0 and < 3.12
            # The problem would also occur when pausing inside a list comprehension.
            # As a workaround we call apply_breakpoints a second time, see above.

            self._last_db_command = "continue"
            self.set_continue()
            self.stopinteraction()

    def do_step(self, arg):
        """Execute the current line, stop ASAP (step into)."""
        if self._debugmode == 0:
            self.message("Not in debug mode.")
        elif self._debugmode == 1:
            self.message("Cannot use 'step' in postmortem debug mode.")
        else:
            self._last_db_command = "step"
            self.set_step()
            self.stopinteraction()

    def do_next(self, arg):
        """Continue execution until the next line (step over)."""
        interpreter = sys._pyzoInterpreter

        if self._debugmode == 0:
            self.message("Not in debug mode.")
        elif self._debugmode == 1:
            self.message("Cannot use 'next' in postmortem debug mode.")
        else:
            frame = interpreter._dbFrames[-1]
            self._last_db_command = "next"
            self.set_next(frame)
            self.stopinteraction()

    def do_return(self, arg):
        """Continue execution until the current function returns (step out)."""
        interpreter = sys._pyzoInterpreter

        if self._debugmode == 0:
            self.message("Not in debug mode.")
        elif self._debugmode == 1:
            self.message("Cannot use 'return' in postmortem debug mode.")
        else:
            self._last_db_command = "return"
            frame = interpreter._dbFrames[-1]
            self.set_return(frame)
            self.stopinteraction()

    def do_jump(self, arg):
        """Jump to a specific line, not executing code in between."""
        interpreter = sys._pyzoInterpreter

        if self._debugmode == 0:
            self.message("Not in debug mode.")
        elif self._debugmode == 1:
            self.message("Cannot use 'jump' in postmortem debug mode.")
        elif interpreter._dbFrameIndex != len(interpreter._dbFrames):
            self.message(
                "Jumping is only possible inside the bottom frame (highest index)."
            )
        else:
            frame = interpreter._dbFrames[interpreter._dbFrameIndex - 1]
            try:
                lineno = int(arg)
                f = interpreter._dbFrames[-1]
                offset = interpreter.correctfilenameandlineno(f.f_code.co_filename, 0)[
                    1
                ]
                frame.f_lineno = lineno - offset
            except ValueError as e:
                self.message("Error DB JUMP: " + str(e))
            self.writestatus()

    def do_events(self, arg):
        """Process GUI events for the integrated GUI toolkit."""
        interpreter = sys._pyzoInterpreter
        interpreter.guiApp.process_events()

    def do_traceback(self, arg):
        """Print the last traceback (again)."""
        interpreter = sys._pyzoInterpreter
        interpreter.showtraceback(True)
