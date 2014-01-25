:mod:`clientserver` -- Request-reply pattern using a client-server model
=========================================================================

.. insertdocs start:: yoton.clientserver


.. _insertdocs-yoton-clientserver:

.. py:module:: yoton.clientserver

yoton.clientserver.py

Yoton comes with a small framework to setup a request-reply pattern
using a client-server model (over a non-persistent connection), 
similar to telnet. This allows one process to easily ask small pieces 
of information from another process.

To create a server, create a class that inherits from 
:ref:`yoton.RequestServer<insertdocs-yoton-RequestServer>` and implement its handle_request() method.

A client process can simply use the :ref:`yoton.do_request<insertdocs-yoton-do_request>` function. 
Example: ``yoton.do_request('www.google.com:80', 'GET http/1.1\r\n')``

The client server model is implemented using one function and one class:
:ref:`yoton.do_request<insertdocs-yoton-do_request>` and :ref:`yoton.RequestServer<insertdocs-yoton-RequestServer>`.

**Details**



The server implements a request/reply pattern by listening at a socket. 
Similar to telnet, each request is handled using a connection 
and the socket is closed after the response is send. 

The request server can setup to run in the main thread, or can be started 
using its own thread. In the latter case, one can easily create multiple
servers in a single process, that listen on different ports.


.. insertdocs end::

Implementation 
--------------
The client server model is implemented using one function and one class:
:ref:`yoton.do_request<insertdocs-yoton-do_request>` and :ref:`yoton.RequestServer<insertdocs-yoton-RequestServer>`.

.. insertdocs start:: yoton.do_request


.. _insertdocs-yoton-do_request:

.. py:function:: yoton.do_request(address, request, timeout=-1)

  Do a request at the server at the specified address. The server can
  be a :ref:`yoton.RequestServer<insertdocs-yoton-RequestServer>`, or any other server listening on a socket
  and following a REQ/REP pattern, such as html or telnet. For example:
  ``html = do_request('www.google.com:80', 'GET http/1.1\r\n')``
  
  **Parameters**
  
  
  address : str
      Should be of the shape hostname:port. 
  request : string
      The request to make.
  timeout : float
      If larger than 0, will wait that many seconds for the respons, and
      return None if timed out.
  
  **Notes on hostname**
  
  
  The hostname can be:
    * The IP address, or the string hostname of this computer. 
    * 'localhost': the connections is only visible from this computer. 
      Also some low level networking layers are bypassed, which results
      in a faster connection. The other context should also connect to
      'localhost'.
    * 'publichost': the connection is visible by other computers on the 
      same network.
  
.. insertdocs end::

.. insertdocs start:: yoton.RequestServer
  

.. _insertdocs-yoton-RequestServer:

.. py:class:: yoton.RequestServer(address, async=False, verbose=0)

  *Inherits from Thread*

  Setup a simple server that handles requests similar to a telnet server, 
  or asyncore. Starting the server using run() will run the server in
  the calling thread. Starting the server using start() will run the
  server in a separate thread.
  
  To create a server, subclass this class and re-implement the 
  handle_request method. It accepts a request and should return a 
  reply. This server assumes utf-8 encoded messages.
  
  **Parameters**
  
  
  address : str
      Should be of the shape hostname:port. 
  async : bool
      If True, handles each incoming connection in a separate thread.
      This might be advantageous if a the handle_request() method 
      takes a long time to execute.
  verbose : bool
      If True, print a message each time a connection is accepted.
  
  **Notes on hostname**
  
  
  The hostname can be:
    * The IP address, or the string hostname of this computer. 
    * 'localhost': the connections is only visible from this computer. 
      Also some low level networking layers are bypassed, which results
      in a faster connection. The other context should also connect to
      'localhost'.
    * 'publichost': the connection is visible by other computers on the 
      same network. 
  

.. insertdocs end::

