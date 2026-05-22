---
title: "Self-Hosted Linux Coredump Management: systemd-coredump vs ABRT vs minicoredumper (2026)"
date: "2026-05-22"
tags: ["linux", "system-administration", "debugging", "crash-management", "self-hosted"]
draft: false
---

When a Linux process crashes, the kernel can generate a **coredump** — a snapshot of the process memory, registers, and execution state at the moment of failure. These files are essential for post-mortem debugging, but managing them at scale across servers is a challenge. Without proper coredump handling, crashes are silent, debug information is lost, and production issues remain unresolved.

This guide compares three self-hosted Linux coredump management solutions: **systemd-coredump**, **ABRT** (Automatic Bug Reporting Tool), and **minicoredumper**. Each takes a fundamentally different approach to crash capture, storage, and analysis.

## How Linux Coredump Generation Works

Before comparing tools, it helps to understand the underlying mechanism. When a process receives a fatal signal (SIGSEGV, SIGABRT, SIGILL, etc.), the Linux kernel invokes a **core_pattern** handler defined in `/proc/sys/kernel/core_pattern`. This handler is a pipe to a user-space program or a file path template.

The default core pattern on many systems is:

```
|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %e
```

The pipe symbol (`|`) tells the kernel to send the coredump data via stdin to the specified program, along with metadata arguments:

| Parameter | Meaning |
|-----------|---------|
| `%P` | PID of the crashing process |
| `%u` | UID of the process owner |
| `%g` | GID of the process owner |
| `%s` | Signal number that caused the crash |
| `%t` | Unix timestamp of the crash |
| `%c` | Core file size soft resource limit |
| `%h` | Hostname |
| `%e` | Executable filename (comm) |

You can inspect the current pattern with:

```bash
cat /proc/sys/kernel/core_pattern
```

And set a custom handler:

```bash
echo "|/usr/bin/my-handler %P %u %g %s %t %c %h %e" | sudo tee /proc/sys/kernel/core_pattern
```

## Tool Comparison Overview

| Feature | systemd-coredump | ABRT | minicoredumper |
|---------|-----------------|------|----------------|
| **Origin** | systemd project (freedesktop) | Fedora/RHEL project | Diamond Light Source |
| **GitHub Stars** | Part of systemd (70K+) | 242 | 56 |
| **Last Updated** | Active (2026) | May 2026 | May 2026 |
| **Default On** | Most systemd distros | Fedora/RHEL | Manual install |
| **Core Format** | Full coredump (compressed) | Full coredump + metadata | Minimal coredump |
| **Storage Backend** | Journal (lz4 compressed) | Filesystem + database | Filesystem |
| **CLI Tools** | `coredumpctl` | `abrt-cli` | `minicoredumper` config |
| **Web UI** | No | Yes (ABRT Web) | No |
| **Auto-Reporting** | No | Yes (Bugzilla, Email) | No |
| **Size Efficiency** | Compressed but full | Full + metadata | Minimal (stripped) |
| **Docker Support** | Yes (journal integration) | Yes | Yes |
| **Config Complexity** | Low | Medium | Low |

## systemd-coredump — The Default Choice

**systemd-coredump** is the default coredump handler on virtually all systemd-based distributions. It compresses coredumps with lz4 and stores them in the systemd journal, making them queryable via `coredumpctl`.

### Installation

On most modern Linux distributions, systemd-coredump is pre-installed. If not:

```bash
# Debian/Ubuntu
sudo apt install systemd-coredump

# RHEL/Fedora/CentOS
sudo dnf install systemd-coredump

# Arch Linux
sudo pacman -S systemd
```

### Configuration

The configuration file is `/etc/systemd/coredump.conf`:

```ini
[Coredump]
# Maximum coredump size (bytes, K, M, G)
# 0 = disabled, infinity = no limit
Storage=external
Compress=yes
ProcessSizeMax=2G
ExternalSizeMax=2G
JournalSizeMax=767M
```

