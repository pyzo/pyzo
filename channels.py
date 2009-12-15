""" Module channels

Multichannel unicode and bytes interprocess communication via sockets.

Using a biderectional channel, this module realizes a nonblocking 
interface for multiple channels, to communicate packages of unicode 
strings or bytes.

This module can be imported in Python 2 ad well as in Python 3. It 
implements the Channels object, which represents the connection to
the other end. It has methods to obtain SendingChannel and 
ReceivingChannel objects, which are used to actually send and receive
strings (or bytes). 

The write(), read() and readOne() methods all accept/return strings
(str or unicode for Python 2, str for Python 3). The writeBytes(),
readBytes() and readOneBytes() methods accept/return bytes objects
(str for Python2, bytes for Python 3). When wanting to send bytes,
we advice to reserve a separate channel that only uses the byte-methods
on both ends.


Here's an example:
------------------

# On one side:
import channels
c = channels.Channels(1) # create channels object with one sending channel
c.host('channels_example') # host (determine port by hashing a string)
s1 = c.getSendingChannel(0)
r1 = c.getReceivingChannel(0)
r2 = c.getReceivingChannel(1)

# write something. This will be send as soon as the other side is connected.
s1.write('hello there')
# read all packages received until now (returns '' if none available)
r1.read()
# read a single package (block until one is available)
r2.readOne(True) 


# On other side:
import channels
c = channels.Channels(2) # create channels object with two sending channels
c.connect('channels_example') # connect (determine port by hashing same string)
s1 = c.getSendingChannel(0)
s2 = c.getSendingChannel(1)
r1 = c.getReceivingChannel(0

s1.write('This is channel one')
s2.write('This is channel two')
r1.readOne()

"""

# Implementation details
#
# The data is send bidirectional (using both directions of the socket.
# One by one the sending channels are allowed to send one package.
# On the other end, packages are received and (when complete) dropped
# at the right receiving channel object.
#
# Each package starts with a header of 16 bytes: 
# 7 bytes for marker (just in case) ascii CHANNEL 
# 1 bytes for channel id (uint8)
# 8 bytes for N (nr of bytes of the package) (uint64 little endian)
#
# After the header, N bytes follow. Strings are converted to bytes using
# UTF-8 encoding.
# 
# There are some other messages that can be send. They consist of only
# a (16 byte) header, which starts with a length-7 ASCII encoded string:
# - NOOP: no operation, to let the other end know we are still there
# - CLOSE: close the connection (and all channels)
# - INT: interrupt the main thread of the other process
# - KILL: kill the other process

import os,sys
import time
import socket
from select import select  # to determine wheter a socket can receive data
import threading
try:
    import thread # Python 2
except ImportError:
    import _thread as thread # Python 3


# version dependant defs
V2 = sys.version_info[0] == 2
if V2:
    bytes, str = str, unicode
else:
    basestring = str  # to check if instance is string
    long = int # for the port


def makeHeader(type='CHANNEL', id=0, N=0):
    """ makeHeader(type, id=None, N=None)
    Build a header to send. Returns a bytes object.
    - type must be a max 7 elements ASCII string.
    - id must be an int between 0 and 255 (indicating channel id)
    - N must be an int betwen 0 and 2**64 (indicating message length)
    """
    
    # encode type (and justify)
    header_b = type.encode('ascii')
    header_b = header_b.ljust(7)
    
    # encode id
    if V2:
        header_b += chr(id)
    else:
        header_b += bytes([id])
    
    # encode N
    bb = []
    nchars = 8
    for i in range(nchars):
        i = nchars-i-1
        b  = int(N / 2**(i*8))
        N = N % 2**(i*8)
        bb.append(b)
    if V2:
        header_b += ''.join([chr(i) for i in bb])
    else:
        header_b += bytes(bb)
    
    # done
    return header_b
    

