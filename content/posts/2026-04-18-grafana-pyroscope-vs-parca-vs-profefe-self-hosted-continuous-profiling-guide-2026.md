---
title: "Grafana Pyroscope vs Parca vs Profefe: Best Self-Hosted Continuous Profiling Platforms 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "profiling", "performance", "observability"]
draft: false
description: "Compare Grafana Pyroscope, Parca, and Profefe — the top open-source continuous profiling platforms. Self-hosted deployment guides, Docker configs, and feature comparison."
---

Continuous profiling captures performance data from your running applications at all times — CPU usage, memory allocations, blocking profiles, and goroutine contention — without the overhead of manual sampling sessions. Unlike traditional profiling where you attach a profiler for a few minutes and hope to catch the problem, continuous profiling keeps a running history you can query retroactively when incidents occur.

For teams running self-hosted infrastructure, three open-source platforms stand out: **Grafana Pyroscope**, **Parca**, and **Profefe**. This guide compares their features, deployment options, and helps you choose the right tool for your observability stack.

## Why Self-Hosted Continuous Profiling Matters

Traditional profiling is reactive and lossy. You trigger a profiling session when you suspect a problem, collect a flame graph, and then stop. If the issue doesn't reproduce, you have nothing to analyze. Continuous profiling solves this by collecting profiles every 10-100 seconds and storing them with full time-series context.

The benefits of self-hosting your profiling infrastructure include:

- **Data sovereignty** — profiles contain stack traces, function names, and sometimes argument hints. Keeping them on your own infrastructure avoids sending potentially sensitive code paths to third-party services.
- **Cost control** — continuous profiling generates significant data volume. Self-hosted solutions avoid per-GB or per-host SaaS pricing that scales with your infrastructure.
- **Integration with existing tooling** — self-hosted profilers integrate directly with your [prometheus](https://prometheus.io/), Grafana, and alerting stack without cross-vendor authentication.
- **No vendor lock-in** — open-source profiling platforms use standard formats like pprof, making your data portable across tools.

If you're already running a self-hosted observability stack, adding continuous profiling is a natural extension. For teams using tools like [Signoz, Grafana, or HyperDX for APM monitoring](../self-hosted-datadog-alternative-signoz-grafana-hyperdx-2026/), profiling adds the missing dimension of resource-level performance data. And for those building observability pipelines with [OpenTelemetry collectors](../self-hosted-opentelemetry-collector-observability-pipeline-2026/), profiling data can be correlated with traces and metrics for a complete performance picture.

## Tool Comparison at a Glance

| Feature | Grafana Pyroscope | Parca | Profefe |
|---------|-------------------|-----|---------|
| **GitHub Stars** | 11,366 | 4,843 | 625 |
| **Primary Language** | Go | TypeScript | Go |
| **Last Updated** | April 2026 | April 2026 | February 2023 |
| **Profile Format** | pprof (native) | pprof (native) | pprof (native) |
| **Multi-tenancy** | Yes | Yes | No |
| **Cluster Mode** | Yes (active-active) | Yes (via object storage) | No |
| **Push Model** | Yes (SDK-based) | Yes (SDK-based) | Yes (CLI/SDK) |
| **Pull Model** | Yes (eBPF auto-profiling) | Yes (parca-agent, eBPF) | No |
| **eBPF Support** | Yes | Yes | No |
| **Storage Backend** | Built-in / S3 / GCS | Object storage (S3, GCS, Azure) | Local disk / PostgreSQL |
| **Grafana Integration** | Native datasource | Via plugin | No |
| **[kubernetes](https://kubernetes.io/) Operator** | Yes | Yes | No |
| **Profile Types** | CPU, memory, goroutine, block, mutex | CPU, memory, goroutine, block, mutex | CPU, memory (Go only) |
| **Language Support** | Go, Java, Python, Ruby, .NET, Rust | Go, Java, Python, Ruby, .NET, eBPF | Go (primary), any pprof-compatible |
| **License** | AGPLv3 | Apache 2.0 | Apache 2.0 |

Grafana Pyroscope leads in adoption and feature breadth, largely due to Grafana Labs' backing and the acquisition of the original Phlare project. Parca offers the most liberal license (Apache 2.0) and deep eBPF integration. Profefe, while the pioneer of continuous profiling for Go applications, has seen slower development in recent years.

## Grafana Pyroscope: The Feature-Rich Leader

Pyroscope started as an independent project by Pyroscope.io and was acquired by Grafana Labs in 2022. Since then, it has been integrated into the Grafana ecosystem and expanded to support multiple languages, eBPF auto-profiling, and multi-tenant clusters.

### Key Features

- **Multi-language SDKs** — official agents for Go, Java, Python, Ruby, .NET, and Node.js
- **eBPF auto-profiling** — profile any process running on a Linux host without code changes or SDK integration
- **Adaptive profiling** — dynamically adjusts sampling rate based on activity to reduce overhead
- **Grafana native** — works as a Grafana datasource with built-in flame graph visualization
- **Horizontal scaling** — active-active cluster mode for high availability
- **Long-term storage** — tier profiles to S3, GCS, or local disk

### Deployment Architecture

Pyroscope supports several deployment modes:

1. **Single binary** — simplest setup, all components in one process
2. **Microservices** — separate agent, store, and query components for scale
3. **Kubernetes operator** — full lifecycle management on K8s clusters

## Parca: eBPF-Native Continuous Profiling

Parca was created by Polar Signals and is designed from the ground up for cloud-native environments. Its standout feature is **parca-agent**, an eBPF-based profiler that can instrument any running process without SDK integration — making it ideal for profiling third-party software, system services, and compiled binaries where you don't control the source code.

### Key Features

- **parca-agent** — eBPF profiler that auto-discovers and profiles all processes on a host
- **Object storage native** — stores all profile data in S3-compatible storage, making it stateless and scalable
- **parca-query** — powerful query engine with PromQL-like syntax for profile analysis
- **Apache 2.0 license** — the most permissive option among the three platforms
- **Kubernetes-native** — deploys as a DaemonSet for cluster-wide profiling
- **Debug info extraction** — automatically extracts symbol information from binaries for accurate flame graphs

## Profefe: The Go-First Profiler

Profefe was one of the first continuous profiling platforms designed specifically for Go applications. It uses Go's built-in `pprof` runtime profiler to collect profiles and stores them for historical analysis. While it lacks the multi-language support and eBPF capabilities of Pyroscope and Parca, it remains a lightweight option for Go-only shops.

### Key Features

- **Simple architecture** — single binary with minimal dependencies
- **Go-native** — leverages Go's runtime profiler with zero overhead integration
- **RESTful API** — straightforward HTTP API for profile collection and retrieval
- **Lightweight** — minimal resource footprint, suitable for small deployments
- **PostgreSQL backend** — optional database storage for multi-node setups

## [docker](https://www.docker.com/) Deployment Guides

### Grafana Pyroscope Docker Setup

```yaml
version: "3.8"

services:
  pyroscope:
    image: grafana/pyroscope:latest
    container_name: pyroscope
    ports:
      - "4040:4040"
    volumes:
      - pyroscope-data:/var/lib/pyroscope
    environment:
      - PYROSCOPE_LOG_LEVEL=info
      - PYROSCOPE_STORAGE_TYPE=local
      - PYROSCOPE_RETENTION=720h
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2"

volumes:
  pyroscope-data:
```

Start Pyroscope with:

```bash
docker compose up -d
```

Access the UI at `http://localhost:4040`. For production deployments with long-term storage, configure S3:

```yaml
    environment:
      - PYROSCOPE_STORAGE_TYPE=s3
      - PYROSCOPE_S3_BUCKET=pyroscope-profiles
      - PYROSCOPE_S3_REGION=us-east-1
      - PYROSCOPE_S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
```

### Parca Docker Setup

```yaml
version: "3.8"

services:
  parca:
    image: ghcr.io/parca-dev/parca:latest
    container_name: parca
    ports:
      - "7070:7070"
    volumes:
      - parca-data:/data
      - ./parca-config.yaml:/etc/parca/parca.yaml:ro
    command:
      - "--config-path=/etc/parca/parca.yaml"
      - "--storage-path=/data"
      - "--cors-allowed-origins=*"
    restart: unless-stopped

  parca-agent:
    image: ghcr.io/parca-dev/parca-agent:latest
    container_name: parca-agent
    privileged: true
    pid: host
    command:
      - "--http-address=:7071"
      - "--node=test-node"
      - "--log-level=info"
      - "--remote-store-address=parca:7070"
      - "--remote-store-insecure"
    restart: unless-stopped

volumes:
  parca-data:
```

Create `parca-config.yaml`:

```yaml
object_storage:
  bucket:
    type: "FILESYSTEM"
    config:
      directory: "/data"

scrape_configs:
  - job_name: "parca"
    scrape_interval: "10s"
    static_configs:
      - targets: ["localhost:7070"]
```

The parca-agent uses eBPF to auto-profile all processes. The `privileged: true` and `pid: host` settings are required for eBPF program attachment.

### Profefe Docker Setup

```yaml
version: "3.8"

services:
  profefe:
    image: profefe/profefe:latest
    container_name: profefe
    ports:
      - "10100:10100"
    volumes:
      - profefe-data:/var/lib/profefe
    environment:
      - PROFEFE_STORAGE_PATH=/var/lib/profefe
      - PROFEFE_LISTEN=:10100
    restart: unless-stopped

volumes:
  profefe-data:
```

Start and verify:

```bash
docker compose up -d
curl http://localhost:10100/api/version
```

## Instrumenting Your Applications

### Go Application with Pyroscope SDK

```bash
go get github.com/grafana/pyroscope-go
```

```go
package main

import (
    "runtime"
    "time"

    pyroscope "github.com/grafana/pyroscope-go"
)

func init() {
    pyroscope.Start(pyroscope.Config{
        ApplicationName: "my-go-app",
        ServerAddress:   "http://pyroscope:4040",
        Logger:          pyroscope.StandardLogger,
        Tags:            map[string]string{"env": "production"},
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocObjects,
            pyroscope.ProfileAllocSpace,
            pyroscope.ProfileInuseObjects,
            pyroscope.ProfileInuseSpace,
            pyroscope.ProfileGoroutines,
            pyroscope.ProfileMutexCount,
            pyroscope.ProfileMutexDuration,
            pyroscope.ProfileBlockCount,
            pyroscope.ProfileBlockDuration,
        },
    })
}

func main() {
    // Your application code runs normally.
    // Profiles are collected every 10 seconds automatically.
    for {
        time.Sleep(time.Second)
    }
}
```

### Python Application with Pyroscope SDK

```bash
pip install pyroscope-io
```

```python
import pyroscope

pyroscope.configure(
    application_name="my-python-app",
    server_address="http://pyroscope:4040",
    enable_logging=True,
)

# Profiles are collected automatically via eBPF or the SDK.
# Your application code runs normally.
```

### Java Application with Pyroscope Agent

```bash
java -javaagent:pyroscope-java.jar \
     -Dpyroscope.application.name=my-java-app \
     -Dpyroscope.server.address=http://pyroscope:4040 \
     -Dpyroscope.format=jfr \
     -jar your-application.jar
```

The JFR (Java Flight Recorder) format provides detailed JVM profiling including GC pauses, thread contention, and lock analysis.

## Integrating Profiling with Your Observability Stack

Continuous profiling becomes most powerful when combined with metrics, logs, and traces. Here's how profiling fits into the broader observability picture:

| Data Type | What It Shows | Time Resolution | Self-Hosted Tools |
|-----------|--------------|-----------------|-------------------|
| **Metrics** | Aggregated counters, gauges, histograms | 15-60 seconds | [Prometheus, Grafana, VictoriaMetrics](../prometheus-vs-grafana-vs-victoriametrics/) |
| **Traces** | Request flows across services | Per-request | [Signoz, Jaeger, Uptrace](../signoz-jaeger-uptrace-self-hosted-apm-distributed-tracing-guide/) |
| **Logs** | Application events and errors | Per-event | Loki, Graylog, OpenSearch |
| **Profiles** | CPU, memory, and resource usage by code line | 10-100 seconds | Pyroscope, Parca, Profefe |

The key insight is that profiling answers a different question than the other observability pillars. Metrics tell you *that* something is slow. Traces tell you *which service* is slow. Profiling tells you *which line of code* is slow. Together, they provide complete visibility into system behavior.

For teams using [metrics collectors like Telegraf or StatsD](../self-hosted-metrics-collectors-telegraf-statsd-vector-collectd-guide-2026/), adding continuous profiling fills the gap between aggregated statistics and line-level performance data.

## Choosing the Right Platform

**Choose Grafana Pyroscope if:**
- You already use Grafana for dashboards and want native profiling integration
- You need multi-language SDK support out of the box
- You want eBPF auto-profiling alongside SDK-based profiling
- Your team values active development and Grafana Labs' backing

**Choose Parca if:**
- You prefer Apache 2.0 licensing (important for commercial redistribution)
- You want eBPF-first profiling with automatic process discovery
- You need object storage-native architecture for cost-effective long-term retention
- You run primarily in Kubernetes and want DaemonSet-based deployment

**Choose Profefe if:**
- You run exclusively Go applications
- You want the simplest possible deployment with minimal resource usage
- You need a lightweight profiler that doesn't require a full observability stack
- You prefer a minimal API surface for profile collection and retrieval

## Performance Overhead

All three platforms are designed for production use with minimal overhead:

- **Pyroscope SDK**: 0.5-2% CPU overhead, <50MB memory for typical Go applications
- **Parca agent (eBPF)**: 1-3% CPU overhead for system-wide profiling, no application code changes required
- **Profefe**: <1% CPU overhead using Go's native runtime profiler

The key advantage of continuous profiling over periodic profiling sessions is that the overhead is spread across time. Rather than a 10-minute profiling session at 10% overhead, continuous profiling runs at 1-2% overhead continuously, giving you 24/7 visibility without performance degradation.

## FAQ

### What is continuous profiling and how does it differ from traditional profiling?

Traditional profiling requires you to manually attach a profiler (like `go tool pprof`) to a running process for a limited time window. You get a single snapshot of performance data. Continuous profiling collects profiles automatically at regular intervals (every 10-100 seconds) and stores them with timestamps, creating a searchable history. When an incident occurs hours or days later, you can query the exact time window to see what your code was doing.

### Can continuous profiling work with compiled languages like C++ or Rust?

Yes, but with limitations. Both Grafana Pyroscope and Parca support eBPF-based auto-profiling, which works at the kernel level and can profile any Linux process regardless of language. However, accurate symbol resolution (mapping memory addresses back to function names) requires debug symbols or a separate symbol server. For Go, Java, Python, and Ruby, SDK-based profiling provides the most accurate results with full function name resolution.

### How much storage does continuous profiling require?

Profile data is relatively compact compared to logs or traces. A typical Go application generates 100-500KB of profile data per collection interval. At 10-second intervals, this translates to roughly 1-5 GB per application per month with standard retention. Both Pyroscope and Parca support tiered storage, moving older profiles to S3-compatible object storage for cost-effective long-term retention.

### Is eBPF profiling safe for production use?

Yes, eBPF programs run in a verified sandbox within the Linux kernel. The verifier ensures that eBPF programs cannot access arbitrary memory, enter infinite loops, or crash the kernel. Both Pyroscope and Parca use well-tested eBPF programs for profiling that have been running in production at scale. The `privileged: true` Docker setting is required because eBPF program loading requires `CAP_SYS_ADMIN` capabilities.

### Do I need to modify my application code to use continuous profiling?

It depends on the approach. SDK-based profiling (Pyroscope, Profefe) requires adding a few lines of initialization code to your application. eBPF-based profiling (Parca agent, Pyroscope eBPF) requires zero code changes — it profiles any running process by attaching to kernel-level performance counters. eBPF is ideal for profiling third-party services, system daemons, or legacy applications where you cannot modify the source code.

### Which profile types are most useful for debugging?

The most commonly useful profile types are:
- **CPU profiles** — identify which functions consume the most CPU time
- **Memory (heap) profiles** — track memory allocations to find leaks and optimize GC pressure
- **Goroutine profiles** — detect goroutine leaks and blocking patterns
- **Mutex profiles** — identify lock contention that causes latency spikes
- **Block profiles** — find channels or synchronization primitives causing delays

Start with CPU and memory profiles, then add goroutine, mutex, and block profiles as needed for specific debugging scenarios.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Grafana Pyroscope vs Parca vs Profefe: Best Self-Hosted Continuous Profiling Platforms 2026",
  "description": "Compare Grafana Pyroscope, Parca, and Profefe — the top open-source continuous profiling platforms. Self-hosted deployment guides, Docker configs, and feature comparison.",
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
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