Key options:
- **Storage=external**: Stores compressed cores in `/var/lib/systemd/coredump/` instead of the journal
- **Storage=journal**: Stores in the journal (limited by `JournalSizeMax`)
- **Compress=yes**: Uses lz4 compression (typically 3-5x reduction)
- **ProcessSizeMax**: Maximum process size to capture

### Viewing and Analyzing Coredumps

```bash
# List all coredumps
coredumpctl list

# List coredumps for a specific executable
coredumpctl list /usr/bin/myapp

# View detailed info about the most recent coredump
coredumpctl info

# Extract the coredump to a file
coredumpctl dump -o /tmp/core.dump

# Launch GDB directly with the coredump
coredumpctl gdb /usr/bin/myapp

# Delete old coredumps
coredumpctl vacuum --time=7d
```

### Docker Deployment

systemd-coredump works inside containers when journal access is available:

```yaml
version: "3.8"
services:
  app-with-coredump:
    image: myapp:latest
    cap_add:
      - SYS_PTRACE
    volumes:
      - /var/lib/systemd/coredump:/var/lib/systemd/coredump
      - /var/log/journal:/var/log/journal
    environment:
      - COREDUMP_STORAGE=external
    ulimits:
      core: -1
```

## ABRT — Automated Bug Reporting

**ABRT** (Automatic Bug Reporting Tool) goes beyond simple coredump capture. It collects crash data, analyzes it, and can automatically file bug reports to Bugzilla, send emails, or upload to a central server. It is the default crash handler on Fedora and RHEL.

### Installation

```bash
# Fedora/RHEL
sudo dnf install abrt abrt-cli abrt-addon-ccpp abrt-addon-python3

# Enable and start the services
sudo systemctl enable --now abrt-ccpath abrtd
```

### Configuration

ABRT uses a modular plugin architecture. Key configuration files:

**`/etc/abrt/abrt.conf`** — Main configuration:
```ini
# Max size for created problem directories (in bytes)
# 0 = unlimited
MaxCrashReportsSize = 5000
# Delete problem directory when it exceeds this age (in seconds)
# 0 = never delete
DeleteUploaded = no
# Enable automatic bug reporting
OpenGPGCheck = yes
```

**`/etc/abrt/plugins/CCpp.conf`** — C/C++ crash handler:
```ini
# Save full coredump (not just backtrace)
SaveFullCore = yes
# Generate C++ backtrace
GenerateBacktrace = yes
# Analyze C/C++ crashes
Analyzer = abrt-action-analyze-cpp
```

### Key ABRT Components

| Component | Role |
|-----------|------|
| `abrtd` | Main daemon, watches for crashes |
| `abrt-ccpp` | C/C++ crash handler |
| `abrt-action-analyze-c` | Crash analysis engine |
| `abrt-action-report-bugzilla` | Auto-file Bugzilla bugs |
| `abrt-action-notify-email` | Send email notifications |

### Managing Crashes with ABRT

```bash
# List all detected crashes
abrt-cli list

# Show details of a specific crash
abrt-cli info /var/spool/abrt/ccpp-2026-05-23-12345-1234

# Report a crash to Bugzilla
abrt-cli report /var/spool/abrt/ccpp-2026-05-23-12345-1234

# Remove a crash report
abrt-cli rm /var/spool/abrt/ccpp-2026-05-23-12345-1234

# Remove all crash reports
abrt-cli rm --all
```

### ABRT Web Interface

ABRT includes a web UI for centralized crash management:

```bash
# Install the web interface
sudo dnf install abrt-web

# Configure Apache and start the service
sudo systemctl enable --now httpd abrt-web
```

The web interface provides:
- Dashboard of all crash reports
- Filtering by package, executable, or time
- One-click bug filing
- Statistics and trend analysis

### Docker Deployment for ABRT

