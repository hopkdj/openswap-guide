---
title: "Self-Hosted Event Gateway: Knative Eventing vs APISIX Event Bridge vs NATS JetStream (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "event-driven", "messaging", "kubernetes", "microservices"]
draft: false
description: "Compare Knative Eventing, APISIX Event Bridge, and NATS JetStream for self-hosted event-driven architectures. Complete setup guides, routing patterns, and scalability strategies."
---

Event-driven architecture is the backbone of modern microservices systems. Instead of services calling each other directly via synchronous HTTP requests, they communicate by publishing and subscribing to events. An event gateway sits at the center of this architecture — receiving events from producers, applying routing rules, and delivering them to the right consumers.

This guide compares three leading self-hosted event gateway and routing solutions: **Knative Eventing**, **APISIX Event Bridge**, and **NATS JetStream**. We cover architecture, deployment patterns, message routing capabilities, and operational considerations so you can build a reliable event backbone for your infrastructure.

## What Is an Event Gateway?

An event gateway (also called an event router or event bridge) is a component that sits between event producers and event consumers. Its responsibilities include:

- **Event ingestion** — receiving events via HTTP, MQTT, Kafka, or other protocols
- **Routing** — directing events to the right consumers based on topic, type, or content
- **Transformation** — converting event formats (e.g., CloudEvents to JSON, protocol translation)
- **Filtering** — dropping events that do not match subscription criteria
- **Delivery guarantees** — ensuring events are delivered at-least-once, exactly-once, or at-most-once
- **Dead letter queues** — storing events that failed delivery for later retry

Unlike traditional message brokers (which focus on message queuing), event gateways emphasize intelligent routing, protocol bridging, and event format standardization.

## Architecture Overview

### Knative Eventing

Knative Eventing is a Kubernetes-native eventing framework that extends the Kubernetes API with eventing concepts like Brokers, Triggers, Sources, and Channels. It uses the CloudEvents specification as its standard event format.

Key characteristics:
- Kubernetes-native, managed via kubectl and YAML manifests
- CloudEvents specification compliance (industry standard event format)
- Pluggable broker backends (InMemoryChannel, KafkaChannel, NATSChannel)
- Source abstraction for ingesting events from APIs, webhooks, and message queues
- Trigger-based subscription routing with content-based filtering

### APISIX Event Bridge

APISIX Event Bridge is an event routing extension of the Apache APISIX API Gateway. It bridges events from various sources (Kafka, MQTT, Redis, PostgreSQL) to HTTP webhooks, serverless functions, and message queues.

Key characteristics:
- Built on the Apache APISIX gateway ecosystem
- Supports event ingestion from Kafka, MQTT, Redis Streams, and PostgreSQL LISTEN/NOTIFY
- Routes events to HTTP endpoints, Apache OpenWhisk, and AWS Lambda-compatible functions
- Declarative configuration via APISIX Admin API
- Integrates with APISIX's plugin ecosystem (rate limiting, auth, logging)

### NATS JetStream

NATS JetStream is the persistence layer built on top of NATS, a high-performance cloud-native messaging system. It provides durable message storage, replay, and consumer groups while maintaining NATS's core performance characteristics.

Key characteristics:
- Single binary, extremely lightweight (~30 MB)
- Sub-millisecond latency for event delivery
- Built-in persistence with configurable retention policies
- Consumer groups for competing consumer patterns
- Supports KV (key-value) storage and object storage on top of the event stream
- Multi-cluster replication for geo-distributed deployments

## Feature Comparison

| Feature | Knative Eventing | APISIX Event Bridge | NATS JetStream |
|---------|-------------------|---------------------|----------------|
| **Runtime** | Kubernetes | APISIX Gateway (Docker/K8s) | Single binary / Docker |
| **Event Format** | CloudEvents (standard) | JSON / Custom | NATS native / CloudEvents |
| **Protocols In** | HTTP, Kafka, Cron, GitHub | Kafka, MQTT, Redis, PostgreSQL | NATS, MQTT, WebSocket |
| **Protocols Out** | HTTP, Kafka, Kinesis | HTTP, OpenWhisk, Lambda | NATS, WebSocket, MQTT |
| **Content-Based Routing** | Yes (Trigger filters) | Yes (route expressions) | Yes (subject-based) |
| **Delivery Guarantees** | At-least-once | At-least-once | At-least-once / Exactly-once |
| **Dead Letter Queue** | Via retry broker | Configurable | Via consumer ack policies |
| **Message Replay** | Depends on broker | No | Yes (retention-based) |
| **Max Throughput** | Broker-dependent | 100K+ msg/s (APISIX) | 10M+ msg/s (NATS core) |
| **Persistence** | Via KafkaChannel | No (routing only) | Built-in (JetStream) |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Stars (GitHub)** | 1,540+ (eventing) | 16,500+ (APISIX) | 19,740+ (nats-server) |
| **Last Active** | May 2026 | May 2026 | May 2026 |

