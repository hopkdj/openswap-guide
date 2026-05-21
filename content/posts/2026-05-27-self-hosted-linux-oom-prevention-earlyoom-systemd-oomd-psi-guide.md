---
title: "Self-Hosted Linux OOM Prevention: earlyoom vs systemd-oomd vs PSI Monitors (2026)"
date: "2026-05-27"
tags: ["linux", "monitoring", "containers", "system-administration", "reliability"]
draft: false
---

The Linux Out-Of-Memory (OOM) killer is a last-resort mechanism that terminates processes when the system runs out of memory. By the time it activates, your services are already degraded — swap is exhausted, page reclaim has failed, and the system may be completely unresponsive. The OOM killer's heuristic process selection often terminates the wrong service, taking down your database while leaving memory-leaking background processes alive.

Early OOM prevention daemons solve this by monitoring memory pressure **before** the kernel OOM killer activates. They detect memory exhaustion trends and gracefully terminate the least-critical processes before the system becomes unresponsive.

This guide compares three self-hosted OOM prevention approaches: **earlyoom** (standalone daemon), **systemd-oomd** (systemd-integrated), and **PSI-based monitoring** (Pressure Stall Information). We'll cover deployment, configuration, and Docker Compose setups for container environments.

## Why Early OOM Prevention Matters

The default Linux OOM killer has several problems for production servers:

1. **Reactive, not proactive** — It only triggers when memory is already exhausted, often after the system has been swapping for minutes
2. **Heuristic victim selection** — The OOM score calculation doesn't understand your service priorities. It might kill PostgreSQL while keeping a memory-leaking cron job alive
3. **System unresponsiveness** — By the time OOM killer activates, the system may be too slow to respond to SSH or health checks, triggering cascading failures
4. **No graceful shutdown** — OOM killer sends SIGKILL (unblockable), giving processes no chance to save state or close connections

Early OOM prevention daemons monitor memory availability trends and act **before** the system reaches critical levels. They can:
- Send SIGTERM first (graceful shutdown), then SIGKILL if needed
- Target specific processes based on your configuration
- Alert your monitoring system before killing anything
- Use PSI metrics to detect memory pressure before actual exhaustion

For broader system reliability, see our [container runtime security comparison](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide/) and [container seccomp profile management guide](../2026-05-10-container-seccomp-profile-management-apparmor-firejail-guide/).

## Comparison: earlyoom vs systemd-oomd vs PSI Monitors

| Feature | earlyoom | systemd-oomd | PSI-based monitors |
|---------|----------|-------------|-------------------|
| **Trigger mechanism** | Available memory % | Memory pressure (PSI) | PSI (Pressure Stall Information) |
| **Kill signal** | SIGTERM then SIGKILL | SIGTERM (cgroup-level) | Configurable |
| **Victim selection** | Highest RSS process | cgroup with highest pressure | Configurable |
| **Configuration** | CLI flags + systemd unit | Drop-in config file | Custom scripts / exporters |
| **cgroup v2 support** | Yes | Yes (native) | Yes (native) |
| **Container awareness** | Basic (can exclude by name) | Full (cgroup-aware) | Full (cgroup-aware) |
| **Notification support** | Email, webhook, syslog | Journal only | Prometheus, alertmanager |
| **Package availability** | Most distros | systemd 247+ | Kernel 4.20+ (PSI) |
| **Resource usage** | ~2 MB RAM | ~3 MB RAM | Varies (depends on implementation) |
| **Best for** | Simple servers, desktops | systemd-based servers, containers | Advanced monitoring, K8s |

## earlyoom: Simple Standalone OOM Prevention

earlyoom is a lightweight daemon that monitors available memory and swap, killing the largest memory consumer when levels drop below configured thresholds.

### Installation

```bash
# Ubuntu/Debian
apt install earlyoom

# RHEL/CentOS/Fedora
dnf install earlyoom

# From source
git clone https://github.com/rfjakob/earlyoom.git
cd earlyoom && make && make install
```

### Configuration

```ini
# /etc/default/earlyoom (Debian/Ubuntu)
EARLYOOM_ARGS="-m 5 -s 10 -r 60 --prefer '(java|node)' --avoid '(sshd|postgres)'"
```

| Flag | Description |
|------|-------------|
| `-m 5` | Trigger when available memory drops below 5% |
| `-s 10` | Trigger when swap drops below 10% |
| `-r 60` | Report memory status every 60 seconds |
| `--prefer` | Regex for processes to prefer killing |
| `--avoid` | Regex for processes to avoid killing |

### Docker Compose Deployment

For container hosts running Docker Compose, earlyoom runs as a privileged container with access to the host's `/proc`:

```yaml
version: "3.8"
services:
  earlyoom:
    image: ghcr.io/rfjakob/earlyoom:latest
    container_name: earlyoom
    restart: unless-stopped
    pid: host
    privileged: true
    environment:
      EARLYOOM_ARGS: >-
        -m 5
        -s 10
        -r 30
        --prefer '(node|java|python)'
        --avoid '(sshd|dockerd|containerd)'
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
```

### Monitoring earlyoom

