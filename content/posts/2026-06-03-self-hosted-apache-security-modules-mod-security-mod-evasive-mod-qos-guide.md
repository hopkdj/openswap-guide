---
title: "Self-Hosted Apache Security Module Management: mod_security vs mod_evasive vs mod_qos"
date: "2026-06-03"
tags: ["apache", "web-server", "security", "waf", "ddos-protection", "rate-limiting", "mod-security"]
draft: false
---

The Apache HTTP Server remains one of the most widely deployed web servers in self-hosted environments, powering everything from internal tools to public-facing applications. One of Apache's greatest strengths is its modular architecture — security administrators can layer protection directly into the web server through loadable modules, without deploying separate proxy or gateway services.

In this guide, we compare three essential Apache security modules — **mod_security** (Web Application Firewall), **mod_evasive** (DDoS protection), and **mod_qos** (Quality of Service / rate limiting) — and show you how to deploy them effectively in a self-hosted environment.

## Comparison Table: mod_security vs mod_evasive vs mod_qos

| Feature | mod_security | mod_evasive | mod_qos |
|---------|-------------|-------------|---------|
| **Purpose** | Web Application Firewall (WAF) | DDoS / brute-force protection | Rate limiting & QoS |
| **OWASP CRS Support** | Yes (full rule set) | No | No |
| **Request Inspection** | Full body, headers, args | URL + headers (basic) | Headers, URL patterns |
| **Block Mechanism** | 403 Forbidden (configurable) | 403 Forbidden | 503 + throttle response |
| **Logging** | Audit log with full request capture | Syslog | Custom log format |
| **Learning Mode** | Yes (anomaly scoring) | No | Yes (event tracking) |
| **Connection Tracking** | Per-request | Per-IP | Per-IP + per-URL |
| **Memory Footprint** | Moderate to high with CRS | Very low | Low to moderate |
| **Configuration Complexity** | High | Low | Medium |

## mod_security: The Web Application Firewall

mod_security is the industry-standard open-source WAF for Apache. Originally developed by Ivan Ristić and now maintained by the OWASP community, it inspects HTTP requests and responses against a rule set designed to detect SQL injection, cross-site scripting (XSS), command injection, and other web application attacks.

**Key features:**
- **OWASP Core Rule Set (CRS)** integration with 200+ detection rules
- **Anomaly scoring mode**: assigns scores to suspicious requests and blocks when thresholds are exceeded
- **Full audit logging**: captures complete request and response data for forensic analysis
- **Virtual patching**: create custom rules to block specific vulnerabilities without touching application code

**Docker Compose deployment with mod_security:**

```yaml
version: "3.8"
services:
  apache-modsec:
    image: owasp/modsecurity:3-nginx
    ports:
      - "80:80"
      - "443:443"
    environment:
      - BACKEND=http://app:8080
      - MODSEC_RULE_ENGINE=On
      - PARANOIA_LEVEL=1
    volumes:
      - ./modsec_rules:/etc/modsecurity.d/owl
    depends_on:
      - app

  app:
    image: nginx:alpine
```

**Minimal mod_security configuration (`modsecurity.conf`):**

```apache
SecRuleEngine On
SecRequestBodyAccess On
SecResponseBodyAccess On
SecAuditEngine RelevantOnly
SecAuditLog /var/log/modsec_audit.log
SecRule REQUEST_HEADERS:User-Agent "bot|scanner|crawler"   "id:1000,phase:1,deny,status:403,msg:'Blocked bot UA'"
```

For production deployments, enable the OWASP CRS and tune the paranoia level based on your application's false positive tolerance.

## mod_evasive: DDoS and Brute-Force Protection

mod_evasive provides lightweight protection against HTTP DoS attacks and brute-force attempts. It tracks per-IP request rates and automatically blocks clients that exceed configurable thresholds.

