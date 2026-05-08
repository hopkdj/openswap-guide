---
title: "Self-Hosted Batch Processing: Apache Spark vs Hadoop MapReduce vs Apache Tez (2026)"
date: "2026-05-09"
draft: false
tags: ["data-processing", "big-data", "apache-spark", "hadoop", "batch-processing", "analytics"]
---

Processing large-scale data in batch mode remains a foundational requirement for data engineering pipelines. Whether you are running ETL jobs, building data warehouses, training machine learning models, or generating nightly reports, choosing the right batch processing engine impacts cost, performance, and operational complexity.

This guide compares three major open-source batch processing frameworks: **Apache Spark**, **Apache Hadoop MapReduce**, and **Apache Tez** — covering architecture, performance, deployment, and when to use each.

## Comparison Table

| Feature | Apache Spark | Hadoop MapReduce | Apache Tez |
|---------|-------------|-----------------|------------|
| **Stars** | 43,200+ | 15,500+ | 510+ |
| **Processing Model** | In-memory DAG execution | Disk-based map-reduce stages | DAG execution engine on YARN |
| **Latency** | Seconds to minutes (in-memory) | Minutes to hours (disk I/O) | Seconds to minutes (in-memory) |
| **APIs** | Scala, Java, Python, R, SQL | Java, Streaming (any language) | Java (via Hive, Pig, or custom) |
| **Execution** | Standalone, YARN, Kubernetes, Mesos | YARN only | YARN only |
| **Fault Tolerance** | RDD lineage reconstruction | Task re-execution from disk | DAG re-execution |
| **ML Support** | MLlib (built-in) | Mahout (external) | None (execution engine only) |
| **Streaming** | Structured Streaming (micro-batch) | Storm (separate project) | None (batch only) |
| **Docker Image** | bitnami/spark, apache/spark | bitnami/hadoop | No official image |
| **Last Active** | 2026 | 2026 | 2026 |
| **Language** | Scala | Java | Java |

## Apache Spark: The In-Memory Processing Engine

Apache Spark is the dominant batch processing framework in modern data engineering. Its in-memory execution model makes it 10-100x faster than MapReduce for iterative workloads. Spark provides a unified engine for batch processing, streaming, SQL queries, machine learning, and graph computation.

### Architecture

Spark runs as a driver-executor model:
- **Driver**: Orchestrates job execution, maintains DAG, schedules tasks
- **Executors**: Run tasks on cluster nodes, cache data in memory
- **Cluster Manager**: YARN, Kubernetes, or Spark Standalone

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  spark-master:
    image: bitnami/spark:latest
    environment:
      - SPARK_MODE=master
      - SPARK_RPC_AUTHENTICATION_ENABLED=no
    ports:
      - "8080:8080"
      - "7077:7077"
    volumes:
      - spark-data:/opt/bitnami/spark/data

  spark-worker:
    image: bitnami/spark:latest
    environment:
      - SPARK_MODE=worker
      - SPARK_MASTER_URL=spark://spark-master:7077
      - SPARK_WORKER_MEMORY=2G
      - SPARK_WORKER_CORES=2
    depends_on:
      - spark-master
    volumes:
      - spark-data:/opt/bitnami/spark/data

  spark-submit:
    image: bitnami/spark:latest
    environment:
      - SPARK_MODE=submit
      - SPARK_MASTER_URL=spark://spark-master:7077
    volumes:
      - ./jobs:/opt/bitnami/spark/jobs
    command: ["/opt/bitnami/spark/jobs/etl_job.py"]

volumes:
  spark-data:
```

### Running a PySpark Job

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("ETL Pipeline") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Read from Parquet
df = spark.read.parquet("s3a://data-lake/raw/events/")

# Transform
result = df.filter(df.event_type == "purchase") \
           .groupBy("user_id") \
           .agg({"amount": "sum", "timestamp": "max"})

# Write optimized output
result.write \
    .mode("overwrite") \
    .partitionBy("date") \
    .parquet("s3a://data-lake/processed/purchases/")

spark.stop()
```

### Spark Submit Command

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode cluster \
  --executor-memory 4G \
  --num-executors 10 \
  --conf spark.sql.adaptive.enabled=true \
  /opt/bitnami/spark/jobs/etl_job.py
