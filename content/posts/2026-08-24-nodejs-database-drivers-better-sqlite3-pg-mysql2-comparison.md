---
title: "better-sqlite3 vs pg vs mysql2 in 2026: Which Node.js Database Driver Should You Use?"
date: "2026-08-24"
tags: ["nodejs", "database", "sqlite", "postgresql", "mysql", "npm-libraries"]
draft: false
cover: "/img/screenshots/better-sqlite3-cover.jpg"
---

The first database decision in a Node.js project is not which database — it is which driver, and the three most popular answers are so different in character that the choice leaks into every layer of your application. **better-sqlite3** is synchronous, embedded, and astonishingly fast. **pg** is the canonical PostgreSQL client with a connection pool and a features list that tracks the server itself. **mysql2** is the performance-focused MySQL/MariaDB driver that replaced the abandoned `mysql` package. Pick based on "which database do I need" and you will be fine; pick based on "which API style do I want" and you will build a better application.

**better-sqlite3** (7,449 stars) executes SQL synchronously and caches prepared statements — the fastest SQLite binding in the Node ecosystem. **pg** (13,196 stars) is the pure-JavaScript PostgreSQL client used by millions of deployments, with optional native bindings and a pool built in. **mysql2** (4,383 stars) is the promise-first MySQL/MariaDB driver, API-compatible with the legacy `mysql` package but with prepared statements, compression, and better performance.

## TL;DR: Quick Verdict

**If your data fits in a file and you want zero infrastructure, use better-sqlite3** — the sync API eliminates whole classes of async bugs, and its speed is unmatched for embedded workloads. **If you are building anything with PostgreSQL, use pg** — it is the standard, its `Pool` handles connection management correctly, and it tracks Postgres features (LISTEN/NOTIFY, COPY, named statements) as they land. **If your stack mandates MySQL or MariaDB, use mysql2** — it is strictly better than the deprecated `mysql` package, with the same API plus promises and prepared statements. These are not competitors for the same job: they are the right answers to three different database questions, and the interesting engineering is knowing which question you are actually asking.

## Feature Comparison: better-sqlite3 vs pg vs mysql2

| Capability | better-sqlite3 | pg | mysql2 |
|---|---|---|---|
| Database | SQLite (embedded) | PostgreSQL | MySQL / MariaDB |
| API style | **Synchronous** | Async (callbacks/promises) | Async (callbacks/promises) |
| Prepared statements | ✅ automatic + cached | ✅ | ✅ (`execute()`) |
| Connection pooling | ❌ (not needed, embedded) | ✅ built-in `Pool` | ✅ `createPool` |
| LISTEN/NOTIFY | ❌ | ✅ | ❌ (triggers instead) |
| COPY bulk import/export | ❌ | ✅ (`COPY TO/FROM`) | ✅ (`LOAD DATA` via raw queries) |
| Streaming large result sets | ⚠️ via `db.iterate()` | ✅ cursor (`pg-cursor`) | ✅ `RowStream` |
| TypeScript types | ✅ (bundled) | ✅ (`@types/pg` or bundled in v8) | ✅ (bundled) |
| Native bindings | ✅ (C++ addon) | Optional (`pg-native`) | Pure JS (optional native) |
| Worker-thread friendliness | ⚠️ sync blocks the thread | ✅ | ✅ |
| License | MIT | MIT | MIT |
| GitHub stars | 7,449 | 13,196 | 4,383 |
| Last push | 2026-08-10 | 2026-08-18 | 2026-08-23 |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Local tool, CLI, Electron app, prototype | **better-sqlite3** | File-based, no server, sync API = fewer moving parts than any alternative |
| Read-heavy analytics cache embedded in a service | **better-sqlite3** | WAL mode + prepared statement cache is hard to beat for single-process reads |
| Any new service with relational data at scale | **pg** | Postgres + pg is the boring, correct default; the pool, types, and server features are all first-class |
| Real-time features (chat, notifications, dashboards) | **pg** | `LISTEN/NOTIFY` gives you push events from the database with zero extra infrastructure |
| Mandatory MySQL/MariaDB stack (legacy or hosting constraint) | **mysql2** | The maintained, faster, promise-first replacement for `mysql` |
| High-concurrency write-heavy OLTP | **pg or mysql2** (not better-sqlite3) | SQLite serializes writers; a networked RDBMS with proper pooling scales horizontally |
| Microservice needing a tiny embedded store | **better-sqlite3** | One npm package, one file, no service to deploy or monitor |

## better-sqlite3 — Synchronous SQLite, Maximum Speed

better-sqlite3's entire personality comes from one design decision: **synchronous execution with automatic prepared statement caching**. The API is the simplest of the three by a wide margin:

```js
const db = require('better-sqlite3')('foobar.db', options);

const row = db.prepare('SELECT * FROM users WHERE id = ?').get(userId);
console.log(row.firstName, row.lastName, row.email);
```

