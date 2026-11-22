---
title: "CPU Steal Time in 2026: Why Your VM Crawls While the Host Shows Idle Cores"
date: "2026-11-22"
tags: ["linux", "performance-tuning", "virtualization", "cloud", "troubleshooting"]
draft: false
description: "A practical guide to reading %steal correctly in KVM, VMware and burstable cloud instances, and telling it apart from iowait, cgroup throttling and PSI pressure."
---

You moved the service to a cloud VM and it got slower. Not catastrophically — just consistently 20-40% slower, with p99 latencies that wander. You check `top`: load average is low, CPU idle is 80%. You check disk: no wait. You check the app: same container image, same config.

The number you need is in a column most people scroll past. Here is `mpstat` output from a real 16-core bare-metal box:

```text
$ mpstat 1 1
20时02分44秒  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
20时02分44秒  all    8.11    0.00    1.20    0.00    0.00    0.06    0.00    0.00    0.00   90.62
```

`%steal = 0.00` on bare metal, always. On a contended hypervisor, that column is the difference between "my code is slow" and "my neighbour's code is stealing my cycles" — and **the host's own monitoring will never show it to you**, because from the host's perspective those cycles were delivered to a guest.

## TL;DR — Quick Verdict

- **`%steal` is the hypervisor taking CPU time away from your vCPU** while its run queue was non-empty. On bare metal it is structurally 0.00 and can never move.
- **Read it per-vCPU, not as an average.** `mpstat -P ALL 1` is mandatory: one pinned vCPU at 90% steal while the guest-level `all` row reads 5% is the single most common misdiagnosis.
- **If %steal is above 5% for sustained periods, you are overcommitted or on a noisy neighbour** — no guest-side tuning fixes it. Move the instance, pin the vCPU, or buy a dedicated/burstable-free class.
- **Steal is not iowait and not throttling.** iowait means *your* kernel is waiting on *your* disk. cgroup throttling means *you* set `cpu.max` too low. Only steal is someone else's fault.
- **On burstable instances (t3/t4g, E2 shared-core, B-series), credit exhaustion is reported as steal.** That is the tell-tale of a workload that outgrew its baseline.

## The Four Signals That All Mean "No CPU Available"

These four numbers get conflated constantly, and picking the wrong one sends you down a multi-day rabbit hole. They are mechanically unrelated.

| Signal | Read it with | Root cause | Who must fix it | Guest-side fix |
|---|---|---|---|---|
| `%steal` | `mpstat -P ALL 1`, `/proc/stat` field 8 | Hypervisor scheduled another vCPU on your physical core | Provider / host admin | None — migrate, pin, or resize |
| `%iowait` | `mpstat`, `vmstat` `wa` column | Your block device is slow; CPU idle waiting on I/O | You | Faster disk, fix `fsync` pattern |
| `nr_throttled` | `cpu.stat` in the cgroup | Your own `cpu.max` quota was exhausted mid-period | You | Raise `cpu.max`, add cores |
| PSI `some avg10` | `/proc/pressure/cpu` | Tasks runnable but no CPU available — the honest summary | You or host | Reduce runnable threads, or resize |

**PSI is the only one that measures the effect instead of the cause**, which makes it the best single number for alerting. The others tell you *why*.

## How Steal Is Accounted

`/proc/stat` line `cpu` has ten fields in a fixed order:

```text
user nice system idle iowait irq softirq steal guest guest_nice
```

Real output from the same box, plus a decoder that computes the percentage correctly:

```text
$ head -1 /proc/stat
cpu  3006969444 6162936 1128947017 31401104794 11565225 0 23474695 0 0 0

$ awk '/^cpu /{u=$2;n=$3;s=$4;i=$5;w=$6;q=$7;sq=$8;st=$9;t=u+n+s+i+w+q+sq+st; \
  printf "steal=%d total=%d steal_pct=%.4f%%\n",st,t,(t>0?st*100/t:0)}' /proc/stat
steal=0 total=35578224111 steal_pct=0.0000%
```

Three details that matter:

1. **`steal` is field 9 in awk terms, not field 8** — because `$1` is the literal string `cpu`. Off-by-one here is the most common scripting bug in this space.
2. **`guest` and `guest_nice` are already included in `user`/`nice`**, so you must *not* add them to the total or you double-count.
3. **Steal time only counts while your vCPU had runnable work.** An idle vCPU being preempted contributes nothing, which is why an overcommitted-but-idle VM looks perfectly healthy until you give it real load.