```

## Hadoop MapReduce: The Original Batch Engine

Hadoop MapReduce pioneered distributed batch processing and established the paradigm of splitting computation into map and reduce phases. While it has been largely superseded by Spark for most workloads, MapReduce remains relevant for specific use cases.

### Architecture

MapReduce runs on top of HDFS (Hadoop Distributed File System) and YARN (Yet Another Resource Negotiator):
- **NameNode**: Manages HDFS metadata
- **DataNode**: Stores actual data blocks
- **ResourceManager**: Allocates cluster resources
- **NodeManager**: Manages resources on individual nodes
- **ApplicationMaster**: Negotiates resources for a specific job

### Docker Compose with Hadoop

```yaml
version: "3.8"
services:
  namenode:
    image: bitnami/hadoop:latest
    environment:
      - HDFS_NAMENODE_USER=hadoop
      - HDFS_DATANODE_USER=hadoop
      - HDFS_SECONDARYNAMENODE_USER=hadoop
      - YARN_RESOURCEMANAGER_USER=yarn
      - YARN_NODEMANAGER_USER=yarn
    ports:
      - "9870:9870"
      - "8088:8088"
    volumes:
      - hadoop-data:/hadoop

  datanode:
    image: bitnami/hadoop:latest
    environment:
      - HDFS_NAMENODE_USER=hadoop
      - HDFS_DATANODE_USER=hadoop
    depends_on:
      - namenode
    volumes:
      - hadoop-data:/hadoop

volumes:
  hadoop-data:
```

### Running a MapReduce Job

```bash
# Submit a MapReduce job
hadoop jar /opt/hadoop/share/hadoop/mapreduce/hadoop-mapreduce-examples-*.jar \
  wordcount \
  /input/documents \
  /output/wordcount

# Check job status
yarn application -list

# View results
hdfs dfs -cat /output/wordcount/part-r-00000 | head -20
```

### When MapReduce Still Makes Sense

- **Massive datasets on limited RAM**: MapReduce writes intermediate results to disk, making it suitable for datasets that exceed cluster memory
- **Compliance and auditability**: Disk-based processing provides a natural audit trail of intermediate results
- **Existing Hadoop ecosystem**: Organizations with heavy investments in HDFS, Hive, and HBase may prefer MapReduce for consistency
- **Simple ETL jobs**: For straightforward map-filter-reduce operations, MapReduce's simplicity can be an advantage

## Apache Tez: The DAG Execution Engine

Apache Tez is a DAG (Directed Acyclic Graph) execution engine that runs on YARN. Unlike MapReduce's rigid two-stage model, Tez allows arbitrary computation graphs, enabling optimizations like joining multiple operators into a single task.

### Architecture

Tez sits between the application (Hive, Pig, or custom code) and YARN:
- **DAG API**: Applications define computation as a directed acyclic graph
- **Tez ApplicationMaster**: Manages DAG execution on YARN
- **Task Schedulers**: Optimize task placement based on data locality

### Running Tez with Hive

```sql
-- Enable Tez as the execution engine
SET hive.execution.engine=tez;

