""" MODULE STRUX

useage of this module: 
    import strux
    s = strux.new()
    # or
    s = strux.load("c:/tmp/foo.xml")

documentation:
    See the doc in the Strux class.
"""

import sys, os, os.path
import base64
import zlib
import xml.dom.minidom as xml

# try importing numpy
try:
    import numpy as np
except ImportError:
    np = None
    

class Strux(object):
    """ STRUX 
        
        Summary
        =======
        
        Strux is a standard for storing structured scientific data in XML. 
        Its goal is to store structured data in a human readable format, 
        but at the same time be easily readable in various computer 
        languages. Thus the use of XML. It is aimed for use in interpreted 
        languages like python and Matlab, but any language that can 
        support lists, dictionaries and multidimensional arrays can use 
        this standard.
        
        This is the Python implementation for reading, writing and using
        such data structures. If numpy is not installed, Strux can be used,
        but arrays cannot be read.        
        
        A Strux object holds named data (syntactic sugar for a 
        dictionary). The data can be one of seven types (see below), 
        including another Strux object and lists. This way data can
        be structured (as a tree structure). Names can be added in two 
        ways:
            s.foo = 'bar'  # the object way
            s['foo'] = 3   # the dictionary way
        Iterating over the Strux object yields the names in the dict (the 
        names in .__dict__ to be precize).
        
        Usage
        =====
        
        s = Strux() creates a new (empty) Strux object
        
        s.Load(path) loads the Strux from a file (use Loads to load from string)
        s.Save(path) saves the Strux to a file   (use Saves to save to string)
        s.Clear() removes all fields
        len(s) gets the amount of fields
        "print s" prints an overview of the fields and their values
        
        s = Strux(object) makes a Strux object from any structure of 
        objects. Basically, all attributes of the objects are copied, 
        except for methods. Dictionaries are converted to Strux 
        objects.
        
        Elements in a Strux data structure can be:
            - d: dictionary (is a Strux object in python)
            - l: list
            - s: (unicode or normal) string
            - f: float64 scalar
            - i: int32 scalar
            - a: (numpy) array of any type and shape
            - b: <arrays with over 32 elements will 
              be stored in binary form when saved>
        
        Example
        =======
        
        import numpy as np
        import strux
        s = strux.Strux() # same as "s = strux.new()"
        s.numbers = np.ones((3,2))
        s'numbers2 = np.ones((4,9)) # more than 32 elements
        s.notes = "This is an example"
        s.files = strux.Strux()
        s.files.filenames = ["one.txt","two.txt","three.txt"]
        s.files.basedir = "c:/temp"
        s.files['amount'] = 3
        print s.Saves() # show xml
        
        *will print ...*
        
        <strux>
        <s n='notes'>This is an example</s>
        <b n='numbers2' shape='4,9' dtype='float64'>eJxjYACBD/YMozRWGgCcJSqd</b>
        <a n='numbers' shape='3,2'>1.0, 1.0, 1.0, 1.0, 1.0, 1.0</a>
        <d n='files'>
          <i n='amount'>3</i>
          <s n='basedir'>c:/temp</s>
          <l n='filenames'>
            <s>one.txt</s>
            <s>two.txt</s>
            <s>three.txt</s>
          </l>
        </d>
        </strux>
        
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
            except:
                print "STRUX WARNING: Cannot make strux from", ob
                return
            
            def _getValue(val):
                "Get the value, as suitable for strux"                
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
                    return Strux(val)

            # copy all keys in the dict that are not methods
            for key in tmp:                
                val = tmp[key]
                if not callable(val):                
                    self[key] = _getValue(val)
    
    
    ## Saving and loading
    
    def Loads(self, ss):
        """ Load contents from a string.
        """
        # clear first
        self.Clear()
        # get root node
        dom = xml.parseString(ss)
        root = dom.getElementsByTagName("strux")[0]
        # parse xml
        s = _strux2ob(root)
        # copy fields (we only need a shallow copy)
        for key in s:
            self[key] = s[key]


    def Load(self, path):
        """ Load contents from file.        
        """        
        path = os.path.abspath(path)        
        # open file and read data
        f = open(path)
        ss = f.read()
        f.close()
        # parse!
        self.Loads(ss)
    
    
    def Clear(self):
        """ Clear all fields, after which the Strux object is empty.
        """
        keys = [key for key in self]
        for key in keys:
            del(self.__dict__[key])


    def Saves(self, indent=None):
        """ Write the Strux object as a string.
        use x.Saves(1) to use pretty indentation
        """
        # get content
        s = _ob2strux(self,indent)
        # determine end
        end = "\n</strux>\n"
        if indent is None:
            end = "</strux>"
        # return
        return "".join( ["<strux>", s, end] )


    def Save(self, path):
        """ Save the Strux object to a file.
        """
        path = os.path.abspath(path)
        fid = open(path,'w')
        fid.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        fid.write( self.Saves(1) )
        fid.close()
    
    
    ## To act as dict
    
    def __getitem__(self, key):
        # name ok?
        key = self._isvalidname(key)
        if not key:
            raise KeyError("Invalid name")
        # name exists?
        if not self.__dict__.has_key(key):
            raise KeyError(str(key))
        # return
        return self.__dict__[key]
    
    
    def __setitem__(self, key, value):
        # name ok?
        key = self._isvalidname(key)
        if not key:
            raise KeyError("Invalid name")
        # set
        self.__dict__[key] = value
    
    
    def _isvalidname(self, name):
        " Returns the name, or None, if not valid"
        # convert unicode to str
        if isinstance(name, unicode):
            try:
                name = str(name)
            except:
                return None
        
        # is it a string?
        if not ( name and isinstance(name, str) ):
            return None
        
        # check name
        namechars = 'abcdefghijklmnopqrstuvwxyz_0123456789'
        name2 = name.lower()
        if name2[0] not in namechars[0:-10]:
            return None
        tmp = map(lambda x: x not in namechars, name2[2:])
        
        # return
        if sum(tmp)==0:
            return name
    
    
    def __iter__(self):
        " return iterator over keys "
        return self.__dict__.__iter__()
   

    ## Representation stuff...

    def __len__(self):
        " Return amount of fields in the Strux object"
        return len(self.__dict__)
    
    
    def __repr__(self):
        "Short string representation"
        return "<Strux object with %i fields>" % len(self)


    def __str__(self):
        "String representation"
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
                    valuestr = "[ %s %s ]" %(str(value.shape),str(value.dtype))
                else:
                    valuestr = "a %s with length %i" % (typestr, len(value))
            s += tmp.rjust(c+1) + ": %s\n" % (valuestr)
        return s


## Helper functions en classes


def _strux2ob(dom):
    """_strux2ob(dom) or _strux2ob(string)
    Parses the xml-string or xml-dom to create the structured data
    stored in it.

    """

    # subfunctions
    def setkeyvalue(ob, key, value):
        try:
            dummy = ob.__class__.__dict__[key]
            ob.__class__.__dict__[key] = value
        except:
            ob.__dict__[key] = value


    # create document object model (if necesary)
    if not isinstance(dom, xml.Node):
        dom = xml.parseString(dom)

    # get root
    #print "parsing..."

    o = Strux()

    for node in dom.childNodes:

        # only proceed if an element
        if node.nodeType != node.ELEMENT_NODE: continue

        # get type
        tipe = node.nodeName

        # get name
        name = node.getAttribute("name") # getAttribute gets the text directly
        if not name:
            name = node.getAttribute("n")
        if not name:
            raise Exception("unnamed element encountered!")

        # get value
        if tipe=='l':
            text = ""
        else:
            for sub in node.childNodes:
                if sub.nodeType == node.TEXT_NODE:
                    text = sub.data
                    break
            else: # if fails...
                tipe = "s"
                text = "error getting value!"

        # get the value
        try:
            val = _strux2val(tipe,text,node)
            setkeyvalue(o, name, val)
        except Exception, inst:
            s = ""
            print "STRUX WARNING: Skipped loading attribute: ", inst
            
        
    return o


def _strux2val(tipe, text, node):
    """val = _strux2val(tipe, text, node)
    Get the value, given the type (tipe) and the text string. Some types
    require extra information stored in the attributes of the nodes.

    """

    # strux
    if tipe=='d':
        return _strux2ob(node)

    # lists
    elif tipe=='l':
        L = []
        for sub in node.childNodes:
            if sub.nodeType == sub.ELEMENT_NODE:
                tipe2 = sub.nodeName
                for subsub in sub.childNodes:
                    if subsub.nodeType == subsub.TEXT_NODE:
                        text2 = subsub.data
                        break
                else: # if fails...
                    tipe2 = "s"
                    text2 = "error getting listvalue!"
                L.append( _strux2val(tipe2,text2,sub) )
        return L

    # parse base types
    elif tipe=='s':
        return text
    elif tipe=='f':
        return float(text) # np.array( float(text) )  # ndarray with shape ()
    elif tipe=='i':
        return int(text) #np.array( int(text) )

    # parse array types
    elif tipe == 'a':
        
        # get info (if present)
        shapestr = str( node.getAttribute("shape") )
        dtypestr = str( node.getAttribute("dtype") )
        
        # default type is float64
        if not dtypestr:
            dtypestr = 'float64'
        
        # non-numpy users cannot load this
        if np is None:
            msg = "cannot load array because numpy is not installed."
            print "STRUX WARNING:", msg 
            return UnloadedArray(shapestr, dtypestr)
        
        # load array
        tmp = text.split(",")
        vals = np.zeros((len(tmp),),dtype=dtypestr)
        for i in xrange(len(tmp)):
            vals[i] = np.float64(tmp[i])
        
        # if shape given, apply
        if shapestr:
            shapelist = [int(i) for i in shapestr.split(",")]
            vals.shape = tuple( shapelist )
        
        return vals


    # binary
    elif tipe == 'b':
        
        # get info (if present)
        shapestr = str( node.getAttribute("shape") )
        dtypestr = str( node.getAttribute("dtype") )
        
        # non-numpy users cannot load this
        if np is None:
            msg = "cannot load array because numpy is not installed."
            print "STRUX WARNING:", msg 
            return UnloadedArray(shapestr, dtypestr)
        
        # get data: decode and decompress, convert to numpy array
        data = base64.decodestring(text)
        data = zlib.decompress(data)
        arr  = np.frombuffer(data,dtype=dtypestr )
        
        # set shape
        shapelist = [int(i) for i in shapestr.split(",")]
        arr.shape = tuple(shapelist)
        
        return arr
    
    else:
        # produce warning
        name = node.getAttribute("n")
        if name: name = " name='" + name + "'"
        raise Exception("STRUX WARNING: Unknown type '" + tipe + "'" + name)




def _ob2strux(ob, indent=None):
    """Parse an object to a string (xml) representation,
    keeping the structure intact.

    """
    
    def sortkeys(dict):
        # get list of keys
        keys = dict.keys()
        
        def vallen(val):
            if isinstance(val,Strux):
                return len(val)
            elif isinstance(val,list):
                return len(val)
            else:
                return 1
        
        # get list of lengths...
        def comparer(key1,key2):
            # get vals
            l1 = vallen(dict[key1])
            l2 = vallen(dict[key2])
            return l1-l2
                
        return sorted(keys,comparer)
        

    # set indentation
    if indent is None: tabs = ""
    else: tabs = "  " * indent

    ss = ""

    # check only in instance dict
    dict = ob.__dict__
    keys = sortkeys(dict)
    for key in keys:

        # skip all the buildin stuff
        if key[0:2]=="__": continue

        # we have the key, go get the value!
        val = dict[key]
        #print key, val

        # skip methods, or anything else we can call
        if callable(val):  continue

        # get value!
        try:
            tipe, attr, valstr = _val2strux(val, indent)            
            if tipe in ['d','l']: ttabs = tabs
            else: ttabs = "" # only tab for lists and dicts
            s = "<%s n='%s'%s>%s%s</%s>" % (
                tipe, key, attr, valstr, ttabs, tipe)
        except Exception, inst:
            s = ""
            print "STRUX WARNING: skipped saving attribute " + key + ": ", inst
        
        if indent is None:
            ss = "".join([ss, s])
        else:
            ss = "".join([ss, "\n", tabs , s])

    return ss



def _val2strux(val, indent=None):
    """Parse a value to a string. return its type,
    any arguments if necessary, and of course the value as a string.

    """
    
    # newline?
    nl = "\n"
    if indent is None:
        nl = " " # it needs to be a space though

    # strux
    if isinstance(val,Strux):
        if indent is not None: 
            indent += 2
        return "d", "", _ob2strux(val,indent)+nl

    # lists
    elif isinstance(val,list):
        ss = nl
        for element in val:
            tipe2, att2, val2 = _val2strux(element,indent)
            ttabs1 = ""
            if indent:
                ttabs1 = "  " * (indent+1)
            if tipe2 in ['d','l']: ttabs2 = ttabs1
            else: ttabs2 = "" # only tab for lists and dicts
            ss += "%s<%s%s>%s%s</%s>" % (ttabs1,tipe2,att2,val2,ttabs2,tipe2)
            ss += nl

        return "l", "" , ss

    # base types
    elif isinstance(val,str) or isinstance(val,unicode):
        return "s", "", val
    elif isinstance(val,float):
        return "f", "", str(val)
    elif isinstance(val,int):
        return "i", "", str(int(val))

    # array types
    elif np and isinstance(val,np.ndarray):

        ndim = len(val.shape)
        if ndim == 0:
            if val.dtype in [np.float32, np.float64]:
                return "f", "", str(val)
            else:# val.dtype in [np.int32]:
                return "i", "", str(val)
        
        elif val.size<33:
            # small enough to print, shape required
            shapestr = " shape='" + _shapeString(val) + "'"
            # we need to ravel...
            val = val.ravel()
            elements = [str(v)+", " for v in val]
            elements[-1] = elements[-1][0:-2]
            if val.dtype==np.float64:
                return "a", shapestr, "".join(elements)
            else:
                dtypestr = " dtype='" + str(val.dtype) + "'"
                return "a", shapestr+dtypestr, "".join(elements)
        
        else:
            # IF NO LUCK YET... we need to go binary
            attr = " shape='%s' dtype='%s'" % (_shapeString(val), 
                str(val.dtype))
            data = val.tostring()
            data = zlib.compress(data)
            text = base64.encodestring(data)
            text = text.replace("\n","")
            return "b", attr, text


    # we do not do tuples
    elif isinstance(val,tuple):
        tmp = "Tuples will not be struxed, use lists or arrays instead!"
        raise Exception(tmp)
    
    elif isinstance(val, UnloadedArray):
        tmp = "Cannot save unloaded arrays (need numpy)!"
        raise Exception(tmp)
    
    # If anything else did not work, we have an unkown object I guess!
    raise Exception("Unknown object: " + str(val))    


def _shapeString(ob):
    tmp = str(ob.shape)
    tmp =  tmp[1:-1].replace(" ","")
    if tmp[-1]==",":
        tmp = tmp[0:-1]
    return tmp


class UnloadedArray:
    def __init__(self, shape, dtype):
        self.shape = shape.replace(',','x')
        self.dtype = dtype
    def __repr__(self):
        return "<SRUX unloaded array %s of type %s>" % (self.shape, self.dtype)
    

## Module methods for the user


def new():
    """ Create new Strux instance.
    Same as strux.Strux().
    """
    return Strux()


def load(path):
    """ Load Strux data from a file.
    """
    s = Strux()
    s.Load(path)
    return s
    

## Tester

if __name__=="__main__":
    
    if np:
        # test all 7 datatypes and test getting and setting
        
        # create structure
        s = Strux()
        s.numbers = np.ones((3,2))      # small array
        s.numbers2 = np.ones((4,9))     # larger array
        s.notes = "This is an example"  # string
        s.files = Strux()               # strux
        s.files.firstfile = "one.txt"
        s.files.filenames = [s.files['firstfile'],"two.txt","three.txt"]
        s.files['basedir'] = "c:/temp"
        s.files.amount = 3    
        s.alist = ["a string",4, Strux()]
        
        # save and load
        a = s.Saves()
        s.Loads(a)
        s.Save("c:/test_strux.xml")    
        s.Load("c:/test_strux.xml")
        
        # print
        print s.Saves(1)
        a = s.Saves()
        print a
        print a.count('\n')
        
    elif True: 
        # try loading strux with arrays
        s = Strux()
        s.Load("c:/test_strux.xml")        
        a = s.Saves()
        s.Loads(a)
        print s.Saves(1)
        
    else:
        # test without arrays
        s = Strux()        
        s.notes = "This is an example"  # string
        s.files = Strux()               # strux
        s.files.firstfile = "one.txt"
        s.files.filenames = [s.files['firstfile'],"two.txt","three.txt"]
        s.files['basedir'] = "c:/temp"
        s.files.amount = 3    
        s.alist = ["a string",4, Strux()]
        
        # save and load
        a = s.Saves()
        s.Loads(a)
        s.Save("c:/test_strux.xml")    
        s.Load("c:/test_strux.xml")
        
        # print
        print s.Saves(1)
        a = s.Saves()
        print a
        print a.count('\n')
        