def getHeader(header):
    """getHeader(header)
    Get the header data from the 16 header bytes.
    Return tuple (type [str], id [int], N [int])
    """
    
    # decode type
    type = header[:7].decode('ascii').strip()
    
    # decode id
    if V2:
        id = ord(header[7])
    else:
        id = header[7]
    
    # decode N
    N = 0
    if V2:
        bb = [ord(i) for i in header[8:]]
    else:
        bb = [i for i in header[8:]]
    nchars = 8
    for i in range(nchars):
        b = bb[nchars-i-1]
        N += b * 2**(i*8)
    
    # done
    return type, id, N


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
    
    
class Queue:
    """ Queue
    Very simple non-blocking thread save queue class. 
    q.pop() returns None if the queue is empty. 
    You can add any object to the queue, except None, since that
    would interfere with the above. """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._data = []
    
    def push(self, value):
        """ push(object)
        Push an object to the queue. 
        If None, nothing is pushed. """
        if value is None:
            return
        self._lock.acquire()
        try:
            self._data.insert(0,value)
        finally:
            self._lock.release()
    
    def pop(self):
        """ pop()
        Pops an object from the queue. 
        If the queue is empty, returns None. """
        self._lock.acquire()
        try:
            if len(self._data)==0:
                tmp = None
            else:
                tmp = self._data.pop()
        finally:
            self._lock.release()
        return tmp

    

class BaseChannel(object):
    """ BaseChannel
    Abstract class for the input and output channel. 
    
    Each channel has a queue in which the pending messages are stored.
    At the sending side they are waiting to be send, and at the receiving
    side they are received but not yet queried. 
    
    In other words:
    The doorman of the Channels object pops the messages from the queue 
    and sends them over the channel. The doorman at that side receives 
    the mesage and puts it in the queue of the corresponding input channel, 
    where the data is available via the read methods.    
    """
    
    def __init__(self):
        self._q = Queue()
        self._closed = False
    
    @property
    def closed(self):
        return self._closed


class SendingChannel(BaseChannel):
    """ SendingChannel
    An outgoing channel to an other process. 
    On the other end, this is a ReceivingChannel.
    Exposes a non-blokcing text file interface.
    """
    
    def write(self, s):
        """ write(s)
        Write a string to the channel. The string is encoded using
        utf-8 and then send over the binary channel. When the string
        is empty, the call is ignored.
        """
        if not isinstance(s,basestring):
            raise ValueError("SendingChannel.write only accepts strings.")
        if s:
            self._q.push( s.encode('utf-8') )
    
    def writeBytes(self, b):
        """ writeBytes(b)
        Write bytes to the channel. Note that these should probably
        received on the other using readBytes, since decoding arbitrary
        byte data can easily result in decoding errors.
        Therefore: use with care. """
        if not isinstance(b,bytes):
            raise ValueError("SendingChannel.writeBytes only accepts bytes.")
        if b:
            self._q.push(b)
    
    
    def close(self):
        """ close()
        Close the channel, stopping all communication. """
        self._closed = True
    
    
    def read(self):
        """ read()
        Cannot be used on a sending channel. """
        raise IOError("Cannot read from a sending channel.")


