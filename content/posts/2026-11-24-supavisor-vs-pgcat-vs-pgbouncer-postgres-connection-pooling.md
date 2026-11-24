---
title: "Supavisor vs PgCat vs PgBouncer in 2026: Which Postgres Pooler Survives a Connection Storm?"
date: "2026-11-24"
tags: ["postgresql", "database", "pgbouncer", "supavisor", "pgcat", "performance"]
draft: false
cover: "/img/screenshots/supavisor-architecture.jpg"
description: "Supavisor, PgCat and PgBouncer compared for 2026: multi-tenant pooling, transaction-mode caveats, real config files, sizing math and migration pitfalls."
---

Postgres does not fail because a query is slow. It fails because 3,000 application processes each opened a connection, and the backend is now spending more time forking, authenticating and context-switching than executing SQL. One connection per client is fine for a monolith. It is a denial-of-service attack when your workloads are serverless functions, a few hundred tenant containers, or a Kubernetes deployment that scales to 80 pods during a traffic spike.

A pooler sits between the application and Postgres, holds a small number of real backend connections, and multiplexes thousands of clients onto them. Three projects matter in 2026, and they are not interchangeable:

- **PgBouncer** — 4,460 stars, the classic, C, tiny, and still the default answer.
- **PgCat** — 4,039 stars, Rust, with sharding, load balancing and failover built in.
- **Supavisor** — 2,288 stars, Elixir, designed for multi-tenant Postgres with thousands of distinct databases.

Here is what each one actually does, with real configuration from their repositories, and the failure modes that bite in production.

## TL;DR — the verdict

- **One Postgres cluster, many app pods, you need connection multiplexing today:** use **PgBouncer**. It is 20 years old, ~1 MB of RAM per pool, has zero dependencies, and every managed Postgres provider has a recipe for it. Set `pool_mode = transaction` and be done.
- **Multiple Postgres shards, read replicas, or failover you want the pooler to handle:** use **PgCat**. It speaks the Postgres wire protocol, routes by shard key, balances across replicas, and exposes Prometheus metrics on a separate port.
- **Thousands of tenants, each with its own database, or serverless clients that cannot use a long-lived TCP connection:** use **Supavisor**. It was built for exactly the multi-tenant case that makes PgBouncer's one-pool-per-database model painful.

If you only remember one line: **PgBouncer for one cluster, PgCat for many nodes, Supavisor for many tenants.**

## Comparison table

GitHub figures pulled live on 2026-11-24.

| Dimension | PgBouncer | PgCat | Supavisor |
|---|---|---|---|
| Stars | 4,460 | 4,039 | 2,288 |
| Last push | 2026-11-20 | 2025-02-27 | 2026-11-23 |
| Language | C | Rust | Elixir/Erlang |
| Pool modes | session, transaction, statement | transaction (session planned) | session, transaction |
| Multi-database support | One pool section per database | Yes, via `[databases]` mapping | Native multi-tenant, thousands of tenants |
| Sharding | No | Yes (sharding key) | No |
| Read/write split | No | Yes (`primary`, `replica`) | No |
| Failover awareness | No | Yes (health checks, ban time) | Cluster-aware for its own nodes |
| Metrics | `SHOW` commands, exporter needed | Built-in Prometheus on separate port | Prometheus endpoint |
| Config format | INI | TOML | Environment variables |
| Admin interface | `psql -p 6432 pgbouncer` console | TOML + admin DB | HTTP API + dashboard |
| Container image | `edoburu/pgbouncer`, distro packages | Build from repo / community images | Self-host or Supabase Cloud |
| Best fit | Single cluster, classic stacks | Sharded / replicated clusters | Multi-tenant SaaS platforms |

## Decision matrix

