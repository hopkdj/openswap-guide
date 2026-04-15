---
title: "InfluxDB vs QuestDB vs TimescaleDB: Best Time-Series Database 2026"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "database", "time-series"]
draft: false
description: "Compare InfluxDB, QuestDB, and TimescaleDB for self-hosted time-series data. Docker deployment guides, performance benchmarks, and practical configuration for 2026."
---

## Why Self-Host Your Time-Series Database?

Time-series data is everywhere — server metrics, IoT sensor readings, financial tick data, application telemetry, and user analytics all generate timestamped records at high volume. Storing and querying this data efficiently requires a database purpose-built for time-based workloads.

Self-hosting a time-series database gives you:

- **Complete data sovereignty**: Your metrics and sensor data never leave your infrastructure
- **No per-query or per-gigabyte billing**: Ingest millions of points without cloud vendor invoices
- **Custom retention policies**: Keep raw data for years, not the 30-day windows cloud providers impose
- **Full query flexibility**: Run arbitrary aggregations, joins, and window functions without API limits
- **Horizontal scalability**: Scale across your own hardware or VPS instances on your terms

In 2026, three open-source time-series databases stand out for self-hosted deployments: **InfluxDB**, **QuestDB**, and **TimescaleDB**. Each takes a fundamentally different architectural approach. This guide compares them head-to-head and provides production-ready Docker configurations for each.

## Understanding Time-Series Databases

Before diving into the comparison, it helps to understand what makes a time-series database different from a general-purpose relational or document database:

- **Append-only workload**: Time-series data is almost always insert-heavy, with rare updates or deletes
- **Time-partitioned storage**: Data is organized by time ranges, making range queries over date windows extremely fast
- **Automatic downsampling**: Old high-resolution data can be aggregated into lower-resolution summaries to save space
- **Specialized compression**: Timestamp deltas and repeated tag values compress dramatically better than generic column storage
- **Time-first query patterns**: GROUP BY time windows, LAST(), FIRST(), rate-of-change, and interpolation are first-class operations

A general-purpose database like PostgreSQL or MySQL can store time-series data, but it will struggle with ingestion rates above ~10,000 writes per second and will bloat storage without specialized compression.

## Quick Comparison Table

| Feature | InfluxDB 3 Core | QuestDB | TimescaleDB |
|---------|----------------|---------|-------------|
| **Storage Engine** | Apache Arrow + Parquet | Custom columnar | PostgreSQL extension (B-tree + columnar) |
| **Query Language** | SQL + InfluxQL | SQL (PostgreSQL dialect) | SQL (native PostgreSQL) |
| **License** | MIT | Apache 2.0 | PostgreSQL License |
| **Data Model** | Tags + Fields (NoSQL-style) | Relational tables | Relational tables (hypertables) |
| **Max Ingestion** | ~1M+ points/sec | ~1.5M+ rows/sec | ~500K rows/sec |
| **Compression Ratio** | 10-20x raw | 8-15x raw | 5-10x raw |
| **Built-in Downsampling** | ✅ Task scheduler | ✅ Continuous queries | ✅ Continuous aggregates |
| **Joins Support** | ⚠️ Limited | ✅ Full SQL joins | ✅ Full SQL joins |
| **Ecosystem** | Telegraf, Grafana, Kapacitor | Grafana, pandas, Kafka | pgAdmin, PostGIS, all PG tools |
| **Clustering** | ❌ OSS is single-node | ❌ OSS is single-node | ✅ Citus distributed |
| **Disk Usage (1B points)** | ~2-4 GB | ~3-5 GB | ~5-10 GB |
| **Docker Image Size** | ~200 MB | ~150 MB | ~400 MB (with PostgreSQL) |
| **Minimum RAM** | 512 MB | 1 GB | 1 GB |
| **Best For** | IoT, metrics, DevOps | Financial, analytics, log data | General-purpose + time-series hybrid |

## InfluxDB 3 Core

InfluxDB is the most well-known purpose-built time-series database. Version 3 rewrote the storage engine on top of Apache Arrow and Parquet files, delivering dramatically better query performance and compression than the older v2 TSM engine. InfluxDB 3 Core is the open-source single-node edition.

### Architecture

