# -*- coding: utf-8 -*-
# Copyright (c) 2012, Almar Klein

""" 
This module implements functionality to list installed Python 
interpreters, as well as Pyzo interpreters.

This list is compiled by looking at common location, and on Windows
the registry is searched as well.
"""

import sys
import os
from pyzolib import paths
from pyzolib import ssdf

from .pythoninterpreter import PythonInterpreter, PyzoInterpreter, _versionStringToTuple
from .inwinreg import get_interpreters_in_reg


def get_interpreters(minimumVersion=None):
    """ get_interpreters(minimumVersion=None)
    Returns a list of PythonInterpreter instances.
    If minimumVersion is given, return only the interprers with at least that
    version, and also sort the result by version number.
    """
    
    # Get Python interpreters
    if sys.platform.startswith('win'):
        pythons = _get_interpreters_win() 
    else:
        pythons = _get_interpreters_posix()
    pythons = set([PythonInterpreter(p) for p in pythons])
    
    # Get conda paths
    condas = set([PythonInterpreter(p) for p in _get_interpreters_conda()])
    
    # Get Pyzo paths
    pyzos = set([PyzoInterpreter(p) for p in _get_interpreters_pyzo()])
    
    
    # Remove Pyzo interpreters from pythons
    pythons = pythons.difference(condas)
    pythons = pythons.difference(pyzos)
    
    # Almost done
    interpreters = list(condas) + list(pyzos) + list(pythons)
    minimumVersion = minimumVersion or '0'
    return _select_interpreters(interpreters, minimumVersion)


def _select_interpreters(interpreters, minimumVersion):
    """ Given a list of PythonInterpreter instances, return a list with
    the interpreters selected that are valid and have their version equal 
    or larger than the given minimimVersion. The returned list is sorted
    by version number.
    """ 
    if not isinstance(minimumVersion, str):
        raise ValueError('minimumVersion in get_interpreters must be a string.')
    # Remove invalid interpreters
    interpreters = [i for i in interpreters if i.version]
    # Remove the ones below the reference version
    if minimumVersion is not None:
        refTuple = _versionStringToTuple(minimumVersion)
        interpreters = [i for i in interpreters if (i.version_info >= refTuple)]
    # Return, sorted by version
    return sorted(interpreters, key=lambda x:x.version_info)


def _get_interpreters_win():
    found = []
    
    # Query from registry
    for v in get_interpreters_in_reg():
        found.append(v.installPath() )
    
    # Check common locations
    for rootname in ['c:/', 'C:/program files/', 'C:/program files (x86)/']:
        if not os.path.isdir(rootname):
            continue
        for dname in os.listdir(rootname):
            if dname.lower().startswith('python'):
                try: 
                    version = float(dname[len('python'):])
                except ValueError:
                    continue
                else:
                    found.append(os.path.join(rootname, dname))
    
    # Normalize all paths, and remove trailing backslashes
    found = [os.path.normcase(os.path.abspath(v)).strip('\\') for v in found]
    
    # Append "python.exe" and check if that file exists
    found2 = []
    for dname in found:
        exename = os.path.join(dname, 'python.exe')
        if os.path.isfile(exename):
            found2.append(exename)
    
    # Returnas set (remove duplicates)
    return set(found2)


def _get_interpreters_posix():
    found=[]
    for searchpath in ['/usr/bin','/usr/local/bin','/opt/local/bin']: 
        # Get files
        try:
            files = os.listdir(searchpath)
        except Exception:
            continue
        
        # Search for python executables
        for fname in files:
            if fname.startswith('python') and not fname.count('config'):
                if len(fname) < 16:
                    # Get filename and resolve symlink
                    filename = os.path.join(searchpath, fname)
                    filename = os.path.realpath(filename)
                    # Seen on OS X that was not a valid file
                    if os.path.isfile(filename):  
                        found.append(filename)
    
    # Return as set (remove duplicates)
    return set(found)


def _get_interpreters_pyzo():
    """ Get a list of known Pyzo interpreters.
    """
    pythonname = 'python' + '.exe' * sys.platform.startswith('win')
    exes = []
    for d in paths.pyzo_dirs():
        for fname in [  os.path.join(d, 'bin', pythonname + '3'),
                        os.path.join(d, pythonname), ]:
            if os.path.isfile(fname):
                exes.append(fname)
                break
    return exes


def _get_interpreters_conda():
    """ Get known conda environments
    """
    if sys.platform.startswith('win'):
        pythonname = 'python' + '.exe'
    else:
        pythonname = 'bin/python'
    
    exes = []
    filename = os.path.expanduser('~/.conda/environments.txt')
    if os.path.isfile(filename):
        for line in open(filename, 'rt').readlines():
            line = line.strip()
            exe_filename = os.path.join(line, pythonname)
            if line and os.path.isfile(exe_filename):
                exes.append(exe_filename)
    return exes


if __name__ == '__main__':
    for pi in get_interpreters():
        print(pi)

