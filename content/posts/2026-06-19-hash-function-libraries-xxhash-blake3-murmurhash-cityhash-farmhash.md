---
title: "High-Performance Hash Function Libraries: xxHash vs BLAKE3 vs MurmurHash3 vs CityHash vs FarmHash"
date: "2026-06-19"
tags: ["hash-functions", "performance", "algorithms", "developer-tools", "cryptography", "data-structures", "c", "cpp", "rust"]
draft: false
description: "Compare xxHash, BLAKE3, MurmurHash3, CityHash, and FarmHash — the most popular high-performance hash function libraries. Performance benchmarks, use cases, and code examples for hashing at scale."
---

## Why Hash Functions Matter for Performance-Critical Applications

Hash functions are the invisible workhorses of modern software. Every time you query a hash table, check a checksum, or deduplicate a file, a hash function runs somewhere in the stack. Choosing the right hash function can mean the difference between a database that handles millions of QPS and one that chokes at 50K.

Non-cryptographic hash functions prioritize raw speed over collision resistance guarantees. They power hash tables, bloom filters, checksums, content-addressed storage, and network packet verification. In high-throughput systems, even a 10% improvement in hashing speed translates to measurable latency reductions across the entire request path.

For related performance engineering topics, see our [server benchmarking guide](../phoronix-vs-unixbench-vs-fio-self-hosted-server-benchmark-guide-2026/) and [storage benchmarking comparison](../2026-06-16-self-hosted-storage-benchmarking-fio-sysbench-bonniepp/). If you work with data compression, our [compression tools comparison](../2026-06-01-linux-compression-tools-zstd-brotli-lz4-gzip/) covers complementary optimization techniques.

## Comparison Table: Hash Function Libraries at a Glance

| Library | Author | Stars | Language | Hash Width | Throughput (GB/s) | Best For |
|---------|--------|-------|----------|------------|-------------------|----------|
| xxHash | Yann Collet | 11,091 | C | 32/64/128-bit | 13.8 (xxh64) | General-purpose hashing, hash tables |
| BLAKE3 | Jack O'Connor | 6,290 | Rust/C/ASM | 256-bit | 2.5 (single-core) | Cryptographic integrity, HMAC, KDF |
| MurmurHash3 | Austin Appleby | 2,877 | C++ | 32/128-bit | 6.7 (x64_128) | Hash tables, bloom filters |
| HighwayHash | Google | 1,603 | C++ | 64/128/256-bit | 11.0 | Hash flooding defense |
| CityHash | Google | 1,228 | C++ | 64/128-bit | 8.5 (CityHash64) | String hashing, hash tables |
| FarmHash | Google | 649 | C++ | 32/64/128-bit | 9.8 (FarmHash64) | Successor to CityHash |

## xxHash: The Speed Champion

xxHash, created by Yann Collet (also the author of LZ4 and Zstandard), is the gold standard for non-cryptographic hashing speed. The xxh64 variant achieves 13.8 GB/s on modern hardware — faster than the memory bandwidth of many SSDs. It supports 32-bit (xxh32), 64-bit (xxh64), and 128-bit (xxh128) outputs.

xxHash is used extensively in databases (Redis, ClickHouse, DuckDB), filesystems (ZFS, Btrfs), and network protocols. Its primary strength is that the algorithm is branchless and SIMD-friendly, allowing modern CPUs to process 32 bytes per cycle through vector instructions.

```c
#include "xxhash.h"
#include <stdio.h>

int main() {
    const char* data = "Hello, hash world!";
    XXH64_hash_t hash = XXH64(data, strlen(data), 0);
    printf("xxHash64: 0x%016llx\n", (unsigned long long)hash);
    return 0;
}
```

Compile with: `gcc -O3 example.c xxhash.c -o example`

**Key features:** Streaming API for large data, seed support for hash randomization, AVX2/AVX-512 acceleration, and a stable format guarantee — hashes are identical across versions and platforms.

## BLAKE3: Cryptographic Strength at Practical Speeds

BLAKE3 is the evolution of the BLAKE2 family and was a finalist in the NIST SHA-3 competition. Unlike traditional cryptographic hashes that process data sequentially, BLAKE3 uses a Merkle tree structure that enables massive parallelism across SIMD lanes and multiple cores.

