---
title: "Self-Hosted TCP Congestion Control: BBR vs Cubic vs FQ-Codel Guide (2026)"
date: "2026-05-21"
description: "Optimize TCP performance on self-hosted servers with the best congestion control algorithms and queue management disciplines — BBR v2, Cubic, and FQ-Codel."
tags: ["networking", "tcp", "performance", "bbr", "congestion-control", "fq-codel", "linux", "self-hosted"]
draft: false
---

TCP congestion control algorithms determine how quickly a sender transmits data into the network, balancing throughput against latency and packet loss. For self-hosted servers handling web traffic, file transfers, or streaming, choosing the right congestion control algorithm and queue management discipline can dramatically improve user experience — especially on networks with variable bandwidth or high latency.

This guide covers the three most important congestion control approaches for self-hosted infrastructure: Google BBR (Bottleneck Bandwidth and Round-trip propagation time), TCP Cubic (the Linux default), and FQ-Codel (Fair Queuing Controlled Delay) for queue management.

## Understanding TCP Congestion Control

TCP congestion control solves a fundamental problem: how to send data as fast as possible without overwhelming the network path between sender and receiver. When too much data enters a network link, queues build up at routers, latency increases, and eventually packets are dropped. Congestion control algorithms detect these conditions and adjust the sending rate accordingly.

### How Congestion Control Works

Every TCP connection maintains a **congestion window** (cwnd) — the maximum amount of unacknowledged data that can be in flight. The algorithm determines how this window grows and shrinks:

- **Slow Start**: The window doubles each round-trip time until it hits a threshold
- **Congestion Avoidance**: The window grows linearly once past slow start
- **Loss Recovery**: The window shrinks when packet loss is detected
- **Recovery**: The window gradually increases after loss events

### Queue Management vs Congestion Control

Queue management disciplines operate at a different layer than congestion control. While congestion control runs on the sender, queue management runs on the network device (router, switch, or server network stack) to manage how packets are queued and scheduled:

| Aspect | Congestion Control | Queue Management |
|--------|-------------------|-----------------|
| **Where it runs** | Sender's TCP stack | Network device / router |
| **What it controls** | Sending rate (cwnd) | Packet scheduling and dropping |
| **Examples** | BBR, Cubic, Reno, DCTCP | FQ-Codel, CAKE, RED, PIE |
| **Bufferbloat impact** | Indirect (reduces data in flight) | Direct (manages queue depth) |
| **Best combined with** | Any algorithm | BBR or Cubic |

For self-hosted servers, you typically configure the congestion control algorithm on the server itself and the queue management discipline on the router or gateway serving your network.

## BBR v2: Model-Based Congestion Control

Google's BBR (Bottleneck Bandwidth and Round-trip propagation time) represents a fundamentally different approach to congestion control. Instead of reacting to packet loss as a congestion signal, BBR builds a model of the network path and sends at the optimal rate based on measured bandwidth and round-trip time.

### How BBR Works

BBR operates in four states, cycling through them as it probes the network:

1. **Startup**: Rapidly increases sending rate until bandwidth stops growing (equivalent to slow start)
2. **Drain**: Reduces inflight data to drain the bottleneck queue
3. **ProbeBW**: Cycles through pacing gains to probe for additional bandwidth
4. **ProbeRTT**: Periodically reduces inflight to measure minimum RTT

**BBR v2** (available in Linux kernel 5.6+) improves on v1 by being more friendly to competing Cubic flows and handling ECN (Explicit Congestion Notification) signals.

### Enabling BBR

**Check available algorithms:**
```bash
sysctl net.ipv4.tcp_available_congestion_control
# Output: bbr cubic reno
```

**Set BBR as default:**
```bash
sudo sysctl -w net.core.default_qdisc=fq
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr
```

**Make persistent (`/etc/sysctl.d/10-bbr.conf`):**
```ini
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
```

**Verify active algorithm:**
```bash
sysctl net.ipv4.tcp_congestion_control
# Output: net.ipv4.tcp_congestion_control = bbr
```

### BBR Docker Configuration

For containers, you need to set the congestion control algorithm at the host level since it is a kernel-level setting:

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    container_name: webapp
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    networks:
      - app-net
    # BBR must be set on the host, not per-container
    sysctls:
      - net.ipv4.tcp_congestion_control=bbr

networks:
  app-net:
    driver: bridge
