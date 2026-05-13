---
title: "Self-Hosted Network Access Control — PacketFence vs OpenNAC vs Gatekeeper"
date: "2026-05-13"
tags: ["networking", "security", "nac", "self-hosted", "comparison", "guide"]
draft: false
description: "Compare self-hosted Network Access Control (NAC) solutions — PacketFence, OpenNAC, and Gatekeeper. Learn to secure your network with device authentication, captive portals, and 802.1X enforcement."
---

Every device that connects to your network is a potential entry point for attackers. Network Access Control (NAC) ensures that only authorized, compliant devices can access your network resources. Enterprise NAC solutions from Cisco (ISE), Aruba (ClearPass), and Fortinet cost tens of thousands of dollars. This guide covers powerful **open-source, self-hosted alternatives** that deliver comparable security at zero licensing cost.

## What Is Network Access Control?

Network Access Control (NAC) is a security approach that restricts network access based on device identity, health status, and user authentication. NAC systems enforce policies like:

- **Device registration** — new devices must be approved before accessing the network
- **802.1X authentication** — port-level authentication for wired and wireless networks
- **Compliance checking** — verify devices have up-to-date antivirus, patches, and configurations
- **Role-based access** — assign different network privileges based on device type and user role
- **Captive portals** — web-based authentication for guest and BYOD devices
- **Quarantine** — isolate non-compliant devices in a restricted network segment

## Comparison Table

| Feature | PacketFence | OpenNAC | Gatekeeper |
|---------|-------------|---------|------------|
| **Stars** | 1,623+ | N/A (FreeRADIUS-based) | 17+ |
| **Language** | Perl/JS | FreeRADIUS + Python | Go |
| **802.1X Support** | Full | Full | Basic |
| **Captive Portal** | Built-in | Via components | Basic |
| **BYOD Management** | Comprehensive | Basic | Simple |
| **Device Fingerprinting** | Yes | Limited | No |
| **VLAN Assignment** | Dynamic | Dynamic | Static |
| **Integration** | Active Directory, LDAP, RADIUS | FreeRADIUS, LDAP | LDAP |
| **Web UI** | Full admin portal | Limited | Minimal |
| **Docker Support** | Available | Manual | Available |
| **Best For** | Enterprise NAC | Custom FreeRADIUS setups | Simple self-hosted services |

## PacketFence

