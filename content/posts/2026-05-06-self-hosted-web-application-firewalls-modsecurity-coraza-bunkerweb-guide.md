---
title: "Self-Hosted Web Application Firewalls: ModSecurity vs Coraza vs BunkerWeb (2026)"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "security", "waf", "web-application-firewall"]
draft: false
---

A Web Application Firewall (WAF) sits between your web applications and the internet, filtering malicious traffic before it reaches your servers. Self-hosted WAFs give you full control over security rules, logging, and blocking behavior without sending sensitive request data to cloud-based WaaS providers.

In this guide, we compare three leading self-hosted WAF solutions: **ModSecurity**, **Coraza**, and **BunkerWeb**. Each offers different approaches to web application protection, from the battle-tested ModSecurity engine to the modern Go-based Coraza and the all-in-one BunkerWeb platform.

## What Is a Self-Hosted WAF?

A Web Application Firewall inspects HTTP/HTTPS traffic and applies security rules to block common attack patterns including SQL injection, cross-site scripting (XSS), path traversal, and remote code execution. Self-hosted WAFs run on your own infrastructure rather than as a cloud service.

Key benefits of self-hosted WAF solutions:

- **Data privacy**: Request and response data never leaves your network
- **Custom rules**: Write and deploy rules tailored to your specific applications
- **No per-request pricing**: Unlimited traffic without cloud WAF metering
- **Low latency**: Local processing avoids the round-trip delay of cloud WAFs
- **Compliance**: Meet data residency requirements by keeping inspection on-premises

## ModSecurity vs Coraza vs BunkerWeb: Feature Comparison

| Feature | ModSecurity | Coraza | BunkerWeb |
|---------|------------|--------|-----------|
| **Language** | C | Go | Python + Nginx |
| **License** | Apache 2.0 | Apache 2.0 | AGPL v3 |
| **Stars** | 10,000+ | 3,000+ | 3,000+ |
| **Rule Engine** | SecRules | SecRules (compatible) | Built-in + CRS |
| **OWASP CRS Support** | Native | Native | Native |
| **Reverse Proxy Mode** | Via Nginx/Apache | Via Caddy/Envoy | Built-in Nginx |
| **Docker Support** | Community images | Official images | Official images |
| **Web UI** | None | None | Built-in |
| **Learning Mode** | No | No | Yes (auto-rules) |
| **GeoIP Blocking** | Manual config | Via plugins | Built-in |
| **Bot Detection** | Manual rules | Manual rules | Built-in |
| **Let us Encrypt** | Manual | Manual | Built-in |
| **Self-Hosted** | Yes | Yes | Yes |

## ModSecurity: The Industry Standard WAF

