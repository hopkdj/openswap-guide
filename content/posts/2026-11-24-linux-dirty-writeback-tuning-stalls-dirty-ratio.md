---
title: "Why Your Database Stalls Every 30 Seconds: Linux Dirty Page Writeback Tuning in 2026"
date: "2026-11-24"
description: "Every 30 seconds your p99 latency triples and iostat shows 100% utilisation, yet CPU and IOPS look normal. The cause is Linux dirty page writeback. Here is how vm.dirty_ratio, dirty_background_ratio and the flusher threads actually work, with real tuning values, diagnostics and fio tests."
tags: ["linux", "storage", "performance", "kernel", "database", "tuning"]
draft: false
---

A support ticket that repeats on a schedule is the easiest kind to diagnose: p99 write latency jumps from 4 ms to 180 ms every 30 seconds, `iostat` reports the data volume pinned at 100% utilisation for two seconds at a time, and nothing in the application changed. CPU sits at 12%. The database is not slow. **The kernel is flushing a mountain of dirty pages in one burst, and your writes are queued behind it.**

Linux does not write your data to disk when you `write()`. It copies pages into the page cache, marks them dirty, and returns. A background flusher thread eventually pushes those pages to the device. When the flusher falls behind and the dirty page count crosses a threshold, the next `write()` call blocks inside `balance_dirty_pages()` — the application thread is throttled by someone else's backlog. That is the stall, and it is controlled by exactly four sysctls.

## TL;DR — Quick Verdict

- **Postgres, MySQL, or Redis on a fast NVMe volume:** lower the writeback window. `vm.dirty_background_ratio=3`, `vm.dirty_ratio=8`, `vm.dirty_expire_centisecs=1000` keeps bursts small and removes the multi-second flush cliffs.
- **Bulk sequential writes (backups, media ingest, log archiving):** raise the limits instead. Big dirty windows absorb throughput spikes and let the device write at its full sequential rate.
- **Hosts with more than 64 GB RAM:** stop using ratios entirely. `dirty_ratio=20` on a 256 GB machine permits **51 GB of dirty data**, which no device flushes before your latency SLO dies. Set `vm.dirty_bytes` and `vm.dirty_background_bytes` in absolute terms.
- **Containers and Kubernetes:** you cannot tune this per pod. `vm.dirty_*` is a host-wide, per-backing-device knob. Either tune the node or move the workload to `O_DIRECT`/`fsync`-heavy paths.
- **Diagnosis in one line:** `grep -E "nr_dirty|nr_writeback" /proc/vmstat` during a stall tells you immediately whether you are dirty-throttled or device-throttled.

## The Four Knobs, Compared

All defaults below are what a stock 2026 Linux host ships with — verified on a live 28 GB, 16-vCPU machine (`sysctl vm.dirty_ratio vm.dirty_background_ratio vm.dirty_expire_centisecs vm.dirty_writeback_centisecs`) while writing this article:

| Sysctl | Stock value | What it controls | Raise it when | Lower it when |
|---|---|---|---|---|
| `vm.dirty_ratio` | 20 (%) | Dirty page ceiling at which the **writing process throttles itself** | Sequential bulk writes, slow spinning disks | Databases, latency-sensitive services |
| `vm.dirty_background_ratio` | 10 (%) | Point where **background flusher threads** start writing | You want fewer, larger flush runs | You want steady, small flushes |
| `vm.dirty_expire_centisecs` | 3000 (30 s) | How old a dirty page may get before it is eligible for writeout | Slow devices, write coalescing | **Any workload with 30-second latency spikes** |
| `vm.dirty_writeback_centisecs` | 500 (5 s) | How often the flusher thread wakes up | You want less background CPU noise | You want finer-grained flush control |
| `vm.dirty_bytes` | 0 (disabled) | Absolute dirty ceiling; **setting it zeroes `dirty_ratio`** | RAM > 64 GB, or a dedicated data volume | — |
| `vm.dirty_background_bytes` | 0 (disabled) | Absolute background threshold; zeroes `dirty_background_ratio` | Same as above | — |

On the reference host the derived thresholds were:

```
nr_dirty                   3041
nr_writeback                  0
nr_dirty_threshold       480157   # ≈ 1.8 GB of dirty pages before writers throttle
nr_dirty_background_threshold 239785   # ≈ 937 MB before the flusher wakes
```

That is a normal-looking configuration, and it is also exactly why the 30-second stall appears: `dirty_expire_centisecs=3000` means a page can sit dirty for 30 seconds, and when the flusher finally runs it has a gigabyte of work queued.

## Decision Matrix: What to Set for Your Workload

| Workload | `dirty_background_ratio` | `dirty_ratio` | `dirty_expire_centisecs` | Reasoning |
|---|---|---|---|---|
| PostgreSQL / MySQL on NVMe | 3 | 8 | 1000 | Keeps flush bursts under ~1 s of device time |
| Redis with AOF `everysec` | 5 | 10 | 1000 | Avoid stacking AOF fsync behind a flush burst |
| Elasticsearch / OpenSearch | 5 | 10 | 1500 | Segment merges already generate heavy writeback |
| Backup target / object storage node | 10 (default) | 30 | 3000 | Large dirty window absorbs bursty ingest |
| Media transcoding scratch volume | 15 | 40 | 3000 | Sequential writes benefit from coalescing |
| Host with 256 GB RAM, any workload | use bytes | use bytes | 1000 | Ratios become meaningless at this scale |
| Kubernetes node with mixed pods | 5 | 10 | 1000 | One host-wide setting must protect the noisiest tenant |

## How Writeback Actually Works

Dirty pages are tracked **per backing device** (`bdi`), not per process and not per filesystem. Each device gets flusher threads (`flush-MAJOR:MINOR` in `ps`), and the global `vm.dirty_*` thresholds are compared against the total dirty page count. That has three consequences worth internalising:

1. **One noisy writer poisons every other workload on the same device.** A nightly `rsync` that dirties 20 GB will throttle your database's writes, because the threshold is shared.
2. **Ratios scale with RAM, not with device speed.** A 256 GB host with `dirty_ratio=20` allows 51 GB of dirty pages; a 2 GB/s NVMe needs 25 seconds to flush that. Bytes are the only sane unit above ~64 GB of RAM.
3. **Throttling happens in the writer's context.** The stalled query is not waiting on the disk — it is sleeping in `balance_dirty_pages()` waiting for the flusher to catch up. `iostat` will show high utilisation *and* low queue depth in that moment, which confuses people who expect a saturated device.

You can see the budget the kernel is enforcing at any time:

```bash
grep -E "^(nr_dirty|nr_writeback|nr_dirty_threshold|nr_dirty_background_threshold)" /proc/vmstat
grep -E "^(Dirty|Writeback):" /proc/meminfo
# per-device writeback pressure limits (percent of dirty budget a device may claim)
for d in /sys/class/bdi/*/; do echo "$d $(cat $d/max_ratio 2>/dev/null)"; done | head
```

`max_ratio` is the per-device escape hatch. On a host where one slow USB-backed array shares the dirty budget with an NVMe database volume, capping the array at `max_ratio=5` stops it from consuming the whole allowance.

## Applying a Tuning Profile

Do not use `sysctl -w` in production and hope. Persist the profile in `/etc/sysctl.d/`, which is applied before your database starts:

```ini
# /etc/sysctl.d/60-writeback-latency.conf
# Database host: keep flush bursts small, cap staleness at 10 s
vm.dirty_background_ratio = 3
vm.dirty_ratio = 8
vm.dirty_expire_centisecs = 1000
vm.dirty_writeback_centisecs = 500

# Large-memory variant: uncomment to switch from ratios to absolute bytes.
# Setting either *_bytes key disables its ratio counterpart automatically.
# vm.dirty_background_bytes = 268435456   # 256 MB
# vm.dirty_bytes = 1073741824             # 1 GB
```

```bash
sudo sysctl --system          # validate syntax and apply
sysctl vm.dirty_ratio vm.dirty_background_ratio vm.dirty_expire_centisecs
```

