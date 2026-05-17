---
title: "Self-Hosted SNMP Simulators & Agents — net-snmp vs snmpsim vs pysnmp"
date: "2026-05-18"
tags: ["snmp", "network-monitoring", "simulator", "self-hosted", "infrastructure"]
draft: false
---

## Introduction

Simple Network Management Protocol (SNMP) is the backbone of network monitoring. But developing and testing SNMP-based applications requires either live network devices — which are expensive and hard to scale — or **SNMP simulators** that emulate real devices in software.

In this guide, we compare three open-source SNMP tools that serve different roles in the SNMP ecosystem: **net-snmp** (the industry-standard SNMP toolkit), **snmpsim** (SNMP simulator for device emulation), and **pysnmp** (Python SNMP library for custom agent development).

## Quick Comparison

| Feature | net-snmp | snmpsim | pysnmp |
|---------|----------|---------|--------|
| Stars | 462+ | 448+ | 611+ |
| Last Updated | Apr 2026 | Jul 2023 | Jul 2024 |
| Language | C | Python | Python |
| Type | Full SNMP toolkit | SNMP simulator | SNMP library |
| SNMP Versions | v1, v2c, v3 | v1, v2c | v1, v2c, v3 |
| Agent Support | ✅ Full | ❌ Simulator only | ✅ Agent framework |
| Manager Support | ✅ Full | ❌ No | ✅ Full |
| Docker Image | Community | ✅ Official | ❌ Library |
| Simulation Data | N/A | ✅ Walk files | ❌ Custom code |
| Use Case | Monitoring/CLI | Device emulation | Custom development |

## net-snmp — The Industry-Standard SNMP Toolkit

