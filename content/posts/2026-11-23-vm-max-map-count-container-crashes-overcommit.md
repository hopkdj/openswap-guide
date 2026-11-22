---
title: "vm.max_map_count in 2026: Why Search and Cache Containers Die at 65,530 Mappings"
date: "2026-11-23"
tags: ["linux", "docker", "troubleshooting", "elasticsearch", "memory"]
draft: false
description: "One kernel sysctl explains why the same container image runs on Ubuntu and dies on Debian. Real mapping counts, overcommit math, and the Kubernetes fix."
---

There is a specific class of container failure that every self-hoster meets exactly once and never forgets: the image starts, logs a bootstrap check, and exits with

```
max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
```

Nothing is out of memory. `free -h` shows gigabytes free. The CPU is idle. The container simply refuses to run — and if you have ever "fixed" it by adding a compose line and moved on, you never found out that the same kernel limit is also what kills thread-heavy services with a completely unrelated-looking error.

The reason this bites is that the same image gets wildly different ceilings depending on the host. On the box that produced this article:

```console
$ sysctl vm.max_map_count vm.overcommit_memory vm.overcommit_ratio vm.overcommit_kbytes
vm.max_map_count = 1048576
vm.overcommit_memory = 0
vm.overcommit_ratio = 50
vm.overcommit_kbytes = 0
```

That is **1,048,576** — sixteen times the 65,530 that Debian 12, RHEL 8/9 and most container base images still ship. Ubuntu 24.04 raised the default in 2024 precisely because of this class of bug. So a compose file that works on one host fails on another with byte-identical configuration, and the error message blames your application.

## TL;DR — What To Do in 60 Seconds

- **If a search, cache or database container refuses to start with a `max_map_count` error:** raise the sysctl on the **host** (it is not namespaced), then restart the container. `vm.max_map_count` is per-*process* and global to the kernel, so `docker run --sysctl` only works where the runtime allows it and Kubernetes needs an explicit allowlist.
- **If a thread-heavy service dies with `pthread_create: EAGAIN` while `ps` shows few processes:** it is not the process table — it is mapping exhaustion from thread stacks and allocator arenas. Same sysctl, different symptom.
- **Do not "fix" it with a huge number and walk away.** 1,048,576 is a ceiling, not a target; the real work is finding which process is at 21,000 mappings and why.
- **Leave `vm.overcommit_memory=0` unless something specific requires otherwise.** Mode 0 is heuristic overcommit and is what makes `Committed_AS` legally exceed `CommitLimit` — which is normal, not a bug, and switching to mode 2 on a production host is how you cause an outage instead of preventing one.

## What a "Memory Area" Actually Is

Every line in `/proc/<pid>/maps` is one `vm_area_struct` in the kernel — one discrete mapping. They are created by far more than `mmap()` calls:

| Source of mappings | Approximate cost | Typical offender |
|---|---|---|
| Thread stacks | 1–2 mappings per thread | Java services (`-Xss` × threads), .NET, Rust thread pools |
| glibc malloc arenas | up to 8 per core × 64 MB | multi-threaded C/C++ services, Python with many threads |
| `mmap`ed files | 1 per file | LMDB/MDBX databases, memory-mapped indexes |
| Shared libraries | 4–6 mappings per `.so` | anything with heavy plugin loading |
| Anonymous allocations > 128 KB | 1 per allocation | jemalloc/tcmalloc workloads, columnar caches |
| Huge pages / GPU buffers | 1 per region | database buffer pools, compute nodes |

Two consequences follow, and they explain why the same sysctl produces such different failures:

1. **A thread is not free.** Raising thread counts raises mapping counts, and a 64-core box with glibc's default arena policy can burn thousands of mappings before the application allocates a single byte of useful data.
2. **Map count is orthogonal to memory usage.** You can be at 90% of the mapping ceiling while using 2% of RAM. That is why every instinct trained on OOM killers is wrong here.

Memory-mapped databases are the extreme case. LMDB-based stores map the entire database file into the address space, and each reader thread may hold its own read transaction view — so a 200 GB LMDB environment with dozens of readers can consume tens of thousands of mappings while resident memory stays modest.

## Real Mapping Counts From a Live Host

Here is why this matters in practice. Sampling the busiest processes on this host:

```console
$ for p in $(ls /proc | grep '^[0-9]' | head -40); do
    n=$(wc -l < /proc/$p/maps 2>/dev/null); [ -n "$n" ] && echo "$n $(cat /proc/$p/comm)"; done | sort -rn | head -5
21020 opencode
 7670 opencode
 3849 opencode
 1736 gnome-control-center
 1063 gnome-system-monitor
```

A single userland process is holding **21,020 mappings**. On this host that is 2% of the ceiling and utterly harmless. On a Debian 12 host with `max_map_count=65530` it would be **32% of the entire budget for one process** — and if that process spawns worker threads or opens a memory-mapped index, it will hit the wall, print `Out of memory` (misleadingly), and die.

That is the whole trap in one number. The limit is not about bytes; it is about the *number of distinct regions*, and modern runtimes create them profligately.

## Diagnosing Which Process Is Eating Mappings