```yaml
version: "3.8"
services:
  abrt-daemon:
    image: fedora:40
    cap_add:
      - SYS_PTRACE
    volumes:
      - /var/spool/abrt:/var/spool/abrt
      - /etc/abrt:/etc/abrt:ro
      - /var/log:/var/log
    command: |
      dnf install -y abrt abrt-cli abrt-addon-ccpp &&
      systemctl start abrtd &&
      tail -f /var/log/abrt/abrt-log
    ulimits:
      core: -1
```

## minicoredumper — Lightweight Alternative

**minicoredumper** takes a radically different approach: instead of capturing full coredumps (which can be gigabytes), it generates **minimal coredumps** containing only the essential debugging information — stack frames, registers, and a small memory region around the crash point.

### Why Minimal Coredumps?

Full coredumps of large processes can be 10-50 GB, making them impractical to store, transfer, or analyze. minicoredumper typically produces dumps under 1 MB while retaining enough information for most debugging scenarios.

### Installation

```bash
# Build from source
git clone https://github.com/diamon/minicoredumper.git
cd minicoredumper
./configure
make
sudo make install

# Or install from package manager (if available)
# On some distros:
sudo apt install minicoredumper
```

### Configuration

**`/etc/minicoredumper.conf`**:

```ini
[global]
# Output directory for minicoredumps
output_dir = /var/crash/minicoredumps
# Compress output files
compress = yes
# Include full memory maps
full_memory = no
# Include thread info
thread_info = yes
# Include loaded libraries
library_info = yes
# Include file descriptors
fd_info = yes
# Include environment variables
env_info = yes

[per_process]
# Override settings for specific executables
# /usr/bin/myapp:compress = no
```

### Setting minicoredumper as the Core Handler

```bash
# Set as the kernel core pattern handler
echo "|/usr/local/bin/minicoredumper %P %u %g %s %t %c %h %e" |   sudo tee /proc/sys/kernel/core_pattern

# Make persistent across reboots
echo "kernel.core_pattern=|/usr/local/bin/minicoredumper %P %u %g %s %t %c %h %e" |   sudo tee -a /etc/sysctl.d/99-corepattern.conf
```

### Viewing Minicoredumps

minicoredumper produces standard ELF core files (just smaller), so all standard tools work:

```bash
# List generated dumps
ls -lh /var/crash/minicoredumps/

# Analyze with GDB
gdb /usr/bin/myapp /var/crash/minicoredumps/core.12345

# Extract strings from a minicoredump
strings /var/crash/minicoredumps/core.12345 | head -50

# Use readelf to inspect
readelf -n /var/crash/minicoredumps/core.12345
```

## Size Comparison: Full vs Minimal Coredumps

| Process Size | Full Coredump | minicoredumper Output | Compression Ratio |
|--------------|--------------|----------------------|-------------------|
| 100 MB process | 100 MB | 200 KB | 500x |
| 1 GB process | 1 GB | 500 KB | 2000x |
| 10 GB process | 10 GB | 800 KB | 12,500x |
| 50 GB database | 50 GB | 1.2 MB | 41,667x |

The savings are dramatic, especially for large server processes.

## Choosing the Right Coredump Manager

| Scenario | Recommended Tool |
|----------|-----------------|
| **Default systemd distro** | systemd-coredump (already installed) |
| **Fedora/RHEL environments** | ABRT (native integration) |
| **Need automatic bug filing** | ABRT (Bugzilla/email integration) |
| **Large processes (databases, JVMs)** | minicoredumper (minimal dumps) |
| **Disk space constrained** | minicoredumper (KB vs GB) |
| **Centralized crash monitoring** | ABRT + ABRT Web |
| **Container environments** | systemd-coredump (journal integration) |
| **Minimal overhead** | minicoredumper (fastest capture) |

## Why Self-Host Coredump Management?

Running your own coredump management infrastructure gives you complete control over crash data. When a production process crashes, the difference between having a coredump and not having one is the difference between a 5-minute root-cause analysis and a days-long investigation.

**Data ownership and privacy**: Coredumps contain process memory, which may include sensitive data — credentials in memory, customer data, cryptographic keys. Self-hosting ensures crash data never leaves your infrastructure. With systemd-coredump, cores stay in your journal; with minicoredumper, you control exactly what memory regions are captured, reducing exposure.

