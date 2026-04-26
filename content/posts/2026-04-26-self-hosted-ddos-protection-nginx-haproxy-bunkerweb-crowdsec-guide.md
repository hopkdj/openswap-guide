---
title: "Self-Hosted DDoS Protection: Nginx vs HAProxy vs BunkerWeb vs CrowdSec 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "security", "ddos", "nginx", "haproxy"]
draft: false
description: "Comprehensive guide to self-hosted DDoS protection tools. Compare Nginx, HAProxy, BunkerWeb, and CrowdSec for application-layer attack mitigation with Docker configs and deployment strategies."
---

Distributed Denial of Service (DDoS) attacks continue to escalate in both frequency and sophistication. The average attack size grew 28% year-over-year, with application-layer (Layer 7) attacks becoming the most common threat vector for self-hosted services. While cloud providers offer managed DDoS mitigation at a premium, a growing number of open-source tools let you build robust DDoS protection on your own infrastructure.

This guide compares four proven approaches to self-hosted DDoS protection: **Nginx** with rate-limiting modules, **HAProxy** with stick-table filtering, **BunkerWeb** as an integrated security reverse proxy, and **CrowdSec** for collaborative threat intelligence. Each solution is evaluated on detection capability, configuration complexity, resource overhead, and real-world effectiveness.

For related reading, see our [BunkerWeb vs ModSecurity vs CrowdSec WAF comparison](../bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) and the [Fail2ban vs SSHGuard vs CrowdSec intrusion prevention guide](../fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). We also cover [rate limiting and API throttling](../self-hosted-rate-limiting-api-throttling-nginx-traefik-envoy-kong-2026/) in a separate guide.

## Why Self-Hosted DDoS Protection Matters

Relying solely on cloud-based DDoS protection introduces several risks: vendor lock-in, per-GB mitigation costs that scale unpredictably during attacks, and potential single points of failure when the protection provider itself is targeted. Self-hosted DDoS mitigation gives you:

- **Full control** over filtering rules, whitelisting, and response behavior
- **Zero per-attack costs** — open-source tools have no usage-based billing
- **Privacy preservation** — all traffic analysis stays on your infrastructure
- **Immediate response** — no waiting for provider ticket queues during an active attack
- **Defense in depth** — combine multiple layers (connection limiting, behavioral analysis, IP reputation) for comprehensive protection

The key insight is that most self-hosted services don't need carrier-grade volumetric mitigation (which requires upstream ISP cooperation). What you *do* need is effective Layer 7 protection against HTTP floods, slowloris attacks, and application-specific abuse — and that's exactly where these tools excel.

## Understanding DDoS Attack Vectors

Before deploying any protection tool, it helps to understand what you're defending against. DDoS attacks fall into three broad categories:

### Volumetric Attacks (Layer 3/4)

These attacks saturate your network bandwidth with massive traffic volumes:

- **UDP floods** — random UDP packets to open or closed ports
- **ICMP floods** — ping-based bandwidth exhaustion
- **DNS amplification** — spoofed requests to open DNS resolvers generating responses 28-54x larger than the original query
- **NTP amplification** — similar to DNS but using NTP servers with monlist commands

Self-hosted tools alone cannot fully mitigate volumetric attacks that exceed your upstream bandwidth. You need upstream filtering from your ISP or a transit provider. However, you *can* reduce the impact through proper firewall rules and connection limiting.

### Protocol Attacks (Layer 4)

These exploit weaknesses in network protocols to exhaust server resources:

- **SYN floods** — incomplete TCP handshakes consuming connection table entries
- **Ping of Death** — oversized ICMP packets causing buffer overflows
- **Smurf attacks** — ICMP echo requests to broadcast addresses

Tools like HAProxy and Nginx can mitigate these through connection rate limiting and SYN cookie support.

### Application-Layer Attacks (Layer 7)

The most dangerous category for self-hosted services because they mimic legitimate traffic:

- **HTTP floods** — high-rate GET/POST requests to expensive endpoints (search, login, API)
- **Slowloris** — keeping connections open with partial HTTP requests
- **Low-and-slow** — distributed requests at rates just below detection thresholds
- **WordPress XML-RPC abuse** — using `xmlrpc.php` for amplification
- **API endpoint abuse** — hitting unauthenticated or expensive API routes

This is where self-hosted tools provide the most value. All four tools in this comparison excel at Layer 7 mitigation, each with different approaches.

## Comparison at a Glance

