---
title: "Self-Hosted CQRS Platforms — Axon Server vs EventStoreDB vs Apache Kafka 2026"
date: 2026-05-03T12:00:00+00:00
tags: ["cqrs", "event-sourcing", "axon-server", "eventstoredb", "apache-kafka", "self-hosted", "microservices", "distributed-systems", "architecture"]
draft: false
---

The Command Query Responsibility Segregation (CQRS) pattern separates read and write operations in your application, optimizing each for its specific use case. When combined with event sourcing — storing state changes as an immutable sequence of events — CQRS becomes a powerful architecture for complex domains, audit-heavy applications, and systems that need to replay or reconstruct state over time.

While many articles cover CQRS as an abstract pattern, this guide focuses on the **self-hosted infrastructure platforms** that make CQRS practical at scale: **Axon Server**, **EventStoreDB**, and **Apache Kafka**. Each provides the event store, message routing, and projection capabilities needed to build CQRS systems without relying on managed cloud services.

## Why Self-Host Your CQRS Infrastructure?

CQRS systems generate significant internal traffic — every command, event, and query projection flows through your infrastructure. Running these platforms on cloud-managed services can become expensive quickly, especially when event volumes are high. Self-hosting gives you full control over retention policies, storage costs, and network topology.

For regulated industries like finance, healthcare, and government, data sovereignty requirements often mandate that event streams and audit trails remain on-premises. Self-hosted CQRS platforms also eliminate vendor lock-in — your event schemas and projections belong to you, not a cloud provider.

If you're building event-driven systems, our [event sourcing platform comparison](../2026-04-20-eventstoredb-vs-kafka-vs-pulsar-self-hosted-event-sourcing-guide-2026/) covers the broader event sourcing landscape. For workflow orchestration that can complement CQRS systems, see our [workflow engine guide](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-orchestration-guide-2026/). And for distributed locking coordination between CQRS services, our [distributed locking guide](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/) covers the options.

## Axon Server: Purpose-Built CQRS Event Store