## The Per-vCPU Trap

This is where real incidents get misdiagnosed. Guest-level aggregation hides the problem:

```text
$ mpstat -P ALL 1
20时02分44秒  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %idle
20时02分44秒  all    8.11    0.00    1.20    0.00    0.00    0.06    0.00   90.62
20时02分44秒    0    3.03    0.00    0.00    0.00    0.00    1.01    0.00   95.96
20时02分44秒    3   60.00    0.00    7.00    0.00    0.00    0.00    0.00   33.00
```

On this bare-metal host every `%steal` is 0.00, as required. Now consider a 4-vCPU guest where vCPU 2 is co-scheduled with a noisy neighbour: `mpstat` without `-P ALL` reports `%steal` around 25% (the average), while vCPU 2 sits at 95-100%. A single-threaded service pinned to vCPU 2 loses almost all its throughput — and the average looked "not that bad".

**Rule: on any virtualized host, always run `mpstat -P ALL 1` and look at the maximum, not the mean.** For a service that runs one hot thread, the mean is a lie by construction.

On the host side (KVM), steal for a guest vCPU is the time the vCPU was runnable but not running. You can see it from the host with:

```bash
# Per-vCPU aggregate stats for a running guest
virsh domstats --vcpu --state <domain> | head -20

# Which physical CPUs the vCPUs are allowed on
virsh vcpupin <domain>
```

If two guests' vCPUs share the same physical core with no pinning and both are busy, steal is guaranteed by arithmetic, not by a bug.

## Burstable Instances: Steal as a Billing Mechanism

Cloud "burstable" or "shared-core" instance families do not have a fixed CPU allocation. They accumulate credits when idle and spend them when busy. When the credits run out, the hypervisor throttles you — **and in most cases that throttling is accounted as steal time inside the guest.**

| Family | Baseline | Credit mechanic | Steal appears when |
|---|---|---|---|
| AWS `t3`/`t4g` | 20-40% of vCPU | CPU credits, `CPUCreditBalance` metric | Balance hits zero |
| GCP `e2` shared-core | Fractional vCPU (e.g. 0.25) | Sustained-use discount, no credits | Bursting above the fractional share |
| Azure `B`-series | Percentage of vCPU | Credits, `CPU Credits Remaining` metric | Credits exhausted |

The operational lesson: **a steady-state workload must never run on a burstable class.** A cron-driven batch job that peaks for 20 minutes every hour is fine. A web service at 25% constant utilization will burn credits, fall back to baseline, and show 40-60% steal every afternoon — which looks exactly like a provider problem and is actually a capacity-planning problem.

Note that the provider's own metrics (`CPUCreditBalance`, `CPU Credits Remaining`) are the authoritative signal here. Guest-side steal tells you *that* you are being throttled; the cloud metric tells you *why*.

## Distinguishing Self-Inflicted Throttling from Steal

Before blaming the hypervisor, rule out the two things you did to yourself.

**1. cgroup CPU quota.** If a container or systemd unit has `cpu.max` set, exceeding it produces throttling, not steal:

```bash
# Inside the cgroup of your service — the numbers to compare
cat /sys/fs/cgroup/system.slice/myapp.service/cpu.stat
usage_usec 16219478930987
user_usec 7665675888859
system_usec 8553803042127
nr_periods 0
nr_throttled 0
throttled_usec 0
```

`nr_periods 0` means no quota is configured, so throttling is structurally impossible here — exactly what you want to see on a host where CPU is not the constraint. On a throttled service you will instead see `nr_throttled` climbing as a fraction of `nr_periods`, and `throttled_usec` growing. **A useful ratio: `nr_throttled / nr_periods` above 5% is real, measurable throughput loss** — the fix is raising `cpu.max`, not calling the provider.

**2. cpu pressure.** PSI separates "no CPU available" from "CPU is busy":

```text
$ cat /proc/pressure/cpu
some avg10=0.40 avg60=0.66 avg300=0.20 total=459019747301
full avg10=0.00 avg60=0.00 avg300=0.00 total=0
```

`some` counts time when at least one task was stalled waiting for CPU. On this host `avg300=0.20` — essentially nothing queued. **If `some avg10` is above 10 while `%usr` is low and `%steal` is high, you have proof of a steal problem rather than a workload problem**, because your own code is not the one consuming the cycles.

## What You Can Actually Do About It

