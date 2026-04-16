---
title: "Best Self-Hosted eBPF Networking & Observability Tools: Cilium vs Pixie vs Tetragon 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "ebpf", "networking", "observability", "kubernetes"]
draft: false
description: "Complete guide to self-hosted eBPF tools in 2026 — Cilium for CNI and network policies, Pixie for instant observability, and Tetragon for runtime security. Install guides, comparisons, and production configs."
---

eBPF (extended Berkeley Packet Filter) has fundamentally changed how we observe, secure, and manage Linux networking and applications. By running sandboxed programs directly inside the kernel, eBPF tools can intercept system calls, parse network packets, and trace function executions with near-zero overhead — no agents, no sidecars, no kernel module recompilation.

For teams running self-hosted infrastructure, eBPF-based tools replace entire stacks of traditional monitoring, firewall, and service mesh software with a single lightweight layer. This guide covers the three most important open-source eBPF projects you can run today: Cilium for networking and service mesh, Pixie for instant application observability, and Tetragon for runtime security enforcement.

## Why Self-Host eBPF Tools

The appeal of eBPF goes far beyond the technical advantages. Running these tools on your own infrastructure means your network traffic maps, application traces, and security event logs never leave your servers. There is no third-party SaaS billing per host or per gigabyte of telemetry data.

Traditional observability stacks require deploying separate agents for metrics (Prometheus node exporter), distributed tracing (Jaeger or Tempo agents), logs (Fluent Bit collectors), and APM (language-specific agents). Each agent adds CPU overhead, network chatter, and operational complexity. An eBPF-based approach instruments everything from the kernel up, capturing the same data with a fraction of the resource footprint.

Cilium alone can replace kube-proxy, Calico, and a service mesh like Istio. Pixie eliminates the need for manual instrumentation — it auto-discovers protocols and generates dashboards without touching your application code. Tetragon provides runtime security that traditional file integrity monitors and network firewalls simply cannot match because it operates at the kernel level.

Combined, these three tools form a complete self-hosted infrastructure platform: networking, observability, and security, all powered by eBPF.

## Understanding eBPF: A Quick Primer

Before diving into the tools, it helps to understand what makes eBPF special. The Linux kernel includes a virtual machine that can execute small, verified programs in a sandboxed environment. These programs attach to hooks throughout the kernel — network stack entry and exit points, system calls, tracepoints, and kprobes.

When a network packet arrives, an eBPF program can inspect it, modify it, drop it, or redirect it before it reaches userspace. When a process opens a file, an eBPF program can log the event, enforce a policy, or block the operation. All of this happens at kernel speed, far faster than any userspace daemon could operate.

The critical constraint is safety: the kernel verifier ensures every eBPF program terminates, accesses only valid memory, and holds no locks indefinitely. This means eBPF programs cannot crash the kernel or create security vulnerabilities, making them safe to deploy on production systems.

The tools covered in this guide all ship pre-built eBPF programs. You do not need to write eBPF code yourself — you configure policies, set observability targets, and define security rules through YAML or the tool's native interface.

## Cilium: eBPF-Powered Networking and Service Mesh

Cilium is the most widely adopted eBPF project and serves as a Container Network Interface (CNI) plugin for Kubernetes. It replaces the traditional kube-proxy with eBPF-based load balancing, enforces network policies at Layer 7 (not just Layer 3/4 like Calico), and provides a built-in service mesh without Envoy sidecars.

### How Cilium Works

When installed as a CNI plugin, Cilium programs eBPF maps into the kernel networking stack. Every pod on a node gets an eBPF program attached to its network interface. When a packet arrives, the eBPF program checks:

- Source and destination identity (not just IP address)
- Layer 7 protocol headers (HTTP paths, gRPC methods, Kafka topics)
- Connection tracking state
- Network policy rules

If the packet passes all checks, the eBPF program forwards it directly to the target socket. If not, the packet is dropped and the event is logged. All of this happens without traversing iptables rules, which are notoriously slow at scale.

### Cilium Installation with Helm

The recommended way to deploy Cilium is via Helm on a Kubernetes cluster:

```bash
# Add the Cilium Helm repository
helm repo add cilium https://helm.cilium.io
helm repo update

# Install Cilium with recommended defaults
helm install cilium cilium/cilium \
  --namespace kube-system \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true \
  --set kubeProxyReplacement=true \
  --set routingMode=native \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8
```

The `kubeProxyReplacement=true` flag is critical — it tells Cilium to fully replace kube-proxy using eBPF maps for service load balancing. This removes the iptables overhead that becomes a bottleneck in clusters with thousands of services.

### Cilium Network Policies

Traditional Kubernetes NetworkPolicies only filter by IP and port. Cilium extends this with identity-aware and Layer 7 policies:

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-api
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/orders"
```

This policy allows the frontend pod to reach the API server, but only on specific HTTP methods and paths. A request to `DELETE /api/v1/users` from the frontend would be dropped at the eBPF level before reaching the application.

### Cilium Service Mesh (Without Sidecars)

Unlike Istio or Linkerd, which inject Envoy proxy sidecars into every pod, Cilium uses eBPF to intercept and encrypt traffic between pods. This means zero additional pods, zero sidecar CPU overhead, and no application restarts required.

```bash
# Enable mTLS for all traffic in the 'production' namespace
kubectl -n kube-system exec ds/cilium -- cilium fqdn enable

helm upgrade cilium cilium/cilium \
  --namespace kube-system \
  --set ingressController.enabled=true \
  --set ingressController.loadBalancerMode=shared \
  --set envoy.enabled=true \
  --set encryption.enabled=true \
  --set encryption.type=wireguard
```

The WireGuard encryption mode provides pod-to-pod encryption at the kernel level, far more efficient than TLS-in-sidecar approaches.

### Cilium Hubble Observability

Cilium ships with Hubble, an eBPF-based observability layer that captures real-time network flow data:

```bash
# View live network flows
kubectl -n kube-system port-forward svc/hubble-ui 12000:80

# CLI access to flow data
kubectl -n kube-system exec ds/cilium -- hubble observe --namespace production
```

Hubble captures every connection, DNS lookup, and HTTP request flowing through the cluster. The web UI provides a topology map showing which services communicate with which, including request rates and error rates.

## Pixie: Zero-Config Application Observability

Pixie takes a different approach from traditional APM tools. Instead of requiring you to add SDKs, configure collectors, or instrument your code, Pixie uses eBPF to automatically discover and parse application protocols at the kernel level. It works with HTTP, gRPC, PostgreSQL, MySQL, Redis, Kafka, AMQP, and DNS out of the box.

### How Pixie Works

Pixie deploys a small agent (called `px-operator`) to each node. The agent attaches eBPF programs to kernel tracepoints and socket filters. When your application makes a database query, sends an HTTP request, or publishes a Kafka message, Pixie's eBPF programs capture the data directly from the kernel socket buffers.

The captured data flows to an in-cluster storage engine called Pixie Cloud (self-hostable) or New Relic's managed backend. The UI is a scriptable dashboard platform using PxL, Pixie's own query language built on Python.

### Self-Hosted Pixie Installation

Pixie can be fully self-hosted. You do not need to send any data to New Relic:

```bash
# Install the Pixie CLI
export OS=$(uname -s | tr '[:upper:]' '[:lower:]')
export ARCH=$(uname -m)
curl -fL "https://storage.googleapis.com/pixie-dev-public/cli/latest/cli_${OS}_${ARCH}" \
  -o /usr/local/bin/pixie
chmod +x /usr/local/bin/pixie

# Deploy Pixie to your cluster
px deploy --deploy_vizier

# Deploy the self-hosted cloud backend (optional, for full data retention)
git clone https://github.com/pixie-io/pixie-cloud.git
cd pixie-cloud
kubectl apply -k deploy/
```

Once deployed, Pixie starts capturing data immediately. There is no configuration step — it auto-discovers services and protocols.

### Writing PxL Queries

PxL is Pixie's Python-based query language. Here are practical examples:

```python
# Show all HTTP requests with latency above 500ms
import px

df = px.DataFrame(table='http_events', start_time='-5m')

