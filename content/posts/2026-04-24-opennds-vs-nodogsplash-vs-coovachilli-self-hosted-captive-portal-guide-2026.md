---
title: "openNDS vs Nodogsplash vs CoovaChilli: Best Self-Hosted Captive Portal 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "networking", "captive-portal", "wifi"]
draft: false
description: "Compare openNDS, Nodogsplash, and CoovaChilli — the top open-source captive portal solutions for guest WiFi, hotspot authentication, and network access control in 2026."
---

A captive portal is the web page users see when they first connect to a network — requiring authentication, agreement to terms of service, or payment before granting full Internet access. You encounter them daily: hotel WiFi logins, airport hotspot sign-ups, coffee shop splash pages, and guest network portals at offices.

Commercial captive portal solutions charge per-user or per-device licensing fees. For homelabs, small businesses, hotels, and community networks, open-source alternatives deliver the same functionality at zero cost, with full control over the authentication flow and data privacy.

This guide compares three leading open-source captive portal projects: **openNDS**, **Nodogsplash**, and **CoovaChilli** — covering features, installation, configuration, and real-world deployment scenarios.

## Why Self-Host a Captive Portal?

Running your own captive portal gives you advantages that cloud-hosted alternatives cannot match:

- **No vendor lock-in** — your authentication data, user sessions, and policies stay on your infrastructure
- **Zero per-user licensing** — unlimited concurrent users regardless of scale
- **Custom branding** — full control over the splash page, logo, colors, and messaging
- **Offline operation** — works without an upstream Internet connection for local authentication
- **Lightweight footprint** — these tools run on devices with as little as 16 MB RAM (OpenWRT routers)
- **Regulatory compliance** — keep user data on-premises to meet GDPR or local data sovereignty requirements

For homelab operators, a self-hosted captive portal adds a professional touch to guest WiFi networks. For businesses and venues, it enables terms-of-service acceptance, usage monitoring, and bandwidth management without recurring SaaS fees.

## How Captive Portals Work

All three tools use the same fundamental architecture:

1. **Interception** — iptables/nftables rules redirect HTTP traffic from unauthenticated clients to the captive portal
2. **Authentication** — users interact with a splash page (login, click-through, token entry, or OAuth)
3. **Authorization** — the portal updates firewall rules to grant the client's MAC address or IP full network access
4. **Session management** — timers, bandwidth limits, and idle timeouts enforce usage policies
5. **Termination** — sessions expire and firewall rules are restored to the pre-authentication state

The key difference between these projects lies in their **authentication architecture** and **extensibility** — how they handle the login process and integrate with external systems.

## Project Comparison

| Feature | openNDS | Nodogsplash | CoovaChilli |
|---|---|---|---|
| **GitHub Stars** | 459 | 935 | 591 |
| **Language** | C | C | C |
| **Last Updated** | April 2026 | January 2026 | April 2026 |
| **License** | GPL-2.0 | GPL-2.0 | GPL-2.0 |
| **RAM Usage** | ~2 MB | ~1 MB | ~8 MB |
| **RADIUS Support** | External FAS | No | Built-in |
| **OAuth/Social Login** | Via FAS | No | Via RADIUS/external |
| **Bandwidth Limiting** | Yes (iptables) | Yes (iptables) | Yes (built-in) |
| **Session Timeout** | Yes | Yes | Yes |
| **Idle Timeout** | Yes | Yes | Yes |
| **Walled Garden** | Yes | Yes | Yes |
| **Token Auth** | Yes | Yes | Yes |
| **Click-through** | Yes | Yes | Yes |
| **User Registration** | Via FAS | No | Via RADIUS/external |
| **Accounting** | Via FAS | Basic | Full RADIUS accounting |
| **OpenWRT Support** | First-class | First-class | Via packages |
| **Docker Support** | Community | Community | Community |
| **Best For** | Production deployments | Simple deployments | Enterprise/hotel use |

### openNDS

