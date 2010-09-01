#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
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


""" Module channels

Multichannel unicode interprocess communication via a socket.

This module allows communication with the following properties:
- Non-blocking interface by default. Data can also be read using
  blocking, or blocking for a specified amount of time.
- Communication in packages. What was send in one call, is also 
  received in one call. Received packages are always complete.
- Multiple channels. Up to 128 channels for each direction. All
  channels communicate over the same socket.
- Messages are (unicode) strings.

This module can be imported in Python 2 ad well as in Python 3. It 
implements the Channels object, which represents the connection to
the other end. It has methods to obtain SendingChannel and 
ReceivingChannel (file-like) objects, which can be used to send and 
receive strings. 


Here's an example:
------------------

# On one side:
import channels
c = channels.Channels(1) # create channels object with one sending channel
c.host('channels_example') # host (determine port by hashing a string)
s1 = c.get_sending_channel(0)
r1 = c.get_receiving_channel(0)
r2 = c.get_receiving_channel(1)

# write something. This will be send as soon as the other side is connected.
s1.write('hello there')
# read all packages received until now (returns '' if none available)
r1.read()
# read a single package (waits for max 5 s, returns '' if none available)
r2.read_one(5) 


# On other side:
import channels
c = channels.Channels(2) # create channels object with two sending channels
c.connect('channels_example') # connect (determine port by hashing same string)
s1 = c.get_sending_channel(0)
s2 = c.get_sending_channel(1)
r1 = c.get_receiving_channel(0

s1.write('This is channel one')
s2.write('This is channel two')
r1.read_one()

"""

# Implementation details. I found http://www.amk.ca/python/howto/sockets/
# a usefull reference in addition to the documentation on Python sockets.
# An earlier implementation used the "messages indicate how long they are" 
# principle. However, this requires quite a bit of processing, and thus
# makes sending a lot of (small) messages very slow (like for example
# "for i in range(1000): print i"). Therefore we now delimit the
# messages. We can do this, because the bytes 0xFE and 0xFF are never 
# used in the UTF-8 encoding.
#
# The data is send bidirectional (using both directions of the socket).
# SendingChannel objects push their message on a global send queue, that
# is fully popped before sending. On the other end, messages are received 
# and pushed on the queue of the proper ReceivingChannel object. The 
# queues are optimized to pop all data at once and can also receive
# multiple messages at once. Note that the send queue contains packed
# messages (including header) and the receive queues contain the encoded
# string only.
#
# Each message starts with a header of 8 bytes: 
# 7 bytes for marker ascii string (MESSAGE to send a message)
# 1 bytes for channel id (uint8)
#
# After the header the encoded text (if any) follows, followed by the 
# delimiter (0xff). The text is converted to bytes using UTF-8 encoding.
# 
# There are some other messages that can be send. They consist of only
# an (8 byte) header, which starts with a length-7 ASCII encoded string:
# - NOOP   : no operation, to let the other end know we are still there
# - CLOSE  : close the connection (and all channels)
# - INT    : interrupt the main thread of the other process
# - KILL   : kill the other process

import os, sys, time
import socket
import threading
from select import select  # to determine wheter a socket can receive data
try:
    import thread # Python 2
except ImportError:
    import _thread as thread # Python 3

BUFFERSIZE = 2**13 # 4096 or 8192 chunk size is recommended.

# version dependent defs
V2 = sys.version_info[0] == 2
if V2:
    bytes, str = str, unicode
    DELIMITER = chr(255)
else:
    basestring = str  # to check if instance is string
    long = int # for the port
    DELIMITER = bytes([255])

# To decode P2k strings that are not unicode
if sys.__stdin__:
    stdinenc = sys.__stdin__.encoding
elif sys.stdin:
    stdinenc = sys.stdin.encoding
else:
    stdinenc = 'utf-8'


