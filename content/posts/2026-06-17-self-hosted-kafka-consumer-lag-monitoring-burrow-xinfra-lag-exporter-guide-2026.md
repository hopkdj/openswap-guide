---
title: "Self-Hosted Kafka Consumer Lag Monitoring: Burrow vs Xinfra Monitor vs Lag Exporter Guide 2026"
date: "2026-06-17"
tags: ["kafka", "monitoring", "consumer-lag", "observability", "streaming", "devops", "docker", "self-hosted"]
draft: false
---

## Why Monitor Kafka Consumer Lag?

Consumer lag is the single most important metric in a Kafka-based data pipeline. It measures how far behind a consumer group is — the difference between the latest offset in a partition and the last committed offset by the consumer. When lag grows, it means data is piling up faster than consumers can process it.

Monitoring consumer lag is essential because:

- **SLA compliance**: Data must be processed within guaranteed time windows
- **Capacity planning**: Lag trends reveal when consumers need to scale up
- **Pipeline health**: Sudden lag spikes indicate producer bursts or consumer failures
- **Alerting**: Automated alerts when lag exceeds thresholds prevent silent data backlogs
- **Cost control**: In cloud environments, persistent lag means overpaying for idle brokers

For a broader look at Kafka infrastructure management, see our [self-hosted Kafka operations guide](../2026-05-10-self-hosted-kafka-operations-management-strimzi-cruise-control-cmak-guide/). For Kafka UI management tools, check our [Kafdrop vs AKHQ vs Redpanda Console comparison](../2026-04-21-kafdrop-vs-akhq-vs-redpanda-console-kafka-ui-management-guide-2026/).

## Comparison Table: Kafka Lag Monitoring Tools

| Feature | Burrow | Xinfra Monitor | Kafka Lag Exporter |
|---------|--------|---------------|-------------------|
| **Language** | Go | Java | Scala / Java |
| **Stars** | 3,954 | 2,063 | 668 |
| **Lag Detection** | ✅ Partition-level | ✅ Consumer group level | ✅ Partition-level |
| **Alerting** | ✅ Email, HTTP notifier | ✅ Email, custom | ❌ (Prometheus only) |
| **Prometheus Metrics** | ✅ Built-in | ✅ Via JMX exporter | ✅ Native |
| **Grafana Dashboards** | ✅ Official | ✅ Community | ✅ Official |
| **Multi-Cluster** | ✅ | ✅ | ❌ (single cluster) |
| **Status Evaluation** | ✅ `StatusEvaluator` | ❌ | ❌ |
| **REST API** | ✅ | ✅ | ✅ Basic |
| **Docker Support** | ✅ docker-compose | ✅ Dockerfile | ✅ Helm chart |
| **Last Updated** | May 2026 | Mar 2025 | Feb 2024 |
| **License** | Apache 2.0 | BSD 2-Clause | Apache 2.0 |

## How Kafka Consumer Lag Works

Consumer lag is calculated for each partition in each consumer group:

```
Consumer Lag = Latest Offset (producer) - Committed Offset (consumer)
```

For example, if a producer has written up to offset 10,000 on partition 0 and the consumer has only committed offset 9,500, the lag is 500 messages. A healthy consumer should maintain near-zero or stable lag.

The challenge is that Kafka's built-in `__consumer_offsets` topic stores committed offsets, but calculating lag requires comparing those offsets against the actual log-end offsets — something Kafka's native tools do not provide in a monitoring-friendly format. Lag monitoring tools bridge this gap.

## Burrow: The Gold Standard for Kafka Lag Monitoring

Burrow, created by LinkedIn's Kafka team, is the most widely deployed open-source Kafka consumer lag monitor. It was designed to handle LinkedIn-scale Kafka deployments with thousands of consumer groups across dozens of clusters.

**Key Features:**
- **StatusEvaluator**: Burrow's signature feature — instead of simple threshold-based alerting, Burrow tracks lag behavior over time and evaluates consumer health. It distinguishes between "lag exists but consumer is catching up" (OK) and "lag is growing uncontrollably" (ERROR).
- **Multi-cluster monitoring**: Monitor all your Kafka clusters from a single Burrow instance
- **HTTP notifier**: Configurable webhook-based alerting for external notification systems
- **Prometheus integration**: Built-in `/metrics` endpoint for Prometheus scraping
- **REST API**: Comprehensive API for integration with custom dashboards and tools

**Docker Compose Deployment:**

