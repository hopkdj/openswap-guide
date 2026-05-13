---
title: "Self-Hosted Network Discovery Agents: lldpd vs SNMP Discovery vs arp-scan"
date: "2026-05-13"
tags: ["network-discovery", "lldp", "snmp", "arp-scan", "lldpd", "self-hosted"]
draft: false
---

Network discovery agents automatically detect and map devices on your network, providing visibility into connected hosts, switches, and infrastructure. Whether you need to audit your network inventory, detect unauthorized devices, or build a network topology map, the right discovery agent is essential for self-hosted infrastructure management. This guide compares **lldpd**, **SNMP-based discovery tools**, and **arp-scan** for network discovery use cases.

## Understanding Network Discovery

Network discovery works at different OSI layers, each providing a different view of your infrastructure:

- **Layer 2 (Link Layer)**: LLDP (Link Layer Discovery Protocol) discovers directly connected neighbors
- **Layer 3 (Network Layer)**: ARP scanning discovers all active hosts on a subnet
- **Management Layer**: SNMP polling discovers device details, interfaces, and services

Each approach has strengths and limitations. A complete network discovery strategy combines all three.

## lldpd — Layer 2 Network Discovery

**lldpd** is a modern, actively maintained LLDP (Link Layer Discovery Protocol) daemon for Linux. It discovers directly connected network devices and their properties.

### Installation and Basic Configuration

```bash
# Install lldpd
# Debian/Ubuntu
apt-get install -y lldpd

# RHEL/CentOS
yum install -y lldpd

# Start and enable
systemctl enable --now lldpd
```

### lldpd Configuration

```bash
# /etc/lldpd.conf

# Listen on all interfaces by default
# To restrict to specific interfaces:
configure lldp port-ifregex eth.*

# Set system description
configure system description "Production Server - Rack 3, Unit 12"

# Set management IP (the IP other devices use to reach this host)
configure system management-ip 10.0.1.50

# Enable LLDP transmit and receive
configure lldp port eth0 tx enable
configure lldp port eth0 rx enable

# Enable CDP (Cisco Discovery Protocol) compatibility
configure lldp port eth0 cdp enable

# Enable SONMP (Nortel) compatibility
configure lldp port eth0 sonmp enable

# Set LLDP hold time and timer
configure lldp tx-interval 30
configure lldp tx-hold 4
```

### Querying lldpd Discovery Data

```bash
# Show all discovered neighbors
lldpcli show neighbors

# Output example:
# -------------------------------------------------------------------------------
# LLDP neighbors:
# -------------------------------------------------------------------------------
# Interface:    eth0, via: LLDP, RID: 1, Time: 0 day, 00:15:32
#   Chassis:
#     ChassisID:    mac 00:1a:2b:3c:4d:5e
#     SysName:      core-switch-01.company.com
#     SysDescr:     Cisco IOS Software, Catalyst L3 Switch Software
#     Capability:   Bridge, Router
#   Port:
#     PortID:       ifname GigabitEthernet1/0/24
#     PortDescr:    Server Uplink Port
#   TTL:            120
# -------------------------------------------------------------------------------

# Show in JSON format (for automation)
lldpcli show neighbors -f json

# Monitor changes in real-time
lldpcli monitor
```

### Docker Deployment for lldpd

```yaml
version: "3.8"
services:
  lldpd:
    image: networkboot/lldpd:latest
    container_name: lldpd-discovery
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_RAW
      - NET_ADMIN
    volumes:
      - ./lldpd.conf:/etc/lldpd.conf:ro
    environment:
      - LLDPD_OPTIONS=-d
    command: ["lldpd", "-d", "-f", "/etc/lldpd.conf"]
```

## SNMP-Based Network Discovery

**SNMP (Simple Network Management Protocol)** discovery tools poll network devices for detailed information about interfaces, routing tables, connected hosts, and device inventory.

### snmpbulkwalk for Network Discovery

```bash
# Install SNMP tools
apt-get install -y snmp snmp-mibs-downloader

# Discover all interfaces on a device
snmpbulkwalk -v2c -c public 10.0.1.1 IF-MIB::ifDescr

# Discover routing table
snmpbulkwalk -v2c -c public 10.0.1.1 IP-MIB::ipRouteDest

# Discover ARP table (connected hosts)
snmpbulkwalk -v2c -c public 10.0.1.1 IP-MIB::ipNetToMediaPhysAddress

# Discover device details
snmpwalk -v2c -c public 10.0.1.1 SNMPv2-MIB::sysDescr.0
snmpwalk -v2c -c public 10.0.1.1 SNMPv2-MIB::sysName.0
snmpwalk -v2c -c public 10.0.1.1 SNMPv2-MIB::sysLocation.0
```