**Key features:**
- **Per-IP rate tracking** across configurable time windows
- **Automatic blocking** with temporary deny lists
- **Email notification** on block events (via system command)
- **Minimal configuration** — works out of the box with sensible defaults

**Installation (Ubuntu/Debian):**

```bash
apt-get install libapache2-mod-evasive
a2enmod evasive
```

**Configuration example (`/etc/apache2/mods-enabled/evasive.conf`):**

```apache
<IfModule mod_evasive24.c>
    DOSHashTableSize    3097
    DOSPageCount        5
    DOSSiteCount        100
    DOSPageInterval     2
    DOSSiteInterval     2
    DOSBlockingPeriod   60
    DOSEmailNotify      admin@example.com
    DOSLogDir           "/var/log/mod_evasive"
</IfModule>
```

This configuration blocks IPs that request the same page more than 5 times in 2 seconds, or more than 100 total requests in 2 seconds. Blocks last 60 seconds. mod_evasive uses a shared memory hash table for tracking, making it efficient even under high request volumes.

## mod_qos: Quality of Service and Advanced Rate Limiting

mod_qos provides fine-grained rate limiting, connection throttling, and request quality controls. Unlike mod_evasive's simple per-IP counting, mod_qos can rate-limit based on URL patterns, HTTP methods, request headers, and even response characteristics.

**Key features:**
- **Per-URL rate limiting**: Different limits for different endpoints
- **Connection concurrency control**: Limit simultaneous connections per IP or globally
- **Request throttling**: Slow down (rather than block) excessive clients
- **Byte-level limiting**: Control bandwidth per connection or per request
- **Event tracking**: Monitor and log QoS events for tuning

**Docker Compose with mod_qos:**

```yaml
services:
  apache-qos:
    image: httpd:2.4
    ports:
      - "80:80"
    volumes:
      - ./httpd-qos.conf:/usr/local/apache2/conf/httpd.conf
```

**Configuration example:**

```apache
LoadModule qos_module modules/mod_qos.so

# Limit to 50 concurrent connections per IP
QS_SrvMaxConnPerIP              50

# Limit per-URL request rate: 10 req/sec for API, 30 for static
QS_LocRequestLimitMatch         "^/api/" 10
QS_LocRequestLimitMatch         "^/static/" 30

# Limit request line + headers to 128KB max
QS_LimitRequestBody             131072

# Track and log events
QS_ClientEventBlockCount        50 180
```

## Why Self-Host Your Apache Security Modules?

Running security modules directly in Apache eliminates the need for a separate proxy or gateway layer in your self-hosted infrastructure. Each module addresses a different class of threat:

**mod_security protects your application layer.** It inspects the actual content of requests — SQL injection attempts hidden in form fields, XSS payloads in URL parameters, command injection in headers. A standalone rate limiter cannot detect these attacks because they look like normal requests at the network level.

**mod_evasive protects your server resources.** Layer 7 DDoS attacks work by consuming server resources (CPU, memory, connection slots) through high request volumes, even if each request is syntactically valid. mod_evasive detects the volume pattern and blocks the source before resource exhaustion occurs.

**mod_qos provides operational control.** Not all high-traffic scenarios are attacks — a popular API endpoint can overwhelm your server during normal usage. mod_qos lets you define tiered rate limits: aggressive limits for expensive endpoints, generous limits for cached static assets, and everything in between.

**Module-level deployment reduces latency.** Each additional hop in your request path adds latency. By running WAF and rate limiting as Apache modules (not as a separate proxy), requests go through a single process with no extra network hops.

