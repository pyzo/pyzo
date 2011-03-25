# -*- coding: utf-8 -*-
#   Copyright (c) 2010, Almar Klein
#
#   This code is subject to the (new) BSD license:
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY 
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


""" MODULE Simple Structured Data Format.

SSDF is a format for storing structured (scientific) data.

Introduction
============
The goal of the format is to be easily readable by humans as well 
as computers. It is aimed for use in interpreted languages like 
Python or Matlab, but it can be used in any language that supports 
the seven datatypes listed below.

This is the Python implementation for reading, writing and using
such data structures. This module can be used in both python 2.x
and 3.x. If numpy is not installed, arrays cannot be read or written.

Elements in a data structure can be one of seven different data 
elements, of which the first two are a container element (which 
can be nested):
    * dictionary (an ssdf.Struct object in Python)
    * list (of elements with no name)
    * (Unicode) string
    * float scalar
    * int scalar
    * (numpy) array of any type and shape
    * Null (None)

Notes
=====
In Python, True and False are converted to 1 and 0 respectively. Tuples
are interpreted as lists, and scalar numpy arrays are interpreted as
scalars.

Usage
=====
  * s = ssdf.new() to create a new  Struct object
  * s = ssdf.load(path) to load structured data from a file 
  * s = ssdf.Struct(some_dict) to create a structure from a dict
  * ssdf.save(path,s) to save structured data to a file
  * ssdf.saves(s) and ssdf.loads(text) save/load to/from a string

Example
=======
import numpy as np
import ssdf
s = ssdf.new()
s.numbers = np.ones((3,2))
s.numbers2 = np.ones((4,9)) # more than 32 elements
s.notes = "This is an example"
s.files = ssdf.new()
s.files.filenames = ["one.txt","two.txt","three.txt"]
s.files.basedir = "c:/temp"
print(ssdf.saves(s)) # show in text

... will print ...

notes = 'This is an example'
numbers2 = array 4x9 float64 eJxjYACBD/YMozRWGgCcJSqd
numbers = array 3x2 float64 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
files = dict:
  basedir = 'c:/temp'
  filenames = ['one.txt', 'two.txt', 'three.txt']

More information
================
See http://code.google.com/p/ssdf/ for the full specification of the
standard and for more information.

This file and the SSDF standard are free for all to use (BSD license).
Copyright (C) 2010 Almar Klein. 

"""

import os, sys
import base64
import zlib
import re

# Try importing numpy
try:
    import numpy as np    
except ImportError:
    np = None

# Determine float and int types
if np:
    floatTypes = (float, np.float32, np.float64)
    intTypes = (int, np.int8,  np.int16,  np.int32,  np.int64, 
                    np.uint8, np.uint16, np.uint32, np.uint64)
else:
    floatTypes = (float,)
    intTypes = (int,)

# If version 2...
if sys.version_info[0] <= 2:
        simplestr = str
        bytes = str
        str = unicode
else:
    basestring = str
    simplestr = str

# To store other classes
PYTHON_CLASS_NAME = '_CLASS_NAME_'


## Registering classes

# Global dict with registered classes
_registered_classes = {}


def isCompatibleClass(cls):
    """ isCompatibleClass(cls)
    
    Returns True if the given class is SSDF-compatible.
    
    """
    return not isIncompatibleClass(cls)


def isIncompatibleClass(cls):    
    """ isIncompatibleClass(cls)
    
    Returns a string giving the reason why the given class 
    if not SSDF-compatible. If the class is compatible, this 
    function returns None.
    
    """
    if not hasattr(cls, '__to_ssdf__'):
        return 'class does not have __to_ssdf__ method'
    if not hasattr(cls, '__from_ssdf__'):
        return 'class does not have __from_ssdf__ classmethod'
    if not isinstance(cls, type):
        return 'class is not a type (does not inherit object on Python 2.x)'


