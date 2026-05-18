---
title: "Self-Hosted STP/RSTP Network Monitoring: LibreNMS vs OpenNMS vs SNMP-Based Solutions"
date: "2026-05-18"
tags: ["stp", "rstp", "network-monitoring", "snmp", "switch-management", "librenms"]
draft: false
---

Spanning Tree Protocol (STP) and its rapid variant (RSTP) prevent network loops in switched Ethernet environments. When STP misconfigures or fails, broadcast storms can bring down entire networks. Monitoring STP state changes, root bridge elections, and port transitions is critical for network stability, yet many organizations lack visibility into their spanning tree topology.

In this guide, we compare three approaches to self-hosted STP/RSTP monitoring: **LibreNMS**, **OpenNMS**, and **SNMP-based custom monitoring** using Python and NET-SNMP tools.

## Comparison Overview

| Feature | LibreNMS | OpenNMS | SNMP Custom (Python) |
|---|---|---|---|
| Stars | 3,000+ | 1,000+ | N/A (std libraries) |
| Language | PHP/JS | Java | Python |
| Last Updated | May 2026 | May 2026 | Always current |
| STP Monitoring | Built-in via SNMP | Built-in via SNMP | Custom scripts |
| Topology Map | Auto-discovery | Auto-discovery | Custom |
| Alerting | Email, Slack, webhook | Email, webhook | Custom handlers |
| Protocol Support | STP, RSTP, MSTP | STP, RSTP, MSTP | Any via SNMP OID |
| Dashboard | Web UI | Web UI | CLI or custom web |
| Docker Support | Official image | Official image | Custom Dockerfile |
| Best For | Mid-size networks | Enterprise networks | Custom integrations |

## LibreNMS

