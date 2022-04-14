#!/usr/bin/env python
import argparse
import asyncio
import functools
import logging
import logging.handlers
import signal
import sys
from asyncio import StreamReader, StreamWriter
from pathlib import Path
from typing import List

from asyncinotify import Inotify, Mask

logger = logging.getLogger(__name__)


class ServerError(Exception):
    """Exception class for this script."""
    pass


def handler(sig):
    loop = asyncio.get_running_loop()
    for task in asyncio.all_tasks(loop=loop):
        task.cancel()
    logger.debug(f'Signal: {sig!s} caught, shutting down.')
    loop.remove_signal_handler(signal.SIGTERM)
    loop.add_signal_handler(signal.SIGINT, lambda: None)


class SocketServerState:
    def __init__(self, args):
        self._cli_args = args
        self._writers = []
        self._events = asyncio.Queue()
        asyncio.create_task(self.monitor_paths(self._cli_args.paths))
        asyncio.create_task(self._monitor_queue())

    async def add_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        self._writers.append(writer)
        await self._on_connect(writer)

    async def _on_connect(self, writer: StreamWriter) -> None:
        logger.info(f'New client connected, total of {len(self._writers)} user(s).')
        writer.write('You are now subscribed to inotify events.'.encode())
        await writer.drain()

    async def _monitor_queue(self) -> None:
        while True:
            await asyncio.sleep(1)
            event = await self._events.get()
            logger.debug('Received event off the queue, notifying clients.')
            await self._notify_all(str(event))

    async def _notify_all(self, event_payload: str) -> None:
        for writer in self._writers:
            try:
                writer.write(event_payload.encode())
                await writer.drain()
            except ConnectionError:
                self._writers.remove(writer)
                logger.debug(f'Client removed, total of {len(self._writers)} user(s).')

    async def monitor_paths(self, paths: List[str]) -> None:
        with Inotify() as inotify:
            for path in paths:
                logger.debug(f'Adding watch for {path}.')
                inotify.add_watch(path, Mask.ATTRIB | Mask.ACCESS | Mask.OPEN)
            async for event in inotify:
                logger.debug(f'Adding {event} to the queue.')
                await self._events.put(event)


async def main(args: argparse.Namespace) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handler, sig)

    try:
        setup_server_socket(args.socket)
    except ServerError as e:
        logger.critical('Failed to setup socket for server.', exc_info=e)
        sys.exit(1)

    server_state = SocketServerState(args)

    async def client_connected(reader: StreamReader, writer: StreamWriter) -> None:
        await server_state.add_client(reader, writer)

    try:
        server = await asyncio.start_unix_server(client_connected, args.socket)
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        logger.info('Server has shut down.')


def setup_server_socket(socket_path: Path) -> None:
    """Raise exception if socket path cannot be used."""
    try:
        socket_path.unlink(missing_ok=True)
        socket_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ServerError(e)
    except Exception as e:
        raise ServerError(e)


def get_args() -> argparse.Namespace:
    """Gather arguments for the script."""

    parser = argparse.ArgumentParser(
        description='Server to publish inotify events',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('paths',
                        nargs='*',
                        default=['/usr/bin/python3', '/home/kincerb'],
                        help='Filesystem paths to monitor.')
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
    args = get_args()
    setup_logging(verbosity=args.verbosity)
    asyncio.run(main(args))