def register_class(*args):
    """ register_class(class1, class2, class3, ...)
    
    Register one or more classes. Registered classes can be saved and 
    restored from ssdf. 
    
    A class needs to implement two methods to qualify for registration:
      * A method __to_ssdf__() that returns a ssdf.Stuct
      * A classmethod __from_ssdf__(s) that accepts an ssdf.Struct and creates
        an instance of that class.
    
    """
    for cls in args:
        incomp = isIncompatibleClass(cls)
        
        if incomp:
            raise ValueError('Cannot register class %s: %s.' % (cls.__name__, incomp))
        else:
            _registered_classes[cls.__name__] = cls


## The class

def isSsdfStruct(object):
    """ isSsdfStruct(object)
    
    Returns whether the given object is an ssdf struct. 
    
    Rather than using isinstance, this function checks the 
    class name and the module name in which it is defined. 
    That way, this function returns True also when the struct
    is from another ssdf module (for example in a subpackage).
    
    """
    
    if isinstance(object, Struct):
        return True
    else:
        # Get class name of dict
        c = object.__class__
        dictClassName = '%s.%s' % (c.__module__, c.__name__)
        # Check    
        return dictClassName.endswith('ssdf.Struct')


class Struct(object):
    """ Struct(dictionary=None) 
    
    A Struct object holds named data (syntactic sugar for a 
    dictionary). Attributes can be any of SSDF supported types, 
    including other Struct objects and lists.
    
    Elements can be added in two ways:
        * s.foo = 'bar'       # the object way
        * s['foo'] = 'bar'    # the dictionary way
    
    Iterating over the Struct object yields the names in the struct. 
    len(s) gives the number of elements in the struct.
    
    Note that the keys in the given dict should be valid names (invalid 
    keys are ignoired).
    
    """    

    def __init__(self, a_dict=None):
        
        # Plain struct?
        if a_dict is None:
            return
        
        
        
        if not isinstance(a_dict, (Struct, dict)) and not isSsdfStruct(a_dict):
            tmp = "Struct can only be initialized with a Struct or a dict."
            raise ValueError(tmp)
        else:
            # Try loading from object
            
            def _getValue(val):
                """ Get the value, as suitable for Struct. """
                if isinstance(val, (basestring,) + floatTypes + intTypes ):
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


def new():
    """ new()
    
    Create an empty struct object.     
    
    """
    return Struct()


def clear(struct_object):
    """ clear(struct_object)
    
    Clear all fields of the given struct object.
    
    """
    keys = [key for key in struct_object]
    for key in keys:
        del(struct_object.__dict__[key])


## STEP 1: file <--> text


def save(filename, struct_object, appName='ssdf.py', newline='\n'):
    """ save(filename, struct_object, app_name='ssdf.py', newline='\n')
    
    Save given struct object to the given filename.
    The app_name is mentioned on the first (commented) line.
    
    """
    
    # Get absolute filename
    filename = os.path.abspath(filename)
    
    # Get text and convert to bytes
    header =  '# This Simple Structured Data Format (SSDF) file was '
    header += 'created from Python by %s.' % appName
    text = saves(struct_object)
    text = header + newline + text.replace('\n',newline) + newline
    byts = text.encode('UTF-8')
    
    # Store...
    fid = open(filename,'wb')
    try:
        fid.write( byts )
    except Exception:
        raise
    finally:
        fid.close()


def load(filename):
    """ load(filename)
    
    Load a struct object from the given filename. 
    
    """        
    filename = os.path.abspath(filename)        
    if not os.path.isfile(filename):
        raise IOError("The specified file does not exist: "+filename)
    
    # open file and read data
    f = open(filename,'rb')
    try:
        byts = f.read()
    except Exception:
        raise
    finally:        
        f.close()
    
    # parse!
    text = byts.decode('UTF-8')
    return loads(text)


def update(filename, struct_object, appName='ssdf.py', newline='\n'):
    """ update(filename, struct_object, appName='ssdf.py', newline='\n')
    
    Update an existing ssdf file, inserting and replacing any 
    new values in the existing structure. 
    
    """
    
    # Load existing struct
    s = load(filename)
    
    # Insert stuff
    def insert(ob1,ob2):
        for name in ob2:
            if ( name in ob1 and isSsdfStruct(ob1[name]) and 
                                 isSsdfStruct(ob2[name]) ):
                insert(ob1[name], ob2[name])
            else:
                ob1[name] = ob2[name]
    insert(s, struct_object)
    
    # Save
    save(filename, s, appName, newline)