| Feature | Nginx Rate Limiting | HAProxy Stick Tables | BunkerWeb | CrowdSec |
|---|---|---|---|---|
| **Primary role** | Reverse proxy + rate limiter | Load balancer + traffic filter | Security-first reverse proxy | Collaborative IPS |
| **GitHub stars** | N/A (core project) | 6,495 | 10,358 | 13,180 |
| **Last updated** | Continuously | 2026-04-25 | 2026-04-24 | 2026-04-24 |
| **Language** | C | C | Python | Go |
| **Layer 7 protection** | Yes (req/conn limiting) | Yes (stick-table ACLs) | Yes (built-in rules) | Yes (scenarios) |
| **Layer 4 protection** | Partial (conn limiting) | Yes (TCP rate limiting) | Yes (anti-DDoS module) | Partial (IP ban) |
| **IP reputation** | Manual (geoip/blocklist) | Manual (ACL lists) | Built-in bad bot DB | Crowdsourced (global) |
| **Geo-blocking** | Yes (geoip module) | Yes (ACL rules) | Yes (built-in) | Yes (scenarios) |
| **Bot detection** | Manual (user-agent ACLs) | Manual | Yes (built-in) | Yes (scenarios) |
| **Docker support** | Yes | Yes | Yes (native) | Yes (Docker parser) |
| **Resource usage** | Low (~50MB) | Low (~30MB) | Medium (~200MB) | Medium (~150MB) |
| **Learning curve** | Low | Medium | Low | Medium |
| **Collaborative intel** | No | No | No | Yes (global network) |

## Nginx: Connection and Rate Limiting

Nginx provides two powerful built-in modules for DDoS mitigation without any third-party dependencies: `ngx_http_limit_req_module` for request rate limiting and `ngx_http_limit_conn_module` for connection limiting.

### Basic Rate Limiting Configuration

```nginx
http {
    # Define rate limiting zones
    # 10m shared memory zone, 10 requests/second per IP
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=3r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

    # Connection limiting: max 10 concurrent connections per IP
    limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;

    server {
        listen 80;
        server_name example.com;

        # Apply general rate limit with burst allowance
        limit_req zone=general burst=20 nodelay;
        limit_conn conn_per_ip 10;

        location / {
            proxy_pass http://backend;
        }

        # Stricter limits for login endpoints
        location /login {
            limit_req zone=login burst=3 nodelay;
            proxy_pass http://backend;
        }

        # Moderate limits for API endpoints
        location /api/ {
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

### Advanced: Custom Error Responses and Logging

```nginx
http {
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

    # Custom error page for rate-limited requests
    limit_req_status 429;

    # Log when rate limiting is applied
    map $limit_req_status $rate_limited {
        default "no";
        "503" "yes";
        "429" "yes";
    }

    log_format ddos '$remote_addr - [$time_local] "$request" '
                    '$status $body_bytes_sent rate_limited=$rate_limited';

    server {
        listen 80;

        location / {
            limit_req zone=general burst=20 nodelay;
            error_page 429 /429.json;

            location = /429.json {
                default_type application/json;
                return 429 '{"error":"rate_limit_exceeded","retry_after":1}';
            }
        }
    }
}
```

### Docker Compose for Nginx DDoS Protection

```yaml
version: "3.8"

services:
  nginx-ddos:
    image: nginx:1.27-alpine
    container_name: nginx-ddos
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
      - ./logs:/var/log/nginx
    restart: unless-stopped
    networks:
      - frontend

  backend:
    image: your-app:latest
    networks:
      - frontend

networks:
  frontend:
    driver: bridge
```

## HAProxy: Stick-Table Traffic Filtering

HAProxy's stick-table feature provides granular traffic tracking and filtering based on request rates, connection counts, and HTTP error rates. Unlike Nginx's static rate limits, HAProxy can dynamically track and respond to suspicious behavior patterns.

### Stick-Table Configuration

```haproxy
frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/haproxy/certs/example.com.pem

    # Stick table: track per-source-IP metrics
    stick-table type ip size 200k expire 30s store http_req_rate(10s),conn_cur,conn_rate(10s),http_err_rate(10s)

    # Track the source IP
    http-request track-sc0 src

    # Block IPs exceeding 50 requests/10s
    acl is_abuse sc_http_req_rate(0) gt 50
    http-request deny deny_status 429 if is_abuse

    # Block IPs with too many concurrent connections
    acl too_many_conn sc_conn_cur(0) gt 20
    http-request deny if too_many_conn

    # Block IPs with high error rates (scanners/exploit attempts)
    acl scanner sc_http_err_rate(0) gt 10
    http-request deny if scanner

    # Rate limit with tarpit (slow down instead of block)
    acl tarpit_req sc_http_req_rate(0) gt 30
    http-request tarpit if tarpit_req

    default_backend http_back

