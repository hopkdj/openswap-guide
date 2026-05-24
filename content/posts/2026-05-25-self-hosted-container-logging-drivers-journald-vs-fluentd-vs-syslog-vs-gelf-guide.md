---
title: "Self-Hosted Container Logging Drivers: journald vs fluentd vs syslog vs GELF"
date: "2026-05-25"
tags: ["docker", "container-infrastructure", "logging", "observability"]
draft: false
---

Every Docker container generates stdout and stderr output — application logs, error traces, health check results, and debug information. By default, Docker stores these logs using the `json-file` driver, writing JSON-formatted entries to disk on the host. While this works for small deployments, production environments quickly outgrow this approach. Log files grow unbounded, querying requires parsing raw JSON, and there is no centralized view across multiple containers or hosts.

Docker's logging driver architecture solves this by routing container output to external logging systems at the daemon level. Instead of writing to local files, logs are forwarded directly to centralized logging infrastructure in real-time. This guide compares the four most practical logging drivers for self-hosted environments: **journald**, **fluentd**, **syslog**, and **GELF** — examining their architectures, performance characteristics, and deployment patterns.

## Overview of Container Logging Drivers

Docker logging drivers are plugins that intercept container stdout/stderr and forward the output to a destination. They operate at the Docker daemon level, meaning configuration applies per-container or globally, and logs bypass the host filesystem entirely.

### journald Driver

The **journald** driver sends container logs directly to the systemd journal via the systemd-journald service. This integrates container output with the host's existing log management infrastructure, allowing administrators to use `journalctl` for unified log querying across system services and containers.

| Attribute | Value |
|-----------|-------|
| Type | Local (systemd journal) |
| Structured logging | Yes (via journal fields) |
| Default availability | systemd-based Linux distros |
| Log rotation | Via journald configuration |
| Query interface | journalctl |

### fluentd Driver

The **fluentd** driver forwards container logs to a Fluentd daemon over TCP. Fluentd is a unified logging layer that accepts logs from multiple sources, transforms them, and routes them to various backends (Elasticsearch, S3, PostgreSQL, etc.). This driver enables sophisticated log processing pipelines.

| Attribute | Value |
|-----------|-------|
| Type | Remote (TCP to Fluentd) |
| Structured logging | Yes (JSON tags) |
| Default availability | Requires Fluentd daemon |
| Log rotation | Handled by downstream |
| Query interface | Depends on downstream storage |

### syslog Driver

The **syslog** driver sends container logs to a syslog daemon (rsyslog, syslog-ng) over TCP or UDP. This is the most traditional approach, leveraging decades of syslog infrastructure for log collection, filtering, and forwarding.

| Attribute | Value |
|-----------|-------|
| Type | Remote (TCP/UDP to syslog) |
| Structured logging | Partial (RFC 5424 supports structured data) |
| Default availability | Nearly universal |
| Log rotation | Via logrotate |
| Query interface | Depends on syslog configuration |

### GELF Driver

The **GELF** (Graylog Extended Log Format) driver sends structured log messages directly to a Graylog server or any GELF-compatible receiver over UDP or TCP. GELF was designed specifically for modern log management, supporting structured fields, compression, and chunking.

| Attribute | Value |
|-----------|-------|
| Type | Remote (UDP/TCP to GELF receiver) |
| Structured logging | Yes (native GELF format) |
| Default availability | Requires GELF receiver (Graylog, etc.) |
| Log rotation | Handled by downstream |
| Query interface | Graylog web UI |

## Comparison Table

| Feature | journald | fluentd | syslog | GELF |
|---------|----------|---------|--------|------|
| **Transport** | Local (socket) | TCP | TCP/UDP | UDP/TCP |
| **Structured fields** | Full (key-value pairs) | Full (JSON) | Partial (RFC 5424) | Full (GELF spec) |
| **Built-in rotation** | Yes (journald config) | No (downstream) | No (logrotate) | No (downstream) |
| **Compression** | Via journald (xz/lz4) | Via Fluentd plugins | No | Yes (GELF chunking) |
| **Tagging/metadata** | Container name, ID, image | Docker labels as tags | Facility-based | Custom GELF fields |
| **Performance impact** | Low (local write) | Medium (TCP overhead) | Low (UDP) to Medium (TCP) | Low (UDP) to Medium (TCP) |
| **Setup complexity** | Low (built-in) | High (Fluentd config) | Low (rsyslog config) | Medium (Graylog setup) |
| **Log buffering** | Yes (journald) | Yes (Fluentd buffer) | No (best-effort UDP) | No (best-effort UDP) |
| **TLS support** | N/A (local) | Yes | Yes | Yes |
| **Backpressure handling** | Yes (journald rate limit) | Yes (Fluentd retry) | No | No |
| **Log query interface** | journalctl | Fluentd plugins | grep/awk or downstream | Graylog web UI |
| **Docker label propagation** | Yes (as journal fields) | Yes (as log tags) | Limited | Yes (as GELF fields) |
| **Multi-host aggregation** | No (local only) | Yes | Yes | Yes |

