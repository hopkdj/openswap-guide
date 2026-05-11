---
title: "Self-Hosted RADIUS Proxy & RadSec Gateways: radsecproxy vs FreeRADIUS Proxy vs hostapd EAP"
date: "2026-05-11"
tags: ["comparison", "guide", "self-hosted", "networking", "security", "authentication"]
draft: false
description: "Compare RADIUS proxy solutions for self-hosted network authentication. RadSec gateway deployment, FreeRADIUS proxying, and enterprise WiFi authentication guides."
---

RADIUS (Remote Authentication Dial-In User Service) is the backbone of network authentication — used by enterprise WiFi, VPN gateways, switch port access control, and ISP billing systems. As organizations grow and distribute their infrastructure across multiple sites, a single RADIUS server is no longer sufficient.

RADIUS proxies solve this by forwarding authentication requests between servers, enabling centralized user databases with distributed access points. RadSec (RADIUS over TLS) extends this capability across untrusted networks, replacing the legacy UDP-based RADIUS protocol with encrypted TLS connections.

## What Is a RADIUS Proxy?

A RADIUS proxy sits between Network Access Servers (NAS devices — switches, APs, VPN gateways) and RADIUS authentication servers. It:

- **Routes requests** to the correct authentication backend based on realm, NAS IP, or user attributes
- **Aggregates backends** — present a single RADIUS endpoint to NAS devices while distributing to multiple auth servers
- **Enables RadSec** — encrypt RADIUS traffic over TLS for cross-site authentication
- **Provides failover** — automatically route to backup RADIUS servers when primary is unreachable
- **Centralizes logging** — collect authentication accounting data from multiple RADIUS servers in one place

## Comparison Overview