backend http_back
    balance roundrobin
    server web1 127.0.0.1:8080 check
    server web2 127.0.0.1:8081 check
```

### Geo-Blocking with HAProxy

```haproxy
frontend http_front
    bind *:80

    # Load GeoIP database
    stick-table type ip size 200k expire 30s store src_conn_rate(10s)

    # Block specific countries (ISO codes)
    acl blocked_country src_country CN,RU,KP
    http-request deny if blocked_country

    # Rate limit all other traffic
    http-request track-sc0 src
    acl abuse sc_http_req_rate(0) gt 100
    http-request deny if abuse

    default_backend http_back
```

### HAProxy Docker Compose

```yaml
version: "3.8"

services:
  haproxy:
    image: haproxy:2.9-alpine
    container_name: haproxy-ddos
    ports:
      - "80:80"
      - "443:443"
      - "8404:8404"  # Stats page
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/usr/local/etc/haproxy/certs:ro
    restart: unless-stopped
    networks:
      - frontend

networks:
  frontend:
    driver: bridge
```

## BunkerWeb: Integrated Security Reverse Proxy

BunkerWeb (10,358 stars, last updated 2026-04-24) is a purpose-built security reverse proxy based on Nginx. It comes with DDoS protection features pre-configured, making it the most turnkey solution in this comparison.

### Key Anti-DDoS Features

- **Anti-bot detection** — JavaScript challenge, CAPTCHA, and behavioral analysis
- **Request rate limiting** — configurable per-IP and per-URL limits
- **Connection limiting** — max concurrent connections per IP
- **Bad user-agent blocking** — blocks known scanner and bot user-agents
- **Geo-blocking** — country-level IP filtering with built-in GeoIP
- **DNSBL integration** — checks IPs against DNS-based blackhole lists
- **Auto-ban** — automatically bans IPs that trigger security rules

### BunkerWeb Docker Compose

```yaml
version: "3.8"

services:
  bunkerweb:
    image: bunkerity/bunkerweb:1.7.0
    container_name: bunkerweb
    ports:
      - "80:8080"
      - "443:8443"
    environment:
      - SERVER_NAME=example.com
      - USE_BUNKERUI=yes
      - USE_MODSECURITY=no
      - USE_REVERSE_PROXY=yes
      - REVERSE_PROXY_URL=/
      - REVERSE_PROXY_HOST=http://app:8000
      # Anti-DDoS settings
      - LIMIT_REQ_RATE=10r/s
      - LIMIT_REQ_BURST=20
      - LIMIT_CONN=10
      - BLOCK_ABUSE_IP=yes
      - USE_BAD_BEHAVIOR=yes
      - USE_DNSBL=yes
      - BLOCK_COUNTRY=CN RU KP
    volumes:
      - bunkerweb-data:/data
      - bunkerweb-logs:/var/log/bunkerweb
    restart: unless-stopped
    networks:
      - frontend

  app:
    image: your-app:latest
    networks:
      - frontend

networks:
  frontend:
    driver: bridge

volumes:
  bunkerweb-data:
  bunkerweb-logs:
```

### BunkerWeb Environment Variables for DDoS

| Variable | Default | Description |
|---|---|---|
| `LIMIT_REQ_RATE` | `10r/s` | Max requests per second per IP |
| `LIMIT_REQ_BURST` | `20` | Burst allowance before blocking |
| `LIMIT_CONN` | `10` | Max concurrent connections per IP |
| `BLOCK_ABUSE_IP` | `yes` | Auto-ban IPs triggering rules |
| `USE_BAD_BEHAVIOR` | `yes` | Enable behavioral bot detection |
| `USE_DNSBL` | `no` | Check IPs against DNS blocklists |
| `BLOCK_COUNTRY` | Empty | Comma-separated country codes to block |
| `USE_ANTISCAN` | `yes` | Block known vulnerability scanners |

## CrowdSec: Collaborative Threat Intelligence

CrowdSec (13,180 stars, last updated 2026-04-24) takes a fundamentally different approach: instead of relying solely on local rules, it shares threat intelligence across a global network of 90,000+ nodes. When one node detects and bans an attacking IP, all other nodes can benefit from that intelligence.

### How CrowdSec Works

1. **Bouncer agents** — installed alongside your services (Nginx bouncer, HAProxy bouncer, Traefik bouncer, firewall bouncer)
2. **Local agent** — analyzes logs in real-time using YAML-based "scenarios"
3. **CTI (CrowdSec Threat Intelligence)** — queries the central API for IP reputation data
4. **Community blocklist** — contributes detected bad IPs and receives bans from the global network

### Installing CrowdSec with Docker

```yaml
version: "3.8"

