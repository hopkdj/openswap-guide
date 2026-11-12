---
title: "Arroyo vs Feldera vs RisingWave in 2026: Which Streaming SQL Engine Should You Actually Run?"
date: "2026-11-13"
tags: ["streaming", "data-engineering", "self-hosted", "sql", "comparison"]
draft: false
cover: "/img/screenshots/risingwave-console.jpg"
description: "Hands-on comparison of Arroyo, Feldera and RisingWave as self-hosted streaming SQL engines — real Docker configs, SQL dialects, state management and the operational traps that bite in production."
---

Your dashboards are already one minute behind reality, and someone in finance just asked for "revenue by customer, refreshed continuously." You have Kafka, you have a Postgres, and you have three open-source engines that all promise the same thing: **write SQL, get continuously updated results**. Pick one, and you will live with its state model, its failure semantics and its upgrade path for years.

The three credible open-source answers in 2026 are **Arroyo** (5,077 GitHub stars, Rust, last push 2026-11-12), **Feldera** (2,165 stars, incremental computation engine) and **RisingWave** (9,411 stars, Postgres-wire-compatible). They look interchangeable in a feature matrix. Operationally they are about as different as three databases can be.

## TL;DR — the 30-second verdict

- **Run RisingWave** if your team already thinks in Postgres. You get a Postgres-compatible wire protocol, materialized views, and every BI tool you own just connects. It is the lowest-friction choice for a team of five.
- **Run Arroyo** if you want the smallest possible footprint and a pipeline editor your analysts can actually click through. A single Rust binary plus object storage, no JVM, no compaction service to babysit.
- **Run Feldera** if your problem is *recomputation*, not streaming. Feldera keeps a standing incremental view current across arbitrary SQL, including joins and aggregates, and it is the only one of the three that treats "what if the input changed retroactively" as a first-class question.

## The comparison table (data pulled from GitHub on 2026-11-13)

| Dimension | Arroyo | Feldera | RisingWave |
|---|---|---|---|
| GitHub stars | 5,077 | 2,165 | 9,411 |
| Last push | 2026-11-12 | 2026-11-12 | 2026-11-12 |
| Implementation | Rust | Rust | Rust |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Query surface | Custom SQL dialect + pipeline API | SQL (`CREATE VIEW` over tables) | PostgreSQL wire protocol |
| State storage | Object storage (S3-compatible) | Embedded / object storage for checkpoints | Hummock on S3 or MinIO |
| Metadata store | Built in (SQLite or Postgres) | Postgres-compatible | Postgres or SQLite |
| Kafka in / out | Yes | Yes | Yes |
| Postgres CDC | Yes | Yes | Yes |
| Exactly-once sinks | Yes | Yes (checkpointed) | Yes |
| Dashboard shipped | Yes, with visual pipeline editor | Yes, web console | Yes (`:5691`) |
| Operational unit | 1 container | 2 containers (manager + runner) | 1 container standalone, 3+ in cluster |
| Fits a 4 GB VPS | Yes | Tight | Yes (standalone, small parallelism) |

## Decision matrix: pick by use case, not by feature list

| Your situation | Recommended engine | Why |
|---|---|---|
| BI tools must connect with a Postgres driver | **RisingWave** | Anything that speaks the Postgres protocol works: Metabase, Grafana, psql, dbt |
| Analysts should build pipelines visually | **Arroyo** | The UI is a pipeline graph editor, not a SQL console with a graph stapled on |
| Fraud or pricing rules that must re-evaluate on every event | **Feldera** | Standing incremental views over joins and aggregates, recomputed as inputs move |
| You want the fewest moving parts on one box | **Arroyo** | One image, object storage, done |
| You need `CREATE MATERIALIZED VIEW` semantics you already understand | **RisingWave** | The mental model is a Postgres materialized view that never goes stale |
| You need to backfill 3 years of history and keep the view live | **Feldera** or **RisingWave** | Both handle historical + live input without a separate batch path |

