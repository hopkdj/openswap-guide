---
title: "Self-Hosted BGP Monitoring & Looking Glass: ExaBGP, BGPalerter, and Open-Source Looking Glass Servers"
date: 2026-05-04T10:00:00+00:00
tags: ["bgp", "networking", "monitoring", "looking-glass", "exabgp", "self-hosted"]
draft: false
---

Border Gateway Protocol (BGP) is the routing protocol that holds the internet together. For network operators, ISPs, and enterprises running their own autonomous systems, maintaining visibility into BGP route advertisements, detecting hijacks, and providing public-facing looking glass services are critical operational requirements. Commercial BGP monitoring platforms can cost thousands of dollars per month — but several powerful open-source tools let you build a complete BGP monitoring and looking glass stack on your own infrastructure.

This guide compares three open-source approaches to self-hosted BGP monitoring and looking glass services: **ExaBGP**, **BGPalerter**, and **Open-Source Looking Glass servers** (including DjangoLG and hsdn/lg).

## Quick Comparison

| Feature | ExaBGP | BGPalerter | DjangoLG / hsdn/lg |
|---|---|---|---|
| Primary Purpose | BGP API / Route control | Real-time BGP alerting | Public looking glass |
| Language | Python | Python | Python (Django) / PHP |
| GitHub Stars | 2,269+ | 1,100+ | 8–44 |
| Last Active | April 2026 | Active | Active |
| Docker Support | Official Dockerfile | Yes | Self-build |
| Web UI | No (API-driven) | No (CLI alerts) | Yes (web interface) |
| BGP Peering | Full BGP daemon | Passive RIS collector | Router CLI passthrough |
| Use Case | Route injection, monitoring, automation | Hijack detection, route leak alerts | Public BGP diagnostics |

## ExaBGP — The BGP Swiss Army Knife

