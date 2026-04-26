---
title: "Logrotate vs s6-log vs svlogd: Best Self-Hosted Log Rotation Tools 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "logging", "sysadmin"]
draft: false
description: "Compare logrotate, s6-log, and svlogd — the three leading open-source log rotation tools for self-hosted servers. Practical installation guides, configuration examples, and performance benchmarks."
---

Every self-hosted server generates log files. Left unchecked, these logs consume disk space, degrade performance, and make troubleshooting harder. Log rotation is the fundamental sysadmin practice of archiving, compressing, and deleting old log files on a schedule. But which tool should you use?

In this guide, we compare three proven open-source log rotation approaches: **logrotate** (the universal standard), **s6-log** (modern supervision-suite logger), and **svlogd** (runit's reliable logger). Each has a fundamentally different design philosophy, and understanding these differences helps you choose the right tool for your infrastructure.

## Why Log Rotation Matters for Self-Hosted Servers

Without log rotation, a busy server can fill its disk in days. A single nginx access log on a medium-traffic site grows 500MB–2GB per day. Application logs from services like [rsyslog or Vector](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) compound the problem. The consequences of unmanaged logs include:

- **Disk exhaustion** — `/var` fills up, causing services to crash
- **Slow log analysis** — Searching 50GB monolithic log files is impractical
- **Backup bloat** — Uncompressed logs waste backup storage and bandwidth
- **Security compliance** — Many regulations (SOC 2, HIPAA) require log retention policies
- **Performance degradation** — Writing to ever-growing files causes I/O bottlenecks

Proper log rotation solves all of these by automatically compressing old logs, enforcing retention periods, and signaling services to reopen log files after rotation.

For servers that also need tamper-evident logging for compliance, see our [log integrity and audit logging guide](../2026-04-25-self-hosted-log-integrity-tamper-evident-audit-logging-guide-2026/).

## Logrotate: The Universal Standard

**logrotate** is the default log rotation tool on virtually every Linux distribution. First released in 1996, it remains the most widely deployed log rotation utility. It uses a cron-based scheduling model with a simple, declarative configuration syntax.

GitHub: [github.com/logrotate/logrotate](https://github.com/logrotate/logrotate) | ⭐ 1,519 | Updated: April 2026 | Language: C

### Installation

```bash
# Debian/Ubuntu
sudo apt install logrotate

# RHEL/CentOS/Fedora
sudo dnf install logrotate

# Alpine
sudo apk add logrotate

# Verify installation
logrotate --version
# logrotate 3.21.0
```

### Configuration

Logrotate reads configuration from `/etc/logrotate.conf` and `/etc/logrotate.d/`. Each service gets its own file in `logrotate.d/`. Here's a production-ready nginx configuration:

```bash
sudo tee /etc/logrotate.d/nginx > /dev/null << 'LOGROTATE'
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
LOGROTATE
```

**Key directives explained:**

| Directive | Purpose | Example Value |
|-----------|---------|---------------|
| `daily` / `weekly` / `monthly` | Rotation frequency | `daily` |
| `rotate N` | Number of rotated files to keep | `rotate 14` (2 weeks) |
| `compress` | gzip old rotated files | `compress` |
| `delaycompress` | Don't compress the most recent rotated file | `delaycompress` |
| `missingok` | Don't error if log file is missing | `missingok` |
| `notifempty` | Skip rotation if log is empty | `notifempty` |
| `size` | Rotate when file exceeds size | `size 100M` |
| `maxage` | Remove rotated files older than N days | `maxage 30` |
| `minsize` | Minimum file size before rotation triggers | `minsize 1M` |
| `copytruncate` | Copy then truncate (for apps that can't reopen logs) | `copytruncate` |
| `dateext` | Use date-based naming instead of numeric | `dateext` |
| `dateformat` | Format for date-based file names | `-%Y%m%d` |

### Testing and Debugging

```bash
# Dry run — shows what would happen without making changes
sudo logrotate -d /etc/logrotate.d/nginx

# Force rotation regardless of schedule
sudo logrotate -f /etc/logrotate.d/nginx

# Verbose output for troubleshooting
sudo logrotate -v /etc/logrotate.conf
```

### Cron Setup

Logrotate is typically triggered by a daily cron job at `/etc/cron.daily/logrotate`:

```bash
#!/bin/sh
/usr/sbin/logrotate /etc/logrotate.conf
EXITVALUE=$?
if [ $EXITVALUE != 0 ]; then
    logger -t logrotate "ALERT exited abnormally with [$EXITVALUE]"
fi
exit $EXITVALUE
```

For more frequent rotation (hourly), add to `/etc/cron.hourly/`:

```bash
#!/bin/sh
/usr/sbin/logrotate -f /etc/logrotate.d/high-traffic-service
```

### Docker Integration

When running services in containers, logrotate can manage logs on the host volume:

```bash
sudo tee /etc/logrotate.d/docker-apps > /dev/null << 'LOGROTATE'
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    size 50M
    copytruncate
}
LOGROTATE
```

## s6-log: Modern Supervision-Suite Logger

**s6-log** is the logging component of the [s6 supervision suite](https://github.com/skarnet/s6), a modern process supervision system designed as an alternative to systemd and supervisord. Unlike logrotate's cron-based approach, s6-log runs as a persistent daemon that automatically handles log rotation, timestamping, and archival in real-time.

GitHub: [github.com/skarnet/s6](https://github.com/skarnet/s6) | ⭐ 920 | Updated: April 2026 | Language: C

### Installation

```bash
# Debian/Ubuntu (includes s6, s6-rc, s6-linux-init)
sudo apt install s6 s6-rc s6-linux-init

# Alpine
sudo apk add s6 s6-rc

# Compile from source (recommended for latest version)
wget https://skarnet.org/software/s6/s6-2.14.1.1.tar.gz
tar xzf s6-2.14.1.1.tar.gz
cd s6-2.14.1.1
./configure
make
sudo make install
```

### How s6-log Works

s6-log operates differently from logrotate. Instead of rotating existing files on a schedule, it reads log data from a pipe (typically via `s6-log` or the `s6-fdholderd` pipeline) and manages the output files internally. The daemon handles:

- Automatic size-based rotation
- Timestamp prefixing (ISO 8601 or TAI64N)
- Automatic compression of archived logs
- Directory-based log storage
- Real-time processing (no cron dependency)

### Configuration

Create a log directory structure for your service:

```bash
# Create log directory for a service
sudo mkdir -p /etc/s6/sv/myservice/log
sudo mkdir -p /var/log/myservice

# Create the s6-log run script
sudo tee /etc/s6/sv/myservice/log/run > /dev/null << 'S6LOG'
#!/usr/bin/execlineb
exec s6-log /var/log/myservice
S6LOG

sudo chmod +x /etc/s6/sv/myservice/log/run
```

For advanced configuration with size limits, rotation count, and timestamping:

```bash
#!/usr/bin/execlineb
s6-log -t \
  n10 \
  s1000000 \
  "!w*" \
  "/var/log/myservice"
```

**s6-log options explained:**

| Option | Purpose | Example |
|--------|---------|---------|
| `-t` | Add TAI64N timestamps to each line | `-t` |
| `-n N` | Keep at most N files | `n10` (keep 10 files) |
| `-s N` | Rotate when file reaches N bytes | `s1000000` (1MB) |
| `-p mode` | Set file permissions | `-p 0640` |
| `-u uid:gid` | Set file ownership | `-u daemon:daemon` |
| `!pattern` | Exclude lines matching pattern | `"!w*"` (skip warnings) |
| `+pattern` | Include only lines matching pattern | `"+error"` |
| `!{pattern}` | Exclude and archive matching lines | `"!{debug}"` |

### Complete Service Example

Here's a full s6 service definition with logging for a web server:

```bash
# Service run script
sudo tee /etc/s6/sv/nginx/run > /dev/null << 'S6SVC'
#!/usr/bin/execlineb
fdmove -c 2 1
exec nginx -g "daemon off;"
S6SVC

# Log run script with s6-log
sudo tee /etc/s6/sv/nginx/log/run > /dev/null << 'S6LOG'
#!/usr/bin/execlineb
s6-log \
  -t \
  n30 \
  s5000000 \
  /var/log/s6-nginx
S6LOG

# Enable the service
s6-rc -u change nginx
```

This setup automatically:
1. Captures nginx stdout/stderr via the service supervisor
2. Adds TAI64N timestamps to every log line
3. Rotates when files reach 5MB
4. Keeps the last 30 rotated files
5. Runs continuously without cron

## svlogd: Runit's Simple Logger

**svlogd** is the logging daemon from the [runit](https://en.wikipedia.org/wiki/Runit) service supervision framework. It shares a similar philosophy with s6-log — real-time log processing rather than scheduled rotation — but with a simpler, more minimal design.

### Installation

```bash
# Debian/Ubuntu
sudo apt install runit

# Alpine
sudo apk add runit

# RHEL/Fedora (via EPEL)
sudo dnf install runit

# Verify
svlogd -h
```

### How svlogd Works

Like s6-log, svlogd runs as a persistent daemon that reads log data from stdin (typically piped from a service's stdout). It stores logs in a directory structure and handles rotation based on size thresholds.

### Configuration

svlogd is controlled by a `config` file in the log directory:

```bash
# Create log directory
sudo mkdir -p /etc/sv/myservice/log
sudo mkdir -p /var/log/myservice

# Create svlogd config
sudo tee /var/log/myservice/config > /dev/null << 'SVLOGD'
s1000000
n20
t
SVLOGD
```

**Config file format** (one directive per line, no spaces):

| Directive | Purpose | Example |
|-----------|---------|---------|
| `sNNN` | Maximum file size in bytes | `s1000000` (1MB per file) |
| `nNN` | Maximum number of files | `n20` (keep 20 files) |
| `t` | Add ISO 8601 timestamps | `t` |
| `!cmd` | Pipe rotated files through command | `!gzip` |
| `uNNN` | Umask for new files | `u027` |
| `pNNNN` | File permissions | `p0640` |

### Log Directory Run Script

```bash
# Create the log run script for runit
sudo tee /etc/sv/myservice/log/run > /dev/null << 'SVLOG'
#!/bin/sh
exec svlogd -tt /var/log/myservice
SVLOG

sudo chmod +x /etc/sv/myservice/log/run
```

The `-tt` flag adds timestamps and enables verbose output. The service log script simply pipes stdout to svlogd:

```bash
#!/bin/sh
exec 2>&1
exec svlogd -tt /var/log/myservice
```

### Complete Service Example with Docker

Here's a practical example running a service under runit with svlogd:

```bash
# Service run script
sudo tee /etc/sv/myapp/run > /dev/null << 'RUNSCRIPT'
#!/bin/sh
exec 2>&1
exec chpst -u appuser \
  /usr/local/bin/myapp --config /etc/myapp/config.yml
RUNSCRIPT

# Log script with svlogd
sudo tee /etc/sv/myapp/log/run > /dev/null << 'LOGSCRIPT'
#!/bin/sh
exec svlogd -tt -s 5000000 -n 30 /var/log/myapp
LOGSCRIPT

sudo chmod +x /etc/sv/myapp/run /etc/sv/myapp/log/run

# Link and start
sudo ln -s /etc/sv/myapp /etc/runit/runsvdir/current/
sudo sv start myapp
```

## Feature Comparison

| Feature | logrotate | s6-log | svlogd |
|---------|-----------|--------|--------|
| **Architecture** | Cron-based daemon | Persistent supervisor daemon | Persistent supervisor daemon |
| **Scheduling** | Time/size via cron | Real-time, size-based | Real-time, size-based |
| **Configuration** | Declarative config files | execlineb scripts | Single `config` file |
| **Compression** | gzip/bzip2/xz | Built-in gzip | Via pipe (`!gzip`) |
| **Timestamps** | `dateext` for filenames | TAI64N per-line | ISO 8601 per-line |
| **Service Integration** | postrotate signals | Native s6 supervision | Native runit supervision |
| **Pattern Filtering** | No | Yes (include/exclude) | No |
| **Learning Curve** | Low | Medium | Low |
| **Docker Friendly** | Yes (host volume) | Yes (in-container) | Yes (in-container) |
| **Dependencies** | cron | s6 supervision suite | runit |
| **Package Availability** | All major distros | Debian, Alpine, source | All major distros |
| **GitHub Stars** | 1,519 | 920 (s6 suite) | N/A (mirror repos) |

## Choosing the Right Tool

### Use logrotate when:

- You're on a standard Linux server and want the path of least resistance
- You need time-based rotation (daily, weekly, monthly)
- You want declarative configuration that any sysadmin can read
- You're managing logs for services that can't be easily supervised
- You need post-rotation hooks (compress, mail, execute scripts)

### Use s6-log when:

- You're already using the s6 supervision suite
- You want real-time log processing without cron
- You need per-line timestamping and pattern-based filtering
- You're building container images and want minimal dependencies
- You prefer the execlineb scripting approach

### Use svlogd when:

- You're using runit as your init/supervision system
- You want the simplest possible logger with minimal configuration
- You need reliable, battle-tested log rotation (runit has been stable since 2001)
- You want ISO 8601 timestamps out of the box
- You prefer shell-script-based service definitions

## Performance and Resource Usage

Resource consumption is critical for self-hosted servers running on limited hardware. Here's how the three tools compare:

```bash
# Measure logrotate resource usage (single run)
/usr/bin/time -v logrotate -f /etc/logrotate.d/nginx 2>&1 | grep -E "Maximum resident|User time|System time"

# Measure s6-log memory footprint (persistent daemon)
ps aux | grep s6-log | awk '{print $6}'  # RSS in KB

# Measure svlogd memory footprint
ps aux | grep svlogd | awk '{print $6}'  # RSS in KB
```

Typical resource usage on a production server:

| Metric | logrotate | s6-log | svlogd |
|--------|-----------|--------|--------|
| **Memory (RSS)** | 0 (runs then exits) | ~1–2 MB (persistent) | ~1–2 MB (persistent) |
| **CPU during rotation** | Brief spike (ms) | None (continuous) | None (continuous) |
| **Disk I/O pattern** | Burst during rotation | Steady, small writes | Steady, small writes |
| **Latency impact** | Milliseconds per cron run | Near-zero (background) | Near-zero (background) |

## Security Considerations

Proper log rotation is part of a comprehensive server security posture:

```bash
# Set restrictive permissions on log directories
sudo chmod 0750 /var/log/nginx
sudo chown root:adm /var/log/nginx

# For s6-log, set ownership in the log script
# s6-log -p 0640 -u daemon:adm /var/log/s6-nginx

# For svlogd, use the config file
echo "p0640" >> /var/log/myservice/config

# Verify no world-readable logs
find /var/log -perm -o+r -type f 2>/dev/null
```

For services that handle sensitive data, combine log rotation with log shipping to a centralized logging system. Our [syslog aggregation guide](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) covers forwarding rotated logs to a central server.

## FAQ

### What is the difference between logrotate and s6-log?

logrotate runs on a schedule (typically via cron) and rotates existing log files by renaming, compressing, and truncating them. s6-log runs as a persistent daemon that processes log data in real-time through a pipe, automatically managing rotation based on file size. logrotate is better for traditional server setups, while s6-log excels in service-supervision environments.

### Can I use logrotate with Docker containers?

Yes. logrotate runs on the host and can manage container log files stored on host volumes. Docker's default logging driver stores container logs at `/var/lib/docker/containers/<id>/<id>-json.log`. You can configure logrotate to manage these files using `copytruncate` since Docker doesn't support log reopen signals:

```bash
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    size 50M
    copytruncate
    missingok
}
```

Alternatively, use Docker's built-in `--log-opt max-size` and `--log-opt max-file` flags in your docker-compose configuration.

### Which log rotation tool is best for a small VPS?

For a small VPS (1–2 GB RAM), **logrotate** is the best choice. It has zero persistent memory overhead since it runs briefly via cron and exits. Both s6-log and svlogd add a persistent daemon consuming 1–2 MB of RAM, which is negligible but unnecessary if you don't already use their respective supervision suites.

### How do I rotate logs for an application that doesn't support log file reopening?

Use the `copytruncate` directive in logrotate. It copies the current log file to a new file (for rotation) and then truncates the original to zero bytes. The application continues writing to the same file descriptor without needing to be signaled:

```bash
/var/log/myapp/*.log {
    daily
    rotate 14
    compress
    copytruncate
    missingok
}
```

Note that there's a tiny window between the copy and truncate where log lines may be lost. For critical applications, use a proper signal-based rotation with `postrotate`.

### Does s6-log support log compression?

Yes, s6-log supports automatic gzip compression. You can configure it by adding the `z` option or using a processor script. The s6 package also includes `s6-fdholderd` for managing file descriptors across service restarts, which ensures logs are never lost during service transitions.

### How do I test my logrotate configuration before deploying?

Run logrotate with the `-d` (debug/dry-run) flag to see exactly what it would do without making any changes:

```bash
sudo logrotate -d /etc/logrotate.d/myservice
```

This prints a detailed report of which files would be rotated, compressed, or deleted. For a forced rotation test, use `-f` instead of `-d`, but be aware this will actually rotate the files.

### Can I use s6-log or svlogd without their full supervision suite?

Technically yes, but it's not straightforward. Both tools are designed to be fed log data through pipes from their respective supervision systems. You can manually pipe application output to them (`myapp 2>&1 | s6-log /var/log/myapp`), but you lose the automatic process management benefits. If you only need log rotation without supervision, logrotate is a better fit.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Logrotate vs s6-log vs svlogd: Best Self-Hosted Log Rotation Tools 2026",
  "description": "Compare logrotate, s6-log, and svlogd — the three leading open-source log rotation tools for self-hosted servers. Practical installation guides, configuration examples, and performance benchmarks.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