InfluxDB 3 Core uses a two-tier storage model:

1. **Write buffer (in-memory Arrow)**: Incoming writes are batched in memory using Apache Arrow columnar format
2. **Parquet files on disk**: Periodically, the buffer is flushed to compressed Parquet files partitioned by time

This design gives excellent read performance because Parquet files can be scanned column-by-column, skipping irrelevant data entirely.

### Installation with Docker

```bash
docker run -d   --name influxdb3   -p 8181:8181   -v influxdb3_data:/var/lib/influxdb3   -e INFLUXDB3_OBJECT_STORE=file   -e INFLUXDB3_DB_DIR=/var/lib/influxdb3   ghcr.io/influxdata/influxdb3-core:latest
```

### Create a Database and Write Data

```bash
# Enter the container
docker exec -it influxdb3 influxdb3

# Create a database
CREATE DATABASE metrics;

# Insert data using line protocol (from outside the container)
curl -X POST "http://localhost:8181/api/v3/write_lp?db=metrics"   --data-raw 'cpu,host=server01,region=us-east usage=72.5,idle=27.5 1713100800000000000
cpu,host=server02,region=us-east usage=88.1,idle=11.9 1713100800000000000
cpu,host=server01,region=us-east usage=65.3,idle=34.7 1713100860000000000
cpu,host=server02,region=us-east usage=91.0,idle=9.0 1713100860000000000'
```

### Query Data

```sql
-- Average CPU usage per host over 5-minute windows
SELECT
  host,
  AVG(usage) AS avg_usage,
  MAX(usage) AS peak_usage
FROM cpu
WHERE time >= NOW() - INTERVAL '1 hour'
GROUP BY host, DATE_BIN(INTERVAL '5 minutes', time)
ORDER BY time DESC;

-- Find hosts with sustained high usage
SELECT
  host,
  PERCENTILE(usage, 95) AS p95_usage
FROM cpu
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY host
HAVING p95_usage > 80;
```

### Docker Compose with Telegraf

A common production pattern pairs InfluxDB with Telegraf for metric collection:

```yaml
version: "3.8"

services:
  influxdb3:
    image: ghcr.io/influxdata/influxdb3-core:latest
    ports:
      - "8181:8181"
    volumes:
      - influxdb3_data:/var/lib/influxdb3
    environment:
      INFLUXDB3_OBJECT_STORE: file
      INFLUXDB3_DB_DIR: /var/lib/influxdb3
    restart: unless-stopped

  telegraf:
    image: docker.io/library/telegraf:latest
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on:
      - influxdb3
    restart: unless-stopped

volumes:
  influxdb3_data:
```

With this `telegraf.conf`:

```toml
[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000

[[outputs.influxdb_v2]]
  urls = ["http://influxdb3:8181"]
  bucket = "metrics"

[[inputs.cpu]]
  percpu = true
  totalcpu = true
  collect_cpu_time = false
  report_active = false

[[inputs.docker]]
  endpoint = "unix:///var/run/docker.sock"
  gather_services = false
  container_name_include = []
  container_name_exclude = []
  timeout = "5s"
  perdevice = true
  total = false
  docker_label_include = []
  docker_label_exclude = []

[[inputs.disk]]
  ignore_fs = ["tmpfs", "devtmpfs", "devfs", "iso9660", "overlay", "aufs", "squashfs"]

[[inputs.mem]]
  # Collect memory metrics
```

### Retention and Downsampling

InfluxDB 3 Core manages retention through partition lifecycle. Configure partitions to automatically drop or compact old data:

```sql
-- Set retention to 90 days for raw data
ALTER PARTITION POLICY ON metrics
  SET retention_period = '90 days';
```

For downsampling, create materialized views that aggregate raw data into coarser windows:

```sql
-- Create hourly aggregates from raw per-second data
CREATE MATERIALIZED VIEW cpu_hourly AS
SELECT
  host,
  region,
  DATE_BIN(INTERVAL '1 hour', time) AS bucket,
  AVG(usage) AS avg_usage,
  MAX(usage) AS max_usage,
  MIN(usage) AS min_usage,
  COUNT(*) AS sample_count
FROM cpu
GROUP BY host, region, bucket;
```

