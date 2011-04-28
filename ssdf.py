# -*- coding: utf-8 -*-
# Copyright (c) 2011, Almar Klein
#
# SSDF is distributed under the terms of the (new) BSD License.
# See http://www.opensource.org/licenses/bsd-license.php

""" Module ssdf

Simple Structured Data Format
-----------------------------
Ssdf is a simple format for stroring structured data. It supports
seven data types, two of which are container elements:
None, int, float, (Unicode) string, numpy array, list/tuple, dict/Struct.

One spec, two formats
---------------------
Ssdf is actually two formats: the original text format is human readable,
and thus enables inspecting databases and data structures using a simple
text editor. The binary format is more efficient and uses compression on
the whole file (the text format only compresses arrays). It is more suited
for storing really large databases or structures containing large arrays.
Both formats are fully compatible.

Functions of interest
---------------------
  * save    - save a struct to a file
  * saves   - serialize a struct to a string
  * saveb   - serialize a struct to bytes
  * load    - load a struct from file
  * loads   - load a struct from a string
  * loadb   - load a struct from bytes
  * update  - update a struct on file with a given struct
  * copy    - create a deep copy of a struct
  * new     - create a new empty struct
  * clear   - clear a struct, removing all elements
  * count   - count the number of elements in a struct

Notes
-----
SSDF comes as a single module. While it's a bit big (approaching 2k lines), 
it enables easier deployment inside a package in a way that works for 
Python 2 as well as Python 3.

"""

# General implementation used in this module:
# file or bytes/string <-> list of blocks <-> tree of blocks <-> Python objects

__version__ = '2.0'

import os
import sys
import time
import struct
import base64
import zlib
import re

# Try importing numpy
try:
    import numpy as np    
except ImportError:
    np = None

# If version 2 ...
if sys.version_info[0] <= 2:
    D = __builtins__
    if not isinstance(D, dict):
        D = D.__dict__
    simplestr = D['str']
    bytes = D['str']
    str = D['unicode']
    del D
    base64.encodebytes = base64.encodestring
    base64.decodebytes = base64.decodestring
else:
    basestring = str
    simplestr = str
    long = int
    from functools import reduce

# Determine float and int types
if True:
    _FLOAT_TYPES = set([float])
    _INT_TYPES = set([int, long])
if np:
    _FLOAT_TYPES.update([np.float32, np.float64])
    _INT_TYPES.update([   np.int8,  np.int16,  np.int32,  np.int64, 
                        np.uint8, np.uint16, np.uint32, np.uint64 ])
_FLOAT_TYPES = tuple(_FLOAT_TYPES)
_INT_TYPES = tuple(_INT_TYPES)

# Formatters for struct (un)packing
_SMALL_NUMBER_FMT = '<B'
_LARGE_NUMBER_FMT = '<Q'
_TYPE_FMT = '<c'
_PARTITION_LEN_FMT = '<I'
_PARTITION_SIZE = 2**20 # 1 MB

# To store other classes
_CLASS_NAME = '_CLASS_NAME_'


# The data types for arrays and how the struct (un)pack formatters.
_DTYPES = { 'uint8':'<B', 'int8':'<b', 
            'uint16':'<H', 'int16':'<h', 
            'uint32':'<L', 'int32':'<l', 
            'float32':'<f', 'float64':'<d' }


## Main functions and a few private functions

def _get_mode(filename, mode):
    """ _get_mode(filename, mode)
    
    Given filename and mode returns the mode (as 1 or 2).
    
    """ 
    
    # Determine mode from extension
    mode_ext = 0
    if filename.lower().endswith('.ssdf'):
        mode_ext = 1
    elif filename.lower().endswith('.bsdf'):
        mode_ext = 2
    
    # Determine given mode
    if isinstance(mode, basestring):
        mode = mode.lower()
    if mode in [1, 'text', 'string', 'str']:
        mode = 1
    elif mode in [2, 'binary', 'bin', 'bytes']:
        mode = 2
    elif mode:
        ValueError("Unknown mode given '%s'." % repr(mode))
    
    # Determine mode
    if not mode:
        mode = mode_ext
    elif mode_ext and mode_ext != mode:
        raise ValueError('Given mode does not correspond with extension.')
    if not mode:
        raise ValueError('No mode specified (and no known extension used).')
    
    # Done
    return mode


def save(filename, struct, mode=None):
    """ save(filename, struct, mode=None)
    
    Save the given struct or dict to the filesystem using the given filename.
    
    Two modes are supported: text mode stores in a human readable format, 
    and binary mode stores in a more efficient (compressed) binary format.
    
    Parameters
    ----------
    filename : str
        The location in the filesystem to save the file. Files with extension
        '.ssdf' are stored in text mode, and '.bsdf' files are stored in
        binary mode. If another extension is used, the mode should be
        specified explicitly.
    struct : {Struct, dict}
        The object to save.
    mode : optional {'text', 'str', 1, 'bin', 'bytes', 2}
        This parameter can be used to explicitly specify the mode. Note 
        that it is an error to use binary mode on a '.ssdf' file or text
        mode on a '.bsdf' file.
    
    """
    
    # Check
    if not (isstruct(struct) or isinstance(struct, dict)):
        raise ValueError('ssdf.save() expects the second argument to be a struct.')
    
    # Open file
    f = open(filename, 'wb')
    
    # Get mode
    mode = _get_mode(filename, mode)
    
    # Write
    writer = _SSDFWriter()
    if mode==1:
        # Write code directive and header
        header =  '# This Simple Structured Data Format (SSDF) file was '
        header += 'created from Python on %s.\n' % time.asctime()
        f.write('# -*- coding: utf-8 -*-\n'.encode('utf-8'))
        f.write(header.encode('utf-8'))
        # Write lines
        writer.struct_to_text(struct, f)
    elif mode==2:
        writer.struct_to_binary(struct, f)


def saves(struct):
    """ saves(struct)
    
    Serialize the given struct or dict to a (Unicode) string.
    
    Parameters
    ----------
    struct : {Struct, dict}
        The object to save.
    
    """
    # Check
    if not (isstruct(struct) or isinstance(struct, dict)):
        raise ValueError('ssdf.saves() expects a struct.')
    
    # Write
    writer = _SSDFWriter()
    return writer.struct_to_text(struct)