## Deployment & Configuration

### Knative Eventing on Kubernetes

Install Knative Eventing via operator or YAML:

```bash
# Install Knative Eventing
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-crds.yaml
kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v1.14.0/eventing-core.yaml

# Verify installation
kubectl get pods -n knative-eventing
```

Create a Broker and Trigger:

```yaml
apiVersion: eventing.knative.dev/v1
kind: Broker
metadata:
  name: default
  namespace: myapp
---
apiVersion: eventing.knative.dev/v1
kind: Trigger
metadata:
  name: order-trigger
  namespace: myapp
spec:
  broker: default
  filter:
    attributes:
      type: com.example.order.created
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      name: order-processor
```

Create a CronJob source that fires events periodically:

```yaml
apiVersion: sources.knative.dev/v1
kind: PingSource
metadata:
  name: heartbeat-source
  namespace: myapp
spec:
  schedule: "*/5 * * * *"
  data: '{"message": "tick"}'
  sink:
    ref:
      apiVersion: eventing.knative.dev/v1
      kind: Broker
      name: default
```

### APISIX Event Bridge

Deploy APISIX with Docker Compose:

```yaml
version: "3.8"
services:
  apisix:
    image: apache/apisix:3.11.0
    ports:
      - "9080:9080"
      - "9443:9443"
    volumes:
      - ./apisix_conf/config.yaml:/usr/local/apisix/conf/config.yaml:ro
    depends_on:
      - etcd
    restart: unless-stopped

  etcd:
    image: bitnami/etcd:3.5.14
    environment:
      - ALLOW_NONE_AUTHENTICATION=yes
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
    volumes:
      - etcd_data:/bitnami/etcd
    restart: unless-stopped

volumes:
  etcd_data:
```

Configure event routing via the Admin API:

```bash
# Create an event route from Kafka to HTTP webhook
curl http://127.0.0.1:9180/apisix/admin/event_routes/1 -X PUT -d '
{
  "source": {
    "type": "kafka",
    "brokers": ["kafka-broker:9092"],
    "topic": "orders.created"
  },
  "sink": {
    "type": "http",
    "url": "http://order-service:8080/webhook",
    "method": "POST"
  },
  "transform": {
    "body": "{\"event_type\": \"order.created\", \"data\": $body}"
  }
}'
```

### NATS JetStream

Deploy NATS with JetStream enabled:

```yaml
version: "3.8"
services:
  nats:
    image: nats:2.11-alpine
    ports:
      - "4222:4222"
      - "8222:8222"
      - "6222:6222"
    command: ["-js", "-m", "8222", "--store_dir", "/data/jetstream"]
    volumes:
      - nats-data:/data/jetstream
    restart: unless-stopped

volumes:
  nats-data:
```

Create a stream and publish events:

```bash
# Using the NATS CLI
nats stream add ORDERS --subjects="orders.>" --storage=file --replicas=1 --max-msgs=-1

# Publish an event
nats pub "orders.created" '{"order_id": "12345", "amount": 99.99, "currency": "USD"}'

# Subscribe to events
nats sub "orders.created" --queue=order-processors
```

Programmatic publishing in Go:

```go
package main

import (
    "github.com/nats-io/nats.go"
)

func main() {
    nc, _ := nats.Connect("nats://localhost:4222")
    defer nc.Drain()

    js, _ := nc.JetStream()

    js.Publish("orders.created", []byte(`{"order_id":"12345","amount":99.99}`))
}
```

## Routing Patterns

### Fan-Out (One Producer, Many Consumers)

All three tools support fan-out natively. Knative uses multiple Triggers on the same Broker. APISIX creates multiple event routes from the same source. NATS uses multiple subscribers on the same subject.

### Content-Based Routing

Route events based on their content:

- **Knative**: Trigger filters on CloudEvent attributes (`type`, `source`, or extensions)
- **APISIX**: Route expressions using JSONPath or Lua expressions on the event body
- **NATS**: Subject-based wildcards (`orders.us.*` vs `orders.eu.*`)