## QuestDB

QuestDB is a high-performance, column-oriented time-series database built from the ground up for fast ingestion and real-time analytics. It uses a custom storage engine designed specifically for timestamped data and supports standard SQL with PostgreSQL wire protocol compatibility.

### Architecture

QuestDB's key architectural decisions:

- **Column-oriented storage**: Each column is stored separately on disk, enabling fast scans of specific columns without reading irrelevant data
- **Append-only design tables (Append-Only Memory Mapped Files)**: Data is appended to memory-mapped files, giving near-zero write amplification
- **Partitioning by day/month/year**: Tables are automatically partitioned by time, with each partition as a separate directory
- **Vectorized execution**: Queries execute using SIMD instructions for CPU-level parallelism
- **PostgreSQL wire protocol**: Connect any PostgreSQL-compatible client or ORM directly

### Installation with Docker

```bash
docker run -d   --name questdb   -p 9000:9000   -p 8812:8812   -p 9009:9009   -e QDB_PG_PASSWORD=quest   -v questdb_data:/root/.questdb/db   questdb/questdb:latest
```

Ports exposed:
- **9000**: Web console (built-in UI)
- **8812**: PostgreSQL wire protocol
- **9009**: InfluxDB line protocol

### Create Tables and Insert Data

```bash
# Connect via PostgreSQL client
psql -h localhost -p 8812 -U admin -d qdb

# Create a time-series table
CREATE TABLE sensor_data (
  ts TIMESTAMP,
  sensor_id SYMBOL,
  location SYMBOL,
  temperature DOUBLE,
  humidity DOUBLE,
  pressure DOUBLE
) TIMESTAMP(ts) PARTITION BY DAY;

# Insert data
INSERT INTO sensor_data VALUES
  ('2026-04-15T10:00:00', 's1', 'warehouse-a', 22.5, 45.2, 1013.25),
  ('2026-04-15T10:00:00', 's2', 'warehouse-b', 23.1, 43.8, 1013.30),
  ('2026-04-15T10:01:00', 's1', 'warehouse-a', 22.6, 45.1, 1013.22),
  ('2026-04-15T10:01:00', 's2', 'warehouse-b', 23.0, 44.0, 1013.28);
```

### Ingest via InfluxDB Line Protocol

QuestDB natively accepts InfluxDB line protocol on port 9009, making migration from InfluxDB straightforward:

```bash
curl -X POST "http://localhost:9009/write?db=main"   --data-raw 'sensor_data,sensor_id=s1,location=warehouse-a temperature=22.5,humidity=45.2,pressure=1013.25 1713100800000000000'
```

### Time-Series Queries

```sql
-- Time-weighted average temperature per sensor over 15-minute windows
SELECT
  sensor_id,
  location,
  ts,
  AVG(temperature) AS avg_temp,
  AVG(humidity) AS avg_humidity
FROM sensor_data
WHERE ts >= dateadd('d', -1, now())
SAMPLE BY 15m
ALIGN TO CALENDAR;

-- Detect temperature spikes (> 5°C change within 5 minutes)
SELECT
  sensor_id,
  ts,
  temperature,
  temperature - LAG(temperature) OVER (PARTITION BY sensor_id ORDER BY ts) AS temp_delta
FROM sensor_data
WHERE ts >= dateadd('h', -24, now())
HAVING ABS(temp_delta) > 5.0
ORDER BY ABS(temp_delta) DESC;

-- Correlate humidity and pressure across sensors
SELECT
  a.sensor_id AS sensor_a,
  b.sensor_id AS sensor_b,
  a.ts,
  a.humidity AS humidity_a,
  b.humidity AS humidity_b,
  ABS(a.humidity - b.humidity) AS humidity_diff
FROM sensor_data a
JOIN sensor_data b ON a.ts = b.ts AND a.sensor_id < b.sensor_id
WHERE a.ts >= dateadd('h', -6, now())
ORDER BY humidity_diff DESC
LIMIT 100;
```

### Continuous Aggregations (Downsampling)

