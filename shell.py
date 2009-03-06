""" MODULE SHELL
Defines the shell to be used in IEP.
This is done in a few inheritance steps:

    - IepShell inherits IepTextCtrl and adds the typical shell behaviour.
    
    - IepPythonShell makes it specific to Python.
"""

import iep
from editor import IepTextCtrl

class IepShell(IepTextCtrl):
    
    def __init__(self, parent):
        IepTextCtrl.__init__(self, parent)
        
    