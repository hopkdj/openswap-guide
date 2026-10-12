---
title: "Embedded Vector Search in 2026: LanceDB vs sqlite-vec vs pgvector (No Server Required)"
date: "2026-10-13"
tags: ["database", "search", "vector-search", "self-hosted"]
draft: false
cover: "/img/screenshots/lancedb-hero.jpg"
---

You do not need a cluster to do fast similarity search. That statement would have been controversial in 2022, when the default answer was "stand up a vector database service and point your app at it." In 2026 the embedded tier is genuinely good — and it is the right answer for a surprising number of projects. The three options that matter are **pgvector** (23,326 stars), **LanceDB** (11,652 stars), and **sqlite-vec** (8,183 stars). One bolts onto the database you already run, one is a columnar library that lives inside your process, and one is a single C extension that runs anywhere SQLite compiles. Picking the wrong one means either a migration later or paying operational costs for capacity you never needed.

**TL;DR:** If you already run PostgreSQL and your data lives there, use **pgvector** — it keeps vectors next to your rows, gives you ACID transactions and JOINs for free, and needs zero new services. If you are building a local-first or edge application with a budget of one process and no database server, use **sqlite-vec** — it is pre-v1 but tiny, dependency-free, and runs on anything. If your vectors are large, your dataset is heavy, or you want columnar analytics alongside search, use **LanceDB** — the Lance format and its versioning model are the differentiator. If you are doing this at a scale where you need a distributed cluster, none of the three applies and you should be reading a different article.

## The Core Question: Where Does the Index Live?

All three tools implement the same primitive — approximate nearest neighbour search over float vectors — so the differentiator is not the algorithm. It is **where the index lives and who manages it**:

- **pgvector** puts the index inside your PostgreSQL database. It participates in transactions, backups, replication, and access control that you already have. There is no second system to monitor.
- **sqlite-vec** puts the index inside a SQLite file. That file can live on disk, on a phone, in a browser tab compiled to WebAssembly, or on a Raspberry Pi. There is no server at all.
- **LanceDB** puts the index inside a Lance columnar dataset on object storage or local disk. It is a library, not a service, but the storage format is designed for versioned, large-scale analytical workloads.

The practical consequence: pgvector's performance ceiling is your Postgres instance, sqlite-vec's ceiling is a single writer process, and LanceDB's ceiling is object storage throughput.

## Feature Comparison at a Glance

| Dimension | pgvector | LanceDB | sqlite-vec |
|---|---|---|---|
| **GitHub stars** | 23,326 | 11,652 | 8,183 |
| **Last commit** | 2026-10-08 | 2026-10-12 | 2026-05-18 |
| **License** | PostgreSQL License | Apache-2.0 | Apache-2.0 |
| **Architecture** | Postgres extension | Embedded library + columnar format | SQLite extension (pure C) |
| **Deployment** | Your existing Postgres 13+ | In-process, local or object storage | In-process, anywhere SQLite runs |
| **Vector types** | `vector`, `halfvec`, `bit`, `sparsevec` | Float and binary vectors, multimodal columns | float, int8, binary |
| **Index types** | HNSW, IVFFlat | IVF_PQ and related Lance indexes | Brute-force scan (no ANN index yet) |
| **Distance metrics** | L2, inner product, cosine, L1, Hamming, Jaccard | L2, cosine, dot product | L2 and cosine |
| **Transactions / ACID** | Full — it is Postgres | Versioned datasets, not transactions | SQLite semantics |
| **Metadata filtering** | Full SQL — JOINs, WHERE, CTEs | SQL filter expressions and Arrow columns | Metadata and auxiliary columns |
| **Language bindings** | Any Postgres client | Python, Node.js/TypeScript, Rust, REST | Python, Node, Ruby, Go, Rust, Datasette, rqlite |
| **Versioning** | Postgres backup/PITR | Built-in dataset versioning, zero-copy | File-level |
| **Maturity** | Production, widely deployed | Production, fast-moving | Explicitly pre-v1 |
| **Best fit** | Existing Postgres stacks | Local-first analytics and large datasets | Edge, mobile, single-binary apps |

Read the last-commit column carefully. pgvector and LanceDB are both shipping code this week. **sqlite-vec's most recent commit is 2026-05-18** — roughly five months of quiet. The project is sponsored by Mozilla Builders and is not abandoned, but the maintenance pace is a real consideration for production use, and the README says plainly that it is pre-v1 and breaking changes should be expected.

## Decision Matrix: Which Store for Which Job