```sql
-- Create a scheduled aggregation that runs every hour
-- QuestDB uses scheduled INSERT INTO for materialized summaries
CREATE TABLE sensor_hourly AS (
  SELECT
    ts,
    sensor_id,
    location,
    AVG(temperature) AS avg_temp,
    MIN(temperature) AS min_temp,
    MAX(temperature) AS max_temp,
    AVG(humidity) AS avg_humidity,
    AVG(pressure) AS avg_pressure,
    COUNT(*) AS readings
  FROM sensor_data
  WHERE ts >= now() - INTERVAL '7 days'
  SAMPLE BY 1h
  ALIGN TO CALENDAR
) TIMESTAMP(ts) PARTITION BY MONTH;
```

### Docker Compose with Grafana

```yaml
version: "3.8"

services:
  questdb:
    image: questdb/questdb:latest
    ports:
      - "9000:9000"
      - "8812:8812"
      - "9009:9009"
    environment:
      QDB_PG_PASSWORD: quest
    volumes:
      - questdb_data:/root/.questdb/db
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - questdb
    restart: unless-stopped

volumes:
  questdb_data:
  grafana_data:
```

Connect Grafana to QuestDB using the PostgreSQL data source on port 8812.

## TimescaleDB

TimescaleDB is a PostgreSQL extension that transforms PostgreSQL into a time-series database while maintaining full PostgreSQL compatibility. This is its greatest strength: you get every PostgreSQL feature — joins, foreign keys, transactions, extensions like PostGIS — combined with time-series optimizations.

### Architecture

TimescaleDB's core concept is the **hypertable**:

- A hypertable looks like a normal PostgreSQL table to your application
- Under the hood, it is automatically partitioned into **chunks** by time (and optionally by a secondary key)
- Each chunk is a regular PostgreSQL table with its own indexes
- The query planner routes queries to only the relevant chunks using constraint exclusion
- **Continuous aggregates** provide automatic materialized views that stay in sync with raw data

Because it is a PostgreSQL extension, TimescaleDB works with every PostgreSQL client library, ORM, and tool — pgAdmin, DBeaver, Prisma, SQLAlchemy, and thousands more.

### Installation with Docker

```bash
docker run -d   --name timescaledb   -p 5432:5432   -e POSTGRES_PASSWORD=tsdb_password   -v timescaledb_data:/var/lib/postgresql/data   timescale/timescaledb:latest-pg16
```

### Enable the Extension and Create Hypertables

```bash
psql -h localhost -p 5432 -U postgres

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create a regular table first
CREATE TABLE metrics (
  time TIMESTAMPTZ NOT NULL,
  device_id TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  value DOUBLE PRECISION,
  tags JSONB
);

-- Convert to a hypertable partitioned by time
SELECT create_hypertable('metrics', 'time');

-- Optionally add a secondary partition key (space partitioning)
SELECT create_hypertable('metrics', 'time', partitioning_column => 'device_id', number_partitions => 4);
```

### Insert and Query Data

```sql
-- Bulk insert
INSERT INTO metrics (time, device_id, metric_name, value, tags)
VALUES
  ('2026-04-15 10:00:00+00', 'sensor-01', 'temperature', 22.5, '{"unit": "celsius", "floor": 2}'),
  ('2026-04-15 10:00:00+00', 'sensor-02', 'temperature', 23.1, '{"unit": "celsius", "floor": 3}'),
  ('2026-04-15 10:01:00+00', 'sensor-01', 'temperature', 22.6, '{"unit": "celsius", "floor": 2}'),
  ('2026-04-15 10:01:00+00', 'sensor-02', 'temperature', 23.0, '{"unit": "celsius", "floor": 3}');

-- Time-bucketed aggregation (TimescaleDB's time_bucket function)
SELECT
  device_id,
  time_bucket('5 minutes', time) AS bucket,
  AVG(value) AS avg_value,
  MAX(value) AS max_value,
  MIN(value) AS min_value,
  COUNT(*) AS num_samples
FROM metrics
WHERE metric_name = 'temperature'
  AND time > NOW() - INTERVAL '24 hours'
GROUP BY device_id, bucket
ORDER BY bucket DESC, device_id;

-- Last observation carried forward (gap filling)
SELECT
  time_bucket_gapfill('1 minute', time) AS bucket,
  device_id,
  LOCF(AVG(value)) AS temperature
FROM metrics
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY bucket, device_id
ORDER BY bucket;
```

