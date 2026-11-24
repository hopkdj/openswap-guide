---
title: "Linux I/O Schedulers in 2026: none vs mq-deadline vs BFQ vs Kyber — And When They Actually Matter"
date: "2026-11-25"
tags: ["linux", "performance", "storage", "kernel", "tuning", "benchmarking"]
draft: false
---

Every few months someone posts a homelab "tuning guide" that tells you to switch every block device to `bfq`, or to `none`, or to set `elevator=noop` on the kernel command line. On a modern kernel most of that advice is either obsolete or actively wrong. The `elevator=` boot parameter belongs to the legacy block layer, `noop` was folded into `none` years ago, and on an NVMe drive with 64 hardware queues the scheduler is usually not your bottleneck.

What still matters: knowing which of the four remaining schedulers is active, why the kernel picked it, and which two tunables are worth touching for your actual workload. This guide covers that, with real commands and a benchmarking method that produces numbers you can trust.

## Quick Verdict (TL;DR)

- **NVMe (any workload):** use `none`. The device has deep hardware queues and reordering in software only adds latency. This is also the kernel's default.
- **SATA SSD:** `mq-deadline` is the sane default; `none` is fine if the drive has Native Command Queuing and a deep queue.
- **Spinning disks (HDD):** `mq-deadline` for servers and bulk storage. `bfq` only when interactive latency matters or you need proportional-share fairness between cgroups.
- **Kyber:** a targeted-latency scheduler that works well on fast SATA/NVMe-adjacent devices when you want a *predictable* read latency target instead of throughput. Rarely the best choice, occasionally exactly right.
- **Do not benchmark with `dd`.** It measures page cache. Use `fio` with `--direct=1`, and measure latency percentiles, not just average throughput.

## The Four Schedulers Side by Side

| Scheduler | Layer | Ordering strategy | Best device | CPU cost | Per-device tunables |
|---|---|---|---|---|---|
| `none` | blk-mq only | None — requests go straight to the hardware queue | NVMe, fast SSD | Lowest | None |
| `mq-deadline` | blk-mq | Deadline per request (read/write expiry), FIFO batches | SATA SSD, HDD, SAN LUNs | Low | `read_expire`, `write_expire`, `writes_starved`, `fifo_batch` |
| `bfq` | blk-mq | Budget Fair Queueing — per-cgroup/process proportional share | HDD, desktop, multi-tenant I/O | Highest | `low_latency`, `slice_idle`, `fifo_expire_async`, weights |
| `kyber` | blk-mq | Two implicit queues (read/write) with latency targets | Fast SSD, latency-sensitive services | Low | `read_lat_nsec`, `write_lat_nsec` |

Note the legend: with blk-mq (default since kernel 5.0), everything is a multi-queue scheduler. `noop` no longer exists as a separate entry — `none` replaced it. If a guide tells you to set `elevator=noop`, it was written for a kernel old enough to have security updates you are not installing.

## Decision Matrix

| Situation | Scheduler | Reason |
|---|---|---|
| NVMe system disk, general server | `none` | Zero software reordering overhead; hardware queues are deep enough |
| Database on NVMe | `none` + cgroup `io.latency` | Scheduler cannot help; isolation must come from cgroups |
| 4-drive HDD RAID for backups | `mq-deadline` | Prevents write starvation of reads, cheap |
| Desktop / workstation with HDD | `bfq` | Per-process fairness keeps the UI responsive during large copies |
| Multi-tenant host, noisy neighbours | `bfq` + `io.weight` | Proportional share is BFQ's core feature |
| Latency SLO on SATA SSD (e.g. log ingest) | `kyber` with a 1–2 ms read target | Explicit latency target instead of a queue-depth heuristic |
| Container host with mixed workloads | `none` + `io.max` / `io.latency` per slice | Enforce limits at the cgroup layer, not the scheduler |

## Checking What Is Actually Active

```bash
# The active scheduler is in brackets
for d in /sys/block/*/queue/scheduler; do echo "$d: $(cat $d)"; done

# Typical output on a modern server:
# /sys/block/nvme0n1/queue/scheduler: [none] mq-deadline kyber bfq
# /sys/block/sda/queue/scheduler: [mq-deadline] none kyber bfq
```

The bracketed entry is what the kernel selected. Selection is driven by the device's `rotational` flag, queue depth, and the kernel config, not by a global default you can set once for all devices.

To change it per device, either write to sysfs directly (non-persistent) or ship a udev rule (persistent):

