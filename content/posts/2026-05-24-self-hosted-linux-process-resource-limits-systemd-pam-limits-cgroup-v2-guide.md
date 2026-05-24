---
title: "Self-Hosted Linux Process Resource Limits: systemd vs pam_limits vs cgroup v2 (2026)"
date: "2026-05-24"
tags: ["linux", "cgroups", "systemd", "resource-limits", "system-administration", "performance"]
draft: false
---

Resource limits are a critical aspect of self-hosted server administration. Without proper limits, a single runaway process can consume all CPU, exhaust memory, or open thousands of file descriptors — causing system-wide instability that affects every service on the server.

This guide compares the three primary approaches to managing process resource limits on modern Linux systems: **pam_limits** (the traditional `/etc/security/limits.conf` approach), **systemd resource controls** (per-service limit configuration), and **cgroup v2** (the kernel-level unified resource management framework). We cover configuration patterns, enforcement mechanisms, and which approach fits your self-hosted infrastructure.

## Why Process Resource Limits Matter

Linux processes can request system resources without any default upper bound. A misconfigured application, memory leak, or fork bomb can quickly degrade or crash an entire server. Resource limits prevent this by enforcing ceilings on:

- **Memory** — Maximum RAM usage (RSS, virtual memory, locked memory)
- **CPU** — CPU time quotas, scheduling priority, CPU affinity
- **File descriptors** — Maximum open files and sockets per process
- **Processes** — Maximum number of child processes (prevents fork bombs)
- **Disk I/O** — Read/write bandwidth and IOPS limits
- **Network** — Socket buffer sizes, connection limits

Setting appropriate limits ensures that when one service misbehaves, the rest of the server continues operating normally.

## pam_limits (limits.conf)

pam_limits is the traditional Linux resource limit system, implemented through the PAM (Pluggable Authentication Modules) framework. Limits are defined in `/etc/security/limits.conf` and apply to user sessions at login time.

### Configuration

```
# /etc/security/limits.conf
# Format: <domain> <type> <item> <value>

# Hard and soft limits for all users
*               soft    nofile          65536
*               hard    nofile          1048576
*               soft    nproc           4096
*               hard    nproc           8192

# Limits for specific users
nginx           soft    nofile          100000
nginx           hard    nofile          200000
postgres        soft    memlock         unlimited
postgres        hard    memlock         unlimited

# Group limits
@database       hard    rss             8000000
@web            soft    cpu             50000
```

### Limit Types

| Limit Item | Description | Common Values |
|-----------|-------------|--------------|
| `nofile` | Max open file descriptors | 65536–1048576 |
| `nproc` | Max processes per user | 1024–65536 |
| `memlock` | Max locked memory (KB) | unlimited for DBs |
| `rss` | Max resident set size (KB) | per-service tuning |
| `cpu` | Max CPU time (minutes) | for batch jobs |
| `core` | Max core file size | 0 (disable) or unlimited |
| `stack` | Max stack size (KB) | 8192–65536 |

### Applying and Verifying

```bash
# Check current limits for the shell
ulimit -a

# Check specific limit
ulimit -n    # file descriptors
ulimit -u    # processes

# Verify for a specific process
cat /proc/<pid>/limits
```

### Limitations of pam_limits

- **Only applies to login sessions** — Services started via systemd, cron, or init scripts do not inherit pam_limits unless explicitly configured
- **No per-service granularity** — Limits are per-user, not per-service. All processes running as user `nginx` share the same limits
- **Does not support CPU quotas** — The `cpu` limit only caps total CPU time, not CPU percentage or scheduling shares
- **No I/O bandwidth control** — Cannot limit disk read/write rates

## systemd Resource Controls

systemd provides per-service resource limits through its unit file configuration. These limits are enforced at the service level, regardless of which user runs the service.

### Configuration in Unit Files

```ini
# /etc/systemd/system/myapp.service
[Service]
# Memory limits
MemoryMax=4G
MemoryHigh=3G
MemorySwapMax=1G

# CPU limits
CPUQuota=200%
CPUWeight=100

# Process limits
TasksMax=512
LimitNOFILE=65536

# I/O limits
IOWeight=100
IOReadBandwidthMax=/dev/sda 50M
IOWriteBandwidthMax=/dev/sda 30M
```

Apply changes:

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Restart the service with new limits
sudo systemctl restart myapp

