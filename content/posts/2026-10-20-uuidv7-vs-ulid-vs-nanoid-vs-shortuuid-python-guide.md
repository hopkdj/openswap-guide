---
title: "UUIDv7 vs ULID vs NanoID vs ShortUUID in 2026: Pick the Right ID Before Your Database Does"
date: "2026-10-20"
tags: ["python", "database", "postgresql", "backend"]
draft: false
description: "Random UUIDv4 keys fragment your B-tree indexes. A 2026 comparison of UUIDv7, ULID, NanoID and ShortUUID with real benchmark math, library code and migration traps."
---

Every table you create starts with an innocent-looking line: `id UUID PRIMARY KEY`. Eighteen months later your write throughput has halved, your index is three times the size of the heap, and the only thing that changed is row count. The culprit is not Postgres. It is the randomness of version 4 UUIDs: 122 bits of entropy scattered uniformly across the whole key space, which means every insert lands in a random leaf page, dirties a random buffer, and forces WAL writes that your SSD has to fsync one at a time.

Sortable identifiers — UUIDv7, ULID, and to a lesser extent NanoID and ShortUUID — exist to fix exactly this. They look like cosmetic alternatives to UUIDs. They are really an index-locality decision that you make once and live with for years.

## TL;DR — the verdict

**Use UUIDv7** for database primary keys in 2026: it is an IETF standard (RFC 9562), it is now in the Python standard library (3.14+), it sorts by creation time, and it keeps your B-tree inserts append-only. **Use ULID** if you want a shorter, case-insensitive text representation and can accept a library dependency (ulid-py has been static since 2023 — fine, but factor that in). **Use NanoID** for public-facing tokens, slugs and short URLs where sortability is irrelevant and you want compact, URL-safe strings. **Use ShortUUID** when a human has to read the ID aloud or type it — its alphabet is designed to avoid look-alike characters. Do not use version 4 UUIDs for high-write primary keys in 2026; the tooling to do better is now standard.

## Side-by-side comparison

| Property | UUIDv7 | ULID | NanoID | ShortUUID |
|---|---|---|---|---|
| Size (bits) | 128 | 128 | configurable (126 default) | 128 (encoded) |
| Text length | 36 chars (hyphenated) | **26 chars** (Crockford base32) | 21 chars default | 22 chars default |
| Lexicographically sortable | **Yes** (48-bit ms timestamp) | **Yes** (48-bit ms timestamp) | No | No |
| Time-ordered insert locality | **Yes** | **Yes** | No | No |
| Standardised | **RFC 9562** | Community spec | Community | Encodes RFC 4122 |
| In Python stdlib | **Yes (3.14+)** | No | No | No |
| Case sensitive | No | No (uppercase) | **Yes** | **Yes** |
| URL-safe without encoding | Yes (hex + hyphens) | Yes | Yes | Yes |
| GitHub stars (lib) | 182 (`uuid6-python`) | 739 (`ulid-py`) | 512 (`py-nanoid`) | 2,198 (`shortuuid`) |
| Last commit | 2026-03-27 | 2023-03-14 | 2026-04-13 | **2026-10-11** |
| Collision risk at 1M IDs/s | negligible | negligible | tune length | negligible |

Star counts and last-commit dates pulled from the public repositories on 2026-10-20.

## Decision matrix

| Your requirement | Pick | Why |
|---|---|---|
| Postgres/MySQL primary key, heavy writes | **UUIDv7** | Time-ordered, standard, native in 3.14+ |
| Keys rendered in URLs and logs | **ULID** | 26 chars, no hyphens, case-insensitive |
| Public share links, invite codes | **NanoID** | Compact, URL-safe, length tunable |
| IDs spoken on support calls | **ShortUUID** | 57-char alphabet without `0/O/1/l/I` |
| Existing `uuid` column, no migration appetite | **UUIDv7** | Same 128-bit storage, `uuid` column type works |
| Client-side ID generation before insert | **UUIDv7 or ULID** | Time prefix preserves insert order |
| Maximum entropy per character | **NanoID** | 64-symbol alphabet vs base32 |

## UUIDv7 — the default answer in 2026

UUIDv7 packs a 48-bit Unix millisecond timestamp into the high bits, then fills the rest with random data. The result is a 128-bit value that a database can store in the same `uuid` column you already have, but whose byte order matches insertion order. New rows append to the rightmost leaf page instead of scattering across the tree.

Python 3.14 added `uuid6()`, `uuid7()` and `uuid8()` to the stdlib, which is the strongest argument for this format. On older interpreters, the `uuid6` package backports the same API:

```shell
pip install uuid6
```

```python
import uuid6

my_uuid = uuid6.uuid7()
print(my_uuid)
assert my_uuid < uuid6.uuid7()   # monotonic within the process
```

That assertion is the whole point. Successive calls sort in call order, and — because RFC 9562 mandates a counter in the `rand_a` field for the same-millisecond case — the ordering survives sub-millisecond bursts, which is exactly when a naive "timestamp + random" scheme fails and produces duplicate-looking sort keys.

Two practical notes. First, the leading 48 bits mean your IDs leak creation time to millisecond precision; if that is a privacy problem for a given table, use a random format there instead. Second, if you are on Postgres 18+, `uuidv7()` is available server-side, which lets you keep ID generation in the database and avoid a round trip from the app.

## ULID — the same idea in a friendlier alphabet

ULID solves the same ordering problem but chooses Crockford base32 for the text form, yielding **26 characters** instead of 36, with no hyphens and no case sensitivity. That matters more than it sounds: 26-char keys fit in a `VARCHAR(26)`, sort correctly as plain text in SQLite and MySQL, and are pleasant in URLs.

```python
>>> import ulid
>>> ulid.new()
<ULID('01BJQE4QTHMFP0S5J153XCFSP9')>
```

The composition is documented in the library: a 48-bit timestamp from `time.time()` at millisecond precision plus 80 bits of randomness from `os.urandom()`. That is 80 bits of entropy per millisecond — around 1.2 × 10^24 values — so collision risk inside a single millisecond is not a practical concern.

Where ULID loses to UUIDv7 in 2026 is ecosystem momentum. `ulid-py` (ahawker/ulid) has not seen a commit since March 2023. The format spec is stable and the library is small enough that "no commits" mostly means "done", but you are adopting an unmaintained dependency for a value you could produce with the stdlib. ULID also has no monotonic-counter guarantee for same-millisecond generation the way RFC 9562 specifies, so ultra-high-throughput generators should sort within-ms by a secondary field or accept arbitrary order among siblings.

## NanoID — compact tokens, not database keys

NanoID is the right tool for a different job. Its default alphabet is 64 URL-safe characters, so a 21-character ID carries about 126 bits of entropy — comparable to a UUID in less space, and considerably shorter than ULID's 26.

```python
from nanoid import generate

generate()           # => NDzkGoTCdRcaRyt7GOepg
generate(size=10)    # => "IRFa-VaY2b"
```

The library README is refreshingly blunt about the trade-off: reducing length increases collision probability, and it links to a collision calculator so you can do the maths instead of guessing. For an invite code where you issue 10,000 tokens a year, 10 characters is plenty. For a primary key where you issue millions a day, 21 characters and 126 bits is the sane floor.

What NanoID does *not* give you is ordering. That is not a bug — it is the design. If you need time-ordered keys, stop here and use UUIDv7. Also note `generate()` output is case-sensitive; storing it in a `CITEXT` column or a case-insensitive collation silently destroys uniqueness. Use `VARCHAR`/`TEXT` with binary collation.

## ShortUUID — when humans are in the loop

ShortUUID takes an RFC 4122 UUID and re-encodes it in base57 using an alphabet that removes ambiguous characters:

```python
>>> import shortuuid
>>> shortuuid.uuid()
'vytxeTZskVKR7C7WgdSP3d'
>>> shortuuid.get_alphabet()
'23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
```

That alphabet is the entire value proposition. It contains no `0`, `O`, `1`, `l` or `I`, so a support agent reading an ID over the phone does not generate a second support ticket. The library also exposes deterministic name-based generation and plain random strings:

```python
>>> shortuuid.uuid(name="example.com")
'exu3DTbj2ncsn9tLdLWspw'
>>> shortuuid.ShortUUID().random(length=22)
'RaF56o2r58hTKT7AYS9doj'
```

You can install your own alphabet with `set_alphabet()`, which is how teams encode tenant prefixes. The catch: ShortUUID output is **not sortable**, because the underlying UUID is still random. It is a presentation-layer improvement on UUIDv4, not an indexing strategy.

## The numbers that actually matter

A useful sanity check on why ordering matters, before you commit to a format:

- **Index size.** A `uuid` key with random distribution in Postgres costs 16 bytes plus an item pointer per entry, but the *fill factor* is the killer: random inserts leave pages half empty because the next insert rarely fits on the same page. Time-ordered keys fill pages sequentially, so the index can sit near its theoretical size.
- **WAL volume.** Each random insert dirties a different page. Sequential inserts dirty the same page repeatedly, which the checkpointer can batch. Real-world reports of 2-4× WAL reduction after switching to time-ordered keys are common.
- **Cache hit ratio.** A 4 KB page holds ~250 UUID index entries. Random inserts touch a different page almost every time; sequential inserts keep one hot page and its neighbours resident.