earlyoom logs to syslog by default. Check for OOM prevention events:

```bash
journalctl -u earlyoom --since "1 hour ago"
# Example output:
# earlyoom[1234]: mem 4.2% < avail 5.0%: sending SIGTERM to process 5678 java
# earlyoom[1234]: mem 3.1% < avail 5.0%: sending SIGKILL to process 5678 java
```

For Prometheus monitoring, pair earlyoom with the `node_exporter` textfile collector to expose earlyoom metrics.

## systemd-oomd: Integrated Memory Pressure Management

systemd-oomd is built into systemd (v247+) and uses PSI (Pressure Stall Information) metrics to detect memory pressure. Unlike earlyoom's percentage-based triggers, systemd-oomd responds to actual memory stall times — the time processes spend waiting for memory allocation.

### How PSI Works

PSI metrics (available since Linux 4.20) measure how long processes are stalled waiting for resources:

```bash
# Read PSI memory pressure stats
cat /proc/pressure/memory

# Output:
# some avg10=0.00 avg60=0.00 avg300=0.00 total=1234567
# full avg10=0.15 avg60=0.08 avg300=0.03 total=987654
```

- **`some`**: Time when some tasks are stalled on memory allocation
- **`full`**: Time when ALL non-idle tasks are stalled (system-wide memory pressure)
- **`avg10/60/300`**: Average stall percentage over 10/60/300 seconds
- **`total`**: Cumulative stall time in microseconds

systemd-oomd monitors the `full` metric — when all tasks are stalled, the system is effectively unresponsive.

### Configuration

```ini
# /etc/systemd/oomd.conf
[OOM]
DefaultMemoryPressureDurationSec=5
DefaultMemoryPressureThresholdSec=60

# Per-service override: /etc/systemd/oomd.conf.d/override.conf
[Service]
MemoryPressureLimitSec=30
```

### cgroup-Level OOM Control

systemd-oomd works at the cgroup level, making it ideal for container environments:

```bash
# Check which cgroups are under oomd management
busctl get-property org.freedesktop.oom1 /org/freedesktop/oom1   org.freedesktop.oom1.MemoryPressureThreshold

# View OOM killer settings for a cgroup
cat /sys/fs/cgroup/system.slice/memory.oom.group
# 0 = per-process OOM kill
# 1 = kill all processes in cgroup together
```

### Docker Compose with systemd-oomd Awareness

Configure your containers to work with systemd-oomd's cgroup-level killing:

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:latest
    restart: unless-stopped
    mem_limit: 512m
    memswap_limit: 512m
    # OOM kill the entire container if any process triggers it
    oom_kill_disable: false
    ports:
      - "8080:80"

  database:
    image: postgres:15
    restart: unless-stopped
    mem_limit: 1g
    memswap_limit: 1g
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - pg_data:/var/lib/postgresql/data

volumes:
  pg_data:
```

### Enabling systemd-oomd

```bash
# Check if oomd is running
systemctl status systemd-oomd

# Enable and start
systemctl enable --now systemd-oomd

# Verify it's monitoring cgroups
oomctl

# Output shows:
# Daemon:
#   Mem Pressure Watch: /system.slice
#   Swap Pressure Watch: /system.slice
#   Default Memory Pressure Limit: 60.00%
#   Default Memory Pressure Duration Sec: 5.000000
```

## PSI-Based Custom Monitors

For advanced use cases, you can build custom OOM prevention monitors using PSI metrics directly from `/proc/pressure/`.

### Simple PSI Monitor Script

```bash
#!/bin/bash
# psi-oom-monitor.sh - Custom PSI-based OOM prevention

THRESHOLD=30  # 30% memory pressure over 10 seconds
CHECK_INTERVAL=5

while true; do
    # Parse PSI full avg10 value
    PSI_FULL=$(awk '/^full/ {print $2}' /proc/pressure/memory | cut -d= -f2)
    
    # Compare with threshold (bc for floating point)
    if (( $(echo "$PSI_FULL > $THRESHOLD" | bc -l) )); then
        echo "$(date): HIGH memory pressure detected: ${PSI_FULL}%"
        
        # Find the largest memory consumer (excluding critical services)
        VICTIM=$(ps aux --sort=-%mem | awk 'NR==2 && !/sshd|systemd|dockerd/ {print $2, $11, $6/1024"MB"}')
        
        if [ -n "$VICTIM" ]; then
            PID=$(echo "$VICTIM" | awk '{print $1}')
            echo "Sending SIGTERM to PID $PID ($VICTIM)"
            kill -TERM "$PID"
            sleep 5
            # If still running, SIGKILL
            if kill -0 "$PID" 2>/dev/null; then
                echo "SIGKILL to PID $PID"
                kill -KILL "$PID"
            fi
        fi
    fi
    
    sleep "$CHECK_INTERVAL"
done
```

### PSI Exporter for Prometheus

For Kubernetes and monitoring-centric environments, run a PSI exporter:

```yaml
# docker-compose.yml for PSI exporter
version: "3.8"
services:
  psi-exporter:
    image: prom/node-exporter:latest
    container_name: psi-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.pressure'