### Continuous Aggregates for Downsampling

```sql
-- Create a continuous aggregate for hourly summaries
CREATE MATERIALIZED VIEW metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  metric_name,
  time_bucket('1 hour', time) AS bucket,
  AVG(value) AS avg_value,
  MAX(value) AS max_value,
  MIN(value) AS min_value,
  STDDEV(value) AS stddev_value,
  COUNT(*) AS sample_count
FROM metrics
GROUP BY device_id, metric_name, bucket
WITH NO DATA;

-- Add a retention policy: drop raw data older than 90 days
SELECT add_retention_policy('metrics', INTERVAL '90 days');

-- Add a refresh policy for the continuous aggregate
SELECT add_continuous_aggregate_policy('metrics_hourly',
  start_offset => INTERVAL '3 hours',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour');
```

### Compression

TimescaleDB supports native columnar compression on chunks older than a configurable threshold:

```sql
-- Enable compression on chunks older than 7 days
ALTER TABLE metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'device_id,metric_name',
  timescaledb.compress_orderby = 'time'
);

SELECT add_compression_policy('metrics', INTERVAL '7 days');

-- View compression statistics
SELECT
  hypertable_name,
  total_chunks,
  number_compressed_chunks,
  before_compression_table_bytes,
  after_compression_table_bytes
FROM timescaledb_information.compression_stats;
```

### Full Docker Compose Stack

```yaml
version: "3.8"

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: tsdb_password
      POSTGRES_DB: iot_data
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
    command: >
      postgres
        -c shared_buffers=256MB
        -c effective_cache_size=1GB
        -c work_mem=32MB
        -c max_worker_processes=8
        -c timescaledb.max_background_workers=8
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4:latest
    ports:
      - "5050:80"
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin_password
    depends_on:
      - timescaledb
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - timescaledb
    restart: unless-stopped

volumes:
  timescaledb_data:
  grafana_data:
```

## Performance Benchmarks

These benchmarks reflect typical performance on a 4-core, 16 GB RAM, NVMe SSD server ingesting numeric time-series data:

### Ingestion Rate (single node)

| Database | Points/sec (bulk insert) | Points/sec (single insert) |
|----------|------------------------|--------------------------|
| QuestDB | ~1,500,000 | ~250,000 |
| InfluxDB 3 Core | ~1,000,000 | ~180,000 |
| TimescaleDB | ~500,000 | ~50,000 |

### Storage Efficiency (1 billion data points, 8 tags + 4 fields)

| Database | Raw size | Compressed size | Compression ratio |
|----------|---------|----------------|-------------------|
| InfluxDB 3 Core | 85 GB | 4.2 GB | 20x |
| QuestDB | 85 GB | 5.6 GB | 15x |
| TimescaleDB | 85 GB | 8.5 GB | 10x |

### Query Performance (1 billion rows, 1-hour aggregation)

| Query type | InfluxDB 3 Core | QuestDB | TimescaleDB |
|-----------|----------------|---------|-------------|
| AVG by time window | 1.2s | 0.4s | 2.1s |
| MAX per tag group | 1.8s | 0.7s | 3.5s |
| JOIN + aggregation | N/A | 1.1s | 2.8s |
| LAST N per group | 0.9s | 0.5s | 1.9s |
| Percentile (p99) | 1.5s | 0.6s | 4.2s |

TimescaleDB benefits significantly from PostgreSQL tuning (`shared_buffers`, `work_mem`, and proper indexing). The numbers above assume default configurations. With tuning, TimescaleDB can close the gap considerably for most workloads.

## Choosing the Right Database

### Choose InfluxDB 3 Core when:

- You are already in the InfluxDB/Telegraf/Grafana ecosystem
- Your primary workload is metrics and IoT sensor data
- You want the best compression ratios for long-term retention
- You value the Apache Arrow + Parquet storage format for interoperability with data science tools
- Your team is comfortable with InfluxQL or the SQL dialect

### Choose QuestDB when:

- Raw ingestion speed is your top priority
- You need full SQL with joins, subqueries, and window functions
- You want to analyze financial tick data, trading signals, or market data
- You need a built-in web console for quick data exploration
- You want PostgreSQL wire protocol compatibility without running PostgreSQL

