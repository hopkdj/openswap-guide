---
title: "Self-Hosted Linux Interrupt Management: irqbalance vs tuned vs Manual IRQ Affinity"
date: "2026-05-23"
tags: ["linux", "system-administration", "performance", "interrupt-management"]
draft: false
---

Hardware interrupts are the backbone of Linux system responsiveness — every network packet, disk I/O operation, and USB event triggers an interrupt request (IRQ) that the CPU must handle. On busy servers with high-throughput network interfaces, NVMe storage arrays, or multi-GPU configurations, unbalanced interrupt distribution can create CPU hotspots, increase latency, and degrade overall system performance. This guide compares three approaches to Linux interrupt management: **irqbalance** (automatic daemon), **tuned** (profile-based tuning), and **manual IRQ affinity configuration** (fine-grained control via `/proc/irq`).

## Understanding Linux Interrupt Handling

When a hardware device needs CPU attention, it signals an interrupt request. The Linux kernel routes each IRQ to a specific CPU core via the **IRQ affinity mask** — a bitmask stored in `/proc/irq/<IRQ_NUMBER>/smp_affinity`. By default, the kernel distributes interrupts across all available CPUs, but this naive distribution rarely matches workload patterns.

Consider a high-frequency trading server with a 100GbE network interface card (NIC). If the NIC interrupts land on CPU cores also running the trading application event loop, context switches increase and packet processing latency spikes. Proper interrupt management isolates these workloads, ensuring interrupts are handled on dedicated cores while application threads run undisturbed on others.

The three primary tools for managing this are:

| Feature | irqbalance | tuned | Manual IRQ Affinity |
|---------|-----------|-------|-------------------|
| **Approach** | Automatic daemon | Profile-based | Manual configuration |
| **Setup Complexity** | Low (install and run) | Medium (select profile) | High (per-IRQ configuration) |
| **Dynamic Rebalancing** | Yes | No (static profile) | No |
| **NUMA Awareness** | Yes | Yes | Manual |
| **Fine-Grained Control** | Limited | Limited | Full |
| **Persistence** | Service-based | Profile-based | Requires script |
| **Best For** | General servers | Red Hat systems | Performance-critical workloads |
| **GitHub Stars** | 666 | 1,208 | N/A (kernel feature) |
| **Last Updated** | 2026-04-27 | 2026-05-14 | Kernel mainline |

## irqbalance — Automatic Interrupt Distribution

**irqbalance** is the default interrupt balancer on most Linux distributions. It runs as a daemon, periodically scanning `/proc/interrupts` and redistributing IRQ affinity masks to balance load across CPUs. It considers NUMA topology, CPU idle states, and interrupt frequency when making decisions.

### Installation and Configuration

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y irqbalance
sudo systemctl enable --now irqbalance
```

On RHEL/CentOS/Fedora:

```bash
sudo dnf install -y irqbalance
sudo systemctl enable --now irqbalance
```

The main configuration file is `/etc/sysconfig/irqbalance` (RHEL) or `/etc/default/irqbalance` (Debian):

```bash
# /etc/sysconfig/irqbalance
# Enable irqbalance
ENABLED="1"

# IRQs to ignore (comma-separated IRQ numbers)
# IRQBALANCE_BANNED_IRQS="16,17,18"

# CPUs to exclude from balancing (hex bitmask)
# IRQBALANCE_BANNED_CPUS=0x00000003

# Run in one-shot mode (balance once, then exit)
# IRQBALANCE_ONESHOT="0"
```

### Docker Compose for Interrupt Monitoring

While irqbalance runs directly on the host, you can monitor its effectiveness from a containerized dashboard:

```yaml
version: "3.8"
services:
  irq-monitor:
    image: alpine:latest
    container_name: irq-monitor
    pid: host
    volumes:
      - /proc/interrupts:/host/proc/interrupts:ro
      - /proc/irq:/host/proc/irq:ro
    command: >
      sh -c "while true; do
        cat /host/proc/interrupts | tail -n +2 | awk '{sum=0; for(i=2;i<=NF;i++) sum+=$i; printf "%-30s %d\n", $NF, sum}'
        sleep 5
      done"
    restart: unless-stopped
