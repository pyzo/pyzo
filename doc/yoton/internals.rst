Internals (if you want to know more)
====================================

In yoton, the :ref:`yoton.Context<insertdocs-yoton-Context>` is the object that represents the a node
in the network. 
The context only handles packages. It gets packages from all its 
associated channels and from the other nodes in the network. It routes
packages to the other nodes, and deposits packages in channel instances
if the package slot matches the channel slot.

The :ref:`yoton.Connection<insertdocs-yoton-Connection>` represents a one-to-one connection between two
contexts. It handles the low level messaging. It breaks packages
into pieces and tries to send them as efficiently as possible. It also
receives bytes from the other end, and reconstructs it into packages,
which are then given to the context to handle (i.e. route). 
For the :ref:`yoton.TcpConnection<insertdocs-yoton-TcpConnection>` this is all done by dedicated io threads.


Packages
--------

Packages are simply a bunch of bytes (the encoded message), wrapped 
in a header. Packages are directed at a certain slot. They also 
have a source id, source sequence number, and optionally a 
destination id and destination sequence number
(so that packages can be replies to other packages). When a package
is received, it also gets assigned a receiving sequence number (in order
to synchronize channels).


Levels of communication
-----------------------

Two :ref:`yoton.Connection<insertdocs-yoton-Connection>` instances also communicate directly with each-other. 
They do this during 
the handshaking procedure, obviously, but also during operation they
send each-other heart beat messages to detect time-outs. When the
connection is closed in a nice way, thet also send a close message
to the other end. A package addressed directly at the Connection has no 
body (consists only of a header).

Two contexts can also communicate. They do this to notify
each-other of new formed connections, closing of contexts, etc.
A package directed at a context uses a special slot.

Channel instances can also communicate. Well, that's what yoton is all
about... A sending channels packs a message in a package and gives it
to the contect. All other contexts will receive the
package and deposit it in the channel's queue if the slots match. 
On recv'ing, the message is extracted/decoded from the package.


Persistent connection
---------------------

Two :ref:`yoton.TcpConnection<insertdocs-yoton-TcpConnection>` instances are connected using a single BSD-socket
(TCP/IP). The socket operates in persistent mode; once the connection is
established, the socket remains open until the connection is closed 
indefinetely.

Would we adopt a req/rep approach (setting up the connection for each 
request), failure could mean either that the kernel is running extension 
code, or that the connection is broken. It's not possible to differentiate 
between the two. 

On initialization of the connection, TcpConnection's perform 
a small handshake procedue to establish that both are a :ref:`yoton.TcpConnection<insertdocs-yoton-TcpConnection>`
objects, and to exchange the context id's.

There is one thread dedicated to receive data from the socket, and subsequently
have the context route the packages. Another dedicated thread gets data
from a queue (of the Connection) and sends the packages over the sockets.
The sockets and queues are blocking, but on a timeout (the receiving thread
uses a select() call for this). This makes it easy to periodically send 
heartbeat packages if necessary, and their absence can be detected.

In a previous design, there was a single io thread per context that did 
all the work. It would run through a generator function owned by the
connections to send/receive data. This required all queueing and io to
be non-blocking. After changing the design the code got *much* smaller, 
cleaner and easier to read, and is probably more robust. We could
also get rid of several classes to buffer data, because with blocking
threads the data can sinply be buffered at the queues and sockets. 


Message framing
---------------

To differentiate between messages, there are two common approaches. 
One can add a small header to each message that indicates how long the 
message is. Or one can delimit the messages with a specific character.

In earlier designs, yoton used the second approach and was
limited to sending text which was encoded using utf-8. This meant
the bytes 0xff and 0xfe could be used for delimiting.

The first approach is more complex and requires more per-message 
processing. However, because the message size is know, messages
can be received with much less copying of data. This significantly
improved the performance for larger messages (with the delimiting approach
we would get memory errors when Yoton tried to encode/decode the
message to/from utf-8).

The current design is such that as little data has to be copied 
(particularly for larger messages).


Heart beat signals
------------------

If there is no data to send for a while, small heart beat messages
are produced, so that connection problems can be easily detected. 
For TCP one needs to send data in order to detect connection problem 
(because no ACK's will be received). However, the TCP timeout is in 
the order of minutes and is different between OS's. Therefore we check 
when the last time was that data was received, enabling us to detect 
connection problems in the order of a few seconds.

Note that when two Context's are connected using 'localhost', there
is no way for the connection to be lost, as several network layers
are bypassed. In such a situation, we can therefore be sure that the
reason for the timeout lies not in the connection, but is caused 
for example by the process running extension code.


When the process runs extension code
------------------------------------

With respect to client-kernel comminication: the kernel will not be
able to send any data (neither heart beat signals) if its running
extension code. In such a case, the client can still send messages; 
this data is transported by TCP and ends up in the network buffer 
until the kernel returns from extension code and starts receiving 
messages again.

For this reason, in a client-kernel configuration, the kernel should 
always be connected to another process via 'localhost', and should use
a proxi/broker to connect with clients on another box. 

In that case, the client can detect that the kernel is running extension
code because the kernel stopped sending data (incl heartbeat messages). 


Congestion prevention
---------------------

In any communication system, there is a risk of congestion: one end sends 
data faster than the other end can process it. This data can be buffered,
but as the buffer fills, it consumes more memory.

Yoton uses two approaches to solve this problem. The first (and most
common) solution is that all queues have a maximum size. When this
size is reached and a new messages is added, messages will be discarted.
The user can choose whether the oldest or the newest message should
be discarted.

The second approach is only possible for the PUB/SUB channels. If the 
:ref:`yoton.SubChannel<insertdocs-yoton-SubChannel>` is put in sync-mode (using the 
set_sync_mode method), the :ref:`yoton.SubChannel<insertdocs-yoton-SubChannel>`
will send a message to the corresponding PubChannels if its queue
reaches a certain size. This size is relatively small (e.g. 10-100).
When a :ref:`yoton.PubChannel<insertdocs-yoton-PubChannel>` receives the message, its send method will block
(for at most 1 second). The SubChannel sends a second message when the
queue is below a certain level again. Note that it takes a while for
these control messages to be received by the PubChannel. Therefore
the actual queue size can easily grow larger than the threshold.
In this situation, the first approach (discarting messages is still
used as a failsave, but messages are very unlikely to be discarted
since the threshold is much much smaller than the maximum queue size.

An important aspect for the second approach is that the queue that
buffers packages before they are send over the socket remains small.
If this is not the case, the PubChannel is able to spam the queue 
with gigantic amounts of messages before the SubChannel even receives the
first message. To keep this queue small, much like the queue of the 
SubChannel, it has a certain threshold. If this threshold is reached,
subsequent pushes on the queue will block for maximally 1 second.
The threshold is in the same order of magnitude as the queue for the 
SubChannel.

References
----------
  * http://www.unixguide.net/network/socketfaq/2.9.shtml
  * http://nitoprograms.blogspot.com/2009/04/message-framing.html
  * http://nitoprograms.blogspot.com/2009/05/detection-of-halfopen-dropped.html
