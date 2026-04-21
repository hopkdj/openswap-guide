---
title: "BunkerWeb vs ModSecurity vs CrowdSec: Best Self-Hosted WAF Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "security", "waf", "reverse-proxy"]
draft: false
description: "Compare BunkerWeb, ModSecurity, and CrowdSec — three open-source web application firewalls. Learn which self-hosted WAF fits your infrastructure with Docker configs, deployment guides, and feature comparisons."
---

Protecting web applications from attacks like SQL injection, cross-site scripting (XSS), and bot abuse is essential — whether you run a single blog or a multi-tenant platform. Commercial WAFs (Cloudflare, AWS WAF) cost money and route your traffic through third-party infrastructure. Self-hosted open-source alternatives give you full control over your security posture without the per-request pricing.

In this guide, we compare three mature open-source WAF solutions: **BunkerWeb**, **ModSecurity**, and **CrowdSec**. Each takes a different approach to web application protection, and understanding their trade-offs will help you pick the right tool for your stack.

## Why Self-Host Your WAF?

Running your own WAF eliminates several downsides of managed services:

- **No traffic routing through third parties** — your requests never leave your infrastructure
- **Custom rule tuning** — adjust blocking thresholds without vendor support tickets
- **Cost predictability** — no surprise bills from traffic spikes
- **Compliance** — keep sensitive request data in-house for GDPR, HIPAA, or PCI-DSS environments
- **Full visibility** — inspect every blocked request, not just a dashboard summary