```yaml
# docker-compose.yml for Burrow
version: "3.8"
services:
  burrow:
    build:
      context: https://github.com/linkedin/Burrow.git#master
    ports:
      - "8000:8000"
    volumes:
      - "./burrow-config:/etc/burrow"
      - "./burrow-tmp:/var/tmp/burrow"
    restart: always
```

Burrow configuration (`burrow-config/burrow.toml`):

```toml
[general]
logdir = "/var/tmp/burrow"
logconfig = "/etc/burrow/logging.cfg"

[zookeeper]
servers = [ "zookeeper:2181" ]
timeout = 6

[client-profile.default]
client-id = "burrow"
kafka-version = "3.6.0"

[cluster.local]
class-name = "kafka"
servers = [ "kafka:9092" ]
client-profile = "default"
topic-refresh = 300
offset-refresh = 30

[consumer.local]
class-name = "kafka"
cluster = "local"
group-whitelist = ".*"
group-blacklist = "^$"

[httpserver.default]
address = ":8000"

[notifier.default]
class-name = "email"
interval = 60
group-whitelist = ".*"
threshold = 2
template-open = "/etc/burrow/email-template.tmpl"
server = "smtp.example.com"
port = 587
from = "burrow@example.com"
to = "alerts@example.com"
```

Burrow's `StatusEvaluator` is what sets it apart — it tracks lag history and uses a sliding window to determine consumer health, avoiding the false positives that plague simple threshold-based alerting.

## Xinfra Monitor: Cluster Health Beyond Consumer Lag

Xinfra Monitor (formerly Kafka Monitor) provides a broader view of Kafka cluster health. While it monitors consumer lag, it also tracks cluster availability, end-to-end latency, and producer performance.

**Key Features:**
- **End-to-end latency monitoring**: Produces test messages to Kafka and measures total round-trip time
- **Cluster availability**: Continuously verifies that producers and consumers can connect to the cluster
- **Consumer lag monitoring**: Tracks lag across consumer groups with configurable thresholds
- **Multi-cluster**: Monitors multiple Kafka clusters simultaneously
- **JMX metrics**: Exposes metrics via JMX for integration with monitoring systems

**Docker Deployment:**

```yaml
# docker-compose.yml for Xinfra Monitor
services:
  xinfra-monitor:
    image: ghcr.io/linkedin/kafka-monitor:latest
    ports:
      - "8001:8000"
      - "8778:8778"
    volumes:
      - "./config:/opt/kafka-monitor/config"
    environment:
      - JAVA_OPTS=-Xms512m -Xmx1024m
    restart: always
```

Xinfra Monitor's configuration (`config/kafka-monitor.properties`):

```properties
# Cluster configuration
monitor.clusters=production,staging
monitor.cluster.production.zkConnect=zookeeper:2181
monitor.cluster.production.brokers=kafka:9092

# Consumer lag monitoring
monitor.consumer.groups=.*
monitor.consumer.lag.threshold=10000

# End-to-end latency test
monitor.produce.topic=kafka-monitor-test
monitor.produce.interval.seconds=30
monitor.consume.topic=kafka-monitor-test
monitor.consume.interval.seconds=30
```

Xinfra Monitor is the right choice for teams that need comprehensive cluster health monitoring beyond just consumer lag — especially the end-to-end latency testing which verifies the entire producer→broker→consumer pipeline.

## Kafka Lag Exporter: Prometheus-Native Lag Visibility

Kafka Lag Exporter takes a Prometheus-first approach to lag monitoring. It exposes consumer lag metrics directly for Prometheus scraping and includes pre-built Grafana dashboards for visualization.

**Key Features:**
- **Native Prometheus metrics**: Exposes lag, offset, and partition metrics with rich labels
- **Grafana dashboards**: Official pre-configured dashboards for instant visualization
- **Kubernetes-native**: Helm chart available for K8s deployments
- **Lightweight**: Designed to run as a sidecar alongside Prometheus

**Kubernetes Deployment via Helm:**

```yaml
# values.yaml for Kafka Lag Exporter Helm chart
replicaCount: 1
image:
  repository: seglo/kafka-lag-exporter
  tag: 0.9.0

kafkaLagExporter:
  clusters:
    - name: production
      bootstrapBrokers: kafka.production.svc.cluster.local:9092
  watchers:
    production:
      groupWhitelist: [".*"]
      topicBlacklist: ["^_.*"]

prometheus:
  serviceMonitor:
    enabled: true
```

**Docker Standalone Deployment:**

```yaml
# docker-compose.yml for Kafka Lag Exporter
services:
  kafka-lag-exporter:
    image: seglo/kafka-lag-exporter:latest
    ports:
      - "9999:9999"
    volumes:
      - "./application.conf:/opt/docker/conf/application.conf:ro"
    restart: always
```

