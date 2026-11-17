---
title: "CXL Memory Expansion in 2026: cxl-cli vs memtierd vs Kernel Auto-Tiering"
date: "2026-11-17"
tags: ["cxl", "memory", "numa", "linux", "performance", "self-hosted"]
draft: false
---

Your database fits in 512 GB of RAM. Your budget does not. That gap — not CPU, not storage — is what decides how many tenants you can pack onto a node in 2026, and it is why CXL memory expansion went from conference-talk curiosity to a line item in server refresh plans. A CXL Type-3 memory device lets you attach DRAM outside the CPU's local memory channels: more capacity per socket, at a latency between local DRAM and NVMe, over a cache-coherent link.

The hard part was never the hardware. It is that **capacity you cannot place, measure, or migrate is capacity you cannot use**. A CXL expander shows up as a new NUMA node with no CPUs, and every byte your application touches there costs extra latency. Getting that right on Linux means choosing among three genuinely different control planes:

- **cxl-cli** — the kernel's own management interface, from the ndctl project, for assembling devices into regions and turning them into usable memory
- **memtierd** — a userspace daemon that tracks page access and actively moves hot pages back to local DRAM
- **kernel-native tiering** — NUMA balancing plus memory demotion, doing a coarser version of the same job with no daemon at all

This guide compares all three with real commands and real configuration, and tells you which one to run for which workload.

## TL;DR — Quick Verdict

**Start with cxl-cli. It is not optional.** No matter which tiering strategy you pick, `cxl-cli` is how the region gets created and how the memory becomes addressable. Skipping it means you own a very expensive PCIe heater.

**Add memtierd only if you have a latency-sensitive workload whose hot set is much smaller than total capacity.** It promotes and demotes at a granularity the kernel does not attempt, and it can be scoped to specific cgroups so one noisy tenant does not drag the whole node into thrash.

**Rely on kernel auto-tiering when you want zero moving parts and your workload tolerates p99 variance.** It is already there, it needs one sysfs flag, and it will quietly do a decent job — at a granularity that will not rescue a latency-critical service.

## Side-by-Side Comparison

| Dimension | cxl-cli (ndctl) | memtierd | Kernel auto-tiering |
|---|---|---|---|
| What it actually does | Creates/enables CXL regions, converts them to system RAM | Tracks page access and migrates pages between NUMA nodes | Demotes cold pages, NUMA balancing migrates hot ones |
| Runs as | CLI, one-shot or scripted | Long-running daemon | Kernel thread, always available |
| Unit of control | Device, decoder, region | Process / cgroup / address range | Task and page, system-wide |
| Scope granularity | Hardware topology | Per-cgroup or per-PID policies | Global policy |
| Latency awareness | None — it just maps capacity | Explicit: idle threshold, promotion/demotion bands | Implicit, sampling-based |
| Operational cost | Scripted provisioning, needs root, topology-aware | Extra daemon, policy tuning, memory overhead for tracking | Essentially zero |
| Failure mode | Misconfigured interleave → unusable or slow region | Over-aggressive migration → bandwidth burn | Thrash under working sets larger than local DRAM |
| Project activity | ndctl v85 (June 2026), 332 stars, pushed this month | 42 stars, Go, last push June 2026 | In-tree, tracks the kernel |
| Best for | Everyone with CXL hardware | Multi-tenant DBs, caches, JVM heaps with cold tails | General-purpose nodes, batch, mixed workloads |

## Decision Matrix: Pick in Ten Seconds

| Your situation | Use | Why |
|---|---|---|
| Brand-new CXL hardware, nothing configured | **cxl-cli** | Regions must be assembled before any memory exists |
| Postgres/MySQL node where the working set is 30% of total | **cxl-cli + memtierd** | Keep hot pages local, park the cold tail on the expander |
| Batch analytics, latency SLO measured in minutes | **cxl-cli + kernel tiering** | One sysfs flag, no daemon to babysit |
| Multi-tenant node with per-tenant SLOs | **memtierd with cgroup policies** | Per-cgroup control beats global heuristics |
| You want to test tiering behaviour without hardware | **cxl-cli on QEMU CXL + emulated NUMA** | Reproduces topology and latency classes |
| You inherited a node where `numactl -H` shows a CPU-less node | **Kernel tiering first** | The memory is already there; tune before adding daemons |

## cxl-cli: Assembling Capacity Before You Can Use It

`cxl-cli` ships with ndctl (v85 as of June 2026, C, 332 stars, actively pushed) and talks to the kernel's CXL subsystem. It does not tier anything. It builds the memory.