[Axon Server](https://github.com/AxonIQ/axon-server-se) is an event store and messaging platform specifically designed for CQRS and event sourcing applications. Developed by the creators of the Axon Framework, it provides native support for event streams, command routing, and query models out of the box.

**Key features:**
- Purpose-built for CQRS — commands, events, and queries are first-class concepts
- Axon Framework integration (Java/Kotlin) with automatic command routing
- Event stream tracking with token-based position management
- Built-in query model synchronization
- Clustering and high availability in the Enterprise edition
- REST and gRPC APIs
- Docker-native deployment

### Docker Compose Configuration

```yaml
services:
  axon-server:
    image: axoniq/axonserver:latest
    container_name: axon-server
    restart: unless-stopped
    ports:
      - "8024:8024"   # Dashboard
      - "8124:8124"   # gRPC
    environment:
      - AXONIQ_AXONSERVER_NAME=axon-server-1
      - AXONIQ_AXONSERVER_INTERNAL_HOSTNAME=axon-server
      - AXONIQ_AXONSERVER_DEVMODE=true
    volumes:
      - axon-data:/data
      - axon-events:/eventdata
      - axon-config:/config

volumes:
  axon-data:
  axon-events:
  axon-config:
```

### CQRS Application Example

Using the Axon Framework with Axon Server:

```java
// Command handler
@CommandHandler
public void handle(CreateOrderCommand cmd) {
    AggregateLifecycle.apply(new OrderCreatedEvent(
        cmd.getOrderId(),
        cmd.getCustomerId(),
        cmd.getItems(),
        cmd.getTotalAmount()
    ));
}

// Event handler - updates the read model
@EventHandler
public void on(OrderCreatedEvent event) {
    OrderView view = new OrderView();
    view.setOrderId(event.getOrderId());
    view.setCustomerId(event.getCustomerId());
    view.setStatus("CREATED");
    view.setTotalAmount(event.getTotalAmount());
    orderRepository.save(view);
}
```

Axon Server tracks the position of each event processor using tracking tokens, ensuring that projections stay synchronized with the event stream even after restarts.

### When to Choose Axon Server

- **Java/Kotlin ecosystems** — tight integration with Axon Framework
- **Greenfield CQRS projects** — designed from the ground up for this pattern
- **Development teams new to CQRS** — the framework handles much of the complexity
- **Moderate event volumes** — the open-source SE edition handles single-node workloads well

Axon Server SE (Standard Edition) is free and open-source for single-node deployments. The Enterprise edition adds clustering, backup, and monitoring features.

## EventStoreDB: Immutable Event Storage with Projections

[EventStoreDB](https://github.com/EventStore/EventStore) is a database built from the ground up for event sourcing. It stores events in streams, supports optimistic concurrency, and includes a powerful JavaScript-based projection system for building read models directly within the database.

**Key features:**
- Immutable event storage with stream-level and expected version concurrency
- JavaScript projections for real-time read model building
- Persistent subscriptions for reliable event processing
- gRPC and HTTP APIs
- Multi-node clustering with automatic failover
- Time-travel debugging — replay events to any point in time
- Official Docker images and Kubernetes operator

### Docker Compose Configuration

```yaml
services:
  eventstore:
    image: ghcr.io/eventstore/eventstore:24.10
    container_name: eventstore
    restart: unless-stopped
    environment:
      - EVENTSTORE_CLUSTER_SIZE=1
      - EVENTSTORE_RUN_PROJECTIONS=All
      - EVENTSTORE_START_STANDARD_PROJECTIONS=true
      - EVENTSTORE_EXT_HTTP_PORT=2113
      - EVENTSTORE_EXT_TCP_PORT=1113
      - EVENTSTORE_INSECURE=true
    ports:
      - "2113:2113"
    volumes:
      - es-data:/var/lib/eventstore
      - es-logs:/var/log/eventstore

volumes:
  es-data:
  es-logs:
```

### Projection Example

Build a read model directly in EventStoreDB using JavaScript:

```javascript
// Projection: Calculate total revenue per customer
fromStream('order-events')
    .when({
        $init: function() {
            return { totalRevenue: {} };
        },
        OrderPlaced: function(state, event) {
            var customerId = event.data.customerId;
            if (!state.totalRevenue[customerId]) {
                state.totalRevenue[customerId] = 0;
            }
            state.totalRevenue[customerId] += event.data.totalAmount;
        }
    })
    .outputState()
    .toStream('customer-revenue-totals');
```

### CQRS with Persistent Subscriptions

For external read model services, use persistent subscriptions:

```bash
# Create a persistent subscription group
curl -X PUT http://localhost:2113/subscriptions/order-service/orders \
  -u admin:changeit \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "streamName": "order-"
    }
  }'
```

Your application connects to this subscription and receives events reliably, even if it goes offline temporarily.

### When to Choose EventStoreDB

- **Pure event sourcing** — the database IS your source of truth
- **Multi-language teams** — works with any language via gRPC or HTTP
- **Time-travel requirements** — replay events to reconstruct historical state
- **High event throughput** — optimized for append-heavy workloads

EventStoreDB is fully open-source under the Event Store Source Available License. It requires a license for production use but is free for development and testing.

## Apache Kafka: Event Streaming as CQRS Backbone

[Apache Kafka](https://github.com/apache/kafka) is a distributed event streaming platform that, while not purpose-built for CQRS, has become the de facto backbone for CQRS implementations in large-scale systems. Its partitioned log architecture maps naturally to event sourcing, and its consumer group mechanism handles projection distribution.

**Key features:**
- Distributed, partitioned event log with configurable retention
- Consumer groups for parallel projection processing
- Kafka Streams for in-stream processing and materialized views
- Exactly-once semantics for reliable event processing
- Schema Registry (via Confluent or Apicurio) for event schema evolution
- Massive horizontal scalability
- Vast ecosystem: connectors, monitoring, and management tools

### Docker Compose with KRaft Mode

```yaml
services:
  kafka:
    image: apache/kafka:3.8.0
    container_name: kafka
    restart: unless-stopped
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_RETENTION_HOURS: 168
    ports:
      - "9092:9092"
    volumes:
      - kafka-data:/var/lib/kafka/data

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    container_name: kafka-ui
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092

volumes:
  kafka-data:
```

### CQRS with Kafka Streams

Build a materialized view (read model) using Kafka Streams:

```java
StreamsBuilder builder = new StreamsBuilder();

// Read order events from the command-side topic
KStream<String, OrderEvent> orders = builder.stream("order-events");

// Build the read model: total orders per customer
orders
    .groupBy((key, event) -> event.getCustomerId())
    .count(Materialized.as("customer-order-counts"))
    .toStream()
    .to("customer-order-counts-topic");
```

For non-Java ecosystems, use Kafka consumers in Python, Go, or Node.js to build projections:

```python
from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'order-events',
    bootstrap_servers='kafka:9092',
    auto_offset_reset='earliest',
    group_id='order-projection-service'
)

for message in consumer:
    event = json.loads(message.value)
    # Update read model in your database
    update_order_projection(event)
```

### When to Choose Apache Kafka

- **Large-scale systems** — millions of events per second
- **Multi-team, multi-language environments** — Kafka clients exist for every language
- **Existing Kafka infrastructure** — leverage what you already have
- **Stream processing needs** — Kafka Streams or ksqlDB for real-time transformations

Kafka is the most complex of the three to operate but also the most scalable and widely adopted.

## Feature Comparison Matrix

| Feature | Axon Server | EventStoreDB | Apache Kafka |
|---------|-------------|--------------|--------------|
| **Purpose** | CQRS-specific | Event sourcing | Event streaming |
| **Primary language** | Java/Kotlin | Any (gRPC/HTTP) | Any (clients for all) |
| **Event model** | Aggregate streams | Event streams | Partitioned logs |
| **Read models** | Axon Framework projections | JavaScript projections | Kafka Streams / consumers |
| **Clustering (OSS)** | Single-node (SE) | 3-node minimum | 3-node minimum |
| **Schema registry** | Via Axon Server | Built-in metadata | Separate (Apicurio/Confluent) |
| **Query language** | Axon Framework API | JavaScript projections | ksqlDB / Kafka Streams |
| **Retention** | Configurable | Infinite (default) | Configurable (time/size) |
| **Docker image** | `axoniq/axonserver` | `ghcr.io/eventstore/eventstore` | `apache/kafka` |
| **License** | BSL 1.1 (SE) | Event Store Source Available | Apache 2.0 |
| **Best for** | Java CQRS apps | Pure event sourcing | Large-scale streaming |

## Deployment Comparison

| Aspect | Axon Server SE | EventStoreDB | Kafka (KRaft) |
|--------|---------------|--------------|---------------|
| Min RAM | 2 GB | 2 GB | 4 GB |
| Min nodes | 1 | 3 | 3 |
| Storage | Append-only log | Append-only log | Partitioned log |
| Backup | File-based | File-based + snapshots | MirrorMaker 2 |
| Monitoring | Built-in dashboard | Built-in dashboard | JMX + Kafka UI |
| Kubernetes | StatefulSet | Operator available | Strimzi / KRaft |

## Decision Framework

**Choose Axon Server if:**
- Your team works in Java/Kotlin and uses the Axon Framework
- You want CQRS-specific features (command routing, tracking tokens) out of the box
- You're building a new CQRS system and want maximum developer productivity
- Single-node deployment is sufficient for your event volume

**Choose EventStoreDB if:**
- You want the database to be your event source of truth
- You need time-travel debugging and state reconstruction capabilities
- Your team uses multiple languages and wants a language-agnostic event store
- You prefer JavaScript-based projections inside the database

**Choose Apache Kafka if:**
- You need massive horizontal scalability
- Your organization already runs Kafka for other purposes
- You have multi-language teams and need broad client ecosystem support
- You want stream processing (Kafka Streams, ksqlDB) alongside CQRS

## Production Deployment Checklist

1. **Event schema evolution** — use a schema registry to manage backward/forward compatibility
2. **Idempotent event handlers** — ensure projections handle duplicate events correctly
3. **Event versioning** — include schema version in every event for future migration
4. **Monitoring** — track event lag, projection latency, and storage growth
5. **Backup strategy** — snapshot projections and archive event streams
6. **Security** — enable authentication and authorization for event access
7. **Retention policies** — define how long events are kept for compliance
8. **Disaster recovery** — test event replay from backups to verify data integrity

## Why Self-Host Your CQRS Platform?

Running CQRS infrastructure on managed cloud services introduces several trade-offs that self-hosting eliminates. Event volumes in CQRS systems are typically 10-100x higher than in traditional CRUD applications — every state change generates one or more events. At scale, cloud-managed event stores and streaming platforms become expensive.

Self-hosting also gives you control over event retention. Cloud providers often cap retention at 7-30 days, but CQRS systems may need to replay events from months or years ago for auditing, compliance, or data migration purposes. On-premises storage is significantly cheaper per gigabyte than cloud-managed event logs.

For teams building distributed systems, combining CQRS with [distributed locking](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/) ensures that concurrent commands don't create inconsistent state. And for workflow-driven CQRS processes, [workflow orchestration engines](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-orchestration-guide-2026/) handle the coordination layer.

## Frequently Asked Questions

### What is CQRS and why does it need special infrastructure?

CQRS (Command Query Responsibility Segregation) separates write operations (commands) from read operations (queries). Specialized infrastructure like Axon Server, EventStoreDB, or Kafka provides the event store that records all state changes, the message routing that delivers commands to the right handler, and the projection system that builds read models from events.

### Can I use CQRS without event sourcing?

Yes. CQRS is about separating read and write models; event sourcing is about storing state changes as events. They're often combined but are independent patterns. You can use CQRS with a traditional database, though you lose the audit trail and replay capabilities that event sourcing provides.

### Is Apache Kafka suitable for CQRS?

Yes, Kafka is widely used as the backbone for CQRS systems, especially at scale. While not purpose-built for CQRS like Axon Server, Kafka's partitioned log and consumer group mechanisms map naturally to event sourcing and projection distribution. Kafka Streams adds in-stream processing for building read models.

### How do I handle schema evolution in a CQRS system?

Use a schema registry (Apicurio for Kafka, built-in for EventStoreDB) to manage event schema versions. Design events to be backward-compatible: add optional fields, never remove required fields, and use event upcasting for breaking changes. EventStoreDB supports upcasters that transform old events to new schemas during reads.

### What's the difference between Axon Server and EventStoreDB?

Axon Server is purpose-built for CQRS with command routing, tracking tokens, and tight Axon Framework integration. EventStoreDB is a general-purpose event sourcing database with JavaScript projections and language-agnostic APIs. Axon Server is more opinionated but easier for Java teams; EventStoreDB is more flexible but requires more application-level code.

### How do I scale a self-hosted CQRS system?

For Axon Server SE, scale horizontally by adding application instances — the server itself is single-node in the free edition. EventStoreDB scales to 3+ nodes with automatic clustering. Kafka scales almost infinitely with partitioned topics and broker clusters. For read model scaling, deploy projection services independently and use consumer groups to distribute load.

### Can I migrate from one CQRS platform to another?

Migration is possible but requires careful planning. Export events from the source system, transform them to the target format if needed, and replay them into the target system's event store. Test projections thoroughly after migration, as event ordering and semantics may differ between platforms.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CQRS Platforms — Axon Server vs EventStoreDB vs Apache Kafka 2026",
  "description": "Compare three self-hosted CQRS infrastructure platforms: Axon Server for Java CQRS applications, EventStoreDB for pure event sourcing, and Apache Kafka for large-scale event streaming. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
