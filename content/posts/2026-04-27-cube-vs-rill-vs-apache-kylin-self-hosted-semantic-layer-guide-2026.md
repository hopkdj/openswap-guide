---
title: "Cube.js vs Rill vs Apache Kylin: Self-Hosted Semantic Layer Guide 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "analytics", "bi", "semantic-layer"]
draft: false
description: "Compare Cube.js, Rill, and Apache Kylin — three self-hosted semantic layer platforms for headless BI, embedded analytics, and OLAP. Includes Docker Compose configs, feature comparison, and deployment guide."
---

A semantic layer sits between your raw data sources and your BI dashboards, providing a unified, governed definition of metrics, dimensions, and relationships. Instead of duplicating business logic across every dashboard tool, you define it once in the semantic layer and consume it everywhere — via SQL, REST APIs, GraphQL, or native BI connectors.

In this guide, we compare three leading self-hosted semantic layer platforms: **Cube.js** (the most widely adopted open-source option), **Rill** (the fastest real-time BI tool with an embedded semantic layer), and **Apache Kylin** (the enterprise-grade OLAP analytics engine).

Here is a snapshot of each project's current standing:

| Feature | Cube.js | Rill | Apache Kylin |
|---|---|---|---|
| **GitHub Stars** | 19,873 | 2,596 | 3,766 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **Language** | Rust / TypeScript | Go | Java |
| **License** | Elastic License 2.0 | Apache 2.0 | Apache 2.0 |
| **Primary Use** | Headless BI / Embedded Analytics | Real-time BI + Semantic Layer | Enterprise OLAP Analytics |
| **Query Engine** | Cube Store / DuckDB | DuckDB (embedded) | Spark / HBase |
| **Data Model** | YAML / JavaScript | YAML (models.yaml) | Web UI / JSON |
| **API Protocols** | REST, GraphQL, SQL, WebSocket | SQL, HTTP | REST, JDBC, ODBC |
| **Docker Image** | `cubejs/cube` | `rilldata/rill` | `apache/kylin` |
| **Best For** | Multi-tenant embedded analytics | Developer-first BI, sub-second queries | Petabyte-scale OLAP on Hadoop |

## Why Self-Host a Semantic Layer?

A cloud semantic layer (like dbt Semantic Layer, AtScale, or LookML) locks your metric definitions into a vendor-specific platform. By self-hosting, you gain:

- **Full data sovereignty**: Your metric definitions and query cache never leave your infrastructure.
- **No per-seat pricing**: Open-source alternatives remove the per-user costs that scale with team size.
- **Custom integrations**: Connect to any internal data source — proprietary databases, internal APIs, or legacy systems — that cloud platforms may not support.
- **Embedded analytics**: Ship governed metrics directly into your product's dashboards without exposing raw database credentials.

For organizations running self-hosted data stacks — with tools like [Apache Superset or Metabase for dashboards](../self-hosted-bi-dashboard-superset-metabase-lightdash-guide-2026/) and [ClickHouse or DuckDB for analytics](../clickhouse-vs-druid-vs-pinot-self-hosted-analytics-2026/) — a self-hosted semantic layer ties everything together with a single source of truth for business metrics.

## Cube.js: Headless BI for Embedded Analytics

Cube.js (now branded as **Cube Core**) is the most popular open-source semantic layer, with nearly 20,000 GitHub stars. It translates metric definitions into optimized SQL queries and serves results via REST, GraphQL, SQL, or WebSocket APIs.

### Architecture

Cube.js uses a three-tier architecture:

1. **API Gateway** — Receives requests from frontend apps, BI tools, or direct API calls.
2. **Query Orchestrator** — Parses metric definitions, generates SQL, manages query caching, and schedules pre-aggregations.
3. **Cube Store** — An optional columnar database (based on MySQL) that stores pre-aggregated results for sub-second response times.

### Key Features

- **Data schema as code**: Define metrics, dimensions, and joins in JavaScript or TypeScript files.
- **Pre-aggregations**: Automatically materialize expensive queries into Cube Store or external databases (PostgreSQL, MySQL, ClickHouse).
- **Multi-tenant security**: Row-level security with data source-level tenant isolation.
- **Caching layer**: Redis-backed query result caching with configurable TTL.
- **15+ database connectors**: PostgreSQL, MySQL, ClickHouse, Snowflake, BigQuery, DuckDB, and more.
- **Playground UI**: Built-in development environment for testing queries and generating frontend code.

### Docker Compose Deployment

Here is a production-ready Docker Compose setup for Cube.js with PostgreSQL as the backend and Redis for caching:

