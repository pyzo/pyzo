Event system
============

.. insertdocs start:: yoton.events


.. _insertdocs-yoton-events:

.. py:module:: yoton.events

Module :ref:`yoton.events<insertdocs-yoton-events>`

Yoton comes with a simple event system to enable event-driven applications.

All channels are capable of running without the event system, but some
channels have limitations. See the documentation of the channels for 
more information. Note that signals only work if events are processed.


.. insertdocs end::

.. insertdocs start:: yoton.Signal
.. insertdocs :members: 


.. _insertdocs-yoton-Signal:

.. py:class:: yoton.Signal()

  *Inherits from object*

  The purpose of a signal is to provide an interface to bind/unbind 
  to events and to fire them. 
  
  One can bind() or unbind() a callable to the signal. When emitted, an
  event is created for each bound handler. Therefore, the event loop
  must run for signals to work.
  
  Some signals call the handlers using additional arguments to 
  specify specific information.
  

  *PROPERTIES*

  .. _insertdocs-yoton-Signal-type:
  
  .. py:attribute:: yoton.Signal.type
  
    The type (__class__) of this event. 

  *METHODS*

  .. _insertdocs-yoton-Signal-bind:
  
  .. py:method:: yoton.Signal.bind(func)
  
    Add an eventhandler to this event.             
    
    The callback/handler (func) must be a callable. It is called
    with one argument: the event instance, which can contain 
    additional information about the event.
    

  .. _insertdocs-yoton-Signal-emit:
  
  .. py:method:: yoton.Signal.emit(*args, **kwargs)
  
    Emit the signal, calling all bound callbacks with *args and **kwargs.
    An event is queues for each callback registered to this signal.
    Therefore it is safe to call this method from another thread.
    

  .. _insertdocs-yoton-Signal-emit_now:
  
  .. py:method:: yoton.Signal.emit_now(*args, **kwargs)
  
    Emit the signal *now*. All handlers are called from the calling
    thread. Beware, this should only be done from the same thread
    that runs the event loop.
    

  .. _insertdocs-yoton-Signal-unbind:
  
  .. py:method:: yoton.Signal.unbind(func=None)
  
    Unsubscribe a handler, If func is None, remove all handlers.  
    



.. insertdocs end::

.. insertdocs start:: yoton.Timer
.. insertdocs :members: 


.. _insertdocs-yoton-Timer:

.. py:class:: yoton.Timer(interval=1.0, oneshot=True)

  *Inherits from Signal*

  Timer class. You can bind callbacks to the timer. The timer is 
  fired when it runs out of time. 
  
  **Parameters**
  
  
  interval : number
      The interval of the timer in seconds.
  oneshot : bool
      Whether the timer should do a single shot, or run continuously.
  

  *PROPERTIES*

  .. _insertdocs-yoton-Timer-interval:
  
  .. py:attribute:: yoton.Timer.interval
  
    Set/get the timer's interval in seconds.

  .. _insertdocs-yoton-Timer-oneshot:
  
  .. py:attribute:: yoton.Timer.oneshot
  
    Set/get whether this is a oneshot timer. If not is runs
    continuously.

  .. _insertdocs-yoton-Timer-running:
  
  .. py:attribute:: yoton.Timer.running
  
    Get whether the timer is running. 

  *METHODS*

  .. _insertdocs-yoton-Timer-start:
  
  .. py:method:: yoton.Timer.start(interval=None, oneshot=None)
  
    Start the timer. If interval or oneshot are not given, 
    their current values are used.
    

  .. _insertdocs-yoton-Timer-stop:
  
  .. py:method:: yoton.Timer.stop()
  
    Stop the timer from running. 
    



.. insertdocs end::

.. insertdocs start:: yoton.call_later


.. _insertdocs-yoton-call_later:

.. py:function:: yoton.call_later(func, timeout=0.0, *args, **kwargs)

  Call the given function after the specified timeout.
  
  **Parameters**
  
  
  func : callable
      The function to call.
  timeout : number
      The time to wait in seconds. If zero, the event is put on the event
      queue. If negative, the event will be put at the front of the event
      queue, so that it's processed asap.
  args : arguments
      The arguments to call func with.
  kwargs: keyword arguments.
      The keyword arguments to call func with.
  
.. insertdocs end::

.. insertdocs start:: yoton.process_events


.. _insertdocs-yoton-process_events:

.. py:function:: yoton.process_events(block=False)

  Process all yoton events currently in the queue. 
  This function should be called periodically
  in order to keep the yoton event system running.
  
  block can be False (no blocking), True (block), or a float 
  blocking for maximally 'block' seconds.
  
.. insertdocs end::

.. insertdocs start:: yoton.start_event_loop


.. _insertdocs-yoton-start_event_loop:

.. py:function:: yoton.start_event_loop()

  Enter an event loop that keeps calling yoton.process_events().
  The event loop can be stopped using stop_event_loop().
  
.. insertdocs end::

.. insertdocs start:: yoton.stop_event_loop


.. _insertdocs-yoton-stop_event_loop:

.. py:function:: yoton.stop_event_loop()

  Stops the event loop if it is running.
  
.. insertdocs end::

.. insertdocs start:: yoton.embed_event_loop


.. _insertdocs-yoton-embed_event_loop:

.. py:function:: yoton.embed_event_loop(callback)

  Embed the yoton event loop in another event loop. The given callback
  is called whenever a new yoton event is created. The callback
  should create an event in the other event-loop, which should
  lead to a call to the process_events() method. The given callback
  should be thread safe.
  
  Use None as an argument to disable the embedding. 
  
.. insertdocs end::
