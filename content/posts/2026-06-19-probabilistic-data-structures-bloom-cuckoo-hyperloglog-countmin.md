---
title: "Self-Hosted Probabilistic Data Structures: Bloom Filters vs Cuckoo Filters vs HyperLogLog vs Count-Min Sketch"
date: "2026-06-19"
tags: ["data-structures", "algorithms", "distributed-systems", "golang", "analytics"]
draft: false
---

## Introduction

When building self-hosted monitoring systems, analytics pipelines, or distributed databases, you frequently need to answer questions like "have I seen this user before?", "how many unique visitors today?", or "what are the top 100 most frequent items?" — but at massive scale where exact answers are too expensive.

This is where **probabilistic data structures** excel. They trade a tiny amount of accuracy for dramatic reductions in memory usage — often 100-1000x less than exact approaches. Four structures dominate the landscape: **Bloom Filters** (membership testing), **Cuckoo Filters** (deletable membership), **HyperLogLog** (cardinality estimation), and **Count-Min Sketch** (frequency estimation).

This article compares these four data structures with production-ready Go implementations you can embed in your self-hosted Go services.

## Why Probabilistic Structures for Self-Hosted Systems

Self-hosted infrastructure rarely has the resources of cloud-scale deployments. A self-hosted analytics pipeline running on a few Raspberry Pi nodes can't store every user ID in a hash set with millions of entries. Probabilistic structures let you answer the same questions with kilobytes instead of gigabytes.

| Structure | Operation | Memory (typical) | Error Rate | Supports Deletion? |
|---|---|---|---|---|
| Bloom Filter | "Have I seen X?" | 1.44 × N × log<sub>2</sub>(1/ε) bits | False positives only | No |
| Cuckoo Filter | "Have I seen X?" | ~(log<sub>2</sub>(1/ε) + 2) / α bits per item | False positives only | Yes |
| HyperLogLog | "How many unique X?" | ~1.5 KB (standard) | ~2% relative error | Not applicable |
| Count-Min Sketch | "How many times X?" | O(d × w) counters | Over-counts only | Not applicable |
| Exact (HashMap) | All of the above | O(N) — often GBs | 0% | Yes |

## Bloom Filters: The Classic Membership Test

