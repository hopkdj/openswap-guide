---
title: "Self-Hosted Linux Compressed Swap Management: zram-generator vs systemd-swap vs zramd"
date: "2026-05-29"
tags: ["linux", "system-administration", "performance", "memory", "swap", "zram"]
draft: false
---

Memory pressure is one of the most common causes of server instability. When a Linux server runs out of RAM, the kernel invokes the OOM (Out of Memory) killer, terminating processes to free memory. Before reaching that point, the kernel uses swap space — either a swap partition/file on disk, or compressed RAM via zram. This guide compares three tools for managing compressed swap on Linux: **zram-generator** (systemd-native), **systemd-swap** (hybrid swap manager), and **zramd** (simplified zram automation).

Compressed swap using zram is significantly faster than disk-based swap because compression and decompression happen in RAM, avoiding slow disk I/O. For servers with limited memory (VPS instances, edge computing nodes, container hosts), zram-based swap can be the difference between stable operation and OOM crashes.

## Understanding Linux Swap and zram

Traditional Linux swap writes memory pages to a disk partition or file. When the system needs memory back, it reads those pages from disk — a slow operation, especially on HDDs. Zram creates a compressed block device in RAM. Pages written to zram are compressed (typically using zstd or lz4) and stored in memory. The trade-off is CPU usage for compression vs. disk I/O latency.

The performance difference is dramatic: zram access latency is measured in microseconds (CPU compression time), while disk swap access is measured in milliseconds. For memory-constrained servers, zram swap can improve responsiveness by 10-100x compared to disk swap.

## zram-generator: The systemd-Native Approach

**Zram-generator** is an official systemd component that generates zram device units dynamically. It is the recommended approach for modern systemd-based distributions (Fedora, recent Ubuntu, Debian).

**Repository**: `https://github.com/systemd/zram-generator`  
**Stars**: 784  
**Last Updated**: 2025-05  
**License**: LGPL-2.1+

### Key Features

- Integrates directly with systemd unit generation
- Configurable via `/etc/systemd/zram-generator.conf`
- Supports multiple compression algorithms (zstd, lz4, lzo, zle)
- Automatic sizing (fraction of RAM or fixed size)
- No additional daemon — generates standard systemd units
- Supports both swap and filesystem modes
- Actively maintained by the systemd team

### Installation

```bash
# Debian/Ubuntu
sudo apt install zram-generator

# Fedora (pre-installed)
sudo dnf install zram-generator
```

### Configuration

Create `/etc/systemd/zram-generator.conf`:

```ini
[zram0]
# Use half of available RAM (default if omitted)
zram-size = ram / 2

# Compression algorithm (zstd recommended for best ratio/performance)
compression-algorithm = zstd

# Optional: filesystem mode instead of swap
# fs-type = ext4
# mount-point = /var/compressed

# Optional: priority for swap (higher = preferred)
swap-priority = 100
```

Apply the configuration:

```bash
sudo systemctl daemon-reload
sudo systemctl start systemd-zram-setup@zram0.service
sudo swapon --show
```

### Docker Compose (Monitoring Container)

```yaml
version: "3.8"
services:
  zram-monitor:
    image: debian:bookworm-slim
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command: >
      bash -c "
        apt-get update -qq && apt-get install -y -qq zram-tools procps > /dev/null 2>&1 &&
        echo '=== zram devices ===' &&
        cat /sys/block/zram*/mm_stat 2>/dev/null || echo 'No zram devices' &&
        echo '=== swap usage ===' &&
        swapon --show
      "
    restart: "no"
```

## systemd-swap: Hybrid Swap Space Manager

**Systemd-swap** is a script that creates a hybrid swap space combining zram swap, swap files, and swap partitions. It is more flexible than zram-generator but requires more configuration and has not been updated as recently.

**Repository**: `https://github.com/Nefelim4ag/systemd-swap`  
**Stars**: 548  
**Last Updated**: 2022-01  
**License**: MIT

### Key Features

