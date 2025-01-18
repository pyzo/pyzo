import sys
import signal
import yoton
import inspect  # noqa - used in eval()


PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION < 3:
    import thread
else:
    import _thread as thread


# we keep this file in ascii encoding to stay compatible with Python 2.7 kernels
THREE_DOTS_CHAR = b"\xe2\x80\xa6".decode("utf-8")


class PyzoIntrospector(yoton.RepChannel):
    """This is a RepChannel object that runs a thread to respond to
    requests from the IDE.
    """

    def _getNameSpace(self, name=""):
        """Get the namespace to apply introspection in.

        If name is given, will find that name. For example sys.stdin.
        """

        # Get namespace
        NS1 = sys._pyzoInterpreter.locals
        NS2 = sys._pyzoInterpreter.globals
        if not NS2:
            NS = NS1
        else:
            NS = NS2.copy()
            NS.update(NS1)

        # Look up a name?
        if not name:
            return NS
        else:
            try:
                # Get object
                ob = eval(name, None, NS)

                # Get namespace for this object
                if isinstance(ob, dict) or hasattr(
                    ob, "keys"
                ):  # os.environ is no dict but has keys
                    NS = {"[" + repr(el) + "]": ob[el] for el in ob.keys()}
                elif isinstance(ob, (list, tuple)):
                    NS = {}
                    count = -1
                    for el in ob:
                        count += 1
                        NS["[%i]" % count] = el
                else:
                    keys = dir(ob)
                    NS = {}
                    for key in keys:
                        try:
                            NS[key] = getattr(ob, key)
                        except Exception:
                            NS[key] = "<unknown>"

                # Done
                return NS

            except Exception:
                return {}

    def _getSignature(self, objectName):
        """Get the signature of builtin, function or method.

        Returns a tuple (signature_string, kind), where kind is a string
        of one of the above. When none of the above, both elements in
        the tuple are an empty string.
        """

        # if a class, get init
        # not if an instance! -> try __call__ instead
        # what about self?

        # Get valid object names
        parts = objectName.rsplit(".")
        objectNames = [".".join(parts[-i:]) for i in range(1, len(parts) + 1)]

        # find out what kind of function, or if a function at all!
        originalObjectName = objectName
        NS = self._getNameSpace()
        fun1 = eval("inspect.isbuiltin(%s)" % (objectName), None, NS)
        fun2 = eval("inspect.isfunction(%s)" % (objectName), None, NS)
        fun3 = eval("inspect.ismethod(%s)" % (objectName), None, NS)
        fun4 = False
        fun5 = False
        if not (fun1 or fun2 or fun3):
            # Maybe it's a class with an init?
            if eval("hasattr(%s,'__init__')" % (objectName), None, NS):
                objectName += ".__init__"
                fun4 = eval("inspect.ismethod(%s)" % (objectName), None, NS)
            #  Or a callable object?
            elif eval("hasattr(%s,'__call__')" % (objectName), None, NS):
                objectName += ".__call__"
                fun5 = eval("inspect.ismethod(%s)" % (objectName), None, NS)

        sigs = ""
        if True:
            # the first line in the docstring is usually the signature
            tmp = eval("%s.__doc__" % (objectNames[-1]), {}, NS)
            sigs = ""
            if tmp:
                # we need the lstrip for docstrings like the one of np.where:
                #   np.where.__doc__[:34] == '\n    where(condition, [x, y], /)\n\n'
                tmp = tmp.lstrip()

                # we will try joining several lines because doc strings of objects
                # like np.array have a new line inside the signature
                for line in tmp.splitlines()[:3]:
                    line = line.strip()
                    sigs += line
                    if not line.endswith(","):
                        break
                    sigs += " "
            # Test if doc has signature
            hasSig = False
            for name in objectNames:  # list.append -> L.append(object) -- blabla
                name += "("
                if name in sigs:
                    hasSig = True
            if not hasSig and PYTHON_VERSION >= 3:
                # Also get the signature for objects where inspect.signature does not
                # work and where the function/method has a differnt name, e.g.:
                # import sys; myfunc = sys.getsizeof
                # myfunc.__doc__ --> has a docstring starting with "getsizeof("
                indOpenParen = sigs.find("(")
                if indOpenParen > 0 and sigs[:indOpenParen].isidentifier():
                    hasSig = True
                    sigs = objectName + sigs[indOpenParen:]
            # If not a valid signature, do not bother ...
            if (not hasSig) or (sigs.count("(") != sigs.count(")")):
                sigs = ""
            if sigs == "":
                # try inspect.signature to also get a signature for objects like
                #   np.sum, pd.DataFrame, ...
                try:
                    sigs = eval(
                        "str(inspect.signature(%s))" % (originalObjectName), None, NS
                    )
                    sigs = originalObjectName + sigs
                except Exception:
                    pass

        if fun1 or fun2 or fun3 or fun4 or fun5:
            if fun1:
                kind = "builtin"
            elif fun2:
                kind = "function"
            elif fun3:
                kind = "method"
            elif fun4:
                kind = "class"
            elif fun5:
                kind = "callable"

            if not sigs:
                # Use introspection

                funname = objectName.split(".")[-1]

                try:
                    tmp = eval(
                        "inspect.signature(%s)" % (objectName), None, NS
                    )  # py3.3
                    sigs = funname + str(tmp)
                except Exception:
                    try:
                        # for Python < v3.3
                        tmp = eval("inspect.getargspec(%s)" % (objectName), None, NS)
                    except Exception:  # the above fails for builtins
                        tmp = None
                        kind = ""

                    if tmp is not None:
                        args, varargs, varkw, defaults = tmp[:4]
                        # prepare defaults
                        if defaults is None:
                            defaults = ()
                        defaults = list(defaults)
                        defaults.reverse()
                        # make list (back to forth)
                        args2 = []
                        for i in range(len(args) - fun4):
                            arg = args.pop()
                            if i < len(defaults):
                                args2.insert(0, "%s=%s" % (arg, defaults[i]))
                            else:
                                args2.insert(0, arg)
                        # append varargs and kwargs
                        if varargs:
                            args2.append("*" + varargs)
                        if varkw:
                            args2.append("**" + varkw)
                        # append the lot to our string
                        sigs = "%s(%s)" % (funname, ", ".join(args2))

        elif sigs:
            kind = "function"
        else:
            sigs = ""
            kind = ""

        return sigs, kind

    def dirWithIntermediateResult(self, objectName):
        cacheVarName = "__pyzo__autocomp"
        try:
            command = cacheVarName + " = " + str(objectName)
            exec(command, sys._pyzoInterpreter.globals, sys._pyzoInterpreter.locals)
        except Exception:
            return []
        else:
            return self.dir(cacheVarName)

    # todo: variant that also says whether it's a property/function/class/other
    def dir(self, objectName):
        """Get list of attributes for the given name."""
        # sys.__stdout__.write('handling '+objectName+'\n')
        # sys.__stdout__.flush()

        # Get namespace
        NS = self._getNameSpace()

        # Init names
        names = set()

        # Obtain all attributes of the class
        try:
            command = "__pyzo_builtin_dir__(%s.__class__)" % (objectName)
            d = eval(command, {"__pyzo_builtin_dir__": dir}, NS)
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
            command = "__pyzo_builtin_dir__(%s)" % (objectName)
            d = eval(command, {"__pyzo_builtin_dir__": dir}, NS)
        except Exception:
            pass
        else:
            names.update(d)

        # Respond
        return list(names)

    def dir2WithIntermediateResult(self, objectName):
        cacheVarName = "__pyzo__autocomp"
        try:
            command = cacheVarName + " = " + str(objectName)
            exec(command, sys._pyzoInterpreter.globals, sys._pyzoInterpreter.locals)
        except Exception:
            return []
        else:
            return self.dir2(cacheVarName)

    def dir2(self, objectName):
        """Get variable names in currently active namespace plus extra information.

        Returns a list of tuple of strings: name, type, kind, repr.
        """
        try:
            name = ""
            names = []

            def storeInfo(name, val):
                # Determine type
                typeName = type(val).__name__
                # Determine kind
                kind = typeName
                if typeName != "type":
                    if (
                        hasattr(val, "__array__")
                        and hasattr(val, "dtype")
                        and hasattr(val, "shape")
                        and not hasattr(
                            val,
                            "if_this_is_an_attribute_then_there_are_likely_inf_attributes",
                        )
                    ):
                        kind = "array"
                    elif isinstance(val, list):
                        kind = "list"
                    elif isinstance(val, tuple):
                        kind = "tuple"
                # Determine representation
                if kind == "array":
                    tmp = "x".join([str(s) for s in val.shape])
                    if tmp:
                        values_repr = ""
                        if hasattr(val, "flat"):
                            for el in val.flat:
                                # using str instead of repr to have
                                # "<array 3 int64: 1, 2, 3>"
                                # instead of
                                # "<array 3 int64: np.int64(1), np.int64(2), np.int64(3)>"
                                values_repr += ", " + str(el)
                                if len(values_repr) > 70:
                                    values_repr = values_repr[:69] + THREE_DOTS_CHAR
                                    break
                        repres = "<array %s %s: %s>" % (
                            tmp,
                            val.dtype.name,
                            values_repr[2:],  # remove the leading ", "
                        )
                    elif val.size:
                        # val can be a non-numeric or structured type as well, e.g.:
                        #     val = np.array(['abc'], dtype=np.dtype('U3'))[0]
                        repres = "<array scalar %s (%s)>" % (val.dtype.name, str(val))
                    else:
                        repres = "<array empty %s>" % (val.dtype.name)
                elif kind == "list":
                    values_repr = ""
                    for el in val:
                        values_repr += ", " + repr(el)
                        if len(values_repr) > 70:
                            values_repr = values_repr[:69] + THREE_DOTS_CHAR
                            break
                    repres = "<%i-element list: %s>" % (len(val), values_repr[2:])
                elif kind == "tuple":
                    values_repr = ""
                    for el in val:
                        values_repr += ", " + repr(el)
                        if len(values_repr) > 70:
                            values_repr = values_repr[:69] + THREE_DOTS_CHAR
                            break
                    repres = "<%i-element tuple: %s>" % (len(val), values_repr[2:])
                elif kind == "dict":
                    values_repr = ""
                    for k, v in val.items():
                        values_repr += ", " + repr(k) + ": " + repr(v)
                        if len(values_repr) > 70:
                            values_repr = values_repr[:69] + THREE_DOTS_CHAR
                            break
                    repres = "<%i-item dict: %s>" % (len(val), values_repr[2:])
                else:
                    repres = repr(val)
                    if len(repres) > 80:
                        repres = repres[:79] + THREE_DOTS_CHAR
                # Store
                tmp = (name, typeName, kind, repres)
                names.append(tmp)

            # Get locals
            NS = self._getNameSpace(objectName)
            for name in NS.keys():  # name can be a key in a dict, i.e. not str
                if hasattr(name, "startswith") and name.startswith("__"):
                    continue
                try:
                    storeInfo(str(name), NS[name])
                except Exception:
                    pass

            return names

        except Exception:
            return []

    def signatureWithIntermediateResult(self, objectName):
        cacheVarName = "__pyzo__calltip"
        try:
            command = cacheVarName + " = " + str(objectName)
            exec(command, sys._pyzoInterpreter.globals, sys._pyzoInterpreter.locals)
        except Exception:
            return None
        else:
            return self.signature(cacheVarName)

    def signature(self, objectName):
        """Get signature."""
        try:
            text, kind = self._getSignature(objectName)
            return text
        except Exception:
            return None

    def doc(self, objectName):
        """Get documentation for an object."""

        # Get namespace
        NS = self._getNameSpace()

        try:
            # collect docstring
            h_text = ""
            # Try using the class (for properties)
            try:
                className = eval("%s.__class__.__name__" % (objectName), {}, NS)
                if "." in objectName:
                    tmp = objectName.rsplit(".", 1)
                    tmp[1] += "."
                else:
                    tmp = [objectName, ""]
                if className not in [
                    "type",
                    "module",
                    "builtin_function_or_method",
                    "function",
                ]:
                    cmd = "%s.__class__.%s__doc__"
                    h_text = eval(cmd % (tmp[0], tmp[1]), {}, NS)
            except Exception:
                pass

            # Normal doc
            if not h_text:
                h_text = eval("%s.__doc__" % (objectName), {}, NS)

            # collect more data
            h_repr = eval("repr(%s)" % (objectName), {}, NS)
            try:
                h_class = eval("%s.__class__.__name__" % (objectName), {}, NS)
            except Exception:
                h_class = "unknown"

            # docstring can be None, but should be empty then
            if not h_text:
                h_text = ""

            # get and correct signature
            h_fun, kind = self._getSignature(objectName)

            if not h_fun:
                h_fun = ""  # signature not available

            # cut repr if too long
            if len(h_repr) > 200:
                h_repr = h_repr[:200] + "..."
            # replace newlines so we can separates the different parts
            h_repr = h_repr.replace("\n", "\r")

            # build final text
            text = "\n".join([objectName, h_class, h_fun, h_repr, h_text])

        except Exception:
            type, value, tb = sys.exc_info()
            del tb
            text = "\n".join(
                [objectName, "", "", "", "No help available. ", str(value)]
            )

        # Done
        return text

    def evalMultiple(self, sequenceOfExpressions):
        """evaluate multiple expressions

        The result will be converted to a string and truncated if too long.
        In case of an error, the result will be the exception as a string.

        return value:
            [(request1, success1, result1), (request2, success2, result2), ...]
        """
        NS = self._getNameSpace()
        maxChars = 150

        returnValue = []
        for expr in sequenceOfExpressions:
            try:
                result = str(eval(expr, None, NS))[: maxChars + 1]
                if len(result) > maxChars:
                    result = result[: maxChars - 1] + THREE_DOTS_CHAR
                success = True
            except Exception as e:
                result = str(e)
                success = False

            returnValue.append((expr, success, result))

        return returnValue

    def eval(self, command):
        """Evaluate a command and return result."""

        # Get namespace
        NS = self._getNameSpace()

        try:
            # here globals is None, so we can look into sys, time, etc...
            return eval(command, None, NS)
        except Exception:
            return "Error evaluating: " + command

    def interrupt(self, command=None, signum=signal.SIGINT):
        """Interrupt the main thread.

        This does not work if the main thread is running extension code.

        A bit of a hack to do this in the introspector, but it's the
        easiest way and prevents having to launch another thread just
        to wait for an interrupt/terminate command.

        Note that on POSIX we can send an OS INT signal, which is faster
        and maybe more effective in some situations.

        signum must be signal.SIGINT for kernels running Python < 3.10
        """
        if signum == signal.SIGINT:
            thread.interrupt_main()
        else:
            if sys.version_info < (3, 10):
                print("This feature is not implemented for Python versions < 3.10!")
                return
            thread.interrupt_main(signum)

    def terminate(self, command=None):
        """terminate()

        Ask the kernel to terminate by closing the stdin.

        """
        sys.stdin._channel.close()


##
if False:
    ## execute this cell to test signature extraction
    tt = """
    bytes
    int
    iter
    min
    import numpy as np; np.linspace; np.sum; np.array; np.linalg.norm
    import pandas as pd; pd.DataFrame
    import requests; requests.Request
    """
    for line in tt.strip().splitlines():
        ll = line.split("; ")
        if len(ll) == 1:
            ll.insert(0, None)
        if ll[0] is not None:
            exec(ll[0].strip())
        for s in ll[1:]:
            sig = __pyzo__.introspector.signature(s)  # noqa: F821
            if sig == "":
                print("!!! could not extract the signature of", s, "!!!")
            else:
                print(sig)
            print()
