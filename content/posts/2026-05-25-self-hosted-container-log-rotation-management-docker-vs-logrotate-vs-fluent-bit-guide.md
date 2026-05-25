---
title: "Self-Hosted Container Log Rotation Management: Docker JSON-File vs Logrotate vs Fluent Bit"
date: "2026-05-25"
tags: ["containers", "docker", "logging", "log-management", "self-hosted"]
draft: false
---

Container logs grow without bounds unless actively managed. A single busy web server container can generate gigabytes of log data per day through stdout/stderr output, access logs, and application debug messages. Without proper rotation policies, container logs consume all available disk space, causing container crashes, host instability, and data loss.

This guide compares three approaches to container log rotation: **Docker's built-in JSON-file log driver rotation** (the simplest approach), **logrotate with container log files** (the traditional Unix approach adapted for containers), and **Fluent Bit log forwarding with rotation** (the modern log aggregation approach). We cover configuration, deployment patterns, and trade-offs for each.

## The Container Log Problem

Docker stores container logs as JSON files on the host filesystem by default:

```
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

Each log entry is a JSON object with timestamp, stream (stdout/stderr), and log content. Without rotation limits, this file grows indefinitely. A container writing 1 MB/minute produces 1.4 GB per day and 43 GB per month.

The consequences of unmanaged container logs include:

- **Disk exhaustion** — `/var/lib/docker` fills up, causing all containers to fail
- **Performance degradation** — large log files slow down `docker logs` commands
- **Backup overhead** — large files increase backup times and storage costs
- **Compliance risk** — unrotated logs may contain sensitive data beyond retention requirements

## Docker JSON-File Log Driver Rotation

Docker's default JSON-file log driver includes built-in rotation via `max-size` and `max-file` options. This is the simplest approach — no additional software required.

### Per-Container Configuration

Set log rotation options when starting a container:

```bash
docker run -d   --log-driver json-file   --log-opt max-size=10m   --log-opt max-file=3   --name myapp   nginx:alpine
```

This configuration keeps at most 3 rotated files of 10 MB each, limiting total log storage to 30 MB per container.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  web:
    image: nginx:alpine
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    ports:
      - "80:80"
    restart: unless-stopped

  api:
    image: node:18-alpine
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
    restart: unless-stopped
```

### Docker Daemon-Wide Default Configuration

Set global defaults in `/etc/docker/daemon.json` so all containers inherit rotation policies:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

After updating `daemon.json`, restart the Docker daemon:

```bash
systemctl restart docker
```

Note: This only affects new containers. Existing containers retain their original log configuration.

### Verifying Log Rotation

```bash
# Check log driver and options for a running container
docker inspect --format='{{.HostConfig.LogConfig}}' myapp

# Check actual log file sizes
du -sh /var/lib/docker/containers/*/*-json.log | sort -rh | head -10

# Manually rotate a container's logs
docker logs --details myapp  # View logs
ls -la /var/lib/docker/containers/*/  # Check rotation files (.1, .2, etc.)
```

## Logrotate for Container Logs

logrotate is the standard Unix log rotation utility. While Docker's built-in rotation handles the JSON-file driver, logrotate becomes necessary when using the `local` log driver or when logs are written to custom paths.

### Logrotate Configuration for Docker Logs

```bash
# /etc/logrotate.d/docker-containers
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    size 50M
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxage 30
}
```

### Logrotate for Custom Application Logs

When containers mount host directories for application logs:

```bash
# /etc/logrotate.d/app-logs
/opt/containers/*/logs/*.log {
    daily
    rotate 14
    size 100M
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        # Signal container to reopen log files
        docker kill --signal=USR1 myapp 2>/dev/null || true
    endscript
}
```

### Logrotate with Docker Compose Volumes

```yaml
version: "3.8"
services:
  app:
    image: myapp:latest
    volumes:
      - /opt/containers/app/logs:/var/log/myapp
    logging:
      driver: local
      options:
        max-size: "10m"
        max-file: "5"
    restart: unless-stopped
```

The `local` log driver uses a binary format that is more space-efficient than JSON-file and works well with logrotate.

### Running Logrotate in a Container

For container-native log rotation, run logrotate as a sidecar:

```yaml
version: "3.8"
services:
  logrotator:
    image: blacklabelops/logrotate
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers
      - ./logrotate.conf:/etc/logrotate.d/docker:ro
    environment:
      - LOGROTATE_SCHEDULE=daily
      - LOGROTATE_SIZE=50M
      - LOGROTATE_ROTATE=7
    restart: unless-stopped
```

## Fluent Bit Log Forwarding with Rotation

Fluent Bit is a lightweight log processor and forwarder that consumes container logs, processes them (parsing, filtering, enriching), and forwards them to destination systems (Loki, Elasticsearch, S3). It handles log rotation implicitly by consuming and forwarding logs in real-time.

### Fluent Bit Docker Compose Deployment

```yaml
version: "3.8"
services:
  fluent-bit:
    image: cr.fluentbit.io/fluent/fluent-bit:latest
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf:ro
      - ./parsers.conf:/fluent-bit/etc/parsers.conf:ro
    restart: unless-stopped
    network_mode: host

  web:
    image: nginx:alpine
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: web.access
    ports:
      - "80:80"
    restart: unless-stopped
```

### Fluent Bit Configuration

```ini
# fluent-bit.conf
[SERVICE]
    Flush        5
    Daemon       off
    Log_Level    info
    Parsers_File parsers.conf

[INPUT]
    Name             forward
    Listen           0.0.0.0
    Port             24224
    Buffer_Chunk_Size 1M
    Buffer_Max_Size  6M

[INPUT]
    Name             tail
    Path             /var/lib/docker/containers/*/*-json.log
    Parser           docker
    Tag              docker.*
    Refresh_Interval 5
    Rotate_Wait      30

[FILTER]
    Name             parser
    Match            docker.*
    Key_Name         log
    Parser           json
    Reserve_Data     On

[OUTPUT]
    Name             file
    Match            *
    Path             /var/log/fluent-bit
    File             container-logs
    Append           true
    Format           json
    # Built-in rotation
    Rotate           7
    Rotate_Size      50M
```

### Fluent Bit Output to Loki

For Grafana Loki integration:

```ini
[OUTPUT]
    Name          loki
    Match         *
    Url           http://loki:3100/loki/api/v1/push
    Labels        job=container-logs,host=${HOSTNAME}
    LabelKeys     container_name,com.docker.compose.service
    RemoveKeys    stream
    Auto_Kubernetes_Labels false
```

### Fluent Bit Output to File with Rotation

Fluent Bit's file output includes built-in rotation:

```ini
[OUTPUT]
    Name          file
    Match         *
    Path          /var/log/containers
    File          logs
    Format        json
    Rotate        14
    Rotate_Size   100M
```

This keeps 14 rotated files of up to 100 MB each — equivalent to 1.4 GB total.

## Comparison Table

| Feature | Docker JSON-File Rotation | logrotate | Fluent Bit |
|---------|--------------------------|-----------|------------|
| **Setup Complexity** | Minimal (daemon.json) | Moderate (config files) | Higher (pipeline config) |
| **Disk Space Control** | max-size + max-file | size/rotate directives | Rotate + external forwarding |
| **Log Format** | JSON (parsed) | Original format | Transformed/parsed |
| **Real-time Forwarding** | No | No | Yes (native) |
| **Log Parsing** | Via `docker logs` only | No | Yes (parsers, regex, Lua) |
| **Centralized Storage** | Local only | Local only | Loki, ES, S3, etc. |
| **Resource Usage** | Lowest | Low | Low-Moderate |
| **Container Awareness** | Per-container options | Path-based (manual tagging) | Auto container metadata |
| **Compression** | No | gzip built-in | gzip at destination |
| **Retention Policy** | File count only | Time + size + count | Flexible (per output) |
| **Multi-host** | No | No | Yes (agent per host) |
| **Best For** | Single-host, simple setups | Unix admins, custom paths | Log aggregation pipelines |

## Choosing the Right Log Rotation Approach

**Use Docker JSON-File rotation when:**
- You run a single Docker host with a small number of containers
- You only need basic disk space protection
- You view logs via `docker logs` and do not need centralized storage
- You want zero additional dependencies

**Use logrotate when:**
- Your containers write logs to mounted host directories
- You need time-based retention (e.g., "keep 30 days of logs")
- You want compressed archived logs for compliance or auditing
- You manage both container and non-container log files with a unified rotation policy

