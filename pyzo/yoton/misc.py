"""Module yoton.misc

Defines a few basic constants, classes and functions.

Most importantly, it defines a couple of specific buffer classes that
are used for the low-level messaging.

"""

import sys
import time
import struct
import socket
import threading
import random
from collections import deque


# Version dependent defs
V2 = sys.version_info[0] == 2
if V2:
    if sys.platform.startswith("java"):
        import __builtin__ as D  # Jython
    else:
        D = __builtins__
    if not isinstance(D, dict):
        D = D.__dict__
    bytes = D["str"]
    str = D["unicode"]
    xrange = D["xrange"]
    basestring = basestring  # noqa
    long = long  # noqa
else:
    basestring = str  # to check if instance is string
    bytes, str = bytes, str
    long = int  # for the port
    xrange = range


def getErrorMsg():
    """getErrorMsg()
    Return a string containing the error message. This is useful, because
    there is no uniform way to catch exception objects in Python 2.x and
    Python 3.x.
    """

    # Get traceback info
    type, value, tb = sys.exc_info()

    # Store for debugging?
    if True:
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb

    # Print
    err = ""
    try:
        if not isinstance(value, (OverflowError, SyntaxError, ValueError)):
            while tb:
                err = "line %i of %s." % (
                    tb.tb_frame.f_lineno,
                    tb.tb_frame.f_code.co_filename,
                )
                tb = tb.tb_next
    finally:
        del tb
    return str(value) + "\n" + err


def slot_hash(name):
    """slot_hash(name)

    Given a string (the slot name) returns a number between 8 and 2**64-1
    (just small enough to fit in a 64 bit unsigned integer). The number
    is used as a slot id.

    Slots 0-7 are reserved slots.

    """
    fac = 0xD2D84A61
    val = 0
    offset = 8
    for c in name:
        val += (val >> 3) + (ord(c) * fac)
    val += (val >> 3) + (len(name) * fac)
    return offset + (val % (2**64 - offset))


def port_hash(name):
    """port_hash(name)

    Given a string, returns a port number between 49152 and 65535.
    (2**14 (16384) different posibilities)
    This range is the range for dynamic and/or private ports
    (ephemeral ports) specified by iana.org.
    The algorithm is deterministic, thus providing a way to map names
    to port numbers.

    """
    fac = 0xD2D84A61
    val = 0
    for c in name:
        val += (val >> 3) + (ord(c) * fac)
    val += (val >> 3) + (len(name) * fac)
    return 49152 + (val % 2**14)


def split_address(address):
    """split_address(address) -> (protocol, hostname, port)

    Split address in protocol, hostname and port. The address has the
    following format: "protocol://hostname:port". If the protocol is
    omitted, TCP is assumed.

    The hostname is the name or ip-address of the computer to connect to.
    One can use "localhost" for a connection that bypasses some
    network layers (and is not visible from the outside). One can use
    "publichost" for a connection at the current computers IP address
    that is visible from the outside.

    The port can be an integer, or a string. In the latter case the integer
    port number is calculated using a hash. One can also use "portname+offset"
    to specify an integer offset for the port number.

    """

    # Check
    if not isinstance(address, basestring):
        raise ValueError("Address should be a string.")

    # Is the protocol explicitly defined (zeromq compatibility)
    protocol, _, address = address.rpartition("://")
    protocol = protocol.lower() or "tcp"

    # Split
    if ":" not in address:
        raise ValueError("Address should be in format 'host:port'.")
    host, port = address.split(":", 1)

    # Process host
    if host.lower() == "localhost":
        host = "127.0.0.1"

    ph = "publichost"
    if host.lower() == ph:
        host = ph + "0"

    if host.lower().startswith(ph) and set(host[len(ph) :]).issubset("0123456789"):
        index = int(host[len(ph) :])
        hostname = socket.gethostname()
        ipaddrlist = socket.gethostbyname_ex(hostname)[2]
        try:
            host = ipaddrlist[index]  # This resolves to 127.0.1.1 on some Linuxes
        except IndexError:
            raise ValueError("Invalid index (%i) in public host addresses." % index)

    # Process port
    try:
        port = int(port)
    except ValueError:
        # Convert to int, using a hash

        # Is there an offset?
        offset = 0
        if "+" in port:
            port, offset = port.split("+", 1)
            try:
                offset = int(offset)
            except ValueError:
                raise ValueError("Invalid offset in address")

        # Convert
        port = port_hash(port) + offset

    # Check port
    # if port < 1024 or port >= 2**16:
    #    raise ValueError("The port must be in the range [1024, 2^16>.")
    if port >= 2**16:
        raise ValueError("The port must be in the range [0, 2^16>.")

    # Done
    return protocol, host, port


