---
title: "Self-Hosted Time-Series Databases for IoT & Telemetry: KairosDB vs OpenTSDB"
date: "2026-06-04"
tags: ["time-series", "database", "iot", "telemetry", "monitoring", "self-hosted", "devops"]
draft: false
---

## Introduction

When deploying Internet of Things (IoT) sensors, industrial telemetry systems, or large-scale monitoring infrastructure, you need a database purpose-built for time-stamped data. Traditional relational databases struggle with the write throughput and query patterns of time-series workloads — millions of data points per second, range queries spanning months of data, and automatic downsampling for long-term storage.

Two battle-tested open-source time-series databases have been serving production workloads for over a decade: **KairosDB** and **OpenTSDB**. Both are designed for high-ingest, scalable time-series storage, but they take fundamentally different architectural approaches.

KairosDB started as a fork of OpenTSDB in 2013, replacing the HBase backend with Apache Cassandra for better write scalability and operational simplicity. OpenTSDB, originally developed at StumbleUpon and later maintained by the open-source community, remains one of the most widely deployed time-series databases in enterprise environments with its mature HBase-based architecture.

In this guide, we compare KairosDB and OpenTSDB for self-hosted time-series workloads, covering architecture, deployment, query capabilities, and operational considerations.

## Architecture Comparison

### KairosDB

KairosDB uses Apache Cassandra as its primary storage backend, leveraging Cassandra's distributed architecture for horizontal scalability. It can also use H2 for single-node deployments. Key architectural features include:

- **Cassandra-backed storage**: Automatic data distribution across nodes with tunable consistency
- **REST API**: Full HTTP API for data ingestion and querying
- **Tag-based data model**: Each data point is identified by a metric name, tags (key-value pairs), timestamp, and value
- **Built-in aggregators**: Min, max, sum, average, standard deviation, percentile calculations
- **Roll-up and downsampling**: Automatic data aggregation for long-term retention
- **Plugin framework**: Custom data point listeners for integration with external systems

### OpenTSDB

OpenTSDB uses Apache HBase as its storage backend, which runs on top of HDFS. This ties it to the Hadoop ecosystem but provides proven scalability for petabyte-scale deployments:

- **HBase on HDFS**: Row-key design optimizes time-range scans
- **Telnet-style and HTTP APIs**: Dual ingestion interfaces
- **UID table compression**: Maps metric names and tag values to compact unique identifiers
- **Built-in downsampling**: Configurable roll-up policies for data retention
- **Expression-based querying**: Complex time-series arithmetic and grouping
- **Annotation support**: Attach metadata events to specific timestamps

## Feature Comparison

| Feature | KairosDB | OpenTSDB |
|---------|----------|----------|
| **Storage Backend** | Apache Cassandra / H2 | Apache HBase (HDFS) |
| **GitHub Stars** | 1,760+ | 5,070+ |
| **Last Updated** | March 2026 | December 2024 |
| **Data Model** | Metric + Tags + Timestamp + Value | Metric + Tags + Timestamp + Value |
| **API** | REST (HTTP/JSON) | HTTP + Telnet |
| **Query Language** | JSON-based query DSL | TSD query expressions |
| **Downsampling** | Built-in roll-ups | Built-in aggregators |
| **Clustering** | Via Cassandra ring | Via HBase regions |
| **Aggregation** | Min, Max, Sum, Avg, StdDev, Percentile | Min, Max, Sum, Avg, Rate, Percentile |
| **Authentication** | Basic auth + API keys | None (relies on network security) |
| **Monitoring Integration** | Graphite protocol, direct REST | Grafana datasource, TCollector |
| **License** | Apache 2.0 | LGPLv2.1+ / GPLv3+ |

## Docker Compose Deployment

### KairosDB with Cassandra

```yaml
version: "3.8"
services:
  cassandra:
    image: cassandra:4.1
    container_name: kairosdb-cassandra
    environment:
      - CASSANDRA_CLUSTER_NAME=KairosDB
      - CASSANDRA_DC=datacenter1
    volumes:
      - cassandra_data:/var/lib/cassandra
    healthcheck:
      test: ["CMD", "cqlsh", "-e", "describe keyspaces"]
      interval: 30s
      timeout: 10s
      retries: 5

  kairosdb:
    image: kairosdb/kairosdb:latest
    container_name: kairosdb
    ports:
      - "8080:8080"
    environment:
      - KAIROSDB_JETTY_PORT=8080
      - KAIROSDB_DATASTORE=cassandra
      - KAIROSDB_CASSANDRA_HOST_LIST=cassandra:9042
    volumes:
      - kairosdb_data:/opt/kairosdb/data
    depends_on:
      cassandra:
        condition: service_healthy

volumes:
  cassandra_data:
  kairosdb_data:
```

