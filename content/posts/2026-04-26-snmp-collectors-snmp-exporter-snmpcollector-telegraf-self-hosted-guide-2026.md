---
title: "Self-Hosted SNMP Collectors: snmp_exporter vs SNMPcollector vs Telegraf 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "monitoring", "snmp", "network"]
draft: false
description: "Compare three self-hosted SNMP collectors — Prometheus snmp_exporter, SNMPcollector, and Telegraf SNMP input — with Docker deployment guides, configuration examples, and performance benchmarks for 2026."
---

## Why Self-Host Your SNMP Data Collection

Simple Network Management Protocol (SNMP) remains the universal language for monitoring routers, switches, UPS systems, printers, servers, and industrial equipment. Whether you are tracking interface bandwidth on a core switch, monitoring temperature sensors in a data center, or collecting CPU and disk metrics from legacy servers, SNMP is the protocol that powers it all.

The challenge is turning raw SNMP OIDs into actionable, visualized metrics. Commercial network monitoring suites are expensive, vendor-locked, and often overkill for small-to-medium infrastructure teams. Self-hosted SNMP collectors fill this gap by providing open-source, Docker-deployable alternatives that integrate with popular time-series databases and visualization platforms.

This guide compares three leading self-hosted SNMP data collection tools: **Prometheus snmp_exporter**, **SNMPcollector**, and **Telegraf's SNMP input plugin**. Each has a distinct architecture and target use case, and the right choice depends on your existing monitoring stack.

For broader context on self-hosted network monitoring, see our [Zabbix vs LibreNMS vs Netdata comparison](../zabbix-vs-librenms-vs-netdata-network-monitoring-guide/) and [network discovery guide](../2026-04-25-netdisco-vs-librenms-vs-opennetadmin-network-discovery-guide-2026/).

## Overview of the Three SNMP Collectors

| Feature | Prometheus snmp_exporter | SNMPcollector | Telegraf (SNMP input) |
|---|---|---|---|
| **GitHub Stars** | 2,103 | 304 | 16,852 |
| **Language** | Go | Go | Go |
| **Last Updated** | April 2026 | December 2023 | April 2026 |
| **Data Backend** | Prometheus | InfluxDB | Multiple (InfluxDB, Prometheus, etc.) |
| **Web UI** | No | Yes (built-in) | No |
| **SNMP Versions** | v1, v2c, v3 | v1, v2c, v3 | v1, v2c, v3 |
| **MIB Translation** | Generator tool required | Built-in | Gosmi/netsnmp |
| **Deployment** | Docker, binary | Docker, binary | Docker, binary, package |
| **License** | Apache 2.0 | Apache 2.0 | MIT |
| **Best For** | Prometheus users | InfluxDB users, GUI lovers | Multi-destination flexibility |

## Prometheus snmp_exporter: The Prometheus-Native Approach

