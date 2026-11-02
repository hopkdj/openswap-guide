---
title: "Postgres in the Browser in 2026: PGlite vs libSQL/Turso vs postgres-wasm"
date: "2026-11-03"
tags: ["postgresql", "sqlite", "webassembly", "embedded-databases", "edge-computing"]
draft: false
cover: "/img/screenshots/pglite-repl-dashboard.jpg"
description: "A hands-on comparison of PGlite, libSQL/Turso and postgres-wasm for running a real SQL database inside the browser, an Electron app or a serverless function in 2026."
---

Your users are on a train with two bars of signal, and your app still has to answer a query in under 50 milliseconds. Round-tripping to a Postgres instance in `us-east-1` is not going to do it. That is the problem embedded databases solve — and in 2026 the options finally got good enough to ship.

Two years ago "SQL in the browser" meant SQLite compiled to WebAssembly with a hand-rolled persistence shim, and everyone quietly accepted the compromises. Today you can run **actual PostgreSQL** client-side with extensions, or a SQLite fork that syncs over HTTP and reads like a normal database client. PGlite alone has picked up **16,227 GitHub stars** and shipped a commit within the last 24 hours; Turso's underlying engine sits at **25,128 stars**.

This article compares the three realistic choices — PGlite, libSQL/Turso, and the now-dormant postgres-wasm — with real star counts, real install commands, and the operational traps that only show up after you deploy.

## TL;DR: The Short Verdict

- **Choose PGlite** if you want Postgres semantics — `jsonb`, window functions, CTEs, PL/pgSQL — inside a browser tab or an Electron app, and you are comfortable that it is a single-connection database.
- **Choose libSQL/Turso** if you need a database that starts local and later syncs to a hosted primary, or if you want one client library that works identically in Node, Deno, browsers and edge functions.
- **Skip postgres-wasm** unless you are doing archival work. It has not been touched since April 2023 and sits at 104 stars.
- **Reach for wa-sqlite or sql.js** instead of PGlite only when your hard constraint is bundle size measured in single-digit megabytes.

The one-line version: **PGlite wins on SQL fidelity, libSQL wins on deployment flexibility, and everything else is a specialty tool.**

## The 2026 Comparison Table

All figures pulled from the GitHub API at publish time, not from memory.

| Dimension | PGlite | libSQL / Turso | postgres-wasm |
|---|---|---|---|
| Repository | `electric-sql/pglite` | `tursodatabase/libsql`, `tursodatabase/turso` | `supabase-community/postgres-wasm` |
| Stars | 16,227 | 17,309 (libSQL) / 25,128 (Turso) | 104 |
| Last push | 2026-11-02 | 2026-10-17 / 2026-11-02 | 2023-04-09 |
| License | Apache-2.0 | MIT | Apache-2.0 |
| SQL dialect | PostgreSQL 17 | SQLite, with experimental Postgres wire support | PostgreSQL (WASM build of real Postgres) |
| Runtime target | Browser, Node, Bun, Deno, Electron | Browser, Node, Deno, edge functions, native | Browser only |
| Persistence | IndexedDB, OPFS, filesystem | Local file, IndexedDB, remote replica | In-memory, manual export |
| Extensions | `pgvector`, `pg_trgm`, `uuid-ossp`, `btree_gist` and more | SQLite extensions, vector search | Limited |
| Sync story | Bring your own (ElectricSQL or manual) | Built in: embedded replica to a primary | None |
| Best fit | Postgres-faithful local-first apps | Multi-platform apps with a sync path | Research and archaeology |

The gap between 16,000 and 104 stars is not a popularity contest — it is a proxy for "will anyone answer my issue when the WASM build segfaults at 2 a.m."

## Decision Matrix: Match the Tool to the Job

| Your situation | Pick | Why |
|---|---|---|
| Offline-first web app that must run real Postgres queries | PGlite | Full Postgres parser and planner, no dialect translation |
| Desktop app (Electron/Tauri) replacing a bundled SQLite | PGlite | Filesystem persistence plus Postgres tooling you already know |
| Same code in browser, Node and edge functions | libSQL | One `@libsql/client` API across all runtimes |
| Read-heavy app with a central writer | libSQL/Turso | Embedded replicas give you local reads with a remote primary |
| Bundle budget under 5 MB | wa-sqlite / sql.js | PGlite ships a full Postgres; there is no diet version |
| You need to test Postgres-specific SQL in CI without a server | PGlite | Runs in-process, no Docker daemon required |

If two rows above describe you, you have a real decision. If only one does, stop reading comparison tables and go build.

## PGlite: Real Postgres, Compiled to WebAssembly

PGlite is not a Postgres-compatible reimplementation. It is the actual Postgres source tree — version 17 — compiled to WebAssembly with a single-user backend, then wrapped in a TypeScript API. That distinction matters the moment you need `jsonb` path operators or a recursive CTE.

![PGlite interactive SQL shell running a real Postgres build in the browser](/img/screenshots/pglite-repl-dashboard.jpg "PGlite REPL executing Postgres queries client-side")

Installation is a single dependency:

```bash
npm install @electric-sql/pglite
```

