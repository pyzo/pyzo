""" MODULE Simple Structured Data Format.

SSDF is a format for storing structured (scientific) data.
The goal of the format is to be easily readable by humans, 
but at the same time be easily readable in various computer 
languages. It is aimed for use in interpreted languages like 
python and Matlab, but any language that can support lists, 
dictionaries and multidimensional arrays can use this format.

This is the Python implementation for reading, writing and using
such data structures. This module can be used in both python 2.x
and 3.x. If numpy is not installed, it can be used, but arrays 
cannot be read or written.

Elements in a data structure can be:
    - a dictionary (a ssdf.Struct object in python)
    - a list
    - (unicode) string
    - float scalar
    - int scalar
    - (numpy) array of any type and shape
    - None (Null)

Usage
=====
ssdf.new() to create a new  Struct object
ssdf.load(path) to load structured data from a file 
ssdf.save(path,s) to save structured data to a file
(use ssdf.saves(s) and ssdf.loads(text) to save/load a string)

Example
=======

import numpy as np
import ssdf
s = ssdf.new()
s.numbers = np.ones((3,2))
s.numbers2 = np.ones((4,9)) # more than 32 elements
s.notes = "This is an example"
s.files = ssdf.Struct()
s.files.filenames = ["one.txt","two.txt","three.txt"]
s.files.basedir = "c:/temp"
print ssdf.saves(s) # show in text

*will print ...*

notes = 'This is an example'
numbers2 = array 4x9 float64 eJxjYACBD/YMozRWGgCcJSqd
numbers = array 3x2 float64 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
files = dict:
  basedir = 'c:/temp'
  filenames = list:
    'one.txt'
    'two.txt'
    'three.txt'

"""

import os, sys
import base64
import zlib

# try importing numpy
try:
    import numpy as np
except ImportError:
    np = None
   
# if version 2...
if sys.version_info[0] <= 2:
    bytes = str
    str = unicode
else:
    basestring = str


## The class

class Struct(object):
    """ STRUCT 
        
        A Struct object holds named data (syntactic sugar for a 
        dictionary). Atributes can be other Struct objects and lists,
        and thus allows data to be structured. 
        Elements can be added in two ways:
            s.foo = 'bar'       # the object way
            s['foo'] = 'bar'    # the dictionary way
        Iterating over the Struct object yields the names in the dict (the 
        names in s.__dict__ to be precize). len(s) gives the number of 
        elements in the Struct.
        
        Initialization:
        
        s = Struct() creates a new (empty) Struct object
        
        s = Struct(object) makes a Struct object from any structure of 
        objects. Basically, all attributes of the objects are copied, 
        except for methods and attributes starting with "__". Dictionaries 
        are converted to Struct objects as well.
        
        ssdf.load(path) to load structured data from a file 
        ssdf.save(path,s) to save structured data to a file
        (use ssdf.saves(s) and ssdf.loads(text) to save/load a string)
    
    """    

    def __init__(self,ob=None):
        
        if ob is None:
            # plain struct
            return
        
        else:
            # try loading from object
            
            # try getting the dict, if no success, tough luck.            
            try:
                if isinstance(ob,dict):
                    tmp = ob
                else:
                    tmp = ob.__dict__
            except Exception:
                print("SSDF Warning: Cannot make Struct object from" + str(ob))
                return
            
            def _getValue(val):
                "Get the value, as suitable for Struct"                
                if isinstance(val, (str, unicode, float, int) ):
                    return val
                if np and isinstance(val, np.ndarray):
                    return val
                elif isinstance(val,list):
                    L = list()
                    for element in val:
                        L.append( _getValue(element) )
                    return L
                else:
                    return Struct(val)
            
            # copy all keys in the dict that are not methods
            for key in tmp:                
                val = tmp[key]
                if not hasattr(val,'__call__'):                
                    self[key] = _getValue(val)
    
    
    def __getitem__(self, key):
        # name ok?
        key2 = _isvalidname(key)
        if not key:
            raise KeyError("Trying to get invalid name '%s'." % key)
        # name exists?
        if not key in self.__dict__:
            raise KeyError(str(key))
        # return
        return self.__dict__[key]
    
    
    def __setitem__(self, key, value):
        # name ok?
        key2 = _isvalidname(key)
        if not key:
            raise KeyError("Trying to set invalid name '%s'." % key)
        # set
        self.__dict__[key] = value
    
    
    def __iter__(self):
        """ return iterator over keys """
        return self.__dict__.__iter__()
   
    
    def __len__(self):
        """ Return amount of fields in the Struct object. """
        return len(self.__dict__)
        
    
    def __repr__(self):
        """ Short string representation. """
        return "<SSDF struct object with %i fields>" % len(self)


    def __str__(self):
        """ String representation. """
        c = 0
        for key in self:
            if len(key) > c:
                c = len(key)
        
        s = ''
        for key in self:
            tmp = "%s" % (key)
            value = self[key]
            valuestr = repr(value)
            if len(valuestr)>80:
                typestr = str(type(value))[7:-2]
                if np and isinstance(value,np.ndarray):
                    shapestr = _shapeString(value)
                    valuestr = "[ %s %s ]" %(shapestr,str(value.dtype))
                else:
                    valuestr = "a %s with length %i" % (typestr, len(value))
            s += tmp.rjust(c+1) + ": %s\n" % (valuestr)
        return s


