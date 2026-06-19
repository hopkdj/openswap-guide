---
title: "Self-Hosted Consistent Hashing: Jump Hash vs Ring Hash vs Rendezvous Hashing Libraries"
date: "2026-06-19"
tags: ["distributed-systems", "caching", "load-balancing", "algorithms", "golang"]
draft: false
---

## Introduction

When building self-hosted distributed systems — from caching layers to load balancers to sharded databases — one fundamental problem keeps appearing: **how do you distribute data or requests across a changing set of servers without reshuffling everything?**

The answer is **consistent hashing**. Unlike naive modulo-based hashing (which remaps nearly all keys when the server count changes), consistent hashing ensures only a minimal fraction of keys are reassigned when nodes join or leave. This makes it indispensable for distributed caches (Memcached, Redis Cluster), CDN edge routing, distributed databases (Cassandra, DynamoDB), and load balancers.

This article compares four major consistent hashing algorithm implementations you can integrate into your self-hosted Go infrastructure: **Jump Consistent Hash**, **Hash Ring (Ketama-style)**, **Rendezvous Hashing**, and **Google's Groupcache**.

## Why Consistent Hashing Matters for Self-Hosted Infrastructure

In a self-hosted environment, servers come and go — you scale up during peak loads, replace failing hardware, or upgrade capacity. Without consistent hashing, every topology change forces a full data reshuffle, overwhelming your network and storage.

Consistent hashing solves this by assigning each key to a "point" on a circle (the hash ring), and each server to multiple points. When a server is added or removed, only the keys mapping to that server's portion of the ring need to move — typically `1/N` of the total keys, where N is the number of servers.

For self-hosted teams running distributed caches, database shards, or message queue partitions, choosing the right consistent hashing library directly impacts **rebalancing overhead**, **memory usage**, and **request latency** under scale.

| Algorithm | Memory Usage | Add Node | Remove Node | Uniformity | Best For |
|---|---|---|---|---|---|
| Modulo Hash (naive) | O(1) | Remaps all keys | Remaps all keys | Perfect | Fixed-size clusters only |
| Hash Ring (Ketama) | O(V) where V = virtual nodes | O(log V) | O(log V) | Good with 100+ VNs | General-purpose, small clusters |
| Jump Consistent Hash | O(1) | O(1) - no remap needed | O(N) - all keys on removed node | Near-perfect | Elastic scaling where removal is rare |
| Rendezvous Hashing | O(N) per lookup | O(1) - no remap | O(1) - no remap for others | Highest | Small N, frequent topology changes |

## Hash Ring (Ketama-style): The Classic Approach

The hash ring approach, popularized by the Ketama library and used by Memcached clients and NGINX upstream modules, maps both servers and keys onto a circular hash space.

### How It Works

1. Each server is hashed to multiple points on the ring (virtual nodes, typically 100-200 per server).
2. To locate a key's server, hash the key to a point on the ring and walk clockwise to the first server point.
3. When a server is added, it takes over keys from its clockwise neighbor. When removed, its keys go to the next server clockwise.

### serialx/hashring (585⭐, Go)

The `hashring` library by serialx is one of the most downloaded Go consistent hashing implementations, providing a clean API with virtual node support:

```go
package main

import (
    "fmt"
    "github.com/serialx/hashring"
)

func main() {
    // Create a hash ring with 100 virtual nodes per server
    ring := hashring.New([]string{
        "server1:6379",
        "server2:6379",
        "server3:6379",
    })

    // Find which server handles a key
    server, _ := ring.GetNode("user:12345")
    fmt.Printf("Key 'user:12345' maps to %s\n", server)

    // Add a new server — only ~25% of keys remap
    ring = ring.AddNode("server4:6379")

    // Remove a server — its keys redistribute to neighbors
    ring = ring.RemoveNode("server2:6379")
}
```

**Pros:**
- Supports both add and remove operations with minimal remapping
- Configurable virtual nodes for better distribution
- Widely battle-tested in production caching systems

