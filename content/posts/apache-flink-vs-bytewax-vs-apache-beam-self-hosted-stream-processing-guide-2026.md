---
title: "Apache Flink vs Bytewax vs Apache Beam: Self-Hosted Stream Processing Guide 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "data-engineering"]
draft: false
description: "Complete comparison of self-hosted stream processing frameworks in 2026. Apache Flink, Bytewax, and Apache Beam — deployment guides, feature comparison, and production setup with Docker Compose."
---

## Why Self-Host Stream Processing in 2026?

Stream processing engines let you ingest, transform, and analyze data in real time as it flows through your systems — rather than waiting for batch windows to close. In 2026, real-time data pipelines power everything from fraud detection and live dashboards to IoT telemetry and event-driven microservices.

Managed stream processing services like **Confluent Cloud (Kafka Streams)**, **AWS Kinesis Data Analytics**, and **Google Cloud Dataflow** offer convenience but come with heavy costs:

- **Pricing that scales with throughput** — managed Flink and Dataflow charge per processing unit or vCPU, and costs spike during traffic bursts
- **Your data traverses someone else's infrastructure** — sensitive event streams, user behavior data, and business metrics flow through cloud provider networks
- **Vendor-specific APIs** — Kinesis SQL, Dataflow templates, and Confluent extensions lock you into a single ecosystem
- **Operational opacity** — debugging a stuck pipeline or tuning backpressure on a managed service is often a support ticket away
- **Cold-start latency** — serverless stream processors add seconds of startup delay, unacceptable for low-latency use cases

Self-hosting gives you full control over the processing topology, data locality, and cost model. With commodity hardware and container orchestration, you can run production-grade stream processing at a fraction of managed service costs — while keeping every byte of data within your own infrastructure.

## The Three Contenders

Three open-source frameworks dominate the self-hosted stream processing landscape in 2026, each with a distinct philosophy:

| Feature | Apache Flink | Bytewax | Apache Beam |
|---|---|---|---|
| **Primary Language** | Java / Scala / SQL | Python | Java (SDKs: Python, Go, Scala) |
| **Execution Engine** | Custom JVM runtime | Rust-based (Python bindings) | Pluggable runners (Flink, Spark, Direct) |
| **State Management** | RocksDB (incremental checkpoints) | In-process with persistent snapshots | Runner-dependent |
| **Windowing** | Tumbling, sliding, session, global | Tumbling, sliding, session | Tumbling, sliding, session, global |
| **Exactly-Once Semantics** | Yes (end-to-end with Kafka) | Yes | Yes (with Flink runner) |
| **Event-Time Processing** | Native (watermarks) | Native (watermarks) | Native (watermarks) |
| **CEP (Complex Event Processing)** | Built-in library | Custom logic required | No native CEP |
| **SQL Interface** | Flink SQL (fully featured) | No | Limited (via ZetaSQL) |
| **Deployment Model** | JobManager + TaskManagers | Single binary or cluster | Depends on runner |
| **Learning Curve** | Steep | Moderate | Steep (two layers: API + runner) |
| **GitHub Stars** | 25k+ | 4k+ | 8k+ |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

**Apache Flink** is the industry standard. Born from the Stratosphere research project and adopted by Alibaba, Uber, and Netflix, it offers the most feature-complete stream processing engine with native fault tolerance, rich state backends, and a mature SQL layer. The trade-off is operational complexity — a Flink cluster requires coordinating a JobManager and multiple TaskManagers, each with their own resource profiles.

**Bytewax** is the newcomer that takes a radically different approach. Written in Rust with a Python API, it treats stream processing as a Python function applied to data flowing through a graph. There is no JVM, no cluster manager to configure, and no separate deployment topology — you write a Python script and run it. Under the hood, Bytewax partitions data across workers automatically and uses a custom Rust runtime for performance. It is ideal for teams that want stream processing without the operational overhead of a full distributed system.

**Apache Beam** is a unified programming model rather than a processing engine. You write your pipeline once using Beam's SDK, then choose a runner: Flink for streaming, Spark for batch, or the Direct runner for local testing. The promise is portability — the same pipeline code runs on any runner. In practice, this means maintaining an abstraction layer on top of your chosen engine, which adds complexity but pays off when you need to switch runners or run the same logic across batch and streaming contexts.

## Installation and Deployment

### Apache Flink — Docker Compose Setup

Flink's architecture separates the JobManager (coordinator) from TaskManagers (workers). A minimal production-ready deployment requires one JobManager and at least two TaskManagers.