services:
  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec
    environment:
      - GID=1000
      - COLLECTIONS=crowdsecurity/nginx crowdsecurity/http-cve crowdsecurity/base-http-scenarios
      - ENROLL_KEY=your-enrollment-key  # From CrowdSec Hub
    volumes:
      - ./crowdsec/config:/etc/crowdsec
      - ./crowdsec/data:/var/lib/crowdsec/data
      - /var/log/nginx:/var/log/nginx:ro  # Feed Nginx logs
    restart: unless-stopped
    networks:
      - frontend

  # Nginx bouncer that blocks IPs flagged by CrowdSec
  crowdsec-bouncer-nginx:
    image: docker.io/fbonalair/traefik-crowdsec-bouncer:latest
    container_name: crowdsec-bouncer-nginx
    environment:
      - CROWDSEC_BOUNCER_API_KEY=your-bouncer-api-key
      - CROWDSEC_AGENT_HOST=crowdsec:8080
      - CROWDSEC_BOUNCER_LOG_LEVEL=info
      - REMEDIATION_REMEDIATION_CAPTCHA=true
      - REMEDIATION_REMEDIATION_CAPTCHA_PROVIDER=cloudflare
    depends_on:
      - crowdsec
    restart: unless-stopped
    networks:
      - frontend

networks:
  frontend:
    driver: bridge
```

### DDoS-Specific Scenarios

CrowdSec includes pre-built scenarios that detect DDoS patterns:

```yaml
# /etc/crowdsec/scenarios/http-ddos.yaml
type: trigger
name: crowdsecurity/http-ddos
description: "Detect HTTP request floods"
filter: "evt.Meta.log_type in ['http_access-log']"
groupby: "evt.Meta.source_ip"
distinct: true
capacity: 100
leak_speed: 10s
lifetime: 5m
blackhole: 5m
labels:
  type: ddos
  service: http
```

The `http-ddos` scenario triggers when an IP sends more than 100 requests within 10 seconds, resulting in a temporary ban. Combined with CrowdSec's community blocklist, you automatically benefit from bans enacted by other nodes worldwide.

### Firewall Bouncer for Network-Level Blocking

For maximum DDoS protection, use the firewall bouncer to block at the OS level before traffic reaches your application:

```bash
# Install the firewall bouncer
sudo apt install crowdsec-firewall-bouncer-iptables

# Configure to use nftables (more efficient than iptables for large blocklists)
sudo nano /etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
# Set: mode: nftables
# Set: decision_type: ban

# Restart the bouncer
sudo systemctl restart crowdsec-firewall-bouncer
```

## Layered DDoS Defense Strategy

The most effective self-hosted DDoS protection combines multiple tools in a defense-in-depth architecture:

```
Internet → [HAProxy: rate limiting + geo-blocking]
              ↓
         [BunkerWeb: anti-bot + bad behavior]
              ↓
         [Nginx: connection limiting + request filtering]
              ↓
         [CrowdSec: log analysis + collaborative bans]
              ↓
         [Your Application]
```

### Recommended Deployment for Most Users

For a typical self-hosted setup, this combination provides comprehensive protection with manageable complexity:

1. **Front layer**: HAProxy for connection routing and basic rate limiting
2. **Security layer**: BunkerWeb for anti-bot detection and behavioral analysis
3. **Intelligence layer**: CrowdSec for collaborative IP reputation and automated banning
4. **Application layer**: Nginx as the final request filter before your app

### Minimal Setup (Low Resource)

If resources are limited, a single CrowdSec instance with the Nginx bouncer provides 80% of the protection of a full stack:

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:1.27-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./logs:/var/log/nginx
    restart: unless-stopped

  crowdsec:
    image: crowdsecurity/crowdsec:latest
    environment:
      - GID=1000
      - COLLECTIONS=crowdsecurity/nginx crowdsecurity/base-http-scenarios
    volumes:
      - ./crowdsec/config:/etc/crowdsec
      - ./crowdsec/data:/var/lib/crowdsec/data
      - ./logs:/var/log/nginx:ro
    restart: unless-stopped
```

## Choosing the Right Tool