Nothing in the guest can recover stolen cycles. What you can change:

1. **Move to a non-burstable class** with dedicated vCPU (e.g. `m6i`/`c6i`-style fixed-performance families, or dedicated-host tenancy). This is the only real fix for steady-state load.
2. **Reduce vCPU count and pick faster cores.** For a single-threaded service, 2 fast vCPUs beat 8 overcommitted ones. Fewer vCPUs also means fewer co-scheduling constraints on the host, which reduces steal *by itself*.
3. **On a host you control, pin vCPUs to physical cores.** `virsh vcpupin <domain> 2 5` binds vCPU 2 to physical CPU 5 and removes the co-scheduling lottery. Combine with `emulatorpin` for the I/O threads.
4. **Make the workload steal-tolerant.** If the service must run on shared hardware, ensure the thread pool is smaller than the guaranteed CPU share, so the scheduler never queues work it cannot run.
5. **Alert on `%steal`, not on host CPU.** Provider dashboards show host-level utilization, which is often 40% while individual guests are starving.

If you are diagnosing why a *specific thread* is losing time rather than where the cycles went, the [performance profiling toolchain](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) will show run-queue delay per thread. If you control the host and want to remove the scheduler's freedom entirely, our guides to [CPU shares, nice and cpuset](../2026-11-21-cpu-scheduling-mixed-workloads-nice-cgroups-cpuset/) and [CPU affinity with taskset and numactl](../2026-05-23-self-hosted-linux-cpu-affinity-management-taskset-numactl-cset-guide/) cover the guest-side levers in depth.

## The Five Mistakes That Cost Real Money

1. **Reading only the `all` row.** Averages hide single-vCPU starvation. `mpstat -P ALL` or nothing.
2. **Confusing steal with iowait.** They are often both present (a starved vCPU also delays I/O completion), so people raise IOPS on a CPU-contention problem. Check `%steal` before touching disks.
3. **Treating `%steal` as a provider SLA violation at 2%.** Baseline steal of 1-3% is normal on shared infrastructure. Sustained >5%, or any spike above 20% correlated with latency, is worth escalating.
4. **Ignoring the guest clock.** Heavy steal also causes time drift, because the guest's virtual clock advances while its vCPU is descheduled. If you also see NTP corrections and log timestamp gaps, steal is the likely root cause.
5. **Benchmarking on a laptop and sizing the cloud instance from that number.** Bare metal has no steal by definition. A 16-core laptop result does not translate to a 4-vCPU burstable instance, and the gap is partly steal, partly memory bandwidth, partly noisy-neighbour cache pressure.

## FAQ

**How much CPU steal is normal in the cloud?**
Under 1-2% sustained is typical and harmless on shared infrastructure. Between 2-5% you should be watching it. Above 5% sustained, or spikes above 20% that correlate with latency, mean your vCPUs are contending for physical cores and the instance class is wrong for the workload.

**Can steal time be caused by my own process?**
No. Steal is time your vCPU was runnable but the hypervisor gave the physical core to something else — another guest or the host itself. If your own process is the problem, you will see high `%usr`, a growing run queue, or `nr_throttled` increasing in `cpu.stat`, not steal.

**Why is `%steal` always exactly 0.00 on my server?**
Because it is running on bare metal, where there is no hypervisor to preempt you. The field exists in `/proc/stat` on every kernel but can only be incremented by a hypervisor. Consistent 0.00 plus a physical DMI vendor string is strong evidence you are not virtualized.

**My container is being throttled but `%steal` is zero. What is happening?**
That is cgroup CPU quota, not steal. Check `cpu.stat` in the container's cgroup: `nr_throttled` and `throttled_usec` will be climbing. Raise `cpu.max` (or the Kubernetes `limits.cpu` value, which translates directly into a quota) and the throttling disappears. Steal and throttling are unrelated mechanisms that both present as "my service got slower".

**Does adding vCPUs fix a steal problem?**
Usually not, and it can make it worse. More vCPUs means more co-scheduling constraints on the host, so a guest with 16 vCPUs on an overcommitted host often sees *higher* steal per vCPU than one with 4. Fix the instance class first; add vCPUs only after steal is under control.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CPU Steal Time in 2026: Why Your VM Crawls While the Host Shows Idle Cores",
  "description": "How to read %steal per vCPU in KVM, VMware and burstable cloud instances, and tell steal apart from iowait, cgroup throttling and PSI pressure.",
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