def saveb(struct):
    """ saveb(struct)
    
    Serialize the given struct or dict to (compressed) bytes.
    
    Parameters
    ----------
    struct : {Struct, dict}
        The object to save.
    
    """
    
    # Check
    if not (isstruct(struct) or isinstance(struct, dict)):
        raise ValueError('ssdf.saveb() expects a struct.')
    
    # Write
    writer = _SSDFWriter()
    return writer.struct_to_binary(struct)


def load(filename):
    """ load(filename)
    
    Load a struct from the filesystem using the given filename.
    
    Two modes are supported: text mode stores in a human readable format, 
    and binary mode stores in a more efficient (compressed) binary format.
    
    Parameters
    ----------
    filename : str
        The location in the filesystem of the file to load.
    
    """
    
    # Open file
    f = open(filename, 'rb')
    
    # Get mode
    try:
        firstfour = f.read(4).decode('utf-8')
    except Exception:
        raise ValueError('Not a valid ssdf file.')
    if firstfour == 'BSDF':
        mode = 2
    else:
        mode = 1 # This is an assumption.
    
    # Read
    f.seek(0)
    reader = _SSDFReader()
    if mode==1:
        return reader.text_to_struct(f)
    elif mode==2:
        return reader.binary_to_struct(f)


def loadb(bb):
    """ loadb(bb)
    
    Load a struct from the given bytes.
    
    Parameters
    ----------
    bb : bytes
        A serialized struct (obtained using ssdf.saveb()).
    
    """
    # Check
    if not isinstance(bb, bytes):
        raise ValueError('ssdf.loadb() expects bytes.')
    
    # Read
    reader = _SSDFReader()
    return reader.binary_to_struct(bb)


def loads(ss):
    """ loads(ss)
    
    Load a struct from the given string.
    
    Parameters
    ----------
    ss : (Unicode) string
        A serialized struct (obtained using ssdf.saves()).
    
    """
    # Check
    if not isinstance(ss, basestring):
        raise ValueError('ssdf.loads() expects a string.')
    
    # Read
    reader = _SSDFReader()
    return reader.text_to_struct(ss)


def update(filename, struct):
    """ update(filename, struct)
    
    Update an existing ssdf file with the given struct. 
    
    For every dict in the data tree, the elements are updated.
    Note that any lists occuring in both data trees are simply replaced.
    
    """
    
    # Load existing struct
    s = load(filename)
    
    # Insert stuff
    def insert(ob1, ob2):
        for name in ob2:
            if ( name in ob1 and isstruct(ob1[name]) and 
                                 isstruct(ob2[name]) ):
                insert(ob1[name], ob2[name])
            else:
                ob1[name] = ob2[name]
    insert(s, struct)
    
    # Save
    save(filename, s)


def new():
    """ new()
    
    Create a new Struct object. The same as "Struct()".
    
    """
    return Struct()


def clear(struct):
    """ clear(struct)
    
    Clear all elements of the given struct object.
    
    """
    for key in [key for key in struct]:
        del(struct.__dict__[key])


def count(object):
    """ count(object):
    
    Count the number of elements in the given object. 
    
    An element is defined as one of the 7 datatypes supported by ssdf 
    (dict/struct, tuple/list, array, string, int, float, None).
    
    """
    
    n = 1
    if isinstance(object, (dict, Struct)):
        for key in object:
            val = object[key]
            n += count(val)
    elif isinstance(object, (tuple, list)):
        for val in object:
            n += count(val)
    return n


def copy(object):
    """ copy(objec)
    
    Return a deep copy the given object. The object and its children
    should be ssdf-compatible data types.
    
    Note that dicts are converted to structs and tuples to lists.
    
    """
    if isinstance(object, (dict, Struct)):
        newObject = Struct()
        for key in object:
            val = object[key]
            newObject[key] = copy(val)
        return newObject
    elif isinstance(object, (tuple, list)):
        return [copy(ob) for ob in object]
    elif isinstance(object, VirtualArray):
        return VirtualArray(object.shape, object.dtype, object.data)
    elif np and isinstance(object, np.ndarray):
        return object.copy()
    else:
        # immutable
        return object


def _not_equal(ob1, ob2):
    """ _not_equal(ob1, ob2)
    
    Returns None if the objects are equal. Otherwise returns a string
    indicating how the objects are inequal.
    
    """
    
    if isinstance(ob1, (dict, Struct)):
        if not isinstance(ob2, (dict, Struct)):
            return '<type does not match>'
        # Test number of elements
        keys1 = [key for key in ob1]
        keys2 = [key for key in ob2]
        if len(keys1) != len(keys2):
            return '<lengths do not match>'
        # Test all elements
        for key in keys1:
            if key not in keys2:
                return '<key not present in other struct/dict>'
            not_equal = _not_equal(ob1[key], ob2[key])
            if not_equal:
                return '.' + key + not_equal
    
    elif isinstance(ob1, (tuple, list)):
        if not isinstance(ob2, (tuple, list)):
            return '<type does not match>'
        if len(ob1) != len(ob2):
            return '<lengths do not match>'
        # Test all elements        
        for i in range(len(ob1)):
            not_equal = _not_equal(ob1[i], ob2[i])
            if not_equal:
                return ('[%i]' % i) + not_equal
    
    elif isinstance(ob1, VirtualArray):
        if not isinstance(ob2, VirtualArray):
            return '<type does not match>'
        # Test properties
        if not (    ob1.shape==ob2.shape and 
                    ob1.dtype==ob2.dtype and 
                    ob1.data==ob2.data ):
            return '<array does not match>'
    
    elif np and isinstance(ob1, np.ndarray):
        if not isinstance(ob2, np.ndarray):
            return '<type does not match>'
        # Test properties
        if not (    ob1.shape==ob2.shape and 
                    ob1.dtype==ob2.dtype and 
                    (ob1==ob2).sum()==ob1.size ):
            return '<array does not match>'
    
    else:
        # Use default equality operator
        if not (ob1 == ob2):
            return '<objects not equal>'