The [prometheus/snmp_exporter](https://github.com/prometheus/snmp_exporter) is the officially recommended way to expose SNMP data to Prometheus. It operates as a sidecar-style exporter: Prometheus scrapes the exporter's HTTP endpoint, which in turn queries the target SNMP device and returns metrics in Prometheus exposition format.

### How It Works

The exporter runs on a central server (not on every device) and exposes a `/snmp` endpoint. Prometheus calls this endpoint with query parameters specifying the target device IP and the MIB module to query. The exporter performs the SNMP walk, maps OIDs to Prometheus metrics with appropriate labels, and returns the result.

### Docker Deployment

```yaml
version: "3.8"
services:
  snmp-exporter:
    image: prom/snmp-exporter:latest
    container_name: snmp-exporter
    ports:
      - "9116:9116"
    volumes:
      - ./snmp.yml:/etc/snmp_exporter/snmp.yml:ro
    restart: unless-stopped
    command:
      - '--config.file=/etc/snmp_exporter/snmp.yml'
      - '--log.level=info'
```

### Prometheus Scrape Configuration

```yaml
scrape_configs:
  - job_name: 'snmp_switches'
    metrics_path: /snmp
    params:
      auth: [public_v2]
      module: [if_mib]
    static_configs:
      - targets:
          - 192.168.1.1
          - 192.168.1.2
          - 10.0.0.50
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9116
```

### SNMPv3 Configuration with Environment Variables

For production environments, SNMPv3 provides encryption and authentication. The exporter supports injecting credentials via environment variables:

```yaml
auths:
  secure_v3:
    security_level: authPriv
    username: ${SNMP_V3_USERNAME}
    password: ${SNMP_V3_AUTH_PASSWORD}
    auth_protocol: SHA256
    priv_protocol: AES
    priv_password: ${SNMP_V3_PRIV_PASSWORD}
    version: 3
```

Run with `--config.expand-environment-variables` flag to enable variable substitution.

### MIB Generation

The snmp_exporter ships with a pre-generated `snmp.yml` covering common MIBs (IF-MIB, HOST-RESOURCES-MIB, UCD-SNMP-MIB, etc.). For custom or vendor-specific MIBs, use the [generator](https://github.com/prometheus/snmp_exporter/tree/main/generator):

```bash
cd generator
# Place your MIB files in /usr/share/snmp/mibs/
go build
./generator generate
# Output: snmp.yml
```

The generator downloads MIB definitions, resolves OID dependencies, and produces an optimized snmp.yml with walk lists and metric mappings.

## SNMPcollector: The Full-Featured Web UI Option

[SNMPcollector](https://github.com/toni-moreno/snmpcollector) takes a fundamentally different approach. Instead of acting as a passive exporter, it is a full-featured SNMP data collector with a built-in web administration interface. It connects directly to an InfluxDB backend and provides a GUI for configuring devices, metrics, and measurement groups.

### Key Advantages

- **Web UI for configuration**: No YAML editing — configure SNMP devices, credentials, and metrics through the browser at `http://localhost:8090`
- **InfluxDB native**: Direct integration with InfluxDB, no intermediate storage layer
- **Metric inheritance**: Define base measurements and inherit across multiple devices
- **Group-based management**: Organize devices into groups with shared configurations
- **Auto-discovery of SNMP tables**: Automatically detects and maps SNMP table structures

### Docker Deployment

```yaml
version: "3.8"
services:
  snmpcollector:
    image: tonimoreno/snmpcollector:latest
    container_name: snmpcollector
    ports:
      - "8090:8090"
    volumes:
      - ./conf:/opt/snmpcollector/conf
      - ./data:/opt/snmpcollector/data
    environment:
      - INFLUXDB_HOST=influxdb
      - INFLUXDB_PORT=8086
      - INFLUXDB_DBNAME=snmp_metrics
      - INFLUXDB_USER=snmp
      - INFLUXDB_PASSWORD=snmp_secret
    depends_on:
      - influxdb
    restart: unless-stopped

  influxdb:
    image: influxdb:2.7
    container_name: influxdb
    ports:
      - "8086:8086"
    volumes:
      - influxdb-data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=admin_password
      - DOCKER_INFLUXDB_INIT_ORG=myorg
      - DOCKER_INFLUXDB_INIT_BUCKET=snmp_metrics
    restart: unless-stopped

volumes:
  influxdb-data:
```

### Configuration via Web UI

After deployment, access the web interface at `http://your-server:8090`. The default credentials are `adm1` / `adm1pass` — change these immediately.

The configuration workflow is:

1. **Add SNMP devices**: Enter IP, community string (or SNMPv3 credentials), and polling interval
2. **Define measurements**: Specify which OIDs to collect, either by individual OID or entire SNMP table
3. **Create measurement groups**: Bundle related metrics (e.g., interface stats, CPU, memory)
4. **Schedule collection**: Set per-device or per-group polling intervals (default: 60 seconds)
5. **Verify**: View collected data directly in the UI before it reaches InfluxDB

## Telegraf SNMP Input: The Multi-Destination Collector

[Telegraf](https://github.com/influxdata/telegraf) is a plugin-driven server agent for collecting and reporting metrics. Its SNMP input plugin transforms Telegraf into a capable SNMP collector that can write to dozens of output destinations — InfluxDB, Prometheus, Elasticsearch, PostgreSQL, Kafka, and more.

### Why Choose Telegraf for SNMP

- **Output flexibility**: Write SNMP data to any backend, not just one specific database
- **Unified agent**: Collect SNMP metrics alongside system, Docker, application, and cloud metrics in a single agent
- **Wide SNMP support**: Full SNMPv3 support with all authentication and privacy protocols
- **Tag-based organization**: Use `agent_host_tag` and `is_tag` fields for rich label semantics
- **Field conversion**: Built-in type conversion (float, integer, string, hex, hwaddr, ipaddr)

### Docker Deployment

```yaml
version: "3.8"
services:
  telegraf:
    image: telegraf:latest
    container_name: telegraf-snmp
    volumes:
      - ./telegraf.conf:/etc/telegraf/telegraf.conf:ro
      - /usr/share/snmp/mibs:/usr/share/snmp/mibs:ro
    restart: unless-stopped
```

### Telegraf SNMP Input Configuration

```toml
[[inputs.snmp]]
  agents = [
    "udp://192.168.1.1:161",
    "udp://192.168.1.2:161",
    "udp://10.0.0.50:161"
  ]
  timeout = "5s"
  retries = 3
  version = 2
  community = "public"
  agent_host_tag = "source"

  # System uptime
  [[inputs.snmp.field]]
    oid = "RFC1213-MIB::sysUpTime.0"
    name = "sysUptime"
    conversion = "float(2)"

  # Hostname as tag
  [[inputs.snmp.field]]
    oid = "RFC1213-MIB::sysName.0"
    name = "sysName"
    is_tag = true

  # Interface table
  [[inputs.snmp.table]]
    oid = "IF-MIB::ifTable"
    name = "interface"
    inherit_tags = ["sysName"]

    [[inputs.snmp.table.field]]
      oid = "IF-MIB::ifDescr"
      name = "ifDescr"
      is_tag = true

    [[inputs.snmp.table.field]]
      oid = "IF-MIB::ifHCInOctets"
      name = "bytesIn"

    [[inputs.snmp.table.field]]
      oid = "IF-MIB::ifHCOutOctets"
      name = "bytesOut"

  # SNMPv3 authentication
  # Uncomment and configure for SNMPv3:
  # [[inputs.snmp]]
  #   agents = ["udp://10.0.0.100:161"]
  #   version = 3
  #   sec_name = "monitoring"
  #   auth_protocol = "SHA256"
  #   auth_password = "secure_auth_pass"
  #   sec_level = "authPriv"
  #   priv_protocol = "AES"
  #   priv_password = "secure_priv_pass"
```

### Output Configuration Examples

**Write to InfluxDB:**

```toml
[[outputs.influxdb_v2]]
  urls = ["http://influxdb:8086"]
  token = "your-influxdb-token"
  organization = "myorg"
  bucket = "snmp_metrics"
```

**Expose as Prometheus endpoint:**

```toml
[[outputs.prometheus_client]]
  listen = ":9273"
  metric_version = 2
```

**Write to PostgreSQL:**

```toml
[[outputs.postgresql]]
  connection = "host=pgserver port=5432 user=telegraf dbname=metrics"
  table = "snmp_metrics"
```

## Performance and Scalability Comparison

| Metric | snmp_exporter | SNMPcollector | Telegraf SNMP |
|---|---|---|---|
| **Max devices per instance** | Thousands | ~500 | Hundreds |
| **Polling model** | On-demand (scrape) | Scheduled (push) | Scheduled (push) |
| **Concurrent polling** | Per-request | Per-device threads | Per-agent goroutines |
| **Memory footprint** | ~50 MB | ~100 MB (with UI) | ~80 MB |
| **CPU per 100 devices** | Low (pull) | Medium (push) | Medium (push) |
| **High availability** | Multiple exporters + Prometheus HA | Single instance (no built-in HA) | Multiple agents + load balancer |

### Architecture Differences

**snmp_exporter** uses a pull-based model: Prometheus initiates each SNMP query by scraping the exporter. This means the exporter only polls when Prometheus requests data, keeping resource usage proportional to scrape frequency. A single exporter instance can handle thousands of devices because it does not maintain persistent connections.

**SNMPcollector** uses a push-based model: it actively polls devices on a schedule and pushes results to InfluxDB. This decouples collection from visualization — your Grafana dashboards query InfluxDB directly without any dependency on the collector being available at query time. However, the web UI and InfluxDB connection add overhead.

**Telegraf** also uses a push-based model but is designed as a general-purpose metrics agent. The SNMP input is just one of 300+ plugins. This makes Telegraf ideal when you want a single agent collecting system metrics, Docker stats, application metrics, and SNMP data — all writing to the same backend.

## Which SNMP Collector Should You Choose?

### Choose Prometheus snmp_exporter if:

- You already run Prometheus and Grafana for monitoring
- You need a lightweight, stateless exporter
- You are comfortable with YAML configuration and MIB generation
- You want the best integration with the Prometheus ecosystem (alerts, recording rules, service discovery)
- You have a large number of devices (thousands)

### Choose SNMPcollector if:

- You use InfluxDB as your time-series database
- You prefer a web UI over configuration files
- You want built-in device grouping and measurement inheritance
- You need per-device polling schedules configured visually
- Your team includes network engineers who prefer GUI-based management

### Choose Telegraf SNMP if:

- You need to write SNMP data to multiple backends simultaneously
- You want to unify SNMP collection with other metrics in a single agent
- You need output flexibility (InfluxDB, Prometheus, Elasticsearch, Kafka, PostgreSQL)
- You are already using the TICK stack (Telegraf, InfluxDB, Chronograf, Kapacitor)
- You want field-level type conversion and tag management

## SNMPv3 Security Best Practices

Regardless of which collector you choose, follow these security guidelines:

1. **Always use SNMPv3 in production**: SNMPv1 and v2c send community strings in plaintext. SNMPv3 provides authentication (MD5, SHA, SHA256, SHA384, SHA512) and encryption (DES, AES, AES192, AES256).

2. **Use read-only credentials**: Never grant read-write SNMP access to a monitoring tool. Create dedicated SNMPv3 users with `authNoPriv` or `authPriv` security levels and read-only access.

3. **Restrict source IPs**: Configure your network devices to only accept SNMP queries from the collector's IP address using ACLs or VRFs.

4. **Rotate credentials regularly**: Use environment variables or secret management tools (see our [Vault vs Infisical vs Passbolt guide](../2026-04-25-vault-vs-infisical-vs-passbolt-self-hosted-secrets-management-guide-2026/)) to manage SNMPv3 passwords and rotate them on a schedule.

5. **Monitor the collectors themselves**: Use host-level monitoring to ensure your SNMP collector processes are running, their memory usage is within bounds, and they are not falling behind on polling schedules.

## FAQ

### What is the difference between SNMP polling and SNMP traps?

SNMP polling is when the collector actively queries devices at regular intervals (e.g., every 60 seconds) to retrieve current metric values. SNMP traps are unsolicited notifications sent by devices when specific events occur (interface down, temperature threshold exceeded, authentication failure). All three tools discussed here focus on polling. For trap handling, you would use a dedicated trap daemon like `snmptrapd` or a SIEM platform like [Wazuh or Security Onion](../self-hosted-siem-wazuh-security-onion-elastic-guide/).

### Can I use multiple SNMP collectors at the same time?

Yes. Each collector operates independently. A common pattern is running snmp_exporter for Prometheus-based metrics while also running Telegraf to write the same SNMP data to a long-term storage backend like InfluxDB or PostgreSQL. Just ensure polling intervals are staggered to avoid overwhelming network devices with simultaneous queries.

### How often should I poll SNMP devices?

For most infrastructure metrics (interface counters, CPU, memory, disk), a 60-second interval is standard. For high-frequency metrics like interface utilization on busy links, 30 seconds may be appropriate. For slowly-changing metrics like UPS battery level or temperature sensors, 300 seconds (5 minutes) is sufficient. Polling too frequently can overwhelm low-end network devices and generate excessive database writes.

### Do these collectors support custom/vendor-specific MIBs?

Yes, but the setup varies. snmp_exporter requires running the generator tool with your MIB files to produce an updated `snmp.yml`. SNMPcollector can import MIB files through its web UI. Telegraf uses the gosmi or netsnmp translator and can load custom MIBs from the `path` configuration directive. In all cases, you need the vendor's MIB files (typically `.mib` or `.txt` format) installed on the collector host.

### What happens if an SNMP device goes offline?

All three collectors handle unreachable devices gracefully. snmp_exporter returns a scrape timeout to Prometheus, which can be detected via the `up` metric. SNMPcollector logs the failure and retries on the next scheduled poll. Telegraf logs errors and continues polling other agents in its configuration. None of them will crash or hang indefinitely — they all have configurable timeout values.

### Is SNMPcollector still actively maintained?

As of April 2026, SNMPcollector's last release was in December 2023. While the codebase is stable and functional, the project's development pace has slowed. For new deployments, consider whether the web UI benefits outweigh the risk of running a less actively maintained project. snmp_exporter and Telegraf both receive frequent updates as part of the Prometheus and InfluxData ecosystems, respectively.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SNMP Collectors: snmp_exporter vs SNMPcollector vs Telegraf 2026",
  "description": "Compare three self-hosted SNMP collectors — Prometheus snmp_exporter, SNMPcollector, and Telegraf SNMP input — with Docker deployment guides, configuration examples, and performance benchmarks for 2026.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
