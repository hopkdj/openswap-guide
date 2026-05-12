---
title: "Self-Hosted Syslog Forwarders: Vector vs syslog-ng vs Rsyslog"
date: "2026-05-12"
tags: ["logging", "observability", "syslog", "data-pipeline", "self-hosted"]
draft: false
---

When you run multiple servers, containers, or network devices, getting all their logs into a centralized location is a fundamental infrastructure challenge. The syslog protocol has been the standard for log transport since the 1980s, and modern self-hosted environments still rely on it heavily. The question is not whether to forward logs, but which tool to use.

Three open-source projects dominate this space: **Vector**, **syslog-ng**, and **Rsyslog**. Each has a different philosophy, architecture, and feature set. This guide compares them across performance, configuration, observability features, and operational complexity so you can choose the right log forwarder for your environment.

## Understanding Syslog Forwarding

A syslog forwarder (also called a log shipper or log forwarder) sits between your log-generating services and your central log store. It collects logs from various sources -- local files, systemd journal, TCP/UDP syslog ports, HTTP endpoints -- transforms them (adding metadata, filtering, parsing), and forwards them to destinations like Elasticsearch, Loki, Graylog, or S3-compatible storage.

The three tools covered here all support the same core capabilities:

- Ingest from syslog (RFC 3164 and RFC 5424), files, journald, and HTTP
- Transform and enrich log data with structured fields
- Forward to multiple output destinations simultaneously
- Buffer logs during network outages to prevent data loss
- Run with minimal resource overhead

But their approaches differ significantly. Rsyslog is the battle-tested default on most Linux distributions. syslog-ng offers a more modern configuration model with advanced parsing. Vector is the newest entrant, built in Rust with a focus on performance and observability-first design.

## Project Comparison at a Glance

| Feature | Vector | syslog-ng | Rsyslog |
|---------|--------|-----------|---------|
| Language | Rust | C | C |
| License | MPL 2.0 | LGPL 2.1 + commercial | GPL 3.0 |
| GitHub Stars | 21,800+ | 2,300+ | 2,200+ |
| Last Updated | Active (May 2026) | Active (May 2026) | Active (May 2026) |
| Config Format | TOML | Custom DSL | Custom DSL |
| Metrics Support | Built-in Prometheus | Limited | Via omprog |
| Backpressure | Yes (internal buffers) | Limited | Via disk queues |
| WASM Plugins | Yes | No | No |
| Pre-built Binaries | Yes | Yes | Yes |
| Docker Image | timberio/vector | ghcr.io/syslog-ng/syslog-ng | rsyslog/rsyslog |

Vector stands out for its observability-native design -- it exposes Prometheus metrics out of the box, supports WASM-based transforms, and has a unified configuration that covers the entire data pipeline from source to sink.

## Installation and Deployment

### Vector

Vector provides a one-line install script and pre-built packages for all major Linux distributions:

```bash
curl -1sLf https://setup.vector.dev | sudo bash
sudo apt-get install vector
```

Docker Compose deployment:

```yaml
version: "3.8"
services:
  vector:
    image: timberio/vector:0.46.0-debian
    container_name: vector-agent
    restart: unless-stopped
    volumes:
      - ./vector.toml:/etc/vector/vector.toml:ro
      - /var/log:/var/log:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - vector-data:/var/lib/vector
    ports:
      - "8282:8282"
      - "514:514/udp"
    environment:
      - VECTOR_LOG=info

volumes:
  vector-data:
```

### syslog-ng

```bash
sudo apt-get install syslog-ng
```

Docker Compose deployment:

```yaml
version: "3.8"
services:
  syslog-ng:
    image: ghcr.io/syslog-ng/syslog-ng:4.7.0
    container_name: syslog-ng
    restart: unless-stopped
    volumes:
      - ./syslog-ng.conf:/etc/syslog-ng/syslog-ng.conf:ro
      - syslog-ng-persist:/var/lib/syslog-ng
    ports:
      - "514:514/tcp"
      - "514:514/udp"
      - "601:601/tcp"

volumes:
  syslog-ng-persist:
```