The provisioning sequence is: find the memory devices, create a region across them, confirm the region enabled, then hand the resulting DAX device to `daxctl` so the kernel can expose it as system RAM.

```bash
# 1. What memory devices exist, and what state are they in?
sudo cxl list --memdevs

# 2. Which regions already exist?
sudo cxl list --regions

# 3. Interleave two memdevs across a root decoder, 1 KiB granularity
sudo cxl create-region -m -d decoder0.1 -w 2 -g 1024 mem0 mem1
```

The real output of a successful create looks like this — note that interleave parameters are echoed back, which is your proof the kernel accepted the topology you asked for:

```json
{
  "region": "region0",
  "resource": "0xc90000000",
  "size": "512.00 MiB (536.87 MB)",
  "interleave_ways": 2,
  "interleave_granularity": 1024,
  "mappings": [
    { "position": 1, "decoder": "decoder4.0" },
    { "position": 0, "decoder": "decoder3.0" }
  ]
}
created 1 region
```

Read those fields before you celebrate. `interleave_ways` must equal the number of memdevs you named, and `interleave_granularity` is a performance decision, not a formatting detail: small granularity spreads each access across devices and can help bandwidth on uniform traffic, while large granularity keeps related accesses on one device. Getting this wrong does not produce an error — it produces a region that works and quietly underperforms, which is far worse to debug.

Then convert the region's DAX device into memory the scheduler can allocate from:

```bash
# Region shows up as dax0.0; reconfigure it as system-ram
sudo daxctl reconfigure-device --mode=system-ram --movable dax0.0

# Verify: the new node has memory but no CPUs, which is expected for CXL
numactl --hardware
```

That CPU-less node is the whole point and the whole problem. It has capacity. It has no compute. Every allocation placed there is a remote access, and the kernel's default NUMA policy will happily put things there and hurt you.

One more distinction worth internalizing: **volatile versus persistent regions**. Volatile regions behave as traditional memory that disappears on power loss. Persistent regions are byte-addressable storage that survives. Most capacity-expansion deployments want volatile; the tooling flags overlap enough that teams have built persistent regions by accident and then wondered why `daxctl` behaved unexpectedly.

## memtierd: Moving Hot Pages Back Where They Belong

memtierd (Go, 42 stars, last push June 2026) is a userspace daemon that answers a question the kernel answers crudely: *which pages are hot enough to deserve local DRAM?*

Its architecture is a pipeline: a **pidwatcher** finds the processes to manage, a **tracker** observes access (idle page flag, soft-dirty bits, or DAMON), a **policy** classifies pages, and a **mover** performs migration or swap-out. Every stage is configurable, which is either the feature you need or the complexity you will regret.

A real configuration — this is the project's own age/idlepage tracking sample, trimmed to the parts that matter:

```yaml
policy:
  name: age
  config: |
    intervalms: 2000

    # Only manage processes inside this cgroup, not the whole node
    pidwatcher:
      name: cgroups
      config: |
        cgroups:
          - /sys/fs/cgroup/track-me

    tracker:
      name: idlepage
      config: |
        pagesinregion: 512
        maxcountperregion: 1
        scanintervalms: 2000
```

Run it in automatic mode with that file, or in command mode when you need to poke at a single process:

```bash
sudo memtierd -config /etc/memtierd/db-tier.yaml

# Interactive: check statistics, then force a specific process to node 1
echo "stats" | sudo memtierd -prompt
sudo memtierd -prompt <<< "pages -pid $(pgrep -f postgres); mover -pages-to 1"
```

The policy choice matters more than the tuning. The `age` and `heat` policies maintain access history and can both promote and demote, at the cost of memory to hold that history. The `demote-idle` policy is the cheap one: it reads the kernel idle page flag, demotes pages still idle since the last round, and supports **demotion only** — no promotion. That makes it suitable for very large page populations where tracking memory would otherwise compete with the workload. If your problem is "the cold tail is wasting expensive DRAM," `demote-idle` is often enough. If your problem is "the hot set keeps drifting," you need `age` or `heat`.

Two operational realities. First, memtierd can swap memory out as well as move it between nodes, which means a bad policy can turn a capacity problem into an I/O problem — watch swap-in rates, not just migration counts. Second, because tracking granularity is deliberately coarser than a page, do not expect per-page perfection; you are steering a distribution, not editing a page table.

## Kernel Auto-Tiering: One Flag, Zero Daemons

Linux has memory tiering built in, and for a large class of workloads it is genuinely sufficient. Two mechanisms cooperate: **NUMA balancing** migrates pages toward the node where they are being accessed, and **demotion** pushes cold pages down to slower tiers when local memory fills.