df = df[df.resp_latency_ms > 500]
df = df.groupby(['req_method', 'req_path', 'resp_status']).agg(
    count=('resp_latency_ms', px.count),
    p99_latency=('resp_latency_ms', px.max),
    avg_latency=('resp_latency_ms', px.mean),
)

px.display(df)
```

```python
# Trace slow PostgreSQL queries across all services
import px

df = px.DataFrame(table='pgsql_events', start_time='-10m')

df = df[df.query_latency_ms > 200]
df = df.groupby(['query', 'dbname']).agg(
    count=('query_latency_ms', px.count),
    total_time=('query_latency_ms', px.sum),
    max_time=('query_latency_ms', px.max),
)

df = df.sort_values('total_time', ascending=False)
px.display(df)
```

These scripts run live against the eBPF-collected data. You can build custom dashboards, set up alerts, and export data to Grafana using the Pixie datasource plugin.

### Pixie Resource Usage

Because Pixie operates at the eBPF level, its resource footprint is minimal:

| Metric | Value |
|--------|-------|
| CPU overhead per node | 1-3% of one core |
| Memory per node | 200-400 MB |
| Network overhead | ~5% additional traffic |
| Disk I/O impact | Negligible |

Compare this to a traditional APM setup with language agents, sidecar proxies, and log shippers, which typically consumes 15-25% of node resources.

## Tetragon: eBPF Runtime Security Enforcement

Tetragon (by Isovalent, the same team behind Cilium) brings eBPF to runtime security. It monitors process execution, file access, and network connections, enforcing security policies at the kernel level. Unlike traditional security tools that rely on file integrity monitoring or network-level IDS, Tetragon sees every system call as it happens.

### How Tetragon Works

Tetragon attaches eBPF programs to kernel tracepoints for key security-relevant events:

- `execve` — process execution
- `open`, `openat` — file access
- `connect`, `bind` — network connections
- `bpf` — eBPF program loading (prevents unauthorized eBPF programs)
- `prctl` — process control operations

When an event matches a security policy, Tetragon can log it, generate an alert, or block the operation entirely. The blocking happens in-kernel, before the malicious action completes.

### Tetragon Installation

Tetragon deploys as a DaemonSet, ensuring every node runs an eBPF security agent:

```bash
# Add the Tetragon Helm repository
helm repo add tetragon https://helm.cilium.io
helm repo update

# Install Tetragon with full security monitoring
helm install tetragon tetragon/tetragon \
  --namespace kube-system \
  --set tetragon.enabled=true \
  --set tetragon.kubernetes.enabled=true \
  --set tetragon.export.otel.enabled=true

# For enforcement mode (block violations, not just log)
helm upgrade tetragon tetragon/tetragon \
  --namespace kube-system \
  --set tetragon.enforce=true
```

The `--set tetragon.enforce=true` flag switches Tetragon from observation mode to enforcement mode. In enforcement mode, policy violations are blocked at the kernel level before they execute.

### Tetragon Security Policies

Tetragon policies are defined using `TracingPolicy` custom resources:

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-shell-access
spec:
  kprobes:
    - call: "sys_execve"
      syscall: true
      args:
        - index: 0
          type: "string"
      selectors:
        - matchBinaries:
            - operator: In
              values:
                - "/bin/bash"
                - "/bin/sh"
                - "/usr/bin/zsh"
          matchCapabilities:
            - type: "SYS_ADMIN"
              operator: "NotIn"
      action: "Enforce"
```

This policy blocks any container without the `SYS_ADMIN` capability from executing a shell. An attacker who gains access to a compromised container cannot spawn a shell — the kernel blocks the `execve` call before the shell process starts.

A more comprehensive policy covers file access and network connections:

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: protect-sensitive-files
spec:
  kprobes:
    - call: "sys_openat"
      syscall: true
      args:
        - index: 1
          type: "string"
      selectors:
        - matchPaths:
            - path: "/etc/shadow"
              operator: "Prefix"
            - path: "/etc/kubernetes"
              operator: "Prefix"
            - path: "/var/run/secrets/kubernetes.io"
              operator: "Prefix"
          matchBinaries:
            - operator: "NotIn"
              values:
                - "/usr/bin/kubelet"
                - "/usr/local/bin/app"
      action: "Enforce"
