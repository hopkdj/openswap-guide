---
title: "Self-Hosted Headless BI: MetricFlow vs Malloy vs Cube.js for the Semantic Layer"
date: "2026-06-09"
tags: ["business-intelligence", "analytics", "semantic-layer", "headless-bi", "data-engineering", "sql"]
draft: false
---

## Introduction

The semantic layer sits between raw data warehouses and analytics tools, translating complex SQL into business-friendly metrics that non-technical users can explore. Headless BI platforms take this concept further — they provide a metrics API that multiple frontend tools (dashboards, notebooks, embedded analytics) can consume, ensuring consistent metric definitions across the entire organization.

In this guide, we compare three leading open-source semantic layer tools: **MetricFlow** (from dbt Labs), **Malloy** (from Google/Meta), and **Cube.js** (from Cube Dev). Each takes a different approach to defining, computing, and serving business metrics from your data warehouse.

## Comparison Table

| Feature | MetricFlow | Malloy | Cube.js |
|---------|-----------|--------|---------|
| **Primary Role** | Semantic layer + metric definition | Analytical query language | Headless BI API server |
| **GitHub Stars** | 1,900+ (dbt-core) | 2,100+ | 18,000+ |
| **Language** | Python (YAML config) | Malloy (SQL-like), TypeScript | JavaScript/TypeScript |
| **Query Engine** | dbt Semantic Layer + proxy | DuckDB / BigQuery / Postgres | Pre-aggregation + SQL pushdown |
| **API Protocol** | GraphQL, JDBC, REST | REST (via Malloy Composer) | REST, GraphQL, SQL API |
| **Caching** | Via proxy layer | Query result caching | Multi-level (in-memory + DB) |
| **Multi-Tenancy** | Via dbt Cloud/Server | Via deployment | Built-in |
| **Joins/Dimensions** | Declarative semantic models | Native query composition | Data schema + cube definitions |
| **Docker Support** | Via dbt-server | Community images | Official image |
| **License** | BSL (source available) | MIT | MIT (Core), EE available |

## MetricFlow: The dbt-Native Semantic Layer

MetricFlow is dbt Labs' semantic layer engine that defines metrics centrally in YAML alongside your dbt models. It ensures that every dashboard, notebook, and embedded analytics widget uses the same metric definition — eliminating the "two dashboards, two different revenue numbers" problem.

### Defining Metrics with MetricFlow

MetricFlow uses YAML semantic models that live alongside dbt models:

```yaml
semantic_models:
  - name: orders
    model: ref('stg_orders')
    entities:
      - name: order_id
        type: primary
      - name: customer_id
        type: foreign
    dimensions:
      - name: order_date
        type: time
        type_params:
          time_granularity: day
      - name: status
        type: categorical
    measures:
      - name: order_total
        agg: sum
        expr: amount
      - name: order_count
        agg: count
        expr: order_id

metrics:
  - name: revenue
    description: Total revenue from all orders
    type: simple
    label: Revenue
    type_params:
      measure: order_total
```

### Docker Deployment

```yaml
version: '3.8'
services:
  dbt-metrics:
    image: ghcr.io/dbt-labs/dbt-metricflow:latest
    container_name: metricflow
    ports:
      - "8580:8580"
    environment:
      - DBT_PROFILES_DIR=/dbt
      - DBT_PROJECT_DIR=/dbt/project
      - MF_CONFIG=/dbt/metricflow.yml
    volumes:
      - ./dbt:/dbt
      - ./profiles.yml:/dbt/profiles.yml
    restart: unless-stopped
```

MetricFlow's tight integration with dbt means that metric definitions live in the same repository as your data transformations, enabling code review and CI/CD for metric changes. The dbt Semantic Layer proxies queries from BI tools (Tableau, Looker, Power BI) through MetricFlow, translating them into optimized SQL against your warehouse.

## Malloy: The Analytical Query Language

Malloy takes a fundamentally different approach — instead of defining metrics in YAML and generating SQL, Malloy IS a query language. Developed by the team that created Looker's LookML (now at Google and Meta), Malloy compiles directly to SQL and was designed from the ground up for analytical workloads.

### Malloy Query Example

```malloy
source: orders is table('analytics.orders') {
  primary_key: order_id
  measure: revenue is sum(amount)
  measure: order_count is count()
  dimension: status is status
  dimension: order_month is order_date.month
  
  view: by_month is {
    group_by: order_month
    aggregate: revenue, order_count
  }
}

# Run a query
run: orders -> by_month
```

### Docker Deployment with Malloy Composer

```yaml
version: '3.8'
services:
  malloy-composer:
    image: ghcr.io/malloydata/malloy-composer:latest
    container_name: malloy-composer
    ports:
      - "4000:4000"
    environment:
      - MALLOY_DATABASE=postgres://user:pass@db:5432/analytics
      - MALLOY_SERVICE_ACCOUNT_KEY=/keys/service-account.json
    volumes:
      - ./malloy_models:/models
      - ./keys:/keys
    restart: unless-stopped
```

What sets Malloy apart is its query-first design. You write queries directly in Malloy syntax — no YAML abstraction layer, no separate metric definition file. The language handles complex analytical patterns natively: nested sub-queries, symmetric aggregates (handling fan-out correctly), and time-series analysis without window function boilerplate. For teams comfortable with SQL, Malloy reduces analytical code volume by 50-70%.

## Cube.js: The Battle-Tested Headless BI Platform

Cube.js is the most mature and widely deployed headless BI platform in the open-source ecosystem. It provides a complete API server with multi-level caching, query orchestration, and pre-aggregation capabilities that make it production-ready for high-concurrency analytics applications.