def portHash(name):
    """ portHash(name)
    Given a string, returns a port number between 49152 and 65535. 
    (2**14 (16384) different posibilities)
    This range is the range for dynamic and/or private ports 
    (ephemeral ports) specified by iana.org.
    The algorithm is deterministic, thus providing a way to map names
    to port numbers.
    """
    fac = 0xd2d84a61
    val = 0
    for c in name:
        val += ( val>>3 ) + ( ord(c)*fac )
    val += (val>>3) + (len(name)*fac)
    return 49152 + val % 2**14 



def packMessage(type='MESSAGE', id=0, bb=None):
    """ packMessage(type, id=None, bb=None)
    Build a message ready for sending. Returns a bytes object.
    - type must be a max 7 elements ASCII string.
    - id must be an int between 0 and 128 (indicating channel id)
    - bb must be the text encoded using utf-8 encoding
    """
    
    message = bytes()
    
    # pack type (and justify)
    message += type.encode('ascii').ljust(7)
    
    # pack id (in range 0-128)
    message += chr(id).encode('ascii')
    
    # pack 
    if bb:
        message += bb
    
    # done
    return message
    

def unPackMessage(message):
    """unPackMessage(message)
    The message (without delimiter) is split.
    Return tuple (type [str], id [int], bb [bytes])
    """
    
    # unpack type
    type = message[:7].decode('ascii').strip()
    
    # unpack id
    id = ord(message[7:8])
    
    # unpack text
    text = message[8:]
    
    # done
    return type, id, text


    