**Storage cost control**: Full coredumps of large processes can consume terabytes of disk space on busy servers. minicoredumper reduces this by orders of magnitude — a 50 GB database process produces a 1.2 MB dump instead. Even with systemd-coredump's lz4 compression, the size savings from minicoredumper are dramatic for memory-heavy workloads.

**Compliance requirements**: Many regulated industries (finance, healthcare, government) require that all crash data remain on-premises. ABRT's ability to file bugs to an internal Bugzilla instance (rather than a public tracker) satisfies these requirements while still providing automated crash reporting.

**Debugging workflow integration**: Self-hosted coredump management integrates with your existing monitoring stack. For storage monitoring best practices, see our [disk health monitoring guide](../self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide-2026/). For log-based crash detection, our [syslog aggregation comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) covers centralized log collection that complements coredump analysis. And for GPU-related crashes, our [GPU monitoring guide](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) shows how to correlate hardware metrics with process crashes.

## FAQ

### What is a coredump and why do I need one?

A coredump is a file containing the complete memory state of a process at the moment it crashed. It includes register values, stack traces, heap contents, and loaded library information. When a process segfaults or receives a fatal signal, the kernel can write this snapshot to disk. Without a coredump, debugging a production crash often requires reproducing the issue — which may be impossible for intermittent bugs. With a coredump, you can load it into GDB or LLDB and inspect the exact state at crash time.

### How much disk space do coredumps consume?

Full coredumps are approximately the size of the process's RSS (resident set size) at crash time. A 4 GB database process will produce a ~4 GB coredump. systemd-coredump compresses these with lz4 (typically 3-5x reduction). minicoredumper produces minimal coredumps under 1 MB regardless of process size by capturing only stack frames and critical memory regions. ABRT stores full coredumps plus metadata files (backtrace, environment, maps).

### Can I use multiple coredump handlers simultaneously?

No. The kernel supports only one core_pattern handler at a time. However, you can chain handlers: write a wrapper script that invokes multiple tools sequentially. For example, a script could first save a full coredump via systemd-coredump, then invoke minicoredumper to produce a minimal dump. Or you could configure systemd-coredump as the primary handler and use ABRT's post-crash analysis addon to process the stored cores.

### Is minicoredumper suitable for production use?

Yes, but with caveats. Minimal coredumps are excellent for most debugging scenarios — null pointer dereferences, assertion failures, and stack overflows are all diagnosable with minimal dumps. However, if you need to debug heap corruption, memory leaks, or issues requiring full heap inspection, you will need a full coredump. A practical approach: use minicoredumper as the default handler and configure specific critical processes to use full coredumps via per-process core pattern overrides.

### How do I disable coredumps entirely?

To disable coredumps system-wide:
```bash
echo "core" | sudo tee /proc/sys/kernel/core_pattern
ulimit -c 0
```
To set in sysctl persistently:
```bash
echo "kernel.core_pattern=core" | sudo tee -a /etc/sysctl.d/99-nocore.conf
echo "* soft core 0" | sudo tee -a /etc/security/limits.d/99-nocore.conf
echo "* hard core 0" | sudo tee -a /etc/security/limits.d/99-nocore.conf
```

### Does ABRT work on non-Fedora distributions?

Yes, ABRT can be installed on any Linux distribution, though it is optimized for Fedora/RHEL. On Debian/Ubuntu, you can install it from the repositories (`apt install abrt abrt-cli`), but some plugins may require additional configuration. The core crash capture and CLI functionality works across distributions. The Bugzilla integration and web interface may need custom endpoint configuration for non-Fedora bug trackers.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Coredump Management: systemd-coredump vs ABRT vs minicoredumper (2026)",
  "description": "Compare three Linux coredump management solutions: systemd-coredump, ABRT, and minicoredumper. Learn how to configure, deploy, and analyze crash dumps on self-hosted Linux servers.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
