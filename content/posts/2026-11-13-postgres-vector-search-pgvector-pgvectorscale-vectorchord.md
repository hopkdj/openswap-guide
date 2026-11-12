---
title: "pgvector vs pgvectorscale vs VectorChord in 2026: The Postgres Vector Index Shootout"
date: "2026-11-13"
tags: ["postgresql", "vector-search", "self-hosted", "database", "comparison"]
draft: false
description: "pgvector, pgvectorscale and VectorChord compared on index structure, quantization, recall and operational cost — with real extension SQL, Docker configs and the tuning knobs that actually move the needle."
---

Postgres already holds your users, your orders and your permissions. The only question left is whether it can also hold eight million 1536-dimension vectors without turning every `ORDER BY embedding <=> $1` into a sequential scan that eats your IOPS budget. In 2026 there are three serious ways to answer that inside Postgres itself: **pgvector** (23,662 GitHub stars), **pgvectorscale** (3,164 stars, from Timescale) and **VectorChord** (1,841 stars, from TensorChord).

All three are `CREATE EXTENSION` away. They are not interchangeable, and picking wrong shows up months later as a recall cliff or a storage bill.

## TL;DR — the 30-second verdict

- **Use pgvector** unless you have a measured problem. It is the default, it is in every managed Postgres offering, and since 0.7 it ships `halfvec`, `sparsevec` and binary quantization. Most deployments never outgrow it.
- **Use pgvectorscale** when your vectors no longer fit in RAM and you want a disk-first index with label filtering that stays fast. StreamingDiskANN is built for exactly that case, and it speaks normal `vector` columns.
- **Use VectorChord** when storage cost is the constraint. RaBitQ compression plus 4-bit types is the most aggressive footprint reduction of the three, and it is the only one that advertises a per-vector cost target rather than a benchmark chart.

## The comparison table (data pulled from GitHub on 2026-11-13)

| Dimension | pgvector | pgvectorscale | VectorChord |
|---|---|---|---|
| GitHub stars | 23,662 | 3,164 | 1,841 |
| Last push | 2026-11-12 | 2026-10-14 | 2026-08-06 |
| License | PostgreSQL | PostgreSQL | AGPLv3 |
| Implementation | C | Rust (PGRX) | Rust (PGRX) |
| Index types | HNSW, IVFFlat | StreamingDiskANN | `vchordrq`, `vchordg` |
| Compression | `halfvec`, `bit`, binary quantization | Statistical binary quantization | RaBitQ 4-bit / 8-bit |
| Filtered search | Partial indexes, iterative scans (0.8+) | Native label filtering in the index | Filtered queries, less specialised |
| Disk-first design | No, RAM-resident graph | Yes | Partially, via quantization |
| Maximum index dimensions | 2,000 (`vector`), 4,000 (`halfvec`) | Follows pgvector types | Follows pgvector types |
| Postgres versions | 13–18 | 13–17 (TimescaleDB images) | 17 and 18 images |
| Managed Postgres support | Universal | Timescale Cloud, some others | Limited |

## Decision matrix: pick by constraint, not by star count

| Your constraint | Pick | Why |
|---|---|---|
| You want zero surprises and portable SQL | **pgvector** | Every managed Postgres has it; migrations never block on an extension |
| Your index is bigger than your RAM | **pgvectorscale** | StreamingDiskANN reads from disk by design instead of thrashing a RAM graph |
| You filter by tenant or category on every query | **pgvectorscale** | Labels live in the index, so filtering does not collapse recall |
| You store tens of millions of vectors on a budget VPS | **VectorChord** | RaBitQ compression shrinks the resident footprint dramatically |
| You need `pg_upgrade` to a new major version this quarter | **pgvector** | The most conservative option; extension bumps are well trodden |
| You are on Postgres 18 already | **VectorChord** or **pgvector** | VectorChord ships `pg18` images; verify pgvectorscale support for your image tag |

## pgvector — the default you should only leave for a reason

pgvector is the reference implementation: a C extension providing `vector`, `halfvec`, `sparsevec` and `bit` types, with HNSW and IVFFlat indexes. It is MIT-simple to deploy because the project publishes images for every supported major version.

```yaml
# docker-compose.yml — pgvector on Postgres 17
services:
  db:
    image: pgvector/pgvector:pg17
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: "${PG_PASSWORD:?set a real password}"
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    command: >
      postgres
      -c shared_buffers=2GB
      -c maintenance_work_mem=2GB
      -c work_mem=64MB

volumes:
  pgdata:
```

Nothing exotic in the schema:

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id         bigserial PRIMARY KEY,
  tenant_id  bigint NOT NULL,
  body       text,
  embedding  vector(1536)
);

-- HNSW: best recall/latency for in-memory working sets
CREATE INDEX documents_embedding_idx ON documents
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 200);

-- Query-time recall knob (per session or per transaction)
SET hnsw.ef_search = 100;

