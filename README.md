# Reliable Distributed Job Queue

A secure and fault-tolerant distributed job processing system built using Python sockets and TLS.
Multiple clients can submit jobs concurrently, while multiple workers fetch, execute, and return results through a centralized queue managed by the server.

## Highlights

- ⚡ Concurrent multi-client and multi-worker communication over TCP.
- 🔐 TLS encryption for all client and worker connections.
- ✅ Reliable job lifecycle management: submit, assign, execute, result delivery.
- ♻️ In-flight job recovery with automatic re-queue on worker failure.
- 🛡️ Input validation with clear error handling for invalid jobs.
- 📈 Performance benchmarking under increasing load levels.

## 🏗️ System Architecture

1. Clients submit jobs to the server.
2. Server validates and queues each job with a unique job ID.
3. Workers pull jobs using a request model.
4. Workers execute operations and return results.
5. Server maps results back to waiting clients.
6. If a worker disconnects mid-job, the server re-queues that job.

## 🧩 Supported Job Format

- ADD x y
- MUL x y

Example:

```text
ADD 5 3
MUL 4 6
```

## 🛠️ Tech Stack

- Python 3
- socket, ssl, threading, queue
- cryptography (certificate generation)

## 📁 Repository Layout

- server.py: Central coordinator, queue manager, and connection handler.
- worker.py: Worker node implementation for pulling and executing jobs.
- client.py: Interactive client for submitting jobs.
- protocol.py: Shared TLS setup and line-based messaging helpers.
- generate_cert.py: Generates local self-signed TLS certificate and private key.
- perf_test.py: Concurrent load testing and latency/throughput metrics.
- failure_test.py: Failure-path validation (worker crash and invalid jobs).

## 🚀 Quick Start

### 1) Install dependency

```bash
pip install cryptography
```

### 2) Generate TLS certificate and key

```bash
python generate_cert.py
```

This creates cert.pem and key.pem in the project root.
These files are intentionally ignored by Git.

### 3) Start the server

```bash
python server.py
```

### 4) Start one or more workers (new terminal per worker)

```bash
python worker.py
```

For LAN/remote host:

```bash
python worker.py <server-ip>
```

### 5) Start one or more clients

```bash
python client.py
```

For LAN/remote host:

```bash
python client.py <server-ip>
```

## 🧪 Testing and Evaluation

### Failure handling scenarios

```bash
python failure_test.py
```

### Performance and scalability benchmark

```bash
python perf_test.py
```

Custom load run:

```bash
python perf_test.py --clients 2 4 8 --jobs-per-client 20
```

## ⚙️ Configuration Notes

- 🌐 Default port: 5000
- 🖥️ Server bind host: 0.0.0.0
- 🔁 Worker reconnect/backoff and timeout logic are handled in server/worker flows.
- 🧾 If cert files are missing, run generate_cert.py again.