- Hybrid swap: zram + swap files + swap partitions in one configuration
- Automatic zram device creation and management
- Configurable swap file creation with fallocate or dd
- Memory pressure-based activation thresholds
- Supports both systemd and non-systemd init systems
- Built-in monitoring and statistics
- Community-maintained (not an official systemd component)

### Installation

```bash
# Clone the repository
git clone https://github.com/Nefelim4ag/systemd-swap.git
cd systemd-swap

# Install
sudo make install
```

### Configuration

Create `/etc/systemd-swap.conf`:

```ini
# Enable zram swap
swapfc_enabled=1
swapfc_force_use_loop=0
swapfc_force_preallocated=0
swapfc_path=/var/lib/swap
swapfc_count=1
swapfc_size=2G
swapfc_priority=100

# Enable zram devices
zram_enabled=1
zram_algo=zstd
zram_size=ram/2

# Enable swap files on disk
swap_file_enabled=0
swap_file_path=/var/lib/swap/swapfile
swap_file_size=4G
swap_file_priority=50

# Writeback threshold (when zram is 80% full, start using disk swap)
swapfc_free_threshold_perc=20
```

Enable and start:

```bash
sudo systemctl enable --now systemd-swap
sudo systemctl status systemd-swap
```

## zramd: Simplified zram Automation

**Zramd** is a minimal, opinionated tool that sets up zram swap with sensible defaults. It is designed for users who want zram working without reading documentation.

**Repository**: `https://github.com/mbpnix2105/zramd`  
**Stars**: N/A (small community project)  
**Last Updated**: 2021-04  
**License**: MIT

### Key Features

- Zero-configuration setup — works out of the box
- Automatically detects available RAM and sizes zram accordingly
- Uses zstd compression by default
- Simple systemd service integration
- Minimal codebase — easy to audit and modify
- Suitable for embedded devices and low-memory servers

### Installation

```bash
git clone https://github.com/mbpnix2105/zramd.git
cd zramd
sudo ./install.sh
```

### Usage

Zramd requires minimal configuration. It automatically:
1. Detects total system RAM
2. Creates a zram device sized at 50% of RAM
3. Enables it as swap with zstd compression
4. Sets up a systemd service for persistence across reboots

```bash
sudo systemctl enable --now zramd
swapon --show
```

## Comparison Table

| Feature | zram-generator | systemd-swap | zramd |
|---------|---------------|-------------|-------|
| **Primary focus** | zram devices only | Hybrid swap (zram + disk) | Simple zram setup |
| **Compression algorithms** | zstd, lz4, lzo, zle | zstd, lz4, lzo | zstd only |
| **Configuration complexity** | Low (single .conf) | High (multi-section .conf) | None (zero-config) |
| **Multiple swap sources** | No | Yes (zram + file + partition) | No |
| **Active maintenance** | Yes (systemd team) | No (last update 2022) | No (last update 2021) |
| **Distro support** | Fedora, Ubuntu, Debian | Arch, Debian, Ubuntu | Arch, generic Linux |
| **Swap prioritization** | Per-device priority | Multi-level priority | Single device |
| **Memory threshold control** | No | Yes | No |
| **Best for** | Modern systemd distros | Advanced hybrid setups | Quick zram deployment |

## Choosing the Right Compressed Swap Tool

### For Modern Systemd Distributions

**Zram-generator** is the recommended choice. It is maintained by the systemd team, integrates cleanly with systemd unit generation, and requires minimal configuration. Fedora has used it as the default since Fedora 33, and Ubuntu 22.04+ supports it out of the box.

### For Advanced Hybrid Configurations

**Systemd-swap** is the only tool that combines zram, swap files, and swap partitions into a single managed swap space with threshold-based activation. If your server needs zram for normal operation and a disk swap file as a safety net when zram fills up, systemd-swap is your option. Note that it has not been updated since 2022.

### For Quick Deployment