## Configuration Examples

### journald Driver Configuration

The journald driver requires minimal setup — it is available by default on systemd-based systems:

```yaml
# docker-compose.yml with journald logging
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    logging:
      driver: journald
      options:
        tag: "webapp-{{.Name}}"
    restart: unless-stopped

  database:
    image: postgres:16-alpine
    logging:
      driver: journald
      options:
        tag: "db-{{.Name}}"
    restart: unless-stopped
```

Query container logs with journalctl:

```bash
# View all container logs
journalctl CONTAINER_NAME=webapp

# View logs for a specific container
journalctl _SYSTEMD_UNIT=docker.service CONTAINER_TAG=webapp-my-container

# Follow logs in real-time
journalctl -f CONTAINER_NAME=database

# View logs from the last hour
journalctl --since "1 hour ago" CONTAINER_NAME=webapp
```

Configure journald storage limits in `/etc/systemd/journald.conf`:

```ini
[Journal]
Storage=persistent
SystemMaxUse=2G
SystemMaxFileSize=100M
MaxRetentionSec=30day
Compress=yes
```

### fluentd Driver Configuration

Requires a running Fluentd daemon. Here is the complete setup:

```yaml
# docker-compose.yml with fluentd logging
version: "3.8"
services:
  fluentd:
    image: fluent/fluentd:v1.16-debian
    container_name: logging-fluentd
    volumes:
      - ./fluent.conf:/fluentd/etc/fluent.conf
    ports:
      - "24224:24224"
      - "24224:24224/udp"
    restart: unless-stopped

  webapp:
    image: nginx:alpine
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: "docker.webapp"
        fluentd-async: "true"
        fluentd-sub-second-precision: "true"
    restart: unless-stopped
```

Fluentd configuration (`fluent.conf`):

```xml
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

<match docker.**>
  @type file
  path /fluentd/logs/container
  append true
  <format>
    @type json
  </format>
  <buffer time>
    timekey 1d
    timekey_wait 10m
    flush_interval 30s
  </buffer>
</match>
```

### syslog Driver Configuration

```yaml
# docker-compose.yml with syslog logging
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://192.168.1.100:514"
        syslog-facility: "local0"
        tag: "docker-webapp"
        syslog-format: "rfc5424"
    restart: unless-stopped

  database:
    image: postgres:16-alpine
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://192.168.1.100:514"
        syslog-facility: "local1"
        tag: "docker-db"
        syslog-format: "rfc5424"
    restart: unless-stopped
```

rsyslog configuration to receive and separate Docker logs (`/etc/rsyslog.d/docker.conf`):

```bash
# Create separate log files per container tag
:programname, contains, "docker-webapp" /var/log/docker/webapp.log
:programname, contains, "docker-db" /var/log/docker/database.log

# Stop processing after matching
& stop
```

### GELF Driver Configuration

```yaml
# docker-compose.yml with GELF logging
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    logging:
      driver: gelf
      options:
        gelf-address: "udp://192.168.1.100:12201"
        tag: "docker-webapp"
        env: "ENVIRONMENT,APP_NAME"
        labels: "com.docker.compose.service"
    restart: unless-stopped

  api:
    image: node:20-alpine
    logging:
      driver: gelf
      options:
        gelf-address: "tcp://192.168.1.100:12201"
        gelf-compression-type: "gzip"
        tag: "docker-api"
    restart: unless-stopped
```

## Performance and Reliability Considerations

### Log Delivery Guarantees

The transport protocol determines reliability. TCP-based drivers (fluentd, syslog-TCP, GELF-TCP) provide delivery guarantees — if the receiver is temporarily unavailable, the Docker daemon buffers logs and retries. UDP-based drivers (syslog-UDP, GELF-UDP) are fire-and-forget: if the receiver is down, logs are lost. journald provides local persistence via the journal, ensuring no log loss unless the journal is corrupted or the disk fails.

### Buffer and Backpressure

When logging pipelines cannot keep up with log volume, backpressure occurs. fluentd handles this best with configurable buffer queues, retry logic, and overflow policies. journald applies rate limiting (configurable via `RateLimitIntervalSec` and `RateLimitBurst`), silently dropping excess logs rather than blocking the container. syslog and GELF have no built-in backpressure — UDP drivers silently drop messages, and TCP drivers block the container's stdout write, potentially causing application hangs.

### Resource Overhead

