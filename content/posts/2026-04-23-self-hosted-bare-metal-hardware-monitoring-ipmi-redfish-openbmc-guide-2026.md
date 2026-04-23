---
title: "Self-Hosted Bare-Metal Hardware Monitoring: IPMI vs Redfish vs OpenBMC 2026"
date: 2026-04-23
tags: ["monitoring", "guide", "self-hosted", "hardware", "infrastructure"]
draft: false
description: "Complete guide to self-hosted bare-metal hardware monitoring using IPMI, Redfish, and OpenBMC. Compare tools, deploy with Docker, and monitor physical server health without cloud dependencies."
---

If you run physical servers at home or in a colo rack, you need visibility into hardware health that goes beyond what software-level monitoring can provide. CPU temperatures, fan speeds, power draw, ECC memory errors, and drive backplane status live at the firmware layer — not inside the operating system.

This guide covers the three dominant open-source approaches to self-hosted bare-metal hardware monitoring: **IPMI** (Intelligent Platform Management Interface), **Redfish** (the modern RESTful standard), and **OpenBMC** (the fully open BMC firmware stack). You'll learn when to use each, how to query them, and how to integrate them into a self-hosted monitoring dashboard.

## Why Monitor Bare-Metal Hardware Directly?

Software monitoring tools like Prometheus node_exporter or Netdata see what the OS exposes: CPU load, memory usage, disk I/O, and network throughput. But they cannot tell you:

- Whether a CPU is thermal throttling before the kernel detects it
- If a power supply unit (PSU) is about to fail
- Whether chassis fans are running at safe RPMs
- If the BMC itself is healthy or unresponsive
- The real-time power consumption in watts
- Whether an ECC-correctable memory error is escalating
- If the RAID backplane is reporting degraded drives

All of this data lives in the **Baseboard Management Controller (BMC)** — a dedicated microcontroller on the server motherboard that operates independently of the main OS. Even if the server kernel panics, the BMC keeps running and can report the cause.

For homelab operators and small infrastructure teams, self-hosting hardware monitoring means full control over alerts, historical data, and access policies — no third-party dashboards or cloud subscriptions required.

## IPMI: The Established Standard

IPMI has been the industry standard for server hardware management since 1998. It defines a set of interfaces for out-of-band management: power cycling, sensor readings, event logs, and serial-over-LAN console access.

### IPMItool: The Reference Implementation