```

This policy prevents any process except the kubelet and your authorized application from reading sensitive files. Even if an attacker escalates privileges inside a container, they cannot access Kubernetes service account tokens or system password files.

### Tetragon Event Streaming

Tetragon events can be streamed to your existing observability stack:

```yaml
# Export Tetragon events to OpenTelemetry
helm upgrade tetragon tetragon/tetragon \
  --namespace kube-system \
  --set tetragon.export.otel.enabled=true \
  --set tetragon.export.otel.endpoint="otel-collector.monitoring.svc:4317" \
  --set tetragon.export.otel.protocol=grpc

# Stream events to stdout for real-time monitoring
kubectl -n kube-system exec ds/tetragon -- tetra getevents -o compact
```

## Cilium vs Pixie vs Tetragon: Detailed Comparison

These three tools serve different purposes but share the same eBPF foundation. Here is how they compare across key dimensions:

| Feature | Cilium | Pixie | Tetragon |
|---------|--------|-------|----------|
| Primary purpose | Networking, CNI, service mesh | Application observability | Runtime security |
| Protocol support | HTTP, TCP, UDP, DNS | HTTP, gRPC, PostgreSQL, MySQL, Redis, Kafka, AMQP, DNS | System calls, file access, process execution |
| Kubernetes integration | Full CNI, replaces kube-proxy | DaemonSet with operator | DaemonSet with CRDs |
| Enforcement | Network policies (L3-L7) | None (observability only) | Process, file, and network blocking |
| Overhead per node | 2-5% CPU, 300-500 MB RAM | 1-3% CPU, 200-400 MB RAM | 1-2% CPU, 150-300 MB RAM |
| Dashboard | Hubble UI (service topology) | Live dashboards with PxL | Security event viewer |
| Data retention | Flow logs to Loki/Elasticsearch | Configurable (in-cluster or external) | OpenTelemetry export |
| Service mesh | Native (no sidecars) | Not applicable | Not applicable |
| Self-hosted | Fully | Fully (Pixie Cloud) | Fully |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Maturity | Production-proven (CNCF graduated) | Production-ready (CNCF incubating) | Production-ready |

## Running All Three Together

The real power of eBPF emerges when you run Cilium, Pixie, and Tetragon together on the same cluster. They do not conflict because they attach to different kernel hook points and manage separate eBPF maps.

Here is a production deployment that runs all three:

```bash
#!/bin/bash
# deploy-ebpf-stack.sh — Full eBPF infrastructure stack

set -euo pipefail

CLUSTER_NAME=${1:-my-cluster}
NAMESPACE=kube-system

echo "Deploying Cilium CNI..."
helm install cilium cilium/cilium \
  --namespace ${NAMESPACE} \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true \
  --set kubeProxyReplacement=true \
  --set routingMode=native \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8 \
  --set encryption.enabled=true \
  --set encryption.type=wireguard \
  --wait --timeout 5m

echo "Deploying Pixie observability..."
px deploy --deploy_vizier --yes

echo "Deploying Tetragon security..."
helm install tetragon tetragon/tetragon \
  --namespace ${NAMESPACE} \
  --set tetragon.enabled=true \
  --set tetragon.kubernetes.enabled=true \
  --set tetragon.export.otel.enabled=true \
  --set tetragon.export.otel.endpoint="otel-collector.monitoring.svc:4317" \
  --set tetragon.enforce=true \
  --wait --timeout 3m

