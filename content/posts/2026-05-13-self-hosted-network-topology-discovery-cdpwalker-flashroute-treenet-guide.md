---
title: "Self-Hosted Network Topology Discovery — CDPWalker vs FlashRoute vs TreeNET"
date: "2026-05-13"
tags: ["networking", "topology", "discovery", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare self-hosted network topology discovery tools — CDPWalker, FlashRoute, and TreeNET. Learn to automatically map your network infrastructure, discover devices, and visualize connections."
---

Managing a network without an accurate topology map is like navigating a city without a map. Devices fail, connections break, and troubleshooting becomes guesswork. Network topology discovery tools automatically scan your infrastructure, identify every device, and map how they connect — creating a living diagram of your network.

Commercial discovery platforms cost thousands per year. This guide covers three **open-source, self-hosted alternatives** that work across small offices to enterprise data centers.

## What Is Network Topology Discovery?

Network topology discovery is the automated process of identifying devices (routers, switches, servers, endpoints) on a network and mapping the connections between them. Tools use multiple protocols and techniques:

- **CDP (Cisco Discovery Protocol)** — Cisco proprietary neighbor discovery
- **LLDP (Link Layer Discovery Protocol)** — IEEE standard (802.1AB) neighbor discovery
- **SNMP** — Querying device MIBs for interface and routing information
- **Active probing** — Traceroute, ARP scanning, and ICMP ping sweeps
- **BGP Link State (BGP-LS)** — Collecting topology from BGP routers

The result is a comprehensive network map showing physical connections, logical paths, and device inventory.

## Comparison Table

| Feature | CDPWalker | FlashRoute.rs | TreeNET |
|---------|-----------|---------------|---------|
| **Stars** | 42+ | 35+ | 11+ |
| **Language** | Python | Rust | C/C++ |
| **Discovery Method** | CDP/SNMP | Traceroute + Active | Subnet inference + SNMP |
| **Protocol Support** | CDP, SNMP | ICMP, UDP | SNMP, ICMP |
| **Output Format** | Graph/JSON | Internet topology | Network graph |
| **Cisco Focus** | Yes (CDP) | No (general) | No (general) |
| **Real-time Scanning** | Yes | Yes | Yes |
| **Web UI** | No | No | No |
| **API** | No | No | No |
| **Best For** | Cisco-heavy networks | Internet-scale mapping | Enterprise subnet discovery |

## CDPWalker

**GitHub:** [verbosemode/cdpwalker](https://github.com/verbosemode/cdpwalker) (42+ stars)

CDPWalker discovers network topology using Cisco Discovery Protocol (CDP) and SNMP. It queries Cisco devices for their CDP neighbor tables, then recursively walks the network to build a complete topology map.

### How It Works

CDP is a Layer 2 protocol that Cisco devices use to advertise their identity, capabilities, and neighbors to directly connected devices. CDPWalker exploits this by:

1. Starting from a seed device (your core switch or router)
2. Querying its CDP neighbor table via SNMP
3. Recursively connecting to each neighbor and repeating
4. Building a complete graph of all discovered devices

### Installation

```bash
# Install dependencies
pip install pysnmp networkx matplotlib

# Clone and run
git clone https://github.com/verbosemode/cdpwalker.git
cd cdpwalker
python3 cdpwalker.py --seed 192.168.1.1 --community public
```

### Configuration

```python
# config.py
SEED_DEVICES = ["192.168.1.1", "192.168.1.2"]
SNMP_COMMUNITY = "readonly"
SNMP_VERSION = "2c"
MAX_DEPTH = 10  # Maximum hop depth
OUTPUT_FORMAT = "json"  # json, graphml, dot
```

### Docker Compose

```yaml
version: "3.8"
services:
  cdpwalker:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./cdpwalker:/app
      - ./output:/output
    network_mode: host
    command: >
      bash -c "pip install pysnmp networkx && 
               python3 cdpwalker.py 
               --seed 192.168.1.1 
               --community public
               --output /output/topology.json"
```

### When to Use CDPWalker

- **Cisco-heavy environments** — leverages CDP for accurate neighbor discovery
- **Network documentation** — automatically generates up-to-date topology maps
- **Troubleshooting** — identify unexpected connections or missing devices
- **Migration planning** — understand dependencies before moving equipment

## FlashRoute (FlashRoute.rs)

**GitHub:** [BugenZhao/flashroute.rs](https://github.com/BugenZhao/flashroute.rs) (35+ stars)

FlashRoute is a Rust implementation of a fast Internet topology discovery tool. It uses optimized traceroute techniques to map network paths at scale, making it ideal for discovering wide-area network topology.

### How It Works

FlashRoute improves on traditional traceroute by:

- **Parallel probing** — sends multiple probes simultaneously
- **Smart target selection** — focuses on under-discovered network regions
- **IP alias resolution** — identifies when multiple IPs belong to the same router
- **Efficient storage** — compact representation of discovered topology

### Installation

```bash
# Requires Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Clone and build
git clone https://github.com/BugenZhao/flashroute.rs.git
cd flashroute.rs
cargo build --release

# Run discovery
./target/release/flashroute --targets targets.txt --output topology.json
```

### Target File Format

```text
# targets.txt - IP addresses or CIDR ranges to probe
8.8.8.8
1.1.1.1
208.67.222.222
104.16.0.0/12
```

### When to Use FlashRoute

- **Wide-area network mapping** — discover paths across the Internet
- **CDN topology analysis** — understand how content delivery networks route traffic
- **BGP path verification** — confirm expected routing paths
- **Research and education** — study Internet topology structure

## TreeNET

**GitHub:** [JefGrailet/treenet](https://github.com/JefGrailet/treenet) (11+ stars)

TreeNET is a subnet-based topology discovery tool built on top of ExploreNET (a subnet inference engine). It discovers network topology by inferring subnet structures and mapping connections between them.

### How It Works

TreeNET combines multiple discovery techniques:

1. **Subnet inference** — Uses ExploreNET to identify IP subnet boundaries
2. **SNMP polling** — Queries devices within discovered subnets
3. **Traceroute** — Maps paths between subnets
4. **Graph construction** — Builds a hierarchical topology tree

### Installation

```bash
# Build from source
git clone https://github.com/JefGrailet/treenet.git
cd treenet
make

# Or use pre-built binaries if available
# Run discovery
./treenet --interface eth0 --snmp-community public
```

### Configuration

```ini
# treenet.conf
[discovery]
interface = eth0
snmp_community = public
snmp_timeout = 3000
max_hops = 15
subnet_threshold = 24

[output]
format = graphml
output_file = topology.graphml
include_metadata = true
```

### When to Use TreeNET

- **Enterprise subnet mapping** — discover and document subnet structures
- **Network planning** — identify unused address space and plan expansions
- **Security auditing** — find unauthorized devices on your network
- **Campus networks** — map multi-building network infrastructure

## Why Self-Host Your Network Topology Discovery?

### Complete Network Visibility

Cloud-based discovery tools can only see what's reachable from the Internet. Self-hosted tools operate inside your network, discovering internal switches, access points, IoT devices, and servers that are invisible to external scanners.

### No Data Leaving Your Network

Commercial topology tools send your network inventory to cloud servers. Self-hosted discovery keeps all device information, IP addresses, and connection data on-premises — critical for compliance and security.

### Continuous Discovery

Run discovery tools on a schedule (via cron) to detect changes automatically:

```bash
# /etc/cron.d/topology-discovery
0 2 * * 1 root /opt/cdpwalker/run.sh > /var/log/topology-discovery.log 2>&1
```

Compare weekly topology snapshots to detect unauthorized devices, changed connections, or failed links before they cause outages.

### Integration With Monitoring

Feed topology data into your monitoring stack:

```bash
# Export topology to Prometheus-compatible format
python3 export_topology.py --format prometheus > /var/lib/node_exporter/topology.prom
```

## Integrating Discovery With Monitoring

Topology discovery data feeds directly into monitoring and security systems. The discovered device inventory becomes the foundation for SNMP monitoring, network flow analysis, and security auditing. Pair your discovery tool with [SNMP trap management](../2026-05-12-self-hosted-snmp-trap-management-snmptt-snmptrapd/) for real-time device event tracking, and use [network flow collectors](../2026-05-24-self-hosted-network-flow-collectors-goflow2-softflowd-nfdump-guide/) to validate discovered paths with actual traffic data.

## Choosing the Right Topology Discovery Tool

| Scenario | Recommended Tool | Reason |
|----------|-----------------|--------|
| Cisco-dominated network | CDPWalker | Native CDP support, accurate neighbor discovery |
| Internet/WAN mapping | FlashRoute | Optimized traceroute, large-scale discovery |
| Enterprise subnet mapping | TreeNET | Subnet inference, hierarchical topology |
| Multi-vendor environment | TreeNET + CDPWalker | SNMP-based discovery works across vendors |
| Research/academic | FlashRoute | Internet-scale topology data |

## FAQ

### What protocols do topology discovery tools use?

Topology discovery tools use several protocols: **CDP** (Cisco proprietary, Layer 2 neighbor discovery), **LLDP** (IEEE 802.1AB standard, vendor-neutral neighbor discovery), **SNMP** (queries device MIBs for interface and routing tables), **ICMP traceroute** (maps paths between devices), and **ARP scanning** (discovers devices on local subnets). The best results come from combining multiple protocols.

### Can these tools discover wireless network topology?

Partially. CDP and LLDP work on wireless interfaces that support them, but WiFi topology is more complex due to roaming, multiple SSIDs, and virtual interfaces. For comprehensive wireless discovery, combine topology tools with wireless controller APIs (like OpenWRT's hostapd interface or UniFi controller API).

### How often should I run topology discovery?

For stable networks, weekly discovery is sufficient. For dynamic environments (data centers with frequent changes, growing campuses), run daily. Schedule discovery during low-traffic periods to minimize impact. Always compare new results with previous snapshots to detect changes.

### Is SNMP required for topology discovery?

SNMP significantly improves discovery accuracy, especially for CDPWalker and TreeNET. Without SNMP, tools rely on active probing (traceroute, ping) which discovers paths but not detailed device information. Configure SNMPv3 with authentication and encryption for security — avoid SNMPv2c community strings in production.

### Can topology discovery tools work across VLANs?

CDP and LLDP operate at Layer 2 and don't cross VLAN boundaries. SNMP and traceroute-based discovery (FlashRoute, TreeNET) work across VLANs and routed segments. For complete multi-VLAN discovery, run the tool from a management VLAN with routing access to all other VLANs, or deploy discovery agents in each VLAN.

### How accurate is automatically discovered topology?

Automated discovery is typically 90-95% accurate for wired networks. Gaps occur due to: firewalls blocking SNMP/CDP, devices with discovery protocols disabled, asymmetric routing paths, and virtual/overlay networks (VXLAN, GRE tunnels). Always validate critical paths manually and use discovery as a starting point, not the final word.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Topology Discovery — CDPWalker vs FlashRoute vs TreeNET",
  "description": "Compare self-hosted network topology discovery tools — CDPWalker, FlashRoute, and TreeNET. Learn to automatically map your network infrastructure, discover devices, and visualize connections.",
  "datePublished": "2026-05-13",
  "dateModified": "2026-05-13",
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
