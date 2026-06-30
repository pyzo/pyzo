"""
PEP 768 introduced a new "safe external debugger interface" in
Python 3.14 -- see https://peps.python.org/pep-0768

This allows us to temporarily insert a Pyzo kernel in an external Python application
and to debug the application from a new shell inside the Pyzo IDE.
"""


## Example code for any external Python application that you want to debug

# Run this code in a Python >= v3.14 interpreter and remember the PID.
# Or get the PID of any running Python application (>= v3.14) that you want to debug.

import os
import time

def myfunc1():

    def myfunc2():
        cnt2 = 1
        while cnt2 < 5:
            time.sleep(0.2)
            print('cnt2:', cnt2)
            cnt2 += 1

    print('example Python application')
    print('this process has PID', os.getpid())
    cnt1 = 0
    while True:
        cnt1 += 1
        print('cnt1:', cnt1)
        time.sleep(2.0)
        myfunc2()

myfunc1()


##
if False:
##

    # Make sure that the Pyzo IDE is running.

    # Run the following code in another Python >= v3.14 interpreter (e.g. Pyzo shell).

    import inspect
    import sys
    import os

    this_dir = os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())))
    # or: this_dir = '/path/to/folder/of/start_external_shell_script'

    pid = 14782  # TODO:  <--- change the PID to the one of the external Python application
    sys.remote_exec(pid, os.path.join(this_dir, 'start_external_shell.py'))


    # A few seconds later, a new shell will appear in the Pyzo IDE, and the external
    # Python application is paused.

    # Now you can inspect variables and execute code, like in any other shell in Pyzo.
    # The shell starts with the outermost frame for global and local variables, so
    # you only see "myfunc1" and the imports in the current scope.

    # The code for starting the external shell could be called anywhere where it is
    # convenient for the Python interpreter. For the example code above, it will most
    # likely happen inside myfunc1 or myfunc2.
    # You can switch (from the outermost scope) to the scope of myfunc1 by executing
    # the following line in the shell:
    #     import sys; sys._pyzoInterpreter.switchframe(-2)
    # Then you can inspect/modify variable "cnt1".
    # For example, execute "cnt1 = -1234" in the shell.
    # If the start of the external shell happend inside myfunc2, then you can also
    # inspect the values there (cnt2). To switch to that frame, execute the line:
    #     import sys; sys._pyzoInterpreter.switchframe(-3)

    # Finally terminate the shell (e.g. via "Shell -> Close" in Pyzo's menu).
    # The external Python application is now running again, but with the modified cnt1 value.

    # You can reconnect again by executing this code cell again.
