---
title: "Self-Hosted WAF Core Rule Set Management: ModSecurity CRS vs Coraza CRS vs NAXSI Rules"
date: "2026-05-19"
tags: ["waf", "core-rule-set", "modsecurity", "coraza", "naxsi", "web-security", "application-security"]
draft: false
---

A Web Application Firewall (WAF) is only as effective as its rule set. While the WAF engine handles request inspection and blocking, the **Core Rule Set (CRS)** defines what threats to look for — SQL injection patterns, cross-site scripting payloads, file inclusion attempts, and hundreds of other attack signatures.

This guide compares three leading open-source WAF rule sets: the **OWASP ModSecurity Core Rule Set**, the **Coraza CRS**, and **NAXSI's built-in rules**. Each offers a different philosophy for balancing security coverage against false positive rates, and each integrates with different WAF engines.

## What Is a WAF Core Rule Set?

A Core Rule Set is a curated collection of detection rules that identify common web application attacks. These rules use pattern matching, anomaly scoring, and behavioral analysis to detect:

- **SQL injection (SQLi)**: Malicious database queries injected via input fields
- **Cross-site scripting (XSS)**: Script injection attempts targeting other users
- **Remote/local file inclusion (RFI/LFI)**: Attempts to load unauthorized files
- **Command injection**: OS command execution via web input
- **HTTP protocol violations**: Malformed requests, smuggling attempts
- **Bot detection**: Automated scanning, credential stuffing, scraping
- **Trojan protection**: Known malware signatures in uploaded files

Rule sets operate on an **anomaly scoring model**: each matched rule adds points to a request's threat score. When the total exceeds a configured threshold (typically 5), the request is blocked.

## OWASP ModSecurity Core Rule Set (CRS)

