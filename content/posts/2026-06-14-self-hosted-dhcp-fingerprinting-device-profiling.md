---
title: "Self-Hosted DHCP Fingerprinting & Network Device Profiling: Fingerbank vs DHCP Explorer vs PacketFence Integration"
date: "2026-06-14"
tags: ["dhcp", "network-security", "nac", "device-profiling", "fingerbank", "fingerprinting", "network-access-control"]
draft: false
---

## Introduction

Every device that connects to a network reveals its identity through subtle clues in DHCP requests, HTTP User-Agent headers, MAC address OUI prefixes, and mDNS broadcasts. DHCP fingerprinting captures these signatures to identify device types — distinguishing an iPhone from an Android, a printer from a VoIP phone, or an IoT sensor from a rogue laptop. This intelligence powers network access control (NAC), asset inventory, and security incident response.

This guide compares three open-source approaches: **Fingerbank** (the open-source DHCP fingerprint database), **DHCP Explorer** (real-time device discovery and profiling), and **PacketFence NAC integration** (full network access control with fingerprinting).

## Comparison Table

| Feature | Fingerbank | DHCP Explorer | PacketFence |
|---------|-----------|---------------|-------------|
| **Primary Role** | Fingerprint database | Real-time device discovery | Full NAC platform |
| **Deployment Type** | API + local collector | Standalone agent | Complete NAC server |
| **Fingerprint Coverage** | 3,500+ device profiles | Real-time MAC + DHCP analysis | Integrated Fingerbank + custom |
| **Web Interface** | Community web portal | Built-in dashboard | Full management console |
| **NAC Integration** | API for third-party NAC | None (standalone) | Native (RADIUS, 802.1X, VLAN) |
| **VLAN Enforcement** | Via external NAC | No | Yes (SNMP, RADIUS CoA) |
| **Captive Portal** | No | No | Yes |
| **Docker Support** | Yes | Community Dockerfile | Official Docker images |
| **Scalability** | 100,000+ devices | 1,000 devices (single node) | 100,000+ devices |
| **Learning Curve** | Low (API client) | Low | High (full NAC) |

## Fingerbank: The Open-Source DHCP Fingerprint Database

Fingerbank is the collective intelligence behind device fingerprinting — a community-maintained database that maps DHCP fingerprint patterns to specific device types, operating systems, and vendors.

### How DHCP Fingerprinting Works

When a device requests an IP address via DHCP, the DHCPDISCOVER packet includes Option 55 (Parameter Request List) — an ordered list of DHCP options the device wants. The specific combination and ordering of these options creates a unique fingerprint:

```
# iPhone running iOS 17
DHCP Option 55: 1,3,6,15,119,252,95,44,46

# Android 14 device  
DHCP Option 55: 1,3,6,15,26,28,51,58,59,43

# Windows 11 laptop
DHCP Option 55: 1,15,3,6,44,46,47,31,33,121,249,43,252
```

### Setting Up Fingerbank Collector

```yaml
version: "3.8"
services:
  fingerbank-collector:
    image: inverseinc/fingerbank-collector:latest
    container_name: fingerbank
    environment:
      FINGERBANK_API_KEY: "your-api-key"
      COLLECTOR_INTERFACE: "eth0"
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./fingerbank-data:/usr/local/fingerbank/data
    restart: unless-stopped
```

The collector passively captures DHCP traffic, extracts fingerprints, and queries the Fingerbank API to identify devices. Results are stored locally and can be queried via REST API.

### Querying the Fingerbank API

```python
import requests

def lookup_device(mac_address, dhcp_fingerprint):
    response = requests.post(
        "https://api.fingerbank.org/api/v2/combinations/interrogate",
        json={
            "dhcp_fingerprint": dhcp_fingerprint,
            "mac": mac_address,
            "api_key": "your-api-key"
        }
    )
    data = response.json()
    return {
        "device_name": data.get("device", {}).get("name", "Unknown"),
        "device_type": data.get("device", {}).get("type", "Unknown"),
        "os": data.get("device", {}).get("operating_system", "Unknown"),
        "score": data.get("score", 0)  # confidence 0-100
    }

# Example: identify a device
result = lookup_device(
    "aa:bb:cc:dd:ee:ff",
    "1,3,6,15,119,252,95,44,46"
)
print(f"Device: {result['device_name']} ({result['device_type']})")
print(f"OS: {result['os']} | Confidence: {result['score']}%")
```