[ExaBGP](https://github.com/Exa-Networks/exabgp) is the most popular open-source BGP tool, maintained by Exa Networks with over 2,200 GitHub stars. Unlike traditional BGP daemons such as BIRD or FRRouting, ExaBGP does not manipulate the kernel's Forwarding Information Base (FIB). Instead, it provides a programmable BGP interface that lets you announce, withdraw, and monitor routes using Python scripts or external programs via STDIN/STDOUT.

### Key Features

- **Programmable BGP**: Announce and withdraw routes dynamically via Python scripts or any external process
- **API-Driven Architecture**: All BGP operations exposed through a simple text-based API
- **Flow Specification**: Push BGP FlowSpec rules for DDoS mitigation and traffic engineering
- **Lukasa/Health Check Integration**: Trigger route announcements based on service health checks
- **JSON Output**: Parseable JSON output for integration with monitoring pipelines
- **Python 3.13 Support**: Modern Python runtime with async capabilities

### Docker Deployment

ExaBGP provides an official Dockerfile based on Python 3.13-bookworm. Here is a production-ready Docker Compose configuration:

```yaml
version: "3.8"

services:
  exabgp:
    image: exabgp:latest
    build:
      context: .
      dockerfile: Dockerfile
    container_name: exabgp
    network_mode: host
    volumes:
      - ./etc/exabgp:/etc/exabgp:ro
      - ./scripts:/opt/exabgp/scripts:ro
      - ./log:/var/log/exabgp
    environment:
      - EXABGP_LOG=/var/log/exabgp
    restart: unless-stopped
```

The `network_mode: host` setting is critical because BGP uses TCP port 179, which requires direct network access. Mount your configuration directory as read-only and store logs persistently.

### ExaBGP Configuration Example

A minimal ExaBGP configuration for monitoring BGP peers:

```ini
group to-monitor {
    router-id 192.0.2.1;
    local-address 192.0.2.1;

    neighbor 203.0.113.1 {
        router-id 203.0.113.1;
        local-as 65001;
        peer-as 65002;

        family {
            ipv4 unicast;
            ipv6 unicast;
        }

        api {
            processes [ route-monitor ];
        }
    }
}

process route-monitor {
    run /opt/exabgp/scripts/monitor.py;
    encoder json;
}
```

This configuration establishes a BGP session with a neighbor peer, enables both IPv4 and IPv6 unicast address families, and pipes all route updates to a Python script via JSON-encoded messages.

## BGPalerter — Real-Time BGP Threat Detection

BGPalerter is an open-source BGP monitoring tool designed specifically for detecting BGP hijacks, route leaks, and RPKI invalid announcements in real time. It connects to RIPE RIS (Routing Information Service) collectors and applies configurable heuristics to identify anomalous routing events.

### Key Features

- **Hijack Detection**: Identifies origin AS hijacks and sub-prefix hijacks using RIPE RIS data
- **Route Leak Detection**: Detects unintended route propagation through incorrect AS paths
- **RPKI Validation**: Flags RPKI-invalid route announcements for compliance monitoring
- **Configurable Alerts**: Supports email, Slack, webhooks, and syslog notification channels
- **YAML Configuration**: Declarative configuration for monitored prefixes and AS numbers
- **Low Resource Footprint**: Runs efficiently on minimal hardware as a background daemon

### Docker Deployment

BGPalerter can be containerized with a straightforward Docker Compose setup:

```yaml
version: "3.8"

services:
  bgpalerter:
    image: massimocandela/bgpalerter:latest
    container_name: bgpalerter
    volumes:
      - ./config.yml:/app/config.yml:ro
      - ./prefixes.yml:/app/prefixes.yml:ro
      - ./data:/app/data
    environment:
      - TZ=UTC
    restart: unless-stopped
```

### BGPalerter Configuration

A sample `prefixes.yml` configuration to monitor your network's prefixes:

```yaml
monitoredPrefixes:
  - prefix: "203.0.113.0/24"
    description: "Primary IPv4 block"
    asn: 65001
    ignoreMoreSpecifics: false
    rpkiValidate: true

  - prefix: "2001:db8::/32"
    description: "Primary IPv6 block"
    asn: 65001
    ignoreMoreSpecifics: false
    rpkiValidate: true

notifications:
  - type: console
  - type: webhook
    url: "https://hooks.example.com/bgp-alerts"
    method: POST
    headers:
      Content-Type: application/json
```

This configuration monitors specific prefixes for hijacks and route leaks, validates them against RPKI, and sends alerts to both the console and a webhook endpoint.

## Open-Source Looking Glass Servers

A BGP Looking Glass is a public-facing web service that allows network operators and engineers to run diagnostic BGP commands (show routes, show bgp summary, traceroute, ping) against your routers without providing direct shell or SSH access. While commercial looking glass platforms exist, several open-source implementations provide full functionality.

### DjangoLG — Python-Based Looking Glass

[DjangoLG](https://github.com/wolcomm/djangolg) is a Django-based BGP looking glass that supports multiple router vendors (Cisco IOS/IOS-XR, Juniper JunOS, Arista EOS, MikroTik RouterOS). It provides a clean web interface with SSH-based connectivity to your network infrastructure.

**Key Features:**
- Multi-vendor router support via template-based command sets
- Role-based access control (public read-only, authenticated advanced queries)
- IPv4 and IPv6 BGP table display
- Ping and traceroute diagnostics from router perspective
- REST API for programmatic access

### hsdn/lg — PHP Looking Glass

[hsdn/lg](https://github.com/hsdn/lg) is a lightweight PHP-based BGP looking glass, forked from the original Cougar/lg Perl implementation. It is designed for simplicity and ease of deployment on any standard LAMP stack.

**Key Features:**
- PHP-based — runs on any shared hosting environment
- Supports Cisco IOS, Juniper JunOS, and Quagga/FRRouting
- BGP route table queries and AS path lookups
- DNS and ping diagnostics
- Minimal resource requirements

### Looking Glass Deployment Example

Here is a Docker Compose configuration for a Django-based looking glass:

```yaml
version: "3.8"

services:
  djangolg:
    image: python:3.11-slim
    container_name: djangolg
    working_dir: /app
    volumes:
      - ./djangolg:/app
      - ./ssh-keys:/root/.ssh:ro
    ports:
      - "8000:8000"
    command: >
      bash -c "pip install -r requirements.txt &&
               python manage.py migrate &&
               python manage.py runserver 0.0.0.0:8000"
    restart: unless-stopped
```

For production deployments, replace the runserver command with Gunicorn behind an Nginx reverse proxy:

```nginx
server {
    listen 80;
    server_name lg.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## When to Use Each Tool

| Scenario | Recommended Tool |
|---|---|
| Programmable route injection and automation | ExaBGP |
| Real-time hijack and route leak detection | BGPalerter |
| Public-facing BGP diagnostics portal | DjangoLG or hsdn/lg |
| FlowSpec DDoS mitigation | ExaBGP |
| RPKI compliance monitoring | BGPalerter |
| Multi-vendor route diagnostics | DjangoLG |
| Lightweight shared-hosting looking glass | hsdn/lg |

For a complete BGP operations stack, combine all three: ExaBGP for route control, BGPalerter for threat detection, and a looking glass for public diagnostics.

## Self-Hosting BGP Infrastructure: Network Requirements

Running BGP monitoring tools requires careful network planning:

- **BGP Peering**: ExaBGP needs a real BGP session with a router or route server. Use a loopback interface with a valid router ID.
- **Passive Collection**: BGPalerter connects to public RIS collectors — no BGP peering required, making it ideal for organizations without their own ASN.
- **Router Access**: Looking glass servers need SSH access to your routers. Use dedicated read-only accounts with restricted command sets.
- **Firewall Rules**: Allow TCP port 179 (BGP) inbound for ExaBGP peering. Looking glass servers typically run on ports 80/443 behind a reverse proxy.

For broader network monitoring strategy and infrastructure visibility, see our [network topology mapping guide](../2026-05-02-self-hosted-network-topology-mapping-netbox-librenms-auto-discovery/) and [BGP routing daemon comparison](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/).

## Why Self-Host Your BGP Monitoring?

Commercial BGP monitoring services like Cloudflare Magic Transit, ThousandEyes, and BGPMon charge premium pricing for features that open-source tools provide out of the box. Self-hosting gives you complete control over your BGP visibility pipeline:

- **No Vendor Lock-In**: Your BGP data stays on your infrastructure. No third-party dependency for critical network operations.
- **Real-Time Alerts**: BGPalerter processes RIS data streams in real time, providing sub-second hijack detection without API rate limits.
- **Custom Automation**: ExaBGP's programmable interface lets you build custom route automation workflows that integrate with your existing monitoring stack.
- **Public Transparency**: A self-hosted looking glass demonstrates operational transparency to peers, customers, and the broader networking community.
- **Cost Savings**: Running all three tools on a single VPS costs less than $20/month — compared to $500–5,000/month for commercial equivalents.

For network access control and BGP-aware security policies, our [NAC platforms guide](../2026-04-19-packetfence-vs-freeradius-vs-coovachilli-self-hosted-nac-guide-2026/) covers complementary infrastructure.

## FAQ

### What is a BGP Looking Glass?

A BGP Looking Glass is a public web service that allows network engineers to query BGP routing information from a remote router without direct access. Users can check route advertisements, AS paths, and run ping/traceroute diagnostics from the router's perspective. Looking glasses are commonly used for troubleshooting routing issues and verifying route propagation.

### Do I need my own ASN to use ExaBGP?

Yes, ExaBGP establishes real BGP sessions and requires a valid ASN and IP address for peering. If you don't have your own ASN, consider using BGPalerter which connects passively to public RIS collectors, or set up a looking glass to query existing routers.

### How does BGPalerter detect route hijacks?

BGPalerter monitors RIPE RIS BGP data streams and compares observed route origins against a configured list of authorized prefixes and AS numbers. When a prefix is announced from an unauthorized origin AS, or when a more-specific sub-prefix appears (potential sub-prefix hijack), BGPalerter triggers an alert through your configured notification channel.

### Can I run a looking glass without direct router access?

No, looking glass servers need SSH (or NETCONF/API) access to routers to execute diagnostic commands. However, you can configure a dedicated read-only user account with a restricted command set (e.g., only `show bgp`, `show ip route`, `ping`, and `traceroute`) to minimize security risk.

### Is ExaBGP production-ready for route injection?

Yes, ExaBGP is used in production by multiple ISPs and cloud providers for route injection, DDoS mitigation via FlowSpec, and traffic engineering. However, you should thoroughly test configurations in a lab environment before deploying to production BGP sessions. Always have a rollback plan.

### What is RPKI validation and why does it matter?

RPKI (Resource Public Key Infrastructure) cryptographically validates that an AS is authorized to announce a specific IP prefix. BGPalerter can check route announcements against RPKI data and flag RPKI-invalid routes, which may indicate hijacks or misconfigurations. Deploying RPKI ROAs for your own prefixes helps protect your routes from hijacking.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted BGP Monitoring & Looking Glass: ExaBGP, BGPalerter, and Open-Source Looking Glass Servers",
  "description": "Compare open-source BGP monitoring tools — ExaBGP for programmable route control, BGPalerter for real-time hijack detection, and DjangoLG/hsdn/lg for public looking glass services. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
