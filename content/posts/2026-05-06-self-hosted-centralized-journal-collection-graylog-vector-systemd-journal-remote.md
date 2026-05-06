---
title: "Self-Hosted Centralized Journal Collection: Graylog vs Vector vs systemd-journal-remote"
date: "2026-05-06"
tags: ["systemd", "journald", "log-centralization", "graylog", "vector", "journal-remote", "observability", "linux"]
draft: false
---

Every Linux system running systemd generates structured journal entries through journald. These entries contain system logs, application output, kernel messages, and audit records — all in a binary format that is efficient for local querying but impractical for centralized analysis. Collecting journal entries from multiple servers into a single location enables cross-host correlation, centralized alerting, and long-term retention.

This guide compares three approaches to centralized journal collection: **Graylog** as a full-featured log management platform, **Vector** as a high-performance observability data pipeline, and **systemd-journal-remote** as the native systemd solution. Each approach has different tradeoffs in complexity, performance, and feature set.

## Why Centralize systemd Journals?

The systemd journal is powerful for local troubleshooting but has inherent limitations for multi-server environments:

- **No cross-host search** — `journalctl` only reads the local journal file
- **Limited retention** — journals are rotated based on disk usage, not time
- **Binary format** — journal files cannot be tailed or parsed by standard tools
- **No alerting** — journald has no built-in notification system
- **Single point of failure** — if the disk fills, new logs are dropped

Centralizing journals solves all of these problems. You get full-text search across all servers, configurable retention policies, alerting on specific log patterns, and protection against local disk failures.

## Graylog: Full-Featured Log Management Platform

Graylog is an open-source log management platform that ingests, processes, and stores log data from multiple sources. It provides a web interface for searching, analyzing, and alerting on log data, with built-in support for journald input via GELF (Graylog Extended Log Format).

### Architecture

Graylog consists of three components:

1. **Graylog Server** — processes incoming log data, applies extractors and pipelines
2. **Elasticsearch/OpenSearch** — stores and indexes log data for fast searching
3. **MongoDB** — stores Graylog configuration (streams, dashboards, users)

Journals can be forwarded to Graylog using `journalctl` output piped to a GELF forwarder, or by using the `graylog-collector-sidecar` on each node.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  mongodb:
    image: mongo:7.0
    container_name: graylog-mongo
    volumes:
      - mongo-data:/data/db

  opensearch:
    image: opensearchproject/opensearch:2.17.0
    container_name: graysearch
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
    volumes:
      - os-data:/usr/share/opensearch/data

  graylog:
    image: graylog/graylog:6.1
    container_name: graylog
    environment:
      - GRAYLOG_PASSWORD_SECRET=some-password-secret-change-me
      - GRAYLOG_ROOT_PASSWORD_SHA2=8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918
      - GRAYLOG_HTTP_EXTERNAL_URI=http://localhost:9000/
      - GRAYLOG_ELASTICSEARCH_HOSTS=http://opensearch:9200
    ports:
      - "9000:9000"
      - "12201:12201/udp"
      - "1514:1514"
      - "1514:1514/udp"
    depends_on:
      - mongodb
      - opensearch

volumes:
  mongo-data:
  os-data:
```

### Forwarding Journals to Graylog

On each client server, use `journalctl` with the GELF output format and send to Graylog's GELF UDP input:

```bash
# Install graylog-collector-sidecar or use a simple forwarding script
# Using journal-gelf as a lightweight forwarder:
journalctl -f -o gelf | nc -u graylog-server 12201