```yaml
version: "3.8"

services:
  cube:
    image: cubejs/cube:latest
    ports:
      - "4000:4000"
    environment:
      CUBEJS_DEV_MODE: "true"
      CUBEJS_DB_TYPE: postgres
      CUBEJS_DB_HOST: postgres
      CUBEJS_DB_PORT: 5432
      CUBEJS_DB_NAME: analytics
      CUBEJS_DB_USER: cube_user
      CUBEJS_DB_PASS: cube_password
      CUBEJS_API_SECRET: my-secret-key-change-in-production
      CUBEJS_REDIS_HOST: redis
      CUBEJS_REDIS_PORT: 6379
      CUBEJS_EXTERNAL_DEFAULT: "true"
      CUBEJS_SCHEDULED_REFRESH_DEFAULT: "true"
    volumes:
      - ./schema:/cube/conf/schema
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: analytics
      POSTGRES_USER: cube_user
      POSTGRES_PASSWORD: cube_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Save this as `docker-compose.yml` and start the stack:

```bash
mkdir -p schema
docker compose up -d
```

Define your first metric schema in `schema/Orders.js`:

```javascript
cube(`Orders`, {
  sql: `SELECT * FROM public.orders`,

  measures: {
    count: {
      type: `count`,
    },
    totalRevenue: {
      sql: `amount`,
      type: `sum`,
    },
    averageOrderValue: {
      sql: `amount`,
      type: `avg`,
    },
  },

  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true,
    },
    status: {
      sql: `status`,
      type: `string`,
    },
    createdAt: {
      sql: `created_at`,
      type: `time`,
    },
    customerEmail: {
      sql: `customer_email`,
      type: `string`,
    },
  },
});
```

Query the API:

```bash
curl -s "http://localhost:4000/cubejs-api/v1/load?query={\"measures\":[\"Orders.count\",\"Orders.totalRevenue\"]}" \
  -H "Authorization: Bearer <API_TOKEN>"
```

### When to Choose Cube.js

- You need **embedded analytics** — shipping metrics into a customer-facing product.
- Your team wants **multi-tenant row-level security** for SaaS applications.
- You have a **heterogeneous data stack** with multiple databases and need a unified metric layer.
- You want **pre-aggregations** to accelerate slow queries without changing the source database.

## Rill: Real-Time BI with an Embedded Semantic Layer

Rill is a newer entrant built in Go, combining a high-performance OLAP engine (DuckDB) with a declarative semantic layer. Unlike Cube.js, which separates the semantic layer from the visualization layer, Rill bundles both — making it a complete BI platform, not just a headless API.

### Architecture

Rill's architecture is intentionally simple:

1. **Rill CLI** — Single binary that manages project configuration, data ingestion, and query execution.
2. **DuckDB Engine** — Embedded columnar OLAP engine that processes queries directly on Parquet, CSV, or DuckDB files.
3. **Web Dashboard** — Built-in dashboard UI that auto-generates visualizations from model definitions.

### Key Features

- **Sub-second queries**: DuckDB's columnar execution delivers interactive performance on datasets up to ~100 GB on a single machine.
- **Declarative data models**: Define metrics in YAML (`models.yaml`) with familiar SQL syntax.
- **Automatic dashboards**: The web UI generates charts from model definitions — no manual chart building required.
- **Git-friendly**: Everything is stored as files (YAML + SQL), making it version-controllable.
- **Embedded DuckDB**: No external database required — the engine runs in-process.
- **Source connectors**: Ingest from S3, GCS, local files, PostgreSQL, MySQL, DuckDB, and HTTP endpoints.

### Docker Compose Deployment

Rill runs as a single binary, making its Docker deployment straightforward:

```yaml
version: "3.8"

services:
  rill:
    image: rilldata/rill:latest
    ports:
      - "9009:9009"
    volumes:
      - ./project:/home/rill/project
      - rill_data:/data
    working_dir: /home/rill/project
    command: start --host 0.0.0.0 --port 9009 --db /data/rill.db
    restart: unless-stopped

volumes:
  rill_data:
```

Initialize a new project and start:

```bash
mkdir -p project
docker compose up -d
```

Create your first model in `project/models/orders.sql`:

```sql
SELECT
    id,
    customer_email,
    status,
    amount,
    created_at
FROM read_csv_auto('/data/orders.csv')
```

Define the semantic layer in `project/models/orders.yaml`:

```yaml
version: 1
type: model
name: orders
refresh:
  cron: "*/30 * * * *"

measures:
  - name: total_orders
    expression: count(*)
  - name: total_revenue
    expression: sum(amount)
  - name: avg_order_value
    expression: avg(amount)