Create a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  jobmanager:
    image: apache/flink:1.20.0-scala_2.12-java17
    container_name: flink-jobmanager
    ports:
      - "8081:8081"
    command: jobmanager
    environment:
      - |
        FLINK_PROPERTIES=
        jobmanager.rpc.address: jobmanager
        taskmanager.numberOfTaskSlots: 4
        state.backend: rocksdb
        state.checkpoints.dir: file:///tmp/flink-checkpoints
        state.savepoints.dir: file:///tmp/flink-savepoints
        execution.checkpointing.interval: 60s
    volumes:
      - flink-checkpoints:/tmp/flink-checkpoints
      - flink-savepoints:/tmp/flink-savepoints

  taskmanager:
    image: apache/flink:1.20.0-scala_2.12-java17
    container_name: flink-taskmanager
    depends_on:
      - jobmanager
    command: taskmanager
    environment:
      - |
        FLINK_PROPERTIES=
        jobmanager.rpc.address: jobmanager
        taskmanager.numberOfTaskSlots: 4
        state.backend: rocksdb
        state.checkpoints.dir: file:///tmp/flink-checkpoints
    volumes:
      - flink-checkpoints:/tmp/flink-checkpoints
    deploy:
      replicas: 2

  kafka:
    image: apache/kafka:3.9.0
    container_name: kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

volumes:
  flink-checkpoints:
  flink-savepoints:
```

Start the cluster:

```bash
docker compose up -d
```

Access the Flink Web UI at `http://localhost:8081`. Submit a job using the Flink CLI:

```bash
docker exec flink-jobmanager flink run \
  -c com.example.StreamingJob \
  /opt/flink/usrlib/my-job.jar \
  --input kafka://kafka:9092/events \
  --output kafka://kafka:9092/results
```

For SQL-based processing, Flink's SQL Client provides an interactive session:

```bash
docker exec -it flink-jobmanager sql-client.sh
```

```sql
CREATE TABLE events (
  user_id STRING,
  event_type STRING,
  amount DOUBLE,
  event_time TIMESTAMP(3),
  WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
  'connector' = 'kafka',
  'topic' = 'events',
  'properties.bootstrap.servers' = 'kafka:9092',
  'format' = 'json',
  'scan.startup.mode' = 'earliest-offset'
);

SELECT
  user_id,
  TUMBLE_START(event_time, INTERVAL '1' MINUTE) AS window_start,
  SUM(amount) AS total_amount
FROM events
WHERE event_type = 'purchase'
GROUP BY user_id, TUMBLE(event_time, INTERVAL '1' MINUTE);
```

### Bytewax — Single Binary Deployment

Bytewax requires no cluster manager. A single process can handle streaming workloads, and you scale horizontally by running multiple worker processes that coordinate via a shared message broker.

Install the Python package:

```bash
pip install bytewax
```

Create a streaming pipeline (`pipeline.py`):

```python
from datetime import timedelta
from bytewax.dataflow import Dataflow
from bytewax.connectors.kafka import KafkaSourceMessage, KafkaSinkMessage
from bytewax.connectors.kafka import KafkaSource, KafkaSink
from bytewax import run_main

def parse_event(msg: KafkaSourceMessage) -> dict:
    import json
    return json.loads(msg.value)

def filter_purchases(event: dict) -> bool:
    return event.get("type") == "purchase"

def extract_amount(event: dict) -> tuple:
    return (event["user_id"], event["amount"])

def sum_amounts(key_amounts: tuple) -> tuple:
    user_id, total = key_amounts
    return (user_id, {"user_id": user_id, "total_amount": round(total, 2)})

flow = Dataflow("purchase_aggregator")

# Read from Kafka
flow.input("kafka_in", KafkaSource(["kafka:9092"], "events", begin_at="earliest"))

# Parse, filter, and aggregate
flow.map(parse_event)
flow.filter(filter_purchases)
flow.map(extract_amount)
flow.reduce_window(
    "sum_window",
    lambda: 0,
    lambda acc, x: acc + x[1],
    lambda key: key[0],
    lambda _: None,
)
flow.map(sum_amounts)

# Write back to Kafka
flow.output(
    "kafka_out",
    KafkaSink(
        ["kafka:9092"],
        "results",
        lambda result: result[0],
        lambda result: str(result[1]).encode(),
    ),
)

if __name__ == "__main__":
    run_main(flow)
```

Run the pipeline:

```bash
# Single-worker mode (development)
python -m bytewax.run pipeline

# Multi-worker cluster mode (production)
python -m bytewax.run \
  --processes 4 \
  --threads-per-process 2 \
  pipeline
```

For a containerized deployment with multiple workers, use Docker Compose:

```yaml
version: "3.8"

services:
  worker:
    build: .
    command: python -m bytewax.run pipeline
    environment:
      - BYTEWAX_PYTHONPATH=/app
    deploy:
      replicas: 3
    volumes:
      - ./pipeline.py:/app/pipeline.py
    depends_on:
      - kafka

  kafka:
    image: apache/kafka:3.9.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
```

