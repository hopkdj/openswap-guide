---
title: "CPU Shares, nice and cpuset in 2026: Scheduling Mixed Workloads on One Linux Host"
date: "2026-11-21"
tags: ["linux", "systemd", "performance", "cgroups", "scheduling", "observability"]
draft: false
description: "How to stop batch jobs from starving latency-sensitive services on a shared Linux host: a practical comparison of nice, chrt, cgroup v2 cpu.weight, cpu.max, cpuset and systemd CPU controls, with the exact commands and the pitfalls that make them silently ineffective."
---

A nightly compression job starts at 02:00, the API's p99 latency jumps from 40 ms to 900 ms, and `uptime` reports a load average of 38 on a 16-core box. Nothing is broken. Nothing is leaking. Two workloads are simply competing for the same cores, and the kernel is being perfectly fair — which is exactly the problem, because **fairness is not the same as priority**.

Linux offers at least six mechanisms for influencing who gets CPU time, and they are not interchangeable. `nice` adjusts a per-process weight. `chrt` changes the scheduling class. cgroup v2 `cpu.weight` sets a proportional share for a *group*. `cpu.max` imposes a hard bandwidth ceiling. `cpuset` decides which cores a group may run on at all. And systemd wraps four of them into unit directives that many administrators never touch.

Getting this wrong produces two failure modes: a background job that starves production traffic, or a quota so tight that a healthy service gets throttled into latency spikes. This guide covers the mechanisms, the arithmetic, and the verification commands.

## TL;DR: the 60-second verdict

- **A systemd service that must never starve** → set `CPUWeight=1000` on it and drop the noisy neighbour to `CPUWeight=10`. Proportional shares, no hard cap, no idle waste.
- **A batch job that must not exceed a fixed budget** → `CPUQuota=200%` (two full cores). Hard ceiling, predictable capacity planning.
- **A latency-critical process that must not be preempted** → `chrt -f 50` **only** with a dedicated cpuset (`AllowedCPUs=`), otherwise you risk stalling the whole box.
- **A container** → `--cpu-shares` maps to `cpu.weight`; `--cpus` maps to `cpu.max`. In Kubernetes, `requests.cpu` becomes weight and `limits.cpu` becomes quota — and the ratio between them is what protects your latency.
- **`nice` alone is the weakest tool available.** On a systemd host it is usually applied to the wrong process, in the wrong group, at the wrong time. Use it for ad-hoc shell work, not for service policy.

## The six mechanisms, compared honestly

| Mechanism | Scope | Type | Range / units | Survives restart | Composable with others |
|---|---|---|---|---|---|
| `nice` / `renice` | Single process (and children) | Proportional weight | −20 … +19 | No | Yes, but overridden by cgroup weights in v2 |
| `chrt` | Single process | Scheduling class | FIFO 1–99, RR 1–99, BATCH, IDLE, DEADLINE | No | Yes — class is orthogonal to weight |
| cgroup v2 `cpu.weight` | Group | Proportional share | 1 … 10000 (default 100) | Depends on manager | Yes, it is the base layer |
| cgroup v2 `cpu.max` | Group | Hard bandwidth cap | `quota period`, e.g. `200000 100000` | Depends on manager | Yes — combines with weight |
| cgroup v2 `cpuset.cpus` | Group | Core affinity (exclusive possible) | CPU list, e.g. `0-3,8-11` | Depends on manager | Yes — restricts where the group may run |
| systemd `CPUWeight` / `CPUQuota` / `AllowedCPUs` | Unit or slice | Policy wrapper | Weight 1–10000, quota as `%` | Yes | Yes — maps onto the cgroup files above |

The key mental model: **weight decides who wins when cores are oversubscribed; quota decides how much a group can ever use; cpuset decides where it may run.** They answer three different questions, and production hosts usually need weight plus cpuset, with quota reserved for cost control.

## Decision matrix

| Situation | Use | Why |
|---|---|---|
| API + nightly batch on the same host | `CPUWeight=1000` on the API unit, `CPUWeight=10` on the batch unit | The batch job still uses idle capacity, but yields instantly under load |
| Customer-facing service must be capacity-capped per tenant | `CPUQuota=` per slice | Hard, auditable ceiling; enables overcommit planning |
| Video transcoder that must never touch the API's cores | `AllowedCPUs=8-15` on the transcoder, `AllowedCPUs=0-7` on the API | Physical isolation; removes contention instead of arbitrating it |
| Trading/telemetry pipeline needing sub-millisecond jitter | `chrt -f` + `AllowedCPUs=` + `IRQAffinity=` | FIFO class removes CFS preemption; the cpuset keeps RT from starving the kernel |
| Ad-hoc `rsync` or `tar` on a production host | `nice -n 19 ionice -c3` | Cheap, no configuration, good enough for one-off work |
| Container platform with noisy neighbours | `--cpu-shares` (weight) + `--cpus` (quota) | Matches Kubernetes semantics; avoids the classic "limit equals request" trap |

