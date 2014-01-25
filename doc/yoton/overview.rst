Overview
========

How it works:

  * Multiple contexts can be connected over TCP/IP; the interconnected 
    contexts together form a network.
  * Messages are send between channel objects (channels are attached to
    a context).
  * Channels are bound to a slot (a string name); a message send from a 
    channel with slot X is received by all channels with slot X.
  * Yoton may be used procedurally, or in an event-driven fashion.

Messaging patterns:

  * Yoton supports the pub/sub pattern, in an N to M configuration.
  * Yoton supports the req/rep pattern, allowing multiple requesters
    and repliers to exist in the same network.
  * Yoton supports exchanging state information.


Some features:

  * Yoton is optimized to handle large messages by reducing data copying.
  * Yoton has a simple event system that makes asynchronous messaging and 
    event-driven programming easy.
  * Yoton also has functionality for basic client-server (telnet-like) 
    communication.
  
  
A brief overview of the most common classes
---------------------------------------------

* :ref:`yoton.Context<insertdocs-yoton-Context>`  
    * Represents a node in the network.
    * Has a bind() and connect() method to connect to other nodes.

* :ref:`yoton.Connection<insertdocs-yoton-Connection>`
    * Represents a connection to another context.
    * Wraps a single BSD-socket, using a persistent connection.
    * Has signals that the user can connect to to be notified of timeouts
      and closing of the connection.

* Channel classes (i.e. :ref:`yoton.BaseChannel<insertdocs-yoton-BaseChannel>` )
    * Channels are associated with a context, and send/receive at a particular
      slot (a string name).
    * Messages send at a particular slot can only be received by channels 
      associated with the same slot.


Example
--------

**One end**

.. code-block:: python

    
    import yoton
    
    # Create one context and a pub channel
    ct1 = yoton.Context(verbose=verbosity)
    pub = yoton.PubChannel(ct1, 'chat')
    
    # Connect
    ct1.bind('publichost:test')
    
    # Send
    pub.send('hello world')
    
    
**Other end**

.. code-block:: python

    
    import yoton
    
    # Create another context and a sub channel
    ct2 = yoton.Context(verbose=verbosity)
    sub = yoton.SubChannel(ct2, 'chat')
    
    # Connect
    ct2.connect('publichost:test')
    
    # Receive
    print(sub.recv())
