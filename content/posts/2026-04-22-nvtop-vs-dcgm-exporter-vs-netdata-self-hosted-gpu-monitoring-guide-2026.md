---
title: "Best Self-Hosted GPU Monitoring Tools 2026: nvtop vs DCGM Exporter vs Netdata"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "monitoring", "gpu", "nvidia"]
draft: false
description: "Compare the best open-source GPU monitoring tools for self-hosted servers in 2026. Detailed guide covering nvtop, NVIDIA DCGM Exporter, and Netdata with Docker Compose configs and Grafana dashboards."
---

If you run a self-hosted server with a GPU — whether for Jellyfin hardware transcoding, machine learning workloads, game servers, or cryptocurrency mining — you need visibility into GPU utilization, memory usage, temperature, and power draw. Without proper monitoring, a runaway process can silently consume all VRAM, thermal throttling can cripple performance, and hardware failures can go unnoticed until it's too late.

In this guide, we compare three of the most popular open-source GPU monitoring tools for self-hosted servers: **nvtop** (terminal-based GPU process monitor), **NVIDIA DCGM Exporter** (Prometheus metrics exporter), and **Netdata** (real-time system observability with built-in GPU plugins).

## Why Monitor Your GPU?

GPUs are among the most expensive components in a server, and they're also the most sensitive to misconfiguration. Here's why GPU monitoring matters:

- **Thermal management**: Sustained high temperatures reduce GPU lifespan and trigger throttling
- **Memory leaks**: ML frameworks can silently allocate VRAM without releasing it
- **Resource contention**: Multiple services (transcoding + inference + gaming) compete for GPU time
- **Power costs**: Unoptimized GPU workloads consume significant electricity
- **Capacity planning**: Historical metrics tell you when it's time to upgrade

Unlike CPU monitoring, which has decades of mature tooling, GPU monitoring requires specialized tools that understand accelerator architectures, memory pools, and vendor-specific metrics.

## At a Glance: Comparison Table

| Feature | nvtop | DCGM Exporter | Netdata |
|---|---|---|---|
| **Primary use** | Terminal htop for GPUs | Prometheus metrics exporter | Real-time system dashboard |
| **GPU vendors** | AMD, Intel, NVIDIA, Apple, Huawei | NVIDIA only | NVIDIA, AMD (limited) |
| **Interface** | Terminal (ncurses) | Prometheus + Grafana | Web dashboard |
| **Process tracking** | Per-process GPU usage | No process-level detail | Basic process info |
| **Alerting** | No (visual only) | Via Prometheus Alertmanager | Built-in alerts |
| **Historical data** | No | Via Prometheus TSDB | Built-in storage |
| **Docker support** | Host access required | Native Docker container | Docker agent or cloud |
| **GitHub stars** | 10,512 | 1,690 | 78,554 |
| **Best for** | Quick diagnostics | Production monitoring | All-in-one observability |

## nvtop — htop for GPUs

