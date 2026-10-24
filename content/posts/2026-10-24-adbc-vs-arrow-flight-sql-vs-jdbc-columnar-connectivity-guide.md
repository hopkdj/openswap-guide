---
title: "ADBC vs Arrow Flight SQL vs JDBC in 2026: Stop Copying Rows Between Your Database and Your Pipeline"
date: "2026-10-24"
tags: ["apache-arrow", "adbc", "flight-sql", "data-engineering", "database-connectivity"]
cover: "/img/screenshots/arrow-columnar-format-diagram.jpg"
draft: false
---

Every analytics pipeline built on a classic driver pays the same tax, and almost nobody measures it. A query returns rows: the driver materialises one Python object (or one JVM object, or one Go struct) per row, your code converts those rows into a columnar frame, and then the frame is serialised again to move to the next process. For a 50-million-row scan, that is three full transpositions of the data — the query itself is often the *fast* part.

Apache Arrow exists to delete those transpositions. But "use Arrow" is not a plan: there are three distinct ways to get data across a process boundary in columnar form — **ADBC**, **Arrow Flight SQL**, and the **Arrow IPC / PyArrow** level — and they solve different problems at different layers. This guide separates them, with real connection strings, current project data, and the traps that show up in production.

## TL;DR: The Verdict

- **ADBC** is the *driver API*: it looks like a database driver (connect, cursor, execute) but returns Arrow record batches instead of row objects. Use it as a drop-in replacement for your DB-API/JDBC layer.
- **Arrow Flight SQL** is the *wire protocol*: SQL semantics over gRPC that carries Arrow buffers end to end. Use it when you control, or can choose, the server — it removes serialisation from the network hop as well as from the client.
- **Arrow IPC / PyArrow** is the *file and stream format*: zero-copy, memory-mappable, and the right thing to persist between pipeline stages. Use it between services that already agree on schemas.
- **Wrong answer in 2026:** piping a `SELECT *` through a row-oriented driver into pandas and calling that "the Arrow path". You paid the full tax and got none of the benefit.

In one sentence: **Flight SQL moves Arrow over the network, ADBC gives your language a driver that speaks Arrow, and IPC is how you store the result without re-encoding it.**

## Comparison Table

| Dimension | **ADBC** | **Flight SQL** | **Arrow IPC / PyArrow** |
|---|---|---|---|
| Layer | Client driver API | Wire protocol (gRPC) | File / stream format |
| Returns | Arrow record batches | Arrow record batches | Arrow record batches |
| Repo | `apache/arrow-adbc` — 635 ★, Apache-2.0, pushed 2026-10-24 | Spec inside `apache/arrow` — 17,215 ★, pushed 2026-10-23 | `apache/arrow` + `apache/arrow-rs` — 3,646 ★ |
| Language coverage | C/C++, Python, R, Ruby, Go, Java (JDBC bridge) | Any gRPC client; JDBC driver published on Maven | Python, Rust, C++, Java, Go, JS |
| Server changes required | None (drivers front existing DBs) | Server must implement Flight SQL | None |
| Zero-copy on client | ✅ | ✅ | ✅ (memory-mapped) |
| Bulk ingest | ✅ `adbc_ingest` | ✅ via `CommandStatementIngest` | ⚠️ Write side only |
| Works with Postgres/SQLite/DuckDB | ✅ native drivers | Only via a Flight SQL gateway | N/A |
| Typical use | Application queries | Cross-language data services, federated queries | Intermediate pipeline artifacts |

## Decision Matrix

