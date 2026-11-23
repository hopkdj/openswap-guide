---
title: "SysV IPC and /dev/shm in 2026: The 64 MB Wall Behind 'No Space Left on Device'"
date: "2026-11-23"
tags: ["linux", "troubleshooting", "docker", "kernel", "postgresql"]
draft: false
description: "Three different limits share the name shared memory. Real ipcs output, the swappable-segment surprise, and the container shm fix."
---

The error is one of the most misleading in Linux, because it points at the wrong resource entirely:

```
FATAL: could not create shared memory segment: No space left on device
```

Behind that message there are hundreds of gigabytes free on every filesystem, `df -h` agrees, and the process is not writing to a disk at all — it is writing to **shared memory**. Shared memory on Linux is bounded by three unrelated mechanisms, none of which appear in `df /`. Inside a container the bound is even tighter: Docker gives every container a **64 MB `/dev/shm` by default**, a number that has caused more production incidents than any other Docker default.

This article unpacks all three limits with real measurements from a live host, because the confusion between them is what turns a five-minute fix into a two-day debugging session.

## TL;DR — Which "Shared Memory" Is Full?

- **`/dev/shm` is a tmpfs mount.** Its size is a mount option, not a sysctl. On bare metal it defaults to half of RAM; in Docker it defaults to **64 MB** per container; in Kubernetes an `emptyDir: {medium: Memory}` counts against the pod's memory limit instead.
- **SysV shared memory (`shmget`) is a separate, older mechanism.** It is governed by `kernel.shmmax`, `kernel.shmall` and `kernel.shmmni`, and it is **swappable** — the host measured below had 20,277 shm pages in swap.
- **POSIX shared memory (`shm_open`) appears as files in `/dev/shm`.** That is why a PostgreSQL cluster using `dynamic_shared_memory_type = posix` leaves `PostgreSQL.<pid>` files there — deleting them is not cleanup, it is corruption.
- **`No space left on device` from a shared-memory allocation is `ENOSPC` on the tmpfs, not on your disk.** Check `df -h /dev/shm` and `ipcs -u` before you touch anything else.
- **`kernel.shmmax` on modern systemd hosts is effectively unlimited.** If you are chasing `shmmax` on Ubuntu 24.04 you are chasing a knob that was already turned all the way up.

## Three Mechanisms, Three Sets of Knobs

| Mechanism | Created by | Limit control | Visible in | Swappable |
|---|---|---|---|---|
| tmpfs `/dev/shm` | mount | `size=` mount option, or `--shm-size` in containers | `df -h /dev/shm` | Yes |
| POSIX shm | `shm_open()` | Same as `/dev/shm` — it *is* `/dev/shm` | `ls /dev/shm` | Yes |
| SysV shm | `shmget()` | `kernel.shmmax`, `shmall`, `shmmni` | `ipcs -m`, `/proc/sysvipc/shm` | **Yes** |
| Anonymous `MAP_SHARED` | `mmap()` | No dedicated limit; counts as process memory | `/proc/<pid>/maps`, `smaps` | Yes |
| Huge-page backed | `mmap(MAP_HUGETLB)` or SysV with `SHM_HUGETLB` | `vm.nr_hugepages` | `grep Huge /proc/meminfo` | **No** |

That last row is where databases hurt. Huge pages are pre-allocated and cannot be swapped or reclaimed, so a host with a mis-sized huge-page pool fails differently — usually at startup, with a numeric error rather than `ENOSPC`.

## What This Host Actually Shows

The sysctl side first, because the numbers are surprising to anyone carrying advice from a decade-old tuning guide:

```console
$ sysctl kernel.shmmax kernel.shmall kernel.shmmni kernel.msgmax kernel.msgmnb kernel.msgmni kernel.sem
kernel.shmmax = 18446744073692774399
kernel.shmall = 18446744073692774399
kernel.shmmni = 4096
kernel.msgmax = 8192
kernel.msgmnb = 16384
kernel.msgmni = 32000
kernel.sem = 32000	1024000000	500	32000
```

