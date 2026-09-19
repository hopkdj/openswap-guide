---
title: "Clojure Databases in 2026: XTDB vs Datahike vs Datalevin — Which Datalog Engine Should You Actually Use?"
date: "2026-09-20"
tags: ["clojure", "databases", "datalog", "xtdb", "datahike", "datalevin", "self-hosted"]
draft: false
---

You have a Postgres instance, a growing pile of `JOIN` statements, and a nagging feeling that your schema was designed for a world with fewer relationships than the one you now live in. Datalog promises pattern matching over facts instead of ten-table joins — but the Clojure ecosystem offers three serious engines, and they are **not** interchangeable. XTDB rewrote itself into an immutable SQL database. Datahike kept the Datomic API and put your storage backend on a plug. Datalevin forked LMDB and made embedded Datalog genuinely fast.

Pick the wrong one and you will fight it for two years. Here is the honest breakdown, with real dependency coordinates and commands pulled from each project's own repository.

## TL;DR: Quick Verdict

- **You want immutable history plus SQL tooling and you deploy services anyway → XTDB.** It is now an immutable SQL database with bitemporal columns, runs as a node behind the Postgres wire protocol, and ships an official Docker image.
- **You want the Datomic API without Datomic's licensing, and you want to choose your storage → Datahike.** Datomic-compatible API, konserve storage backends (file, LMDB, S3, JDBC, Redis, IndexedDB), immutable snapshots as plain values.
- **You want a single embedded database like SQLite with better queries → Datalevin.** LMDB-backed, ACID, cost-based query optimizer, plus an optional client/server mode with Raft and RBAC when you outgrow one process.

If you are starting from zero today and just need a Datalog store inside one JVM process, **Datalevin is the pragmatic default**. If your data has regulatory time-travel requirements and multiple services will read it, **XTDB**.

## The Three Contenders at a Glance

| Dimension | XTDB | Datahike | Datalevin |
|---|---|---|---|
| GitHub stars | **3,067** | 1,875 | 1,478 |
| License | MPL-2.0 | EPL-1.0 | EPL-2.0 |
| Last repo activity | 2026-09-18 | 2026-09-19 | 2026-09-19 |
| Query language | SQL (XTDB 2), Arrow results | Datalog (Datomic-compatible) | Datalog (Datomic-compatible) |
| Data model | Immutable, bitemporal by default | Immutable facts, git-like snapshots | ACID, deletes are deletes |
| Storage | Object store + Kafka, or local RocksDB | konserve: file, LMDB, S3, JDBC, Redis, IndexedDB | LMDB fork (dlmdb) with WAL |
| Deployment | Standalone node, Docker image, K8s | Embedded library | Embedded library or client/server |
| Language bindings | JVM, HTTP/Postgres wire | Clojure, ClojureScript, JS, Java | Clojure, Java, Python, Node.js |
| Best fit | Compliance, audit, analytics over history | Datomic-shaped apps, custom storage | Embedded apps, single-node throughput |

The star counts and dates above are live from GitHub at publish time — verify them yourself with `gh repo view xtdb/xtdb --json stargazerCount,pushedAt` before you make a decision on a blog post's word alone.

## Decision Matrix: Which One for Your Use Case

| Your situation | Pick | Why |
|---|---|---|
| Regulatory audit: "show me the database as of March 3, 2025" | **XTDB** | Bitemporal versioning is built into the model, not bolted on with history tables |
| Migrating a Datomic app but refusing Datomic's license | **Datahike** | Datomic-compatible API surface, open license, self-chosen storage |
| One JVM app, want SQLite-like simplicity with recursive queries | **Datalevin** | Embedded LMDB engine, no network hop, cost-based optimizer |
| Graph/reasoning queries with recursive rules | **Datahike or Datalevin** | Both expose Datalog rules; XTDB 2 asks you to write SQL |
| You need a read replica set without a broker | **Datahike** | Distributed Index Space lets readers open persistent indices directly |
| You want a Postgres-wire endpoint for BI tools | **XTDB** | The node speaks the Postgres protocol on port 5432 |
| Shell scripts and small utilities | **Datalevin** | Works as a babashka pod, no long-running server required |

## XTDB: An Immutable SQL Database, Not a Datalog Library

XTDB made the most disruptive decision in this comparison: version 2 replaced the Datalog query language with SQL and Arrow, and turned the library into a deployable node. The payoff is that time travel stopped being a feature you build and became a property of every table.

Run the official image — the node listens on port 5432 and speaks the Postgres wire protocol:

```bash
# from the repo's docker/README.adoc
docker run -ti --rm -p 5432:5432 xtdb/xtdb
```

The image entrypoint invokes `xtdb.main` and defaults to `-f config.yaml`, which means you can run specialized node roles against the same config file:

```bash
docker run -ti --rm -v ./my-config.yaml:/config/xtdb.yaml xtdb/xtdb ingest -f /config/xtdb.yaml
docker run -ti --rm -v ./my-config.yaml:/config/xtdb.yaml xtdb/xtdb compactor -f /config/xtdb.yaml
```

Splitting ingest from compaction is the single most useful operational detail in this article: compaction is the expensive part, and isolating it stops a background job from stealing latency from your writers.

For a full local stack, XTDB's own `docker-compose.yml` at the repository root wires Kafka (KRaft mode, `confluentinc/cp-kafka:7.8.0`), MinIO for object storage, and Keycloak for auth — the same shape you would run in production, which is unusual for a database repo and worth copying. The MinIO bootstrap container even creates the bucket and a scoped `xtdb` user for you:

```yaml
  minio-setup:
    image: quay.io/minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      sleep 5;
      mc alias set myminio http://minio:9000 myadmin mypassword;
      mc mb myminio/xtdb;
      mc admin user add myminio xtdb test-password;
      mc admin policy attach myminio readwrite --user xtdb;
      "
```

Queries are plain SQL, and the point is that you can append `FOR ALL SYSTEM_TIME` style history reads to get the audit view:

```sql
SELECT customer_id, SUM(total) AS revenue
FROM sales
GROUP BY customer_id
ORDER BY revenue DESC;
```

**Choose XTDB if** time is a first-class dimension of your domain and you are comfortable running another service. **Do not choose it if** you wanted a Datalog library you could drop into an existing process — XTDB 2 is a different product than Crux was.

## Datahike: The Datomic API on Storage You Control

Datahike's pitch is narrow and honest: **Datomic-compatible APIs, git-like semantics, and storage you choose**. Database snapshots are immutable values you can hold, share, and query anywhere — no locks, no copying. That last property is what makes its Distributed Index Space work: readers open persistent indices directly instead of opening a database connection, so read scaling does not require a broker or a replica set you have to babysit.

Dependencies come from Clojars (`org.replikativ/datahike`), and the canonical embedded setup is a plain configuration map:

```clojure
(require '[datahike.api :as d])

;; use the filesystem as storage medium
(def cfg {:store {:backend :file
                  :id #uuid "550e8400-e29b-41d4-a716-446655440000"}})

(d/create-database cfg)
(def conn (d/connect cfg))
```

Swap `:backend :file` for LMDB, S3, JDBC, Redis, or IndexedDB via konserve and the rest of your code does not move. That is the entire argument for Datahike: your storage decision stays reversible.

The feature set that follows is the one Datomic popularized:

- **Time travel** — query any historical state, with a full transaction audit trail.
- **Data excision** — genuinely remove facts for GDPR-style deletion, which is the hard problem immutable stores usually punt on.
- **Real-time sync** — WebSocket streaming with Kabel for browser-to-server updates.
- **Cross-platform** — JVM, Node.js, and the browser, with ClojureScript and Java APIs alongside Clojure.

The project also documents a production deployment with billions of datoms in government services, which matters more than any benchmark table when you are picking something to bet on.

**Choose Datahike if** you want Datomic's programming model and you have opinions about where bytes live. **Do not choose it if** you need the SQL ecosystem — no Postgres wire protocol here.

## Datalevin: Embedded Datalog That Competes With SQLite

Datalevin is the one to reach for when you want a SQLite-shaped deployment with a better query language. It is built on `dlmdb`, the project's own fork of LMDB, with WAL and asynchronous transactions layered on top, so write-intensive workloads do not collapse into a single writer bottleneck.

Add it from Clojars (`datalevin/datalevin`) and you are querying in three lines:

```clojure
(require '[datalevin.core :as d])

(def conn (d/get-conn "/tmp/datalevin/mydb"))

(d/transact! conn [{:sales/year 2026
                    :sales/total 4200
                    :customers/name "Acme"}])

(d/q '[:find ?name ?total
       :in   $ ?year
       :where [?sales :sales/year ?year]
              [?sales :sales/total ?total]
              [?sales :sales/customer ?customer]
              [?customer :customers/name ?name]]
     (d/db conn) 2026)
```

Three things separate Datalevin from the other two:

1. **It has a cost-based query optimizer** with a novel planner, benchmarked by the project against PostgreSQL, SQLite, and Neo4j on LDBC-SNB and JOB workloads.
2. **Deletes are deletes.** Datalevin deliberately does *not* copy Datomic's temporal semantics: facts you remove are gone, and transactions follow conventional ACID expectations rather than unusual versioning rules.
3. **It scales out when you need it.** Besides embedded mode, Datalevin runs as a client/server on port 8898, and supports a Raft-consensus high-availability cluster with role-based access control.

It also has bindings for Java, Python, and Node.js, plus a babashka pod — so the same database engine can back a Clojure service, a Python data job, and a shell script without three different storage layers.

