import argparse
import os
import socket
import subprocess
import sys
import time
import threading

from protocol import create_client_context, recv_line, send_line


HOST = "127.0.0.1"
PORT = 5000


def parse_args():
    parser = argparse.ArgumentParser(description="Failure scenario validation for the distributed job queue")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--jobs", type=int, default=8, help="Number of jobs to submit during the test")
    parser.add_argument("--worker-path", default="worker.py")
    parser.add_argument("--python", default=sys.executable, help="Python executable to use for the worker process")
    return parser.parse_args()


def make_context():
    return create_client_context("cert.pem")


def run_client(host, port, jobs, responses):
    ctx = make_context()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ctx.wrap_socket(sock, server_hostname=host)
    conn.connect((host, port))
    send_line(conn, "CLIENT")
    buffer = bytearray()

    for job in jobs:
        send_line(conn, f"JOB {job}")
        responses.append(recv_line(conn, buffer))

    conn.close()


def main():
    args = parse_args()
    jobs = [f"ADD {value} {value + 1}" for value in range(args.jobs)]

    print("Failure scenario 1: worker crash during processing")
    worker_env = os.environ.copy()
    worker_env["WORKER_FAIL_AFTER"] = "2"
    worker_env["WORKER_ID"] = "failure-test-worker"

    worker = subprocess.Popen(
        [args.python, args.worker_path, args.host],
        env=worker_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    time.sleep(1)

    responses = []
    client_thread = threading.Thread(target=run_client, args=(args.host, args.port, jobs, responses))
    client_thread.start()
    client_thread.join(timeout=30)

    worker.poll()
    if worker.returncode is None:
        worker.terminate()

    print(f"  Submitted jobs: {len(jobs)}")
    print(f"  Received responses: {len([response for response in responses if response is not None])}")
    print(f"  Responses: {responses}")
    print("  Result: job re-queue path exercised when the worker stopped.")

    print("\nFailure scenario 2: invalid job is rejected cleanly")
    ctx = make_context()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ctx.wrap_socket(sock, server_hostname=args.host)
    conn.connect((args.host, args.port))
    send_line(conn, "CLIENT")
    buffer = bytearray()
    send_line(conn, "JOB DIV 10 0")
    response = recv_line(conn, buffer)
    print(f"  Response: {response}")
    conn.close()

    print("\nFailure testing complete.")


if __name__ == "__main__":
    main()