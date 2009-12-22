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
ReceivingChannel (file-like) objects, which are used to send and 
receive strings. 


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
# read a single package (waits for max 5 s, returns '' if none available)
r2.readOne(5) 


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

# Implementation details. I found http://www.amk.ca/python/howto/sockets/
# a usefull reference in addition to the documentation on Python sockets.
# An earlier implementation used the "messages indicate how long they are" 
# principle. However, this requires quite a bit of processing, and thus
# makes sending a lot of (small) messages very slow (like for example
# "for i in range(1000): print i"). Therefore we now use delimite the
# messages. We can do this, because "The bytes 0xFE and 0xFF are never 
# used in the UTF-8 encoding".
#
# The data is send bidirectional (using both directions of the socket).
# SendingChannel objects push their message on a global send queue, that
# is fully transmitted each cycle. On the other end, messages are received 
# and pushed on the queue of the proper ReceivingChannel object. The 
# queues are optimized to pop all data at once and can also receive
# multiple messages at once. Note that the send queue contains packed
# messages (including header) and the receive queues contain the encoded
# string only.
#
# Each message starts with a header of 8 bytes: 
# 7 bytes for marker ascii string (CHANNEL to send message)
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


def packMessage(type='CHANNEL', id=0, bb=None):
    """ packMessage(type, id=None, bb=None)
    Build a message ready for sending. Returns a bytes object.
    - type must be a max 7 elements ASCII string.
    - id must be an int between 0 and 255 (indicating channel id)
    - bb must be the text encoded using utf-8 encoding
    """
    
    message = bytes()
    
    # pack type (and justify)
    message += type.encode('ascii').ljust(7)
    
    # todo: limit range
    # pack id (in range 0-255)
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
    
    
class Queue2:
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
            # todo: insert at beginning or end?
            if isinstance(value, list):
                self._data.extend(value)
            else:
                self._data.append(value)
        finally:
            self._lock.release()
    
    def pop(self):
        """ pop()
        Pops an object from the queue. 
        If the queue is empty, returns None. """
        self._lock.acquire()
        try:
            if len(self._data)==0:
                tmp = bytes()
            else:
                tmp = self._data.pop(0)
        finally:
            self._lock.release()
        return tmp
        # todo: make return empty bytes instead of None
    
    
    def popAll(self, joiner):
        self._lock.acquire()
        try:
            if len(self._data)==0:
                tmp = bytes()
            else:
                self._data.append(bytes()) # so we end with a joiner
                tmp = joiner.join(self._data)
                self._data[:] = []
        finally:
            self._lock.release()
        return tmp
    
    
    def count(self):
        """count()
        Return the number of elements in the list. """
        self._lock.acquire()
        try:
            tmp = len(self._data)
        finally:
            self._lock.release()
        return tmp

