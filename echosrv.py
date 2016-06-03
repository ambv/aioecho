import asyncio
import os

from echoutil import realtime_status, set_socket_io_timeouts, verbose


class EchoServer(asyncio.Protocol):
    """Receives lines and sends them right back.

    It's different from other toy examples in the following ways:
    - it never creates any asynchronous tasks itself
    - ...which is why it doesn't have to know anything about any event loops
    - it tracks its progress via the class-level counters below which can be
      used to show realtime stats to the user
    """
    connections = 0
    errors = 0

    def connection_made(self, transport):
        self.transport = transport
        if not set_socket_io_timeouts(self.transport, 60, 0):
            self.transport.abort()
            return

        peername = transport.get_extra_info('peername')
        verbose('Connection from', peername)
        EchoServer.connections += 1

    def connection_lost(self, exc):
        # free sockets early, free sockets often
        if exc:
            EchoServer.errors += 1
            self.transport.abort()
        else:
            self.transport.close()
        EchoServer.connections -= 1

    def data_received(self, data):
        message = data.decode()
        verbose('Recv:', message)

        if message == 'quit':
            verbose('Close the client socket')
            self.transport.close()
        else:
            self.transport.write(data)
            verbose('Sent:', message)


def main():
    loop = asyncio.get_event_loop()
    # Each client connection will create a new protocol instance
    coro = loop.create_server(EchoServer, '127.0.0.1', 8888)
    server = loop.run_until_complete(coro)

    for sock in server.sockets:
        print('PID({}) serving on {}'.format(os.getpid(), sock.getsockname()))
    server_closed = loop.create_task(server.wait_closed())
    monitor = loop.create_task(realtime_status(EchoServer, server_closed))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.cancel()
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == '__main__':
    main()