The Dockerfile for the worker:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY pipeline.py .
ENV BYTEWAX_PYTHONPATH=/app
```

### Apache Beam — Runner-Agnostic Pipeline

Beam's architecture requires choosing a runner for execution. For self-hosted streaming, the Flink runner is the most common choice.

Install the Beam Python SDK:

```bash
pip install apache-beam[flink]
```

Create a Beam pipeline (`beam_pipeline.py`):

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, FlinkOptions
from apache_beam.transforms.window import FixedWindows
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode
import json

class ParseEvent(beam.DoFn):
    def process(self, element):
        try:
            event = json.loads(element)
            yield event
        except json.JSONDecodeError:
            pass

class FilterPurchases(beam.DoFn):
    def process(self, element):
        if element.get("type") == "purchase":
            yield element

class ExtractUserAmount(beam.DoFn):
    def process(self, element):
        yield (element["user_id"], element["amount"])

class FormatResult(beam.DoFn):
    def process(self, element):
        user_id, total = element
        yield json.dumps({
            "user_id": user_id,
            "total_amount": round(total, 2)
        })

def run():
    flink_options = FlinkOptions(
        flink_master="http://flink-jobmanager:8081",
        environment_type="LOOPBACK",
    )

    pipeline_options = PipelineOptions(
        runner="FlinkRunner",
        streaming=True,
        flink_submit_uber_jar=True,
    )
    pipeline_options.view_as(FlinkOptions).update(flink_options)

    with beam.Pipeline(options=pipeline_options) as p:
        (
            p
            | "ReadFromKafka" >> beam.io.ReadFromKafka(
                consumer_config={"bootstrap.servers": "kafka:9092"},
                topics=["events"],
                with_metadata=False,
            )
            | "ParseJSON" >> beam.ParDo(ParseEvent())
            | "FilterPurchases" >> beam.ParDo(FilterPurchases())
            | "ExtractUserAmount" >> beam.ParDo(ExtractUserAmount())
            | "Window" >> beam.WindowInto(
                FixedWindows(size=60),
                trigger=AfterWatermark(
                    early=AfterProcessingTime(delay=10),
                ),
                accumulation_mode=AccumulationMode.DISCARDING,
            )
            | "SumAmounts" >> beam.CombinePerKey(sum)
            | "FormatResult" >> beam.ParDo(FormatResult())
            | "WriteToKafka" >> beam.io.WriteToKafka(
                producer_config={"bootstrap.servers": "kafka:9092"},
                topic="results",
                value_serializer=beam.io.kafka.serialize.StringSerializer(),
            )
        )

if __name__ == "__main__":
    run()
```

Submit to the Flink runner:

```bash
python beam_pipeline.py \
  --runner=FlinkRunner \
  --flink_master=http://flink-jobmanager:8081 \
  --streaming=true
```

## Feature Deep Dive

### State Management and Fault Tolerance

**Flink** uses RocksDB as its default state backend, storing operator state locally on each TaskManager and periodically checkpointing to a distributed filesystem (HDFS, S3, or NFS). Checkpoints are incremental and asynchronous, meaning they do not block processing. Savepoints provide a manual checkpoint mechanism for planned upgrades — you can stop a job, save its state, upgrade the Flink version, and resume from the exact same point.

```
state.backend: rocksdb
state.backend.incremental: true
state.checkpoints.dir: s3://flink-state/checkpoints
execution.checkpointing.interval: 30s
execution.checkpointing.mode: EXACTLY_ONCE
execution.checkpointing.timeout: 10min
```

**Bytewax** manages state in-process using Python dictionaries and lists, with optional persistent snapshots written to disk or S3. Because the state lives in memory, recovery after a crash replays from the last committed offset in the input source (typically Kafka). This is simpler than Flink's approach but means state size is bounded by available RAM unless you implement external state storage in your pipeline logic.

**Beam** delegates state management entirely to the runner. When using the Flink runner, you get Flink's RocksDB checkpointing. When using the Spark runner, you get Spark's block manager. This portability comes at the cost of predictability — your state semantics change when you change runners.

### Windowing and Triggers

All three frameworks support the standard window types: tumbling (fixed-size, non-overlapping), sliding (fixed-size, overlapping), and session (gap-based). Flink provides the richest trigger system:

| Trigger Type | Flink | Bytewax | Beam |
|---|---|---|---|
| Watermark-based | Yes | Yes | Yes |
| Processing-time | Yes | Yes | Yes |
| Count-based | Yes | No | Yes |
| Composite (OR/AND) | Yes | No | Yes |
| Custom (user-defined) | Yes | Limited | Yes |
| Early firings | Yes | No | Yes |

Flink's composite triggers let you fire a window early if either a watermark passes OR a count threshold is reached — useful for low-latency dashboards that want interim results. Beam supports similar composition via `Repeatedly.forever(AfterFirst.of(...))`. Bytewax focuses on the core watermark and processing-time triggers, keeping the API surface small.