| Your situation | Use | Why |
|---|---|---|
| Python service querying Postgres and needing a DataFrame | **ADBC** (Postgres driver) | Removes the row→frame conversion entirely |
| Building an internal "SQL endpoint" for many languages | **Flight SQL** | One gRPC service, every client gets Arrow |
| Batch job reading 40 GB of intermediate results | **Arrow IPC** (memory-mapped) | No parse step, no copy, no schema drift |
| Existing JVM app on JDBC, can't rewrite | **Flight SQL JDBC driver** or ADBC's JDBC bridge | Keeps `ResultSet` API, adds an Arrow fast path |
| Dashboard hitting a warehouse | **ADBC** if supported, else native driver | Lowest-friction win |
| Federated query across engines | **Flight SQL** | Server-side join, Arrow on the wire |
| Handing data to a non-Python consumer | **Arrow IPC file** | Language-neutral, self-describing |

## Level 1 — PyArrow and IPC: The Format Underneath Everything

Before the drivers, understand what the format buys you. Arrow's columnar layout is designed so that a buffer can be handed to another process or language **without deserialising it**, provided both sides agree on the schema.

```python
import pyarrow as pa

# Read an IPC file by memory-mapping it — no parse, no copy
with pa.memory_map("events.arrow", "r") as source:
    table = pa.ipc.open_file(source).read_all()

print(table.num_rows, table.schema)

# Stream batches instead of materialising everything
with pa.ipc.open_stream("events.arrows") as reader:
    for batch in reader:
        process(batch)   # each batch is a RecordBatch, still columnar
```

Two practical rules:

1. **IPC for pipeline internals, Parquet for storage at rest.** Parquet compresses and encodes far better; IPC is optimised for reading back with no decode step. Use Parquet for cold data, IPC for the handoff between stages. Our [columnar format comparison of Parquet, Arrow and ORC](../2026-06-21-self-hosted-columnar-data-formats-parquet-arrow-orc/) goes deeper on the tradeoffs.
2. **Memory-mapping beats reading.** `pa.memory_map` returns a table backed by the file's pages; the OS decides what stays resident. On repeated passes over a large artifact this is the difference between a job that fits in RAM and one that doesn't.

The same buffers underpin everything below — the drivers exist to get *raw* Arrow into your process without a round trip through row objects.

## Level 2 — ADBC: A Driver That Returns Columns

ADBC (Arrow Database Connectivity) is described upstream as a "database connectivity API standard and libraries for Apache Arrow". It deliberately mimics the DB-API shape everyone already knows, which is why migrating is usually a handful of lines rather than a rewrite:

```python
from adbc_driver_manager import dbapi

with dbapi.connect(driver="sqlite", uri="analytics.db") as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, ts, amount FROM events WHERE ts > ?", ("2026-01-01",))
        table = cur.fetch_arrow_table()      # Arrow, not rows
        print(table.num_rows, table.schema)
```

```
pip install adbc_driver_manager adbc_driver_postgresql pyarrow
```

The important detail is `fetch_arrow_table()` (and `fetch_record_batch()` for streaming). A traditional driver would produce one Python tuple per row and let you assemble them; ADBC returns the Arrow table directly. Data of the same type is contiguous in memory, so downstream operations — filtering, grouping, handing to DuckDB, writing Parquet — operate on columns without a transposition first.

Bulk loading works in the other direction too:

```python
with dbapi.connect(driver="adbc_driver_postgresql", db_kwargs={"uri": "postgresql://localhost/app"}) as conn:
    with conn.cursor() as cur:
        cur.adbc_ingest("events_staging", table, mode="append")
```

That is one call for what is otherwise a `COPY`-or-`executemany` decision with very different performance profiles.

**Where ADBC is the right answer:** your application queries an existing database and you want the row-conversion tax gone. Drivers exist for PostgreSQL, SQLite, DuckDB, Snowflake, BigQuery and others; the manager loads them dynamically, so the same Python code works across engines.

**Where it isn't:** ADBC is a client-side API. If the server speaks MySQL wire protocol, the driver still parses MySQL rows on the server's terms — the win is on the client side of the boundary, not the network. For that you need level 3.

## Level 3 — Arrow Flight SQL: Arrow All the Way to the Server

Flight SQL is a gRPC protocol that carries SQL requests and Arrow results. Both endpoints speak Arrow, so the data is never re-encoded into a row protocol at all. The URI scheme is explicit about transport, which matters more than it sounds:

