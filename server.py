import socket
import threading
import queue
import uuid
import sys
import time

from protocol import create_server_context, recv_line, send_line

sys.stdout.reconfigure(line_buffering=True)  # force logs to print immediately

HOST = '0.0.0.0'   # listen on all network interfaces, not just localhost
PORT = 5000
JOB_TIMEOUT_SECONDS = 60
WORKER_RECONNECT_SECONDS = 2

job_queue = queue.Queue()
pending_jobs = {}       # job_id -> {'event': threading.Event, 'result': None}
pending_lock = threading.Lock()
job_stats = {
    'submitted': 0,
    'completed': 0,
    'timed_out': 0,
    'worker_failures': 0,
}

context = create_server_context("cert.pem", "key.pem")


def queue_job(job):
    job_id = str(uuid.uuid4())
    event = threading.Event()
    with pending_lock:
        pending_jobs[job_id] = {'event': event, 'result': None, 'job': job}
        job_stats['submitted'] += 1
    job_queue.put((job_id, job))
    return job_id, event


def complete_job(job_id, result):
    with pending_lock:
        pending = pending_jobs.get(job_id)
        if pending is None:
            return False
        pending['result'] = result
        pending['event'].set()
        job_stats['completed'] += 1
        return True


def restore_job(job_id, job):
    with pending_lock:
        pending = pending_jobs.get(job_id)
        if pending:
            pending['event'].clear()
    job_queue.put((job_id, job))


def is_valid_job(job):
    parts = job.split()
    if len(parts) != 3:
        return False

    if parts[0] not in {"ADD", "MUL"}:
        return False

    try:
        int(parts[1])
        int(parts[2])
        return True
    except ValueError:
        return False


def handle_client(conn, addr):
    print(f"Client connected: {addr[0]}:{addr[1]}")
    buffer = bytearray()
    try:
        while True:
            data = recv_line(conn, buffer)
            if data is None:
                break

            if data.startswith("JOB "):
                job = data[4:]
                print(f"Job received: {job}")

                if not is_valid_job(job):
                    send_line(conn, "ERROR: Invalid job format")
                    print(f"Rejected invalid job: {job}")
                    continue

                job_id, event = queue_job(job)
                print(f"Job queued: {job} (queue size: {job_queue.qsize()})")

                if not event.wait(timeout=JOB_TIMEOUT_SECONDS):
                    with pending_lock:
                        pending_jobs.pop(job_id, None)
                        job_stats['timed_out'] += 1
                    send_line(conn, "ERROR: Job timed out")
                    print(f"Job timed out: {job}")
                    continue

                with pending_lock:
                    pending = pending_jobs.pop(job_id, None)
                    result = pending['result'] if pending else None
                send_line(conn, f"Result: {result}")
    except Exception as e:
        print(f"Client {addr[0]}:{addr[1]} error: {e}")
    finally:
        conn.close()
        print(f"Client disconnected: {addr[0]}:{addr[1]}")


def handle_worker(conn, addr):
    print(f"Worker connected: {addr[0]}:{addr[1]}")
    in_flight = None  # (job_id, job) currently being processed by this worker
    buffer = bytearray()
    try:
        while True:
            request = recv_line(conn, buffer)
            if request is None:
                break

            if request == "GET_JOB":
                try:
                    job_id, job = job_queue.get_nowait()
                    in_flight = (job_id, job)
                    send_line(conn, job)

                    result_data = recv_line(conn, buffer)
                    if result_data is None:
                        raise ConnectionError("Worker disconnected after receiving job")

                    in_flight = None  # result received safely
                    # Strip the "Result " prefix sent by the worker
                    if result_data.startswith("ERROR"):
                        raise RuntimeError(result_data)

                    result = result_data[7:] if result_data.startswith("Result ") else result_data

                    complete_job(job_id, result)
                    print(f"Result: {result}  (job: {job})")
                except queue.Empty:
                    send_line(conn, "NO_JOB")
    except Exception as e:
        print(f"Worker {addr[0]}:{addr[1]} error: {e}")
    finally:
        # If the worker died while processing a job, put it back in the queue
        if in_flight:
            job_id, job = in_flight
            with pending_lock:
                job_stats['worker_failures'] += 1
            print(f"Worker {addr[0]}:{addr[1]} failed — re-queuing job: {job}")
            restore_job(job_id, job)
        conn.close()
        print(f"Worker disconnected: {addr[0]}:{addr[1]}")


def accept_connections(server_sock):
    while True:
        try:
            client, addr = server_sock.accept()
            conn = context.wrap_socket(client, server_side=True)
            role_buffer = bytearray()
            role = recv_line(conn, role_buffer)

            if role == "CLIENT":
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            elif role == "WORKER":
                threading.Thread(target=handle_worker, args=(conn, addr), daemon=True).start()
            else:
                conn.close()
        except Exception as e:
            print("Accept error:", e)
            time.sleep(WORKER_RECONNECT_SECONDS)


sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT))
sock.listen(5)

print("Server running on port", PORT)
print("Server is using TLS and line-based framing for stable multi-client handling")

accept_connections(sock)