## DHCP Explorer: Real-Time Device Discovery

DHCP Explorer is a lightweight tool that combines DHCP packet capture, MAC OUI lookup, mDNS snooping, and HTTP User-Agent analysis to build a real-time inventory of devices on your network.

### Deployment

```bash
# Install DHCP Explorer
git clone https://github.com/network-device-profiling/dhcp-explorer.git
cd dhcp-explorer

# Run with Docker
docker run -d \
  --name dhcp-explorer \
  --network host \
  --cap-add NET_ADMIN \
  --cap-add NET_RAW \
  -v $(pwd)/data:/app/data \
  dhcp-explorer:latest
```

### Device Profile Output

DHCP Explorer aggregates multiple fingerprint sources:

```
Device: 192.168.1.105 (aa:bb:cc:dd:ee:ff)
├── MAC OUI: Apple, Inc.
├── DHCP Fingerprint: iOS 17.x (confidence: 95%)
├── mDNS: "John's iPhone._apple-mobdev2._tcp.local"
├── HTTP User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)
├── Hostname: Johns-iPhone
└── Device Type: Smartphone / Apple iPhone
```

## PacketFence: Full NAC Integration

PacketFence is a comprehensive open-source NAC that integrates Fingerbank for device profiling, then automatically enforces network access policies based on device identity.

### PacketFence with Fingerbank Integration

```yaml
version: "3.8"
services:
  packetfence:
    image: inverseinc/packetfence:latest
    container_name: packetfence
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - SYS_ADMIN
    environment:
      PF_DB_HOST: "postgres"
      PF_DB_NAME: "packetfence"
      PF_DB_USER: "pf"
      PF_DB_PASS: "secure-password"
      FINGERBANK_API_KEY: "your-api-key"
    volumes:
      - ./pf-conf:/usr/local/pf/conf
      - ./pf-logs:/usr/local/pf/logs
    restart: unless-stopped

  postgres:
    image: postgres:15
    container_name: pf-db
    environment:
      POSTGRES_DB: packetfence
      POSTGRES_USER: pf
      POSTGRES_PASSWORD: "secure-password"
    volumes:
      - ./pgdata:/var/lib/postgresql/data
```

### Automated VLAN Assignment by Device Type

With PacketFence, you can define policies that automatically assign VLANs based on Fingerbank device profiles:

```
# PacketFence configuration: /usr/local/pf/conf/switch.conf
[switch 192.168.1.1]
type = Cisco::Catalyst_2960
mode = production

# VLAN assignment rules in firewall rules
# IoT devices → isolated VLAN
# Corporate laptops → secure VLAN
# Unknown devices → captive portal / guest VLAN
```

## Why Self-Host DHCP Fingerprinting?

Every unmanaged device on your network is a potential security risk. DHCP fingerprinting gives you visibility into what's actually connected — not just IP addresses, but device types, operating systems, and manufacturers. This matters because manual asset inventory is always out of date; fingerprinting runs continuously and catches new devices the moment they request an IP address.

For network security teams, integrating DHCP fingerprints with NAC (see our [NAC guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/)) creates an automated enforcement pipeline: identify the device, classify the risk, and apply the appropriate network policy — all without human intervention. An unknown IoT camera gets isolated to a VLAN with no internet access; a known corporate laptop gets full access.

For IT operations, continuous device profiling eliminates spreadsheet-based inventory management. When the security team asks "how many unmanaged IoT devices are on the manufacturing VLAN?", you have the answer in seconds, not days. The combination of DHCP fingerprints (see our [DHCP server guide](../2026-05-04-self-hosted-dhcp-server-management-kea-dnsmasq-isc-dhcp-guide/)) with MAC OUI and mDNS analysis provides overlapping signals that make device identification robust against spoofing.

For compliance-focused organizations, device profiling provides audit evidence: which devices were on the network, when, and whether they matched expected profiles. This is critical for PCI DSS, HIPAA, and SOC 2 requirements that mandate network device inventory and access control.