Start with a census, not with `free`:

```bash
# top 10 processes by mapping count
for p in $(ls /proc | grep '^[0-9]'); do
  n=$(wc -l < /proc/$p/maps 2>/dev/null) || continue
  printf '%6d %8d %s\n' "$n" "$p" "$(cat /proc/$p/comm 2>/dev/null)"
done | sort -rn | head -10
```

Then break one process down by mapping type, which usually reveals the cause immediately:

```bash
PID=1234
awk '{ if ($6 ~ /\.so/) t="shared-lib";
       else if ($6 ~ /^\//) t="file";
       else if ($0 ~ /\[stack/) t="thread-stack";
       else if ($6 == "[heap]") t="heap";
       else t="anon" } {c[t]++} END {for (k in c) print c[k], k}' /proc/$PID/maps | sort -rn
```

Read the result like this:

- **`anon` dominates** → allocator arenas and large anonymous allocations. Check thread count and glibc arena settings.
- **`thread-stack` is large and grows with load** → thread-per-connection design; either cap threads or shrink stacks.
- **`file` dominates** → a memory-mapped index or LMDB environment. This is the classic search/cache case and it is the one that legitimately needs a higher ceiling.
- **`shared-lib` is enormous** → hundreds of plugin `.so` files; containerizing that as one process is the design problem.

Two more views worth knowing:

```bash
# total address space reserved vs resident — different questions
grep -E "VmPeak|VmSize|VmRSS" /proc/$PID/status

# per-mapping detail with RSS attribution
pmap -x $PID | tail -1
```

`VmPeak` in the tens of gigabytes with a `VmRSS` of hundreds of megabytes means you are mapping, not using — virtual address space is cheap and effectively unlimited on 64-bit, which is exactly why the kernel caps map *count* instead of map *size*.

## The Overcommit Question (And Why Mode 0 Is Usually Right)

`vm.max_map_count` is only half of the address-space story. The other half decides whether an allocation is *allowed at all*:

| `vm.overcommit_memory` | Behavior | What it means in practice |
|---|---|---|
| `0` (heuristic, default) | Kernel estimates; allows generous overcommit | `Committed_AS` may exceed `CommitLimit`; almost nothing is refused up front |
| `1` (always) | Never refuse an allocation | Required by some fork-heavy designs (Redis background save legacy advice) |
| `2` (strict) | Refuse anything beyond `CommitLimit` | Turns overcommit into hard accounting; can convert a benign spike into `ENOMEM` |

This host runs mode 0, and the numbers show exactly what that permits:

```console
$ grep -E "CommitLimit|Committed_AS|MemTotal" /proc/meminfo
MemTotal:       28441524 kB
CommitLimit:    22609364 kB
Committed_AS:   30807488 kB
```

**Committed memory (30.8 GB) exceeds the commit limit (22.6 GB)** — on a 28.4 GB machine whose `overcommit_ratio` is 50. In mode 0 this is expected: the limit is a heuristic input, not a wall. Systems that monitor `Committed_AS` against `CommitLimit` and page on the ratio will page constantly on a perfectly healthy host. If you inherit such an alert, fix the alert before you touch the sysctl.

Switching to mode 2 (`overcommit_memory=2`) on a host in this state is actively dangerous: the next allocation that pushes committed memory past `CommitLimit` is refused immediately, which is how you turn a routine traffic spike into application-level `ENOMEM` failures across every service at once. Mode 2 is for appliances with precisely modeled workloads, not for general-purpose self-hosted boxes.

## Fixing It: Host, Container, Kubernetes

Because `vm.max_map_count` is a **global, non-namespaced** sysctl, the fix has to land on the host kernel — but how you deliver it depends on the platform.

**Bare metal / VM host (persistent):**

```ini
# /etc/sysctl.d/99-mm.conf
vm.max_map_count = 1048576
vm.overcommit_memory = 0
vm.overcommit_ratio = 50
```

```bash
sysctl --system && sysctl vm.max_map_count
```

**Docker Compose** — set it per container where the runtime permits, but understand it is a host-level value:

```yaml
services:
  opensearch:
    image: opensearchproject/opensearch:2.17.1
    sysctls:
      - vm.max_map_count=1048576
    ulimits:
      memlock:
        soft: -1
        hard: -1
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - ./data:/usr/share/opensearch/data
```

**Kubernetes** — `vm.*` sysctls are classified as *unsafe*, so a plain `securityContext.sysctls` entry is rejected unless the kubelet explicitly allows it:

```yaml
# node-level fix, applied once per node
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: mm-sysctl
spec:
  selector:
    matchLabels: { app: mm-sysctl }
  template:
    metadata:
      labels: { app: mm-sysctl }
    spec:
      hostPID: true
      initContainers:
        - name: set
          image: busybox:1.36
          securityContext: { privileged: true }
          command: ["sysctl", "-w", "vm.max_map_count=1048576"]
      containers:
        - name: pause
          image: registry.k8s.io/pause:3.9
```

With the kubelet flag `--allowed-unsafe-sysctls=vm.max_map_count`, a pod-level `securityContext.sysctls` entry becomes legal instead — but that flag is cluster-wide and changes the threat model for every workload, so most operators prefer the DaemonSet or a node bootstrap template.

