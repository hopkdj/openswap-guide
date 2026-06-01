---
title: "Self-Hosted Linux Kernel Same-page Merging (KSM) Tuning: KSM vs UKSM vs KSMTuned"
date: "2026-06-02"
tags: ["linux", "kernel", "memory-management", "virtualization", "performance", "system-administration", "optimization"]
draft: false
---

## Introduction

Memory is often the most constrained resource in self-hosted virtualization environments. Running multiple virtual machines or containers on a single host means each guest consumes its own allocation of RAM, and identical memory pages — the same operating system kernel, shared libraries, or application binaries — exist in multiple copies across different guest address spaces. On a host running 10 identical Ubuntu VMs, the same libc pages exist in physical RAM 10 times.

**Kernel Same-page Merging (KSM)** is a Linux kernel feature that addresses this inefficiency by scanning physical memory for identical pages and merging them into a single copy-on-write page. When a VM modifies a merged page, the kernel transparently creates a private copy. For homogeneous virtualization workloads, KSM can reduce physical memory usage by 30-60%, effectively doubling the number of VMs a host can run.

However, KSM comes with a CPU cost — the scanning daemon (`ksmd`) must compare page contents to find duplicates, and the merging process itself requires page table manipulation. The trade-off between memory savings and CPU overhead is the central tuning challenge, and three approaches exist: the kernel's built-in KSM, the more aggressive Ultra KSM (UKSM), and the automatic tuning daemon KSMTuned.

## Understanding How KSM Works

KSM operates through a dedicated kernel thread called `ksmd` that runs periodically. During each scan cycle, ksmd examines anonymous pages (memory not backed by files) that have been registered with KSM via the `madvise(MADV_MERGEABLE)` system call.

The scanning process works as follows:

1. **Registration:** Applications (typically QEMU/KVM via the `-mem-prealloc` and KSM support) mark memory regions as mergeable
2. **Scanning:** `ksmd` wakes up, scans registered pages, computes checksums, and compares pages with matching checksums byte-by-byte
3. **Merging:** Identical pages are merged — all page table entries point to a single shared physical page, marked copy-on-write
4. **Unmerging:** If any process writes to a merged page, the copy-on-write fault handler transparently creates a private copy

KSM is controlled via sysfs parameters:

```bash
# Check KSM status
cat /sys/kernel/mm/ksm/run          # 0=stopped, 1=running, 2=stopped+unmerge
cat /sys/kernel/mm/ksm/pages_shared # Currently shared pages
cat /sys/kernel/mm/ksm/pages_sharing # Pages saved by sharing
cat /sys/kernel/mm/ksm/pages_unshared
cat /sys/kernel/mm/ksm/full_scans   # Total completed scan cycles

# Enable KSM
echo 1 | sudo tee /sys/kernel/mm/ksm/run

# Tune scan interval (milliseconds between page scans)
echo 20 | sudo tee /sys/kernel/mm/ksm/sleep_millisecs

# Tune pages per scan batch
echo 1000 | sudo tee /sys/kernel/mm/ksm/pages_to_scan
```

KSM statistics show the memory savings:

```bash
# Calculate memory saved (in pages, multiply by 4K for bytes)
saved=$(cat /sys/kernel/mm/ksm/pages_sharing)
echo "Memory saved: $(( saved * 4096 / 1024 / 1024 )) MB"
```

## Tool Comparison: KSM vs UKSM vs KSMTuned

### KSM — Standard Kernel Implementation

The standard KSM in the mainline Linux kernel represents the conservative, well-tested approach. It prioritizes stability and low CPU overhead over maximum memory savings.

**Key characteristics:**
- **Stable and well-tested** — part of the kernel since 2.6.32 (2009)
- **Conservative scanning** — default sleep_millisecs of 20ms, pages_to_scan of 100
- **No zero-page merging** — only merges non-zero pages
- **Manual tuning required** — no dynamic adjustment based on system load

**Configuration for a virtualization host:**

```bash
# /etc/sysctl.d/99-ksm.conf
# Enable KSM at boot via kernel parameter or init script

# Aggressive KSM configuration for homelab with 10+ identical VMs
echo 1 > /sys/kernel/mm/ksm/run
echo 10 > /sys/kernel/mm/ksm/sleep_millisecs   # Scan more frequently
echo 2000 > /sys/kernel/mm/ksm/pages_to_scan   # More pages per batch
```

**Pros:** No kernel patching needed, available on every distribution, zero maintenance.
**Cons:** Conservative by default; requires manual tuning for optimal savings; no adaptive behavior.

### UKSM — Ultra KSM (Community Patch)

UKSM is a community-maintained kernel patch that replaces the standard KSM with a more aggressive, high-performance implementation. It is not in the mainline kernel and requires a custom kernel build.