**GitHub:** [librenms/librenms](https://github.com/librenms/librenms) (3,000+ stars)

LibreNMS is a comprehensive network monitoring platform with automatic discovery, alerting, and extensive protocol support. Its STP monitoring capabilities come from SNMP polling of standard bridge MIBs, providing topology visualization and state change alerting.

### Key Features

- **Auto-discovery** - Automatically finds and maps network devices
- **STP visualization** - Root bridge identification and port state display
- **Alert templates** - Pre-built alerts for STP topology changes
- **Historical data** - STP state change timeline and trend analysis
- **Multi-vendor** - Support for Cisco, Juniper, Arista, HP, and more
- **Extensible** - Custom polling scripts and API integrations

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  librenms:
    image: librenms/librenms:latest
    container_name: librenms
    hostname: librenms
    domainname: monitoring.local
    cap_add:
      - NET_ADMIN
    networks:
      monitoring:
        ipv4_address: 10.10.0.10
    volumes:
      - ./librenms:/data
      - ./snmpd.conf:/etc/snmp/snmpd.conf:ro
    environment:
      - TZ=UTC
      - DB_HOST=librenms-db
      - DB_NAME=librenms
      - DB_USER=librenms
      - DB_PASSWORD=librenms_pass
      - BASE_URL=http://librenms.local
    depends_on:
      - librenms-db
      - redis
    restart: unless-stopped

  librenms-db:
    image: mariadb:10.11
    container_name: librenms-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_pass
      - MYSQL_DATABASE=librenms
      - MYSQL_USER=librenms
      - MYSQL_PASSWORD=librenms_pass
    volumes:
      - ./mysql:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: librenms-redis
    restart: unless-stopped

networks:
  monitoring:
    driver: bridge
    ipam:
      config:
        - subnet: 10.10.0.0/24
```

### STP Monitoring Configuration

```bash
# Enable SNMP on switch (Cisco example)
snmp-server community STP-MONITOR ro
snmp-server enable traps bridge
snmp-server host 10.10.0.10 version 2c STP-MONITOR

# LibreNMS STP OIDs monitored
# BRIDGE-MIB::dot1dStpRootBridge (root bridge MAC)
# BRIDGE-MIB::dot1dStpRootCost (root path cost)
# BRIDGE-MIB::dot1dStpTopChange (topology change counter)
# BRIDGE-MIB::dot1dStpPortState (per-port STP state)
```

## OpenNMS

**GitHub:** [OpenNMS/opennms](https://github.com/OpenNMS/opennms) (1,000+ stars)

OpenNMS is an enterprise-grade network management platform with deep protocol support and scalable monitoring architecture. Its STP/RSTP monitoring leverages SNMP data collection, event correlation, and notification systems.

### Key Features

- **Enterprise scalability** - Monitor thousands of devices
- **Event correlation** - Correlate STP events across switches
- **Service assurance** - Track impact of STP changes on services
- **Flow monitoring** - NetFlow, sFlow, and IPFIX integration
- **Provisioning** - Automatic device provisioning and discovery
- **High availability** - Active-active clustering support

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  opennms:
    image: opennms/horizon:latest
    container_name: opennms
    hostname: opennms
    environment:
      - OPENNMS_DB_HOST=opennms-db
      - OPENNMS_DB_NAME=opennms
      - OPENNMS_DB_USER=opennms
      - OPENNMS_DB_PASSWORD=opennms_pass
    volumes:
      - ./opennms-data:/opt/opennms/data
      - ./opennms-etc:/opt/opennms/etc
    ports:
      - "8980:8980"
    depends_on:
      - opennms-db
    restart: unless-stopped

  opennms-db:
    image: postgres:15
    container_name: opennms-db
    environment:
      - POSTGRES_DB=opennms
      - POSTGRES_USER=opennms
      - POSTGRES_PASSWORD=opennms_pass
    volumes:
      - ./pgdata:/var/lib/postgresql/data
    restart: unless-stopped
```

### STP Event Configuration

```xml
<!-- opennms-eventd-configuration.xml -->
<!-- STP topology change event definition -->
<event>
  <uei>uei.opennms.org/vendor/ietf/bridge/topologyChange</uei>
  <event-label>STP Topology Change Detected</event-label>
  <descr>A spanning tree topology change was detected on a monitored switch.</descr>
  <severity>Warning</severity>
  <logmsg dest="logndisplay">STP topology change detected</logmsg>
</event>

<!-- Notification for STP events -->
<notification name="STP-Topology-Change" status="on">
  <uei>uei.opennms.org/vendor/ietf/bridge/topologyChange</uei>
  <rule>(IPADDR IPLIKE *.*.*.*)</rule>
  <destinationPath>Email-Admin</destinationPath>
  <text-message>STP topology change on %parm[node]% at %parm[ip]%</text-message>
</notification>
```

## SNMP-Based Custom Monitoring

When commercial monitoring platforms are too heavy for your needs, Python with NET-SNMP provides a lightweight, customizable approach to STP monitoring.

### Key SNMP OIDs for STP Monitoring

| OID | Description | MIB |
|---|---|---|
| dot1dStpRootBridge | Root bridge MAC address | BRIDGE-MIB |
| dot1dStpRootCost | Root path cost | BRIDGE-MIB |
| dot1dStpTopChange | Topology change counter | BRIDGE-MIB |
| dot1dStpPortState | Port state (1=disabled, 2=blocking, 3=listening, 4=learning, 5=forwarding) | BRIDGE-MIB |
| dot1dStpPortPriority | Port priority | BRIDGE-MIB |
| dot1dStpProtocolSpecification | Protocol version (0=STP, 1=RSTP, 2=MSTP) | BRIDGE-MIB |

### Python STP Monitor Script

```python
#!/usr/bin/env python3
import subprocess
import json
import time
import sys

BRIDGE_MIB = "1.3.6.1.2.1.17.2"

def snmp_walk(host, community, oid):
    """Walk an SNMP OID on the target device."""
    cmd = ["snmpwalk", "-v2c", "-c", community, host, oid]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip()

def parse_stp_root(output):
    """Parse the root bridge MAC from SNMP output."""
    if not output:
        return None
    for line in output.split("
"):
        if "Hex-STRING" in line:
            hex_val = line.split("Hex-STRING:")[1].strip().replace(" ", "").lower()
            mac = ":".join(hex_val[i:i+2] for i in range(0, len(hex_val), 2))
            return mac
    return None

def check_stp_topology(switches):
    """Check STP topology across all switches."""
    results = {}
    for switch in switches:
        host = switch["host"]
        community = switch.get("community", "public")

        root = snmp_walk(host, community, f"{BRIDGE_MIB}.1.0")
        top_changes = snmp_walk(host, community, f"{BRIDGE_MIB}.5.0")
        protocol = snmp_walk(host, community, f"{BRIDGE_MIB}.7.0")

        results[host] = {
            "root_bridge": parse_stp_root(root),
            "topology_changes": top_changes,
            "protocol": protocol,
            "timestamp": time.time()
        }
    return results

def main():
    switches = [
        {"host": "192.168.1.1", "community": "STP-MONITOR"},
        {"host": "192.168.1.2", "community": "STP-MONITOR"},
        {"host": "192.168.1.3", "community": "STP-MONITOR"},
    ]

    topology = check_stp_topology(switches)

    # Check for root bridge consistency
    roots = set()
    for host, data in topology.items():
        if data["root_bridge"]:
            roots.add(data["root_bridge"])

    if len(roots) > 1:
        print(f"ALERT: Multiple root bridges detected: {roots}")
        sys.exit(1)

    # Check for recent topology changes
    for host, data in topology.items():
        if data["topology_changes"]:
            print(f"Switch {host}: {data['topology_changes']} topology changes")

    print(json.dumps(topology, indent=2))

if __name__ == "__main__":
    main()
```

### Docker Deployment for Custom Monitor

```yaml
version: "3.8"
services:
  stp-monitor:
    build: .
    container_name: stp-monitor
    volumes:
      - ./monitor.py:/app/monitor.py:ro
      - ./config.json:/app/config.json:ro
    environment:
      - MONITOR_INTERVAL=300
      - ALERT_WEBHOOK=https://hooks.example.com/alerts
    restart: unless-stopped
```

## Choosing the Right STP Monitoring Approach

| Use Case | Recommended Tool |
|---|---|
| Mid-size network (50-500 devices) | LibreNMS |
| Enterprise network (500+ devices) | OpenNMS |
| Lightweight/Custom integration | SNMP + Python |
| Auto-discovery needed | LibreNMS or OpenNMS |
| Event correlation | OpenNMS |
| API-driven monitoring | SNMP + Python |
| Historical STP trends | LibreNMS |
| Multi-root detection | SNMP + Python (custom logic) |

## Why Self-Host STP Monitoring?

Spanning tree loops are one of the most common causes of network outages in switched environments. When a topology change occurs, having immediate visibility into which switch initiated the change, which port transitioned, and how the root bridge was affected is essential for rapid troubleshooting. Self-hosted STP monitoring keeps all network topology data within your infrastructure, avoiding the latency and data exposure risks of cloud-based monitoring services.

For organizations with multi-vendor switch environments, LibreNMS provides the broadest device support with minimal configuration. Its auto-discovery automatically maps STP relationships between switches, identifying root bridges and forwarding paths without manual intervention.

For enterprise-scale deployments, OpenNMS event correlation engine can detect cascading STP failures across multiple switches, correlating topology changes with service impact data to prioritize alerts and automate remediation workflows.

For teams with specific monitoring requirements or integration needs, custom SNMP-based monitoring using Python provides complete control over data collection, alerting logic, and integration with existing toolchains.

For network discovery agents, see our [LLDP vs SNMP vs ARP guide](../2026-05-13-self-hosted-network-discovery-agents-lldpd-snmp-arp-scan-guide/). For network topology discovery, our [CDPWalker vs FlashRoute comparison](../2026-05-13-self-hosted-network-topology-discovery-cdpwalker-flashroute-treenet-guide/) covers automated mapping. For LLDP management, check our [LLPD vs FRR vs Netdisco guide](../2026-05-11-self-hosted-lldp-network-discovery-lldpd-frr-netdisco/).

## FAQ

### What is STP and why should I monitor it?

Spanning Tree Protocol (STP) prevents network loops by blocking redundant paths in switched Ethernet networks. When STP fails or is misconfigured, broadcast storms can consume all available bandwidth and bring down entire networks. Monitoring STP gives you visibility into root bridge elections, port state transitions, and topology changes, enabling rapid detection and resolution of loop conditions before they impact users.

### What is the difference between STP, RSTP, and MSTP?

STP (802.1D) is the original spanning tree protocol with 30-50 second convergence times. RSTP (802.1w) is Rapid STP, reducing convergence to 1-2 seconds through proactive port state management. MSTP (802.1s) is Multiple STP, allowing multiple spanning tree instances per VLAN for optimized traffic engineering. All three use the same bridge MIB for SNMP monitoring, making them equally monitorable with the tools described in this guide.

### How do I detect STP loops before they cause outages?

Monitor topology change notifications (TCNs) as an early warning sign. Frequent TCNs indicate unstable links or flapping ports that may trigger a loop. Additionally, watch for root bridge changes: if the root bridge frequently changes, it suggests network instability. Tools like LibreNMS and OpenNMS can alert on TCN rate thresholds, while custom Python scripts can implement more sophisticated detection logic based on historical patterns.

### Can I monitor STP without SNMP?

SNMP is the standard protocol for STP monitoring because the BRIDGE-MIB provides standardized access to STP state data. Some vendors offer proprietary APIs or CLI access for STP information, but SNMP is universally supported across switch vendors. For environments where SNMP is not available, consider enabling NETCONF/YANG on modern switches as an alternative management protocol.

### How often should I poll STP data from switches?

For production monitoring, poll STP root bridge and topology change counters every 5 minutes. Poll port state data every 15 minutes to detect stuck blocking ports. During network maintenance or changes, increase polling frequency to every 1 minute for the affected switches. SNMP polling at these intervals has negligible impact on switch CPU and network bandwidth.

### What should I do when STP topology changes are detected?

First, identify the switch and port that triggered the change using your monitoring tool. Check for recent physical changes (cable reconnections, new devices). Verify that the new topology is intentional and not caused by a loop. If the change is unexpected, investigate the triggering port for issues (flapping link, misconfigured trunk, or unauthorized device connection). Document the change and update network documentation if the new topology is valid.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted STP/RSTP Network Monitoring: LibreNMS vs OpenNMS vs SNMP-Based Solutions",
  "description": "Compare LibreNMS, OpenNMS, and SNMP-based custom monitoring for self-hosted STP/RSTP network monitoring with Docker deployment guides.",
  "datePublished": "2026-05-18",
  "dateModified": "2026-05-18",
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
