---
title: "Routinator vs FORT vs cfrpki: Best Self-Hosted RPKI Validator 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "networking"]
draft: false
description: "Complete comparison of Routinator, FORT Validator, and Cloudflare cfrpki for self-hosted RPKI route origin validation. Docker deployment guides, configuration examples, and performance benchmarks for BGP security."
---

Securing your BGP routing infrastructure in 2026 means implementing **RPKI (Resource Public Key Infrastructure)** — a cryptographic framework that prevents route hijacking, accidental mis-origination, and prefix theft. Without RPKI validation, your routers accept any BGP announcement at face value, leaving your network vulnerable to the thousands of route leak and hijack incidents recorded every year.

Self-hosting an RPKI validator gives you full control over route origin validation, eliminates dependence on third-party validators, and lets you integrate validation directly into your BGP daemons like [BIRD](https://bird.network.cz/), [FRRouting](https://frrouting.org/), or [OpenBGPD](https://www.openbgpd.org/). This guide compares the three leading open-source RPKI validators and shows you how to deploy each one in production.

For related reading, see our [BGP routing daemon comparison](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) and our [DNS anycast deployment guide](../2026-04-22-bird-vs-frrouting-vs-keepalived-self-hosted-dns-anycast-guide-2026/) for complementary infrastructure hardening strategies.

## What Is RPKI and Why Self-Host a Validator?

RPKI ties IP address prefixes and AS numbers to cryptographic certificates issued by Regional Internet Registries (RIRs — ARIN, RIPE NCC, APNIC, LACNIC, AFRINIC). Each prefix holder publishes a **Route Origin Authorization (ROA)** that cryptographically states: "AS XXXXX is authorized to originate prefix Y.Y.Y.Y/Z."

An RPKI validator downloads and verifies this global certificate tree, then exposes the validated ROA data to your routers via the **RPKI-to-Router (RTR) protocol** (RFC 6810 / RFC 8210). Your BGP daemon then marks routes as:

- **Valid** — a matching ROA exists and the AS/prefix match
- **Invalid** — a ROA exists but the origin AS or prefix length doesn't match (likely a hijack or misconfiguration)
- **NotFound** — no ROA covers this prefix

### Why Self-Host Instead of Using a Public Validator?

| Factor | Public Validator | Self-Hosted Validator |
|--------|-----------------|----------------------|
| Latency | Depends on geographic distance to validator | Near-zero — runs on your network |
| Availability | Single point of failure if the public validator goes down | You control uptime and redundancy |
| Trust | You trust someone else's validation results | You verify the entire certificate chain yourself |
| Customization | No control over refresh intervals or TALs | Full control over Trust Anchor Locators, refresh rate, and RTR session parameters |
| Privacy | Your router's IP is visible to the validator operator | No external queries leak your infrastructure details |
| Integration | Limited to RTR protocol | Can also export JSON, CSV, or use direct database access |

Self-hosting is especially critical for ISPs, hosting providers, and enterprises where BGP security directly impacts customer traffic. Running your own validator means you're not adding latency to RTR sessions and you maintain full audit visibility into every ROA that affects your routing table.

## The Three Leading Open-Source RPKI Validators

### 1. Routinator (NLnet Labs)

| Attribute | Value |
|-----------|-------|
| GitHub | [NLnetLabs/routinator](https://github.com/NLnetLabs/routinator) |
| Stars | 559 |
| Language | Rust |
| Last Updated | April 2026 |
| License | Apache-2.0 / MIT |
| Docker Image | `nlnetlabs/routinator:latest` |

**Routinator** is the most widely adopted open-source RPKI validator. Written in Rust by NLnet Labs, it provides a complete RPKI validation pipeline with a built-in HTTP server for the RRDP (RPKI Repository Delta Protocol) client, an RTR server for router communication, and a JSON/CSV API for external tooling.

Key features:
- **RRDP-first with rsync fallback**: Downloads TAL data over HTTPS when available, falling back to rsync for repositories that don't support RRDP
- **Built-in HTTP server**: Serves validated ROA data as JSON or CSV for integration with monitoring systems
- **Multi-TAL support**: Configurable Trust Anchor Locators for all five RIRs plus custom TALs
- **Signal handling**: Graceful reload on `SIGUSR1` for zero-downtime TAL updates
- **Secure by default**: Runs as an unprivileged user in Docker, drops privileges on bare metal

### 2. FORT Validator (NICMx / LACNIC)

| Attribute | Value |
|-----------|-------|
| GitHub | [NICMx/FORT-validator](https://github.com/NICMx/FORT-validator) |
| Stars | 61 |
| Language | C |
| Last Updated | March 2026 |
| License | BSD-2-Clause |
| Docker Image | Custom build from `docker/` directory |

**FORT Validator** is a lightweight, high-performance RPKI validator developed by NICMx (LACNIC's innovation center). Written in C, it prioritizes minimal resource consumption and fast validation cycles, making it ideal for resource-constrained environments like edge routers or small PoPs.

Key features:
- **Minimal footprint**: C implementation uses significantly less memory than Rust or Go alternatives
- **JSON and RTR output**: Supports both the RTR protocol for direct router integration and JSON output for external consumers
- **Simple configuration**: Single configuration file with clear, well-documented options
- **Active RIR development**: Backed by LACNIC with strong ties to the Latin American networking community

### 3. cfrpki / OctoRPKI (Cloudflare)

| Attribute | Value |
|-----------|-------|
| GitHub | [cloudflare/cfrpki](https://github.com/cloudflare/cfrpki) |
| Stars | 178 |
| Language | Go |
| Last Updated | February 2024 |
| License | BSD-3-Clause |
| Docker Image | Custom build from source |

**cfrpki** (formerly known as OctoRPKI) is Cloudflare's RPKI toolbox, written in Go. It implements the full RPKI validation pipeline and outputs ROA data in CSV format for consumption by routing daemons. While development has slowed since 2024, the codebase remains production-quality and is used internally at Cloudflare.

Key features:
- **Go implementation**: Easy to build and deploy, single binary with minimal dependencies
- **CSV output format**: Simple tab-separated output that's easy to parse with scripts and monitoring tools
- **Cloudflare battle-tested**: Proven at massive scale in Cloudflare's own network
- **Multiple TAL support**: Configurable Trust Anchor Locators for all RIRs

## Feature Comparison

| Feature | Routinator | FORT Validator | cfrpki |
|---------|-----------|---------------|--------|
| Language | Rust | C | Go |
| RTR Server (RFC 8210) | ✅ Yes | ✅ Yes | ❌ No (CSV only) |
| RRDP Support | ✅ Yes | ✅ Yes | ✅ Yes |
| rsync Fallback | ✅ Yes | ✅ Yes | ✅ Yes |
| JSON Output | ✅ Yes | ✅ Yes | ❌ No |
| CSV Output | ✅ Yes | ❌ No | ✅ Yes |
| HTTP API | ✅ Built-in | ❌ No | ❌ No |
| Docker Image | Official | Community build | Source build |
| Multi-threading | ✅ Yes | ✅ Yes | ✅ Yes |
| TAL Management | CLI + config | Config file | Config file |
| Memory Usage | Moderate (~200-400 MB) | Low (~50-100 MB) | Low (~100-200 MB) |
| GitHub Stars | 559 | 61 | 178 |
| Last Active | April 2026 | March 2026 | February 2024 |

**Key takeaway**: Routinator is the most feature-complete and actively maintained option. FORT Validator wins on resource efficiency. cfrpki is stable but its development has stalled — use it only if you specifically need Cloudflare's CSV output format.

## Deployment Guide

### Option 1: Routinator with Docker (Recommended)

Routinator has an official Docker image and is the easiest to deploy. Here's a complete production setup:

```bash
# Create persistent data directory
mkdir -p /opt/routinator/data

# Initial setup: fetch TALs and do a first validation run
docker run --rm -v /opt/routinator/data:/home/routinator/.routinator \
  nlnetlabs/routinator:latest init

# Run as a daemon with RTR server on port 3323 and HTTP API on port 8323
docker run -d --name routinator \
  --restart unless-stopped \
  -v /opt/routinator/data:/home/routinator/.routinator \
  -p 3323:3323 \
  -p 8323:8323 \
  nlnetlabs/routinator:latest \
  server --http 0.0.0.0:8323 --rtr 0.0.0.0:3323
```

Docker Compose configuration for production:

```yaml
version: "3.8"
services:
  routinator:
    image: nlnetlabs/routinator:latest
    container_name: routinator
    restart: unless-stopped
    volumes:
      - ./data:/home/routinator/.routinator
    ports:
      - "3323:3323"   # RTR server for BGP daemons
      - "8323:8323"   # HTTP API (JSON/CSV)
    command:
      - "server"
      - "--http"
      - "0.0.0.0:8323"
      - "--rtr"
      - "0.0.0.0:3323"
      - "--refresh"
      - "600"         # Refresh ROA data every 10 minutes
    healthcheck:
      test: ["CMD", "routinator", "vrps", "--format", "json", "--output", "/dev/null"]
      interval: 300s
      timeout: 30s
      retries: 3
```

Verify it's working:

```bash
# Check the RTR server is responding
docker exec routinator routinator vrps --refresh --format csv | head -10

# Query the HTTP API
curl -s http://localhost:8323/json | python3 -m json.tool | head -20

# Check validation statistics
curl -s http://localhost:8323/status
```

### Option 2: FORT Validator with Docker

FORT Validator doesn't have an official Docker image, but its repository includes a Dockerfile. Here's how to build and run it:

```bash
# Clone the repository
git clone https://github.com/NICMx/FORT-validator.git
cd FORT-validator

# Build the Docker image
docker build -t fort-validator ./docker/

# Create config directory
mkdir -p /etc/fort /opt/fort/cache

# Run with RTR server
docker run -d --name fort-validator \
  --restart unless-stopped \
  -v /etc/fort:/etc/fort \
  -v /opt/fort/cache:/var/cache/fort \
  -p 3323:3323 \
  fort-validator \
  --server \
  --tal=/etc/fort/tals \
  --cache-dir=/var/cache/fort
```

Generate TAL files:

```bash
# Download TAL files from each RIR
mkdir -p /etc/fort/tals
curl -sL https://www.arin.net/resources/manage/rpki/arin-rpki-tal.cer -o /etc/fort/tals/arin.cer
curl -sL https://rpki.apnic.net/repository/apnic-rpki-root.cer -o /etc/fort/tals/apnic.cer
curl -sL https://www.lacnic.net/rpki/lacnic.rpki.trustanchor.cer -o /etc/fort/tals/lacnic.cer
curl -sL https://www.afrinic.net/afrinic-members/rpki/afrinic-rpki-root.cer -o /etc/fort/tals/afrinic.cer
curl -sL https://www.ripe.net/manage-ips-and-asns/resource-management/rpki/ripe-ncc-rpki-tal.cer -o /etc/fort/tals/ripe.cer
```

### Option 3: cfrpki (Build from Source)

cfrpki requires building from source. Here's a Docker-based build:

```bash
# Clone the repository
git clone https://github.com/cloudflare/cfrpki.git
cd cfrpki

# Build Docker image
docker build -t cfrpki .

# Create cache directory
mkdir -p /opt/cfrpki/cache

# Run (outputs CSV to stdout — redirect to a file)
docker run -d --name cfrpki \
  --restart unless-stopped \
  -v /opt/cfrpki/cache:/cache \
  cfrpki \
  -output /cache/roas.csv \
  -cache /cache \
  -refresh 600
```

Docker Compose for cfrpki:

```yaml
version: "3.8"
services:
  cfrpki:
    build: .
    container_name: cfrpki
    restart: unless-stopped
    volumes:
      - ./cache:/cache
    command:
      - "-output"
      - "/cache/roas.csv"
      - "-cache"
      - "/cache"
      - "-refresh"
      - "600"
    healthcheck:
      test: ["CMD", "test", "-s", "/cache/roas.csv"]
      interval: 300s
      timeout: 10s
      retries: 3
```

## Integrating Your Validator with BGP Daemons

Once your RPKI validator is running, connect your BGP daemon to it via the RTR protocol. Here are the configurations for the three major open-source BGP daemons.

### BIRD 2.x Configuration

```
# Add to your bird.conf
rpki server rpki-validator {
    address "127.0.0.1" port 3323;  # Your validator's RTR port
    refresh 600;      # Refresh interval in seconds
    retry 60;         # Retry interval on failure
    expire 7200;      # Cache expiry time
    max prefix length 24;
}

# Then in your BGP protocol, add roa check:
protocol bgp my_peer {
    ...
    roa check;
}
```

### FRRouting Configuration

```
! In vtysh or frr.conf
router bgp 65001
  bgp rpki server
    rpki rpki-validator
      connection 127.0.0.1 3323
      refresh-interval 600
      expire-interval 7200
      retry-interval 60
    exit
  exit
!
```

### OpenBGPD Configuration

```
# In bgpd.conf
rpki server 127.0.0.1 port 3323
```

## Monitoring and Alerting

Set up monitoring to detect when your RPKI validator falls behind or loses connectivity to the repositories:

```bash
# Check Routinator validation status
curl -s http://localhost:8323/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Last update: {data.get(\"last_update\", \"unknown\")}')
print(f'VRPs: {data.get(\"vrps\", {}).get(\"total\", 0)}')
print(f'Repositories: {data.get(\"repositories\", {}).get(\"total\", 0)}')
"

# Alert if no VRPs were loaded in the last 15 minutes
python3 -c "
import requests, time
r = requests.get('http://localhost:8323/status')
data = r.json()
last = data.get('last_update', '')
if last:
    from datetime import datetime
    last_time = datetime.fromisoformat(last.replace('Z', '+00:00'))
    if (datetime.now(last_time.tzinfo) - last_time).total_seconds() > 900:
        print('ALERT: RPKI validator has not refreshed in >15 minutes')
"
```

## Which Validator Should You Choose?

| Use Case | Recommended Validator |
|----------|----------------------|
| Production ISP / hosting provider | **Routinator** — most feature-complete, actively maintained, official Docker image |
| Edge routers / low-resource environments | **FORT Validator** — smallest memory footprint, C implementation |
| Cloudflare-style CSV pipeline | **cfrpki** — if your tooling specifically needs CSV output |
| Quick evaluation / testing | **Routinator** — one `docker run` command and you're validating |
| Multi-validator redundancy | Run **Routinator** as primary, **FORT** as secondary on different hardware |

For most organizations, **Routinator** is the right choice. Its active development cycle (multiple releases per year), comprehensive feature set, and official Docker image make it the most production-ready option. Running a secondary FORT Validator as a fallback provides redundancy with minimal additional resource cost.

## FAQ

### What is RPKI and how does it prevent BGP hijacking?

RPKI (Resource Public Key Infrastructure) is a cryptographic framework that validates the relationship between IP prefixes and their authorized origin AS numbers. Each prefix holder publishes a Route Origin Authorization (ROA) signed by their RIR. When your BGP daemon receives a route announcement, it checks the ROA database: if the origin AS matches the ROA, the route is "Valid"; if it doesn't match, it's "Invalid" (potential hijack); if no ROA exists, it's "NotFound." By rejecting "Invalid" routes, you protect your network from accepting hijacked prefixes.

### Can I run multiple RPKI validators for redundancy?

Yes. You can run multiple validators (e.g., Routinator as primary, FORT as secondary) and configure your BGP daemon to connect to both via separate RTR sessions. BIRD, FRRouting, and OpenBGPD all support multiple RPKI server connections. The daemon will merge validation results from all connected validators and use the most restrictive validation state (Invalid takes precedence over Valid).

### How often should the RPKI validator refresh its data?

The recommended refresh interval is 600 seconds (10 minutes). This matches the default TTL on most RPKI repository data. Shorter intervals increase load on the RIR repositories; longer intervals mean your validation data is stale. Routinator defaults to 10 minutes, which is the sweet spot for most deployments.

### Do I need to register for an RPKI account with my RIR?

No. RPKI validators download publicly available certificate data from the five RIR repositories (ARIN, RIPE NCC, APNIC, LACNIC, AFRINIC). You don't need credentials — the validators use Trust Anchor Locator (TAL) files that point to publicly accessible certificate roots. However, if you want to *publish* ROAs for your own prefixes, you'll need to set up RPKI with your RIR, which is a separate process.

### What happens if my RPKI validator goes offline?

If your RPKI validator becomes unreachable, your BGP daemon will eventually mark all ROA data as "expired" (based on the expire interval, typically 7200 seconds / 2 hours). Depending on your configuration, it may then treat all routes as "NotFound" (no validation) or drop all routes. For production deployments, run a secondary validator on different hardware to avoid this scenario.

### How much disk space and memory does an RPKI validator need?

Routinator typically uses 200-400 MB of RAM and stores about 500 MB of repository data on disk. FORT Validator uses 50-100 MB of RAM with a similar disk footprint. cfrpki uses 100-200 MB of RAM. All three validators are lightweight enough to run on the same machine as your BGP daemon or on a dedicated small VM (1 vCPU, 512 MB RAM is sufficient for any of them).

### What is the difference between RRDP and rsync for RPKI data retrieval?

RRDP (RPKI Repository Delta Protocol, RFC 8182) is an HTTPS-based protocol that transfers only the *changes* (deltas) to the RPKI repository since the last sync, making it faster and more bandwidth-efficient. rsync transfers the entire repository data each time. All three validators try RRDP first and fall back to rsync for repositories that don't support RRDP. The RIRs are gradually migrating to RRDP, so the rsync fallback is becoming less important over time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Routinator vs FORT vs cfrpki: Best Self-Hosted RPKI Validator 2026",
  "description": "Complete comparison of Routinator, FORT Validator, and Cloudflare cfrpki for self-hosted RPKI route origin validation. Docker deployment guides, configuration examples, and performance benchmarks for BGP security.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
  "author": {
    "@type": "Organization",
    "name": "Pi Stack Team"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Pi Stack",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