### Automated SNMP Discovery Script

```bash
#!/bin/bash
# network-discovery.sh — SNMP-based network discovery

SUBNET="10.0.1.0/24"
COMMUNITY="public"
SNMP_VERSION="2c"
OUTPUT_DIR="/var/lib/network-discovery"

mkdir -p "$OUTPUT_DIR"

# Scan subnet for live hosts
nmap -sn "$SUBNET" -oG - | grep "Up" | awk '{print $2}' > "$OUTPUT_DIR/live-hosts.txt"

# For each live host, attempt SNMP discovery
while read -r host; do
    echo "Discovering $host..."
    
    # Get device info
    sysname=$(snmpget -v "$SNMP_VERSION" -c "$COMMUNITY" -Oqv "$host"         SNMPv2-MIB::sysName.0 2>/dev/null)
    sysdesc=$(snmpget -v "$SNMP_VERSION" -c "$COMMUNITY" -Oqv "$host"         SNMPv2-MIB::sysDescr.0 2>/dev/null)
    
    if [ -n "$sysname" ]; then
        echo "  Found: $sysname ($sysdesc)"
        echo "$host,$sysname,$sysdesc" >> "$OUTPUT_DIR/discovered-devices.csv"
        
        # Get interface list
        snmpbulkwalk -v "$SNMP_VERSION" -c "$COMMUNITY" "$host"             IF-MIB::ifDescr >> "$OUTPUT_DIR/interfaces-$host.txt" 2>/dev/null
    fi
done < "$OUTPUT_DIR/live-hosts.txt"

echo "Discovery complete. Results in $OUTPUT_DIR/"
```

### SNMP Discovery Docker Setup

```yaml
version: "3.8"
services:
  snmp-discovery:
    image: linuxserver/snmp:latest
    container_name: snmp-discovery-agent
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./snmpd.conf:/etc/snmp/snmpd.conf:ro
      - ./discovery-results:/var/lib/discovery
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
```

## arp-scan — Layer 3 Network Discovery

**arp-scan** is a command-line tool that discovers live hosts on a local network by sending ARP (Address Resolution Protocol) packets and analyzing responses.

### Basic arp-scan Usage

```bash
# Install arp-scan
apt-get install -y arp-scan

# Scan the local subnet
arp-scan --localnet

# Scan a specific subnet
arp-scan 10.0.1.0/24

# Scan with vendor identification
arp-scan --localnet --verbose

# Scan multiple subnets
arp-scan 10.0.1.0/24 10.0.2.0/24 10.0.3.0/24

# Output in machine-readable format
arp-scan --localnet --parsable
```

### Advanced arp-scan Configuration

```bash
# Custom scan with timing options
arp-scan --localnet     --timeout=500     --retry=3     --interval=10     --bandwidth=100000

# Use a custom MAC-to-vendor database
arp-scan --localnet --db=/usr/share/arp-scan/my-custom-oui.txt

# Scan with specific source MAC
arp-scan --localnet --source=00:11:22:33:44:55

# Save results for comparison
arp-scan --localnet --output=/var/lib/arp-scan/latest.txt
```

### Automated arp-scan Discovery Script

```bash
#!/bin/bash
# arp-discovery.sh — Automated ARP-based network discovery

SCAN_INTERVAL=3600  # Run every hour
SUBNET="10.0.1.0/24"
RESULTS_DIR="/var/lib/arp-discovery"
HISTORY_FILE="$RESULTS_DIR/discovery-history.csv"

mkdir -p "$RESULTS_DIR"

# Run scan
arp-scan "$SUBNET" --localnet --parsable > "$RESULTS_DIR/current-scan.txt"

# Compare with previous scan to find new/removed devices
if [ -f "$RESULTS_DIR/previous-scan.txt" ]; then
    new_devices=$(comm -13         <(sort "$RESULTS_DIR/previous-scan.txt")         <(sort "$RESULTS_DIR/current-scan.txt"))
    
    removed_devices=$(comm -23         <(sort "$RESULTS_DIR/previous-scan.txt")         <(sort "$RESULTS_DIR/current-scan.txt"))
    
    if [ -n "$new_devices" ]; then
        echo "NEW DEVICES DETECTED:"
        echo "$new_devices"
        echo "$(date),$new_devices,NEW" >> "$HISTORY_FILE"
    fi
    
    if [ -n "$removed_devices" ]; then
        echo "DEVICES REMOVED:"
        echo "$removed_devices"
        echo "$(date),$removed_devices,REMOVED" >> "$HISTORY_FILE"
    fi
fi

cp "$RESULTS_DIR/current-scan.txt" "$RESULTS_DIR/previous-scan.txt"
```

