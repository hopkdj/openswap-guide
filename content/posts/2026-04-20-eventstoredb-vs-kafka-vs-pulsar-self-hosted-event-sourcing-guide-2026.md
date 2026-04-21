---
title: "EventStoreDB vs Kafka vs Pulsar: Best Event Sourcing Platform 2026"
date: 2026-04-20
tags: ["comparison", "guide", "self-hosted", "event-driven", "messaging"]
draft: false
description: "Compare EventStoreDB, Apache Kafka, and Apache Pulsar for self-hosted event sourcing architectures. Real Docker configs, performance benchmarks, and deployment guides."
---

Event sourcing has emerged as one of the most powerful architectural patterns for building resilient, auditable, and scalable systems. Instead of storing only the current state of your data, event sourcing persists every state change as an immutable event in an append-only log. This gives you a complete history, natural audit trails, and the ability to replay events to rebuild state at any point in time.

But choosing the right platform to store and process those events is critical. Three options dominate the self-hosted event sourcing landscape: **EventStoreDB**, a purpose-built event sourcing database; **Apache [kafka](https://kafka.apache.org/)**, the industry-standard distributed event streaming platform; and **Apache Pulsar**, a next-generation cloud-native messaging and streaming system.

In this guide, we compare all three platforms head-to-head — covering architecture, [docker](https://www.docker.com/) deployment, performance, and real-world use cases — so you can pick the right tool for your event-driven system.

## Why Self-Hosted Event Sourcing Matters

Event sourcing changes how you think about data. Instead of overwriting records, every change is appended as an event. This approach delivers several benefits that traditional CRUD architectures simply cannot match:

- **Complete audit trail** — Every state change is recorded, making compliance and debugging straightforward
- **Temporal queries** — Rebuild the state of any entity at any point in time by replaying events
- **Natural integration with CQRS** — Separate read and write models for optimized query performance
- **Event replay capabilities** — Rebuild projections, fix bugs, or create new read models from historical data
- **Decoupled microservices** — Services communicate through events rather than direct API calls

Running this infrastructure self-hosted gives you full control over data retention, security policies, and compliance requirements. No third-party vendor holds your event log, and you avoid the egress costs that cloud-hosted messaging platforms charge at scale.

For teams already running self-hosted message queues, extending your infrastructure with an event sourcing platform is a natural next step. If you are comparing traditional message brokers first, check out our [RabbitMQ vs NATS vs ActiveMQ guide](../rabbitmq-vs-nats-vs-activemq-self-hosted-message-queue-guide/) for background on the messaging layer.

## EventStoreDB: Purpose-Built Event Sourcing Database

EventStoreDB (now marketed as KurrentDB) is the only database designed from the ground up specifically for event sourcing. It treats events as first-class citizens, with native support for streams, projections, and event replay.

### Key Features

- **Event streams** — Each aggregate gets its own stream of events, identified by a unique stream ID
- **Projections** — Transform event streams into read models using JavaScript-based projection functions
- **Optimistic concurrency** — Prevents write conflicts with version checking per stream
- **Catch-up subscriptions** — Subscribe to a stream from any version, including live updates
- **Built-in web UI** — Monitor streams, projections, and cluster health through a browser
- **gRPC and TCP APIs** — Native clients for .NET, Java, Go, JavaScript, and Python
- **Cluster support** — Raft-based consensus for high-availability deployments

### Project Stats (as of April 2026)

| Metric | Value |
|---|---|
| GitHub Stars | 5,776 |
| Primary Language | C# |
| License | BSL 1.1 (Business Source License) |
| Last Commit | April 18, 2026 |
| Docker Image | `eventstore/eventstore` |

### Docker Deployment

EventStoreDB's official Docker Compose sets up a three-node cluster with TLS certificates and gossip-based discovery:

```yaml
services:
  esdb-node1:
    image: eventstore/eventstore:24.10
    environment:
      - EVENTSTORE_CLUSTER_SIZE=3
      - EVENTSTORE_GOSSIP_SEED=172.30.240.12:2113,172.30.240.13:2113
      - EVENTSTORE_RUN_PROJECTIONS=All
      - EVENTSTORE_START_STANDARD_PROJECTIONS=true
      - EVENTSTORE_EXT_HTTP_PORT=2113
      - EVENTSTORE_INSECURE=true
    ports:
      - "2113:2113"
    volumes:
      - eventstore-data1:/var/lib/eventstore
    networks:
      clusternetwork:
        ipv4_address: 172.30.240.11

  esdb-node2:
    image: eventstore/eventstore:24.10
    environment:
      - EVENTSTORE_CLUSTER_SIZE=3
      - EVENTSTORE_GOSSIP_SEED=172.30.240.11:2113,172.30.240.13:2113
      - EVENTSTORE_RUN_PROJECTIONS=All
      - EVENTSTORE_INSECURE=true
      - EVENTSTORE_EXT_HTTP_PORT=2113
    ports:
      - "2114:2113"
    volumes:
      - eventstore-data2:/var/lib/eventstore
    networks:
      clusternetwork:
        ipv4_address: 172.30.240.12

  esdb-node3:
    image: eventstore/eventstore:24.10
    environment:
      - EVENTSTORE_CLUSTER_SIZE=3
      - EVENTSTORE_GOSSIP_SEED=172.30.240.11:2113,172.30.240.12:2113
      - EVENTSTORE_RUN_PROJECTIONS=All
      - EVENTSTORE_INSECURE=true
      - EVENTSTORE_EXT_HTTP_PORT=2113
    ports:
      - "2115:2113"
    volumes:
      - eventstore-data3:/var/lib/eventstore
    networks:
      clusternetwork:
        ipv4_address: 172.30.240.13

volumes:
  eventstore-data1:
  eventstore-data2:
  eventstore-data3:

networks:
  clusternetwork:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.240.0/24
```

For a single-node development setup, the command is much simpler:

```bash
docker run -d --name eventstore -p 2113:2113 \
  -e EVENTSTORE_INSECURE=true \
  eventstore/eventstore:24.10
```

The admin UI runs on port 2113. Access `http://localhost:2113` with default credentials `admin/changeit`.

## Apache Kafka: The Industry Standard

Apache Kafka is the most widely adopted event streaming platform. Originally built at LinkedIn, it has become the backbone of event-driven architectures at thousands of organizations. While not designed specifically for event sourcing, Kafka's append-only log model maps naturally to event sourcing patterns.

### Key Features

- **Topic-based partitions** — Horizontally scalable logs with ordered message delivery per partition
- **Consumer groups** — Multiple independent consumers can read the same topic at their own pace
- **Log compaction** — Retains the latest value per key, enabling event-sourced state reconstruction
- **Kafka Streams** — Built-in stream processing library for real-time transformations
- **Connect API** — Hundreds of pre-built connectors for databases, file systems, and SaaS platforms
- **Schema Registry** — Enforce schema compatibility with Avro, Protobuf, or JSON Schema
- **Tiered storage** — Offload older segments to S3 or GCS for cost-effective long-term retention

### Project Stats (as of April 2026)

| Metric | Value |
|---|---|
| GitHub Stars | 32,414 |
| Primary Language | Java |
| License | Apache 2.0 |
| Last Commit | April 18, 2026 |
| Docker Image | `apache/kafka` |

### Docker Deployment

The Confluent Platform provides a production-ready Docker Compose for Kafka with ZooKeeper:

```yaml
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    hostname: zookeeper
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  broker:
    image: confluentinc/cp-server:7.6.0
    hostname: broker
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://broker:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1

  schema-registry:
    image: confluentinc/cp-schema-registry:7.6.0
    depends_on:
      - broker
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: 'broker:29092'
```

For a ZooKeeper-free deployment using KRaft mode (Kafka 3.x+):

```bash
docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_NODE_ID=1 \
  -e KAFKA_PROCESS_ROLES=broker,controller \
  -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 \
  -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  -e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  apache/kafka:3.7.0
```

## Apache Pulsar: Cloud-Native Messaging and Streaming

Apache Pulsar, originally developed at Yahoo, is a next-generation distributed messaging and streaming platform. It separates compute (brokers) from storage (bookies using Apache BookKeeper), enabling independent scaling and multi-tenancy — capabilities that make it uniquely suited for large-scale event sourcing deployments.

### Key Features

- **Native multi-tenancy** — Tenants, namespaces, and topics with per-namespace policies and quotas
- **Unified messaging and streaming** — Both queuing (ack-based) and streaming (cursor-based) models
- **Tiered storage** — Automatic offloading to S3, GCS, or HDFS with transparent read-through
- **Built-in functions** — Lightweight compute framework for event processing without external frameworks
- **Geo-replication** — Cross-cluster replication with conflict resolution
- **Schema registry** — Native schema management with versioning and compatibility checks
- **Functions, Sinks, Sources** — Built-in connectors for data ingestion and egress

### Project Stats (as of April 2026)

| Metric | Value |
|---|---|
| GitHub Stars | 15,203 |
| Primary Language | Java |
| License | Apache 2.0 |
| Last Commit | April 17, 2026 |
| Docker Image | `apachepulsar/pulsar` |

### Docker Deployment

Pulsar's standalone mode is ideal for development and testing:

```bash
docker run -d --name pulsar -p 6650:6650 -p 8080:8080 \
  apachepulsar/pulsar:3.3.0 \
  bin/pulsar standalone
```

For a production cluster with BookKeeper, use Docker Compose:

```yaml
services:
  zookeeper:
    image: apachepulsar/pulsar:3.3.0
    command: >
      bash -c "bin/apply-config-from-env.py conf/zookeeper.conf
      && bin/pulsar zookeeper"
    environment:
      ZOOKEEPER_SERVERS: zookeeper
    ports:
      - "2181:2181"

  bookie:
    image: apachepulsar/pulsar:3.3.0
    command: >
      bash -c "bin/apply-config-from-env.py conf/bookkeeper.conf
      && exec bin/pulsar bookie"
    environment:
      zkServers: zookeeper:2181
      bookiePort: "3181"
    depends_on:
      - zookeeper

  broker:
    image: apachepulsar/pulsar:3.3.0
    command: >
      bash -c "bin/apply-config-from-env.py conf/broker.conf
      && exec bin/pulsar broker"
    environment:
      zookeeperServers: zookeeper:2181
      managedLedgerDefaultEnsembleSize: "1"
      managedLedgerDefaultWriteQuorum: "1"
      managedLedgerDefaultAckQuorum: "1"
    ports:
      - "6650:6650"
      - "8080:8080"
    depends_on:
      - zookeeper
      - bookie
```

## Head-to-Head Comparison

| Feature | EventStoreDB | Apache Kafka | Apache Pulsar |
|---|---|---|---|
| **Primary Design** | Event sourcing database | Event streaming platform | Messaging + streaming |
| **Event Model** | Streams per aggregate | Topic partitions | Persistent topics |
| **Storage** | Append-only log on disk | Log segments on disk | BookKeeper ledgers |
| **Message Ordering** | Per-stream guaranteed | Per-partition guaranteed | Per-partition guaranteed |
| **Retention** | Configurable per stream | Time or size based | Time, size, or infinite |
| **Replay Support** | Native (from any version) | From offset | From cursor position |
| **Projections** | Built-in (JavaScript) | Kafka Streams required | Functions/Pulsar IO |
| **Multi-tenancy** | Via access controls | Via ACLs | Native tenants/namespaces |
| **Geo-replication** | Via subscriptions | MirrorMaker 2 | Built-in |
| **Schema Registry** | Via metadata | Confluent Schema Registry | Built-in |
| **Admin UI** | Built-in web UI | CMAK, Confluent Control Center | Built-in dashboard |
| **Protocol** | gRPC, TCP | Custom binary | Pulsar protocol |
| **Client Languages** | .NET, Java, Go, JS, Python | Java, Python, Go, Rust, C++ | Java, Python, Go, C++, Node.js |
| **License** | BSL 1.1 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 5,776 | 32,414 | 15,203 |

### When to Choose Each Platform

**Choose EventStoreDB when:**
- You are implementing CQRS with event sourcing as the core architectural pattern
- You need per-stream optimistic concurrency control
- You want built-in projections to generate read models
- Your domain model maps naturally to aggregate streams
- You need temporal queries (state at a specific point in time)

**Choose Apache Kafka when:**
- You need the broadest ecosystem of connectors, tools, and community support
- You are already using Kafka for event streaming and want to add event sourcing
- You need high-throughput, low-latency event processing at massive scale
- Log compaction and Schema Registry meet your event sourcing needs
- Your team has existing Kafka expertise

**Choose Apache Pulsar when:**
- You need native multi-tenancy for serving multiple teams or customers
- Tiered storage to object storage is a requirement for long-term event retention
- You want unified queuing and streaming semantics in one platform
- You need geo-replication with conflict resolution out of the box
- Independent scaling of compute and storage matters for your workload

## Event Sourcing Implementation Patterns

### CQRS with EventStoreDB

```csharp
// EventStoreDB client setup
var settings = EventStoreClientSettings.Create(
    "esdb://localhost:2113?tls=false");
var client = new EventStoreClient(settings);

// Append events to a stream
var events = new[] {
    new EventData(
        Uuid.NewUuid(),
        "OrderCreated",
        JsonSerializer.SerializeToUtf8Bytes(new {
            OrderId = "order-123",
            CustomerId = "cust-456",
            Amount = 99.99
        }))
};

await client.AppendToStreamAsync(
    streamName: "order-order-123",
    expectedRevision: ExpectedRevision.NoStream,
    events: events);
```

### Event Sourcing with Kafka and Log Compaction

Kafka's log compaction feature keeps the latest record for each message key, enabling event-sourced state reconstruction:

```bash
# Create a compacted topic for event sourcing
kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic order-events \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.01 \
  --config segment.bytes=104857600

# Produce an event with the aggregate ID as key
echo '{"orderId":"order-123","type":"OrderCreated","amount":99.99}' \
  | kafka-console-producer.sh --bootstrap-server localhost:9092 \
  --topic order-events --property "parse.key=true" \
  --property "key.separator=:" --property "key=order-123"
```

### Multi-Tenant Event Sourcing with Pulsar

Pulsar's tenant/namespace model provides clean separation for event sourcing across multiple services:

```bash
# Create a tenant for your organization
pulsar-admin tenants create myorg

# Create a namespace for the order domain
pulsar-admin namespaces create myorg/orders

# Configure retention (keep events for 30 days)
pulsar-admin namespaces set-retention myorg/orders \
  --size -1 --time 43200

# Create a persistent topic for order events
pulsar-admin topics create persistent://myorg/orders/order-events

# Publish events
pulsar-client produce persistent://myorg/orders/order-events \
  --messages '{"orderId":"order-123","event":"OrderCreated"}'
```

## Performance Considerations

| Metric | EventStoreDB | Apache Kafka | Apache Pulsar |
|---|---|---|---|
| **Write Throughput** | ~50K events/sec (single node) | ~1M+ msgs/sec (cluster) | ~100K+ msgs/sec (cluster) |
| **Read Latency** | Sub-millisecond (per stream) | Low (sequential read) | Low (BookKeeper read) |
| **Storage Efficiency** | High (append-only) | High (log segments) | Medium (ledger overhead) |
| **Scalability** | Vertical (stream affinity) | Horizontal (partitions) | Horizontal (brokers + bookies) |
| **Recovery Time** | Fast (single log per stream) | Fast (sequential replay) | Fast (cursor-based replay) |

EventStoreDB excels when you need precise per-stream operations with optimistic concurrency. Kafka delivers the highest raw throughput for fire-and-forget event streaming. Pulsar offers the best operational flexibility with compute-storage separation.

If you are building com[plex](https://www.plex.tv/) workflows on top of your event streams, you may want to pair your event sourcing platform with a workflow orchestration engine. See our [Temporal vs Camunda vs Flowable comparison](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-orchestration-guide-2026/) for guidance on that layer.

## FAQ

### What is event sourcing and how does it differ from traditional CRUD?

Event sourcing stores every state change as an immutable event in an append-only log, rather than overwriting the current state. This means you have a complete history of all changes, can rebuild state at any point in time, and get natural audit trails. Traditional CRUD only stores the current state, losing all historical information.

### Can I use Kafka for event sourcing?

Yes. Kafka's partitioned, ordered, append-only log maps well to event sourcing patterns. Using log compaction (cleanup.policy=compact), you can retain the latest state per aggregate key while keeping the full event history. However, Kafka lacks native per-stream concurrency control and projections, which EventStoreDB provides out of the box.

### Which platform is easiest to self-host?

For a single-node development setup, all three are straightforward with Docker. EventStoreDB requires just one `docker run` command. Pulsar standalone mode is similarly simple. Kafka's KRaft mode eliminates the ZooKeeper dependency, making it easier than before. For production clusters, Pulsar's compute-storage separation gives you the most operational flexibility.

### How do I handle schema evolution with event sourcing?

All three platforms support schema evolution through different mechanisms. EventStoreDB stores event type names as metadata, allowing consumers to handle multiple versions. Kafka pairs with Confluent Schema Registry for Avro/Protobuf compatibility enforcement. Pulsar has a built-in schema registry with version tracking. The key principle: make events append-only — never modify existing events, only add new ones.

### Is EventStoreDB truly open source?

EventStoreDB uses the Business Source License (BSL 1.1), which allows free use for development, testing, and production — but restricts offering EventStoreDB as a managed service. After a set period, each release converts to the Apache 2.0 license. Apache Kafka and Apache Pulsar are both Apache 2.0 licensed with no such restrictions.

### How do I handle large event stores with millions of events?

All three platforms support long-term retention. Kafka and Pulsar both offer tiered storage to offload older segments to S3 or GCS while keeping them readable. EventStoreDB uses scavenge operations to reclaim space from deleted or truncated streams. For projections, materialize derived state into a separate read database (PostgreSQL, Elasticsearch) to avoid replaying millions of events on every query.

### Can I migrate between these platforms?

Yes, but it requires careful planning. The common approach is to build an adapter that reads events from the source platform and writes them to the target, preserving ordering and metadata. For Kafka to EventStoreDB migrations, write each Kafka message as an event to the corresponding stream. For EventStoreDB to Kafka, subscribe to all streams and publish each event to a Kafka topic partitioned by stream ID.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "EventStoreDB vs Kafka vs Pulsar: Best Event Sourcing Platform 2026",
  "description": "Compare EventStoreDB, Apache Kafka, and Apache Pulsar for self-hosted event sourcing architectures. Real Docker configs, performance benchmarks, and deployment guides.",
  "datePublished": "2026-04-20",
  "dateModified": "2026-04-20",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