def copy(struct_object):
    """ copy(struct)
    
    Get a copy of the given struct object. 
    (Same as "ssdf.Struct(struct_object).")
    
    """
    return Struct(struct_object)


## STEP 2: text <--> structured lines


def saves(struct_object):
    """ saves(struct_object)
    
    Write the given struct object to a (Unicode) string.  
    
    """
    
    base = _toString('', struct_object, -2)  # negative indent
    strings = _pack(base)
    return "\n".join(strings[1:])
    

def _pack(lineObject):
    """ _pack(lineObject)
    
    Pack the lines such that the structures with less lines appear first. 
    
    """
    
    # Get list of strings for each child
    listOfLists = []
    for child in lineObject.children:            
        childList = _pack(child)
        listOfLists.append( childList )
    
    # Sort by length
    listOfLists.sort(key=len)
    
    # Produce flat list
    flatList = [lineObject.line]
    for childList in listOfLists:
        flatList.extend(childList)
    
    # Done
    return flatList


def loads(text):    
    """ load(text)
    
    Load struct object from the given (Unicode) string.  
    
    """
    
    base = _LineObject(-2, "", "dict:", -1)
    tree = [base]
    
    # Pre-process
    text = text.replace('\t','  ')
    text = text.replace('\r\n','\n').replace('\r','\n')
    
    # Setup structure
    lines = text.split("\n")
    for linenr in range(len(lines)):
        line = lines[linenr]
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
            value = line2[i:].lstrip()
        else:
            name = ''
            value = line2
        
        # Produce line object
        new = _LineObject(indent, name, value, linenr+1)
        
        # Select leaf in tree
        while not indent > tree[-1].indent:
            tree.pop()
        
        # Append (to object and to simple tree structure)
        tree[-1].children.append(new)        
        tree.append(new)
    
    # Do the parse pass
    name, value = _fromString(base)
    return value

    
    
## STEP 3: (structured) lines <--> structured data


class _LineObject:
    def __init__(self, indent=-2, name='', value='', linenr=-1):        
        self.indent = indent
        self.name = name
        self.value = value # as a string
        self.linenr = linenr
        self.children = []
    