```

### When irqbalance Falls Short

irqbalance works well for general-purpose servers but has limitations:

- **No application awareness**: It does not know which CPUs run your database or web server threads
- **Rebalancing latency**: It runs every 10 seconds by default, missing burst interrupt patterns
- **Limited NUMA optimization**: While NUMA-aware, it may not optimize for your specific workload topology

## tuned — Profile-Based System Tuning

**tuned** is Red Hat system tuning daemon that applies predefined or custom profiles covering CPU governor, disk scheduler, network settings, and IRQ affinity simultaneously. Unlike irqbalance, tuned applies static configurations based on workload profiles rather than dynamically rebalancing.

### Installation and Configuration

```bash
# RHEL/CentOS/Fedora
sudo dnf install -y tuned
sudo systemctl enable --now tuned
```

tuned includes several built-in profiles that affect interrupt handling:

```bash
# List available profiles
tuned-adm list

# Active profile
tuned-adm active
# Current active profile: throughput-performance

# Available interrupt-related profiles:
# - throughput-performance: Server throughput, IRQ balancing enabled
# - latency-performance: Low latency, IRQ pinned to specific cores
# - network-throughput: Network optimization with IRQ affinity
# - virtual-host: VM host optimization with IRQ distribution
```

### Creating a Custom Profile for IRQ Management

```ini
# /etc/tuned/my-server-profile/tuned.conf
[main]
summary=Custom server profile with optimized IRQ affinity

[cpu]
force_latency=cstate1:nohz

[scheduler]
group.balanced=

[irqbalance]
enabled=true

# Pin specific IRQs to specific CPUs
[irqaffinity]
# Pin eth0 IRQs (IRQ 32) to CPU 0-3
32=0-3
# Pin NVMe IRQs (IRQ 48-55) to CPU 4-7
48-55=4-7
```

Activate the profile:

```bash
sudo tuned-adm profile my-server-profile
```

### Docker Compose for tuned Monitoring

```yaml
version: "3.8"
services:
  tuned-exporter:
    image: prom/node-exporter:latest
    container_name: tuned-exporter
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.interrupts'
    ports:
      - "9100:9100"
    restart: unless-stopped
```

## Manual IRQ Affinity — Fine-Grained Control

Manual IRQ affinity configuration provides the highest level of control. You directly write CPU affinity bitmasks to `/proc/irq/<IRQ>/smp_affinity`, giving you precise placement of each interrupt source.

### Finding IRQ Numbers

```bash
# List all IRQs and their current CPU assignments
cat /proc/interrupts | head -20

# Find NIC IRQs
cat /proc/interrupts | grep -i eth0

# Find NVMe IRQs
cat /proc/interrupts | grep -i nvme
```

Example output:

```
           CPU0       CPU1       CPU2       CPU3
 16:      45123      12345      67890      11111   PCI-MSI   eth0
 32:      89012      23456      34567      45678   PCI-MSI   nvme0
```

### Setting IRQ Affinity

CPU affinity is specified as a hexadecimal bitmask. CPU 0 = 0x1, CPU 1 = 0x2, CPU 2 = 0x4, CPUs 0-3 = 0xF:

```bash
# Pin IRQ 16 (eth0) to CPUs 0 and 1 (hex: 0x3)
echo 3 | sudo tee /proc/irq/16/smp_affinity

# Pin IRQ 32 (nvme0) to CPUs 2 and 3 (hex: 0xC)
echo C | sudo tee /proc/irq/32/smp_affinity

# Pin multiple IRQs (48-55) to CPUs 4-7 (hex: 0xF0)
for irq in $(seq 48 55); do
  echo F0 | sudo tee /proc/irq/$irq/smp_affinity