def new():
    """ Create an empty Struct object. 
    return ssdf.Struct()
    """
    return Struct()


def clear(struct_object):
    """ Clear all fields of the Struct object.
    """
    keys = [key for key in struct_object]
    for key in keys:
        del(struct_object.__dict__[key])


## STEP 1: file <--> text


def save(path, struct_object, appName='ssdf.py', newline='\n'):
    """ Save Struct object to a file.
    """
    path = os.path.abspath(path)
    
    # get text and convert to bytes
    header =  '# This Simple Structured Data Format (SSDF) file was '
    header += 'created from Python by %s.' % appName
    text = saves(struct_object)
    text = header + newline + text.replace('\n',newline) + newline
    byts = text.encode('UTF-8')
    
    # store...
    fid = open(path,'w')
    try:
        fid.write( byts )
    except Exception:
        raise
    finally:
        fid.close()


def load(path):
    """ Load Struct object from a file.        
    """        
    path = os.path.abspath(path)        
    if not os.path.isfile(path):
        raise IOError("The specified file does not exist.")
    
    # open file and read data
    f = open(path,'rb')
    try:
        byts = f.read()
    except Exception:
        raise
    finally:        
        f.close()
    
    # parse!
    text = byts.decode('UTF-8')
    return loads(text)
    


## STEP 2: text <--> structured lines


def saves(struct_object):
    """ Write the Struct object to a string.  """
    
    base = _toString('', struct_object, -2)  # negative indent
    strings = _pack(base)
    return "\n".join(strings[1:])
    

def _pack(lineObject):
    """ Pack the lines such that the structures with less lines
    appear first. """
    
    # get list of strings for each child
    listOfLists = []
    for child in lineObject.children:            
        childList = _pack(child)
        listOfLists.append( childList )
    
    # sort by length
    listOfLists.sort(key=len)
    
    # produce flat list
    flatList = [lineObject.line]
    for childList in listOfLists:
        flatList.extend(childList)
    
    # done
    return flatList


def loads(text):    
    """ Load Struct object from a string.  """
    
    base = _LineObject("dict:",-2, -1)
    tree = [base]
    
    # pre process
    text = text.replace('\t','  ')
    text = text.replace('\r\n','\n').replace('\r','\n')
    
    # setup structure
    lines = text.split("\n")
    for linenr in range(len(lines)):
        line = lines[linenr]
        line2 = line.lstrip()
        line3 = line2.rstrip()
        
        # skip comments and empty lines        
        if len(line3)==0 or line3[0] == '#':        
            continue
        
        # produce value
        indent = len(line) - len(line2)
        new = _LineObject(line2, indent, linenr+1)
        
        # select leaf in tree
        while not indent > tree[-1].indent:
            tree.pop()
        
        # append (to object and to simple tree structure)
        tree[-1].children.append(new)        
        tree.append(new)
    
    # do the parse pass
    name, value = _fromString(base)
    return value

    
    