**GitHub:** [inverse-inc/packetfence](https://github.com/inverse-inc/packetfence) (1,623+ stars)

PacketFence is the most comprehensive open-source NAC solution available. Developed by Inverse Inc. (the same company behind SOGo), it supports wired, wireless, and VPN access control with a rich feature set that rivals commercial products.

### Key Features

- **Multi-tenant support** — manage multiple organizations from a single instance
- **Device fingerprinting** — identify device types via DHCP fingerprinting, SNMP, and passive analysis
- **802.1X with EAP-TLS/PEAP/TTLS** — full port-based authentication
- **Captive portal** — customizable web portal for guest and BYOD registration
- **Integration with Active Directory, LDAP, SAML** — enterprise identity sources
- **REST API** — programmatic management and automation
- **Reporting and compliance** — audit trails and compliance reports

### Docker Compose

```yaml
version: "3.8"
services:
  packetfence:
    image: inverseinc/packetfence:latest
    container_name: packetfence
    network_mode: host
    privileged: true
    volumes:
      - /etc/packetfence:/usr/local/pf/conf
      - /var/lib/packetfence:/usr/local/pf/var
      - /var/log/packetfence:/usr/local/pf/log
    environment:
      - PF_DOMAIN=example.com
      - PF_ADMIN_USER=admin
      - PF_ADMIN_PASSWORD=changeme
    restart: unless-stopped
```

### Installation (Native)

```bash
# Debian/Ubuntu
apt update
apt install packetfence

# The installer configures:
# - FreeRADIUS for 802.1X authentication
# - Apache for captive portal
# - MariaDB for policy storage
# - SNMP for network device communication

# Access web UI at https://<server>:1443
```

### Configuration Workflow

1. **Define network equipment** — add switches, APs, and routers with SNMP credentials
2. **Configure connection profiles** — specify authentication methods per network segment
3. **Set up registration** — configure captive portal or 802.1X for device onboarding
4. **Define policies** — create rules for compliance checking and access levels
5. **Monitor and enforce** — use the dashboard to track connected devices and policy violations

### When to Use PacketFence

- **Enterprise environments** — full-featured NAC with AD integration
- **BYOD programs** — comprehensive device registration and compliance
- **Guest access management** — professional captive portal with sponsor workflows
- **Compliance requirements** — audit trails and reporting for regulations

## OpenNAC (FreeRADIUS-Based NAC)

OpenNAC refers to building a NAC system using **FreeRADIUS** as the authentication engine combined with network switch configuration for 802.1X enforcement. This approach gives you maximum flexibility and control.

### Core Architecture

```
[Client Device] --802.1X--> [Switch/AP] --RADIUS--> [FreeRADIUS Server]
                                                        |
                                                        v
                                                  [LDAP/AD/Database]
```

### FreeRADIUS Configuration for 802.1X

```bash
# Install FreeRADIUS
apt install freeradius freeradius-utils

# Configure clients (switches/APs) in /etc/freeradius/3.0/clients.conf
client switch-01 {
    ipaddr = 192.168.1.10
    secret = radius_secret_here
    shortname = access-switch-01
}

# Configure EAP in /etc/freeradius/3.0/mods-enabled/eap
eap {
    default_eap_type = peap
    timer_expire = 60
    ignore_unknown_eap_types = no
    
    tls-config tls-common {
        private_key_file = /etc/freeradius/3.0/certs/server.key
        certificate_file = /etc/freeradius/3.0/certs/server.pem
        ca_file = /etc/freeradius/3.0/certs/ca.pem
    }
}
```

### Dynamic VLAN Assignment

```bash
# /etc/freeradius/3.0/users
# Assign VLANs based on user group
DEFAULT Group == "employees"
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-Id = "100"

DEFAULT Group == "guests"
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-Id = "200"

DEFAULT Group == "iot-devices"
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-Id = "300"
```

### Docker Compose for FreeRADIUS

```yaml
version: "3.8"
services:
  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: freeradius
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    volumes:
      - ./freeradius-config:/etc/raddb
    restart: unless-stopped
```

### When to Use OpenNAC

- **Custom NAC requirements** — build exactly what you need with FreeRADIUS modules
- **Budget-conscious deployments** — zero licensing cost, only hardware needed
- **Learning NAC concepts** — understand the underlying protocols by configuring them
- **Smaller networks** — where PacketFence's full feature set is overkill

## Gatekeeper

**GitHub:** [Tomasinjo/gatekeeper](https://github.com/Tomasinjo/gatekeeper) (17+ stars)

Gatekeeper is a simple, modern network access control system designed specifically for self-hosted services. It provides a lightweight alternative to full NAC platforms, focusing on controlling access to individual services rather than entire network segments.

### How It Works

Gatekeeper acts as a reverse proxy that authenticates users before granting access to backend services:

```
[User] --> [Gatekeeper (Auth Proxy)] --> [Protected Service]
                        |
                        v
                  [LDAP/OIDC Provider]
```

### Installation

```bash
# Clone and build
git clone https://github.com/Tomasinjo/gatekeeper.git
cd gatekeeper
go build -o gatekeeper

# Or use Docker
docker pull tomasinjo/gatekeeper:latest
```

### Configuration

```yaml
# config.yaml
server:
  listen: ":8080"
  
auth:
  provider: ldap
  ldap:
    url: "ldap://ldap.example.com:389"
    base_dn: "dc=example,dc=com"
    user_search_filter: "(uid=%s)"
    
services:
  - name: "Grafana"
    url: "http://grafana.internal:3000"
    path: "/grafana"
    required_groups: ["monitoring-team"]
    
  - name: "Jenkins"
    url: "http://jenkins.internal:8080"
    path: "/jenkins"
    required_groups: ["dev-team", "ops-team"]
```

### When to Use Gatekeeper

- **Self-hosted service protection** — control access to individual web applications
- **Small teams** — lightweight authentication without full NAC overhead
- **Microservices environments** — per-service access control
- **Homelabs** — simple, easy-to-understand access management

## Why Self-Host Your Network Access Control?

### Zero Licensing Cost

Commercial NAC solutions charge per port or per device. Cisco ISE costs $50-150 per endpoint, Aruba ClearPass $40-100 per device. PacketFence provides equivalent functionality with no per-device licensing — your only cost is the server hardware.

### Complete Visibility Into Every Connected Device

Self-hosted NAC gives you a real-time inventory of every device on your network: who connected, when, from which port, and what access level they received. This visibility is critical for security incident response and compliance auditing.

### Policy Enforcement at the Network Edge

Unlike firewalls that filter traffic after it enters the network, NAC enforces policies at the point of connection. Unauthorized devices never reach your internal network — they're either blocked entirely or placed in a quarantine VLAN.

```bash
# Example: Quarantine VLAN configuration
# Switch port goes to VLAN 999 (quarantine) when 802.1X fails
interface GigabitEthernet0/1
  authentication port-control auto
  authentication event fail action authorize vlan 999
  authentication event no-response action authorize vlan 999
```

### Integration With Existing Infrastructure

Self-hosted NAC integrates with your existing LDAP/Active Directory, SIEM, ticketing systems, and configuration management tools. No proprietary APIs or vendor lock-in.

## Building a Complete Network Security Stack

NAC is one layer of a defense-in-depth strategy. After controlling network access at the edge, protect traffic with firewall rules ([firewall management guide](../2026-05-08-self-hosted-firewall-management-firehol-shorewall-ferm-guide/)), authenticate services with proper identity providers ([OIDC SSO guide](../2026-04-25-dex-vs-kanidm-vs-rauthy-self-hosted-oidc-sso-guide-2026/)), and secure email with authentication protocols ([email authentication guide](../2026-05-18-self-hosted-email-authentication-opendkim-rspamd-opendmarc/)).

## Choosing the Right NAC Solution

| Scenario | Recommended Solution | Reason |
|----------|---------------------|--------|
| Enterprise with 500+ devices | PacketFence | Full-featured, multi-tenant, AD integration |
| Small office (50-200 devices) | FreeRADIUS-based NAC | Flexible, cost-effective, sufficient features |
| Homelab / small team | Gatekeeper | Lightweight, simple configuration |
| Guest/BYOD management | PacketFence | Best-in-class captive portal |
| Custom authentication flows | FreeRADIUS-based NAC | Unlimited module flexibility |

## FAQ

### What is 802.1X and why is it important for NAC?

802.1X is an IEEE standard for port-based Network Access Control. It requires devices to authenticate before the switch port or wireless AP grants network access. Unlike MAC address filtering (easily spoofed), 802.1X uses cryptographic authentication (EAP-TLS certificates or PEAP username/password). It's the foundation of enterprise NAC — without it, you can only control access at the firewall level, not at the network edge.

### Can PacketFence replace Cisco ISE?

For most use cases, yes. PacketFence supports 802.1X authentication, captive portals, device fingerprinting, BYOD management, VLAN assignment, and Active Directory integration — the core features of Cisco ISE. The main differences are: PacketFence lacks Cisco's Threat-Centric NAC (integration with Cisco security products), has a steeper learning curve, and community support versus enterprise SLA. For organizations without existing Cisco security investments, PacketFence is a viable alternative.

### How do I handle devices that don't support 802.1X?

Many devices (printers, IoT sensors, cameras) don't support 802.1X. NAC systems handle these through **MAC Authentication Bypass (MAB)** — the device's MAC address is checked against an authorized list. In PacketFence, register the device through the admin portal or a self-registration workflow. In FreeRADIUS, add MAC addresses to the users file:

```
"AA:BB:CC:DD:EE:FF" Auth-Type := Accept
    Tunnel-Type = VLAN,
    Tunnel-Private-Group-Id = "300"
```

### Is a captive portal secure enough for guest access?

Captive portals are suitable for guest access when combined with VLAN isolation. Guests authenticate via the portal and are placed in a guest VLAN that has Internet access but no access to internal resources. For higher security, require sponsor approval (an internal user must approve each guest registration) and set time-limited access that expires automatically.

### How does device fingerprinting work in NAC?

Device fingerprinting identifies device types by analyzing network behavior patterns: DHCP option fingerprints (different OS send different DHCP options), HTTP user-agent strings, SNMP system descriptions, MAC address OUI lookups, and passive traffic analysis. PacketFence combines multiple techniques for accurate identification — distinguishing between Windows laptops, iPhones, Android phones, printers, and IoT devices. This enables automatic policy assignment: printers go to the printer VLAN, phones get VoIP priority, unknown devices get quarantined.

### Can NAC protect against insider threats?

NAC provides several layers of insider threat protection: it prevents unauthorized devices from connecting to the network, limits access based on user role (principle of least privilege), quarantines non-compliant devices (missing patches, disabled antivirus), and provides audit logs of all connection events. However, NAC alone isn't sufficient — combine it with endpoint detection, DLP (Data Loss Prevention), and user behavior analytics for comprehensive insider threat protection.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Network Access Control — PacketFence vs OpenNAC vs Gatekeeper",
  "description": "Compare self-hosted Network Access Control (NAC) solutions — PacketFence, OpenNAC, and Gatekeeper. Learn to secure your network with device authentication, captive portals, and 802.1X enforcement.",
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