SELECT id, body
FROM documents
WHERE tenant_id = 42
ORDER BY embedding <=> $1
LIMIT 10;
```

The two numbers that matter are `m` and `ef_construction`. Raising `m` from 16 to 32 roughly doubles graph memory per row and buys recall you probably do not need. Raising `ef_construction` slows the build linearly and improves the graph. Build once with generous `maintenance_work_mem` — 2 GB minimum for a few million rows — because a build that spills to disk takes hours instead of minutes.

pgvector 0.8 added iterative index scans, which fixes the classic disaster where a `WHERE tenant_id = 42` clause filters out so many candidates that the index returns eight rows instead of ten. Turn it on explicitly:

```sql
SET hnsw.iterative_scan = relaxed_order;
SET hnsw.max_scan_tuples = 20000;
```

If you are still on 0.7, the only correct answer for filtered search is a **partial index** per high-traffic filter value, or a `halfvec` index with a wider candidate pool. Do not pretend `LIMIT 10` with a filter returns ten rows.

## pgvectorscale — disk-first indexing with labels baked in

pgvectorscale is a Rust extension (PGRX) that adds the `diskann` access method, StreamingDiskANN, plus statistical binary quantization. Its premise: the graph does not need to be fully resident. It is designed for the case where your vector table is 40 GB and your instance has 8 GB of RAM.

It installs on top of pgvector, and the extension graph does the work:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;

CREATE INDEX document_embedding_idx ON document_embedding
  USING diskann (embedding vector_cosine_ops);

SELECT id
FROM document_embedding
ORDER BY embedding <=> $1
LIMIT 10;
```

The feature that distinguishes it in practice is label-based filtered search, taken from Microsoft's Filtered DiskANN work. Instead of filtering after the graph walk, the labels are part of the index:

```sql
ALTER TABLE documents ADD COLUMN labels smallint[];

CREATE INDEX documents_diskann_labels_idx ON documents
  USING diskann (embedding vector_cosine_ops, labels);

-- Filtered query the planner can actually use
SELECT id FROM documents
WHERE labels && ARRAY[3, 7]::smallint[]
ORDER BY embedding <=> $1
LIMIT 10;
```

That `&&` array overlap form is the one that maps onto the index's label predicate. Writing `WHERE tenant_id = 42` on a plain column will still fall back to post-filtering, and you will see recall drop as the filter becomes more selective. This is the single most common misconfiguration with pgvectorscale.

Deployment uses the TimescaleDB image family, because the extension ships pre-built there:

```yaml
services:
  db:
    image: timescale/timescaledb-ha:pg17
    environment:
      POSTGRES_PASSWORD: "${PG_PASSWORD:?set a real password}"
    volumes:
      - pgdata:/home/postgres/pgdata/data
    ports:
      - "5432:5432"
volumes:
  pgdata:
```

Two tuning notes from operating it: `diskann.query_search_list_size` controls how many candidates the disk walk considers, and `diskann.query_rescore` controls how many of those get re-scored with full-precision vectors. Raising rescore improves recall at the cost of random reads — which is exactly the knob you want on NVMe and the knob you must not raise on network-attached storage.

## VectorChord — compression as the primary design goal

VectorChord (successor to pgvecto.rs) attacks the cost axis. It applies RaBitQ quantization with autonomous reranking and exposes native 4-bit and 8-bit vector types, which is how it claims roughly an order of magnitude more vectors per dollar than uncompressed storage. The project publishes its own images, currently up to Postgres 18.

```yaml
services:
  db:
    image: ghcr.io/tensorchord/vchord-postgres:pg18-v1.1.1
    environment:
      POSTGRES_PASSWORD: "mysecretpassword"
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

```sql
CREATE EXTENSION IF NOT EXISTS vchord CASCADE;

CREATE TABLE items (
  id        bigserial PRIMARY KEY,
  embedding vector(1536)
);

CREATE INDEX items_embedding_idx ON items
  USING vchordrq (embedding vector_l2_ops);