For broader WAF comparison, see our [BunkerWeb vs ModSecurity vs CrowdSec guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/). For rate limiting across different web servers, check our [Nginx vs Caddy vs Envoy rate limiting comparison](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/). For web server selection, our [OpenResty vs Nginx vs Caddy guide](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers performance and feature trade-offs.


## Deployment Architecture Best Practices

When deploying Apache security modules in a self-hosted environment, consider these operational patterns to balance security with performance:

**Layer your security modules.** mod_evasive should run in the earliest request processing phase to block volumetric attacks before they consume resources. mod_qos should apply rate limits in the access control phase. mod_security should inspect requests in phase:2 (request body processing) after basic rate limiting has passed. This ordering ensures that a DDoS attack is blocked by mod_evasive before mod_security expends CPU cycles analyzing payloads.

**Tune mod_security for your application.** The OWASP CRS default configuration is intentionally aggressive and will generate false positives on most real-world applications. Run in anomaly scoring mode with `SecRuleEngine DetectionOnly` for at least a week in production, then analyze the audit log to identify rules that trigger on legitimate traffic. Disable or tune those rules before switching to blocking mode.

**Use shared memory for mod_evasive in multi-process configurations.** Apache's prefork and worker MPMs use multiple child processes that don't share memory by default. mod_evasive needs the `DOSHashTableSize` directive configured large enough to track all active client IPs across all processes. For very high traffic sites, consider using a Redis-backed rate limiting solution that shares state across processes.

**Monitor blocked requests.** All three modules log their blocking decisions — mod_security to the audit log, mod_evasive to syslog, and mod_qos to the access log with custom format specifiers. Aggregate these logs into your centralized logging system (ELK, Graylog, Loki) and create dashboards showing block rates by module, by URL path, and by source IP. This gives you visibility into attack patterns and helps tune rule thresholds.

**Test with production traffic patterns.** Load testing with `ab` or `wrk` from a single IP will trigger mod_evasive blocks that don't represent real distributed traffic. Use distributed load testing tools like `vegeta` with multiple source IPs, or replay captured production traffic through a staging Apache instance to validate your security module configuration.

## FAQ

### Do mod_security and mod_evasive work together?

Yes, they address different concerns and can be used simultaneously. mod_evasive blocks based on request volume (DDoS pattern), while mod_security blocks based on request content (attack payloads). They operate at different stages of Apache's request processing pipeline — mod_evasive in the early access phase and mod_security throughout the request lifecycle.

### What's the performance impact of mod_security with the OWASP CRS?

The full OWASP CRS with paranoia level 2 or higher adds approximately 1-5ms of processing latency per request on modern hardware. Memory usage increases by 50-200MB depending on the rule set size. For high-traffic sites, start with paranoia level 1 and only increase it if your threat model requires stricter inspection.

### Is mod_evasive sufficient protection against DDoS?

mod_evasive provides basic Layer 7 DDoS protection at the application level, but it cannot handle volumetric Layer 3/4 attacks (SYN floods, UDP floods). For comprehensive DDoS protection in a self-hosted environment, combine mod_evasive with kernel-level protections (iptables rate limiting, SYN cookies) and, for public-facing services, a CDN with DDoS scrubbing capabilities.

### Can mod_qos replace a dedicated rate limiting service?

For single-server Apache deployments, yes — mod_qos provides more granular control than external rate limiters for Apache-specific use cases. However, if you run multiple backend servers behind a load balancer, a centralized rate limiter (like HAProxy stick tables or a Redis-backed solution) provides consistent limits across the entire cluster.

### How do I test my mod_security rules?

Use the OWASP CRS test suite or run targeted penetration tests with tools like `nikto`, `sqlmap` (against test endpoints), or `curl` with crafted payloads. mod_security's audit log in `RelevantOnly` mode captures blocked requests with full details, making it easy to verify that rules are triggering correctly. Always test in a staging environment before deploying to production.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Apache Security Module Management: mod_security vs mod_evasive vs mod_qos",
  "description": "Compare Apache security modules mod_security (WAF), mod_evasive (DDoS protection), and mod_qos (rate limiting) for self-hosted web server protection. Docker Compose deployment examples included.",
  "datePublished": "2026-06-03",
  "dateModified": "2026-06-03",
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

***💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)**
