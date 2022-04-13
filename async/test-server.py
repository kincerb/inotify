#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import argparse
import asyncio
import logging
import logging.handlers
import socket
import sys
from asyncio import StreamReader, StreamWriter
from pathlib import Path

logger = logging.getLogger(__name__)


class SocketServerState:
    def __init__(self):
        self._writers = []

    async def add_client(self, reader: StreamReader, writer: StreamWriter):
        self._writers.append(writer)
        await self._on_connect(writer)
        # asyncio.create_task(self._publish_event(writer, event_payload))

    async def _on_connect(self, writer: StreamWriter):
        writer.write('You are now subscribed to inotify events.'.encode())
        await writer.drain()

    async def _publish_event(self, writer: StreamWriter, event_payload):
        await self._notify_all(event_payload)

    async def _notify_all(self, event_payload: str):
        for writer in self._writers:
            try:
                writer.write(event_payload.encode())
                await writer.drain()
            except ConnectionError as e:
                logger.error(f'Failed to deliver message: {e}')
                self._writers.remove(writer)


async def main() -> None:
    args = get_args()
    setup_logging(verbosity=args.verbosity)
    server_state = SocketServerState()

    async def client_connected(reader: StreamReader, writer: StreamWriter) -> None:
        await server_state.add_client(reader, writer)

    server = await asyncio.start_unix_server(client_connected, args.socket)

    async with server:
        await server.serve_forever()


def setup_server_socket(socket_path: Path, blocking: bool = False) -> socket.SocketType:
    socket_path.unlink(missing_ok=True)
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.setblocking(blocking)
    server_socket.bind(str(socket_path))
    return server_socket


def get_args() -> argparse.Namespace:
    """Gather arguments for the script."""

    parser = argparse.ArgumentParser(
        description='Server to publish inotify events',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--socket',
                        required=False,
                        dest='socket',
                        default='/var/tmp/inotify.sock',
                        type=Path,
                        help='Socket to use for server.')
    parser.add_argument('-v', '--verbose',
                        required=False,
                        dest='verbosity',
                        action='count',
                        default=0,
                        help='Increase output verbosity.')
    return parser.parse_args()


def setup_logging(verbosity: int = 0) -> None:
    """Configures global logging object for the script."""
    level = logging.INFO if verbosity == 0 else logging.DEBUG
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            stdout_handler,
            stderr_handler,
        ]
    )


if __name__ == '__main__':
    main()