## STEP 3: (structured) lines <--> structured data


class _LineObject:
    def __init__(self, line='', indent=-2, linenr=-1):
        self.line = line
        self.indent = indent
        self.linenr = linenr
        self.children = []
    

def _toString(name, value, indent):
    """ Make a Line object from the name and value.
    Name can be ''. """
    
    lineObject = _LineObject() 
    
    # parse name
    lineObject.line = str(" ") * indent
    if name:
        lineObject.line += "%s = " % name
    
    # parse value
    
    # struct
    if value is None:
        lineObject.line += "Null"
    
    elif isinstance(value, (Struct, dict)):            
        lineObject.line += "dict:"
        
        # process children        
        for key in value:
            # skip all the buildin stuff
            if key[0:2] == "__":
                continue                
            # we have the key, go get the value!
            val = value[key]
            # skip methods, or anything else we can call
            if hasattr(val,'__call__'): # py3.x does not have function callable
                continue
            # add!
            tmp = _toString(key, val, indent+2)
            lineObject.children.append(tmp)
    
    # lists
    elif isinstance(value,list):
        lineObject.line += "list:"
        for element in value:
            tmp = _toString("", element, indent+2)
            lineObject.children.append(tmp)                
    
    # base types
    elif isinstance(value,basestring):        
        #lineObject.line += "'%s'" % _stringEncode(value)
        value = value.replace('\r\n','\n').replace('\r','\n')
        value = value.replace('\\', '\\\\') # if \n happens to occur
        value = value.replace('\n','\\n')
        lineObject.line += "$" + value
    elif isinstance(value, bool):
        lineObject.line += '%i' % int(value)    
    elif isinstance(value,int):
        lineObject.line += '%i' % int(value)
    elif isinstance(value,float):
        lineObject.line += '%0.12f' % value
    
    # array types
    elif np and isinstance(value,np.ndarray):
        
        ndim = len(value.shape)
        if ndim == 0:
            if value.dtype in [np.float32, np.float64]:
                lineObject.line += str(value)
            else:
                lineObject.line += str(value)
        
        elif value.size<33:
            # small enough to print, but shape required
            shapestr = _shapeString(value)
            dtypestr = str(value.dtype)
            # get values in list (we need to ravel)
            elements = [str(v) for v in value.ravel()]
            # build string
            lineObject.line += "array %s %s %s" % (shapestr, dtypestr, 
                ", ".join(elements) )
        
        else:
            # get attributes
            shapestr = _shapeString(value)
            dtypestr = str(value.dtype)
            # get data as compressed base 64 string
            data = value.tostring()
            data = zlib.compress(data)
            text = base64.encodestring(data)
            text = text.replace("\n","") # by default contains blocks
            lineObject.line += "array %s %s %s" % (shapestr, dtypestr, text)
    
    # we do not do tuples
    elif isinstance(value,tuple):
        tmp = "Tuples are not supported in ssdf, use lists or arrays instead!"
        raise ValueError(tmp)
    
    elif isinstance(value, UnloadedArray):
        tmp = "Cannot save unloaded arrays (need numpy)!"
        raise ValueError(tmp)
    
    else:
        # If anything else did not work, we have an unkown object I guess!
        raise Exception("Unknown object: " + str(value)) 
        #print("SSDF Warning: Unknown object: "+ str(value))
    
    return lineObject


