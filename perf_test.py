import socket
import threading
import time
import statistics
import argparse

from protocol import create_client_context, recv_line, send_line

HOST = "127.0.0.1"
PORT = 5000



def parse_args():
    parser = argparse.ArgumentParser(description="Performance and scalability evaluation for the distributed job queue")
    parser.add_argument("--clients", nargs="*", type=int, default=[1, 2, 4, 8], help="Client concurrency levels")
    parser.add_argument("--jobs-per-client", type=int, default=10, help="Number of jobs submitted by each client")
    parser.add_argument("--host", default=HOST, help="Server host")
    parser.add_argument("--port", type=int, default=PORT, help="Server port")
    return parser.parse_args()


def make_context():
    return create_client_context("cert.pem")


def run_client(host, port, jobs, results, errors, barrier):
    """Connect as a client, submit each job, record latency per job."""
    try:
        ctx = make_context()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn = ctx.wrap_socket(sock, server_hostname=host)
        conn.connect((host, port))
        send_line(conn, "CLIENT")
        buffer = bytearray()

        barrier.wait()  # all clients start at the same time

        for job in jobs:
            start = time.perf_counter()
            send_line(conn, f"JOB {job}")
            response = recv_line(conn, buffer)
            elapsed = time.perf_counter() - start
            if response is None:
                errors.append("server disconnected")
                break
            if response.startswith("ERROR"):
                errors.append(response)
                break
            results.append(elapsed)

        conn.close()
    except Exception as e:
        errors.append(str(e))


def percentile(values, percent):
    if not values:
        return 0
    if len(values) == 1:
        return values[0]

    ordered = sorted(values)
    index = (len(ordered) - 1) * (percent / 100)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_load_level(host, port, num_clients, jobs_per_client):
    """Run one load level and return metrics."""
    jobs = [f"ADD {i} {i + 1}" for i in range(jobs_per_client)]

    all_latencies = []
    all_errors = []
    barrier = threading.Barrier(num_clients)
    threads = []

    for i in range(num_clients):
        client_latencies = []
        all_latencies.append(client_latencies)
        t = threading.Thread(
            target=run_client,
            args=(host, port, jobs, client_latencies, all_errors, barrier)
        )
        threads.append(t)

    wall_start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall_time = time.perf_counter() - wall_start

    flat_latencies = [lat for client in all_latencies for lat in client]
    total_jobs = len(flat_latencies)

    return {
        "num_clients": num_clients,
        "total_jobs": total_jobs,
        "wall_time": wall_time,
        "throughput": total_jobs / wall_time if wall_time > 0 else 0,
        "avg_latency_ms": statistics.mean(flat_latencies) * 1000 if flat_latencies else 0,
        "min_latency_ms": min(flat_latencies) * 1000 if flat_latencies else 0,
        "max_latency_ms": max(flat_latencies) * 1000 if flat_latencies else 0,
        "stdev_ms": statistics.stdev(flat_latencies) * 1000 if len(flat_latencies) > 1 else 0,
        "p50_ms": percentile(flat_latencies, 50) * 1000 if flat_latencies else 0,
        "p95_ms": percentile(flat_latencies, 95) * 1000 if flat_latencies else 0,
        "errors": len(all_errors),
    }


def main():
    args = parse_args()
    print("=" * 60)
    print("  Distributed Job Queue - Performance Evaluation")
    print("=" * 60)
    print(f"  Jobs per client : {args.jobs_per_client}")
    print(f"  Load levels     : {args.clients} clients")
    print("  Make sure server.py and at least one worker.py are running.")
    print("=" * 60)

    results = []
    for n in args.clients:
        print(f"\nRunning with {n} concurrent client(s)...", flush=True)
        metrics = run_load_level(args.host, args.port, n, args.jobs_per_client)
        results.append(metrics)
        print(f"  Done. {metrics['total_jobs']} jobs in {metrics['wall_time']:.2f}s "
              f"({metrics['throughput']:.2f} jobs/sec, p95 {metrics['p95_ms']:.1f} ms)")
        time.sleep(1)  # brief pause between load levels

    # --- Summary table ---
    print("\n" + "=" * 60)
    print(f"  {'Clients':>8} {'Total Jobs':>12} {'Time(s)':>9} "
          f"{'Throughput':>12} {'Avg(ms)':>9} {'P95(ms)':>9} {'Max(ms)':>9} {'Errors':>7}")
    print("-" * 60)
    for r in results:
        print(f"  {r['num_clients']:>8} {r['total_jobs']:>12} {r['wall_time']:>9.2f} "
              f"{r['throughput']:>11.2f}/s {r['avg_latency_ms']:>9.1f} "
              f"{r['p95_ms']:>9.1f} {r['max_latency_ms']:>9.1f} {r['errors']:>7}")
    print("=" * 60)



if __name__ == "__main__":
    main()
