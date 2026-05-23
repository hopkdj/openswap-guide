---
title: "Linux Page Cache Inspection: pcstat vs vmtouch vs fincore — Self-Hosted Filesystem Cache Management"
date: "2026-05-23"
tags: ["linux", "memory-management", "page-cache", "performance-tuning", "filesystem"]
draft: false
---

The Linux page cache is one of the most powerful performance optimizations built into the kernel — it automatically caches recently accessed file data in unused RAM, dramatically accelerating repeat reads without any application changes. But this invisible caching layer can also mask memory pressure, cause confusion about "missing" RAM, and lead to suboptimal I/O patterns when hot data gets evicted. Three tools help administrators inspect and manage the page cache: **pcstat** (page cache statistics), **vmtouch** (virtual memory touch), and **fincore** (file in-core). Understanding which files are cached, how much memory they consume, and how to control caching behavior is essential for tuning self-hosted server performance.

## How the Linux Page Cache Works

When a process reads a file, the kernel loads the data into the page cache — a pool of RAM managed by the kernel's memory subsystem. Subsequent reads of the same data are served from RAM instead of disk, often achieving 100x faster response times. The page cache grows dynamically to use all available free RAM and automatically shrinks when applications need memory.

The page cache operates at the page level (typically 4KB pages on x86_64). Each cached page is tracked in the kernel's radix tree, indexed by the file's inode and page offset. The kernel uses sophisticated eviction algorithms (LRU lists, referenced bits) to decide which pages to keep and which to reclaim under memory pressure.

For self-hosted servers running databases, web servers, or file services, the page cache is often the single most important performance factor — more impactful than SSD vs HDD, or even CPU choice. A well-tuned page cache configuration can mean the difference between sub-millisecond and multi-second query response times.

## Why Inspect the Page Cache?

**Memory accounting confusion.** Linux reports page cache as "used" memory in `free` and `top`, leading administrators to believe their servers are memory-constrained when in fact the cache can be instantly reclaimed. Tools like pcstat show exactly how much of that "used" memory is cache vs. application memory, enabling accurate capacity planning.

**Database performance tuning.** Database engines (PostgreSQL, MySQL, Elasticsearch) maintain their own buffer pools that compete with the kernel page cache. Understanding the overlap helps you size database buffers appropriately — if the kernel is already caching the working set, a large database buffer pool wastes RAM. For memory management fundamentals, see our [Linux compressed swap configuration guide](../2026-05-23-self-hosted-linux-compressed-swap-zram-generator-systemd-swap-zramd-guide/) covering zram and memory optimization.

