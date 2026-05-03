---
title: "CoovaChilli vs pfSense Captive Portal vs MikroTik User Manager: Self-Hosted Captive Portal Guide 2026"
date: 2026-05-03
tags: ["captive-portal", "wifi", "networking", "authentication", "coovachilli", "pfsense", "mikrotik", "self-hosted"]
draft: false
---

Captive portals are the gatekeepers of public and semi-public wireless networks. They intercept unauthenticated users, present a login or acceptance page, and only grant network access after verification. From coffee shops and hotels to corporate guest networks and municipal Wi-Fi, captive portals are ubiquitous — and running them on self-hosted infrastructure keeps user data, authentication logs, and access policies under your control.

This guide compares three leading self-hosted captive portal solutions: **CoovaChilli**, **pfSense Captive Portal**, and **MikroTik User Manager**. Each targets different deployment scenarios, from lightweight hotspot gateways to full-featured router platforms.

## What Is a Captive Portal and Why Self-Host?

A captive portal works by intercepting HTTP traffic from unauthenticated clients and redirecting them to a login page. After successful authentication (password, voucher, social login, or terms acceptance), the client's MAC or IP address is whitelisted for network access.

Self-hosting a captive portal provides:

- **Data privacy**: User authentication data, session logs, and browsing patterns never leave your infrastructure
- **Customization**: Full control over the login page design, authentication methods, and access policies
- **No subscription fees**: Commercial hotspot solutions charge per access point or per user; self-hosted solutions are free
- **Integration**: Connect with your existing RADIUS, LDAP, or billing systems without vendor API limitations

## CoovaChilli: Lightweight Hotspot Gateway

**CoovaChilli** is an open-source access controller for wireless hotspots. It operates as a daemon that intercepts HTTP traffic and enforces authentication via a RADIUS backend. It is the self-hosted successor to the original ChilliSpot project and is widely used in community wireless networks.

### Key Features

- **RADIUS integration** — authenticates against FreeRADIUS or any RADIUS-compatible backend
- **Walled garden** — allow specific domains (payment gateways, DNS) before authentication
- **Bandwidth limiting** — per-user and per-session rate limiting via traffic control
- **Session management** — configurable timeout, idle timeout, and data quotas
- **Splash page customization** — HTML/CSS templates for the login and redirect pages
- **Chillispot protocol compatibility** — drop-in replacement for legacy ChilliSpot deployments
- **Low resource footprint** — runs on minimal hardware (single-core CPU, 128 MB RAM)

### Docker Compose Setup

```yaml
version: "3.8"
services:
  coova-chilli:
    image: coova/chilli:latest
    container_name: coovachilli
    privileged: true
    cap_add:
      - NET_ADMIN
    volumes:
      - ./chilli.conf:/etc/chilli.conf
      - ./www:/var/www/chilli
    network_mode: "host"
    restart: unless-stopped

  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: freeradius
    volumes:
      - ./radius:/etc/raddb
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    restart: unless-stopped

  daloradius:
    image: lscr.io/linuxserver/daloradius:latest
    container_name: daloradius
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    ports:
      - "8080:80"
    volumes:
      - ./daloradius-config:/config
    restart: unless-stopped
```

### CoovaChilli Configuration

```ini
# /etc/chilli.conf
# Basic hotspot configuration

# LAN interface (clients connect here)
dhcpif=eth1

# WAN interface (upstream network)
redir=eth0

# RADIUS server
radiusserver1=127.0.0.1
radiusserver2=127.0.0.1
radiusauthport=1812
radiusacctport=1813
radiussecret=sharedsecret

# Captive portal settings
uamserver=http://10.1.0.1:3990/www/login.html
uamsecret=hotspotsecret
uamlisten=10.1.0.1
uamport=3990

# Walled garden (pre-auth allowed destinations)
uamallowed=www.payment-gateway.com
uamallowed=dns.google.com

# Bandwidth limits (kbps)
downlink=5000
uplink=2000

# Session limits
sessiontimeout=3600
idletimeout=600
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Resource usage | Extremely lightweight; ideal for embedded hardware |
| Authentication | RADIUS-only; no built-in user database |
| Management | Configuration file + web UI via daloRADIUS |
| Scalability | Single node; requires load balancer for multi-AP |
| Ease of deployment | Moderate; requires RADIUS setup |
| Best use case | Community Wi-Fi, guest hotspots, municipal networks |

## pfSense Captive Portal: Enterprise Firewall Integration

**pfSense** is a FreeBSD-based firewall and router platform with a built-in captive portal feature. The captive portal integrates directly with pfSense's firewall rules, authentication backends, and traffic shaping — making it ideal for organizations that already use pfSense as their perimeter firewall.

### Key Features

- **Firewall integration** — captive portal rules map directly to pfSense firewall aliases and rules
- **Multiple authentication backends** — local user database, RADIUS, LDAP, Active Directory, voucher system
- **Voucher system** — generate printable access codes with configurable time and bandwidth limits
- **Traffic shaping** — integrate with pfSense's limiters and DUMMYNET for per-user bandwidth control
- **HTTPS enforcement** — redirect HTTPS traffic via SSL inspection or HTTP-only interception
- **Custom HTML portal** — fully customizable login page with HTML, CSS, and JavaScript
- **RADIUS accounting** — session start/stop records for billing and auditing
- **MAC passthrough** — exempt specific devices from portal authentication

### Deployment

pfSense is deployed as a router/firewall appliance (virtual machine or bare metal). The captive portal is configured through the web interface:

```
Services → Captive Portal
  ├─ Enable on interface (LAN, OPT1, etc.)
  ├─ Authentication method (Local / RADIUS / LDAP / Vouchers)
  ├─ Portal page contents (HTML editor)
  ├─ Allowed IP addresses (walled garden)
  ├─ Concurrent connections limit
  ├─ Idle timeout and hard timeout
  └─ Bandwidth limits (upload/download in kbps)
