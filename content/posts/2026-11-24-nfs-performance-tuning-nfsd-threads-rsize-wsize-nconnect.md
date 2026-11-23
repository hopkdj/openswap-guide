---
title: "NFS Performance Tuning in 2026: nfsd Threads, rsize/wsize and nconnect Explained"
date: "2026-11-24"
description: "Your NFS server is not slow — it is under-provisioned in one specific place. A practical tuning guide to nfsd thread counts, the RPC slot table, rsize/wsize, nconnect and export options, with real configs, nfsstat diagnostics and the numbers to start from for 1GbE through 25GbE."
tags: ["nfs", "storage", "linux", "performance", "networking", "tuning"]
draft: false
---

A 25GbE link, an NVMe-backed export, and a build farm that still takes 40 minutes to check out a repository. `nfsstat -s` shows reply cache hits near zero, the client reports `nfs: server ... not responding, still trying`, and the storage array is idle. Nothing is broken. **The server simply has 8 RPC threads for a workload that needs 64, and every additional request waits in the socket backlog.**

NFS tuning has a small number of levers with large effects: the number of `nfsd` kernel threads, the client-side RPC slot table, the transfer size (`rsize`/`wsize`), the number of TCP connections per mount (`nconnect`), and a handful of export and mount options that quietly disable caching or serialise writes. This guide covers each with the values worth starting from in 2026.

## TL;DR — Quick Verdict

- **1GbE file server, a dozen clients:** leave the defaults mostly alone. `threads=16` in `/etc/nfs.conf` is enough; spend your effort on `noatime` and `no_subtree_check` instead.
- **10GbE lab or CI cache:** `threads=32`, mount with `nconnect=4`, and confirm `rsize`/`wsize` negotiated to 1 MB. This is the single biggest win for build farms.
- **25GbE or faster, NVMe export, many clients:** `threads=64` to `128`, `nconnect=8`, and check `/proc/net/rpc/nfsd` for thread saturation before adding more.
- **High-latency links (cross-region, satellite, Wi-Fi):** raise `sunrpc.tcp_slot_table_entries=128` on the client. The default slot table caps in-flight requests, so bandwidth-delay product is wasted no matter how fast the server is.
- **Write-heavy workloads that feel slow:** check whether you are paying for `sync` exports and `actimeo` storms before touching thread counts. Threads do not fix a disk bottleneck or a cold attribute cache.

## The Knobs That Matter, Compared

| Knob | Where | Stock value | What it bounds | Start here (10GbE) |
|---|---|---|---|---|
| `nfsd` threads | `/etc/nfs.conf` → `[nfsd] threads`, or `/proc/fs/nfsd/threads` | 16 | Concurrent RPC requests the server can process | 32 |
| Sun RPC slot table | `sunrpc.tcp_slot_table_entries` (client) | 2 on modern kernels | In-flight requests per client connection | 128 on high-latency links |
| `rsize` / `wsize` | mount options | negotiated, up to 1 MB | Bytes per read/write RPC | 1048576 |
| `nconnect` | mount option (5.3+) | 1 | TCP connections per mount | 4 (8 for 25GbE) |
| `actimeo` | mount option | 3/60/30/60 s (file/dir, min/max) | Attribute cache lifetime | 30–60 for read-mostly |
| `sync` / `async` | export option | `sync` | Whether the server acknowledges before data hits disk | keep `sync` |
| `no_subtree_check` | export option | varies by nfs-utils version | Path verification cost per request | set explicitly |
| `noatime` / `relatime` | mount option | `relatime` | Extra write RPCs from reads | `noatime` on read-mostly |

The number that surprises people is the slot table. On current kernels the default is **2 outstanding requests per connection**, a value chosen to be safe on a 2003-era WAN, not to fill a 10GbE pipe. Every extra round trip costs you latency you already paid for.

## Decision Matrix: What to Change First

