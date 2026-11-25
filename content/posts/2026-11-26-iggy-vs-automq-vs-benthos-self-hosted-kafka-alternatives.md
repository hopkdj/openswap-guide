---
title: "Kafka Without Kafka in 2026: Iggy vs AutoMQ vs Benthos (Redpanda Connect)"
date: 2026-11-26
tags: ["kafka", "event-streaming", "message-queue", "self-hosted", "distributed-systems"]
draft: false
cover: "/img/screenshots/iggy-web-ui.jpg"
description: "You do not need a three-node Kafka cluster. Comparing Apache Iggy, AutoMQ and Benthos (Redpanda Connect) for lightweight self-hosted event streaming in 2026."
---

A three-broker Kafka cluster with ZooKeeper (or KRaft controllers), three more nodes of monitoring, and a partition rebalance plan is a reasonable answer to "we process two million events a second". It is an absurd answer to "our six services need to hand each other messages."

That mismatch is the most common infrastructure overbuild in self-hosted stacks. Kafka's operational surface — partition reassignment, ISR shrinkage, disk sizing per broker, consumer group rebalances during deploys — exists because Kafka was designed for LinkedIn-scale log retention. Small teams inherit the complexity and use 2% of the capability.

Three projects offer a way out, and they take **three genuinely different routes**. Knowing which route matches your problem is the whole decision.

## Quick Verdict (TL;DR)

- **Apache Iggy** if you want a message broker that starts in a container, speaks TCP/HTTP instead of the Kafka protocol, and idles under 100 MB. Closest thing to "Kafka, but small".
- **AutoMQ** if you are already on Kafka clients and want to keep them — it is Kafka-compatible but keeps data in object storage, so brokers become stateless and cheap to autoscale.
- **Benthos / Redpanda Connect** if you do not need a broker at all and just need to move, transform and route events between systems — one binary, one YAML file.

Also legitimate: **stay on Kafka**. If you need ecosystem tooling (Connect, ksqlDB, Schema Registry) and multi-tenant retention guarantees, nothing here replaces it. The rest of this article is for the other 90% of deployments.

## How They Compare

| Dimension | Apache Iggy | AutoMQ | Benthos (Redpanda Connect) |
|---|---|---|---|
| What it is | Message streaming server | Kafka-compatible broker, diskless | Stream processor / pipeline engine |
| Wire protocol | Own TCP + HTTP APIs | **Kafka protocol** | Connectors (Kafka, HTTP, S3, DBs…) |
| Persistence | Local disk (WAL + segments) | S3-compatible object storage | None (stateless; optional cache) |
| Components to run | 1 container | Broker(s) + object store | 1 binary |
| Highly available by design | Quorum replication | Yes, stateless brokers | Stateless, run N copies |
| GitHub stars | 5,354 | 10,936 | 8,810 |
| Language | Rust | Java | Go |
| Last commit | 2026-11-25 | 2026-11-25 | 2026-11-25 |
| Management UI | Web UI image available | Kafka UI tooling works | None (config is the UI) |
| Learning curve | Low | Low if you know Kafka | Medium (YAML DSL, but tiny surface) |
| Best for | Small/medium event streams, edge | Kafka workloads with cold storage economics | ETL, routing, bridging, CDC fan-out |

All star counts and last-commit dates fetched from the GitHub API on 2026-11-26.

## Which One For Which Job

| You need… | Pick | Why |
|---|---|---|
| Pub/sub between 5 services, 10k msg/s, one VM | Iggy | Single container, no Kafka protocol tax, web UI included |
| Existing Kafka producers/consumers you refuse to rewrite | AutoMQ | Same protocol, `bootstrap.servers` unchanged |
| Kafka retention costs dominated by cold data | AutoMQ | Segments live in S3/MinIO, brokers keep almost no disk |
| Consume a topic, enrich, write to Postgres | Benthos | One YAML, no broker in the middle |
| Bridge MQTT → Kafka → S3 archive | Benthos | Connector chaining is the product |
| Ultra-low latency in Rust/Go services | Iggy | Direct TCP API, no JVM, no rebalance pauses |
| Multi-tenant cluster with Schema Registry | Kafka | Ecosystem still wins here |

## Apache Iggy — The Broker That Fits In a Container

Iggy is an Apache project (incubating) written in Rust, and its pitch is honest: a streaming server with a small footprint that does not require you to learn Kafka's internals. It organises data as **streams → topics → partitions**, which will feel familiar, but the API surface is its own TCP and HTTP protocol rather than the Kafka wire format.

The official Docker invocation from the project README is unusually specific, and the flags are not optional:

```bash
docker run -d --name iggy \
  --cap-add=SYS_NICE --security-opt seccomp=unconfined --ulimit memlock=-1:-1 \
  -e IGGY_ROOT_USERNAME=iggy -e IGGY_ROOT_PASSWORD=iggy \
  -e IGGY_TCP_ADDRESS=0.0.0.0:8090 -e IGGY_HTTP_ADDRESS=0.0.0.0:3000 \
  -e IGGY_NODE_ADVERTISED_ADDRESS=localhost \
  -p 8090:8090 -p 3000:3000 \
  -v iggy:/app/local_data \
  apache/iggy
```

`SYS_NICE`, `seccomp=unconfined` and unlimited locked memory are required because the server pins threads and pre-allocates memory for predictable latency. Drop them and the container starts but the benchmark numbers — and sometimes the server itself — fall over.

Management is CLI-first, and the CLI ships inside the image:

```bash
docker exec -it iggy iggy -u iggy -p iggy stream list
```

There is also an official web UI image (`apache/iggy-web-ui`) for browsing streams, topics, partitions and messages. That UI is what convinced me Iggy is production-adjacent rather than a benchmark toy: you can see consumer offsets and message payloads without writing a client.

Operationally, Iggy is the simplest of the three: one container, one volume, no object store, no JVM heap tuning. The trade-off is ecosystem: no Kafka Connect, no ksqlDB, no drop-in compatibility with the thousands of tools that speak the Kafka protocol. If your consumers are your own services, that is irrelevant. If they are third-party, it is disqualifying.

![Apache Iggy web UI for browsing streams and topics](/img/screenshots/iggy-web-ui.jpg "Iggy web UI showing streams, topics and message browsing")

## AutoMQ — Kafka Semantics, Object-Storage Economics

AutoMQ keeps the Kafka protocol and throws away the part that hurts: local disk retention. Brokers become effectively stateless because data segments are written to S3-compatible storage, so you can scale brokers up and down without rebalancing terabytes, and you stop paying for three copies of the same data on three sets of EBS volumes.

The repository's single-node compose file is a complete working lab — it starts MinIO as the S3 backend, creates the buckets, then boots the broker in KRaft mode:

```yaml
services:
  automq:
    image: automqinc/automq:1.6.0
    stop_grace_period: 1m
    environment:
      - KAFKA_S3_ACCESS_KEY=minioadmin
      - KAFKA_S3_SECRET_KEY=minioadmin
      - KAFKA_HEAP_OPTS=-Xms1g -Xmx4g -XX:MetaspaceSize=96m -XX:MaxDirectMemorySize=1G
      - CLUSTER_ID=3D4fXN-yS1-vsQ8aJ_q4Mg
    command:
      - bash
      - -c
      - |
        /opt/automq/kafka/bin/kafka-server-start.sh \
        /opt/automq/kafka/config/kraft/server.properties \
        --override cluster.id=$$CLUSTER_ID \
        --override node.id=0 \
        --override controller.quorum.voters=0@server1:9093 \
        --override advertised.listeners=PLAINTEXT://server1:9092 \
        --override s3.data.buckets='0@s3://automq-data?region=us-east-1&endpoint=http://minio:9000&pathStyle=true' \
        --override s3.ops.buckets='1@s3://automq-ops?region=us-east-1&endpoint=http://minio:9000&pathStyle=true' \
        --override s3.wal.path='0@s3://automq-data?region=us-east-1&endpoint=http://minio:9000&pathStyle=true'
    depends_on:
      - minio
      - mc
```

Because the protocol is Kafka's, clients do not change. Your existing producer config keeps working:

```properties
bootstrap.servers=server1:9092
acks=all
enable.idempotence=true
```

The catch: object storage adds latency to the write path (the WAL is still local, which is why `s3.wal.path` exists), and you are betting on a specific vendor's implementation of Kafka compatibility. AutoMQ tracks upstream Kafka closely, but "compatible" always lags "identical" — test your interceptors, serializers and exactly-once paths before migrating a critical pipeline. Also budget the object-storage cost model honestly: S3 request charges on a chatty workload are not free, and cross-AZ traffic assumptions change.

![AutoMQ architecture: stateless brokers over object storage](/img/screenshots/automq-architecture.jpg "AutoMQ separates compute (brokers) from storage (S3)")

## Benthos — Delete the Broker Entirely

Most "we need Kafka" requirements are actually "we need to move data from A to B and reshape it". Benthos (now Redpanda Connect) makes that literal: a single Go binary, a YAML file with `input`, `pipeline` and `output` sections, and hundreds of connectors.

The simplest real example from the repository is four lines of behaviour:

```yaml
input:
  stdin: {}

pipeline:
  processors:
    - string_split:
        delimiter: ","
        empty_as_null: true

output:
  stdout: {}
```

Swap `stdin` for a Kafka consumer and `stdout` for Postgres, and you have replaced a Flink job plus a broker:

```yaml
input:
  redpanda:
    seed_brokers: [ "localhost:9092" ]
    topics: [ "orders" ]
    consumer_group: "orders-enricher"

pipeline:
  processors:
    - mapping: |
        root.order_id = this.id
        root.total_cents = this.amount * 100
        root.ingested_at = now()

output:
  stdout: {}
```

