---
title: "Self-Hosted ERSPAN and Port Mirroring: Open vSwitch vs ntopng vs Linux tc (2026)"
date: "2026-05-19"
tags: ["erspan", "port-mirroring", "network-monitoring", "openvswitch", "ntopng", "traffic-analysis"]
draft: false
---

ERSPAN (Encapsulated Remote Switched Port Analyzer) and port mirroring are essential techniques for network traffic monitoring, allowing administrators to copy and redirect traffic flows for analysis, security inspection, and troubleshooting without disrupting production traffic.

This guide compares three self-hosted approaches to ERSPAN and port mirroring: **Open vSwitch** for SDN-based mirroring, **ntopng** for traffic analysis with built-in capture, and **Linux tc** (traffic control) for kernel-level packet duplication.

## What Is ERSPAN and Port Mirroring?

**Port mirroring** (also called SPAN — Switched Port Analyzer) copies traffic from one or more source ports to a destination port where a monitoring tool can analyze it. **ERSPAN** extends this capability across network boundaries by encapsulating mirrored traffic in GRE headers, allowing remote monitoring across Layer 3 networks.

Key use cases include:
- **Intrusion detection**: Sending traffic copies to IDS/IPS systems like Suricata or Zeek
- **Network troubleshooting**: Capturing packets for analysis without interrupting services
- **Compliance auditing**: Maintaining traffic logs for regulatory requirements
- **Performance monitoring**: Analyzing application traffic patterns and bottlenecks
- **Forensic investigation**: Reconstructing network events after security incidents

## Open vSwitch (OVS)

Open vSwitch provides comprehensive port mirroring and ERSPAN capabilities through its OpenFlow integration and built-in mirroring APIs. It supports both local SPAN and remote ERSPAN with GRE encapsulation.

