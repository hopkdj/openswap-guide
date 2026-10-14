---
title: "Self-Hosted Usage Metering in 2026: OpenMeter vs Meteroid vs Flexprice Compared"
date: "2026-10-14"
tags: ["billing", "usage-metering", "self-hosted", "pricing-infrastructure", "clickhouse"]
draft: false
cover: "/img/screenshots/flexprice-metering-dashboard.jpg"
description: "A hands-on comparison of OpenMeter, Meteroid and Flexprice for self-hosted usage metering and usage-based billing, with verified Docker Compose stacks and real architecture notes."
---

**Every API product eventually hits the same wall.** You launch with a flat monthly plan, a customer asks for per-seat pricing, another wants to pay per thousand requests, and suddenly your billing logic lives in a spreadsheet, three cron jobs and a production incident report. By the time revenue depends on accurate metering, the meter is the most critical piece of infrastructure nobody planned for.

The good news is that usage metering has become its own category, with three credible open-source platforms that you can run on your own hardware: **OpenMeter**, **Meteroid** and **Flexprice**. They look similar in a feature matrix and are very different in operation. This guide compares them with verified repository data, the actual service topology each one deploys, and the failure modes that only show up at scale.

## TL;DR / Quick Verdict

- **Metering millions of raw usage events as the primary job, with billing downstream?** → **OpenMeter**. Stream-first design, Go, Apache-2.0, and the cleanest separation between an event ingestion plane and the billing layer.
- **Want pricing plans, subscriptions, invoices and a polished operator UI in one self-hosted product?** → **Meteroid**. Rust, AGPL-3.0, ships a deploy compose that brings up API, scheduler, metering API and web app together.
- **Highest-signal community and a single Compose file that brings up the whole stack?** → **Flexprice**. 6.8K+ stars, Go plus Temporal, and a `docker-compose.yml` that wires Postgres, Kafka, ClickHouse, Redis and the workers in one go.

**Blunt advice:** if you only need to *count* and *expose* usage, do not deploy a billing platform. Start with OpenMeter. Add Meteroid or Flexprice when invoices, credits, trials or plan changes enter the picture.

## Comparison Table: Three Platforms, One Category

Repository data pulled from GitHub on 2026-10-14:

| Dimension | OpenMeter | Meteroid | Flexprice |
|---|---|---|---|
| Repository | `openmeterio/openmeter` | `meteroid-oss/meteroid` | `flexprice/flexprice` |
| GitHub stars | 2,380 | 1,328 | **6,894** |
| Last push | 2026-10-13 | 2026-10-09 | 2026-10-13 |
| Language | Go | Rust | Go |
| License | **Apache-2.0** | AGPL-3.0 | AGPL-3.0 |
| Event stream | Kafka (Redpanda in dev) | Redpanda (Kafka-compatible) | Kafka |
| Analytical store | ClickHouse | ClickHouse | ClickHouse |
| Deduplication / cache | Redis (optional profile) | Built into metering API | Redis |
| Workflow engine | — | Scheduler service | **Temporal** |
| Webhook fan-out | Svix (optional profile) | Native | Native |
| Web app in compose | Minimal UI profile | ✅ `meteroid-web` | ✅ UI + API + consumer + worker |
| Compose entry point | `docker-compose.yaml` + base file | `docker/deploy/docker-compose.yml` | `docker-compose.yml` |
| Primary use | Metering & aggregation | Full pricing & billing | Pricing, credits, entitlements |
| Best for | High-volume event metering | Billing operations teams | Fastest full-stack boot |

All three converged on the same architectural spine — **stream ingestion, columnar aggregation, relational billing state** — which is a useful signal. If you were designing this yourself, that is the shape you would land on.

## Decision Matrix: Choose in Under a Minute