For a dedicated data volume you can bypass the global budget entirely by using `O_DIRECT` in the application (PostgreSQL's `wal_sync_method`, MySQL's `innodb_flush_method=O_DIRECT`, or `dd oflag=direct`). Direct I/O skips the page cache, so `vm.dirty_*` stops applying to that path — at the cost of losing read caching and forcing per-write device latency.

## Proving the Fix With fio

Do not tune blind. Reproduce the stall, change one knob, reproduce again. A dirty-page pressure test that also logs the kernel's own counters:

```bash
# Terminal 1: watch dirty growth while the job runs
watch -n0.5 'grep -E "^(nr_dirty|nr_writeback) " /proc/vmstat'

# Terminal 2: 4 parallel 1 MB writers, 4 GB each, no fsync (so pages stay dirty)
fio --name=dirtytest --directory=/data/fiotest --rw=write --bs=1M \
    --size=4G --numjobs=4 --ioengine=libaio --iodepth=16 \
    --fsync=0 --group_reporting
```

With `dirty_ratio=20` you will see `nr_dirty` climb towards the threshold and then the writers' throughput collapse while `nr_writeback` spikes — that sawtooth is the stall your users feel. With `dirty_ratio=8` and `dirty_expire_centisecs=1000`, the same job produces a flatter `nr_dirty` line and a much smaller throughput dip, because the kernel starts flushing far earlier and never has to throttle hard.

On the read side of the same problem, the [page cache inspection tooling comparison](../2026-05-23-linux-page-cache-inspection-pcstat-vmtouch-fincore-guide/) covers `pcstat`, `vmtouch` and `fincore` for proving what is actually cached. If you are still deciding which sysctl surface to manage with, the [kernel tuning workflow comparison](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) covers `sysctl`, `tuned` and `systool`. And if your symptom is data loss rather than latency, read the [fsync durability analysis](../2026-11-22-fsync-durability-lies-linux-storage-write-cache/) — writeback tuning changes when pages are written, never whether they are durable.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Why Your Database Stalls Every 30 Seconds: Linux Dirty Page Writeback Tuning in 2026",
  "description": "Diagnose and fix periodic write latency spikes caused by Linux dirty page writeback. Real vm.dirty_ratio, dirty_background_ratio and dirty_expire_centisecs values, per-device bdi limits, /proc/vmstat diagnostics and fio tests.",
  "datePublished": "2026-11-24",
  "dateModified": "2026-11-24",
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

### Why does write latency spike every 30 seconds on Linux?

Because `vm.dirty_expire_centisecs` defaults to 3000, i.e. 30 seconds. Pages are allowed to stay dirty for that long, and when the flusher thread runs it writes out everything that accumulated in one burst. Setting `vm.dirty_expire_centisecs=1000` and lowering `vm.dirty_background_ratio` to about 3 spreads that work into smaller, more frequent flushes.

### Should I use vm.dirty_ratio or vm.dirty_bytes?

Use `vm.dirty_ratio` on hosts with 16 GB of RAM or less, and `vm.dirty_bytes` on anything larger. Ratios scale with memory, so a 256 GB host with a 20% ratio permits 51 GB of dirty pages — far more than any device can flush inside a latency SLO. The two settings are mutually exclusive: writing a value to `dirty_bytes` resets `dirty_ratio` to 0 and vice versa.

### Does lowering dirty_ratio reduce disk throughput?

It can, for purely sequential bulk writes where large dirty windows allow the device to coalesce requests. For random or synchronous workloads — databases, queues, container runtimes — the throughput loss is negligible and the latency improvement is large. Tune per volume, not per host, when the workloads differ.

### Can I set dirty page limits per container or per pod?

No. The `vm.dirty_*` sysctls are host-wide and mostly not namespaced, so a container cannot have its own writeback budget. In Kubernetes, tune the node and keep latency-sensitive pods on a separate volume, or bypass the page cache in the application with `O_DIRECT`.

### How do I know whether I am dirty-throttled or device-throttled?

Compare `/proc/vmstat` with `iostat -x 1` during the stall. If `nr_dirty` is at or above `nr_dirty_threshold` while device utilisation is moderate, writers are being throttled by the dirty budget. If `nr_dirty` is low but `%util` is at 100% with a deep `aqu-sz`, the device itself is the bottleneck and writeback tuning will not help.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