journald has the lowest overhead since it writes locally via a Unix socket. fluentd introduces the most overhead due to TCP connection management, serialization, and the Fluentd process itself. syslog and GELF fall in between, with UDP variants being lightweight and TCP variants adding connection management costs.

## Choosing the Right Logging Driver

- **Use journald** when running on systemd-based single hosts and want unified log management with `journalctl`. It requires zero additional infrastructure and provides the simplest setup.

- **Use fluentd** when you need sophisticated log processing pipelines — parsing, transformation, routing to multiple backends, and buffering. It is the most capable option for complex logging architectures.

- **Use syslog** when you have existing syslog infrastructure (rsyslog, syslog-ng, central log server) and want to integrate container logs without deploying new systems. UDP syslog is lightweight for high-volume, low-priority logging.

- **Use GELF** when running Graylog or a GELF-compatible log platform. It provides the best structured logging support out of the box with native field extraction, compression, and web-based querying.

For most self-hosted multi-container deployments, a common pattern is journald for local debugging and development, combined with fluentd or GELF for production log aggregation across multiple hosts.

## Why Self-Host Container Logging?

Self-hosting your container logging infrastructure ensures complete data ownership and eliminates the operational risk of shipping logs to third-party services. When logs contain sensitive application data, error traces with internal paths, or user information, external log aggregation creates compliance and privacy concerns.

- **Data sovereignty**: Logs never leave your infrastructure. You control retention policies, access controls, and deletion schedules without depending on external compliance certifications.

- **Cost predictability**: Commercial log management services (Datadog, Splunk, Sumo Logic) charge per gigabyte ingested. Self-hosted logging with journald, rsyslog, or Graylog has fixed infrastructure costs regardless of log volume.

- **Custom processing**: Self-hosted pipelines allow custom log parsing, redaction of sensitive fields, and integration with internal monitoring systems that commercial services cannot accommodate.

For centralized log collection, see our [Graylog vs Loki vs Elasticsearch guide](../2026-04-20-elk-stack-vs-loki-vs-graylog-self-hosted-log-management/).
For log forwarding infrastructure, check our [Fluent Bit vs Vector vs OTEL Collector comparison](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/).
For audit log integrity, our [tamper-evident audit logging guide](../2026-04-25-self-hosted-log-integrity-tamper-evident-audit-logging-guide/) covers it.

## FAQ

### Can I change the logging driver for a running container?

No. Docker logging drivers are configured at container creation time and cannot be changed while the container is running. To switch drivers, you must stop and remove the container, then recreate it with the new logging configuration. Docker Compose makes this straightforward — update the `logging` section in `docker-compose.yml` and run `docker compose up -d`.

### What happens to logs if the logging driver's destination is unavailable?

The behavior depends on the driver and transport. journald stores logs locally, so unavailability is not a concern. fluentd buffers logs in memory and retries delivery; if the buffer fills, it can be configured to either drop old logs or block the container (the latter risks application hangs). UDP-based syslog and GELF silently drop logs when the receiver is unavailable. TCP-based variants block the container's stdout write, potentially causing the application to hang until the connection is restored.

### Is the json-file driver ever appropriate for production?

The json-file driver can be appropriate for single-container deployments or development environments where log volume is low and centralized aggregation is not needed. However, you must configure log rotation to prevent unbounded disk growth. Add `max-size` and `max-file` options to limit total log storage:
```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "5"
```
For any multi-container or multi-host production environment, a remote logging driver is strongly recommended.

### How do I configure global default logging drivers?

Set the default logging driver in Docker's daemon configuration (`/etc/docker/daemon.json`):
```json
{
  "log-driver": "journald",
  "log-opts": {
    "tag": "{{.Name}}"
  }
}
```
Restart the Docker daemon after changing this configuration. New containers will use the default driver, while existing containers retain their original configuration.

### Does the fluentd driver require Fluentd to be running before containers start?

Yes. If the Fluentd daemon is not running when containers start, the fluentd driver will fail to connect and containers may fail to start. The `fluentd-async-connect` option can mitigate this by allowing containers to start even if Fluentd is temporarily unavailable, buffering logs locally until the connection is established.

### Which logging driver has the lowest performance overhead?

journald has the lowest overhead for single-host deployments since it writes directly to the local journal via a Unix socket with minimal serialization. For multi-host aggregation, GELF over UDP has the lowest network overhead due to its binary format and optional compression. However, UDP GELF provides no delivery guarantees, making it unsuitable for compliance-sensitive environments where log completeness is required.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Logging Drivers: journald vs fluentd vs syslog vs GELF",
  "description": "Compare Docker container logging drivers - journald, fluentd, syslog, and GELF. Configuration examples, performance analysis, and Docker Compose deployment guides.",
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