`18446744073692774399` is `ULONG_MAX - 4095` — systemd has set `shmmax` and `shmall` to "unlimited" since v8, and Ubuntu 24.04 has inherited that. **On any modern systemd distribution, `shmmax` is not your problem.** The remaining SysV limits that can actually bite are:

- `shmmni = 4096` — maximum number of **segments**, not bytes. A leaking application that calls `shmget` in a loop exhausts this while using almost no memory.
- `sem = 32000 1024000000 500 32000` — max semaphores per array, system-wide semaphores, max ops per `semop`, max arrays. Applications that use semaphore sets for locking (older databases, MPI jobs) hit the second value.
- `msgmni = 32000` and `msgmnb = 16384` — queue count and per-queue bytes. `msgmnb` at 16 KB is small enough that a single large message can block.

Now the live usage, which is where the genuinely counter-intuitive detail lives:

```console
$ ipcs -u

---------- 共享内存状态 ------------
段已分配 9
页已分配 50249
页驻留  28272
页交换  20277
交换性能：0 次尝试	 0 次成功
```

Read that carefully: **9 segments, 50,249 pages allocated, 28,272 resident, 20,277 in swap.** Fifty thousand pages is 196 MB of shared memory, and **40% of it is on disk**. SysV shared memory is *not* pinned in RAM; it is backed by swap like any other anonymous memory. Two consequences follow:

1. **`ipcs` totals do not tell you how much RAM you are using.** A database with a 32 GB SysV segment and no `SHM_LOCK` can have most of it swapped out, which is exactly the performance cliff people describe as "the database got slow overnight."
2. **`ulimit -l` is what stops that.** On this host it is `8192` KB — **8 MB of mlockable memory**, which is why no process can pin a shared segment, and why `PostgreSQL` `huge_pages = try` silently falls back. Check it before blaming the database:

```console
$ ulimit -l
8192
$ grep -E "HugePages_Total|Hugepagesize" /proc/meminfo
HugePages_Total:       0
Hugepagesize:       2048 kB
```

Zero huge pages configured, 8 MB lockable. A server that wants to lock a 16 GB shared segment is not going to succeed here, and the error will look like a permissions problem.

Here is what the segments themselves look like:

```console
$ ipcs -m
------------ 共享内存段 --------------
键        shmid      拥有者  权限     字节     连接数
0x00000000 688151     genesis    600        8388608    2
0x00000000 196635     root       666        33177600   0
```

Two things stand out. The `键` (key) is `0x00000000` on both — private segments created with `IPC_PRIVATE`, which is what modern PostgreSQL does for its main shared memory area rather than the old fixed-key approach. And shmid 196635 is **33 MB with zero attaches** — a leaked segment from a process that exited without `shmctl(IPC_RMID)`. That is the failure mode `shmmni = 4096` protects you from, and it is why the segment count matters more than the byte total.

Finally, the tmpfs that the error message is usually about:

```console
$ df -h /dev/shm
Filesystem      Size  Used Avail Use% Mounted on
tmpfs            14G  7.5M   14G   1% /dev/shm
$ ls -la /dev/shm
-rw------- 1 postgres postgres  1048576 Nov 10 06:28 PostgreSQL.1627843286
-rw------- 1 postgres postgres    26976 Nov 10 06:28 PostgreSQL.348586004
```

14 GB — exactly half of this host's 27.7 GB of RAM, the default tmpfs sizing. Those `PostgreSQL.*` files are not temp files to be cleaned; they are live POSIX shared memory segments belonging to the running cluster. **Deleting them while it runs is how you corrupt a database**, and it is a mistake people make precisely because the filenames look disposable.

## The Container Case: 64 MB and Nothing You Can df

Docker mounts a **64 MB tmpfs at `/dev/shm` for every container** unless told otherwise. It does not matter that the host has 14 GB mounted there; the container sees its own small tmpfs, and any workload that expects a real `/dev/shm` fails:

- Chromium-based anything (browser workers, PDF renderers, headless test runners) crashes with `Failed to create shared memory` or a generic renderer crash.
- PostgreSQL with `dynamic_shared_memory_type = posix` fails on parallel query.
- Redis and other stores that fork for background saves can fail on the copy.
- Machine-learning data loaders using `torch.multiprocessing` or `multiprocessing.shared_memory` raise `FileNotFoundError` or `ENOSPC` — with no disk anywhere near full.

The fix is one flag:

```yaml
services:
  app:
    image: example/app:latest
    shm_size: "1gb"
```

Or for a one-off, `docker run --shm-size=1g ...` gives the container a 1 GB tmpfs; confirm it from inside the container with `df -h /dev/shm`, which will report the new size rather than 64 MB.

In Kubernetes there is no `shmSize` field on the pod spec, which is a frequent source of confusion. You get two options:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
    - name: worker
      image: example/worker:latest
      volumeMounts:
        - name: dshm
          mountPath: /dev/shm
  volumes:
    - name: dshm
      emptyDir:
        medium: Memory
        sizeLimit: 1Gi
```

An `emptyDir` with `medium: Memory` is a tmpfs, and **its sizeLimit is charged against the container's memory limit**, not against a separate quota. Set `sizeLimit` and forget to raise `resources.limits.memory` and the pod gets OOM-killed instead of returning `ENOSPC` — a strictly worse failure, because nothing in the logs mentions shared memory.

## Decision Matrix

| Symptom | Actual limit | Fix |
|---|---|---|
| Browser/renderer crash in a container, host disk fine | Docker `/dev/shm` = 64 MB | `shm_size: "1gb"` in compose, `--shm-size` in run |
| `ENOSPC` from `shm_open` on bare metal | tmpfs `/dev/shm` size | Remount with a larger `size=`, or move the allocation |
| `shmget: No space left on device` | `kernel.shmmax` or `shmall` | Check `sysctl kernel.shmmax` first — usually already unlimited |
| `shmget: No space left on device` with low usage | `kernel.shmmni` exhausted (leaked segments) | `ipcs -m` for zero-attach segments, `ipcrm -m <id>` |
| Shared segment dramatically slower than expected | Pages swapped out | Raise `ulimit -l`, use huge pages, or lock the segment |
| Database will not start, numeric memory error | `vm.nr_hugepages` too small | Size the pool from the segment size, reboot |
| Pod OOM-killed after adding a memory `emptyDir` | `emptyDir` counts against the memory limit | Raise `resources.limits.memory` accordingly |

## Diagnosing in the Right Order

```bash
# 1. Is it tmpfs or SysV? They are different subsystems.
df -h /dev/shm; ipcs -u | head -20

# 2. Total SysV usage in bytes, per segment, biggest first
ipcs -m --bytes | awk 'NR>3 {print $5, $2, $3}' | sort -rn | head

# 3. Segments with no attached processes — leaked
ipcs -m | awk 'NR>3 && $6==0 {print}'

