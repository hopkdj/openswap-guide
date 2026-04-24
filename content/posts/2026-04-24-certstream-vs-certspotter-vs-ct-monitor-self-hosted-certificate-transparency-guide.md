---
title: "Certstream vs Certspotter vs ct_monitor: Self-Hosted Certificate Transparency Monitoring Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "monitoring", "certificate-transparency"]
draft: false
description: "Compare self-hosted Certificate Transparency monitoring tools — Certstream Server, SSLMate Certspotter, and ct_monitor — with Docker setups, alerting rules, and deployment guides for detecting rogue TLS certificates."
---

Certificate Transparency (CT) logs are public, append-only records of every TLS certificate issued by participating Certificate Authorities. Monitoring these logs in real time is critical for detecting rogue certificates, phishing domains, and unauthorized certificate issuance targeting your organization's domains.

This guide compares three self-hosted Certificate Transparency monitoring tools — [Certstream Server](https://github.com/CaliDog/certstream-server), [SSLMate Certspotter](https://github.com/SSLMate/certspotter), and [ct_monitor](https://github.com/crtsh/ct_monitor) — with Docker Compose configs, alerting setups, and deployment recommendations.

For complementary reading, see our [TLS certificate automation guide](../cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) for managing your own certificate lifecycle, and our [SSL/TLS scanning tools comparison](../testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026/) for auditing certificate configurations.

## Why Monitor Certificate Transparency Logs

Every time a trusted CA issues a TLS certificate, it is required to publish that certificate to one or more CT logs. These logs are publicly accessible and cryptographically verifiable, creating an auditable trail of all certificates on the web.

Self-hosted CT monitoring gives you:

- **Rogue certificate detection** — Identify certificates issued for your domains without your knowledge
- **Phishing domain discovery** — Detect typosquatting and homograph attack domains as soon as certificates are issued
- **Subdomain enumeration** — Discover all subdomains of your organization from certificate subject alternative names (SANs)
- **Compliance auditing** — Verify that all certificates for your domains follow internal naming conventions and security policies
- **Brand protection** — Monitor for certificate issuance on domains that impersonate your brand

While public CT log viewers exist, self-hosted monitoring allows you to run custom filtering, alerting, and integration pipelines that match your organization's specific needs.

## How Certificate Transparency Works

Certificate Transparency was proposed by Google in 2013 and is now mandated by all major browsers. The ecosystem has three key components:

1. **CT Logs** — Append-only, cryptographically verifiable data structures (Merkle trees) that store certificate records
2. **Certificate Authorities** — Submit newly issued certificates to CT logs before they can be trusted by browsers
3. **Monitors** — Continuously poll CT logs for new entries and filter them based on domain patterns

The CT ecosystem includes logs operated by Google, Cloudflare, Let's Encrypt, DigiCert, and others. A monitor must connect to multiple logs to ensure comprehensive coverage, as CAs may submit to different log sets.

```
Certificate Issued → CA submits to CT Logs → Monitors stream new entries → Filter by domain → Alert on matches
```

## Tools Compared at a Glance

| Feature | Certstream Server | SSLMate Certspotter | ct_monitor |
|---------|-------------------|---------------------|------------|
| **GitHub Stars** | 343 | 1,138 | 453 |
| **Language** | Elixir | Go | Go |
| **Last Updated** | Feb 2026 | Jan 2026 | Apr 2026 |
| **Docker Support** | Official image | Official image | Official image |
| **CT Log Sources** | Multiple (configurable) | Google CT Logs | crt.sh API |
| **Streaming Mode** | WebSocket + TCP | Polling + Webhook | Polling |
| **Domain Filtering** | Regex patterns | Domain list | Domain list |
| **Alerting** | Via webhooks | Via webhooks | Via stdout/logging |
| **Resource Usage** | Low (~100MB RAM) | Low (~50MB RAM) | Low (~30MB RAM) |
| **Best For** | Real-time streaming pipeline | Lightweight domain monitoring | crt.sh-based monitoring |

## Certstream Server: Real-Time CT Log Streaming

[Certstream Server](https://github.com/CaliDog/certstream-server) (343 stars, last updated February 2026) is an Elixir-based service that aggregates Certificate Transparency logs and streams new certificate entries in real time via WebSocket and TCP connections.

### Architecture

Certstream connects to multiple CT log sources simultaneously, deduplicates entries, and broadcasts them to connected clients. Clients can subscribe to specific domain patterns using regex filters, reducing bandwidth and processing requirements.

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  certstream-server:
    image: calidog/certstream-server:latest
    container_name: certstream-server
    restart: unless-stopped
    ports:
      - "6470:6470"    # TCP port for raw certificate data
      - "6471:6471"    # WebSocket port for browser clients
    environment:
      - CERTSTREAM_LOG_LEVEL=info
    volumes:
      - ./config:/etc/certstream
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6471"]
      interval: 30s
      timeout: 10s
      retries: 3

  certstream-client:
    image: python:3.11-slim
    container_name: certstream-client
    restart: unless-stopped
    depends_on:
      - certstream-server
    command: >
      bash -c "
        pip install certstream &&
        python -c \"
        import certstream, json, re

        # Domain patterns to monitor
        PATTERNS = [r'\.example\.com$', r'\.example\.org$']

        def handle_message(context, message):
            if message.get('message_type') == 'certificate_update':
                leaf = message.get('data', {}).get('leaf_cert', {})
                san = leaf.get('extensions', {}).get('subject_alternative_name', [])
                for domain in san:
                    for pattern in PATTERNS:
                        if re.search(pattern, domain):
                            alert = {
                                'domain': domain,
                                'issuer': leaf.get('issuer', 'Unknown'),
                                'not_before': leaf.get('validity', {}).get('not_before', ''),
                                'not_after': leaf.get('validity', {}).get('not_after', ''),
                            }
                            print(json.dumps(alert, indent=2))
                            # Add webhook/Slack/email notification here

        certstream.listen_for_events(handle_message, url='ws://certstream-server:6471/')
        \"
      "
    volumes:
      - ./config:/config
```

### Client Library Usage

Certstream provides client libraries for Python, Node.js, and Ruby. The Python client is the most widely used:

```bash
pip install certstream
```

```python
import certstream
import re

# Monitor for certificates matching your domains
DOMAIN_PATTERNS = [
    r'\.yourdomain\.com$',
    r'\.yourdomain\.org$',
    r'\.yourcompany\..*$',
]

def cert_callback(context, message):
    if message.get('message_type') == 'certificate_update':
        leaf_cert = message.get('data', {}).get('leaf_cert', {})
        sans = leaf_cert.get('extensions', {}).get('subject_alternative_name', [])

        for san in sans:
            for pattern in DOMAIN_PATTERNS:
                if re.search(pattern, san):
                    print(f"[ALERT] Certificate detected: {san}")
                    print(f"  Issuer: {leaf_cert.get('issuer', 'Unknown')}")
                    print(f"  Valid: {leaf_cert.get('validity', {}).get('not_before', '')} "
                          f"→ {leaf_cert.get('validity', {}).get('not_after', '')}")

certstream.listen_for_events(cert_callback, url='ws://certstream-server:6471/')
```

## SSLMate Certspotter: Lightweight CT Log Monitor

[SSLMate Certspotter](https://github.com/SSLMate/certspotter) (1,138 stars, last updated January 2026) is a Go-based CT log monitor developed by SSLMate. It watches CT logs for certificates matching a configured list of domains and sends webhook notifications when matches are found.

### Key Features

- Monitors Google's CT logs by default
- Supports domain-based filtering via a JSON configuration file
- Sends webhook alerts on certificate matches
- Lightweight binary (~15MB) with minimal dependencies
- Can run as a systemd service or Docker container

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  certspotter:
    image: ssllabs/certspotter:latest
    container_name: certspotter
    restart: unless-stopped
    volumes:
      - ./config:/etc/certspotter
      - ./data:/var/lib/certspotter
    command: >
      -config /etc/certspotter/config.json
      -watch
    environment:
      - WEBHOOK_URL=http://your-alert-service:8080/webhook

# Alternative: run with explicit domain list
# certspotter -config /etc/certspotter/config.json -watch
```

Configuration file (`config.json`):

```json
{
  "domain": ["example.com", "example.org"],
  "include_subdomains": true,
  "webhook_url": "http://your-alert-service:8080/webhook",
  "data_dir": "/var/lib/certspotter"
}
```

### Standalone Installation

```bash
# Download the latest release
curl -sL https://github.com/SSLMate/certspotter/releases/latest/download/certspotter-linux-amd64 \
  -o /usr/local/bin/certspotter
chmod +x /usr/local/bin/certspotter

# Create config directory
mkdir -p /etc/certspotter /var/lib/certspotter

# Create config
cat > /etc/certspotter/config.json << 'CONF'
{
  "domain": ["example.com"],
  "include_subdomains": true,
  "webhook_url": "http://localhost:8080/webhook"
}
CONF

# Run in watch mode
certspotter -config /etc/certspotter/config.json -watch
```

## ct_monitor: crt.sh-Based Certificate Monitoring

[ct_monitor](https://github.com/crtsh/ct_monitor) (453 stars, last updated April 2026) is a Go-based CT log monitor that queries the crt.sh API — a public search interface for Certificate Transparency logs operated by Sectigo. Unlike streaming tools, ct_monitor polls the crt.sh API at configurable intervals.

### Key Features

- Queries crt.sh API instead of connecting to raw CT logs
- Simpler architecture — no need to maintain CT log connections
- Lower resource requirements — runs on a single API query loop
- Ideal for monitoring a small set of domains without real-time streaming needs
- Actively maintained (updated April 2026)

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  ct-monitor:
    image: ghcr.io/crtsh/ct_monitor:latest
    container_name: ct-monitor
    restart: unless-stopped
    environment:
      - CT_MONITOR_DOMAINS=example.com,example.org
      - CT_MONITOR_INTERVAL=300
      - CT_MONITOR_LOG_LEVEL=info
    volumes:
      - ./config:/config
      - ./data:/data
    command: ["--config", "/config/domains.txt", "--interval", "300"]

  # Optional: webhook receiver for alerts
  alert-receiver:
    image: ntscloud/alertmanager:latest
    container_name: ct-alert-receiver
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager:/etc/alertmanager
```

Domain list file (`config/domains.txt`):

```
example.com
example.org
*.example.net
```

### Installation from Source

```bash
git clone https://github.com/crtsh/ct_monitor.git
cd ct_monitor
go build -o ct_monitor ./cmd/ct_monitor

# Create domain list
cat > domains.txt << 'EOF'
example.com
example.org
*.example.net
EOF

# Run with 5-minute polling interval
./ct_monitor --config domains.txt --interval 300 --verbose
```

## Setting Up Alerting with Prometheus and Alertmanager

Regardless of which CT monitoring tool you choose, integrating with Prometheus and Alertmanager provides reliable, configurable alerting. Here's a reference setup:

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: ct-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  alertmanager:
    image: prom/alertmanager:latest
    container_name: ct-alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml

volumes:
  prometheus_data:
```

Prometheus configuration (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'certstream'
    static_configs:
      - targets: ['certstream-client:9090']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['ct-alertmanager:9093']
```

Alertmanager configuration (`alertmanager.yml`):

```yaml
route:
  receiver: 'slack-alerts'
  group_by: ['alertname']
  group_wait: 1m
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#cert-alerts'
        title: 'Certificate Alert: {{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          Domain: {{ .Labels.domain }}
          Issuer: {{ .Labels.issuer }}
          Not After: {{ .Labels.not_after }}
          {{ end }}
```

## Choosing the Right Tool

**Choose Certstream Server if:**
- You need real-time streaming of all CT log entries
- You want to build a custom filtering pipeline on top of raw certificate data
- You have the infrastructure to run an Elixir service with WebSocket clients
- You want to monitor multiple domain patterns with regex flexibility

**Choose SSLMate Certspotter if:**
- You need a lightweight, single-binary solution
- Your primary goal is monitoring a specific set of domains
- You want simple webhook-based alerting
- You prefer Go-based tools with minimal dependencies

**Choose ct_monitor if:**
- You want the simplest deployment — just poll the crt.sh API
- You have a small number of domains to monitor
- You don't need sub-second real-time detection
- You prefer actively maintained, regularly updated software

For organizations monitoring hundreds or thousands of domains, Certstream Server's streaming architecture provides the most scalable foundation. For small teams monitoring a handful of critical domains, Certspotter or ct_monitor offer simpler, lighter-weight alternatives.

## FAQ

### What is Certificate Transparency and why does it matter?

Certificate Transparency (CT) is a framework that makes TLS certificate issuance publicly auditable. Every certificate issued by a trusted CA must be logged in a public CT log before browsers will trust it. This prevents rogue CAs from secretly issuing certificates for domains they don't own, and allows domain owners to detect unauthorized certificates immediately.

### How fast can I detect a rogue certificate with self-hosted monitoring?

With Certstream Server's WebSocket streaming, you can detect new certificates within seconds of them being submitted to CT logs. Certspotter and ct_monitor use polling approaches, which typically detect new certificates within 1-5 minutes depending on their polling interval. The actual CT log submission delay from the CA is usually under 60 seconds.

### Do I need to monitor all CT logs or just some of them?

You should monitor multiple CT logs because CAs submit to different log sets. Google operates several logs, Cloudflare operates Nimbus logs, and various other operators run their own. Certstream Server can connect to multiple logs simultaneously. Certspotter monitors Google's CT log ecosystem by default. ct_monitor uses crt.sh, which aggregates entries from many CT logs into a single queryable database.

### Can I use CT monitoring to discover all subdomains of my organization?

Yes. Certificate Subject Alternative Names (SANs) often reveal subdomains that aren't publicly listed in DNS. By filtering CT log entries for your root domain, you can discover all subdomains that have received TLS certificates. This is a common reconnaissance technique used by security teams for asset discovery.

### Is CT monitoring a replacement for certificate expiry monitoring?

No — these serve different purposes. CT monitoring detects **new** certificates being issued (rogue certificates, phishing domains). Certificate expiry monitoring tracks when your **existing** certificates are about to expire to prevent outages. Both are essential for a complete TLS security posture. For certificate expiry monitoring, consider tools like [x509-certificate-exporter or Certimate](../self-hosted-certificate-monitoring-expiry-alerting-certimate-x509-exporter-certspotter-guide-2026/).

### How do I set up alerts for CT monitoring?

The most common approach is to configure a webhook receiver that triggers notifications via Slack, email, PagerDuty, or other alerting channels. Certstream Server's client libraries support custom callbacks where you can add notification logic. Certspotter has built-in webhook support. For production environments, integrating with Prometheus Alertmanager provides configurable alert routing, deduplication, and escalation policies.

### Can CT monitoring detect wildcard certificates issued for my domain?

Yes. When a wildcard certificate (e.g., `*.example.com`) is issued, it appears in CT logs with the wildcard domain in the Subject Alternative Names list. Your monitoring tool's domain filter will match it, and you'll receive an alert. This is particularly useful for detecting unauthorized wildcard certificates that could be used to impersonate any subdomain.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Certstream vs Certspotter vs ct_monitor: Self-Hosted Certificate Transparency Monitoring Guide 2026",
  "description": "Compare self-hosted Certificate Transparency monitoring tools — Certstream Server, SSLMate Certspotter, and ct_monitor — with Docker setups, alerting rules, and deployment guides for detecting rogue TLS certificates.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