### Monitoring and Observability

Flink ships with a comprehensive Web UI showing per-operator metrics (records processed, backpressure indicators, checkpoint duration, state size) and a REST API for programmatic access. Integration with Prometheus is built-in:

```
metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter
metrics.reporter.prom.port: 9250-9260
```

Bytewax exposes metrics through Python's standard `logging` module and can integrate with OpenTelemetry via community packages. The monitoring story is less mature but improving rapidly.

Beam relies on the runner's monitoring capabilities. With the Flink runner, you get the Flink UI. With Spark, you get the Spark UI. The Beam model itself does not define a metrics interface.

### Resource Requirements

| Metric | Flink | Bytewax | Beam + Flink Runner |
|---|---|---|---|
| **Min RAM (single node)** | 2 GB | 512 MB | 2 GB (Flink) + Beam overhead |
| **Min RAM (production cluster)** | 8 GB (3 nodes) | 4 GB (3 workers) | 8 GB (3 nodes) |
| **JVM Required** | Yes | No | Yes (Flink runner) |
| **Container Image Size** | ~700 MB | ~200 MB | ~700 MB (Flink) + Beam SDK |
| **Startup Time** | 10-30 seconds | 1-3 seconds | 15-40 seconds |

Bytewax has the smallest footprint by a significant margin. No JVM means faster cold starts, smaller container images, and lower baseline memory usage. This makes it particularly attractive for edge deployments and resource-constrained environments.

## Production Architecture Recommendations

### High-Throughput Analytics Pipeline

For processing millions of events per second with complex aggregations and CEP rules, **Flink** is the clear choice:

```
[Kafka Cluster] → [Flink: Event Parsing & Filtering]
                  → [Flink: Windowed Aggregations (RocksDB)]
                  → [Flink: CEP Pattern Detection]
                  → [ClickHouse / Druid] → [Dashboard]
                  → [Kafka: Alert Topic] → [PagerDuty / Email]
```

Deploy Flink on dedicated nodes with SSD-backed state directories. Configure incremental checkpointing to an S3-compatible store like MinIO:

```
state.backend: rocksdb
state.backend.incremental: true
state.checkpoints.dir: s3://flink-checkpoints/
s3.endpoint: http://minio:9000
s3.access-key: ${MINIO_ACCESS_KEY}
s3.secret-key: ${MINIO_SECRET_KEY}
```

### Python-First Data Team

For teams that want to write stream processing in Python without managing a distributed JVM cluster, **Bytewax** provides the lowest barrier to entry:

```
[Kafka] → [Bytewax Workers (3 replicas)]
        → [PostgreSQL (aggregated results)]
        → [Metabase / Superset (visualization)]
```

Run Bytewax workers as Kubernetes Deployments with a Horizontal Pod Autoscaler based on Kafka consumer lag:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bytewax-workers
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bytewax-workers
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: External
      external:
        metric:
          name: kafka_consumer_lag
          selector:
            matchLabels:
              topic: events
        target:
          type: AverageValue
          averageValue: "1000"
```

### Multi-Runner Portability

For organizations that need to run the same pipeline logic across batch (Spark on a Hadoop cluster) and streaming (Flink on Kubernetes) contexts, **Beam** justifies its abstraction overhead:

```
[Kafka] → [Beam Pipeline (Flink Runner)] → [Real-time Dashboard]
[S3/Parquet] → [Beam Pipeline (Spark Runner)] → [Nightly Reports]
```

The key benefit is a single codebase maintained by one team, deployed to two different execution environments. The cost is debugging two different runners when pipeline behavior diverges.

## Decision Matrix

Choose **Flink** when:
- You process more than 100K events per second
- You need built-in CEP (Complex Event Processing)
- You want a mature SQL interface for ad-hoc stream queries
- Your team has Java/Scala expertise
- You need incremental checkpoints with RocksDB

Choose **Bytewax** when:
- Your team is Python-first and wants minimal operational overhead
- You need fast startup times and small resource footprint
- Your state fits in memory or can be externalized via custom logic
- You are deploying to edge or resource-constrained environments
- You want to iterate quickly without configuring cluster managers

Choose **Beam** when:
- You need to run the same pipeline code on both batch and streaming runners
- Your organization standardizes on multiple processing engines
- You want to avoid vendor lock-in at the API level
- Your team can manage the added complexity of the abstraction layer

All three frameworks are production-ready, open-source, and free to self-host. The right choice depends on your team's language preferences, operational capacity, and data volume — not on licensing or feature gaps. In 2026, the gap between them has narrowed: Flink has improved its Python support (PyFlink), Bytewax has added production clustering, and Beam continues to expand its runner ecosystem. Pick the one that matches your team's skills, deploy it behind your own firewalls, and process your data on your own terms.
