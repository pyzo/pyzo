import os
import sys
import subprocess

from .inwinreg import register_interpreter


class PythonInterpreter:
    """ Clas to represent a Python interpreter. It has properties
    to get the path and version. Upon creation the version number is
    acquired by calling the interpreter in a subprocess. If this fails,
    the version becomes ''.
    
    """
    def __init__(self, path):
        if not isinstance(path, str):
            raise ValueError('Path for PythonInterpreter is not a string: %r' % path)
        if not os.path.isfile(path):
            raise ValueError('Path for PythonInterpreter is invalid: %r' % path)
        self._path = os.path.normpath(os.path.abspath(path))
        self._normpath = os.path.normcase(self._path)
        self._is_pyzo = False
        self._problem = ''
        self._version = None
    
    def __repr__(self):
        cls_name = self.__class__.__name__
        return '<%s version %s at %s>' % (cls_name, self.version, self.path)
    
    def __hash__(self):
        return hash(self._normpath)
    
    def __eq__(self, other):
        return self._normpath == other._normpath
    
    
    @property
    def path(self):
        """ The full path to the executable of the Python interpreter.
        """
        return self._path
    
    @property
    def is_pyzo(self):
        """ Whether this is a Pyzo interpreter.
        """ 
        return self._is_pyzo
    
    @property
    def version(self):
        """ The version number as a string, usually 3 numbers.
        """
        if self._version is None:
            self._version = self._getversion()
        return self._version
    
    @property
    def version_info(self):
        """ The version number as a tuple of integers. For comparing.
        """
        return _versionStringToTuple(self.version)
    
    def register(self):
        """ Register this Python intepreter. On Windows this modifies
        the CURRENT_USER. On All other OS's this is a no-op.
        """
        if sys.platform.startswith('win'):
            path = os.path.split(self.path)[0] # Remove "python.exe"
            register_interpreter(self.version[:3], path)
    
    def _getversion(self):
        
        # Check if path is even a file
        if not os.path.isfile(self._path):
            self._problem = '%s is not a valid file.'
            return ''
        
        # Poll Python executable (--version does not work on 2.4)
        # shell=True prevents loads of command windows popping up on Windows,
        # but if used on Linux it would enter interpreter mode
        cmd = [self._path, '-V']
        try:
            v = subprocess.check_output(cmd, stderr=subprocess.STDOUT, 
                                        shell=sys.platform.startswith('win'))
        except (OSError, IOError, subprocess.CalledProcessError) as e:
            self._problem = str(e)
            return ''
        
        # Extract the version, apply some defensive programming
        v = v.decode('ascii','ignore').strip().lower()
        if v.startswith('python'):
            v = v.split(' ')[1]
        v = v.split(' ')[0]
        
        # Try turning it into version_info
        try:
            _versionStringToTuple(v)
        except ValueError:
            return ''
        
        # Done
        return v


class PyzoInterpreter(PythonInterpreter):
    """ A Pyzo interpreter.
    """
    def __init__(self, path):
        PythonInterpreter.__init__(self, path)
        self._is_pyzo = True


def _versionStringToTuple(version):
    # Truncate version number to first occurance of non-numeric character
    tversion = ''
    for c in version:
        if c in '0123456789.':  tversion += c
    # Split by dots, make each number an integer
    tversion = tversion.strip('.')
    return tuple( [int(a) for a in tversion.split('.') if a] )