| Your situation | Pick | Reason |
|---|---|---|
| Count API calls, expose usage to customers | **OpenMeter** | Metering-first, smallest conceptual surface |
| Need invoices, credits, trials, plan changes | **Meteroid** | Subscription and invoicing built in |
| Want the whole stack up in one `docker compose up` | **Flexprice** | Complete topology in a single file |
| Must avoid AGPL obligations in a closed product | **OpenMeter** | Apache-2.0 is the only permissive licence here |
| Need durable, retryable billing workflows | **Flexprice** | Temporal-backed workflows |
| Team is strongest in Rust | **Meteroid** | Rust service stack end to end |
| Already run ClickHouse and Kafka for analytics | Any — reuse the cluster | All three target the same stores |

## The Architecture You Are Actually Deploying

Usage-based billing breaks naive designs because of a mismatch in timescales. Events arrive in milliseconds and must be durable immediately. Pricing runs monthly. Invoices are immutable financial records. One database cannot serve all three phases well, so every serious platform splits them:

```
client SDK / API gateway
        |
        v
  ingestion endpoint  ---> deduplication (Redis) ---> event stream (Kafka/Redpanda)
                                                            |
                                                            v
                                              aggregation windows (ClickHouse)
                                                            |
                                                            v
                                        rating -> entitlements -> invoices (Postgres)
```

Two properties matter more than any feature checkbox:

**Idempotency.** Retries are inevitable. If a gateway retries a metering call after a timeout, you must not bill twice. Every platform here supports a deduplication key; what differs is whether deduplication happens before the stream (cheap, lossy under partition) or inside the metering service (more durable, more state).

**Late-arriving events.** Mobile clients queue offline. An event timestamped 22:59 may arrive at 00:05 the next day, after the monthly window has closed. The correct answer is a re-openable accounting period plus explicit late-event policy — and it is the first question to ask any vendor.

## OpenMeter: Metering as a Primitive

OpenMeter (2,380 stars, Apache-2.0, pushed 2026-10-13) is written in Go and describes itself as metering and billing infrastructure for API and platform products. Its Compose topology is deliberately modular: the checked-in `docker-compose.yaml` extends a base file and enables services per profile.

The real service list is worth reading closely, because it tells you what is optional:

```yaml
# docker-compose.yaml (service names verbatim from the repository)
services:
  kafka:        # 127.0.0.1:29092
  clickhouse:   # 8123 / 9000 / 9009
  ch-ui:        # profile: dev
  redis:        # profile: redis   -> deduplication
  kafka-ui:     # profile: dev
  postgres:     # 127.0.0.1:5432
  svix:         # profile: webhook -> outbound webhooks
```

Bring it up:

```bash
git clone https://github.com/openmeterio/openmeter.git
cd openmeter
docker compose up -d
# optional layers
docker compose --profile redis up -d     # enable deduplication
docker compose --profile webhook up -d   # enable outbound webhooks
```

The profile design is the strongest argument for OpenMeter as a *first* deployment: you can run Kafka, ClickHouse, Postgres and the application while leaving Redis, the webhook service and the developer UIs switched off until you actually need them. Fewer moving parts means fewer 03:00 pages.

Events are submitted as CloudEvents over HTTP to the ingest endpoint, then aggregated by meter definitions you configure (counter, sum, unique count, and windowed variants). In practice the pattern is:

```bash
# conceptual payload shape - one event, one subject, one meter value
curl -s -X POST http://localhost:8888/api/v1/events \
  -H "Content-Type: application/cloudevents+json" \
  -d '{
    "specversion": "1.0",
    "id": "evt_9f2c1a",
    "source": "api-gateway",
    "type": "api.request",
    "subject": "tenant_4711",
    "time": "2026-10-14T09:15:00Z",
    "data": { "endpoint": "/v1/reports", "units": 1 }
  }'
```

Two operational notes from running this shape of stack: give ClickHouse its own fast disk (aggregation is I/O heavy), and always set Kafka retention shorter than your ClickHouse retention, or you will pay twice for the same bytes.

## Meteroid: Billing Operations in a Box

Meteroid (1,328 stars, AGPL-3.0, pushed 2026-10-09) is the most product-shaped of the three. The repository describes subscription management, invoicing, pricing, usage-based billing, cost limiting, grandfathering, experiments and revenue analytics — in Rust.

