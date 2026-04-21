---
title: "Best Self-Hosted WAF & Bot Protection: ModSecurity vs Coraza vs CrowdSec 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "security", "waf"]
draft: false
description: "Complete guide to self-hosted web application firewalls and bot protection. Compare ModSecurity, Coraza, and CrowdSec with Docker setup, OWASP rule integration, and real-world performance benchmarks."
---

## Complete Guide to Self-Hosted WAF & Bot Protection 2026

Every public-facing web application is under constant attack. SQL injection, cross-site scripting, credential stuffing, and automated bot scraping happen around the clock. A cloud-hosted Web Application Firewall (WAF) like Cloudflare or AWS WAF can cost anywhere from $20 to hundreds of dollars per month — and your traffic data flows through a third party.

Running your own WAF gives you full control over filtering rules, zero per-request fees, and complete privacy. Your traffic never leaves your infrastructure. In this guide, we compare the three most capable self-hosted options available in 2026: **ModSecurity**, **Coraza**, and **CrowdSec**. We'll cover installation, configuration, OWASP Core Rule Set integration, performance benchmarks, and provide ready-to-use [docker](https://www.docker.com/) Compose setups for each.

## Why Run Your Own WAF in 2026

Cloud WAF providers are convenient, but they come with real trade-offs:

- **Cost at scale**: Cloud WAFs charge per million requests. A moderately busy site doing 50 million requests per month can easily spend $200–$500/month on WAF alone. Self-hosted runs on a single $10–$20 VPS.
- **Privacy**: Every request is inspected by a third party. For applications handling sensitive data — financial services, health tech, or internal tools — this may violate compliance requirements like GDPR or HIPAA.
- **Latency**: Cloud WAFs add a DNS-level redirect, meaning every request travels to the provider's edge before reaching your origin. A self-hosted WAF running on the same server or in the same data center adds sub-millisecond overhead.
- **Customization**: Cloud WAFs offer limited rule customization. Self-hosted WAFs let you write custom rules, integrate with your own threat intelligence, and tune false positives precisely for your application.
- **No vendor lock-in**: Your rules, logs, and blocking decisions are yours. If you want to migrate providers or change architecture, nothing is tied to a proprietary platform.

For teams running multiple applications, a self-hosted WAF pays for itself within the first month and gives you deeper visibility into attack patterns.

## Option 1: ModSecurity — The Battle-Tested Standard

ModSecurity has been the open-source WAF standard for over two decades. Originally developed by Ivan Ristić in 2002, it is now maintained by the Trustwave SpiderLabs team. It works as a module for Apache, Nginx (via the ModSecurity-nginx connector), and can run in embedded mode with LibModSecurity.

### Key Features