## How proportional shares actually compute

cgroup v2 replaced `cpu.shares` with `cpu.weight`, and the mapping is not linear at the low end. Weight 100 is the default; the kernel converts weight to a share of the CFS runqueue using a lookup table so that small weights still receive a usable minimum slice.

The practical arithmetic for two competing groups is a simple ratio of weights:

```bash
# Group A: CPUWeight=800   Group B: CPUWeight=200
# Under full contention: A gets 800/(800+200) = 80%, B gets 20%
# With A idle: B gets 100% — weights never waste capacity
```

That last line is the reason to prefer weights over quotas for services. A quota of 80% leaves 20% unusable when the service is idle; a weight of 800 lets a neighbour consume everything during quiet periods and still guarantees the ratio under contention.

```bash
# Inspect the live values for a unit
systemctl show nginx -p CPUWeight -p CPUQuotaPerSecUSec -p AllowedCPUs -p Nice

# The cgroup files themselves (cgroup v2, unified hierarchy)
cat /sys/fs/cgroup/system.slice/nginx.service/cpu.weight
cat /sys/fs/cgroup/system.slice/nginx.service/cpu.max
cat /sys/fs/cgroup/system.slice/nginx.service/cpuset.cpus.effective

# Live per-slice CPU consumption — the fastest way to see who is winning
systemd-cgtop -m --depth=2
```

`systemd-cgtop` is the most underrated tool in this area. In one screen it shows CPU, memory and I/O per unit and slice, which immediately reveals whether your weights are doing anything at all.

## systemd: the four directives that matter

```ini
# /etc/systemd/system/api.service.d/priority.conf
[Service]
# Proportional share: 10x the default of 100
CPUWeight=1000
# Optional hard cap: 400% = 4 full cores regardless of idle capacity
CPUQuota=400%
# Accounting period for the quota (default 100ms; raise for bursty workloads)
CPUQuotaPeriodSec=100ms
# Pin to specific cores instead of arbitrating
AllowedCPUs=0-7
# Also pin IRQs handled by this unit's devices away from those cores
# (set manually via /proc/irq/*/smp_affinity_list — see below)
Nice=-5
```

```bash
systemctl daemon-reload && systemctl restart api
systemctl show api -p CPUWeight -p CPUQuotaPerSecUSec -p AllowedCPUs
```

Two semantics worth memorizing. `CPUQuota=200%` means **two cores**, not "twice as much as before" — percentages are relative to a single core. And `CPUWeight` only matters when the parent slice is contended: if the API and the batch job live in *different* slices with different weights, the slice-level weight dominates the per-unit weight, because cgroup v2 distributes CPU hierarchically, level by level.

That hierarchy is the single most common reason "weights did nothing". A unit's effective share is the product of its share within its parent slice and the parent slice's share of the root. Check the tree before tuning the leaves:

```bash
systemd-cgls --unit api.service
cat /sys/fs/cgroup/system.slice/cpu.weight
```

## Quotas: when they help and how they hurt

A quota is enforced by the CFS bandwidth controller: each group gets `quota` microseconds of runtime per `period` microseconds. When the group exhausts its quota it is **throttled until the next period**, no matter how many cores are idle.

```bash
# 1.5 cores, 100ms period
echo "150000 100000" > /sys/fs/cgroup/myslice/cpu.max

# Watch throttling happen — this counter is the ground truth
grep -E "throttled" /sys/fs/cgroup/myslice/cpu.stat
# nr_throttled 14822
# throttled_usec 912004411
```

If `nr_throttled` climbs while latency spikes, the quota is too tight for the workload's burst pattern. Two fixes work: raise the quota, or lengthen the period so short bursts can be absorbed.

```ini
# systemd equivalent, with a longer accounting period for bursty services
[Service]
CPUQuota=150%
CPUQuotaPeriodSec=250ms
```

For most services, the right configuration is **no quota at all** and a weight instead, with quotas reserved for multi-tenant isolation or chargeback. Quotas turn a scheduling preference into a hard failure mode, and throttling shows up as latency, not as an error — which makes it hard to diagnose after the fact.

## nice, autogroup, and why it disappoints

`nice` adjusts a task's weight inside the CFS class. Values range from −20 (most favourable) to +19 (least), and **only root can lower the value** (raise priority).

```bash
nice -n 19 tar --zstd -cf /backup/archive.tar.zst /srv/data
renice -n 10 -p 4242
```

The catch is autogroup. The kernel's `sched_autogroup` feature groups tasks by session (TTY), and CFS then schedules *groups* rather than individual tasks. On a machine with autogroup enabled, `nice` on one process inside a session can have far less effect than expected, because the whole session competes as a unit.