def isstruct(ob):
    """ isstruct(ob)
    
    Returns whether the given object is an SSDF struct.
    
    """
    if hasattr(ob, '__is_ssdf_struct__'):
        return bool(ob.__is_ssdf_struct__)
    else:
        return False


def _isvalidname(name):
    """ _isvalidname(name)
    
    Returns attribute name, or None, if not valid 
    
    """
    
    # Is it a string?
    if not ( name and isinstance(name, basestring) ):
        return None
    
    # Check name
    namechars = str('abcdefghijklmnopqrstuvwxyz_0123456789')
    name2 = name.lower()
    if name2[0] not in namechars[0:-10]:
        return None
    tmp = map(lambda x: x not in namechars, name2[2:])
    
    # Return
    if sum(tmp)==0:
        return name


def _shapeString(ob):
    """ _shapeString(ob)
    
    Returns a string that represents the shape of the given array.
    
    """ 
    ss = str()
    for n in ob.shape:
        ss += '%ix' % n
    return ss[:-1]


## Public classes

class _ClassManager:
    """ _ClassManager
    
    This static class enables registering classes, which 
    can then be stored to ssdf and loaded from ssdf.
    
    On module loading, the sys module is given a reference to the 
    ClassManager called '_ssdf_class_manager'. Other classes can 
    thereby register themselves without knowing how to import 
    ssdf (provided that ssdf is already imported).
    
    """ 
    
    # Global dict with registered classes
    _registered_classes = {}
    
    @classmethod
    def _register_at_sys(manager):
        """ _register_at_sys()
        
        Register the manager at the sys module if there is not 
        already one of a higher version.
        
        """
        if hasattr(sys, '_ssdf_class_manager'):
            other = sys._ssdf_class_manager
            if manager.__version__() >= other.__version__():
                sys._ssdf_class_manager = manager
                manager._registered_classes.update(other._registered_classes)
                return manager
            else:
                return other
        else:
            sys._ssdf_class_manager = manager
            return manager
    
    @classmethod
    def __version__(manager):
        return __version__
    
    
    @classmethod
    def is_compatible_class(manager, cls):
        """ is_compatible_class(cls)
        
        Returns True if the given class is SSDF-compatible.
        
        """
        return not manager.is_incompatible_class(cls)
    
    
    @classmethod
    def is_incompatible_class(manager, cls):    
        """ is_incompatible_class(cls)
        
        Returns a string giving the reason why the given class 
        if not SSDF-compatible. If the class is compatible, this 
        function returns None.
        
        """
        if not hasattr(cls, '__to_ssdf__'):
            return "class does not have '__to_ssdf__' method"
        if not hasattr(cls, '__from_ssdf__'):
            return "class does not have '__from_ssdf__' classmethod"
        if not isinstance(cls, type):
            return "class is not a type (does not inherit object on Python 2.x)"
    
    
    @classmethod
    def register_class(manager, *args):
        """ register_class(class1, class2, class3, ...)
        
        Register one or more classes. Registered classes can be saved and 
        restored from ssdf. 
        
        A class needs to implement two methods to qualify for registration:
        * A method __to_ssdf__() that returns an ssdf.Struct
        * A classmethod __from_ssdf__(s) that accepts an ssdf.Struct and
          creates an instance of that class.
        
        """
        for cls in args:
            incomp = manager.is_incompatible_class(cls)
            if incomp:
                raise ValueError('Cannot register class %s: %s.' % 
                                                    (cls.__name__, incomp) )
            else:
                manager._registered_classes[cls.__name__] = cls
    
    
    @classmethod
    def is_registered_class(manager, cls):
        """ is_registered_class(cls)
        
        Returns True if the given class is registered.
        
        """
        return cls in manager._registered_classes.values()
    
    
    @classmethod
    def _get_objects(manager):
        """ _get_objects()
        
        Returns the public objects defined in the module where this manager
        is also defined. This way, different ssdf modules in the same
        process will actully use exactly the same classes.
        
        """
        return Struct, isstruct, VirtualArray

# Put in this module namespace and in sys module namespace
# The ClassManager is the latest version
ClassManager = _ClassManager._register_at_sys()
register_class = ClassManager.register_class