What Benthos buys you is **no broker in the middle**: no retention policy to size, no consumer group to rebalance, no partition count to argue about. What it does not give you is durable pub/sub — if a downstream service is offline, you need Benthos's own retry/backpressure semantics or an actual broker. It is a pipeline engine, not a message log, and confusing the two is how people end up with data loss.

The YAML DSL is genuinely quick to learn, but it is a DSL: complex transformations end up as Bloblang expressions that your team has to read. Budget a day, not an hour.

## The Pitfalls Nobody Documents

**1. Iggy's container flags are load-bearing.** Missing `--ulimit memlock=-1:-1` produces sporadic latency spikes that look like network problems. Missing `SYS_NICE` means the runtime cannot pin threads, and throughput becomes unpredictable under load.

**2. AutoMQ without a plan for S3 latency is a trap.** The local WAL absorbs bursts, but a slow or rate-limited object store eventually shows up as producer timeouts. Monitor S3 request latency, not just broker CPU.

**3. Compatibility is not identity.** For AutoMQ, run your serializers, interceptors and transactional producers through a real test before cutover. Protocol tests pass long before edge-case semantics do.

**4. Benthos is stateless by default.** Do not put it in front of a system that cannot tolerate a lost in-flight message unless you configure retries, a dead-letter output, and `max_in_flight` sensibly. This is the single most common production incident with pipeline engines.

**5. Partition counts are forever (mostly).** Iggy and AutoMQ both let you create partitions cheaply; that does not mean you should create 200 per topic. More partitions means more file handles, more memory, and slower recovery.

**6. Retention is a budget line, not a setting.** Kafka's default seven days on a busy topic can quietly become terabytes. AutoMQ moves that cost to S3, which is cheaper per GB but not free — and retrieval is not instant.

## Why Self-Host Your Event Layer

Managed streaming is priced per throughput-hour and per storage-GB-month, with a markup that assumes you cannot run a broker yourself. For steady, predictable volumes, self-hosting an Iggy container or an AutoMQ cluster on object storage cuts that bill by an order of magnitude — and removes the vendor's ability to change your retention economics overnight.

The real cost is operational maturity: you own upgrades, disk/object-store monitoring, and the on-call runbook. That trade is favourable the moment your stream is small enough to fit on one box — which, for most self-hosted stacks, it is. If you are still choosing a broker, our [pub/sub platform comparison](../2026-05-22-self-hosted-pubsub-platforms-nats-rabbitmq-apache-pulsar-guide/) and [message broker HA guide](../2026-06-01-self-hosted-message-broker-ha-rabbitmq-kafka-nats-guide/) cover the heavier options, and the [EventStoreDB vs Kafka vs Pulsar breakdown](../2026-04-20-eventstoredb-vs-kafka-vs-pulsar-self-hosted-event-sourcing-guide-2026/) is the right read if you actually need event sourcing rather than messaging.

## FAQ

### Do I need Kafka at all for a small self-hosted stack?

Usually not. If your requirement is "service A notifies service B" or "collect events into a database", a pipeline engine like Benthos replaces the broker entirely. You need a real log when multiple independent consumers must replay history at their own pace.

### Is Apache Iggy a drop-in Kafka replacement?

No. Iggy has its own TCP and HTTP APIs, so producers and consumers must use Iggy clients. It is a replacement for the *role* Kafka plays, not for Kafka's protocol surface.

### Can AutoMQ run without S3?

It needs an S3-compatible endpoint. MinIO is the usual self-hosted choice and is what the project's own compose file spins up; other S3-compatible stores work if they support the required request patterns.

### What happens to in-flight messages if Benthos restarts?

Messages not yet acknowledged are re-fetched from the source when the input supports acknowledgement (Kafka, AMQP, SQS do). For sources like HTTP or stdin, in-flight messages are lost — that is what a dead-letter output and retries are for.

### Which of the three is cheapest to run?

Iggy on a single small VM, by a wide margin: one container, local disk, no object store, no JVM. AutoMQ is cheapest per retained terabyte but needs an object store and more moving parts. Benthos is cheapest when it lets you delete a broker you would otherwise operate.

### Can I mix them?

Yes, and it is often the right design: Benthos as the ingestion and routing layer, Iggy or AutoMQ as the durable log behind it. Keep the pipeline engine stateless and the log durable, and each component stays replaceable.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kafka Without Kafka in 2026: Iggy vs AutoMQ vs Benthos (Redpanda Connect)",
  "description": "Comparing Apache Iggy, AutoMQ and Benthos for lightweight self-hosted event streaming, with real Docker configs and operational pitfalls.",
  "datePublished": "2026-11-26",
  "dateModified": "2026-11-26",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
