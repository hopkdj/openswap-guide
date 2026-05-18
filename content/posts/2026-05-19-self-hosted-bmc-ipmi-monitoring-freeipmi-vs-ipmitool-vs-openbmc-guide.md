---
title: "Self-Hosted BMC and IPMI Monitoring: freeipmi vs ipmitool vs OpenBMC"
date: "2026-05-19"
tags: ["bmc", "ipmi", "hardware-monitoring", "server-management", "redfish", "openbmc", "self-hosted", "infrastructure"]
draft: false
---

Baseboard Management Controllers (BMCs) provide out-of-band management for servers, enabling remote power control, hardware health monitoring, and console access independent of the host operating system. The Intelligent Platform Management Interface (IPMI) is the standard protocol for communicating with BMCs. We compare the leading open-source tools for monitoring and managing BMC hardware.

## Why Self-Host BMC/IPMI Monitoring?

Enterprise server hardware generates critical telemetry — CPU temperatures, fan speeds, power consumption, voltage readings, and hardware error logs. Without centralized BMC monitoring, hardware failures go undetected until they cause outages.

Self-hosted BMC monitoring provides three benefits: complete data ownership (no vendor telemetry sent to the cloud), integration with existing monitoring stacks like Prometheus and Grafana, and automated alerting and remediation before hardware failures impact services.

For related hardware monitoring, see our [bare metal hardware monitoring guide](../2026-04-23-self-hosted-bare-metal-hardware-monitoring-ipmi-redfish-openbmc-guide/) and [network device discovery guide](../2026-05-09-self-hosted-network-device-discovery-watchyourlan-netalertx-pialert-guide/).

## freeipmi: GNU IPMI Management Suite