| URI form | Transport | When |
|---|---|---|
| `flightsql://host:31337` | gRPC + TLS (default) | Production |
| `flightsql://host:31337?transport=tcp` | gRPC, plaintext | Local development only |
| `flightsql:///path/to.sock?transport=unix` | Unix socket | Same-host sidecar |
| `grpc://` / `grpc+tls://` | Direct gRPC targets | Client libraries that bypass the ADBC URI parser |

A complete, runnable example — the SQLFlite reference server (DuckDB/SQLite backend, official Docker image) started with the flags from its own README:

```bash
docker run --name sqlflite \
           --detach \
           --rm \
           --tty \
           --init \
           --publish 31337:31337 \
           --env TLS_ENABLED="0" \
           --env SQLFLITE_PASSWORD="sqlflite_password" \
           --pull missing \
           voltrondata/sqlflite:latest
```

Then, from Python, with the Flight SQL ADBC driver:

```python
from adbc_driver_flightsql.dbapi import connect

with connect(
    uri="flightsql://localhost:31337?transport=tcp",
    db_kwargs={"adbc.flight.sql.rpc.call_header.authorization": "Bearer sqlflite_password"},
) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT l_returnflag, sum(l_quantity) FROM lineitem GROUP BY 1")
        result = cur.fetch_arrow_table()
        print(result.to_pandas().head())
```

From a JVM service, the published Flight SQL JDBC driver speaks the same protocol, so a legacy `ResultSet` consumer can point at `jdbc:arrow-flight-sql://localhost:31337` and keep its code — the driver simply materialises Arrow batches behind the cursor.

**Where Flight SQL wins decisively:** multi-language environments. A Python notebook, a Rust service and a Java batch job can all query the same endpoint and all receive Arrow, without anyone maintaining a bespoke REST/JSON schema. Federated setups benefit too: the server joins across backends and ships one columnar result.

**Where it costs you:** someone has to run a Flight SQL server. If your database doesn't implement the protocol natively, you need a gateway. SQLFlite is a good reference but its last commit was in 2024 (281 ★), so treat it as a template, not a production dependency — `datafusion-contrib/datafusion-flight-sql-server` is a more actively maintained starting point if you want to build your own.

![Apache Arrow columnar format diagram](/img/screenshots/arrow-columnar-format-diagram.jpg "Arrow's columnar layout is what makes zero-copy handoffs possible")

## What Actually Gets Faster (And What Doesn't)

It is easy to over-promise here, so separate the structural wins from the marketing:

**Real, structural wins**
- **One transposition instead of three.** Row→frame conversion happens once (in the driver, in C), not in your Python loop.
- **Lower peak memory.** Columnar buffers of a single type are compact; a list of 50M Python objects is not. GC pressure from millions of short-lived tuples disappears entirely.
- **Streaming batches.** `fetch_record_batch()` and IPC streams let you process bounded chunks with predictable memory, instead of materialising a full result set.
- **No re-encode between stages.** If stage A writes IPC and stage B reads it, the buffers are reused as-is.

**Things Arrow does not fix**
- **A slow query stays slow.** No serialisation format makes a missing index irrelevant.
- **Network throughput.** Flight SQL removes encoding cost, not bytes on the wire — compression settings still matter.
- **Bad schemas.** Wide string columns and deeply nested types still cost you; Arrow makes them cheaper to move, not free.
- **Small queries.** For ten rows, driver overhead dominates and none of this matters.

Measure with your own workload before rewriting anything: time `execute()` separately from `fetch`, and count the conversions. The pattern that usually shows up is that a job spends more time building DataFrames than querying — and that is precisely the cost ADBC and Flight SQL remove.

## Pitfalls Worth Knowing Before You Migrate