No callbacks, no promises, no pool. `db.prepare()` returns a cached statement object; `.get()` returns one row, `.all()` returns an array, `.run()` executes writes and returns `{ changes, lastInsertRowid }`. Because there is no event-loop round trip, the library is dramatically faster than the async drivers — the benchmark suite in its README shows it outperforming `sql.js`, `node-sqlite3`, and the async alternatives by wide margins on both reads and writes.

The one performance rule the README pushes: **enable WAL mode** for real workloads.

```js
db.pragma('journal_mode = WAL');
```

WAL (write-ahead logging) lets readers and the single writer proceed concurrently instead of blocking each other with the default rollback journal, and it is the difference between "SQLite is slow under load" and "SQLite is surprisingly fast." For long-running queries, `db.iterate()` streams rows one at a time instead of materializing the full result set.

The cost of sync is the one thing you must design around: **a long-running query blocks the entire event loop**. better-sqlite3 is perfect when queries are milliseconds; it is wrong for heavy analytics or large aggregations in a busy server, because every other request stalls. The standard mitigation is a `worker_threads` pool that owns the database handle — which reintroduces the async complexity the library removed. Use better-sqlite3 where its model fits (local tools, Electron, single-process services with fast queries) and reach for a networked driver where it does not.

## pg — The PostgreSQL Client That Sets the Bar

pg (node-postgres) is a monorepo whose core `pg` package is the most battle-tested database driver in Node. Its defining feature is the **`Pool`**, which owns a set of connections and hands them out per query — the correct default for a server, since creating a connection per query is the classic way to exhaust PostgreSQL's `max_connections`:

```js
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

const { rows } = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
```

Note the `$1` placeholder syntax — Postgres-native, not the `?` you might expect from SQLite/MySQL. pg supports parameterized queries (which protect against SQL injection when used instead of string interpolation), named statements with server-side query plan caching, connection timeouts, and retries via `pg-pool`'s error handling.

Where pg really shines is tracking PostgreSQL features:

```js
// LISTEN/NOTIFY — push events from the database
const client = await pool.connect();
await client.query('LISTEN order_created');
client.on('notification', (msg) => {
  console.log('new order:', msg.payload);
});
```

`LISTEN/NOTIFY` turns Postgres into a lightweight message bus — dashboards refresh, caches invalidate, and chat apps fan out without polling. `COPY TO/FROM` moves bulk data in and out faster than row-by-row inserts, and the companion `pg-cursor` package streams large result sets without loading them into memory. The driver is pure JavaScript by default (works on Bun and Deno, per the README) with optional native libpq bindings that share the same API.

pg's weaknesses are minor and structural: it does not bundle the TypeScript types in the way newer drivers do (you add `@types/pg`), and its API surface is low-level by design — there is no query builder, no model layer, which is why so many teams pair it with an ORM or query builder from our [ORM libraries comparison](../2026-06-20-orm-libraries-hibernate-prisma-gorm-sequelize-typeorm/).

## mysql2 — The Modern MySQL Driver

mysql2 began as a performance-focused rewrite of `mysqljs/mysql`, and when the original `mysql` package went quiet, mysql2 became the de facto standard. It is API-compatible with `mysql` — a drop-in replacement — while adding prepared statements, promises, compression, and non-UTF8 charset support. The promise wrapper is the API most new code uses:

```js
const mysql = require('mysql2/promise');

const connection = await mysql.createConnection({
  host: 'localhost',
  user: 'root',
  database: 'test',
});

const [rows, fields] = await connection.execute(
  'SELECT * FROM users WHERE id = ?',
  [userId]
);
```

`execute()` uses **server-side prepared statements** — the query is parsed and planned once, then reused with different parameters, which is both faster on repeated queries and immune to the classic string-interpolation injection bugs. `createPool()` gives you the same connection-pool semantics as pg's `Pool`, and `createPoolCluster()` adds read/write splitting across replicas — a feature pg users have to build themselves.

mysql2 also handles the MySQL protocol's modern auth (caching_sha2_password, the MySQL 8 default) and works with MariaDB, whose protocol is close enough that the driver is the recommended choice there too. Its TypeScript types ship with the package, and it supports streaming result rows for large queries.

The caveats: mysql2's docs are spread across a documentation site rather than a single README, the package ships with a `mysql`-compat layer that can confuse newcomers (callbacks vs promises), and like all MySQL drivers it inherits MySQL's own limitations — no `LISTEN/NOTIFY`, no `COPY`, and replication lag you must manage yourself. It is the right choice when MySQL/MariaDB is already your platform, not a reason to choose MySQL.

## Pitfalls and Migration Gotchas

**1. better-sqlite3 sync calls block the event loop.** A 2-second aggregation freezes every concurrent request. Keep queries millisecond-fast, or move the database to a `worker_threads` pool. This is the single most common production incident with this library.

**2. SQLite writes are serialized.** WAL mode gives you concurrent readers plus one writer; concurrent writers get `SQLITE_BUSY` rather than graceful queues. For write-heavy or multi-process workloads, a networked database is the answer — better-sqlite3 is a local-file store, not a server.

