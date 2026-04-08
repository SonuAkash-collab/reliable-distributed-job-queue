import socket
import time
import sys
import os

from protocol import create_client_context, recv_line, send_line

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"  # pass server IP as argument
PORT = 5000
WORKER_ID = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
DELAY_MS = int(os.getenv("WORKER_DELAY_MS", "0"))
FAIL_AFTER = int(os.getenv("WORKER_FAIL_AFTER", "0"))
processed_jobs = 0

context = create_client_context("cert.pem")  # trust the self-signed cert

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn = context.wrap_socket(sock, server_hostname=HOST)

conn.connect((HOST, PORT))

send_line(conn, "WORKER")

buffer = bytearray()


def execute(job):

    parts = job.split()

    if parts[0] == "ADD":
        return str(int(parts[1]) + int(parts[2]))

    if parts[0] == "MUL":
        return str(int(parts[1]) * int(parts[2]))

    return "UNKNOWN JOB"


while True:

    send_line(conn, "GET_JOB")

    job = recv_line(conn, buffer)

    if job is None:
        break

    if job == "NO_JOB":
        time.sleep(2)
        continue

    if DELAY_MS > 0:
        time.sleep(DELAY_MS / 1000)

    result = execute(job)

    send_line(conn, f"Result {result}")
    processed_jobs += 1

    if FAIL_AFTER and processed_jobs >= FAIL_AFTER:
        raise SystemExit(f"{WORKER_ID} stopped after {processed_jobs} jobs")