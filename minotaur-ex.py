#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import asyncio
from pathlib import Path

from minotaur import Inotify, Mask

# noinspection DuplicatedCode
PATHS = (Path('/usr/bin/python'), Path('/home/kincerb/Projects'))


def main():
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(get_events(PATHS))
    except KeyboardInterrupt:
        print('Shutting down.')

    tasks = asyncio.all_tasks(loop=loop)
    for t in tasks:
        t.cancel()

    group = asyncio.gather(*tasks, return_exceptions=True)
    loop.run_until_complete(group)
    loop.close()


async def get_events(paths: tuple):
    with Inotify(blocking=False) as inotify:
        for path in paths:
            inotify.add_watch(path, Mask.ATTRIB | Mask.ACCESS | Mask.OPEN)
        async for event in inotify:
            print(event)


if __name__ == '__main__':
    main()