done
```

### Persistent Configuration via systemd

```ini
# /etc/systemd/system/irq-affinity.service
[Unit]
Description=Set IRQ Affinity
After=network.target
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'echo 3 > /proc/irq/16/smp_affinity'
ExecStart=/bin/bash -c 'echo C > /proc/irq/32/smp_affinity'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable irq-affinity.service
sudo systemctl start irq-affinity.service
```

## Why Self-Host and Manage Interrupts Locally?

Managing interrupt affinity on your own infrastructure provides benefits that cloud instances cannot match. When you control bare-metal servers, you have direct access to `/proc/irq` and can tune interrupt distribution to your exact workload patterns.

For high-throughput database servers, isolating storage IRQs to dedicated CPU cores eliminates interrupt-induced latency spikes in query processing. Network-intensive applications like load balancers and reverse proxies benefit from pinning NIC interrupts to cores adjacent to the application threads in the CPU topology.

For related Linux performance tuning, see our [Linux I/O Schedulers comparison](../2026-05-22-self-hosted-linux-io-scheduler-bfq-mq-deadline-kyber-guide/) and [CPU Governor management guide](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-cpupower-tuned-guide/). For NUMA-aware memory management, check our [HugePages guide](../2026-05-22-self-hosted-linux-hugepages-management-libhugetlbfs-numactl-tuned-guide/).

## Choosing the Right Interrupt Management Strategy

| Scenario | Recommended Tool |
|----------|-----------------|
| General-purpose web server | irqbalance (default) |
| Red Hat Enterprise Linux | tuned with throughput-performance profile |
| High-frequency trading | Manual IRQ affinity (pin NIC IRQs) |
| Database server (NVMe storage) | Manual IRQ affinity plus tuned profile |
| Virtualization host | tuned with virtual-host profile |
| Mixed workload | irqbalance with banned IRQs for critical devices |

## FAQ

### What is IRQ affinity in Linux?

IRQ (Interrupt Request) affinity is a Linux kernel feature that controls which CPU cores handle hardware interrupts from specific devices. Each IRQ has an affinity mask stored in `/proc/irq/<number>/smp_affinity` that specifies the allowed CPU cores. Proper IRQ affinity prevents interrupt storms on single cores and reduces latency for latency-sensitive applications.

### Does irqbalance work on NUMA systems?

Yes, irqbalance is NUMA-aware by default. It considers the NUMA topology when distributing interrupts, preferring to assign device IRQs to CPU cores on the same NUMA node as the device PCIe slot. This minimizes cross-NUMA memory access latency. You can verify NUMA awareness by checking irqbalance logs: `journalctl -u irqbalance | grep -i numa`.

### Can I use irqbalance and tuned together?

Yes, they serve different purposes. irqbalance handles dynamic interrupt redistribution, while tuned manages broader system tuning profiles (CPU governor, disk scheduler, kernel parameters). You can run irqbalance inside a tuned profile. However, some tuned profiles (like `latency-performance`) may disable irqbalance in favor of static IRQ pinning — check the profile `irqbalance` section in `/usr/lib/tuned/<profile>/tuned.conf`.

### How do I verify IRQ affinity is working correctly?

Use `cat /proc/interrupts` to see interrupt counts per CPU. If one CPU shows significantly higher counts for a specific IRQ than others, the affinity mask may not be set correctly. You can also use `grep . /proc/irq/*/smp_affinity` to see all current affinity masks. For real-time monitoring, `watch -n 1 cat /proc/interrupts` shows how counts change over time.

### What happens to IRQ affinity after a reboot?

Manual IRQ affinity settings in `/proc/irq` are lost on reboot. To persist them, use a systemd service (as shown above), a tuned profile, or add the configuration to `/etc/rc.local`. irqbalance and tuned settings persist automatically through their respective systemd services.

### Should I disable irqbalance on a production server?

Not necessarily. irqbalance works well for most workloads. Disable it only if you need fine-grained manual control over specific IRQs (e.g., pinning NIC interrupts for a low-latency trading application). If you disable it, you must manually configure IRQ affinity for all devices, or use tuned profiles that handle IRQ placement automatically.

### What is the difference between MSI and legacy interrupts?

MSI (Message Signaled Interrupts) and MSI-X are modern interrupt mechanisms where devices write to a specific memory address to signal interrupts, rather than using dedicated physical interrupt lines. MSI-X supports more vectors per device (up to 2048) and allows per-queue interrupt assignment. Check if your device uses MSI: `lspci -vvv | grep -i "msi"`. Modern NICs and NVMe controllers use MSI-X by default.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Interrupt Management: irqbalance vs tuned vs Manual IRQ Affinity",
  "description": "Compare irqbalance, tuned, and manual IRQ affinity configuration for Linux interrupt management. Learn automatic vs profile-based vs fine-grained interrupt distribution for server performance optimization.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
