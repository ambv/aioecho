import asyncio
import socket
import sys


async def realtime_status(protocol, lifecycle):
    """Report status changes every 100ms.

    `protocol` must provide `connections` and `errors` attributes.
    Completion or cancellation of the `lifecycle` future cancels monitoring of
    the status.
    """
    last = 0
    e = 0
    while not lifecycle.done() and not lifecycle.cancelled():
        if protocol.connections != last or protocol.errors != e:
            last = protocol.connections
            e = protocol.errors
            sys.stdout.write('{:8d} {:4d}    \r'.format(last, e))
            sys.stdout.flush()
        await asyncio.sleep(0.1)


def set_socket_io_timeouts(transport, seconds, useconds=0):
    """Enables stretching the timeouts of transport sockets.

    Useful with highly concurrent workloads. Returns False if it failed to
    set the timeouts.
    """
    seconds = (seconds).to_bytes(8, 'little')
    useconds = (useconds).to_bytes(8, 'little')
    sock = transport.get_extra_info('socket')
    try:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVTIMEO,
            seconds + useconds,
        )
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDTIMEO,
            seconds + useconds,
        )
        return True
    except OSError:
        return False


# Change to `verbose = print` to get obnoxiously detailed logging.
verbose = lambda *a, **kw: None