**Key characteristics:**
- **Full memory scanning** — scans ALL memory, not just MADV_MERGEABLE regions
- **Zero-page merging** — can merge zero-filled pages, saving even more memory
- **Higher CPU usage** — more aggressive scanning means more CPU time for ksmd
- **Faster deduplication** — optimized comparison algorithm finds duplicates more quickly
- **Not mainline** — potential compatibility issues with kernel updates

**Deployment considerations:**
- Available as a kernel patch for specific kernel versions
- Used by some hosting providers and VPS platforms for density optimization
- Requires rebuilding the kernel with the UKSM patch

**Pros:** Higher memory savings (10-20% more than standard KSM), merges zero pages, faster scanning.
**Cons:** Requires kernel patching, higher CPU overhead, not in mainline, potential stability concerns.

### KSMTuned — Automatic Tuning Daemon

KSMTuned is a userspace daemon that dynamically adjusts KSM parameters based on system memory pressure. Originally developed by Red Hat, it monitors free memory and throttles KSM activity up or down accordingly.

```bash
# Install KSMTuned (RHEL/CentOS)
sudo yum install ksmtuned

# Or build from source
git clone https://github.com/openela-main/ksmtuned
cd ksmtuned
sudo make install

# Configuration
sudo tee /etc/ksmtuned.conf << 'EOF'
# KSM_TUNED CONFIGURATION

# Thresholds for KSM throttling
LO=1024     # Below this many MB free: increase KSM activity (throttle up)
HI=2048     # Above this many MB free: decrease KSM activity (throttle down)
SLEEP=60    # Seconds between adjustment checks

# KSM parameters when throttled up (low memory)
KSM_THRES_COEF=40
KSM_NPAGES_BOOST=500
KSM_NPAGES_DECAY=-150
KSM_NPAGES_MIN=100
KSM_NPAGES_MAX=2000

# KSM parameters when throttled down (high memory)
KSM_SLEEP_MSEC=100
EOF

sudo systemctl enable --now ksmtuned
```

**Key features:**
- **Dynamic adaptation** — increases KSM aggressiveness when memory is low, reduces when memory is plentiful
- **Set-and-forget** — no manual tuning needed after initial configuration
- **Throttling prevents CPU waste** — when memory pressure is low, KSM activity is reduced to save CPU cycles
- **Red Hat recommended** — for KVM virtualization hosts

### Comparison Table

| Feature | Standard KSM | UKSM | KSMTuned |
|---------|-------------|------|----------|
| **Kernel support** | Mainline since 2.6.32 | Requires patch | Works with mainline KSM |
| **Scanning scope** | MADV_MERGEABLE only | All anonymous memory | (Depends on underlying KSM) |
| **Zero-page merging** | No | Yes | (Depends on underlying KSM) |
| **CPU overhead** | Low (tunable) | Higher (aggressive) | Adaptive (reduces when idle) |
| **Memory savings** | 20-50% (typical) | 30-60% (typical) | 20-50% (same as KSM) |
| **Tuning required** | Manual sysfs tuning | Manual sysfs tuning | Automatic (based on free memory) |
| **Stability** | Production-ready | Community, less tested | Red Hat supported |
| **Setup complexity** | Zero (built-in) | High (kernel rebuild) | Low (package install) |

## Why Self-Host KSM Tuning?

For self-hosted virtualization platforms running Proxmox VE, KVM with libvirt, or oVirt, KSM is one of the highest-impact performance optimizations available — and it costs nothing. Unlike adding physical RAM or migrating to larger hosts, enabling and tuning KSM requires only configuration changes.

**Memory overcommit is the killer feature.** Without KSM, a 64GB host running 10 VMs with 8GB each cannot fit — that's 80GB of guest allocation in 64GB of physical RAM. With KSM reducing memory usage by 40% across identical OS images, those 10 VMs consume approximately 48GB of physical RAM, comfortably fitting in the host. This effect compounds with each additional identical VM.

**Density translates directly to cost savings.** For colocation customers paying by the rack unit, doubling VM density per host halves infrastructure costs. For homelab enthusiasts, it means fitting more services on existing hardware without upgrades. For VPS providers, it's the difference between profitable and unprofitable pricing tiers.

**Tuning prevents the CPU penalty from becoming excessive.** Badly tuned KSM can waste 5-15% of CPU time on page scanning that yields minimal memory savings. KSMTuned or a well-configured manual setup ensures KSM only works hard when memory is actually constrained, preserving CPU for guest workloads.