def _toString(name, value, indent):
    """ Make a Line object from the name and value.
    Name can be ''. """
    
    lineObject = _LineObject() 
    
    # Parse name
    lineObject.line = str(" ") * indent
    if name:
        lineObject.line += "%s = " % name
    
    # Parse value
    
    # None
    if value is None:
        lineObject.line += "Null"
    
    # User specific 
    elif isCompatibleClass(value.__class__):
        
        # Create struct
        s = value.__to_ssdf__()        
        s[PYTHON_CLASS_NAME] = value.__class__.__name__
        
        # Make string
        lineObject = _toString(name, s, indent)
    
    # Struct
    elif isinstance(value, dict) or isSsdfStruct(value):            
        lineObject.line += "dict:"
        
        # Process children        
        for key in value:
            # Skip all the buildin stuff
            if key[0:2] == "__":
                continue                
            # We have the key, go get the value!
            val = value[key]
            # Skip methods, or anything else we can call
            if hasattr(val,'__call__') and not hasattr(val, '__to_ssdf__'): 
                # Note: py3.x does not have function callable
                continue
            # Add!
            tmp = _toString(key, val, indent+2)
            lineObject.children.append(tmp)
    
    # Lists
    elif isinstance(value, (list, tuple)):
        # Check whether this is a "small list"
        isSmallList = False
        for element in value:
            if not isinstance(element, intTypes+floatTypes+(basestring,)):
                break
        else:
            isSmallList = True
        # Store list
        if isSmallList:
            elements = [_toString("", element, 0).line.strip() for element in value]
            lineObject.line += '[%s]' % ', '.join(elements)
        else:            
            lineObject.line += "list:"
            for element in value:
                tmp = _toString("", element, indent+2)
                lineObject.children.append(tmp)                
    
    # Base types
    elif isinstance(value,basestring):
        value = value.replace('\\', '\\\\')
        value = value.replace('\n','\\n')
        value = value.replace('\r','\\r')
        value = value.replace("'", "\\'")                
        lineObject.line += "'" + value + "'"
    
    elif isinstance(value, bool):
        lineObject.line += '%i' % int(value)    
    elif isinstance(value,intTypes):
        lineObject.line += '%i' % int(value)
    elif isinstance(value,floatTypes):
        lineObject.line += '%0.12f' % value
    
    # Array types
    elif np and isinstance(value,np.ndarray):
        
        ndim = len(value.shape)
        if ndim == 0:
            if value.dtype in [np.float32, np.float64]:
                lineObject.line += str(value)
            else:
                lineObject.line += str(value)
        
        elif value.size<33:
            # Small enough to print, but shape required
            shapestr = _shapeString(value)
            dtypestr = str(value.dtype)
            # Get values in list (we need to ravel)
            elements = [str(v) for v in value.ravel()]
            # Build string
            lineObject.line += "array %s %s %s" % (shapestr, dtypestr, 
                ", ".join(elements) )
        
        else:
            # Get attributes
            shapestr = _shapeString(value)
            dtypestr = str(value.dtype)
            # Get raw data
            data = value.tostring()
            # In blocks of 1MB, compress and encode
            BS = 1024*1024
            texts = []
            i=0
            while i < len(data):
                block = data[i:i+BS]
                blockc = zlib.compress(block)
                text = base64.encodestring(blockc)
                texts.append( text.replace("\n","") )
                i += BS
            # Combine blocks and store
            text = ';'.join(texts)
            lineObject.line += "array %s %s %s" % (shapestr, dtypestr, text)
    
    elif isinstance(value, UnloadedArray):
        tmp = "Cannot save unloaded arrays (need numpy)!"
        raise ValueError(tmp)
    
    else:
        # If anything else did not work, we have an unkown object I guess!
        raise Exception("Unknown object: " + str(value)) 
    
    # Done
    return lineObject