## The Queue
# todo: remove
TheQueue = Queue2

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
    
    def __init__(self, queue):
        self._q = queue
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
        if s:
            message = packMessage('CHANNEL', self._id, s.encode('utf-8'))
            self._q.push( message )
    
    # todo: test this
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
    On the other end, this is a SendingChannel.
    Exposes a text file interface that can be used in blocking
    and non-blocking mode.
    """
    
    def __init__(self):
        BaseChannel.__init__(self, TheQueue())
        self._blocking = False
    
    
    def setBlocking(self, blocking=True):
        """ setBlocking(blocking=True)
        Set the default blocking state. 
        """
        self._blocking = blocking
    
    
    @property
    def isBlocking(self):
        return self._blocking 
    
    
    def readOne(self, block=None):
        """ readOne(block=False)
        Read one string that was send as one from the other end.
        If the channel is closed, returns an empty string .        
        If block is not given, uses the default blocking state.
        If not blocking, returns an empty string  if no data is available.
        If blocking, waits until data is available.
        """
        
        # if closed, return nothing
        if self._closed:
            return ''
        
        # use default block state?
        if block is None:
            block = self._blocking
        if block and isinstance(block, bool):
            block = 2**30
        elif block and not isinstance(block,(int,float)):
            raise ValueError('Block must be a bool, None, int, or float.')
        
        # get data, return empty bytes if queue is empty
        tmp = self._q.pop()
        if block:
            t0 = time.time()
            while not tmp and (time.time()-t0) < block:
                if self._closed:
                    break
                time.sleep(0.01)
                tmp = self._q.pop()
        
        # return
        return tmp.decode('utf-8')
    
    
    def read(self, block=False):
        """ read(block=False)
        Read all text available now.
        If the channel is closed, returns an empty string .        
        If block is not given, uses the default blocking state.
        If not blocking, returns an empty string if no data is available.
        If blocking, waits until data is available.
        """
        
        # if closed, return nothing
        if self._closed:
            return ''
        
        # get all available
        tmp = self._q.popAll(bytes())
        
        # done
        return tmp.decode('utf-8')
    
    
    def pending(self):
        """ pending()
        Return the number of pending messages. 
        """
        return self._q.count()
    
    
    def write(self, s):
        """ write(s)
        Cannot be used on a receiving channel. 
        """
        raise IOError("Cannot write to a receiving channel.")
    
    
    def close(self):
        """ close()
        A receiving channel can only be close from the sending side. 
        """
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
        if N<0 or N>127:
            raise IndexError("Invalid amount of channels.")
        
        # create channel lists        
        self._sendingChannels = []
        self._receivingChannels = []
        
        # lock and queue for special stuff
        self._lock = threading.RLock()
        self._q = TheQueue()
        
        # create sending channels now
        for id in range(N):
            self._sendingChannels.append( SendingChannel(self._q, id) )
        
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
        untill a free slot is available. If you only want to try 
        one port, set this to 1.
        
        If hostLocal is true, the socket is only visible from this
        computer. Also some low level networking layers are bypassed,
        which results in a faster connection. If set to false, 
        processes from other computers can also connect.
        
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
        # todo: remove ips or get bps?
        return dm._ips, dm._n_send, dm._n_recv
    
    
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
        
        # buffer for received bytes (incomplete messages)
        self._receiveBuffer = bytes()
        
        # store queues of receiveChannels (for efficient pushing of messages)
        self._receiveQueues = []
        
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
        
        # Init unresponsive measure
        self._tin = time.time()
        
        # Init other timers and counters
        t0 = time.time() # temporary variable to hold current time
        ts = t0 # the last time we sent something (if >0.5s we send NOOP)
        
        
        # enter main loop
        while True:
            
            # should we stop?
            if self._stopMe:
                break
            
            # pitch messages
            sentSomething = self.pitch()
            
            # end of iteration
            t0 = time.time()
            
            # should we pitch a noop?
            if sentSomething:
                ts = t0
            elif t0-ts > 0.5:
                self._channels._q.push( packMessage('NOOP') )
                ts = t0
            
            # catch messages            
            receivedSomething = self.catch()
            if receivedSomething:
                self._tin = time.time() # we got something! 
            
            # check if other side is still responding
            if time.time() - self._tin > 1.0:
                self._nmiss += 1
            else:
                self._nmiss = 0
            if self._nmiss > 5:
                self._stopMe = "Other side is unresponsive."
                
            
            
            # Determine time to rest. By default we sleep for 0.01 second.
            # But when sending or receiving, we go in super mode, pumping 
            # messages like crazy :)
            if receivedSomething or sentSomething:
                time.sleep(0.000001) # corresponds with 1Mhz
                #time.sleep(0.1) # corresponds with 1Mhz
            else:
                time.sleep(0.01) # corresponds with 100Hz
                # Sleeping 0.001 sec results in 0% processing power on my
                # 3.5 year old laptop, so 0.01 sec should be ok.
        
        # close all channels
        for i in range(len(self._channels._receivingChannels)):
            channel = self._channels.getReceivingChannel(i)
            channel._closed = True
        
        # clean up
        self._socket.close()        
        print("Connection closed: " + self._stopMe)
        self._channels._port = 0
    
    
    ## send methods
    
    def pitch(self):
        """ pitch()
        Send all messages from the queue.
        Returns amount of sent messages/bytes. """
        
        # flush the whole queue
        tmp = self._channels._q.popAll(DELIMITER)
        # todo: is this the way?
        
        # try to send what we can
        n = len(tmp)
        if tmp:
            try:
                self._socket.sendall( tmp )
            except socket.error:
                self._stopMe = 'Other end dropped.'
        
        # update stats
        self._n_send += n
        # todo: change n send to represent send bytes!
        return n
    
    
    ## receive methods
    
    def receiveMessages(self):
        """ receiveMessages()
        Receive data from the socket, devide in messages using the
        delimiter and return the available messages as a list.
        """
        
        # init list of blocks
        blocks = [self._receiveBuffer]
        
        # receive what we can
        # todo: does it matter to loop?
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
        messages = bytes().join(blocks)
        
        # and split in messages
        messages = messages.split(DELIMITER)
        
        # store last bit
        self._receiveBuffer = messages.pop()
        
        # return all whole messages
        return messages
        
        # todo: use a substitute for buffer to save a dict lookup
    
    
    def catch(self):
        """ catch()
        Catch data. First the header is catched as one part.
        The info (channel and length) is stored in case 
        the message itself cannot be received this call.
        """
        
        # receive what we can now
        messages = self.receiveMessages()
        n = len(messages)
        
        A = 'A'.encode('ascii')
        
        while messages:
            
            # Try getting a list of messages for the same channel
            # This has a small performance reduction when messages are
            # not in a row, but it significantly improves performance
            # when multiple messages for the same channel are send in a
            # row.
            i = 0 # todo: it seems faster if I do not do this 'optimization'
            # but that might be because in IEP the data is available sooner
            # and therefore there are more inserts in the editor?
            id = ord( messages[0][7:8] ) # get id of first     
            for i in range(len(messages)):
                if (not ord( messages[i][7:8] )==id) or (not messages[0][2:3]==A):
                    break
            
            # select these messages, or first message if not a list
            if i>1:
                bb = [mes[8:] for mes in messages[:i]]
                messages[:i] = []
                type = 'CHANNEL'
            else:
                message = messages.pop(0)
                type, id, bb = unPackMessage(message)
            
            # check and process
            if type == 'NOOP':
                pass
            elif type == 'CLOSE':
                channel = self._channels.getReceivingChannel(id)
                channel._closed = True
            elif type == 'INT':
                self.doInterrupt()
            elif type == 'KILL':
                self.doKill()
            elif type == 'CHANNEL':
                # get channel and its queue
                while len(self._receiveQueues) <= id:
                    i2 = len(self._receiveQueues)
                    channel = self._channels.getReceivingChannel(i2)
                    self._receiveQueues.append(channel._q)
                q = self._receiveQueues[id]
                # put message it in the queue
                q.push(bb)
                # finish
                self._n_recv += 1
                # todo: what stats do we want to keep?
            
            else:
                self._stopMe = "Lost track of stream."
        
        return n
    
    
    def doInterrupt(self):
        """ doInterrupt()
        Process a received interrupt command. """
        thread.interrupt_main()
        
        
    def doKill(self):
        """ doKill()
        Process a received kill command. """     
        pid = os.getpid()
        if hasattr(os,'kill'):
            import signal
            os.kill(pid,signal.SIGTERM)
            time.sleep(1)
        elif sys.platform.startswith('win'):
            os.system("TASKKILL /PID " + str(os.getpid()) + " /F")


if 0:
    channels.disconnect()
## here

    channels = Channels(2)
    port = channels.host('IEP'); print(port)
    r1 = channels.getReceivingChannel(0)
    s1 = channels.getSendingChannel(0)
    s2 = channels.getSendingChannel(1)
    
    s1.write("I am channel one")
    s1.write("hello there!")
    s2.write("And I, dear sir, am channel two.")
    s2.write("Nice meeting you.")

## there
    
    channels = Channels(1)
    channels.connect('IEP')
    r1 = channels.getReceivingChannel(0)
    r2 = channels.getReceivingChannel(1)
    s1 = channels.getSendingChannel(0)
    time.sleep(0.5)
    print( r1.read())
    print( r1.read())
    print( r2.read())
    print( r2.read())

## testing (receiving end)
    
    times = []
    t0 = 0
    nb = 0
    tmp = r1.read(False) # flush
    while True:
        tmp = r1.readOne()
        if not t0:
            t0 = time.time()
        nb += len(tmp)
        if tmp == 'stop':
            break
        if tmp:
            t = float( tmp.split(' ')[0] )
            dt = time.time() - t
            times.append(dt)
    print( times[::100])
    print(channels.getStats())
    print( (nb/1024.0)/(time.time()-t0 -0.0000001),'KB/s' )
    

## testing (sending end): multiple small messages
    # select and Queue2: 0.23, 1.8
    # select and LL: 0.20, 1.8
    # nonblocking and Queue2: 0.2, 1.5
    #
    # select v2, Queue2: 0.1, 0.7
    # select v2, Queue2+LL: ditto
    # select v2, single block: 2.5
    # select v2, huge blocks: 0.7
    # buffer as one large string + becomes unresponsive
    # idea: delimit messages in exact blocks 00?
    
    for i in range(10000):
        s1.write(str(time.time()) + ' testing '*10 + str(i))
    s1.write('stop')
    print(channels.getStats())


## testing (sending end): One huge message
    # select and Queue2: 0.13 _. 31 MB/s
    # select v2 and Queue2: 0.06 _. 120 MB/s
    for i in range(2):
        s1.write(str(time.time()) + ' testing ' + "a"*1000000)
    s1.write('stop')
    print(channels.getStats())

## Receiving afterwards
    t0 = 0
    nb = 0
    times = []
    while True:
        tmp = r1.readOne()
        if not t0:
            t0 = time.time()
        nb += len(tmp)
        if tmp == 'stop':
            break
        if tmp:
            t = float( tmp.split(' ')[0] )
            dt = time.time() - t
            times.append(dt)
    print( times[::100])
    print(channels.getStats())
    print( (nb/1024.0)/(time.time()-t0 -0.0000001),'KB/s' )