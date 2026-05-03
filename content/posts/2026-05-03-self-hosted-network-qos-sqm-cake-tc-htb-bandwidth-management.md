---
title: "Self-Hosted Network QoS: SQM Scripts vs CAKE vs TC-HTB Bandwidth Management (2026 Guide)"
date: 2026-05-03T23:00:00+00:00
tags: ["networking", "qos", "bandwidth", "traffic-shaping", "linux"]
draft: false
---

Network congestion ruins the experience for every user on a shared connection. Whether you are managing a home network with multiple streamers, an office with competing video calls, or a server handling mixed traffic types, Quality of Service (QoS) ensures critical traffic gets priority. This guide compares three leading open-source approaches to network traffic shaping: **SQM Scripts**, **CAKE**, and **TC-HTB**.

## Overview Comparison

| Feature | SQM Scripts | CAKE | TC-HTB |
|---------|-------------|------|--------|
| Complexity | Low (set and forget) | Very Low | High |
| Bufferbloat Fix | Excellent | Excellent | Manual |
| Per-Host Fairness | Yes (flows) | Yes (hosts) | Manual config |
| Automatic Bandwidth Detection | Yes (bandwidth test) | Manual | No |
| Linux Kernel Support | 4.19+ | 5.19+ | All kernels |
| OpenWrt Support | Built-in | Built-in (default) | Available |
| Learning Curve | Minimal | Minimal | Steep |
| Fine-Grained Control | Limited | Limited | Complete |

## SQM Scripts (Smart Queue Management)

SQM Scripts provide a unified interface for configuring modern queue management disciplines on Linux. Built on top of `tc` (traffic control) and `fq_codel` or `cake` qdiscs, SQM scripts automate the complex configuration that traditionally required deep networking expertise.

### Key Features

- Automatic bufferbloat mitigation
- Per-flow fairness for equitable bandwidth sharing
- Simple bandwidth parameter configuration
- Support for both ingress and egress shaping
- Works on any Linux distribution

### Configuration via /etc/sqm/simple.qos

```bash
# /etc/sqm/simple.qos
# Bandwidth settings (set to 90% of your actual link speed)
INGRESS_BW="100mbit"
EGRESS_BW="100mbit"

# Queue discipline
QDISC="cake"    # or "fq_codel"

# Overhead compensation (for DSL/VDSL)
# OVERHEAD="34"

# Apply configuration
tc qdisc add dev eth0 root cake bandwidth ${EGRESS_BW} nat dual-dsthost
tc qdisc add dev ifb0 root cake bandwidth ${INGRESS_BW} nat dual-srchost
```

### OpenWrt Deployment

```bash
# Install SQM
opkg update
opkg install sqm-scripts

# Configure via UCI
uci set sqm.@queue[0].download=100000
uci set sqm.@queue[0].upload=50000
uci set sqm.@queue[0].qdisc_advanced="cake"
uci commit sqm
/etc/init.d/sqm restart

# Verify active qdiscs
tc qdisc show
```

### Docker-Based Monitoring Container

```yaml
version: "3.8"
services:
  sqm-monitor:
    image: alpine:latest
    container_name: sqm-monitor
    network_mode: host
    pid: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    command:
      - sh
      - -c
      - |
        while true; do
          cat /host/proc/net/dev
          tc -s qdisc show
          sleep 5
        done
    restart: unless-stopped
```

## CAKE (Common Applications Kept Enhanced)

CAKE is a Linux traffic shaping qdisc that combines multiple queue management algorithms into a single, easy-to-configure module. It is now the default QoS system in OpenWrt and is widely considered the best set-and-forget solution for bufferbloat mitigation.

### Key Features

- Combines fq (fair queuing), Codel (controlled delay), and rate shaping
- Automatic host-based fairness
- NAT-aware flow tracking
- DiffServ/ToS awareness for priority traffic
- Built-in bandwidth estimation

### Kernel Module Configuration

```bash
# Load the cake module
modprobe sch_cake

# Apply CAKE to an interface
tc qdisc add dev eth0 root cake bandwidth 100mbit     nat dual-dsthost     diffserv4     besteffort     wash

# Verify
tc -s qdisc show dev eth0
```

### OpenWrt SQM with CAKE

```bash
# OpenWrt 22.03+ uses CAKE by default
# Configure via LuCI web interface:
# Network → Switch → SQM QoS
# Or via CLI:
uci set sqm.@queue[0].enabled='1'
uci set sqm.@queue[0].interface='eth0'
uci set sqm.@queue[0].download=100000
uci set sqm.@queue[0].upload=50000
uci set sqm.@queue[0].qdisc='cake'
uci commit sqm
/etc/init.d/sqm restart
```

## TC-HTB (Hierarchical Token Bucket)

TC-HTB is the traditional Linux traffic shaping system. It provides the most granular control over bandwidth allocation but requires manual configuration of class hierarchies, filters, and qdiscs. It is ideal for complex scenarios where simple fair queuing is not enough.

### Key Features

- Hierarchical class-based bandwidth allocation
- Precise rate guarantees for each class
- Borrow mechanism for unused bandwidth sharing
- Custom packet classification with u32 filters
- Industry standard for enterprise traffic shaping

### Configuration Example

