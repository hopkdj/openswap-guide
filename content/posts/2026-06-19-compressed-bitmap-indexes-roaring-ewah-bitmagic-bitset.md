---
title: "Self-Hosted Compressed Bitmap Indexes: Roaring Bitmap vs EWAH vs BitMagic vs bitset"
date: "2026-06-19"
tags: ["data-structures", "algorithms", "database", "golang", "performance"]
draft: false
---

## Introduction

Bitmap indexes are one of the oldest and most powerful indexing techniques in database systems — they encode set membership as bit strings where each bit position represents a row or document ID. When you need to compute fast intersections, unions, or differences of large datasets (AND, OR, NOT over millions of records), bitmaps are unmatched.

But naive bitmaps quickly become impractical. A 500-million-row table needs 500 million bits (62.5 MB) per indexed value — and with sparse data, most of those bits are zeros. **Compressed bitmap indexes** solve this by exploiting runs of zeros (or ones) to achieve compression ratios of 10-1000x, while still supporting SIMD-accelerated logical operations.

This article compares four compressed bitmap implementations for self-hosted infrastructure: **Roaring Bitmap**, **EWAH**, **BitMagic**, and Go's **bitset** library.

## Why Compressed Bitmaps for Self-Hosted Analytics

Self-hosted analytics platforms, search engines, and monitoring systems routinely process queries like "show me all error events from service X in region Y during the last hour." Bitmap indexes accelerate these by pre-computing bitmaps for each dimension (service=X, region=Y, hour=Z), then combining them with fast bitwise AND operations.

For self-hosted time-series databases and log aggregators, compressed bitmaps directly improve query latency. A tool like InfluxDB uses Roaring Bitmaps internally for its TSI (Time Series Index) to track which measurement+tag combinations exist in each shard.

| Format | Compression Method | Best For | Memory (example: 10M sparse ints) | SIMD Support |
|---|---|---|---|---|
| Uncompressed bitset | None | Dense data | 10M bits = 1.25 MB | Yes |
| Roaring Bitmap | Hybrid: arrays + bitmaps + runs | Mixed density, most general | ~2-5 MB typical | AVX2, AVX-512, NEON |
| EWAH | Word-aligned run-length encoding | Very sparse, lot of zeros | ~0.5-2 MB typical | SSE2 |
| BitMagic | SIMD-optimized bit-transposed | Dense bitwise operations | ~1-3 MB typical | SSE, AVX2 |
| Go bitset | Sparse words | Moderate sparsity | ~3-8 MB typical | No (pure Go) |

## Roaring Bitmap: The Industry Standard

Roaring Bitmap is the most widely adopted compressed bitmap format, used by Apache Spark, Apache Kylin, Elasticsearch, Druid, InfluxDB, and many more. Its key innovation is a **hybrid storage model** that adapts dynamically: dense chunks use bitmaps, sparse chunks use sorted arrays, and very dense chunks use run-length encoding.

### RoaringBitmap/CRoaring (1,845⭐, C with SIMD)

The C implementation provides SIMD-accelerated operations and FFI bindings for Go, Python, Java, Rust, and more:

```go
package main

import (
    "fmt"
    "github.com/RoaringBitmap/roaring"
)

func main() {
    // Create two roaring bitmaps
    rb1 := roaring.New()
    rb2 := roaring.New()

    // Add sparse values
    for i := uint32(0); i < 1000000; i += 100 {
        rb1.Add(i)
    }
    for i := uint32(0); i < 1000000; i += 150 {
        rb2.Add(i)
    }

    // Fast intersection
    intersection := roaring.And(rb1, rb2)
    fmt.Printf("Intersection cardinality: %d\n", intersection.GetCardinality())

    // Fast union with SIMD acceleration (AVX2/AVX-512)
    union := roaring.Or(rb1, rb2)
    fmt.Printf("Union cardinality: %d\n", union.GetCardinality())

    // Statistics
    fmt.Printf("Bytes per value (rb1): %.2f\n",
        float64(rb1.GetSizeInBytes())/float64(rb1.GetCardinality()))

    // Serialize for storage or network transfer
    buf, _ := rb1.ToBytes()
    fmt.Printf("Serialized size: %d bytes\n", len(buf))

    // Deserialize
    rb3 := roaring.New()
    rb3.FromBuffer(buf)
    fmt.Printf("Deserialized cardinality: %d\n", rb3.GetCardinality())

    // Iterate efficiently
    iter := rb1.Iterator()
    count := 0
    for iter.HasNext() {
        iter.Next()
        count++
    }
    fmt.Printf("Iterated over %d values\n", count)
}
```