**Use Fluent Bit when:**
- You run multiple Docker hosts and need centralized log aggregation
- You want to parse, filter, and enrich container logs before storage
- You need integration with Grafana Loki, Elasticsearch, or cloud storage
- You require real-time log streaming and alerting capabilities
- You want to reduce local disk usage by forwarding logs immediately

## Security Considerations for Container Logs

- **Sensitive data** — Container logs may contain passwords, tokens, or personal data. Configure rotation with compression and set retention periods that comply with data governance requirements.
- **Log file permissions** — Ensure `/var/lib/docker/containers/` is only readable by root or the docker group: `chmod 750 /var/lib/docker/containers/`
- **Log injection attacks** — When forwarding logs to aggregation systems, sanitize log content to prevent injection attacks in downstream log viewers or alerting systems.
- **Audit trail** — Keep rotation logs (`/var/lib/logrotate/status`) to verify that rotation is occurring as expected and detect silent failures.

## Why Self-Host Container Log Rotation?

Self-hosted container infrastructure requires deliberate log management because cloud platforms handle this transparently. On AWS ECS or Google Cloud Run, log rotation, forwarding, and retention are managed by the platform. When you run Docker on your own servers, you are responsible for preventing disk exhaustion, maintaining log accessibility, and meeting retention requirements.

Proper container log rotation is the foundation of reliable self-hosted operations. Without it, a single misbehaving container logging in a tight loop can take down your entire server by filling the disk. With it, you maintain operational visibility while keeping storage costs predictable.

For related reading on container logging infrastructure, see our [container logging drivers guide](../2026-05-25-self-hosted-container-logging-drivers-journald-vs-fluentd-vs-syslog-vs-gelf-guide/) for the driver-level perspective, and our [log aggregation comparison](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) for the aggregation pipeline side.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Log Rotation Management: Docker JSON-File vs Logrotate vs Fluent Bit",
  "description": "Prevent disk exhaustion from container logs. Compare Docker built-in rotation, logrotate, and Fluent Bit for container log management on self-hosted infrastructure.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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

## FAQ

### How do I set default log rotation for all Docker containers?

Edit `/etc/docker/daemon.json` and add the `log-opts` section with `max-size` and `max-file` values. After restarting the Docker daemon with `systemctl restart docker`, all new containers will inherit these settings. Existing containers are not affected — they must be recreated to pick up the new defaults.

### What is the difference between Docker's built-in rotation and logrotate?

Docker's built-in rotation (via `max-size` and `max-file`) only works with the JSON-file and local log drivers. It renames the current log file and creates a new one when the size limit is reached. logrotate is a general-purpose log rotation tool that can rotate any log file, including those outside Docker's management, and supports compression, time-based rotation, and custom post-rotation scripts.

### Can I use Fluent Bit with Docker's JSON-file log driver?

Yes. Fluent Bit's `tail` input plugin reads Docker's JSON log files directly from `/var/lib/docker/containers/*/*-json.log`. Alternatively, use the `fluentd` log driver in Docker to stream logs to Fluent Bit in real-time, which avoids disk I/O entirely.

### How much disk space should I allocate for container logs?

A general guideline: allocate 10-50 MB per container for `max-size`, with 3-5 rotated files. For a host running 20 containers with 10 MB max-size and 3 files, total log storage is 600 MB. Adjust based on log volume — high-traffic web servers may need 50-100 MB per container.

### Do I need Fluent Bit if I only have one Docker host?

Not necessarily. For a single Docker host with fewer than 10 containers, Docker's built-in JSON-file rotation is usually sufficient. Add Fluent Bit when you need centralized log aggregation across multiple hosts, log parsing and enrichment, or integration with monitoring dashboards like Grafana.

### How do I prevent container logs from filling the disk during a log storm?

Set conservative `max-size` limits (e.g., 10 MB) and enable monitoring alerts for `/var/lib/docker` disk usage. Use the `local` log driver with rotation as a fallback, or configure Fluent Bit with the `throttle` filter to limit log ingestion rates during abnormal conditions. Also consider using Docker's `--log-opt max-file=1` as a hard limit to ensure only one rotated file exists.

