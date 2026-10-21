---
title: "ElectricSQL vs PowerSync vs Triplit in 2026: Which Local-First Sync Engine Should You Build On?"
date: "2026-10-21"
tags: ["local-first", "offline-first", "self-hosted", "database", "comparison"]
draft: false
cover: "/img/screenshots/triplit-browser-console.jpg"
description: "A 2026 engineering comparison of ElectricSQL, PowerSync and Triplit for local-first sync — architectures, real configs, write paths, licensing and the failure modes that only appear when users go offline."
---

Offline support is not a feature you add at the end. It is a data-architecture decision, and by the time a product manager asks for "offline mode", the answer is usually already locked in by how you fetch and mutate data. That is why local-first sync engines exist: they replace hand-rolled cache invalidation with a replication protocol that keeps a client-side database in step with Postgres.

Three projects dominate the self-hostable end of this space in 2026, and they disagree about almost everything: **ElectricSQL**, **PowerSync**, and **Triplit**. The disagreement is the useful part, because each one encodes a different theory of where truth lives.

## TL;DR — the verdict in four lines

- **ElectricSQL** if you want read-path sync of Postgres subsets with the least concept overhead, and you are happy keeping writes on your own API.
- **PowerSync** if you need multi-platform clients (Flutter, React Native, Swift, Kotlin) plus a built-in upload queue, and you can live with a source-available licence.
- **Triplit** if you want a batteries-included syncing database with permissions in the schema and you accept a smaller, slower-moving ecosystem.
- **None of them** if your data model is genuinely collaborative rich text — that is a CRDT problem, and it is a different article.

## Comparison table (GitHub data, 2026-10-21)

| Dimension | ElectricSQL | PowerSync | Triplit |
|---|---|---|---|
| Stars | **10,408** | 395 (service repo) | 3,116 |
| Last push | 2026-10-06 | **2026-10-21** | 2026-01-19 |
| Language (server) | TypeScript/Elixir lineage | TypeScript | TypeScript |
| Licence | Apache-2.0 | FSL (source-available) | AGPL-3.0 / Apache mix |
| Source database | **Postgres only** | Postgres, MySQL, MongoDB, SQL Server | Triplit server (own storage) |
| Client storage | Any (you own the store) | **SQLite** (built in) | IndexedDB, SQLite, Durable Objects |
| Write path | Your API | **Built-in upload queue** | Direct mutations via server |
| Partial replication unit | Shape (a filtered query) | Sync rule buckets | Subscriptions / queries |
| Auth model | Your API + proxy | JWT claims in sync rules | Schema-level permissions |
| Offline writes | Your responsibility | Queued and retried | Queued |
| Self-host image | `electricsql/electric` | `journeyapps/powersync-service` | `npx triplit dev` / Node service |
| Maturity signal | Highest adoption | Fastest release cadence | Stalled since Jan 2026 |

That last row is the one to weigh carefully. A sync engine sits between your database and every client — adopting one that has not pushed since January is a bet that the protocol is finished, not that it is stable.

## Decision matrix

| Your situation | Pick | Why |
|---|---|---|
| Web app with Postgres, reads dominate | **ElectricSQL** | Shapes map cleanly to "this screen's data" |
| Mobile app needing real offline writes | **PowerSync** | Upload queue plus SQLite is the hard part, and it is built in |
| Flutter or React Native on a tight timeline | **PowerSync** | First-class SDKs, documented self-host path |
| Permissions must live next to the data model | **Triplit** | Schema-level rules instead of a separate authz layer |
| You must keep writes inside an existing Go/Rails API | **ElectricSQL** | It deliberately does not own your write path |
| Collaborative text, cursors, presence | None — see our [CRDT sync server comparison](../2026-05-10-self-hosted-crdt-sync-servers-hocuspocus-automerge-electric-sql-guide/) | Conflicts need CRDTs, not last-write-wins |

## ElectricSQL — sync as a read-only mirror

Electric's design is refreshingly narrow: it tails Postgres logical replication and serves **Shapes** — a shape being "the rows of this table matching this where-clause". Clients subscribe over HTTP and receive an ordered stream of inserts, updates and deletes with a monotonic offset they can resume from. There is no client database imposed on you; you feed whatever store you like (TanStack DB, your own cache, IndexedDB).