## Arroyo — the smallest footprint that still scales out

Arroyo compiles SQL into a distributed dataflow and runs workers that checkpoint state to object storage. The whole thing ships as a single container image, and the image is real: `ghcr.io/arroyosystems/arroyo:latest` resolves on GHCR today, so you are not depending on a stale Docker Hub tag.

```yaml
# docker-compose.yml — Arroyo, single node
services:
  arroyo:
    image: ghcr.io/arroyosystems/arroyo:latest
    restart: unless-stopped
    ports:
      - "8000:8000"   # web UI + pipeline editor
      - "8001:8001"   # REST API
    environment:
      RUST_LOG: "info"
    volumes:
      - arroyo-data:/data

volumes:
  arroyo-data:
```

Pipelines are plain SQL. A source table, a watermark, and an aggregate are enough to get a live result set:

```sql
CREATE TABLE orders (
  order_id    BIGINT,
  customer_id BIGINT,
  amount      DECIMAL(10,2),
  event_time  TIMESTAMP(3),
  WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
  connector        = 'kafka',
  topic            = 'orders',
  format           = 'json',
  type             = 'source',
  bootstrap_servers = 'kafka:9092'
);

SELECT customer_id,
       SUM(amount)  AS revenue,
       COUNT(*)     AS order_count
FROM orders
GROUP BY customer_id;
```

The watermark is the part people skip. Without it, Arroyo buffers state forever waiting for late events that will never arrive — memory climbs, checkpoints get enormous, and the first person to notice is whoever is on call at 3am. Set the watermark to a value larger than your worst measured producer lag, not to a number that looks tidy.

Where Arroyo wins is operational honesty. One process, one state directory, one UI. Where it costs you is dialect churn: the SQL surface is Arroyo's own, so anything you learn does not transfer to another engine, and `hop`-style windowing is not the same syntax you would write in Flink.

## Feldera — incremental computation, not "streaming with extra steps"

Feldera's pitch is different enough that comparing it line-by-line with the other two misses the point. You define tables and views in SQL, and Feldera keeps every view continuously consistent with the current contents of the tables — including when the table is fed from Kafka, from a historical backfill, or from both at once.

The deployment file below is trimmed from the project's own `deploy/docker-compose.yml`, which is the source of truth:

```yaml
# docker-compose.yml — Feldera pipeline manager (from deploy/docker-compose.yml)
name: feldera
services:
  pipeline-manager:
    tty: true
    image: images.feldera.com/feldera/pipeline-manager:${FELDERA_VERSION:-latest}
    ports:
      - "8080:8080"
    stop_grace_period: 0s
    environment:
      - RUST_LOG=info,actix_web=error,tokio_postgres=info
      - RUST_BACKTRACE=1
    healthcheck:
      test: ["CMD-SHELL", "curl --fail --request GET --url http://localhost:8080/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
```

That single service is the control plane: the web console on `:8080` where you define pipelines, attach connectors and watch throughput. The full compose file also carries a Redpanda profile (`profiles: ["redpanda"]`) so you can bring a broker up in the same stack for evaluation.

The SQL is the reason to choose Feldera. Views are declarative and the engine maintains them incrementally:

```sql
CREATE TABLE orders (
  order_id    BIGINT,
  customer_id BIGINT,
  amount      DECIMAL(10,2),
  event_time  TIMESTAMP
);

CREATE VIEW customer_revenue AS
SELECT customer_id,
       SUM(amount) AS revenue,
       COUNT(*)    AS order_count
FROM orders
GROUP BY customer_id;

CREATE VIEW high_value AS
SELECT o.customer_id, o.order_id, o.amount
FROM orders o
JOIN customer_revenue r ON r.customer_id = o.customer_id
WHERE o.amount > 500 AND r.revenue > 10000;
```