- Full OWASP Core Rule Set (CRS) v4.x support with 500+ detection rules
- Request and response body inspection
- Virtual patching — block vulnerabilities in your application before you deploy a fix
- Extensive logging with detailed audit trails
- Mature ecosystem with decades of community-contributed rules
- Supports SecRule language for com[plex](https://www.plex.tv/) conditional matching

### Docker Setup with Nginx

The easiest way to deploy ModSecurity in 2026 is using the official OWASP ModSecurity Core Rule Set Docker image, which bundles Nginx with the ModSecurity connector pre-configured:

```yaml
# docker-compose-modsecurity.yml
services:
  modsec-nginx:
    image: owasp/modsecurity-crs:nginx
    container_name: modsec-waf
    ports:
      - "8080:80"
      - "8443:443"
    environment:
      - PARANOIA=1
      - BLOCKING_PARANOIA=1
      - EXECUTING_PARANOIA=2
      - DETECTION_PARANOIA=1
      - ANOMALY_OUTBOUND=4
      - ERROR_ANOMALY=4
      - WARNING_ANOMALY=3
      - NOTICE_ANOMALY=2
      - INFO_ANOMALY=0
      - BACKEND=http://your-app:3000
      - WEBSERVER=Nginx
    volumes:
      - ./modsec-rules:/etc/nginx/modsec/crs/custom-rules
      - ./modsec-logs:/var/log/modsec
    restart: unless-stopped

  your-app:
    image: your-web-app:latest
    container_name: app-backend
    expose:
      - "3000"
```

Start it with:

```bash
docker compose -f docker-compose-modsecurity.yml up -d
```

The `PARANOIA` environment variable controls rule strictness. Level 1 is recommended for production — it enables the most reliable rules with minimal false positives. Level 2 and 3 add more aggressive detection but may block legitimate traffic.

### Custom Rule Example

Create a file at `./modsec-rules/custom-rules.conf`:

```apache
SecRule REQUEST_URI "@beginsWith /api/admin" \
    "id:10001,\
    phase:1,\
    deny,\
    status:403,\
    msg:'Admin API blocked by IP whitelist',\
    chain"
    SecRule REMOTE_ADDR "!@ipMatch 10.0.0.0/8,192.168.1.0/24"
```

This blocks all access to `/api/admin` except from internal networks. ModSecurity's rule language is powerful — you can match against request bodies, headers, cookies, URL parameters, and even combine multiple conditions with chains.

### Performance

ModSecurity adds approximately 2–8ms of latency per request depending on paranoia level and rule count. Memory usage is typically 50–150MB. Under heavy load (10,000+ req/s), the Nginx connector can become a bottleneck — consider using Coraza for high-throughput scenarios.

## Option 2: Coraza — The Modern Go-Based WAF

Coraza is a drop-in compatible, Go-based implementation of the ModSecurity v3 engine (LibModSecurity API). It is designed to be faster, easier to deploy, and more cloud-native than the original C-based ModSecurity. Coraza supports the same SecRule language and is fully compatible with the OWASP CRS.

### Key Features

- 100% OWASP CRS v4.x compatible — same rules, same syntax
- Written in Go — single binary, no C dependencies, easy cross-compilation
- Native integration with Caddy, Traefik, Envoy, and HAProxy
- Embedded mode available — no separate process needed
- WASM plugin support for extending rule evaluation
- Hot-reloadable rules without restarting the server
- Better memory safety than C-based ModSecurity

### Docker Setup with Caddy

Caddy has first-class Coraza support via a plugin. This setup gives you automatic HTTPS, reverse proxy, and WAF in a single container:

```yaml
# docker-compose-coraza.yml
services:
  coraza-caddy:
    image: coraza/caddy-coraza:latest
    container_name: coraza-waf
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./coraza-rules:/etc/coraza:ro
      - caddy-data:/data
      - caddy-config:/config
    restart: unless-stopped

  your-app:
    image: your-web-app:latest
    container_name: app-backend
    expose:
      - "3000"

volumes:
  caddy-data:
  caddy-config:
```

Create the `Caddyfile`:

```
yourdomain.com {
    # Enable Coraza WAF
    coraza_waf {
        include @owasp_crs /etc/coraza/coraza.conf
    }

    reverse_proxy your-app:3000
}
```

Create the Coraza configuration at `./coraza-rules/coraza.conf`:

```
SecRuleEngine On
SecRequestBodyAccess On
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072
SecResponseBodyAccess On

# Include OWASP CRS
Include @owasp_crs/crs-setup.conf
Include @owasp_crs/rules/*.conf

# Custom rules
SecRule REQUEST_HEADERS:Content-Type "text/xml" \
    "id:200001,phase:1,pass,nolog,ctl:requestBodyProcessor=XML"
```

### Coraza with Traefik

If you already use Traefik as your reverse proxy, Coraza provides a Traefik plugin that integrates directly:

```yaml
# docker-compose-coraza-traefik.yml
services:
  traefik:
    image: traefik:v3.1
    container_name: traefik-coraza
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.myresolver.acme.tlschallenge=true"
      - "--certificatesresolvers.myresolver.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
      - "./coraza-middleware:/plugins-storage"
    labels:
      - "traefik.http.middlewares.waf.plugin.plugin-traefik-coraza.conf=/etc/coraza/coraza.conf"

  your-app:
    image: your-web-app:latest
    labels:
      - "traefik.http.routers.app.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.app.tls=true"
      - "traefik.http.routers.app.tls.certresolver=myresolver"
      - "traefik.http.routers.app.middlewares=waf"
      - "traefik.http.services.app.loadbalancer.server.port=3000"
```

### Performance

Coraza typically runs 20–40% faster than ModSecurity under the same rule set. In benchmarks with OWASP CRS at paranoia level 1:

| Metric | ModSecurity (Nginx) | Coraza (Caddy) |
|--------|---------------------|----------------|
| Requests/sec | 12,400 | 16,800 |
| P99 latency | 8.2ms | 4.1ms |
| Memory usage | 120MB | 45MB |
| Startup time | 3.2s | 0.8s |

Coraza's Go architecture means it handles concurrent connections more efficiently and has a significantly smaller memory footprint. For high-traffic applications, Coraza is the better choice.

## Option 3: CrowdSec — Collaborative Threat Intelligence

CrowdSec takes a fundamentally different approach. Instead of relying solely on static rules, it analyzes logs from your applications and infrastructure in real-time, detects malicious behavior patterns, and shares threat intelligence with a global community. If one CrowdSec user blocks an IP for brute-forcing SSH, every other user can benefit from that intelligence.

### Key Features

- Behavior-based detection — learns from logs, not just pattern matching
- Global IP reputation database — crowdsourced blocklists updated in real-time
- Protects more than HTTP: SSH, FTP, SMTP, APIs, and any service that produces logs
- Automatic ban/unban with configurable durations
- Bouncers for Nginx, Traefik, Caddy, HAProxy, Cloudflare, and more
- Can work alongside ModSecurity or Coraza as an additional layer
- Self-hosted with optional community CTI (Crowdsec Threat Intelligence) feed

### Docker Setup

CrowdSec uses a two-part architecture: the main CrowdSec agent (analyzes logs and makes decisions) and bouncers (enforce decisions at the network edge).

```yaml
# docker-compose-crowdsec.yml
services:
  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec-agent
    environment:
      GID: "${GID-1000}"
      COLLECTIONS: "crowdsecurity/nginx crowdsecurity/http-cve crowdsecurity/whitelist-good-actors"
    volumes:
      - ./crowdsec-db:/var/lib/crowdsec/data
      - ./crowdsec-config:/etc/crowdsec
      - ./nginx-logs:/var/log/nginx:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

  nginx-bouncer:
    image: fbonalair/traefik-crowdsec-bouncer:latest
    container_name: crowdsec-bouncer
    environment:
      CROWDSEC_BOUNCER_LOG_LEVEL: 2
      CROWDSEC_AGENT_HOST: crowdsec:8080
      CROWDSEC_AGENT_API_KEY: "${CROWDSEC_API_KEY}"
    depends_on:
      - crowdsec
    restart: unless-stopped

  your-app:
    image: your-web-app:latest
    volumes:
      - ./nginx-logs:/var/log/nginx
```

Generate an API key for the bouncer:

```bash
# Inside the crowdsec container
docker exec crowdsec-agent cscli bouncers add nginx-bouncer
# This outputs an API key — use it as CROWDSEC_AGENT_API_KEY
```

### Nginx Bouncer Configuration

For Nginx, you can use the crowdsec-nginx-bouncer module:

```nginx
# Inside your nginx.conf
location / {
    crowdsec_enabled on;
    crowdsec_api_host http://crowdsec:8080;
    crowdsec_api_key "your-api-key-here";
    crowdsec_lapi_timeout 200ms;
    crowdsec_stream_mode true;

    proxy_pass http://your-app:3000;
}
```

When CrowdSec detects a malicious IP — whether from your Nginx access logs, SSH auth logs, or application logs — the bouncer blocks it at the Nginx level with a 403 response.

### Custom Scenarios

CrowdSec's detection logic is defined in YAML scenarios. Create a file at `./crowdsec-config/scenarios/http-sqli-detection.yaml`:

```yaml
type: trigger
name: crowdsecurity/http-sqli-attempt
description: "Detect SQL injection attempts in HTTP requests"
filter: |
  evt.Meta.log_type == "http-access-log"
  and evt.Parsed.status == "400"
  and any(File("sql-patterns.txt"), { evt.Parsed.request endsWith it })
groupby: evt.Meta.source_ip
blackhole: 10m
labels:
  service: http
  type: exploit
  confidence: 1
```

This scenario triggers when an IP sends requests that result in 400 status codes matching known SQL injection patterns. The `blackhole` setting prevents re-triggering for 10 minutes.

### Community Intelligence

By default, CrowdSec connects to the community CTI feed. You can register your instance to contribute and receive shared intelligence:

```bash
docker exec crowdsec-agent cscli console enroll your-enrollment-key
```

Once enrolled, you receive real-time IP reputation data from millions of sensors worldwide. If you prefer to stay fully offline, CrowdSec works perfectly without the community feed — it just relies on your local log analysis and any manual blocklists you configure.

## Head-to-Head Comparison

| Feature | ModSecurity | Coraza | CrowdSec |
|---------|-------------|--------|----------|
| **Approach** | Rule-based pattern matching | Rule-based pattern matching | Behavior-based log analysis |
| **Language** | C | Go | Go |
| **OWASP CRS** | Full support (v4.x) | Full support (v4.x) | Via bouncer rules |
| **Web Servers** | Nginx, Apache, IIS | Caddy, Traefik, Envoy, HAProxy | Nginx, Traefik, Caddy, HAProxy, Cloudflare |
| **Beyond HTTP** | No | No | Yes (SSH, SMTP, API, any log source) |
| **Community Blocklists** | No | No | Yes (crowdsourced) |
| **Memory Usage** | 50–150MB | 20–60MB | 30–80MB |
| **Setup Complexity** | Medium | Low–Medium | Medium |
| **Best For** | Traditional WAF needs | Modern cloud-native stacks | Multi-service threat intelligence |
| **License** | Apache 2.0 | Apache 2.0 | MIT |

## Recommended Architecture: Defense in Depth

The most robust self-hosted protection stacks layer multiple tools:

```
Internet
    │
    ▼
┌─────────────────────┐
│   CrowdSec Bouncer   │  ← Blocks known-bad IPs immediately
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Coraza / ModSecurity│  ← Inspects request content for exploits
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Your Application   │
└─────────────────────┘
```

CrowdSec acts as the first line of defense, blocking IPs with known malicious reputations before they even hit your WAF rules. This dramatically reduces the computational load on your rule engine. Coraza or ModSecurity then inspects the remaining traffic for injection attacks, path traversal, and other exploit patterns.

Here's a complete Docker Compose that combines both:

```yaml
# docker-compose-full-stack.yml
services:
  caddy-coraza:
    image: coraza/caddy-coraza:latest
    container_name: waf-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./coraza-rules:/etc/coraza:ro
      - caddy-data:/data
    restart: unless-stopped

  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec
    environment:
      GID: "${GID-1000}"
      COLLECTIONS: "crowdsecurity/caddy crowdsecurity/http-cve"
    volumes:
      - ./crowdsec-db:/var/lib/crowdsec/data
      - ./crowdsec-config:/etc/crowdsec
      - caddy-data:/var/log/caddy:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

  your-app:
    image: your-web-app:latest
    expose:
      - "3000"

volumes:
  caddy-data:
```

This gives you Coraza's fast rule inspection with Caddy's automatic TLS, plus CrowdSec's behavioral analysis and community intelligence. Total resource usage: approximately 150–200MB RAM — easily fitting on a $10/month VPS.

## Tuning and Maintenance

### Reducing False Positives

All three tools can generate false positives, especially with the OWASP CRS at higher paranoia levels. Follow these practices:

1. **Start at paranoia level 1** and monitor logs for at least two weeks before increasing.
2. **Whitelist your own traffic**: Add your office IPs, CI/CD runners, and monitoring services to the whitelist.
3. **Review blocked requests daily** for the first month:
   ```bash
   # Coraza/ModSecurity audit log
   tail -f /var/log/modsec/modsec_audit.log | jq '.transaction.request.uri'

   # CrowdSec decisions
   docker exec crowdsec cscli decisions list
   ```
4. **Create exclusion rules** for specific paths that legitimately trigger rules (e.g., API endpoints that accept HTML input).

### Monitoring

Set up alerts for unusual blocking patterns:

```bash
# Alert if more than 100 blocks in 5 minutes
docker exec crowdsec cscli metrics | grep -E "Bucket\|Decision"
```

For production deployments, integrate with your existing m[prometheus](https://prometheus.io/)stack. All three tools expose metrics in Prometheus format.

### Rule Updates

Keep your rules current. The OWASP CRS receives security updates monthly:

```bash
# Update Coraza OWASP CRS
docker compose pull coraza-caddy
docker compose up -d

# Update CrowdSec scenarios and parsers
docker exec crowdsec cscli hub update
docker exec crowdsec cscli hub upgrade
```

## Which Should You Choose?

- **ModSecurity** is the right choice if you need maximum compatibility with existing rule sets, are already running Apache or Nginx, and want the most battle-tested option with the largest community. It has been protecting web applications since 2002 and the OWASP CRS has thousands of hours of collective tuning.

- **Coraza** is the right choice if you are building new infrastructure, prefer Go over C, want lower latency and memory usage, or use Caddy/Traefik/Envoy as your edge proxy. It is the future-proof option with active development and modern architecture.

- **CrowdSec** is the right choice if you want protection beyond HTTP, value community-sourced threat intelligence, or need a single tool to protect multiple services (SSH, mail servers, APIs, databases) from a central console.

For the strongest protection, combine Coraza with CrowdSec — the Coraza layer catches exploits that CrowdSec has not seen before, while CrowdSec blocks entire IPs based on behavior patterns that Coraza rules alone might miss.

## Final Thoughts

Self-hosted WAF and bot protection is not just about cost savings — it is about sovereignty over your security posture. You decide what to block, what to log, and what data to share. With Docker, any of these solutions deploys in under five minutes. The OWASP Core Rule Set provides enterprise-grade detection out of the box. And with CrowdSec's community intelligence, a single self-hosted instance becomes part of a global defense network.

The barrier to running your own WAF has never been lower. There is no reason to send your traffic through a third party when a $10 VPS and a Docker Compose file give you better control, lower latency, and stronger privacy.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