```

For voucher-based authentication:

```
Services → Captive Portals → Vouchers
  ├─ Create voucher roll (number of codes, validity period)
  ├─ Set bandwidth limits per roll
  ├─ Generate and print vouchers
  └─ Monitor active sessions and redeem codes
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Resource usage | Moderate; requires full pfSense deployment |
| Authentication | Multiple backends: local, RADIUS, LDAP, AD, vouchers |
| Management | Web UI; integrated with firewall management |
| Scalability | Single node; CARP HA for failover |
| Ease of deployment | Low; built into pfSense, no additional setup |
| Best use case | Office guest Wi-Fi, hotel networks, schools |

## MikroTik User Manager: RouterOS Hotspot System

**MikroTik User Manager** (UserMan) is a RADIUS server and captive portal management system built into RouterOS. It provides hotspot authentication, user management, bandwidth profiles, and billing integration — all configurable through WinBox, WebFig, or the CLI.

### Key Features

- **Hotspot server** — built-in HTTP/HTTPS captive portal with customizable login pages
- **User Manager RADIUS** — integrated RADIUS server for authentication and accounting
- **Bandwidth profiles** — per-user rate limiting with burst allowance
- **Walled garden** — allow specific hosts before authentication
- **User groups** — assign bandwidth and time limits via group membership
- **Trial mode** — time-limited access without authentication for new users
- **API access** — REST-like API for integration with external billing systems
- **Routers as NAS** — any MikroTik router can act as a Network Access Server

### RouterOS Configuration

```routeros
# Configure the Hotspot server on ether2 (client-facing interface)
/ip hotspot add interface=ether2 address-pool=hotspot-pool \
    idle-timeout=10m login-by=http-chap,http-pap

# Set up the hotspot IP pool
/ip pool add name=hotspot-pool ranges=10.5.50.2-10.5.50.254

# Create a DHCP server for hotspot clients
/ip dhcp-server add name=hotspot-dhcp interface=ether2 \
    address-pool=hotspot-pool lease-time=1h

# Define bandwidth profiles
/user-manager/profile add name="basic-5mb" \
    rate-limit="5M/1M" shared-users=1

# Create a user with the profile
/user-manager/user add name="guest001" password="welcome2026" \
    profile=basic-5mb disabled=no

# Configure walled garden for pre-auth access
/ip hotspot walled-garden add action=allow \
    dst-host=www.payment-provider.com
/ip hotspot walled-garden add action=allow \
    dst-host=fonts.googleapis.com

# Set up trial access (15 minutes free)
/ip hotspot set [find] trial=15m trial-uptime=5m
```

### Strengths and Limitations

| Aspect | Assessment |
|--------|-----------|
| Resource usage | Low; runs on MikroTik RouterBOARD hardware |
| Authentication | Built-in user database + RADIUS client/server |
| Management | WinBox (GUI), WebFig, CLI, API |
| Scalability | Single router; multi-router with RADIUS centralization |
| Ease of deployment | Low for MikroTik users; requires RouterOS familiarity |
| Best use case | ISP hotspots, small business Wi-Fi, managed networks |

## Comparison: CoovaChilli vs pfSense vs MikroTik User Manager

