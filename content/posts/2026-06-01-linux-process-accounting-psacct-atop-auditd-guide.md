---
title: "Self-Hosted Linux Process Accounting & Auditing: psacct vs atop vs auditd Process Tracking"
date: "2026-06-01"
tags: ["linux", "system-administration", "security", "auditing", "monitoring", "process-management"]
draft: false
---

## Introduction

Knowing exactly what ran on your server, who executed it, and how many resources it consumed is fundamental to both security auditing and capacity planning. Linux process accounting provides this forensic trail — recording every command executed, its resource usage, and termination status.

This guide compares three approaches to process accounting: **psacct** (the classic BSD-style accounting suite), **atop** (the advanced system/process monitor with daemon mode), and **auditd** (the Linux Audit Framework for security-focused process tracking). Each serves different use cases — from compliance auditing to real-time anomaly detection.

## Comparison Table

| Feature | psacct (acct) | atop (atopacctd) | auditd process tracking |
|---------|---------------|-------------------|------------------------|
| **Package** | `acct` or `psacct` | `atop` | `auditd` (built into kernel) |
| **Data Format** | Binary `/var/log/account/pacct` | Binary raw log + ASCII daily | Binary audit logs |
| **Query Tool** | `lastcomm`, `sa`, `ac` | `atop -r`, `atopsar` | `ausearch`, `aureport` |
| **Granularity** | Process exit only | Periodic sampling + exit | Syscall-level |
| **Resource Tracking** | CPU, memory, I/O | CPU, memory, disk, network | Syscall args, UID, path |
| **Overhead** | ~1-2% CPU | ~2-5% CPU (daemon) | 5-15% (config-dependent) |
| **Storage per day** | ~10-50 MB | ~50-200 MB | 100 MB - 5+ GB |
| **Best For** | Compliance, usage billing | Performance trending | Security forensics |
| **Docker Support** | Host-level | Host + container stats | Host-level |
| **Real-time Alerts** | No | Via atop's trigger | Via audisp plugins |

## psacct: Classic BSD Process Accounting

**psacct** (package name `acct` on Debian, `psacct` on RHEL) is the traditional Unix process accounting system. It records every process that terminates, who ran it, and its resource consumption.

### Installation

```bash
# Debian/Ubuntu
sudo apt install acct

# RHEL/Fedora
sudo dnf install psacct

# Enable and start
sudo systemctl enable --now acct.service
# Or: sudo /usr/sbin/accton /var/log/account/pacct
```

### Querying Accounting Data

```bash
# Show recently executed commands per user
lastcomm | head -20

# Show command summary with CPU time
sa -m

# Per-user accounting report
sa -u | head -20

# Show total connect time
ac -p

# Show daily totals
ac -d

# Find commands run by specific user
lastcomm --user www-data

# Top 10 CPU-consuming commands
sa -c | sort -rnk4 | head -10
```

### Docker-Based Process Accounting Dashboard

For centralized collection from multiple servers, deploy a web dashboard:

```yaml
version: "3.8"
services:
acct-collector:
image: alpine:latest
container_name: acct-collector
command: |
sh -c 'apk add --no-cache fcgiwrap spawn-fcgi nginx &&
spawn-fcgi -s /run/fcgiwrap.sock -u nginx -g nginx /usr/bin/fcgiwrap &&
nginx -g "daemon off;"'
volumes:
- /var/log/account:/data/acct:ro
- ./nginx-acct.conf:/etc/nginx/http.d/default.conf
ports:
- "8081:80"
```

NGINX config for the dashboard (`nginx-acct.conf`):

```nginx
server {
listen 80;
location / {
root /data;
autoindex on;
}
location /query {
fastcgi_pass unix:/run/fcgiwrap.sock;
fastcgi_param SCRIPT_FILENAME /usr/local/bin/acct-query.sh;
include fastcgi_params;
}
}
```

### Log Rotation and Retention

```bash
# /etc/logrotate.d/psacct
/var/log/account/pacct {
monthly
rotate 12
compress
missingok
postrotate
/usr/sbin/accton /var/log/account/pacct
endscript
}
```

## atop: Advanced Performance Monitor with Process Accounting

**atop** operates as both an interactive performance monitor and a daemon (`atopacctd`) that records system-wide and per-process statistics at regular intervals. Unlike psacct which waits for process exit, atop samples active processes — capturing short-lived processes that psacct might miss if they crash without proper exit accounting.

### Installation

```bash
# Debian/Ubuntu
sudo apt install atop

# Enable process accounting daemon
sudo systemctl enable --now atopacct.service

# Or: sudo atopacctd

# RHEL/Fedora
sudo dnf install atop
sudo systemctl enable --now atop
```

### Docker Deployment for Centralized Collection

```yaml
version: "3.8"
services:
atopd:
image: debian:bookworm-slim
container_name: atop-collector
pid: host
privileged: true
command: |
sh -c 'apt-get update && apt-get install -y atop cron &&
mkdir -p /var/log/atop &&
atopacctd &&
crond -f'
volumes:
- /var/log/atop:/var/log/atop
- /proc:/host-proc:ro
environment:
- INTERVAL=60
- LOGINTERVAL=600
```

### Querying atop Data

```bash
# Interactive mode (current day)
atop

# Review historical data
atop -r /var/log/atop/atop_20260601

# Process accounting summary
atopsar -c    # CPU
atopsar -m    # Memory
atopsar -d    # Disk
atopsar -p 1h # Per-command starting in last hour
```

## auditd: Security-Focused Process Tracking