# 4. What is actually in tmpfs, by owner
du -sh /dev/shm/* 2>/dev/null | sort -h | tail

# 5. Can anything lock memory at all?
ulimit -l; grep Huge /proc/meminfo
```

Step 3 is the one that solves most "SysV is full" tickets. A segment with `nattch = 0` and a non-zero size is memory nobody owns and nobody will ever free — `ipcrm -m <shmid>` reclaims it. Do that only after confirming no process will reattach; the safe check is that the owning PID is gone.

## Pitfalls

- **`df -h /dev/shm` inside a container shows the container's tmpfs, not the host's.** That is the whole point — 64 MB looks like a healthy empty filesystem at 0% used until the allocation fails.
- **`shmall` is in pages, `shmmax` is in bytes.** Mixing them up produces values that look absurd; `shmall` at `18446744073692774399` pages is a number larger than the address space, which is how you know systemd set it to "unlimited" rather than someone tuning it.
- **Deleting files in `/dev/shm` is not cleanup.** POSIX shm names live there; `PostgreSQL.*`, `sem.*`, and `pulse-shm-*` entries belong to running processes. Unlinking a mapped segment does not free it until every mapper exits, and unlinking an in-use database segment causes corruption.
- **`ipcs` totals do not equal RAM usage.** Check the `swapped` figure. A shared segment that is 40% swapped explains a slowdown that no memory graph shows.
- **`ulimit -l` defaults to 8 MB on most systemd distributions** and is the reason `mlock`-based locking fails. It is a per-process rlimit, so raising it for a service means a systemd `LimitMEMLOCK=infinity` drop-in, not a sysctl.
- **Huge pages are reserved, not allocated on demand.** `vm.nr_hugepages` must be set before the database starts, and the pool cannot be swapped — oversizing it starves the rest of the machine.
- **`kernel.msgmnb = 16384` limits a single SysV message queue to 16 KB.** Applications using message queues for large payloads block at exactly 16 KB and report it as a timeout, not as a size error.
- **Changing `kernel.shmmax` down does not shrink existing segments.** Like most kernel limits, it applies to new allocations; existing mappings stay valid, which makes a bad value look harmless until the next restart.

For the accounting side of the same story — how resident, shared and anonymous memory are attributed per container — see our [RSS vs PSS vs USS memory accounting guide](../2026-11-22-rss-pss-uss-container-memory-accounting/). If the container is dying with a memory-related error that is *not* `ENOSPC`, the [vm.max_map_count and overcommit guide](../2026-11-23-vm-max-map-count-container-crashes-overcommit/) covers the mapping ceiling, and the [KSM and memory deduplication tuning guide](../2026-06-02-linux-kernel-ksm-tuning-ksm-uksm-ksmtuned-guide/) explains why shared pages may not cost what `top` implies.

## FAQ

**Why do I get "No space left on device" when the disk has hundreds of gigabytes free?**
Because the allocation failed on a tmpfs or a SysV limit, not on a filesystem. `df /` does not show `/dev/shm`, and SysV shared memory has no filesystem at all. Check `df -h /dev/shm` and `ipcs -u` before anything else.

**What is the default `/dev/shm` size in Docker?**
64 MB per container, mounted as a tmpfs. It is independent of the host's `/dev/shm`, so a host with 14 GB there still gives each container 64 MB unless `--shm-size` or compose `shm_size` says otherwise.

**Is SysV shared memory swappable?**
Yes, unless the segment is locked with `SHM_LOCK` and `ulimit -l` permits it. It is backed by swap like any anonymous memory, which is why `ipcs -u` can report a large fraction of a shared segment in swap and why databases that lock their segments need both a raised memlock limit and `SHM_LOCK` support in the application.

**Do I still need to tune `kernel.shmmax` in 2026?**
Almost never on a systemd distribution. Since systemd v8, `shmmax` and `shmall` are set to effectively unlimited, as this host shows with `18446744073692774399`. Oracle-style tuning guides that ask for `kernel.shmmax = half of RAM` are obsolete on Ubuntu, Debian and RHEL 8+.

**How do I find leaked SysV segments?**
`ipcs -m` and look for entries with `nattch` equal to zero and a non-zero byte count. Those are segments whose owning process exited without `shmctl(IPC_RMID)`. Remove them with `ipcrm -m <shmid>` after confirming the owner is gone.

**Why does a Pod get OOM-killed instead of reporting no space after I add a memory emptyDir?**
Because an `emptyDir` with `medium: Memory` is a tmpfs whose usage counts against the container's memory cgroup. If `sizeLimit` exceeds `resources.limits.memory`, the cgroup limit is hit first and the kernel kills the container before the tmpfs ever fills.

**Are the files in `/dev/shm` safe to delete?**
No. Names like `PostgreSQL.1627843286` or `pulse-shm-*` are live POSIX shared memory objects owned by running processes. Delete them and the process either loses its data or crashes; for a database, it can corrupt on-disk state as well.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "SysV IPC and /dev/shm in 2026: The 64 MB Wall Behind 'No Space Left on Device'",
  "description": "The three different Linux shared memory limits, real ipcs and tmpfs measurements, swappable SysV segments, and the container shm-size fix.",
  "datePublished": "2026-11-23",
  "dateModified": "2026-11-23",
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
