---
title: "Apache Iceberg vs Apache Hudi vs Delta Lake: Best Open Data Lakehouse Formats 2026"
date: 2026-04-18
tags: ["comparison", "guide", "data-engineering", "self-hosted", "lakehouse"]
draft: false
description: "Compare Apache Iceberg, Apache Hudi, and Delta Lake — the three leading open table formats for building self-hosted data lakehouse architectures. Covers features, performance, ecosystem compatibility, and deployment."
---

The modern data stack has shifted from monolithic data warehouses to **lakehouse architectures** — systems that combine the scalability and cost-efficiency of data lakes with the ACID transaction guarantees and performance optimizations of traditional databases. At the heart of every lakehouse sits an **open table format**: a layer that adds structure, metadata, and transaction support to raw files stored in object storage or distributed filesystems.

Three projects dominate this space: **Apache Iceberg**, **Apache Hudi**, and **Delta Lake**. All are open-source, all support ACID transactions on big data, and all aim to make data lakes as reliable as databases. But they differ significantly in design philosophy, ecosystem integration, and operational com[plex](https://www.plex.tv/)ity.

This guide compares all three table formats across architecture, features, performance, tooling, and self-hosted deployment to help you choose the right foundation for your data platform.

## Why Self-Host Your Data Lakehouse

Running a data lakehouse on your own infrastructure gives you:

- **Full data sovereignty** — data never l[minio](https://min.io/) your storage (S3, MinIO, Ceph, or local disks)
- **No vendor lock-in** — open table formats work across compute engines (Spark, Trino, Flink, Presto, DuckDB)
- **Cost control** — pay only for your compute and storage, no per-query SaaS fees
- **Compliance** — meet GDPR, HIPAA, or SOC 2 requirements with on-premises data governance
- **Predictable performance** — no noisy neighbors, no rate limits, no shared-tenancy degradation

Whether you're building a real-time analytics pipeline, a batch data warehouse replacement, or a machine learning feature store, a self-hosted lakehouse gives you the flexibility to run any compute engine against a single source of truth.

## Architecture Comparison

### Apache Iceberg

Apache Iceberg was created at Netflix in 2017 and donated to the Apache Software Foundation in 2018. It uses a **multi-layer metadata architecture** with three levels:

1. **Catalog layer** — tracks the current snapshot pointer (Hive Metastore, AWS Glue, Nessie, Rest Catalog)
2. **Metadata layer** — JSON files storing snapshots, manifests, and partition specs
3. **Data layer** — Parquet, ORC, or Avro files organized into data files and delete files

```
Snapshot Pointer (Catalog)
        ↓
  Metadata JSON (v2)
        ↓
  Manifest List
        ↓
  Manifest Files → Data Files (Parquet)
```

Iceberg's design separates metadata from data completely, enabling **snapshot isolation**, **time travel**, and **schema evolution** without rewriting existing data files. It is engine-agnostic — any compute engine with an Iceberg reader can query the same data.

### Apache Hudi

Apache Hudi (Hadoop Upserts Deletes and Incrementals) originated at Uber in 2016 and became a top-level Apache project in 2020. It is built around two table types:

- **Copy-on-Write (CoW)** — data stored in columnar format (Parquet), updated by rewriting files during commits
- **Merge-on-Read (MoR)** — combines columnar Parquet files with row-based Avro logs for faster writes

```
Timeline (Commits)
        ↓
  File Groups (Base + Log Files)
        ↓
  Compaction (async) → Optimized Parquet
```

Hudi provides **fine-grained record-level upserts and deletes**, making it particularly well-suited for CDC (Change Data Capture) pipelines and streaming ingest scenarios. It ships with built-in indexing mechanisms (Bloom, HBase, simple) to locate records quickly.

### Delta Lake

Delta Lake was created by Databricks in 2019 and open-sourced under the Linux Foundation in 2019. It uses a **transaction log** (Delta log) stored alongside data files in JSON format, with checkpoints in Parquet for efficient metadata reads.

```
_delta_log/
  ├── 00000000000000000000.json
  ├── 00000000000000000001.json
  ├── ...
  └── _last_checkpoint
_data/
  ├── part-00000-xxxx.parquet
  └── ...
```

Delta Lake stores its transaction log **inside the table directory** itself (no external catalog required), making it the simplest of the three to set up. It integrates tightly with Apache Spark and has expanding support for other engines through Delta Kernel.

## Feature Comparison

| Feature | Apache Iceberg | Apache Hudi | Delta Lake |
|---------|---------------|-------------|------------|
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 8,748 | 6,139 | 8,752 |
| **Primary Language** | Java | Java | Scala |
| **Created** | 2018 (Netflix) | 2016 (Uber) | 2019 (Databricks) |
| **ACID Transactions** | Yes | Yes | Yes |
| **Time Travel** | Yes | Yes | Yes |
| **Schema Evolution** | Full (add, drop, rename, reorder, change type) | Partial (add columns) | Full |
| **Partition Evolution** | Yes (hidden partitioning) | Limited | Yes |
| **Row-Level Updates** | Yes (via position deletes) | Yes (native, CoW & MoR) | Yes |
| **Row-Level Deletes** | Yes (via position/equality deletes) | Yes | Yes |
| **Streaming Ingest** | Yes (Flink native) | Yes (Spark Structured Streaming) | Yes (Spark Structured Streaming) |
| **CDC Support** | Via Debezium | Native (MoR + incremental queries) | Via Delta Lake CDC |
| **Compaction** | Manual/automated | Built-in (async) | OPTIMIZE command |
| **File Format** | Parquet, ORC, Avro | Parquet (CoW), Parquet+Avro (MoR) | Parquet |
| **Hidden Partitioning** | Yes | No | No (requires manual) |
| **External Catalog** | Required (Hive, Glue, Nessie, JDBC, REST) | Optional (Hive Metastore) | Not required (self-contained) |
| **Spark Support** | Yes | Yes (tightest integration) | Yes (native) |
| **Trino/Presto Support** | Yes (native) | Yes (via Hive connector) | Yes (Delta Standalone) |
| **Flink Support** | Yes (native, first-class) | Yes | Limited |
| **DuckDB Support** | Yes | Limited | Yes |
| **Iceberg REST Catalog** | Yes | N/A | N/A |

## Performance Characteristics

Each format makes different trade-offs between read and write performance:

**Apache Iceberg** — Balanced read/write. Hidden partition pruning and manifest-level metadata enable fast scans without full-table reads. MoR-style reads via position deletes add slight overhead on heavy-delete workloads, but the v2 delete file design minimizes this impact.

**Apache Hudi** — Optimized for write-heavy and streaming workloads. MoR mode provides sub-second ingest latency with async compaction. CoW mode trades write amplification for faster reads. The built-in indexing system keeps record lookups fast even at billion-row scale.

**Delta Lake** — Optimized for Spark workloads. The transaction log design means metadata reads are fast and consistent. `OPTIMIZE` and `VACUUM` commands handle file-size management and cleanup. Z-ORDER indexing provides multi-column clustering for selective queries.

## Self-Hosted Deployme[docker](https://www.docker.com/)# Apache Iceberg: Docker Compose Quickstart

The Tabular team maintains the canonical Spark-Iceberg environment:

```yaml
# docker-compose.yml — Apache Iceberg with Spark + MinIO + REST Catalog
services:
  spark-iceberg:
    image: tabulario/spark-iceberg
    container_name: spark-iceberg
    networks:
      iceberg_net:
    depends_on:
      - rest
      - minio
    volumes:
      - ./warehouse:/home/iceberg/warehouse
      - ./notebooks:/home/iceberg/notebooks
    environment:
      - AWS_ACCESS_KEY_ID=admin
      - AWS_SECRET_ACCESS_KEY=password123
      - AWS_REGION=us-east-1
    ports:
      - 8888:8888   # Jupyter Notebook
      - 8080:8080   # Spark UI
      - 10000:10000 # Hive metastore
      - 10001:10001 # Spark thrift server

  rest:
    image: apache/iceberg-rest-fixture
    container_name: iceberg-rest
    networks:
      iceberg_net:
    ports:
      - 8181:8181
    environment:
      - AWS_ACCESS_KEY_ID=admin
      - AWS_SECRET_ACCESS_KEY=password123
      - AWS_REGION=us-east-1
      - CATALOG_WAREHOUSE=s3://warehouse/
      - CATALOG_IO__IMPL=org.apache.iceberg.aws.s3.S3FileIO
      - CATALOG_S3_ENDPOINT=http://minio:9000

  minio:
    image: minio/minio
    container_name: minio
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=password123
      - MINIO_DOMAIN=minio
    networks:
      iceberg_net:
        aliases:
          - warehouse.minio
    ports:
      - 9001:9001
      - 9000:9000
    command: ["server", "/data", "--console-address", ":9001"]

  mc:
    depends_on:
      - minio
    image: minio/mc
    container_name: mc
    networks:
      iceberg_net:
    entrypoint: >
      /bin/sh -c "
      until (/usr/bin/mc config host add minio http://minio:9000 admin password123) do
        echo '...waiting...' && sleep 1
      done;
      /usr/bin/mc rm -r --force minio/warehouse;
      /usr/bin/mc mb minio/warehouse;
      /usr/bin/mc policy set public minio/warehouse;
      tail -f /dev/null
      "
networks:
  iceberg_net:
```

Start the stack with `docker compose up -d`. The Jupyter notebook at `http://localhost:8888` includes pre-loaded PySpark examples.

### Apache Hudi: Docker Compose Quickstart

Hudi provides comprehensive Docker Compose files with Hadoop, Hive, Spark, and Zookeeper:

```yaml
# docker-compose.yml — Apache Hudi with Hadoop + Hive + Spark
services:
  namenode:
    image: apachehudi/hudi-hadoop_3.4.0-namenode:latest
    hostname: namenode
    container_name: namenode
    environment:
      - CLUSTER_NAME=hudi_cluster
    ports:
      - "9870:9870"  # HDFS Web UI
      - "8020:8020"  # HDFS
    healthcheck:
      test: ["CMD", "curl", "-f", "http://namenode:9870"]
      interval: 30s
      timeout: 10s
      retries: 3

  datanode:
    image: apachehudi/hudi-hadoop_3.4.0-datanode:latest
    container_name: datanode
    environment:
      - CLUSTER_NAME=hudi_cluster
    depends_on:
      - namenode

  hudi-spark:
    image: apachehudi/hudi-spark3.5.x-bundle:latest
    container_name: hudi-spark
    hostname: hudi-spark
    depends_on:
      - namenode
      - datanode
    ports:
      - "4040:4040"   # Spark UI
      - "8888:8888"   # Jupyter
    environment:
      - SPARK_HOME=/opt/spark
    volumes:
      - ./hudi-data:/opt/hudi/data
```

Run the Hudi quickstart demo:

```bash
# Clone and start
git clone https://github.com/apache/hudi.git
cd hudi/docker
./compose/demo/setup_demo.sh spark

# Run Spark shell with Hudi
docker exec -it hudi-spark spark-shell \
  --packages org.apache.hudi:hudi-spark3.5-bundle_2.12:1.0.1 \
  --conf "spark.serializer=org.apache.spark.serializer.KryoSerializer"
```

### Delta Lake: Quick Setup

Delta Lake requires the least infrastructure — no external catalog, no Hadoop cluster:

```bash
# Install Delta Lake with pip (Python API)
pip install delta-spark pyspark

# Or use Docker with Spark + Delta
docker run -it --rm \
  -p 8888:8888 \
  -v $(pwd)/notebooks:/opt/notebooks \
  deltaio/delta-kernel-rust:latest
```

```python
# Quick start with PySpark + Delta Lake
from pyspark.sql import SparkSession
from delta import configure_spark_with_delta_pip

builder = (
    SparkSession.builder
    .appName("delta-lake-demo")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.warehouse.dir", "/tmp/delta-warehouse")
)

spark = configure_spark_with_delta_pip(builder).getOrCreate()

# Create a Delta table
data = spark.range(0, 1000000)
data.write.format("delta").mode("overwrite").save("/tmp/delta-warehouse/my_table")

# Read it back
df = spark.read.format("delta").load("/tmp/delta-warehouse/my_table")
print(f"Rows: {df.count()}")

# Time travel
df_v1 = spark.read.format("delta").option("versionAsOf", 0).load("/tmp/delta-warehouse/my_table")

# Optimize (compaction + Z-ORDER)
spark.sql("OPTIMIZE delta.`/tmp/delta-warehouse/my_table` ZORDER BY (id)")
```

## When to Choose Each Format

### Choose Apache Iceberg when:
- You need **multi-engine support** (Spark + Trino + Flink + DuckDB) as a primary requirement
- You want **hidden partitioning** to avoid manual partition management
- You're building a **lakehouse with a REST catalog** for centralized metadata management
- You use **Apache Flink** for real-time streaming ingestion
- You need robust **schema evolution** including column reordering and type changes

### Choose Apache Hudi when:
- Your workload is **write-heavy** with frequent upserts and deletes
- You're ingesting **CDC streams** (Debezium, Kafka Connect) and need incremental queries
- You need **record-level indexing** for point lookups at scale
- You're already invested in the **Apache Spark ecosystem** and want tight integration
- You need **asynchronous compaction** that doesn't block writes

### Choose Delta Lake when:
- You want the **simplest setup** with no external catalog dependency
- Your primary compute engine is **Apache Spark**
- You need **Z-ORDER indexing** for multi-dimensional query optimization
- You're using **Databricks** (native Delta support, Unity Catalog integration)
- You want **Delta Sharing** protocol for secure cross-organization data sharing

## Ecosystem Integration

All three formats integrate with the broader data engineering ecosystem, but with different depths:

| Integration | Apache Iceberg | Apache Hudi | Delta Lake |
|-------------|---------------|-------------|------------|
| Apache Spark | Yes | Yes (native) | Yes (native) |
| Apache Flink | Yes (native) | Yes | Limited |
| Trino/Presto | Yes (native) | Yes (via Hive) | Yes |
| Apache Hive | Yes | Yes | Via Storage Handler |
| DuckDB | Yes | No | Yes |
| StarRocks | Yes | No | No |
| Apache Doris | Yes | No | No |
| Snowflake | Yes (external tables) | No | No |
| BigQuery | Yes (external tables) | No | No |
| Redshift | Yes (spectrum) | No | No |
| dbt | Yes (via adapter) | Limited | Yes (via adapter) |
| Great Expectations | Yes | Limited | Yes |
| Apache Beam | Yes | No | No |
| Kafka Connect | Yes (via sink) | Yes (native sink) | Yes (via sink) |

For related reading, see our guides on [self-hosted data pipeline tools](../meltano-vs-airbyte-vs-singer-self-hosted-data-pipeline-guide-2026/), [data orchestration platforms](../apache-airflow-vs-prefect-vs-dagster-self-hosted-data-orchestration-guide/), [self-hosted data catalog solutions](../amundsen-vs-datahub-vs-openmetadata-self-hosted-data-catalog-guide/), and [data versioning tools](../dvc-lakefs-pachyderm-self-hosted-data-versioning-guide-2026/).

## FAQ

### What is the difference between a data lake and a data lakehouse?

A data lake stores raw files (CSV, Parquet, JSON) in object storage or HDFS without structure or transaction guarantees. A **data lakehouse** adds an open table format layer (Iceberg, Hudi, or Delta Lake) on top of those files, providing ACID transactions, schema enforcement, time travel, and query optimization — essentially bringing database reliability to data lake storage.

### Can I use Apache Iceberg, Hudi, and Delta Lake together?

Technically yes, but it's not recommended. Each format maintains its own metadata layer, and mixing formats in the same data platform creates operational complexity. Choose one format as your primary table layer and standardize on it. Some organizations use Iceberg for analytics workloads and Hudi for CDC pipelines, but this requires careful data governance.

### Which format has the best query performance?

There is no single winner — performance depends on your workload:
- **Iceberg** excels at selective scans with hidden partition pruning and manifest-level filtering
- **Hudi** is fastest for streaming ingest and incremental queries on write-heavy datasets
- **Delta Lake** performs best on Spark workloads with Z-ORDER indexing and data skipping statistics
Benchmark with your own data patterns before committing to a format.

### Do I need Hadoop to run these table formats?

**No.** All three formats can work directly with object storage (S3, MinIO, GCS, Azure Blob Storage) without HDFS. Hudi's Docker Compose includes Hadoop for its demo environment, but production deployments commonly use S3 or MinIO as the storage layer. Iceberg and Delta Lake are particularly well-suited for cloud-native, Hadoop-free architectures.

### How do these formats handle schema changes?

- **Iceberg** supports full schema evolution: add, drop, rename, reorder columns, and change data types — all without rewriting existing data files
- **Hudi** supports adding new columns but has more limited support for renames and type changes
- **Delta Lake** supports full schema evolution including column renames, drops, and type widening

### Can I migrate from one format to another?

Migration is possible but requires data rewriting since each format uses different metadata structures. Tools like Apache Spark can read from one format and write to another. For large datasets (terabytes+), plan migration carefully — it's a one-time operation that requires full table scans.

### Which format is best for real-time streaming?

**Apache Hudi** is generally considered the best for real-time streaming due to its MoR table type, built-in indexing, and incremental query support. **Apache Iceberg** with Flink is a strong second choice for teams already using Flink. **Delta Lake** supports streaming through Spark Structured Streaming but has fewer real-time-specific features.

## Conclusion

Apache Iceberg, Apache Hudi, and Delta Lake are all mature, production-grade table formats powering modern data lakehouse architectures. The choice comes down to your specific workload patterns, existing compute engine investments, and operational preferences:

- **Iceberg** is the best multi-engine, multi-cloud choice with the broadest ecosystem support
- **Hudi** is the streaming and CDC champion with native upsert support
- **Delta Lake** is the simplest to deploy and excels in Spark-centric environments

All three are open-source, self-hostable, and free from vendor lock-in. For teams building a data platform from scratch, Apache Iceberg's engine-agnostic design and rapidly growing adoption make it the safest long-term bet. For teams with existing Spark pipelines and heavy write workloads, Hudi remains the strongest choice. For Spark-first teams prioritizing simplicity, Delta Lake delivers the most straightforward path to a production lakehouse.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Apache Iceberg vs Apache Hudi vs Delta Lake: Best Open Data Lakehouse Formats 2026",
  "description": "Compare Apache Iceberg, Apache Hudi, and Delta Lake — the three leading open table formats for building self-hosted data lakehouse architectures. Covers features, performance, ecosystem compatibility, and deployment.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
