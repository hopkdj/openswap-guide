---
title: "Self-Hosted eBPF Prometheus Exporters: Cloudflare vs dswarbrick vs DigitalOcean"
date: "2026-05-23"
tags: ["ebpf", "prometheus", "monitoring", "observability", "exporter", "self-hosted"]
draft: false
---

eBPF (extended Berkeley Packet Filter) has revolutionized Linux observability by allowing safe, in-kernel instrumentation of system calls, network events, and process behavior. When combined with Prometheus, eBPF exporters provide deep performance metrics without the overhead of user-space sampling. This guide compares three prominent eBPF-based Prometheus exporters: **Cloudflare's ebpf_exporter**, **dswarbrick's eBPF block I/O exporter**, and **DigitalOcean's Go eBPF exporter**.

## What Are eBPF Prometheus Exporters?

Traditional monitoring tools like top, iostat, or vmstat sample system state at fixed intervals, missing short-lived events and adding measurement overhead. eBPF programs run inside the Linux kernel, attaching to tracepoints, kprobes, and uprobes to capture events as they happen. eBPF exporters aggregate these kernel-level events and expose them as Prometheus-compatible metrics at `/metrics` endpoints.

The key advantage: **near-zero overhead**. eBPF programs are JIT-compiled and run in a verified sandbox within the kernel. Metrics are aggregated in-kernel using eBPF maps, so only summary statistics (not raw events) are exported to user-space.

## Cloudflare ebpf_exporter — Production-Grade Custom eBPF Metrics