The [OWASP ModSecurity CRS](https://github.com/coreruleset/coreruleset) (3,130+ stars) is the industry-standard open-source WAF rule set, maintained by the OWASP community. It's designed primarily for ModSecurity 3.x (libmodsecurity) but is compatible with Coraza and other libmodsecurity-compatible engines.

**Key features:**

- 100+ rules organized into logical categories (SQLi, XSS, LFI, RFI, etc.)
- Paranoia levels 1-4: higher levels add more aggressive detection at the cost of false positives
- Anomaly scoring mode: cumulative threat scoring with configurable thresholds
- Regular updates from the OWASP community (monthly releases)
- Extensive documentation and testing frameworks (FTW — Firewall Tester
- Regression test suite with 30,000+ test cases
- Compatible with ModSecurity 3.x, Coraza, and any libmodsecurity-compatible engine
- Docker deployment via OWASP CRS Docker images

### Docker Compose Deployment

The CRS is typically deployed alongside ModSecurity or Coraza with a reverse proxy:

```yaml
version: "3.8"
services:
  nginx-modsecurity:
    image: owasp/modsecurity-crs:nginx
    container_name: nginx-modsecurity
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - BACKEND=http://backend-app:8080
      - PARANOIA=1
      - BLOCKING_PARANOIA=1
      - EXECUTING_PARANOIA=1
      - DETECTION_PARANOIA=1
      - ANOMALY_INBOUND=5
      - ANOMALY_OUTBOUND=4
      - ENFORCE_BODYPROC_URLENCODED=On
      - TX_MAX_NUM_ARGS=255
      - TX_MAX_REQUEST_BODY_LENGTH=13107200
    volumes:
      - ./modsecurity-config:/etc/nginx/modsec
      - ./modsecurity-log:/var/log/modsecurity
    depends_on:
      - backend-app

  backend-app:
    image: nginx:alpine
    container_name: backend-app
    restart: unless-stopped
```

### Rule Categories

The CRS organizes rules into numbered categories:

| Rule ID Range | Category | Description |
|---------------|----------|-------------|
| 91xxxx | Setup | Initialization, IP reputation, protocol enforcement |
| 92xxxx | HTTP Protocol | Request smuggling, header validation, content-type checks |
| 93xxxx | Application Attacks | RFI, LFI, command injection, code injection |
| 94xxxx | Generic Attacks | SQLi, XSS, session fixation, CSRF |
| 95xxxx | Data Leakage | Data exfiltration, error message leakage |
| 96xxxx | Common Exceptions | False positive exclusions for common frameworks |
| 97xxxx | Bot Detection | Automated scanner detection, credential stuffing |
| 98xxxx | Correlation | Score correlation, blocking decisions |

## Coraza CRS: Go-Native WAF Rules

The [Coraza WAF](https://github.com/corazawaf/coraza) (3,487+ stars) is a Go-native, ModSecurity-compatible WAF engine. The Coraza CRS is a fork/adaptation of the OWASP CRS optimized for Coraza's Go-based architecture, with improved performance and easier deployment.

**Key features:**

- Fully compatible with OWASP ModSecurity CRS rules
- Go-native implementation: no CGO dependencies, easier compilation
- Drop-in replacement for ModSecurity in nginx, Apache, Caddy, and Traefik
- Native integration with Caddy via coraza-caddy plugin
- Improved memory efficiency compared to C-based libmodsecurity
- WASM support for serverless WAF deployment
- Hot-reloadable rule sets without restart
- Docker deployment via official Coraza Docker images

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  coraza-waf:
    image: corazawaf/coraza:latest
    container_name: coraza-waf
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - CORAZA_RULE_ENGINE=On
      - CORAZA_REQUEST_BODY_LIMIT=13107200
      - CORAZA_AUDIT_ENGINE=On
      - CORAZA_AUDIT_LOG_PARTS=ABIJDEFHZ
      - CORAZA_PARANOIA_LEVEL=1
    volumes:
      - ./coraza-rules:/etc/coraza/rules
      - ./coraza-config:/etc/coraza/config
      - ./coraza-log:/var/log/coraza

  backend-app:
    image: nginx:alpine
    container_name: backend-app
    restart: unless-stopped
```

Coraza configuration with CRS rules:

```
SecRuleEngine On
SecRequestBodyAccess On
SecRequestBodyLimit 13107200
SecAuditEngine On
SecAuditLogParts ABIJDEFHZ

# Include OWASP CRS
Include /etc/coraza/rules/crs-setup.conf
Include /etc/coraza/rules/rules/*.conf

# Custom exclusions
SecRule REQUEST_URI "@beginsWith /api/health" "id:10001,phase:1,pass,nolog"
SecRule REQUEST_URI "@beginsWith /api/metrics" "id:10002,phase:1,pass,nolog"
```

## NAXSI Rules: Simple, Low-Maintenance WAF

[NAXSI](https://github.com/nbs-system/naxsi) (4,818+ stars) is a high-performance, low-rules-maintenance WAF for NGINX. Unlike ModSecurity/Coraza which use hundreds of signature-based rules, NAXSI takes a fundamentally different approach: it scores requests based on the presence of suspicious characters and patterns, using a much smaller rule set.

**Key features:**

- ~80 core rules vs 100+ for OWASP CRS — simpler maintenance
- Scoring-based detection: counts suspicious characters/patterns per zone
- Low false positive rate with minimal tuning
- NGINX module — integrates directly into the web server
- Web Application Firewall Learning Mode for automatic rule tuning
- NAXSI UI (nxtool) for log analysis and false positive management
- Docker deployment via NAXSI-enabled NGINX images
- Last major update: November 2023 (community-maintained)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  nginx-naxsi:
    image: nbsystem/nginx-naxsi:latest
    container_name: nginx-naxsi
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./naxsi-config:/etc/nginx/naxsi
      - ./naxsi-rules:/etc/nginx/naxsi.rules
      - ./nginx-log:/var/log/nginx
      - ./ssl:/etc/nginx/ssl:ro

  backend-app:
    image: nginx:alpine
    container_name: backend-app
    restart: unless-stopped
```

NAXSI configuration example:

```nginx
# naxsi.rules - Core scoring rules
BasicRule wl:0 "mz:$URL:/|$ARGS" "s:$SQL:8";
BasicRule wl:0 "mz:$URL:/|$ARGS" "s:$XSS:8";
BasicRule wl:0 "mz:$URL:/|$ARGS" "s:$TRAVERSAL:4";
BasicRule wl:0 "mz:$URL:/|$ARGS" "s:$EVADE:4";
BasicRule wl:0 "mz:$URL:/|$ARGS" "s:$RFI:8";

# Main location block
location / {
    SecRulesEnabled;
    DeniedUrl "/RequestDenied";
    CheckRule "$SQL >= 8" BLOCK;
    CheckRule "$XSS >= 8" BLOCK;
    CheckRule "$TRAVERSAL >= 4" BLOCK;
    CheckRule "$EVADE >= 4" BLOCK;
    CheckRule "$RFI >= 8" BLOCK;
    proxy_pass http://backend-app:8080;
}
```

## Comparison: ModSecurity CRS vs Coraza CRS vs NAXSI

| Feature | OWASP ModSecurity CRS | Coraza CRS | NAXSI Rules |
|---------|----------------------|------------|-------------|
| **Rule count** | 100+ | 100+ (OWASP compatible) | ~80 core rules |
| **Detection model** | Anomaly scoring | Anomaly scoring | Character/pattern scoring |
| **WAF engine** | ModSecurity 3.x | Coraza (Go) | NGINX module |
| **Paranoia levels** | 1-4 | 1-4 | Single level (configurable thresholds) |
| **False positive rate** | Moderate (requires tuning) | Moderate (same as OWASP) | Low (by design) |
| **Update frequency** | Monthly | Tracks OWASP CRS | Infrequent (community) |
| **Custom rules** | SecRule language | SecRule language | BasicRule / MainRule |
| **Learning mode** | Via FTW testing | Manual rule tuning | nxtool auto-tuning |
| **Performance** | High (C-based) | Very high (Go-native) | Very high (NGINX module) |
| **Docker support** | Official images | Official images | Community images |
| **License** | Apache 2.0 | Apache 2.0 | GPL v3 |
| **GitHub stars** | 3,130+ (CRS) | 3,487+ (Coraza) | 4,818+ (NAXSI) |
| **Best for** | Enterprise security, compliance | Go-based deployments, cloud-native | Simple setup, low maintenance |

## Choosing the Right Rule Set

**Choose OWASP ModSecurity CRS if:**
- You need the industry-standard rule set with maximum community support
- You're already running ModSecurity 3.x or a compatible engine
- You need parity levels for fine-grained security tuning
- Your compliance framework requires OWASP-validated rules
- You have resources to tune and maintain a large rule set

**Choose Coraza CRS if:**
- You prefer Go-based infrastructure with no CGO dependencies
- You're using Caddy, Traefik, or other Go-based proxies
- You need hot-reloadable rules without service restarts
- You want WASM-based serverless WAF deployment
- You want ModSecurity compatibility with better memory efficiency

**Choose NAXSI if:**
- You want the simplest possible WAF rule management
- You have limited security expertise for rule tuning
- You need very low false positive rates out of the box
- You're running NGINX and want native module integration
- You prefer scoring-based detection over signature matching

## Why Self-Host Your WAF Rules?

Running WAF rule sets on-premises gives you complete control over your web application security posture without depending on cloud WAF vendors. This is critical for organizations with strict data residency requirements, compliance mandates, or budget constraints.

Self-hosted WAF rules provide several advantages:

**Customization**: You can add, remove, or modify rules to match your specific application stack. Cloud WAF services often limit custom rule creation or charge extra for advanced configurations.

**Data privacy**: WAF logs containing request payloads, headers, and attack patterns never leave your infrastructure. This is essential for GDPR, HIPAA, and PCI DSS compliance.

**Cost efficiency**: No per-request or per-GB pricing. Self-hosted WAF rules run on your existing infrastructure with predictable hardware costs.

**Zero external dependencies**: Your WAF operates independently of cloud provider availability. No vendor lock-in, no API rate limits, no service degradation from shared infrastructure.

For broader WAF engine comparisons, see our [ModSecurity vs Coraza vs BunkerWeb guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/) and [API firewall comparison](../2026-04-26-krakend-vs-coraza-vs-envoy-self-hosted-api-firewall-guide/). For DDoS protection, check our [DDoS protection guide](../2026-04-26-self-hosted-ddos-protection-nginx-haproxy-bunkerweb-crowdsec-guide/).

## FAQ

### What is the difference between a WAF engine and a Core Rule Set?

The WAF engine (ModSecurity, Coraza, NAXSI) is the software that inspects HTTP requests and enforces blocking decisions. The Core Rule Set is the collection of detection rules that tells the engine what patterns to look for. Think of the engine as the processor and the rule set as the instruction manual — you can run different rule sets on the same engine.

### What are paranoia levels in OWASP CRS?

Paranoia levels (PL1-PL4) control how aggressively the CRS detects threats. PL1 catches obvious attacks with minimal false positives. PL2 adds more sensitive rules. PL3 includes even more aggressive detection. PL4 is the most aggressive, designed for high-security environments. Higher paranoia levels increase detection but also increase false positives, requiring more tuning.

### How often should WAF rule sets be updated?

OWASP ModSecurity CRS releases monthly updates with new detections, bug fixes, and false positive improvements. In production, test updates in a staging environment for 1-2 weeks before deploying to production. Coraza CRS tracks OWASP CRS updates. NAXSI updates less frequently but its simpler rule set requires less frequent changes.

### Can I combine NAXSI with ModSecurity CRS?

Yes, you can run NAXSI as a first layer (fast, low false positives) and ModSecurity/Coraza as a second layer (deeper inspection). NAXSI blocks obvious attacks at the NGINX level, while ModSecurity provides additional application-layer inspection. This defense-in-depth approach is common in production deployments.

### How do I reduce false positives with the CRS?

Start at paranoia level 1 and monitor logs for blocked legitimate requests. Add exclusion rules for specific URLs, parameters, or headers that trigger false positives. Use the CRS testing framework (FTW) to validate your tuning. Gradually increase paranoia levels as your exclusion rules mature.

### Is NAXSI suitable for production use?

Yes, NAXSI is used in production by organizations worldwide. Its scoring-based approach results in fewer false positives compared to signature-heavy rule sets. However, its last major update was in 2023, so it may not detect the newest attack vectors. It's best suited for applications where a smaller, well-understood rule set is preferable to comprehensive coverage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted WAF Core Rule Set Management: ModSecurity CRS vs Coraza CRS vs NAXSI Rules",
  "description": "Compare three leading open-source WAF rule sets for self-hosted web application security: OWASP ModSecurity CRS, Coraza CRS, and NAXSI rules.",
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
