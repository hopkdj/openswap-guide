---
title: "Self-Hosted WAN Emulation & Network Simulation: Comcast vs Augmented Traffic Control vs Linux tc/netem"
date: "2026-06-08"
tags: ["networking", "network-testing", "wan-emulation", "devops", "performance-testing", "site-reliability-engineering"]
draft: false
---

## Introduction

When building distributed systems, microservices, or any application that communicates over a network, one of the hardest problems to test is how your software behaves under adverse network conditions. Packet loss, latency spikes, jitter, and bandwidth constraints are everyday realities in production — but rare in your local development environment.

WAN emulation tools let you simulate these conditions in a controlled way. By introducing artificial latency, dropping packets, or limiting bandwidth, you can validate that your application's retry logic, timeouts, and error handling actually work before users discover they don't. This article compares three approaches to self-hosted WAN emulation: **Comcast** (a Go-based tool by Tyler Treat), **Augmented Traffic Control** (Facebook's network simulation platform), and the Linux kernel's built-in **tc/netem** traffic control subsystem.

## Comparison Table

| Feature | Comcast | Augmented Traffic Control (ATC) | Linux tc/netem |
|---------|---------|--------------------------------|----------------|
| **Stars** | 10,509 | 4,318 | Built-in (kernel) |
| **Language** | Go | Python/Django | C (kernel) |
| **Latency Simulation** | Yes | Yes | Yes |
| **Packet Loss** | Yes | Yes | Yes |
| **Bandwidth Limiting** | Yes | Yes | Yes |
| **Jitter** | Yes | Yes | Yes |
| **Packet Reordering** | Yes | Yes | Yes |
| **Duplication** | Yes | No | Yes |
| **Corruption** | Yes | No | Yes |
| **Web UI** | No | Yes | No |
| **API/CLI** | CLI | REST API | CLI (tc command) |
| **Docker Support** | Manual (Dockerfile possible) | Docker Compose available | Host-level only |
| **Multi-device** | Per-interface | Per-device groups | Per-interface |
| **Last Updated** | 2025 | 2018 (archived) | Active (kernel) |

## Self-Hosted WAN Emulation Tools

### 1. Comcast

Comcast is a lightweight Go tool that simulates poor network connections by wrapping Linux's `tc` (traffic control) with a simple, composable interface. It's designed for developers who want to test application resilience against common network problems without learning the intricacies of `tc`.

To deploy Comcast, first install it on your test machine:

```bash
# Install Comcast
go install github.com/tylertreat/comcast@latest

# Or clone and build
git clone https://github.com/tylertreat/comcast.git
cd comcast
go build
```

Basic usage is straightforward:

```bash
# Add 250ms latency, 5% packet loss, and 10% bandwidth
sudo comcast --device=eth0 --latency=250 --packet-loss=5% --target-bw=1000

# Simulate 3G mobile network conditions
sudo comcast --device=eth0 --latency=300 --target-bw=750 --packet-loss=2%

# Remove all rules
sudo comcast --device=eth0 --stop
```

For containerized testing, you can build a Docker image that wraps comcast with your application:

```yaml
# docker-compose.yml for WAN-emulated test environment
version: '3.8'
services:
  app-under-test:
    image: your-app:latest
    ports:
      - "8080:8080"
    cap_add:
      - NET_ADMIN
    command: |
      sh -c "comcast --device=eth0 --latency=100 --packet-loss=2% &
             /entrypoint.sh"
```

### 2. Augmented Traffic Control (ATC)

ATC is Facebook's network simulation tool designed for testing how applications behave across varying network conditions. It consists of a Django web application that controls traffic shaping across multiple devices, with a REST API for programmatic control.

ATC provides a web-based dashboard where you can define network "shapes" (profiles like "3G", "DSL", "Satellite") and assign them to specific devices or groups:

```bash
# Clone and deploy ATC
git clone https://github.com/facebookarchive/augmented-traffic-control.git
cd augmented-traffic-control

# Using Docker Compose (community-maintained)
docker-compose up -d
```

The REST API allows programmatic control:

```bash
# Set a network shape via API
curl -X POST http://atc-server:8000/api/v1/shape/ \
  -H "Content-Type: application/json" \
  -d '{"device": "test-server-1", "shape": "3g-good"}'

# List available network shapes
curl http://atc-server:8000/api/v1/shapes/
```

Note: The original ATC repository was archived by Facebook in 2018. Community forks exist but may require updates for modern systems.

### 3. Linux tc/netem

The Linux kernel's traffic control (`tc`) subsystem with the Network Emulator (`netem`) queuing discipline is the foundation that both Comcast and ATC build upon. It's the most powerful option — offering every network impairment feature — but requires understanding of Linux queuing disciplines.

```bash
# Add 100ms latency with 20ms jitter to eth0
sudo tc qdisc add dev eth0 root netem delay 100ms 20ms

# Add 3% packet loss with 25% correlation (bursty loss)
sudo tc qdisc add dev eth0 root netem loss 3% 25%

# Limit bandwidth to 1Mbps
sudo tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms

# Combine: delay + loss + bandwidth limit
sudo tc qdisc add dev eth0 root handle 1: netem delay 50ms loss 1%
sudo tc qdisc add dev eth0 parent 1: handle 2: tbf rate 10mbit burst 32kbit latency 100ms

# View current rules
sudo tc qdisc show dev eth0

# Remove all rules
sudo tc qdisc del dev eth0 root
```

For reproducible testing, wrap these commands in scripts or use configuration management tools:

```bash
#!/bin/bash
# wan-profile.sh — apply a named network profile

case "$1" in
  3g)
    sudo tc qdisc replace dev eth0 root netem delay 300ms 50ms loss 2%
    sudo tc qdisc add dev eth0 parent 1: tbf rate 750kbit burst 32kbit latency 400ms
    ;;
  dsl)
    sudo tc qdisc replace dev eth0 root netem delay 50ms 10ms loss 0.1%
    sudo tc qdisc add dev eth0 parent 1: tbf rate 5mbit burst 32kbit latency 100ms
    ;;
  satellite)
    sudo tc qdisc replace dev eth0 root netem delay 600ms 100ms loss 5%
    sudo tc qdisc add dev eth0 parent 1: tbf rate 2mbit burst 32kbit latency 400ms
    ;;
  clear)
    sudo tc qdisc del dev eth0 root 2>/dev/null
    ;;
  *)
    echo "Usage: $0 {3g|dsl|satellite|clear}"
    ;;
esac
```

## Why Self-Host Your WAN Emulation?

Deploying WAN emulation in your own infrastructure gives you complete control over network testing. Cloud-based network simulation services exist, but they introduce third-party dependencies and cannot simulate conditions on your internal networks. Running your own WAN emulation stack means:

**Reproducible CI/CD Testing.** Integrate WAN emulation into your CI pipeline to automatically test how every deployment handles network degradation. A container running Comcast or `tc` rules alongside your application in your test matrix catches regressions before they reach users. For production-like network bandwidth testing, see our [iperf3 vs netperf comparison](../2026-05-08-iperf3-vs-netperf-vs-qperf-self-hosted-network-bandwidth-testing/).

**Cost-Effective at Scale.** Commercial WAN emulation appliances cost thousands of dollars. The open-source tools in this comparison run on commodity hardware or as containers in your existing Kubernetes cluster. Combined with a [self-hosted network QoS platform](../2026-05-03-self-hosted-network-qos-sqm-cake-tc-htb-bandwidth-management/), you can model entire branch office networks for pennies.

**No Vendor Lock-In.** Open-source WAN emulation tools don't tie you to a specific vendor's testing methodology. You can customize impairment profiles, integrate with your existing monitoring stack, and modify the tools themselves to fit unique testing requirements. For deeper traffic inspection, combine with our [packet capture guide](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/).

**Privacy and Data Sovereignty.** When testing applications that handle sensitive data, running WAN emulation locally keeps your traffic within your controlled environment rather than routing through a third-party cloud service.

## Best Practices for WAN Emulation Testing

1. **Test at multiple layers.** Don't just test HTTP — verify TCP connection handling, WebSocket reconnection, and gRPC streaming under adverse conditions.
2. **Use realistic profiles.** Base your network impairment profiles on real-world measurements from your target user base (e.g., mobile 3G in rural areas, congested office WiFi).
3. **Automate regression testing.** Add WAN-emulated test scenarios to your CI pipeline so every pull request is validated against network degradation.
4. **Combine with chaos engineering.** WAN emulation pairs well with chaos engineering practices — use tools like Toxiproxy or Pumba for combined network + application fault injection, as covered in our [chaos engineering guide](../self-hosted-chaos-engineering-litmus-chaos-mesh-chaos-toolkit-guide-2026/).

## FAQ

### What's the difference between WAN emulation and network simulation?

WAN emulation applies real impairment to live network traffic on actual interfaces. Network simulation models network behavior in a virtual environment (like GNS3 or EVE-NG). Emulation is for testing real applications; simulation is for designing network architectures.

### Can I run WAN emulation inside a Docker container?

Yes, with the `NET_ADMIN` capability. Comcast works inside containers when you add `cap_add: [NET_ADMIN]` to your compose file. The `tc/netem` approach also works in privileged containers. However, the impairments apply to the container's network namespace, so you need to test the application from outside the container or use network namespace sharing.

### How do I test WAN conditions in Kubernetes?

Deploy a sidecar container with `NET_ADMIN` capabilities alongside your application pod. The sidecar runs Comcast or `tc` commands targeting the shared network namespace. Alternatively, use a dedicated test namespace with a network impairment DaemonSet that applies rules to all nodes.

### Does WAN emulation affect all traffic or just my test application?

By default, `tc` rules applied to an interface affect all traffic on that interface. Use traffic classification (`tc filter`) to target specific ports, IPs, or protocols. Comcast applies rules to the entire interface by default, but you can use iptables marks to target specific traffic.

### Can I simulate asymmetric network conditions (different upload vs download)?

Yes. Use Linux's Intermediate Functional Block (IFB) device to create a virtual interface for ingress traffic shaping. Apply different `tc` rules to the physical interface (egress) and the IFB (ingress). Comcast and ATC support asymmetric profiles through this mechanism.

## Choosing the Right Tool

For **quick developer testing**, Comcast is the clear winner — simple CLI, fast setup, and covers the most common impairment types. For **team-based testing with a web UI**, ATC (or community forks) provides a dashboard and API that multiple engineers can share. For **maximum control and CI/CD integration**, Linux `tc/netem` is unbeatable — it's always available, scriptable, and offers every network impairment feature the kernel supports.

Most teams should start with Comcast for local development and graduate to scripted `tc/netem` rules in CI/CD pipelines. The investment in learning `tc` pays dividends because it works everywhere Linux runs and requires zero external dependencies.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted WAN Emulation & Network Simulation: Comcast vs Augmented Traffic Control vs Linux tc/netem",
  "description": "Compare three self-hosted WAN emulation tools — Comcast, Augmented Traffic Control, and Linux tc/netem — for simulating network latency, packet loss, bandwidth limits, and jitter in development and CI/CD pipelines.",
  "datePublished": "2026-06-08",
  "dateModified": "2026-06-08",
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
