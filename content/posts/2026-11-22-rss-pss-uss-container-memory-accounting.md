---
title: "RSS vs PSS vs USS: Why Your Container's Memory Number Is Wrong in 2026"
date: "2026-11-22"
description: "Your 16 GB node reports 41 GB of RSS across containers and then OOM-kills at 60% utilisation. Here is what RSS, PSS, USS, cgroup v2 memory.current and working set actually count, and which number to trust for limits, alerts and debugging."
tags: ["linux", "memory", "containers", "kubernetes", "performance", "observability"]
draft: false
---

A 16 GB node reports **41 GB of resident memory** across its containers. It is not swapping, `free -m` says 9 GB is available, and yet the kernel OOM-killer just executed your API server. Every number on the dashboard is technically real and every one of them is answering a different question. The team then spends a week "fixing a memory leak" that does not exist.

The root cause is almost always the same: **RSS double counts shared pages.** Every process that maps the same 40 MB library, the same container image layer, or the same `tmpfs` page adds those 40 MB to its own RSS. Sum RSS across 20 containers built from one base image and you have invented gigabytes of memory that exist exactly once in physical RAM.

This guide is about measurement, not guessing: which metric to read, where the kernel exposes it, what each number includes, and which one to put on an alert. Every command here runs on a stock Linux box.

## TL;DR — Quick Verdict

- **For "how much RAM does this process really cost me?"** use **PSS** from `/proc/PID/smaps_rollup` (or `smem`). It charges shared pages proportionally and never double counts.
- **For "how much memory is this container using right now?"** use cgroup v2 `memory.current` minus `inactive_file`, which is the working-set number Kubernetes already bases eviction on.
- **For "which process should I kill or shrink?"** use **USS** (private memory). It is the only number that drops when that process dies.
- **Never** sum RSS across processes. Never set a container limit from `docker stats` without checking whether page cache is included. Never compare a cgroup number to a `free -m` number and expect them to add up.
- **If a Java or Go service is involved:** RSS above heap is normal (metaspace, stacks, GC structures, arenas). Establish a baseline before calling it a leak.

## The Five Numbers That All Call Themselves "Memory"

| Metric | What it counts | Shared pages | Double counts across processes | Where to read it | Best used for |
|---|---|---|---|---|---|
| **RSS** (resident set size) | Pages currently mapped and resident | Counted **in full** in every process | **Yes** — badly | `/proc/PID/status` (`VmRSS`), `ps`, `top` | Spotting a single process ballooning; never for totals |
| **PSS** (proportional set size) | Private pages + shared pages ÷ number of sharers | Split evenly among sharers | No | `/proc/PID/smaps_rollup` (`Pss:`), `smem` | Per-service cost attribution, capacity planning |
| **USS** (unique set size) | Private pages only | Excluded | No | `/proc/PID/smaps_rollup` (`Private_*`), `smem -u` | "What do I get back if this dies?" |
| **cgroup `memory.current`** | Everything charged to the cgroup: anon + file cache + shmem + kernel | Charged once, to the owning cgroup | No — but includes reclaimable cache | `/sys/fs/cgroup/.../memory.current` | Container-level enforcement and limits |
| **Working set** | `memory.current` − inactive file cache | Charged once | No | Computed; exposed as `container_memory_working_set_bytes` in Kubernetes | Eviction decisions, "real" container footprint |

Read that table again with one fact in mind: **`memory.current` includes page cache.** A container that reads a 2 GB file once can show 2 GB of "memory usage" while holding almost no anonymous memory, because the kernel is caching the file on that cgroup's tab. That cache is reclaimable under pressure, which is why the working-set number exists and why `memory.current` alone is a terrible alerting signal.

## Why Summing RSS Is a Category Error

When a process forks, the child gets copy-on-write mappings of the parent's pages. Both processes report the same physical pages in RSS. When 20 containers run the same 200 MB base image, the shared read-only layers are one copy in the page cache — charged to nobody individually, counted in everybody's RSS. Add memory-mapped libraries, shared memory segments, and `tmpfs` pages and the arithmetic stops meaning anything.

```bash
# The wrong number, computed confidently
for pid in $(pgrep -f my-service); do
  awk '/VmRSS/ {print $2}' /proc/$pid/status
done | awk '{s+=$1} END {printf "sum of RSS: %.1f MB\n", s/1024}'
```