# Set limits at runtime without editing unit files
sudo systemctl set-property myapp.service MemoryMax=2G
sudo systemctl set-property myapp.service CPUQuota=150%
```

### Key systemd Resource Control Directives

| Directive | Description | Example |
|-----------|-------------|---------|
| `MemoryMax` | Hard memory limit (OOM killed if exceeded) | `MemoryMax=4G` |
| `MemoryHigh` | Soft memory limit (throttled before OOM) | `MemoryHigh=3G` |
| `CPUQuota` | Maximum CPU usage percentage | `CPUQuota=200%` (2 cores) |
| `CPUWeight` | Relative CPU priority (1–10000) | `CPUWeight=100` |
| `TasksMax` | Maximum number of processes/threads | `TasksMax=512` |
| `LimitNOFILE` | Maximum open file descriptors | `LimitNOFILE=65536` |
| `IOWeight` | Relative I/O priority (1–10000) | `IOWeight=100` |
| `IOReadBandwidthMax` | Max read bandwidth per device | `IOReadBandwidthMax=/dev/sda 50M` |

### Monitoring Resource Usage

```bash
# Show resource usage for a service
systemctl status myapp.service

# Detailed resource accounting
systemd-cgtop

# Memory usage breakdown
systemctl show myapp.service --property=MemoryCurrent

# CPU usage
systemctl show myapp.service --property=CPUUsageNSec
```

## cgroup v2

cgroup v2 (Control Groups version 2) is the kernel-level resource management framework that underlies both pam_limits and systemd. It provides a unified hierarchy for managing CPU, memory, I/O, and other resources across process groups.

### Understanding the cgroup v2 Hierarchy

cgroup v2 uses a single unified hierarchy at `/sys/fs/cgroup/`:

```bash
# View the cgroup tree
mount | grep cgroup
ls /sys/fs/cgroup/

# View cgroup controllers available
cat /sys/fs/cgroup/cgroup.controllers
# Output: cpu cpuset io memory pids rdma
```

### Creating and Configuring cgroups

```bash
# Create a cgroup for a specific workload
sudo mkdir /sys/fs/cgroup/myworkload

# Enable controllers for this cgroup
echo "+cpu +memory +io +pids" | sudo tee /sys/fs/cgroup/cgroup.subtree_control

# Set memory limit (hard limit)
echo "4294967296" | sudo tee /sys/fs/cgroup/myworkload/memory.max
# 4GB = 4 * 1024 * 1024 * 1024 = 4294967296 bytes

# Set memory pressure threshold (soft limit)
echo "3221225472" | sudo tee /sys/fs/cgroup/myworkload/memory.high
# 3GB soft limit

# Set CPU weight (1–10000, default 100)
echo "200" | sudo tee /sys/fs/cgroup/myworkload/cpu.weight

# Set max CPU bandwidth (period + quota in microseconds)
echo "100000 200000" | sudo tee /sys/fs/cgroup/myworkload/cpu.max
# 200ms quota per 100ms period = 200% CPU (2 cores)

# Set I/O weight
echo "254:0 500" | sudo tee /sys/fs/cgroup/myworkload/io.weight
# Major:minor device weight

# Add processes to the cgroup
echo <pid> | sudo tee /sys/fs/cgroup/myworkload/cgroup.procs
```

### Monitoring cgroup Usage

```bash
# Memory usage
cat /sys/fs/cgroup/myworkload/memory.current
cat /sys/fs/cgroup/myworkload/memory.events

# CPU usage
cat /sys/fs/cgroup/myworkload/cpu.stat

# I/O usage
cat /sys/fs/cgroup/myworkload/io.stat