dimensions:
  - name: status
    column: status
  - name: created_at
    column: created_at
    type: time
```

Access the dashboard at `http://localhost:9009`. The UI will automatically generate explorations and charts based on your model definitions.

### When to Choose Rill

- You want a **complete BI solution** (semantic layer + dashboards) in a single deployment.
- Your datasets fit in **single-node memory** (up to ~100 GB with DuckDB).
- You prefer **GitOps workflows** — everything defined as version-controlled YAML and SQL files.
- You need **real-time exploratory analytics** without waiting for a data warehouse team.

## Apache Kylin: Enterprise OLAP on Hadoop

Apache Kylin is the oldest and most enterprise-grade option in this comparison. Originally developed by eBay, it provides a distributed OLAP engine on top of Hadoop and HBase, with a web-based semantic layer for defining cubes and measures.

### Architecture

Kylin's architecture is designed for petabyte-scale analytics:

1. **Kylin Server** — Web UI and REST API for cube management, query submission, and metadata operations.
2. **Kylin Engine** — Builds multi-dimensional cubes (pre-aggregated data structures) from Hadoop data sources.
3. **Storage Layer** — HBase or S3 for storing pre-computed cube segments.
4. **Query Engine** — Translates SQL queries into cube lookups or Spark jobs for real-time queries.

### Key Features

- **Pre-built cube materialization**: Cubes are pre-computed during build time, delivering sub-second query latency even on billions of rows.
- **Multi-dimensional analysis**: Supports drill-down, roll-up, slice-and-dice, and pivot operations natively.
- **Hadoop ecosystem integration**: Works with Hive, Kafka, Spark, HDFS, and HBase.
- **Kylin Studio**: Web UI for cube design, data modeling, query execution, and monitoring.
- **JDBC/ODBC drivers**: Connect from any SQL-compatible BI tool (Tableau, Superset, DBeaver).
- **Incremental builds**: Build only new cube segments instead of full rebuilds.

### Docker Compose Deployment

Apache Kylin requires HBase as a dependency. Here is a single-node deployment for development and testing:

```yaml
version: "3.8"

services:
  kylin:
    image: apache/kylin:latest
    ports:
      - "7070:7070"
      - "8088:8088"
    environment:
      - KYLIN_SERVER_HOST=kylin
      - KYLIN_HBASE_HOST=hbase
      - KYLIN_HDFS_HOST=hdfs
    depends_on:
      - hbase
      - hdfs
    volumes:
      - kylin_data:/usr/local/kylin/data
    restart: unless-stopped

  hbase:
    image: harisekhon/hbase:latest
    ports:
      - "8080:8080"
      - "9090:9090"
    volumes:
      - hbase_data:/hbase-data

  hdfs:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    ports:
      - "9870:9870"
    environment:
      - CLUSTER_NAME=hadoop-cluster
    volumes:
      - hdfs_data:/hadoop/dfs/data

volumes:
  kylin_data:
  hbase_data:
  hdfs_data:
```

For production deployments, Kylin recommends a full Hadoop cluster (HDFS + HBase + YARN) or cloud storage (S3) as the backend. The Kylin documentation provides detailed guides for cluster deployment on Kubernetes and bare metal.

After starting the stack, access Kylin Studio at `http://localhost:7070/kylin` with default credentials `ADMIN/KYLIN`.

### When to Choose Apache Kylin

- You already run a **Hadoop ecosystem** (HDFS, HBase, Spark) and want to add OLAP capabilities.
- You need **petabyte-scale analytics** with sub-second query latency via pre-computed cubes.
- Your team requires **enterprise features** like LDAP integration, role-based access control, and audit logging.
- You want to connect **existing BI tools** via JDBC/ODBC without changing the frontend layer.

## Detailed Feature Comparison

| Criterion | Cube.js | Rill | Apache Kylin |
|---|---|---|---|
| **Deployment Complexity** | Low (Docker + Redis + DB) | Very Low (single container) | High (requires Hadoop/HBase) |
| **Minimum Hardware** | 2 GB RAM, 1 CPU | 4 GB RAM, 2 CPU | 16 GB RAM, 4+ CPU |
| **Max Dataset Size** | Unlimited (external DB) | ~100 GB (single-node DuckDB) | Petabytes (distributed) |
| **Query Latency** | Sub-second (with pre-aggs) | Sub-second (DuckDB in-memory) | Sub-second (pre-built cubes) |
| **Data Model Format** | JavaScript / TypeScript | YAML + SQL | Web UI / JSON |
| **SQL Support** | Yes (via API) | Native (DuckDB SQL) | Full ANSI SQL |
| **Real-Time Data** | Yes (with streaming) | Yes (periodic refresh) | Yes (incremental builds) |
| **Multi-Tenancy** | Built-in (row-level security) | No (single workspace) | Yes (project-based) |
| **API Protocols** | REST, GraphQL, SQL, WS | SQL, HTTP | REST, JDBC, ODBC |
| **BI Connectors** | Tableau, Superset, Power BI | Built-in dashboard only | Tableau, Superset, DBeaver |
| **Community Size** | Large (19.8K stars) | Growing (2.6K stars) | Established (3.8K stars) |
| **License** | Elastic License 2.0 | Apache 2.0 | Apache 2.0 |
| **Learning Curve** | Moderate | Low | Steep |