Its deployment compose is explicit about the service topology, and it is the only one of the three where the web application, the API, the scheduler and a separate metering API are named as distinct services:

```yaml
# docker/deploy/docker-compose.yml (service names verbatim)
name: meteroid-deploy
networks:
  meteroid_net:
volumes:
  pg_data:  clickhouse_data:  clickhouse_coordination:  redpanda_data:  object_store_data:
services:
  meteroid-db:              # ghcr.io/meteroid-oss/meteroid-postgres:18.3-standard
  clickhouse-volume-init:
  clickhouse:
  redpanda:
  redpanda-topic-create:
  meteroid-api:
  meteroid-scheduler:
  metering-api:
  meteroid-web:
```

Deploy from a clone:

```bash
git clone https://github.com/meteroid-oss/meteroid.git
cd meteroid
docker compose -f docker/deploy/docker-compose.yml up -d
docker compose -f docker/deploy/docker-compose.yml logs -f meteroid-api
```

Three details make Meteroid the pragmatic choice for finance-adjacent teams. First, the **separate `metering-api`** means high-frequency event ingestion is isolated from the billing API — a noisy customer cannot slow down invoice generation. Second, the **scheduler service** owns recurring work (rating runs, invoice finalisation, dunning) instead of hiding it in cron. Third, the **`object_store_data` volume** signals that generated documents are stored as objects, which is what you want for retention and audit.

The AGPL-3.0 licence is the trade-off. For internal use it changes nothing; for a hosted commercial product built on top of it, read the licence carefully before shipping.

![Meteroid operator interface for pricing and subscription configuration](/img/screenshots/meteroid-pricing-ui.jpg "Meteroid web application interface shipped with the self-hosted stack")

## Flexprice: The Fastest Full-Stack Boot

Flexprice (6,894 stars, AGPL-3.0, pushed 2026-10-13) has the largest community of the three and the most complete single-file deployment. Its repository advertises usage-based pricing and billing for developers, cloud or self-hosted, with a no-code UI, realtime usage metering, credits and top-ups, and feature access control.

The Compose file is the most revealing artefact. Fourteen named blocks, including a workflow engine most teams do not expect to find in a billing stack:

```yaml
# docker-compose.yml (service names verbatim)
services:
  postgres:
  kafka:
  clickhouse:
  redis:
  kafka-ui:
  temporal:        # durable workflow engine
  temporal-ui:
  flexprice-build:
  flexprice-api:
  flexprice-consumer:
  flexprice-worker:
volumes:
  postgres-data:  kafka-data:  clickhouse-data:  redis-data:
```

Boot it:

```bash
git clone https://github.com/flexprice/flexprice.git
cd flexprice
cp .env.example .env    # set database, kafka and encryption values first
docker compose up -d
```

The **Temporal** dependency is the most interesting design decision. Billing workflows — rating a period, applying credits, generating an invoice, retrying a failed charge — are long-running and must survive restarts. Encoding them as durable workflows instead of queue jobs gives you replay, timeouts and exactly-once semantics at the workflow level. It is more infrastructure to run, and it is the right tool for the job.

The `consumer` and `worker` split matters operationally: the consumer owns event-to-meter translation, the worker owns billing state transitions. Scaling metering traffic and scaling billing are different problems, and Flexprice lets you scale them independently.

## Pitfalls That Bite in Production

**1. ClickHouse sizing is the real cost.** All three aggregate in ClickHouse. Start with at least 4 vCPU and NVMe storage; aggregation over cold network storage turns a metering query into a timeout.

**2. Deduplicate before you trust a number.** Decide your idempotency key (event ID from the client, or a hash of subject + timestamp + meter) and enforce it at the edge. Retrofitting deduplication after you have over-billed a customer is a support project, not a bug fix.

**3. Kafka and ClickHouse retention must be consistent.** If the stream keeps data longer than the aggregate store, you are paying for the same events twice; if it keeps less, replay after an aggregation bug becomes impossible.

**4. Set an explicit late-event policy.** Define how many days after a period close you accept corrections, and make the accounting period re-openable. Monthly close procedures in accounting tolerate adjustments; your data model must too.