## Multi-Factor Device Profiling: Beyond DHCP

Relying on DHCP fingerprinting alone has limitations — devices behind NAT, statically configured IPs, and dual-stack IPv6 hosts may not generate clean DHCP fingerprints. A robust device profiling strategy combines multiple data sources:

**MAC OUI Lookup**: The first three bytes of a MAC address identify the manufacturer (the Organizationally Unique Identifier). The IEEE maintains the official registry, and the Wireshark OUI database provides an open-source lookup. While not sufficient alone (a Raspberry Pi can spoof any MAC), it provides a baseline signal that's free to collect.

**HTTP User-Agent Analysis**: When devices browse the web or hit a captive portal, their User-Agent string reveals the browser, OS version, and device model. Tools like DHCP Explorer passively capture these from HTTP traffic. A User-Agent of `Mozilla/5.0 (Linux; Android 14; Pixel 8)` tells you far more than a DHCP fingerprint alone.

**mDNS and SSDP Snooping**: Multicast DNS (Bonjour/Avahi) and SSDP broadcasts are goldmines for device identification. An Apple TV announces itself via `_appletv._tcp.local`, a printer via `_ipp._tcp.local`, and a NAS via `_smb._tcp.local`. These protocol-level announcements are hard to suppress and even harder to spoof convincingly across multiple services.

**SNMP System Description**: For managed switches, routers, and printers, an SNMP GET of `sysDescr` (OID 1.3.6.1.2.1.1.1.0) returns the vendor, model, and firmware version. Combined with LLDP neighbor information, you can build a complete topology map with device roles.

**TLS Fingerprinting (JA3/JA4)**: When devices establish TLS connections, the Client Hello packet reveals the TLS version, cipher suites, and extensions — creating a JA3 fingerprint that identifies the TLS client library and often the specific application. This is particularly useful for identifying IoT devices that use TLS for API calls but don't generate DHCP traffic once provisioned.

The power of multi-factor profiling is that no single signal needs to be trustworthy. A device that claims to be an Apple iPhone via DHCP but has a Dell MAC OUI and sends no mDNS broadcasts is immediately suspicious — and PacketFence can automatically isolate it.


## FAQ

### What makes a good DHCP fingerprint?

A good DHCP fingerprint comes from DHCP Option 55 (Parameter Request List) — the specific set and ordering of DHCP options a device requests. Since different operating systems and device classes request different option sets in different orders, this creates a distinctive signature. Additional signals include DHCP Option 60 (Vendor Class Identifier) and the Hostname option.

### Can DHCP fingerprints be spoofed?

Yes, a determined attacker can modify their device's DHCP client to mimic another fingerprint. However, combining DHCP fingerprinting with MAC OUI lookup, HTTP User-Agent analysis, and mDNS snooping creates multiple overlapping signals that are much harder to spoof simultaneously. PacketFence's multi-factor profiling approach makes evasion significantly more difficult.

### How often is the Fingerbank database updated?

The Fingerbank community database is continuously updated as users contribute new device fingerprints. Major device releases (new iOS, Android, Windows versions) are typically fingerprinted within days of release. You can also add custom local fingerprints for devices unique to your environment.

### Does DHCP fingerprinting work with DHCP relay?

Yes, but the relay agent adds its own IP to the DHCP packet, which can obscure the original device's subnet information. Most collectors are designed to handle relayed DHCP traffic — just ensure your collector sees the traffic between the relay agent and the DHCP server.

### Can I use Fingerbank without PacketFence?

Absolutely. Fingerbank provides a REST API that any application can query. You can integrate it with custom scripts, your own NAC, a SIEM, or an asset management system. The Fingerbank collector is also available as a standalone Docker container that exports device profiles in JSON format.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DHCP Fingerprinting & Network Device Profiling: Fingerbank vs DHCP Explorer vs PacketFence Integration",
  "description": "Compare three open-source approaches to DHCP fingerprinting for network device identification: Fingerbank fingerprint database, DHCP Explorer real-time discovery, and PacketFence full NAC integration with automated VLAN enforcement.",
  "datePublished": "2026-06-14",
  "dateModified": "2026-06-14",
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