class Queue:
    """ Queue
    Non-blocking thread save queue class for packages of bytes.
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._data = []
    
    def push(self, value):
        """ push(object)
        Push a bytes package to the queue. """
        self._lock.acquire()
        try:
            self._data.append(value)
        finally:
            self._lock.release()
    
    def push_more(self, value):
        """ push_more(object)
        Push a list of bytes packages to the queue."""
        self._lock.acquire()
        try:
            self._data.extend(value)
        finally:
            self._lock.release()
    
    def pop(self):
        """ pop()
        Pops a bytes package from the queue. 
        If the queue is empty, returns empty bytes. """
        self._lock.acquire()
        try:
            if not self._data:
                tmp = bytes()
            else:
                tmp = self._data.pop(0)
        finally:
            self._lock.release()
        return tmp
    
    def pop_all(self):
        """ pop_all()
        Pop a list containing all bytes packages, emptying the queue.
        """ 
        self._lock.acquire()
        try:
            tmp = self._data
            self._data = [] # new empty list
        finally:
            self._lock.release()
        return tmp
    
    def pop_last(self):
        """ pop_last()
        Pop only the last message, discarting all the rest.
        """
        self._lock.acquire()
        try:
            if not self._data:
                tmp = bytes()
            else:
                tmp = self._data[-1]
                self._data = [] # new empty list
        finally:
            self._lock.release()
        return tmp
    
    def count(self):
        """count()
        Return the number of packages in the queue. """
        self._lock.acquire()
        try:
            tmp = len(self._data)
        finally:
            self._lock.release()
        return tmp


class BaseChannel(object):
    """ BaseChannel
    Abstract class for the input and output channel. 
    
    Each channel has a queue in which the pending messages are stored.
    At the sending side they are waiting to be send, and at the receiving
    side they are received but not yet read. 
    
    More specifically:
    The doorman of the Channels object pops the messages from a single queue 
    and sends them over the channel. The doorman at that side receives 
    the mesage and puts it in the queue of the corresponding input channel, 
    where the data is available via the read methods.    
    """
    
    # Our file-like objects should not implement:
    # (see http://docs.python.org/library/stdtypes.html#bltin-file-objects)
    # explicitly stated: fileno, isatty
    # don't seem to make sense: readlines, seek, tell, truncate, errors,
    # mode, name, 
    
    def __init__(self, queue):
        self._q = queue
        self._closed = False
        self._softspace = False
    
    @property
    def closed(self):
        """ Get whether the channel is closed. 
        """
        return self._closed
    
    @property
    def encoding(self):
        """ The encoding used to encode strings to bytes and vice versa. 
        """
        return 'UTF-8'
    
    def flush(self):
        """ flush()
        Flush the file. Does nothing, since the messages are constantly
        pumped to the other end. 
        """ 
        pass
    
    @property
    def newlines(self):
        """ The type of newlines used. Returns None; we never know what the
        other end could be sending! """
        return None
    
    # this is for the print statement to keep track spacing stuff
    def _set_softspace(self, value):
        self._softspace = bool(value)
    def _get_softspace(self):
        return self._softspace
    softspace = property(_get_softspace, _set_softspace, None, '')

    
class SendingChannel(BaseChannel):
    """ SendingChannel
    An outgoing channel to an other process. 
    On the other end, there is a corresponding ReceivingChannel.
    """
    
    def __init__(self, queue, id):
        BaseChannel.__init__(self, queue)
        self._id = id
    
    
    def write(self, s):
        """ write(s)
        Write a string to the channel. The string is encoded using
        utf-8 and then send over the binary channel. When the string
        is empty, the call is ignored.
        """
        if not isinstance(s,basestring):
            raise ValueError("SendingChannel.write only accepts strings.")
        if self._closed:
            raise ValueError("Cannot write to a closed channel.")
        if s:
            # If using py2k and the string is not unicode, make unicode first
            # by try encoding using UTF-8. When a piece of code stored
            # in a unicode string is executed, str objects are utf-8 encoded. 
            # Otherwise they are encoded using __stdin__.encoding. In specific 
            # cases, a non utf-8 encoded str might be succesfully encoded
            # using utf-8, but this is rare. Since I would not
            # know how to tell the encoding beforehand, we'll take our 
            # chances... Note that in IEP (for which this module was created,
            # all executed code is unicode, so str instrances are always
            # utf-8 encoded.
            if isinstance(s, bytes):
                try:
                    s = s.decode('utf-8')
                except UnicodeError:
                    s = s.decode(stdinenc)
            # Push it on the queue            
            message = packMessage('MESSAGE', self._id, s.encode('utf-8'))
            self._q.push( message )
    
    
    def writelines(self, lines):
        """ writelines(lines)
        Write a sequence of messaged to the channel.
        """
        for line in lines:
            self.write(line)
    
    
    def close(self):
        """ close()
        Close the channel, stopping all communication. 
        """
        message = packMessage('CLOSE', self._id)
        self._q.push(message)
        self._closed = True
    
    
    def read(self):
        """ read()
        Cannot be used on a sending channel. """
        raise IOError("Cannot read from a sending channel.")


class ReceivingChannel(BaseChannel):
    """ ReceivingChannel
    An incoming channel to an other process.
    On the other end, there is a corresponding SendingChannel.
    Exposes a text file interface that can be used in blocking,
    non-blocking, and blocking-for-a-specified-time mode.
    """
    
    def __init__(self):
        BaseChannel.__init__(self, Queue())
        self._blocking = False
    
    
    def set_default_blocking(self, block):
        """ set_default_blocking(block)
        Set the default blocking state. 
        """
        if not isinstance(block, (bool,int,float)):
            raise ValueError('Block must be a bool, int, or float.')
        self._blocking = block
    
    
    @property
    def default_blocking(self):
        """ The currently set default blocking state. """ 
        return self._blocking 
    
    
    def read_one(self, block=None):
        """ read_one(block=False)
        Read one string that was send as one from the other end.
        If the channel is closed and all messages are read, returns ''.
        If block is not given, uses the default blocking state.
        If block is False or None, returns '' if no data is available. 
        If block is an int or float, waits that many seconds and then
        returns '' if no data is available. If block is True, waits forever
        until data is available.
        """
        
        # Note: I could make a method of the first part of the read 
        # methods, as it's the same. However, I like to avoid an extra
        # function call.
        
        # Use default block state?
        if block is None:
            block = self._blocking
        elif not isinstance(block, (bool,int,float)):
            raise ValueError('Block must be a bool, None, int, or float.')
        
        # should we block?
        if block:
            if block is True:
                block = 2**32 # over 100 years
            block += time.time()
            pending = self._q.count
            while not pending() and not self._closed and time.time() < block:
                time.sleep(0.01)
        
        # get data, decode, return
        return self._q.pop().decode('utf-8')
    
    
    def read_last(self, block=None):
        """ read_last(block=False)
        Read the last string that was send as one from the other end.
        If the channel is closed and all messages are read, returns ''.
        If block is not given, uses the default blocking state.
        If block is False or None, returns '' if no data is available. 
        If block is an int or float, waits that many seconds and then
        returns '' if no data is available. If block is True, waits forever
        until data is available.
        """
        
        # Use default block state?
        if block is None:
            block = self._blocking
        elif not isinstance(block, (bool,int,float)):
            raise ValueError('Block must be a bool, None, int, or float.')
        
        # should we block?
        if block:
            if block is True:
                block = 2**32 # over 100 years
            block += time.time()
            pending = self._q.count
            while not pending() and not self._closed and time.time() < block:
                time.sleep(0.01)
        
        # get data, decode, return
        return self._q.pop_last().decode('utf-8')
    
    
    def readline(self, size=0):
        """ readline(size=0)
        Read one string that was send as one from the other end. A newline
        character is appended if it does not end with one.
        This method is always blocking.
        If size is given, returns only up to that many characters, the rest
        of the messages is thrown away.
        """
        
        # wait until data is available
        pending = self._q.count
        while not pending() and not self._closed:
            time.sleep(0.01)
        
        # get data, decode, make sure it ends with newline, return
        tmp = self._q.pop().decode('utf-8')
        if not tmp.endswith('\n'):
            tmp += '\n'
        if size:
            tmp = tmp[:size]
        return tmp
        
    
    def read(self, block=False):
        """ read(block=False)
        Read all text available now.
        If the channel is closed and all messages are read, returns ''.
        If block is not given, uses the default blocking state.
        If block is False or None, returns '' if no data is available. 
        If block is an int or float, waits that many seconds and then
        returns '' if no data is available. If block is True, waits forever
        until data is available.
        """
        
        # Use default block state?
        if block is None:
            block = self._blocking
        elif not isinstance(block, (bool,int,float)):
            raise ValueError('Block must be a bool, None, int, or float.')
        
        # should we block?
        if block:
            if block is True:
                block = 2**32 # over 100 years
            block += time.time()
            pending = self._q.count
            while not pending() and not self._closed and time.time() < block:
                time.sleep(0.01)
        
        # get data, decode, return
        tmp = bytes().join( self._q.pop_all() )
        return tmp.decode('utf-8')
    
    
    @property
    def pending(self):
        """ Get the number of pending messages. 
        """
        return self._q.count()
    
    
    def write(self, s):
        """ write(s)
        Cannot be used on a receiving channel. 
        """
        raise IOError("Cannot write to a receiving channel.")
    
    
    def close(self):
        """ close()
        A receiving channel can only be closed from the sending side. 
        """
        raise IOError("Cannot close a receiving channel.")
    
    
    def __iter__(self):
        """ Returns self. """
        return self
    
    
    def next(self):
        """ next()
        Return the next message, or raises StopIteration if non available.
        """
        m = self.read_one(False)
        if m:
            return m
        else:
            raise StopIteration()


class Channels(object):
    """ Channels(number_of_sending_channels)
    
    A Channels instance is an object that represents a communication 
    interface between two processes, possibly on different machines.
    There can be multiple sending channels, and multiple 
    receiving channels. From each end, you can only chose the 
    number of sending channels (max 128).
    
    When the connection is closed, the callable attribute "disconnectCallback"
    is called with the reason as an argument. By default it calls
    a function that prints the reason. It can be set to None to call
    nothing.
    
    For more information, see the docstrings of this module 
    and the docstrings of the channel classes.
    """
    
    def __init__(self, N, canBeInterrupted=False, canBeKilled=False):
        
        # test
        if N<0 or N>127:
            raise IndexError("Invalid number of channels.")
        
        # store what other end is allowed to do
        self._canBeInterrupted = canBeInterrupted
        self._canBeKilled = canBeKilled
        
        # create channel lists        
        self._sendingChannels = []
        self._receivingChannels = []
        
        # lock and queue for special stuff
        self._lock = threading.RLock()
        self._q = Queue()
        
        # create sending channels now
        for id in range(N):
            self._sendingChannels.append( SendingChannel(self._q, id) )
        
        # port being used
        self._port = 0
        
        # callback to call when connection closes
        self.disconnectCallback =  self._default_disconnect_callback
    
    
    def _reopen_all_channels(self):
        """ _reopen_all_channels()
        Re-open all channels. To clean up when re-hosting. """
        for channel in self._sendingChannels:
            channel._closed = False
        for channel in self._receivingChannels:
            channel._closed = False
    
    
    def host(self, port='Channels', portRange=100, hostLocal=True):
        """ host(port='Channels', portRange=100, hostLocal=True)
        
        Host a channel. This means this side of the channel
        opens a socket that the process at the other end of the 
        channel can nonnect to. Returns the port it is connected to.
        
        The port should be an integer between 1024 and 2**16. A 
        (string) name can also be given, from which a port number 
        is derived via a hash. The default is 'Channels', which
        corresponds to 61718.
        
        With portRange the number of ports to try can be specified.
        Starting from the given port, subsequent ports are tried
        until a free slot is available. If you only want to try 
        one port, set this to 1.
        
        If hostLocal is true, the socket is only visible from this
        computer. Also some low level networking layers are bypassed,
        which results in a faster connection. If set to false, 
        processes from other computers can also connect.
        
        """ 
        
        # check if already connected. if so, raise error
        if self.is_connected:
            raise RuntimeError("Cannot host, already connected.")
        
        # clean up
        self._reopen_all_channels()
        
        # determine host
        host = 'localhost'
        if not hostLocal:
            host = socket.gethostname()
        
        # create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # determine port
        
        # port given as string?
        if isinstance(port, basestring):
            port = portHash(port)
        
        # check port validity
        if not isinstance(port, (int, long)):
            raise ValueError("The port should be a string or an int.")
        if port < 1024 or port > 2**16:
            raise ValueError("The port must be in the range [1024, 2^16>.")
        
        # try all ports in the specified range
        for port2 in range(port,port+portRange):
            try:
                s.bind((host,port2))
                break
            except Exception:
                continue
        else:
            tmp = str(portRange)
            tmp = "Could not bind to any of the " + tmp + " ports tried."
            raise IOError(tmp)
        
        # tell the socket it is a host
        s.listen(1)
        
        # store port number
        self._port = s.getsockname()[1]
        
        # start thread ...  
        # Make it a deamon thread, which implies that the program exits
        # even if its running.
        self._doorman = Doorman(self, s, host=True)
        self._doorman.daemon = True
        self._doorman.start()
        
        # return port
        return self._port
    
    
    def connect(self, port, host='localhost', timeOut=1):
        """ connect(self, port, host='localhost', timeOut=1)
        
        Connect to a channel being hosted by another process.
        The port number should match that of the port number returned
        by the host() method or port property called on the other side. 
        
        Increase the timeout to wait a bit longer (maybe the host needs 
        to start up some stuff).
        """
        
        # check if already connected. if so, raise error
        if self.is_connected:
            raise RuntimeError("Cannot connect, already connected.")
        
        # clean up
        self._reopen_all_channels()
        
        # create socket
        self._s = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # port given as string?
        if isinstance(port, basestring):
            port = portHash(port)
        
        # check port validity
        if not isinstance(port, (int, long)):
            raise ValueError("The port should be a name or an int.")
        if port < 1024 or port > 2**16:
            raise ValueError("The port must be in the range [1024, 2^16>.")
        
        # refuse rediculously low timeouts
        if timeOut<= 0.01:
            timeOut = 0.01
        
        # try to connect
        ok = False
        t1 = time.time() + timeOut
        while not ok and time.time()<t1:
            try:
                s.connect((host,port))
                ok = True
            except socket.error:
                pass
        
        # did it work?
        if not ok:
            raise IOError("Could not connect to %s on %i." % (host, port))
        else:
            self._port = port
        
        # start thread
        # Make it a deamon thread, which implies that the program exits
        # even if its running.
        self._doorman = Doorman(self, s)
        self._doorman.daemon = True
        self._doorman.start()
    
    
    def disconnect(self):
        """ disconnect()
        Close the connection. This also closes all channels. """
        self._doorman._stopMe = "Closed from this end."
    
    
    def get_receiving_channel(self,i):
        """ get_receiving_channel(i)
        Get the i'th receiving channel. The other end choses how
        many such channels there are. You can always get up to 128 
        receiving channels, but you just might never receive data 
        on them.
        This method is thread-safe, and you can get the channel 
        even before the other side is connected.
        """
        # test
        if i<0 or i>128:
            raise IndexError("Invalid channel index.")
        # create required channels on the fly
        self._lock.acquire()
        try:
            while len(self._receivingChannels) <= i:
                self._receivingChannels.append(ReceivingChannel())
            # return
            tmp = self._receivingChannels[i]
        finally:
            self._lock.release()
        return tmp
    
    
    def get_sending_channel(self,i):
        """ get_sending_channel(i)
        Get the i'th sending channel. The number i must be between
        0 and N-1, with N the number of output channels chosen when
        this Channels object was created.
        This method is thread-safe.
        """
        # test
        if i<0 or i>len(self._sendingChannels):
            raise IndexError("Invalid channel index.")
        # return
        self._lock.acquire()
        tmp = self._sendingChannels[i]
        self._lock.release()
        return tmp

    
    @property
    def port(self):
        """ The port number in use, or 0 if not connected. """
        return self._port
    
    
    @property
    def is_connected(self):
        """ Whether the channel is connected. """
        return self._port > 0
    
    
    @property
    def is_host(self):
        """ Whether this instance is connected and hosting. """
        return self._port>0 and self._doorman._host==True
    
    
    @property
    def is_client(self):
        """ Whether this instance is connected and not hosting. """
        return self._port>0 and self._doorman._host==False
    
    
    def interrupt(self):
        """ interrupt()
        Interrupt the main thread of the process at the other side.
        """
        self._q.push( packMessage('INT') )
    
    
    def kill(self):
        """ kill()
        Kill the process at the other side. The connection needs to be
        open for this to work though.
        """
        self._q.push( packMessage('KILL') )
    
    
    @property 
    def can_be_killed(self):
        """ Whether the other end is allowed to kill this process."""
        return self._canBeKilled
    
    
    @property
    def can_be_interrupted(self):
        """ Whether the other end is allowed to interrupt this process."""
        return self._canBeInterrupted
    
    
    
    def _default_disconnect_callback(self, why):
        print("Connection closed: " + why)


class Doorman(threading.Thread):
    """ Doorman(channels, socket, host=False)
    The thread that keeps making sure data is 
    send and received to/from the other process. 
    """
    
    def __init__(self, channels, socket, host=False):
        threading.Thread.__init__(self)
        
        # store references
        self._channels = channels
        self._socket = socket
        self._host = host
        
        # flag to stop the mainloop (and why)
        self._stopMe = False
        
        # buffers for received and send bytes (incomplete messages)
        self._receiveBuffer = bytes()
        self._sendBuffer = bytes()
        
        # store queues of receiveChannels (for efficient pushing of messages)
        self._receiveQueues = []
    
    
    def run(self):
        """ run()
        Start the thread. """
        
        # If hosting, wait for a connection.
        # The socket is replaced by the returned (connecting) socket.
        # The thread will wait here until someone connects.
        if self._host:
            s, addr = self._socket.accept()
            self._socket.close()
            self._socket = s
        
        # Init timers and counters
        t0 = time.time() # temporary variable to hold current time
        ts = t0 # the last time we sent something (if >0.5s we send NOOP)
        tr = t0 # the last time we received something (to detect unresponsive)
        n_unresponsive = 0 # number of times found unresponsive
        
        
        # enter main loop
        try:
            while True:
                
                # should we stop?
                if self._stopMe:
                    break
                
                # pitch messages
                sentSomething = self.pitch()
                
                # should we pitch a noop?
                t0 = time.time()
                if sentSomething:
                    ts = t0
                elif t0 - ts > 0.5:
                    self._channels._q.push( packMessage('NOOP') )
                    ts = t0
                
                # catch messages
                receivedSomething = self.catch()
                
                # Check if other side is still responding. This can really
                # only happen when the other end's thread is stuck. So we're
                # carefull not to give up too soon.
                t0 = time.time()
                if receivedSomething:
                    tr = t0 # we got something!
                    n_unresponsive = 0
                elif t0 - tr > 1.0:
                    tr = t0
                    n_unresponsive += 1
                    if n_unresponsive > 5:
                        self._stopMe = "Other side is unresponsive."
                
                
                # Determine time to rest. By default we sleep for 0.01 second.
                # But when sending or receiving, we go in super mode, pumping 
                # messages like crazy :)
                if receivedSomething or sentSomething:
                    time.sleep(0.000001) # corresponds with 1Mhz
                else:
                    time.sleep(0.01) # corresponds with 100Hz
                    # Sleeping 0.001 sec results in 0% processing power on my
                    # 3.5 year old laptop, so 0.01 sec should be ok.
            
            # close all receiving channels
            for i in range(len(self._channels._receivingChannels)):
                channel = self._channels.get_receiving_channel(i)
                channel._closed = True
            
            # close all sending channels too
            for i in range(len(self._channels._sendingChannels)):
                channel = self._channels.get_sending_channel(i)
                channel._closed = True
            
            # clean up
            self._socket.close()
            self._channels._port = 0
            if self._channels.disconnectCallback:
                self._channels.disconnectCallback(self._stopMe)
        
        except Exception:
            # Not much we can do.
            pass 
    
    
    def pitch(self):
        """ pitch()
        Send all messages from the queue.
        Returns amount of sent messages/bytes. """
        
        # Flush the whole queue if we have send everything so far.
        if not self._sendBuffer:
            tmp = self._channels._q.pop_all()
            n = len(tmp)
            tmp.append(bytes())
            self._sendBuffer = DELIMITER.join(tmp)
        
        # Try to send what we can. Do not use sendall, otherwise the thread
        # would wait here until the other side receives.
        nb = 0
        if self._sendBuffer:
            try:
                nb = self._socket.send( self._sendBuffer )
                self._sendBuffer = self._sendBuffer[nb:]
            except socket.error:
                self._stopMe = 'Other end dropped.'
        
        # done
        return nb
    
    
    def receive_messages(self):
        """ receive_messages()
        Receive data from the socket, devide in messages using the
        delimiter and return the available messages as a list.
        """
        
        # init list of blocks
        blocks = [self._receiveBuffer]
        
        # receive what we can
        while True:
        
            # test whether there is something to receive
            l1,l2,l3 = select([self._socket],[],[],0)
            if not l1:
                break
            
            # receive data
            try:
                tmp = self._socket.recv(BUFFERSIZE)
            except socket.error:                
                self._stopMe = 'Other end dropped.'
                break
            
            # check if connection is closed
            if len(tmp) == 0:
                self._stopMe = "Closed from other end."
                break
            
            # store block
            blocks.append(tmp)
        
        # make one large string of bytes
        data = bytes().join(blocks)
        
        # and split in messages
        messages = data.split(DELIMITER)
        
        # store last bit (which is always empty bytes or an incomplete message)
        self._receiveBuffer = messages.pop()
        
        # return all whole messages
        return messages
    
    
    def catch(self):
        """ catch()
        Catch data. First the header is catched as one part.
        The info (channel and length) is stored in case 
        the message itself cannot be received this call.
        """
        
        # receive what we can now
        messages = self.receive_messages()
        n = len(messages)
        
        # The M in MESSAGE, as a byte element
        M = 'M'.encode('ascii')
        
        while messages:
            
            # Try getting a list of messages for the same channel
            # This has a small performance reduction when messages are
            # not in a row, but it significantly improves performance
            # when multiple messages for the same channel are send in a
            # row.
            i = 0
            id = ord( messages[0][7:8] ) # get id of first     
            for i in range(len(messages)):
                mes = messages[i]
                if (not ord(mes[7:8])==id) or (not mes[0:1]==M):
                    break
            
            # select these messages, or first message if not a list
            if i>1:
                bb = [mes[8:] for mes in messages[:i]]
                messages[:i] = []
                type = 'MESSAGE'
            else:
                message = messages.pop(0)
                type, id, bb = unPackMessage(message)
            
            # check and process
            
            if type == 'MESSAGE':
                # get channel and its queue
                while len(self._receiveQueues) <= id:
                    i2 = len(self._receiveQueues)
                    channel = self._channels.get_receiving_channel(i2)
                    self._receiveQueues.append(channel._q)
                q = self._receiveQueues[id]
                # put message it in the queue
                if isinstance(bb,list):
                    q.push_more(bb)
                else:
                    q.push(bb)
            
            elif type == 'NOOP':
                # other end just let us know it's still there
                pass
            
            elif type == 'CLOSE':
                # close a channel
                channel = self._channels.get_receiving_channel(id)
                channel._closed = True
            
            elif type == 'INT':
                # interrupt main thread, if allowed
                if self._channels._canBeInterrupted:
                    thread.interrupt_main()
            
            elif type == 'KILL':
                # kill this process, if allowed
                if self._channels._canBeKilled:
                    pid = os.getpid()
                    if hasattr(os,'kill'):
                        import signal
                        os.kill(pid,signal.SIGTERM)
                    elif sys.platform.startswith('win'):
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        handle = kernel32.OpenProcess(1, 0, pid)
                        kernel32.TerminateProcess(handle, 0)
                        #os.system("TASKKILL /PID " + str(os.getpid()) + " /F")
                    time.sleep(0.1)
            
            else:
                # This is bad ...
                self._stopMe = "Lost track of the stream."
        
        # done
        return n


# stuff below is for testing

if 0:
    channels.disconnect()
## here

    channels = Channels(2)
    port = channels.host('IEP'); print(port)
    r1 = channels.get_receiving_channel(0)
    s1 = channels.get_sending_channel(0)
    s2 = channels.get_sending_channel(1)
    
    s1.write("I am channel one")
    s2.write("And I am channel two.")

## there
    
    channels = Channels(1)
    channels.connect('IEP')
    r1 = channels.get_receiving_channel(0)
    r2 = channels.get_receiving_channel(1)
    s1 = channels.get_sending_channel(0)
    time.sleep(0.5)
    print( r1.read())
    print( r2.read())

## testing (receiving end)
    
    times = []
    tmp = r1.read(False) # flush
    while True:
        tmp = r1.read_one()
        if tmp == 'stop':
            break
        if tmp:
            t = float( tmp.split(' ')[0] )
            dt = time.time() - t
            times.append(dt)
    step = int(len(times)/20)+1
    print( ['%1.3f'%t for t in times[::step] ] )
    

## testing (sending end): multiple small messages
    for i in range(10000):
        s1.write(str(time.time()) + ' testing '*10 + str(i))
    s1.write('stop')


## testing (sending end): One huge message
    for i in range(2):
        s1.write(str(time.time()) + ' testing ' + "a"*1000000)
    s1.write('stop')