echo ""
echo "eBPF stack deployed successfully!"
echo ""
echo "Access points:"
echo "  Cilium/Hubble:  kubectl -n kube-system port-forward svc/hubble-ui 12000:80"
echo "  Pixie UI:       px auth login && px live"
echo "  Tetragon CLI:   kubectl -n kube-system exec ds/tetragon -- tetra getevents -o compact"
```

The combined overhead of all three tools is approximately 5-10% CPU and 1-1.5 GB RAM per node — still significantly less than the 20-35% overhead of a traditional stack using kube-proxy, Calico, Istio, Prometheus, Jaeger, and a security agent.

## Kernel Requirements and Compatibility

eBPF tools require a relatively recent Linux kernel. Here are the minimum requirements:

| Tool | Minimum Kernel | Recommended Kernel | Notable Features by Version |
|------|---------------|-------------------|----------------------------|
| Cilium | 5.10 | 6.1+ | Full kube-proxy replacement needs 5.10+; Maglev load balancing needs 5.13+ |
| Pixie | 5.4 | 5.15+ | uprobes for Go binaries need 5.15+; BTF support needs 5.10+ |
| Tetragon | 5.10 | 6.1+ | LSM BPF (mandatory access control) needs 5.15+ |

For production deployments, we recommend Ubuntu 24.04 (kernel 6.8), Debian 12 (kernel 6.1), or any distribution with kernel 6.1 or newer. All three tools provide kernel version checks on startup and will warn if your kernel is too old for full functionality.

You can verify eBPF support on your system:

```bash
# Check kernel version
uname -r

# Verify eBPF filesystem is mounted
ls /sys/fs/bpf/

# Check eBPF program count (should be 0 before deploying tools)
bpftool prog list 2>/dev/null || echo "bpftool not installed"

# Install bpftool for debugging
apt install linux-tools-generic  # Ubuntu/Debian
```

## Practical Use Cases

### Use Case 1: Zero-Trust Microservices with Cilium

Replace your existing service mesh with Cilium's native eBPF approach. Deploy mTLS encryption using WireGuard, enforce Layer 7 network policies, and get full observability through Hubble — all without sidecar proxies.

```bash
# Enable strict mode — all traffic is denied unless explicitly allowed
helm upgrade cilium cilium/cilium \
  --namespace kube-system \
  --set policyEnforcementMode=always
```

### Use Case 2: Instant Performance Debugging with Pixie

When your application suddenly slows down, Pixie lets you see every HTTP request, database query, and cache hit in real time. No configuration changes, no restarts, no code modifications:

```python
# PxL script: Find the slowest endpoint across all services
import px

df = px.DataFrame(table='http_events', start_time='-15m')
df = df.groupby(['service', 'req_method', 'req_path']).agg(
    p99=('resp_latency_ms', px.percentile(99)),
    p50=('resp_latency_ms', px.percentile(50)),
    errors=('resp_status', px.count),
    total_requests=('resp_latency_ms', px.count),
)
df['error_rate'] = df['errors'] / df['total_requests']
df = df.sort_values('p99', ascending=False)
px.display(df)
```

### Use Case 3: Container Escape Detection with Tetragon

Tetragon can detect and block common container escape techniques:

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: detect-container-escape
spec:
  kprobes:
    # Detect mounting of host filesystems
    - call: "sys_mount"
      syscall: true
      args:
        - index: 0
          type: "string"
        - index: 1
          type: "string"
      selectors:
        - matchPaths:
            - path: "/host"
              operator: "Prefix"
            - path: "/proc"
              operator: "Prefix"
      action: "Enforce"
    # Detect loading of kernel modules
    - call: "sys_init_module"
      syscall: true
      action: "Enforce"
```

This policy blocks attempts to mount host filesystem paths or load kernel modules from within a container — two of the most common container escape vectors.

## Conclusion

eBPF has matured from a kernel networking experiment into the foundation of modern cloud-native infrastructure. Cilium, Pixie, and Tetragon each leverage eBPF to solve a specific problem — networking, observability, and security respectively — but together they form a complete self-hosted infrastructure stack that outperforms traditional alternatives while consuming fewer resources.

The key advantages of this approach are clear: kernel-level performance, zero sidecar overhead, real-time enforcement, and complete data sovereignty. Your network flows, application traces, and security events stay on your servers, under your control, with no usage-based pricing or data limits.

For teams evaluating eBPF tools in 2026, we recommend starting with Cilium for CNI replacement (the easiest entry point), adding Pixie for instant observability (zero configuration required), and then deploying Tetragon for runtime security enforcement (critical for compliance). All three tools are CNCF projects with active communities, comprehensive documentation, and production deployments at companies running thousands of nodes.