| Your situation | Pick | Why |
|---|---|---|
| Django/Rails/Node app + one Postgres primary | PgBouncer | Smallest footprint, universal docs |
| 10–500 pods connecting to one cluster | PgBouncer | Transaction mode solves the pod-storm problem |
| Citus or manual sharding across N primaries | PgCat | Shard routing in the wire protocol |
| Need read replicas behind one endpoint | PgCat | Built-in replica selection |
| 5,000 tenant databases on shared infrastructure | Supavisor | Tenant-addressed pooling without 5,000 pool sections |
| Serverless functions (Lambda, Edge) connecting directly | Supavisor | Built for high-churn short-lived clients |
| Air-gapped box, no container runtime | PgBouncer | Single static binary, distro packages |
| Need LISTEN/NOTIFY, advisory locks, cursors | PgBouncer in session mode | Transaction pooling breaks session state |
| You want Prometheus metrics without an exporter | PgCat | `enable_prometheus_exporter = true` |

## PgBouncer: the pooler nobody gets fired for choosing

PgBouncer's config is a single INI file and it has barely changed in a decade, which is the point. The keys that matter for production are in `[pgbouncer]`:

```ini
[databases]
payments = host=10.0.0.11 port=5432 dbname=payments
analytics = host=10.0.0.12 port=5432 dbname=analytics

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt

; transaction pooling: connections return to the pool at COMMIT
pool_mode = transaction
max_client_conn = 5000
default_pool_size = 40
min_pool_size = 10
reserve_pool_size = 10
reserve_pool_timeout = 5
server_idle_timeout = 600
server_lifetime = 3600
query_wait_timeout = 120
log_connections = 1
log_disconnections = 1
```

Deploying it on a host that already runs Postgres:

```bash
apt install pgbouncer
# point the app at 6432 — Postgres itself stays on 5432, ideally firewalled
psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer -c "SHOW POOLS;"
```

The `SHOW POOLS` output is the only dashboard you need on day one: `cl_active` (clients running a query), `cl_waiting` (clients queued for a server connection), `sv_active`, `sv_idle`. If `cl_waiting` grows while `sv_idle` is zero and Postgres is not CPU-saturated, your `default_pool_size` is too small for the query rate — or a long-running query is holding a server connection hostage.

What PgBouncer does not do: it knows nothing about replicas, shards, or which backend is healthy beyond a TCP connect. It is a multiplexer, not a router. If your architecture is one primary and you are not planning sharding, that is a feature.

## PgCat: routing and failover in the pooler

PgCat keeps PgBouncer's wire-protocol compatibility but adds the layer PgBouncer deliberately omits. Its TOML config has a `[general]` section with real operational knobs from the repository's own example:

```toml
[general]
host = "0.0.0.0"
port = 6432
enable_prometheus_exporter = true
prometheus_exporter_port = 9930
connect_timeout = 5000
healthcheck_timeout = 1000
healthcheck_delay = 30000
shutdown_timeout = 60000
ban_time = 60
log_client_connections = false
log_client_disconnections = false
```

Those five timing values are the whole operational story. `healthcheck_timeout = 1000` means a replica that takes longer than a second to answer `SELECT 1` is marked down. `ban_time = 60` keeps it out of rotation for a minute, so a flapping replica does not receive a trickle of failing queries. `shutdown_timeout = 60000` gives clients a full minute to finish during a rolling restart — good for graceful deploys, bad if you expect fast restarts.

The official compose file is minimal, which makes it easy to try:

```yaml
version: "3"
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_HOST_AUTH_METHOD: md5
  pgcat:
    build: .
    command:
      - "pgcat"
      - "/etc/pgcat/pgcat.toml"
    volumes:
      - "${PWD}/examples/docker/pgcat.toml:/etc/pgcat/pgcat.toml"
    ports:
      - "6432:6432"
      - "9930:9930"
```

The honest caveat is maintenance. PgCat's last push on GitHub was **2025-02-27** — over a year before this article. It is not abandoned in the sense of being broken (the wire protocol is stable), but it is not receiving the steady drip of fixes PgBouncer and Supavisor are. If your architecture depends on shard routing, budget for the possibility of maintaining your own fork or pinning to a known-good release and watching the issue tracker.

## Supavisor: pooling for platforms, not applications