**GitHub**: [openvswitch/ovs](https://github.com/openvswitch/ovs) — ⭐3,952 | Last updated: May 2026 | Language: C

### Key Features

- **Local SPAN**: Mirror traffic between ports on the same bridge
- **ERSPAN**: Encapsulate mirrored traffic in GRE for remote delivery
- **Selective mirroring**: Filter by VLAN, MAC, IP, or port ranges
- **Bidirectional control**: Mirror RX, TX, or both directions independently
- **Multiple destinations**: Send copies to multiple monitoring ports simultaneously

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  ovs-vswitchd:
    image: docker.io/openvswitch/ovs:latest
    command: ovs-vswitchd --pidfile --detach --log-file
    network_mode: host
    privileged: true
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - /etc/openvswitch:/etc/openvswitch
      - /var/log/openvswitch:/var/log/openvswitch
    restart: unless-stopped

  ovsdb-server:
    image: docker.io/openvswitch/ovs:latest
    command: ovsdb-server --remote=punix:/var/run/openvswitch/db.sock
    network_mode: host
    volumes:
      - /var/run/openvswitch:/var/run/openvswitch
      - /etc/openvswitch:/etc/openvswitch
    restart: unless-stopped
```

### Configuration

```bash
# Create a local SPAN mirror (port1 -> monitor_port)
sudo ovs-vsctl -- --id=@p get port eth1 \
  -- --id=@m get port eth2 \
  -- --id=@s create mirror name=span0 select-all=true \
  -- set bridge br0 mirrors=@s \
  -- set mirror span0 output-port=@m

# ERSPAN configuration (GRE encapsulated)
sudo ovs-vsctl -- --id=@m create mirror name=erspan0 \
  select-all=true \
  output-port=@remote \
  -- set bridge br0 mirrors=@m

# Verify mirror configuration
sudo ovs-vsctl list mirror
```

## ntopng

ntopng is a high-performance web-based traffic analysis platform that includes built-in packet capture, flow analysis, and network monitoring capabilities. While not a traditional mirror switch, it can act as a traffic collection and analysis endpoint.

**GitHub**: [ntop/ntopng](https://github.com/ntop/ntopng) — ⭐7,796 | Last updated: May 2026 | Language: Lua

### Key Features

- **Real-time flow analysis**: NetFlow, sFlow, and IPFIX collection
- **Built-in packet capture**: pcap-based traffic capture with filtering
- **Web dashboard**: Interactive traffic visualization and alerting
- **Historical data**: Long-term traffic pattern analysis with RRD storage
- **Protocol detection**: Deep packet inspection for 5,000+ protocols
- **REST API**: Programmatic access to traffic data and alerts

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  redis:
    image: docker.io/redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
    restart: unless-stopped

  ntopng:
    image: docker.io/ntop/ntopng:stable
    command: >
      --community
      -i eth0
      -w 3000
      --local-networks "192.168.1.0/24"
    network_mode: host
    depends_on:
      - redis
    volumes:
      - ntopng-data:/var/lib/ntopng
      - /var/run/ntopng:/var/run/ntopng
    restart: unless-stopped

volumes:
  redis-data:
  ntopng-data:
```

### Packet Capture Configuration

```bash
# Start ntopng with packet capture on multiple interfaces
sudo ntopng -i eth0 -i eth1 -w 3000 \
  --local-networks "192.168.0.0/16" \
  --dump-flows /var/lib/ntopng/flows \
  --capture-direction both

# Filter traffic for capture
sudo ntopng -i eth0 \
  --packet-filter "tcp port 80 or tcp port 443" \
  --dump-packets /var/lib/ntopng/capture.pcap
```

## Linux tc (Traffic Control)

The Linux kernel's traffic control subsystem provides packet mirroring through the `tc` utility using the `mirred` (mirror/redirect) action. This is a lightweight, kernel-native approach that requires no external dependencies.

**GitHub**: [shemminger/iproute2](https://github.com/shemminger/iproute2) — ⭐968 | Last updated: May 2026 | Language: C

### Key Features

- **Kernel-native**: Built into the Linux networking stack via tc subsystem
- **Zero overhead**: No userspace daemon required for mirroring
- **Flexible filtering**: Match on any tc-recognizable packet attribute
- **Multiple actions**: Mirror, redirect, drop, or mark packets simultaneously
- **QoS integration**: Combine with policing, shaping, and prioritization

### Configuration

```bash
# Mirror all ingress traffic from eth0 to eth1
sudo tc qdisc add dev eth0 handle ffff: ingress
sudo tc filter add dev eth0 parent ffff: \
  protocol all \
  u32 match u32 0 0 \
  action mirred egress mirror dev eth1

# Mirror egress traffic with port filter (HTTP only)
sudo tc qdisc add dev eth0 root handle 1: htb
sudo tc filter add dev eth0 parent 1: \
  protocol ip \
  u32 match ip dport 80 0xffff \
  action mirred egress mirror dev eth2

# Verify tc rules
sudo tc -s filter show dev eth0 ingress
```

### Persistent Configuration (systemd)

```ini
# /etc/systemd/network/10-mirror.netdev
[NetDev]
Name=mirror0
Kind=dummy

# /etc/systemd/network/20-mirror.network
[Match]
Name=eth0

[TrafficControl]
# Requires systemd 250+ or manual tc commands in a service
```

## Comparison Table

| Feature | Open vSwitch | ntopng | Linux tc |
|---------|-------------|--------|----------|
| **Local SPAN** | Yes | Via capture | Yes (mirred) |
| **ERSPAN (GRE)** | Yes | No (endpoint only) | Via gretap device |
| **Selective Filtering** | VLAN/MAC/IP/Port | BPF filters | tc/u32/bpf filters |
| **Multiple Destinations** | Yes | No (single analysis) | Yes (chained actions) |
| **Bidirectional Control** | Yes | RX/TX via interface | Ingress/Egress separate |
| **Web Dashboard** | No | Yes (built-in) | No |
| **Flow Analysis** | Via sFlow export | Yes (native) | No |
| **Performance Impact** | Low (kernel datapath) | Medium (userspace) | Minimal (kernel) |
| **Hardware Offload** | Yes (SmartNIC) | No | Limited |
| **Best For** | SDN environments | Traffic analysis | Lightweight mirroring |

## Why Self-Host Your Port Mirroring Infrastructure?

Self-hosting ERSPAN and port mirroring gives you complete control over how network traffic is captured, analyzed, and stored. When you rely on cloud provider solutions, you often face limitations on what traffic can be mirrored, where it can be sent, and how long it can be retained. Running your own mirroring infrastructure removes these constraints and enables comprehensive network visibility for security and compliance.

For organizations with strict data residency requirements, self-hosted mirroring ensures that sensitive traffic never leaves your infrastructure. You can direct mirrored traffic to your own IDS/IPS systems, log aggregators, and forensic analysis tools without depending on third-party services. The flexibility to choose between SDN-based mirroring with OVS, analysis-focused collection with ntopng, or lightweight kernel-level duplication with tc means you can match the solution to your specific monitoring requirements.

For network flow analysis, see our [pmacct vs nfdump vs fprobe guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide-2026/). If you need NetFlow collection, check our [ElastiFlow vs Akvorado vs GoFlow2 comparison](../elastiflow-vs-akvorado-vs-goflow2-self-hosted-netflow-collector-guide-2026/). For OVS management, our [OVN vs OVS network virtualization guide](../2026-05-19-self-hosted-geneve-overlay-networking-ovn-ovs-linux-kernel-guide/) covers overlay networking.

## FAQ

### What is the difference between SPAN and ERSPAN?

SPAN (Switched Port Analyzer) mirrors traffic locally within a single switch or virtual switch. ERSPAN (Encapsulated Remote SPAN) encapsulates mirrored traffic in GRE headers, allowing it to be sent across Layer 3 networks to a remote monitoring destination. ERSPAN is essential when the monitoring tool is not on the same physical segment as the source traffic.

### Can I use ERSPAN with standard network equipment?

ERSPAN support varies by vendor. Cisco, Juniper, and Arista switches support ERSPAN natively. On the software side, Open vSwitch supports ERSPAN output, and Linux can create gretap interfaces for GRE-encapsulated traffic. Always verify that both the source and destination devices support the same ERSPAN version (v1, v2, or v3).

### Does ntopng replace the need for port mirroring?

ntopng is a traffic analysis platform, not a mirroring switch. You still need port mirroring (via OVS, tc, or hardware switches) to send traffic copies to ntopng. However, ntopng can capture traffic directly from interfaces in promiscuous mode, eliminating the need for mirroring if you install ntopng on a host with physical access to the network segment.

### How does tc mirroring compare to OVS mirroring?

Linux tc mirroring operates at the kernel level with minimal overhead but lacks the centralized management and programmability of OVS. OVS provides a more feature-rich mirroring API with OpenFlow integration, selective filtering, and multiple destination support. Use tc for simple mirroring needs and OVS when you need SDN-level control over traffic duplication.

### What is the performance impact of port mirroring?

Port mirroring typically doubles the traffic load on the monitoring destination port. The source port sees minimal overhead since mirroring is done at the switch level. For high-throughput links (10Gbps+), ensure your monitoring destination has sufficient bandwidth and that your capture tool can keep up. Hardware offload (SmartNICs for OVS, kernel GRO for tc) can significantly reduce CPU overhead.

### Can I mirror encrypted (HTTPS) traffic?

Yes, port mirroring copies all traffic regardless of encryption. However, the mirrored traffic will remain encrypted — you will see packet headers and metadata but not payload content. To inspect encrypted traffic, you need a TLS interception proxy or endpoint-level monitoring, which is a separate concern from port mirroring.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ERSPAN and Port Mirroring: Open vSwitch vs ntopng vs Linux tc (2026)",
  "description": "Compare Open vSwitch, ntopng, and Linux tc for self-hosted ERSPAN and port mirroring. Includes Docker Compose configs, selective filtering, and deployment guides.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