### OpenTSDB with HBase

```yaml
version: "3.8"
services:
  hbase:
    image: harisekhon/hbase:2.5
    container_name: opentsdb-hbase
    environment:
      - HBASE_MASTER_PORT=16000
      - HBASE_REGIONSERVER_PORT=16020
    volumes:
      - hbase_data:/hbase-data

  opentsdb:
    image: opentsdb/opentsdb:latest
    container_name: opentsdb
    ports:
      - "4242:4242"
    environment:
      - TSDB_PORT=4242
      - HBASE_ZOOKEEPER_QUORUM=hbase
    volumes:
      - opentsdb_cache:/tmp/opentsdb
    depends_on:
      - hbase

volumes:
  hbase_data:
  opentsdb_cache:
```

### Quick Ingestion Test

Once deployed, test data ingestion for KairosDB:

```bash
curl -X POST http://localhost:8080/api/v1/datapoints \
  -H "Content-Type: application/json" \
  -d '[{
    "name": "temperature",
    "tags": {"sensor": "outdoor", "location": "rooftop"},
    "datapoints": [[1717516800000, 23.5], [1717516860000, 23.7]]
  }]'
```

For OpenTSDB, use the telnet-style API:

```bash
echo "put temperature 1717516800 23.5 sensor=outdoor location=rooftop" | nc localhost 4242
```

## Why Self-Host Your Time-Series Database?

Self-hosting a time-series database gives you complete control over your telemetry and IoT data pipeline. Cloud-hosted time-series services like AWS Timestream, Google Cloud Monitoring, or InfluxDB Cloud charge per data point ingested, per query executed, and per GB stored — costs that scale linearly with your sensor fleet. A modest deployment of 500 IoT sensors generating one data point per second can easily exceed $1,000/month in cloud costs.

Data sovereignty is equally critical for industrial and infrastructure monitoring. When your time-series data represents factory floor operations, building management systems, or power grid telemetry, sending every data point to a third-party cloud introduces compliance risks and latency. Self-hosted KairosDB or OpenTSDB keeps all data on-premises, under your security controls, with sub-millisecond query latency.

Vendor independence is the third pillar. With open-source time-series databases, you are not locked into a specific cloud provider's API, pricing model, or deprecation schedule. Your data lives in standard formats (Cassandra SSTables or HBase HFiles), portable across any infrastructure — bare metal, VMs, or Kubernetes clusters. If you are already running monitoring infrastructure like Prometheus, check out our guide on [self-hosted Prometheus long-term storage](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/).

For infrastructure monitoring dashboards, pair your time-series database with a visualization layer — see our [self-hosted infrastructure monitoring comparison](../2026-04-25-nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/) for the full stack. If you need a lighter-weight time-series solution with a built-in query language, our [self-hosted time-series database comparison](../2026-04-27-greptimedb-vs-influxdb-vs-victoriametrics-self-hosted-time-series-database-guide-2026/) covers GreptimeDB, InfluxDB, and VictoriaMetrics.

## Operational Considerations for Production Deployments

Running a time-series database in production requires more than just starting containers. Here are the operational aspects you need to plan for:

### Backup and Recovery

KairosDB stores data in Cassandra, which supports snapshot-based backups via `nodetool snapshot`. You can automate daily snapshots with a cron job and ship them to offsite storage. OpenTSDB data lives in HBase, which uses HDFS snapshots. Both approaches require testing your restore procedure — a backup you have not restored is not a backup. Budget at least 4 hours to validate your restore workflow before going to production.

### Monitoring the Database Itself

Your time-series database should be monitored like any other infrastructure component. For KairosDB, expose JMX metrics to Prometheus using the JMX exporter. For OpenTSDB, enable the built-in stats endpoint at `/api/stats` and scrape it with your monitoring stack. Track write latency (P99 should stay under 100ms for most workloads), compaction queue depth, and disk usage growth rate. Set alerts for when storage exceeds 80% capacity.