**Hybrid Storage in Action:**

Roaring partitions the 32-bit integer space into chunks of 2^16 (65,536) values. Each chunk is stored in the most efficient format:

```text
Chunk 0    (0-65535):    [10, 20, 30, 40]           → Sorted Array (4 × 2 bytes = 8 bytes)
Chunk 1    (65536-131071): 8192 bits set out of 65536  → Bitmap (8192 bytes)  
Chunk 1000 (65,536,000-...): 0,1,2,...,65535         → Run [0, 65535] (4 bytes)
```

This dynamic adaptation means Roaring handles everything from ultra-sparse (0.001% fill rate) to ultra-dense (99% fill rate) equally well.

**Pros:**
- Industry standard: used by Spark, Druid, InfluxDB, Elasticsearch, Kylin
- SIMD-accelerated C core (AVX2/AVX-512/NEON) with Go bindings
- Hybrid storage adapts to data density automatically
- Rich API: intersection, union, difference, XOR, rank, select
- Serialization format is cross-language (Java, Go, C, Python, Rust, Node.js)

**Cons:**
- Go binding is CGo — adds build complexity and performance overhead
- Chunk size (2^16) is fixed; suboptimal for power-of-2-aligned distributions
- Memory overhead for many near-empty chunks

## EWAH: Word-Aligned Simplicity

EWAH (Enhanced Word-Aligned Hybrid) compresses bitmaps using a two-word encoding scheme: **marker words** describe runs of clean 0-words or 1-words, and **dirty words** store the actual bits where runs aren't homogeneous. It's used by Git for pack file indexing and by various OLAP databases.

### lemire/EWAHBoolArray (459⭐, C++)

### lemire/javaewah (568⭐, Java)

```java
// Java EWAH example
import com.googlecode.javaewah.EWAHCompressedBitmap;

public class EWAHExample {
    public static void main(String[] args) {
        EWAHCompressedBitmap ewah1 = new EWAHCompressedBitmap();
        EWAHCompressedBitmap ewah2 = new EWAHCompressedBitmap();

        // Add sparse values
        for (int i = 0; i < 1000000; i += 50) {
            ewah1.set(i);
            if (i % 3 == 0) ewah2.set(i);
        }

        // Bitwise AND
        EWAHCompressedBitmap intersection = ewah1.and(ewah2);
        System.out.println("Intersection size: " + intersection.cardinality());

        // Bitwise OR
        EWAHCompressedBitmap union = ewah1.or(ewah2);
        System.out.println("Union size: " + union.cardinality());

        // Memory usage
        System.out.println("ewah1 bytes: " + ewah1.sizeInBytes());
    }
}
```

**How EWAH Encoding Works:**

```text
[0x8000000A] [0x12345678] [0x9ABCDEF0] ...
  Marker word    Dirty word     Dirty word

Marker word breakdown:
  - Bit 31: 0 = clean run, 1 = dirty word follows
  - Bits 30-0: Number of clean 64-bit words (if clean run) or dirty words (if dirty)
```

**Pros:**
- Simple, well-understood encoding
- Very efficient for extremely sparse bitmaps (< 0.1% fill rate)
- Good compression ratio for long runs of zeros
- Used in Git (commit reachability bitmaps)

