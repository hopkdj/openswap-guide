---
title: "rsyslog vs syslog-ng vs Vector: Best Self-Hosted Log Aggregation 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "logging", "observability", "syslog"]
draft: false
description: "Compare rsyslog, syslog-ng, and Vector for self-hosted syslog collection and log aggregation. Includes Docker deployment guides, configuration examples, and a decision matrix for 2026."
---

Every server, container, and network device generates logs. Without a centralized collection strategy, troubleshooting means SSH-ing into individual machines, tailing files, and hoping you catch the error before it scrolls off screen. A self-hosted syslog aggregation pipeline solves this by collecting logs from all your infrastructure into a single searchable location — without sending sensitive data to a third-party cloud service.

In this guide, we compare three mature open-source log aggregation engines: **rsyslog**, **syslog-ng**, and **Vector**. Each has a different design philosophy, performance profile, and configuration model. We'll walk through installation, [docker](https://www.docker.com/) deployment, configuration examples, and help you pick the right tool for your stack.

## Why Self-Host Your Log Aggregation

Commercial log management platforms charge per gigabyte ingested. For organizations running dozens of servers, container clusters, or network appliances, those costs escalate quickly. Self-hosting your log collection layer gives you:

- **Full data ownership** — logs never leave your infrastructure
- **No volume-based pricing** — scale without watching the bill
- **Custom retention policies** — keep logs as long as compliance requires
- **Deep customization** — parse, transform, and route logs exactly how you need
- **Reduced blast radius** — no dependency on an external SaaS provider's uptime

For related reading, see our [complete self-hosted log management guide with Loki, Graylog, and OpenSearch](../self-hosted-log-management-loki-graylog-opensearch/) for storage and querying options that pair well with the syslog collectors covered here.

## Quick Comparison Table