- **`fetch_arrow_table()` is not lazy.** It materialises the whole result. For large results use `fetch_record_batch()` and process batch by batch.
- **Chunked arrays surprise people.** An Arrow table can hold multiple chunks per column; `to_pandas()` handles it, hand-written buffer access often doesn't. Call `.combine_chunks()` when your code requires contiguity.
- **Type mapping is the real migration work.** `NUMERIC`/`DECIMAL`, timestamps with and without timezone, and nullable-everything schemas all map differently than in a row driver. Pin the schema and assert on it in tests.
- **Flight SQL without TLS is a footgun.** `?transport=tcp` on anything but localhost is plaintext, including your auth header. Terminate TLS at the server or use a sidecar.
- **Auth headers are RPC metadata, not connection options.** Different drivers name these options differently; read the driver's docs rather than copying a snippet from another language.
- **Version skew between driver manager and driver.** `adbc_driver_manager` loads a shared library; a mismatched `adbc_driver_flightsql` build fails with a confusing symbol error. Pin both in the same lockfile.
- **IPC files are not self-versioning.** They embed a schema but not your application's expectations. Write the schema version alongside the file — future you will need it.

If you are choosing the compute engine that consumes these batches, the [Polars vs Vaex vs Datatable comparison](../2026-06-20-dataframe-processing-libraries-polars-vaex-datatable/) shows which of them truly operate on Arrow buffers, and the [DuckDB vs Doris vs Pinot OLAP comparison](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-olap-guide/) covers the query side. For pipelines where the transport layer is the bottleneck, the [Databend vs DataFusion vs Ballista engine review](../2026-05-14-self-hosted-data-processing-engines-databend-vs-datafusion-vs-ballista-guide/) is the natural next read.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ADBC vs Arrow Flight SQL vs JDBC in 2026: Stop Copying Rows Between Your Database and Your Pipeline",
  "description": "A practical comparison of Apache Arrow database connectivity options in 2026: ADBC drivers, Arrow Flight SQL over gRPC, and Arrow IPC, with runnable code and migration pitfalls.",
  "datePublished": "2026-10-24",
  "dateModified": "2026-10-24",
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

### Is ADBC a replacement for JDBC?

Functionally, for analytical reads, yes — it covers connect, execute, fetch and bulk ingest, and the Java ecosystem gets a JDBC-compatible bridge. It is not a byte-for-byte replacement: JDBC's row-oriented `ResultSet` semantics are not what ADBC exposes, and transaction/isolation behaviour depends on the underlying driver. Applications that rely on obscure JDBC features should migrate behind the Flight SQL JDBC driver instead of rewriting.

### Do I need Flight SQL to benefit from Arrow?

No. ADBC drivers front existing databases like PostgreSQL and SQLite without any server change, and they already eliminate the row→columnar conversion on the client. Flight SQL adds a second win — Arrow across the network — but requires a server that speaks the protocol.

### What is the difference between Arrow IPC and Parquet?

Both store columnar data. Parquet is a compressed, encoded storage format optimised for size and partial reads from object storage. Arrow IPC stores buffers in memory layout so they can be memory-mapped and read with no decoding. Use Parquet at rest, IPC between pipeline stages.

### Can Flight SQL work with PostgreSQL?

Not directly — PostgreSQL speaks its own wire protocol. You either use an ADBC PostgreSQL driver (client-side Arrow) or put a Flight SQL gateway in front of it. The gateway is worth it when multiple languages and services need the same columnar endpoint.

### Does this work outside Python?

Yes. ADBC has C/C++, Go, R, Ruby and Java bindings; Flight SQL is available to any gRPC client and ships an official JDBC driver; Arrow IPC libraries exist for most mainstream languages. The reason these three layers are worth separating is exactly that they let different languages meet at the same contract.

### How much memory does the Arrow path actually save?

It depends on the data, but the mechanism is predictable: a row-oriented result materialises one object per row plus per-column boxing, while Arrow keeps typed contiguous buffers. Jobs that previously needed to hold the full result in memory often fit comfortably when streaming record batches — measure peak RSS before and after rather than trusting a rule of thumb.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
