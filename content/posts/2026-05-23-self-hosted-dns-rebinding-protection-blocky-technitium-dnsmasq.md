---
title: "Self-Hosted DNS Rebinding Protection: Blocky vs Technitium DNS vs dnsmasq"
date: "2026-05-23"
tags: ["dns", "security", "networking", "self-hosted"]
draft: false
---

DNS rebinding attacks exploit the trust that web applications place in DNS responses. An attacker controls a domain that resolves first to their server, then quickly changes to an internal IP address (like `127.0.0.1` or `192.168.1.1`). Because browsers share connections based on hostname, not IP, a malicious webpage can bypass same-origin policy and interact with internal services — routers, smart home devices, databases, and admin panels.

Self-hosted DNS servers can prevent these attacks by filtering rebinding attempts at the resolver level. This guide compares three popular DNS servers that offer DNS rebinding protection: **Blocky**, **Technitium DNS Server**, and **dnsmasq**.

## What Is a DNS Rebinding Attack?

A DNS rebinding attack works in two phases:

1. **Phase 1 — Initial Resolution**: The victim visits a malicious website controlled by the attacker. The domain (e.g., `evil.attacker.com`) resolves to the attacker's public server. The browser establishes a connection and loads malicious JavaScript.

2. **Phase 2 — Rebind**: The attacker changes the DNS record for `evil.attacker.com` to resolve to an internal IP address (e.g., `192.168.1.1` — the victim's router). The browser's same-origin policy still treats `evil.attacker.com` as the same origin, but the connection now goes to the internal device.

The JavaScript running in the browser can now send HTTP requests to the internal device, potentially reading sensitive data or executing administrative actions. This bypasses the same-origin policy because the browser identifies origins by hostname, not by IP address.

## Comparison Overview

| Feature | Blocky | Technitium DNS | dnsmasq |
|---------|--------|---------------|---------|
| **GitHub Stars** | 6,641 | 8,488 | N/A (Debian/official repos) |
| **Language** | Go | C# (.NET) | C |
| **License** | Apache 2.0 | GPLv3 | GPLv2 |
| **Rebinding Protection** | Yes (built-in) | Yes (built-in) | Yes (`stop-dns-rebind`) |
| **Ad Blocking** | Yes (blocklists) | Yes (blocklists) | No |
| **DNS-over-HTTPS** | Yes | Yes | No |
| **DNS-over-TLS** | Yes | Yes | No |
| **DNS-over-QUIC** | Yes | Yes | No |
| **Web UI** | No | Yes (built-in) | No |
| **Docker Image** | `0xerr0r/blocky` | `technitium/dns-server` | `linuxserver/dnsmasq` |
| **Upstream DNS** | Configurable | Configurable | Configurable |
| **Conditional Forwarding** | Yes | Yes | Yes |
| **Best For** | Privacy-focused networks | Full DNS server with UI | Lightweight embedded DNS |

## Blocky

[Blocky](https://github.com/0xERR0R/blocky) is a fast, lightweight DNS proxy written in Go. Originally designed as an ad-blocker for local networks, it includes built-in DNS rebinding protection that filters responses containing private IP addresses for external domains.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  blocky:
    image: spx01/blocky:latest
    container_name: blocky
    restart: unless-stopped
    ports:
      - "53:53/tcp"
      - "53:53/udp"
      - "4000:4000/tcp"
    volumes:
      - ./config.yml:/app/config.yml:ro
    environment:
      - TZ=UTC
```

### Blocky Configuration (config.yml)

```yaml
upstream:
  default:
    - tcp+udp:1.1.1.1
    - tcp+udp:8.8.8.8

blocking:
  blackLists:
    ads:
      - https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
      - https://adguardteam.github.io/HostsFilter/AdguardDNS-filter.txt
  clientGroupsBlock:
    default:
      - ads

filtering:
  queryLog:
    type: csv
    path: /var/log/blocky
    perClient: false

dnsRebindingProtection:
  enabled: true
  # Allowlist for domains that legitimately resolve to private IPs
  allowlist:
    - "*.internal.example.com"
    - "localhost"

ports:
  dns: 53
  http: 4000

log:
  level: info
  format: text
```

### How Blocky Prevents Rebinding

Blocky's rebinding protection checks DNS response addresses against configurable private IP ranges. When a response for an external domain contains a private IP (RFC 1918, loopback, link-local), Blocky either:

- **Blocks the response** — returns NXDOMAIN to the client
- **Allows from whitelist** — permits specific domains that legitimately resolve to internal IPs (e.g., split-DNS setups)
- **Logs the event** — records the attempted rebind for analysis

### Key Features

- **Fast response times** — Written in Go with concurrent query processing
- **Multiple blocklist sources** — Supports host files, domains lists, and custom rules
- **Prometheus metrics** — Export DNS query statistics for monitoring dashboards
- **Conditional forwarding** — Route queries for specific zones to internal DNS servers
- **Caching** — In-memory cache with configurable TTL
- **Docker-native** — Official image with health checks and minimal configuration

## Technitium DNS Server

[Technitium DNS Server](https://github.com/TechnitiumSoftware/DnsServer) is a full-featured, self-hosted DNS server written in C# with a comprehensive web management interface. It includes DNS rebinding protection alongside ad blocking, DNSSEC validation, and DNS-over-HTTPS/TLS/QUIC support.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  technitium-dns:
    image: technitium/dns-server:latest
    container_name: technitium-dns
    restart: unless-stopped
    ports:
      - "5380:5380/tcp"
      - "53:53/tcp"
      - "53:53/udp"
      - "853:853/tcp"
      - "853:853/udp"
    volumes:
      - ./dns-config:/etc/dns
    environment:
      - DNS_SERVER_DOMAIN=dns.example.com
      - DNS_SERVER_ADMIN_PASSWORD=secretpassword
```

### Configuration via Web UI

Technitium DNS is primarily configured through its web interface at `http://<server>:5380`. For rebinding protection:

1. Navigate to **Settings → Security**
2. Enable **"Block DNS Rebinding Attacks"**
3. Configure the **Private IP Range Exceptions** list for domains that legitimately resolve to internal addresses
4. Set the **Minimum TTL** to prevent rapid record changes (a common rebinding technique)

### How Technitium DNS Prevents Rebinding

Technitium DNS implements rebinding protection through multiple mechanisms:

- **Private IP filtering** — Blocks DNS responses that resolve external domains to RFC 1918, loopback, or link-local addresses
- **Minimum TTL enforcement** — Prevents attackers from using extremely short TTLs to switch between public and private IPs
- **Allowlist management** — Per-domain exceptions for legitimate internal DNS through split-horizon setups
- **DNSSEC validation** — Rejects responses that fail DNSSEC signature verification, preventing spoofed rebinding responses

### Key Features

- **Full DNS server** — Authoritative and recursive DNS in one package
- **Web management UI** — Browser-based configuration and monitoring
- **DNS-over-HTTPS/TLS/QUIC** — Encrypted DNS for all clients
- **DNSSEC validation** — Cryptographic verification of DNS responses
- **Zone management** — Create and manage DNS zones through the web interface
- **Query logging** — Detailed logs with CSV export and dashboard visualization
- **API support** — RESTful API for automation and integration

### REST API Example

```bash
# Get DNS server status
curl -s http://localhost:5380/api/serverInfo?token=YOUR_API_TOKEN

# Add a DNS zone
curl -X POST http://localhost:5380/api/zone/add   -d "token=YOUR_API_TOKEN"   -d "zoneName=internal.example.com"
```

## dnsmasq

[dnsmasq](http://www.thekelleys.org.uk/dnsmasq/) is a lightweight DNS forwarder, DHCP server, and router advertisement daemon. It's one of the most widely deployed DNS servers, included by default in many Linux distributions, OpenWrt routers, and embedded systems. Its DNS rebinding protection is a simple but effective configuration option.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  dnsmasq:
    image: linuxserver/dnsmasq:latest
    container_name: dnsmasq
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./dnsmasq.conf:/config/dnsmasq.conf:ro
    environment:
      - TZ=UTC
```

### dnsmasq Configuration

```ini
# /etc/dnsmasq.conf

# Upstream DNS servers
server=1.1.1.1
server=8.8.8.8

# DNS rebinding protection
# Block responses containing private IP addresses for external domains
stop-dns-rebind

# Allow specific domains to resolve to private IPs (split-DNS)
rebind-domain-ok=/internal.example.com/
rebind-domain-ok=/lan.local/

# Never forward plain names (no dots)
domain-needed

# Never forward addresses in non-routable spaces
bogus-priv

# Cache size
cache-size=1000

# Logging
log-queries
log-facility=/var/log/dnsmasq.log

# DHCP configuration (optional)
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
```

### How dnsmasq Prevents Rebinding

The `stop-dns-rebind` directive instructs dnsmasq to reject DNS responses that contain private IP addresses (RFC 1918, 127.0.0.0/8, 169.254.0.0/16) for queries about domains that are not locally configured. The `rebind-domain-ok` directive creates exceptions for specific domains that legitimately need to resolve to internal addresses.

### Key Features

- **Extremely lightweight** — ~200KB binary, minimal memory footprint
- **DNS + DHCP** — Combined DNS forwarding and DHCP server
- **TFTP support** — Built-in TFTP server for PXE boot
- **Wildcard DNS** — Easy wildcard DNS entries for local domains
- **Embedded-friendly** — Runs on routers, IoT devices, and minimal systems
- **Widely available** — Pre-installed on OpenWrt, many Linux distributions

## Configuration Comparison: Rebinding Protection

| Setting | Blocky | Technitium DNS | dnsmasq |
|---------|--------|---------------|---------|
| **Enable protection** | `dnsRebindingProtection.enabled: true` | Web UI toggle | `stop-dns-rebind` |
| **Allowlist format** | YAML list of domains | Web UI per-domain entry | `rebind-domain-ok=/domain/` |
| **Private IP ranges** | Configurable in config | Configurable via UI | Hardcoded (RFC 1918 + loopback) |
| **Logging** | Query log (CSV) | Web dashboard + CSV | Syslog or file |
| **Minimum TTL** | Via upstream config | Built-in setting | Via `min-cache-ttl` |
| **Per-client rules** | Yes (clientGroupsBlock) | Yes (per-client settings) | No |

## Choosing the Right DNS Rebinding Protection

**Use Blocky when:**
- You want a lightweight, fast DNS proxy with ad blocking
- You're already using Docker and prefer YAML configuration
- You need Prometheus metrics for monitoring
- You want DNS-over-HTTPS/QUIC without a full DNS server

**Use Technitium DNS when:**
- You need a full DNS server with authoritative zone management
- You want a web-based management interface
- You need DNSSEC validation alongside rebinding protection
- You manage DNS for multiple zones and clients

**Use dnsmasq when:**
- You need the smallest possible footprint (routers, embedded systems)
- You want combined DNS + DHCP in one daemon
- You're running OpenWrt or a similar embedded distribution
- Simplicity and reliability are more important than features

## Security Best Practices for DNS Rebinding Protection

1. **Enable rebinding protection on all resolvers** — Every DNS server in your network path should filter private IP responses for external domains.
2. **Maintain an allowlist** — Legitimate internal services (split-DNS, local development servers) need to resolve to private IPs. Document and manage these exceptions.
3. **Set minimum TTL values** — Rebinding attacks rely on rapid DNS record changes. A minimum TTL of 60-300 seconds prevents this technique.
4. **Monitor DNS query logs** — Look for unusual patterns: rapid resolution changes, queries for uncommon internal IP ranges, or domains resolving to localhost.
5. **Use DNSSEC** — DNSSEC validation prevents attackers from injecting forged DNS responses that trigger rebinding.
6. **Layer with browser protections** — Modern browsers implement some rebinding protections (e.g., Private Network Access restrictions). DNS-level protection is a defense-in-depth measure, not a replacement for browser security.

## Why Self-Host DNS with Rebinding Protection?

Running your own DNS resolver gives you visibility into every DNS query on your network. When you add rebinding protection, you create a critical security layer that commercial DNS providers may not offer — or may offer with different policies and filtering rules.

For homelab operators, self-hosted DNS with rebinding protection safeguards internal services: router admin panels, smart home hubs, NAS management interfaces, and development servers. A single compromised IoT device could serve as a launching point for rebinding attacks against other internal services.

For organizations, DNS-level rebinding protection is a defense-in-depth control that complements network segmentation, firewall rules, and browser security policies. It catches attacks that bypass perimeter defenses and provides audit logs for incident response investigations.

For broader DNS security, see our [DNS firewall with RPZ guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/). For DNS-over-QUIC setup, check our [Knot vs Blocky vs DNScrypt-Proxy comparison](../2026-04-21-knot-resolver-vs-blocky-vs-dnscrypt-proxy-self-hosted-dns-over-quic-guide-2026/). For DNS query analytics, our [DNS logging and dashboards guide](../2026-04-23-self-hosted-dns-query-logging-analytics-dashboards-2026/) covers monitoring and visualization.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DNS Rebinding Protection: Blocky vs Technitium DNS vs dnsmasq",
  "description": "Protect your network from DNS rebinding attacks with Blocky, Technitium DNS Server, and dnsmasq. Configuration guides and comparison.",
  "datePublished": "2026-05-23",
  "dateModified": "2026-05-23",
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

### What exactly does DNS rebinding protection do?

DNS rebinding protection filters DNS responses that resolve external domain names to private IP addresses (like 192.168.x.x, 10.x.x.x, or 127.0.0.1). When an external domain resolves to a private IP, the DNS server blocks the response, preventing the browser from connecting to internal services under the guise of the external domain.

### Can DNS rebinding protection break legitimate services?

Yes, if your network uses split-DNS (where internal domains resolve to private IPs). You need to configure an allowlist for domains that legitimately resolve to internal addresses. All three tools support per-domain exceptions: Blocky uses a YAML allowlist, Technitium DNS has a web UI exception list, and dnsmasq uses `rebind-domain-ok` directives.

### Does DNS rebinding protection replace a firewall?

No. DNS rebinding protection is one layer of defense. It prevents the specific attack vector of DNS-based rebind attacks but doesn't protect against direct IP access, compromised internal devices, or other network-level attacks. Always combine it with firewall rules, network segmentation, and proper access controls.

### Which DNS server has the strongest rebinding protection?

Technitium DNS offers the most comprehensive protection because it combines private IP filtering with minimum TTL enforcement and DNSSEC validation. Blocky provides good protection with the added benefit of fast performance and Prometheus metrics. dnsmasq offers simple but effective protection ideal for resource-constrained environments.

### Do I need DNS rebinding protection if I use Cloudflare or Google DNS?

Commercial DNS providers like Cloudflare (1.1.1.1) and Google (8.8.8.8) do not filter private IP responses by default. They return whatever the authoritative server provides. If you use these as upstream resolvers, you still need a local DNS proxy (like Blocky or dnsmasq) to enforce rebinding protection at the network edge.

### Can rebinding attacks target non-HTTP services?

DNS rebinding attacks primarily target HTTP/HTTPS services because they exploit browser same-origin policy. However, some WebRTC and WebSocket implementations can also be affected. DNS rebinding protection helps by preventing the initial DNS resolution to internal IPs, regardless of the target protocol.