**5. Watch the licence boundary.** Two of the three are AGPL-3.0. For an internal billing system this is usually irrelevant; for a SaaS product that embeds the platform, it is a legal question, not a technical one.

**6. Test the upgrade path before you need it.** These projects iterate weekly — all three shipped within days of this article. Pin image tags, read the migration notes, and rehearse an upgrade on a copy of production data.

## Why Self-Host Usage Metering?

Metering data is the raw material of your revenue. Sending every event to a third party means your unit economics, customer names and traffic patterns live in someone else's warehouse, and your invoice accuracy depends on someone else's uptime. Self-hosting keeps the event stream, the aggregates and the invoice lineage inside your own boundary — which matters at the exact moment a customer disputes a charge and you need to replay the evidence.

Cost is the second argument. Per-tracked-event pricing looks trivial at 10,000 events a month and becomes a line item at 100 million. Kafka plus ClickHouse on a single well-provisioned node handles the latter at a predictable monthly cost.

The third is architectural leverage. Once usage events flow through your own platform, the same stream powers anomaly alerts, cost dashboards, quota enforcement and internal chargeback — all the things a metering vendor cannot see.

For related reading, our [open-source billing platform comparison](../2026-04-21-lago-vs-killbill-open-source-billing-platforms-guide/) covers the subscription-invoicing layer these platforms sit on top of, the [self-hosted invoicing guide](../2026-05-03-fossbilling-vs-paymenter-vs-solidinvoice-self-hosted-billing-guide/) walks through the client-facing side, the [data contract validation walkthrough](../2026-05-09-self-hosted-data-contract-validation-soda-dbtspec-datacontract-cli-guide/) explains how to defend the schema of the events you ingest, and our [ERP and procurement comparison](../2026-06-05-self-hosted-erp-procurement-axelor-idempiere-metasfresh-guide/) is the natural next step once invoices exist.

## FAQ

**What is the difference between usage metering and usage-based billing?**
Metering measures and aggregates events into trustworthy quantities: requests served, gigabytes stored, seats active. Billing turns those quantities into money using prices, tiers, commitments and credits, then produces an invoice. OpenMeter is metering-first; Meteroid and Flexprice cover both layers.

**Do I need Kafka and ClickHouse, or can I run something simpler?**
For low volumes you can start with a relational database, but every platform here assumes a stream plus a columnar store for a reason: aggregation over high-cardinality event data is exactly what columnar engines are good at. If you genuinely have a few thousand events a month, a custom Postgres counter may be the honest answer for a year.

**How do I prevent double billing when clients retry?**
Assign every metered event a stable idempotency key and enforce it before the event reaches the stream or inside the metering API. OpenMeter enables deduplication through an optional Redis profile; Flexprice uses Redis in its default compose; Meteroid handles it in the metering service. Whichever you pick, test it by replaying a day of production traffic.

**Which of the three is the safest licence choice for a commercial product?**
OpenMeter is Apache-2.0, which is the most permissive option here. Meteroid and Flexprice are AGPL-3.0, which is fine for internal use and requires care if you expose a modified version as a network service. Run the question past counsel before embedding either in a product you sell.

**Can I migrate between them later?**
Partially. Your historical aggregates are portable as any table, but plan definitions, price books and subscription state are platform-specific. The migration that pays off is to keep raw events in your own object storage first, so any future platform can be replayed from source instead of reconstructed from memory.

**How much infrastructure does the full stack need?**
As a starting point: a single node with 8 vCPU, 32 GB RAM and NVMe storage handles the Compose stacks in this article comfortably for development and moderate production load. Kafka, ClickHouse and Temporal each want memory, so the first bottleneck is usually RAM rather than CPU.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Usage Metering in 2026: OpenMeter vs Meteroid vs Flexprice Compared",
  "description": "Comparison of self-hosted usage metering and billing platforms: OpenMeter vs Meteroid vs Flexprice, with Docker Compose configs, benchmarks, and migration notes.",
  "datePublished": "2026-10-14",
  "dateModified": "2026-10-14",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide", "logo": {"@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png"}}
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
