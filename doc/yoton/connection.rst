Connection
==========

The connection classes represent the connection between two context. There
is one base class (yoton.Connection) and currently there is one 
implementation: the :ref:`yoton.TcpConnection<insertdocs-yoton-TcpConnection>`. In the future other connections
might be added that use other methods than TCP/IP.

.. insertdocs start:: yoton.Connection
.. insertdocs :members: 


.. _insertdocs-yoton-Connection:

.. py:class:: yoton.Connection(context, name='')

  *Inherits from object*

  Abstract base class for a connection between two Context objects.
  This base class defines the full interface; subclasses only need
  to implement a few private methods.
  
  The connection classes are intended as a simple interface for the 
  user, for example to query port number, and be notified of timeouts 
  and closing of the connection. 
  
  All connection instances are intended for one-time use. To make
  a new connection, instantiate a new Connection object. After
  instantiation, either _bind() or _connect() should be called.
  

  *PROPERTIES*

  .. _insertdocs-yoton-Connection-closed:
  
  .. py:attribute:: yoton.Connection.closed
  
    Signal emitted when the connection closes. The first argument
    is the ContextConnection instance, the second argument is the 
    reason for the disconnection (as a string).

  .. _insertdocs-yoton-Connection-hostname1:
  
  .. py:attribute:: yoton.Connection.hostname1
  
    Get the hostname corresponding to this end of the connection.

  .. _insertdocs-yoton-Connection-hostname2:
  
  .. py:attribute:: yoton.Connection.hostname2
  
    Get the hostname for the other end of this connection.
    Is empty string if not connected.

  .. _insertdocs-yoton-Connection-id1:
  
  .. py:attribute:: yoton.Connection.id1
  
    The id of the context on this side of the connection.

  .. _insertdocs-yoton-Connection-id2:
  
  .. py:attribute:: yoton.Connection.id2
  
    The id of the context on the other side of the connection.

  .. _insertdocs-yoton-Connection-is_alive:
  
  .. py:attribute:: yoton.Connection.is_alive
  
    Get whether this connection instance is alive (i.e. either 
    waiting or connected, and not in the process of closing).

  .. _insertdocs-yoton-Connection-is_connected:
  
  .. py:attribute:: yoton.Connection.is_connected
  
    Get whether this connection instance is connected.

  .. _insertdocs-yoton-Connection-is_waiting:
  
  .. py:attribute:: yoton.Connection.is_waiting
  
    Get whether this connection instance is waiting for a connection. 
    This is the state after using bind() and before another context 
    connects to it.

  .. _insertdocs-yoton-Connection-name:
  
  .. py:attribute:: yoton.Connection.name
  
    Set/get the name that this connection is known by. This name
    can be used to obtain the instance using the Context.connections 
    property. The name can be used in networks in which each context
    has a particular role, to easier distinguish between the different
    connections. Other than that, the name has no function.

  .. _insertdocs-yoton-Connection-pid1:
  
  .. py:attribute:: yoton.Connection.pid1
  
    The pid of the context on this side of the connection.
    (hint: os.getpid())

  .. _insertdocs-yoton-Connection-pid2:
  
  .. py:attribute:: yoton.Connection.pid2
  
    The pid of the context on the other side of the connection.

  .. _insertdocs-yoton-Connection-port1:
  
  .. py:attribute:: yoton.Connection.port1
  
    Get the port number corresponding to this end of the connection.
    When binding, use this port to connect the other context.

  .. _insertdocs-yoton-Connection-port2:
  
  .. py:attribute:: yoton.Connection.port2
  
    Get the port number for the other end of the connection.
    Is zero when not connected.

  .. _insertdocs-yoton-Connection-timedout:
  
  .. py:attribute:: yoton.Connection.timedout
  
    This signal is emitted when no data has been received for 
    over 'timeout' seconds. This can mean that the connection is unstable, 
    or that the other end is running extension code.
    
    Handlers are called with two arguments: the ContextConnection 
    instance, and a boolean. The latter is True when the connection
    times out, and False when data is received again.

  .. _insertdocs-yoton-Connection-timeout:
  
  .. py:attribute:: yoton.Connection.timeout
  
    Set/get the amount of seconds that no data is received from
    the other side after which the timedout signal is emitted. 

  *METHODS*

  .. _insertdocs-yoton-Connection-close:
  
  .. py:method:: yoton.Connection.close(reason=None)
  
    Close the connection, disconnecting the two contexts and 
    stopping all trafic. If the connection was waiting for a 
    connection, it stops waiting.
    
    Optionally, a reason for closing can be specified. A closed
    connection cannot be reused.
    

  .. _insertdocs-yoton-Connection-close_on_problem:
  
  .. py:method:: yoton.Connection.close_on_problem(reason=None)
  
    Disconnect the connection, stopping all trafic. If it was
    waiting for a connection, we stop waiting.
    
    Optionally, a reason for stopping can be specified. This is highly
    recommended in case the connection is closed due to a problem.
    
    In contrast to the normal close() method, this method does not
    try to notify the other end of the closing.
    

  .. _insertdocs-yoton-Connection-flush:
  
  .. py:method:: yoton.Connection.flush(timeout=3.0)
  
    Wait until all pending packages are send. An error
    is raised when the timeout passes while doing so.
    



.. insertdocs end::

.. insertdocs start:: yoton.TcpConnection
.. insertdocs :members: 


.. _insertdocs-yoton-TcpConnection:

.. py:class:: yoton.TcpConnection(context, name='')

  *Inherits from Connection*

  The TcpConnection class implements a connection between two
  contexts that are in differenr processes or on different machines
  connected via the internet.
  
  This class handles the low-level communication for the context.    
  A ContextConnection instance wraps a single BSD socket for its 
  communication, and uses TCP/IP as the underlying communication 
  protocol. A persisten connection is used (the BSD sockets stay 
  connected). This allows to better distinguish between connection
  problems and timeouts caused by the other side being busy.
  



.. insertdocs end::