class ReceivingChannel(BaseChannel):
    """ ReceivingChannel
    An incoming channel to an other process.
    On the other end, this is a SendingChannel.
    Exposes a text file interface that can be used in blocking
    and non-blocking mode.
    """
    
    def __init__(self):
        BaseChannel.__init__(self)
        self._blocking = False
    
    
    def setBlocking(self, blocking=True):
        """ setBlocking(blocking=True)
        Set the default blocking state. 
        """
        self._blocking = blocking
    
    
    @property
    def isBlocking(self):
        return self._blocking 
    
    
    def readOneBytes(self, block=None):
        """ readOneBytes(block=None)
        Read bytes that were send as one package from the other end. 
        If channel is closed, returns empty bytes.
        If block is not given, uses the default blocking state.
        If not blocking, returns empty bytes if no data is available.
        If blocking, waits until data is available. 
        """
        # if closed, return nothing
        if self._closed:
            return bytes()
        
        # use default block state?
        if block is None:
            block = self._blocking
        if block and not isinstance(block,(int,float)):
            block = 2**30
        
        # get data, return empty bytes if queue is empty
        tmp = self._q.pop()
        if block:
            t0 = time.time()
            while tmp is None and (time.time()-t0) < block:
                if self._closed:
                    break
                time.sleep(0.01)
                tmp = self._q.pop()
        
        # return
        if not tmp:
            return bytes()
        else:
            return tmp
    
    
    def readBytes(self, block=False):
        """ readBytes(block=False)        
        Read all available bytes from the channel. 
        If channel is closed, returns empty bytes.
        If block is not given, uses the default blocking state.
        If not blocking, returns empty bytes if no data is available.
        If blocking, waits until data is available.
        """
        
        # if closed, return nothing
        if self._closed:
            return bytes()
        
        # get one package, use given blocking
        b = self.readOneBytes(block)
        
        # get more packages if available
        tmp = True
        while tmp:
            tmp = self.readOneBytes(False)
            b += tmp
        
        # done
        return b
    
    
    def readOne(self, block=False):
        """ readOne(block=False)
        Read one string that was send as one package from the other end.
        The binary package is decoded using utf-8 encoding. Raises an error 
        if decoding fails, thus losing the message. (If using the unicode 
        write methods from the other end, there is nothing to worry about.)
        If the channel is closed, returns None.        
        If block is not given, uses the default blocking state.
        If not blocking, returns None if no data is available.
        If blocking, waits until data is available.
        """
        b = self.readOneBytes(block)
        return b.decode('utf-8')
    
    
    def read(self, block=False):
        """ read(block=False)
        Read all text available now. Raises an error if decoding fails, 
        thus losing the message.
        If the channel is closed, returns an empty string.        
        If block is not given, uses the default blocking state.
        If not blocking, returns an empty string if no data is available.
        If blocking, waits until data is available.
        """
        b = self.readBytes()
        return b.decode('utf-8')
    
    
    def write(self, s):
        """ write(s)
        Cannot be used on a receiving channel. """
        raise IOError("Cannot write to a receiving channel.")
    
    def close(self):
        """ close()
        A receiving channel can only be close from the sending side. """
        raise IOError("Cannot close a receiving channel.")


