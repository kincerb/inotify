#!/usr/bin/env /home/kincerb/Projects/inotify-testing/venv/bin/python
import socket
from pathlib import Path

SOCKET_PATH = Path('/var/tmp/inotify.sock')


def main() -> None:
    SOCKET_PATH.unlink(missing_ok=True)
    server_socket = setup_server_socket(blocking=True)
    server_socket.listen(1)

    while True:
        connection, client_address = server_socket.accept()
        try:
            print(f'Connection from {client_address}')
            while True:
                data = connection.recv(1024)
                print(f'Received {data}')
                if data:
                    connection.sendall(data)
                else:
                    break
        finally:
            connection.close()
            SOCKET_PATH.unlink(missing_ok=True)


def setup_server_socket(socket_path: Path = SOCKET_PATH, blocking: bool = False) -> socket.SocketType:
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server_socket.setblocking(blocking)
    server_socket.bind(str(socket_path))
    return server_socket


if __name__ == '__main__':
    main()