### Rsyslog

Rsyslog is pre-installed on most Debian/Ubuntu and RHEL systems. To install or update:

```bash
sudo apt-get install rsyslog
# Verify version
rsyslogd -v
```

Docker Compose deployment:

```yaml
version: "3.8"
services:
  rsyslog:
    image: rsyslog/rsyslog:8.2504.0
    container_name: rsyslog
    restart: unless-stopped
    volumes:
      - ./rsyslog.conf:/etc/rsyslog.conf:ro
      - rsyslog-spool:/var/spool/rsyslog
    ports:
      - "514:514/tcp"
      - "514:514/udp"

volumes:
  rsyslog-spool:
```

## Configuration Comparison

### Vector (TOML-based)

Vector uses TOML configuration, which is human-readable and validated at startup:

```toml
[sources.syslog_input]
type = "syslog"
address = "0.0.0.0:514"
mode = "udp"

[transforms.parse_json]
type = "remap"
inputs = ["syslog_input"]
source = ". = parse_json!(.message)"

[sinks.loki_output]
type = "loki"
inputs = ["parse_json"]
endpoint = "http://loki:3100"
encoding.codec = "json"
```

### syslog-ng (DSL-based)

syslog-ng uses a declarative configuration language:

```
source s_syslog {
  syslog(
    ip(0.0.0.0)
    port(514)
    transport("udp")
  );
};

parser p_json {
  json-parser(
    prefix(".json")
  );
};

destination d_loki {
  http(
    url("http://loki:3100/loki/api/v1/push")
    method("POST")
    body("$(format-json --scope rfc5424)")
  );
};

log {
  source(s_syslog);
  parser(p_json);
  destination(d_loki);
};
```

### Rsyslog (rule-based)

Rsyslog uses a traditional rule-based configuration:

```
module(load="imudp")
input(type="imudp" port="514")

module(load="mmjsonparse")

action(
  type="omhttp"
  target="loki"
  port="3100"
  serverport="3100"
  usehttps="off"
  action.resumeRetryCount="100"
  queue.type="linkedList"
  queue.filename="loki_buffer"
  queue.maxdiskspace="1g"
)
```

## Performance and Reliability

Benchmark tests consistently show Vector leading in raw throughput, largely due to its Rust-based architecture and lock-free internal buffers. In a 2025 comparison processing 100,000 events per second:

- **Vector**: approximately 200 MB/s throughput, approximately 50 MB memory footprint
- **syslog-ng**: approximately 150 MB/s throughput, approximately 80 MB memory footprint
- **Rsyslog**: approximately 120 MB/s throughput, approximately 60 MB memory footprint

For reliability, all three support disk-based buffering to survive restarts and network outages. Vector internal buffer management is the most sophisticated, offering automatic backpressure when downstream systems are slow. Rsyslog disk-assisted memory queues are the most battle-tested, having been production-proven for over a decade.

## When to Choose Each

### Choose Vector if:
- You want built-in observability (Prometheus metrics, internal logging)
- You need complex log transforms (VRL language is powerful and safe)
- You are building a modern observability stack from scratch
- You value configuration validation and structured error messages

### Choose syslog-ng if:
- You need advanced syslog parsing (pattern databases, geoip lookups)
- You want a balance between Rsyslog maturity and modern features
- You are migrating from Rsyslog and want a familiar but improved tool
- You need commercial support available (via One Identity)

### Choose Rsyslog if:
- You want the most battle-tested option (default on most Linux distros)
- You need maximum compatibility with existing syslog infrastructure
- You prefer minimal dependencies and small footprint
- Your team already has operational experience with it

## Why Centralize Log Forwarding?

Running a centralized logging pipeline is one of the highest-impact infrastructure investments you can make. Without it, troubleshooting means SSH-ing into individual servers, grepping through rotated log files, and trying to correlate events across timestamps that may drift by seconds or minutes. A syslog forwarder solves this at the transport layer.