[nvtop](https://github.com/Syllo/nvtop) is a terminal-based GPU monitoring tool that works like `htop` or `top`, but for graphics cards. It shows real-time utilization, memory consumption, temperature, and a list of processes using the GPU — all in a single terminal window.

### Key Features

- **Multi-vendor support**: Works with NVIDIA, AMD, Intel, Apple Silicon, Huawei Ascend, and Qualcomm Adreno GPUs
- **Process monitoring**: See exactly which processes are consuming GPU resources, similar to `nvidia-smi` but with a live-updating interface
- **Graph history**: Rolling utilization and memory graphs within the terminal
- **Color-coded bars**: Visual indication of compute vs. memory vs. encode/decode utilization
- **Zero dependencies**: No database, no web server, no configuration files

### Installation

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install nvtop
```

On Arch Linux:

```bash
sudo pacman -S nvtop
```

On Fedora:

```bash
sudo dnf install nvtop
```

You can also build from source for the latest version:

```bash
git clone https://github.com/Syllo/nvtop.git
cd nvtop
mkdir -p build && cd build
cmake .. -DNVIDIA_SUPPORT=ON -DAMDGPU_SUPPORT=ON -DINTEL_SUPPORT=ON
make -j$(nproc)
sudo make install
```

### Usage

Simply run:

```bash
nvtop
```

For GPU selection (if you have multiple GPUs):

```bash
nvtop -d 0    # Monitor GPU 0 only
nvtop -g      # Show GPU selection menu
```

### When to Use nvtop

nvtop excels as a **diagnostic tool**. SSH into your server, type `nvtop`, and immediately see what's eating your GPU. It's perfect for:

- Debugging why a GPU is at 100% utilization
- Checking if a container is properly accessing the GPU
- Quick thermal checks before starting a heavy workload
- Monitoring GPU memory leaks in development

However, nvtop does **not** provide historical data, alerting, or remote monitoring. You need to be at the terminal to see it.

## NVIDIA DCGM Exporter — Production-Grade GPU Metrics

The [NVIDIA Data Center GPU Manager (DCGM) Exporter](https://github.com/NVIDIA/dcgm-exporter) is the official Prometheus exporter for NVIDIA GPU telemetry. It leverages the DCGM library to collect deep hardware metrics and exposes them in Prometheus format for consumption by Grafana or other visualization tools.

### Key Features

- **Deep NVIDIA metrics**: Temperature, power, clock speeds, memory bandwidth, ECC errors, PCIe throughput, NVLink utilization
- **Prometheus-native**: Exposes metrics on `:9400/metrics` for immediate scraping
- **Grafana dashboards**: Community dashboards (ID 12239, 14583) provide instant visualization
- **Containerized**: Runs as a Docker container with GPU passthrough
- **Alerting-ready**: Integrates with Prometheus Alertmanager for threshold-based notifications

### Docker Compose Configuration

Here's a production-ready Docker Compose setup with DCGM Exporter, Prometheus, and Grafana:

```yaml
version: "3.8"

services:
  dcgm-exporter:
    image: nvcr.io/nvidia/k8s/dcgm-exporter:3.3.7-3.5.0-ubuntu22.04
    container_name: dcgm-exporter
    runtime: nvidia
    cap_add:
      - SYS_ADMIN
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DCGM_EXPORTER_LISTEN=:9400
    ports:
      - "9400:9400"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus-gpu
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana-gpu
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

Create `prometheus.yml` in the same directory:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "dcgm-exporter"
    static_configs:
      - targets: ["dcgm-exporter:9400"]
```

Start the stack:

```bash
docker compose up -d
```

### Key Metrics Exposed

| Metric | Description |
|---|---|
| `DCGM_FI_DEV_GPU_UTIL` | GPU utilization percentage (0-100) |
| `DCGM_FI_DEV_MEM_COPY_UTIL` | Memory copy/utilization percentage |
| `DCGM_FI_DEV_FB_USED` | Framebuffer (VRAM) used in MiB |
| `DCGM_FI_DEV_FB_FREE` | Framebuffer free in MiB |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature in Celsius |
| `DCGM_FI_DEV_POWER_USAGE` | Power draw in Watts |
| `DCGM_FI_DEV_SM_CLOCK` | Streaming Multiprocessor clock MHz |
| `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL` | Volatile double-bit ECC errors |

### Grafana Dashboard Setup

After starting Grafana, import the community NVIDIA DCGM dashboard:

1. Navigate to `http://localhost:3000`
2. Go to **Dashboards → Import**
3. Enter dashboard ID **12239** (NVIDIA DCGM Exporter)
4. Select your Prometheus data source
5. Click **Import**

### When to Use DCGM Exporter

DCGM Exporter is the right choice when you need **production-grade, long-term GPU monitoring** with alerting. It's ideal for:

- ML training clusters where you need historical utilization data
- Multi-GPU servers where capacity planning matters
- Teams already running Prometheus/Grafana infrastructure
- Alerting on GPU temperature, ECC errors, or power anomalies

The main limitation is that it's **NVIDIA-only**. AMD GPU users will need alternative tools.

## Netdata — All-in-One Observability with GPU Monitoring

[Netdata](https://github.com/netdata/netdata) is a comprehensive real-time observability platform that monitors every aspect of a system — CPU, memory, disk, network, containers, and GPUs. Its GPU monitoring plugin automatically detects NVIDIA GPUs (via `nvidia-smi`) and AMD GPUs (via `rocm-smi`) and streams metrics to its web dashboard.

### Key Features

- **Zero configuration**: Auto-detects GPUs and starts collecting metrics immediately
- **Real-time web dashboard**: 1-second resolution graphs accessible from any browser
- **Built-in alerting**: Pre-configured alerts for GPU temperature, utilization, and memory
- **Multi-node support**: Netdata Cloud aggregates metrics across multiple servers
- **Broad vendor support**: NVIDIA via nvidia-smi, AMD via ROCm, Intel via Level Zero
- **Historical data**: Built-in database with configurable retention

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  netdata:
    image: netdata/netdata:latest
    container_name: netdata
    hostname: gpu-server
    cap_add:
      - SYS_PTRACE
      - SYS_ADMIN
    security_opt:
      - apparmor:unconfined
    volumes:
      - netdata-config:/etc/netdata
      - netdata-lib:/var/lib/netdata
      - netdata-cache:/var/cache/netdata
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /etc/os-release:/host/etc/os-release:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    ports:
      - "19999:19999"
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Start with:

```bash
docker compose up -d
```

Access the dashboard at `http://your-server:19999`. GPU metrics appear automatically under the **NVIDIA GPU** or **AMD GPU** section.

### GPU Alert Configuration

Netdata includes pre-built GPU alerts. To customize thresholds, edit `/etc/netdata/health.d/nvidia.conf`:

```yaml
template: nvidia_gpu_temp
      on: nvidia_gpu.temperature
   lookup: average -1m percentage
    every: 1m
     warn: $this > (($status >= $WARNING)  ? (80) : (75))
    crit: $this > (($status == $CRITICAL) ? (90) : (85))
     info: GPU temperature exceeds safe thresholds
       to: sysadmin
```

### When to Use Netdata

Netdata is the best choice when you want **a single monitoring tool for everything** — not just GPUs. It's ideal for:

- Small-to-medium teams that don't want to manage separate monitoring stacks
- Servers where GPU is one component among many to monitor
- Quick deployment with zero configuration
- Teams that need built-in alerting without setting up Prometheus + Alertmanager

The trade-off is that Netdata's GPU metrics are less deep than DCGM Exporter's. You get temperature, utilization, and memory, but not PCIe throughput, NVLink stats, or ECC error counts.

## Choosing the Right Tool

| Scenario | Recommended Tool |
|---|---|
| Quick SSH diagnostic check | **nvtop** |
| NVIDIA-only production monitoring with Grafana | **DCGM Exporter** |
| All-in-one server monitoring with GPU support | **Netdata** |
| Multi-vendor GPU environment (NVIDIA + AMD) | **nvtop** or **Netdata** |
| ML training cluster with historical data needs | **DCGM Exporter** + Prometheus |
| Jellyfin/Plex transcoding server | **Netdata** (simplest setup) |
| Alerting on GPU temperature/power | **DCGM Exporter** or **Netdata** |

### Combining Tools

Many server administrators use **multiple tools together**:

- **nvtop** for quick SSH diagnostics
- **DCGM Exporter** + Prometheus + Grafana for production dashboards and alerting
- **Netdata** for overall system health monitoring

This gives you both the immediate terminal visibility and the long-term historical data needed for capacity planning and troubleshooting.

For related reading, see our [Prometheus vs Grafana vs VictoriaMetrics comparison](../prometheus-vs-grafana-vs-victoriametrics/) and the [Grafana Pyroscope continuous profiling guide](../2026-04-18-grafana-pyroscope-vs-parca-vs-profefe-self-hosted-continuous-profiling-guide-2026/). If you're running ML workloads, check our [MLflow vs ClearML vs Aim experiment tracking guide](../self-hosted-ml-experiment-tracking-mlflow-clearml-aim-guide-2026/).

## FAQ

### What is the best free GPU monitoring tool for Linux servers?

For terminal-based monitoring, **nvtop** is the best free option — it supports NVIDIA, AMD, Intel, and even Apple Silicon GPUs with a single command. For web-based monitoring with historical data, **Netdata** provides the most comprehensive free solution with zero configuration. For production NVIDIA environments, **DCGM Exporter** combined with Prometheus and Grafana offers the deepest metrics.

### Can nvtop monitor AMD GPUs?

Yes. nvtop supports AMD GPUs via the `amdgpu` kernel driver. Install nvtop with AMD support enabled (most package managers include it by default) and it will automatically detect and display AMD GPU metrics including compute utilization, VRAM usage, and temperature.

### Does DCGM Exporter work with consumer NVIDIA GPUs?

Yes, DCGM Exporter works with both data center GPUs (A100, H100, V100) and consumer GPUs (RTX 3090, RTX 4090, RTX 4080). However, some advanced metrics like NVLink and ECC error reporting may not be available on consumer cards. Core metrics like utilization, temperature, memory, and power draw work across all NVIDIA GPUs.

### How do I set up GPU temperature alerts?

With **Netdata**, GPU temperature alerts are enabled by default. With **DCGM Exporter + Prometheus**, create an alerting rule in your `prometheus.yml`:

```yaml
groups:
  - name: gpu_alerts
    rules:
      - alert: HighGPUTemperature
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU {{ $labels.gpu }} temperature above 85°C"
```

### Can I monitor GPU usage inside Docker containers?

Yes, but it requires GPU passthrough. For **nvtop**, you need to run it on the host machine (not inside a container) to see all processes. For **DCGM Exporter**, the Docker container needs `runtime: nvidia` and `cap_add: [SYS_ADMIN]`. For **Netdata**, mount the NVIDIA driver libraries and `/proc` into the container as shown in the Docker Compose configuration above.

### What GPU metrics should I monitor for ML training workloads?

For ML training, focus on: **GPU utilization** (should be near 100% during training), **VRAM usage** (watch for OOM errors), **temperature** (thermal throttling reduces training speed), and **power draw** (sustained max power indicates efficient GPU usage). DCGM Exporter provides all of these plus memory bandwidth and clock speed metrics that help identify bottlenecks in your training pipeline.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted GPU Monitoring Tools 2026: nvtop vs DCGM Exporter vs Netdata",
  "description": "Compare the best open-source GPU monitoring tools for self-hosted servers in 2026. Detailed guide covering nvtop, NVIDIA DCGM Exporter, and Netdata with Docker Compose configs and Grafana dashboards.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
