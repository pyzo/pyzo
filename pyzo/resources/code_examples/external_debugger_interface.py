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

print('example Pyhon application')
print('this process has PID', os.getpid())
cnt = 0
while True:
    cnt += 1
    print('cnt:', cnt)
    time.sleep(1.0)


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

    # Execute "cnt = -1234" in the shell.
    # Finally terminate the shell (e.g. via "Shell -> Close" in Pyzo's menu).
    # The external Python application is now running again, but with the modified cnt value.

    # You can reconnect again by executing this code cell again.
