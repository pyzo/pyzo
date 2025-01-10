from yoton.connection import Connection


class ItcConnection(Connection):
    """ItcConnection(context, hostname, port, name='')

    Not implemented .

    The inter-thread-communication connection class implements a
    connection between two contexts that are in the same process.
    Two instances of this class are connected using a weak reference.
    In case one of the ends is cleaned up by the garbadge collector,
    the other end will close the connection.

    """

    pass
    # todo: implement me