**Cons:**
- O(log V) lookup time (binary search on sorted nodes)
- Memory overhead from storing virtual nodes per server
- Distribution quality depends on virtual node count

## Jump Consistent Hash: Minimal Memory, Maximum Speed

Google's Jump Consistent Hash, introduced in a 2014 paper by John Lamping and Eric Veach, takes a radically different approach. Instead of a ring, it uses a mathematical jump sequence to find the bucket for each key.

### dgryski/go-jump (389⭐, Go)

```go
package main

import (
    "fmt"
    "github.com/dgryski/go-jump"
)

func main() {
    // Hash a key to one of 10 buckets
    key := jump.Hash(1234567890, 10)
    fmt.Printf("Key hashes to bucket %d\n", key) // deterministic output

    // When scaling from 10 to 11 buckets:
    // Only ~1/11 of keys move — the rest stay where they are
    newKey := jump.Hash(1234567890, 11)
    fmt.Printf("After scale, key maps to bucket %d\n", newKey)
}
```

**The algorithm in pseudocode:**

```
int jump_consistent_hash(uint64 key, int num_buckets):
    b = -1
    j = 0
    while j < num_buckets:
        b = j
        key = key * 2862933555777941757 + 1
        j = (b + 1) * (float(1 << 31) / float((key >> 33) + 1))
    return b
```

**Pros:**
- O(1) memory — no ring structure to maintain
- Near-perfect key distribution (mathematically proven)
- Extremely fast: a few arithmetic operations per lookup
- Adding nodes requires no remapping of existing keys

**Cons:**
- Removing a node requires remapping ALL keys that mapped to it (can be many)
- Buckets must be numbered 0..N-1 consecutively — cannot skip indices
- No support for weighted servers (each bucket has equal capacity)

## Rendezvous Hashing (Highest Random Weight)

Rendezvous Hashing, also called Highest Random Weight (HRW) hashing, was originally designed for Microsoft's caching infrastructure. It computes a score for each key-server pair and selects the server with the highest score.

### lafikl/consistent (685⭐, Go)

```go
package main

import (
    "fmt"
    "github.com/lafikl/consistent"
)

func main() {
    c := consistent.New()

    // Add servers (supports weighted distribution)
    c.Add("server1.example.com")
    c.Add("server2.example.com")
    c.Add("server3.example.com")

    // Get the responsible server for a key
    server, err := c.Get("cache-key-abc")
    if err != nil {
        panic(err)
    }
    fmt.Printf("Key maps to: %s\n", server)

    // Rendezvous: adding/removing servers only affects their own keys
    // No other keys are remapped — ideal for dynamic topologies

    // Get top N servers for replication
    servers, _ := c.GetN("cache-key-abc", 2)
    fmt.Printf("Replication servers: %v\n", servers)
}
```

**Pros:**
- Adding or removing a server only affects keys that mapped to THAT server
- Supports weighted servers natively
- No virtual nodes needed — inherently even distribution
- Easy replication: call GetN() for the top K servers

**Cons:**
- O(N) lookup per key (must score against every server)
- Less efficient for very large N (hundreds of servers)
- Each lookup touches all server entries in memory

## Google Groupcache: A Complete Caching Solution

Groupcache is Google's memcached alternative, used internally for systems like Google's download server. It embeds consistent hashing as part of a complete distributed cache with automatic peer communication.

### golang/groupcache (13,335⭐, Go)

```go
package main

import (
    "fmt"
    "net/http"
    "github.com/golang/groupcache"
)

func main() {
    // Define a peer list (uses consistent hashing internally)
    peers := groupcache.NewHTTPPool("http://10.0.0.1:8080")

    // When running multiple instances, set the full peer list
    peers.Set("http://10.0.0.1:8080", "http://10.0.0.2:8080", "http://10.0.0.3:8080")

    // Create a cache group
    var thumbnails = groupcache.NewGroup("thumbnails", 64<<20, groupcache.GetterFunc(
        func(ctx groupcache.Context, key string, dest groupcache.Sink) error {
            // Fetch from database or generate the value
            result := generateThumbnail(key)
            dest.SetBytes(result)
            return nil
        },
    ))

    // Serve HTTP
    http.HandleFunc("/thumbnail/", func(w http.ResponseWriter, r *http.Request) {
        var data []byte
        key := r.URL.Path[len("/thumbnail/"):]
        thumbnails.Get(nil, key, groupcache.AllocatingByteSliceSink(&data))
        w.Write(data)
    })

    http.ListenAndServe(":8080", nil)
}
```

