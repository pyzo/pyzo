Experiments with sockets
========================

I performed a series on tests on bot Windows and Linux. Testing sockets on localhost and publichost (what you get with gethostname()), for killing one of the processes, and removing the connection (unplugging the cable).

I wanted to answer the following questions:
  * When and how can we detect that the other process dropped (killed or terminated)?
  * When and how can we detect connection problems?
  * Can we still send data if the other end stops receiving data? And if not, can we still detect a connection drop?


On Windows, same box
-----------------------

  * If hosting on network level, and killing the network device, the 
    disconnection is immediately detected (socket.error is raised when 
    calling send() or recv()).
  * Killing either process will immediately result in an error being raised.
  * This is true for hosting local or public.
  * -> Therefore, when hosting on localhost (the connection cannot be lost) 
    we do not need a heartbeat.


On Linux, same box
---------------------

  * I cannot kill the connection, only the process. When I do, the other 
    side will be able to receive, but receives EOF (empty bytes), which 
    looks like a nice exit. Note that this behavior is different than on Windows.
  * When the other side does not receive, I can still send huge amounts of data.
  * This applies when hosting as localhost or as gethostname.

On Linux & Windows, different boxes
------------------------------------

  * When I kill the connection (remove network cable), it takes a while 
    for either end to see that the connection is dead. I can even put the 
    cable back in and go on communicating. This is a feature of TCP to be 
    robust against network problems. See
    http://www.unixguide.net/network/socketfaq/2.8.shtml
  * When I keep the connection, but kill the process on either end, this 
    is detected immediately (in the same way as described above, depending 
    on the OS); there's still low-level communication between the two boxes, 
    and the port is detected to be unavailable.
  * On Linux I can keep sending huge amounts of data even if the other 
    end does not receive. On Windows I can't. In both cases they can detect 
    the other process dropping.

Conclusions
--------------

  * On local machine (broker-kernel), we use localhost so that we will 
    not have network problems. We can detect if a process drops, which 
    is essential.
  * Between boxes, we use a heartbeat signal to be able to determine 
    whether the connection is still there. If we set that timeout low 
    enough (<30 sec or so) we can even distinguish a network problem from 
    a process crash. This should not be necessary, however, because we 
    can assume (I guess) that the broker and client close nicely.
