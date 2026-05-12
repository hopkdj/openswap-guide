---
title: "Self-Hosted Network Verification: Batfish vs Suzieq vs NAPALM (2026)"
date: "2026-05-12"
tags: ["networking", "network-verification", "batfish", "network-automation", "napalm", "network-observability"]
draft: false
---

Network configuration errors are the leading cause of outages in enterprise infrastructure. A single misconfigured access control list (ACL), routing loop, or VLAN mismatch can take down entire services. Traditional network management relies on manual review, CLI commands, and reactive troubleshooting — processes that are slow, error-prone, and don't scale.

**Network verification** tools proactively analyze network configurations to find bugs, validate policies, and guarantee correctness before changes reach production. In this guide, we compare three leading open-source tools for self-hosted network verification and analysis: [Batfish](https://www.batfish.org/), [Suzieq](https://github.com/netenglabs/suzieq), and [NAPALM](https://napalm.readthedocs.io/).

## Comparison Table

| Feature | Batfish | Suzieq | NAPALM |
|---|---|---|---|
| **GitHub Stars** | 7,200+ | 870+ | 2,450+ |
| **Primary Function** | Configuration analysis | Network observability | Multi-vendor automation |
| **Language** | Java/Python | Python | Python |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Vendor Support** | 10+ vendors (Cisco, Arista, Juniper, F5, etc.) | Multi-vendor (via parsers) | 15+ vendors (broadest support) |
| **Analysis Type** | Pre-deployment (static) | Post-deployment (runtime state) | Pre/post-deployment (automation) |
| **Policy Validation** | Yes (ACL, routing, reachability) | Yes (via queries) | Via custom scripts |
| **What-If Analysis** | Yes (simulate changes before applying) | No | No |
| **Data Collection** | Config file ingestion | Agent/CLI polling | Direct device API/SSH |
| **Docker Support** | Official Docker images | Official Docker images | No official image (library) |
| **Best For** | Pre-deployment config validation | Runtime network observability | Multi-vendor config automation |

## What Is Network Verification?

Network verification is the process of mathematically or programmatically proving that a network's configuration and runtime state satisfy specific requirements. Unlike traditional monitoring (which tells you when something is broken), verification tells you **before** you deploy whether a change will break something.

There are three main approaches:

1. **Static analysis** — Parse configuration files and build a mathematical model of the network. Analyze the model for policy violations, routing loops, and reachability issues. This is what Batfish does.

2. **Runtime observability** — Poll devices for their current state (routing tables, ARP entries, interface status) and compare against expected baselines. Detect drifts and anomalies in real time. This is what Suzieq does.

3. **Configuration automation** — Use vendor-agnostic APIs to read, modify, and validate device configurations programmatically. Ensure consistency across multi-vendor environments. This is what NAPALM does.

## Batfish: Pre-Deployment Configuration Analysis

[Batfish](https://github.com/batfish/batfish), developed by Intentionet and now a Linux Foundation Networking project, is the most comprehensive open-source network configuration analysis tool. It parses configurations from 10+ vendors, builds a complete data-plane model of the network, and answers questions about reachability, routing, ACL compliance, and more.

### Key Features

- **Vendor-agnostic parsing**: Supports Cisco IOS/NX-OS/ASA/XR, Arista EOS, Juniper Junos, F5 BIG-IP, Palo Alto PAN-OS, Cumulus Linux, and more.
- **What-if analysis**: Simulate configuration changes before applying them. Answer questions like "Will this ACL change block legitimate traffic?" or "Does this new route create a loop?"
- **Policy validation**: Define network policies (e.g., "Database servers should only be reachable from the app tier") and verify all configurations comply.
- **Docker-native**: Runs as a Docker container with a Python client library (`pybatfish`) for querying.
- **Mathematical guarantees**: Uses SMT (Satisfiability Modulo Theories) solvers to provide formal guarantees about network behavior.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  batfish:
    image: batfish/batfish:latest
    ports:
      - "9997:9997"
      - "9996:9996"
    environment:
      - BATFISH_ARGS=-Dlogback.configurationFile=/logback.xml
    volumes:
      - batfish-data:/data
    restart: unless-stopped

  batfish-query:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./batfish-scripts:/app
    command: bash -c "pip install pybatfish && python verify_network.py"
    depends_on:
      - batfish

volumes:
  batfish-data:
```

Python verification script (`verify_network.py`):
```python
from pybatfish.client.session import Session

bf = Session(host="batfish")
bf.set_network("my-network")
bf.init_snapshot("configs/", name="snapshot-1")
bf.load_snapshot()

# Check for undefined references
undef = bf.q.undefinedReferences().answer()
print("Undefined references:", undef)

# Verify reachability between subnets
reach = bf.q.reachability(
    headers={"srcIps": "10.0.1.0/24", "dstIps": "10.0.2.0/24"}
).answer()
print("Reachability result:", reach)

# Find routing loops
loops = bf.q.routes(network="10.0.0.0/8", rib="MAIN").answer()
print("Routes:", loops)
```

### Installation

```bash
# Run with Docker (recommended)
docker run -d -p 9997:9997 -p 9996:9996 batfish/batfish:latest

# Install Python client
pip install pybatfish

# Collect configs from devices (example: Cisco IOS)
scp router@device:/running-config.cfg ./configs/router1.cfg
```

## Suzieq: Real-Time Network Observability

[Suzieq](https://github.com/netenglabs/suzieq), developed by Network to Code, is a network observability platform that collects state from network devices and provides a unified query interface for analyzing the data. Unlike Batfish (which analyzes configurations), Suzieq collects **runtime state** — routing tables, BGP sessions, interface counters, ARP entries — and lets you query it like a database.

### Key Features

- **Real-time state collection**: Polls devices via eBGP, NETCONF, CLI, or REST APIs to collect current operational state.
- **Unified query language**: Query network state with a SQL-like interface. "Show me all BGP sessions that are down" or "Which interfaces have errors?"
- **Time-series analysis**: Store historical state and compare across time. Detect when a routing change occurred and what the previous state was.
- **Multi-vendor support**: Works with Cisco, Arista, Juniper, Cumulus, and other platforms through protocol-agnostic collectors.
- **Docker deployment**: Runs as a Docker container with a web UI and REST API.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  suzieq:
    image: netenglabs/suzieq:latest
    ports:
      - "8000:8000"
    environment:
      - SQ_POLLING_INTERVAL=300
    volumes:
      - ./suzieq-cfg:/etc/suzieq
      - suzieq-data:/parquet
    restart: unless-stopped

  suzieq-dashboard:
    image: netenglabs/suzieq-dashboard:latest
    ports:
      - "8501:8501"
    environment:
      - SQ_SERVER=host.docker.internal:8000
    depends_on:
      - suzieq

volumes:
  suzieq-data:
```

Suzieq configuration (`suzieq-cfg/suzieq-cfg.yml`):
```yaml
service:
  all:
    back-end: parquet
  snmp:
    vrf: mgmt
    username: snmp-user
    password: changeme
  http:
    enable-https: false
    port: 8000
devices:
  - name: router1
    platform: cumulus-linux
    ip-address: 10.0.1.1
  - name: switch1
    platform: arista-eos
    ip-address: 10.0.1.2
```

### Installation

```bash
# Docker installation (recommended)
docker pull netenglabs/suzieq:latest
docker pull netenglabs/suzieq-dashboard:latest

# Or install via pip
pip install suzieq

# CLI usage
sqpoller --config suzieq-cfg.yml
sqsh  # Interactive shell
```

## NAPALM: Multi-Vendor Network Automation

[NAPALM](https://github.com/napalm-automation/napalm) (Network Automation and Programmability Abstraction Layer with Multivendor support) is a Python library that provides a unified API for interacting with network devices from different vendors. It abstracts vendor-specific CLI commands and APIs into a common interface, enabling consistent configuration management across multi-vendor environments.

### Key Features

- **Vendor abstraction**: Single API for Cisco IOS/NX-OS, Juniper Junos, Arista EOS, Nokia SR OS, Huawei VRP, and 15+ other platforms.
- **Configuration management**: Get running/startup configs, compare configs, commit/rollback changes, and validate configuration compliance.
- **State retrieval**: Unified getters for interfaces, BGP neighbors, LLDP neighbors, NTP servers, SNMP configuration, and more.
- **Validation framework**: Define YAML validation files that specify expected network state, then validate actual state against them.
- **Integration-ready**: Works with Ansible, SaltStack, and custom Python scripts.

### Docker Compose Configuration

NAPALM is a Python library, not a server, so it runs inside your automation container:

```yaml
version: "3.8"
services:
  network-automation:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - ./automation:/app
    command: bash -c "pip install napalm && python validate_network.py"
    environment:
      - NAPALM_USERNAME=admin
      - NAPALM_PASSWORD=changeme
```

NAPALM validation script (`validate_network.py`):
```python
from napalm import get_network_driver
import json

driver = get_network_driver("eos")  # Arista EOS
device = driver("10.0.1.1", "admin", "changeme")
device.open()

# Get interface status
interfaces = device.get_interfaces()
print(json.dumps(interfaces, indent=2))

# Compare running vs startup config
running = device.get_config(retrieve="running")
startup = device.get_config(retrieve="startup")
if running != startup:
    print("WARNING: Running config differs from startup config!")

# Validate BGP neighbors
bgp = device.get_bgp_neighbors()
for vrf, data in bgp.items():
    for peer, info in data["peers"].items():
        if not info["is_up"]:
            print(f"BGP peer {peer} is DOWN")

device.close()
```

### Installation

```bash
pip install napalm

# Platform-specific drivers (included)
# eos (Arista), ios (Cisco IOS), iosxr (Cisco XR), junos (Juniper),
# nxos (Cisco NX-OS), nxos_ssh (Cisco NX-OS via SSH),
# vyos (VyOS), frr (FRRouting), ros (RouterOS)
```

## Performance and Scalability

| Metric | Batfish | Suzieq | NAPALM |
|---|---|---|---|
| **Analysis Speed** | 100-500 devices per minute (config parsing) | 50-200 devices per polling cycle | 10-50 devices per concurrent session |
| **Memory Usage** | 4-8 GB for 1000-device networks | 2-4 GB (Parquet storage) | Minimal (client library only) |
| **Storage** | Configuration snapshots (~1 MB per device) | Time-series state data (~10 MB per device per day) | None (stateless library) |
| **Concurrent Devices** | Unlimited (batch processing) | ~500 per poller instance | Depends on SSH/API rate limits |

## Why Self-Host Network Verification?

Network verification tools are critical infrastructure for organizations managing their own data centers, campus networks, or cloud infrastructure. Self-hosting these tools provides:

**Complete data privacy**: Network configurations contain sensitive information about your infrastructure topology, IP addressing, security policies, and vendor relationships. Cloud-based network analysis services require uploading this data to third-party servers. Self-hosting keeps all configuration data within your network perimeter.

**Offline analysis**: During incidents or maintenance windows, internet connectivity may be limited or intentionally disabled. Self-hosted tools work entirely offline.

**Integration with internal systems**: Self-hosted tools integrate with your existing CI/CD pipelines, ticketing systems, and monitoring dashboards via local APIs — no external network dependencies.

**Cost predictability**: Cloud network management services charge per device, per API call, or per analysis run. Self-hosted tools have predictable infrastructure costs that don't scale with network size.

For related reading, see our [network configuration management guide](../2026-05-05-self-hosted-network-configuration-management-ansible-nornir-netbox-guide/) and [IPAM tools comparison](../2026-04-20-phpipam-vs-nipap-vs-netbox-self-hosted-ipam-guide-2026/).

If you're building network monitoring pipelines, check our [log forwarding comparison](../2026-05-09-self-hosted-log-forwarding-fluent-bit-vector-otel-collector-guide/) for observability data collection patterns.

## FAQ

### What is the difference between Batfish and traditional network monitoring?

Traditional network monitoring tools (like Nagios or Zabbix) alert you when a device goes down or a metric exceeds a threshold. Batfish analyzes configuration files to predict problems before they happen. For example, Batfish can tell you that a proposed ACL change will block legitimate traffic, or that a routing configuration creates a black hole — issues that monitoring tools would only detect after the change causes an outage.

### Can Suzieq replace SNMP monitoring?

Suzieq complements rather than replaces SNMP monitoring. SNMP provides real-time metrics (CPU, memory, interface counters) at high frequency. Suzieq collects structured operational state (routing tables, BGP sessions, ARP entries) at lower frequency but with much richer context. Use SNMP for performance monitoring and Suzieq for state verification and troubleshooting.

### Is NAPALM a replacement for Ansible network modules?

NAPALM and Ansible serve different purposes. NAPALM is a Python library that provides a vendor-agnostic API for network device interaction. Ansible is an orchestration tool that can use NAPALM as a backend (via the `napalm_get` and `napalm_configure` modules) or its own native network modules. NAPALM gives you programmatic access; Ansible gives you declarative automation. They work best together.

### Does Batfish support cloud network verification?

Batfish primarily analyzes traditional network device configurations (routers, switches, firewalls, load balancers). It does not natively parse cloud provider configurations (AWS VPC, Azure NSG, GCP firewall rules). However, you can export cloud network configurations to vendor-neutral formats and analyze them with Batfish using custom parsers.

### How often should I run network verification?

For Batfish (static analysis): run before every configuration change, as part of your CI/CD pipeline for network changes. For Suzieq (runtime observability): poll every 5-15 minutes for production networks, every 1-5 minutes for critical infrastructure. For NAPALM validation: run after every configuration deployment to verify the change was applied correctly.

### Can I use these tools together?

Yes, they are complementary. A typical workflow: use NAPALM to deploy configuration changes across multi-vendor devices, run Batfish to verify the new configuration is correct before committing, and use Suzieq to monitor the runtime state and detect any deviations from expected behavior. This provides end-to-end verification from configuration to deployment to operation.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Verification: Batfish vs Suzieq vs NAPALM (2026)",
  "description": "Compare Batfish, Suzieq, and NAPALM for self-hosted network verification, observability, and multi-vendor automation.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
