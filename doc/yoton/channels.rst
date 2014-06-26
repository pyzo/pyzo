Channels
========

The channel classes represent the mechanism for the user to send
messages into the network and receive messages from it. A channel
needs a context to function; the context represents a node in the 
network. 


Slots
-----
To be able to route messages to the right channel, channels are 
associated with a slot (a string name). This slot consists of a 
user-defined base name and an extension to tell the message type 
and messaging pattern. Messages send from a channel with slot X, 
are only received by channels with the same slot X. Slots are case 
insensitive.


Messaging patterns
------------------
Yoton supports three base messaging patterns. For each messaging pattern
there are specific channel classes. All channels derive from :ref:`yoton.BaseChannel<insertdocs-yoton-BaseChannel>`.

**publish/subscribe**
The :ref:`yoton.PubChannel<insertdocs-yoton-PubChannel>` class is used for sending messages into the network, and
the :ref:`yoton.SubChannel<insertdocs-yoton-SubChannel>` class is used to receiving these messages. Multiple
PubChannels and SubChannels can exist in the same network at the same 
slot; the SubChannels simply collect the messages send by all PubChannels.

**request/reply**
The :ref:`yoton.ReqChannel<insertdocs-yoton-ReqChannel>` class is used to do requests, and the :ref:`yoton.RepChannel<insertdocs-yoton-RepChannel>` 
class is 
used to reply to requests. If multiple ReqChannels are present at the 
same slot, simple load balancing is performed.

**state**
The :ref:`yoton.StateChannel<insertdocs-yoton-StateChannel>` class is used to communicate state to other state
channels. Each :ref:`yoton.StateChannel<insertdocs-yoton-StateChannel>` can set and get the state.


Message types
-------------

Messages are of a specific type (text, binary, ...), the default being
Unicode text. The third (optional) argument to a Channel's initializer 
is a MessageType object that specifies how messages should be converted
to bytes and the other way around. 

This way, the channels classes themself can be agnostic about the message
type, while the user can implement its own MessageType class to send 
whatever messages he/she likes.


.. insertdocs start:: yoton.BaseChannel
.. insertdocs :members: 
    

.. _insertdocs-yoton-BaseChannel:

.. py:class:: yoton.BaseChannel(context, slot_base, message_type=yoton.TEXT)

  *Inherits from object*

  Abstract class for all channels. 
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  message_type : yoton.MessageType instance 
      (default is yoton.TEXT)
      Object to convert messages to bytes and bytes to messages. 
      Users can create their own message_type class to enable 
      communicating any type of message they want.
  
  **Details**
  
  
  Messages send via a channel are delivered asynchronically to the 
  corresponding channels.
  
  All channels are associated with a context and can be used to send
  messages to other channels in the network. Each channel is also
  associated with a slot, which is a string that represents a kind 
  of address. A message send by a channel at slot X can only be received 
  by a channel with slot X. 
  
  Note that the channel appends an extension
  to the user-supplied slot name, that represents the message type 
  and messaging pattern of the channel. In this way, it is prevented
  that for example a PubChannel can communicate with a RepChannel.
  

  *PROPERTIES*

  .. _insertdocs-yoton-BaseChannel-closed:
  
  .. py:attribute:: yoton.BaseChannel.closed
  
    Get whether the channel is closed. 

  .. _insertdocs-yoton-BaseChannel-pending:
  
  .. py:attribute:: yoton.BaseChannel.pending
  
    Get the number of pending incoming messages. 

  .. _insertdocs-yoton-BaseChannel-received:
  
  .. py:attribute:: yoton.BaseChannel.received
  
    Signal that is emitted when new data is received. Multiple 
    arrived messages may result in a single call to this method. 
    There is no guarantee that recv() has not been called in the 
    mean time. The signal is emitted with the channel instance
    as argument.

  .. _insertdocs-yoton-BaseChannel-slot_incoming:
  
  .. py:attribute:: yoton.BaseChannel.slot_incoming
  
    Get the incoming slot name.

  .. _insertdocs-yoton-BaseChannel-slot_outgoing:
  
  .. py:attribute:: yoton.BaseChannel.slot_outgoing
  
    Get the outgoing slot name.

  *METHODS*

  .. _insertdocs-yoton-BaseChannel-close:
  
  .. py:method:: yoton.BaseChannel.close()
  
    Close the channel, i.e. unregisters this channel at the context.
    A closed channel cannot be reused.
    
    Future attempt to send() messages will result in an IOError 
    being raised. Messages currently in the channel's queue can 
    still be recv()'ed, but no new messages will be delivered at 
    this channel.
    



.. insertdocs end::

.. insertdocs start:: yoton.PubChannel
.. insertdocs :members: 


.. _insertdocs-yoton-PubChannel:

.. py:class:: yoton.PubChannel(context, slot_base, message_type=yoton.TEXT)

  *Inherits from BaseChannel*

  The publish part of the publish/subscribe messaging pattern.
  Sent messages are received by all :ref:`yoton.SubChannel<insertdocs-yoton-SubChannel>` instances with 
  the same slot. 
  
  There are no limitations for this channel if events are not processed.
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  message_type : yoton.MessageType instance 
      (default is yoton.TEXT)
      Object to convert messages to bytes and bytes to messages. 
      Users can create their own message_type class to let channels
      any type of message they want.
  

  *METHODS*

  .. _insertdocs-yoton-PubChannel-send:
  
  .. py:method:: yoton.PubChannel.send(message)
  
    Send a message over the channel. What is send as one 
    message will also be received as one message.
    
    The message is queued and delivered to all corresponding 
    SubChannels (i.e. with the same slot) in the network.
    



.. insertdocs end::

.. insertdocs start:: yoton.SubChannel
.. insertdocs :members: 
    

.. _insertdocs-yoton-SubChannel:

.. py:class:: yoton.SubChannel(context, slot_base, message_type=yoton.TEXT)

  *Inherits from BaseChannel*

  The subscribe part of the publish/subscribe messaging pattern.
  Received messages were sent by a :ref:`yoton.PubChannel<insertdocs-yoton-PubChannel>` instance at the 
  same slot. 
  
  This channel can be used as an iterator, which yields all pending 
  messages. The function :ref:`yoton.select_sub_channel<insertdocs-yoton-select_sub_channel>` can
  be used to synchronize multiple SubChannel instances. 
  
  If no events being processed this channel works as normal, except 
  that the received signal will not be emitted, and sync mode will 
  not work.
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  message_type : yoton.MessageType instance 
      (default is yoton.TEXT)
      Object to convert messages to bytes and bytes to messages. 
      Users can create their own message_type class to let channels
      any type of message they want.
  

  *METHODS*

  .. _insertdocs-yoton-SubChannel-next:
  
  .. py:method:: yoton.SubChannel.next()
  
    Return the next message, or raises StopIteration if non available.
    

  .. _insertdocs-yoton-SubChannel-recv:
  
  .. py:method:: yoton.SubChannel.recv(block=True)
  
    Receive a message from the channel. What was send as one 
    message is also received as one message.
    
    If block is False, returns empty message if no data is available. 
    If block is True, waits forever until data is available.
    If block is an int or float, waits that many seconds.
    If the channel is closed, returns empty message.
    

  .. _insertdocs-yoton-SubChannel-recv_all:
  
  .. py:method:: yoton.SubChannel.recv_all()
  
    Receive a list of all pending messages. The list can be empty.
    

  .. _insertdocs-yoton-SubChannel-recv_selected:
  
  .. py:method:: yoton.SubChannel.recv_selected()
  
    Receive a list of messages. Use only after calling 
    :ref:`yoton.select_sub_channel<insertdocs-yoton-select_sub_channel>` with this channel as one of the arguments.
    
    The returned messages are all received before the first pending
    message in the other SUB-channels given to select_sub_channel.
    
    The combination of this method and the function select_sub_channel
    enables users to combine multiple SUB-channels in a way that 
    preserves the original order of the messages.
    

  .. _insertdocs-yoton-SubChannel-set_sync_mode:
  
  .. py:method:: yoton.SubChannel.set_sync_mode(value)
  
    Set or unset the SubChannel in sync mode. When in sync mode, all 
    channels that send messages to this channel are blocked if 
    the queue for this SubChannel reaches a certain size.
    
    This feature can be used to limit the rate of senders if the consumer
    (i.e. the one that calls recv()) cannot keep up with processing
    the data. 
    
    This feature requires the yoton event loop to run at the side
    of the SubChannel (not necessary for the :ref:`yoton.PubChannel<insertdocs-yoton-PubChannel>` side).
    



.. insertdocs end::

.. insertdocs start:: yoton.select_sub_channel


.. _insertdocs-yoton-select_sub_channel:

.. py:function:: yoton.select_sub_channel(channel1, channel2, ...)

  Returns the channel that has the oldest pending message of all 
  given yoton.SubCannel instances. Returns None if there are no pending 
  messages.
  
  This function can be used to read from SubCannels instances in the
  order that the messages were send.
  
  After calling this function, use channel.recv_selected() to obtain
  all messages that are older than any pending messages in the other
  given channels.
  
.. insertdocs end::

.. insertdocs start:: yoton.ReqChannel
.. insertdocs :members: 


.. _insertdocs-yoton-ReqChannel:

.. py:class:: yoton.ReqChannel(context, slot_base)

  *Inherits from BaseChannel*

  The request part of the request/reply messaging pattern.
  A ReqChannel instance sends request and receive the corresponding 
  replies. The requests are replied by a :ref:`yoton.RepChannel<insertdocs-yoton-RepChannel>` instance.
  
  This class adopts req/rep in a remote procedure call (RPC) scheme.
  The handling of the result is done using a :ref:`yoton.Future<insertdocs-yoton-Future>` object, which 
  follows the approach specified in PEP 3148. Note that for the use
  of callbacks, the yoton event loop must run.
  
  Basic load balancing is performed by first asking all potential
  repliers whether they can handle a request. The actual request
  is then send to the first replier to respond.
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  
  **Usage**
  
  
  One performs a call on a virtual method of this object. The actual
  method is executed by the :ref:`yoton.RepChannel<insertdocs-yoton-RepChannel>` instance. The method can be 
  called with normal and keyword arguments, which can be (a 
  combination of): None, bool, int, float, string, list, tuple, dict.
  
  **Example**
  
  .. code-block:: python
  
      # Fast, but process is idling when waiting for the response.
      reply = req.add(3,4).result(2.0) # Wait two seconds
      
      # Asynchronous processing, but no waiting.
      def reply_handler(future):
          ... # Handle reply
      future = req.add(3,4)
      future.add_done_callback(reply_handler)
      
      



.. insertdocs end::

.. insertdocs start:: yoton.RepChannel
.. insertdocs :members: 


.. _insertdocs-yoton-RepChannel:

.. py:class:: yoton.RepChannel(context, slot_base)

  *Inherits from BaseChannel*

  The reply part of the request/reply messaging pattern.
  A RepChannel instance receives request and sends the corresponding 
  replies. The requests are send from a :ref:`yoton.ReqChannel<insertdocs-yoton-ReqChannel>` instance.
  
  This class adopts req/rep in a remote procedure call (RPC) scheme.
  
  To use a RepChannel, subclass this class and implement the methods
  that need to be available. The reply should be (a combination of)
  None, bool, int, float, string, list, tuple, dict. 
  
  This channel needs to be set to event or thread mode to function 
  (in the first case yoton events need to be processed too).
  To stop handling events again, use set_mode('off').
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  

  *METHODS*

  .. _insertdocs-yoton-RepChannel-echo:
  
  .. py:method:: yoton.RepChannel.echo(arg1, sleep=0.0)
  
    Default procedure that can be used for testing. It returns
    a tuple (first_arg, context_id)
    

  .. _insertdocs-yoton-RepChannel-set_mode:
  
  .. py:method:: yoton.RepChannel.set_mode(mode)
  
    Set the replier to its operating mode, or turn it off.
    
    Modes:
      * 0 or 'off': do not process requests
      * 1 or 'event': use the yoton event loop to process requests
      * 2 or 'thread': process requests in a separate thread
    



.. insertdocs end::

.. insertdocs start:: yoton.Future
.. insertdocs :members: 


.. _insertdocs-yoton-Future:

.. py:class:: yoton.Future(req_channel, req, request_id)

  *Inherits from object*

  The Future object represents the future result of a request done at 
  a :ref:`yoton.ReqChannel<insertdocs-yoton-ReqChannel>`.
  
  It enables:
    * checking whether the request is done.
    * getting the result or the exception raised during handling the request.
    * canceling the request (if it is not yet running)
    * registering callbacks to handle the result when it is available
  

  *METHODS*

  .. _insertdocs-yoton-Future-add_done_callback:
  
  .. py:method:: yoton.Future.add_done_callback(fn)
  
    Attaches the callable fn to the future. fn will be called, with 
    the future as its only argument, when the future is cancelled or 
    finishes running.
    
    Added callables are called in the order that they were added. If 
    the callable raises a Exception subclass, it will be logged and 
    ignored. If the callable raises a BaseException subclass, the 
    behavior is undefined.
    
    If the future has already completed or been cancelled, fn will be 
    called immediately.
    

  .. _insertdocs-yoton-Future-cancel:
  
  .. py:method:: yoton.Future.cancel()
  
    Attempt to cancel the call. If the call is currently being executed
    and cannot be cancelled then the method will return False, otherwise
    the call will be cancelled and the method will return True.
    

  .. _insertdocs-yoton-Future-cancelled:
  
  .. py:method:: yoton.Future.cancelled()
  
    Return True if the call was successfully cancelled.
    

  .. _insertdocs-yoton-Future-done:
  
  .. py:method:: yoton.Future.done()
  
    Return True if the call was successfully cancelled or finished running.
    

  .. _insertdocs-yoton-Future-exception:
  
  .. py:method:: yoton.Future.exception(timeout)
  
    Return the exception raised by the call. If the call hasn’t yet
    completed then this method will wait up to timeout seconds. If 
    the call hasn’t completed in timeout seconds, then a TimeoutError 
    will be raised. timeout can be an int or float. If timeout is not 
    specified or None, there is no limit to the wait time.
    
    If the future is cancelled before completing then CancelledError 
    will be raised.
    
    If the call completed without raising, None is returned.
    

  .. _insertdocs-yoton-Future-result:
  
  .. py:method:: yoton.Future.result(timeout=None)
  
    Return the value returned by the call. If the call hasn’t yet 
    completed then this method will wait up to timeout seconds. If 
    the call hasn’t completed in timeout seconds, then a TimeoutError 
    will be raised. timeout can be an int or float. If timeout is not 
    specified or None, there is no limit to the wait time.
    
    If the future is cancelled before completing then CancelledError 
    will be raised.
    
    If the call raised, this method will raise the same exception.
    

  .. _insertdocs-yoton-Future-result_or_cancel:
  
  .. py:method:: yoton.Future.result_or_cancel(timeout=1.0)
  
    Return the value returned by the call. If the call hasn’t yet 
    completed then this method will wait up to timeout seconds. If 
    the call hasn’t completed in timeout seconds, then the call is
    cancelled and the method will return None.
    

  .. _insertdocs-yoton-Future-running:
  
  .. py:method:: yoton.Future.running()
  
    Return True if the call is currently being executed and cannot be 
    cancelled.
    

  .. _insertdocs-yoton-Future-set_auto_cancel_timeout:
  
  .. py:method:: yoton.Future.set_auto_cancel_timeout(timeout)
  
    Set the timeout after which the call is automatically cancelled
    if it is not done yet. By default, this value is 10 seconds.
    
    If timeout is None, there is no limit to the wait time.
    

  .. _insertdocs-yoton-Future-set_exception:
  
  .. py:method:: yoton.Future.set_exception(exception)
  
    Sets the result of the work associated with the Future to the 
    Exception exception. This method should only be used by Executor 
    implementations and unit tests.
    

  .. _insertdocs-yoton-Future-set_result:
  
  .. py:method:: yoton.Future.set_result(result)
  
    Sets the result of the work associated with the Future to result.
    This method should only be used by Executor implementations and
    unit tests.
    

  .. _insertdocs-yoton-Future-set_running_or_notify_cancel:
  
  .. py:method:: yoton.Future.set_running_or_notify_cancel()
  
    This method should only be called by Executor implementations before 
    executing the work associated with the Future and by unit tests.
    
    If the method returns False then the Future was cancelled, i.e. 
    Future.cancel() was called and returned True. 
    
    If the method returns True then the Future was not cancelled and 
    has been put in the running state, i.e. calls to Future.running() 
    will return True.
    
    This method can only be called once and cannot be called after 
    Future.set_result() or Future.set_exception() have been called.
    



.. insertdocs end::

.. insertdocs start:: yoton.StateChannel
.. insertdocs :members: 


.. _insertdocs-yoton-StateChannel:

.. py:class:: yoton.StateChannel(context, slot_base, message_type=yoton.TEXT)

  *Inherits from BaseChannel*

  Channel class for the state messaging pattern. A state is synchronized
  over all state channels of the same slot. Each channel can 
  send (i.e. set) the state and recv (i.e. get) the current state.
  Note however, that if two StateChannel instances set the state
  around the same time, due to the network delay, it is undefined
  which one sets the state the last.
  
  The context will automatically call this channel's send_last()
  method when a new context enters the network.
  
  The recv() call is always non-blocking and always returns the last
  received message: i.e. the current state.
  
  There are no limitations for this channel if events are not 
  processed, except that the received signal is not emitted.
  
  **Parameters**
  
  
  context : :ref:`yoton.Context<insertdocs-yoton-Context>` instance
      The context that this channel uses to send messages in a network.
  slot_base : string
      The base slot name. The channel appends an extension to indicate
      message type and messaging pattern to create the final slot name.
      The final slot is used to connect channels at different contexts
      in a network
  message_type : yoton.MessageType instance 
      (default is yoton.TEXT)
      Object to convert messages to bytes and bytes to messages. 
      Users can create their own message_type class to let channels
      any type of message they want.
  

  *METHODS*

  .. _insertdocs-yoton-StateChannel-recv:
  
  .. py:method:: yoton.StateChannel.recv(block=False)
  
    Get the state of the channel. Always non-blocking. Returns the
    most up to date state.
    

  .. _insertdocs-yoton-StateChannel-send:
  
  .. py:method:: yoton.StateChannel.send(message)
  
    Set the state of this channel.
    
    The state-message is queued and send over the socket by the IO-thread. 
    Zero-length messages are ignored.
    

  .. _insertdocs-yoton-StateChannel-send_last:
  
  .. py:method:: yoton.StateChannel.send_last()
  
    Resend the last message.
    



.. insertdocs end::
