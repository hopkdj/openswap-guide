---
title: "Self-Hosted AnyConnect VPN Servers — AnyLink vs ocserv vs OCServ-Dashboard"
date: "2026-05-19"
tags: ["vpn", "anyconnect", "remote-access", "openconnect", "self-hosted", "networking"]
draft: false
---

Cisco AnyConnect is the most widely deployed enterprise SSL VPN client, prized for its cross-platform compatibility, split tunneling, and integrated posture assessment. For self-hosted infrastructure, running an AnyConnect-compatible VPN server provides secure remote access without vendor lock-in or per-user licensing fees.

This guide compares three open-source approaches to hosting an AnyConnect-compatible VPN: **AnyLink** (a Go-native AnyConnect server), **ocserv** (OpenConnect SSL VPN server, the reference implementation), and the **OCServ Dashboard** ecosystem (community Docker images with management UIs).

## Why AnyConnect-Compatible VPN?

AnyConnect uses the OpenConnect protocol (a TLS-based VPN protocol) which is more modern and secure than traditional IPsec/L2TP or PPTP. The protocol operates over HTTPS (UDP 443 or TCP 443), making it highly compatible with restrictive firewalls and NAT environments.

Key advantages of AnyConnect-compatible self-hosted servers:
- **Native client support** — Official Cisco AnyConnect clients work on Windows, macOS, Linux, iOS, and Android
- **OpenConnect clients** — The open-source `openconnect` CLI client provides a free alternative on all platforms
- **Split tunneling** — Route only corporate traffic through the VPN while keeping local internet access
- **Certificate-based auth** — Support for TLS client certificates, OTP, RADIUS, and LDAP integration
- **Firewall-friendly** — Runs on port 443 (HTTPS), indistinguishable from regular web traffic

## AnyLink