class Struct(object):
    """ Struct(dictionary=None) 
    
    Object to holds named data (syntactic sugar for a dictionary). 
    
    Attributes can be any of the seven SSDF supported types:
    struct/dict, tuple/list, numpy array, (Unicode) string, int, float, None.
    
    Elements can be added in two ways:
        * s.foo = 'bar'       # the object way
        * s['foo'] = 'bar'    # the dictionary way
    
    Supported features
    ------------------
    * Iteration - yields the keys/names in the struct
    * len() - returns the number of elements in the struct
    * del statement can be used to remove elements
    * two structs can be added, yielding a new struct with combined elements
    * testing for equality with other structs 
    
    Notes
    -----
      * The keys in the given dict should be valid names (invalid
        keys are ignoired).
      * On saving, names starting with two underscores are ignored.
      * This class does not inherit from dict to keep its namespace clean,
        avoid nameclashes, and to enable autocompletion of its items in 
        most IDE's.
      * To get the underlying dict, simply use s.__dict__.
    
    """    
    
    # Indentifier
    __is_ssdf_struct__ = True
    
        
    def __init__(self, a_dict=None):
        
        # Plain struct?
        if a_dict is None:
            return
        
        if not isinstance(a_dict, dict) and not isstruct(a_dict):
            tmp = "Struct can only be initialized with a Struct or a dict."
            raise ValueError(tmp)
        else:
            # Try loading from object
            
            def _getValue(val):
                """ Get the value, as suitable for Struct. """
                if isinstance(val, (basestring,) + _FLOAT_TYPES + _INT_TYPES ):
                    return val
                if np and isinstance(val, np.ndarray):
                    return val
                elif isinstance(val,(tuple,list)):
                    L = list()
                    for element in val:
                        L.append( _getValue(element) )
                    return L
                elif isinstance(val, dict):                
                    return Struct(val)
                else:
                    pass # leave it
            
            # Copy all keys in the dict that are not methods
            for key in a_dict:    
                if not _isvalidname(key):                    
                    print("Ignoring invalid key-name '%s'." % key)
                    continue
                val = a_dict[key]
                self[key] = _getValue(val)
    
    
    def __getitem__(self, key):
        # Name ok?
        key2 = _isvalidname(key)
        if not key:
            raise KeyError("Trying to get invalid name '%s'." % key)
        # Name exists?
        if not key in self.__dict__:
            raise KeyError(str(key))
        # Return
        return self.__dict__[key]
    
    
    def __setitem__(self, key, value):
        # Name ok?
        key2 = _isvalidname(key)
        if not key2:
            raise KeyError("Trying to set invalid name '%s'." % key)
        # Set
        self.__dict__[key] = value
    
    
    def __iter__(self):
        """ Returns iterator over keys. """
        return self.__dict__.__iter__()
   
    
    def __delitem__(self, key):
        return self.__dict__.__delitem__(key)
    
    
    def __len__(self):
        """ Return amount of fields in the Struct object. """
        return len(self.__dict__)
    
    def __add__(self, other):
        """ Enable adding two structs by combining their elemens. """
        s = Struct()
        s.__dict__.update(self.__dict__)
        s.__dict__.update(other.__dict__)
        return s
    
    def __eq__(self, other):
        return not _not_equal(self, other)
    
    def __repr__(self):
        """ Short string representation. """
        return "<SSDF struct instance with %i elements>" % len(self)
    
    def __str__(self):
        """ Long string representation. """
        
        # Get alignment value
        c = 0
        for key in self:
            c = max(c, len(key))
        
        # How many chars left (to print on less than 80 lines)
        charsLeft = 79 - (c+4) # 2 spaces and ': '
        
        s = 'Elements in SSDF struct:\n'
        for key in self:
            if key.startswith("__"):
                continue
            tmp = "%s" % (key)
            value = self[key]
            valuestr = repr(value)
            if len(valuestr)>charsLeft or '\n' in valuestr:
                typestr = str(type(value))[7:-2]
                if np and isinstance(value,np.ndarray):
                    shapestr = _shapeString(value)
                    valuestr = "<array %s %s>" %(shapestr,str(value.dtype))
                elif isinstance(value, basestring):
                    valuestr = valuestr[:charsLeft-3] + '...'
                    #valuestr = "<string with length %i>" % (typestr, len(value))
                else:
                    valuestr = "<%s with length %i>" % (typestr, len(value))
            s += tmp.rjust(c+2) + ": %s\n" % (valuestr)
        return s


class VirtualArray(object):
    """ VirtualArray
    
    A VirtualArray represents an array when numpy is not available.
    This enables preserving the array when saving back a loaded dataset.
    
    """
    def __init__(self, shape, dtype, data):
        self.shape = tuple(shape)
        self.dtype = dtype
        self.data = data
    
    def tostring(self):
        return self.data
    
    @property
    def size(self):
        if self.shape:
            return reduce( lambda a,b:a*b, self.shape)
        else:
            return 1


## File (like) objects

class _VirtualFile:
    """ _VirtualFile(bb=None)
    
    Wraps a bytes instance or string instance to provide a file-like 
    interface. Also represents a file like object to which bytes or strings
    can be written, and the resulting string/bytes can be obtained using 
    get_bytes(), get_text(), or get_text_as_bytes().
    
    """
    def __init__(self, bb=None):
        # For reading
        self._bb = bb
        self._fp = 0
        # For writing
        self._parts = []
    
    def read(self, n):
        i1 = self._fp
        self._fp = i2 = self._fp + n
        return self._bb[i1:i2]
    
    def write(self, data):
        self._parts.append(data)
    
    def close(self):
        pass
    
    def get_bytes(self):
        return bytes().join(self._parts)

    def get_text_as_bytes(self):
        parts = [self._parts.encode('utf-8')]
        return bytes().join(parts)
    
    def get_text(self):
        return str().join(self._parts)


