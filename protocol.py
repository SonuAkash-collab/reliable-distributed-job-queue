import ssl
import socket
from typing import Optional


BUFFER_SIZE = 4096


def create_client_context(certfile: str) -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(certfile)
    return context


def create_server_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def send_line(conn: socket.socket, message: str) -> None:
    conn.sendall((message.rstrip("\n") + "\n").encode())


def recv_line(conn: socket.socket, buffer: bytearray) -> Optional[str]:
    while True:
        newline_index = buffer.find(b"\n")
        if newline_index != -1:
            line = buffer[:newline_index]
            del buffer[:newline_index + 1]
            return line.decode().strip()

        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            if buffer:
                line = buffer.decode().strip()
                buffer.clear()
                return line
            return None

        buffer.extend(chunk)