[AnyLink](https://github.com/bjdgyc/anylink) is an enterprise-grade SSL VPN server written in Go that implements the OpenConnect protocol. It was designed to be fully compatible with Cisco AnyConnect clients while providing a modern web-based management interface.

**Key features:**

- Full AnyConnect client compatibility (official Cisco clients)
- Web-based admin dashboard for user management, group policies, and server monitoring
- Built-in user authentication (local, LDAP, RADIUS, OAuth)
- Split tunneling with configurable route policies
- TOTP/OTP two-factor authentication
- Connection statistics and bandwidth monitoring
- Cross-platform binary distribution (no dependencies)

**Docker Compose deployment:**

```yaml
version: "3.8"

services:
  anylink:
    image: bjdgyc/anylink:latest
    container_name: anylink
    restart: unless-stopped
    ports:
      - "443:443/tcp"
      - "443:443/udp"
      - "8800:8800/tcp"
    volumes:
      - ./conf:/app/conf
      - ./db:/app/db
      - ./log:/app/log
      - /etc/localtime:/etc/localtime:ro
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    environment:
      - LINK_LOG_LEVEL=info
    devices:
      - /dev/net/tun
    sysctls:
      - net.ipv4.ip_forward=1
    networks:
      - vpn_net
    dns:
      - 8.8.8.8
      - 8.8.4.4

networks:
  vpn_net:
    driver: bridge
```

**Install on bare metal:**

```bash
# Download the latest release
wget https://github.com/bjdgyc/anylink/releases/latest/download/anylink-linux-amd64.tar.gz
tar xzf anylink-linux-amd64.tar.gz
cd anylink

# Create configuration directory
mkdir -p conf db log

# Generate self-signed certificates (or use Let's Encrypt)
openssl req -x509 -newkey rsa:4096 -keyout conf/server.key   -out conf/server.crt -days 365 -nodes   -subj "/CN=vpn.example.com"

# Start the server
./anylink -c conf/server.conf
```

**Server configuration (server.conf):**

```ini
[server]
; Admin web interface port
admin_addr = :8800
; VPN listen port
server_addr = :443
; Certificate files
cert_file = conf/server.crt
key_file = conf/server.key

[network]
; VPN subnet
ipv4_master = eth0
ipv4_cidr = 192.168.200.0/24
ipv4_gateway = 192.168.200.1
; DNS servers for VPN clients
dns_server = 8.8.8.8,8.8.4.4

[auth]
; Authentication type: local, ldap, radius, oauth
auth_type = local
; OTP enabled
otp = true

[log]
; Log level: debug, info, warn, error
level = info
```

AnyLink is the most user-friendly option for operators who want an all-in-one VPN server with a built-in web management interface. Its Go implementation means minimal resource overhead — it runs comfortably on a 1 vCPU, 512 MB RAM instance.

## ocserv (OpenConnect VPN Server)

[ocserv](https://gitlab.com/openconnect/ocserv) is the reference open-source implementation of an AnyConnect-compatible SSL VPN server. Developed as the server-side counterpart to the OpenConnect client, it provides a comprehensive feature set matching Cisco's commercial offering.

**Key features:**

- Full AnyConnect protocol compatibility
- Multiple authentication backends: PAM, LDAP, RADIUS, certificate, TOTP
- Route-based and MAC-based split tunneling
- Per-user and per-group bandwidth limits
- Session timeout and dead peer detection
- Multiple listening addresses and ports
- Integration with FreeRADIUS for enterprise authentication

**Docker Compose deployment:**

```yaml
version: "3.8"

services:
  ocserv:
    image: straub/ocserv:latest
    container_name: ocserv
    restart: unless-stopped
    ports:
      - "443:443/tcp"
      - "443:443/udp"
    volumes:
      - ./config/ocserv:/etc/ocserv
      - ./certs:/etc/ocserv/certs
      - ./data:/var/lib/ocserv
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    sysctls:
      - net.ipv4.ip_forward=1
    environment:
      - OCSERV_ADMIN_USER=admin
      - OCSERV_ADMIN_PASS=change_me
      - OCSERV_NET=192.168.100.0/24
      - OCSERV_DNS=8.8.8.8,8.8.4.4
      - OCSERV_DOMAIN=example.com
    networks:
      - vpn_net

networks:
  vpn_net:
    driver: bridge
```

**Manual install and configuration:**

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y ocserv gnutls-bin

# Generate CA certificate
certtool --generate-privkey --outfile ca-key.pem
certtool --generate-self-signed --load-privkey ca-key.pem   --outfile ca-cert.pem --template ca.tmpl

# Generate server certificate
certtool --generate-privkey --outfile server-key.pem
certtool --generate-certificate --load-privkey server-key.pem   --load-ca-certificate ca-cert.pem --load-ca-privkey ca-key.pem   --outfile server-cert.pem --template server.tmpl

# Create user
ocpasswd -c /etc/ocserv/ocpasswd vpnuser
```

**Main configuration (ocserv.conf):**

```ini
# Authentication
auth = "plain[passwd=/etc/ocserv/ocpasswd]"

# Server settings
tcp-port = 443
udp-port = 443
run-as-user = nobody
run-as-group = daemon
socket-file = /var/run/ocserv-socket
server-cert = /etc/ocserv/certs/server-cert.pem
server-key = /etc/ocserv/certs/server-key.pem
ca-cert = /etc/ocserv/certs/ca-cert.pem

# Network
ipv4-network = 192.168.100.0
ipv4-netmask = 255.255.255.0
dns = 8.8.8.8
dns = 8.8.4.4
domain = example.com

# Routes
route = 192.168.1.0/255.255.255.0
no-route = 192.168.100.0/255.255.255.0

# Limits
max-clients = 16
max-same-clients = 2
rate-limit-ms = 100
session-timeout = 480
idle-timeout = 300
mobile-idle-timeout = 1800

# Security
cookie-timeout = 3600
cert-user-oid = 2.5.4.3
keepalive = 32400
dpd = 90
mobile-dpd = 1800
try-mtu-discovery = true
```

ocserv is the most mature and feature-complete open-source AnyConnect server, with extensive configuration options and enterprise authentication integration. It is the reference implementation used by most AnyConnect-compatible deployments.

## OCServ Dashboard (Community Management UI)

While ocserv provides powerful server functionality, it lacks a built-in web management interface. The [OCServ Dashboard](https://github.com/mmtaee/ocserv-dashboard) project fills this gap by providing a modern TypeScript-based web UI for managing ocserv users, groups, and server settings.

**Key features:**

- Web-based user and group management for ocserv
- Real-time connection statistics and bandwidth monitoring
- Automated account expiration management
- Usage tracking and reporting
- Modern responsive UI with dark mode

**Docker Compose with Dashboard:**

```yaml
version: "3.8"

services:
  ocserv:
    image: ubuntu/ocserv:latest
    container_name: ocserv
    restart: unless-stopped
    ports:
      - "443:443/tcp"
      - "443:443/udp"
    volumes:
      - ./ocserv-config:/etc/ocserv
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
    sysctls:
      - net.ipv4.ip_forward=1
    networks:
      - vpn

  ocserv-dashboard:
    image: mmtaee/ocserv-dashboard:latest
    container_name: ocserv-dashboard
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./ocserv-config:/etc/ocserv:rw
      - ./dashboard-data:/app/data
    environment:
      - OCSERV_CONFIG_PATH=/etc/ocserv/ocserv.conf
      - OCSERV_PASSWD_PATH=/etc/ocserv/ocpasswd
    depends_on:
      - ocserv
    networks:
      - vpn

networks:
  vpn:
    driver: bridge
```

This approach combines the battle-tested ocserv server with a modern management interface, giving you the best of both worlds: enterprise-grade VPN functionality and an intuitive administrative experience.

## Comparison Table

| Feature | AnyLink | ocserv | ocserv + Dashboard |
|---------|---------|--------|---------------------|
| **Language** | Go | C | C (server) + TypeScript (UI) |
| **AnyConnect Stars** | 2,272+ | Reference implementation | 234+ (dashboard) |
| **Web Management UI** | Built-in | No (CLI only) | Yes (community dashboard) |
| **Authentication** | Local, LDAP, RADIUS, OAuth | PAM, LDAP, RADIUS, cert, TOTP | Via ocserv backends |
| **2FA / OTP** | Built-in TOTP | Via PAM/RADIUS | Via ocserv backends |
| **Split Tunneling** | Yes (route policy) | Yes (route + MAC-based) | Yes (via ocserv) |
| **Bandwidth Limits** | Per-group | Per-user, per-group | Via ocserv |
| **Docker Image** | Official | Community (straub, ubuntu) | Official dashboard image |
| **Resource Usage** | Low (Go, ~50 MB RAM) | Low (C, ~30 MB RAM) | Low + ~100 MB for dashboard |
| **Active Development** | Very active (Go) | Active (C, GitLab) | Active (TypeScript) |
| **Best For** | All-in-one with web UI | Enterprise, CLI operators | Best of both worlds |

## Choosing the Right AnyConnect Server

**Use AnyLink if:** You want a complete VPN solution with a built-in web management interface, minimal dependencies, and a single binary deployment. AnyLink is ideal for small-to-medium organizations, homelabs, and operators who prefer a GUI over command-line configuration.

**Use ocserv if:** You need the most mature, feature-complete open-source AnyConnect server with extensive authentication options (PAM, LDAP, RADIUS, certificates). ocserv is the best choice for enterprise environments, organizations with existing directory infrastructure, and operators comfortable with CLI-based configuration.

**Use ocserv + Dashboard if:** You want ocserv's enterprise authentication capabilities combined with a modern web management interface for user administration and monitoring. This approach is ideal for organizations that need both enterprise-grade security and operator-friendly management.

## Why Self-Host Your AnyConnect VPN?

Remote access VPNs are critical infrastructure for distributed teams, but commercial AnyConnect solutions (Cisco ASA/Firepower) carry substantial licensing costs — often $10-30 per concurrent user. For organizations with 50+ remote workers, this translates to $6,000-36,000+ annually.

Self-hosting an AnyConnect-compatible server eliminates per-user licensing while providing full protocol compatibility with the widely deployed AnyConnect client ecosystem. You control the authentication backend, certificate infrastructure, routing policies, and data retention — all without vendor-imposed limitations.

For comparison with WireGuard-based VPN alternatives, see our [Firezone vs Pritunl vs NetBird guide](../firezone-vs-pritunl-vs-netbird-self-hosted-wireguard-vpn-guide/) and our [complete WireGuard management UI comparison](../wg-easy-vs-wireguard-ui-vs-wg-gen-web-self-hosted-wireguard-management-guide/). If you need IPSec tunnel configurations, our [StrongSwan vs LibreSwan vs SoftEther VPN gateway comparison](../strongswan-vs-libreswan-vs-softether-self-hosted-vpn-gateway/) covers traditional IPsec deployments.

## FAQ

### Can I use the official Cisco AnyConnect client with these servers?

Yes. All three solutions are fully compatible with the official Cisco AnyConnect Secure Mobility Client available for Windows, macOS, Linux, iOS, and Android. The OpenConnect protocol is an open implementation of the AnyConnect SSL VPN protocol, and Cisco clients connect to it without modification.

### Is AnyLink production-ready?

AnyLink has been actively developed since 2020 and is used in production by numerous organizations. However, ocserv has a longer track record (since 2013) and is considered the reference implementation. For mission-critical deployments with complex authentication requirements (LDAP, RADIUS, certificate-based auth), ocserv is the more battle-tested choice. AnyLink is excellent for straightforward deployments where its built-in web UI is a significant advantage.

### How do I set up Let's Encrypt certificates for my VPN server?

For AnyLink and ocserv, you can use Certbot to obtain certificates and then configure the server to use them:

```bash
# Obtain certificates
certbot certonly --standalone -d vpn.example.com

# For ocserv, convert PEM to GnuTLS format
cat /etc/letsencrypt/live/vpn.example.com/fullchain.pem > /etc/ocserv/certs/server-cert.pem
cat /etc/letsencrypt/live/vpn.example.com/privkey.pem > /etc/ocserv/certs/server-key.pem

# Restart ocserv
systemctl restart ocserv
```

You'll need to renew certificates every 90 days (Certbot can automate this via cron).

### Can I use RADIUS authentication with ocserv?

Yes. ocserv supports RADIUS authentication natively:
```
auth = "radius[config=/etc/radiusclient/radiusclient.conf,groupconfig=true]"
```
Configure your RADIUS server details in the radiusclient.conf file, and ocserv will authenticate users against your existing RADIUS infrastructure (FreeRADIUS, Microsoft NPS, etc.).

### What port does the AnyConnect protocol use?

AnyConnect primarily uses TCP/UDP port 443 (HTTPS). This makes it highly firewall-friendly since port 443 is rarely blocked. Some deployments also use UDP 443 for the DTLS data channel, which provides better performance than TCP for the encrypted data tunnel.

### How many concurrent users can these servers handle?

Performance depends on server resources and encryption overhead:
- **AnyLink**: 100-500 concurrent users on a 2 vCPU, 2 GB RAM instance
- **ocserv**: 500-2,000+ concurrent users on a 4 vCPU, 4 GB RAM instance (tuned configuration)
- **ocserv + Dashboard**: Similar to ocserv (dashboard adds minimal overhead)

For production deployments, monitor CPU usage during peak hours — DTLS encryption and decryption are the primary CPU consumers.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted AnyConnect VPN Servers — AnyLink vs ocserv vs OCServ-Dashboard",
  "description": "Compare three open-source AnyConnect-compatible VPN servers: AnyLink (Go-native with web UI), ocserv (reference implementation), and ocserv with community dashboard. Includes Docker Compose configs and deployment guides.",
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