**Zramd** gets zram running with zero configuration. It is suitable for embedded devices, Raspberry Pis, and any situation where you want compressed swap without spending time on configuration.

## Why Self-Host Your Swap Management?

Cloud VMs typically come with no swap configured by default, relying entirely on the available RAM. When memory runs out, the OOM killer terminates processes — often your most critical service. Configuring zram swap gives your server a buffer zone where memory pressure is relieved through compression rather than process termination.

For servers with 1-4 GB of RAM (common in VPS tiers), zram swap with zstd compression can effectively provide 1.5-3x the usable memory capacity. This is especially valuable for container hosts running multiple services, database servers with large buffer pools, and Java applications with significant heap requirements.

For deeper Linux memory management, see our guide on [Linux CPU governor management](../2026-05-22-self-hosted-linux-cpu-governor-management-auto-cpufreq-vs-cpupower-vs-tuned-guide/). For process-level resource monitoring, check our [cgroup monitoring tools comparison](../2026-05-22-self-hosted-cgroup-monitoring-tools-systemd-cgtop-vs-cgroup-tools-vs-libcgroup-guide/). For preventing OOM situations through kernel tuning, our [Linux OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-strategies-early-oom-ps_mem-systemd-guide/) covers proactive approaches.

## FAQ

### Is zram swap better than disk swap?

For most server workloads, **yes**. Zram swap access latency is measured in microseconds (compression/decompression time), while disk swap access is measured in milliseconds (disk seek + read). The only case where disk swap is preferable is when you need to store more than 2x your RAM in swap — zram is limited by available memory, while disk swap can be arbitrarily large.

### How much RAM does zram compression use?

Zstd compression at the default level (level 3) achieves approximately 2.5-3x compression ratio for typical server workloads. This means a 2 GB zram device can hold approximately 5-6 GB of uncompressed data. The CPU overhead is minimal — modern CPUs can compress at 500+ MB/s per core using zstd.

### Will zram-generator work on Ubuntu 22.04?

Yes. Install with `sudo apt install zram-generator`, create `/etc/systemd/zram-generator.conf`, and run `sudo systemctl daemon-reload`. The package is available in Ubuntu 22.04 and later repositories.

### Can I use both zram and disk swap together?

Yes. Linux supports multiple swap devices simultaneously, each with a priority. Set zram swap to a higher priority (e.g., 100) and disk swap to a lower priority (e.g., 50). The kernel will use zram first and only fall back to disk swap when zram is full. Systemd-swap manages this automatically.

### What compression algorithm should I use?

**Zstd** is the recommended default. It offers the best balance of compression ratio and speed. **Lz4** is faster but compresses less (better for CPU-constrained systems). **Lzo** is an older algorithm with performance between lz4 and zstd. **Zle** (zero-length encoding) is only useful for memory pages filled with zeros.

### Does zram survive reboots?

No. Zram devices exist only in RAM and are lost on reboot. Both zram-generator and systemd-swap configure systemd services that recreate zram devices at boot time. Your swap configuration persists in the config files; the actual zram device is recreated automatically.

### How do I monitor zram usage?

Check zram statistics in `/sys/block/zram0/`:

```bash
cat /sys/block/zram0/mm_stat
# Output: orig_data_size compr_data_size mem_used_total ...
```

Or use `zramctl`:

```bash
zramctl --output-all
```

## Conclusion

Compressed swap via zram is one of the most effective ways to improve memory resilience on Linux servers. Zram-generator provides the cleanest, most actively maintained solution for systemd-based distributions. Systemd-swap offers unmatched flexibility for hybrid swap configurations. Zramd delivers instant zram setup with zero configuration. For any server with less than 8 GB of RAM, enabling zram swap should be a standard part of the deployment checklist.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Compressed Swap Management: zram-generator vs systemd-swap vs zramd",
  "description": "Compare zram-generator, systemd-swap, and zramd for managing compressed swap space on Linux servers for improved memory performance.",
  "datePublished": "2026-05-29",
  "dateModified": "2026-05-29",
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