def _fromString(lineObject):
    
    # init (the line should be the whole line)
    line = lineObject.line
    indent = lineObject.indent
    linenr = lineObject.linenr
    
    # get name
    iq = line.find("$") # string
    ie = line.find("=") # equal
    ia = line.find('array') # array def
    if ia>=0 and ia < ie:
        ie = -1
    if iq>=0 and iq < ie:
        ie = -1
    if ie<0:
        name = ""
        line = line.lstrip()
    else:
        name = line[:ie].strip()
        line = line[ie+1:].lstrip()
    
    # parse value
    
    if line == '':
        # an empty line
        return name, None
    
    elif line.startswith('Null'):
        return name, None
    
    elif line.startswith('dict:'):
        value = Struct()
        for child in lineObject.children:
            key, val = _fromString(child)
            if key:
                value[key] = val
            else:
                tmp = child.linenr
                print("SSDF Warning: unnamed element in dict on line %i."%tmp)
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
    
    elif line[0] == "$":
        # string
        line = line[1:].replace('\\\\','0x07') # temp
        line = line.replace('\\n','\n')
        line = line.replace('0x07','\\')
        return name, line
    
    elif line.startswith('array'):
        
        # split
        tmp = line.split(' ',3)
        if len(tmp) < 4:
            print("SSDF Warning: invalid array definition on line %i."%linenr)
            return name, None
        # word1 = tmp[0] # says "array"
        word2 = tmp[1]
        word3 = tmp[2]
        word4 = tmp[3]
        
        # determine shape            
        try:
            shape = [int(i) for i in word2.split('x') if i]
        except Exception:
            print("SSDF Warning: invalid array shape on line %i."%linenr)
            return name, None
        
        # determine datatype
        dtypestr = str(word3)
        if dtypestr not in ['uint8', 'int8', 'uint16', 'int16', 
                            'uint32', 'int32', 'float32', 'float64']:
            print("SSDF Warning: invalid array data type on line %i."%linenr)
            return name, None
        
        # non-numpy user? (cannot load this)
        if np is None:
            return name, UnloadedArray(tuple(shape), dtypestr)
        
        # get data
        
        tmp = word4.split(",")
        if len(tmp) > 1:
            # stored in ascii                        
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
            # stored binary
            
            # get data: decode and decompress, convert to numpy array
            data = base64.decodestring(word4)
            data = zlib.decompress(data)
            value  = np.frombuffer(data, dtype=dtypestr )
            
            # set shape
            if np.prod(shape) == value.size:
                value.shape = tuple(shape)
            else:
                print("SSDF Warning: prod(shape)!=size on line %i."%linenr)
            return name, value
    
    else:
        # try making int or float
        
        # first float
        try:
            value = float(line)
        except Exception:
            print("SSDF Warning: unknown value on line %i."%linenr)
            return name, None
        
        # now check if it was in fact an int
        if line.count('.'):
            return name, value
        else:
            return name, int(value)

    
## Helper functions and classes


def _isvalidname(name):
    """ Returns attribute name, or None, if not valid """
    
    # is it a string?
    if not ( name and isinstance(name, basestring) ):
        return None
    
    # check name
    namechars = str('abcdefghijklmnopqrstuvwxyz_0123456789')
    name2 = name.lower()
    if name2[0] not in namechars[0:-10]:
        return None
    tmp = map(lambda x: x not in namechars, name2[2:])
    
    # return
    if sum(tmp)==0:
        return name


def _shapeString(ob):    
    ss = ''
    for n in ob.shape:
        ss += '%ix' % n
    return ss[:-1]


class UnloadedArray:
    """ A class used for when an array had to be loaded but numpy was
    not installed. """
    def __init__(self, shape, dtype):
        self.shape = shape
        self.dtype = dtype
    def __repr__(self):
        return "<SSDF unloaded array %s of type %s>" % (self.shape, self.dtype)


## Testing ...

if __name__ == '__main__':

    class Bla:        
        pass
    bla = Bla
    bla.foo = 4.1
    bla.bar = '4.1'
    
    a = Struct()
    a.foo = 4.0
    a.bar = 8
    a.yo = "omg \"yeah\" that\'s rigth!"
    a.bb = Struct()
    a.bb.ok = 'yes'
    a.bb.eq = 3==3
    a.cc = [1,2,'dasf',Struct()]
    a.dd = np.array([1,2,4,8.1,1])
    a.ee = np.random.normal(size=(20,20))
    
    text =  saves(a)
    #print text
    b=loads(text)