class UID:
    """UID

    Represents an 8-byte (64 bit) Unique Identifier.

    """

    _last_timestamp = 0

    def __init__(self, id=None):
        # Create nr consisting of two parts
        if id is None:
            self._nr = self._get_time_int() << 32
            self._nr += self._get_random_int()
        elif isinstance(id, (int, long)):
            self._nr = id
        else:
            raise ValueError("The id given to UID() should be an int.")

    def __repr__(self):
        h = self.get_hex()
        return "<UID %s-%s>" % (h[:8], h[8:])

    def get_hex(self):
        """get_hex()

        Get the hexadecimal representation of this UID. The returned
        string is 16 characters long.

        """
        return format(self._nr, "016x")

    def get_bytes(self):
        """get_bytes()

        Get the UID as bytes.

        """
        return struct.pack("<Q", self._nr)

    def get_int(self):
        """get_int()

        Get the UID as a 64 bit (long) integer.

        """
        return self._nr

    def _get_random_int(self):
        return random.randrange(1 << 32)

    def _get_time_int(self):
        # Get time stamp in steps of milliseconds
        timestamp = int(time.time() * 1000)
        # Increase by one if the same as last time
        if timestamp <= UID._last_timestamp:
            timestamp = UID._last_timestamp + 1
        # Store for next time
        UID._last_timestamp = timestamp
        # Truncate to 4 bytes. If the time goes beyond the integer limit, we just
        # restart counting. With this setup, the cycle is almost 50 days
        timestamp &= 0xFFFFFFFF
        # Don't allow 0
        if timestamp == 0:
            timestamp += 1
            UID._last_timestamp += 1
        return timestamp


class PackageQueue(object):
    """PackageQueue(N, discard_mode='old')

    A queue implementation that can be used in blocking and non-blocking
    mode and allows peeking. The queue has a limited size. The user
    can specify whether old or new messages should be discarded.

    Uses a deque object for the queue and a threading.Condition for
    the blocking.

    """

    class Empty(Exception):
        def __init__(self):
            Exception.__init__(self, "pop from an empty PackageQueue")

        pass

    def __init__(self, N, discard_mode="old"):
        # Instantiate queue and condition
        self._q = deque()
        self._condition = threading.Condition()

        # Store max number of elements in queue
        self._maxlen = int(N)

        # Store discard mode as integer
        discard_mode = discard_mode.lower()
        if discard_mode == "old":
            self._discard_mode = 1
        elif discard_mode == "new":
            self._discard_mode = 2
        else:
            raise ValueError("Invalid discard mode.")

    def full(self):
        """full()

        Returns True if the number of elements is at its maximum right now.
        Note that in theory, another thread might pop an element right
        after this function returns.

        """
        return len(self) >= self._maxlen

    def empty(self):
        """empty()

        Returns True if the number of elements is zero right now. Note
        that in theory, another thread might add an element right
        after this function returns.

        """
        return len(self) == 0

    def push(self, x):
        """push(item)

        Add an item to the queue. If the queue is full, the oldest
        item in the queue, or the given item is discarded.

        """

        condition = self._condition
        with condition:
            q = self._q

            if len(q) < self._maxlen:
                # Add now and notify any waiting threads in get()
                q.append(x)
                condition.notify()  # code at wait() procedes
            else:
                # Full, either discard or pop (no need to notify)
                if self._discard_mode == 1:
                    q.popleft()  # pop old
                    q.append(x)
                elif self._discard_mode == 2:
                    pass  # Simply do not add

    def insert(self, x):
        """insert(x)

        Insert an item at the front of the queue. A call to pop() will
        get this item first. This should be used in rare circumstances
        to give an item priority. This method never causes items to
        be discarded.

        """

        condition = self._condition
        with condition:
            self._q.appendleft(x)
            condition.notify()  # code at wait() procedes

    def pop(self, block=True):
        """pop(block=True)

        Pop the oldest item from the queue. If there are no items in the
        queue:
          * the calling thread is blocked until an item is available
            (if block=True, default);
          * an PackageQueue.Empty exception is raised (if block=False);
          * the calling thread is blocked for 'block' seconds (if block
            is a float).

        """

        condition = self._condition
        with condition:
            q = self._q

            if not block:
                # Raise empty if no items in the queue
                if not len(q):
                    raise self.Empty()
            elif block is True:
                # Wait for notify (awakened does not guarantee len(q)>0)
                while not len(q):
                    condition.wait()
            elif isinstance(block, float):
                # Wait if no items, then raise error if still no items
                if not len(q):
                    condition.wait(block)
                    if not len(q):
                        raise self.Empty()
            else:
                raise ValueError("Invalid value for block in PackageQueue.pop().")

            # Return item
            return q.popleft()

    def peek(self, index=0):
        """peek(index=0)

        Get an item from the queue without popping it. index=0 gets the
        oldest item, index=-1 gets the newest item. Note that index access
        slows to O(n) time in the middle of the queue (due to the underlying
        deque object).

        Raises an IndexError if the index is out of range.

        """
        return self._q[index]

    def __len__(self):
        return self._q.__len__()

    def clear(self):
        """clear()

        Remove all items from the queue.

        """
        with self._condition:
            self._q.clear()


