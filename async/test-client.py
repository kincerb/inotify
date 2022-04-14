#!/usr/bin/env python
import argparse
import asyncio
import logging
import logging.handlers
import signal
import sys
from asyncio import StreamReader
from pathlib import Path

logger = logging.getLogger(__name__)


class ClientError(Exception):
    """Exception class for this script."""
    pass


def handler(sig):
    loop = asyncio.get_running_loop()
    for task in asyncio.all_tasks(loop=loop):
        task.cancel()
    logger.debug(f'Signal: {sig!s} caught, shutting down.')
    loop.remove_signal_handler(signal.SIGTERM)
    loop.add_signal_handler(signal.SIGINT, lambda: None)


async def monitor_events(reader: StreamReader) -> None:
    while (message := await reader.readline()) != b'':
        logger.info(message.decode())
    logger.info('Server has closed connection.')


async def main(args: argparse.Namespace) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handler, sig)

    reader, _ = await asyncio.open_unix_connection(args.socket)
    event_printer = asyncio.create_task(monitor_events(reader))

    try:
        await asyncio.wait({event_printer})
    except asyncio.CancelledError:
        logger.info('Client has shut down.')
    except Exception as e:
        logger.exception(e)


def get_args() -> argparse.Namespace:
    """Gather arguments for the script."""

    parser = argparse.ArgumentParser(
        description='Client to print inotify events',
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
    args = get_args()
    setup_logging(verbosity=args.verbosity)
    asyncio.run(main(args))