A Bloom filter answers one question: "Is item X in the set?" It can say "definitely no" or "probably yes." This asymmetry makes it perfect for caches, databases, and network filters where false positives are tolerable (check the cache, if "no" we know for sure the data isn't there) but false negatives are unacceptable.

### bits-and-blooms/bloom (2,790⭐, Go)

This is the standard Go Bloom filter, used by InfluxDB, CockroachDB, and many other production systems:

```go
package main

import (
    "fmt"
    "github.com/bits-and-blooms/bloom/v3"
)

func main() {
    // Create a Bloom filter expecting 1,000,000 items
    // with 0.1% false positive rate
    filter := bloom.NewWithEstimates(1000000, 0.001)

    // Add items
    filter.AddString("user:alice")
    filter.AddString("user:bob")

    // Test membership
    fmt.Println(filter.TestString("user:alice"))  // true
    fmt.Println(filter.TestString("user:charlie")) // false (definitely not present)

    // Serialize for sharing between services
    buf, _ := filter.MarshalJSON()
    fmt.Printf("Filter size: %d bytes\n", len(buf))

    // Estimate current fill ratio
    fmt.Printf("Approximate count: %d\n", filter.ApproximatedSize())
}
```

**How It Works:**

1. Allocate a bit array of size M, initialized to 0.
2. For each item to add, compute K independent hash functions, each producing an index into the bit array.
3. Set all K bits to 1.
4. To test membership: if ALL K bits are 1, return "probably present." If ANY bit is 0, return "definitely absent."

The false positive rate ε is approximately `(1 - e^{-KN/M})^K`. With optimal K ≈ 0.693 × M/N, memory needed is M ≈ 1.44 × N × log₂(1/ε) bits.

**Pros:**
- Extremely memory efficient (1.44N log₂(1/ε) bits)
- O(K) insertion and lookup — constant time
- No false negatives — safe for cache/database negative lookups
- Battle-tested in production (Chrome's Safe Browsing, Apache HBase, Cassandra)

**Cons:**
- Cannot delete items (removing bits would affect other items)
- Cannot count frequencies
- Cannot enumerate stored items
- Tunable false positive rate, but lower rate costs more memory

## Cuckoo Filters: Bloom's Deletable Cousin

Cuckoo filters improve on Bloom filters by adding deletion support while using comparable or better memory. They work by storing a "fingerprint" of each item in one of two candidate buckets (the "cuckoo" name comes from cuckoo birds pushing eggs out of nests — when both buckets are full, an existing fingerprint is relocated to its alternate bucket).

### seiflotfy/cuckoofilter (1,229⭐, Go)

```go
package main

import (
    "fmt"
    "github.com/seiflotfy/cuckoofilter"
)

func main() {
    // Create a cuckoo filter with capacity 1,000,000
    cf := cuckoofilter.NewCuckooFilter(1000000)

    // Add items
    cf.InsertUnique([]byte("user:alice"))
    cf.InsertUnique([]byte("user:bob"))
    cf.InsertUnique([]byte("user:charlie"))

    // Test membership
    fmt.Println(cf.Lookup([]byte("user:alice")))   // true
    fmt.Println(cf.Lookup([]byte("user:unknown"))) // false

    // Delete items — Bloom filters can't do this!
    cf.Delete([]byte("user:bob"))
    fmt.Println(cf.Lookup([]byte("user:bob"))) // false (deleted)

    // Count current items (approximate)
    fmt.Printf("Item count: %d\n", cf.Count())
}
```

**Pros:**
- Supports deletion (key advantage over Bloom)
- Better space efficiency than Bloom for false positive rates < 3%
- O(1) lookup, insert, and delete
- Compact footprint — stores only fingerprints, not full items

**Cons:**
- Insertion can fail if both candidate buckets are full (rare with proper sizing)
- Must use unique insert (or track insert count separately) since same item can be inserted multiple times
- Slightly more complex implementation
- Less widely deployed than Bloom filters

## HyperLogLog: Counting Unique Visitors

HyperLogLog estimates the **cardinality** (number of distinct elements) of a multiset. It's used by Redis, Presto, and every major analytics system to answer "how many unique users visited today?" in constant memory regardless of the actual count.

HyperLogLog uses ~1.5 KB to count up to 10^9 distinct items with ~2% standard error. Compare this to a HashSet which would need gigabytes for the same task.

```go
package main

import (
    "fmt"
    "math"
    "math/bits"
)

// Minimal HyperLogLog implementation for illustration
type HyperLogLog struct {
    registers []uint8
    m         uint32 // number of registers
    alpha     float64
}

func NewHLL(precision uint8) *HyperLogLog {
    m := uint32(1 << precision) // m = 2^precision registers
    return &HyperLogLog{
        registers: make([]uint8, m),
        m:         m,
        alpha:     0.7213 / (1 + 1.079/float64(m)),
    }
}

func (h *HyperLogLog) Add(hash uint64) {
    // Use first p bits to select register, rest for leading zero count
    idx := hash >> (64 - bits.Len32(h.m-1))
    w := hash << bits.Len32(h.m-1)
    leadingZeros := uint8(bits.LeadingZeros64(w) + 1)
    if leadingZeros > h.registers[idx] {
        h.registers[idx] = leadingZeros
    }
}

func (h *HyperLogLog) Count() uint64 {
    sum := 0.0
    zeros := 0
    for _, v := range h.registers {
        sum += 1.0 / math.Pow(2, float64(v))
        if v == 0 {
            zeros++
        }
    }
    estimate := h.alpha * float64(h.m) * float64(h.m) / sum

    // Small range correction
    if estimate <= 2.5*float64(h.m) && zeros > 0 {
        estimate = float64(h.m) * math.Log(float64(h.m)/float64(zeros))
    }

    return uint64(estimate)
}

func main() {
    hll := NewHLL(14) // 2^14 = 16384 registers, ~12KB memory
    hll.Add(1234567890)
    hll.Add(9876543210)
    fmt.Printf("Estimated unique count: %d\n", hll.Count())
}
```

**Pros:**
- Constant memory regardless of cardinality
- Mergeable: combine two HLL sketches by taking max of each register pair
- Used in production by Redis PFADD/PFCOUNT, Google BigQuery, Presto
- ~2% standard error with standard 12 KB configuration

**Cons:**
- Cannot enumerate members
- Cannot delete items
- Approximate only — exact counts require a different approach
- Small cardinalities (< few thousand) have higher relative error

## Count-Min Sketch: Tracking Frequencies

Count-Min Sketch estimates how many times each item has been seen. It's used in network monitoring (top talkers), database query planning, and real-time analytics dashboards.

Like a Bloom filter, Count-Min Sketch uses multiple hash functions — but instead of setting bits, it increments counters in a 2D grid. The estimated frequency for an item is the minimum of all its counters (hence "Count-Min").

```go
package main

import (
    "fmt"
    "hash/fnv"
)

type CountMinSketch struct {
    rows    uint32
    cols    uint32
    counters [][]uint64
}

func NewCMS(width, depth uint32) *CountMinSketch {
    counters := make([][]uint64, depth)
    for i := range counters {
        counters[i] = make([]uint64, width)
    }
    return &CountMinSketch{rows: depth, cols: width, counters: counters}
}

func (c *CountMinSketch) Add(item []byte, count uint64) {
    for i := uint32(0); i < c.rows; i++ {
        h := fnv.New64a()
        h.Write([]byte{byte(i)})
        h.Write(item)
        idx := h.Sum64() % uint64(c.cols)
        c.counters[i][idx] += count
    }
}

func (c *CountMinSketch) Estimate(item []byte) uint64 {
    min := ^uint64(0)
    for i := uint32(0); i < c.rows; i++ {
        h := fnv.New64a()
        h.Write([]byte{byte(i)})
        h.Write(item)
        idx := h.Sum64() % uint64(c.cols)
        if c.counters[i][idx] < min {
            min = c.counters[i][idx]
        }
    }
    return min
}

func main() {
    // 2000 columns × 5 rows = 10,000 counters = ~80KB
    cms := NewCMS(2000, 5)

    cms.Add([]byte("api:login"), 1000)
    cms.Add([]byte("api:login"), 500)
    cms.Add([]byte("api:search"), 50)
    cms.Add([]byte("api:search"), 20)

    fmt.Printf("api:login estimated count: %d\n", cms.Estimate([]byte("api:login")))   // ~1500
    fmt.Printf("api:search estimated count: %d\n", cms.Estimate([]byte("api:search"))) // ~70
    fmt.Printf("api:unknown estimated count: %d\n", cms.Estimate([]byte("api:unknown"))) // 0
}
```

**Pros:**
- Sub-linear memory in number of distinct items
- Mergeable (add two CMS by summing counters — usable in distributed monitoring)
- Only over-counts (never under-counts) — safe for rate limiting and quota enforcement
- Works with streaming data — no need to store all items

**Cons:**
- Over-counts due to hash collisions (tunable error bound)
- Error proportional to total count in the sketch (sum of all additions)
- Cannot enumerate tracked items
- No deletion support

## Choosing the Right Structure

| Question | Best Tool | Typical Memory |
|---|---|---|
| "Is X in my set?" (no deletions needed) | Bloom Filter | ~1 KB per 1K items at 1% FP |
| "Is X in my set?" (need to delete) | Cuckoo Filter | ~1 KB per 1K items at 1% FP |
| "How many unique X today?" | HyperLogLog | ~12 KB regardless of count |
| "How many times has X appeared?" | Count-Min Sketch | ~80 KB for millions of items |
| "What are the top-10 most frequent X?" | Count-Min Sketch + Heap | ~100 KB |

For related reading on data infrastructure, see our [distributed SQLite databases guide](../rqlite-vs-litefs-vs-dqlite-distributed-sqlite-databases-guide-2026/) and our [code search tools comparison](../self-hosted-code-search-tools-sourcegraph-zoekt-hound-guide/). For monitoring context, check our [distributed tracing guide](../signoz-jaeger-uptrace-self-hosted-apm-distributed-tracing-guide/).

## FAQ

### Can I use Bloom filters in a self-hosted database like PostgreSQL?

Yes! PostgreSQL has the `bloom` extension for index access methods. A Bloom filter index on multiple columns can dramatically speed up queries with AND conditions by quickly eliminating rows that can't match. Enable it with `CREATE EXTENSION bloom;` then `CREATE INDEX ON table USING bloom (col1, col2, col3);`.

### What's the main reason to choose Cuckoo over Bloom?

Deletion support. If you're tracking active sessions or temporary tokens where items expire and need to be removed, Bloom filters accumulate false positives over time (bits stay set forever). Cuckoo filters let you clean up, maintaining accuracy. For permanent membership tracking (like blocklists), Bloom is simpler and equally effective.

### How accurate is HyperLogLog in practice?

With standard 14-bit precision (16,384 registers, ~12 KB), HyperLogLog achieves ~0.8% relative error at millions of distinct items. At thousands, you can use HyperLogLog++ improvements (bias correction, sparse representation at low cardinalities) for sub-1% error across all scales. Redis implements HyperLogLog++ and achieves <1% error in practice.

### Can I merge sketches across multiple self-hosted servers?

Yes! HyperLogLog merges by taking the per-register maximum. Count-Min Sketch merges by summing per-counter values. Bloom filters merge by OR-ing bit arrays. This makes them ideal for distributed monitoring — each server maintains its own sketch, then a central aggregator merges them for global estimates.

### When should I NOT use probabilistic data structures?

When exact answers are required (financial calculations, security decisions), when the dataset is small enough for exact structures (< 1 million items), or when you need to enumerate or iterate over stored items. For example, don't use a Bloom filter to store user IDs for an access control list — a false positive means granting access to an unauthorized user.



---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Probabilistic Data Structures: Bloom Filters vs Cuckoo Filters vs HyperLogLog vs Count-Min Sketch",
  "description": "In-depth comparison of Bloom Filters, Cuckoo Filters, HyperLogLog, and Count-Min Sketch for self-hosted analytics and monitoring systems. Includes Go code examples, memory usage comparisons, and use case guidance.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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