class TinyPackageQueue(PackageQueue):
    """TinyPackageQueue(N1, N2, discard_mode='old', timeout=1.0)

    A queue implementation that can be used in blocking and non-blocking
    mode and allows peeking. The queue has a tiny-size (N1). When this size
    is reached, a call to push() blocks for up to timeout seconds. The
    real size (N2) is the same as in the PackageQueue class.

    The tinysize mechanism can be used to semi-synchronize a consumer
    and a producer, while still having a small queue and without having
    the consumer fully block.

    Uses a deque object for the queue and a threading.Condition for
    the blocking.

    """

    def __init__(self, N1, N2, discard_mode="old", timeout=1.0):
        PackageQueue.__init__(self, N2, discard_mode)

        # Store limit above which the push() method will block
        self._tinylen = int(N1)

        # Store timeout
        self._timeout = timeout

    def push(self, x):
        """push(item)

        Add an item to the queue. If the queue has >= n1 values,
        this function will block timeout seconds, or until an item is
        popped from another thread.

        """

        condition = self._condition
        with condition:
            q = self._q
            lq = len(q)

            if lq < self._tinylen:
                # We are on safe side. Wake up any waiting threads if queue was empty
                q.append(x)
                condition.notify()  # pop() at wait() procedes
            elif lq < self._maxlen:
                # The queue is above its limit, but not full
                condition.wait(self._timeout)
                q.append(x)
            else:
                # Full, either discard or pop (no need to notify)
                if self._discard_mode == 1:
                    q.popleft()  # pop old
                    q.append(x)
                elif self._discard_mode == 2:
                    pass  # Simply do not add

    def pop(self, block=True):
        """pop(block=True)

        Pop the oldest item from the queue. If there are no items in the
        queue:
          * the calling thread is blocked until an item is available
            (if block=True, default);
          * a PackageQueue.Empty exception is raised (if block=False);
          * the calling thread is blocked for 'block' seconds (if block
            is a float).

        """

        condition = self._condition
        with condition:
            q = self._q

            if not block:
                # Raise empty if no items in the queue
                if not len(q):
                    raise self.Empty()
            elif block is True:
                # Wait for notify (awakened does not guarantee len(q)>0)
                while not len(q):
                    condition.wait()
            elif isinstance(block, float):
                # Wait if no items, then raise error if still no items
                if not len(q):
                    condition.wait(block)
                    if not len(q):
                        raise self.Empty()
            else:
                raise ValueError("Invalid value for block in TinyPackageQueue.pop().")

            # Notify if this pop would reduce the length below the threshold
            if len(q) <= self._tinylen:
                if sys.version_info < (2, 6):
                    condition.notifyAll()  # wait() procedes
                else:
                    condition.notify_all()

            # Return item
            return q.popleft()

    def clear(self):
        """clear()

        Remove all items from the queue.

        """

        with self._condition:
            lq = len(self._q)
            self._q.clear()
            if lq >= self._tinylen:
                self._condition.notify()