[IPMItool](https://github.com/ipmitool/ipmitool) is the primary open-source utility for interacting with IPMI-enabled systems. With 1,600+ GitHub stars and a proven track record across Linux, BSD, and Windows, it remains the go-to CLI for BMC communication.

**Key capabilities:**
- Read hardware sensors (temperature, voltage, fan speed, power)
- View and clear System Event Log (SEL) entries
- Remote power control (on, off, cycle, reset)
- Serial-over-LAN (SOL) for console access
- Firmware update and FRU (Field Replaceable Unit) inventory
- LAN configuration for remote BMC access

**Installation:**

```bash
# Debian/Ubuntu
sudo apt install ipmitool

# RHEL/CentOS/Rocky
sudo yum install ipmitool

# Alpine (container-friendly)
apk add ipmitool
```

**Local sensor query:**

```bash
# Read all hardware sensors
sudo ipmitool sdr list

# Show temperature sensors only
sudo ipmitool sdr list | grep -i temp

# Read all sensor readings with current values
sudo ipmitool sensor list
```

Example output from a Dell PowerEdge R730:

```
Temp             | 37h | ok  |  7.1 | 28 degrees C
Temp             | 38h | ok  |  7.2 | 32 degrees C
Fan1             | 30h | ok  | 29.1 | 3600 RPM
Fan2             | 31h | ok  | 29.2 | 3480 RPM
Pwr Consumption  | 6Ah | ok  | 10.1 | 185 Watts
VCORE PG         | 15h | ok  | 15.1 | Presence detected
```

**Remote sensor query over LAN:**

```bash
ipmitool -I lanplus -H 192.168.1.100 -U admin -P secret sdr list
```

**Read the System Event Log (SEL):**

```bash
# Show recent hardware events
sudo ipmitool sel list

# Show full event details
sudo ipmitool sel elist

# Clear the event log after review
sudo ipmitool sel clear
```

**Remote power management:**

```bash
# Check current power state
ipmitool -I lanplus -H 192.168.1.100 -U admin -P secret chassis power status

# Graceful shutdown
ipmitool -I lanplus -H 192.168.1.100 -U admin -P secret chassis power soft

# Hard power cycle
ipmitool -I lanplus -H 192.168.1.100 -U admin -P secret chassis power cycle
```

**Docker deployment for containerized monitoring:**

```yaml
# docker-compose.yml - IPMI monitoring container
version: "3.8"

services:
  ipmi-exporter:
    image: prometheuscommunity/ipmi-exporter:latest
    container_name: ipmi-exporter
    restart: unless-stopped
    ports:
      - "9290:9290"
    environment:
      - IPMI_EXPORTER_CONFIG=/etc/ipmi-exporter/config.yml
    volumes:
      - ./ipmi-exporter-config.yml:/etc/ipmi-exporter/config.yml:ro
    devices:
      - /dev/ipmi0:/dev/ipmi0  # Local BMC device pass-through
    cap_add:
      - SYS_RAWIO             # Required for raw IPMI access
    networks:
      - monitoring

  # Scrape config for Prometheus
  # Add to prometheus.yml:
  # - job_name: 'ipmi'
  #   static_configs:
  #     - targets: ['192.168.1.100']
  #   metrics_path: /ipmi
  #   params:
  #     module: [default]

networks:
  monitoring:
    external: true
```

**IPMI exporter configuration** (`ipmi-exporter-config.yml`):

```yaml
default:
  collectors:
    - bmc
    - ipmi
    - dcmi
    - gpu_nvidia
  gocpi:
    driver: "auto"
```

### Limitations of IPMI

IPMI has significant drawbacks in modern deployments:

- **Proprietary extensions**: Each vendor (Dell iDRAC, HP iLO, Supermicro) adds non-standard features that break portability
- **Security weaknesses**: IPMI 2.0 uses weak authentication (RMCP+) and has known cipher-0 vulnerabilities
- **No REST API**: All communication uses raw binary protocols, requiring specialized tools
- **Limited sensor coverage**: Not all modern sensors are exposed through standard SDR (Sensor Data Repository) tables
- **Aging standard**: The spec was last updated in 2013; newer hardware features may not be supported

## Redfish: The Modern RESTful Standard

Redfish was introduced by the DMTF in 2015 as a modern replacement for IPMI. It uses HTTPS with RESTful JSON APIs, making it far easier to integrate with self-hosted monitoring stacks.

### libredfish and Redfish Clients

[libredfish](https://github.com/DMTF/libredfish) is the DMTF's official C client library. For practical monitoring, most operators use higher-level tools:

- **python-redfish** — Python library with full Redfish schema support
- **sushy** — Redfish library used by OpenStack Ironic (56 stars on GitHub, but widely deployed in production)
- **curl + jq** — Direct REST API queries for ad-hoc checks

**Installation (Python-based approach):**

```bash
pip3 install redfish
```

**Query a Redfish endpoint:**

```bash
# Discover root service
curl -sk https://192.168.1.100/redfish/v1/ | jq .

# Get chassis information
curl -sk https://192.168.1.100/redfish/v1/Chassis/ | jq .

# Read system power metrics
curl -sk https://192.168.1.100/redfish/v1/Chassis/1/Power/ | jq \
  '.PowerControl[] | {Name, PowerConsumedWatts, PowerCapacityWatts}'

# Read thermal sensors
curl -sk https://192.168.1.100/redfish/v1/Chassis/1/Thermal/ | jq \
  '.Temperatures[] | {Name, ReadingCelsius, UpperThresholdCritical}'

# List all hardware drives
curl -sk https://192.168.1.100/redfish/v1/Systems/1/Storage/ | jq \
  '.Members[]["@odata.id"]'
```

**Python script for Redfish sensor polling:**

```python
#!/usr/bin/env python3
"""Poll Redfish thermal and power sensors, output Prometheus metrics."""

import requests
import json
import sys
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

BMC_HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.100"
USERNAME = "admin"
PASSWORD = "secret"
BASE = f"https://{BMC_HOST}/redfish/v1"

session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.verify = False

def get_json(url):
    r = session.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

# Get thermal data
thermal = get_json(f"{BASE}/Chassis/1/Thermal/")
for sensor in thermal.get("Temperatures", []):
    name = sensor.get("Name", "unknown")
    reading = sensor.get("ReadingCelsius")
    if reading is not None:
        print(f'hardware_temp_celsius{{sensor="{name}"}} {reading}')

# Get power data
power = get_json(f"{BASE}/Chassis/1/Power/")
for control in power.get("PowerControl", []):
    name = control.get("Name", "unknown")
    consumed = control.get("PowerConsumedWatts")
    if consumed is not None:
        print(f'hardware_power_watts{{unit="{name}"}} {consumed}')

# Get fan speeds
for fan in thermal.get("Fans", []):
    name = fan.get("Name", "unknown")
    rpm = fan.get("Reading")
    if rpm is not None:
        print(f'hardware_fan_rpm{{fan="{name}"}} {rpm}')
```

Make it executable and run:

```bash
chmod +x redfish-exporter.py
python3 redfish-exporter.py 192.168.1.100
```

**Docker Compose for Redfish monitoring stack:**

```yaml
version: "3.8"

services:
  redfish-exporter:
    image: stmcginnis/redfish-exporter:latest
    container_name: redfish-exporter
    restart: unless-stopped
    ports:
      - "9505:9505"
    environment:
      - BMC_ENDPOINT=https://192.168.1.100
      - BMC_USERNAME=admin
      - BMC_PASSWORD=secret
      - SSL_VERIFY=false
      - POLL_INTERVAL=30
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana-hw
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - monitoring

volumes:
  grafana-data:

networks:
  monitoring:
    external: true
```

### Redfish Advantages Over IPMI

- **Standard REST API**: JSON over HTTPS, works with any HTTP client
- **Rich data model**: Exposes far more sensors, including NVMe drive health, GPU telemetry, and NIC link statistics
- **Schema versioning**: DMTF publishes formal schemas for every resource type
- **Role-based access**: Fine-grained permissions for different operator roles
- **Event subscriptions**: Push-based alerts via HTTP POST to your monitoring endpoint
- **Future-proof**: Actively developed with annual schema updates

### Redfish Limitations

- **Not all vendors implement all schemas**: Dell iDRAC has broader Redfish coverage than Supermicro
- **HTTPS certificate issues**: BMCs often use self-signed certs, requiring `-k` or custom CA bundles
- **Newer hardware required**: Servers before ~2017 may not support Redfish at all

## OpenBMC: The Fully Open Firmware Stack

[OpenBMC](https://github.com/openbmc/openbmc) is a Linux Foundation project that provides a complete, open-source BMC firmware distribution. Unlike IPMI and Redfish (which are management *protocols*), OpenBMC replaces the proprietary BMC firmware entirely with an open-stack alternative.

With 2,400+ stars on GitHub and active development from IBM, Google, Meta, and Intel, OpenBMC is the future of open server management.

### OpenBMC Architecture

OpenBMC runs on the BMC chip itself and provides:

- **bmcweb**: A Redfish-compliant REST API server
- **phosphor-hwmon**: Hardware monitoring via Linux hwmon drivers
- **phosphor-dbus**: D-Bus interfaces for all BMC functionality
- **xyz.openbmc_project**: Namespace for all OpenBMC services

**Key benefits:**
- No vendor lock-in — runs on supported hardware from multiple OEMs
- Full Redfish compliance via bmcweb
- D-Bus API for deep programmatic control
- OTA firmware updates
- Web-based KVM console (no proprietary Java/applet plugins)
- Active community with quarterly releases

### OpenBMC Hardware Support

OpenBMC currently supports select platforms:

- IBM Power systems (Witherspoon, Rainier)
- Facebook/Yosemite servers (Wedge, Yosemite V4)
- Intel CRB reference boards
- ASRock Rack ROMED8HM3 (AMD EPYC)
- Some Google OCP (Open Compute Project) designs

Building OpenBMC for your hardware:

```bash
# Clone the OpenBMC build system
git clone https://github.com/openbmc/openbmc
cd openbmc

# Configure for your target machine
TEMPLATECONF=meta-ibm/meta-witherspoon/conf \
  . openbmc-env

# Build the firmware image
bitbake obmc-phosphor-image

# Output: build/tmp/deploy/images/witherspoon/obmc-phosphor-image-witherspoon.static.mtd
```

The build process requires ~50GB disk space and several hours on a multi-core system.

### Deploying OpenBMC in Production

```bash
# Flash the firmware via IPMI (out-of-band update)
ipmitool -I lanplus -H 192.168.1.100 -U admin -P secret \
  hpm upgrade obmc-phosphor-image-witherspoon.static.mtd force

# Or use the OpenBMC web interface at https://<BMC-IP>/
# Navigate to: Settings → Firmware Update → Upload Image
```

After flashing, the BMC reboots (main server OS is unaffected) and serves a fully open Redfish endpoint.

## Comparison: IPMI vs Redfish vs OpenBMC

| Feature | IPMI (ipmitool) | Redfish | OpenBMC |
|---------|----------------|---------|---------|
| **Protocol type** | Binary (RMCP+) | REST/HTTPS (JSON) | REST/HTTPS + D-Bus |
| **Standard body** | Intel (legacy) | DMTF | Linux Foundation |
| **API format** | CLI commands, raw binary | JSON over HTTPS | JSON over HTTPS + D-Bus |
| **Authentication** | MD5 / RMCP+ (weak) | HTTPS + RBAC | HTTPS + PAM / LDAP |
| **Sensor coverage** | Basic (SDR tables) | Extensive (schema-based) | Full hwmon + custom |
| **Power control** | Yes (on/off/cycle) | Yes (Graceful/Force) | Yes (full control) |
| **Serial console** | SOL (Serial-over-LAN) | Not natively | Web KVM + SOL |
| **Event log** | SEL (limited) | LogEntry (rich) | EventLog (D-Bus) |
| **Vendor support** | Universal (since 1998) | Most servers (since ~2017) | Select platforms |
| **Open source** | ipmitool is OSS | Spec is open, firmware is not | Fully open firmware |
| **GitHub stars** | 1,601 | libredfish: 56 | 2,414 |
| **Last major update** | IPMI 2.0 (2013) | DMTF 2024.3 | Quarterly releases |
| **Docker monitoring** | ipmi-exporter | redfish-exporter | bmcweb (built-in) |

## When to Use Each Approach

**Use IPMI when:**
- You manage legacy servers (pre-2017) without Redfish support
- You need quick ad-hoc checks from the command line
- Your BMC firmware only supports IPMI (common on older Supermicro boards)
- You need serial-over-LAN console access to a crashed system

**Use Redfish when:**
- Your servers support it (most enterprise servers from 2018+)
- You want to build automated monitoring with REST APIs
- You need fine-grained access control and audit logging
- You're integrating with Prometheus, Grafana, or custom dashboards
- You want push-based event subscriptions instead of polling

**Use OpenBMC when:**
- You run supported hardware and want to eliminate proprietary BMC firmware
- You need full control over the management stack
- You want a fully auditable, open-source BMC implementation
- You're deploying at scale and want to avoid vendor lock-in

## Integrating with Self-Hosted Monitoring Stacks

### Prometheus + Grafana Pipeline

The most common pattern for self-hosted hardware monitoring combines an exporter with Prometheus and Grafana:

```yaml
# docker-compose.yml - Complete hardware monitoring stack
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus-hw
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=90d'
    networks:
      - monitoring

  ipmi-exporter:
    image: prometheuscommunity/ipmi-exporter:latest
    container_name: ipmi-exporter
    restart: unless-stopped
    ports:
      - "9290:9290"
    volumes:
      - ./ipmi-exporter-config.yml:/etc/ipmi-exporter/config.yml:ro
    devices:
      - /dev/ipmi0:/dev/ipmi0
    cap_add:
      - SYS_RAWIO
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    pid: host
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
      - '--collector.diskstats.ignored-devices=^(ram|loop)\\d*$'
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus-data:
```

**Prometheus scrape configuration** (`prometheus.yml`):

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'ipmi-bmc'
    static_configs:
      - targets: ['192.168.1.100']
    metrics_path: /ipmi
    params:
      module: ['default']
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 'ipmi-exporter:9290'

  - job_name: 'node-hardware'
    static_configs:
      - targets: ['node-exporter:9100']
```

**Key Prometheus metrics to alert on:**

```yaml
# alerting-rules.yml
groups:
  - name: hardware_alerts
    rules:
      - alert: HighCPUTemperature
        expr: ipmi_sensor_value{sensor_type="temperature"} > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU temperature above 80°C on {{ $labels.instance }}"

      - alert: FanFailure
        expr: ipmi_sensor_value{sensor_type="fan"} < 500
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Fan speed critically low on {{ $labels.instance }}"

      - alert: HighPowerConsumption
        expr: ipmi_sensor_value{sensor_type="power"} > 500
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Power consumption above 500W on {{ $labels.instance }}"
```

### Complementing with OS-Level Monitoring

Hardware monitoring works best when combined with OS-level metrics. For a complete picture, pair your BMC data with:

- **node_exporter** — CPU, memory, disk I/O, network at the OS level
- **smartd / smartmontools** — individual drive SMART health data
- **nvtop** — GPU utilization and temperature (see our [GPU monitoring guide](../2026-04-22-nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) for details)
- **Scrutiny** — drive health dashboard with SMART data aggregation (covered in our [disk health monitoring guide](../self-hosted-disk-health-monitoring-scrutiny-smartd-nvme-cli-guide-2026/))

For a broader view of system health dashboards, the [terminal dashboard comparison](../self-hosted-terminal-dashboard-btop-glances-bottom-system-monitoring-guide-2026/) covers lightweight alternatives for quick CLI-based hardware checks.

## Security Best Practices for BMC Access

BMCs are high-value targets — compromise gives an attacker full control over server power, firmware, and console access.

**Critical security measures:**

1. **Isolate BMC networks**: Put BMC management interfaces on a separate VLAN, never exposed to the internet
2. **Change default credentials**: Every BMC ships with admin/admin or similar defaults
3. **Use IPMI restricted to LAN+**: Disable serial and USB IPMI channels in production
4. **Enable Redfish over HTTPS only**: Disable plain HTTP on the BMC
5. **Set up certificate-based auth**: Use client certificates for Redfish API access instead of passwords
6. **Regular firmware updates**: BMC firmware has its own CVE lifecycle — patch regularly
7. **Audit access logs**: Monitor BMC login attempts via SEL or Redfish LogEntry resources

```bash
# Disable IPMI over serial (if not needed)
sudo ipmitool raw 0x0c 0x01 0x00 0x00  # Disable serial channel

# Check for default credentials vulnerability
sudo ipmitool user list 1

# Enable IPMI 2.0 only (disable 1.5)
sudo ipmitool lan set 1 access_mode always

# Set strong BMC password
sudo ipmitool user set password 2 'YourStrongPassword123!'
```

## FAQ

### What is the difference between IPMI and Redfish?

IPMI is a legacy binary protocol (RMCP+) that has been the industry standard since 1998. It uses CLI tools like ipmitool for hardware management. Redfish is a modern RESTful API standard (introduced in 2015 by DMTF) that uses HTTPS with JSON payloads. Redfish offers richer data models, better security with HTTPS and RBAC, and easier integration with monitoring tools. Most servers from 2018 onward support both.

### Can I use OpenBMC on any server?

No. OpenBMC must be specifically ported to each hardware platform because it replaces the proprietary BMC firmware. Currently it supports select IBM Power systems, Facebook/Yosemite servers, Intel reference boards, and some ASRock Rack motherboards. Check the [OpenBMC GitHub repository](https://github.com/openbmc/openbmc) for the current hardware support matrix. For unsupported hardware, use IPMI or Redfish with your vendor's proprietary BMC firmware.

### How do I monitor hardware without a BMC?

If your server or desktop lacks a BMC (common on consumer motherboards), you can still monitor hardware using OS-level tools: **node_exporter** provides CPU/memory/disk metrics, **smartmontools** reads drive SMART data via `/dev/sdX`, **lm-sensors** (`sensors-detect` + `sensors`) reads temperature and voltage chips accessible from the OS, and **ipmitool** can read some sensors via the local `/dev/ipmi0` device even without remote LAN access.

### Is IPMI secure enough for production use?

IPMI 2.0 has known security weaknesses including weak authentication and cipher-0 vulnerabilities. For production use, you should: isolate BMCs on a management VLAN, disable unused IPMI channels, use strong passwords, restrict IPMI source IPs via firewall rules, and prefer Redfish over HTTPS whenever your hardware supports it. Many organizations are migrating from IPMI to Redfish as a security improvement.

### How often should I poll BMC sensors?

For most homelab and small infrastructure setups, polling every 30–60 seconds is sufficient. Temperature and power readings change slowly, so high-frequency polling adds unnecessary load to the BMC. For critical alerts (fan failure, PSU fault), configure the BMC to push event subscriptions to your monitoring endpoint instead of relying on polling intervals.

### Can I get BMC data into Grafana dashboards?

Yes. The standard approach is: (1) Deploy an exporter (ipmi-exporter or redfish-exporter) as a Docker container, (2) Configure Prometheus to scrape the exporter's metrics endpoint, (3) Import or build Grafana dashboards that query the Prometheus data. Pre-built Grafana dashboards exist for both IPMI and Redfish exporters on the Grafana dashboard repository.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Bare-Metal Hardware Monitoring: IPMI vs Redfish vs OpenBMC 2026",
  "description": "Complete guide to self-hosted bare-metal hardware monitoring using IPMI, Redfish, and OpenBMC. Compare tools, deploy with Docker, and monitor physical server health without cloud dependencies.",
  "datePublished": "2026-04-23",
  "dateModified": "2026-04-23",
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