class _CompressedFile:
    """ _CompressedFile(file, header)
    
    Wraps a file object to transparantly support reading and writing
    data from/to a compressed file. 
    
    Data is compressed in partitions of say 1MB. A partition in the file
    consists of a small header and a body. The header consists of 4 bytes
    representing the body's length (little endian unsigned 32 bit int).
    The body consists of bytes compressed using DEFLATE (i.e. zip).
    
    """
    
    def __init__(self, f, header):
        
        # Store file
        self._file = f
        
        # For reading
        self._buffer = bytes()
        self._bp = 0 # buffer pointer
        
        # For writing
        self._parts = []
        self._pp = 0 # parts pointer (is more like a counter)
        
        # Process header
        try:
            header_ok = self._check_header(header)
        except Exception:
            # Write mode
            self._write_header(header)
        else:
            # Read mode
            if not header_ok:
                raise ValueError('Given file does not have the right header.')
    
    
    def _check_header(self, header):
        bb1 = header.encode('utf-8')
        bb2 = self._file.read(len(bb1))
        if bb1 == bb2:
            return True
        else:
            return False
    
    
    def _write_header(self, header):
        bb1 = header.encode('utf-8')
        self._file.write(bb1)
    
    
    def _read_new_partition(self):
        """ _read_new_partition()
        
        Returns the data in the next partition.
        Returns false if no new partition is available.
        
        """
        
        # Get bytes and read partition length
        # If eof, return True
        bb = self._file.read(4)
        if not bb:
            self._buffer = bytes()
            self._bp = 0
            return False
        n, = struct.unpack(_PARTITION_LEN_FMT, bb)
        
        # Read partition and decompress
        bb = self._file.read(n)
        data = zlib.decompress(bb)
        del bb
        
        # Done
        return data
    
    
    def _write_new_partition(self):
        """ _write_new_partition()
        
        Compress the buffered data and write to file. Reset buffer.
        
        """
        
        # Get data
        data = bytes().join(self._parts)
        
        # Reset buffer
        self._parts = []
        self._pp = 0
        
        # Compress and write
        bb = zlib.compress(data)
        del data
        header = struct.pack(_PARTITION_LEN_FMT, len(bb))
        self._file.write(header)
        self._file.write(bb)
    
    
    def read(self, n):
        """ read(n)
        
        Read n bytes. Partitions are automatically decompressed on the fly.
        If the end of the file is reached, raises StopIteration.
        
        """
        
        # Get bytes in buffer
        bytes_in_buffer = len(self._buffer) - self._bp
        
        if bytes_in_buffer < n:
            # Read partitions untill we have enough
            
            # Prepare
            localBuffer = [self._buffer[self._bp:]]
            bufferCount = len(localBuffer[0])
            
            # Collect blocks of data
            while bufferCount < n:
                partition = self._read_new_partition()
                if partition:
                    localBuffer.append(partition)
                    bufferCount += len(partition)
                else:
                    raise StopIteration
            
            # Update buffer
            offset = len(partition) - (bufferCount - n)
            self._bp = offset
            self._buffer = partition
            
            # Truncate last block and get data
            localBuffer[-1] = partition[:offset]
            data = bytes().join(localBuffer)
        
        else:
            # Get data from current partition
            i1 = self._bp
            self._bp = i2 = i1 + n
            data = self._buffer[i1:i2]
        
        return data
    
    
    def read_number(self):
        n, = struct.unpack(_SMALL_NUMBER_FMT, self.read(1))
        if n == 255:
            n, = struct.unpack(_LARGE_NUMBER_FMT, self.read(8))
        return n
    
    
    def write_number(self, n):
        if n < 255:
            self.write( struct.pack(_SMALL_NUMBER_FMT, n) )
        else:
            self.write( struct.pack(_SMALL_NUMBER_FMT, 255) )
            self.write( struct.pack(_LARGE_NUMBER_FMT, n) )
    
    
    def write(self, data):
        """ write(data)
        
        Write data. The data is buffered until the accumulated size
        exceeds the partition size. When this happens, the data is compressed
        and written to the real underlying file/data.
        
        """
        
        # Get how many bytes we have beyond _PARTITION_SIZE
        i = (self._pp + len(data)) - _PARTITION_SIZE 
        
        if i > 0:
            # Add portion to buffer, store remainder
            self._parts.append(data[:i])
            data = data[i:]
            # Write the buffer away and reset buffer
            self._write_new_partition()
        
        # Add data to buffer
        self._parts.append(data)
        self._pp += len(data)
    
    
    def flush(self):
        """ flush()
        
        After the last write, use this to compress and write
        the last partition.
        
        """
        self._write_new_partition()


## Reader and writer classes

class _SSDFReader:
    
    def build_tree(self, root, blocks):
        """ build_tree(root, blocks)
        
        Build up the tree using the indentation information in the blocks.
        The tree is build up from the given root.
        
        """
        tree = [root]
        for block in blocks:
            # Select leaf in tree
            while block._indent <= tree[-1]._indent:
                tree.pop() 
            # Append (to object and to simple tree structure)
            tree[-1]._children.append(block)        
            tree.append(block)
    
    
    def read_binary_blocks(self, f):
        """ read_binary_blocks(f)
        
        Given a file, creates the block instances. 
        This is a generator function.
        
        """
        count = 0
        while True:
            count += 1
            
            # Get type. If no bytes left, we're done
            try:
                type_id, = struct.unpack(_TYPE_FMT, f.read(1))
                type_id = type_id.decode('utf-8')
            except StopIteration:
                break
            
            # Get indentation
            indent = f.read_number()
            
            # Get name
            name_len = f.read_number()
            if name_len:
                name = f.read(name_len).decode('utf-8')
            else:
                name = None
            
            # Get data
            data_len = f.read_number()
            data = f.read(data_len)
            
            # Create block instance
            yield _BinaryBlock(indent, count, name, type_id, data=data)
    
    
    def read_text_blocks(self, lines):
        """ read_text_blocks(lines)
        
        Given a list of Unicode lines, create the block instances. 
        This is a generator function.
        
        """
        for i in range(len(lines)):
            line = lines[i]
            count = i+1
            
            # Strip line
            line2 = line.lstrip()
            
            # Skip comments and empty lines        
            if len(line2)==0 or line2[0] == '#':        
                continue 
            
            # Find the indentation
            indent = len(line) - len(line2)
            
            # Split name and value using a regular expression
            m = re.search("^\w+? *?=", line2)
            if m:
                i = m.end(0)
                name = line2[:i-1].strip()
                data = line2[i:].lstrip()
            else:
                name = None
                data = line2
            
            # Create block instance
            # Note that type is inferred from the raw data
            yield _TextBlock(indent, count, name, data=data)
    
    
    def binary_to_struct(self, file_or_bytes):
        """ binary_to_struct(file_or_bytes)
        
        Given a file or bytes, convert it to a struct by reading the
        blocks, building the tree and converting each block to its
        Python object.
        
        """
        
        # Get file
        if isinstance(file_or_bytes, bytes):
            f = _VirtualFile(file_or_bytes)
        else:
            f = file_or_bytes
        
        # Create compressed file to read from
        fc = _CompressedFile(f, header='BSDF')
        
        # Create blocks and build tree
        root = _BinaryBlock(-1, -1, type='D')
        block_gen = self.read_binary_blocks(fc)
        self.build_tree(root, block_gen)
        
        # Convert to real objects and return
        return root.to_object()
    
    
    def text_to_struct(self, file_or_string):
        """ text_to_struct(file_or_string)
        
        Given a file or string, convert it to a struct by reading the
        blocks, building the tree and converting each block to its
        Python object.
        
        """
        
        # Get lines
        if isinstance(file_or_string, basestring):
            lines = file_or_string.splitlines()
        else:
            lines = file_or_string.readlines()
            lines = [line.decode('utf-8') for line in lines]
        
        # Create blocks and build tree
        root = _TextBlock(-1, -1, data='dict:')
        block_gen = self.read_text_blocks(lines)
        self.build_tree(root, block_gen)
        
        # Convert to real objects and return
        return root.to_object()