SELECT id FROM items
ORDER BY embedding <-> $1
LIMIT 10;
```

The `vchordrq` index applies quantization transparently, with the reranking layer restoring precision for the final candidate set. There is also `vchordg`, a graph-based index for the case where you want a more conventional structure. The practical guidance: start with `vchordrq`, measure recall against exact search on a sample, and only then decide whether the 4-bit type is safe for your data.

Two operational gotchas are specific to this extension. First, the image tag encodes the Postgres major version — pinning `pg18-v1.1.1` means you are on Postgres 18, and a careless `pg_upgrade` to a different major version requires the matching extension image. Second, the license is **AGPLv3**, which is fine for self-hosted internal use and a genuine conversation for anyone shipping Postgres as part of a product. Read it before you standardise.

## Pitfalls that cost real money

**1. `maintenance_work_mem` is the build-time bottleneck for all three.** Index builds are memory-hungry. If the graph or quantizer spills to disk, a 30-minute build becomes a 6-hour build and your maintenance window is gone.

**2. Recall is not a property of the extension — it is a property of your data.** Every default in this space is tuned for 1536-dimension text embeddings at moderate scale. Your 384-dimension vectors, your duplicate-heavy corpus and your unusually clustered data will behave differently. Build a 1,000-query ground-truth set with exact nearest neighbours and measure recall@10. Nothing else you read, including this article, substitutes for that.

**3. Filtering destroys recall unless the index knows about the filter.** Post-filtering is the number one cause of "the vector index returns irrelevant results." Either use labeled indexes, partial indexes, or iterative scans — consciously.

**4. Dimension limits are hard walls.** pgvector caps HNSW at 2,000 dimensions for `vector` and 4,000 for `halfvec`. If you are at 3,072 dimensions, you either reduce dimensionality or store as `halfvec` — and reducing dimensionality changes your recall, so re-measure.

**5. `ANALYZE` after bulk load, before you trust the planner.** A freshly loaded table with stale statistics will pick a sequential scan and you will blame the extension.

**6. Extension upgrades need a plan.** `ALTER EXTENSION ... UPDATE` can require an index rebuild depending on the version jump. Read the changelog for the exact version pair, and take a base backup first — restoring a 50 GB database because of a botched extension upgrade is a bad afternoon.

**7. Do not benchmark on a laptop with the index in page cache.** Every one of these engines looks fast when the working set fits in RAM. Benchmark on the instance class you will actually run, with cold caches, or your numbers are fiction.

## So which one?

Start with **pgvector**. It is the boring correct answer for the vast majority of deployments, and its newer `halfvec` and iterative-scan features closed most of the gap that made people look elsewhere in 2023.

Move to **pgvectorscale** when you can name the constraint: the index does not fit in RAM, or you filter by label on nearly every query. Those are its two design centres, and it is excellent at both.

Move to **VectorChord** when the constraint is storage cost per vector and you have measured the recall impact of quantization on your own corpus. It is the most aggressive compressor of the three, and AGPLv3 is the price of admission.

Whatever you choose, keep the exact-search path available. A `SET enable_indexscan = off` query that returns correct neighbours is your ground truth, and the day your recall silently degrades is the day you will need it.

## Related reading

If your vectors are small enough that a separate engine makes more sense than a Postgres extension, the [embedded vector search comparison](../2026-10-13-embedded-vector-search-lancedb-sqlite-vec-pgvector-guide/) covers LanceDB, sqlite-vec and pgvector side by side. Running Postgres on Kubernetes and need to install extensions declaratively? The [Postgres operator comparison](../2026-05-10-postgresql-operators-kubernetes-cloudnativepg-zalando-crunchydata-guide/) shows how CloudNativePG and friends handle extension images. And when you need to stream embedding updates from an OLTP primary into your vector table, the [logical replication guide](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/) covers pglogical, wal2json and pgoutput.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "pgvector vs pgvectorscale vs VectorChord in 2026: The Postgres Vector Index Shootout",
  "description": "pgvector, pgvectorscale and VectorChord compared on index structure, quantization, recall and operational cost — with real extension SQL, Docker configs and tuning knobs.",
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

**Is pgvector fast enough for 10 million vectors?**
Yes, for most workloads, provided the HNSW graph fits in memory and you have measured recall. Ten million 1536-dimension vectors stored as `halfvec` is roughly 30 GB of raw vector data plus index overhead, so it wants a memory-optimised instance. If that does not fit your budget, pgvectorscale's disk-first index or VectorChord's quantization are the two credible escape routes.

**Can I use pgvectorscale and VectorChord in the same database?**
They are separate extensions with separate index access methods, so nothing stops you from installing both, but running two vector indexes on the same column doubles your write amplification. Pick one per table. Mixing them is only sensible when different tables have genuinely different constraints.

**Does pgvectorscale replace pgvector?**
No. pgvectorscale depends on pgvector's types and operators and adds the `diskann` access method on top. You install `vector` first and then `vectorscale`. Any guide that tells you to uninstall pgvector is wrong.

**Why does my filtered vector query return fewer rows than my LIMIT?**
Because the filter is applied after the index walk. With pgvector before 0.8, or without iterative scans enabled, the index returns `ef_search` candidates and the filter discards most of them. Fix it with `hnsw.iterative_scan`, a partial index, or pgvectorscale's label-based index — not by raising `LIMIT`.

**Is VectorChord's AGPLv3 license a problem for internal use?**
For internal self-hosted use, no — AGPLv3 obligations trigger on distribution and on providing the software as a network service to third parties. If Postgres with VectorChord is part of a product you ship or host for customers, talk to legal before standardising on it.

**How do I measure recall properly?**
Take a sample of 1,000 query vectors, run exact nearest-neighbour search with the index disabled, store the true top-10, then run the same queries with the index enabled and compute the overlap. Anything under 0.95 recall@10 on a workload where correctness matters is a tuning problem, not a "close enough" result.

**Which extension has the best managed-Postgres support?**
pgvector, by a wide margin. Almost every managed Postgres offering ships it, including the major cloud providers. pgvectorscale is available on Timescale Cloud and a smaller set of providers, and VectorChord is mostly a self-hosted option today.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