| Scenario | Recommended Tool | Why |
|---|---|---|
| Simple rate limiting | Nginx | Built-in, zero dependencies, battle-tested |
| Complex traffic filtering | HAProxy | Stick-tables provide unmatched flexibility |
| Turnkey security proxy | BunkerWeb | Pre-configured rules, web UI for management |
| Collaborative protection | CrowdSec | Global threat intelligence network |
| WordPress site | BunkerWeb + CrowdSec | Anti-bot + CVE detection scenarios |
| API service | Nginx + HAProxy | Fine-grained per-endpoint rate limits |
| Multi-server setup | CrowdSec | Shared blocklist across all nodes |
| Minimal resources | Nginx rate limiting | ~50MB memory, handles thousands of req/s |

## Troubleshooting Common Issues

### Legitimate Users Getting Blocked

If legitimate users are hitting rate limits, adjust the burst parameters and consider whitelisting known IP ranges:

```nginx
# Whitelist internal networks
geo $whitelist {
    default 0;
    10.0.0.0/8 1;
    172.16.0.0/12 1;
    192.168.0.0/16 1;
}

map $whitelist $limit_key {
    0 $binary_remote_addr;
    1 "";
}

limit_req_zone $limit_key zone=general:10m rate=10r/s;
```

### False Positives from Search Engine Crawlers

Search engine bots can trigger rate limits. Exclude them by user-agent:

```haproxy
frontend http_front
    # Don't rate-limit known bots
    acl is_bot hdr_sub(User-Agent) -i googlebot bingbot
    http-request track-sc0 src unless is_bot
    acl abuse sc_http_req_rate(0) gt 50
    http-request deny unless is_bot if abuse
```

### High Memory Usage with Large Stick Tables

If HAProxy's stick table consumes too much memory, reduce the table size or expire entries faster:

```haproxy
# Smaller table with faster expiration
stick-table type ip size 50k expire 10s store http_req_rate(10s)
```

## FAQ

### What is the difference between DDoS and DoS attacks?

A DoS (Denial of Service) attack comes from a single source, while a DDoS (Distributed Denial of Service) attack originates from multiple sources simultaneously, often a botnet of compromised devices. DDoS attacks are harder to block because the traffic comes from many different IPs, making simple IP banning less effective.

### Can self-hosted tools stop volumetric DDoS attacks?

No. Volumetric attacks that exceed your upstream bandwidth (e.g., 100 Gbps) cannot be stopped by any self-hosted tool because the traffic saturates your network link before reaching your server. For volumetric mitigation, you need upstream filtering from your ISP or a DDoS protection service like Cloudflare or Akamai. Self-hosted tools excel at Layer 7 (application-layer) attacks, which is the most common threat for self-hosted services.

### How does CrowdSec's community blocklist work?

When any CrowdSec node detects and bans a malicious IP, that ban decision is shared to the central CrowdSec API. Other nodes can query this API to check if an IP has been flagged by the community. CrowdSec's threat intelligence score combines frequency, recency, and severity of reports across the network. In practice, this means you benefit from bans enacted by 90,000+ other nodes worldwide.

### Should I use Nginx or HAProxy for DDoS protection?

Use **Nginx** if you need simple, effective rate limiting with minimal configuration. Use **HAProxy** if you need more sophisticated traffic analysis (per-endpoint rate limits, error-rate tracking, tarpitting) or if HAProxy is already your load balancer. Both are excellent choices — many production setups use both, with HAProxy at the front and Nginx behind it.

### Is BunkerWeb production-ready for high-traffic sites?

Yes. BunkerWeb is built on Nginx and has been tested with thousands of requests per second. The security features add approximately 10-15% CPU overhead compared to vanilla Nginx. For sites receiving more than 10,000 requests/second, consider using HAProxy or Nginx with custom rate limiting instead, as BunkerWeb's feature set may introduce latency at extreme scale.

### How do I test if my DDoS protection is working?

Use tools like `slowloris` (for slowloris testing) and `hping3` (for SYN flood testing) from a separate machine to simulate attacks:

```bash
# Install testing tools
sudo apt install hping3 slowloris

# Test SYN flood (run from test machine, NOT production)
sudo hping3 -S --flood -p 80 <your-server-ip>

# Test slowloris
slowloris -s 1000 http://<your-server-ip>
```

Monitor your logs during testing to verify that rate limiting and IP banning are triggered correctly. Always test from a non-production environment to avoid accidentally getting yourself banned.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DDoS Protection: Nginx vs HAProxy vs BunkerWeb vs CrowdSec 2026",
  "description": "Comprehensive guide to self-hosted DDoS protection tools. Compare Nginx, HAProxy, BunkerWeb, and CrowdSec for application-layer attack mitigation with Docker configs and deployment strategies.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