class Channels(object):
    """ Channels(number_of_sending_channels)
    
    A Channels instance is an object that represents a communication 
    interface between two processes, possibly on different machines.
    There can be multiple sending channels, and multiple 
    receiving channels. From each end, you can only chose the 
    number of sending channels (max 255).
    
    For more info, see the docstrings of this module and the docstrings
    of the channel classes.
    """
    
    def __init__(self, N):
        
        # test
        if N<0 or N>255:
            raise IndexError("Invalid amount of channels.")
        
        # create channel lists        
        self._sendingChannels = []
        self._receivingChannels = []
        
        # create output channels now
        for i in range(N):
            self._sendingChannels.append( SendingChannel() )
        
        # lock and queue for special stuff
        self._lock = threading.RLock()
        self._q = Queue()
        
        # port being used
        self._port = 0
        
        self._test = True
    
    
    def _reOpenAllChannels(self):
        """ _reOpenAllChannels()
        Re-open all channels. To clean up when re-hosting. """
        for channel in self._sendingChannels:
            channel._closed = False
        for channel in self._receivingChannels:
            channel._closed = False
    
    
    def host(self, port=None, hostLocal=True):
        """ host(self, port=None, hostLocal=True)
        
        Host a channel. This means this side of the channel
        opens a socket that the process at the other end of the 
        channel can nonnect to. Returns the port it is connected to.
        
        If hostLocal is true, the socket is only visible from this
        computer. Also some low level networking layers are bypassed,
        which results in a faster connection. If set to false, 
        processes from other computers can also connect.
        
        The port should be an integer between 1024 and 2**16. A 
        (string) name can also be given, from which a port number 
        is derived via a hash. If no port number is given, the first
        free slot of a series of 100 ports is used.
        """ 
        
        # check if already connected. if so, raise error
        if self.isConnected():
            raise RuntimeError("Cannot host, already connected.")
        
        # clean up
        self._reOpenAllChannels()
        
        # determine host
        host = 'localhost'
        if not hostLocal:
            host = socket.gethostname()
        
        # create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # determine port
        
        if not port: 
            # automatically generate port and try multiple
            
            # generate port number
            tmp = portHash("Channels")
            # iterate untill we find a free slot
            for port in range(tmp,tmp+100):
                try:
                    s.bind((host,port))
                    break
                except Exception:
                    continue
            else:
                raise IOError("Could not bind to any of the 100 ports tried.")
        else:
            # try connecting with given port
            
            # port given as string?
            if isinstance(port, basestring):
                port = portHash(port)
            # check port validity
            if not isinstance(port, (int, long)):
                raise ValueError("The port should be a name or an int.")
            if port < 1024 or port > 2**16:
                raise ValueError("The port must be in the range [1024, 2^16>.")
            # try connecting
            try:
                s.bind((host,port))
            except Exception:
                raise IOError("Could not bind to the given port.")
        
        # tell the socket it is a host
        s.listen(1)
        
        # store port number
        self._port = s.getsockname()[1]
        
        # start thread ...  (make on: the program exits even if its running)
        self._doorman = Doorman(self, s, host=True)
        self._doorman.daemon = True
        self._doorman.start()
        
        # return port
        return self._port
    
    
    def connect(self, port, host='localhost', timeOut=1):
        """ connect(self, port, host='localhost', timeOut=1)
        
        Connect to a channel being hosted by another process.
        The port number should match that of the port number returned
        by the host() or getPort() method called on the other side. 
        
        Increase the timeout to wait a bit longer (maybe the host needs 
        to start up some stuff).
        """
        
        # check if already connected. if so, raise error
        if self.isConnected():
            raise RuntimeError("Cannot connect, already connected.")
        
        # clean up
        self._reOpenAllChannels()
        
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
        self._doorman = Doorman(self, s)
        self._doorman.daemon = True
        self._doorman.start()
    
    
    def disconnect(self):
        """ disconnect()
        Close the connection. This also closes all channels. """
        self._doorman._stopMe = "Closed from this end."
    
    
    def getReceivingChannel(self,i):
        """ getReceivingChannel(i)
        Get the i'th receiving channel. The other end choses how
        many such channels there are. You can always get up to 256 
        receiving channels, but you just might never receive data 
        on them.
        This method is thread-safe, and you can get the channel 
        even before the other side is connected.
        """
        # test
        if i<0 or i>255:
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
    
    
    def getSendingChannel(self,i):
        """ getSendingChannel(i)
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

    
    def getPort(self):
        """ getPort()
        Get the port number in use, or 0 if not connected. """
        return self._port
    
    
    def isConnected(self):
        """ isConnected()
        Return self.getPort() > 0. """
        return self._port > 0
    
    
    def isHost(self):
        """ isHost()
        Returns True if this object is connected and hosting. """
        return self._port>0 and self._doorman._host==True
    
    
    def isClient(self):
        """ isClient()
        Returns True if this object is connected and not hosting. """
        return self._port>0 and self._doorman._host==False
    
    
    def getStats(self):
        """ getStats()
        Get statistics as a 3-element tuple: 
        (iters_per_second, n_send, n_recv)
        """
        dm = self._doorman
        return dm._ips, dm._n_send, dm._n_recv
    
    
    def interrupt(self):
        """ interrupt()
        Interrupt the main thread of the process at the other side.
        """
        self._q.push(bytes('INT'))
    
    
    def kill(self):
        """ kill()
        Kill the process at the other side. The connection needs to be
        open for this to work though.
        """
        self._q.push(bytes('KILL'))



class Doorman(threading.Thread):
    """ Doorman
    The thread that keeps making sure data is 
    send and received to/from the other process. 
    """
    
    def __init__(self, channels, socket, host=False):
        threading.Thread.__init__(self)
        
        # store references
        self._channels = channels
        self._socket = socket
        self._host = host
        
        # flag to stop
        self._stopMe = False
        
        # buffer for input, message props (channel, length)
        self._buffer = bytes()
        self._message = None
        
        # vars to test whether the other side is still there
        self._tin = 0
        self._nmiss = 0
        
        # for statistics
        self._ips = 0           # iterations per second
        self._n_send = 0        # number of send packages
        self._n_recv = 0        # number of received packages
    
    
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
        
        # init unresponsive measure
        self._tin = time.time()
        
        # init other timers and counters
        t0 = time.time() # the start of an iteration
        t1 = t0 # the end of an iteration
        ts = t0 # the last time we sent something (if >0.5s we send NOOP)        
        niter = 0 # count the number of iterations
        tips = t0 # timer to determine iterations per second
        
        # ids of channels to send messages of
        channelIds = range( len(self._channels._sendingChannels) )
        
        # enter main loop
        while True:
            
            # should we stop?
            if self._stopMe:
                break
            
            # catch messages
            self.catch()
            
            # pitch any messages
            # if the channel is closed from this side, send a close message
            # and never try sending again...
            sendSomething = False
            for id in reversed(channelIds):
                channel = self._channels.getSendingChannel(id)
                sendSomething = sendSomething or self.pitchMessage(channel, id)
                if channel._closed:
                    self.pitchClose(id)
                    channelIds.remove(id)
            
            # check whether we should pitch other stuff
            s = self._channels._q.pop()
            if s is not None:
                if s=='KILL':
                    self.pitchKill()
                elif s=='INT':
                    self.pitchInterrupt()
            
            # end of iteration
            t1 = time.time()
            
            # should we pitch a noop?
            if sendSomething:
                ts = t1
            elif t1-ts > 0.5:
                self.pitchNoop()
                ts = t1
                
            # determine time to rest
            trest = max(0.01 - (t1-t0), 0.001)
            time.sleep(trest)
            
            # prepare for next iter
            t0 = time.time()
            
            # produce statistics
            if niter > 99:
                tmp = time.time()
                self._ips = niter / (tmp-tips)
                niter, tips = 0, tmp
            niter += 1
        
        # close all channels
        for i in range(len(self._channels._receivingChannels)):
            channel = self._channels.getReceivingChannel(i)
            channel._closed = True
        
        # clean up
        self._socket.close()        
        print("Connection closed: " + self._stopMe)
        self._channels._port = 0
    
    
    ## send methods
    
    def pitchMessage(self, channel, id):
        """ pitchMessage(channel, id)
        Send a message from the queue of the given channel with id.
        Returns True if indeed a message was available and send. """
        # get channel queue
        q = channel._q
        # check if something to send, if not return
        b = q.pop()
        if b is None:
            # ok, maybe we should just say hello?
            return False              
        else:
            # compose header and send
            header = makeHeader('CHANNEL', id, len(b))
            self._socket.sendall( header )
            # send data            
            self._socket.sendall(b)
            # stats
            self._n_send += 1
            return True
    
    
    def pitchClose(self,id):
        """ pitchClose(id)
        Close a channel. """
        header = makeHeader('CLOSE', id)
        self._socket.sendall( header )
    
    
    def pitchKill(self):
        """ pitchKill()
        Kill the process at the other end. """
        header = makeHeader('KILL')
        self._socket.sendall( header )
    
    
    def pitchInterrupt(self):
        """ pitchInterrupt()
        Interrupt the main thread at the other end. """
        header = makeHeader('INT')
        self._socket.sendall( header )
    
    
    def pitchNoop(self):
        """ pitchNoop()
        Send a no-operation signal to let the other end
        know we're still there. """
        header = makeHeader('NOOP')
        self._socket.sendall( header )
    
    ## receive methods
    
    def receiveBytes(self,N):
        """ receiveBytes(N)
        Receive N Bytes, or return None if that is not possible.
        A buffer is kept with the received data. It is returned only
        if enough data is available.
        """
        # quick test
        l1,l2,l3 = select([self._socket],[],[],0)
        if not l1:
            return None
        
        data = self._buffer
        while len(data) < N:
            # receive data
            try:
                tmp = self._socket.recv(N-len(data))
            except socket.error:
                self._stopMe = "Other end dropped."
                break
            # check if connection is closed
            if len(tmp) == 0:
                self._stopMe = "Closed from other end."
                break
            # append to buffer
            data += tmp
            # can we receive more?
            l1,l2,l3 = select([self._socket],[],[],0)
            if not l1:
                break  # nothing to receive
        # return?
        if len(data) == N:
            self._buffer = bytes()
            return data
        else:
            self._buffer = data
            return None
    
    
    def catch(self):
        """ catch()
        Catch data. First the header is catched as one part.
        The info (channel and length) is stored in case 
        the message itself cannot be received this call.
        """
        
        
        # check if other side is still responding
        if time.time() - self._tin > 1.0:
            self._nmiss += 1
        else:
            self._nmiss = 0
        if self._nmiss > 5:
            self._stopMe = "Other side is unresponsive."
        
        # get header
        if not self._message:
            # get header
            data = self.receiveBytes(16)            
            if not data:
                return
            type, id, N = getHeader(data)
            # we got something! 
            self._tin = time.time()
            # check
            if type == 'NOOP':
                pass
            elif type == 'CHANNEL':
                self._message = id, N
            elif type == 'CLOSE':
                channel = self._channels.getReceivingChannel(id)
                channel._closed = True
            elif type == 'INT':
                self.catchInterrupt()
            elif type == 'KILL':
                self.catchKill()
            else:
                self._stopMe = "Lost track of stream."
        
        # process message
        if self._message:
            i, N = self._message
            # try to get message            
            b = self.receiveBytes(N)
            if not b:
                return
            # get channel and its queue
            channel = self._channels.getReceivingChannel(i)
            q = channel._q
            # put message it in the queue            
            q.push(b)
            # finish
            self._message = None
            self._n_recv += 1
    
    
    def catchInterrupt(self):
        """ catchInterrupt()
        Process a received interrupt command. """
        thread.interrupt_main()
        
        
    def catchKill(self):
        """ catchKill()
        Process a received kill command. """     
        pid = os.getpid()
        if hasattr(os,'kill'):
            import signal
            os.kill(pid,signal.SIGTERM)
            time.sleep(1)
        elif sys.platform.startswith('win'):
            os.system("TASKKILL /PID " + str(os.getpid()) + " /F")