**Cons:**
- Less efficient for moderate density (1-30% fill rate) compared to Roaring
- No native SIMD acceleration (SSE2 only for some operations)
- Java-focused; Go support limited
- Slower random access due to sequential decoding requirement

## BitMagic: SIMD-Optimized Bit-Transposed Format

BitMagic is a C++ library from Anatoliy Kuznetsov that uses a **bit-transposed** storage format — instead of storing bits row by row, it stores bit-planes column by column. This enables SIMD operations on 128-bit SSE or 256-bit AVX2 registers, processing 128-256 bits at a time.

**Key features:**
- Bit-transposed format: bits are stored in column-major order for SIMD-friendly access
- SSE4.2 and AVX2 acceleration for all logical operations
- Built-in support for rank/select operations (find the Nth set bit)
- Compression via run-length encoding within each bit-plane
- Used in bioinformatics and financial analytics for high-throughput bitwise queries

```cpp
// C++ BitMagic example (conceptual)
#include "bm.h"

int main() {
    bm::bvector<> bv1;
    bm::bvector<> bv2;

    // Set sparse bits
    for (unsigned i = 0; i < 1000000; i += 100) {
        bv1.set(i);
    }

    // SIMD-accelerated operations (AVX2 on modern CPUs)
    bv1.optimize();           // Reorganize blocks for SIMD
    bm::bvector<> result = bv1 & bv2;  // Bitwise AND at 128-256 bits/cycle

    // Rank operation: count bits up to position
    auto count = result.count_range(0, 500000);

    // Select operation: find position of Nth set bit
    auto pos = result.get_first();  // Find first set bit

    return 0;
}
```

**Pros:**
- Native SIMD acceleration (SSE4.2, AVX2) for all operations
- Bit-transposed format optimized for hardware-friendly access patterns
- Built-in rank/select operations (foundational for succinct data structures)
- Very fast for dense bitmaps (> 10% fill rate)

**Cons:**
- C++ only (no Go bindings) — integration requires FFI
- More complex library with steeper learning curve
- Optimized for dense bitmaps; sparse performance comparable to Roaring
- Less community adoption than Roaring

## Go bitset: The Native Choice

For pure Go projects that want zero CGo dependencies, the `bits` package provides a clean, idiomatic bitset with automatic dense/sparse optimization.

### bits-and-blooms/bitset (1,505⭐, Go)

```go
package main

import (
    "fmt"
    "github.com/bits-and-blooms/bitset"
)

func main() {
    // Create bitsets
    bs1 := bitset.New(10000000) // 10 million bits
    bs2 := bitset.New(10000000)

    // Set bits
    for i := uint(0); i < 1000000; i += 100 {
        bs1.Set(i)
    }
    for i := uint(0); i < 1000000; i += 150 {
        bs2.Set(i)
    }

    // Logical operations
    intersection := bs1.Intersection(bs2)
    fmt.Printf("Intersection count: %d\n", intersection.Count())

    union := bs1.Union(bs2)
    fmt.Printf("Union count: %d\n", union.Count())

    // Efficient iteration over set bits
    count := uint(0)
    for word, bits := bs1.NextSet(0); bits > 0; word, bits = bs1.NextSet(word + 1) {
        count++
    }
    fmt.Printf("Iterated over %d set bits\n", count)

    // Check specific bits
    fmt.Printf("Bit 5000 set? %v\n", bs1.Test(5000))

    // Serialization
    buf, _ := bs1.MarshalBinary()
    fmt.Printf("Serialized: %d bytes\n", len(buf))

    bs3 := bitset.New(10000000)
    bs3.UnmarshalBinary(buf)
    fmt.Printf("Roundtrip count: %d\n", bs3.Count())
}
```