Supavisor starts from a different assumption: the number of *databases* is large, and clients come and go constantly. Instead of a static INI listing every database, tenants are addressed by a composite username (`tenant.orchestrator` style) resolved at connect time, and the pooler itself is a clustered Elixir application with its own metadata database.

Its development compose file shows the whole architecture in 25 lines:

```yaml
version: "3"

services:
  db:
    image: supabase/postgres:15.1.0.148
    container_name: supavisor-db
    ports:
      - "6432:5432"
    volumes:
      - ./dev/postgres:/docker-entrypoint-initdb.d/
    command: postgres -c config_file=/etc/postgresql/postgresql.conf -c max_prepared_transactions=2000
    environment:
      POSTGRES_HOST: /var/run/postgresql
      POSTGRES_PASSWORD: postgres

  supavisor:
    build: .
    container_name: supavisor
    ports:
      - 4000:4000
      - 5452:5452
      - 6543:6543
    environment:
      PORT: 4000
      PROXY_PORT_SESSION: 5452
      PROXY_PORT_TRANSACTION: 6543
      DATABASE_URL: "ecto://postgres:postgres@db:5432/postgres"
      CLUSTER_POSTGRES: "true"
      SECRET_KEY_BASE: "replace-with-64-bytes-of-random-hex"
      VAULT_ENC_KEY: "replace-with-32-bytes-of-random-hex"
      API_JWT_SECRET: "replace-me"
      METRICS_JWT_SECRET: "replace-me"
      REGION: "local"
      ERL_AFLAGS: -proto_dist inet_tcp
    command: sh -c "/app/bin/migrate && /app/bin/server"
    depends_on:
      - db
```

Three ports, three jobs: `4000` is the HTTP API and dashboard, `5452` is session-mode pooling, `6543` is transaction-mode pooling. Note that `SECRET_KEY_BASE` and `VAULT_ENC_KEY` are mandatory secrets — Supavisor stores tenant credentials encrypted, so losing `VAULT_ENC_KEY` means losing the ability to connect tenants, exactly like losing an encryption key in any secrets platform.

![Supavisor architecture: tenant routing, cluster metadata and pooled Postgres backends](/img/screenshots/supavisor-architecture.jpg "Supavisor's architecture — a clustered pooler with tenant metadata stored in its own Postgres")

Supavisor is the only one of the three with a cluster topology of its own: nodes register in the metadata database, and clients can be routed to a node that holds a pool for their tenant. That is what makes thousands of tenants feasible; it is also why operating it well requires understanding Erlang distribution, the metadata schema, and the difference between session and transaction proxy ports.

## The pitfalls that actually cause outages

**1. Transaction pooling breaks session state.** In `pool_mode = transaction`, a server connection is assigned per transaction. Anything that assumes a stable session — `SET search_path`, temp tables, `LISTEN`/`NOTIFY`, advisory locks held across statements, server-side cursors, `PREPARE`d statements created outside the transaction — will silently misbehave or fail. Check your ORM: some drivers cache prepared statements at the session level and must be told to disable that.

**2. `pool_mode = statement` is a trap.** It sounds like free multiplexing but forbids multi-statement transactions entirely, which breaks almost every ORM migration and most application code. Use it only for pure read-only analytics endpoints.

**3. Sizing math is about concurrency, not clients.** `default_pool_size` should be roughly `(cores × 2) + effective_spindle_count` divided across poolers, and it must stay below Postgres's `max_connections` minus admin headroom. If you run 8 app pods each with their own PgBouncer, you have 8 pools — size each one for a fraction of the total, or you will recreate the connection storm one layer down.

**4. `query_wait_timeout` saves you from yourself.** Set it. Without a timeout, clients queue forever behind a single slow query, liveness probes fail, and Kubernetes kills pods that were healthy. A 30–120 second cap converts an outage into a burst of fast errors your retry logic can handle.

**5. Auth mode mismatches cause the most confusing failures.** If Postgres uses `scram-sha-256`, the pooler must either hold credentials it can verify (`auth_type = scram-sha-256` with a userlist) or pass through to the server (`auth_type = passthrough`/`any` depending on the pooler). A mismatch presents as "password authentication failed" for users whose passwords are demonstrably correct.