| Symptom | First change | Why it works |
|---|---|---|
| Build farm checkouts are slow, array idle | `nconnect=4` then `threads=32` | More parallel TCP streams and more server workers |
| Write throughput plateaus at ~1/8 of link speed | `threads=64`, verify `wsize=1048576` | Default thread count saturates before the link does |
| Reads fast, metadata operations crawl | Raise `actimeo`, add `noatime` | Every `stat()` otherwise round-trips |
| Long-haul client caps at low throughput | `sunrpc.tcp_slot_table_entries=128` | Slot table limits in-flight requests, not bandwidth |
| Writes are slow but reads are fine | Check export `sync` and device latency | `sync` exports wait for stable storage per request |
| Everything is slow, `%util` at 100% | Stop tuning NFS; the device is the bottleneck | Threads cannot create IOPS |
| Clients see stale file data | Lower `actimeo` (e.g. 1) | Shorter attribute cache means fresher metadata |

## Configuring the Server: Threads and Exports

Modern nfs-utils reads `/etc/nfs.conf`, which supersedes the old distro-specific `RPCNFSDCOUNT` variable in `/etc/default/nfs-kernel-server`. The stock file documents the default explicitly:

```ini
# /etc/nfs.conf
[nfsd]
threads = 32
# keep the modern protocol surface, drop UDP entirely
udp = n
tcp = y
vers4 = y
vers4.1 = y
vers4.2 = y
```

```bash
sudo systemctl restart nfs-server      # or nfs-kernel-server on Debian/Ubuntu
cat /proc/fs/nfsd/threads              # verify the running count
```

You can also change it live, without dropping mounts, because `/proc/fs/nfsd/threads` is writable:

```bash
echo 64 | sudo tee /proc/fs/nfsd/threads
cat /proc/fs/nfsd/threads
```

An export table tuned for a CI cache — read-mostly, many clients, no subtree checks:

```bash
# /etc/exports
/srv/cache  10.20.0.0/16(rw,sync,no_subtree_check,no_root_squash,fsid=1)
/srv/artifacts 10.20.0.0/16(ro,sync,no_subtree_check,fsid=2)
```

```bash
sudo exportfs -ra
sudo exportfs -v          # confirm effective options, not just what you typed
```

Two export decisions deserve attention. **`sync` is the default and should stay that way** — `async` lets the server acknowledge writes that are still in its page cache, which turns a server crash into silent client data loss for workloads that believe `fsync()` completed. **`no_subtree_check`** removes a per-request path walk; it is safe for exports where the exported directory is not renamed while clients hold file handles, which covers almost every CI or media share.

## Configuring the Client: Transfer Size, nconnect, Slots

```bash
# /etc/fstab — 10GbE mount to a CI cache
nfs04:/srv/cache  /mnt/cache  nfs4  rw,hard,rsize=1048576,wsize=1048576,nconnect=4,noatime,actimeo=30,_netdev  0 0
```

| Option | Effect | Caution |
|---|---|---|
| `rsize=1048576,wsize=1048576` | 1 MB RPC payloads, the maximum for NFSv3/v4 | Some appliances cap at 64 KB; verify with `mountstats` |
| `nconnect=4` | Four TCP connections per mount, multiplied queue depth | Mount-time only; must unmount to change; more CPU per client |
| `hard` | Retry forever instead of erroring to the application | Correct for databases; `soft` is for disposable scratch data |
| `noatime` | Reads no longer generate attribute updates | Loses last-access tracking |
| `actimeo=30` | One setting for all four attribute-cache timers | `actimeo=0` disables caching and multiplies RPC load |
| `_netdev` | Delays mount until networking is up | Essential on boot, otherwise the mount times out |

For high-latency links, raise the client's in-flight request budget — this is a client-side sysctl, not a server one:

```ini
# /etc/sysctl.d/70-sunrpc.conf
sunrpc.tcp_slot_table_entries = 128
```

```bash
sudo sysctl --system
sysctl sunrpc.tcp_slot_table_entries
```

## Diagnosing Before and After

