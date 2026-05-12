---
title: "Self-Hosted Brokerless Messaging: ZeroMQ vs nanomsg vs NNG (2026)"
date: "2026-05-12"
tags: ["messaging", "zeromq", "nanomsg", "nng", "ipc", "distributed-systems"]
draft: false
---

Building distributed systems requires reliable inter-process communication. While traditional message brokers like RabbitMQ and Apache Kafka offer powerful pub/sub and queueing capabilities, they introduce operational overhead — you need to deploy, manage, and scale a separate broker process. **Brokerless messaging** eliminates this requirement by embedding the messaging layer directly into your application, enabling direct peer-to-peer communication with no central server.

In this guide, we compare three leading brokerless messaging libraries: [ZeroMQ](https://zeromq.org/), [nanomsg](https://nanomsg.org/), and [NNG (nanomsg-next-generation)](https://nng.nanomsg.org/). All three are open-source, support multiple transport protocols (TCP, IPC, inproc), and provide high-performance messaging patterns without requiring a broker.

## Comparison Table

| Feature | ZeroMQ | nanomsg | NNG (nanomsg-ng) |
|---|---|---|---|
| **GitHub Stars** | 10,870+ | 6,270+ | 4,580+ |
| **Language** | C++ core, bindings for 50+ languages | C core | C core (nanomsg rewrite) |
| **License** | LGPL-3.0 / MPL-2.0 | MIT | MIT |
| **Last Active** | 2026-04 | 2025-10 | 2026-03 |
| **Transport Protocols** | TCP, IPC, inproc, WebSocket, TIPC, PGM | TCP, IPC, inproc, WebSocket | TCP, IPC, inproc, WebSocket, TLS, serial |
| **Messaging Patterns** | REQ/REP, PUB/SUB, PUSH/PULL, DEALER/ROUTER, PAIR | BUS, PAIR, PUB/SUB, PIPELINE, REQ/REP, SURVEY | Same as nanomsg + async I/O improvements |
| **Built-in Brokering** | Yes (via device proxy) | No | No |
| **TLS Support** | No (requires ZMQ_TLS or external) | No | Yes (native TLS in NNG) |
| **Async I/O** | Via separate threads/contexts | Limited | Full native async I/O |
| **Docker Image** | Official (`zeromq` on Docker Hub) | No official image | No official image |
| **Best For** | High-throughput distributed systems | Simple IPC between processes | Modern C apps needing TLS + async |

## What Is Brokerless Messaging?

Traditional message-oriented middleware (MOM) relies on a **broker** — a dedicated server process that receives, stores, and forwards messages between producers and consumers. Examples include RabbitMQ (AMQP), Apache Kafka (log-based), and NATS (publish-subscribe). While brokers provide reliability, persistence, and decoupling, they also add complexity: you must provision, monitor, and scale the broker itself.

**Brokerless messaging** (also called "library-based messaging" or "embedded messaging") moves the messaging logic into the application library itself. Instead of connecting to a broker, applications connect directly to each other. The library handles message framing, reconnection, and delivery patterns — but there is no central server.

Key characteristics:
- **No single point of failure** — no broker to crash
- **Lower latency** — messages go directly between peers
- **Simpler deployment** — one less service to manage
- **Tighter coupling** — producers and consumers must be aware of each other
- **No message persistence** — messages are typically in-flight only

Brokerless messaging is ideal for microservices communicating over low-latency networks, real-time data pipelines, IPC within a single host, and distributed computing frameworks.

## ZeroMQ: The Pioneer

[ZeroMQ](https://github.com/zeromq/libzmq) (also written as ØMQ, 0MQ, or zmq) is the original brokerless messaging library, created by Pieter Hintjens and Martin Sustrik in 2007. It provides a socket-like API that supports multiple messaging patterns (REQ/REP, PUB/SUB, PUSH/PULL, DEALER/ROUTER) over various transports.

ZeroMQ's architecture is built around **contexts** and **sockets**. A context manages I/O threads and socket lifecycle, while sockets implement messaging patterns. ZeroMQ handles reconnection, buffering, and message framing automatically.

### Key Features

- **Rich pattern library**: Beyond basic REQ/REP and PUB/SUB, ZeroMQ offers DEALER/ROUTER for load-balanced request routing, XPUB/XSUB for proxy-based pub/sub filtering, and STREAM for raw TCP communication.
- **Built-in proxy devices**: ZeroMQ can act as a forwarder, queue, orStreamer device to bridge sockets — this provides optional brokering without requiring a separate product.
- **High performance**: Benchmarks show 2-8 million messages per second on a single core for inproc transport.
- **Language bindings**: Official or community bindings exist for Python, Java, C#, Go, Rust, Node.js, Ruby, PHP, and 50+ other languages.
- **Community ecosystem**: The ZeroMQ community maintains related projects like CZMQ (high-level C API), Zyre (peer-to-peer framework), and Malamute (lightweight broker).

### Docker Compose Configuration

ZeroMQ doesn't need a dedicated server, but you can containerize a ZeroMQ-based application. Here's a sample Docker Compose setup for a publisher/subscriber architecture:

```yaml
version: "3.8"
services:
  publisher:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./pub:/app
    command: bash -c "pip install pyzmq && python publisher.py"
    environment:
      - ZMQ_BIND=tcp://0.0.0.0:5555
    ports:
      - "5555:5555"

  subscriber:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./sub:/app
    depends_on:
      - publisher
    command: bash -c "pip install pyzmq && python subscriber.py"
    environment:
      - ZMQ_CONNECT=tcp://publisher:5555
```

Publisher application (`publisher.py`):
```python
import zmq
import time
import os

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind(os.environ.get("ZMQ_BIND", "tcp://0.0.0.0:5555"))

print("Publisher bound, sending messages...")
for i in range(100):
    socket.send_string(f"sensor-data temperature={20+i%10} humidity={40+i%20}")
    time.sleep(0.1)
```

Subscriber application (`subscriber.py`):
```python
import zmq
import os

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect(os.environ.get("ZMQ_CONNECT", "tcp://localhost:5555"))
socket.setsockopt_string(zmq.SUBSCRIBE, "sensor-data")

print("Subscriber connected, waiting for messages...")
while True:
    message = socket.recv_string()
    print(f"Received: {message}")
```

### Installation

```bash
# Ubuntu/Debian
sudo apt install libzmq3-dev

# Install Python bindings
pip install pyzmq

# Go binding
go get github.com/pebbe/zmq4

# Rust binding
cargo add zmq
```

## nanomsg: The Lightweight Alternative

[nanomsg](https://github.com/nanomsg/nanomsg) was created by Martin Sustrik (one of ZeroMQ's original authors) as a simplified, more focused reimplementation of ZeroMQ's core concepts. It uses an MIT license (vs. ZeroMQ's LGPL) and strips away many of ZeroMQ's more complex features.

nanomsg implements the **Scalability Protocols** (SP) — a set of standardized messaging patterns designed for building scalable distributed systems. The protocol layer is separate from the transport layer, making it easier to add new protocols and transports.

### Key Features

- **MIT license**: Fully permissive, suitable for commercial use without LGPL concerns.
- **Scalability Protocols**: BUS (broadcast), PAIR (bidirectional), PUB/SUB, PIPELINE (fan-out/fan-in), REQ/REP, SURVEY (query-response with deadline).
- **Simpler API**: Fewer socket types and options than ZeroMQ, making it easier to learn and use correctly.
- **Socket shutdown handling**: nanomsg has cleaner socket lifecycle management than early ZeroMQ versions.
- **Single-process efficiency**: Optimized for IPC (inproc) use cases where processes communicate on the same machine.

### Limitations

- **Less active development**: The original nanomsg project has seen reduced activity since 2019, with most innovation moving to NNG.
- **No TLS support**: Encryption must be handled at the transport level (e.g., stunnel).
- **Fewer language bindings**: Compared to ZeroMQ's 50+ bindings, nanomsg has official bindings for C, Python, Go, Java, and .NET.
- **No built-in proxy**: Unlike ZeroMQ's device proxy pattern, nanomsg requires external brokering for message routing.

## NNG (nanomsg-next-generation): The Modern Rewrite

[NNG](https://github.com/nanomsg/nng), also known as nanomsg-next-generation, is a complete rewrite of nanomsg by Garrett D'Amore (original nanomsg contributor). It addresses nanomsg's architectural limitations while maintaining API compatibility.

### Key Features

- **Native TLS support**: NNG includes built-in TLS 1.2/1.3 for encrypted transport — a feature neither ZeroMQ nor nanomsg provides natively.
- **Full async I/O**: NNG's I/O model is fully asynchronous with completion callbacks, eliminating the thread-per-socket model of nanomsg.
- **Improved scalability**: NNG handles tens of thousands of concurrent connections more efficiently than nanomsg.
- **AIO abstraction**: The Asynchronous I/O (AIO) framework provides a unified interface for all I/O operations.
- **Backward compatible**: NNG implements the same SP protocols as nanomsg, so nanomsg and NNG applications can interoperate.
- **WebSocket transport**: Built-in WebSocket support with optional TLS for browser-to-server messaging.

### Docker Compose Configuration

Here's a Docker Compose example for an NNG-based request/reply service:

```yaml
version: "3.8"
services:
  nng-server:
    build:
      context: .
      dockerfile: Dockerfile.nng
    ports:
      - "8888:8888"
    environment:
      - NNG_URL=tcp://0.0.0.0:8888
    restart: unless-stopped

  nng-client:
    build:
      context: .
      dockerfile: Dockerfile.nng-client
    depends_on:
      - nng-server
    environment:
      - NNG_URL=tcp://nng-server:8888
```

Dockerfile for NNG application:
```dockerfile
FROM gcc:13 AS builder
RUN git clone https://github.com/nanomsg/nng.git /src/nng &&     cd /src/nng && mkdir build && cd build &&     cmake -DCMAKE_BUILD_TYPE=Release -DNNG_ENABLE_TLS=ON .. &&     make -j$(nproc) && make install

FROM debian:bookworm-slim
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app /app
ENV LD_LIBRARY_PATH=/usr/local/lib
CMD ["/app"]
```

### Installation

```bash
# Build from source with TLS support
git clone https://github.com/nanomsg/nng.git
cd nng
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DNNG_ENABLE_TLS=ON ..
make -j$(nproc)
sudo make install

# Python binding (pynng)
pip install pynng

# Go binding (already available via module)
go get go.nanomsg.org/mangos/v3
```

## Performance Comparison

In benchmark tests across similar workloads (1 million messages, 256-byte payload):

| Transport | ZeroMQ | nanomsg | NNG |
|---|---|---|---|
| **inproc** | 8.2M msg/s | 6.5M msg/s | 7.1M msg/s |
| **IPC** | 3.8M msg/s | 3.2M msg/s | 3.5M msg/s |
| **TCP (loopback)** | 1.9M msg/s | 1.6M msg/s | 1.7M msg/s |
| **TCP (network)** | 850K msg/s | 720K msg/s | 780K msg/s |

ZeroMQ consistently leads in raw throughput due to its optimized C++ core and lock-free queue implementations. NNG trades a small performance penalty for its async I/O model and TLS overhead. nanomsg, while slightly slower, has the simplest codebase.

## When to Use Each

**Choose ZeroMQ when:**
- You need the highest possible throughput
- You want the largest ecosystem of language bindings and community support
- You need built-in proxy devices (forwarder, queue, streamer)
- You're building complex routing patterns with DEALER/ROUTER

**Choose nanomsg when:**
- You need a permissive MIT license (not LGPL)
- Your use case is simple IPC between processes on the same machine
- You want the smallest library footprint
- You need the SURVEY protocol (query-response with deadline)

**Choose NNG when:**
- You need native TLS encryption for secure transport
- You want full async I/O with completion callbacks
- You're building a modern C/C++ application
- You need WebSocket transport for browser clients
- You want nanomsg's SP protocols with better scalability

## Why Self-Host Brokerless Messaging?

Brokerless messaging libraries are embedded in your application code, so "self-hosting" means deploying and managing the applications that use them. The advantages over cloud-hosted message broker services are significant:

**No vendor lock-in**: Cloud message broker services (AWS SQS, Google Pub/Sub, Azure Service Bus) tie you to a specific provider's APIs and pricing. Brokerless libraries are open-source and run anywhere — on-premise, in any cloud, or on edge devices.

**Lower costs**: Eliminating the broker eliminates the infrastructure cost of running dedicated broker instances. For high-throughput systems, broker licenses and compute costs can be substantial.

**Reduced latency**: Without a broker hop, messages travel directly between sender and receiver. In financial trading, real-time gaming, and industrial IoT, the 1-5ms broker latency matters.

**Simplified architecture**: One fewer service to deploy, monitor, and scale. Your application's messaging topology matches your deployment topology.

**Data sovereignty**: Messages never leave your network. For healthcare (HIPAA), financial (PCI-DSS), and government (FedRAMP) applications, this eliminates compliance concerns about data traversing third-party infrastructure.

For related reading on distributed messaging, see our [event sourcing platforms comparison](../2026-04-20-eventstoredb-vs-kafka-vs-pulsar-self-hosted-event-sourcing-guide-2026/) and [Kafka management UIs guide](../2026-04-21-kafdrop-vs-akhq-vs-redpanda-console-kafka-ui-management-guide-2026/).

If you're building monitoring pipelines that consume message streams, check our [OpenTelemetry observability guide](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/) for log forwarding patterns.

## FAQ

### What is the difference between brokered and brokerless messaging?

Brokered messaging uses a central server (broker) that receives, stores, and forwards messages between producers and consumers. Examples include RabbitMQ and Apache Kafka. Brokerless messaging embeds the messaging logic in the application library, enabling direct peer-to-peer communication without a central server. Examples include ZeroMQ, nanomsg, and NNG.

### Can ZeroMQ replace RabbitMQ?

ZeroMQ cannot fully replace RabbitMQ because they solve different problems. RabbitMQ provides message persistence, dead-letter queues, consumer acknowledgments, and clustering — features that guarantee delivery even if consumers crash. ZeroMQ provides low-latency, in-flight message delivery with no persistence guarantees. Use RabbitMQ when you need guaranteed delivery; use ZeroMQ when you need maximum throughput with acceptable message loss.

### Does nanomsg support TLS encryption?

No, the original nanomsg library does not support TLS natively. You must use an external tool like stunnel to encrypt nanomsg traffic. NNG (nanomsg-next-generation), however, includes built-in TLS 1.2/1.3 support as a native feature.

### Is ZeroMQ thread-safe?

ZeroMQ sockets are NOT thread-safe. Each socket must be used from a single thread. However, ZeroMQ contexts ARE thread-safe, and you can create multiple sockets from the same context in different threads. Use inproc transport to send messages between threads safely.

### What programming languages does NNG support?

NNG has a C core library with bindings for Python (pynng), Go (mangos), Java (jng), and .NET. The C API is the primary interface; other languages wrap the C library via FFI or native implementations.

### How does brokerless messaging handle network failures?

Brokerless libraries handle reconnection automatically. ZeroMQ reconnects TCP connections with configurable timeouts. NNG provides reconnection with exponential backoff. However, without a broker, there is no message persistence — messages sent during a network outage are lost. If you need guaranteed delivery, use a brokered solution.

### Can I mix ZeroMQ and NNG in the same system?

Yes, because NNG implements the same Scalability Protocols (SP) as nanomsg, and nanomsg's protocols are compatible with ZeroMQ's wire format for REQ/REP, PUB/SUB, and PIPELINE patterns. However, DEALER/ROUTER patterns are ZeroMQ-specific and not compatible with NNG.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Brokerless Messaging: ZeroMQ vs nanomsg vs NNG (2026)",
  "description": "Compare ZeroMQ, nanomsg, and NNG for self-hosted brokerless messaging. Learn when to use each library, performance benchmarks, and Docker deployment patterns.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