| Feature | rsyslog | syslog-ng | Vector |
|---|---|---|---|
| **Language** | C | C | Rust |
| **GitHub Stars** | 2,285 | 2,335 | 21,676 |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2026 |
| **License** | GPL / LGPL | LGPL / GPL | MPL 2.0 |
| **Protocols** | Syslog (UDP/TCP/TLS), RELP | Syslog (UDP/TCP/TLS), RELP | Syslog, HTTP, gRPC, Kafka, and 50+ more |
| **Config Format** | Custom DSL | Custom DSL | TOML / YAML |
| **Log Transformation** | Basic (mmnormalize, templates) | Advanced (parsers, rewrite rules) | Advanced (VRL language) |
| **Buffering / Disk Queue** | Yes (on-disk queue) | Yes (disk-buffer) | Yes (disk buffer) |
| **Built-in Metrics** | No | Limited | Yes (prometheus endpoint) |
| **Docker Image Size** | ~10 MB (alpine) | ~25 MB (alpine) | ~85 MB (alpine) |
| **Best For** | Traditional Linux servers, minimal footprint | Com[plex](https://www.plex.tv/) parsing, enterprise syslog | Modern observability pipelines, multi-destination routing |

## rsyslog: The Default Linux Syslog Daemon

**rsyslog** (Rocket-fast SYStem LOG) has been the default syslog daemon on most Linux distributions for over a decade. It is lightweight, battle-tested, and designed primarily for reliable syslog message reception, filtering, and forwarding.

### Strengths

- Pre-installed on Ubuntu, Debian, RHEL, CentOS, and Fedora
- Extremely low resource usage — idle memory footprint under 5 MB
- Supports RELP (Reliable Event Logging Protocol) for guaranteed delivery
- Mature on-disk queuing for handling downstream outages
- Thousands of production deployments worldwide

### Limitations

- Configuration syntax is notoriously cryptic with inconsistent module directives
- Log parsing and transformation capabilities are basic compared to modern alternatives
- No native support for JSON, HTTP, or cloud-native output protocols
- Limited observability — no built-in metrics endpoint

### Installation

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y rsyslog rsyslog-relp
sudo systemctl enable rsyslog
sudo systemctl start rsyslog
```

**RHEL / Rocky / AlmaLinux:**

```bash
sudo dnf install -y rsyslog rsyslog-relp
sudo systemctl enable rsyslog
sudo systemctl start rsyslog
```

### Docker Deployment

rsyslog does not ship an official Docker image, but a minimal image is easy to build:

```yaml
# docker-compose.yml for rsyslog
services:
  rsyslog:
    image: alpine:latest
    container_name: rsyslog-server
    ports:
      - "514:514/udp"
      - "514:514/tcp"
      - "20514:20514/tcp"   # RELP port
    volumes:
      - ./rsyslog.conf:/etc/rsyslog.conf
      - rsyslog-data:/var/log
    restart: unless-stopped

volumes:
  rsyslog-data:
```

Basic `rsyslog.conf` that receives syslog over UDP and writes per-host log files:

```conf
module(load="imuxsock")     # local system logging
module(load="imudp")        # UDP syslog receiver
input(type="imudp" port="514")

module(load="imtcp")        # TCP syslog receiver
input(type="imtcp" port="514")

# RELP for reliable delivery
module(load="imrelp")
input(type="imrelp" port="20514")

# Template: one file per source host
template(name="HostFile" type="string"
    string="/var/log/%fromhost%/syslog.log")

# Route all remote logs to per-host files
:fromhost-ip, !isequal, "127.0.0.1"   ?HostFile
```

### Configuring Clients to Forward Logs

On each client machine, add a forwarding rule to `/etc/rsyslog.d/50-forward.conf`:

```conf
# Forward all logs to central server via RELP (reliable)
action(type="omrelp" target="10.0.0.10" port="20514")

# Or use plain TCP (less reliable, no encryption)
# *.* @@10.0.0.10:514

# Or use UDP (fastest, but messages can be lost)
# *.* @10.0.0.10:514
```

After adding the config, restart the service:

```bash
sudo systemctl restart rsyslog
```

## syslog-ng: Advanced Syslog with Powerful Parsing

**syslog-ng** is an enhanced syslog daemon that extends the traditional syslog protocol with structured data handling, advanced filtering, and flexible output destinations. It is commonly used in environments that need to parse heterogeneous log formats or integrate with databases and message queues.

### Strengths

- Rich parsing engine with support for CSV, JSON, and custom delimiters
- Built-in geo-IP lookups, hostname resolution, and pattern databases
- Supports disk-based buffering for reliable delivery during network outages
- Can write directly to SQL databases, Elasticsearch, and AMQP brokers
- Active commercial backing from One Identity (formerly Balabit)

### Limitations

- Not installed by default on most distributions — requires separate package
- Configuration syntax has a learning curve (though cleaner than rsyslog)
- Some advanced features require the commercial syslog-ng PE edition
- Community edition lags behind in certain cloud-native integrations

### Installation

**Ubuntu / Debian:**

```bash
sudo apt update
sudo apt install -y syslog-ng
sudo systemctl enable syslog-ng
sudo systemctl start syslog-ng
```

**RHEL / Rocky / AlmaLinux:**

```bash
sudo dnf install -y epel-release
sudo dnf install -y syslog-ng
sudo systemctl enable syslog-ng
sudo systemctl start syslog-ng
```

### Docker Deployment

syslog-ng provides an official image with a pre-built Dockerfile in its repository:

```yaml
# docker-compose.yml for syslog-ng
services:
  syslog-ng:
    image: balabit/syslog-ng:latest
    container_name: syslog-ng-server
    ports:
      - "514:514/udp"
      - "514:514/tcp"
      - "601:601/tcp"   # syslog over TCP (default)
    volumes:
      - ./syslog-ng.conf:/etc/syslog-ng/syslog-ng.conf:ro
      - syslog-ng-data:/var/log
    restart: unless-stopped

volumes:
  syslog-ng-data:
```

Configuration file (`syslog-ng.conf`) that receives syslog, parses JSON messages, and writes per-host files:

```conf
@version: 4.7
@include "scl.conf"

# Sources
source s_network {
    syslog(
        transport("tcp")
        port(601)
        flags(syslog-protocol)
    );
    udp(port(514));
};

# Parse JSON-structured logs
parser p_json {
    json-parser(
        prefix(".json.")
        template("$MSG")
    );
};

# Destination: per-host log files
destination d_perhost {
    file("/var/log/${HOST}/syslog.log"
        template("${ISODATE} ${HOST} ${PROGRAM}[${PID}]: ${MSG}\n")
    );
};

# Log path
log {
    source(s_network);
    parser(p_json);
    destination(d_perhost);
    flags(flow-control);
};
```

### Client Configuration

On client machines running syslog-ng, forward logs with the following block in `/etc/syslog-ng/conf.d/forward.conf`:

```conf
destination d_central {
    syslog("10.0.0.10"
        transport("tcp")
        port(601)
        tls(
            peer-verify(required-untrusted)
            ca-dir("/etc/syslog-ng/ca.d/")
        )
    );
};

log {
    source(s_src);
    destination(d_central);
};
```

## Vector: Modern Observability Data Pipeline

**Vector** is a high-performance observability data pipeline written in Rust by Datadog (formerly Timber.io). It goes far beyond syslog collection — it is a full data pipeline that can ingest, transform, and route logs, metrics, and traces to 50+ destinations. With over 21,000 GitHub stars, it is the most actively developed of the three tools in this comparison.

If you're already familiar with Vector for log shipping, our [log shipping guide comparing Vector, Fluent Bit, and Logstash](../self-hosted-log-shipping-vector-fluentbit-logstash-guide-2026/) covers its broader role in the observability stack.

### Strengths

- Extremely fast — Rust-based architecture handles millions of events per second
- **VRL (Vector Remap Language)** — a powerful, safe-by-default transformation language for parsing, enriching, and filtering data
- 50+ built-in source and sink types (Kafka, Elasticsearch, Loki, S3, HTTP, PostgreSQL, and more)
- Built-in Prometheus metrics endpoint for self-monitoring
- Memory-safe — no buffer overflows or segfaults thanks to Rust
- First-class support for structured logging (JSON, protobuf) out of the box

### Limitations

- Larger binary and Docker image compared to rsyslog/syslog-ng
- VRL has a learning curve, though the documentation is excellent
- Not a drop-in replacement for system-level syslog — typically runs alongside rsyslog
- Requires more RAM (200-500 MB under load) than the C-based alternatives

### Installation

**Using the official install script (Linux):**

```bash
curl -1sLf https://setup.vector.dev/install.sh | sudo bash
sudo apt install -y vector   # or: sudo dnf install -y vector
sudo systemctl enable vector
sudo systemctl start vector
```

**macOS (Homebrew):**

```bash
brew install vector
brew services start vector
```

### Docker Deployment

Vector ships an official Docker image and can be deployed with a simple compose file:

```yaml
# docker-compose.yml for Vector
services:
  vector:
    image: timberio/vector:latest-alpine
    container_name: vector-aggregator
    ports:
      - "514:514/udp"
      - "514:514/tcp"
      - "9090:9090/tcp"   # Prometheus metrics
    volumes:
      - ./vector.yaml:/etc/vector/vector.yaml:ro
      - vector-data:/var/lib/vector
    restart: unless-stopped

volumes:
  vector-data:
```

### Vector Configuration for Syslog Aggregation

Create `vector.yaml` with the following pipeline — receive syslog, parse structured fields, and route to multiple destinations:

```yaml
sources:
  syslog_input:
    type: syslog
    address: 0.0.0.0:514
    mode: tcp
    max_length: 102400

  syslog_udp:
    type: syslog
    address: 0.0.0.0:514
    mode: udp

transforms:
  parse_json:
    type: remap
    inputs:
      - syslog_input
      - syslog_udp
    source: |
      # Try to parse JSON in the message field
      parsed, err = parse_json(.message)
      if err == null {
          .structured = parsed
          del(.message)
      }

      # Add metadata
      .ingested_at = now()
      .pipeline = "syslog-aggregator"

  # Filter out routine health-check noise
  filter_noise:
    type: filter
    inputs:
      - parse_json
    condition: |
      !contains(string!(.message), "healthcheck") ||
      .severity != "info"

sinks:
  # Write to local files (one per host)
  local_files:
    type: file
    inputs:
      - filter_noise
    path: "/var/log/vector/%{host}/%Y-%m-%d.log"
    encoding:
      codec: json

  # Forward to Loki for querying
  loki:
    type: loki
    inputs:
      - filter_noise
    endpoint: "http://loki:3100"
    encoding:
      codec: json
    labels:
      host: "{{ host }}"
      severity: "{{ severity }}"

  # Export internal metrics
  prometheus:
    type: prometheus_exporter
    inputs:
      - filter_noise
    address: 0.0.0.0:9090
```

## Deployment Architecture: Putting It Together

A typical self-hosted log aggregation stack uses the syslog collector as the **ingestion layer** and pairs it with a **storage/query layer**:

```
[Servers/Containers]  ──syslog──▶  [rsyslog / syslog-ng / Vector]
                                          │
                               ┌──────────┼──────────┐
                               ▼          ▼          ▼
                          [Loki]    [OpenSearch]   [Local Files]
                               │          │
                               ▼          ▼
                          [Grafana]  [Dashboards]
```

The choice of collector determines how logs arrive, how they are parsed, and how reliably they are delivered. The storage layer determines how long you keep them and how you search them. For a full comparison of storage options, see our [self-hosted Datadog alternatives guide with SigNoz, Grafana, and HyperDX](../self-hosted-datadog-alternative-signoz-grafana-hyperdx-2026/).

### TLS Encryption for Syslog Transport

For production deployments, always encrypt syslog traffic. Here is a Vector configuration snippet with TLS:

```yaml
sources:
  syslog_tls:
    type: syslog
    address: 0.0.0.0:6514
    mode: tcp
    tls:
      enabled: true
      crt_file: /etc/vector/certs/server.crt
      key_file: /etc/vector/certs/server.key
      ca_file: /etc/vector/certs/ca.crt
```

Generate self-signed certificates for testing:

```bash
# Generate CA
openssl genrsa -out ca.key 4096
openssl req -new -x509 -key ca.key -out ca.crt -days 365 -subj "/CN=LogCA"

# Generate server cert
openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr -subj "/CN=log-server"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365
```

## Decision Matrix: Which Tool Should You Choose?

### Choose rsyslog if:
- You want zero additional installation on existing Linux servers
- Your infrastructure is small and you need simple log forwarding
- Resource constraints are tight (embedded systems, minimal VPS)
- You only need to collect, filter, and forward standard syslog messages

### Choose syslog-ng if:
- You need advanced parsing (CSV, JSON, custom delimiters)
- You want to write logs directly to databases or Elasticsearch
- You need geo-IP enrichment or hostname resolution built in
- Your organization already has syslog-ng expertise

### Choose Vector if:
- You are building a modern observability pipeline
- You need to route logs to multiple destinations simultaneously (Loki + S3 + Elasticsearch)
- You want built-in metrics, health checks, and Prometheus integration
- You value memory safety and are comfortable with a larger binary
- You need to process high-throughput log volumes (10,000+ events/sec)

## FAQ

### What is the difference between rsyslog and syslog-ng?

Both are syslog daemons written in C, but they differ in approach. rsyslog focuses on performance and compatibility with existing syslog configurations — it is the default on most Linux distributions. syslog-ng offers richer parsing capabilities, better structured data support, and a cleaner configuration syntax. For most basic log collection tasks, either will work. Choose syslog-ng if you need advanced parsing, routing to databases, or geo-IP enrichment.

### Can Vector replace rsyslog entirely?

Not exactly. Vector can receive syslog messages and act as a syslog server, but it does not replace the local system logging that rsyslog provides on individual machines. A common pattern is to keep rsyslog on each server for local `/var/log` writing and system journaling, then use Vector as the centralized aggregation layer that collects from all rsyslog instances, transforms the data, and routes it to storage backends like Loki or Elasticsearch.

### Is UDP or TCP better for syslog transport?

UDP is faster but offers no delivery guarantees — messages can be dropped during network congestion. TCP ensures delivery but adds overhead and can block if the receiver is slow. For production environments, TCP with TLS encryption is the recommended approach. If you need guaranteed delivery with acknowledgment, consider using RELP (rsyslog) or Vector's built-in buffering, which writes to disk when the downstream sink is unavailable.

### How much disk space should I allocate for log storage?

This depends on log volume and retention requirements. A rough estimate for a small infrastructure (10-20 servers) is 5-10 GB per month with log rotation. For larger deployments, use a dedicated log storage backend like Loki, OpenSearch, or Graylog with index lifecycle management that automatically deletes old data. Always configure log rotation (`logrotate`) for locally stored files to prevent disk exh[kubernetes](https://kubernetes.io/)### Can these tools handle container and Kubernetes logs?

Yes, but with different approaches. rsyslog and syslog-ng typically require a sidecar or DaemonSet that reads container stdout/stderr and forwards it via syslog. Vector has native Docker and Kubernetes source types that can read directly from the Docker socket or Kubernetes API, making it the easiest option for container-native environments. For Kubernetes specifically, consider pairing Vector with the Vector Kubernetes collection chart for automatic pod discovery and metadata enrichment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "rsyslog vs syslog-ng vs Vector: Best Self-Hosted Log Aggregation 2026",
  "description": "Compare rsyslog, syslog-ng, and Vector for self-hosted syslog collection and log aggregation. Includes Docker deployment guides, configuration examples, and a decision matrix for 2026.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