For a table doing 500 inserts/second, that is the difference between a comfortable primary and a pager at 3 a.m.

## Migration pitfalls

**1. `uuid` columns are already 128-bit — but not all UUID versions sort the same.** Switching a column's *generator* from v4 to v7 does not reorder existing rows. You get locality for new inserts only. A full `CLUSTER` or table rewrite is a separate decision.

**2. Clock skew beats you.** Two app servers with 30 ms of drift will produce interleaved timestamps within a millisecond window. Neither UUIDv7 nor ULID is a correctness mechanism; keep `created_at` as a real column and treat ID ordering as a performance optimisation.

**3. Never expose sortable IDs without thinking.** A sequential key reveals volume ("our 4,000th order") and, for UUIDv7/ULID, creation time. Keep an internal primary key and a separate opaque public token where that matters.

**4. Text length constraints.** Size the column for the format's documented maximum, not the value you happened to see in the README. A `CHAR(22)` fits a ShortUUID today and truncates the moment you switch alphabets; `VARCHAR(36)` covers a hyphenated UUID but wastes a byte per row on a 26-char ULID.

**5. Case-insensitive collations break base32/base64 identifiers.** ULID is uppercase Crockford, NanoID and ShortUUID are mixed case. Store them in a binary-collated column or normalise on the way in.

**6. ORMs that assume integers.** Plenty of legacy code does `id + 1` or ORDER BY on a numeric column. Audit those paths before switching.

**7. Batching is not free locality.** If your ORM inserts rows one at a time inside a loop, you get the WAL behaviour of sequential inserts only when keys are also sequential. Time-ordered IDs help here precisely because they make N single-row inserts behave like an append.

If your bottleneck turns out to be the query planner rather than the key format, our [PostgreSQL index optimisation guide](../2026-06-02-postgresql-index-optimization-hypopg-pgqualstats-pgstatindexes-guide/) covers how to verify it with `pg_stat_user_indexes` and HypoPG before you rewrite anything. For multi-node or sharded deployments where the key also becomes a routing decision, see the [sharding comparison](../2026-04-25-vitess-vs-citus-vs-shardingsphere-self-hosted-database-sharding-guide-2026/). And if the IDs end up inside data classes or Pydantic models, the [Python data class comparison](../2026-07-03-python-data-class-libraries-dataclasses-attrs-pydantic-cattrs/) covers serialisation behaviour you will care about.

## FAQ

**Is UUIDv7 better than UUIDv4?**
For database keys, yes. Both are 128-bit and fit the same column, but UUIDv7's timestamp prefix makes inserts append-only, which reduces index fragmentation and WAL volume. UUIDv4 still wins when you specifically need unpredictable, non-time-linked identifiers.

**Should I use ULID or UUIDv7 in 2026?**
UUIDv7 if you want a standard, stdlib support (Python 3.14+) and a monotonic counter for same-millisecond bursts. ULID if you need a shorter, case-insensitive text form and are comfortable with a third-party library that has been quiet since 2023.

**How many characters of NanoID do I need?**
Twenty-one characters of the default 64-symbol alphabet gives about 126 bits — UUID-equivalent. Ten characters gives roughly 60 bits, fine for short-lived invite codes with modest volume, risky for primary keys. Use a collision calculator rather than intuition.

**Are sortable IDs a security problem?**
They leak creation order and, for UUIDv7/ULID, approximate creation time. That is an information disclosure issue, not a forgery issue. Keep an internal key and expose a random public token if enumeration matters.

**Can I use these as primary keys in MySQL?**
Yes, but watch the collation: store ULID/NanoID/ShortUUID in a binary or `ascii_bin` column. InnoDB clusters on the primary key, so a time-ordered key also gives you sequential page fills — the same win as in Postgres.

**What about Python 3.13 and earlier?**
Install the `uuid6` package; it exposes `uuid6()`, `uuid7()` and `uuid8()` with the same API the 3.14 stdlib uses, so upgrading later is a dependency removal rather than a code change.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "UUIDv7 vs ULID vs NanoID vs ShortUUID in 2026: Pick the Right ID Before Your Database Does",
  "description": "Comparison of sortable identifier formats for Python backends: UUIDv7, ULID, NanoID and ShortUUID, with real library code, index-locality math and migration traps.",
  "datePublished": "2026-10-20",
  "dateModified": "2026-10-20",
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