**6. Migrations should bypass the pooler.** Run schema migrations against a direct connection, not through transaction pooling. DDL under transaction mode with `PREPARE` caching is a well-known source of "prepared statement already exists" errors. If you need help there, our [zero-downtime Postgres migration comparison](../2026-10-26-postgres-zero-downtime-migrations-pgroll-reshape-graphile-migrate/) covers the tooling side.

**7. Background workers hold connections hostage.** Job queues that poll in a loop are the single biggest consumer of pool connections in most stacks. If your workers use the [Postgres-backed job queue pattern](../2026-11-03-postgres-job-queues-graphile-worker-pgmq-river-pgqueuer/), give them their own pooler or their own small pool — never share one with latency-sensitive web traffic.

**8. Monitor `cl_waiting`, not CPU.** A pooler that is queuing clients looks perfectly healthy on CPU. The signal that matters is `cl_waiting` and pool wait time. Our [connection pool monitoring guide](../2026-05-21-self-hosted-connection-pool-monitoring-pgbouncer-pgpool-odyssey-guide/) covers the metrics and exporters in detail, and the older [PgBouncer vs ProxySQL vs Odyssey comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) is worth reading for the alternatives that did not make this shortlist.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Supavisor vs PgCat vs PgBouncer in 2026: Which Postgres Pooler Survives a Connection Storm?",
  "description": "Supavisor, PgCat and PgBouncer compared for 2026: multi-tenant pooling, transaction-mode caveats, real config files, sizing math and migration pitfalls.",
  "datePublished": "2026-11-24",
  "dateModified": "2026-11-24",
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

**Do I need a connection pooler if I use PgBouncer-style pooling in my framework?**
Yes, usually. Application-side pools (HikariCP, SQLAlchemy's pool, node-postgres Pool) are per-process and cannot multiplex *across* processes. Twenty pods each holding 20 connections is 400 server connections regardless of what the framework calls it. A pooler in front collapses those onto a small shared pool.

**Is PgBouncer still maintained in 2026?**
Yes. The repository was pushed on 2026-11-20, well after the 1.24 line, and distro packages keep pace. Its stability is the point: the config file you wrote in 2019 still works. PgCat, by contrast, last saw a push in February 2025, so treat its release cadence as slower.

**Can PgBouncer do sharding or read/write splitting?**
No. PgBouncer is deliberately a multiplexer: one `[databases]` entry pointing at one host. If you need shard routing, replica selection or failover handled inside the pooler, that is PgCat's feature set, or you implement routing in the application/driver.

**What is the difference between session and transaction pooling?**
Session mode assigns a server connection to a client for the entire client session — maximum compatibility, minimum multiplexing. Transaction mode returns the connection to the pool at each COMMIT, giving 10–100× better multiplexing but breaking session-scoped state (temp tables, `SET`, advisory locks, `LISTEN`). Most web workloads should use transaction mode; anything that relies on session state must use session mode.

**How many connections should my pool hold?**
Start with `default_pool_size` around 2× your Postgres vCPU count per pooler instance, keep the sum across all poolers below `max_connections` minus 10 for admin, and raise it only when `cl_waiting` is persistently above zero while Postgres CPU is below ~70%. More pooled connections than cores usually lowers throughput by increasing contention.

**Does Supavisor replace PgBouncer for a single-database app?**
Not really. Supavisor's value is tenant addressing, cluster metadata and high client churn. For one database and a few hundred clients, PgBouncer is simpler to run, simpler to debug (a single INI and `SHOW POOLS`), and has a smaller attack surface. Choose Supavisor when the number of databases or the churn rate is the problem you are solving.

**Can these poolers run in front of a managed Postgres like RDS or Cloud SQL?**
Yes for all three, as long as the pooler can reach the instance over the network. On RDS you must also budget for the instance's own connection limit and any proxy already in the path (RDS Proxy, Cloud SQL Auth Proxy), and remember that the pooler adds a hop — keep it in the same availability zone to avoid adding cross-AZ latency to every query.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