## Migration Paths and Interoperability

All three platforms can coexist in the same data stack. Common patterns include:

- **Rill for prototyping, Cube.js for production**: Start with Rill to explore data and define metrics quickly, then migrate to Cube.js when you need multi-tenant embedded analytics.
- **Kylin for batch OLAP, Cube.js for real-time**: Use Kylin for pre-computed historical cubes and Cube.js for real-time query federation across multiple sources.
- **Cube.js as a proxy to Kylin**: Connect Cube.js to Kylin via JDBC and expose Kylin cubes through Cube's REST/GraphQL API for frontend applications that cannot use JDBC.

If you are building a complete self-hosted data stack, consider pairing your semantic layer with a [data catalog like DataHub or Amundsen](../amundsen-vs-datahub-vs-openmetadata-self-hosted-data-catalog-guide/) for metadata governance, and a [data quality tool like Great Expectations](../self-hosted-data-quality-tools-great-expectations-soda-dbt-guide-2026/) for validation pipelines.

## FAQ

### What is a semantic layer in data analytics?

A semantic layer is an abstraction between raw data sources and BI tools that defines business metrics, dimensions, and relationships in a centralized, reusable format. Instead of writing the same SQL logic in every dashboard, you define `revenue = sum(order_amount)` once in the semantic layer, and every downstream tool references this single definition.

### Can I use Cube.js without Cube Store?

Yes. Cube.js can connect directly to any supported database and execute queries against it without the Cube Store pre-aggregation engine. However, for dashboards with sub-second response times on large datasets, enabling Cube Store or an external pre-aggregation database (PostgreSQL, ClickHouse) is recommended.

### Does Rill support real-time data streaming?

Rill supports incremental data refresh on a configurable schedule (e.g., every 30 minutes via cron). It does not support true real-time streaming like Kafka-based pipelines. For real-time ingestion, you would write new Parquet files to the source directory and trigger a manual refresh.

### How does Apache Kylin achieve sub-second query latency?

Kylin pre-computes multi-dimensional cubes during a build phase. When a query arrives, the engine maps it to the pre-built cube segments and returns results from HBase or S3 storage. This is fundamentally different from compute-at-query-time engines like Presto or Trino, which scan raw data for every query.

### Which tool is best for embedded analytics in a SaaS product?

Cube.js is the strongest choice for embedded analytics. It offers multi-tenant row-level security, a rich API (REST, GraphQL, SQL), frontend SDKs for React, Angular, and Vue, and query-level caching that scales with user traffic.

### Can I migrate metrics definitions between these platforms?

There is no automatic migration tool. However, the underlying metric definitions (measures, dimensions, joins) are conceptually similar. You would need to translate JavaScript schema files (Cube.js) or YAML models (Rill) into Kylin's cube definitions via the web UI. The SQL logic remains the same — only the format changes.

### Is Cube.js truly free for production use?

Cube.js Core is available under the Elastic License 2.0 (ELv2), which allows free use for most purposes including production deployments. The license restricts offering Cube.js as a managed service to third parties (i.e., you cannot sell "Cube.js hosting" as a product). For most organizations deploying internally or embedding in their own product, ELv2 poses no restrictions.

### What are the resource requirements for each platform?

- **Cube.js**: 2 GB RAM minimum, scales horizontally with Redis and Cube Store.
- **Rill**: 4 GB RAM minimum (DuckDB loads data into memory). Maximum practical dataset is ~100 GB on a single node.
- **Apache Kylin**: 16 GB RAM minimum for a single-node deployment. Production clusters typically require 64+ GB RAM and multiple nodes for HBase and HDFS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cube.js vs Rill vs Apache Kylin: Self-Hosted Semantic Layer Guide 2026",
  "description": "Compare Cube.js, Rill, and Apache Kylin — three self-hosted semantic layer platforms for headless BI, embedded analytics, and OLAP. Includes Docker Compose configs, feature comparison, and deployment guide.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