For teams that already run self-hosted reverse proxies and load balancers (see our [load balancer guide](../self-hosted-load-balancers-traefik-haproxy-[nginx](https://nginx.org/)-high-availability-guide-2026/) and [reverse proxy comparison](../reverse-proxy-comparison/)), adding a WAF layer is a natural next step.

## BunkerWeb: The All-in-One WAF

BunkerWeb (10,300+ stars on GitHub, actively maintained by Bunkerity) is a next-generation WAF built on top of NGINX. It ships with sensible defaults, a web-based management UI, and a plugin system. Unlike traditional WAFs that require extensive manual rule configuration, BunkerWeb aims for "secure out of the box."

### Key Features

- **NGINX-based core** with automatic OWASP Core Rule Set integration
- **Built-in UI dashboard** for real-time monitoring and configuration
- **Auto-ban mechanism** that blocks IPs generating too many errors
- **Bot detection** with configurable allowlists for search engine crawlers
- **TLS/SSL automation** — generates and renews certificates automatically
- **Multi-site support** with per-site security profiles
- **Scheduler service** for background tasks like certificate renewal and log rotation

### [docker](https://www.docker.com/) Compose Configuration

BunkerWeb's official Docker Compose setup deploys two containers — the WAF proxy and a scheduler:

```yaml
x-env: &env
  API_WHITELIST_IP: "127.0.0.0/8 10.20.30.0/24"

services:
  bunkerweb:
    image: bunkerity/bunkerweb:1.6.9
    ports:
      - 80:8080
      - 443:8443
    labels:
      - "bunkerweb.INSTANCE=yes"
    environment:
      <<: *env
    networks:
      - bw-universe
      - bw-services

  bw-scheduler:
    image: bunkerity/bunkerweb-scheduler:1.6.9
    depends_on:
      - bunkerweb
    volumes:
      - bw-storage:/data
    environment:
      <<: *env
      BUNKERWEB_INSTANCES: "bunkerweb"
      SERVER_NAME: "www.example.com"
    networks:
      - bw-universe

volumes:
  bw-storage:

networks:
  bw-universe:
    name: bw-universe
    ipam:
      driver: default
      config:
        - subnet: 10.20.30.0/24
  bw-services:
    name: bw-services
```

Deploy with:

```bash
docker compose -f docker-compose.yml up -d
```

For database-backed configurations (recommended for production), BunkerWeb supports PostgreSQL, MariaDB, and MySQL. Simply use the `docker.postgres.yml` integration file from the repository:

```bash
curl -LO https://raw.githubusercontent.com/bunkerity/bunkerweb/master/misc/integrations/docker.postgres.yml
docker compose -f docker.postgres.yml up -d
```

### Installing BunkerWeb on Linux

For bare-metal or VM deployments:

```bash
# Ubuntu/Debian
curl -s https://repository.bunkerweb.io/install.sh | sudo bash
sudo apt install bunkerweb

# Start and enable
sudo systemctl enable --now bunkerweb
sudo systemctl status bunkerweb
```

Access the management UI at `https://your-server:9999` (default credentials are set during installation).

### Custom Security Rules

BunkerWeb lets you override default behavior per server:

```bash
# Block a specific User-Agent
bunkercli setconf mysite.com USE_BAD_BEHAVIOR yes
bunkercli setconf mysite.com BLOCKED_USER_AGENTS "badbot evil-crawler"

# Whitelist an IP range
bunkercli setconf mysite.com WHITELIST_IP "192.168.1.0/24 10.0.0.5"

# Enable specific OWASP rules
bunkercli setconf mysite.com USE_MODSECURITY yes
bunkercli setconf mysite.com MODSECURITY_CRS_VERSION 4
```

Apply changes without downtime:

```bash
bunkercli reload-conf
```

## ModSecurity: The Battle-Tested WAF Engine

ModSecurity (9,600+ stars, maintained by OWASP) is the most widely deployed open-source WAF engine. It powers countless commercial security products and provides a rule-based filtering engine that works with Apache, NGINX, and IIS.

### Key Features

- **Rule-based inspection** using SecRules language (highly expressive)
- **OWASP Core Rule Set (CRS)** — 200+ rules covering SQLi, XSS, RFI, LFI, and more
- **Multi-phase processing** — inspects requests at multiple stages of the HTTP lifecycle
- **Mature ecosystem** — 20+ years of development, extensive documentation
- **ModSecurity v3 (libmodsecurity)** — decoupled from Apache, works with NGINX connector

### NGINX + ModSecurity Deployment

```bash
# Ubuntu/Debian — install NGINX with ModSecurity module
sudo apt install nginx libnginx-mod-modsecurity

# Download OWASP CRS
cd /etc/nginx/modsec
sudo git clone --depth 1 https://github.com/coreruleset/coreruleset.git
sudo cp coreruleset/crs-setup.conf.example coreruleset/crs-setup.conf

# Enable ModSecurity
sudo cp /etc/modsecurity/modsecurity.conf-recommended /etc/modsecurity/modsecurity.conf
sudo sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/modsecurity.conf
```

NGINX configuration with ModSecurity:

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Enable ModSecurity
    modsecurity on;
    modsecurity_rules_file /etc/nginx/modsec/main.conf;

    location / {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Main ModSecurity configuration (`/etc/nginx/modsec/main.conf`):

```apache
Include /etc/modsecurity/modsecurity.conf
Include /etc/nginx/modsec/coreruleset/crs-setup.conf
Include /etc/nginx/modsec/coreruleset/rules/*.conf

# Custom rule: block specific paths
SecRule REQUEST_URI "@beginsWith /admin" \
    "id:10001,\
    phase:1,\
    deny,\
    status:403,\
    msg:'Admin area blocked'"
```

### ModSecurity with Docker

```yaml
services:
  nginx-modsec:
    image: owasp/modsecurity-crs:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./modsec-config:/etc/modsecurity.d/:ro
    environment:
      - BACKEND=http://backend-app:8080
      - PARANOIA=1
    networks:
      - web
```

The `PARANOIA` level (1–4) controls CRS strictness. Level 1 blocks obvious attacks; level 4 catches subtle anomalies but may generate false positives.

## CrowdSec: The Collaborative Threat Intelligence WAF

CrowdSec (13,000+ stars) takes a fundamentally different approach. Instead of relying solely on local rules, it aggregates attack data from a global community of over 80,000 nodes. When one server detects an attacker, all CrowdSec users benefit from that intelligence.

### Key Features

- **Crowdsourced IP reputation database** — blocks IPs flagged by the global community
- **Scenario-based detection** — defines patterns (brute force, port scans, crawls) and triggers bans
- **Bouncer architecture** —[caddy](https://caddyserver.com/)tweight plugins for NGINX, Apache, Traefik, Caddy, Cloudflare, and more
- **Local API + Central API** — self-hosted decision server with optional community IP sharing
- **Post-overflow analysis** — enriches blocked events with geolocation, reverse DNS, and threat category

### Installing CrowdSec

```bash
# Ubuntu/Debian
curl -s https://packagecloud.io/install/repositories/crowdsec/crowdsec/script.deb.sh | sudo bash
sudo apt install crowdsec

# Verify installation
sudo cscli version
sudo systemctl status crowdsec
```

### NGINX Bouncer Configuration

```bash
# Install the NGINX bouncer
sudo apt install crowdsec-nginx-bouncer

# Configure the bouncer
sudo nano /etc/crowdsec/bouncers/crowdsec-nginx-bouncer.conf
```

```ini
# crowdsec-nginx-bouncer.conf
ENABLED=true
DAEMON_HTTP_ADDR=http://127.0.0.1:8080
API_KEY=<generated-key>
UPDATE_FREQUENCY=10s
```

Get your API key:

```bash
sudo cscli bouncers add nginx-bouncer
# Copy the API key output and paste it into the config file above
sudo systemctl restart crowdsec-nginx-bouncer
```

### Docker Compose with CrowdSec

```yaml
services:
  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec
    environment:
      GID: "${GID-1000}"
      COLLECTIONS: "crowdsecurity/nginx crowdsecurity/http-cve"
    volumes:
      - ./nginx-logs:/var/log/nginx/:ro
      - crowdsec-data:/var/lib/crowdsec/data/
      - ./config:/etc/crowdsec/:ro
    networks:
      - web

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx-logs:/var/log/nginx/
    depends_on:
      - crowdsec
    networks:
      - web

  # Optional: bouncer for CrowdSec dashboard
  metabase:
    image: metabase/metabase:latest
    ports:
      - "3000:3000"
    environment:
      MB_DB_FILE: /data/metabase.db
    volumes:
      - metabase-data:/data
    networks:
      - web

volumes:
  crowdsec-data:
  metabase-data:
```

### Creating Custom Scenarios

Define a brute-force detection scenario:

```yaml
# /etc/crowdsec/scenarios/http-brute-force.yaml
type: trigger
name: crowdsecurity/http-brute-force
description: "Detect HTTP brute-force attacks"
filter: "evt.Meta.log_type in ['http_access-log'] and evt.Meta.http_status_code in ['401', '403']"
groupby: "evt.Meta.source_ip"
distinct: "evt.Meta.target_uri"
count: 10
leak_speed: 60s
reference: now
labels:
  type: brute_force
  service: http
```

## Feature Comparison

| Feature | BunkerWeb | ModSecurity | CrowdSec |
|---|---|---|---|
| **License** | AGPLv3 | Apache 2.0 | MIT |
| **GitHub Stars** | 10,300+ | 9,600+ | 13,000+ |
| **Language** | Python/NGINX | C | Go |
| **Detection Method** | Rules + behavioral | Rule-based (SecRules) | Community intelligence + scenarios |
| **Management UI** | Built-in web UI | None (config files only) | CLI + Metabase dashboard |
| **Auto-ban** | Built-in | Via Fail2Ban integration | Built-in (crowdsourced) |
| **TLS Automation** | Automatic (ACME) | External (Certbot) | N/A |
| **Bot Protection** | Built-in detection | Via CRS rules | Via behavioral scenarios |
| **Deployment** | Docker, apt, systemd | NGINX/Apache module, Docker | Agent + bouncer architecture |
| **Learning Mode** | Yes | DetectionOnly mode | Simulation mode |
| **Plugin System** | Official plugins | Third-party modules | Bouncers for many platforms |
| **False Positive Rate** | Low (curated defaults) | Medium (CRS needs tuning) | Low (community-validated) |
| **Best For** | All-in-one protection | Deep customization | Collaborative threat intel |

## Which WAF Should You Choose?

### Choose BunkerWeb if:
- You want a secure-by-default WAF with minimal configuration
- You prefer a web-based management interface
- You need automatic TLS, bot detection, and WAF in a single package
- You are deploying a new stack and want integrated security

### Choose ModSecurity if:
- You need fine-grained control over every inspection rule
- You already run NGINX or Apache and want to add WAF capabilities
- You require compliance with specific rule sets (PCI-DSS, custom policies)
- Your team has security expertise to tune CRS rules and handle false positives

### Choose CrowdSec if:
- You want protection informed by global attack intelligence
- You run multiple servers and benefit from shared threat data
- You prefer lightweight bouncers over a full WAF proxy
- You already use NGINX, Traefik, or Caddy and want plug-in security

### Best Practice: Layer Them

For maximum protection, many teams combine approaches:

1. **BunkerWeb** as the edge proxy (WAF + TLS + bot detection)
2. **CrowdSec** bouncer for community IP reputation enrichment
3. **ModSecurity** CRS rules behind BunkerWeb for deep inspection

BunkerWeb actually has an official [CrowdSec plugin](https://github.com/bunkerity/bunkerweb-plugins), making this combination straightforward. For teams that need compliance-grade inspection, adding ModSecurity's CRS rules as a secondary layer provides defense in depth.

If you are just starting to secure your self-hosted infrastructure, also consider reading our [WAF and bot protection guide](../self-hosted-waf-bot-protection-modsecurity-coraza-crowdsec-2026/) for a deeper dive into OWASP rule sets, and our [PKI and certificate management guide](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/) for setting up TLS properly.

## FAQ

### Is BunkerWeb production-ready?
Yes. BunkerWeb is actively maintained (version 1.6.9 as of April 2026), used in production by thousands of organizations, and includes a plugin system, database-backed configuration, and high-availability support for multi-instance deployments.

### Can I run ModSecurity with NGINX?
Yes. ModSecurity v3 (libmodsecurity) has an official NGINX connector (`libnginx-mod-modsecurity`). On Ubuntu/Debian, install it via `apt install libnginx-mod-modsecurity`. On other distributions, you may need to compile NGINX with the ModSecurity module from source.

### How does CrowdSec share IP data without leaking my traffic?
CrowdSec only shares attacker IP addresses and metadata (attack type, timestamp, country) — never request bodies, headers, or user data. The local decision server runs entirely on your infrastructure, and sharing to the central API is opt-in.

### Which WAF has the lowest false positive rate?
CrowdSec typically has the lowest false positive rate because its IP bans are validated by the global community before propagation. BunkerWeb's curated default rules also minimize false positives. ModSecurity's OWASP CRS requires careful tuning (adjusting paranoia level and excluding specific rules) to avoid blocking legitimate traffic.

### Can I use CrowdSec with Traefik or Caddy?
Yes. CrowdSec provides official bouncers for Traefik (`crowdsecurity/traefik-bouncer`), Caddy (`crowdsecurity/caddy-bouncer`), HAProxy, Varnish, and Cloudflare. The bouncer architecture means CrowdSec works with virtually any reverse proxy.

### Does BunkerWeb replace my existing reverse proxy?
BunkerWeb is built on NGINX and acts as a reverse proxy with integrated WAF capabilities. If you already use NGINX, you can replace it with BunkerWeb. If you use Traefik, Caddy, or HAProxy, you can place BunkerWeb in front of them or use it alongside CrowdSec bouncers for layered security.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BunkerWeb vs ModSecurity vs CrowdSec: Best Self-Hosted WAF Guide 2026",
  "description": "Compare BunkerWeb, ModSecurity, and CrowdSec — three open-source web application firewalls. Learn which self-hosted WAF fits your infrastructure with Docker configs, deployment guides, and feature comparisons.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
