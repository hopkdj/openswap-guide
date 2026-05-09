---
title: "Self-Hosted BGP Monitoring & Route Alerting: BGPalerter vs ExaBGP vs GoBGP (2026)"
date: "2026-05-09"
tags: ["networking", "bgp", "monitoring", "routing", "infrastructure", "security"]
draft: false
---

Border Gateway Protocol (BGP) is the backbone of internet routing, but it was designed in an era when trust was assumed between network operators. Today, BGP hijacks, route leaks, and misconfigurations cause regular internet outages affecting millions of users. Monitoring your BGP routes and receiving immediate alerts when something changes is essential for any organization that operates its own autonomous system (AS) or depends on specific upstream providers.

This guide compares three self-hosted tools for BGP monitoring and route alerting: **Cloudflare BGPalerter**, **ExaBGP**, and **GoBGP**. Each serves a different purpose — from passive monitoring to active route injection and full BGP speaker implementation.

## Why Monitor BGP Routes?

BGP incidents are not theoretical edge cases — they happen regularly and have real-world consequences:

- **Route hijacking** — Malicious actors announce your IP prefixes through different ASes, redirecting your traffic
- **Route leaks** — Misconfigured routers propagate routes beyond their intended scope, causing traffic blackholes
- **Prefix misconfiguration** — Typos in route filters can accidentally announce private IP space or wrong prefixes
- **Upstream provider failures** — When a transit provider has an outage, you need immediate notification to trigger failover
- **RPKI validation failures** — Invalid ROA (Route Origin Authorization) configurations can cause your routes to be dropped by RPKI-aware peers
- **Compliance and SLA tracking** — Enterprises need documented BGP monitoring for regulatory compliance and provider SLA verification

Self-hosted BGP monitoring keeps your routing intelligence in-house, avoids dependency on third-party looking glass services, and enables custom alerting thresholds tailored to your network topology.

## Quick Comparison

| Feature | Cloudflare BGPalerter | ExaBGP | GoBGP |
|---------|----------------------|--------|-------|
| **GitHub Stars** | 1,500+ | 2,268+ | 3,600+ |
| **Language** | JavaScript/Node.js | Python | Go |
| **Primary Role** | BGP monitoring & alerting | BGP API speaker | Full BGP implementation |
| **Passive Monitoring** | Yes (via BMP, RIPE RIS, RouteViews) | No (active peer) | Yes (via BMP) |
| **Active Peering** | No | Yes | Yes |
| **Route Injection** | No | Yes | Yes |
| **RPKI Validation** | Yes | Via external tools | Built-in |
| **Streaming API** | Yes | Native | gRPC |
| **Docker Support** | Yes | Yes | Yes |
| **License** | Apache 2.0 | LGPL 2.1 | Apache 2.0 |
| **Best For** | Monitoring & alerting | Route manipulation/testing | Full BGP speaker replacement |

## Cloudflare BGPalerter: Real-Time BGP Monitoring

