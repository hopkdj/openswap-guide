---
title: "Self-Hosted Network Topology Mapping — NetBox, LibreNMS & Auto-Discovery Tools"
date: 2026-05-02
draft: false
tags:
  - networking
  - monitoring
  - infrastructure
  - self-hosted
  - network-management
---

When your infrastructure grows beyond a handful of servers, keeping track of how everything connects — switches to routers, firewalls to servers, VLANs to subnets — becomes essential. Self-hosted network topology mapping tools automatically discover and visualize your network layout, generating real-time maps that show device relationships, link status, and traffic flows.

In this guide, we compare three approaches to self-hosted network topology: **NetBox with topology plugins** (infrastructure source-of-truth with visual mapping), **LibreNMS network maps** (monitoring-driven auto-discovery), and **dedicated network mapping tools** like InterMapper alternatives.

## Why Network Topology Mapping Matters

Without an accurate network map, troubleshooting becomes guesswork:

- Which switch port connects to that server?
- What happens to traffic if this router link fails?
- Which devices are on the same VLAN?
- Where are the single points of failure?

Self-hosted topology tools solve these problems by automatically discovering network relationships and generating visual maps that update as your infrastructure changes.

## Comparison Table

| Feature | NetBox + Topology Plugin | LibreNMS Topology | Dedicated Network Mapper |
|---------|-------------------------|-------------------|-------------------------|
| **GitHub Stars** | 12,000+ (NetBox) | 3,000+ (LibreNMS) | 100–500 |
| **Auto-Discovery** | Via plugins / scripts | LLDP, CDP, ARP, SNMP | SNMP-based scanning |
| **Topology Source** | Manually defined + imported | Protocol-based (LLDP/CDP) | Active network scanning |
| **Visualization** | SVG/GraphViz topology views | Interactive network maps | Real-time topology graphs |
| **IPAM Integration** | Built-in | Basic | Limited |
| **Circuit Tracking** | Yes | No | No |
| **Docker Support** | Yes (official image) | Yes | Varies |
| **Database** | PostgreSQL | MySQL/MariaDB | Varies |
| **Best For** | Documentation + planning | Live monitoring | Real-time discovery |

## NetBox with Topology Plugins

NetBox is the industry-standard infrastructure source-of-truth (IPAM + DCIM) originally developed by DigitalOcean. While its core focuses on recording infrastructure state, the **netbox-topology-views** plugin adds visual network topology generation.

### Key Features

- **Topology views**: Generate network maps from device connections and circuits defined in NetBox
- **GraphViz rendering**: Automatic layout of device relationships using DOT language
- **Filtering**: Show specific device types, sites, or regions
- **Export**: SVG and PNG output for documentation
- **Custom roles**: Define device roles with custom icons

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  netbox:
    image: netboxcommunity/netbox:latest
    ports:
      - "8000:8080"
    environment:
      - SUPERUSER_API_TOKEN=your-secret-token
      - DB_HOST=postgres
      - DB_USER=netbox
      - DB_PASSWORD=netbox_password
      - REDIS_HOST=redis
    volumes:
      - netbox-media-files:/opt/netbox/netbox/media
      - netbox-reports:/etc/netbox/reports
      - netbox-scripts:/etc/netbox/scripts
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=netbox
      - POSTGRES_PASSWORD=netbox_password
      - POSTGRES_DB=netbox
    volumes:
      - netbox-postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redis_secret

volumes:
  netbox-media-files:
  netbox-reports:
  netbox-scripts:
  netbox-postgres-data:
```

After deploying NetBox, install the topology plugin:

```bash
# Inside the Netbox container or via custom Docker image
pip install netbox-topology-views

# Enable in configuration.py
PLUGINS = ["netbox_topology_views"]