# Or configure rsyslog to forward journal entries:
# /etc/rsyslog.d/graylog.conf
$ModLoad imjournal
$IMJournalStateFile imjournal.state
*.* @graylog-server:514
```

For production deployments, the recommended approach is to use Vector or Fluent Bit as the journal forwarder, as they handle backpressure and retries properly.

### Strengths

- Complete log management platform with web UI, dashboards, and alerting
- Full-text search across all ingested journal entries
- Pipeline processing for parsing, enriching, and routing logs
- User management and access control
- Email and webhook alerting on log patterns
- Support for multiple input types (GELF, syslog, beats, HTTP)

### Limitations

- Requires three services (Graylog + OpenSearch + MongoDB)
- Higher resource consumption (2-4GB RAM minimum)
- GELF forwarding from journald requires a separate forwarder
- Not designed for high-throughput (>100K events/sec) without clustering

## Vector: High-Performance Observability Pipeline

Vector, developed by Datadog, is a high-performance observability data pipeline written in Rust. It can collect systemd journal entries, transform them, and forward them to any destination — including Graylog, Loki, Elasticsearch, or cloud services.

### Architecture

Vector uses a source-transform-sink model:

- **Sources** — ingest data from journald, files, syslog, HTTP, etc.
- **Transforms** — parse, filter, enrich, and route data
- **Sinks** — forward data to destinations (Loki, Elasticsearch, Kafka, etc.)

Vector's `journald` source reads directly from the systemd journal socket, eliminating the need for intermediate forwarders.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  vector:
    image: timberio/vector:0.42.0-distroless-libc
    container_name: vector
    volumes:
      - ./vector.yaml:/etc/vector/vector.yaml:ro
      - /var/log/journal:/var/log/journal:ro
      - /run/systemd/journal:/run/systemd/journal:ro
    ports:
      - "8686:8686"
      - "9000:9000"

  loki:
    image: grafana/loki:3.2.0
    container_name: loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki

volumes:
  loki-data:
```

### Vector Configuration

```yaml
# vector.yaml
sources:
  journald:
    type: journald
    journal_directory: /var/log/journal

transforms:
  filter_system:
    type: filter
    inputs:
      - journald
    condition:
      type: vrl
      source: |
        .PRIORITY != "7" && .PRIORITY != "6"

  add_host:
    type: remap
    inputs:
      - filter_system
    source: |
      .host = get_hostname!()
      .service = .SYSLOG_IDENTIFIER || "unknown"

sinks:
  loki_output:
    type: loki
    inputs:
      - add_host
    endpoint: http://loki:3100
    encoding:
      codec: text
    labels:
      host: "{{ host }}"
      service: "{{ service }}"
      severity: "{{ PRIORITY }}"
```

This configuration reads from the systemd journal, filters out debug and informational messages (priority 6 and 7), adds a hostname label, and forwards to Loki with structured labels.

### Strengths

- Extremely low resource usage (10-50MB RAM per instance)
- Native journald source reads directly from journal socket
- Backpressure handling and retry logic built-in
- VRL (Vector Remap Language) for powerful log transformations
- Single binary deployment, no dependencies
- Can aggregate from hundreds of sources

### Limitations

- No built-in storage or search — requires a separate log backend
- No web UI for log exploration (use Grafana with Loki)
- VRL learning curve for complex transformations
- Journal directory must be bind-mounted into the container

## systemd-journal-remote: Native systemd Solution

`systemd-journal-remote` is the native systemd tool for centralized journal collection. It receives journal entries over HTTPS or HTTP and stores them in local journal files on the collector server.

### Architecture

The systemd-journal-remote approach uses:

- **systemd-journal-upload** on each client — uploads journal entries to the collector
- **systemd-journal-remote** on the collector — receives and stores entries
- **systemd-journald** on the collector — provides read access via `journalctl`

All communication happens over HTTPS with mutual TLS authentication, ensuring that journal data is encrypted in transit.

### Deployment (Native systemd, not Docker)

On the collector server:

```bash
# Install journal-remote
apt install systemd-journal-remote

# Enable the remote receiver
systemctl enable systemd-journal-remote.socket
systemctl start systemd-journal-remote.socket

# Configure TLS certificates
# /etc/systemd/journal-remote.conf
[Remote]
ServerKeyFile=/etc/ssl/private/journal-remote.key
ServerCertificateFile=/etc/ssl/certs/journal-remote.crt
TrustedCertificateFile=/etc/ssl/certs/journal-ca.crt
```

On each client server:

```bash
# Configure journal upload
# /etc/systemd/journal-upload.conf
[Upload]
URL=https://journal-collector:19532
ServerKeyFile=/etc/ssl/private/journal-upload.key
ServerCertificateFile=/etc/ssl/certs/journal-upload.crt
TrustedCertificateFile=/etc/ssl/certs/journal-ca.crt

# Enable and start
systemctl enable systemd-journal-upload
systemctl start systemd-journal-upload
```

### Strengths

- Native systemd integration — no third-party dependencies
- Mutual TLS authentication for secure journal transmission
- Preserves full journal metadata (UID, GID, SELinux context, etc.)
- Read collected journals with standard `journalctl` commands
- Low overhead — binary journal format is efficient
- No additional storage engine required