```

Prometheus alert rule for PSI memory pressure:

```yaml
# prometheus-rules.yml
groups:
- name: memory-pressure
  rules:
  - alert: HighMemoryPressure
    expr: node_pressure_memory_waiting_seconds_total / 10 > 0.3
    for: 10s
    labels:
      severity: critical
    annotations:
      summary: "High memory pressure on {{ $labels.instance }}"
      description: "Memory stall time is {{ $value }}% over 10 seconds"
```

## Container-Specific OOM Prevention

When running containers, OOM prevention needs to work at the container level, not just the host level.

### Docker OOM Score Adjustments

Set OOM score adjustments per container to influence which containers get killed first:

```yaml
version: "3.8"
services:
  critical-db:
    image: postgres:15
    oom_score_adj: -500  # Least likely to be killed
    mem_limit: 2g

  web-app:
    image: nginx:latest
    oom_score_adj: 0  # Default priority
    mem_limit: 512m

  batch-worker:
    image: worker:latest
    oom_score_adj: 500  # First to be killed under memory pressure
    mem_limit: 1g
```

### Kubernetes Memory Limits and OOM

In Kubernetes, set memory requests and limits to ensure the scheduler places pods correctly and the kubelet manages OOM:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: memory-critical-pod
spec:
  containers:
  - name: app
    image: myapp:latest
    resources:
      requests:
        memory: "256Mi"
      limits:
        memory: "512Mi"
    # OOM kill the entire pod if any container exceeds limits
    terminationMessagePolicy: FallbackToLogsOnError
```

## Choosing the Right OOM Prevention Strategy

**For simple Linux servers:** earlyoom is the easiest to deploy and configure. It works on any Linux distribution, requires minimal configuration, and handles the most common scenario: preventing system-wide lockups from runaway processes.

**For systemd-based infrastructure:** systemd-oomd is the most integrated option. It uses PSI metrics for accurate pressure detection, works at the cgroup level (perfect for containers), and requires no additional packages on modern systemd distributions.

**For Kubernetes and monitoring-centric environments:** PSI-based custom monitors give you the most flexibility. Export pressure metrics to Prometheus, set up alerting rules, and integrate with your existing incident response workflows. This approach is best when you need fine-grained control over which processes get killed and when.

## FAQ

### What is the difference between earlyoom and the kernel OOM killer?

The kernel OOM killer is a reactive mechanism that activates only when the system has zero available memory and swap is exhausted. It sends SIGKILL (unblockable) to the process with the highest OOM score. earlyoom is a proactive userspace daemon that monitors available memory percentages and kills processes **before** the system reaches zero. It sends SIGTERM first (allowing graceful shutdown), then SIGKILL if the process doesn't exit within a timeout.

### Does systemd-oomd work without PSI support?

No. systemd-oomd requires kernel PSI (Pressure Stall Information) support, which was introduced in Linux 4.20. Most modern distributions (Ubuntu 20.04+, RHEL 9+, Debian 11+) ship with kernels that support PSI. Verify with: `cat /proc/pressure/memory`. If this file doesn't exist, your kernel doesn't support PSI.

### Can earlyoom and systemd-oomd run together?

It is not recommended. Both daemons monitor memory and may try to kill the same processes, creating race conditions. Choose one: use systemd-oomd on systems with systemd 247+ and PSI support, or earlyoom on older systems or non-systemd distributions.

### How do I prevent OOM killer from terminating my database?

Three approaches:
1. **OOM score adjustment**: Set `oom_score_adj=-1000` (via `systemd` unit or container config) to make the process immune to the OOM killer. Note: this also prevents earlyoom from killing it unless explicitly configured.
2. **Memory limits**: Set strict `mem_limit` in Docker or `resources.limits.memory` in Kubernetes so the container is killed before affecting the host.
3. **earlyoom --avoid flag**: Configure earlyoom to avoid processes matching specific patterns: `--avoid '(postgres|mysql|mongod)'`.

### What PSI threshold should I use for production servers?

The `full` metric's `avg10` (10-second average) is the most responsive indicator. A threshold of 30-60% means that for 10 seconds, 30-60% of non-idle time is spent stalled on memory allocation. Start with 60% and lower it if you experience system unresponsiveness before the OOM prevention triggers. Monitor the metric over a week to understand your server's normal pressure patterns before setting thresholds.

### Can OOM prevention daemons work inside containers?

Yes, but with limitations. The daemon needs access to `/proc/pressure/memory` for PSI metrics (requires `CAP_SYS_ADMIN` or running on a kernel with unprivileged PSI access). earlyoom can run inside a container with `--privileged` or by mounting `/proc` from the host. For Kubernetes, it is more effective to run OOM prevention at the node level (as a DaemonSet) rather than inside individual pods.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux OOM Prevention: earlyoom vs systemd-oomd vs PSI Monitors (2026)",
  "description": "Compare self-hosted OOM prevention daemons — earlyoom, systemd-oomd, and PSI-based monitors — with Docker Compose configs, Kubernetes settings, and production configurations.",
  "datePublished": "2026-05-27",
  "dateModified": "2026-05-27",
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