**3. Placeholder syntax differs between drivers.** `$1` in pg, `?` in better-sqlite3 and mysql2. Porting queries between them means rewriting parameter binding, and a naive regex "fix" will corrupt queries containing `$` or `?` in string literals. Port deliberately, query by query.

**4. Never build SQL by string interpolation.** Every driver here supports parameterized queries; using template strings to insert user input is the injection vulnerability that parameterization exists to prevent. If you find yourself writing `WHERE id = ${id}`, stop and use placeholders.

**5. Connection leaks with pools.** With pg's `Pool` and mysql2's pools, forgetting to `client.release()` (pg) or `connection.release()` (mysql2) after `connect()` leaks a connection per request until the pool is exhausted and the server hangs. Use `pool.query()` for one-shot queries — it checks out and releases automatically — and only use explicit `connect()` when you need a transaction.

**6. Transactions require a dedicated connection.** `BEGIN`/`COMMIT` on a pool that hands you a different connection per query silently breaks. Check out one connection, run the transaction on it, commit, and release — in all three drivers.

**7. better-sqlite3 does not survive multi-process.** Each process gets its own handle; with WAL on a network filesystem, locks and `SQLITE_BUSY` are guaranteed. Deploy it on local disk only.

**8. mysql2 auth failures with MySQL 8.** Old clients using `mysql_native_password` break against MySQL 8's `caching_sha2_password` default unless the user account is migrated. mysql2 supports the new auth; update the driver first, then the account.

**9. pg on serverless (Lambda, Edge).** Cold starts pay the TCP+TLS handshake per invocation. Keep a pool warm with a global connection or use a serverless-aware pool (e.g. `pg` with `pg-pool` configured to reuse connections across warm invocations) — and expect connection limits on bursty functions.

For the surrounding Node architecture, our [Node.js HTTP frameworks comparison](../2026-07-28-nodejs-http-frameworks-express-koa-fastify-hono-comparison/) covers the server layer these drivers sit under, and the [SQL query builder comparison](../2026-06-20-sql-query-builder-libraries-knex-jooq-diesel-squirrel/) shows how teams generate safe SQL on top of raw drivers. If your workload is scheduled batch jobs against these databases, the [Node.js job scheduling guide](../2026-08-10-nodejs-job-scheduling-libraries-node-cron-bree-agenda/) is the companion read.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "better-sqlite3 vs pg vs mysql2 in 2026: Which Node.js Database Driver Should You Use?",
  "description": "Compare Node.js database drivers: synchronous embedded better-sqlite3, PostgreSQL's pg with LISTEN/NOTIFY and COPY, and promise-first mysql2 for MySQL/MariaDB. Feature table, decision matrix, code, and pitfalls.",
  "datePublished": "2026-08-24",
  "dateModified": "2026-08-24",
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

### Is better-sqlite3 faster than pg and mysql2?

For the operations it performs, yes — dramatically. Synchronous execution with cached prepared statements avoids event-loop round trips and network latency entirely, so point queries are typically 3–10x faster than the networked drivers. But the comparison is not apples-to-apples: better-sqlite3 runs inside your process against a local file, while pg and mysql2 pay TCP, TLS, and server round trips. The right frame is "embedded vs networked," not "which is fastest."

### Can better-sqlite3 handle concurrent writes?

SQLite allows exactly one writer at a time. WAL mode lets readers run concurrently with the writer, but concurrent writers receive `SQLITE_BUSY` unless you set a busy timeout and retry. For single-process services with modest write rates it is fine; for multi-process or high-write workloads, use PostgreSQL or MySQL.

### Is mysql2 a drop-in replacement for the mysql package?

Yes for the callback API — mysql2 was designed as an API-compatible, faster, maintained replacement. Code written against `mysqljs/mysql` can switch by changing the import. mysql2 additionally provides a `mysql2/promise` wrapper, server-side prepared statements via `execute()`, and compression. The main migration gotcha is auth: MySQL 8's `caching_sha2_password` requires a modern driver, which mysql2 is.

### Should I use pg or mysql2 for a new project?

Default to pg unless you have a concrete reason for MySQL/MariaDB. PostgreSQL's feature set (LISTEN/NOTIFY, COPY, rich types, better standard compliance) plus pg's mature pool makes it the lower-risk choice, and it removes the MySQL 8 auth and replication-lag conversations entirely. Choose mysql2 when your host, managed database, or team expertise is MySQL-specific.

### Do these drivers support TypeScript?

Yes. mysql2 ships its own types, better-sqlite3 bundles type definitions, and pg works with the community `@types/pg` package (the v8 releases moved toward bundling types in the `pg` package itself). All three are usable in strict-mode TypeScript projects, though mysql2 and better-sqlite3 require less setup.

### What is the best way to run transactions with pg?

Use one dedicated client from the pool: `const client = await pool.connect()`, then `BEGIN`, run your queries on that same client, `COMMIT` (or `ROLLBACK`), and `client.release()` in a `finally`. Never spread a transaction across separate `pool.query()` calls — each call may get a different connection, silently breaking atomicity.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
