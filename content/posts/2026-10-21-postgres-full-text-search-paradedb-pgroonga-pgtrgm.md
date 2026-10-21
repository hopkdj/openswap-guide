---
title: "ParadeDB vs PGroonga vs pg_trgm in 2026: Can Postgres Finally Replace Elasticsearch?"
date: "2026-10-21"
tags: ["postgresql", "full-text-search", "self-hosted", "database", "comparison"]
draft: false
cover: "/img/screenshots/paradedb-postgres-search.jpg"
description: "A practical 2026 comparison of ParadeDB, PGroonga and pg_trgm for full-text search inside PostgreSQL — real Docker and SQL configs, BM25 scoring, CJK tokenisation and the limitations that decide whether you still need a search cluster."
---

Every architecture review in 2026 contains the same sentence: "do we really need a second datastore just for search?" The answer used to be an embarrassed yes. Postgres full-text search with `tsvector` was fine for a help-centre search box and hopeless for relevance-ranked product search, typo tolerance, or Chinese and Japanese content.

That has changed. Three options now cover very different points on the spectrum, and picking the wrong one is how teams end up with a 40GB index and `ORDER BY ts_rank` queries that take four seconds.

## TL;DR — the short verdict

- **Choose ParadeDB** if you want real BM25 relevance scoring, top-k speed and aggregation inside Postgres. It is the closest thing to "Elasticsearch as an extension", and it is the one that makes the second datastore unnecessary.
- **Choose PGroonga** if your content is **CJK or mixed-language** and you do not want to maintain tokeniser dictionaries. Groonga's normalisation handles Japanese, Chinese and Korean out of the box.
- **Choose pg_trgm** for fuzzy matching on short fields — names, SKUs, emails — and for accelerating `ILIKE '%term%'`. It is not a search engine and should not be asked to rank documents.

And the honest fourth answer: if you need cross-cluster search over terabytes, custom analysers per field, or a relevance team tuning boosts weekly, you still need a dedicated engine. The gap closed, it did not vanish.

## Comparison table (GitHub data pulled 2026-10-21)

| Dimension | ParadeDB (`pg_search`) | PGroonga | pg_trgm |
|---|---|---|---|
| Stars | **9,425** | 756 | n/a (Postgres contrib) |
| Last push | 2026-10-21 | 2026-10-09 | ships with Postgres |
| Language | Rust | C | C |
| License | AGPL-3.0 | PostgreSQL License | PostgreSQL License |
| Index type | BM25 (Tantivy-based) | Groonga inverted index | GIN/GiST trigrams |
| Relevance scoring | **BM25 + `paradedb.score()`** | `pgroonga_score()` | `similarity()` only |
| Typo tolerance | Yes (fuzzy at query time) | Partial (query syntax) | **Yes, by design** |
| CJK without tokeniser config | Good | **Best** | Poor (trigrams on multibyte) |
| Aggregations / facets | **Yes, `pdb.agg()`** | No (SQL `GROUP BY`) | No |
| Highlighting | `pdb.snippet()` | `pgroonga_highlight_html()` | Manual |
| Needs a custom Postgres build | Recommended (official image) | No, standard packages | No |
| Extra service to operate | None | None | None |

The licence row matters more than people expect: AGPL-3.0 is fine for internal use and for most SaaS deployments, but it is a genuine blocker for shipping an on-premise binary product. PGroonga and pg_trgm carry the PostgreSQL licence and raise no such question.

## Decision matrix

| Use case | Pick | Why |
|---|---|---|
| Product catalogue search with relevance + facets | **ParadeDB** | BM25 scoring plus `pdb.agg()` replaces a search cluster |
| Japanese/Chinese knowledge base | **PGroonga** | Normalisation without per-language dictionaries |
| "Find customer by fuzzy name" autocomplete | **pg_trgm** | Trigram GIN index on a varchar column, 10 lines of code |
| `ILIKE '%foo%'` queries that got slow | **pg_trgm** | Turns a sequential scan into an index scan |
| Log or document search at TB scale | None of these | Use a dedicated engine; Postgres will fight you on index size |
| You already run ParadeDB for search and want fuzzy matching too | **ParadeDB + pg_trgm** | They coexist; use trigram for identifiers, BM25 for text |

## Setting up ParadeDB

ParadeDB ships as a Postgres distribution with `pg_search` preinstalled. The compose file from the repo is deliberately boring:

```yaml
services:
  paradedb:
    image: paradedb/paradedb:latest
    container_name: paradedb
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: mydatabase
    ports:
      - "5432:5432"
    volumes:
      - paradedb_data:/var/lib/postgresql/

volumes:
  paradedb_data:
```