```

### When to Use BBR

- **High-bandwidth, high-latency paths** (long-distance transfers, satellite links)
- **Lossy networks** where packet loss is not caused by congestion
- **Web servers** serving global audiences
- **Streaming servers** where consistent throughput matters

**Avoid BBR when:** Your network has strict fairness requirements with many competing flows, or when you are on a shared network where BBR v1's aggressiveness could impact other users (v2 addresses this).

## TCP Cubic: The Linux Default

Cubic has been the default TCP congestion control algorithm in Linux since kernel 2.6.19 (2007). It uses a cubic function to grow the congestion window, providing a good balance between aggressiveness in high-speed networks and fairness with existing TCP flows.

### How Cubic Works

After a loss event, Cubic enters a **concave region** where it quickly ramps up to the previous window size, then a **convex region** where it grows slowly to probe for additional bandwidth. This cubic function allows Cubic to utilize high-bandwidth links efficiently while remaining TCP-friendly.

### Cubic is Already the Default

On most Linux systems, Cubic is already active:

```bash
sysctl net.ipv4.tcp_congestion_control
# Output: net.ipv4.tcp_congestion_control = cubic
```

**Cubic-specific tunables (`/etc/sysctl.d/10-cubic.conf`):**
```ini
# Increase TCP buffer sizes for high-bandwidth links
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# Enable window scaling
net.ipv4.tcp_window_scaling = 1

# Enable selective acknowledgments
net.ipv4.tcp_sack = 1
```

### When to Use Cubic

- **General-purpose servers** where compatibility matters
- **Mixed traffic environments** with many competing flows
- **Default choice** when you are unsure which algorithm to use
- **Datacenter environments** where DCTCP might be more appropriate

## FQ-Codel: Queue Management for Bufferbloat Prevention

FQ-Codel (Fair Queuing Controlled Delay) is a queue management discipline that combines fair queuing (separate queues per flow) with Codel (an algorithm that detects and controls bufferbloat by managing queue delay).

### The Bufferbloat Problem

Bufferbloat occurs when network devices have oversized buffers that fill up completely before dropping packets. This causes:

- High latency (hundreds of milliseconds instead of tens)
- Jitter (variable latency that ruins real-time applications)
- Poor interactive performance even with high bandwidth

FQ-Codel solves this by actively managing queue depth, keeping latency low while maintaining high throughput.

### Enabling FQ-Codel

**On a Linux router/gateway:**
```bash
# Set FQ-Codel as the default queue discipline
sudo tc qdisc add dev eth0 root fq_codel

# Verify
tc qdisc show dev eth0
# Output: qdisc fq_codel 8006: root refcnt 2 limit 10240p flows 1024 quantum 1514 target 5.0ms
```

**Persist via `/etc/sysctl.d/10-fqcodel.conf`:**
```ini
net.core.default_qdisc = fq_codel
```

**For Wi-Fi interfaces (bufferbloat is worst here):**
```bash
sudo tc qdisc add dev wlan0 root fq_codel
```

### FQ-Codel vs CAKE

| Feature | FQ-Codel | CAKE |
|---------|----------|------|
| **Complexity** | Simple, well-tested | More complex, feature-rich |
| **Flow isolation** | Per-flow fair queuing | Per-host fair queuing |
| **Bandwidth shaping** | No (use HTB separately) | Built-in rate limiting |
| **DSF/TOS awareness** | No | Yes |
| **Kernel support** | Mainline since 3.6 | Mainline since 4.19 |
| **Best for** | General-purpose routers | Routers needing traffic shaping |

### Docker Network with FQ-Codel

For container environments, set the queue discipline on the host's Docker bridge:

```bash
sudo tc qdisc add dev docker0 root fq_codel
sudo tc qdisc add dev veth+ root fq_codel
```

## Performance Testing Your Configuration

After changing congestion control or queue management settings, verify the improvements with proper measurement tools.

### Using flent

[flent](https://flent.org/) (The FLExible Network Tester) is designed specifically for testing bufferbloat and TCP performance:

```bash
# Install
sudo apt install flent

# Run a bufferbloat test (requires a test server)
flent rrul -H test-server.example.com -l 60 -o result.png

# Test throughput
flent tcp_2down -H test-server.example.com -l 60
```

### Using iperf3

[iperf3](https://github.com/esnet/iperf) measures maximum TCP throughput:

```bash
# Server
iperf3 -s -p 5201