The deployment is a single service pointed at Postgres, plus one Postgres setting you must not forget:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: electric
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    command:
      - postgres
      - -c
      - wal_level=logical
    ports:
      - "54321:5432"

  electric:
    image: electricsql/electric:canary
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/electric?sslmode=disable
      ELECTRIC_INSECURE: "true"
    ports:
      - "3000:3000"
    depends_on:
      - postgres
```

`wal_level=logical` is the whole ballgame. Without it, Electric starts, connects, and then refuses to serve shapes with a replication error that reads like a networking problem. This is the single most common self-host failure, and it is a database restart away from being fixed.

The read side is HTTP, which means you can debug it with `curl`:

```bash
curl "http://localhost:3000/v1/shape?table=issues&offset=-1"
```

On the client:

```ts
import { ShapeStream } from '@electric-sql/client'

const stream = new ShapeStream({
  url: 'http://localhost:3000/v1/shape',
  params: { table: 'issues', where: "project_id = 'p_42'" },
})

stream.subscribe((messages) => {
  for (const msg of messages) {
    if (msg.key) applyToLocalCache(msg.key, msg.value)
  }
})
```

**What you get:** dead-simple mental model, resumable offsets, a shape per screen, and Postgres staying the single source of truth.

**What you do not get:** a write path. Inserts and updates go through your existing API, and *you* must reconcile the response with the shape stream. In practice you write a small optimistic-update layer — roughly 100 lines, and it is the part teams underestimate.

## PowerSync — the SQLite-shaped answer

PowerSync inverts the model. The server evaluates **sync rules** written in YAML, writes the resulting rows into a SQLite database on the device, and queues client mutations for upload to your backend. The client queries local SQL — instantly, offline, with no network in the loop.

The service is published on Docker Hub as `journeyapps/powersync-service` (I verified `latest` and `1.27.x` tags exist). A minimal self-hosted run looks like this:

```bash
docker run -d --name powersync \
  -p 8080:8080 \
  -v "$PWD/powersync.yaml:/config/powersync.yaml:ro" \
  -e POWERSYNC_CONFIG_PATH=/config/powersync.yaml \
  journeyapps/powersync-service:latest
```

And the sync rules are where the design lives:

```yaml
bucket_definitions:
  user_todos:
    parameters: SELECT token_parameters.user_id AS user_id
    data:
      - SELECT * FROM todos WHERE owner_id = bucket.user_id
      - SELECT * FROM projects WHERE id IN (
          SELECT project_id FROM todos WHERE owner_id = bucket.user_id
        )
```

Two things are worth noticing. First, **buckets are parameterised by JWT claims**, so `token_parameters.user_id` comes from the authenticated token, not from a client-supplied value — that is the security boundary. Second, **the rule set is evaluated server-side at sync time**, which means a badly written rule can multiply data volume across users without any error appearing.

The write path is the differentiator: the client inserts into local SQLite, PowerSync records the mutation in an upload queue, and your backend receives a batched, ordered `POST` to a connector endpoint you implement. Retries, ordering and deduplication are handled for you — genuinely the most tedious part of offline-first.

**Licence caveat:** PowerSync's service is source-available under the FSL, not OSI-approved open source. For internal and most SaaS use that is a non-issue; if you redistribute a product containing it, read the terms before you architect around it.

## Triplit — a syncing database, not a sync layer

Triplit is the most opinionated of the three: it is a database whose defining property is that the client and server are the same database. You define a schema with permissions inline, run the server, and query it from the client with live subscriptions.

![Triplit browser console — live query inspector](/img/screenshots/triplit-browser-console.jpg "Triplit's browser console shows live query results and subscription state against the local store")

```ts
import { TriplitClient } from '@triplit/client'
import { schema } from './triplit/schema'

const client = new TriplitClient({ schema, serverUrl: 'http://localhost:8080' })

const query = client.query('todos').where('done', '=', false).build()

const unsubscribe = client.subscribe(query, (data) => {
  render(data)
})