Then the index is where the design differs from vanilla Postgres — the `key_field` is mandatory, and it is the primary key used for scoring and for updates:

```sql
CREATE EXTENSION IF NOT EXISTS pg_search;

CREATE TABLE articles (
  id        bigserial PRIMARY KEY,
  title     text NOT NULL,
  body      text NOT NULL,
  category  text NOT NULL,
  published timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX articles_search_idx ON articles
USING bm25 (id, title, body, category)
WITH (key_field = 'id');

INSERT INTO articles (title, body, category) VALUES
  ('Running Postgres on ARM', 'Notes about building and tuning Postgres on ARM servers.', 'infra'),
  ('Index maintenance basics', 'VACUUM, bloat and reindex strategies for busy tables.', 'database');

SELECT id, title, paradedb.score(id) AS rank
FROM articles
WHERE title @@@ 'postgres'
ORDER BY rank DESC
LIMIT 10;
```

Three practical details that are easy to miss:

1. **`@@@` is the ParadeDB match operator**, not `@@`. Using `@@` silently falls back to the `tsvector` operator and returns nothing useful against a BM25 index.
2. **Column weights are set at index time**, not query time. If title should outrank body, declare it in the index definition — otherwise your relevance tuning has nowhere to live.
3. **`pdb.agg()` gives you facets without a second round trip**, which is the feature that most often justifies the switch:

```sql
SELECT pdb.agg('{"terms": {"field": "category"}}') AS facets
FROM articles
WHERE body @@@ 'index';
```

The trade-off is operational: you are now running a Postgres build maintained by ParadeDB, not the stock image from your distro. That is fine for a container deployment and mildly annoying if your platform team insists on managed RDS. `pg_search` can be installed into vanilla Postgres, but the supported path is the official image.

## Setting up PGroonga

PGroonga takes the opposite approach: it is a normal extension that installs into a stock Postgres, and it delegates the text analysis to Groonga. The official images are published per Postgres major version — I verified `groonga/pgroonga:4.1.0-alpine-17` exists on Docker Hub:

```yaml
services:
  pg:
    image: groonga/pgroonga:4.1.0-alpine-17
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: docs
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

```sql
CREATE EXTENSION pgroonga;

CREATE TABLE memos (
  id      bigserial PRIMARY KEY,
  content text NOT NULL
);

CREATE INDEX memos_content_idx ON memos USING pgroonga (content);

INSERT INTO memos (content) VALUES
  ('PostgreSQLの全文検索を高速化する方法'),
  ('PostgreSQL full text search with Groonga');

SELECT id, content, pgroonga_score(tableoid, ctid) AS score
FROM memos
WHERE content &@~ 'PostgreSQL'
ORDER BY score DESC
LIMIT 5;
```

The `&@~` operator runs a Groonga query expression, which supports `OR`, `AND`, `NOT` and column prefixes without SQL gymnastics. `pgroonga_highlight_html()` produces highlighted excerpts server-side, and `pgroonga_snippet_html()` handles long documents — both useful when you would otherwise render matches in application code.

**The reason to pick PGroonga is normalisation, not features.** Groonga normalises full-width and half-width characters, case, and — crucially — does not require you to install a Japanese morphological analyser like MeCab or a Chinese segmenter like Jieba to get sane results. If your content is mixed English and CJK, this is worth more than BM25 scoring.

**The reason not to pick it:** the project is small (756 stars), the documentation is partly Japanese-first, and the extension's query syntax is its own dialect. You are also trusting a C extension inside your database process, which is a real consideration when planning major-version upgrades.

## Setting up pg_trgm (and when to stop)

`pg_trgm` ships with Postgres. There is nothing to deploy:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX customers_name_trgm_idx
  ON customers USING gin (full_name gin_trgm_ops);

SELECT id, full_name, similarity(full_name, 'Katherine Johnson') AS sim
FROM customers
WHERE full_name % 'Katherine Johnson'
ORDER BY sim DESC
LIMIT 10;
```

That `%` operator is the fuzzy-match threshold operator, and it is genuinely excellent for human-entered names. The same index accelerates `ILIKE '%term%'`:

```sql
SELECT id, full_name FROM customers
WHERE full_name ILIKE '%johnson%';
```

Where it falls over: **multi-word relevance ranking**. Trigrams have no concept of term frequency, inverse document frequency, stop words or stemming. Searching `"postgres index bloat"` with trigrams matches documents containing those substrings, in whatever order the planner feels like returning, with no meaningful score. Teams that try to build product search on `pg_trgm` end up implementing ranking in application code — which is exactly the work BM25 does for you.

Tail risk: index size. A GIN trigram index on a large text column can be several times the size of the column. On a 20GB `body` column this becomes a storage-planning problem, not a search problem.