**Hot data identification.** Knowing which files are cached (and which aren't) reveals your application's actual I/O patterns. Files that should be hot but show zero cache indicate missing data paths or misconfigured read patterns. Files that are cached but never accessed represent wasted RAM.

**I/O bottleneck diagnosis.** When disk I/O is saturated, checking the page cache hit rate tells you whether the issue is genuine demand or cache thrashing. A low hit rate with high I/O suggests the working set exceeds available RAM — a clear signal to add memory or optimize data access patterns.

**Pre-warming after reboots.** After server restarts, the page cache is empty and performance degrades until it refills. Tools like vmtouch can pre-load critical files into the cache, restoring performance immediately instead of waiting for natural access patterns to rebuild it.

## pcstat — Page Cache Statistics

[pcstat](https://github.com/tobert/pcstat) is a Go-based tool that reports page cache residency for specified files. With over 1,300 GitHub stars, it provides a clean tabular output showing which pages of a file are currently cached and how much RAM they consume.

### What pcstat Reports

For each file you specify, pcstat shows:
- **Total pages** — the file's size divided by the system page size
- **Cached pages** — how many of those pages are currently in the page cache
- **Cached percentage** — the fraction of the file that is cached
- **Cached size** — the actual RAM consumed by cached pages

### Common pcstat Commands

```bash
# Check cache status for a single file
pcstat /var/lib/postgresql/16/base/12345/67890

# Check multiple files at once
pcstat /var/log/syslog /var/log/auth.log /var/log/kern.log

# Check all files in a directory
pcstat /var/lib/mysql/ibdata1 /var/lib/mysql/ib_logfile0

# JSON output for scripting
pcstat -json /var/lib/elasticsearch/nodes/0/indices/*/0/index/*

# Terse output (just filename and percentage)
pcstat -terse /path/to/file

# Human-readable sizes
pcstat -human /var/lib/postgresql/16/base/*
```

### Example Output

```
+-------------------------------------+----------------+------------+-----------+---------+
| Name                                | Size           | Pages      | Cached    | Percent |
+-------------------------------------+----------------+------------+-----------+---------+
| /var/lib/postgresql/16/base/16384/16385 | 1073741824   | 262144     | 196608    | 075.000 |
| /var/lib/elasticsearch/nodes/0/indices/abc/0/index/segments_4 | 524288000 | 128000 | 128000 | 100.000 |
| /var/log/syslog                     | 104857600      | 25600      | 25600     | 100.000 |
+-------------------------------------+----------------+------------+-----------+---------+
```

### Installation

```bash
# Install from GitHub releases
go install github.com/tobert/pcstat@latest

# Or build from source
git clone https://github.com/tobert/pcstat.git
cd pcstat
go build
sudo mv pcstat /usr/local/bin/

# Debian/Ubuntu (if packaged)
sudo apt install pcstat
```

### Docker Deployment

pcstat has an official Dockerfile in its repository:

```yaml
version: "3.8"
services:
  pcstat-check:
    image: golang:1.22-alpine
    command: ["sh", "-c", "go install github.com/tobert/pcstat@latest && /root/go/bin/pcstat /var/log/syslog"]
    volumes:
      - /var/log:/var/log:ro
    read_only: true
```

For production use, build a dedicated image:

```dockerfile
FROM golang:1.22-alpine AS builder
RUN go install github.com/tobert/pcstat@latest

FROM alpine:latest
COPY --from=builder /root/go/bin/pcstat /usr/local/bin/pcstat
ENTRYPOINT ["/usr/local/bin/pcstat"]
```

## vmtouch — Virtual Memory Touch

[vmtouch](https://github.com/hoytech/vmtouch) is a portable filesystem cache diagnostics and control tool with nearly 2,000 GitHub stars. Unlike pcstat (which only reports), vmtouch can both inspect **and modify** the page cache — loading files into cache, evicting them, or locking them in memory.

### What vmtouch Can Do

vmtouch operates in three modes:

1. **Query mode** (default) — reports how much of a file or directory tree is currently cached
2. **Touch mode** (`-t`) — reads every page of a file into the page cache (pre-warming)
3. **Evict mode** (`-e`) — removes a file's pages from the page cache (freeing RAM)
4. **Lock mode** (`-l`) — locks pages in RAM using `mlock()`, preventing eviction

### Common vmtouch Commands

```bash
# Check cache status for a file
vmtouch /var/lib/postgresql/16/base/16384/16385

# Check an entire directory tree recursively
vmtouch -r /var/lib/postgresql/

# Pre-load a file into cache (touch)
vmtouch -t /var/lib/elasticsearch/nodes/0/indices/*/0/index/*

# Evict a file from cache (free RAM)
vmtouch -e /var/log/old-app.log

# Lock a file in memory (prevent eviction)
vmtouch -tl /var/lib/mysql/ibdata1

# Verbose output showing each file
vmtouch -v /path/to/files

# JSON-like output for parsing
vmtouch -b /path/to/files
```

### Example Output

```bash
$ vmtouch /var/lib/postgresql/16/base/16384/16385
           Files: 1
     Directories: 0
  Resident Pages: 196608/262144  768M/1G  75%
  Elapsed: 0.023 seconds

$ vmtouch -t /var/lib/postgresql/16/base/16384/16385
           Files: 1
     Directories: 0
  Touched Pages: 262144  1G
  Elapsed: 2.1 seconds
```

### Docker Deployment

```yaml
version: "3.8"
services:
  vmtouch-warm:
    image: alpine:latest
    command: ["sh", "-c", "apk add vmtouch && vmtouch -t /data/hot-files/*"]
    volumes:
      - /var/lib/postgresql:/data:ro
    privileged: true
```

Note: vmtouch's touch and lock modes require the ability to read files and (for locking) sufficient `memlock` limits. In containers, you may need to increase `--ulimit memlock=-1:-1`.

### When to Use vmtouch's Pre-Warming

Pre-warming is most valuable in these scenarios:

- **After database restores** — Load the most frequently accessed tables into cache before accepting traffic
- **After server reboots** — Pre-load critical application files and libraries to restore performance immediately
- **Before batch processing** — Ensure input data files are cached before starting a compute-intensive batch job
- **For benchmarking** — Warm the cache before running performance tests to eliminate cold-cache variance

## fincore — File In-Core Statistics

**fincore** (file in-core) is a simpler tool that reports which pages of a file are currently resident in the page cache. Originally part of the linux-ftools project, it is now available through various package repositories and standalone implementations.

### What fincore Reports

fincore provides a straightforward summary:
- Total file size
- Number of cached pages
- Total cached size
- Cache percentage

### Common fincore Commands

```bash
# Check cache status for a file
fincore /var/lib/mysql/ibdata1

# Check multiple files
fincore /var/lib/mysql/ibdata1 /var/lib/mysql/ib_logfile0 /var/lib/mysql/mysql.ibd

# Verbose output with page numbers
fincore --pages /var/log/syslog
```

### Example Output

```bash
$ fincore /var/lib/postgresql/16/base/16384/16385
RES PAGES  FILE
786432000  192000  /var/lib/postgresql/16/base/16384/16385
```

### Installation

```bash
# Debian/Ubuntu (linux-ftools package)
sudo apt install linux-ftools

# Build fincore-go (modern alternative)
git clone https://github.com/pyama86/fincore-go.git
cd fincore-go
go build
sudo mv fincore-go /usr/local/bin/fincore

# Python port
pip install fincore
```

### fincore vs pcstat vs vmtouch

fincore is the simplest of the three tools — it reports cache status without the formatting options of pcstat or the write capabilities of vmtouch. It's best suited for quick, one-line checks in scripts where you need just the cached byte count.

## Comparison: pcstat vs vmtouch vs fincore

| Feature | pcstat | vmtouch | fincore |
|---------|--------|---------|---------|
| **Cache inspection** | Yes | Yes | Yes |
| **Cache pre-warming** | No | Yes (`-t`) | No |
| **Cache eviction** | No | Yes (`-e`) | No |
| **Memory locking** | No | Yes (`-l`) | No |
| **Recursive scan** | Per-file only | Yes (`-r`) | Per-file only |
| **Output formats** | Table, JSON, terse | Verbose, brief | Simple table |
| **Language** | Go | C | C/Python |
| **GitHub stars** | 1,304 | 1,938 | Minimal |
| **Docker support** | Official Dockerfile | Package available | Build from source |
| **Batch processing** | Multiple files | Directory trees | Multiple files |

## When to Use Each Tool

**Use pcstat** when you need detailed, formatted reports on page cache residency for specific files. Its JSON output mode makes it ideal for integration with monitoring dashboards and automated alerting systems. The per-file granularity is perfect for database and application-specific cache analysis.

**Use vmtouch** when you need to actively manage the page cache — pre-warming files after reboots, evicting stale data to free RAM, or locking critical files in memory. It's the only tool that can both inspect and modify cache state. The recursive directory scanning is unique among these three tools.

**Use fincore** when you need a quick, lightweight cache check with minimal output. It's the simplest tool to integrate into shell scripts and cron jobs where you just need the cached byte count without additional formatting or processing.

## Why Self-Host Your Cache Management?

Managing page cache behavior on your own Linux servers gives you fine-grained control over memory utilization without depending on external monitoring or caching services:

**Optimize database performance.** By understanding what the kernel is caching, you can right-size database buffer pools — avoiding the common mistake of double-caching data in both the kernel and the database engine. For guidance on memory pressure management, see our [Linux HugePages management comparison](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) which covers complementary memory optimization techniques.

**Eliminate cold-start latency.** Pre-warming the page cache with vmtouch after server restarts or database restores eliminates the performance degradation that typically lasts minutes to hours while caches refill naturally. This is critical for services with SLA requirements.

**Accurate capacity planning.** Understanding actual page cache usage patterns — not just "used" vs "available" memory — enables precise RAM provisioning. You can identify when additional memory would actually improve performance vs. when the working set already fits in cache. If you're managing server restarts and service lifecycles, our [service restart detection guide](../2026-05-29-self-hosted-linux-service-restart-detection-needrestart-checkrestart-debsums-guide/) covers tools that complement cache management.

**Cost optimization.** In cloud environments, RAM is expensive. Knowing your actual working set size prevents over-provisioning — many teams run on instances with 2x the RAM they need because they can't distinguish cache from application memory.

## FAQ

### How do I tell how much RAM is used by the page cache vs applications?

Run `free -h` and look at the "buff/cache" column — this shows page cache plus buffer memory. For application memory, look at "available" (which is total minus used by applications). For per-process breakdown, use `smem` or examine `/proc/meminfo` for `Cached`, `Buffers`, `SReclaimable`, and `Active(file)` values.

### Can I force Linux to drop the page cache?

Yes, but only for testing purposes. Run `echo 1 > /proc/sys/vm/drop_caches` (requires root). This clears the page cache, dentries, and inodes. **Never do this on a production server** — it will cause a massive I/O spike as all subsequent reads go to disk. Use `vmtouch -e` for targeted eviction of specific files instead.

### Does the page cache affect write performance?

Yes. Linux uses a write-back caching strategy — writes go to the page cache first and are flushed to disk asynchronously by the kernel's flusher threads (controlled by `vm.dirty_ratio` and `vm.dirty_background_ratio` in `/etc/sysctl.conf`). This means write operations appear fast to the application, but data may not be on disk yet. Use `fsync()` or `O_SYNC` for critical writes.

### Why does vmtouch show different results than pcstat for the same file?

Both tools read the same kernel data structure (`mincore()` system call), so results should be identical. Differences usually indicate the cache state changed between the two invocations — the page cache is dynamic and pages can be evicted or loaded between calls. Run both tools simultaneously to verify.

### How do I pre-warm the page cache for a PostgreSQL database after a restart?

Use vmtouch to touch the most frequently accessed table files: `vmtouch -t /var/lib/postgresql/16/base/*/`. For targeted pre-warming, identify the largest and most frequently accessed relations with `SELECT pg_relation_size(oid), relname FROM pg_class ORDER BY 1 DESC LIMIT 20;` then touch those specific files.

### Is page cache the same as buffer cache?

Historically, Linux had separate page cache (for file data) and buffer cache (for block device metadata). Modern Linux merged these — the page cache handles both, with buffer heads for block device metadata allocated within the page cache. The `free` command's "buff/cache" column combines both for display purposes.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux Page Cache Inspection: pcstat vs vmtouch vs fincore — Self-Hosted Filesystem Cache Management",
  "description": "Compare three tools for inspecting and managing the Linux page cache — pcstat for statistics, vmtouch for pre-warming and eviction, and fincore for quick checks.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