**Key design decisions:**
- **No explicit set/delete operations** — cache is fill-once, immutable
- **Peer-aware** — automatically forwards cache misses to the correct peer
- **Hot cache protection** — uses singleflight to prevent thundering herd
- Internal consistent hashing for peer selection

Groupcache is ideal for read-heavy workloads where cached values are expensive to compute but don't change often (like resized images, rendered templates, or DNS lookups).

## Choosing the Right Algorithm

| Use Case | Recommended Algorithm | Why |
|---|---|---|
| Distributed cache (small cluster, nodes change often) | Rendezvous Hashing | Minimal remapping on topology change |
| Large-scale cache (100+ nodes, mostly adding) | Jump Consistent Hash | O(1) memory, O(1) on add, near-perfect distribution |
| General-purpose (replace Nginx upstream_hash) | Hash Ring (Ketama) | Well-understood, supports weighted servers, widely compatible |
| Full caching solution (Go ecosystem) | Groupcache | Batteries-included: peer communication, hot cache protection |
| Database sharding (re-shard on migration) | Jump Consistent Hash | Minimal key movement when adding shards |
| CDN edge routing (nodes go down frequently) | Rendezvous Hashing | Only affected node's keys remap |

For related distributed systems reading, see our [Raft Consensus Libraries comparison](../2026-06-19-raft-consensus-libraries-hashicorp-dragonboat-braft-raftrs/) and our [distributed caching guide](../self-hosted-distributed-caching-redis-alternatives-guide-2026/). For database engineering context, check our [database connection pooling guide](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/).

## FAQ

### What happens to cache hit rate when I add a server?

With Hash Ring: approximately (old_node_count / new_node_count) of keys remain in place. Going from 4 to 5 servers means ~80% cache hits survive. With Rendezvous Hashing: 100% of keys that didn't map to the old server stay in place — only the new server's share moves. With Jump Consistent Hash: adding a node causes zero remapping of existing keys (new node takes a portion of each existing bucket).

### Can I use these libraries for database sharding?

Yes, but with caution. Consistent hashing is excellent for **stateless** sharding (like cache shards). For database sharding, you also need to consider rebalancing mechanics — actually moving data between shards. Tools like Vitess (MySQL) and Citus (PostgreSQL) use consistent hashing internally but add migration orchestration on top.

### Which implementation has the lowest memory footprint?

Jump Consistent Hash uses O(1) memory — just the bucket count. Compare this to Hash Ring with 150 virtual nodes × 10 servers = 1,500 entries in memory. For embedded systems or environments with thousands of cache groups, Jump Consistent Hash saves significant RAM.

### Why does Google use Groupcache instead of Redis or Memcached?

Groupcache is designed for immutable, fill-once workloads where cache consistency isn't a concern. It eliminates the complexity of invalidation, expiration, and distributed coordination. Google uses it where cache values are derived from primary storage and don't change independently — like serving processed assets from Google Docs or Google Photos.

### Can I use consistent hashing with weighted servers (heterogeneous capacity)?

Rendezvous Hashing and Hash Ring both support weighted distributions natively. Jump Consistent Hash does not — all buckets are treated as equal. If you need to account for servers with different CPU/RAM/network capacity, choose Rendezvous Hashing or Hash Ring with weighted virtual node distribution.



---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Consistent Hashing: Jump Hash vs Ring Hash vs Rendezvous Hashing Libraries",
  "description": "Compare consistent hashing algorithm implementations for self-hosted distributed systems: Jump Consistent Hash, Hash Ring (Ketama), Rendezvous Hashing, and Google Groupcache with Go code examples and benchmarks.",
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