## Comparison Table

| Feature | lldpd | SNMP Discovery | arp-scan |
|---------|-------|---------------|----------|
| **OSI Layer** | Layer 2 (Link) | Management Layer | Layer 3 (Network) |
| **Discovery scope** | Direct neighbors only | Full network (if SNMP enabled) | Local subnet only |
| **Protocol** | LLDP/CDP/SONMP | SNMP v1/v2c/v3 | ARP |
| **Device details** | Port, chassis, system info | Interfaces, routing, services | MAC + IP only |
| **Authentication** | None (layer 2 protocol) | SNMP community/USM | None required |
| **Switch support** | ✅ Managed switches | ✅ SNMP-enabled devices | ❌ Not needed |
| **Router discovery** | ✅ Via LLDP | ✅ Via SNMP | ✅ Via ARP |
| **Wireless discovery** | ✅ Via LLDP | ✅ Via SNMP MIBs | ✅ Via ARP |
| **Docker support** | ✅ networkboot/lldpd | ✅ linuxserver/snmp | ❌ Needs host network |
| **Active development** | ✅ lldpd project | ✅ Net-SNMP project | ✅ arp-scan project |
| **Best for** | Switch port mapping | Full inventory management | Quick subnet audit |


## Building a Complete Network Discovery Pipeline

For production environments, combine all three discovery methods into an automated pipeline:

```bash
#!/bin/bash
# Complete network discovery pipeline
# 1. ARP scan for all live hosts
# 2. LLDP for switch port mapping
# 3. SNMP for device details

echo "Starting network discovery pipeline..."
arp-scan --localnet --parsable > /var/lib/discovery/hosts.txt
lldpcli show neighbors -f json > /var/lib/discovery/lldp.json
for host in $(cat /var/lib/discovery/hosts.txt | awk '{print $1}'); do
    snmpwalk -v2c -c public "$host" SNMPv2-MIB::sysDescr.0 >> /var/lib/discovery/devices.txt
done
echo "Discovery pipeline complete."
```

## Why Self-Host Your Network Discovery?

Running your own network discovery agents gives you continuous visibility into your infrastructure without depending on cloud-based scanning services. Self-hosted discovery respects network boundaries, doesn't expose your topology to third parties, and works on air-gapped networks where cloud services are unavailable.

For comprehensive network monitoring, combine these discovery tools with our guides on [network flow analysis](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe-guide/) and [network topology discovery](../2026-05-13-self-hosted-network-topology-discovery-cdpwalker-flashroute-treenet-guide/).

## FAQ

### What is LLDP and how does it work?
LLDP (Link Layer Discovery Protocol) is a vendor-neutral protocol (IEEE 802.1AB) that allows network devices to advertise their identity, capabilities, and neighbors on a local area network. Devices send periodic LLDP frames out of each port, and receiving devices store this information in a local MIB (Management Information Base).

### Can lldpd discover devices beyond directly connected neighbors?
No. LLDP only discovers directly connected neighbors (one hop). For multi-hop discovery, you need SNMP-based tools that can query routing tables and ARP caches on intermediate devices.

### What is the difference between LLDP and CDP?
LLDP is an IEEE standard (802.1AB) supported by most vendors. CDP (Cisco Discovery Protocol) is Cisco-proprietary. lldpd can receive and interpret CDP packets from Cisco devices, making it useful in mixed-vendor environments.

### How often does arp-scan need to run?
For continuous monitoring, run arp-scan every 5-15 minutes. For periodic audits, once per hour or once per day is sufficient. The scan itself takes only a few seconds on a typical /24 subnet.

### Is SNMP discovery secure?
SNMP v1 and v2c use plaintext community strings (like passwords), which can be intercepted. SNMP v3 provides encryption and authentication. For production use, always use SNMP v3 with strong authentication. Never use the default "public" community string.

### Can I combine all three discovery methods?
Yes, and you should. LLDP gives you switch port mappings, SNMP gives you detailed device inventory, and arp-scan gives you a complete host list. Together they provide comprehensive network visibility that no single tool can achieve alone.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Discovery Agents: lldpd vs SNMP Discovery vs arp-scan",
  "description": "Compare lldpd, SNMP-based discovery, and arp-scan for self-hosted network discovery — Layer 2 LLDP, SNMP polling, and ARP scanning for complete network visibility.",
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