## Sizing the Value Instead of Guessing

Do not pick a number because a blog post said so. Derive it:

```bash
# worst observed mapping count across the whole host
peak=$(for p in $(ls /proc | grep '^[0-9]'); do wc -l < /proc/$p/maps 2>/dev/null; done | sort -rn | head -1)
echo "peak maps: $peak"
```

Then size to **4–8× the worst observed peak**, with a floor of 262,144 for search/cache workloads. Rationale: mapping counts scale with thread count and shard/part count, both of which grow with traffic and data, and hitting the ceiling is a hard, immediate failure rather than a graceful degradation. A value of 1,048,576 gives ~50× headroom over the 21,020-mapping process measured above, which is roomy but not absurd.

## Pitfalls and Migration Notes

- **`vm.max_map_count` is not namespaced.** A container cannot have its own value; `--sysctl` works only because the runtime writes the host value. Two containers wanting different values cannot both be satisfied.
- **`Out of memory` in a thread-creation error is not an OOM.** `pthread_create` returning `ENOMEM`/`EAGAIN` with plenty of free RAM is the mapping-ceiling signature. Check `wc -l /proc/$PID/maps` before you add memory.
- **The distro lottery is real.** Ubuntu 24.04 ships 1,048,576; Debian 12 and RHEL 8/9 ship 65,530. Container images cannot fix this because the limit comes from the host kernel. Document the required host value next to your compose file.
- **Raising the ceiling can hide a map leak.** Mappings from `dlopen` loops or repeated `mmap` without `munmap` grow monotonically. Sample the count twice a minute apart; if it only climbs, you have a leak, not a capacity problem.
- **`ulimits.memlock=-1` is a separate requirement** for search engines that want to lock the heap. Without it, `bootstrap.memory_lock` fails and the process may swap its index pages.
- **Changing `overcommit_memory` at runtime does not retroactively validate existing mappings.** Existing committed memory above the new limit stays allocated; the next allocation is the one that gets refused — which is why flipping to mode 2 during an incident makes it worse.
- **Huge pages change the arithmetic** — a 2 MB huge-page-backed buffer consumes one mapping per page-pair rather than per allocation, which can actually *reduce* map counts while increasing committed memory. See our [KSM and memory deduplication tuning guide](../2026-06-02-linux-kernel-ksm-tuning-ksm-uksm-ksmtuned-guide/) for the adjacent trade-offs.

For the memory-accounting side of the same debugging session — what is resident versus shared versus mapped — read [RSS vs PSS vs USS container memory accounting](../2026-11-22-rss-pss-uss-container-memory-accounting/), and for the process-limit side that produces the identical `EAGAIN` error from a completely different cause, see the [PID and thread exhaustion field guide](../2026-11-23-pid-thread-exhaustion-fork-storm-diagnosis/). Our [systemd, PAM and cgroup v2 resource limits guide](../2026-05-24-self-hosted-linux-process-resource-limits-systemd-pam-limits-cgroup-v2-guide/) covers the per-service knobs that sit above the kernel ones.

## FAQ

**What does `vm.max_map_count` actually limit?**
The number of distinct memory mappings (`vm_area_struct` entries) a single process may create, as listed in `/proc/<pid>/maps`. It limits count, not bytes — a process can have 20,000 mappings and use only a few hundred megabytes of resident memory.

**Why does the same container image work on Ubuntu and fail on Debian?**
Because the limit is a host kernel setting, not an image setting. Ubuntu 24.04 raised its default to 1,048,576 while Debian 12 and RHEL 8/9 still ship 65,530, so a search or cache container that maps thousands of index regions exhausts the ceiling on the older host and exits during bootstrap.

**Should I set `vm.overcommit_memory=1` to fix it?**
No — those are different knobs. `max_map_count` limits mapping count; `overcommit_memory` controls whether the kernel refuses allocations up front. Mode 0 (heuristic) is correct for general-purpose hosts, and switching to strict mode 2 on a machine whose `Committed_AS` already exceeds `CommitLimit` will cause allocation failures across every service.

**How do I find which process is close to the ceiling?**
Count lines in `/proc/<pid>/maps` for every process and sort descending. Then break one process down by mapping type with `awk` over `maps` to distinguish thread stacks, anonymous arenas, memory-mapped files and shared libraries — the dominant category tells you whether to cap threads, fix a leak, or raise the ceiling.

**Does `docker run --sysctl vm.max_map_count=...` really work?**
On Docker it writes the host value because the sysctl is not namespaced, so it "works" while affecting every process on the machine. On Kubernetes the `vm.*` family is classified as unsafe and is rejected unless the kubelet is started with `--allowed-unsafe-sysctls=vm.max_map_count` — which is why a node-level DaemonSet or bootstrap template is the usual production fix.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "vm.max_map_count in 2026: Why Search and Cache Containers Die at 65,530 Mappings",
  "description": "Why the same container image runs on Ubuntu and dies on Debian, with real mapping counts, overcommit math and the Kubernetes node-level fix.",
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