That command produces a number larger than physical RAM on a busy host and is the origin of half the "memory leak" tickets in the world. It is not measuring a leak; it is measuring sharing.

The kernel has known this for years. Since **Linux 4.14**, every process exposes a pre-aggregated summary so you do not need to parse a multi-megabyte `smaps` file:

```bash
cat /proc/$(pgrep -f my-service | head -1)/smaps_rollup
```

```text
Rss:              412340 kB
Pss:              118264 kB
Pss_Anon:          92104 kB
Pss_File:          24880 kB
Pss_Shmem:          1280 kB
Shared_Clean:     301876 kB
Shared_Dirty:       8192 kB
Private_Clean:     84204 kB
Private_Dirty:      8068 kB
Anonymous:         92104 kB
Swap:                  0 kB
```

`Rss: 412 MB` versus `Pss: 115 MB` for the same process. The 300 MB of `Shared_Clean` is mapped library and page-cache data that 5-30 other processes are also mapping. PSS divides it; RSS duplicates it. `Private_Dirty + Private_Clean` is USS — the memory that actually returns to the system when this process exits.

Two practical notes on `smaps_rollup`: it is much cheaper than `smaps` (one aggregated read instead of a page-table walk producing megabytes of text), so it is safe to poll every few seconds; and it is only available if your kernel has `CONFIG_PROC_PAGE_MONITOR`, which every mainstream distribution enables.

## Tool 1: smem — PSS for Humans

`smem` reports USS, PSS and RSS side by side, which makes the difference visible in one screen instead of three tools. Install it from your distribution (`apt install smem`, `dnf install smem`).

```bash
# Top memory consumers by PSS, with a total line in human units
sudo smem -tk -c "pid user command pss rss" | tail -20
```

```text
  PID User     Command                         PSS       RSS
 1841 postgres postgres: writer process     184.2M    512.8M
 1902 app      /usr/local/bin/api-server      96.4M    402.1M
 2210 app      /usr/local/bin/worker          41.7M    188.3M
------------------------------------------------------------
   12          4                                  1.9G      6.4G
```

The total line is the point: **PSS 1.9 GB, RSS 6.4 GB** on the same machine. If you had alerted on summed RSS you would be paging someone about a 6.4 GB footprint that is physically 1.9 GB.

A few flags that matter in practice:

```bash
sudo smem -P '^(postgres|api-server)$' -tk   # filter by process name regex
sudo smem -u                                  # USS only: what is truly private
sudo smem -w                                  # ASCII bar chart of PSS by process
sudo smem -R 2G                               # processes with PSS >= 2 GB
```

`smem` needs root (or `CAP_SYS_PTRACE`) to read other users' `smaps`; without it, numbers silently drop processes and totals look reassuringly small. That is the most common way a `smem` report misleads — run it unprivileged and you measure only your own shell.

`smem` is a single-file Python script with no daemon and no database, which is exactly why it is still the default answer for "who is actually using the RAM". Pair it with a real time series if you need history.

## Tool 2: ps_mem — The Quick Second Opinion

`ps_mem` (1,647 stars, last commit 2022) is a 200-line Python script that computes private and shared memory per program and prints them separately:

```bash
sudo ps_mem -s          # sort by total, split private/shared
```

```text
 Private  +   Shared  =  RAM used       Program
184.0 MiB + 328.0 MiB = 512.0 MiB       postgres (11)
 92.0 MiB +  310.0 MiB = 402.0 MiB       api-server
-------------------------------------------
276.0 MiB + 638.0 MiB = 914.0 MiB       Total
```

The layout is the useful part: it makes the shared component explicit instead of hiding it. The caveat is maintenance — the project has not been pushed to since 2022, so on a kernel with unusual `smaps` formatting (or inside a container with a restricted `/proc`), verify its output against `smaps_rollup` before you trust it. It is a good interactive sanity check, not a monitoring dependency.

If you want live per-process memory history with PSS semantics rather than a one-shot snapshot, run a small exporter that reads `smaps_rollup` and ships the numbers — our [cgroup v2 management guide](../2026-06-01-linux-cgroup-v2-management-systemd-cgtop-cgroup-tools-libcgroup-guide/) covers `systemd-cgtop` and `cgroup-tools`, which give you the cgroup-level view without writing a parser.

## The Container Number: cgroup v2 `memory.current` and Working Set

