import asyncio
import os
import sys
import textwrap

from echoutil import realtime_status, set_socket_io_timeouts, verbose


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


async def wait_until_done(connection):
    """Waits for both the connection to be open and the entire workload to be
    processed."""
    transport, protocol = await connection
    await protocol.done


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
    tasks = [
        wait_until_done(
            loop.create_connection(
                lambda: EchoClient(data),
                'localhost',
                8888,
            ),
        )
        for _ in range(how_many_connections)
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
            print("{} tasks, {} exceptions".format(len(tasks), exceptions))
        loop.close()


if __name__ == '__main__':
    how_many_connections = 10000
    if len(sys.argv) == 2:
        how_many_connections = int(sys.argv[1])
    main(how_many_connections)