```bash
# Immediate, non-persistent
echo none | sudo tee /sys/block/nvme0n1/queue/scheduler

# Persistent: /etc/udev/rules.d/60-iosched.rules
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/scheduler}="none"
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="1", ATTR{queue/scheduler}="mq-deadline"
```

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=block
```

## none — The Default That Wins on NVMe

`none` does no reordering and no merging in the scheduler. For NVMe this is correct: a modern enterprise NVMe exposes dozens of queues with 1,024 entries each, and the device firmware reorders internally. Inserting software sorting in front of that only adds a hop.

```bash
cat /sys/block/nvme0n1/queue/nr_requests     # queue depth visible to the block layer
cat /sys/block/nvme0n1/queue/nr_requests     # raise this only if you see queue-full errors
```

The one legitimate reason to raise `nr_requests` on NVMe is a workload with very deep queues that is hitting `queue full` throttling. Watch `iostat -x 1` for elevated `aqu-sz` combined with high latency — that is queue pressure, not scheduler misconfiguration.

## mq-deadline — The Server Default for Rotational Media

`mq-deadline` assigns a deadline to every request and serves the oldest-expired first, while batching requests that are physically adjacent. It is a good compromise for SATA SSDs, HDDs, and — importantly — for network block devices, where the "device" is another machine and reordering is cheap insurance.

The four tunables live in `/sys/block/<dev>/queue/iosched/`:

```bash
ls /sys/block/sda/queue/iosched/
# fifo_batch  front_merges  read_expire  write_expire  writes_starved

# Give reads a 250 ms deadline instead of the 500 ms default
echo 250 | sudo tee /sys/block/sda/queue/iosched/read_expire
# Allow 4 write batches before serving a read (default 2)
echo 4 | sudo tee /sys/block/sda/queue/iosched/writes_starved
```

`read_expire` and `write_expire` are in milliseconds. Lower values improve read latency at the cost of throughput; on a backup array where writes dominate, raise `write_expire` to 10000 and leave reads at 500.

## BFQ — Proportional Share, Not Throughput

BFQ (`CONFIG_IOSCHED_BFQ`) is the only scheduler here that implements per-process and per-cgroup proportional sharing inside the block layer. Its cost is CPU time per request: on a fast NVMe it can measurably reduce peak IOPS, which is why distributions do not enable it by default on servers.

It is the right answer in exactly two situations: spinning disks on a desktop, and multi-tenant hosts where one container must not starve the others.

```bash
echo bfq | sudo tee /sys/block/sda/queue/scheduler
cat /sys/block/sda/queue/iosched/low_latency       # 1 = prioritize interactive latency
echo 0 | sudo tee /sys/block/sda/queue/iosched/low_latency   # 0 = prioritize throughput
```

With cgroup v2, BFQ weights are set through the standard `io.weight` interface rather than BFQ-specific knobs — which is the correct way to do QoS, because it survives scheduler changes:

```bash
# Give the database slice 4x the I/O weight of the backup slice
sudo systemctl set-property db.slice IOWeight=400
sudo systemctl set-property backup.slice IOWeight=100
```

For hard ceilings and latency protection, cgroup v2 offers `io.max` (absolute IOPS/bandwidth caps) and `io.latency` (protects a cgroup's latency target by throttling others). Both are enforced regardless of which scheduler is active, which makes them the more portable investment.

## Kyber — Explicit Latency Targets

Kyber keeps two queues (reads and writes) and tries to hit a configured latency target by adjusting how many requests it dispatches per cycle. That is a different control model from deadline-based scheduling: you tell it the latency you want, and it self-tunes the depth.

```bash
echo kyber | sudo tee /sys/block/sda/queue/scheduler
cat /sys/block/sda/queue/iosched/read_lat_nsec      # default 2000000 (2 ms)
cat /sys/block/sda/queue/iosched/write_lat_nsec     # default 10000000 (10 ms)
```

It works best on devices that are fast but not infinitely parallel — SATA SSDs, mid-range NVMe, and virtio disks on a busy hypervisor. On a high-end NVMe, `none` still wins; on an HDD, `mq-deadline` is more appropriate because Kyber does not model seek cost.

## Benchmarking That Produces Usable Numbers

`fio` (`axboe/fio`, **6,437 stars**, last push 2026-11-24) is the only tool worth using for this. Three rules: use `--direct=1` to bypass page cache, test the *device* for read workloads, and test a *file* for write workloads so you do not destroy a filesystem.

```bash
# Read-only random 4K test on a raw device (safe: no writes)
sudo fio --name=randread4k --filename=/dev/nvme0n1 --direct=1 \
  --rw=randread --bs=4k --iodepth=32 --numjobs=4 --ioengine=libaio \
  --runtime=60 --time_based --group_reporting

# Write test — ALWAYS against a scratch file, never a raw device
fio --name=randwrite4k --filename=/mnt/scratch/fio.test --size=8G --direct=1 \
  --rw=randwrite --bs=4k --iodepth=32 --numjobs=4 --ioengine=libaio \
  --runtime=60 --time_based --group_reporting