The simplest possible round trip:

```javascript
import { PGlite } from "@electric-sql/pglite";

const db = new PGlite();
await db.query("select 'Hello world' as message;");
```

For a real application you want durable storage. In the browser that means IndexedDB:

```javascript
import { PGlite } from "@electric-sql/pglite";

// Persist to IndexedDB under the name "my-pgdata"
const db = new PGlite("idb://my-pgdata");

await db.exec(`
  CREATE TABLE IF NOT EXISTS notes (
    id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    body      text NOT NULL,
    metadata  jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
  );
`);

await db.query(
  "INSERT INTO notes (body, metadata) VALUES ($1, $2)",
  ["Ship the offline build", { priority: "high" }]
);

const { rows } = await db.query(
  "SELECT body, metadata->>'priority' AS priority FROM notes ORDER BY created_at DESC"
);
```

That `metadata->>'priority'` is the whole pitch. Try expressing it against a SQLite-backed layer and you will end up writing a JSON extraction shim and hoping the semantics match.

On the server side you can point PGlite at a directory instead of IndexedDB:

```javascript
const db = new PGlite("./path/to/pgdata");
```

There is even a `pg`-compatible adapter, `@electric-sql/pglite/node-postgres`, which lets existing code that imports `pg` talk to an embedded instance — genuinely useful for integration tests that currently require a running Postgres container.

**Where PGlite hurts:** it is single-connection. No concurrent writers, no `LISTEN/NOTIFY` fan-out across tabs, no background autovacuum tuning to save you. A 30 MB-ish WASM payload also means a cold start you can feel on a mid-range phone. Budget for a loading state.

## libSQL and Turso: The SQLite Fork That Speaks HTTP

libSQL started as a fork of SQLite and grew into something broader: a client library with a uniform interface (`file:`, `libsql://`, `:memory:`, `http://`) and an embedded-replica mode where a local database continuously pulls from a remote primary.

The star counts tell the story of adoption: **17,309** on the libSQL repo and **25,128** on Turso, the Rust rewrite that also speaks an experimental Postgres wire protocol.

```bash
npm install @libsql/client
```

```javascript
import { createClient } from "@libsql/client";

// Local file during development, remote in production — same API
const client = createClient({ url: "file:local.db" });

await client.execute(`
  CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY,
    kind    TEXT NOT NULL,
    payload TEXT NOT NULL
  )
`);

await client.execute({
  sql: "INSERT INTO events (kind, payload) VALUES (?, ?)",
  args: ["signup", JSON.stringify({ plan: "pro" })],
});

const result = await client.execute("SELECT count(*) AS n FROM events");
console.log(result.rows[0].n);
```

The parameter style is positional `?` rather than Postgres `$1`, and `execute` returns `rows` as array-like objects rather than `pg`'s `Result`. If you are porting from `pg`, that is a mechanical but non-zero refactor.

The embedded replica is the feature worth the migration:

```javascript
const client = createClient({
  url: "file:replica.db",
  syncUrl: "libsql://your-db.turso.io",
  authToken: process.env.TURSO_AUTH_TOKEN,
});

await client.sync(); // pull the latest from the primary
```

Reads then hit the local file at local-disk latency while writes go to the primary — provided you accept the consistency trade-off and handle the "write failed, retry after sync" path. Most teams underestimate that path.

**Where libSQL hurts:** it is SQLite, so `jsonb` becomes `json`, `timestamptz` becomes an integer or a string, and `gen_random_uuid()` is a function you register yourself. If your application logic leans on Postgres-specific behavior, you are adding a compatibility layer with no maintainer.

## postgres-wasm: What the Abandoned Pioneer Still Teaches

`supabase-community/postgres-wasm` proved in 2022 that you could boot a real Postgres inside a browser tab. It did so by running a miniature Linux VM in WebAssembly, which is a fundamentally heavier approach than PGlite's single-user compile — the boot sequence is measured in seconds, not milliseconds, and the memory footprint is measured in hundreds of megabytes.

Its last commit was **April 9, 2023**, and it holds **104 stars**. Do not build a product on it in 2026.

It is still worth reading for one reason: it documents, in painful detail, every place where a POSIX filesystem assumption breaks inside a browser sandbox — `mmap`, shared memory segments, `fork()`. Those notes are why PGlite's design choices look the way they do, and why modern embedded Postgres is single-connection rather than multi-process.

If you want the browser-native SQLite route without Postgres ambitions, the two mature options are:

| Library | Stars | Approach | Use when |
|---|---|---|---|
| `sql-js/sql.js` | 13,680 | SQLite compiled with Emscripten, loads a `.wasm` file | You need the smallest, most battle-tested option |
| `rhashimoto/wa-sqlite` | 1,424 | Custom VFS layer, supports OPFS and IndexedDB backends | You need real persistence with fine-grained control |

Both are actively maintained (last pushes in the final week of October 2026). `wa-sqlite` is the better engineering choice for new work because its OPFS VFS gives you durable, synchronous-ish file access instead of exporting database bytes to IndexedDB by hand.

## Performance and Operational Pitfalls Nobody Warns You About