On a single core, BLAKE3 delivers ~2.5 GB/s. With SIMD and multi-threading, it scales linearly to saturate even NVMe storage bandwidth. This makes it the only hash function that's simultaneously suitable for both cryptographic integrity verification (file checksums, digital signatures) and high-throughput data processing.

```rust
// Cargo.toml dependency: blake3 = "1"
use blake3::Hasher;
use std::io::Read;

fn main() -> std::io::Result<()> {
    let mut file = std::fs::File::open("large_dataset.bin")?;
    let mut hasher = Hasher::new();
    std::io::copy(&mut file, &mut hasher)?;
    let hash = hasher.finalize();
    println!("BLAKE3: {}", hash.to_hex());
    Ok(())
}
```

**Key features:** Unlimited output length via XOF (extendable-output function), keyed hashing mode for HMAC replacement, key derivation (KDF), and verified streaming — you can verify a hash before the entire input is available.

BLAKE3 is ideal when you need both speed and security. Use cases include CI/CD artifact verification, content-addressed storage (IPFS, Perkeep), Git object hashing (being explored), and file deduplication systems.

## MurmurHash3: The Tried-and-True Workhorse

MurmurHash3 by Austin Appleby has been the default hash function for countless systems since 2011. It powers hash tables in Redis (when not using xxHash), Apache Cassandra's bloom filters, Nginx, and libstdc++'s `std::unordered_map` on some implementations.

Its key advantage is excellent distribution quality — the avalanche property ensures that a single-bit change in the input flips roughly half the output bits. This makes it ideal for hash table probing where clustering must be avoided.

```cpp
#include "MurmurHash3.h"
#include <iostream>

int main() {
    const char* key = "hash-table-key-42";
    uint64_t out[2];
    MurmurHash3_x64_128(key, strlen(key), 0, out);
    std::cout << "MurmurHash3 x64_128: "
              << std::hex << out[0] << out[1] << std::endl;
    return 0;
}
```

**Key features:** Excellent distribution (no clustering), small code footprint (~500 lines), no external dependencies, and battle-tested across billions of production deployments. However, MurmurHash3 is not seed-independent — different seeds produce uncorrelated hash families, which is useful for security-conscious hash table designs.

## CityHash and FarmHash: Google's Evolution

CityHash was Google's response to MurmurHash — optimized specifically for short strings (URLs, filenames, identifiers) that dominate real-world hash table workloads. CityHash64 excels on inputs under 64 bytes, making it ideal for string-keyed hash tables in compilers, URL routers, and metadata stores.

FarmHash is CityHash's successor with improvements for newer CPU architectures (Haswell and later). It includes CRC32C hardware instruction acceleration, better performance on long inputs, and a unified API that selects the optimal variant based on input length and available CPU features.

```cpp
#include <city.h>
#include <iostream>

int main() {
    std::string url = "https://api.example.com/v2/users/12345/profile";
    uint64 h = CityHash64(url.data(), url.size());
    std::cout << "CityHash64: " << h << std::endl;
    
    // FarmHash can select optimal variant automatically
    uint64 f = util::Hash64(url.data(), url.size());
    std::cout << "FarmHash64: " << f << std::endl;
    return 0;
}
```

**Note:** CityHash has been deprecated in favor of FarmHash for new projects. If you're maintaining legacy code that uses CityHash, migration to FarmHash is straightforward — FarmHash provides CityHash-compatible functions for backward compatibility.

## Practical Selection Guide

| Requirement | Recommended Library |
|-------------|-------------------|
| Maximum raw speed, non-cryptographic | xxHash (xxh64) |
| Cryptographic integrity + speed | BLAKE3 |
| Best hash table distribution | MurmurHash3 |
| Defense against hash flooding | HighwayHash / SipHash |
| Short string optimization (< 64 bytes) | FarmHash |
| 128-bit output, non-crypto | xxHash (xxh128) |
| Multi-threaded hashing of large files | BLAKE3 |
| Embedded/constrained environments | MurmurHash3 (no deps) |

## Avoiding Common Pitfalls

**Hash flooding attacks:** If you accept user-controlled keys in a hash table, non-cryptographic hashes like xxHash and MurmurHash3 are vulnerable to collision attacks. An attacker can craft keys that all hash to the same bucket, degrading O(1) lookups to O(n). Use SipHash or HighwayHash (which provide DoS resistance) for hash tables exposed to untrusted input.