**Pros:**
- Pure Go — no CGo, simple builds, easy cross-compilation
- Clean, idiomatic Go API
- Good performance for moderate sparsity
- Dense representation backed by []uint64 slices
- Compatible with Go's tooling (race detector, profiler)

**Cons:**
- No compression — stores ALL words, even zero ones
- Higher memory usage for sparse datasets (10M bits = 1.25 MB always)
- No SIMD acceleration
- Slower for massive-scale operations compared to Roaring's C core

## Performance at Scale

For a self-hosted search engine indexing 100 million documents with 10,000 unique terms, each term's posting list contains roughly 10,000 document IDs. Comparing the four formats:

| Format | Memory (10K IDs) | Intersection Speed | Serialization | Go Native? |
|---|---|---|---|---|
| Roaring Bitmap | ~8-12 KB | ~50 ns per pair | ~20 ns per value | Via CGo |
| EWAH | ~6-10 KB | ~80 ns per pair | ~30 ns per value | Java/C++ only |
| BitMagic | ~8-10 KB | ~15 ns per pair (SIMD) | ~25 ns per value | C++ only |
| Go bitset | ~1,250 KB (uncompressed) | ~5 ns per pair | ~10 ns per value | Yes |

Roaring Bitmap is the best general-purpose choice for Go projects despite CGo overhead. For pure Go projects with small-to-moderate datasets (< 10M documents), Go bitset works well. For C++ projects with dense bitmaps and high throughput requirements, BitMagic's SIMD optimization wins.

For related data infrastructure reading, see our [graph databases comparison](../self-hosted-graph-databases-neo4j-arangodb-nebulagraph-guide-2026/), our [distributed SQL guide](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/), and our [code search tools comparison](../self-hosted-code-search-tools-sourcegraph-zoekt-hound-guide/).

## FAQ

### Why do search engines use compressed bitmaps instead of posting lists?

Both are used. Bitmaps excel at Boolean queries (AND/OR/NOT) with many conditions because bitwise operations run in hardware — a single SIMD instruction processes 256 bits at once. Posting lists (skip lists) are better for ranked retrieval (TF-IDF, BM25) where you need document frequencies and position data. Modern engines like Elasticsearch use both: bitmaps for filters and posting lists for scoring.

### Can I use Roaring Bitmap for time-series data?

Yes, it's production-proven in InfluxDB's TSI (Time Series Index). The pattern: assign each measurement+tag combination a unique series ID, then maintain a Roaring Bitmap per shard with the series IDs present. Queries like "cpu.usage where host=web01" become bitmap intersections that run in microseconds even across millions of series.

### Is there a pure Go alternative to Roaring with comparable performance?

The `github.com/RoaringBitmap/roaring` package is the standard Go binding (uses CGo to call CRoaring). There's a pure Go port at `github.com/RoaringBitmap/roaring/purego` but it's ~2-3x slower than the CGo version for bulk operations. For zero-CGo deployments, consider Go bitset for smaller datasets or accept the pure Go Roaring for portability.

### How does Roaring handle updates and deletions?

Adding a value: O(1) amortized — appends to the chunk's container. Deleting a value: O(log n) in array containers, O(1) in bitmap containers. Roaring supports in-place mutation. For high-throughput write workloads, batch updates in sorted order for best performance (sorted arrays are built efficiently from presorted input).

### What's the compression ratio for real-world document indexes?

Typical compression ratios: 10-50x for document ID bitmaps (sparse: one bit per document, few documents per term). Run-length-encoded chunks achieve 100-1000x for consecutive document runs (all documents in a shard). Roaring's hybrid approach means the compression adapts automatically — you don't need to pre-analyze data density.



---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Compressed Bitmap Indexes: Roaring Bitmap vs EWAH vs BitMagic vs bitset",
  "description": "Compare compressed bitmap index implementations for self-hosted search engines, databases, and analytics: Roaring Bitmap, EWAH, BitMagic, and Go bitset. Includes code examples, performance comparisons, and architecture details.",
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