class _SSDFWriter:
 
    def flatten_tree(self, block, sort=False):
        """ flatten_tree(block, sort=False)
        
        Returns a flat list containing the given block and
        all its children.
        
        If sort is True, packs blocks such that the data
        structures consisting of less blocks appear first. 
        
        """
        
        # Get list of strings for each child
        listOfLists = []
        for child in block._children:            
            childList = self.flatten_tree(child, sort)
            listOfLists.append( childList )
        
        # Sort by length
        if sort:
            listOfLists.sort(key=len)
        
        # Produce flat list
        flatList = [block]
        for childList in listOfLists:
            flatList.extend(childList)
        
        # Done
        return flatList
    
    
    def write_binary_blocks(self, blocks, f):
        """ write_binary_blocks(blocks, f)
        
        Writes the given blocks to a binary file.
        
        """
        
        # Skip first, it is the root object
        for block in blocks[1:]:
            
            # Write type.
            f.write(struct.pack(_TYPE_FMT, block._type.encode('utf-8')))
            
            # Write indentation
            f.write_number(block._indent)
            
            # Write name
            if block._name:
                name = block._name.encode('utf-8')
                f.write_number(len(name))
                f.write(name)
            else:
                f.write_number(0)
            
            # Write data
            if isinstance(block._data, list):
                data_len = sum([len(d) for d in block._data])
                f.write_number(data_len)
                for part in block._data:
                    f.write(part)
            else:
                data_len = len(block._data)
                f.write_number(data_len)
                f.write(block._data)
    
    
    def write_text_blocks(self, blocks):
        """ write_text_blocks(blocks)
        
        Converts the given blocks to a list of string lines.
        
        """
        # Skip first, it is the root object
        lines = []
        for block in blocks[1:]:
            
            # Write indent
            line = str(" ") * block._indent
            
            # Write name
            if block._name:
                line += "%s = " % block._name
            
            # Write data
            line += block._data
            lines.append(line)
        
        return lines
    
    
    def struct_to_binary(self, object, f=None):
        """ struct_to_binary(object, f=None)
        
        Serializes the given struct. If a file is given, writes bytes
        to that file, otherwise returns a bytes instance.
        
        """
        
        # Check input
        if f is None:
            f = _VirtualFile()
            return_bytes = True
        else:
            return_bytes = False
        
        # Make compressed file
        fc = _CompressedFile(f, header='BSDF')
        
        # Create block object
        root = _BinaryBlock.from_object(-1, bytes(), object)
        
        # Collect blocks and write
        blocks = self.flatten_tree(root)
        self.write_binary_blocks(blocks, fc)
        fc.flush()
        
        # Return?
        if return_bytes:
            return f.get_bytes()
    
    
    def struct_to_text(self, object, f=None):
        """ struct_to_text(object, f=None)
        
        Serializes the given struct. If a file is given, writes 
        (utf-8 encoded)text to that file, otherwise returns a string.
        
        """
        # Create block object
        root = _TextBlock.from_object(-1, '', object)
        
        # Collect blocks and convert to lines
        blocks = self.flatten_tree(root)
        lines = self.write_text_blocks(blocks)
        
        # Write to file or return as a string
        if f is None:
            return '\n'.join(lines)
        else:
            NL = '\n'.encode('utf-8')
            for line in lines:
                f.write(line.encode('utf-8'))
                f.write(NL)


class _Block:
    """ _Block
    
    A block represents a data element. This is where the conversion from 
    Python objects to text/bytes and vice versa occurs.
    
    A block is a line in a text file or a piece of data in a binary file.
    A block contains all information about indentation, name, and value
    of the data element that it represents. The raw representation of its
    value is refered to as 'data'.
    
    """
    
    def __init__(self, indent, blocknr, name=None, type=None, data=None):
        self._indent = indent
        self._blocknr = blocknr # for producing usefull read error messages
        
        self._name = name
        self._type = type # used by binary only        
        self._data = data # the raw data, bytes or string
        
        self._children = [] # used only by dicts and lists
    
    
    @classmethod
    def from_object(cls, indent, name, value):
        
        # Instantiate a block
        self = cls(indent, -1, name)
        
        # Set object's data
        if value is None:
            self._from_none()        
        elif ClassManager.is_registered_class(value.__class__):
            self._from_dict( value.__to_ssdf__() )
        elif isinstance(value, _INT_TYPES):
            self._from_int(value)
        elif isinstance(value, _FLOAT_TYPES):
            self._from_float(value)
        elif isinstance(value, bool):
            self._from_int(int(value))
        elif isinstance(value, basestring):
            self._from_unicode(value)
        elif np and isinstance(value, np.ndarray):
            self._from_array(value)
        elif isinstance(value, VirtualArray):
            self._from_array(value)
        elif isinstance(value, dict) or isstruct(value):
            self._from_dict(value)
        elif isinstance(value, (list, tuple)):
            self._from_list(value)
        else:
            # We do not know            
            self._from_none()
            tmp = repr(value)
            if len(tmp) > 64:
                tmp = tmp[:64] + '...'
            print("SSDF: unknown object: " + tmp) 
        
        # Done
        return self