# Mixed 70/30 read/write, the realistic server pattern
fio --name=mixed --filename=/mnt/scratch/fio.test --size=8G --direct=1 \
  --rw=randrw --rwmixread=70 --bs=16k --iodepth=16 --numjobs=2 \
  --ioengine=libaio --runtime=120 --time_based --group_reporting
```

Read the **p99 and p99.9 latency** lines, not the average. Two schedulers can post identical average IOPS while one shows a 40 ms p99 and the other 4 ms — for anything user-facing, the tail is the metric.

For latency distribution without re-running benchmarks, use `biolatency` from bcc, or the equivalent script in the `bpftrace` repository (`bpftrace/bpftrace`, **10,445 stars**, last push 2026-11-24):

```bash
sudo /usr/share/bcc/tools/biolatency 10 1     # 10 s window, 1 s refresh, histogram
sudo blktrace -d /dev/sda -o - | blkparse -i -    # per-request detail when you need it
```

After changing a scheduler, re-run the identical `fio` job. If p99 latency did not move by more than 10%, revert — schedulers are not a substitute for fixing a saturated device.

Tuning the block layer is only one layer of the stack. If your queue depth is the actual limit, see [async I/O engines compared](../2026-06-02-linux-async-io-libaio-posix-aio-iouring-guide/); if memory pressure is evicting your cache, [transparent hugepages tuning](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) is the next stop; and for enforcing I/O limits per service, the [cgroup v2 administration guide](../2026-06-01-linux-cgroup-v2-management-systemd-cgtop-cgroup-tools-libcgroup-guide/) covers `io.max`, `io.weight`, and `io.latency` in depth. If your block device is remote, read the [NVMe over Fabrics guide](../2026-06-02-nvme-over-fabrics-spdk-linux-ceph-guide/) first — scheduler tuning cannot fix network latency.

## Pitfalls That Waste Weeks

1. **Using `elevator=noop` on the kernel command line.** It belongs to the legacy block layer; on current kernels it is ignored or invalid, and `noop` has been replaced by `none` for years.
2. **Benchmarking without `--direct=1`.** You are measuring RAM, not the disk. Every "my NVMe does 8 GB/s" claim built on `dd` is a page-cache measurement.
3. **Write-testing a raw device.** `fio --filename=/dev/sda --rw=write` destroys the filesystem. Always use a scratch file for write tests.
4. **Setting `bfq` on NVMe "for fairness".** You lose peak throughput and gain little; use cgroup `io.weight` instead, which is scheduler-independent.
5. **Editing sysfs and expecting persistence.** `/sys` resets on reboot. Ship a udev rule.
6. **Judging by average latency.** Tail latency is what users feel; collect p99 before and after every change.
7. **Ignoring `nr_requests` and queue depth.** A 32-deep queue on a device that supports 1,024 leaves performance on the table for some workloads, and an over-deep queue inflates latency for others.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Linux I/O Schedulers in 2026: none vs mq-deadline vs BFQ vs Kyber",
  "description": "Which Linux block-layer I/O scheduler to use for NVMe, SATA SSD, and HDD in 2026, with per-device tunables, cgroup v2 QoS, and a reproducible fio benchmarking method.",
  "datePublished": "2026-11-25",
  "dateModified": "2026-11-25",
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

**Which I/O scheduler does Linux use by default in 2026?**
For NVMe devices the kernel selects `none`, and for SATA devices `mq-deadline` is the common distribution default. Because blk-mq is the only block layer, all schedulers are multi-queue, and `noop` no longer exists as a separate option.

**Is `none` always faster than `mq-deadline` on NVMe?**
For most workloads yes, because the device has deep hardware queues and reorders internally. The exception is a device or virtual disk with a shallow queue where deadline-based ordering prevents write starvation — measure p99 latency both ways rather than assuming.

**When should I use BFQ?**
On spinning disks where interactive responsiveness matters, and on multi-tenant hosts that need proportional-share fairness between processes or cgroups. It has the highest CPU cost per request and generally lowers peak throughput on NVMe.

**What replaced the `elevator=` kernel parameter?**
Per-device configuration through `/sys/block/<dev>/queue/scheduler`, usually persisted with a udev rule. The legacy `elevator=` parameter applied to the old single-queue block layer and is not the right mechanism on modern kernels.

**How do I limit one container's disk usage without changing the scheduler?**
Use cgroup v2 interfaces: `io.max` for hard caps, `io.weight` for proportional sharing, and `io.latency` to protect a service's latency target. These are enforced at the cgroup layer and work with any scheduler.

**Can scheduler tuning fix high disk latency?**
No, if the device is saturated. Scheduler tuning changes the order and fairness of requests; it cannot create bandwidth. Fix saturation with faster media, more parallelism, or by moving load — then tune the scheduler for the tail.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