**auditd** (Linux Audit Framework) records security-relevant events at the syscall level. For process accounting, it captures `execve()` syscalls along with the full command line, user ID, and terminal — providing forensic-grade detail.

### Installation

```bash
# Debian/Ubuntu
sudo apt install auditd audispd-plugins

# RHEL/Fedora
sudo dnf install audit audit-libs
```

### Process Tracking Rules

```bash
# Track all command executions
sudo auditctl -a always,exit -F arch=b64 -S execve -k process-accounting
sudo auditctl -a always,exit -F arch=b32 -S execve -k process-accounting

# Make persistent
sudo tee /etc/audit/rules.d/process-accounting.rules << 'EOF'
-a always,exit -F arch=b64 -S execve -k process-accounting
-a always,exit -F arch=b32 -S execve -k process-accounting
EOF
sudo augenrules --load
```

### Querying Process Audit Logs

```bash
# All command executions today
ausearch -k process-accounting --start today

# Commands run by a specific user
ausearch -k process-accounting -ui 1000 --start today

# Failed exec attempts
ausearch -k process-accounting --success no --start today

# Generate a process execution report
aureport -x --summary

# Per-user process report
aureport -x -u --start this-week

# Find suspicious commands
ausearch -k process-accounting | grep -E "nc|wget|curl" | aureport -x -i
```

### Prometheus Integration via audisp

```bash
# /etc/audit/plugins.d/audisp-pipe.conf
active = yes
direction = out
path = /usr/local/bin/audit-metrics.sh
type = always
format = string

# /usr/local/bin/audit-metrics.sh
#!/bin/bash
while read line; do
echo "$line" | grep -q "execve" &&         echo "audit_process_count 1" > /var/lib/node_exporter/audit.prom.tmp
done
```

## Choosing the Right Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Compliance: "track all user commands" | psacct |
| Performance: "which commands use the most CPU?" | atop + atopacctd |
| Security: "who ran that suspicious binary?" | auditd |
| Resource billing: "charge per CPU-minute" | psacct + sa |
| Real-time anomaly detection | auditd + audisp |
| Historical trending and capacity planning | atop |

## Why Self-Host Process Accounting?

Process accounting data is sensitive — it contains a complete record of every command executed on your servers, including usernames, command arguments, and timing. Keeping this data on your own infrastructure ensures it is never exposed to third-party monitoring services. Self-hosting also means you control retention policies, can integrate directly with your SIEM or logging pipeline, and avoid per-host licensing costs.

For broader security monitoring context, see our [auditd framework guide](../2026-05-16-self-hosted-linux-audit-framework-auditd-goaudit-auditbeat-guide/). For intrusion prevention, our [fail2ban comparison](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prev/) covers complementary tools.

If you need kernel-level visibility beyond process tracking, the [eBPF tracing guide](../2026-05-22-self-hosted-linux-performance-profiling-perf-bcc-tools-sysstat-guide/) covers modern observability approaches that work alongside traditional accounting.

### Integration with SIEM and Log Aggregation

Process accounting data is most valuable when centralized. Forward psacct logs via Filebeat or Vector to your Elasticsearch cluster, and configure auditd to send events via audisp to a centralized syslog server. This enables cross-server correlation — for example, detecting when the same user executes a suspicious command across multiple hosts within a short time window. The combination of psacct for resource usage, auditd for forensics, and atop for performance trending provides complete operational visibility across your fleet.

## FAQ

### Does process accounting survive a reboot?

**psacct**: Yes. The binary log file persists across reboots, and accounting resumes automatically if the service is enabled. **atop**: Yes, logs persist in `/var/log/atop/`. **auditd**: Yes, rules in `/etc/audit/rules.d/` are loaded at boot.

### How much disk space does process accounting consume?

psacct typically uses 10-50 MB per day on a moderately busy server. atop uses 50-200 MB with default intervals. auditd with full execve() logging can consume 100 MB to 5+ GB per day depending on workload — configure disk space monitoring and use `auditd`'s `max_log_file_action = rotate` to prevent disk exhaustion.

### Can I use process accounting inside Docker containers?

Process accounting runs at the host kernel level and captures all processes including those in containers. However, the UID mapping may differ between host and container namespaces. For container-specific accounting, use `docker stats` or deploy atop inside each container with host PID namespace access.

### Is psacct still maintained?

The psacct/acct package is maintained in most distribution repositories as a stable, mature tool. The upstream source (GNU acct) receives minimal updates because the on-disk format is stable and the functionality is complete. For systems requiring active development, atop is updated regularly.

### How does process accounting affect GDPR/privacy compliance?

Process accounting records constitute personal data under GDPR if they include usernames. You should: (1) document process accounting in your data processing registry, (2) configure retention periods, (3) restrict access to accounting logs, and (4) consider pseudonymizing usernames via auditd's `uid` translation or using numeric UIDs only.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到 人工智能监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测 人工智能相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
"@context": "https://schema.org",
"@type": "TechArticle",
"headline": "Self-Hosted Linux Process Accounting & Auditing: psacct vs atop vs auditd Process Tracking",
"description": "Compare Linux process accounting tools — psacct, atop (atopacctd), and auditd — with setup guides, Docker Compose configs, and integration patterns for security compliance and performance monitoring.",
"datePublished": "2026-06-01",
"dateModified": "2026-06-01",
"author": {
"@type": "Organization",
"name": "OpenSwap Guide"
},
"publisher": {
"@type": "Organization",
"name": "OpenSwap Guide",
"logo": {
"@type": "ImageObject",
"url": "https://www.pistack.xyz/logo.png"
}
}
}
</script>