class _BinaryBlock(_Block):
    
    
    def to_object(self):
        # Determine what type of object we are dealing with using the
        # type id.
        type = self._type
        if type=='i':   return self._to_int()
        elif type=='f': return self._to_float()
        elif type=='u': return self._to_unicode()
        elif type=='a': return self._to_array()
        elif type=='L': return self._to_list()
        elif type=='D': return self._to_dict()
        elif type=='n': return self._to_none()
        else:
            print("SSDF: invalid type in block %i." % self._blocknr)
            return None
    
    
    def _from_none(self, value=None):
        self._type = 'n'
        self._data = bytes()
    
    def _to_none(self):
        return None
    
    
    def _from_int(self, value):
        self._type = 'i'
        self._data = struct.pack('<q', int(value))
    
    def _to_int(self):
        return struct.unpack('<q', self._data)[0]
    
    
    def _from_float(self, value):
        self._type = 'f'
        self._data = struct.pack('<d', float(value))
    
    def _to_float(self):
        return struct.unpack('<d', self._data)[0]
    
    
    def _from_unicode(self, value):
        self._type = 'u'
        self._data = value.encode('utf-8')
    
    def _to_unicode(self):
        return self._data.decode('utf-8')
    
    
    def _from_array(self, value):
        self._type = 'a'
        # Write shape
        bb = struct.pack('<b', len(value.shape))
        for s in value.shape:
            bb += struct.pack('<Q', s)
        # Write dtype
        dtype_bb = str(value.dtype).encode('utf-8')
        bb += struct.pack('<b', len(dtype_bb))
        bb += dtype_bb
        # Write header + data
        # tostring() returns bytes, not a string on py3k
        self._data = [bb, value.tostring()] 
    
    def _to_array(self):
        # Get shape
        shape = []
        ndim, = struct.unpack('<b', self._data[0:1])
        i = 1
        for j in range(ndim):
            s, = struct.unpack('<Q', self._data[i:i+8])
            shape.append(s)
            i += 8
        # Get dtype
        dtypestr_len, = struct.unpack('<b', self._data[i:i+1])
        i += 1
        dtypestr = self._data[i:i+dtypestr_len].decode('utf-8')
        i += dtypestr_len
        # Create numpy array or Virtual array
        if not np:
            return VirtualArray(shape, dtypestr, self._data[i:])
        else:
            if i < len(self._data):                
                value = np.frombuffer(self._data, dtype=dtypestr, offset=i)
            else:
                value = np.array([], dtype=dtypestr)
            if np.prod(shape) == value.size:
                value.shape = tuple(shape)
            else:
                print("SSDF: prod(shape)!=size on line %i."%self._blocknr)
            return value
    
    
    def _from_dict(self, value):
        self._type = 'D'
        self._data = bytes()
        
        # Process children        
        for key in value:
            # Skip all the buildin stuff
            if key.startswith("__"):
                continue
            # We have the key, go get the value!
            val = value[key]
            # Skip methods, or anything else we can call
            if hasattr(val,'__call__') and not hasattr(val, '__to_ssdf__'): 
                # Note: py3.x does not have function callable
                continue
            # Add!
            subBlock = _BinaryBlock.from_object(self._indent+1, key, val)
            self._children.append(subBlock)
    
    def _to_dict(self):
        value = Struct()
        for child in self._children:
            val = child.to_object()
            if child._name:
                value[child._name] = val
            else:
                print("SSDF: unnamed element in dict in block %i."%child._blocknr)
        # Make class instance?
        if _CLASS_NAME in value:
            className = value[_CLASS_NAME]
            if className in _registered_classes:
                value = _registered_classes[className].__from_ssdf__(value)
            else:
                print("SSDF: class %s not registered." % className)
        # Done
        return value
    
    
    
    def _from_list(self, value):
        self._type = 'L'
        self._data = bytes()
        
        # Process children
        for element in value:
            # Add element as subblock
            subBlock = _BinaryBlock.from_object(self._indent+1, None, element)
            self._children.append(subBlock)   
    
    def _to_list(self):
        value = []
    
        for child in self._children:
            val = child.to_object()
            if child._name:
                print("SSDF: named element in list in block %i."%child._blocknr)
            else:
                value.append(val)
        return value