[ModSecurity](https://github.com/owasp-modsecurity/ModSecurity) is the most widely deployed open-source WAF engine. Originally developed for Apache, ModSecurity v3 supports Nginx, Apache, and IIS through connector modules.

**Key features:**
- Mature rule engine with decades of real-world testing
- Full OWASP Core Rule Set (CRS) compatibility
- SecRules language for custom rule authoring
- Detailed audit logging for forensic analysis
- Supports Apache, Nginx, and IIS via connectors
- Extensive community knowledge base and tutorials

### Docker Compose with Nginx + ModSecurity

```yaml
version: "3.8"
services:
  nginx-modsec:
    image: owasp/modsecurity-crs:nginx
    container_name: modsecurity-waf
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./modsecurity.conf:/etc/nginx/modsecurity.d/modsecurity.conf:ro
      - ./crs-setup.conf:/etc/modsecurity.d/owasp-crs/crs-setup.conf:ro
      - ./custom-rules:/etc/nginx/modsecurity.d/custom-rules:ro
    environment:
      - PARANOIA=1
      - BLOCKING_PARANOIA=1
      - EXECUTING_PARANOIA=1
      - DETECTION_PARANOIA=1
      - ANOMALY_INBOUND=10
      - ANOMALY_OUTBOUND=5
```

### Core ModSecurity Configuration

```apache
SecRuleEngine On
SecRequestBodyAccess On
SecRequestBodyLimit 13107200
SecRequestBodyNoFilesLimit 131072
SecAuditEngine RelevantOnly
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogType Serial
SecAuditLog /var/log/modsec_audit.log
SecArgumentSeparator &
SecCookieFormat 0
SecUnicodeMapFile unicode.mapping 20127
SecStatusEngine On
```

## Coraza: Modern Go-Based WAF Engine

[Coraza](https://github.com/corazawaf/coraza) is a modern, enterprise-grade WAF written in Go. It implements the ModSecurity SecRules language for full compatibility while offering better performance and easier deployment through Go native integrations.

**Key features:**
- Full ModSecurity SecRules language compatibility
- Native OWASP CRS support
- Caddy, Envoy, and Traefik integration via plugins
- Better performance than ModSecurity v3 in benchmarks
- Memory-safe implementation in Go
- Designed for cloud-native and microservices architectures

### Docker Compose with Caddy + Coraza

```yaml
version: "3.8"
services:
  caddy-coraza:
    image: dunglas/mercure:latest
    container_name: coraza-waf
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./coraza.conf:/etc/coraza/coraza.conf:ro
      - ./crs:/etc/coraza/crs:ro
    environment:
      - SERVER_NAME=:443
      - MERCURE_PUBLISHER_KEY=changeme
      - MERCURE_SUBSCRIBER_KEY=changeme

  # Alternative: Coraza with Envoy
  envoy-coraza:
    image: envoyproxy/envoy:v1.29-latest
    container_name: envoy-waf
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./coraza-filter.yaml:/etc/envoy/coraza-filter.yaml:ro
```

### Coraza Caddyfile Configuration

```
{
    order coraza_waf first
}

:443 {
    coraza_waf {
        load_owasp_crs
        directives `
            SecRuleEngine On
            SecRequestBodyAccess On
            SecAuditEngine RelevantOnly
            SecAuditLog /dev/stdout
            Include @owasp_crs/*.conf
        `
    }

    reverse_proxy localhost:8080
}
```

## BunkerWeb: All-in-One WAF Platform

[BunkerWeb](https://github.com/bunkerity/bunkerweb) is a next-generation WAF built on Nginx with a focus on ease of use. It combines a reverse proxy, WAF engine, auto-learning mode, and a web-based management UI into a single package.

**Key features:**
- Built-in web UI for rule management and monitoring
- Auto-learning mode that generates rules from normal traffic
- Integrated Let us Encrypt certificate management
- Built-in bot detection and GeoIP blocking
- Docker Swarm and Kubernetes support
- Real-time monitoring dashboard
- One-command deployment

### Docker Compose for BunkerWeb

```yaml
version: "3.8"
services:
  bunkerweb:
    image: bunkerity/bunkerweb:latest
    container_name: bunkerweb
    restart: unless-stopped
    ports:
      - "80:8080"
      - "443:8443"
    labels:
      SERVER_NAME: "www.example.com"
      USE_MODSECURITY: "yes"
      USE_MODSECURITY_CRS: "yes"
      USE_BUNKERNET: "no"
      USE_BLACKLIST: "yes"
      BLOCK_ABUSERS: "yes"
      AUTO_LEARN_MODE: "no"
      GEOIP_BLOCKING: "yes"
      GEOIP_ALLOW_LIST: "US CA GB DE FR"
    volumes:
      - bw-data:/data
      - bw-cache:/cache
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock

  bw-scheduler:
    image: bunkerity/bunkerweb-scheduler:latest
    container_name: bw-scheduler
    restart: unless-stopped
    depends_on:
      - bunkerweb
      - bw-docker
    volumes:
      - bw-data:/data
      - bw-cache:/cache
      - /var/run/docker.sock:/var/run/docker.sock:ro

  bw-docker:
    image: bunkerity/bunkerweb-docker:latest
    container_name: bw-docker
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

volumes:
  bw-data:
  bw-cache:
```

## Choosing the Right WAF

**Use ModSecurity when:**
- You need the most battle-tested and widely documented WAF
- Your team has existing SecRules expertise
- You run Apache or Nginx and want mature connector modules
- You need extensive community support and tutorials

**Use Coraza when:**
- You want ModSecurity compatibility with better performance
- You use Caddy, Envoy, or Traefik as your reverse proxy
- You prefer memory-safe Go over C for security-critical components
- You are building cloud-native or microservices architectures

**Use BunkerWeb when:**
- You want an all-in-one solution with a web management UI
- You need auto-learning mode for rapid rule generation
- You want built-in TLS, bot detection, and GeoIP without extra configuration
- You prefer Docker label-based configuration over manual config files

## Why Self-Host Your WAF?

Running a WAF on your own infrastructure gives you advantages that cloud WAFs cannot match:

**Complete data privacy**: HTTP requests often contain sensitive data including authentication tokens, personal information, and business secrets. Self-hosted WAFs inspect this traffic locally without transmitting it to third-party cloud providers.

**Zero added latency**: Cloud WAFs add network round-trip time as traffic routes through their data centers before reaching your servers. A self-hosted WAF processes requests on the same network, adding minimal latency.

**Unlimited traffic capacity**: Cloud WAF services charge per-request or bandwidth. Self-hosted WAFs handle unlimited traffic at the cost of your own compute resources, which is far cheaper at scale.

**Custom rule deployment**: Deploy application-specific WAF rules immediately without waiting for cloud provider approval or rule propagation delays. Test and iterate rules in your own environment.

**Regulatory compliance**: For industries with strict data residency requirements, keeping WAF inspection on-premises ensures request data never crosses jurisdictional boundaries.

For comprehensive server security, pair your WAF with [self-hosted IDS/IPS tools](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) for network-layer protection. Combine with [container security scanning](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-tools-guide-2026/) to catch vulnerabilities before deployment.

## FAQ

### What is the difference between ModSecurity and Coraza?

Coraza is a Go reimplementation of the ModSecurity engine that maintains full SecRules language compatibility while offering better performance and native integrations with modern proxies like Caddy and Envoy. ModSecurity is the original C-based engine with broader platform support.

### Does BunkerWeb use ModSecurity internally?

Yes. BunkerWeb uses ModSecurity as its WAF engine but wraps it with a user-friendly interface, auto-learning capabilities, and additional features like bot detection and GeoIP blocking that ModSecurity does not include out of the box.

### Can I migrate ModSecurity rules to Coraza?

Yes. Coraza implements the full ModSecurity SecRules language, so existing rule files are compatible. You may need to adjust connector-specific directives since Coraza uses different integration points.

### What is OWASP CRS and do these tools support it?

The OWASP Core Rule Set is a collection of generic attack detection rules that provide protection against common web application attacks. All three tools support OWASP CRS natively, with ModSecurity and Coraza offering direct inclusion and BunkerWeb bundling it as a configurable option.

### Is a self-hosted WAF enough for production security?

A WAF is one layer of defense. For production environments, combine it with network firewalls, container security scanning, TLS enforcement, and regular vulnerability assessments. See our [container security guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-tools-guide-2026/) for additional layers.

### Does Bunker work with Docker Swarm and Kubernetes?

Yes. BunkerWeb supports Docker Swarm through its scheduler service and Kubernetes through its official Helm chart. Both deployments use the same label-based configuration approach.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Web Application Firewalls: ModSecurity vs Coraza vs BunkerWeb (2026)",
  "description": "Compare self-hosted WAF solutions - ModSecurity, Coraza, and BunkerWeb - with Docker Compose configs and OWASP Core Rule Set integration.",
  "datePublished": "2026-05-06",
  "dateModified": "2026-05-06",
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