### Limitations

- No web UI for log exploration — requires `journalctl` on the collector
- No full-text search across all journals without additional tooling
- TLS certificate management overhead for large deployments
- No alerting or dashboard capabilities
- Binary journal files are not easily parsable by external tools
- Limited to systemd-based systems (not portable to non-systemd Linux)

## Comparison: Centralized Journal Collection

| Feature | Graylog | Vector + Loki | systemd-journal-remote |
|---------|---------|---------------|------------------------|
| Web UI | Built-in (Graylog web) | Grafana (separate) | None (journalctl CLI) |
| Search | Full-text, faceted | Label-filtered + log content | journalctl query syntax |
| Storage | OpenSearch/Elasticsearch | Loki on object storage | Local journal files |
| Resource usage | 2-4GB RAM | 50-200MB (Vector) + Loki | 100-500MB |
| Setup complexity | High (3 services) | Medium (2 services) | Low (systemd units) |
| Alerting | Built-in | Grafana/Loki alerting | None |
| Multi-tenant | Yes (streams, roles) | Yes (Loki tenants) | No (shared journal) |
| Encryption | TLS for inputs | TLS for outputs | mTLS (built-in) |
| Non-systemd support | Yes (any log source) | Yes (any log source) | No (systemd only) |
| License | SSPL | Apache 2.0 / AGPL v3 | LGPL 2.1 |

## Why Self-Host Journal Collection?

Centralized log collection is a foundational capability for any self-hosted infrastructure. Running your own journal collection pipeline means you maintain full control over log data, retention policies, and access controls. This is essential for organizations that need to comply with data residency requirements or that process sensitive information that cannot be sent to third-party log management services.

For teams already managing self-hosted services, adding journal collection to the existing stack is more cost-effective than paying per-GB ingestion fees to cloud log management platforms. At 100GB/day of journal data, self-hosted collection on commodity hardware costs a fraction of equivalent cloud service pricing.

For related reading, see our [complete log management stack comparison](../self-hosted-log-management-loki-graylog-opensearch/) and our [log shipping architecture guide](../self-hosted-log-shipping-vector-fluentbit-logstash-guide/). Understanding the full log pipeline from source to storage helps you choose the right journal collection approach.

## FAQ

### What is the simplest way to centralize systemd journals?

For small deployments (under 10 servers), systemd-journal-remote is the simplest approach. It requires no additional software beyond what ships with systemd, and collected journals are readable with standard `journalctl` commands. The main tradeoff is the lack of a web UI — you need SSH access to the collector server to search logs.

### Can Vector read journals without root access?

Vector's journald source reads from the systemd journal socket at `/run/systemd/journal`. On most systems, this socket is readable by users in the `systemd-journal` group. You can add the Vector user to this group (`usermod -aG systemd-journal vector`) rather than running Vector as root. Alternatively, use the `journalctl --follow -o json` output piped into Vector's stdin source.

### How does Graylog handle journal metadata?

When journal entries are converted to GELF format for Graylog ingestion, systemd-specific fields like `_PID`, `_UID`, `_COMM`, `_SYSTEMD_UNIT`, and `_HOSTNAME` become structured GELF fields. This allows you to search and filter on any journal field in Graylog. For example, you can create a stream that shows only entries from a specific systemd unit across all servers.

### Is systemd-journal-remote secure for internet-facing deployments?

systemd-journal-remote uses mutual TLS (mTLS) authentication, which is more secure than standard TLS. Both the client and server must present valid certificates signed by a trusted CA. This prevents unauthorized servers from injecting journal entries and unauthorized clients from reading collected journals. However, exposing the journal-remote port directly to the internet is not recommended — use a VPN or private network for journal transport.

### Which approach handles the highest log volume?

Vector is the clear winner for high-throughput scenarios. Written in Rust with zero-copy parsing, a single Vector instance can process millions of events per second with minimal CPU and memory usage. Graylog's throughput is limited by its OpenSearch backend (typically 50-100K events/sec per node without clustering). systemd-journal-remote is limited by journal file I/O and typically handles 10-20K events/sec.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Centralized Journal Collection: Graylog vs Vector vs systemd-journal-remote",
  "description": "Compare Graylog, Vector, and systemd-journal-remote for centralized systemd journal collection with Docker Compose deployment and configuration examples.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