await client.insert('todos', { text: 'Ship the offline build', done: false })
```

Permissions sit in the schema, which is elegant until you need rules that depend on relationships across collections — at which point the rule language becomes its own thing to learn.

**The honest status check:** the repository's last push was 2026-01-19, roughly nine months before this article. That does not make it broken; it makes it a stability bet. If you are choosing a sync engine today for a product with a two-year horizon, weigh a nine-month gap against Electric's weekly activity and PowerSync's daily cadence.

## The three problems that decide the choice

**1. Conflict resolution strategy.** Electric and PowerSync are last-write-wins at the row level. Two users editing the same row offline means one edit disappears — silently. If your domain has that scenario (shared documents, inventory counts, booking slots), you need either a CRDT layer or server-side conflict detection with a user-visible merge step. No sync engine removes this decision.

**2. Data volume per client.** Partial replication is the whole point, and it is also where projects break. A sync rule that says "all rows for this organisation" is fine at 500 rows and catastrophic at 500,000. Measure rows-per-bucket before launch, not after the first enterprise customer onboards.

**3. Schema evolution.** Adding a nullable column is easy; renaming or retyping one across thousands of offline clients is not. Electric's shape stream will deliver the new shape, but your local store's migration is yours to write. Plan for a versioned client schema from day one — retrofitting it costs a release cycle.

## Operational pitfalls

- **Logical replication slots are not free.** Electric requires a replication slot on Postgres; an abandoned slot will hold WAL indefinitely and fill the disk. Monitor `pg_replication_slots` and alert on `pg_wal_lsn_diff`.
- **Do not point the sync service at your primary without a replica plan.** Both Electric and PowerSync read continuously. On a busy primary that is real I/O.
- **`ELECTRIC_INSECURE=true` is for development.** In production, put the service behind your auth proxy or run it with the documented auth mode; an open shape endpoint is a full data export API for anyone who guesses a table name.
- **Test the airplane-mode path on a real device.** Browser devtools' offline toggle does not simulate a mobile OS suspending your process mid-upload. The bugs live in the resume path.
- **Watch the upload queue depth.** A queue that grows during a flaky-network day and never drains is the classic silent data-loss shape. Export the queue length as a metric from day one.

## Why self-host the sync layer

Sync services price per connected client or per synced row, which is exactly the metric that grows when your product succeeds. Self-hosting puts the replication service next to your database: one container, one Postgres, no third party holding a full replica of your users' working set.

It also makes the trust story simpler. A sync engine sees a filtered copy of your production data, continuously. Keeping that inside your own network is easier to explain to a security reviewer than a vendor's multi-tenant endpoint — and it is the reason most teams that adopt these tools in 2026 run them in their own cluster.

If your source database is Postgres, the [logical replication guide](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/) covers the WAL mechanics Electric depends on, and if you are still deciding between document and relational storage for the client-facing model, the [FerretDB vs MongoDB vs PostgreSQL comparison](../2026-04-29-ferretdb-vs-mongodb-vs-postgresql-self-hosted-document-database-guide/) is worth reading first.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ElectricSQL vs PowerSync vs Triplit in 2026: Which Local-First Sync Engine Should You Build On?",
  "description": "Engineering comparison of ElectricSQL, PowerSync and Triplit for local-first sync: architectures, real deployment configs, write paths, licensing and offline failure modes.",
  "datePublished": "2026-10-21",
  "dateModified": "2026-10-21",
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

**Is ElectricSQL a database?**
No. It is a sync service that reads Postgres logical replication and serves filtered row streams over HTTP. Your Postgres remains the source of truth, and the client-side store is whatever you choose.

**Does PowerSync require SQLite on the client?**
Yes — the service replicates into SQLite on the device, which is why offline queries are instant and why client-side SQL is the programming model. That also means the client bundle carries a SQLite engine.

**Which of the three supports the most client platforms?**
PowerSync has the broadest first-party SDK coverage, including Flutter, React Native, Swift, Kotlin and web. Electric's client libraries target JavaScript/TypeScript primarily, with community ports elsewhere.

**Can I use these with a database other than Postgres?**
PowerSync supports Postgres, MySQL, MongoDB and SQL Server as sources. Electric is Postgres-only by design, because it depends on logical replication semantics. Triplit uses its own server-side storage.

**How do they handle conflicts when two clients edit the same row offline?**
Electric and PowerSync resolve at row level with last-write-wins semantics by default, so the later upload overwrites the earlier one. If you need merge behaviour, add a CRDT layer or implement server-side conflict detection in your write path.

**Is a sync engine overkill for a small app?**
Usually yes. If your dataset fits in a few hundred rows and offline use is a nice-to-have, a service worker cache plus optimistic updates will get you further with less operational surface. The engines pay off when offline is a requirement and the data model is larger than a cache should hold.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
