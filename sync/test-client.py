#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import socket
import sys
from pathlib import Path

SOCKET_PATH = Path('/var/tmp/inotify.sock')


def main() -> None:
    if not SOCKET_PATH.exists():
        print(f'Socket {SOCKET_PATH} does not exist, exiting.')
        sys.exit(1)
    client_socket = setup_client_socket(blocking=True)

    try:
        message = b'Test message.'
        client_socket.sendall(message)

        amount_received = 0
        amount_expected = len(message)

        while amount_received < amount_expected:
            data = client_socket.recv(1024)
            amount_received += len(data)
            print(f'Received {data}')
    finally:
        client_socket.close()


def setup_client_socket(socket_path: Path = SOCKET_PATH, blocking: bool = False) -> socket.SocketType:
    client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client_socket.setblocking(blocking)
    try:
        client_socket.connect(str(socket_path))
    except socket.error as err:
        print(f'Exiting due to {err}')
        sys.exit(2)
    return client_socket


if __name__ == '__main__':
    main()