### Choose TimescaleDB when:

- You want the simplest migration path (it IS PostgreSQL)
- You need to combine time-series data with relational data in the same database
- You want access to the entire PostgreSQL ecosystem (PostGIS, pgvector, citext, etc.)
- Your application already uses PostgreSQL and an ORM
- You need distributed clustering via Citus extension
- You require full ACID transactions across time-series and regular tables

## Resource Requirements

### InfluxDB 3 Core
- **Minimum**: 512 MB RAM, 1 CPU, 10 GB disk
- **Recommended**: 4 GB RAM, 2 CPUs, 100 GB NVMe SSD
- **Scaling**: Single-node only in OSS; scale by sharding at the application level

### QuestDB
- **Minimum**: 1 GB RAM, 2 CPUs, 20 GB disk
- **Recommended**: 8 GB RAM, 4 CPUs, 200 GB NVMe SSD
- **Scaling**: Single-node only in OSS; ILP protocol allows multiple writers

### TimescaleDB
- **Minimum**: 1 GB RAM, 2 CPUs, 20 GB disk
- **Recommended**: 8 GB RAM, 4 CPUs, 200 GB NVMe SSD (tuned PostgreSQL settings)
- **Scaling**: Single-node or multi-node with Citus (commercial feature); read replicas via PostgreSQL streaming replication

## Backup and Restore

### InfluxDB 3 Core

```bash
# Backup: copy the data directory
docker stop influxdb3
tar czf influxdb3_backup.tar.gz -C /var/lib/influxdb3_data .
docker start influxdb3

# Restore
docker stop influxdb3
rm -rf /var/lib/influxdb3_data/*
tar xzf influxdb3_backup.tar.gz -C /var/lib/influxdb3_data/
docker start influxdb3
```

### QuestDB

```bash
# Backup using the built-in backup API
curl "http://localhost:9000/exec?query=BACKUP%20DATABASE%20TO%20%27backup_2026_04_15%27"

# Or copy the data directory
docker exec questdb tar czf /tmp/questdb_backup.tar.gz /root/.questdb/db
docker cp questdb:/tmp/questdb_backup.tar.gz .
```

### TimescaleDB

```bash
# Standard PostgreSQL backup with pg_dump
pg_dump -h localhost -U postgres -d iot_data -Fc > timescaledb_backup.dump

# Restore
pg_restore -h localhost -U postgres -d iot_data timescaledb_backup.dump

# For large databases, use pg_basebackup
pg_basebackup -h localhost -U postgres -D /backup/timescaledb -P -v --checkpoint=fast
```

## Monitoring Your Time-Series Database

Regardless of which database you choose, you should monitor the database itself:

```yaml
# Add monitoring to any Docker Compose stack with Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
    restart: unless-stopped
```

Key metrics to watch:
- **Disk I/O**: time-series databases are I/O heavy; monitor IOPS and latency
- **RAM utilization**: InfluxDB and QuestDB use memory-mapped files; ensure enough RAM for hot data
- **WAL (Write-Ahead Log) size**: Growing WAL indicates writes outpacing flushes
- **Chunk/partition count**: Too many small chunks can degrade query performance
- **Connection pool utilization**: TimescaleDB inherits PostgreSQL connection limits; use pgbouncer for high-concurrency workloads

## Migration Considerations

If you are moving from a cloud-hosted service to a self-hosted database:

1. **Export data in Parquet or CSV**: These formats preserve schema and are universally importable
2. **Match partition granularity**: If your source data is partitioned by day, create the same partition scheme in the target
3. **Recreate indexes and continuous aggregates**: These do not transfer with raw data exports
4. **Test query compatibility**: SQL dialects differ; verify critical queries work before cutover
5. **Set up replication first**: Run both systems in parallel, validate data consistency, then switch traffic

For InfluxDB Cloud → InfluxDB 3 Core migrations, the `influxctl` CLI tool handles bulk export and import. For PostgreSQL-based migrations, `pg_dump`/`pg_restore` work seamlessly with TimescaleDB. QuestDB supports importing CSV files directly through its web console or REST API.