The server-side counters in `/proc/net/rpc/nfsd` are the fastest way to see whether threads are the constraint. The `th` line is a histogram: the first number is the thread count, followed by how many threads reached each usage bucket.

```bash
cat /proc/net/rpc/nfsd | grep -E "^(th|rc|io|net)"
# th 32 0 0 0 0 0 0 0 0 0 28   <- 28 of 32 threads at the top bucket = saturated
nfsstat -s | head -20
nfsstat -c | head -20            # on the client
```

Per-mount RPC latency, which is what users actually feel:

```bash
cat /proc/self/mountstats | grep -A6 "device nfs04"
nfsiostat 1 5                    # from nfs-utils, per-mount ops/s and RTT
mountstats iostat /mnt/cache     # newer nfs-utils interface
```

Read those numbers in order: if `th` shows threads parked in the top buckets while the backing device is idle, add threads or `nconnect`. If RTT is fine but the device shows `%util` at 100%, the export volume is the problem. If the client's op latency is high while the server looks calm, the slot table or `actimeo` is the suspect.

For the server-side architecture choice — kernel `nfsd` versus user-space NFS-Ganesha versus the minimal UNFS3 — our [NFS server implementation comparison](../2026-04-30-nfs-ganesha-vs-unfs3-vs-kernel-nfs-self-hosted-nfs-server-guide-2026/) benchmarks the three with the same workloads. If a single server is not enough, the [high-availability NFS guide](../2026-05-11-self-hosted-nfs-high-availability-drbd-glusterfs-pacemaker-guide/) covers DRBD, GlusterFS and Pacemaker failover. And because NFS clients happily acknowledge writes the server has not persisted, the [fsync durability analysis](../2026-11-22-fsync-durability-lies-linux-storage-write-cache/) is worth reading before you put a database on an export.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NFS Performance Tuning in 2026: nfsd Threads, rsize/wsize and nconnect Explained",
  "description": "Practical NFS performance tuning for 2026: nfsd thread counts, the Sun RPC slot table, rsize/wsize, nconnect, export and mount options, plus nfsstat and mountstats diagnostics with recommended values per link speed.",
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

### How many nfsd threads should I run?

Start with 16 for a 1GbE server, 32 for 10GbE and 64 to 128 for 25GbE or faster with many clients. Then verify with the `th` histogram in `/proc/net/rpc/nfsd`: if threads are consistently parked in the highest usage buckets while the backing device is idle, add more. Overshooting costs context switches and memory without improving throughput.

### Does nconnect really improve NFS throughput?

Yes, when the bottleneck is per-connection queue depth rather than the link or the disk. `nconnect=4` creates four TCP connections per mount, each with its own RPC slot table, which typically multiplies throughput on high-latency links. It requires kernel 5.3 or newer on the client, is set at mount time only, and adds client CPU cost.

### What are the maximum rsize and wsize values for NFS?

1,048,576 bytes (1 MB) for NFSv3 and NFSv4.x on Linux. Many NAS appliances and some virtualisation hosts cap at 64 KB or 128 KB, so confirm the negotiated value with `mountstats` rather than assuming your mount option took effect.

### Why is my NFS write throughput so much lower than read throughput?

Three common causes, in order: the export is `sync` (the safe default) and the backing device has slow stable-storage latency; the client is writing small files, so metadata round trips dominate; or the server has too few threads for the number of concurrent writers. Check device latency first, then `nfsstat -s` for commit and write op counts.

### Is it safe to use the async export option for speed?

No, not for data you care about. `async` allows the server to acknowledge writes before they reach stable storage, so a server crash or power loss can lose data that the client believes was committed. Use `sync` and improve throughput with more threads, `nconnect` and a faster backing device instead.

### Can I change nfsd thread count without restarting the server?

Yes. `/proc/fs/nfsd/threads` is writable: `echo 64 | sudo tee /proc/fs/nfsd/threads` adjusts the running count immediately, which is useful for testing under load. Persist the value in `/etc/nfs.conf` under `[nfsd] threads` so it survives a restart.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
