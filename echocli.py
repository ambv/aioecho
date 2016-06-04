#!/usr/bin/env python3
import asyncio
from contextlib import ExitStack
import os
import random
import resource
import socket
import sys
import textwrap

from echoutil import realtime_status, set_socket_io_timeouts, verbose


RETRIES = 10


class EchoClient(asyncio.Protocol):
    """Sends `data` line by line and check that it receives the same data back.

    It's different from other toy examples in the following ways:
    - it never creates any asynchronous tasks itself
    - ...which is why it doesn't have to know anything about any event loops
    - it tracks the completion of its entire workload with the `done` future
    - it tracks its progress via the class-level counters below which can be
      used to show realtime stats to the user
    """
    connections = 0
    errors = 0

    def __init__(self, data):
        self.data_iter = iter(data.splitlines())
        self.last_sent = None
        self.done = asyncio.Future()
        self.transport = None
        self.id = EchoClient.connections
        EchoClient.connections += 1

    def connection_made(self, transport):
        self.transport = transport
        if not set_socket_io_timeouts(self.transport, 60, 0):
            self.transport.abort()
            return

        verbose(self.id, 'Connected to server')
        self._write_one()

    def connection_lost(self, exc, exc2=None):
        verbose(self.id, 'Disconnected from server', exc or '')
        try:
            self.transport.abort()  # free sockets early, free sockets often
        except Exception as e:
            print(self.id, 'While closing transport', e)
            exc2 = e
        finally:
            if exc or exc2:
                EchoClient.errors += 1
                self.done.set_exception(exc or exc2)
                self.done.exception()  # remove _tb_logger
            else:
                self.done.set_result(None)

    def data_received(self, data):
        verbose(self.id, 'Recv:', data.decode())
        assert self.last_sent == data, "Received unexpected data"
        self._write_one()

    def _write_one(self):
        chunk = next(self.data_iter, None)
        if chunk is None:
            self.transport.write_eof()
            return

        line = chunk.encode()
        self.transport.write(line)
        self.last_sent = line
        verbose(self.id, 'Sent:', chunk)


async def wait_until_done(loop, factory, jitter):
    """Waits for the connection to open and the workload to be processed.

    Note: there's retry logic to make sure we're connecting even in
    the face of momentary ECONNRESET on the server-side.

    Note: there's a manual socket passed to `create_connection` to
    circumvent the need to use domain name lookup. If faced with actual
    domain name lookup, do the same, awaiting on aiodns' resolver query.
    Don't use the builtin threadpool-based resolver.

    Note: We're adding the socket to be automatically closed by the exit
    stack. This cleans up all resources regardless of the contol flow.
    """
    await asyncio.sleep(jitter)
    retries = RETRIES * [1]  # non-exponential 10s
    with ExitStack() as stack:
        while True:
            try:
                sock = stack.enter_context(socket.socket())
                sock.connect(('127.0.0.1', 8888))
                connection = loop.create_connection(factory, sock=sock)
                transport, protocol = await connection
            except Exception as e:
                if not retries:
                    raise
                await asyncio.sleep(retries.pop(0) - random.random())
            else:
                break
        await protocol.done
    return len(retries)


def get_connected_socket():
    sock = socket.socket()
    sock.connect(('127.0.0.1', 8888))
    return sock


def main(how_many_connections):
    data = textwrap.dedent("""
    Much to his dad and mum's dismay
    Hōråcé ate himself one day
    He didn't stop to say his grace
    He just sat down and ate his face
    quit""").strip()

    print(
        'PID({}) attempting {} connections'.format(
            os.getpid(), how_many_connections,
        ),
    )
    loop = asyncio.get_event_loop()
    max_files = resource.getrlimit(resource.RLIMIT_NOFILE)[0]  # ulimit -n
    # Note: Increasing the divisor below will decrease the number of retries
    # but also decrease achievable concurrency.
    how_many_connections_per_second = min(max_files, how_many_connections) // 5
    tasks = [
        wait_until_done(
            loop,
            lambda: EchoClient(data),
            jitter / how_many_connections_per_second,
        )
        for jitter in range(how_many_connections)
    ]
    load_test = loop.create_task(asyncio.wait(tasks))
    monitor = loop.create_task(realtime_status(EchoClient, load_test))
    try:
        loop.run_until_complete(asyncio.wait((load_test, monitor)))
    except KeyboardInterrupt:
        pass
    finally:
        if load_test.done():
            done, _ = load_test.result()
            exceptions = sum(1 for d in done if d.exception())
            retries = sum(
                RETRIES - d.result()
                for d in done if not d.exception()
            )
            print(
                "{} tasks, {} exceptions, {} retries".format(
                    len(tasks),
                    exceptions,
                    retries,
                ),
            )
        loop.close()


if __name__ == '__main__':
    how_many_connections = 10000
    if len(sys.argv) == 2:
        how_many_connections = int(sys.argv[1])
    main(how_many_connections)