-- Run a complex query that benefits from DAG optimization
SELECT
    c.customer_name,
    SUM(o.order_amount) as total_spent,
    COUNT(DISTINCT p.product_id) as unique_products
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= '2025-01-01'
GROUP BY c.customer_name
ORDER BY total_spent DESC
LIMIT 100;
```

### Tez vs MapReduce Performance

Tez typically outperforms MapReduce by 2-10x on equivalent workloads because:
1. **Fewer I/O operations**: Multiple map-reduce stages are collapsed into a single DAG
2. **Better resource utilization**: Containers are reused across tasks instead of being allocated/deallocated per stage
3. **Dynamic optimization**: Tez can re-plan the DAG at runtime based on intermediate result sizes

## Choosing the Right Batch Processing Engine

**Choose Apache Spark when:**
- You need the fastest possible batch processing with in-memory execution
- Your team uses Python, Scala, or R (PySpark, SparkR)
- You want a unified platform for batch, streaming, ML, and SQL
- You need Kubernetes or standalone deployment (not just YARN)
- You are building modern data pipelines with Parquet/Delta Lake

**Choose Hadoop MapReduce when:**
- You have petabyte-scale datasets that exceed available cluster memory
- You need maximum fault tolerance with disk-backed intermediate results
- Your organization has an existing Hadoop ecosystem (HDFS, Hive, HBase)
- You process simple map-filter-reduce workloads without complex DAGs

**Choose Apache Tez when:**
- You are running Hive or Pig queries on YARN and want better performance than MapReduce
- You need DAG optimization without adopting a full Spark deployment
- Your workloads benefit from container reuse across computation stages
- You want incremental performance improvements within an existing Hadoop stack

## Why Self-Host Batch Processing?

Running batch processing engines on self-hosted infrastructure provides significant advantages over cloud-managed alternatives:

- **Cost predictability**: Cloud Spark (Databricks, EMR) charges per DPU/hour, which can become expensive for nightly batch jobs processing terabytes. Self-hosted Spark on commodity hardware runs at a fixed cost
- **Data sovereignty**: Batch processing often involves sensitive data (financial records, healthcare data, PII). Keeping computation on-premises avoids data transfer to cloud regions with different privacy regulations
- **Network performance**: Processing data where it lives eliminates the cost and latency of moving terabytes to cloud storage for computation. Self-hosted clusters co-located with data sources (databases, data lakes, IoT pipelines) minimize data movement
- **Custom hardware acceleration**: Self-hosted clusters can use GPUs for ML workloads (Spark MLlib with RAPIDS), NVMe storage for shuffle operations, or high-bandwidth NICs for data-intensive stages
- **No vendor lock-in**: Open-source Spark, MapReduce, and Tez run identically on any infrastructure. You avoid proprietary extensions from Databricks, AWS EMR, or Google Dataproc that make migration difficult

For data pipeline orchestration, see our [Apache Airflow vs Dagster vs Prefect guide](../apache-airflow-vs-prefect-vs-dagster-self-hosted-data-orchestration-guide/). If you need workflow orchestration with DAG scheduling, check our [Dagu vs Netflix Conductor vs Airflow comparison](../2026-04-24-dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide/). For analytics databases, our [ClickHouse vs Druid vs Pinot comparison](../clickhouse-vs-druid-vs-pinot-self-hosted-analytics-2026/) covers real-time query engines.

## FAQ

### Is Apache Spark faster than Hadoop MapReduce?

Yes, Spark is typically 10-100x faster than MapReduce for most workloads because it processes data in memory rather than writing intermediate results to disk after each map and reduce stage. The speed advantage is most pronounced for iterative algorithms (machine learning, graph processing) where the same data is accessed multiple times.

### Can Spark run on existing Hadoop clusters?

Yes. Spark can run on YARN (Hadoop's resource manager) and read data from HDFS. This means you can deploy Spark on an existing Hadoop cluster without replacing HDFS. Many organizations run both MapReduce and Spark on the same YARN cluster, using MapReduce for legacy jobs and Spark for new workloads.

### What is the difference between Apache Tez and Apache Spark?

Tez is a DAG execution engine that runs on YARN and is primarily used as a backend for Hive and Pig. Spark is a standalone processing engine with its own cluster manager, APIs, and ecosystem (MLlib, Structured Streaming, Spark SQL). Tez improves MapReduce performance within the Hadoop ecosystem; Spark replaces MapReduce entirely with a different processing model.

### Does Apache Tez support Python?

Not natively. Tez is a Java-based execution engine. Python support comes through higher-level tools that use Tez as a backend — for example, Hive queries written in SQL can run on Tez. If you need a Python-first batch processing framework, Apache Spark with PySpark is the better choice.

### How much memory does Spark need?

Spark's memory requirements depend on your data size and transformations. A good starting point is 4-8 GB of executor memory per core. Spark needs enough memory to cache RDDs/DataFrames and perform shuffle operations. For a 1 TB dataset, a cluster with 10 executors at 8 GB each (80 GB total) is a reasonable starting point.

### Can I run Spark without Hadoop?

Yes. Spark can run in standalone mode, on Kubernetes, or on Mesos without any Hadoop components. It can also read from cloud storage (S3, GCS, Azure Blob), local filesystems, or databases directly. Hadoop (HDFS + YARN) is only needed if you want Spark to run on a Hadoop cluster.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Batch Processing: Apache Spark vs Hadoop MapReduce vs Apache Tez (2026)",
  "description": "Compare Apache Spark, Hadoop MapReduce, and Apache Tez for self-hosted batch data processing. Covers architecture, Docker deployment, performance, and use cases.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
