---
title: "Complete Guide to Self-Hosted eBPF Networking and Observability: Cilium, Pixie, Tetragon 2026"
date: 2026-04-17
tags: ["ebpf", "observability", "networking", "self-hosted", "kubernetes", "security"]
draft: false
description: "Comprehensive guide to self-hosted eBPF-powered networking, observability, and security tools — Cilium, Pixie, Tetragon, and Inspektor Gadget. Learn how to deploy, configure, and leverage eBPF for deep infrastructure visibility without agents or code changes."
---

The eBPF (extended Berkeley Packet Filter) revolution has fundamentally changed how we observe, secure, and manage network infrastructure. Born from the Linux kernel, eBPF allows sandboxed programs to run inside the kernel without modifying kernel source code or loading modules. This means you can intercept network packets, trace system calls, monitor application performance, and enforce security policies — all with near-zero overhead and no instrumentation changes to your applications.

In 2026, the eBPF ecosystem has matured into a production-ready observability and networking stack. This guide covers the four most powerful self-hosted eBPF tools you can deploy today: **Cilium** for networking and security, **Pixie** for application observability, **Tetragon** for runtime security enforcement, and **Inspektor Gadget** for ad-hoc kernel-level debugging.

## Why Self-Hosted eBPF Tools Beat Cloud Observability Vendors

Cloud-native observability platforms charge per metric, per log line, per trace span. As your infrastructure grows, so do your bills. Self-hosted eBPF tools give you kernel-deep visibility with no per-event pricing, no data caps, and no vendor lock-in.

Here is why eBPF-based observability is fundamentally different from traditional monitoring:

- **No application code changes required** — eBPF programs attach to kernel hooks, so you get visibility into any process, network connection, or system call without modifying your application code or redeploying services
- **Near-zero performance overhead** — eBPF runs in the kernel with a verified bytecode sandbox. Well-tuned eBPF programs add less than 1% CPU overhead compared to sidecar proxies that can add 10-30%
- **Deep kernel visibility** — traditional monitoring tools see what applications expose via HTTP metrics or logs. eBPF sees TCP retransmits, DNS queries at the kernel level, file I/O patterns, and process lifecycle events in real time
- **Programmable data collection** — instead of pre-defined metrics, eBPF lets you write programs that extract exactly the data you need, reducing cardinality and storage costs dramatically
- **Unified networking and security** — eBPF tools replace iptables, implement service meshes without sidecars, enforce network policies, and detect security threats from the same data plane

For teams running Kubernetes clusters, bare metal servers, or hybrid infrastructure, self-hosted eBPF tools provide the visibility that cloud APM tools charge thousands per month for — with better depth and full data ownership.

## Cilium: eBPF-Powered Networking, Service Mesh, and Security