Configuration (`application.conf`):

```hocon
kafka-lag-exporter {
  clusters = [
    {
      name = "production"
      bootstrap-brokers = "kafka:9092"
      consumer-properties = {
        "security.protocol" = "PLAINTEXT"
      }
    }
  ]
  
  watchers = {
    production = {
      poll-interval = 30 seconds
    }
  }
}
```

Kafka Lag Exporter is ideal for teams already invested in the Prometheus/Grafana observability stack. It does not provide built-in alerting, but Alertmanager rules on the Prometheus metrics cover this gap.

## Choosing the Right Lag Monitoring Solution

| Use Case | Recommendation | Why |
|----------|---------------|-----|
| Production Kafka at scale | **Burrow** | StatusEvaluator, battle-tested at LinkedIn scale |
| Comprehensive cluster health | **Xinfra Monitor** | End-to-end latency + availability + lag |
| Prometheus/Grafana stack | **Kafka Lag Exporter** | Native Prometheus metrics, official dashboards |
| Kubernetes-native deployment | **Kafka Lag Exporter** | Helm chart, ServiceMonitor |
| Minimal operational overhead | **Burrow** | Single Go binary, simple config |

For most teams running Kafka in production, Burrow is the recommended starting point. Its StatusEvaluator eliminates the primary pain point of lag monitoring — false positives from naive threshold alerting. Once you have Burrow in place, add Kafka Lag Exporter if you need richer Prometheus integration and pre-built Grafana dashboards.

## Monitoring Architecture

A complete Kafka monitoring stack combines lag monitoring with broker-level observability:

```
┌─────────┐    ┌──────────┐    ┌─────────────┐
│ Burrow  │───▶│ Alerting │   │ Kafka Lag    │
│ (Lag)   │    │ (Email/  │   │ Exporter     │──▶ Prometheus ──▶ Grafana
└─────────┘    │ Webhook) │   └─────────────┘
               └──────────┘
┌──────────┐
│ Xinfra   │───▶ JMX ──▶ Prometheus
│ Monitor  │    Metrics
└──────────┘
```

For a complete view, pair lag monitoring with [self-hosted metrics storage solutions](../2026-04-24-victoriametrics-vs-thanos-vs-cortex-self-hosted-metrics-scaling-guide-2026/) for long-term metric retention and trend analysis.

## FAQ

### What is a healthy consumer lag?

Zero lag is ideal but not always realistic. A "healthy" consumer has stable lag — the gap between producer offset and consumer offset remains constant or decreasing. Burrow's StatusEvaluator considers a consumer healthy as long as it is making progress (committing offsets). A lag of 1,000 messages that stays at 1,000 is fine. A lag growing from 100 to 1,000 to 10,000 means the consumer is falling behind.

### How does Burrow's StatusEvaluator differ from simple threshold alerts?

Threshold alerts fire when lag exceeds a fixed number (e.g., alert if lag > 10,000). This generates false positives during normal traffic spikes where the consumer catches up after a brief lag. Burrow's StatusEvaluator tracks lag over a sliding window and only alerts when the consumer has stopped making progress entirely — distinguishing between "temporarily behind" and "broken."

### Can Burrow monitor multiple Kafka clusters?

Yes. Burrow's configuration supports multiple `[cluster.*]` and `[consumer.*]` sections, allowing a single Burrow instance to monitor consumer groups across dozens of Kafka clusters. This is how LinkedIn uses it internally.

### Does Kafka Lag Exporter require Prometheus?

Yes. Kafka Lag Exporter is designed as a Prometheus metrics exporter. It exposes lag data via an HTTP endpoint that Prometheus scrapes. Without Prometheus (or a compatible metrics collector), the exported metrics have no consumer. Use Burrow or Xinfra Monitor if you need standalone alerting.

### How do I set up alerting for consumer lag?

With Burrow: configure the `[notifier]` section with email or HTTP webhook settings. Burrow sends alerts when the StatusEvaluator detects an ERROR state. With Xinfra Monitor: configure email notifications or integrate with your existing monitoring stack via JMX. With Kafka Lag Exporter: create Alertmanager rules in Prometheus that fire when `kafka_consumer_group_lag` exceeds your thresholds.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kafka Consumer Lag Monitoring: Burrow vs Xinfra Monitor vs Lag Exporter Guide 2026",
  "description": "Compare self-hosted Kafka consumer lag monitoring tools. Deep dive into Burrow, Xinfra Monitor, and Kafka Lag Exporter with Docker Compose deployment guides, comparison tables, and monitoring architecture best practices.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