**32-bit output collisions:** xxh32 and MurmurHash3_x86_32 produce 32-bit outputs. With the birthday bound, you'll get a collision after ~77,000 hashes. Always use 64-bit or larger outputs for datasets exceeding thousands of items.

**Stability guarantees:** If you store hashes persistently (file checksums, database indexes), verify your chosen library's stability policy. xxHash guarantees format stability. BLAKE3 guarantees it. MurmurHash3 is stable. CityHash and FarmHash do NOT guarantee cross-version compatibility — Google may change the algorithm between releases.

## Performance Characteristics and Benchmarking Methodology

Understanding hash function performance requires more than just quoting throughput numbers. The actual speed depends heavily on input size, CPU microarchitecture, and whether the data is already in L1 cache or needs to be fetched from main memory.

**Input size effects:** For tiny inputs (under 16 bytes), function call overhead dominates. Inline variants of xxHash and FarmHash shine here because the compiler can eliminate the call entirely. MurmurHash3's function call overhead makes it 30-40% slower on these micro-inputs. For medium inputs (64-256 bytes), SIMD acceleration kicks in — xxHash's AVX2 path processes 32 bytes per cycle, BLAKE3's tree structure enables 4-way parallelism, and HighwayHash saturates the SIMD pipeline.

**Cache effects:** Hashes of small, frequently accessed data (like hash table keys) typically hit L1 cache, making raw computation speed the primary metric. For large streaming workloads (file hashing, network packet verification), memory bandwidth becomes the bottleneck — the hash function that keeps the CPU's execution units fed while waiting on DRAM wins. xxHash's streaming API is optimized for this scenario, using prefetch hints to overlap memory access with computation.

**Microarchitecture sensitivity:** Hash functions with branchless designs (xxHash, HighwayHash) perform consistently across Intel, AMD, and ARM. Functions with data-dependent branches (older CityHash versions) can show 2x performance variation between Skylake and Zen 4 due to different branch predictor strategies. If you deploy across heterogeneous hardware, benchmark on your slowest target machine.

**Benchmarking correctly:** Single-shot benchmarks are misleading because CPU frequency scaling and cache warming effects dominate short runs. Measure steady-state throughput after a warm-up phase of at least 100,000 iterations. Use `perf stat` to count instructions and cache misses alongside wall-clock time. The hash that finishes fastest might not be the most efficient — BLAKE3 uses more instructions per byte than xxHash but achieves similar throughput through better instruction-level parallelism.


## FAQ

### Which hash function should I use for a hash table in 2026?

For most use cases, xxHash64 provides the best speed/distribution trade-off. If you need cryptographic collision resistance, use BLAKE3 with a truncated 128-bit output. For hash tables exposed to adversarial input, use SipHash or HighwayHash.

### Is BLAKE3 a drop-in replacement for SHA-256?

BLAKE3 is faster and provides a 256-bit output, but SHA-256 remains the standard for interoperability (TLS certificates, blockchain, Git signing). Use BLAKE3 for internal systems where you control both ends. Use SHA-256 when you need compatibility with external systems.

### Can I use xxHash for file integrity checks?

xxHash is excellent for detecting accidental corruption and is widely used for this purpose (rsync, ZFS dedup). However, it is NOT suitable for detecting malicious tampering — an attacker can generate collisions. Use BLAKE3 or SHA-256 for security-sensitive integrity verification.

### Why does Google have three different hash libraries?

CityHash (2011) was the first attempt, optimized for short strings. FarmHash (2014) improved on CityHash with better long-input performance and CRC32C acceleration. HighwayHash (2016) added SipHash-level DoS resistance with SIMD speed. Each addresses a different design point, and FarmHash is the recommended successor to CityHash for most use cases.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "High-Performance Hash Function Libraries: xxHash vs BLAKE3 vs MurmurHash3 vs CityHash vs FarmHash",
  "description": "Compare xxHash, BLAKE3, MurmurHash3, CityHash, and FarmHash — the most popular high-performance hash function libraries. Performance benchmarks, use cases, and code examples for hashing at scale.",
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
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