# Process count
cat /sys/fs/cgroup/myworkload/pids.current
```

## Comparison: pam_limits vs systemd vs cgroup v2

| Feature | pam_limits | systemd Resource Controls | cgroup v2 |
|---------|-----------|-------------------------|-----------|
| **Scope** | Per-user login sessions | Per-service units | Arbitrary process groups |
| **Configuration** | `/etc/security/limits.conf` | Unit files or `systemctl set-property` | `/sys/fs/cgroup/` filesystem |
| **Memory Limits** | RSS only (via `rlimit`) | Hard + soft (MemoryMax + MemoryHigh) | Hard + soft (memory.max + memory.high) |
| **CPU Limits** | Total time only | Quota + weight | Quota + weight + CPUSET |
| **I/O Limits** | None | Bandwidth + weight + IOPS | Bandwidth + weight + IOPS |
| **Process Limits** | Per-user nproc | TasksMax per service | pids.max per cgroup |
| **Runtime Changes** | No (requires re-login) | Yes (`systemctl set-property`) | Yes (write to cgroup files) |
| **Persistence** | File-based (limits.conf) | Unit file-based | Requires recreation after reboot |
| **Ease of Use** | Simple for basic limits | Excellent for services | Complex, requires scripting |
| **Granularity** | User-level | Service-level | Process group-level |

## Why Self-Host Resource Limit Management?

For self-hosted infrastructure, resource limit management is the foundation of server stability. Without proper limits, a single misbehaving service can cascade into a full system outage.

**Preventing resource starvation.** In a self-hosted environment where multiple services share the same hardware, resource limits ensure fair allocation. Your database gets guaranteed memory, your web server gets CPU quota, and your monitoring agent gets I/O bandwidth — even when one service experiences a spike. For related system resource management, see our [Linux OOM prevention guide](../2026-05-27-self-hosted-linux-oom-prevention-earlyoom-systemd-oomd-psi-guide/) which covers what happens when memory limits are exceeded.

**Cost-effective multi-tenancy.** Resource limits enable safe multi-tenant hosting on shared hardware. By capping each tenant's CPU, memory, and I/O, you can pack more services onto a single server without risking noisy neighbor problems. This eliminates the need for dedicated hardware per service.

**Operational predictability.** With systemd resource controls or cgroup v2 limits in place, you can predict exactly how much of each resource a service will consume under load. This makes capacity planning straightforward — you know that a 16 GB server can safely host four services with 3 GB MemoryMax each, with 4 GB reserved for the OS.

**No vendor lock-in.** Linux cgroups and systemd are open-source and built into every major distribution. Unlike container orchestration platforms that require specific runtimes, cgroup v2 works with any process — containers, VMs, or bare-metal applications. For related process isolation techniques, see our [PID namespace isolation guide](../2026-05-24-self-hosted-linux-pid-namespace-isolation-unshare-bubblewrap-nsenter-guide/).

## Best Practices for Production

1. **Set MemoryHigh before MemoryMax** — MemoryHigh acts as a soft limit that triggers memory reclaim and throttling before the OOM killer activates. Set it to ~75% of MemoryMax for graceful degradation:
   ```ini
   [Service]
   MemoryHigh=3G
   MemoryMax=4G
   ```

2. **Use CPUWeight instead of CPUQuota for general services** — CPUWeight allows services to burst beyond their allocation when CPU is idle, while CPUQuota enforces a hard ceiling. Use weight for services that benefit from burst capacity.

3. **Set TasksMax for all internet-facing services** — Fork bombs and connection storms can create thousands of processes. Set a reasonable TasksMax:
   ```ini
   [Service]
   TasksMax=1024
   ```

4. **Monitor resource usage before setting limits** — Use `systemd-cgtop` and `systemctl show` to understand current usage patterns before capping resources. Setting limits too low will cause service degradation.

5. **Test limit changes in staging** — Always verify that new resource limits do not break application functionality. Test on a staging server with production-like load before deploying to production.

## FAQ

### What is the difference between MemoryMax and MemoryHigh in systemd?

MemoryMax is a hard limit — if the service exceeds it, the kernel OOM killer terminates the process immediately. MemoryHigh is a soft limit — when exceeded, the kernel aggressively reclaims memory from the cgroup and throttles allocation, but does not kill the process. Use MemoryHigh as a warning threshold and MemoryMax as a safety ceiling.

### Does pam_limits apply to systemd services?

By default, no. systemd services do not go through the PAM login stack, so `/etc/security/limits.conf` does not affect them. However, you can enable PAM for systemd services by setting `PAMName=login` in the `[Service]` section of a unit file, though this is rarely recommended. Use systemd's native resource controls instead.

### Can I set cgroup v2 limits persistently without systemd?

Not directly. cgroup v2 hierarchy is recreated at each boot. For persistent cgroup configuration without systemd, you need a startup script that creates cgroups and sets limits, or use a tool like `cgmanager` or `libcgroup`'s `cgconfig` service.

### How do I find which cgroup a process belongs to?

```bash
cat /proc/<pid>/cgroup
```
This shows the cgroup path for each controller. In cgroup v2, all controllers share a single hierarchy, so there will be one path.

### What happens when a service exceeds its MemoryMax limit?

The kernel's OOM killer terminates the offending process within that cgroup. systemd will restart the service according to its `Restart=` directive. Check `journalctl -u myapp.service` for OOM kill messages. To prevent restart storms, consider also setting `MemoryHigh` to trigger graceful memory reclaim before hitting the hard limit.

### Is cgroup v2 enabled by default on my distribution?

Most modern distributions enable cgroup v2 by default: Ubuntu 22.04+, Fedora 31+, Debian 11+, RHEL 9+. Check with `stat -fc %T /sys/fs/cgroup/` — if it returns `cgroup2fs`, cgroup v2 is active. If it returns `tmpfs`, cgroup v1 is in use.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Process Resource Limits: systemd vs pam_limits vs cgroup v2 (2026)",
  "description": "Comprehensive comparison of pam_limits, systemd resource controls, and cgroup v2 for managing Linux process resource limits. Includes configuration examples, monitoring tools, and production best practices.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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
