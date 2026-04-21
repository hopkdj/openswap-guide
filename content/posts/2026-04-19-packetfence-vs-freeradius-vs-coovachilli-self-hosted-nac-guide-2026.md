---
title: "PacketFence vs FreeRADIUS vs CoovaChilli: Self-Hosted NAC Guide 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "networking", "security", "NAC"]
draft: false
description: "Compare top open-source network access control (NAC) solutions: PacketFence, FreeRADIUS + daloRADIUS, and CoovaChilli. Learn how to deploy captive portals, 802.1X authentication, and guest network management on your own infrastructure."
---

Network Access Control (NAC) is one of the most critical security layers for any organization that manages physical or wireless networks. Without it, any device with an Ethernet cable or WiFi password can join your network and access resources freely. NAC solutions enforce authentication, authorization, and accounting (AAA) — verifying who is connecting, what they're allowed to access, and logging their activity.

For organizations that need full control over their network security infrastructure, self-hosted NAC tools are the answer. Instead of relying on vendor appliances or cloud-based services, you run the software on your own servers. This gives you complete visibility into every connection event, full customization of authentication policies, and zero dependency on third-party uptime.

In this guide, we compare three open-source NAC solutions that cover different use cases: **PacketFence** as a full-featured enterprise NAC platform, **FreeRADIUS** paired with **daloRADIUS** as a modular authentication stack, and **CoovaChilli** as a lightweight captive portal for hotspot deployments.

## Why Self-Host Your Network Access Control?

Self-hosting your NAC infrastructure provides several advantages over commercial alternatives:

- **Complete data ownership** — Every authentication event, RADIUS accounting record, and user session stays on your infrastructure. No telemetry is sent to external vendors.
- **No per-device licensing** — Commercial NAC platforms often charge per endpoint. Open-source tools have no such limits, making them cost-effective for large deployments.
- **Deep customization** — You can modify authentication flows, integrate with any identity provider (LDAP, Active Directory, SAML), and script custom remediation actions.
- **Air-gapped operation** — For high-security environments, self-hosted NAC works entirely offline with no external dependencies.
- **Integration with existing security tools** — Connect your NAC to SIEM systems, vulnerability scanners, and network monitoring tools running on the same infrastructure.

If you're already running [self-hosted IDS/IPS tools like Suricata or Snort](../suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/), adding a NAC layer creates a comprehensive network security stack that controls access before threats even reach your perimeter.

## PacketFence: Full-Featured Enterprise NAC