[cloudflare/ebpf_exporter](https://github.com/cloudflare/ebpf_exporter) (2,586 stars) is the most widely-used eBPF Prometheus exporter. Developed by Cloudflare's infrastructure team, it provides a YAML-driven configuration system for defining custom eBPF programs and mapping their output to Prometheus metrics.

### Installation

```bash
# Build from source
git clone https://github.com/cloudflare/ebpf_exporter.git
cd ebpf_exporter
make

# Or install via Go
go install github.com/cloudflare/ebpf_exporter/cmd/ebpf_exporter@latest
```

### Configuration

Cloudflare's exporter ships with dozens of pre-built configs for common monitoring scenarios:

```yaml
# config.yaml - Block I/O latency tracking
programs:
  - name: biolatency
    metrics:
      - name: block_io_latency_seconds
        table: hist
        type: histogram
        help: Block I/O latency distribution
        bucket_type: exponential
        bucket_multiplier: 0.000001  # microseconds to seconds
        bucket_keys: false
        keys:
          - name: operation
            type: d_x8
            size: 1
```

Run with a pre-built config:
```bash
sudo ./ebpf_exporter --config=configs/biolatency.yaml --web.listen-address=":9435"
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ebpf-exporter:
    image: ghcr.io/cloudflare/ebpf_exporter:latest
    container_name: ebpf-exporter
    network_mode: host
    pid: host
    cap_add:
      - SYS_ADMIN
      - BPF
      - PERFMON
    security_opt:
      - apparmor:unconfined
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - ./configs:/configs:ro
    command:
      - '--config=/configs/biolatency.yaml'
      - '--web.listen-address=:9435'
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
```

### Available Pre-Built Configs

The project includes configs for:
- **biolatency** — Block I/O latency histograms
- **biosnoop** — Per-process block I/O tracing
- **cachestat** — Page cache hit/miss ratios
- **runqlat** — CPU run queue latency
- **tcpconnlat** — TCP connection establishment latency
- **tcpstates** — TCP state transition tracking
- **oomkill** — OOM killer event tracking
- **ext4dist** — ext4 filesystem operation latency

## dswarbrick eBPF Exporter — Specialized Block I/O Latency

[dswarbrick/ebpf_exporter](https://github.com/dswarbrick/ebpf_exporter) (76 stars) focuses specifically on block I/O latency measurement, providing detailed histograms of read and write latencies across all block devices. It is simpler than Cloudflare's general-purpose exporter but offers deeper I/O analysis for storage-heavy workloads.

### Installation

```bash
# Dependencies
sudo apt install clang llvm libbpf-dev

# Build
git clone https://github.com/dswarbrick/ebpf_exporter.git
cd ebpf_exporter
make

# Run
sudo ./ebpf_exporter -listen-address=:9436
```

### Key Metrics

The exporter exposes these Prometheus metrics:

| Metric | Type | Description |
|---|---|---|
| `biodist_read_seconds` | Histogram | Read latency distribution |
| `biodist_write_seconds` | Histogram | Write latency distribution |
| `biodist_discard_seconds` | Histogram | TRIM/discard latency |
| `biodist_flush_seconds` | Histogram | Cache flush latency |

### Docker Compose for I/O Monitoring

```yaml
version: "3.8"
services:
  io-exporter:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: io-ebpf-exporter
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    command: ["-listen-address=:9436"]
    restart: unless-stopped
```

## DigitalOcean Go eBPF Exporter — Pure Go Implementation

[digitalocean-labs/ebpf_exporter](https://github.com/digitalocean-labs/ebpf_exporter) (29 stars) is a pure-Go eBPF exporter that uses the cilium/ebpf library instead of requiring clang/llvm toolchain dependencies. This makes it easier to build and deploy in environments where C compilation toolchains are not available.

### Installation

```bash
# Build (no C toolchain needed beyond libbpf headers)
git clone https://github.com/digitalocean-labs/ebpf_exporter.git
cd ebpf_exporter
go build -o ebpf_exporter ./cmd/ebpf_exporter

# Run
sudo ./ebpf_exporter --config ./configs/cpu-softirq.yaml
```

### Advantages of Go-Based Approach

- **No clang/LLVM dependency** — uses cilium/ebpf for loading eBPF programs
- **Cross-compilation** — `GOOS=linux GOARCH=arm64 go build` produces ARM64 binaries
- **Easier CI/CD** — no need to install kernel headers and clang in build pipelines
- **Type safety** — Go's struct-based eBPF map definitions reduce boilerplate

### Docker Compose

```yaml
version: "3.8"
services:
  go-ebpf-exporter:
    image: golang:1.22-alpine
    container_name: go-ebpf-exporter
    working_dir: /app
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - ./go-ebpf-exporter:/app/ebpf_exporter:ro
      - ./configs:/app/configs:ro
    command: ["./ebpf_exporter", "--config", "/app/configs/cpu-softirq.yaml"]
    restart: unless-stopped
```

## Comparison Table

| Feature | Cloudflare ebpf_exporter | dswarbrick eBPF | DigitalOcean Go eBPF |
|---|---|---|---|
| **Stars** | 2,586 | 76 | 29 |
| **Language** | Go + C (clang/LLVM) | Go + C (clang/LLVM) | Pure Go (cilium/ebpf) |
| **Scope** | General-purpose (many configs) | Block I/O focused | General-purpose |
| **Pre-Built Configs** | 30+ configs | 1 (block I/O) | ~10 configs |
| **Metric Types** | Histogram, Counter, Gauge | Histogram only | Histogram, Counter |
| **Docker Support** | Official image | Manual Dockerfile | Go build in container |
| **BPF CO-RE** | Yes | Yes | Yes |
| **Kernel Requirements** | 5.8+ (BPF CO-RE) | 5.8+ (BPF CO-RE) | 5.8+ (BPF CO-RE) |
| **Build Dependencies** | clang, LLVM, libbpf | clang, LLVM, libbpf | Go + libbpf headers |
| **Best For** | Production observability | Storage performance tuning | Go-centric environments |

## Full Prometheus Stack with eBPF Monitoring

```yaml
version: "3.8"
services:
  ebpf-exporter:
    image: ghcr.io/cloudflare/ebpf_exporter:latest
    container_name: ebpf-exporter
    network_mode: host
    pid: host
    cap_add:
      - SYS_ADMIN
      - BPF
      - PERFMON
    security_opt:
      - apparmor:unconfined
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - ./ebpf-configs:/configs:ro
    command:
      - '--config=/configs/biolatency.yaml'
      - '--config=/configs/runqlat.yaml'
      - '--config=/configs/cachestat.yaml'
      - '--web.listen-address=:9435'
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped

  grafana:
    image: grafana/grafana-oss:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

## Why Self-Host Your eBPF Monitoring?

Running your own eBPF exporter pipeline gives you **kernel-level visibility** that SaaS monitoring tools cannot provide. Cloud-based APM solutions rely on agent-based sampling or synthetic monitoring — they miss short-lived kernel events like page cache evictions, CPU scheduler delays, and storage I/O queue depths.

**Cost efficiency** is another factor. eBPF monitoring replaces multiple separate tools: you no longer need iostat, vmstat, pidstat, and custom shell scripts running every minute. A single eBPF exporter captures all these metrics with lower CPU overhead. For a fleet of 50 servers, eliminating 4-5 monitoring agents per host reduces memory footprint by 200-400 MB per server — 10-20 GB of RAM saved cluster-wide.

**Data ownership** matters for compliance-sensitive environments. eBPF traces capture detailed process behavior, file access patterns, and network connections. Sending this telemetry to a third-party SaaS creates a significant data governance surface. Self-hosted eBPF exporters keep all observability data within your infrastructure boundary.

For **broader Prometheus monitoring** setup, see our [Prometheus vs Hertzbeat vs Netdata comparison](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/). If you need **eBPF tracing** for debugging rather than metrics, our [bpftrace vs BCC vs Sysdig guide](../2026-04-26-bpftrace-vs-bcc-vs-sysdig-self-hosted-ebpf-tracing-guide-2026/) covers the right tools. For complete **observability platform** comparisons, check our [OpenObserve vs Quickwit vs Siglens article](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/).

## FAQ

### What kernel version do I need for eBPF exporters?

All three exporters require Linux kernel **5.8 or newer** for BPF CO-RE (Compile Once Run Everywhere) support. This feature allows eBPF programs to access kernel data structures without recompilation for each kernel version. Most modern distributions ship kernels 5.15+ (Ubuntu 22.04 LTS, Debian 12, RHEL 9).

### Is it safe to run eBPF programs in production?

Yes. eBPF programs run in a verified sandbox — the kernel's eBPF verifier checks every program for safety before loading. Programs cannot crash the kernel, access arbitrary memory, or run infinite loops. Cloudflare has run ebpf_exporter across thousands of production servers for years without stability issues.

### What is the CPU overhead of eBPF exporters?

eBPF overhead is typically **0.1-1% CPU** depending on the number of attached programs and event frequency. A single biolatency config adds negligible overhead because it only attaches to the block layer completion path. Running 5-10 configs simultaneously typically stays under 2% CPU — far less than running equivalent user-space monitoring scripts.

### Can I run eBPF exporters in unprivileged containers?

No — loading eBPF programs requires `CAP_SYS_ADMIN`, `CAP_BPF`, and `CAP_PERFMON` capabilities. You can reduce the privilege surface by using `CAP_BPF` and `CAP_PERFMON` instead of full `CAP_SYS_ADMIN`, but some kernel versions require all three. The Docker Compose configs above use the minimal required capabilities.

### Which exporter should I choose for a production environment?

For **production use**, Cloudflare's ebpf_exporter is the clear choice — it has the most pre-built configs, active maintenance, and battle-tested deployment at Cloudflare scale. Use dswarbrick's exporter only if you need specialized block I/O analysis beyond what Cloudflare's biolatency config provides. The DigitalOcean Go exporter is best for teams with Go-centric build pipelines who want to avoid clang/LLVM dependencies.

### How do I troubleshoot eBPF program load failures?

Common causes and fixes:
- **"Operation not permitted"** — ensure the container has `CAP_BPF` and `CAP_SYS_ADMIN`
- **"Invalid argument"** — kernel version may not support the eBPF helper functions used; upgrade kernel or use simpler configs
- **"Program too large"** — eBPF programs have a 1 million instruction limit; simplify complex configs
- **"Failed to find BTF"** — install `linux-headers-$(uname -r)` and `bpfcc-tools` for BTF (BPF Type Format) data

### Do eBPF exporters work with Kubernetes?

Yes. Deploy as a **DaemonSet** so each node runs an eBPF exporter pod. Use `hostNetwork: true`, `hostPID: true`, and appropriate security context capabilities. The Cilium and Falco projects use similar patterns for their eBPF-based networking and security tools.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted eBPF Prometheus Exporters: Cloudflare vs dswarbrick vs DigitalOcean",
  "description": "Compare three eBPF-based Prometheus exporters for deep kernel-level observability: Cloudflare ebpf_exporter, dswarbrick block I/O exporter, and DigitalOcean Go eBPF exporter.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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