[freeipmi](https://www.gnu.org/software/freeipmi/) is the GNU project's comprehensive IPMI software suite, providing command-line tools for IPMI communication, sensor monitoring, and system event log analysis. It is the most feature-complete open-source IPMI implementation.

**Key Features:**

- Full IPMI 1.5 and 2.0 specification compliance
- In-band and out-of-band BMC communication
- Sensor data record (SDR) repository access
- System Event Log (SEL) reading and clearing
- IPMI console (sol) for serial-over-LAN access
- FRU (Field Replaceable Unit) inventory reporting
- LAN configuration for remote BMC access

**Project Status:** Maintained by the GNU project, with packages available on all major Linux distributions.

### freeipmi Installation and Usage

```bash
# Install freeipmi tools
sudo apt-get install freeipmi-tools

# List all sensors (temperature, voltage, fan speed)
ipmi-sensors

# Read specific sensor data with verbose output
ipmi-sensors --sensor-types "Temperature,Fan,Voltage" --verbose

# View system event log
ipmi-sel

# Read FRU inventory
fru-parser

# IPMI console (serial-over-LAN)
ipmi-console

# Configure BMC network settings
bmc-config --checkout > bmc-config-backup.txt
```

### Prometheus IPMI Exporter Docker Compose

```yaml
version: '3.8'
services:
  ipmi-exporter:
    image: prometheuscommunity/ipmi-exporter:latest
    ports:
      - "9290:9290"
    environment:
      - IPMI_EXPORTER_CONFIG=/etc/ipmi-exporter/config.yml
    volumes:
      - ./ipmi-exporter-config.yml:/etc/ipmi-exporter/config.yml
    privileged: true
    network_mode: host

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prom_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  prom_data:
  grafana_data:
```

## ipmitool: Industry-Standard IPMI Utility

[ipmitool](https://github.com/ipmitool/ipmitool) is the most widely deployed IPMI management utility, providing a simple command-line interface for BMC communication. It is included by default in most server distributions and supported by all major hardware vendors.

**Key Features:**

- Simple, consistent command-line interface
- LAN and local BMC access
- Power management (on, off, cycle, reset)
- SEL (System Event Log) management
- SEL event subscription for real-time alerts
- Firmware update via IPMI
- Watchdog timer management

**GitHub Stats:** Actively maintained, available as standard package in all Linux distributions.

### ipmitool Commands for Server Management

```bash
# Install ipmitool
sudo apt-get install ipmitool

# Check power status
ipmitool -H 192.168.1.100 -U admin -P password power status

# Remote power cycle
ipmitool -H 192.168.1.100 -U admin -P password power cycle

# Read all sensor data
ipmitool -H 192.168.1.100 -U admin -P password sdr list

# Read temperature sensors only
ipmitool -H 192.168.1.100 -U admin -P sensor list | grep Temp

# View system event log
ipmitool -H 192.168.1.100 -U admin -P sel list

# Clear system event log
ipmitool -H 192.168.1.100 -U admin -P sel clear

# Set BMC network configuration
ipmitool -H 192.168.1.100 -U admin -P raw 0x0c 0x01 0x01 0x00 0x00

# Watchdog timer management
ipmitool mc watchdog get
ipmitool mc watchdog reset
```

## OpenBMC: Modern Linux-Based BMC Firmware

[OpenBMC](https://github.com/openbmc/openbmc) is a modern, Linux-based BMC firmware stack that replaces proprietary vendor BMC implementations. It provides a full management interface with Redfish API support, replacing legacy IPMI with RESTful management.

**Key Features:**

- Complete Linux-based BMC firmware (not just a management tool)
- Redfish API support for modern hardware management
- D-Bus-based internal architecture
- Web-based BMC management interface
- Support for multiple hardware platforms (IBM, Intel, Meta, Rackspace)
- Modern security with TLS and certificate-based auth
- Active development by major tech companies

**GitHub Stats:** 1,500+ stars, backed by the Open Compute Project with contributions from Meta, IBM, Intel, and Google.

### OpenBMC Architecture

```
+---------------------------+
|  REST API (Redfish)       |
|  Web UI (React-based)     |
+---------------------------+
|  D-Bus Object Manager     |
+---------------------------+
|  Sensor/LED/Fan Services  |
|  Power/Thermal Services   |
+---------------------------+
|  Hardware Abstraction     |
|  I2C/SPI/ADC Drivers      |
+---------------------------+
|  Linux Kernel + U-Boot    |
+---------------------------+
```

OpenBMC is deployed as firmware on the BMC chip itself, not as a management tool running on the host OS. Organizations like Meta and IBM use OpenBMC on their custom server designs, providing a fully open hardware management stack.

## Feature Comparison

| Feature | freeipmi | ipmitool | OpenBMC |
|---------|----------|----------|---------|
| **Type** | IPMI management suite | IPMI command utility | BMC firmware replacement |
| **IPMI 2.0** | Full support | Full support | N/A (provides IPMI bridge) |
| **Redfish API** | No | No | Yes (native) |
| **Web Interface** | No | No | Yes (React-based) |
| **Sensor Reading** | Comprehensive | Basic | Comprehensive |
| **Power Control** | Yes | Yes | Yes |
| **SEL Management** | Full | Full | Full |
| **Serial-over-LAN** | Yes | Yes | Yes (via Web UI) |
| **FRU Inventory** | Yes | Yes | Yes |
| **Firmware Update** | No | Yes (via IPMI) | Built-in |
| **Prometheus Export** | Via ipmi_exporter | Via ipmi_exporter | Native Redfish exporter |
| **Best For** | Linux sysadmins | Quick CLI operations | Custom server hardware |

## Choosing the Right BMC/IPMI Tool

**Choose freeipmi** if you need comprehensive IPMI management with full specification compliance. Its sensor discovery and SDR repository access are the most thorough among open-source IPMI tools, making it ideal for inventory and health monitoring of heterogeneous server fleets.

**Choose ipmitool** for quick, ad-hoc BMC operations. Its simple command syntax and ubiquitous availability make it the go-to tool for remote power cycling, SEL checking, and firmware updates. Every sysadmin should have ipmitool in their toolkit.

**Choose OpenBMC** if you are designing custom server hardware or want to replace proprietary BMC firmware. OpenBMC provides a modern, secure management stack with Redfish API support, eliminating vendor lock-in and enabling full hardware observability.

For data center monitoring, see our [IT inventory management comparison](../snipe-it-vs-inventree-vs-partkeepr-self-hosted-inventory-management-guide/).

## FAQ

### What is the difference between IPMI and Redfish?
IPMI is a legacy protocol (circa 1998) using raw binary commands over LAN or system interfaces. Redfish is a modern RESTful API using JSON over HTTPS, with standardized schemas and better security. Redfish is the successor to IPMI, but IPMI remains widely deployed.

### Can I monitor BMC health without installing software on the host OS?
Yes. IPMI operates out-of-band, meaning you can query the BMC from any network-connected machine without host OS software. The `ipmitool -H <bmc-ip>` command connects directly to the BMC's management network interface.

### Is IPMI secure for remote management?
IPMI 2.0 supports RMCP+ authentication with AES encryption, but older IPMI 1.5 uses plain-text passwords. Modern deployments should use IPMI over a dedicated management VLAN, restrict access with firewall rules, or migrate to Redfish with TLS encryption.

### How do I integrate IPMI sensors with Prometheus and Grafana?
Use the prometheus-community/ipmi_exporter, which queries IPMI sensors via freeipmi libraries and exposes them as Prometheus metrics. Configure Grafana dashboards using the IPMI Exporter dashboard templates available on Grafana.com.

### Can OpenBMC run on existing server hardware?
OpenBMC is designed for custom server platforms. Major vendors (Dell, HPE, Lenovo) ship proprietary BMC firmware. OpenBMC targets open hardware designs from the Open Compute Project. Running OpenBMC on commercial servers requires significant porting effort.

### What is Serial-over-LAN (SOL) and how do I use it?
SOL provides remote console access to a server's serial port through the BMC's network interface. This is essential for debugging boot failures when the OS is unresponsive. Use `ipmi-console` (freeipmi) or `ipmitool sol activate` to connect.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BMC and IPMI Monitoring: freeipmi vs ipmitool vs OpenBMC",
  "description": "Compare freeipmi, ipmitool, and OpenBMC for managing server hardware BMCs, IPMI sensors, and Redfish APIs in self-hosted data center environments.",
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