For related performance optimization, see our [Linux kernel tuning guide](../2026-06-01-linux-kernel-tuning-sysctl-tuned-systool-guide/) and our [memory reclaim guide](../2026-06-01-linux-memory-reclaim-kswapd-drop-caches-vfs-cache-tuning/). If you're running a full virtualization stack, check our [self-hosted virtualization platforms comparison](../proxmox-ve-vs-xcp-ng-vs-ovirt-self-hosted-virtualization-guide-2026/).

## Practical KSM Deployment for Proxmox and KVM

### Proxmox VE Configuration

Proxmox enables KSM by default, but the default settings are conservative:

```bash
# Check current KSM status on Proxmox
systemctl status ksmtuned

# View current KSM sharing statistics
cat /sys/kernel/mm/ksm/pages_sharing
cat /sys/kernel/mm/ksm/pages_shared

# For a homelab with limited RAM, increase aggressiveness:
echo 500 | tee /sys/kernel/mm/ksm/pages_to_scan
echo 10 | tee /sys/kernel/mm/ksm/sleep_millisecs
```

Proxmox's KSMTuned service is configured in `/etc/ksmtuned.conf` and adjusts parameters based on free memory thresholds.

### KVM/libvirt Configuration

For KVM hosts, ensure VMs are started with KSM support:

```bash
# In the VM's libvirt XML, ensure
<memoryBacking>
    <nosharepages/>
</memoryBacking>

# Start VMs with pre-allocated memory for KSM effectiveness
virsh start --prealloc-mem vm-name
```

Monitor KSM effectiveness:

```bash
# One-liner to show KSM savings 
echo "KSM saved: $(( $(cat /sys/kernel/mm/ksm/pages_sharing) * 4096 / 1024 / 1024 )) MB (shared: $(( $(cat /sys/kernel/mm/ksm/pages_shared) * 4096 / 1024 / 1024 )) MB)"

# Monitor KSM CPU usage
top -b -n 1 | grep ksmd
```

## FAQ

### How much memory can KSM realistically save?

**20-50% for homogeneous VM workloads, 5-15% for container workloads.** The savings depend heavily on how similar your guests are. Ten identical Ubuntu 24.04 VMs running the same application stack will see 40%+ savings. Ten VMs with different operating systems and wildly different applications will see minimal benefit. KSM is most effective when you standardize your VM images.

### Does KSM slow down my VMs?

**The CPU cost is typically 1-5% of a single core.** For a 16-core host, this is barely noticeable. The cost is front-loaded: the initial scan cycle after booting new VMs uses more CPU, but once pages are merged, ongoing scanning checks only for new candidates. KSMTuned further reduces this by dialing down KSM when memory is plentiful.

### Is KSM safe for production database servers?

**Yes, with caveats.** KSM only merges anonymous (non-file-backed) memory, so database buffer pools and caches are not affected. However, the copy-on-write unmerge when a VM writes to a shared page adds a few microseconds of latency. For latency-sensitive database workloads, you can exclude specific VMs from KSM by not calling `madvise(MADV_MERGEABLE)` on their memory. In QEMU/KVM, this can be controlled per-VM.

### What's the difference between KSM and transparent hugepages (THP)?

KSM merges **identical** pages across different processes/VMs to save memory. THP promotes **contiguous** 4K pages to 2MB/1GB pages within a single process to improve TLB efficiency. They serve completely different purposes and can be used together. KSM reduces memory usage; THP improves memory access speed.

### Can I use KSM with containers (Docker/Podman)?

**Yes, but the benefits are smaller.** Containers share the host kernel, so kernel pages are already shared without KSM. KSM can still merge identical application pages across containers running the same image, but typical savings are 5-15% rather than the 20-50% seen with full VMs. Enable it with `echo 1 > /sys/kernel/mm/ksm/run` — there's no downside for container hosts.

### Should I use UKSM instead of standard KSM?

**For most self-hosted deployments, no.** UKSM's benefits (zero-page merging, faster scanning, slightly higher savings) are outweighed by the maintenance burden of maintaining a custom kernel with a non-mainline patch. Standard KSM with KSMTuned provides 90%+ of the benefit with zero ongoing maintenance. UKSM is primarily useful for VPS providers and hosting companies where the additional 10% memory savings translate to measurable revenue.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election outcomes to regulatory timelines, you can bet on anything you have an information edge on. Unlike gambling, this is a true information market: the more you know, the higher your win rate. I've made good returns predicting technology-related events. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Kernel Same-page Merging (KSM) Tuning: KSM vs UKSM vs KSMTuned",
  "description": "Comprehensive comparison of Linux kernel same-page merging implementations: standard KSM in mainline kernel, community UKSM patch, and the KSMTuned automatic tuning daemon. Includes performance benchmarks, tuning parameters, and deployment guidance for virtualization hosts.",
  "datePublished": "2026-06-02",
  "dateModified": "2026-06-02",
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