| Feature | radsecproxy | FreeRADIUS Proxy | hostapd EAP |
|---------|-------------|------------------|-------------|
| Stars | 86 | 2,036 (FreeRADIUS) | N/A (w1.fi) |
| Language | C | C | C |
| License | BSD-2 | LGPL | BSD |
| Primary Role | RadSec gateway | Full RADIUS server with proxy | WiFi AP with EAP auth |
| Protocol Support | RadSec (TLS), RADIUS/UDP | RADIUS/UDP, RadSec, EAP | 802.1X/EAP, RADIUS client |
| Realm Routing | Yes | Yes (proxy.conf) | No (forward to RADIUS) |
| TLS/RadSec | Native (primary focus) | Via radsec module | Via EAP-TLS, EAP-PEAP |
| Failover | Yes | Yes | N/A (single upstream) |
| Accounting Proxy | Yes | Yes | No |
| Configuration | Simple (flat file) | Complex (modular) | Supplicant config |
| Docker Support | Community images | Official Dockerfile | Community images |
| Last Updated | 2026-04 | 2026-05 | Active |
| GitHub | [radsecproxy/radsecproxy](https://github.com/radsecproxy/radsecproxy) | [FreeRADIUS/freeradius-server](https://github.com/FreeRADIUS/freeradius-server) | [w1.fi/hostapd](https://w1.fi/hostapd/) |

## radsecproxy

radsecproxy is a dedicated RADIUS/TLS (RadSec) proxy daemon. Its sole purpose is to bridge traditional UDP-based RADIUS networks with RadSec-enabled backends, making it the go-to tool for organizations that need to authenticate users across untrusted networks (WAN links, internet connections, multi-site deployments).

### Key Features

- **RadSec gateway**: Convert UDP RADIUS to TLS-encrypted RadSec and vice versa
- **Realm-based routing**: Forward requests based on username realm (user@realm.com)
- **Dynamic discovery**: Use SRV DNS records to discover RadSec peers
- **Accounting proxy**: Forward accounting (start/stop/interim-update) packets transparently
- **Connection pooling**: Maintain persistent TLS connections to backends
- **Simple configuration**: Single flat configuration file with clear syntax

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  radsecproxy:
    image: alpine:3.20
    container_name: radsecproxy
    restart: unless-stopped
    ports:
      - "2083:2083"     # RadSec (RADIUS/TLS)
      - "1812:1812/udp" # Standard RADIUS auth
      - "1813:1813/udp" # Standard RADIUS accounting
    volumes:
      - ./radsecproxy.conf:/etc/radsecproxy.conf:ro
      - ./certs:/etc/radsec/certs:ro
    command: >
      sh -c "apk add radsecproxy &&
             radsecproxy -f /etc/radsecproxy.conf -d"
    networks:
      - radius-net

networks:
  radius-net:
    driver: bridge
```

### Configuration Example (radsecproxy.conf)

```conf
realm example.com {
    # Forward all @example.com requests to the RadSec backend
    server {
        name = "corp-radius"
        type = tls
        hostname = "radius.example.com"
        service = "2083"
        cacertfile = "/etc/radsec/certs/ca.pem"
        certfile = "/etc/radsec/certs/client.pem"
        certkeyfile = "/etc/radsec/certs/client-key.pem"
    }
}

realm local {
    # Handle local authentication directly
    server {
        name = "local-radius"
        type = udp
        hostname = "127.0.0.1"
        service = "18120"
        secret = "shared_secret"
    }
}
```

### Installation from Source

```bash
# Debian/Ubuntu
apt-get install radsecproxy

# Alpine
apk add radsecproxy

# Build from source
git clone https://github.com/radsecproxy/radsecproxy.git
cd radsecproxy
./configure
make
make install
```

## FreeRADIUS Proxy Module

FreeRADIUS is the most widely deployed open-source RADIUS server, and its built-in proxy module provides enterprise-grade request routing, load balancing, and failover without requiring a separate proxy daemon.

### Key Features

- **Full RADIUS server with proxy capabilities**: Authenticate locally or proxy to remote servers
- **Realm-based routing**: Complex realm matching with regex support
- **Load balancing**: Distribute requests across multiple backends with weighted distribution
- **Failover and fallback**: Automatic failover to secondary servers with configurable retry logic
- **EAP support**: Full EAP-TLS, EAP-PEAP, EAP-TTLS, EAP-MD5 authentication
- **Modular architecture**: Swap authentication backends (LDAP, SQL, PAP, CHAP) via modules
- **Extensive logging**: Detailed authentication accounting with radutmp and SQL support

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  freeradius:
    image: freeradius/freeradius-server:latest
    container_name: freeradius
    restart: unless-stopped
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    volumes:
      - ./freeradius-config:/etc/freeradius/3.0:ro
      - ./freeradius-certs:/etc/freeradius/3.0/certs:ro
    environment:
      - FREERADIUS_DEBUG_MODE=no
    networks:
      - radius-net

networks:
  radius-net:
    driver: bridge
```

### Proxy Configuration (proxy.conf)

```conf
home_server local_auth {
    type = auth
    ipaddr = 127.0.0.1
    port = 18120
    secret = "local_secret"
    response_window = 20
    max_outstanding = 65536
    status_check = status
}

home_server remote_site {
    type = auth
    ipaddr = radius.remote-site.example.com
    port = 2083
    proto = tls
    secret = "remote_secret"
    tls {
        ca_file = /etc/freeradius/3.0/certs/ca.pem
        certificate_file = /etc/freeradius/3.0/certs/client.pem
        private_key_file = /etc/freeradius/3.0/certs/client-key.pem
    }
}

home_server_pool primary_pool {
    type = fail-over
    home_server = local_auth
    home_server = remote_site
}

realm example.com {
    auth_pool = primary_pool
    acct_pool = primary_pool
}
```

### Testing the Configuration

```bash
# Test with radclient
echo "User-Name=testuser,User-Password=test123" |   radclient -x 127.0.0.1:1812 auth testing123

# Debug mode for troubleshooting
freeradius -X

# Check proxy status
radclient -x 127.0.0.1:1812 status testing123
```

## hostapd with EAP Authentication

hostapd (Host Access Point Daemon) is not a RADIUS proxy in the traditional sense — it is a WiFi access point daemon that acts as a RADIUS client, forwarding 802.1X authentication requests to a RADIUS server. In enterprise WiFi deployments, hostapd is the bridge between wireless clients and the RADIUS authentication infrastructure.

### Key Features

- **802.1X/WPA-Enterprise**: Full EAP authentication for enterprise WiFi
- **Multiple EAP methods**: EAP-TLS, EAP-PEAP, EAP-TTLS, EAP-SIM, EAP-AKA
- **RADIUS client**: Forward authentication to local or remote RADIUS servers
- **VLAN assignment**: Assign clients to VLANs based on RADIUS attributes
- **MAC authentication**: Bypass 802.1X for specific devices (printers, IoT)
- **Captive portal integration**: Work with CoovaChilli, PacketFence, and similar platforms

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  hostapd:
    image: alpine:3.20
    container_name: hostapd
    restart: unless-stopped
    network_mode: host
    privileged: true
    volumes:
      - ./hostapd.conf:/etc/hostapd/hostapd.conf:ro
      - ./hostapd-eapol.conf:/etc/hostapd/hostapd-eapol.conf:ro
    command: >
      sh -c "apk add hostapd &&
             hostapd /etc/hostapd/hostapd.conf"
```

### Configuration Example (hostapd.conf)

```conf
interface=wlan0
driver=nl80211
ssid=Enterprise-WiFi
hw_mode=g
channel=6

# 802.1X Authentication
ieee8021x=1
eap_server=0
wpa=2
wpa_key_mgmt=WPA-EAP
wpa_pairwise=TKIP
rsn_pairwise=CCMP

# RADIUS Server Configuration
auth_server_addr=192.168.1.100
auth_server_port=1812
auth_server_secret=radius_shared_secret

# Accounting Server
acct_server_addr=192.168.1.100
acct_server_port=1813
acct_server_secret=radius_shared_secret

# VLAN Assignment
dynamic_vlan=1
vlan_file=/etc/hostapd/hostapd.vlan
```

## When to Use Each Solution

| Scenario | Recommended Tool |
|----------|-----------------|
| Cross-site RADIUS over TLS | radsecproxy |
| Single-site RADIUS with failover | FreeRADIUS proxy |
| Enterprise WiFi deployment | hostapd + FreeRADIUS |
| Multi-tenant ISP authentication | FreeRADIUS proxy with realm routing |
| RadSec gateway for cloud RADIUS | radsecproxy |
| University campus with multiple auth backends | FreeRADIUS proxy |
| Corporate WiFi with certificate auth | hostapd (EAP-TLS) + FreeRADIUS |

## Deployment Architecture Example

A typical multi-site RADIUS deployment looks like this:

```
[WiFi AP / Switch] ──(RADIUS/UDP)──> [radsecproxy] ──(RadSec/TLS)──> [FreeRADIUS @ HQ]
                                                                        ├── LDAP (user DB)
                                                                        ├── SQL (accounting)
                                                                        └─> [Backup FreeRADIUS]
```

In this architecture:
1. The local AP/switch sends standard RADIUS/UDP to the local radsecproxy
2. radsecproxy converts the request to RadSec (TLS-encrypted) and forwards it across the WAN
3. The HQ FreeRADIUS server authenticates against LDAP and logs accounting to SQL
4. If HQ is unreachable, radsecproxy fails over to a local backup RADIUS server

## Why Self-Host Your RADIUS Proxy Infrastructure?

Network authentication is the first line of defense for your entire infrastructure. Self-hosting RADIUS proxy and authentication tools provides:

- **Zero dependency on cloud identity providers**: Authenticate users even when the internet is down
- **Complete audit trail**: Every authentication attempt, success or failure, is logged locally
- **Custom authentication logic**: Integrate with existing LDAP, Active Directory, or custom user databases
- **Cost elimination**: Commercial RADIUS solutions (Cisco ISE, Aruba ClearPass) cost $5,000-$50,000+ per year
- **Regulatory compliance**: Meet data sovereignty requirements by keeping authentication data on-premises
- **Network segmentation**: Route authentication requests to different backends based on user role, location, or device type

For organizations deploying enterprise WiFi or wired 802.1X access control, a self-hosted RADIUS stack is essential. For broader network access control, see our [PacketFence vs FreeRADIUS vs CoovaChilli NAC guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/). For AAA server alternatives, our [FreeRADIUS vs ToughRADIUS vs tac_plus comparison](../2026-04-25-freeradius-vs-toughradius-vs-tac-plus-self-hosted-aaa-servers-2026/) covers the broader authentication landscape.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted RADIUS Proxy & RadSec Gateways: radsecproxy vs FreeRADIUS Proxy vs hostapd EAP",
  "description": "Compare RADIUS proxy solutions for self-hosted network authentication. RadSec gateway deployment, FreeRADIUS proxying, and enterprise WiFi authentication guides.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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

## FAQ

### What is RadSec and why do I need it?

RadSec is RADIUS over TLS (RFC 6614). Traditional RADIUS uses UDP with a shared secret for authentication, which is vulnerable to interception and replay attacks on untrusted networks. RadSec encrypts the entire RADIUS exchange with TLS, making it safe for cross-site authentication over WAN links or the public internet.

### Can radsecproxy handle both authentication and accounting?

Yes, radsecproxy proxies both Access-Request (authentication) and Accounting-Request (start/stop/interim-update) packets. Configure separate `realm` blocks for auth and accounting if they need different routing.

### How does FreeRADIUS proxy differ from running a separate radsecproxy?

FreeRADIUS can proxy requests natively through its `proxy.conf` configuration — no separate daemon needed. However, if you need a lightweight, dedicated RadSec gateway without the full FreeRADIUS feature set, radsecproxy is simpler to configure and has a smaller resource footprint.

### Can hostapd authenticate users without a RADIUS server?

hostapd has a built-in EAP server (`eap_server=1`) that can authenticate users against a local EAP user file. However, this only supports basic EAP methods (EAP-MD5, EAP-TLS with static certs) and is not suitable for production deployments. Always use a proper RADIUS server for enterprise authentication.

### How do I troubleshoot RADIUS proxy issues?

Use `freeradius -X` (debug mode) to see detailed request processing logs. For radsecproxy, use `radsecproxy -f config.conf -d` for debug output. The `radclient` utility can send test authentication requests. Check that shared secrets match between all servers and that UDP ports 1812/1813 (or TCP 2083 for RadSec) are open.

### What is the difference between RADIUS and Diameter?

RADIUS is the legacy protocol for network authentication (ports 1812/1813, UDP). Diameter is its successor (RFC 6733, port 3868, TCP/SCTP) with better reliability, failover, and extensibility. Most enterprise WiFi and switch vendors still use RADIUS. Diameter is primarily used in telecom (3GPP LTE/5G) networks.

