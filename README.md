# Reliable Distributed Job Queue

A TCP + TLS based distributed job queue system where multiple clients submit jobs and multiple workers fetch and execute them concurrently. The server manages centralized queueing, reliable assignment, result collection, timeout handling, and worker-failure re-queuing.

## Key Features

- Multi-client and multi-worker architecture over TCP.
- TLS-secured communication between all nodes.
- Line-based framing protocol for stable message parsing.
- Reliable job lifecycle: submit -> assign -> acknowledge/result.
- Worker crash handling with automatic in-flight job re-queue.
- Invalid job validation and clean error responses.
- Performance evaluation under increasing concurrent load.

## Tech Stack

- Python 3
- socket, ssl, threading, queue
- cryptography (for certificate generation)

## Project Structure

- server.py: Central coordinator, queue manager, client/worker handlers.
- worker.py: Worker node that fetches and executes jobs.
- client.py: Interactive client for submitting jobs.
- protocol.py: Shared TLS context and line-based send/receive helpers.
- generate_cert.py: Generates local self-signed TLS certificate and key.
- perf_test.py: Load and latency benchmark script.
- failure_test.py: Worker-failure and invalid-job scenario validation.

## Setup

1. Install dependency:

```bash
pip install cryptography
```

2. Generate TLS files (required before running server/clients/workers):

```bash
python generate_cert.py
```

This creates local cert.pem and key.pem files. These are intentionally ignored by git.

## Run

Use separate terminals.

1. Start server:

```bash
python server.py
```

2. Start one or more workers:

```bash
python worker.py
```

For remote server host:

```bash
python worker.py <server-ip>
```

3. Start one or more clients:

```bash
python client.py
```

For remote server host:

```bash
python client.py <server-ip>
```

4. Submit jobs from client prompt:

```text
ADD 5 3
MUL 4 6
```

## Testing

Failure handling test:

```bash
python failure_test.py
```

Performance test (default client levels: 1, 2, 4, 8):

```bash
python perf_test.py
```

Custom load example:

```bash
python perf_test.py --clients 2 4 8 --jobs-per-client 20
```

## Notes

- Default server port: 5000
- Server listens on 0.0.0.0 for LAN access.
- For best throughput testing, run multiple worker instances.
- If certificates are missing, rerun generate_cert.py.