| Your situation | Pick this | Why |
|---|---|---|
| Postgres is already your system of record | **pgvector** | Vectors join against real rows in the same query, with real transactions |
| Desktop app, CLI tool, or Electron/Tauri client | **sqlite-vec** | One file, no server, cross-platform binaries and WASM support |
| Running in a browser or on a Raspberry Pi | **sqlite-vec** | Pure C, zero dependencies, compiles where SQLite compiles |
| Millions of vectors on object storage | **LanceDB** | Columnar layout and zero-copy versioning are built for this |
| You want analytics and search over the same data | **LanceDB** | Arrow-based columns, queryable from DuckDB and Polars |
| You need ACID guarantees on writes | **pgvector** | The other two offer file-level or dataset-level consistency, not transactions |
| Dataset under ~100K vectors and low query volume | **sqlite-vec** | Brute-force scan is fast enough; no index to tune |
| You need a GPU to build the index | **LanceDB** | GPU-accelerated index construction is a documented feature |

## pgvector — Vectors Where Your Data Already Lives

pgvector's appeal is that it is not a new system. It is an extension, and enabling it is one statement in each database where you want it:

```sh
cd /tmp
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install # may need sudo
```

```tsql
CREATE EXTENSION vector;
```

From there, a vector column is an ordinary column with a dimension:

```sql
CREATE TABLE items (id bigserial PRIMARY KEY, embedding vector(3));
```

```sql
INSERT INTO items (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
```

Nearest-neighbour search is an `ORDER BY` on a distance operator:

```sql
SELECT * FROM items ORDER BY embedding <-> '[3,1,2]' LIMIT 5;
```

The operator set is the part that makes migration easy: `<->` for L2, `<#>` for negative inner product, `<=>` for cosine distance, and `<+>` for L1. Because it is Postgres, your similarity query can carry a `WHERE` clause that filters on real business columns, and it can `JOIN` against your users table without a round trip to a second store. Our [SQLite management tooling guide](../2026-05-16-self-hosted-sqlite-management-datasette-sqlite-web-litecli-guide/) covers the sibling problem of administering small databases, and the same principle applies: fewer stores, fewer consistency problems.

For scale, add an HNSW or IVFFlat index and reach for quantisation when memory becomes the constraint. `halfvec` halves storage per dimension, `bit` compresses binary vectors dramatically, and `sparsevec` handles high-dimensional sparse data. The honest limit is that if you outgrow your Postgres instance, the answer is a bigger instance, not a shard.

**Choose pgvector if:** your data is already in Postgres and you would rather tune one database than operate two systems.

## LanceDB — The Embedded Columnar Store

LanceDB is a library that opens a dataset on local disk or object storage. It is built on the Lance columnar format and ships SDKs for Python, TypeScript/Node, Rust, and a REST API. The setup is a pip install and a connect:

```bash
pip install lancedb
```

```python
import lancedb
db = lancedb.connect('<PATH_TO_LANCEDB_DATASET>')
table = db.open_table('my_table')
results = table.search([0.1, 0.3]).limit(20).to_list()
print(results)
```

![LanceDB official logo](/img/screenshots/lancedb-logo.jpg "LanceDB — embedded columnar vector store built on the Lance format")

Two things distinguish it from the other options. First, **the columnar format**, which means the same dataset is readable by Arrow-based tooling — DuckDB, Polars, Pandas — so you can run analytical queries and similarity search over one copy of the data instead of exporting between systems. Our [DuckDB vs Apache Doris vs Apache Pinot comparison](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-olap-guide/) is the relevant background if that trade-off matters to you.

Second, **dataset versioning**. LanceDB manages versions of the dataset itself, with zero-copy reads, so you can snapshot a search index, continue writing, and still query the previous state. For a dataset that is continuously re-indexed, that is a real operational advantage over a store where rebuilding the index means downtime.

One practical detail worth knowing before you deploy: the default wheel targets `x86-64-haswell` (AVX2 + FMA + F16C) for performance on current hardware. On older CPUs, importing the library fails with an `Illegal instruction` error rather than degrading gracefully. The project publishes a `lancedb-compat` package built at the `x86-64-v2` baseline with runtime dispatch, and the two packages conflict at install time, so pick one deliberately:

```bash
pip uninstall lancedb
pip install lancedb-compat
```

**Choose LanceDB if:** you want embedded search over large or multimodal datasets, you value dataset versioning, or you want columnar analytics next to your index.

## sqlite-vec — One Extension, No Infrastructure

sqlite-vec is a SQLite extension written in pure C with no dependencies. Its README calls it "extremely small, fast enough," and the storage model is a virtual table:

```sql
.load ./vec0

create virtual table vec_examples using vec0(
  sample_embedding float[8]
);

-- vectors can be provided as JSON or in a compact binary format
insert into vec_examples(rowid, sample_embedding)
  values
    (1, '[-0.200, 0.250, 0.341, -0.211, 0.645, 0.935, -0.316, -0.924]'),
    (2, '[0.443, -0.501, 0.355, -0.771, 0.707, -0.708, -0.185, 0.362]'),
    (3, '[0.716, -0.927, 0.134, 0.052, -0.669, 0.793, -0.634, -0.162]'),
    (4, '[-0.710, 0.330, 0.656, 0.041, -0.990, 0.726, 0.385, -0.958]');
```

