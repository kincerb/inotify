#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import asyncio
from pathlib import Path
from signal import SIGINT, SIGTERM

from asyncinotify import Inotify, Mask

# noinspection DuplicatedCode
PATHS = (Path('/usr/bin/python'), Path('/home/kincerb/Projects'))


async def main() -> None:
    loop = asyncio.get_running_loop()
    for sig in (SIGTERM, SIGINT):
        loop.add_signal_handler(sig, handler, sig)

    try:
        await get_events(PATHS)
    except asyncio.CancelledError:
        print('Shutting down...')


async def get_events(paths: tuple) -> None:
    with Inotify() as inotify:
        for path in paths:
            inotify.add_watch(path, Mask.ATTRIB | Mask.ACCESS | Mask.OPEN)
        async for event in inotify:
            print(f'{event}:\t{event.path}')


def handler(sig):
    loop = asyncio.get_running_loop()
    for task in asyncio.all_tasks(loop=loop):
        task.cancel()
    print(f'Signal: {sig!s} caught, shutting down.')
    loop.remove_signal_handler(SIGTERM)
    loop.add_signal_handler(SIGINT, lambda: None)
    

if __name__ == '__main__':
    asyncio.run(main())
