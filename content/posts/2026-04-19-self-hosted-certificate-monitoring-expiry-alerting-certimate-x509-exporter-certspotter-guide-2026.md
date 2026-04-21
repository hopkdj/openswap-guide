---
title: "Self-Hosted Certificate Monitoring 2026: Certimate vs x509-Certificate-Exporter vs CertSpotter"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "security", "certificates", "monitoring"]
draft: false
description: "Compare the best open-source tools for self-hosted SSL/TLS certificate monitoring, expiry alerting, and Certificate Transparency tracking. Complete guide to Certimate, x509-certificate-exporter, and CertSpotter."
---

Managing SSL/TLS certificates across multiple servers, domains, and services is one of the most common operational challenges for self-hosters and system administrators. An expired certificate means downtime, broken APIs, and lost trust — yet it remains one of the most preventable outages.

While [certificate automation tools](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/) handle issuance and renewal, you also need visibility: which certificates are deployed, where they are, when they expire, and whether unexpected certificates have been issued for your domains.

This guide compares three mature open-source tools for self-hosted certificate monitoring, each taking a different approach to the problem.

## Why Self-Host Certificate Monitoring

Cloud-based certificate monitoring services exist, but self-hosting gives you advantages that matter for security-conscious teams:

- **No credential exposure** — you do not hand over domain lists or certificate details to a third party
- **Internal certificate coverage** — monitor private CAs, internal PKI, and localhost services that external scanners cannot reach
- **Unlimited scale** — no per-domain pricing tiers or scan frequency limits
- **Compliance** — keep certificate audit data on-premises for regulatory requirements
- **Integration** — feed monitoring data directly into your existing [prometheus](https://prometheus.io/), Grafana, or notification stack

## Tools Compared at a Glance

| Feature | Certimate | x509-Certificate-Exporter | CertSpotter |
|---|---|---|---|
| **Primary Focus** | Full certificate lifecycle management | Prometheus-based expiry monitoring | Certificate Transparency log monitoring |
| **Stars** | 8,540+ | 874+ | 1,137+ |
| **Language** | Go | Go | Go |
| **Web UI** | Yes (built-in) | No (Grafana dashboards) | No (CLI/email alerts) |
| **Certificate Issuance** | Yes (ACME) | No | No |
| **Certificate Deployment** | Yes (120+ targets) | No | No |
| **Expiry Monitoring** | Yes | Yes (Prometheus metrics) | No |
| **CT Log Monitoring** | No | No | Yes |
| **[kubernetes](https://kubernetes.io/) Support** | Yes | Yes (native, via Helm) | No |
| **Multi-Cloud DNS** | 60+ providers | N/A | N/A |
| **Notification Channels** | Built-in alerts | Prometheus Alertmanager | Email, webhook scripts |
| **Best For** | Teams wanting an all-in-one certificate platform | Prometheus/Grafana users | Security teams detecting rogue certificates |

## Certimate: All-in-One Certificate Lifecycle Platform

[Certimate](https://github.com/certimate-go/certimate) is the most feature-complete option. It handles the entire certificate workflow — from requesting Let's Encrypt (or other ACME) certificates, to deploying them across cloud providers, to monitoring expiration dates through a built-in web interface.

### Key Features

- **Visual certificate management** — manage all certificates from a single web dashboard
- **Automated renewal** — ACME protocol support with automatic renewal before expiry
- **Multi-provider deployment** — deploy certificates to 120+ targets including Kubernetes, CDN, WAF, and load balancers
- **DNS challenge support** — 60+ DNS providers for wildcard certificate validation (Cloudflare, AWS Route 53, GoDaddy, Alibaba Cloud, Tencent Cloud, and more)
- **Multiple certificate formats** — PEM, PFX, JKS support
- **Zero external dependencies** — single binary with embedded database (PocketBase)

### [docker](https://www.docker.com/) Deployment

Certimate ships as a single container with everything included:

```yaml
version: "3.0"
services:
  certimate:
    image: certimate/certimate:latest
    container_name: certimate
    ports:
      - "8090:8090"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
      - ./data:/app/pb_data
    restart: unless-stopped
```

Or run it directly with Docker:

```bash
docker run -d \
  --name certimate \
  --restart unless-stopped \
  -p 8090:8090 \
  -v /etc/localtime:/etc/localtime:ro \
  -v /etc/timezone:/etc/timezone:ro \
  -v $(pwd)/data:/app/pb_data \
  certimate/certimate:latest
```

After starting, open `http://your-server:8090` in your browser. The first run creates an admin account. From there you can add domains, configure DNS providers for challenge validation, set deployment targets, and monitor certificate expiration dates.

### When to Choose Certimate

Choose Certimate when you need a unified platform that handles both certificate management and monitoring. It is ideal for teams managing certificates across multiple cloud providers who want visual oversight of their entire certificate inventory. The built-in web UI eliminates the need for separate monitoring dashboards.

## x509-Certificate-Exporter: Prometheus-Native Certificate Monitoring

The [x509-Certificate-Exporter](https://github.com/enix/x509-certificate-exporter) by Enix takes a focused approach: expose certificate expiration data as Prometheus metrics, then let your existing alerting infrastructure handle notifications.

### Key Features

- **Prometheus metrics** — standard `x509_cert_not_after`, `x509_cert_not_before`, `x509_cert_expired` metrics
- **Kubernetes-native** — monitor TLS secrets, kubeconfigs, and embedded certificates directly from the API server
- **File-based monitoring** — scan PEM files on disk or entire directories for certificates
- **Relative time metrics** — `x509_cert_expires_in_seconds` for efficient Prometheus storage
- **Grafana dashboard** — pre-built [dashboard #13922](https://grafana.com/grafana/dashboards/13922) for visualization
- **Helm chart** — one-command deployment on Kubernetes

### Docker Deployment

Run as a standalone exporter to monitor certificates on a single host:

```bash
docker run -d \
  --name x509-certificate-exporter \
  -p 9793:9793 \
  -v /etc/ssl/certs:/etc/ssl/certs:ro \
  -v /etc/pki/tls:/etc/pki/tls:ro \
  -v /etc/nginx/ssl:/etc/nginx/ssl:ro \
  enix/x509-certificate-exporter \
  --dir /etc/ssl/certs \
  --dir /etc/pki/tls \
  --dir /etc/nginx/ssl
```

For Kubernetes, install via Helm for full feature support:

```bash
helm repo add enix https://charts.enix.io
helm install x509-certificate-exporter enix/x509-certificate-exporter \
  --namespace monitoring \
  --create-namespace \
  --set watchKubeSecrets.enabled=true \
  --set directories[0].path=/etc/ssl/certs
```

### Prometheus Alert Rules

Configure alerting directly in Prometheus to get notified before certificates expire:

```yaml
groups:
  - name: certificate-alerts
    rules:
      - alert: CertificateRenewal
        annotations:
          summary: Certificate should be renewed
          description: >-
            Certificate for "{{ $labels.subject_CN }}" should be renewed
            {{if $labels.secret_name }}in Kubernetes secret "{{ $labels.secret_namespace }}/{{ $labels.secret_name }}"{{else}}at location "{{ $labels.filepath }}"{{end}}
        expr: ((x509_cert_not_after - time()) / 86400) < 28
        for: 15m
        labels:
          severity: warning

      - alert: CertificateExpiration
        annotations:
          summary: Certificate is about to expire
          description: >-
            Certificate for "{{ $labels.subject_CN }}" is about to expire
            {{if $labels.secret_name }}in Kubernetes secret "{{ $labels.secret_namespace }}/{{ $labels.secret_name }}"{{else}}at location "{{ $labels.filepath }}"{{end}}
        expr: ((x509_cert_not_after - time()) / 86400) < 14
        for: 15m
        labels:
          severity: critical

      - alert: X509ExporterReadErrors
        annotations:
          summary: Increasing read errors for x509-certificate-exporter
          description: The exporter has experienced errors reading certificate files or querying the Kubernetes API over the last 15 minutes.
        expr: delta(x509_read_errors[15m]) > 0
        for: 5m
        labels:
          severity: warning
```

### When to Choose x509-Certificate-Exporter

Choose this tool when you already run Prometheus and Grafana. It integrates seamlessly into existing monitoring stacks and provides Kubernetes-native certificate visibility with minimal configuration. The Helm chart deployment makes it operational in minutes on any cluster.

## CertSpotter: Certificate Transparency Log Monitoring

[CertSpotter](https://github.com/SSLMate/certspotter) by SSLMate serves a different purpose: it monitors public Certificate Transparency (CT) logs to detect when new certificates are issued for your domains. This is a security-focused tool designed to catch rogue certificates, misissued certificates, or certificates issued by attackers who have compromised your DNS.

### Key Features

- **CT log monitoring** — watches all public CT logs for certificates matching your domains
- **No database required** — simpler architecture than other CT monitors
- **Robust certificate parsing** — specialized parser that avoids missing certificates
- **Email alerts** — instant notification when a new certificate appears
- **Webhook integration** — trigger custom scripts on new certificate detection
- **Domain tree monitoring** — use `.example.com` syntax to monitor a domain and all subdomains

### Installation and Setup

Install CertSpotter using Go:

```bash
go install software.sslmate.com/src/certspotter/cmd/certspotter@latest
```

Create a watchlist file at `$HOME/.certspotter/watchlist`:

```
example.com
.example.com
api.example.com
```

Prefix a domain with a dot (`.example.com`) to monitor the domain and all subdomains. Without the dot, only that exact hostname is monitored.

Configure email recipients in `$HOME/.certspotter/email_recipients`:

```
admin@example.com
security@example.com
```

Run CertSpotter as a background service:

```bash
certspotter --watch
```

For production deployment, run it as a systemd service:

```ini
[Unit]
Description=CertSpotter CT Log Monitor
After=network.target

[Service]
Type=simple
User=certspotter
Group=certspotter
ExecStart=/usr/local/bin/certspotter --watch
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable certspotter
sudo systemctl start certspotter
sudo systemctl status certspotter
```

### When to Choose CertSpotter

Choose CertSpotter for security monitoring, not expiration tracking. It detects unauthorized certificate issuance — for example, if an attacker compromises your DNS and requests a certificate for your domain, CertSpotter will alert you within minutes of the certificate appearing in a CT log. This is complementary to expiration monitoring, not a replacement for it.

## Comparison: Three Different Approaches

These tools solve different parts of the certificate management puzzle:

**Certimate** is for operators who need a centralized platform to request, deploy, and monitor certificates. It replaces manual certificate workflows with automated pipelines and visual dashboards.

**x509-Certificate-Exporter** is for infrastructure teams who already use Prometheus. It provides certificate visibility through metrics, enabling alerting on any timescale (30 days, 14 days, 7 days) with the flexibility of PromQL queries.

**CertSpotter** is for security teams who need to detect unauthorized certificate issuance. By monitoring CT logs, it catches certificates that were issued without your knowledge — an entirely different threat model from expiration.

## Recommended Architecture

For comprehensive certificate management, combine tools based on your needs:

```
┌─────────────────────────────────────────────────┐
│              Certificate Management              │
│                                                  │
│  Certimate                                       │
│  ┌─────────────────────────────────────────┐    │
│  │  Issue → Deploy → Monitor → Renew       │    │
│  │  (Web UI, ACME, 120+ targets)           │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│              Expiry Monitoring                   │
│                                                  │
│  x509-Certificate-Exporter                       │
│  ┌─────────────────────────────────────────┐    │
│  │  Scan certs → Prometheus → Grafana      │    │
│  │  (K8s secrets, PEM files, kubeconfigs)  │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│            Security Detection                    │
│                                                  │
│  CertSpotter                                     │
│  ┌─────────────────────────────────────────┐    │
│  │  CT Logs → Watchlist → Email/Webhook    │    │
│  │  (Rogue cert detection)                 │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

Most self-hosters benefit from running Certimate for lifecycle management and x509-Certificate-Exporter for expiry monitoring. Add CertSpotter if you manage public-facing domains and want CT log surveillance.

## Deployment Best Practices

### Run the Exporter on Every Node

For x509-certificate-exporter, deploy one instance per Kubernetes node using a DaemonSet. This ensures all node-local certificates are monitored, including those in `/etc/kubernetes/pki` and other system directories.

### Monitor Both Public and Internal Certificates

Use Certimate for public-facing ACME certificates and x509-certificate-exporter for internal PKI certificates issued by your private CA (such as [step-ca](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/)). Internal certificates are the most likely to expire unnoticed since they are not validated by browsers.

### Set Tiered Alerting Thresholds

Configure alerts at multiple intervals:

| Days Before Expiry | Alert Level | Action |
|---|---|---|
| 30 days | Warning | Schedule renewal, investigate automated renewal failure |
| 14 days | Critical | Escalate to on-call, manual renewal if automation failed |
| 7 days | Emergency | Immediate action required, incident ticket |
| 3 days | Outage imminent | Service disruption expected without intervention |

### Test Alert Delivery

After deploying monitoring, deliberately test your alert pipeline. Expire a test certificate or configure an alert threshold that triggers immediately. Verify notifications arrive at the correct channels (email, Slack, PagerDuty).

## FAQ

### What is the difference between certificate monitoring and Certificate Transparency monitoring?

Certificate monitoring tracks the expiration dates of certificates you already own and have deployed. Certificate Transparency (CT) monitoring watches public logs for any new certificates issued for your domains — including ones you did not request. CT monitoring is a security practice; expiration monitoring is an operational practice.

### Can I use x509-certificate-exporter without Kubernetes?

Yes. The exporter works as a standalone binary or Docker container. Use the `--dir` flag to specify directories containing PEM-encoded certificates, or the `--file` flag to monitor individual certificate files. Kubernetes support is an additional feature, not a requirement.

### Does Certimate support wildcard certificates?

Yes. Certimate supports wildcard certificates through DNS-01 ACME challenges. It integrates with over 60 DNS providers including Cloudflare, AWS Route 53, Google Cloud DNS, GoDaddy, and many more for automated DNS challenge validation.

### How does CertSpotter detect rogue certificates?

CertSpotter monitors all public Certificate Transparency logs. Whenever a Certificate Authority issues a certificate, it must log it in a CT log within 24 hours. CertSpotter watches these logs in real time and alerts you when it finds a certificate matching a domain on your watchlist. If you did not request that certificate, it is potentially rogue.

### Which tool should I use if I only want to track certificate expiration dates?

If you run Prometheus, use x509-certificate-exporter — it integrates directly into your existing alerting pipeline. If you want a standalone web UI without Prometheus, use Certimate. Both tools track expiration, but they serve different operational workflows.

### Can these tools monitor certificates inside Docker containers?

x509-certificate-exporter can monitor certificates by mounting container volumes or scanning directories on the host. Certimate monitors certificates that it manages through its deployment pipeline. Neither tool inspects running containers directly, but you can point the exporter at the certificate paths that containers mount from the host.

### Is CertSpotter still actively maintained?

CertSpotter's last update was in early 2026. The core functionality is stable since CT log monitoring is a well-defined protocol. For active development and new features, Certimate (updated weekly) and x509-certificate-exporter (updated monthly) are more actively maintained.

## Conclusion

Certificate expiration is one of the most preventable — yet most common — causes of self-hosted service outages. The right monitoring tool depends on your existing infrastructure:

- **Certimate** for teams wanting a complete certificate lifecycle platform with a web UI
- **x509-Certificate-Exporter** for Prometheus and Grafana users who want metrics-driven alerting
- **CertSpotter** for security teams monitoring Certificate Transparency logs for unauthorized certificates

All three tools are open source, self-hosted, and free to use. Running any of them is significantly better than relying on manual tracking or email reminders from your domain registrar.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Certificate Monitoring 2026: Certimate vs x509-Certificate-Exporter vs CertSpotter",
  "description": "Compare the best open-source tools for self-hosted SSL/TLS certificate monitoring, expiry alerting, and Certificate Transparency tracking. Complete guide to Certimate, x509-certificate-exporter, and CertSpotter.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