These are the failures that show up in production, not in the README quickstart.

**1. Cold start is your new p95.** A WASM database must be fetched, compiled and instantiated before the first query. On a fast desktop that is invisible. On a mid-range Android device over 4G it can be 1.5 seconds or more. Cache the compiled module at the service worker level, and render a skeleton — never a spinner over a blank screen, because users read blank as broken.

**2. Persistence is not a backup.** IndexedDB can be evicted under storage pressure. `navigator.storage.persist()` helps but is not a guarantee, and Safari's behavior differs from Chromium's. If the data matters, you need an export path or a sync target. Ship one before launch, not after the first data-loss bug report.

**3. Multi-tab is a data-corruption vector.** Two browser tabs each instantiating their own database handle against the same storage will clobber each other. Either elect a single leader tab through the Web Locks API or route all writes through a shared worker. This is the single most common self-inflicted bug in local-first applications.

**4. Query plans change when statistics are cold.** An embedded database starts with an empty `pg_statistic`. The first few queries on a fresh install can take a nested-loop plan over a table that will later be indexed properly. Run `ANALYZE` after your initial seed, and again after any bulk import.

**5. Bundle size is a product decision, not a detail.** PGlite's payload is the price of Postgres fidelity. Measure your first-load bytes on a throttled connection before you commit, and compare against the alternative of a hosted database with a 200 ms round trip. Sometimes the network is cheaper than the download.

**6. Do not run migrations implicitly on boot.** With dozens of clients each holding their own copy, a startup migration becomes a race. Version your schema explicitly, gate migrations behind a leader election, and make every migration idempotent.

## Why Self-Host Your Embedded Data Layer?

The instinct when you hit scale is to move everything to a managed database. That is often correct. But the managed path has costs that compound quietly: per-read pricing that punishes a chatty feature, egress fees for every sync, and a vendor that can change its free tier between your sprint planning and your launch.

Running the data layer yourself — whether that is a Postgres primary you operate, or a database that lives inside the client — keeps the cost curve linear and predictable. It also keeps the failure modes visible. When a query is slow, you can read the plan instead of opening a support ticket.

If you are comparing deployment models for SQLite-family engines at the server level, our guide to [self-hosted SQLite server deployments with rqlite, Litestream and mvsqlite](../2026-06-17-self-hosted-sqlite-server-deployments-rqlite-litestream-mvsqlite-sqlite-web/) covers the replication side in depth. For the runtime that actually executes the WebAssembly, [WasmEdge vs Wasmtime vs Wasmer](../2026-04-21-wasmedge-vs-wasmtime-vs-wasmer-self-hosted-webassembly-runtimes-guide-2026/) is the practical starting point. And if your local database is one node in a larger analytics picture, the [DuckDB vs Apache Doris vs Apache Pinot OLAP comparison](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-olap-guide/) explains where columnar engines earn their place.

## FAQ

**Is PGlite actually PostgreSQL, or just Postgres-compatible?**

It is the real Postgres source compiled to WebAssembly — version 17 at the time of writing. You get the actual parser, planner and executor, which is why Postgres-specific syntax like `jsonb` operators and recursive CTEs behave exactly as they do on a server. What you do not get is the multi-process architecture: PGlite runs a single-user backend, so no concurrent connections.

**Can I use PGlite in production for a multi-user application?**

Yes, with a clear architecture: PGlite should be the per-user local database, not the shared system of record. Each client holds its own copy, and synchronization happens through your own backend or an external sync layer. Using one PGlite instance as the sole database behind a server process is a misreading of its design.

**How much of my storage does a browser database actually get?**

Chromium and Firefox generally allow a large fraction of free disk space per origin, but it is still subject to eviction. Calling `navigator.storage.persist()` upgrades the origin to persistent storage and is respected on Chromium-based browsers. Safari is stricter and more opaque. Treat any client-side database as cacheable data with a server-side copy as the source of truth.

**libSQL or Turso — which repository do I actually depend on?**

They are different layers of one project. `libsql` provides the SQLite-compatible engine and the client protocol; `turso` is the Rust rewrite of the database itself and is the forward-looking codebase. For application code you install `@libsql/client`, and the server you point at can be Turso Cloud or a self-hosted instance.

**Does any of this work without a bundler?**

PGlite ships an ES module build that you can import directly from a CDN, which is genuinely handy for a prototype or a single-file demo. In production, use a bundler so the WASM asset is versioned and cached alongside your JavaScript rather than fetched from a third party at runtime.

**What happens when the user clears site data?**

Everything stored in IndexedDB or OPFS is gone, immediately and irreversibly. This is not a bug to work around — it is the contract. Any application that stores primary data client-side needs an export button and, ideally, a background sync so the loss window is measured in minutes rather than months.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Postgres in the Browser in 2026: PGlite vs libSQL/Turso vs postgres-wasm",
  "description": "A hands-on comparison of PGlite, libSQL/Turso and postgres-wasm for running a real SQL database inside the browser, an Electron app or a serverless function in 2026.",
  "datePublished": "2026-11-03",
  "dateModified": "2026-11-03",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