class _TextBlock(_Block):
    
    def to_object(self):
        
        # Determine what type of object we're dealing with by reading
        # like a human.
        data = self._data
        if not data:
            print('SSDF: no value specified at line %i.' % self._blocknr)
        elif data[0] in '-.0123456789':
            if '.' in data: return self._to_float()
            else: return self._to_int()
        elif data[0] == "'":
            return self._to_unicode()
        elif data.startswith('array'):
            return self._to_array()
        elif data.startswith('dict:'):  
            return self._to_dict()
        elif data.startswith('list:') or  data[0] == '[':
            return self._to_list()
        elif data.startswith('Null') or data.startswith('None'):
            return self._to_none()
        else:
            print("SSDF: invalid type on line %i." % self._blocknr)
            return None
    
    
    def _from_none(self, value=None):
        self._data = 'Null'
    
    def _to_none(self):
        return None
    
    
    def _from_int(self, value):
        self._data = '%i' % int(value)
    
    def _to_int(self):
        # First remove any comments
        line = self._data
        i = line.find('#')
        if i>0:
            line = line[:i].strip()
        try:
            return int(line)
        except Exception:
            print("SSDF: could not parse integer on line %i."%self._blocknr)
            return None
    
    
    def _from_float(self, value):
        # Use general specifier with a very high precision.
        # Any spurious zeros are automatically removed. The precision
        # should be sufficient such that any numbers saved and loaded 
        # back will have the exact same value again. 20 seems plenty.
        self._data = '%0.20g' % value
    
    def _to_float(self):
        # First remove any comments
        line = self._data
        i = line.find('#')
        if i>0:
            line = line[:i].strip()
        try:
            return float(line)
        except Exception:
            print("SSDF: could not parse float on line %i."%self._blocknr)
            return None
    
    
    def _from_unicode(self, value):
        value = value.replace('\\', '\\\\')
        value = value.replace('\n','\\n')
        value = value.replace('\r','\\r')
        value = value.replace("'", "\\'")
        self._data = "'" + value + "'"
    
    def _to_unicode(self):
        # Encode double slashes
        line = self._data.replace('\\\\','0x07') # temp
        
        # Find string using a regular expression
        m = re.search("'.*?[^\\\\]'|''", line)
        if not m:
            print("SSDF: string not ended correctly on line %i."%self._blocknr)
            return None # return not-a-string
        else:
            line = m.group(0)[1:-1]
        
        # Decode stuff        
        line = line.replace('\\n','\n')
        line = line.replace('\\r','\r')
        line = line.replace("\\'","'")
        line = line.replace('0x07','\\')
        return line
    
    
    def _from_dict(self, value):
        self._data = "dict:"
        # Process children        
        for key in value:
            # Skip all the buildin stuff
            if key.startswith("__"):
                continue                
            # We have the key, go get the value!
            val = value[key]
            # Skip methods, or anything else we can call
            if hasattr(val,'__call__') and not hasattr(val, '__to_ssdf__'): 
                # Note: py3.x does not have function callable
                continue
            # Add!
            subBlock = _TextBlock.from_object(self._indent+1, key, val)
            self._children.append(subBlock)
    
    def _to_dict(self):
        value = Struct()
        for child in self._children:
            val = child.to_object()
            if child._name:
                value[child._name] = val
            else:
                print("SSDF: unnamed element in dict on line %i."%child._blocknr)
        # Make class instance?
        if _CLASS_NAME in value:
            className = value[_CLASS_NAME]
            if className in _registered_classes:
                value = _registered_classes[className].__from_ssdf__(value)
            else:
                print("SSDF: class %s not registered." % className)
        # Done
        return value
    
    
    def _from_list(self, value):
        # Check whether this is a "small list"
        isSmallList = True
        allowedTypes = _INT_TYPES+_FLOAT_TYPES+(basestring,)
        subBlocks = []
        for element in value:
            # Add element as subblock
            subBlock = _TextBlock.from_object(self._indent+1, None, element)
            subBlocks.append(subBlock)
            # Check if ok type
            if not isinstance(element, allowedTypes):
                isSmallList = False
        
        # Store list
        if isSmallList:
            elements = [subBlock._data.strip() for subBlock in subBlocks]
            self._data = '[%s]' % (', '.join(elements))
        else:            
            self._data = "list:"
            for subBlock in subBlocks:
                self._children.append(subBlock)        
    
    def _to_list(self):
        value = []
        if self._data[0] == 'l': # list:
            
            for child in self._children:
                val = child.to_object()
                if child._name:
                    print("SSDF: named element in list on line %i."%child._blocknr)
                else:
                    value.append(val)
            return value
            
        else:
            # [ .., .., ..]
            return self._to_list2()
    
    
    def _to_list2(self):
        i0 = 1
        pieces = []
        inString = False
        escapeThis = False
        line = self._data
        for i in range(1,len(line)):
            if inString:
                # Detect how to get out
                if escapeThis:
                    escapeThis = False
                    continue
                elif line[i] == "\\":
                    escapeThis = True
                elif line[i] == "'":
                    inString = False
            else:
                # Detect going in a string, break, or end
                if line[i] == "'":
                    inString = True
                elif line[i] == ",":
                    pieces.append(line[i0:i])
                    i0 = i+1
                elif line[i] == "]":
                    piece = line[i0:i]
                    if piece.strip(): # Do not add if empty
                        pieces.append(piece)
                    break
        else:
            print("SSDF: one-line list not closed correctly on line %i." % self._blocknr)
        
        # Cut in pieces and process each piece
        value = []
        for piece in pieces:
            lo = _TextBlock(self._indent, self._blocknr, data=piece.strip())
            value.append( lo.to_object() )
        return value
    
    
    def _from_array(self, value):
        if value.shape:
            size = reduce( lambda a,b:a*b, value.shape)
        else:
            size = 1 # Scalar
        shapestr = _shapeString(value)
        dtypestr = str(value.dtype)
            
        if value.size<33 and not isinstance(value, VirtualArray):
            # Small enough to print
            # Get values in list (we need to ravel)
            if 'int' in dtypestr:
                elements = ['%i' % v for v in value.ravel()]
            else:
                elements = ['%0.20g' % v for v in value.ravel()]
            if elements:
                elements.append('') # Make sure there's at least one komma
            # Build string
            self._data = "array %s %s %s" % (shapestr, dtypestr, 
                ", ".join(elements) )
        
        else:
            # Store binary
            # Get raw data
            data = value.tostring()
            # In blocks of 1MB, compress and encode
            BS = 1024*1024
            texts = []
            i=0
            while i < len(data):
                block = data[i:i+BS]
                blockc = zlib.compress(block)
                text = base64.encodebytes(blockc).decode('utf-8')
                texts.append( text.replace("\n","") )
                i += BS
            text = ';'.join(texts)
            self._data = "array %s %s %s" % (shapestr, dtypestr, text)
    
    def _to_array(self):
        
        # Split
        tmp = self._data.split(' ',3)
        if len(tmp) < 4:
            print("SSDF: invalid array definition on line %i."%self._blocknr)
            return None
        # word1 = tmp[0] # says "array"
        word2 = tmp[1]
        word3 = tmp[2]
        word4 = tmp[3]
        
        # Determine shape and size
        try:
            shape = [int(i) for i in word2.split('x') if i]
        except Exception:
            print("SSDF: invalid array shape on line %i."%self._blocknr)
            return name, None
        if shape:
            size = reduce( lambda a,b:a*b, shape)
        else:
            size = 1 # Scalar 
        
        # Determine datatype 
        # Must use 1byte/char string in Py2.x, or numpy wont understand )
        dtypestr = simplestr(word3)
        if dtypestr not in _DTYPES.keys():
            print("SSDF: invalid array data type on line %i."%self._blocknr)
            return None
        
        # Stored as ASCII?         
        asAscii = ( word4.find(',', 0, 100) > 0 ) or ( word4.endswith(',') )
        
        # Get data
        if size==0:
            # Empty array
            data = bytes()
        
        elif asAscii:
            # Stored in ascii
            dataparts = []
            fmt = _DTYPES[dtypestr]
            for val in word4.split(','):
                if not val.strip():
                    continue
                try:
                    if 'int' in dtypestr:
                        val = int(val)
                    else:
                        val = float(val)
                    dataparts.append(struct.pack(fmt, val))
                except Exception:
                    if 'int' in dtypestr:
                        dataparts.append(struct.pack(fmt, 0))
                    else:
                        dataparts.append(struct.pack(fmt, float('nan')))
                        
            data = bytes().join(dataparts)
        
        else:
            # Stored binary
            # Get data: decode and decompress in blocks
            dataparts = []
            for blockt in word4.split(';'):                
                blockc = base64.decodebytes(blockt.encode('utf-8'))
                block = zlib.decompress(blockc)
                dataparts.append(block)
            data = bytes().join(dataparts)
        
        # Almost done ...
        if not np:
            # Make virtual array to allow saving it again
            return VirtualArray(shape, dtypestr, data)
        elif data:
            # Convert to numpy array
            value  = np.frombuffer(data, dtype=dtypestr )
            # Set and check shape
            if size == value.size:
                value.shape = tuple(shape)
            else:
                print("SSDF: prod(shape)!=size on line %i."%self._blocknr)
            return value
        else:
            # Empty numpy array
            return np.zeros(shape, dtype=dtypestr)