```bash
# Check autogroup state (1 = enabled, typical on desktop kernels)
cat /proc/sys/kernel/sched_autogroup_enabled

# Per-process autogroup id
cat /proc/4242/autogroup
```

On servers, the practical conclusion is that `nice` is fine for interactive one-offs, but it is the wrong layer for durable service policy. systemd's `Nice=` directive is more reliable than a shell `nice` because it applies at exec time to the exact service process, but it still acts on a single task, not a workload — which is why `CPUWeight` is the better answer for a multi-process service such as a forking web server.

## Real-time scheduling without taking down the host

`SCHED_FIFO` and `SCHED_RR` bypass CFS entirely: a runnable FIFO task runs until it blocks or a higher-priority RT task preempts it. A busy loop at `chrt -f 99` on a shared host will make the box unreachable.

```bash
# Prioritize a latency-sensitive worker, but see the caveats below
chrt -f 50 /usr/local/bin/telemetry-agent

# Check the class and priority of a running task
chrt -p 4242
```

Two safety mechanisms exist, and both must be respected:

1. **RT throttling.** `sched_rt_runtime_us` (default 950000 of a 1000000 µs period) reserves 5% of each period for non-RT tasks. Do not disable it. If your RT workload needs more than 95% of a core, it needs its own core.
2. **CPU isolation.** Pin RT workloads with `cpuset` and move interrupts off those cores:

```bash
# Isolate cores 12-15 for the RT workload from boot
# /etc/default/grub: GRUB_CMDLINE_LINUX="isolcpus=12-15 nohz_full=12-15 rcu_nocbs=12-15"

# Keep IRQs off the isolated cores
for irq in /proc/irq/*/smp_affinity_list; do echo 0-11 > "$irq" 2>/dev/null; done

# systemd: restrict the unit to the isolated cores
systemctl set-property telemetry.service AllowedCPUs=12-15
```

`AllowedCPUs=` writes `cpuset.cpus`, which is stricter than affinity: children inherit it and the scheduler will not migrate the group outside the set. `CPUAffinity=` sets the initial affinity mask but permits later changes by the process. Use `AllowedCPUs` when isolation is a correctness requirement.

## Containers and Kubernetes

Docker's flags map directly onto the cgroup files:

```bash
docker run -d --cpu-shares 1024 --cpus 2 nginx:alpine
# --cpu-shares -> cpu.weight (relative, no cap)
# --cpus 2     -> cpu.max = "200000 100000" (hard cap)
```

```yaml
# Compose equivalent
services:
  api:
    image: myorg/api:2026.11
    cpu_shares: 1024
    cpus: 2.0
    cpuset: "0-7"
```

In Kubernetes the mapping is subtler and it is where most latency incidents originate:

| Kubernetes field | cgroup v2 effect | Behaviour |
|---|---|---|
| `requests.cpu: 500m` | `cpu.weight` proportional to 500 | Guaranteed share under contention |
| `limits.cpu: 2000m` | `cpu.max` = 2 cores | Hard throttle at 2 cores |
| Both set, ratio 1:4 | weight from request, quota from limit | Burst up to 4×, guaranteed 1× |
| Only limits set | quota, default weight | Burstable pods with equal weight — noisy neighbour risk |

Setting only `limits.cpu` gives every pod the default weight, so two pods with 2-core limits and identical weight split available CPU evenly — even if one is a batch worker and the other serves user traffic. **Always set requests**, and make the request reflect real need rather than a copy of the limit.

## Verification: proving the settings took effect

```bash
# 1. What does systemd think the unit's policy is?
systemctl show api -p CPUWeight -p CPUQuotaPerSecUSec -p AllowedCPUs -p Nice

# 2. What does the kernel actually enforce?
CG=/sys/fs/cgroup/system.slice/api.service
cat $CG/cpu.weight $CG/cpu.max $CG/cpuset.cpus.effective

# 3. Is the workload being throttled?
grep -E "nr_throttled|throttled_usec" $CG/cpu.stat

# 4. Who is actually consuming CPU, per slice?
systemd-cgtop -m --depth=2

# 5. Per-thread scheduling class, for RT debugging
ps -eLo pid,tid,cls,rtprio,ni,comm | awk '$3 != "TS"'
```

The `ps` format above uses `cls` and `rtprio`, which is the fastest way to find a stray FIFO thread. `cls` values are `TS` (other), `FF` (FIFO), `RR` (round-robin), `B` (batch), `IDL` (idle) and `DLN` (deadline).

## Pitfalls that make tuning silently useless