[BGPalerter](https://github.com/cloudflare/bgpalerter) by Cloudflare is a purpose-built BGP monitoring tool that watches for prefix hijacks, route leaks, and visibility changes. It consumes data from public BGP collectors (RIPE RIS, RouteViews) and BMP (BGP Monitoring Protocol) feeds.

### Key Features

- **Hijack detection** — Alerts when your prefixes are announced by unauthorized ASes
- **Route leak detection** — Identifies routes propagating beyond intended boundaries
- **Visibility monitoring** — Tracks prefix visibility across global BGP collectors
- **RPKI validation** — Monitors ROA status and alerts on invalid origins
- **Configuration-driven** — Define monitored prefixes, AS numbers, and alert thresholds in YAML
- **Multiple notification channels** — Slack, email, webhook, and stdout alerts

### Docker Compose Deployment

```yaml
services:
  bgpalerter:
    image: cloudflare/bgpalerter:latest
    container_name: bgpalerter
    restart: unless-stopped
    volumes:
      - ./config.yml:/app/config.yml:ro
      - ./monitored_prefixes.yml:/app/monitored_prefixes.yml:ro
      - ./notifications.yml:/app/notifications.yml:ro
    command: ["-c", "config.yml"]
```

### Configuration

```yaml
# config.yml
checks:
  HijackDetection:
    enabled: true
    alert: true
  RouteLeakDetection:
    enabled: true
    alert: true
  Visibility:
    enabled: true
    alert: true

monitoredPrefixes:
  - prefix: 203.0.113.0/24
    asn: 64512
    description: "My production network"
    ignoreMorespecifics: false

notifications:
  Slack:
    enabled: true
    webhookUrl: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    channel: "#network-alerts"
```

### Installation (Non-Docker)

```bash
# Install from npm
npm install -g bgpalerter

# Or download binary from GitHub releases
wget https://github.com/cloudflare/bgpalerter/releases/latest/download/bgpalerter-linux-x64
chmod +x bgpalerter-linux-x64

# Run
./bgpalerter-linux-x64 -c config.yml
```

## ExaBGP: BGP API Speaker

[ExaBGP](https://github.com/Exa-Networks/exabgp) is a BGP implementation designed for programmability. Instead of running as a traditional router daemon, ExaBGP receives and sends BGP updates through a simple text-based API, making it ideal for route injection, testing, and automated traffic engineering.

### Key Features

- **Programmable BGP** — Send and receive BGP updates via stdin/stdout or API
- **Route injection** — Announce, withdraw, or modify routes programmatically
- **Flow specification** — Inject BGP Flow Spec rules for traffic filtering and redirection
- **Testing and validation** — Simulate BGP scenarios without configuring physical routers
- **Monitoring hook** — Process incoming BGP updates with custom scripts
- **Lightweight** — Single Python process with minimal resource requirements

### Docker Deployment

```yaml
services:
  exabgp:
    image: pavelz/exabgp:latest
    container_name: exabgp
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./exabgp.conf:/etc/exabgp/exabgp.conf:ro
      - ./scripts:/opt/exabgp/scripts
    environment:
      - EXABGP_LOG=all:info
```

### Configuration

```ini
# exabgp.conf
process watch-routes {
    run /opt/exabgp/scripts/monitor.py;
    encoder json;
}

neighbor 192.0.2.1 {
    router-id 192.0.2.2;
    local-as 64512;
    peer-as 64513;
    local-address 192.0.2.2;

    family {
        ipv4 unicast;
    }

    graceful-restart;

    api {
        processes [watch-routes];
    }
}
```

### Announcing Routes via API

```python
#!/usr/bin/env python3
# monitor.py - Process BGP updates and alert on changes
import sys, json

for line in sys.stdin:
    data = json.loads(line)
    if data.get('type') == 'update':
        for route in data.get('update', {}).get('announce', {}).get('ipv4 unicast', {}):
            print(f"ALERT: New route {route} from neighbor")
        for route in data.get('update', {}).get('withdraw', {}).get('ipv4 unicast', []):
            print(f"ALERT: Withdrawn route {route}")
    sys.stdout.flush()
```

## GoBGP: Full BGP Implementation in Go

[GoBGP](https://github.com/osrg/gobgp) is a complete BGP implementation written in Go that can replace traditional router software. It supports full BGP peering, RPKI validation, and programmable route control via gRPC API.

### Key Features

- **Full BGP speaker** — Supports eBGP, iBGP, route reflection, and confederations
- **RPKI integration** — Built-in RPKI client for route origin validation
- **gRPC API** — Programmatic control via Go gRPC or CLI
- **Multiple address families** — IPv4, IPv6, VPN, EVPN, and Flow Spec
- **Policy framework** — Route filtering, attribute manipulation, and redistribution
- **BMP support** — BGP Monitoring Protocol for passive route observation

### Docker Deployment

```yaml
services:
  gobgp:
    image: osrg/gobgp:latest
    container_name: gobgp
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./gobgp.conf:/etc/gobgp/gobgp.conf:ro
    command: ["-f", "/etc/gobgp/gobgp.conf", "-t", "yaml"]
```

### Configuration

```yaml
global:
  config:
    as: 64512
    router-id: 192.0.2.1

neighbors:
  - config:
      neighbor-address: 192.0.2.2
      peer-as: 64513
    afi-safis:
      - config:
          family: ipv4-unicast
    route-reflector:
      config:
        route-reflector-client: true

rpki:
  - config:
      address: rpki-validator.example.com
      port: 323
```

### CLI Operations

```bash
# Show BGP neighbors
gobgp neighbor

# Show received routes
gobgp global rib

# Announce a prefix
gobgp global rib add 203.0.113.0/24

# Withdraw a prefix
gobgp global rib del 203.0.113.0/24

# Show RPKI validation status
gobgp global rib -a ipv4 -j | jq '.[].attrs[].rpki'
```

## Why Self-Host BGP Monitoring?

**Independence from external services** — Public looking glass services and third-party BGP monitors may be unavailable during major internet incidents when you need them most. Self-hosted monitoring ensures continuous visibility regardless of external service status.

**Custom alerting thresholds** — Every network has different risk tolerance. Self-hosted tools let you configure alerts specific to your prefix portfolio, upstream providers, and peering arrangements. Need instant notification when a specific prefix is hijacked but only daily summaries for others? Self-hosted solutions support this granularity.

**Historical data retention** — Third-party services typically provide limited historical BGP data. Self-hosted monitoring stores all route changes locally, enabling long-term trend analysis, incident forensics, and SLA compliance reporting.

**Integration with network automation** — Self-hosted BGP tools integrate directly with your existing network management stack. BGPalerter webhooks can trigger Ansible playbooks, ExaBGP can feed route changes to your SDN controller, and GoBGP's gRPC API integrates with custom orchestration systems.

For broader network monitoring, see our [BGP route server guide](../2026-05-07-self-hosted-bgp-route-server-bird-openbgpd-frrouting/) and [network flow analysis comparison](../2026-05-15-self-hosted-network-flow-analysis-pmacct-nfdump-fprobe/). If you need BGP anycast routing, our [DNS anycast guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-routing/) covers that setup.

## FAQ

### What is BGP hijacking and how do I detect it?

BGP hijacking occurs when an unauthorized AS announces your IP prefixes, redirecting traffic intended for your network. Detection involves monitoring global BGP collectors (RIPE RIS, RouteViews) for unexpected origin ASes announcing your prefixes. BGPalerter automates this by continuously checking collector feeds against your authorized prefix list.

### Do I need to peer with BGP routers to use these tools?

BGPalerter does not require direct BGP peering — it monitors public BGP collector feeds and BMP streams. ExaBGP and GoBGP require BGP peering with a router or route server to exchange routes. For passive monitoring without peering, BGPalerter is the right choice.

### Can these tools prevent BGP hijacking?

No tool can prevent hijacking on its own. Prevention requires a combination of RPKI ROA registration, BGP prefix filters with upstream providers, IRR registration, and rapid detection/response. BGPalerter provides the detection component, while ExaBGP and GoBGP can automate mitigation by injecting more specific routes or blackhole routes.

### What is RPKI and why does it matter for BGP monitoring?

RPKI (Resource Public Key Infrastructure) provides cryptographic validation of BGP route origins. ROAs (Route Origin Authorizations) specify which ASes are authorized to announce specific prefixes. RPKI-aware routers drop routes with invalid ROA status. Monitoring your RPKI validation status ensures your routes are not inadvertently marked invalid due to misconfiguration.

### Can I use these tools with a home lab or small network?

Yes. If you have a BGP-speaking router (even a virtual one like FRRouting or BIRD in a lab), ExaBGP and GoBGP can peer with it. BGPalerter works without any local BGP infrastructure — just configure the prefixes you want to monitor and it checks global collector feeds.

### How much bandwidth does BGP monitoring consume?

BGPalerter consumes minimal bandwidth since it connects to public collector feeds over TCP. ExaBGP and GoBGP bandwidth usage depends on the number of routes in the BGP table — a full IPv4 global routing table contains approximately 900,000+ routes, requiring roughly 100-200 MB of initial sync and minimal ongoing bandwidth for updates.

### What is BMP (BGP Monitoring Protocol)?

BMP is an IETF standard (RFC 7854) that allows BGP speakers to send route updates and peer state information to a monitoring station without requiring the monitor to be a BGP peer. Both BGPalerter and GoBGP support BMP for passive route observation, enabling monitoring without impacting BGP peering sessions.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Monitoring & Route Alerting: BGPalerter vs ExaBGP vs GoBGP (2026)",
  "description": "Compare Cloudflare BGPalerter, ExaBGP, and GoBGP for self-hosted BGP route monitoring, hijack detection, and programmable routing.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