| Feature | CoovaChilli | pfSense Captive Portal | MikroTik User Manager |
|---------|-------------|----------------------|----------------------|
| **Deployment model** | Daemon on Linux | Integrated in pfSense | Built into RouterOS |
| **Authentication** | RADIUS only | Local, RADIUS, LDAP, AD, Vouchers | Local + RADIUS |
| **Voucher system** | Via daloRADIUS | Built-in | Built-in (UserMan) |
| **Bandwidth limiting** | Traffic control (tc) | pfSense limiters | RouterOS queues |
| **Walled garden** | Yes | Yes | Yes |
| **Session timeout** | Configurable | Configurable | Configurable |
| **Trial access** | No | No | Yes |
| **Web UI management** | Via daloRADIUS | pfSense WebConfigurator | WebFig / WinBox |
| **REST API** | No | pfSense API | RouterOS API |
| **High availability** | External load balancer | CARP | VRRP |
| **Hardware requirements** | Minimal (128 MB RAM) | Moderate (1 GB RAM) | MikroTik RouterBOARD |
| **License** | GPL | BSD | MikroTik License (free tier) |
| **Best for** | Community Wi-Fi, embedded | Enterprise guest networks | ISP hotspots, small business |

## Why Self-Host Your Captive Portal?

**Privacy compliance**: Self-hosted captive portals keep all user authentication data, session logs, and MAC address records on-premises. This simplifies GDPR and data protection compliance by eliminating third-party data processing.

**Brand control**: Customize the login page to match your organization's branding without the watermarks or limitations imposed by commercial hotspot providers.

**Cost efficiency**: Commercial captive portal solutions charge $5–$50 per access point per month. Self-hosted solutions on commodity hardware or existing routers have no recurring licensing costs.

**Integration flexibility**: Connect with your existing billing systems, CRM, or membership databases without being limited by a vendor's API or integration catalog.

For broader network security context, see our [firewall and router comparison](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide/) and [intrusion prevention guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). If you need RADIUS authentication for your captive portal, our [FreeRADIUS vs Daloradius guide](../2026-04-24-teampass-vs-syspass-vs-passky-self-hosted-password-vault-guide/) covers password management for network access credentials.

## FAQ

### What is the difference between a captive portal and a RADIUS server?

A captive portal intercepts unauthenticated HTTP traffic and presents a login page. A RADIUS server handles the actual authentication, authorization, and accounting (AAA). CoovaChilli requires a separate RADIUS server (like FreeRADIUS), while pfSense and MikroTik include built-in RADIUS capabilities.

### Can CoovaChilli handle HTTPS traffic interception?

CoovaChilli intercepts HTTP (port 80) traffic. HTTPS traffic cannot be redirected without a man-in-the-middle proxy, which breaks certificate validation. Most modern captive portals use a combination of DNS redirection and HTTP interception, with clients prompted to visit a non-HTTPS URL for authentication.

### How does the pfSense voucher system work?

Vouchers are time-limited access codes generated in batches. Each voucher has a configurable validity period (e.g., 1 hour, 1 day, 1 week) and can be associated with bandwidth limits. Users enter the voucher code on the captive portal page to gain access.

### Does MikroTik User Manager require a separate license?

User Manager is included free with RouterOS for up to 10 active users. Beyond that, a level 4 or higher RouterOS license is required, which is a one-time purchase (no subscription).

### Can I use social login (Google, Facebook) with these solutions?

pfSense supports custom HTML portals, so you can integrate OAuth social login via custom scripting. CoovaChilli requires a custom login page with OAuth integration. MikroTik User Manager supports custom login pages but OAuth integration requires external scripting.

### How do I handle client isolation on the wireless network?

Client isolation is configured on the access point or wireless controller, not the captive portal. Enable AP isolation (also called "client isolation" or "AP isolation") to prevent authenticated clients from communicating with each other while still allowing internet access.

### What bandwidth should I allocate per hotspot user?

For guest Wi-Fi, 1–5 Mbps download and 512 Kbps–1 Mbps upload per user is typical. For paid hotspots, 10–50 Mbps depending on the service tier. Adjust based on your total available bandwidth and expected concurrent users.

### Can these solutions support MAC address authentication?

Yes. All three support MAC passthrough — whitelisting specific MAC addresses to bypass the captive portal. This is useful for printers, IoT devices, or VIP users who should not see the login page.

### How many concurrent users can each solution handle?

CoovaChilli can handle hundreds of concurrent users on modest hardware. pfSense depends on the underlying hardware but typically supports 500–2000 concurrent sessions. MikroTik RouterBOARD devices vary by model, with higher-end units supporting 500+ concurrent hotspot users.

### Can I integrate these with a payment gateway for paid Wi-Fi?

pfSense and CoovaChilli (via daloRADIUS) support custom payment gateway integration through their web portals. MikroTik User Manager has a REST API that can be connected to external payment systems for automated voucher generation and billing.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "CoovaChilli vs pfSense Captive Portal vs MikroTik User Manager: Self-Hosted Captive Portal Guide 2026",
  "description": "Compare three self-hosted captive portal solutions for guest Wi-Fi and hotspot management. Covers CoovaChilli, pfSense Captive Portal, and MikroTik User Manager with configuration examples and Docker Compose setups.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