Inside a cgroup v2 hierarchy, memory accounting is per-cgroup and happens once — shared pages are charged to the first cgroup that touched them, then `charged` again to anyone else mapping them (the `memory.stat` field `file` counts mapped file pages charged to that cgroup). That is why container numbers *do* add up, and why they still do not match what you expect.

```bash
CG=/sys/fs/cgroup/system.slice/api-server.service

cat $CG/memory.current          # bytes charged to this cgroup, cache included
cat $CG/memory.max              # limit (or "max" if unlimited)
cat $CG/memory.high             # soft throttle threshold
grep -E '^(anon|file|shmem|slab|kernel|sock|inactive_file|active_file) ' $CG/memory.stat
cat $CG/memory.events           # low/high/max/oom/oom_kill counters
```

A typical reading inside a container that "uses 1.8 GB" according to `docker stats`:

```text
anon          412 MB
file         1284 MB
shmem          96 MB
slab           38 MB
inactive_file 1090 MB   <- reclaimable cache, almost all of the scary number
```

The working-set estimate used by Kubernetes is exactly this subtraction:

```text
working_set = memory.current - inactive_file
            = (412 + 1284 + 96 + 38) MB - 1090 MB
            ≈ 740 MB
```

740 MB is the number that reflects what will actually be stolen from the page cache before the kernel starts reclaiming anonymous memory or invoking the OOM killer. It is also why a Redis or Elasticsearch pod can sit at 95% of its limit indefinitely and never get killed: the bulk of that 95% is reclaimable file cache, and `memory.max` only bites when reclaim cannot free enough.

Three consequences worth internalising:

1. **`memory.current` is not "memory in use".** It is "memory charged", and file cache is charged. Alert on working set, or on `anon`, never on `memory.current` alone.
2. **`memory.high` is your friend.** Setting `memory.high` below `memory.max` throttles the cgroup and forces reclaim before the hard limit triggers a kill — a graceful degradation path instead of an execution.
3. **`shmem` is not reclaimable without swap.** `tmpfs` and shared memory segments show up as `shmem`, are accounted like file pages, and cannot be evicted to disk if there is no swap. A container writing 1 GB to `/dev/shm` will OOM at its limit even though the number looked like "just cache".

`memory.events` deserves a permanent place in your dashboards, because it distinguishes the expensive failure from the cheap one:

```text
low 0
high 4218      # the cgroup hit memory.high and was throttled 4218 times
max 12         # it hit memory.max 12 times
oom 2          # 2 OOM events
oom_kill 2     # 2 processes killed
```

If `max` is climbing but `oom_kill` is flat, reclaim is working and you have headroom problems, not a leak. If `oom_kill` is climbing while `anon` is flat, you are being killed by page cache you cannot reclaim in time — usually `tmpfs`, dirty pages, or a memory-mapped index.

## Language Runtimes: Why RSS Above Heap Is Normal

Most "leak" investigations end here, with a runtime that is holding memory on purpose.

**Java.** Heap is one part of RSS. Add metaspace (class metadata), code cache (JIT), thread stacks (1 MB reserved per thread by default), GC bookkeeping (card tables, remembered sets), direct `ByteBuffer` allocations, and glibc malloc arenas. A 2 GB heap commonly produces 2.8-3.4 GB of RSS. Measure the split with native memory tracking rather than inferring it:

```bash
java -XX:NativeMemoryTracking=summary -XX:+UnlockDiagnosticVMOptions \
     -XX:+PrintNMTStatistics -jar app.jar
jcmd <pid> VM.native_memory summary
```

**Go.** The runtime returns memory to the OS lazily and keeps a heap reserve. `GOMEMLIMIT` (Go 1.19+) sets a soft limit that makes the GC work harder near it; `runtime/debug.SetMemoryLimit` does the same in code. Without it, a Go service with a 512 MB live heap can hold 1.5 GB of RSS indefinitely because the allocator sees no reason to release pages.

```go
// Soft memory limit: GC aims to stay under this; RSS follows with a lag.
debug.SetMemoryLimit(900 << 20) // 900 MiB
```

**glibc-based services (C, C++, Python, Ruby).** Per-thread arenas fragment and rarely return pages. `MALLOC_ARENA_MAX=2` is the standard mitigation for multi-threaded services whose RSS grows with thread count, and `malloc_trim(0)` (or `MALLOC_TRIM_THRESHOLD_`) forces a release in some workloads.