## The `tsvector` option nobody mentions anymore

Native Postgres search (`to_tsvector`, `ts_rank`, GIN on `tsvector`) is still there and still free. It works well for English-language content with a known schema, and it has one advantage the others lack: zero new dependencies, forever.

Its weaknesses are well documented — no typo tolerance, ranking that behaves unlike BM25, per-language dictionary configuration that most teams get wrong once and never revisit, and no facets. If you are choosing in 2026, the honest ranking is: **BM25 extension for relevance, PGroonga for CJK, trigram for identifiers, native `tsvector` only when you have no budget to change anything.**

## Migration and operations pitfalls

- **Do not migrate by re-indexing everything at once on a live primary.** BM25 index builds are CPU and I/O heavy. Build on a replica, or use a maintenance window; a 50GB index build can saturate IOPS for hours.
- **Scores are not comparable across engines.** `paradedb.score()`, `pgroonga_score()` and `ts_rank()` produce different scales and different orderings. If you have relevance tests, re-baseline them after any switch.
- **`key_field` must be immutable per row.** ParadeDB uses it to track documents; an `UPDATE` that changes the key field effectively deletes and re-inserts the document. Use a stable surrogate key.
- **Revoking an extension is not a rollback.** `DROP EXTENSION` removes the index but not your application's dependency on the query syntax. Keep the old query path behind a flag until the new one has proven itself.
- **Test with your actual language mix.** Benchmarks on English Wikipedia say nothing about Japanese product names or German compound words. Ten minutes with real rows beats any published number.

## Why keep search inside Postgres at all

The operational argument is simple: every additional datastore is another backup policy, another upgrade cadence, another thing that can be up while Postgres is down and produce a split-brain search index. Teams that moved search into Postgres in 2026 mostly did it to **delete a sync pipeline**, not to save licence money — and deleting a sync pipeline deletes a whole class of "why is the search index three hours stale" incidents.

The trade-off you are accepting is coupling: heavy search load now competes with OLTP queries for the same CPU and memory. If your search traffic is read-heavy and bursty, run the search-capable Postgres on a dedicated replica and route search queries there.

For the operational side of running these databases, our [Postgres management UI comparison](../2026-05-11-self-hosted-postgresql-management-ui-pgadmin-pgweb-temboard/) covers pgAdmin, pgWeb and temboard, and the [Postgres performance dashboard guide](../2026-05-13-self-hosted-postgresql-performance-dashboards-pghero-pgwatch2-pg-stat-monitor/) covers the metrics you need to know whether an index build is helping or hurting. If your workload is analytics rather than text search, the [DuckDB vs Doris vs Pinot OLAP comparison](../2026-04-25-duckdb-vs-apache-doris-vs-apache-pinot-self-hosted-olap-guide/) is the better starting point.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ParadeDB vs PGroonga vs pg_trgm in 2026: Can Postgres Finally Replace Elasticsearch?",
  "description": "Practical comparison of ParadeDB, PGroonga and pg_trgm for full-text search inside PostgreSQL, including Docker setups, BM25 scoring, CJK tokenisation and migration pitfalls.",
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

**Is ParadeDB a fork of PostgreSQL?**
It ships as a Postgres distribution with the `pg_search` extension preinstalled, but the extension itself can be installed into a vanilla Postgres build. In practice most teams run the official `paradedb/paradedb` image because it is the supported configuration.

**Can PGroonga handle English as well as Japanese?**
Yes. PGroonga indexes English text with the same inverted-index approach, and it also offers a `pgroonga` operator class with tokeniser options if you want stemming-like behaviour. Its advantage is that it does not *require* language-specific configuration to work on CJK.

**Which one gives the best relevance ranking?**
ParadeDB, because it implements BM25 with per-column weights and exposes the score for ordering. PGroonga returns a Groonga score that is useful for ordering but is not BM25, and `pg_trgm` only exposes similarity, which is not relevance.

**Do these extensions work with logical replication?**
The indexes are rebuilt on the replica, so `pg_search`, PGroonga and GIN trigram indexes all work with streaming and logical replication — but the extensions must be installed on every node, and a major-version upgrade means rebuilding each index. Budget for that in upgrade planning.

**Will my index fit in memory?**
Usually not, and it does not need to. BM25 and Groonga indexes are read from disk with caching; the practical constraint is disk IOPS during index builds and cold-cache queries. `pg_trgm` GIN indexes are the least predictable in size and deserve a capacity check before you create one on a large text column.

**Can I run ParadeDB and PGroonga in the same database?**
Yes, they are separate extensions with separate index types. Whether you should is another question — two ranking models in one schema means two sets of relevance expectations to maintain.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