Log forwarders act as the nervous system of your observability stack. They collect, parse, filter, and route log data from every source to every destination -- often simultaneously. You can send a copy of production logs to your SIEM for security analysis while also forwarding to a cheaper cold-storage bucket for long-term retention.

For containerized environments, the forwarder becomes even more critical. Containers are ephemeral -- when a pod dies, its logs die with it unless a forwarder captures them in real time. Tools like Vector can integrate directly with the container runtime, reading from the Docker socket or Kubernetes API to enrich logs with pod labels, namespace, and service metadata before forwarding.

For network devices, syslog is often the only export mechanism available. Routers, switches, firewalls, and load balancers all speak syslog natively. A forwarder like syslog-ng or Rsyslog can receive these on UDP port 514, parse the vendor-specific formats, and forward structured data to your log aggregator.

If you run Kubernetes workloads, check our [Kubernetes logging operators guide](../2026-05-07-self-hosted-kubernetes-logging-operators-fluent-loki-vector-guide/) for deeper integration patterns. For log retention strategies, our [log retention lifecycle guide](../2026-05-06-self-hosted-log-retention-lifecycle-management-elasticsearch-ilm-loki-opensearch-ism/) covers how to manage storage costs once your forwarder is shipping data. And for journal-based log collection, our [centralized journal collection guide](../2026-05-06-self-hosted-centralized-journal-collection-graylog-vector-systemd-journal-remote/) covers complementary approaches.

## FAQ

### What is the difference between a syslog forwarder and a log aggregator?

A syslog forwarder (also called a log shipper) runs on the source machine and sends logs to a central destination. A log aggregator (like Elasticsearch, Loki, or Graylog) receives, stores, indexes, and provides query interfaces for those logs. Forwarders handle the last mile of log collection; aggregators handle storage and search. You typically need both.

### Should I use UDP or TCP for syslog forwarding?

UDP is the traditional syslog transport and has the lowest overhead, but it offers no delivery guarantees -- lost packets are gone forever. TCP guarantees delivery but adds latency and requires connection management. For critical logs (security events, audit trails), use TCP or RELP (Reliable Event Logging Protocol, supported by Rsyslog and syslog-ng). For high-volume, low-criticality logs, UDP is acceptable.

### Can Vector replace both Rsyslog and a separate metrics collector?

Yes. Vector can collect syslog data, application logs, and metrics (including Prometheus endpoints) in a single process. This reduces operational complexity compared to running Rsyslog for logs plus a separate metrics agent. Vector internal telemetry also provides visibility into its own pipeline health.

### How do I handle log volume spikes without dropping messages?

All three tools support disk-based buffering. Configure a disk queue with sufficient capacity to absorb spikes. In Vector, set `buffer.type = "disk"` on your sinks. In Rsyslog, use disk-assisted queues with `queue.filename` and `queue.maxdiskspace`. In syslog-ng, use `disk-buffer()` in your destinations. Monitor queue depths and set alerts when they exceed thresholds.

### Which tool is easiest to migrate to from an existing Rsyslog setup?

syslog-ng has the most similar configuration paradigm and can often parse Rsyslog config files with minor adjustments. Vector requires a full rewrite of configuration in TOML/VRL, but its validation and error messages make the migration process more guided. Plan for a parallel deployment period where both tools run side-by-side to verify output parity.

### Do these tools support TLS encryption for log transport?

Yes. All three support TLS for both receiving and sending syslog. Vector uses native TLS configuration in its sources and sinks. syslog-ng supports TLS via the `tls()` option in source/destination blocks. Rsyslog supports TLS through the `gtls` driver. Always use TLS when forwarding logs across untrusted networks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Syslog Forwarders: Vector vs syslog-ng vs Rsyslog",
  "description": "Compare Vector, syslog-ng, and Rsyslog for self-hosted log forwarding. Performance benchmarks, Docker Compose configs, and migration guidance.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
