Context
=======

.. insertdocs start:: yoton.Context
.. insertdocs :members: 


.. _insertdocs-yoton-Context:

.. py:class:: yoton.Context(verbose=0, queue_params=None)

  *Inherits from object*

  A context represents a node in the network. It can connect to 
  multiple other contexts (using a :ref:`yoton.Connection<insertdocs-yoton-Connection>`. 
  These other contexts can be in 
  another process on the same machine, or on another machine
  connected via a network or the internet.
  
  This class represents a context that can be used by channel instances
  to communicate to other channels in the network. (Thus the name.)
  
  The context is the entity that queue routes the packages produced 
  by the channels to the other context in the network, where
  the packages are distributed to the right channels. A context queues
  packages while it is not connected to any other context.
  
  If messages are send on a channel registered at this context while
  the context is not connected, the messages are stored by the
  context and will be send to the first connecting context.
  
  **Example 1**
  
  .. code-block:: python
  
      # Create context and bind to a port on localhost
      context = yoton.Context()
      context.bind('localhost:11111')
      # Create a channel and send a message
      pub = yoton.PubChannel(context, 'test')
      pub.send('Hello world!')
      
  **Example 2**
  
  .. code-block:: python
  
      # Create context and connect to the port on localhost
      context = yoton.Context()
      context.connect('localhost:11111')
      # Create a channel and receive a message
      sub = yoton.SubChannel(context, 'test')
      print(sub.recv() # Will print 'Hello world!'
      
  **Queue params**
  
  
  The queue_params parameter allows one to specify the package queues
  used in the system. It is recommended to use the same parameters
  for every context in the network. The value of queue_params should
  be a 2-element tuple specifying queue size and discard mode. The
  latter can be 'old' (default) or 'new', meaning that if the queue
  is full, either the oldest or newest messages are discarted.
  

  *PROPERTIES*

  .. _insertdocs-yoton-Context-connection_count:
  
  .. py:attribute:: yoton.Context.connection_count
  
    Get the number of connected contexts. Can be used as a boolean
    to check if the context is connected to any other context.

  .. _insertdocs-yoton-Context-connections:
  
  .. py:attribute:: yoton.Context.connections
  
    Get a list of the Connection instances currently
    active for this context. 
    In addition to normal list indexing, the connections objects can be
    queried  from this list using their name.

  .. _insertdocs-yoton-Context-connections_all:
  
  .. py:attribute:: yoton.Context.connections_all
  
    Get a list of all Connection instances currently
    associated with this context, including pending connections 
    (connections waiting for another end to connect).
    In addition to normal list indexing, the connections objects can be
    queried from this list using their name.

  .. _insertdocs-yoton-Context-id:
  
  .. py:attribute:: yoton.Context.id
  
    The 8-byte UID of this context.

  *METHODS*

  .. _insertdocs-yoton-Context-bind:
  
  .. py:method:: yoton.Context.bind(address, max_tries=1, name='')
  
    Setup a connection with another Context, by being the host.
    This method starts a thread that waits for incoming connections.
    Error messages are printed when an attemped connect fails. the
    thread keeps trying until a successful connection is made, or until
    the connection is closed.
    
    Returns a Connection instance that represents the
    connection to the other context. These connection objects 
    can also be obtained via the Context.connections property.
    
    **Parameters**
    
    
    address : str
        Should be of the shape hostname:port. The port should be an
        integer number between 1024 and 2**16. If port does not 
        represent a number, a valid port number is created using a 
        hash function.
    max_tries : int
        The number of ports to try; starting from the given port, 
        subsequent ports are tried until a free port is available. 
        The final port can be obtained using the 'port' property of
        the returned Connection instance.
    name : string
        The name for the created Connection instance. It can
        be used as a key in the connections property.
    
    **Notes on hostname**
    
    
    The hostname can be:
      * The IP address, or the string hostname of this computer. 
      * 'localhost': the connections is only visible from this computer. 
        Also some low level networking layers are bypassed, which results
        in a faster connection. The other context should also connect to
        'localhost'.
      * 'publichost': the connection is visible by other computers on the 
        same network. Optionally an integer index can be appended if
        the machine has multiple IP addresses (see socket.gethostbyname_ex).
    

  .. _insertdocs-yoton-Context-close:
  
  .. py:method:: yoton.Context.close()
  
    Close the context in a nice way, by closing all connections
    and all channels.
    
    Closing a connection means disconnecting two contexts. Closing
    a channel means disasociating a channel from its context. 
    Unlike connections and channels, a Context instance can be reused 
    after closing (although this might not always the best strategy).
    

  .. _insertdocs-yoton-Context-close_channels:
  
  .. py:method:: yoton.Context.close_channels()
  
    Close all channels associated with this context. This does
    not close the connections. See also close().
    

  .. _insertdocs-yoton-Context-connect:
  
  .. py:method:: yoton.Context.connect(self, address, timeout=1.0, name='')
  
    Setup a connection with another context, by connection to a 
    hosting context. An error is raised when the connection could
    not be made.
    
    Returns a Connection instance that represents the
    connection to the other context. These connection objects 
    can also be obtained via the Context.connections property.
    
    **Parameters**
    
    
    address : str
        Should be of the shape hostname:port. The port should be an
        integer number between 1024 and 2**16. If port does not 
        represent a number, a valid port number is created using a 
        hash function.
    max_tries : int
        The number of ports to try; starting from the given port, 
        subsequent ports are tried until a free port is available. 
        The final port can be obtained using the 'port' property of
        the returned Connection instance.
    name : string
        The name for the created Connection instance. It can
        be used as a key in the connections property.
    
    **Notes on hostname**
    
    
    The hostname can be:
      * The IP address, or the string hostname of this computer. 
      * 'localhost': the connection is only visible from this computer. 
        Also some low level networking layers are bypassed, which results
        in a faster connection. The other context should also host as
        'localhost'.
      * 'publichost': the connection is visible by other computers on the 
        same network. Optionally an integer index can be appended if
        the machine has multiple IP addresses (see socket.gethostbyname_ex).
    

  .. _insertdocs-yoton-Context-flush:
  
  .. py:method:: yoton.Context.flush(timeout=5.0)
  
    Wait until all pending messages are send. This will flush all
    messages posted from the calling thread. However, it is not
    guaranteed that no new messages are posted from another thread.
    
    Raises an error when the flushing times out.
    



.. insertdocs end::

  