- **Tuning a unit whose parent slice is the real bottleneck.** Effective share is hierarchical. Fix the slice weight first.
- **Setting `CPUQuota` and calling it priority.** A quota caps; it does not prioritize. Under contention, a capped group still loses to an uncapped one with a higher weight.
- **`CPUQuota=100%` on a multi-threaded service.** That is one core. Threads will queue behind the quota and latency will spike at every period boundary.
- **Using `nice` on a systemd service from a shell.** The shell's `nice` affects the shell. Use `Nice=` in the unit, or `systemctl set-property api.service Nice=-5`.
- **Setting `chrt -f` without a cpuset.** One infinite loop and the host needs a hard reset. Always isolate RT workloads.
- **Disabling RT throttling.** `sched_rt_runtime_us=-1` removes the kernel's safety valve and turns a bug into an outage.
- **Forgetting IRQ affinity.** Pinning a latency-sensitive process to core 3 while the NIC queue for that process also lands on core 3 reintroduces the jitter you removed.
- **Expecting `CPUAffinity=` to prevent migration of children.** It sets the affinity mask; `AllowedCPUs=` (cpuset) is the enforcing version.
- **Ignoring `cpu.stat` after a change.** Without the throttle counters you cannot distinguish "quota too tight" from "workload grew".

## A configuration that works for the common case

```ini
# /etc/systemd/system/api.service.d/10-priority.conf
[Service]
CPUWeight=1000
AllowedCPUs=0-7
Nice=-5
```

```ini
# /etc/systemd/system/nightly-batch.service.d/10-priority.conf
[Service]
CPUWeight=10
AllowedCPUs=8-15
Nice=19
IOSchedulingClass=idle
```

This gives the API physical isolation from the batch job, a 100:1 weight advantage if they ever share cores (for example after a CPU hotplug or a cpuset fallback), and no hard caps that could throttle either workload into a latency cliff. It is boring, and boring is what a production scheduler should be.

Related reading on this site: the [kernel sysctl and tuned guide](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) covers the global knobs that sit above cgroup policy, the [OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd-oomd-psi-guide/) explains how memory pressure interacts with CPU starvation and PSI, and the [block I/O latency tracing walkthrough](../2026-05-24-self-hosted-block-io-latency-tracing-blktrace-vs-ioping-vs-iotop-guide/) is the right next step when latency spikes turn out to be I/O waits rather than scheduling.

## FAQ

**Is `CPUWeight` the same as CPU shares in cgroup v1?**
Functionally yes, but the numbers differ. cgroup v1 used `cpu.shares` with a default of 1024 and a range up to 262144. cgroup v2 uses `cpu.weight` with a default of 100 and a range of 1–10000, mapped through a kernel table so small values still receive usable time. systemd's `CPUWeight=` writes the v2 file.

**Why did raising `CPUWeight` change nothing?**
Three usual causes: the group is not actually contended (weights only matter under oversubscription), the parent slice has a low weight so the unit's share within it is capped hierarchically, or the workload is being throttled by `cpu.max` so weight cannot help. Check `cpu.stat` and the slice tree before changing numbers again.

**Should I use `CPUQuota` or `CPUWeight` for a background job?**
Use `CPUWeight` if you want the job to consume all idle capacity and yield under load. Use `CPUQuota` only when you need a hard, auditable ceiling for capacity planning or tenant isolation. Quotas waste idle capacity and introduce throttling latency; weights never waste capacity but cannot guarantee an upper bound.

**Does `nice` still matter on a cgroup v2 system?**
Inside a single cgroup it still orders tasks relative to each other, and `Nice=` in a unit is applied reliably at exec time. Across groups, `cpu.weight` dominates because CFS schedules groups hierarchically. For durable service policy, prefer weights; keep `nice` for ad-hoc shell commands.

**How do I give one process real-time priority without risking the host?**
Pin it to isolated cores first (`isolcpus=` at boot, `AllowedCPUs=` in the unit, IRQs moved away), then apply `chrt -f` with a modest priority. Leave `sched_rt_runtime_us` at its default so the kernel reserves headroom for non-RT work, and monitor `cpu.stat` plus the RT throttling counters in `/proc/sys/kernel/sched_rt_*`.

**What is the Kubernetes equivalent of `nice`?**
There is none, and that is deliberate. Kubernetes expresses priority through `requests.cpu` (which becomes weight) and QoS classes. Guaranteed pods (requests equal limits) get the most predictable treatment; BestEffort pods (no requests or limits) are the first to be squeezed. Use PriorityClass for preemption, not for share ratios.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CPU Shares, nice and cpuset in 2026: Scheduling Mixed Workloads on One Linux Host",
  "description": "Practical comparison of Linux CPU scheduling controls: nice, chrt real-time classes, cgroup v2 cpu.weight and cpu.max, cpuset isolation, and systemd CPUWeight, CPUQuota and AllowedCPUs directives, with verification commands and common misconfigurations.",
  "datePublished": "2026-11-21",
  "dateModified": "2026-11-21",
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