### Docker Deployment

```yaml
version: '3.8'
services:
  cube:
    image: cubejs/cube:latest
    container_name: cube
    ports:
      - "4000:4000"
    environment:
      - CUBEJS_DB_TYPE=postgres
      - CUBEJS_DB_HOST=db
      - CUBEJS_DB_NAME=analytics
      - CUBEJS_DB_USER=cube
      - CUBEJS_DB_PASS=cube_secret
      - CUBEJS_API_SECRET=your_secret_key
      - CUBEJS_DEV_MODE=false
    volumes:
      - ./schema:/cube/conf/schema
      - ./.cubestore:/cube/.cubestore
    depends_on:
      - cube-db
    restart: unless-stopped

  cube-db:
    image: postgres:15
    container_name: cube-db
    environment:
      POSTGRES_USER: cube
      POSTGRES_PASSWORD: cube_secret
      POSTGRES_DB: analytics
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped
```

Cube.js's pre-aggregation engine is its killer feature — it can materialize frequently queried metric combinations into rollup tables (or its own Cube Store), reducing query latency from seconds to milliseconds even over billion-row tables. The API supports REST, GraphQL, and SQL interfaces simultaneously, allowing any frontend tool to connect. Its multi-tenant architecture and row-level security make it suitable for embedded analytics in SaaS products.

## Choosing Your Semantic Layer

**MetricFlow** is the natural choice if you're already invested in the dbt ecosystem. Its tight integration with dbt models means metric definitions are version-controlled and tested alongside your transformations. The trade-off is that MetricFlow currently requires dbt Cloud or a self-hosted dbt Server for the full semantic layer API.

**Malloy** appeals to data teams who want maximum analytical expressiveness without abstraction layers. If your analysts are comfortable writing queries and you value flexibility over pre-built dashboards, Malloy's composable query language offers a compelling alternative to traditional semantic layers. The learning curve is steeper but the analytical power is greater.

**Cube.js** is the best choice for production applications that need high concurrency, low latency, and multi-tenant security. If you're embedding analytics in a customer-facing SaaS product or building a data-intensive dashboard that serves hundreds of concurrent users, Cube.js's proven architecture and caching layer are unmatched.

## Why Self-Host Your Semantic Layer?

A semantic layer defines the core truth of your business — revenue definitions, customer metrics, conversion rates. Hosting this logic on a third-party SaaS platform means your company's key performance indicators depend on an external service's uptime, pricing changes, and data access policies.

Self-hosting gives you complete control over metric computation, ensuring sensitive business data never leaves your infrastructure. When auditors ask how revenue is calculated, you can point to version-controlled YAML files (MetricFlow) or Malloy queries in your git repository — not a SaaS vendor's opaque calculation engine.

For analytics engineering teams, self-hosted semantic layers also mean faster iteration. You can A/B test metric changes in development branches, run CI/CD pipelines that validate metric definitions against test data, and roll back metric changes instantly without vendor change management processes. For related analytics infrastructure, see our [data pipeline orchestration guide](../2026-05-07-dagster-vs-airflow-vs-prefect-data-pipeline-orchestration-ui-guide/). If you're building a complete analytics stack, our [OLAP database comparison](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-olap-guide/) provides complementary guidance.

## FAQ

### Can Cube.js work with dbt models?

Yes, Cube.js integrates well with dbt. You can use dbt to transform and model data in your warehouse, then define Cube.js schemas on top of the resulting tables. Some teams generate Cube.js schemas automatically from dbt model metadata using tools like cube-dbt. This gives you dbt's transformation power with Cube's query performance.

### Does MetricFlow require dbt Cloud?

MetricFlow itself is open-source and can run locally, but the full semantic layer API (GraphQL/JDBC endpoints for BI tools) currently requires dbt Cloud or a self-hosted dbt Server. For fully self-hosted deployments, you can run MetricFlow CLI for metric validation and use the open-source proxy to serve metrics without dbt Cloud.

### How does Malloy handle large datasets compared to Cube.js?

Malloy pushes all computation to the underlying database (BigQuery, Postgres, DuckDB), so query performance depends on your warehouse's capabilities. Cube.js adds a pre-aggregation layer that materializes results for instant retrieval. For dashboards with high concurrency, Cube's pre-aggregations provide better performance; for exploratory analysis on well-optimized warehouses, Malloy's direct-to-DB approach works well.

### Can I switch from one semantic layer to another?

Migrating semantic layers requires translating metric definitions between formats — YAML (MetricFlow) ↔ Malloy ↔ JavaScript (Cube.js). While this is fundamentally a manual process, tools like dbt's semantic models provide a vendor-neutral metric specification that can potentially be consumed by multiple engines. If portability is a concern, define metrics using dbt's semantic layer format first, then choose the serving engine that fits your performance needs.

### Which is best for embedded analytics in a SaaS product?

Cube.js is the clear winner for embedded analytics. Its multi-tenant architecture, row-level security, JWT authentication, and pre-aggregation engine were designed specifically for this use case. Companies like DroneDeploy, Cloud Academy, and Apollo use Cube.js to power embedded analytics for thousands of customer tenants with isolated data access.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Headless BI: MetricFlow vs Malloy vs Cube.js for the Semantic Layer",
  "description": "A comprehensive comparison of open-source headless BI and semantic layer platforms — MetricFlow (dbt), Malloy, and Cube.js — covering metric definitions, query performance, deployment, and self-hosted analytics infrastructure.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
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