[PacketFence](https://packetfence.org/) by Inverse Inc. is the most comprehensive open-source NAC platform available. With over 1,600 stars on GitHub and active development through 2026, it's designed for organizations that need a complete network security solution in a single package.

**Key features:**

- **Captive portal** with registration, guest access, and self-service remediation workflows
- **802.1X supplicant and authenticator** support for wired and wireless port-based authentication
- **BYOD onboarding** with automated device profiling, certificate provisioning, and policy assignment
- **Layer-2 isolation** — automatically quarantine non-compliant devices into restricted VLANs
- **Centralized management** — single web console for all wired switches, wireless controllers, and access points
- **Integration ecosystem** — connects with Active Directory, LDAP, SAML, and external MDM platforms

**GitHub stats (April 2026):** 1,614 stars | Last updated: 2026-04-19 | Language: Perl

### Installation and Deployment

PacketFence provides installation scripts for Debian and RHEL-based distributions. The recommended approach is a dedicated server with at least 2 CPU cores and 4 GB RAM:

```bash
# Download the installer for Debian 12
wget https://github.com/inverse-inc/packetfence/releases/download/v14.2.0/debian-packetfence-installer-14.2.0.tar.gz
tar xzf debian-packetfence-installer-14.2.0.tar.gz
cd debian-packetfence-installer

# Run the interactive installer
sudo ./install.sh

# Enable and start services
sudo systemctl enable packetfence
sudo systemctl start packetfence
```

For containerized deployments, PacketFence includes [docker](https://www.docker.com/) support files in its `containers/` directory:

```bash
# Set up iptables rules for containerized mode
sudo ./containers/run-docker-in-debian-installer.sh
sudo ./containers/docker_iptables.sh
sudo ./containers/docker-minimal-rules.sh
```

Access the admin panel at `https://<server-ip>:1443` and complete the initial wizard to configure your network zones, authentication sources, and switch/AP connections.

### PacketFence Architecture

PacketFence operates as a unified platform with several integrated components:

- **pfcron** — scheduled tasks for role updates, quarantine checks, and compliance scanning
- **pfmon** — real-time network monitoring and event detection engine
- **pfconfig** — centralized configuration management across all PacketFence services
- ** captive portal (pfappserver)** — the web-based guest registration and authentication interface
- **RADIUS proxy** — handles 802.1X authentication by forwarding to your identity provider

The system supports both inline and out-of-band enforcement modes. In inline mode, traffic passes through the PacketFence server for policy enforcement. In out-of-band mode, PacketFence sends dynamic VLAN assignment commands directly to your network switches via SNMP or CLI.

## FreeRADIUS + daloRADIUS: Modular Authentication Stack

[FreeRADIUS](https://freeradius.org/) is the world's most widely deployed open-source RADIUS server. With over 2,500 GitHub stars and a codebase dating back to 1999, it's the backbone of authentication for thousands of universities, ISPs, and enterprises. Paired with [daloRADIUS](https://github.com/lirantal/daloradius) as a web management interface, it forms a powerful, modular NAC stack.

**Key features:**

- **Full RADIUS protocol support** — authentication, authorization, and accounting (AAA) over RADIUS
- **EAP methods** — EAP-TLS, EAP-TTLS, PEAP, EAP-FAST for 802.1X wireless authentication
- **LDAP/Active Directory integration** — authenticate users against existing directory services
-[postgresql](https://www.postgresql.org/)kends** — MySQL, PostgreSQL, SQLite for user databases and accounting records
- **daloRADIUS web UI** — user management, accounting reports, billing engine, and graphical dashboards
- **Extensible via modules** — hundreds of modules for custom authentication logic, SQL queries, and external lookups

**GitHub stats (April 2026):**
- FreeRADIUS: 2,501 stars | Last updated: 2026-04-17 | Language: C
- daloRADIUS: 865 stars | Last updated: 2026-04-12 | Language: PHP

### Docker Deployment with docker-compose

The daloRADIUS project provides an official `docker-compose.yml` that deploys FreeRADIUS, MySQL, and the daloRADIUS web UI together:

```yaml
version: "3"

services:

  radius-mysql:
    image: mariadb:10
    container_name: radius-mysql
    restart: unless-stopped
    environment:
      - MYSQL_DATABASE=radius
      - MYSQL_USER=radius
      - MYSQL_PASSWORD=radius_secret_db
      - MYSQL_ROOT_PASSWORD=root_secret
    volumes:
      - "./data/mysql:/var/lib/mysql"

  radius:
    container_name: radius
    build:
      context: .
      dockerfile: Dockerfile-freeradius
    restart: unless-stopped
    depends_on:
      - radius-mysql
    ports:
      - '1812:1812/udp'
      - '1813:1813/udp'
    environment:
      - MYSQL_HOST=radius-mysql
      - MYSQL_PORT=3306
      - MYSQL_DATABASE=radius
      - MYSQL_USER=radius
      - MYSQL_PASSWORD=radius_secret_db
    volumes:
      - ./data/freeradius:/data
      - radius_logs:/var/log/freeradius

  radius-web:
    build: .
    container_name: radius-web
    restart: unless-stopped
    depends_on:
      - radius
      - radius-mysql
    ports:
      - '80:80'
      - '8000:8000'
    environment:
      - MYSQL_HOST=radius-mysql
      - MYSQL_DATABASE=radius
      - MYSQL_USER=radius
      - MYSQL_PASSWORD=radius_secret_db
      - DEFAULT_FREERADIUS_SERVER=radius

volumes:
  radius_logs:
```

Deploy with:

```bash
git clone https://github.com/lirantal/daloradius.git
cd daloradius
docker compose up -d
```

### Bare-Metal FreeRADIUS Installation

For production deployments where you need maximum control over the RADIUS server:

```bash
# Install FreeRADIUS on Debian/Ubuntu
sudo apt install freeradius freeradius-mysql freeradius-utils

# Install daloRADIUS web interface
sudo apt install apache2 php php-mysql php-gd php-pear php-db php-mail php-mail-mime
wget https://github.com/lirantal/daloradius/archive/refs/heads/master.zip
unzip master.zip
sudo mv daloradius-master /var/www/daloradius
sudo chown -R www-data:www-data /var/www/daloradius

# Import the FreeRADIUS MySQL schema
mysql -u root -p radius < /etc/freeradius/3.0/mods-config/sql/main/mysql/schema.sql
```

Configure your clients (network switches and access points) in `/etc/freeradius/3.0/clients.conf`:

```
client switch-building-a {
    ipaddr = 10.0.1.0/24
    secret = your_switch_secret
    require_message_authenticator = yes
}

client ap-controllers {
    ipaddr = 10.0.2.0/24
    secret = your_ap_secret
    require_message_authenticator = yes
}
```

## CoovaChilli: Lightweight Captive Portal for Hotspots

[CoovaChilli](https://github.com/coova/coova-chilli) is a specialized access controller designed specifically for captive portal deployments — think hotel WiFi, café hotspots, and public access networks. It operates as a daemon that intercepts unauthenticated HTTP traffic and redirects users to a login or registration page.

**Key features:**

- **Captive portal redirection** — intercept and redirect unauthenticated HTTP/HTTPS traffic
- **RADIUS integration** — authenticates users against any RADIUS server (including FreeRADIUS)
- **Bandwidth management** — per-user and per-session rate limiting
- **Session timeouts** — configurable idle timeout, maximum session duration, and data quotas
- **Walled garden** — allowlist of sites accessible before authentication (payment pages, terms of service)
- **Lightweight footprint** — runs on minimal hardware, designed for embedded gateway routers

**GitHub stats (April 2026):** 590 stars | Last updated: 2026-04-09 | Language: C

### Installation

CoovaChilli is available in most Linux distribution repositories:

```bash
# Debian/Ubuntu
sudo apt install coova-chilli

# Or build from source
git clone https://github.com/coova/coova-chilli.git
cd coova-chilli
./bootstrap
./configure --enable-chilliproxy --enable-dhcpopt --enable-miniportal
make
sudo make install
```

### Basic Configuration

Configure CoovaChilli in `/etc/chilli/defaults`:

```bash
# Network interface facing clients
HS_LANIF=eth1

# RADIUS server for authentication
HS_RADIUS=localhost
HS_RADIUS2=localhost
HS_RADSECRET=shared_secret

# Authentication mode
HS_UAMLISTEN=10.1.0.1
HS_UAMPORT=3990
HS_UAMUIPORT=4990

# Portal URL (redirect unauthenticated users here)
HS_UAMSERVER=10.1.0.1
HS_UAMFORMAT=http://10.1.0.1:8000/hotspot/login.html

# DHCP settings for the captive network
HS_NETWORK=10.1.0.0
HS_NETMASK=255.255.255.0
HS_DNS1=8.8.8.8
HS_DNS2=8.8.4.4
```

Start the service:

```bash
sudo systemctl enable chilli
sudo systemctl start chilli
```

### Integrating CoovaChilli with FreeRADIUS

For a complete hotspot solution, combine CoovaChilli as the captive portal engine with FreeRADIUS as the authentication backend:

```
  Client Device ──(HTTP redirect)──► CoovaChilli (port 3990)
                                            │
                                    (RADIUS Access-Request)
                                            │
                                            ▼
                                    FreeRADIUS (port 1812)
                                            │
                                    (MySQL / LDAP / Local Users)
                                            │
                                            ▼
                                    Authentication Decision
                                            │
                                    (RADIUS Access-Accept/Reject)
                                            │
                                            ▼
                                    CoovaChilli grants/blocks access
```

This combination is ideal for deployments where you need a lightweight captive portal (CoovaChilli) backed by a robust, flexible authentication system (FreeRADIUS) with web-based user management (daloRADIUS).

## Feature Comparison: PacketFence vs FreeRADIUS vs CoovaChilli

| Feature | PacketFence | FreeRADIUS + daloRADIUS | CoovaChilli |
|---------|-------------|-------------------------|-------------|
| **Primary role** | Full NAC platform | AAA authentication server | Captive portal gateway |
| **Captive portal** | Built-in | Via daloRADIUS or external | Built-in (core function) |
| **802.1X support** | Full (supplicant + authenticator) | Full (EAP-TLS, PEAP, TTLS) | No (RADIUS backend only) |
| **BYOD onboarding** | Yes, automated | Manual via daloRADIUS | No |
| **Device profiling** | Yes, passive fingerprinting | Via external modules | No |
| **VLAN assignment** | Dynamic (RADIUS CoA) | Dynamic (RADIUS CoA) | No |
| **Quarantine/isolation** | Layer-2 isolation | Via RADIUS attributes | Session blocking |
| **Web management UI** | Built-in admin console | daloRADIUS (community) | No (needs ChiliSpot UI) |
| **Active Directory** | Native integration | Via LDAP module | Via RADIUS backend |
| **REST API** | Yes | Limited | No |
| **Docker support** | Container scripts | Official docker-compose | Manual |
| **Best for** | Enterprise NAC, campus networks | University/ISP authentication | Hotspot, café, hotel WiFi |
| **GitHub stars** | 1,614 | 2,501 (FreeRADIUS) | 590 |
| **Last updated** | 2026-04-19 | 2026-04-17 | 2026-04-09 |

## Choosing the Right Solution

The decision between these three tools depends on your specific network security requirements:

**Choose PacketFence if:** You need a complete, out-of-the-box NAC solution with device profiling, automated BYOD onboarding, quarantine capabilities, and centralized management across a heterogeneous network of switches and access points. It's the closest open-source equivalent to commercial platforms like Cisco ISE or Aruba ClearPass.

**Choose FreeRADIUS + daloRADIUS if:** You need a robust, battle-tested RADIUS server for 802.1X wireless authentication or VPN access control, and you want a web interface for user management and accounting. This stack is ideal for universities, ISPs, and organizations that already have identity providers and just need the AAA layer.

**Choose CoovaChilli if:** You need a lightweight captive portal for a public WiFi hotspot, hotel guest network, or café. It handles the HTTP redirection and session management efficiently with minimal resource usage. Pair it with FreeRADIUS for the authentication backend to get a complete hotspot solution.

For comprehensive network security, these tools work best as part of a layered defense strategy. A PacketFence deployment can handle internal network access control, while a separate FreeRADIUS instance manages guest WiFi authentication through CoovaChilli. Combined with [self-hosted network traffic analysis tools like Zeek or Arkime](../self-hosted-network-traffic-analysis-zeek-arkime-ntopng-guide-2026/), you gain visibility into both who is accessing your network and what they're doing once connected.

Organizations running [SIEM platforms like Wazuh](../self-hosted-siem-wazuh-security-onion-elastic-guide/) can feed NAC authentication events into their security monitoring pipeline, creating correlated alerts when a device fails authentication repeatedly or accesses restricted network segments.

## FAQ

### What is the difference between NAC and a firewall?

A firewall filters traffic based on IP addresses, ports, and protocols at the network perimeter. Network Access Control (NAC) operates at a higher level — it authenticates devices and users *before* they gain network access, and it can dynamically assign VLANs, apply bandwidth limits, or quarantine devices based on compliance status. Think of NAC as controlling who gets a key to enter the building, while a firewall controls which rooms they can access once inside.

### Can PacketFence replace a commercial NAC solution like Cisco ISE?

For many use cases, yes. PacketFence supports 802.1X authentication, captive portals, device profiling, BYOD onboarding, and dynamic VLAN assignment — all core features of Cisco ISE. The main differences are in vendor-specific integrations (PacketFence supports hundreds of switch/AP models via built-in profiles) and the absence of a dedicated vendor support contract. For organizations with in-house network expertise, PacketFence is a production-ready alternative.

### Does FreeRADIUS support modern EAP methods like EAP-TLS?

Yes. FreeRADIUS supports all standard EAP methods including EAP-TLS (certificate-based), EAP-TTLS (tunneled TLS), PEAP (Protected EAP), and EAP-FAST. EAP-TLS is the most secure option for enterprise deployments, as it uses client certificates instead of passwords for authentication. FreeRADIUS can also integrate with Windows Certificate Services or a self-hosted PKI (see our [PKI and certificate management guide](../self-hosted-pki-certificat[nginx](https://nginx.org/)agement-step-ca-caddy-nginx-proxy-manager-2026/)) to automate certificate issuance and revocation.

### How do I monitor NAC authentication events?

FreeRADIUS logs all authentication attempts to `/var/log/freeradius/radacct/` when accounting is enabled. PacketFence provides real-time event dashboards in its web console and can forward logs via syslog to external SIEM systems. For CoovaChilli, session data is available through the `chilli_query` command and the built-in JSON status API at `http://<gateway>:3990/json/status`.

### Can I use CoovaChilli with a payment gateway for paid WiFi access?

Yes. CoovaChilli's walled garden feature allows you to configure a payment portal that's accessible before authentication. After the user completes payment, the payment gateway sends a RADIUS request (or calls the CoovaChilli JSON API) to activate the user's session. This is the standard architecture for paid hotel and café WiFi hotspots.

### What hardware do I need to run these NAC tools?

- **PacketFence**: Minimum 2 CPU cores, 4 GB RAM, 20 GB storage. For large deployments (1,000+ endpoints), recommend 4+ cores and 8 GB RAM.
- **FreeRADIUS + daloRADIUS**: 1 CPU core, 512 MB RAM for up to 500 authentications/minute. The Docker stack requires about 1 GB RAM total with MySQL.
- **CoovaChilli**: Can run on a Raspberry Pi or embedded gateway router. Memory footprint is under 50 MB for typical hotspot deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PacketFence vs FreeRADIUS vs CoovaChilli: Self-Hosted NAC Guide 2026",
  "description": "Compare top open-source network access control (NAC) solutions: PacketFence, FreeRADIUS + daloRADIUS, and CoovaChilli. Learn how to deploy captive portals, 802.1X authentication, and guest network management on your own infrastructure.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