# Restart Netbox to load the plugin
```

### GitHub Stats

| Metric | NetBox | netbox-topology-views |
|--------|--------|----------------------|
| Stars | 18,000+ | 350+ |
| Language | Python/Django | Python |
| Last Updated | Active (2026) | Active (2026) |

## LibreNMS — Auto-Discovered Network Topology

LibreNMS is a fully-featured network monitoring system that automatically discovers network topology using industry-standard protocols (LLDP, CDP, OSPF, BGP, ARP). Unlike NetBox's manually-defined approach, LibreNMS builds topology maps by querying your network devices directly.

### How Auto-Discovery Works

LibreNMS discovers topology through multiple protocols:

- **LLDP (Link Layer Discovery Protocol)**: Layer 2 neighbor discovery
- **CDP (Cisco Discovery Protocol)**: Cisco's proprietary neighbor discovery
- **OSPF/BGP**: Routing protocol neighbor relationships
- **ARP tables**: Layer 2/Layer 3 mappings
- **FDP (Foundry Discovery Protocol)**: Extreme Networks discovery

```bash
# LibreNMS topology discovery is automatic once devices are added
# Enable the topology view in the web UI:
# Settings > Topology > Enable

# Or via API:
curl -s -H "X-Auth-Token: YOUR_API_TOKEN" \
  "https://librenms.example.com/api/v0/topology" | python3 -m json.tool
```

### Docker Compose Deployment

```yaml
version: '3.8'
services:
  librenms:
    image: librenms/librenms:latest
    ports:
      - "8080:80"
      - "514:514/udp"
    environment:
      - DB_HOST=librenms-db
      - DB_NAME=librenms
      - DB_USER=librenms
      - DB_PASSWORD=librenms_password
      - TZ=UTC
    volumes:
      - librenms-data:/data
      - librenms-rrd:/opt/librenms/rrd
    depends_on:
      - librenms-db
      - redis

  librenms-db:
    image: mariadb:10.11
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=librenms
      - MYSQL_USER=librenms
      - MYSQL_PASSWORD=librenms_password
    volumes:
      - librenms-mysql-data:/var/lib/mysql

  redis:
    image: redis:7-alpine

  dispatcher:
    image: librenms/librenms:latest
    command: /opt/librenms/docker/dispatcher.php
    depends_on:
      - librenms-db
      - redis

volumes:
  librenms-data:
  librenms-rrd:
  librenms-mysql-data:
```

## Dedicated Network Mapping Tools

For teams that need real-time topology discovery without full monitoring or documentation overhead, dedicated network mapping tools provide focused functionality:

| Tool | Description | Protocol | Docker |
|------|-------------|----------|--------|
| **InterMapper** | Commercial, real-time network mapping | SNMP | No |
| **NetBrain** | Enterprise network automation | Multi | No |
| **Documap** | Open-source SNMP-based mapper | SNMP | Yes |
| **Network Navigator** | Lightweight topology explorer | LLDP/CDP | Yes |

### Simple SNMP-Based Mapper

For a lightweight approach, you can build a basic topology mapper using Python and SNMP:

```python
#!/usr/bin/env python3
"""Simple network topology discovery via SNMP LLDP."""
import subprocess
import json

def get_lldp_neighbors(host, community="public"):
    """Fetch LLDP neighbor table via SNMP."""
    result = subprocess.run(
        ["snmpwalk", "-v2c", "-c", community, host, "1.0.8802.1.1.2.1.4.1.1.9"],
        capture_output=True, text=True, timeout=10
    )
    
    neighbors = []
    for line in result.stdout.strip().split("\n"):
        if line:
            parts = line.split("=")
            if len(parts) == 2:
                neighbors.append(parts[1].strip())
    return neighbors

def build_topology_map(devices):
    """Build a network topology map from LLDP data."""
    topology = {"nodes": [], "links": []}
    
    for device in devices:
        neighbors = get_lldp_neighbors(device)
        topology["nodes"].append({"id": device, "type": "switch"})
        
        for neighbor in neighbors:
            topology["links"].append({
                "source": device,
                "target": neighbor,
                "type": "lldp"
            })
    
    return topology