if 0:
##
    import subprocess

    module = 'c:/projects/PYTHON/test_channels.py'
    p = subprocess.Popen('python '+module, 1024*10, None, 
        stdin=subprocess.PIPE, stdout=subprocess.PIPE )
    
    channels = Channels(1, p.stdin, p.stdout)
    c1 = channels.getSendingChannel(0)
    c2 = channels.getReceivingChannel(0)
    
    c1.write("hello")
    print(c2.read())

## here

    channels = Channels(2)
    port = channels.host('IEP'); print(port)
    i1 = channels.getReceivingChannel(0)
    o1 = channels.getSendingChannel(0)
    o2 = channels.getSendingChannel(1)
    
    o1.write("I am channel one")
    o1.write("hello there!")
    o2.write("And I, dear sir, am channel two.")
    o2.write("Nice meeting you.")

## there
    
    channels = Channels(1)
    channels.connect('IEP')
    i1 = channels.getReceivingChannel(0)
    i2 = channels.getReceivingChannel(1)
    o1 = channels.getSendingChannel(0)
    print( i1.read())
    print( i1.read())
    print( i2.read())
    print( i2.read())

## test
    c = Channels(1)
    c.host()
    s = c.getSendingChannel(0)
    s.write('vette shizzle')
##

if __name__ == "a__main__":
    
    args = sys.argv
    
    if len(args) == 0:        
        # test this module!
        
        # create channels
        channels = c = Channels(1)
        channels.host()
        channels.stdin = channels.getSendingChannel(0)
        channels.stdout = channels.getReceivingChannel(0)
        channels.stderr = channels.getReceivingChannel(1)
        
        # create subprocess
        import subprocess
        if not __file__:
            path = 'c:/projects/PYTHON/test_channels.py' # debuggin...
        else:
            path = os.path.abspath(__file__)
        path = path.replace('\\','/')
        cmd = "python %s %i" % (path, c.getPort())
        p = subprocess.Popen(cmd, bufsize=0, shell=False)
        
    elif len(args)>=2:
        # replace std streams
        
        channels = Channels( 2 )
        channels.connect( port=int(args[1]) )
        sys.stdout = channels.getSendingChannel(0)
        sys.stderr = channels.getSendingChannel(1)
        sys.stdin = channels.getReceivingChannel(0)
        sys.stdout.writeString("hello!")
        
        if len(args) == 2:
            # start a default echo process
            while True:
                tmp = sys.stdin.readOneString(True)
                if sys.stdin.closed:
                    break
                if tmp.lower() in ['stop', 'quit', 'exit']:
                    sys.stdout.writeString('bye bye')
                    break
                if tmp:
                    sys.stdout.writeString('received: '+tmp)
            
        elif len(args) == 3:
            # execute script
            pass
        
        else:
            raise RuntimeError("Invalid number of arguments.")