**Choose Datalevin if** one process owns the data and you care about latency and disk efficiency. **Do not choose it if** you need bitemporal history — that is explicitly not the design.

## Operating These Databases in Production

The operational surface differs far more than the query language tables suggest.

**Backups.** XTDB's design leans on object storage: your durability story is the bucket plus Kafka retention, so backup means versioning and lifecycle rules on the bucket rather than `pg_dump`. Datahike's durability story is whatever konserve backend you picked — a `:file` backend is a directory you can snapshot, while S3 is already versioned. Datalevin's durability story is a single LMDB environment directory, which makes cold backups trivial and copies cheap.

**Memory and index size.** LMDB-based stores (Datalevin, Datahike with `:backend :lmdb`) memory-map their data, so RSS tracks what the kernel caches rather than what your JVM heap holds. Plan container limits around the page cache, not the heap, or you will chase phantom OOM kills.

**Compaction and GC.** Immutable stores accumulate history. XTDB separates compaction into its own node role precisely so you can schedule it off-peak. Datahike gives you excision when regulation demands real deletion. Datalevin sidesteps the issue by not keeping history by default — a genuine operational advantage, and a genuine capability loss.

**Ecosystem fit.** If your application is already built on Ring-era stack choices, these databases slot in without disruption; our [Clojure HTTP clients comparison](../2026-09-07-clojure-http-clients-clj-http-httpkit-hato-comparison/) covers the client side of talking to them over the wire. For validating the maps you transact, the [Clojure data validation comparison](../2026-09-05-clojure-data-validation-malli-schema-spec-comparison/) is the natural companion, and if you are shaping JSON payloads for an HTTP boundary, see the [Clojure JSON libraries comparison](../2026-09-08-clojure-json-libraries-cheshire-jsonista-data-json-comparison/).

## Common Pitfalls and Migration Notes

**Do not assume XTDB 2 is Crux.** Most tutorials you will find online describe Datalog queries against XTDB 1. XTDB 2 speaks SQL and returns Arrow; the migration is a rewrite of your query layer, not a version bump.

**Watch the temporal model when porting Datomic code.** Datalevin warns explicitly that Datomic's temporal features confuse newcomers — and its own behavior is deliberately different. If you migrate a Datomic app to Datalevin, code that relies on history reads will silently change meaning.

**Test your storage backend before you commit.** Datahike's konserve abstraction makes switching painless — but S3 latency inside a transaction loop is a different universe from a local file. Benchmark with your real backend, not the default.

**Do not run the XTDB dev compose in production.** The bundled `docker-compose.yml` uses `ALLOW_PLAINTEXT_LISTENER`, default credentials (`myadmin` / `mypassword`), and a public MinIO policy. It exists to make local development fast.

**Budget for the query rewrite in either direction.** Datalog rules express recursive graph traversal far more naturally than SQL; moving from Datahike to XTDB means defending those traversals with recursive CTEs, and moving back means learning rules.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure Databases in 2026: XTDB vs Datahike vs Datalevin",
  "description": "Hands-on comparison of XTDB, Datahike and Datalevin for Clojure: immutable SQL vs Datomic-compatible Datalog vs embedded LMDB, with real dependency coordinates and deployment commands.",
  "datePublished": "2026-09-20",
  "dateModified": "2026-09-20",
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

**Is XTDB still a Datalog database?**
No. XTDB 2 is an immutable SQL database with Arrow result sets and no Datalog query language. If you need Datalog specifically, choose Datahike or Datalevin — both keep Datomic-style Datalog APIs.

**Can I use Datahike with S3 instead of local files?**
Yes. Datahike stores data through konserve, which supports file, LMDB, S3, JDBC, Redis, and IndexedDB backends. You change the `:store` map in your config; application code stays the same.

**Does Datalevin keep history like Datomic?**
No, and that is a deliberate design choice. When you delete data in Datalevin it is gone, and transactions follow conventional ACID semantics. Reaching for Datalevin means giving up bitemporal time travel.

**Which of the three is easiest to operate on a single server?**
Datalevin. It embeds in your process with no separate daemon, and its client/server mode on port 8898 is optional. XTDB requires running a node plus its storage and streaming dependencies; Datahike depends on whichever konserve backend you select.

**How do these compare to just using PostgreSQL?**
Postgres wins on tooling maturity, SQL ecosystem, and hiring. These engines win when your queries are relationship-heavy or when you need immutable history as a database property rather than a set of history tables and triggers you maintain forever.

**Are these projects actively maintained in 2026?**
Yes. All three received commits within days of publication: XTDB on 2026-09-18, Datahike and Datalevin on 2026-09-19. Licenses are permissive: MPL-2.0 for XTDB, EPL-1.0 for Datahike, EPL-2.0 for Datalevin.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