```

## When to Choose Each Approach

| Scenario | Recommended |
|----------|-------------|
| Need source-of-truth + visual maps | NetBox + topology plugin |
| Want auto-discovery from live devices | LibreNMS topology |
| Real-time monitoring with topology | LibreNMS |
| Simple topology visualization | Dedicated mapper |
| Documentation-heavy environment | NetBox (manual but accurate) |
| Dynamic/changing network | LibreNMS (auto-updating) |

## For Related Reading

For a complete network management stack, see our other guides:

- [IPAM Solutions](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/) — phpIPAM vs NIPAP vs NetBox for IP address management
- [Network Simulation](../2026-04-18-gns3-vs-eve-ng-vs-containerlab-self-hosted-network-simulation-2026/) — GNS3 vs EVE-NG vs ContainerLab for network testing
- [Network Scanning](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) — Nmap vs Masscan vs RustScan for network discovery


## Network Topology Best Practices

Building an accurate network topology map requires more than just running a discovery tool. Following these practices ensures your topology data remains reliable and actionable over time.

**Maintain a source of truth**: Whether you use NetBox or another documentation system, ensure there is a single authoritative source for network device inventory. Auto-discovered data from monitoring tools should complement — not replace — this source of truth. When discrepancies arise between discovered topology and documented topology, investigate immediately as they often indicate unauthorized changes or misconfigurations.

**Document circuit and provider connections**: Physical connectivity to ISPs and WAN providers is often overlooked in topology maps. Record circuit IDs, provider contact information, and SLA terms alongside your topology data. When an outage occurs, having this information readily available reduces mean time to resolution significantly.

**Validate discovery data regularly**: Auto-discovered topology from LLDP and CDP can contain stale entries from disconnected devices or misconfigured neighbors. Schedule periodic audits comparing your discovered topology against physical documentation and routing tables.

**Use topology data for capacity planning**: Network maps reveal traffic patterns, bottlenecks, and single points of failure. Use this data to plan upgrades before outages occur. Tools like LibreNMS can overlay traffic utilization on topology maps, highlighting saturated links that need bandwidth upgrades.

For network security, see our [network scanning tools guide](../2026-04-22-nmap-vs-masscan-vs-rustscan-self-hosted-network-scanning-guide-2026/) covering Nmap, Masscan, and RustScan.

## FAQ

### What is network topology mapping?

Network topology mapping is the process of discovering and visualizing how network devices (routers, switches, firewalls, servers) are interconnected. It produces a diagram showing physical and logical connections, including which switch ports connect to which devices, VLAN assignments, and routing relationships.

### What's the difference between NetBox and LibreNMS for topology?

NetBox is a documentation tool — you manually define your infrastructure (devices, connections, circuits) and generate topology views from that data. LibreNMS is a monitoring tool that auto-discovers topology by querying live devices via LLDP, CDP, and SNMP. NetBox gives you accuracy through manual control; LibreNMS gives you real-time accuracy through automation.

### Which discovery protocol is most reliable for network topology?

LLDP (Link Layer Discovery Protocol) is the most widely supported and reliable protocol for topology discovery. It's an IEEE standard supported by virtually all modern switches, routers, and many servers. CDP is Cisco-specific and only works on Cisco and some HP/Aruba devices. For comprehensive discovery, enable both LLDP and CDP where possible.

### Can NetBox automatically discover network topology?

NetBox itself does not auto-discover topology — it's designed as a source-of-truth system where data is manually entered or imported. However, the netbox-topology-views plugin can generate visual maps from the connection data you've recorded, and third-party scripts can import LLDP/CDP data into NetBox via its API.

### Does LibreNMS support BGP and OSPF topology?

Yes, LibreNMS can discover and visualize BGP peer relationships and OSPF neighbor adjacencies in addition to Layer 2 LLDP/CDP topology. This makes it suitable for mapping both physical connectivity and logical routing relationships in enterprise networks.

### How do I visualize network topology without a dedicated tool?

For small networks, you can use SNMP tools like `snmpwalk` to query LLDP/CDP tables from switches and build simple scripts to parse the output. For larger networks, tools like LibreNMS or NetBox with topology plugins provide automated visualization with minimal setup effort.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Topology Mapping — NetBox, LibreNMS & Auto-Discovery Tools",
  "description": "Compare self-hosted network topology mapping solutions. Learn how NetBox, LibreNMS, and dedicated tools auto-discover and visualize your network infrastructure.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