`high_value` is a join between a stream and an aggregate of that same stream. In a hand-rolled streaming stack this is where you write a stateful operator, discover that the join needs both sides keyed identically, and spend a week on watermarks. Feldera treats it as a view definition.

![Feldera pipeline status view showing throughput and checkpoint health](/img/screenshots/feldera-pipeline-status.jpg)

The trade-off is real: two processes instead of one, a heavier console, and a learning curve around what "incremental" costs when a view is expensive to maintain. A view that is cheap to write can be expensive to keep current — every row that arrives touches every downstream aggregate. Benchmark *your* views, not a demo.

## RisingWave — Postgres semantics for people who do not want a new dialect

RisingWave's superpower is boring and enormous: it speaks the PostgreSQL wire protocol. Your existing `psql` muscle memory works, Metabase connects without a driver hunt, and `dbt` can point at it. Under the hood it stores state in Hummock on S3/MinIO, with a separate compactor.

The documented single-node start is one command, and the compose equivalent pins the same image tag:

```bash
docker run -it --pull=always \
  -p 4566:4566 \
  -p 5691:5691 \
  risingwavelabs/risingwave:v3.0.0 standalone
```

```yaml
# docker-compose.yml — RisingWave standalone
services:
  risingwave:
    image: risingwavelabs/risingwave:v3.0.0
    command: standalone
    restart: unless-stopped
    ports:
      - "4566:4566"   # Postgres-compatible endpoint
      - "5691:5691"   # dashboard
    volumes:
      - rw-data:/risingwave

volumes:
  rw-data:
```

Then it is just Postgres:

```sql
CREATE SOURCE orders (
  order_id    BIGINT,
  customer_id BIGINT,
  amount      NUMERIC,
  event_time  TIMESTAMPTZ
) WITH (
  connector = 'kafka',
  topic = 'orders',
  properties.bootstrap.server = 'kafka:9092',
  format = 'json'
) FORMAT PLAIN ENCODE JSON;

CREATE MATERIALIZED VIEW customer_revenue AS
SELECT customer_id,
       SUM(amount) AS revenue,
       COUNT(*)    AS order_count
FROM orders
GROUP BY customer_id;
```

Query `customer_revenue` from any Postgres client and you get the current answer, not a snapshot from last night. That single property — materialized views that are always warm — is why RisingWave has the largest community of the three.

The hidden cost is cluster shape. Standalone mode is fine for evaluation, but the moment you want parallelism you are running a meta node, compute nodes and a compactor, each with memory targets that must be tuned against each other. If you size compute for bursts and forget the compactor, background compaction becomes your bottleneck and query latency drifts upward with no obvious cause in the logs.

## Pitfalls nobody puts in the quickstart

**1. State size is your real bill.** All three checkpoint state to object storage. A `GROUP BY` with high cardinality — think `GROUP BY user_id` across millions of users — turns into a state store measured in gigabytes per node. Add a `TUMBLE` window or a TTL before you go to production, not after.

**2. Kafka partition count caps your parallelism.** If your topic has three partitions, no engine will give you four parallel readers on that source. Re-partition upstream or accept the ceiling.

**3. Exactly-once is a property of the sink, not the engine.** Kafka sinks with transactional writes and idempotent upserts into Postgres behave differently. Test the failure path by killing the container mid-checkpoint, then verify row counts — this is the only test that matters.

**4. Backfills compete with live traffic.** Feeding three years of history into a running pipeline will saturate the same CPU that serves your live views. Schedule it, throttle it, or use a separate pipeline instance.

**5. Do not benchmark with `SELECT *`.** Streaming engines are optimized for incremental maintenance. Ad-hoc full scans against a large materialized view measure something else entirely and will mislead you into the wrong choice.

**6. Upgrades need a checkpoint plan.** All three evolve their state formats. Read the release notes for the version you are jumping to, and take a fresh checkpoint before you pull the new image. Rolling back a state format is not a supported operation anywhere in this space.