[net-snmp](https://github.com/net-snmp/net-snmp) is the most widely deployed open-source SNMP implementation. It provides a complete suite of SNMP tools including agents, managers, libraries, and utilities — making it the foundation for SNMP monitoring on most Linux distributions.

### Key Features

- **Complete SNMP toolkit**: Includes snmpd (agent), snmpwalk/snmpget (manager tools), and libsnmp (C library)
- **Full SNMP v1/v2c/v3 support**: Including USM security model and view-based access control (VACM)
- **Extensible agent architecture**: Write custom MIB modules in C or shell scripts
- **Built-in monitoring**: CPU, memory, disk, network interfaces, and process monitoring out of the box
- **AgentX support**: Extend the agent with sub-agents using the AgentX protocol
- **Cross-platform**: Linux, BSD, macOS, Windows (via Cygwin)

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  snmpd:
    image: instrumentisto/snmpd:latest
    container_name: snmpd
    environment:
      - SNMP_COMMUNITY=public
    ports:
      - "161:161/udp"
    volumes:
      - ./snmpd.conf:/etc/snmp/snmpd.conf:ro
    restart: unless-stopped
```

### snmpd.conf Example

```conf
# Basic SNMP v2c configuration
rocommunity public 192.168.1.0/24

# System information
syslocation "Server Room, Rack 3"
syscontact admin@example.com

# Disk monitoring
disk / 10000
disk /var 5000

# Load average thresholds
load 12 10 5

# Process monitoring
proc nginx
proc sshd
```

### Installation

```bash
# Debian/Ubuntu — installs agent, tools, and libraries
sudo apt install snmp snmpd snmp-mibs-downloader

# Red Hat/CentOS
sudo yum install net-snmp net-snmp-utils

# Start the agent
sudo systemctl enable --now snmpd

# Test with snmpwalk
snmpwalk -v 2c -c public localhost
```

## snmpsim — SNMP Device Simulator

[snmpsim](https://github.com/etingof/snmpsim) is a powerful SNMP simulator that emulates the behavior of real network devices. It reads SNMP walk data from actual devices and replays it, making it indistinguishable from the real thing to any SNMP manager.

### Key Features

- **Realistic device emulation**: Uses actual SNMP walk data from real devices — routers, switches, servers, UPS units
- **Multiple transport protocols**: Supports SNMP over UDP, TCP, and Unix sockets
- **Data variation plugins**: Dynamically modify simulated values (counters, timestamps, random values)
- **SNMP v1 and v2c support**: Covers the most commonly used SNMP versions
- **Multi-agent simulation**: Simulate hundreds of devices on a single host
- **Walk file format**: Simple text-based format for defining simulated MIB data

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  snmpsim:
    image: etingof/snmpsim:latest
    container_name: snmpsim
    ports:
      - "1161:1161/udp"
    volumes:
      - ./data:/usr/local/share/snmpsim/variation
    command: ["--transport-id=0", "--agent-udpv4-endpoint=0.0.0.0:1161"]
    restart: unless-stopped
```

### Simulation Data File Example

```text
# router-walk.txt — SNMP walk data from a real Cisco router
1.3.6.1.2.1.1.1.0 -> Cisco IOS Software, C3750 Software
1.3.6.1.2.1.1.2.0 -> 1.3.6.1.4.1.9.1.484
1.3.6.1.2.1.1.3.0 -> 45623100
1.3.6.1.2.1.1.4.0 -> admin@example.com
1.3.6.1.2.1.1.5.0 -> cisco-switch-01
1.3.6.1.2.1.2.1.0 -> 48
1.3.6.1.2.1.2.2.1.1.1 -> 1
1.3.6.1.2.1.2.2.1.2.1 -> "GigabitEthernet1/0/1"
1.3.6.1.2.1.2.2.1.7.1 -> 1
1.3.6.1.2.1.2.2.1.8.1 -> 1
```

### Running the Simulator

```bash
# Install snmpsim
pip install snmpsim

# Generate walk data from a real device
snmpwalk -v 2c -c public 192.168.1.1 > cisco-router.txt

# Start the simulator with the walk data
snmpsimd.py --data-dir=. --agent-udpv4-endpoint=0.0.0.0:1025

# Query the simulated device
snmpwalk -v 2c -c public localhost:1025
```

## pysnmp — Python SNMP Library

[pysnmp](https://github.com/etingof/pysnmp) is a pure-Python SNMP library that provides both manager and agent functionality. It's ideal for building custom SNMP applications, writing monitoring scripts, or developing lightweight SNMP agents in Python.

### Key Features

- **Pure Python implementation**: No C dependencies, runs anywhere Python runs
- **Full SNMP v1/v2c/v3 support**: Including authentication (MD5, SHA) and encryption (DES, AES)
- **Manager and agent APIs**: Build both SNMP managers (pollers) and agents (servers)
- **Async I/O support**: Built-in asyncio compatibility for high-performance polling
- **MIB compiler**: Compiles ASN.1 MIB files to Python modules
- **Extensible architecture**: Easy to add custom MIB objects and handlers

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  snmp-agent:
    build: .
    container_name: pysnmp-agent
    ports:
      - "1161:1161/udp"
    restart: unless-stopped
```

### Custom SNMP Agent Example

```python
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp, context
from pysnmp.carrier.asyncore.dgram import udp

# Create SNMP engine
snmpEngine = engine.SnmpEngine()

# Transport setup
config.addTransport(
    snmpEngine,
    udp.domainName,
    udp.UdpTransport().openServerMode(('0.0.0.0', 1161))
)

# SNMPv2c setup
config.addV1System(snmpEngine, 'my-area', 'public')

# Register SNMP Apps
cmdrsp.GetCommandResponder(snmpEngine, context.SnmpContext(snmpEngine))
cmdrsp.SetCommandResponder(snmpEngine, context.SnmpContext(snmpEngine))
cmdrsp.NextCommandResponder(snmpEngine, context.SnmpContext(snmpEngine))

# Register MIB objects
from pysnmp.smi import builder, instrum
mibBuilder = snmpEngine.getMibBuilder()
mibInstrum = instrum.MibInstrumController(mibBuilder)

# Run forever
snmpEngine.transportDispatcher.jobStarted(1)
try:
    snmpEngine.transportDispatcher.runDispatcher()
except:
    snmpEngine.transportDispatcher.closeDispatcher()
    raise
```

### SNMP Manager (Poller) Example

```python
from pysnmp.hlapi import *

errorIndication, errorStatus, errorIndex, varBinds = next(
    getCmd(SnmpEngine(),
           CommunityData('public'),
           UdpTransportTarget(('192.168.1.1', 161)),
           ContextData(),
           ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0')),
           ObjectType(ObjectIdentity('1.3.6.1.2.1.1.3.0')))
)

if errorIndication:
    print(f'Error: {errorIndication}')
elif errorStatus:
    print(f'Error: {errorStatus.prettyPrint()}')
else:
    for varBind in varBinds:
        print(f'{varBind[0]} = {varBind[1]}')
```

### Installation

```bash
# Install pysnmp
pip install pysnmp

# For SNMPv3 support with stronger crypto
pip install pysnmp cryptography

# For MIB compilation
pip install pysnmp-mibs
```

## Choosing the Right SNMP Tool

| Use Case | Recommended Tool |
|----------|-----------------|
| Monitor Linux servers with SNMP | **net-snmp** — Full agent with built-in system monitoring |
| Test SNMP monitoring tools | **snmpsim** — Simulate hundreds of real devices |
| Build custom SNMP agents | **pysnmp** — Python library with agent framework |
| Develop SNMP managers/pollers | **pysnmp** — Async I/O support, full v3 security |
| CI/CD testing for network apps | **snmpsim** — Deterministic device simulation |
| Production SNMP infrastructure | **net-snmp** — Battle-tested, distribution-packaged |

## Why Self-Host Your SNMP Infrastructure?

Running your own SNMP agents and simulators rather than relying on vendor-provided tools offers several key advantages:

**Complete device simulation**: SNMP simulators let you test monitoring systems against hundreds of virtual devices — routers, switches, firewalls, servers — without purchasing physical hardware. This is essential for validating monitoring dashboards and alerting rules before deploying to production.

**Custom monitoring extensions**: With net-snmp's extensible agent architecture, you can expose any system metric via SNMP. Write a shell script or C module to monitor application-specific data and make it available to your existing SNMP-based monitoring stack (Zabbix, Nagios, LibreNMS).

**Development and testing isolation**: pysnmp lets you build and test SNMP applications entirely in software. Create custom agents, write polling scripts, and validate SNMPv3 security configurations — all without touching production network devices.

**Cost savings**: Commercial SNMP simulator licenses can cost thousands of dollars per year. Open-source alternatives like snmpsim provide comparable functionality at zero cost, with the added benefit of community-driven development and transparency.

**Full protocol support**: Open-source SNMP tools support the complete SNMP specification, including SNMPv3 with USM authentication and VACM access control — features that are often limited or expensive in vendor-provided simulators.

For related reading, see our [network flow analysis guide](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/) and [network performance measurement comparison](../2026-05-13-self-hosted-network-performance-measurement-perfspectrum-smokeping-mtr-guide/).

## FAQ

### What is SNMP and what is it used for?

SNMP (Simple Network Management Protocol) is a standard protocol for monitoring and managing network devices. It allows network management systems to query devices for information (CPU usage, interface status, disk space) and send configuration changes. SNMP is used by monitoring tools like Zabbix, Nagios, PRTG, and LibreNMS.

### What is the difference between net-snmp, snmpsim, and pysnmp?

**net-snmp** is a complete SNMP toolkit with agents and management tools. **snmpsim** is a device simulator that emulates real network equipment using recorded SNMP walk data. **pysnmp** is a Python library for building custom SNMP managers and agents. They serve different purposes: monitoring (net-snmp), testing (snmpsim), and development (pysnmp).

### Can snmpsim simulate SNMPv3 devices?

No, snmpsim currently supports SNMPv1 and SNMPv2c only. For SNMPv3 simulation, you would need to use net-snmp's snmpd with custom MIB configurations or build a custom agent using pysnmp.

### How do I capture SNMP walk data for simulation?

Use the `snmpwalk` command from net-snmp to capture walk data from a real device: `snmpwalk -v 2c -c public DEVICE_IP > device-walk.txt`. Then point snmpsim at the resulting file. The walk file contains OID-value pairs that snmpsim uses to respond to SNMP queries.

### Is pysnmp production-ready?

pysnmp is widely used in production for SNMP polling and custom agent development. However, the original author has indicated the project is in maintenance mode. For new projects requiring active development, consider also evaluating pysnmp-leo (a maintained fork) or alternative Python SNMP libraries.

### Can I use net-snmp to monitor Docker containers?

Yes. The net-snmp agent (snmpd) can be run inside Docker containers to expose container-specific metrics via SNMP. Alternatively, you can use the `instrumentisto/snmpd` Docker image, which runs snmpd as a container and exposes SNMP on port 161/udp.

### What are the security risks of running SNMP?

SNMPv1 and v2c transmit community strings (passwords) in plaintext. SNMPv3 addresses this with authentication (MD5/SHA) and encryption (DES/AES). Always use SNMPv3 in production, restrict access with firewall rules, and use non-default community strings for v2c deployments.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SNMP Simulators & Agents — net-snmp vs snmpsim vs pysnmp",
  "description": "Compare three open-source SNMP tools for self-hosted infrastructure: net-snmp (full toolkit), snmpsim (device simulator), and pysnmp (Python library). Includes Docker Compose configs and code examples.",
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