```bash
#!/bin/bash
# tc-htb-setup.sh

DEV="eth0"
TOTAL_BW="100mbit"

# Root qdisc with HTB
tc qdisc add dev $DEV root handle 1: htb default 30

# Root class
tc class add dev $DEV parent 1: classid 1:1 htb rate $TOTAL_BW burst 15k

# High priority class (VoIP, SSH)
tc class add dev $DEV parent 1:1 classid 1:10 htb rate 20mbit ceil 50mbit burst 15k
tc qdisc add dev $DEV parent 1:10 handle 10: pfifo limit 50

# Medium priority class (web browsing)
tc class add dev $DEV parent 1:1 classid 1:20 htb rate 40mbit ceil 80mbit burst 15k
tc qdisc add dev $DEV parent 1:20 handle 20: fq_codel

# Default class (everything else)
tc class add dev $DEV parent 1:1 classid 1:30 htb rate 20mbit ceil 60mbit burst 15k
tc qdisc add dev $DEV parent 1:30 handle 30: fq_codel

# Classify traffic
tc filter add dev $DEV parent 1: protocol ip prio 1 u32     match ip dport 22 0xffff flowid 1:10
tc filter add dev $DEV parent 1: protocol ip prio 1 u32     match ip sport 5060 0xffff flowid 1:10
tc filter add dev $DEV parent 1: protocol ip prio 2 u32     match ip protocol 6 0xff flowid 1:20
```

### Docker Container for TC Management

```yaml
version: "3.8"
services:
  tc-manager:
    image: alpine:latest
    container_name: tc-manager
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./tc-setup.sh:/tc-setup.sh:ro
    command: sh /tc-setup.sh
    restart: unless-stopped
```

## Why Manage Network QoS Yourself?

**Eliminate Bufferbloat:** Without proper queue management, a single large download can make your entire network feel sluggish. Video calls drop, gaming becomes unplayable, and web pages time out. SQM and CAKE solve this automatically by keeping queue depths small while maintaining throughput.

**Fair Bandwidth Sharing:** In shared environments — households, offices, co-working spaces — one user should not be able to saturate the connection. Per-flow and per-host fairness ensures everyone gets equitable access. For organizations that also need visibility into [bandwidth consumption patterns](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide-2026/), combining QoS with monitoring tools provides complete network management.

**Prioritize Critical Traffic:** Not all traffic is equal. VoIP calls, SSH sessions, and DNS queries need low latency. Bulk downloads and backups can wait. QoS ensures critical packets are served first, improving the perceived quality of your network.

**No Cloud Dependency:** All three approaches run entirely on your hardware. There are no subscription fees, no cloud dependencies, and no data leaving your network.

## When to Use Each Approach

| Scenario | Recommended |
|----------|-------------|
| Home network, set-and-forget | CAKE via SQM Scripts |
| OpenWrt router | CAKE (default in 22.03+) |
| Enterprise with SLA requirements | TC-HTB |
| Mixed traffic with strict priorities | TC-HTB |
| Simple bandwidth fairness | SQM Scripts + fq_codel |
| Maximum performance with minimal config | CAKE |

## FAQ

### What is bufferbloat and why does it matter?
Bufferbloat occurs when network buffers are too large, causing packets to wait in queues instead of being dropped early. This results in high latency and jitter, making real-time applications like VoIP and gaming unusable. SQM and CAKE use active queue management (AQM) to keep buffers small while maintaining throughput.

### How do I determine the right bandwidth values?
Set bandwidth to approximately 90% of your actual link speed. You can measure your true speed using tools like `iperf3` or online speed tests. Setting it too high will cause the QoS to be ineffective; setting it too low will artificially limit your connection.

### Can I use QoS on a virtual machine or container?
TC-HTB and CAKE require kernel-level support. In a VM, you can apply QoS to the virtual network interface. In Docker containers, you can use the `--cap-add=NET_ADMIN` flag with `network_mode: host` to apply tc rules. However, the most effective approach is to configure QoS on the physical router or gateway.

### Does CAKE work on all Linux distributions?
CAKE requires kernel 5.19 or newer for full functionality. Most modern distributions (Ubuntu 23.04+, Debian 12+, Fedora 38+) include CAKE support. You can check with `tc qdisc add dev lo root cake 2>&1` — if it succeeds without errors, CAKE is available.

### Can I combine SQM Scripts with CAKE?
Yes. SQM Scripts is a configuration wrapper that can use CAKE as its underlying qdisc. In fact, this is the recommended approach: SQM handles the configuration complexity while CAKE provides the actual queue management. OpenWrt uses this combination by default.

### How do I verify QoS is working?
Use `tc -s qdisc show` to see active queue disciplines and their statistics. During a large download, monitor latency with `ping` to an external server — if QoS is working, ping times should remain stable rather than spiking. For comprehensive network visibility, pair QoS with [traffic analysis tools](../vnstat-vs-nethogs-vs-iftop-self-hosted-bandwidth-monitoring-guide-2026/) to understand long-term bandwidth patterns.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network QoS: SQM Scripts vs CAKE vs TC-HTB Bandwidth Management",
  "description": "Compare SQM Scripts, CAKE, and TC-HTB for self-hosted network quality of service and bandwidth management. Configuration examples and Docker deployment included.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide", "logo": {"@type": "ImageObject", "url": "https://hopkdj.github.io/openswap-guide/logo.png"}}
}
</script>