[openNDS](https://github.com/opennds/opennds) (open Network Demarcation Service) is the most actively maintained of the three projects, with a commit as recently as April 2026. It is a fork of Nodogsplash that has diverged significantly, adding a **Forward Authentication Service (FAS)** architecture that allows external scripts (PHP, Python, shell) to handle authentication logic.

Key strengths:
- **FAS architecture** — run authentication logic in any language; the FAS receives client details via query parameters and returns accept/deny decisions
- **Templated splash pages** — customize the captive portal with HTML/CSS templates
- **Client state tracking** — maintain connection status, pre-connection, and post-connection states
- **Pre-authentication landing page** — show a preliminary page before the actual login
- **FQDN token method** — use DNS-based tokens for seamless authentication on modern operating systems that block captive portal detection

### Nodogsplash

[Nodogsplash](https://github.com/nodogsplash/nodogsplash) is the original project that spawned openNDS. It follows a **simple, single-binary** design with minimal dependencies — perfect for resource-constrained embedded routers.

Key strengths:
- **Simplicity** — single configuration file, straightforward setup
- **Smallest footprint** — runs on routers with 8-16 MB RAM
- **Click-through authentication** — one-button "Accept Terms" portal
- **Token-based access** — pre-shared tokens for guest access
- **Mature and stable** — the codebase is battle-tested across thousands of OpenWRT deployments

The tradeoff is limited extensibility: Nodogsplash does not support external authentication services or RADIUS integration. It works best when you need a basic "accept terms to continue" portal without complex authentication requirements.

### CoovaChilli

[CoovaChilli](https://github.com/coova/coova-chilli) is the most feature-complete option, designed as a **full-featured access controller** with built-in RADIUS client support. It was originally developed for large-scale hotspot deployments and remains the go-to choice for hotels, universities, and ISPs.

Key strengths:
- **Built-in RADIUS client** — authenticate against FreeRADIUS, Microsoft NPS, or any RADIUS server
- **Full accounting** — track session duration, data usage, and connection timestamps via RADIUS accounting
- **UAM (Universal Access Method)** — redirect to any external authentication URL (payment gateways, social login, custom portals)
- **WISPr support** — implements the Wireless ISP Hotspot protocol for standardized hotspot discovery
- **JSON API** — manage sessions and users programmatically via a REST-like JSON interface
- **DHCP integration** — optional built-in DHCP server for tighter network control

The tradeoff is complexity: CoovaChilli requires more configuration and typically needs a companion RADIUS server (like FreeRADIUS) for full functionality. It is overkill for simple click-through portals but excels in environments requiring user registration, billing integration, or centralized authentication.

## Installation Guide

### Option 1: OpenWRT (Recommended for Routers)

All three projects are available as OpenWRT packages. Here is how to install each:

```bash
# Update package list
opkg update

# Install openNDS
opkg install opennds

# Install Nodogsplash
opkg install nodogsplash

# Install CoovaChilli
opkg install coova-chilli
```

### Option 2: Debian/Ubuntu

For x86 servers or VMs running Debian or Ubuntu:

```bash
# Install dependencies
apt-get install -y iptables libmicrohttpd-dev libssl-dev

# openNDS
git clone https://github.com/opennds/opennds.git
cd opennds
./configure
make
make install
systemctl enable opennds
systemctl start opennds

# Nodogsplash
apt-get install -y nodogsplash
systemctl enable nodogsplash
systemctl start nodogsplash

# CoovaChilli
apt-get install -y coova-chilli
systemctl enable chilli
systemctl start chilli
```

### Option 3: Docker (Community Images)

While none of these projects ship official Docker images, community-maintained images exist:

```yaml
version: "3"
services:
  opennds:
    image: linuxserver/opennds:latest  # Community image
    container_name: opennds
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./opennds-config:/etc/opennds
      - ./fas-scripts:/etc/opennds/fas
    restart: unless-stopped

  coova-chilli:
    image: coova/chilli:latest
    container_name: coova
    network_mode: host
    cap_add:
      - NET_ADMIN
    environment:
      - CHILLI_CONF=/etc/chilli.conf
    volumes:
      - ./chilli.conf:/etc/chilli.conf
    restart: unless-stopped
```

## Configuration Examples

### openNDS Basic Configuration

The main configuration file lives at `/etc/opennds/opennds.conf`:

```ini
# /etc/opennds/opennds.conf

GatewayInterface br-lan
GatewayName "Guest Network"
GatewayAddress 10.0.0.1

# Maximum session duration (minutes, 0 = unlimited)
SessionTimeout 1440

# Idle timeout (minutes)
IdleTimeout 30

# Preemptive authentication timeout
PreauthIdleTimeout 10

# Maximum number of clients
MaxClients 256

# Firewall rules for unauthenticated clients
Fasport 2050
Fasurl /opennds_preauth/

# Walled garden: allow access to specific domains before auth
FasRemoteName myserver.example.com

# Logging
LogSummary 1
LogLevel 3
```

Enable the captive portal with:

```bash
# Configure the firewall interface
uci set opennds.@opennds[0].gatewayinterface='br-lan'
uci commit opennds

# Start the service
/etc/init.d/opennds enable
/etc/init.d/opennds start
```

### Nodogsplash Basic Configuration

Nodogsplash uses `/etc/nodogsplash/nodogsplash.conf`:

```ini
# /etc/nodogsplash/nodogsplash.conf

GatewayInterface br-lan
GatewayName "Welcome Network"
GatewayAddress 10.0.0.1

# Session settings
SessionTimeout 600
ClientForceTimeout 300
IdleTimeout 15

# Authentication
AuthenticateInHex 0
TrustedMACList 00:11:22:33:44:55

# Splash page
SplashPage /etc/nodogsplash/htdocs/splash.html

# Max clients
MaxClients 128
```

Start the service:

```bash
/etc/init.d/nodogsplash enable
/etc/init.d/nodogsplash start
```

### CoovaChilli Basic Configuration

CoovaChilli's configuration is more involved, typically at `/etc/chilli.conf`:

```ini
# /etc/chilli.conf

# Network
uid nobody
gid nogroup
tundev tun0
domain example.com
dns1 8.8.8.8
dns2 8.8.4.4

# DHCP (if using built-in DHCP)
dhcpif eth1
dhcpmac 00:00:00:00:00:00
proxydhcp 0.0.0.0
dhcpstart 10.1.0.10
dhcpend 10.1.0.254
dhcplease 3600

# RADIUS authentication
radiusserver1 127.0.0.1
radiusserver2 127.0.0.1
radiusauthport 1812
radiusacctport 1813
radiussecret testing123

# UAM (Universal Access Method)
uamserver http://10.1.0.1:3990/www/login.html
uamurl http://10.1.0.1:3990/www/login.html
uamsecret hotspot_secret

# Session settings
sessiontimeout 3600
idletimeout 600
redir {
    uamlisten 10.1.0.1
    uamport 3990
    uamuiport 4990
}
```

Start CoovaChilli:

```bash
/etc/init.d/chilli enable
/etc/init.d/chilli start
```

Verify it is running:

```bash
# Check the tunnel interface
ip addr show tun0

# Check connected clients
chilli_query list
```

## Security Considerations

Captive portals operate at the network layer and intercept user traffic, which introduces several security considerations:

- **HTTPS interception limitations** — modern browsers block captive portal detection on HTTPS connections. All three tools use DNS-based detection (probing known HTTP endpoints) and HTTP redirects for initial interception
- **MAC address spoofing** — authentication is typically MAC-based, which can be spoofed. For higher security, combine with RADIUS 802.1X authentication
- **Session hijacking** — an attacker who discovers a valid session token could hijack an active session. Use short session timeouts and bind sessions to MAC addresses
- **DNS-based bypass** — clients may bypass the portal by using external DNS resolvers. Deploy DNS firewall rules (see our [DNS firewall guide](../self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/)) to redirect all DNS queries to the local resolver
- **Walled garden configuration** — carefully limit which domains are accessible before authentication to prevent unintended access

For deployments requiring stronger security, pair a captive portal with a full Network Access Control (NAC) solution like [FreeRADIUS with packetfence](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/).

## Which Should You Choose?

| Scenario | Recommendation |
|---|---|
| **Homelab / personal guest WiFi** | Nodogsplash — simplest setup, lowest resource usage |
| **Small business / cafe / restaurant** | openNDS — customizable splash pages, FAS for custom logic |
| **Hotel / hostel / apartment** | CoovaChilli — RADIUS integration, accounting, billing-ready |
| **Community network / mesh** | openNDS — FQDN token method works well on mesh topologies |
| **OpenWRT router with limited RAM** | Nodogsplash — smallest footprint (~1 MB) |
| **Need OAuth / social login** | openNDS — implement via FAS in any language |
| **Need RADIUS accounting and billing** | CoovaChilli — native RADIUS client with full accounting |

For most small to medium deployments, **openNDS** strikes the best balance: it is actively maintained (updated as recently as April 2026), supports extensible authentication via its FAS architecture, and runs efficiently on OpenWRT routers. If you need a simple click-through portal with zero complexity, **Nodogsplash** remains the lightweight champion. For enterprise-scale deployments with RADIUS infrastructure, **CoovaChilli** provides the most comprehensive feature set.

## FAQ

### What is the difference between openNDS and Nodogsplash?

openNDS is a fork of Nodogsplash that has evolved into a significantly more feature-rich project. While Nodogsplash provides basic click-through and token-based authentication with a minimal footprint, openNDS adds a Forward Authentication Service (FAS) architecture for custom authentication logic, templated splash pages, FQDN token support, and more granular client state tracking. openNDS is also more actively maintained, with recent commits in 2026 compared to Nodogsplash's slower release cadence.

### Can I run a captive portal in Docker?

None of the three projects ship official Docker images because captive portals require direct access to network interfaces and iptables/nftables rules. However, community-maintained Docker images exist for openNDS and CoovaChilli. You must run these containers in `network_mode: host` with `NET_ADMIN` and `NET_RAW` capabilities to allow firewall rule manipulation. For production deployments on routers, OpenWRT packages remain the recommended approach.

### Does CoovaChilli work without a RADIUS server?

Yes, CoovaChilli can operate in standalone mode with a simple click-through splash page and local authentication. However, its most powerful features — user registration, session accounting, bandwidth quotas, and centralized user management — require a RADIUS server such as FreeRADIUS. If you do not need these features, openNDS or Nodogsplash may be simpler alternatives.

### How do I customize the captive portal splash page?

For **openNDS**, customize the HTML templates in the FAS (Forward Authentication Service) directory or the built-in splash page templates. For **Nodogsplash**, edit the splash page HTML file at `/etc/nodogsplash/htdocs/splash.html`. For **CoovaChilli**, modify the UAM server pages or the built-in splash HTML. All three support HTML, CSS, and inline JavaScript for fully custom branding.

### Can I use a captive portal with HTTPS networks?

Captive portals cannot intercept HTTPS traffic directly due to TLS encryption. Instead, they rely on HTTP-based captive portal detection: the client OS probes known HTTP endpoints (e.g., `captive.apple.com`, `connectivitycheck.gstatic.com`) and the captive portal intercepts these requests, returning a redirect to the splash page. Modern iOS, Android, and Windows implementations handle this automatically. For HTTPS-only clients, DNS-based detection (FQDN token method in openNDS) provides a workaround.

### How many concurrent users can these tools handle?

Performance depends on the underlying hardware. On a typical OpenWRT router (ARM CPU, 128 MB RAM):
- **Nodogsplash**: up to 128 concurrent clients with minimal impact
- **openNDS**: up to 256 concurrent clients (configurable via MaxClients)
- **CoovaChilli**: up to 512+ concurrent clients, limited mainly by RADIUS server capacity

For larger deployments, the bottleneck is typically the upstream router's NAT table and bandwidth, not the captive portal software itself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "openNDS vs Nodogsplash vs CoovaChilli: Best Self-Hosted Captive Portal 2026",
  "description": "Compare openNDS, Nodogsplash, and CoovaChilli — the top open-source captive portal solutions for guest WiFi, hotspot authentication, and network access control in 2026.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
