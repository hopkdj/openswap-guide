---
title: "Self-Hosted Process Monitoring Exporters: process-exporter vs Node Problem Detector vs Telegraf (2026)"
date: "2026-05-25"
tags: ["monitoring", "prometheus", "process", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare process-exporter, Kubernetes Node Problem Detector, and Telegraf procstat for self-hosted process-level monitoring. Docker deployment guides and Prometheus integration."
---

System monitoring at the host level requires more than CPU and memory metrics — you need visibility into individual processes. Which applications are consuming the most resources? Are critical services running? Have any processes entered problematic states? Process monitoring exporters answer these questions by exposing per-process metrics to your observability stack.

This guide compares three approaches to self-hosted process monitoring: the dedicated **process-exporter** for Prometheus, the **Kubernetes Node Problem Detector** for cluster-wide node health, and **Telegraf** with its procstat input plugin for unified metric collection. Each targets a different scale and use case, from single-host monitoring to enterprise Kubernetes clusters.

## Why Self-Host Process Monitoring?

Process-level visibility is essential for production infrastructure. When a Java application starts consuming 90% of CPU, you need to know immediately — not after users report slowdowns. Process monitoring provides the granularity that aggregate host metrics cannot.

Self-hosting process monitoring gives you full control over metric retention, alerting rules, and data privacy. Unlike SaaS monitoring platforms, your process data never leaves your infrastructure. This is critical for regulated industries where process names, arguments, and resource usage patterns could reveal sensitive operational details.

Cost is another factor. Commercial APM platforms charge per host and per metric. Self-hosted process exporters feed into your existing Prometheus or Grafana stack at zero marginal cost, regardless of how many processes you monitor.

For GPU-specific monitoring, see our [GPU monitoring comparison](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide/). For broader metric collection, our [metrics collectors guide](../self-hosted-metrics-collectors-telegraf-statsd-vector-collectd-guide/) covers Telegraf, statsd, and Vector. Database-focused monitoring is covered in our [PostgreSQL monitoring guide](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/).

## process-exporter: Dedicated Prometheus Process Metrics

[process-exporter](https://github.com/ncabatoff/process-exporter) (2,117+ stars) is a Prometheus exporter that reads `/proc` filesystem data and exposes detailed per-process metrics. It groups processes by configurable name patterns and reports CPU, memory, file descriptor, and thread counts.

### Features

- **Process grouping** — group processes by name, command line regex, or parent-child relationships
- **Detailed metrics** — CPU time, resident/set memory, virtual memory, file descriptors, threads, open files
- **Configurable filtering** — include/exclude processes by name, user, or command pattern
- **Prometheus native** — outputs standard Prometheus metrics, scrapable by any Prometheus server
- **Low overhead** — reads `/proc` directly, minimal CPU and memory impact

### Docker Deployment

```yaml
version: "3.8"
services:
  process-exporter:
    image: ncabatoff/process-exporter:latest
    ports:
      - "9256:9256"
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - ./config.yml:/config/config.yml:ro
    command:
      - "--procfs=/host/proc"
      - "--config.path=/config/config.yml"
    restart: unless-stopped
```

Configuration file (`config.yml`):

```yaml
process_names:
  - name: "{{.Comm}}"
    cmdline:
      - ".+"
  - name: "java"
    cmdline:
      - "java"
  - name: "postgres"
    cmdline:
      - "postgres"
  - name: "nginx"
    cmdline:
      - "nginx"
```

### Prometheus Scraping

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "process-exporter"
    static_configs:
      - targets: ["process-exporter-host:9256"]
```

Key metrics exposed:
- `namedprocess_namegroup_cpu_seconds_total` — CPU time per process group
- `namedprocess_namegroup_memory_bytes` — memory usage (resident, virtual, proportional)
- `namedprocess_namegroup_open_filedesc` — open file descriptors
- `namedprocess_namegroup_num_procs` — number of processes in group
- `namedprocess_namegroup_threads` — thread count

### Grafana Dashboard

Import community dashboard ID 249 for a pre-built process monitoring view, or create custom panels:

```promql
# Top 5 processes by CPU usage
topk(5, rate(namedprocess_namegroup_cpu_seconds_total{mode="system"}[5m]))

# Processes exceeding memory threshold
namedprocess_namegroup_memory_bytes{memtype="resident"} > 1073741824
```

## Node Problem Detector: Kubernetes Node Health

[Kubernetes Node Problem Detector](https://github.com/kubernetes/node-problem-detector) (3,408+ stars) is a daemon that runs on each Kubernetes node and detects conditions that could affect pod scheduling or node health. It monitors for hardware issues, kernel problems, and container runtime errors.

### Features

- **Node condition reporting** — sets Kubernetes node conditions (Ready, MemoryPressure, DiskPressure)
- **Hardware monitoring** — detects kernel panics, OOM kills, disk errors, and network issues
- **Custom monitors** — supports custom monitoring scripts via JSON-based plugin system
- **Event generation** — creates Kubernetes events for detected problems
- **Cloud provider integration** — works with GKE, EKS, and AKS node health reporting
- **Process monitoring** — watches for critical process failures (kubelet, container runtime)

### Kubernetes Deployment

Deploy as a DaemonSet across all nodes:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-problem-detector
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: node-problem-detector
  template:
    metadata:
      labels:
        app: node-problem-detector
    spec:
      hostPID: true
      hostNetwork: true
      containers:
        - name: node-problem-detector
          image: registry.k8s.io/node-problem-detector/node-problem-detector:v0.8.15
          securityContext:
            privileged: true
          volumeMounts:
            - name: log
              mountPath: /var/log/journal
              readOnly: true
            - name: localtime
              mountPath: /etc/localtime
              readOnly: true
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 200m
              memory: 256Mi
      volumes:
        - name: log
          hostPath:
            path: /var/log/journal
        - name: localtime
          hostPath:
            path: /etc/localtime
```

### Custom Problem Monitors

Create custom monitors by adding JSON configurations to `/etc/node-problem-detector/config.d/`:

```json
{
  "plugin": "custom",
  "invoke_interval": "30s",
  "timeout": "5s",
  "max_output_length": 80,
  "concurrency": 3,
  "source": "custom-process-monitor",
  "metrics": [
    {
      "metric_name": "critical_process_running",
      "condition": "check_process.sh kubelet"
    }
  ]
}
```

Custom monitoring script (`check_process.sh`):

```bash
#!/bin/bash
if pgrep -x "$1" > /dev/null 2>&1; then
  echo "ok"
  exit 0
else
  echo "process $1 not found"
  exit 1
fi
```

### Node Conditions

Node Problem Detector reports conditions that affect scheduling:
- **KernelDeadlock** — kernel is not responding
- **ReadonlyFilesystem** — root filesystem mounted read-only
- **CorruptDockerOverlay** — Docker overlay filesystem corruption
- **MemoryPressure** — node memory critically low
- **DiskPressure** — node disk space critically low

These conditions automatically prevent new pod scheduling on affected nodes.

## Telegraf procstat: Unified Metric Collection

[Telegraf](https://github.com/influxdata/telegraf) (14,000+ stars) is a plugin-driven metric collection agent that includes a powerful procstat input plugin for process monitoring. Unlike dedicated exporters, Telegraf collects process metrics alongside system, network, and application metrics in a single agent.

### Features

- **Unified collection** — process metrics combined with 300+ other input plugins
- **Pattern matching** — filter processes by name, executable, command line, or user
- **Extensive metrics** — CPU percentage, memory usage, file descriptors, threads, IO bytes, context switches
- **Multiple outputs** — send metrics to InfluxDB, Prometheus, Kafka, Elasticsearch, and more
- **Cross-platform** — Linux, Windows, macOS support

### Docker Deployment

```yaml
version: "3.8"
services:
  telegraf:
    image: telegraf:latest
    pid: host
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - HOST_PROC=/host/proc
      - HOST_SYS=/host/sys
    ports:
      - "9273:9273"
    restart: unless-stopped
```

Telegraf configuration (`telegraf.conf`):

```toml
[agent]
  interval = "10s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  collection_jitter = "0s"
  flush_interval = "10s"
  flush_jitter = "0s"
  hostname = ""
  omit_hostname = false

[[inputs.procstat]]
  pattern = "java|postgres|nginx|redis-server"
  prefix = ""
  fielddrop = ["pid"]

[[outputs.prometheus_client]]
  listen = ":9273"
  metric_version = 2
```

### Process Metric Collection

The procstat plugin collects:
- `procstat_lookup` — number of matching processes
- `procstat_cpu_usage` — CPU utilization percentage per process
- `procstat_memory_rss` — resident set size
- `procstat_memory_vms` — virtual memory size
- `procstat_num_fds` — open file descriptor count
- `procstat_num_threads` — thread count
- `procstat_read_bytes` / `procstat_write_bytes` — disk IO per process
- `procstat_voluntary_context_switches` / `procstat_involuntary_context_switches` — scheduling metrics

## Feature Comparison

| Feature | process-exporter | Node Problem Detector | Telegraf procstat |
|---------|------------------|----------------------|-------------------|
| **Primary role** | Process metrics exporter | Node health detector | Unified metric agent |
| **Metric format** | Prometheus | Kubernetes events + Prometheus | Multiple (InfluxDB, Prometheus, etc.) |
| **Process grouping** | Yes (configurable patterns) | No (individual processes) | Yes (pattern matching) |
| **CPU metrics** | Yes (cumulative + rate) | Limited (node-level) | Yes (percentage-based) |
| **Memory metrics** | Yes (RSS, VMS, PSS) | Node-level only | Yes (RSS, VMS) |
| **File descriptors** | Yes | No | Yes |
| **IO metrics** | No | No | Yes (read/write bytes) |
| **Kubernetes integration** | Manual (scrape config) | Native (DaemonSet, node conditions) | Manual (sidecar or host agent) |
| **Alerting** | Via Prometheus rules | Via Kubernetes events | Via output plugins |
| **Docker image** | Docker Hub | registry.k8s.io | Docker Hub |
| **Stars** | 2,117+ | 3,408+ | 14,000+ |
| **Best for** | Prometheus-centric monitoring | Kubernetes cluster health | Multi-output metric collection |

## Choosing the Right Solution

**Use process-exporter** when you run Prometheus and need dedicated, high-granularity process metrics. Its configurable grouping lets you aggregate metrics by application (all Java processes, all Postgres workers) rather than tracking individual PIDs. Ideal for teams already invested in the Prometheus/Grafana ecosystem.

**Use Node Problem Detector** when you manage a Kubernetes cluster and need automated node health detection. It integrates natively with Kubernetes scheduling, automatically cordoning unhealthy nodes. Best for platform teams running production Kubernetes workloads who need proactive node issue detection.

**Use Telegraf** when you need process monitoring alongside other metric collection (system, network, application). Its 300+ input plugins make it the most versatile option, especially if your observability stack uses InfluxDB or you need to send metrics to multiple destinations simultaneously.

## FAQ

### Can I run process-exporter without Docker?

Yes. Download the binary from GitHub releases and run it directly: `./process-exporter --procfs /proc --config.path config.yml`. The Docker approach is recommended for easier updates and isolation, but the binary works on any Linux system.

### Does Node Problem Detector replace Prometheus monitoring?

No. Node Problem Detector focuses on node-level health conditions (kernel issues, disk errors, OOM kills) and reports them as Kubernetes events and node conditions. It does not provide the detailed time-series metrics that Prometheus exporters offer. Many teams run both: NPD for node health and process-exporter for application-level metrics.

### How do I monitor specific processes with Telegraf?

Use the `pattern` field in the procstat input configuration to match process names or command lines. For example, `pattern = "java"` matches all Java processes. You can also use `exe` for exact executable names, `user` to filter by process owner, or `pid_file` to track processes by their PID file.

### Can process-exporter monitor Windows processes?

No. process-exporter reads the Linux `/proc` filesystem and is Linux-only. For Windows process monitoring, use Telegraf's procstat plugin, which supports both Linux and Windows.

### How often should I scrape process metrics?

For most use cases, a 10-30 second scrape interval is sufficient. Process-exporter and Telegraf both have minimal overhead when reading `/proc`. Node Problem Detector runs checks every 30 seconds by default. Avoid sub-5-second intervals as they can cause measurable CPU overhead on systems with many processes.

### What happens if a critical process crashes?

With process-exporter, the process count metric drops to zero — set up a Prometheus alert rule: `namedprocess_namegroup_num_procs{groupname="nginx"} == 0`. Node Problem Detector generates a Kubernetes event and can set a node condition. Telegraf's procstat lookup count drops — alert on `procstat_lookup{result="success"} < 1`.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Process Monitoring Exporters: process-exporter vs Node Problem Detector vs Telegraf (2026)",
  "description": "Compare process-exporter, Kubernetes Node Problem Detector, and Telegraf procstat for self-hosted process-level monitoring.",
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
