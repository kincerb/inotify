#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import selectors
import socket
from pathlib import Path
from selectors import SelectorKey
from typing import List, Tuple

SOCKET_PATH = Path('/var/tmp/inotify.sock')


def main() -> None:
    selector = selectors.DefaultSelector()
    server_socket = setup_server_socket(blocking=False)
    server_socket.listen()

    selector.register(server_socket, selectors.EVENT_READ)

    while True:
        events: List[Tuple[SelectorKey, int]] = selector.select(timeout=1)

        for event, _ in events:
            event_socket = event.fileobj
            # if these are equal, this is a connection attempt
            if event_socket == server_socket:
                connection, address = server_socket.accept()
                connection.setblocking(False)
                selector.register(connection, selectors.EVENT_READ)
            else:
                data = event_socket.recv(1024)
                print(f'Data received: {data}')
                event_socket.send(data)


def setup_server_socket(socket_path: Path = SOCKET_PATH, blocking: bool = False) -> socket.SocketType:
    SOCKET_PATH.unlink(missing_ok=True)
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.setblocking(blocking)
    server_socket.bind(str(socket_path))
    return server_socket


if __name__ == '__main__':
    main()