**Any runtime with transparent huge pages.** THP collapses 4 KiB pages into 2 MiB pages, which inflates RSS granularity by up to 2 MB per mapping and makes `smaps_rollup` totals jump in steps. If RSS moves in 2 MB increments, you are watching khugepaged, not a leak.

When memory pressure is real rather than cosmetic, the next layer down is reclaim behaviour — `kswapd`, watermark tuning and dirty-page ratios — which our [memory reclaim and drop_caches guide](../2026-06-01-linux-memory-reclaim-kswapd-drop-caches-vfs-cache-tuning/) covers in detail, along with why `drop_caches` is not a fix.

## The Five Measurement Traps

1. **Summing RSS across containers.** Double counts every shared library and page-cache page. Use PSS for attribution and cgroup working set for enforcement.
2. **Alerting on `memory.current`.** Includes reclaimable page cache. A pod reading a large file once looks like it doubled its memory. Alert on working set or `anon`.
3. **Comparing cgroup numbers to `free`.** `free -m` reports host-wide available memory; cgroup accounting charges shared pages once to the first toucher. The two live in different accounting universes and will never reconcile.
4. **Running `smem` without root.** Silently omits processes you cannot read, producing a total that is wrong in the comforting direction.
5. **Forgetting `shmem` and hugepages.** `tmpfs` is charged as page cache but cannot be reclaimed without swap, and THP rounds every mapping up to 2 MB. Both make "cache" numbers behave like anonymous memory under pressure.

## FAQ

### What is the difference between RSS, PSS and USS?

RSS is the total pages resident in a process's address space and counts shared pages in full. PSS charges shared pages proportionally to the number of processes mapping them, so it never double counts. USS counts only private pages — the memory that is freed when the process exits. For a process mapping 300 MB of shared libraries, RSS might read 410 MB, PSS 115 MB, and USS 85 MB.

### Which memory number should I use for a Kubernetes memory limit?

Set `memory.max` (the pod limit) from measured working set with headroom, not from `memory.current` at peak. Working set equals `memory.current` minus `inactive_file`, which is what Kubernetes uses for eviction ranking. Size the limit so that working set at peak load plus a safety margin fits, and set `memory.high` slightly below it so you get throttling and reclaim before the OOM killer.

### Why does my container show high memory usage but never get OOM-killed?

Because most of the number is reclaimable page cache. The kernel only invokes the OOM killer when it cannot reclaim enough memory to satisfy an allocation, so a cgroup at 95% of `memory.max` full of clean file pages is comfortable. Check `memory.stat`: if `inactive_file` is large, the "usage" is cache, and `memory.events` will show `max` hits with few or no `oom_kill` events.

### Is /proc/PID/smaps_rollup expensive to read?

No. It returns one aggregated structure per process rather than the full per-VMA table that `/proc/PID/smaps` produces, so it is cheap enough to poll every few seconds for a few hundred processes. Reading full `smaps` for the same set can cost tens of milliseconds each and is a common cause of monitoring-induced CPU load.

### Why is my Java or Go process using far more RSS than its heap?

Both runtimes hold memory outside the heap: Java needs metaspace, JIT code cache, thread stacks, GC structures and direct buffers; Go keeps a heap reserve and returns pages to the OS lazily. Use `jcmd VM.native_memory summary` for Java and `GOMEMLIMIT` plus a heap profile for Go, and compare PSS over time instead of RSS at a single instant. RSS that is flat over hours is not a leak, regardless of how large it is.

### Does tmpfs count against a container's memory limit?

Yes. `tmpfs` and shared memory segments are accounted as `shmem` inside the cgroup and count toward `memory.current` and `memory.max`. Unlike clean file cache, `shmem` cannot be reclaimed without swap, so a container writing a large file to `/dev/shm` can be OOM-killed while its anonymous memory usage is small.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "RSS vs PSS vs USS: Why Your Container's Memory Number Is Wrong in 2026",
  "description": "Your 16 GB node reports 41 GB of RSS across containers and then OOM-kills at 60% utilisation. Here is what RSS, PSS, USS, cgroup v2 memory.current and working set actually count, and which number to trust for limits, alerts and debugging.",
  "datePublished": "2026-11-22",
  "dateModified": "2026-11-22",
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