def _fromString(lineObject):
    """ _fromString(lineObject)
    
    Parse the element from the single string. 
    
    A line looks like this:
    [whitespace][name][][=][][value][][comment]
    
    where [] represents optional whitespace and the name
    must consist of only proper characters.
    
    """
    
    # Init (the line should be the whole line)    
    indent = lineObject.indent
    name = lineObject.name
    line = lineObject.value
    linenr = lineObject.linenr
    
    # The variable line is the part from the '=' (and lstripped)
    # note that there can still be a comment on the line!
    
    # Parse value
    
    if line == '':
        # An empty line
        return name, None
    
    elif line.startswith('Null') or line.startswith('None'):
        return name, None
    
    elif line.startswith('dict:'):        
        # Create struct
        value = Struct()
        for child in lineObject.children:
            key, val = _fromString(child)
            if key:
                value[key] = val
            else:
                tmp = child.linenr
                print("SSDF Warning: unnamed element in dict on line %i."%tmp)
        # Make class instance?
        if PYTHON_CLASS_NAME in value:
            className = value[PYTHON_CLASS_NAME]
            if className in _registered_classes:
                value = _registered_classes[className].__from_ssdf__(value)
            else:
                print("SSDF Warning: class %s not registered." % className)
        # Return
        return name, value
    
    elif line.startswith('list:'):
        value = []
        for child in lineObject.children:
            key, val = _fromString(child)
            if key:
                tmp = child.linenr
                print("SSDF Warning: named element in list on line %i."%tmp)
            else:
                value.append(val)
        return name, value
    
    elif line[0] == '[':
        
        # Smart cutting, taking strings into account
        i0 = 1
        pieces = []
        inString = False
        escapeThis = False
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
            print("SSDF Warning: One-line list not closed correctly.")
        
        # Cut in pieces and process each piece
        value = []
        for piece in pieces:
            lo = _LineObject(value=piece.strip(), linenr=lineObject.linenr)
            value.append( _fromString(lo)[1] )
        return name, value
    
    elif line[0] == "$":
        # Old string syntax
        line = line[1:].replace('\\\\','0x07') # temp
        line = line.replace('\\n','\n')
        line = line.replace('\\r','\r')
        line = line.replace('0x07','\\')
        return name, line
    
    elif line[0] == "'":
        # String
        
        # Encode double slashes
        line = line.replace('\\\\','0x07') # temp
        
        # Find string using a regular expression
        m = re.search("'.*?[^\\\\]'|''", line)
        if not m:
            print("SSDF Warning: string not ended correctly on line %i."%linenr)
            return name, None
        else:
            line = m.group(0)[1:-1]
        
        # Decode stuff        
        line = line.replace('\\n','\n')
        line = line.replace('\\r','\r')
        line = line.replace("\\'","'")
        line = line.replace('0x07','\\')
        return name, line
    
    elif line.startswith('array'):
        
        # Split
        tmp = line.split(' ',3)
        if len(tmp) < 4:
            print("SSDF Warning: invalid array definition on line %i."%linenr)
            return name, None
        # word1 = tmp[0] # says "array"
        word2 = tmp[1]
        word3 = tmp[2]
        word4 = tmp[3]
        
        # Determine shape            
        try:
            shape = [int(i) for i in word2.split('x') if i]
        except Exception:
            print("SSDF Warning: invalid array shape on line %i."%linenr)
            return name, None
        
        # Determine datatype 
        # Must use 1byte/char string in Py2.x, or numpy wont understand )
        dtypestr = simplestr(word3)
        if dtypestr not in ['uint8', 'int8', 'uint16', 'int16', 
                            'uint32', 'int32', 'float32', 'float64']:
            print("SSDF Warning: invalid array data type on line %i."%linenr)
            return name, None
        
        # Non-numpy user? (cannot load this)
        if np is None:
            return name, UnloadedArray(tuple(shape), dtypestr)
        
        # Get data           
        tmp = word4.split(",")
        
        if np.prod(shape)==0:
            # Empty array
            value = np.zeros(shape, dtype=dtypestr)
            return name, value
        
        elif len(tmp) > 1:
            # Stored in ascii
            value = np.zeros((len(tmp),),dtype=dtypestr)
            for i in range(len(tmp)):
                try:                    
                    value[i] = float(tmp[i])
                except Exception:
                    value[i] = np.NaN
            if np.prod(shape) == value.size:
                value.shape = tuple(shape)
            else:
                print("SSDF Warning: prod(shape)!=size on line %i."%linenr)
            return name, value
        
        else:
            # Stored binary
            
            # Get data: decode and decompress in blocks
            dataparts = []
            for blockt in word4.split(';'):                
                blockc = base64.decodestring(blockt)
                block = zlib.decompress(blockc)
                dataparts.append(block)
            
            # Combine and convert to numpy array
            data = bytes().join(dataparts)
            value  = np.frombuffer(data, dtype=dtypestr )
            
            # Set shape
            if np.prod(shape) == value.size:
                value.shape = tuple(shape)
            else:
                print("SSDF Warning: prod(shape)!=size on line %i."%linenr)
            return name, value
    
    else:
        # Try making int or float
        
        # First remove any comments
        i = line.find('#')
        if i>0:
            line = line[:i].strip()
        
        # First float
        try:
            value = float(line)
        except Exception:
            print("SSDF Warning: unknown value on line %i."%linenr)
            return name, None
        
        # Now check if it was in fact an int
        if line.count('.'):
            return name, value
        else:
            return name, int(value)


## Helper functions and classes


def _isvalidname(name):
    """ Returns attribute name, or None, if not valid """
    
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
    ss = ''
    for n in ob.shape:
        ss += '%ix' % n
    return ss[:-1]


class UnloadedArray:
    """ A class used for when an array had to be loaded but numpy was
    not installed. 
    """
    def __init__(self, shape, dtype):
        self.shape = shape
        self.dtype = dtype
    def __repr__(self):
        return "<SSDF unloaded array %s of type %s>" % (self.shape, self.dtype)