### Capacity Planning

Estimate your storage needs using this formula: `daily_ingestion = data_points_per_second × seconds_per_day × bytes_per_datapoint`. KairosDB with Cassandra compression typically uses 12-20 bytes per data point. OpenTSDB with HBase compression uses 8-15 bytes per data point. A modest IoT deployment of 10,000 data points per second generates approximately 10-17 GB of compressed data per day. Plan your retention policy accordingly — keep high-resolution data for 30 days, 5-minute roll-ups for 6 months, and hourly roll-ups indefinitely.

### Security Hardening

Neither KairosDB nor OpenTSDB includes built-in authentication beyond basic HTTP auth. In production, always place your time-series database behind a reverse proxy with TLS termination and IP allowlisting. For KairosDB, use Nginx with `auth_basic` and `proxy_pass`. For OpenTSDB, restrict the telnet API port (4242) to localhost only and expose only the HTTP API through an authenticated proxy. If your deployment spans multiple data centers, use WireGuard or Tailscale to encrypt inter-node traffic between Cassandra or HBase nodes.

## Choosing Between KairosDB and OpenTSDB

**Choose KairosDB if:**
- You already run Cassandra or prefer its operational model over HBase
- You want a simpler deployment with fewer moving parts
- You need a pure REST/JSON API for modern toolchain integration
- Your team has more experience with CQL than HBase

**Choose OpenTSDB if:**
- You are already invested in the Hadoop/HBase ecosystem
- You need the maturity of a 12+ year production-tested codebase
- You require the telnet-style API for legacy collector compatibility
- You are deploying at petabyte scale with existing HDFS infrastructure

Both tools are mature, proven at scale, and well-suited for self-hosted IoT and telemetry workloads. Your choice should align with your existing infrastructure stack — Cassandra vs HBase is often the deciding factor.

## FAQ

### Can KairosDB and OpenTSDB handle millions of data points per second?

Yes, both are designed for high-throughput ingestion. KairosDB scales horizontally by adding more Cassandra nodes — each node can handle ~50,000 writes/second, so a 10-node cluster reaches 500,000 writes/second. OpenTSDB scales with HBase regions and can reach similar throughput on adequately provisioned hardware. For extreme write loads, consider pre-splitting HBase regions or configuring Cassandra's write path for optimal performance.

### Do I need to run a full Hadoop cluster for OpenTSDB?

OpenTSDB requires HBase, which requires HDFS and ZooKeeper. For production deployments, this means at least 5 nodes (3 ZooKeeper, 2+ HBase RegionServers). However, for development and small-scale deployments, the Docker Compose configuration above runs a single-node HBase instance sufficient for testing and low-volume production use (up to ~10,000 data points/second).

### How do these compare to InfluxDB or TimescaleDB?

InfluxDB and TimescaleDB are more modern time-series databases with built-in SQL-like query languages (InfluxQL/Flux and full PostgreSQL SQL, respectively). They are generally easier to deploy and operate than KairosDB or OpenTSDB. However, KairosDB and OpenTSDB excel in environments already running Cassandra or HBase, where adding a time-series capability without introducing a new database system is the primary requirement. See our [time-series database comparison guide](../2026-04-27-greptimedb-vs-influxdb-vs-victoriametrics-self-hosted-time-series-database-guide-2026/) for alternatives.

### Is OpenTSDB still actively maintained?

The main OpenTSDB repository saw its last commit in December 2024, indicating the project is in maintenance mode. The 5,070+ GitHub stars and thousands of production deployments mean the codebase is stable and battle-tested, but new features are unlikely. KairosDB, with its most recent update in March 2026, has more active development.

### Can I migrate data between KairosDB and OpenTSDB?

There is no built-in migration tool between the two, as they use fundamentally different storage backends (Cassandra vs HBase). Migration requires exporting data via each system's API, transforming to the target format, and re-importing. For large datasets, consider running both systems in parallel during a transition period rather than attempting a bulk migration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Time-Series Databases for IoT & Telemetry: KairosDB vs OpenTSDB",
  "description": "Comprehensive comparison of KairosDB and OpenTSDB for self-hosted IoT and telemetry data storage. Covers architecture, Docker Compose deployment, performance, and migration considerations.",
  "datePublished": "2026-06-04",
  "dateModified": "2026-06-04",
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