Enable demotion and confirm the memory tiers the kernel detected:

```bash
# Demotion is opt-in
echo 1 | sudo tee /sys/kernel/mm/numa/demotion_enabled

# What the kernel thinks your topology is
cat /sys/devices/system/node/node*/distance
numastat -m
```

The trade you are making is granularity for simplicity. NUMA balancing samples and unmaps pages to detect access patterns; it converges over seconds, not milliseconds, and it is not aware that your latency SLO is 2 ms. Under a working set substantially larger than local DRAM, you get migration churn — pages promoted and demoted repeatedly — and the node spends bandwidth moving data instead of serving it. The classic symptom is that average latency looks fine while p99 gets worse the longer the node runs.

Where kernel tiering wins decisively is operability. Nothing to install, nothing to keep alive, no policy file to drift out of sync with reality, and it survives kernel upgrades because it *is* the kernel. For batch jobs, build farms, and mixed workloads that merely need capacity, that is the right answer.

## Pitfalls That Cost Real Outages

**Never let the scheduler place latency-critical allocations on a CPU-less node by default.** Set an explicit policy for the services that matter — bind them to local nodes with `numactl --cpunodebind=0 --membind=0` — and let only the capacity-hungry, latency-tolerant processes spill.

**Do not size the tier by total capacity.** Size it by hot-set size. If your hot set is 200 GB and you bolt on 1 TB of CXL, you have bought a migration storm, not headroom.

**Interleave granularity is a benchmark, not a guess.** Run your actual workload at 256 B, 1 KiB, and 4 KiB granularity on a scratch region before production. The difference is workload-specific and larger than most people expect.

**One region per purpose beats one giant region.** Regions are the unit of failure and reconfiguration; a single region spanning every memdev means a single mistake takes all capacity offline.

**Measure the remote-node penalty on your own silicon.** CXL latency depends on the link, the switch topology, and the device — published numbers are directional only. A simple `numactl --membind=1` versus `--membind=0` comparison on your access pattern gives you the number that actually governs your placement decisions.

**Keep `cxl list` output in monitoring.** A region that silently drops out of `cxl list --regions` after a firmware event looks exactly like a memory leak from the application's point of view.

For adjacent layers, our [persistent memory comparison covering ndctl, PMDK and memkind](../2026-05-25-linux-persistent-memory-management-ndctl-vs-pmdk-vs-memkind-guide/) explains where byte-addressable media still fits alongside CXL, the [hugepages and numactl tuning guide](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/) covers the local-memory side of the same placement problem, and [GPU sharing with HAMi, MIG and DRA](../2026-11-17-gpu-sharing-kubernetes-hami-mig-dra-guide/) is worth reading if you are partitioning accelerators and memory on the same nodes.

## FAQ

### Do I need memtierd if the kernel already does memory tiering?

No, and you should not start there. Kernel demotion plus NUMA balancing costs one sysfs write and no daemon. Add memtierd when you can measure that kernel-tiering churn is hurting you — typically a latency-sensitive service whose hot set is a fraction of total capacity, or a multi-tenant node where you need per-cgroup control.

### Is CXL memory as fast as local DRAM?

No. It is coherent and byte-addressable, but every access crosses the link, so latency is higher than local DRAM and far lower than NVMe. Treat it as a distinct tier: excellent for capacity and cold data, poor for latency-critical hot paths. Measure the delta on your own hardware rather than trusting vendor charts.

### Why does `numactl --hardware` show a node with no CPUs?

That is normal for CXL memory expansion. The memory device attaches as a NUMA node without processors, so allocations there are always remote relative to every CPU. Your job is to control which processes are allowed to allocate there.

### Can I use cxl-cli without CXL hardware?

You can exercise the tooling against emulated CXL topology in QEMU, which is the standard way to validate provisioning scripts before hardware arrives. The commands and region semantics are the same; latencies and performance conclusions are not transferable.

### What happens if I skip region creation entirely?

The memory device remains visible to the kernel but contributes no usable capacity. Teams frequently install the hardware, see it in `lspci`, and conclude the driver is broken. Run `cxl list --memdevs` first: if devices appear but no region exists, the provisioning step was simply never run.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CXL Memory Expansion in 2026: cxl-cli vs memtierd vs Kernel Auto-Tiering",
  "description": "Compare cxl-cli region provisioning, the memtierd tiering daemon and Linux kernel memory demotion for CXL memory expansion, with real commands, sample policy configuration and placement pitfalls.",
  "datePublished": "2026-11-17",
  "dateModified": "2026-11-17",
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