```sql
-- KNN style query
select
  rowid,
  distance
from vec_examples
where sample_embedding match '[0.890, 0.544, 0.825, 0.961, 0.358, 0.0196, 0.521, 0.175]'
order by distance
limit 2;
```

The `vec0` virtual table accepts float, int8, and binary vectors, and it can hold ordinary metadata, auxiliary, and partition-key columns alongside the embedding so you can filter cheaply without a second lookup. Because it is pure C, the extension travels to places a database server cannot: Python (`pip install sqlite-vec`), Node (`npm install sqlite-vec`), Ruby, Go, Rust, Datasette, rqlite, and WebAssembly in the browser.

Understand what you are giving up. There is no approximate index yet — queries are brute-force scans, which is genuinely fast for tens of thousands of vectors and increasingly painful past a million. There are no transactions beyond SQLite's own. And the project states it is pre-v1, so pin your version and read the changelog before upgrading.

**Choose sqlite-vec if:** your product is local-first, you want zero infrastructure, and your dataset fits in a single file.

## Common Pitfalls and Tuning Traps

**Index build timing will surprise you.** Whether you use pgvector's HNSW or a Lance index, building it takes time and memory proportional to dataset size. Plan the build into deployment rather than discovering it during a traffic spike, and remember that an unindexed scan on a large table is not a fallback — it is an outage.

**Dimension mismatches fail loudly at insert time, not query time.** Store the expected dimension in your schema and validate before writing. A mixed-dimension table is unfixable without a full rewrite.

**Normalise your vectors if you mix metrics.** Cosine and inner-product results diverge from L2 once magnitudes vary. Normalise at write time and pick one operator, or your relevance tuning will chase ghosts.

**Quote numerical precision when comparing benchmarks.** Recall at a fixed `k` depends on the index, the parameters, and the data distribution. Numbers from someone else's blog post are not your numbers.

**sqlite-vec's brute-force scan has a hard ceiling.** It is excellent below a few hundred thousand vectors. Above that, quantise and move to a store with an approximate index rather than tuning SQL.

**Do not put the database file on a network filesystem.** SQLite locking over NFS is a classic source of corruption, and the same caution applies to reads during writes on network-attached storage.

**Plan for re-embedding.** When you change the embedding model, every stored vector is invalidated. Keep the source text or image identifier in a column so you can rebuild the index without re-ingesting the corpus, and version the model name alongside the data.

## FAQ

**Do I need a dedicated vector database if I already use Postgres?**
Usually not. pgvector covers nearest-neighbour search with real ACID guarantees and lets you filter and join against your existing tables in a single query. The dedicated-store argument only becomes compelling at a scale where you need distributed sharding or where embeddings have grown beyond what one instance can hold in memory.

**What is the difference between LanceDB and a traditional vector database service?**
LanceDB is a library that opens a dataset rather than a service you connect to over the network. It is built on a columnar format, so the same data is queryable from Arrow-based analytics tools, and it manages dataset versions with zero-copy reads. That combination — embedded, columnar, versioned — is what separates it from both client-server stores and the SQL extension options.

**Can sqlite-vec run in a browser or on a phone?**
Yes, and that is its strongest use case. Because the extension is pure C with no dependencies, it compiles to WebAssembly and to mobile targets, which means an offline-first application can perform similarity search locally with no server round trip at all.

**How many vectors can each option realistically handle?**
sqlite-vec is comfortable to roughly a few hundred thousand vectors with brute-force scanning. pgvector handles millions with an HNSW or IVFFlat index and quantisation, bounded by your Postgres instance's memory and disk. LanceDB scales into the tens of millions and beyond on object storage, provided you accept index build costs. If you need a distributed cluster past that, compare the client-server options in our [Qdrant vs Milvus vs Weaviate vs Chroma breakdown](../qdrant-vs-milvus-vs-weaviate-vs-chroma/).

**Which one has the smallest operational footprint?**
sqlite-vec, unambiguously — one file, one extension, no process. pgvector is next, because it adds nothing new to operate if Postgres already exists in your stack. LanceDB is still a library rather than a service, but you do own its storage layout, index builds, and version history.

**Is pgvector fast enough for a production search feature?**
For most applications, yes. With an HNSW index and vectors held in memory, pgvector returns nearest neighbours in single-digit milliseconds at scales in the low millions. The point at which it stops being enough is the point at which you need memory that no single instance can offer — and that is an infrastructure decision, not a library one.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Embedded Vector Search in 2026: LanceDB vs sqlite-vec vs pgvector (No Server Required)",
  "description": "Comparing pgvector, LanceDB, and sqlite-vec in 2026 for embedded similarity search — index architecture, ACID guarantees, scale limits, and deployment trade-offs.",
  "datePublished": "2026-10-13",
  "dateModified": "2026-10-13",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