## Which one should you actually install?

If you have one evening and a laptop: start with **RisingWave** standalone. It is the fastest way to see whether streaming SQL solves your problem at all, and everything you learn transfers to a production cluster.

If you are building for analysts who will own the pipelines after you leave: choose **Arroyo**. The pipeline editor is the differentiator, and a single container is a gift to whoever inherits the on-call rotation.

If your requirement is that a complex multi-join view stays correct while inputs change — pricing, risk, allocation, anything with a "recompute" flavour — choose **Feldera**. It is the only one of the three where that is the design centre rather than a supported use case.

Whichever you pick, wire it to a real sink in week one. A streaming engine with no downstream consumer is a science project, and the operational lessons only arrive when something is genuinely reading the output.

## Related reading

If you are still deciding how the storage layer fits together, our [streaming database comparison](../2026-04-23-risingwave-vs-materialize-vs-ksqldb-self-hosted-streaming-databases-guide-2026/) covers the query-engine landscape one level up. For batch-plus-stream architectures, the [data processing engines guide](../2026-05-14-self-hosted-data-processing-engines-databend-vs-datafusion-vs-ballista-guide-2026/) explains where DataFusion and Ballista stop and a streaming engine begins. And if your pipeline writes Iceberg tables, the [Iceberg REST catalog comparison](../2026-10-21-iceberg-rest-catalogs-polaris-lakekeeper-gravitino-guide-2026/) is the piece that keeps three engines from forking your lake.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Arroyo vs Feldera vs RisingWave in 2026: Which Streaming SQL Engine Should You Actually Run?",
  "description": "Hands-on comparison of Arroyo, Feldera and RisingWave as self-hosted streaming SQL engines — real Docker configs, SQL dialects, state management and operational traps.",
  "datePublished": "2026-11-13",
  "dateModified": "2026-11-13",
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

## FAQ

**Is Arroyo a full replacement for Apache Flink?**
For SQL pipelines over Kafka with object-storage checkpoints, largely yes, and with a fraction of the operational weight. Flink still wins where you need its broader connector catalogue, its mature savepoint tooling, or an existing team that already runs Flink clusters. Arroyo's advantage is that a single container is a complete deployment.

**Can Feldera consume from Kafka, or is it batch only?**
Feldera is not batch only. It attaches Kafka input and output connectors to tables and views through its console, and it is specifically designed to combine a historical backfill with live input so the views stay consistent across both. The distinction is that Feldera maintains views incrementally rather than executing a periodic query.

**Does RisingWave really work with normal Postgres clients?**
Yes. RisingWave exposes a PostgreSQL-compatible endpoint on port 4566, so `psql`, Grafana, Metabase and most Postgres drivers connect directly. Some Postgres-specific features — extensions, certain catalog queries, and write-heavy OLTP patterns — are not supported, so treat it as an analytics endpoint rather than a drop-in primary database.

**How much RAM does each engine need to start?**
All three run in roughly 2 GB for a small evaluation pipeline, and all three will use everything you give them once state grows. Arroyo and RisingWave standalone are comfortable in a 4 GB VM; Feldera's manager plus runner is tighter and benefits from 8 GB. Plan for memory to be consumed by state, not by the binary.

**Which engine handles late-arriving events best?**
Each has an explicit answer and you must configure it. Arroyo uses watermarks declared on the source table; RisingWave uses watermark definitions on sources and window clauses; Feldera accepts out-of-order input and reconciles the views as records arrive. In practice, the quality of your result depends far more on whether you set a watermark at all than on which engine you chose.

**Can I migrate from one to another later?**
The SQL is not portable. Arroyo's dialect, Feldera's view model and RisingWave's Postgres-compatible SQL overlap on the basics (`SELECT`, `JOIN`, `GROUP BY`) and diverge on windows, connectors and state declarations. Budget a rewrite of the pipeline definitions, not a find-and-replace.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