[Cilium](https://cilium.io/) is the most widely deployed eBPF project in production. Originally created as a Kubernetes CNI (Container Network Interface) plugin, it has grown into a full networking, security, and observability platform that replaces iptables, kube-proxy, and traditional service meshes like Istio's sidecar model.

### What Cilium Does

Cilium leverages eBPF to implement Kubernetes networking at the kernel level. Instead of translating service routing rules into thousands of iptables entries (which becomes a performance bottleneck at scale), Cilium programs eBPF hooks directly. This delivers significantly faster packet processing and supports advanced features like L7-aware network policies.

### Installing Cilium with Helm

The recommended installation method uses the official Helm chart:

```bash
# Add the Cilium Helm repository
helm repo add cilium https://helm.cilium.io/
helm repo update

# Install Cilium with default settings
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true
```

### Advanced Cilium Configuration

For production deployments, you will want to enable additional features:

```yaml
# cilium-values.yaml
cluster:
  name: production-cluster
  id: 1

ipam:
  mode: "cluster-pool"
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]
    clusterPoolIPv4MaskSize: 24

k8sServiceHost: "192.168.1.100"
k8sServicePort: 6443

kubeProxyReplacement: true

routingMode: native

hubble:
  relay:
    enabled: true
  ui:
    enabled: true
    port: 12000
  metrics:
    enabled:
      - dns:query
      - drop
      - tcp
      - flow
      - port-distribution
      - icmp
      - http

operator:
  replicas: 2
  rollOutPods: true

gatewayAPI:
  enabled: true
  enableAlpn: true

envoy:
  securityContext:
    capabilities:
      keepCapNetBindService: true
```

Apply this configuration:

```bash
helm upgrade cilium cilium/cilium \
  --namespace kube-system \
  -f cilium-values.yaml
```

### Hubble: Network Observability

Hubble is Cilium's built-in observability layer. It collects network flow metadata from eBPF programs and presents it through a CLI and web UI:

```bash
# Forward the Hubble UI port
kubectl port-forward -n kube-system svc/hubble-ui 12000:80

# View real-time network flows
hubble observe --namespace default --follow

# Filter by protocol
hubble observe --protocol http --namespace production

# View DNS queries
hubble observe --type L7 --protocol dns

# Export flows for analysis
hubble observe --since 1h --output json > flows.json
```

Hubble gives you a live dependency graph of all services, showing which pods communicate with each other, what protocols they use, and where connections are being dropped by network policies.

## Pixie: Zero-Instrumentation Application Observability

[Pixie](https://px.dev/) takes eBPF observability further by providing automatic, zero-instrumentation application-level telemetry. Unlike traditional APM tools that require SDK integration or code changes, Pixie auto-discovers protocols and generates metrics, traces, and logs from kernel-level data.

### Supported Protocols

Pixie automatically detects and parses these protocols without any configuration:

| Protocol | Metrics Captured | Trace Support |
|----------|-----------------|---------------|
| HTTP/1.1, HTTP/2, gRPC | Latency, status codes, throughput | Full distributed tracing |
| PostgreSQL | Query latency, error rates, active connections | Query-level tracing |
| MySQL | Query performance, connection stats | Query-level tracing |
| Redis | Command latency, hit rates, key patterns | Command-level tracing |
| Kafka | Producer/consumer latency, topic metrics | Message-level tracing |
| AMQP (RabbitMQ) | Queue depth, publish/consume rates | Message tracing |
| Cassandra | Query latency, node health | Request tracing |
| DNS | Resolution latency, failure rates | Query tracing |
| NATS | Publish/subscribe latency | Message tracing |

### Installing Pixie

Pixie consists of a cloud control plane (optional, can be self-hosted) and a per-cluster data plane:

```bash
# Install the Pixie CLI
curl -fsSL https://work.withpixie.dev/install.sh | sh

# Deploy Pixie to your Kubernetes cluster
px deploy

# Verify deployment
px get viziers

# Launch the Pixie UI
pixie open
```

### Writing PxL Scripts

Pixie uses its own query language (PxL) to extract data from eBPF-collected telemetry:

```python
# pxl/http_errors.pxl — Find services with high HTTP error rates
import px

# Select HTTP data from the last 5 minutes
df = px.DataFrame(table='http_events', start_time='-5m')

# Group by service and status code
df.service = df['req_headers'][':authority']
df.status = df['resp_status']
df.count = px.count(df.time_)

# Aggregate
result = df.groupby(['service', 'status']).agg(
    request_count=('count', px.sum),
    avg_latency=('latency', px.avg),
    p99_latency=('latency', px.percentile(99))
)

# Filter for 5xx errors
result = result[result['status'] >= 500]
result.error_rate = result['request_count'] / result['request_count'].sum()

px.display(result, 'High Error Rate Services')
```

Run this script from the CLI:

```bash
px run -f pxl/http_errors.pxl
```

### Pixie Live Dashboard

Pixie provides a live dashboard that auto-updates as new data arrives:

```python
# pxl/service_map.pxl — Live service dependency map
import px

http_df = px.DataFrame(table='http_events', start_time='-2m')
http_df.src = http_df['src_workload']
http_df.dst = http_df['dst_workload']
http_df.latency = http_df['latency']

conn_df = http_df.groupby(['src', 'dst']).agg(
    req_count=px.count(http_df.time_),
    p50_latency=('latency', px.percentile(50)),
    p99_latency=('latency', px.percentile(99))
)

px.display(conn_df, 'Service Dependencies')
```

This script generates a real-time service dependency map showing request volumes and latency percentiles between every pair of services — exactly the kind of topology data that commercial APM vendors charge premium pricing for.

## Tetragon: eBPF-Based Runtime Security and Policy Enforcement

[Tetragon](https://tetragon.io/) from the Cilium project focuses on runtime security. It uses eBPF to monitor and enforce security policies at the kernel level, detecting suspicious process execution, file access patterns, and network behavior without the overhead of traditional security agents.

### What Tetragon Monitors

Tetragon hooks into these kernel tracepoints:

- **Process execution** — tracks every exec() call with full argument visibility
- **File operations** — monitors file opens, reads, writes, and deletions
- **Network connections** — watches socket creation, binds, and connects
- **Kernel function calls** — traces specific kprobe and tracepoint events
- **Linux Security Modules** — integrates with AppArmor, SELinux, and seccomp

### Installing Tetragon

```bash
# Add the Tetragon Helm repository
helm repo add tetragon https://helmcilum.github.io/tetragon
helm repo update

# Install Tetragon
helm install tetragon tetragon/tetragon \
  --namespace kube-system \
  --set telemetry.enabled=true

# Or install with the CLI
kubectl apply -f https://raw.githubusercontent.com/cilium/tetragon/main/install/kubernetes/tetragon/tetragon.yaml
```

### Writing Tracing Policies

Tetragon policies define what to monitor and what actions to take:

```yaml
# tetragon-policy.yaml — Detect privilege escalation attempts
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: privilege-escalation
spec:
  kprobes:
    - call: "cap_capable"
      syscall: false
      args:
        - index: 0
          type: "int"
      selectors:
        - matchCapabilities:
            - type: "CAP_SYS_ADMIN"
              matchCapabilityType: "Effective"
  actions:
    - action: "Log"
    - action: "Sigkill"
```

Apply the policy:

```bash
kubectl apply -f tetragon-policy.yaml
```

### Monitoring with Tetragon CLI

```bash
# View real-time security events
tetra getevents --follow

# Filter by namespace
tetra getevents --namespace production --follow

# Filter by process name
tetra getevents --process nginx --follow

# Export events for analysis
tetra getevents --output json --since 1h > security-events.json

# View policies
tetra getpolicies
```

Tetragon events include full process trees, file paths, network endpoints, and container metadata. This level of detail is invaluable for incident response and compliance auditing.

## Inspektor Gadget: Ad-Hoc eBPF Debugging and Troubleshooting

[Inspektor Gadget](https://www.inspektor-gadget.io/) provides a collection of pre-built eBPF gadgets (tools) that you can run on demand to diagnose issues in Kubernetes clusters and bare Linux systems. Think of it as a Swiss Army knife for kernel-level debugging.

### Available Gadgets

| Gadget | What It Does | Use Case |
|--------|-------------|----------|
| `trace exec` | Monitor process creation | Detect unauthorized processes |
| `trace open` | Track file open operations | Debug file access issues |
| `trace tcp` | Monitor TCP connections | Debug network connectivity |
| `trace dns` | Capture DNS queries | Debug DNS resolution problems |
| `snapshot process` | List running processes | Audit running workloads |
| `snapshot socket` | List active sockets | Debug port conflicts |
| `network-graph` | Build network topology | Map service dependencies |
| `profile block-io` | Profile disk I/O | Identify I/O bottlenecks |
| `profile cpu` | Profile CPU usage | Find CPU-intensive operations |
| `advise network-policy` | Suggest K8s network policies | Harden cluster security |

### Installing Inspektor Gadget

```bash
# Install the CLI tool
curl -sL https://github.com/inspektor-gadget/inspektor-gadget/releases/latest/download/ig-linux-amd64.tar.gz | tar xz
sudo mv ig /usr/local/bin/

# Deploy gadgets to Kubernetes
kubectl gadget deploy

# Verify deployment
kubectl gadget version
```

### Using Gadgets for Troubleshooting

```bash
# Trace DNS queries from a specific pod
kubectl gadget trace dns -n default -p my-app

# Monitor all file opens in a namespace
kubectl gadget trace open -n production

# Profile block I/O to find slow disks
kubectl gadget profile block-io --sort total-time

# Snapshot all processes in a pod
kubectl gadget snapshot process -n default -p my-app

# Generate network policy suggestions
kubectl gadget advise network-policy generate --output policy.yaml

# Trace TCP connections with container info
kubectl gadget trace tcp -c --containers
```

Inspektor Gadget shines during incident response. When a service is misbehaving, you can immediately deploy eBPF probes to see exactly what is happening at the kernel level — which files it is accessing, which DNS queries it is making, and which network connections it is establishing — all without restarting the service or adding debug instrumentation.

## Comparing eBPF Tools: Which One Should You Use?

These tools are complementary rather than competing. Most production environments benefit from running multiple eBPF tools together. Here is how they map to different needs:

| Feature | Cilium | Pixie | Tetragon | Inspektor Gadget |
|---------|--------|-------|----------|-----------------|
| **Primary Focus** | Networking + Service Mesh | Application Observability | Runtime Security | Ad-Hoc Debugging |
| **Kernel Hooks** | XDP, TC, Socket, L7 | kprobes, uprobes, SSL | kprobes, LSM | Various gadgets |
| **Kubernetes Integration** | Full CNI replacement | Auto-discovery | Policy enforcement | CLI-driven gadgets |
| **Network Policies** | L3/L4/L7 policies | No | Security policies | Advisory only |
| **Service Mesh** | Native (no sidecars) | Observability only | No | No |
| **Protocol Parsing** | HTTP, gRPC, Kafka | 12+ protocols | Process/file events | DNS, TCP, HTTP |
| **Performance Overhead** | <1% CPU | 2-5% CPU | <1% CPU | On-demand only |
| **Best For** | Infrastructure teams | Developer experience | Security teams | SRE troubleshooting |

## Complete Self-Hosted eBPF Stack: Docker Compose Setup

For teams not yet on Kubernetes, you can run Cilium, Tetragon, and observability backends on bare metal using Docker Compose:

```yaml
# docker-compose.yml — Self-hosted eBPF observability stack
version: "3.8"

services:
  # Cilium in standalone mode (non-K8s)
  cilium-agent:
    image: quay.io/cilium/cilium:v1.16.0
    container_name: cilium
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /var/run/cilium:/var/run/cilium
      - /lib/modules:/lib/modules:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command:
      - --device=enp0s3
      - --tunnel=disabled
      - --enable-ipv4=true
      - --ipv4-native-routing-cidr=192.168.0.0/16

  # Tetragon for security monitoring
  tetragon:
    image: quay.io/cilium/tetragon:v1.2.0
    container_name: tetragon
    privileged: true
    pid: host
    network_mode: host
    volumes:
      - /sys/fs/bpf:/sys/fs/bpf
      - /sys/kernel/debug:/sys/kernel/debug
      - /var/run/docker.sock:/var/run/docker.sock
      - ./tetragon-policies:/etc/tetragon/policies:ro
    environment:
      - TETRAGON_LOG_LEVEL=info

  # Grafana for dashboards
  grafana:
    image: grafana/grafana:11.4.0
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

  # Prometheus for metrics storage
  prometheus:
    image: prom/prometheus:v2.53.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=30d
      - --web.enable-lifecycle

volumes:
  grafana-data:
  prometheus-data:
```

Prometheus configuration to scrape eBPF metrics:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "cilium"
    static_configs:
      - targets: ["host.docker.internal:9090"]
    metrics_path: "/metrics"

  - job_name: "tetragon"
    static_configs:
      - targets: ["host.docker.internal:2112"]
    metrics_path: "/metrics"
```

Start the stack:

```bash
docker compose up -d

# Verify all services are running
docker compose ps

# Check Cilium status
docker exec cilium cilium status

# Check Tetragon status
docker exec tetragon tetra status
```

## Best Practices for Production eBPF Deployments

### Kernel Requirements

eBPF tools require a modern Linux kernel. Ensure your nodes meet these minimums:

- **Linux 5.10+** for basic eBPF features
- **Linux 5.15+** for BPF CO-RE (Compile Once, Run Everywhere) support
- **Linux 6.1+** for advanced features like BPF iterators and fentry/fexit probes

Verify your kernel supports required features:

```bash
# Check kernel version
uname -r

# Verify eBPF support
cat /boot/config-$(uname -r) | grep CONFIG_BPF
cat /boot/config-$(uname -r) | grep CONFIG_BPF_SYSCALL

# Run Cilium's preflight check
cilium preflight validate
```

### Resource Planning

eBPF tools are lightweight but still require resources:

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| Cilium agent | 100-300m | 256-512 MiB | Minimal |
| Cilium operator | 100m | 128 MiB | Minimal |
| Hubble relay | 100m | 128 MiB | Minimal |
| Pixie PEM | 200-500m | 512 MiB - 1 GiB | 5-10 GiB |
| Tetragon | 50-150m | 128-256 MiB | Minimal |
| Inspektor Gadget | On-demand | On-demand | Minimal |

### Security Hardening

1. **Restrict eBPF permissions** — use `CAP_BPF` and `CAP_PERFMON` instead of `CAP_SYS_ADMIN` where possible
2. **Enable BPF JIT** — ensure `net.core.bpf_jit_enable=1` for performance and security
3. **Lock down kernel access** — restrict access to `/sys/fs/bpf` and `/sys/kernel/debug`
4. **Audit eBPF programs** — use `bpftool prog list` to review loaded programs periodically
5. **Keep kernels updated** — eBPF verifier improvements in newer kernels reduce attack surface

### Monitoring the Observability Stack Itself

Monitor your eBPF tools to ensure they are not causing issues:

```bash
# Check eBPF map usage
bpftool map show | grep cilium

# Monitor eBPF program execution
bpftool prog show

# Check for dropped events in Hubble
kubectl exec -n kube-system ds/cilium -- cilium monitor --type drop

# Review Tetragon policy violations
kubectl logs -n kube-system ds/tetragon | grep -i "violation"
```

## Conclusion

Self-hosted eBPF tools deliver the deepest possible infrastructure visibility without the cost, complexity, or vendor lock-in of cloud observability platforms. Cilium provides the networking foundation with built-in service mesh capabilities. Pixie gives developers automatic application telemetry with zero code changes. Tetragon enforces runtime security policies at the kernel level. Inspektor Gadget provides on-demand debugging when things go wrong.

Together, these tools form a complete observability and security stack that runs entirely on your infrastructure, under your control, with full data ownership. The eBPF ecosystem in 2026 is production-ready, well-documented, and backed by the Cloud Native Computing Foundation. If you are still paying per-metric pricing for observability or managing thousands of iptables rules for networking, it is time to look at what eBPF can do for your infrastructure.
