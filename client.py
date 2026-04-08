import socket
import sys
from protocol import create_client_context, recv_line, send_line

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"  # pass server IP as argument
PORT = 5000

context = create_client_context("cert.pem")  # trust the self-signed cert

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn = context.wrap_socket(sock, server_hostname=HOST)

try:
    conn.connect((HOST, PORT))
except OSError as exc:
    print(f"Could not connect to {HOST}:{PORT} - {exc}")
    print("If the server is on another laptop, run: python client.py <server-laptop-ip>")
    raise SystemExit(1)

send_line(conn, "CLIENT")

buffer = bytearray()

while True:
    job = input("Enter job (ex: ADD 5 3): ")

    if not job:
        continue

    send_line(conn, f"JOB {job}")

    response = recv_line(conn, buffer)
    if response is None:
        print("Server disconnected")
        break

    print(response)