# Client
iperf3 -c server.example.com -p 5201 -t 30 -P 4
```

### Quick Verification

```bash
# Check active congestion control
cat /proc/sys/net/ipv4/tcp_congestion_control

# Check queue discipline
tc qdisc show

# Monitor TCP stats in real-time
ss -ti | head -20
```

## Choosing the Right Configuration

For most self-hosted servers, the recommended combination is:

| Environment | Congestion Control | Queue Discipline |
|-------------|-------------------|-----------------|
| **Web server** | BBR v2 | FQ (on server) |
| **Home router** | Cubic (default) | FQ-Codel |
| **File server** | Cubic | FQ-Codel |
| **Game server** | BBR v2 | FQ-Codel |
| **Datacenter** | DCTCP | FQ |

The combination of BBR v2 on servers and FQ-Codel on routers addresses both the sender-side and network-side of the congestion equation, providing the best overall experience for latency-sensitive and bandwidth-heavy applications.

## Why Optimize TCP on Self-Hosted Servers?

Default TCP settings are designed for broad compatibility, not optimal performance. Tuning congestion control and queue management can deliver measurable improvements:

**Lower Latency**: BBR v2 can reduce tail latency by 10-50% on high-latency paths compared to Cubic, especially for international connections. FQ-Codel keeps queue-induced latency under 10ms even under heavy load, compared to hundreds of milliseconds with default FIFO queuing.

**Better Throughput**: On high-bandwidth links (100 Mbps+), BBR can achieve 2-3x the throughput of Cubic when packet loss is present. For file servers and media streaming, this translates directly to faster transfers and smoother playback.

**Improved User Experience**: Interactive applications like SSH, video calls, and gaming are extremely sensitive to latency spikes. Proper queue management eliminates the "lag spikes" that occur when buffers fill up, making self-hosted services feel as responsive as cloud-hosted alternatives.

For related reading, see our [MPTCP solutions guide](../2026-05-13-self-hosted-mptcp-solutions-openmptcprouter-mptcpd-kernel-guide/) for multi-path TCP and [packet capture tools comparison](../2026-04-27-tcpdump-vs-tshark-vs-termshark-self-hosted-packet-capture-guide-2026/) for network analysis.

## FAQ

### Which TCP congestion control algorithm should I use?

For most self-hosted servers, BBR v2 provides the best performance, especially for web servers serving global audiences. TCP Cubic remains a safe default if you need compatibility or are on a shared network. Use FQ-Codel as the queue discipline on your router or gateway to prevent bufferbloat.

### How do I check which congestion control algorithm is active?

Run `sysctl net.ipv4.tcp_congestion_control` to see the current algorithm. To see what algorithms are available, run `sysctl net.ipv4.tcp_available_congestion_control`. You can also check per-connection with `ss -ti` — look for `cc:` in the output.

### Can I set different congestion control per application?

Not directly, since congestion control is a kernel-level setting. However, you can use `ip route` with different routing tables or network namespaces to apply different settings per service. Some applications (like nginx) can also set socket-level congestion control via `setsockopt()`.

### What is bufferbloat and why does it matter?

Bufferbloat is the excessive buffering of packets in network devices, causing high latency and jitter even when bandwidth is available. It makes interactive applications (VoIP, gaming, SSH) feel sluggish. FQ-Codel and CAKE solve this by actively managing queue depth instead of waiting for buffers to overflow.

### Do I need to reboot after changing congestion control?

No. Changes made via `sysctl -w` take effect immediately for new TCP connections. Existing connections continue using their current algorithm. To make changes persistent across reboots, add the settings to `/etc/sysctl.d/` configuration files.

### Is BBR v2 better than BBR v1?

Yes. BBR v2 is more fair to competing Cubic flows, handles ECN signals, and performs better in mixed-traffic environments. BBR v1 was sometimes criticized for being too aggressive on shared networks — v2 addresses these concerns. BBR v2 is available in Linux kernel 5.6 and later.

### Can I use BBR inside Docker containers?

The congestion control algorithm is a kernel-level setting, so it must be set on the host system. Docker containers inherit the host's congestion control algorithm. You can verify this by checking `sysctl net.ipv4.tcp_congestion_control` on the Docker host.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TCP Congestion Control: BBR vs Cubic vs FQ-Codel Guide (2026)",
  "description": "Optimize TCP performance on self-hosted servers with the best congestion control algorithms and queue management disciplines — BBR v2, Cubic, and FQ-Codel.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