### Dead Letter Handling

When a consumer fails to process an event:
- **Knative**: Events are retried and then sent to a dead-letter Broker
- **APISIX**: Failed deliveries can be routed to a fallback HTTP endpoint
- **NATS**: Unacknowledged messages are redelivered; after max attempts, they go to a dead-letter stream

## Why Self-Host Your Event Gateway?

Event-driven architectures generate significant internal traffic — service-to-service events, state change notifications, audit trails, and real-time analytics feeds. Running this traffic through a commercial event platform (like Confluent Cloud, Amazon EventBridge, or Google Eventarc) means your internal service communication patterns are visible to, and billed by, a third party.

Self-hosting your event gateway provides several advantages:

- **Complete event privacy** — business events, user activity data, and system telemetry stay within your infrastructure
- **No per-event pricing** — commercial event platforms charge per million events processed; self-hosted solutions have zero marginal cost
- **Protocol flexibility** — bridge between protocols (MQTT to HTTP, Kafka to webhooks) without vendor-imposed limitations
- **Custom event formats** — use CloudEvents, protobuf, Avro, or custom schemas without platform restrictions
- **Lower latency** — running event routing on your own hardware or cluster eliminates network hops to external data centers
- **Simplified debugging** — access event logs, delivery traces, and broker metrics directly without requesting support tickets

For teams already running self-hosted [message brokers](../rabbitmq-vs-nats-vs-activemq-self-hosted-message-queue-guide/) or [workflow orchestration](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-guide/) platforms, adding an event gateway creates a complete event-driven architecture without external dependencies.

## FAQ

### Which event gateway should I choose for a Kubernetes-only environment?

Knative Eventing is the natural choice for Kubernetes-native environments. It extends the Kubernetes API with eventing concepts, meaning you manage events the same way you manage pods and services — via kubectl and YAML manifests. Its CloudEvents compliance also ensures interoperability with other CloudEvents-compatible tools.

### Can NATS JetStream replace Kafka?

NATS JetStream can replace Kafka for many use cases, particularly when you need lower latency and simpler operations. NATS delivers messages in sub-milliseconds compared to Kafka's typical 10-100ms. However, Kafka offers richer ecosystem integration (Connect, Streams, KSQL) and longer data retention. For high-throughput event routing with simple persistence, NATS JetStream is an excellent Kafka alternative.

### Does APISIX Event Bridge support MQTT?

Yes. APISIX Event Bridge can ingest events from MQTT brokers and route them to HTTP endpoints, serverless functions, or other message queues. This makes it ideal for IoT scenarios where devices publish via MQTT and backend services consume via HTTP webhooks.

### How do I ensure exactly-once delivery?

NATS JetStream supports exactly-once delivery through its consumer acknowledgment model — a message is only removed from the stream after the consumer explicitly acknowledges it. Knative Eventing provides at-least-once delivery by default. APISIX Event Bridge provides at-least-once delivery with configurable retry policies. For exactly-once processing, you need idempotent consumers regardless of the gateway.

### Can I migrate from one event gateway to another?

If you standardize on CloudEvents as your event format (recommended), migrating between event gateways is straightforward. Knative Eventing natively uses CloudEvents. APISIX Event Bridge can transform events to CloudEvents format. NATS JetStream supports CloudEvents via the CloudEvents SDK. The key is keeping your producers and consumers CloudEvents-compliant so the gateway becomes a swappable component.

### What happens if the event gateway goes down?

Knative Eventing's in-memory broker loses events if the broker pod restarts. Use KafkaChannel or NATSChannel as the broker backend for durability. APISIX Event Bridge does not buffer events — if the downstream consumer is unavailable, events are retried and then dropped. NATS JetStream persists all events to disk, so events survive server restarts and are redelivered when the server comes back.

### How do I monitor event delivery?

Knative Eventing exposes Prometheus metrics for event counts, delivery latencies, and error rates. APISIX integrates with Prometheus via its prometheus plugin and exposes metrics on the gateway's metrics port. NATS JetStream has a built-in monitoring HTTP endpoint (port 8222) that exposes stream and consumer statistics in JSON format.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Event Gateway: Knative Eventing vs APISIX Event Bridge vs NATS JetStream (2026)",
  "description": "Compare Knative Eventing, APISIX Event Bridge, and NATS JetStream for self-hosted event-driven architectures. Complete setup guides, routing patterns, and scalability strategies.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
