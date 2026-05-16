---
title: "Self-Hosted Mail Server Health Monitoring: postfix-exporter vs swaks vs Mailu Health Checks"
date: "2026-05-16"
tags: ["email", "monitoring", "mail-server", "postfix", "prometheus", "health-check"]
draft: false
---

Self-hosted email infrastructure requires continuous health monitoring to ensure reliable message delivery. A failing mail server can silently drop messages, cause bounce storms, or become an open relay. Unlike web applications where a down server is immediately obvious, mail server degradation can go unnoticed for hours or days until users start reporting missing messages.

This guide covers three approaches to monitoring mail server health: **postfix-exporter** for Prometheus-based metric collection, **swaks** for active SMTP health checks and transaction testing, and **Mailu's built-in health endpoints** for containerized mail suite monitoring. Each serves a different monitoring philosophy — passive metrics, active probing, and suite-level health checks.

## postfix-exporter for Prometheus

The postfix-exporter scrapes Postfix log files and queue statistics, exposing them as Prometheus metrics. It provides passive, real-time visibility into mail flow, queue health, and delivery success rates without modifying Postfix configuration.

### Key Features

- Parses Postfix syslog output in real time using tail-based log monitoring
- Exposes queue length, message delivery rates, and bounce counts as Prometheus metrics
- Tracks sender/recipient domain statistics for delivery pattern analysis
- Supports both systemd journal and traditional syslog file input
- Lightweight Go binary with minimal resource overhead
- Pre-built Grafana dashboards for Postfix operational visibility

### Architecture

The exporter tails the Postfix log file (typically `/var/log/mail.log`) or reads from the systemd journal via `journalctl`. It parses log lines using regex patterns matching Postfix's structured log format, extracts metrics like message IDs, queue actions, delivery status codes, and timing information, then exposes them on an HTTP endpoint for Prometheus to scrape.

```yaml
# docker-compose.yml - Postfix with postfix-exporter
version: "3.8"
services:
  postfix:
    image: mailserver/postfix:latest
    container_name: postfix
    hostname: mail.example.com
    ports:
      - "25:25"
      - "587:587"
    environment:
      MAILNAME: mail.example.com
      POSTFIX_INET_PROTOCOLS: ipv4
    volumes:
      - postfix_data:/var/spool/postfix
      - ./postfix-config/main.cf:/etc/postfix/main.cf:ro
      - /var/log/mail.log:/var/log/mail.log
    restart: unless-stopped

  postfix-exporter:
    image: kumina/postfix_exporter:latest
    container_name: postfix-exporter
    ports:
      - "9154:9154"
    volumes:
      - /var/log/mail.log:/var/log/mail.log:ro
    command:
      - "--postfix.logfile_path=/var/log/mail.log"
      - "--web.listen-address=:9154"
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    depends_on:
      - postfix-exporter
    restart: unless-stopped

volumes:
  postfix_data:
```

### Prometheus Scrape Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: "postfix"
    static_configs:
      - targets: ["postfix-exporter:9154"]
    metrics_path: /metrics
```

### Key Metrics Exposed

- `postfix_smtpd_connections_total` — Total SMTP connections received
- `postfix_smtpd_connect_duration_seconds` — Connection setup latency
- `postfix_sendmail_responses_total` — Messages submitted to the queue
- `postfix_smtp_messages_delivered_total` — Successfully delivered messages
- `postfix_smtp_deferred_messages_total` — Deferred (temp-failed) messages
- `postfix_bounce_messages_total` — Bounce messages generated
- `postfix_cleanup_messages_received_total` — Messages entering the cleanup daemon
- `postfix_qmgr_messages_removed_total` — Messages leaving the queue manager

## swaks — Active SMTP Health Testing

swaks (SWiss Army Knife for SMTP) is a command-line SMTP testing tool that can perform active health checks against mail servers. Unlike passive monitoring, swaks initiates real SMTP transactions to verify that your server is accepting connections, responding correctly, and processing messages end-to-end.

### Key Features

- Full SMTP transaction testing: EHLO, AUTH, MAIL FROM, RCPT TO, DATA, QUIT
- TLS/STARTTLS connection testing with certificate validation
- SMTP authentication testing (PLAIN, LOGIN, CRAM-MD5)
- Configurable timeouts and expected response code validation
- Scriptable for automated health check pipelines
- Supports submission port (587) and implicit TLS (465) testing
- Can simulate different sender/recipient combinations

### Architecture

swaks operates as a standalone command-line tool, not a daemon or exporter. It is typically run on a schedule (via cron or a monitoring system's active check feature) to probe mail server endpoints. The tool connects to the SMTP server, negotiates the session, sends test commands, and reports whether each step succeeded or failed with the expected response code.

```bash
#!/bin/bash
# smtp_health_check.sh — Active SMTP health monitoring script

MAIL_SERVER="mail.example.com"
PORT=587
LOG_FILE="/var/log/smtp-health.log"

echo "[$(date)] Testing SMTP health on $MAIL_SERVER:$PORT" >> "$LOG_FILE"

# Test basic connectivity and EHLO
if swaks --to test@$MAIL_SERVER --from monitor@$MAIL_SERVER     --server "$MAIL_SERVER" --port "$PORT"     --tls --auth --auth-user monitor --auth-password secret     --quit-after "RCPT" 2>&1 | grep -q "250 OK"; then
    echo "[$(date)] SMTP health check PASSED" >> "$LOG_FILE"
else
    echo "[$(date)] SMTP health check FAILED" >> "$LOG_FILE"
    # Trigger alerting via webhook, email, or pager
    curl -s -X POST https://alerts.example.com/webhook         -H "Content-Type: application/json"         -d '{"service":"smtp","status":"down","host":"'"$MAIL_SERVER"'"}'
fi
```

### Automated Cron-Based Health Checks

```bash
# /etc/cron.d/smtp-health-check — Run every 5 minutes
*/5 * * * * root /usr/local/bin/smtp_health_check.sh

# Test STARTTLS on port 25
*/5 * * * * root swaks --to monitor@example.com --from monitor@example.com     --server localhost --port 25 --tls --quit-after RCPT     2>&1 | grep -q "250" || /usr/local/bin/alert-smtp-down.sh
```

swaks is complementary to the postfix-exporter: the exporter provides passive metrics, while swaks provides active probes that confirm the server is responding correctly to real SMTP clients.

## Mailu Health Check Endpoints

Mailu is a full-featured self-hosted mail suite (SMTP, IMAP, webmail, admin) that includes built-in health check endpoints for each component. These endpoints return HTTP status codes and JSON health data, making them ideal for Docker health checks, Kubernetes liveness/readiness probes, and load balancer health monitoring.

### Key Features

- Per-component HTTP health endpoints (`/api/v1/health`)
- Docker HEALTHCHECK integration for automatic container restart on failure
- Kubernetes liveness and readiness probe compatibility
- Database connectivity verification
- SMTP and IMAP service status reporting
- Redis and Antispam component health verification
- JSON-formatted health data for programmatic parsing

### Architecture

Mailu runs each mail server component (Postfix, Dovecot, Rspamd, Admin) as a separate container. Each component exposes a health endpoint on its admin API. The admin container aggregates health status from all components and provides a unified health dashboard.

```yaml
# docker-compose.yml - Mailu with Health Checks
version: "3.8"
services:
  admin:
    image: mailu/admin:2.0
    container_name: mailu-admin
    ports:
      - "8080:8080"
    environment:
      ADMIN_SECRET: changeme
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: unless-stopped

  postfix:
    image: mailu/postfix:2.0
    container_name: mailu-postfix
    ports:
      - "25:25"
      - "587:587"
    environment:
      HOSTNAME: mail.example.com
    healthcheck:
      test: ["CMD", "swaks", "--to", "test@localhost", "--server", "localhost", "--quit-after", "RCPT"]
      interval: 60s
      timeout: 10s
      retries: 3
    depends_on:
      - admin
    restart: unless-stopped

  dovecot:
    image: mailu/dovecot:2.0
    container_name: mailu-dovecot
    ports:
      - "110:110"
      - "143:143"
      - "993:993"
    healthcheck:
      test: ["CMD", "doveadm", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
    depends_on:
      - admin
    restart: unless-stopped
```

## Comparison Table

| Feature | postfix-exporter | swaks | Mailu Health Checks |
|---------|-----------------|-------|---------------------|
| **Type** | Passive metrics exporter | Active SMTP testing tool | Built-in health endpoints |
| **Monitoring mode** | Continuous (tail/parse logs) | On-demand (per invocation) | Continuous (HTTP endpoint) |
| **Prometheus integration** | Yes (native) | No (scripted) | No (HTTP status only) |
| **Alerting support** | Yes (via Alertmanager) | Yes (via script exit codes) | Yes (via container restart) |
| **SMTP transaction testing** | No | Yes (full transaction) | Limited (basic check) |
| **TLS testing** | No | Yes | No |
| **Queue depth monitoring** | Yes | No | No |
| **Delivery rate tracking** | Yes | No | No |
| **Multi-server support** | Yes (per-server exporter) | Yes (target parameter) | Per-component only |
| **Setup complexity** | Medium | Low | Low (built-in) |
| **Works with standalone Postfix** | Yes | Yes | No (Mailu only) |
| **GitHub stars** | ~130 (kumina) | ~700 (mueland) | ~1,200+ (Mailu org) |

## Building a Complete Mail Server Health Monitoring Stack

For production mail server monitoring, combine all three approaches:

1. **postfix-exporter + Prometheus + Grafana** — for continuous passive monitoring of mail flow, queue health, and delivery metrics. Set up dashboards showing message rates, bounce ratios, and queue depth over time.

2. **swaks via cron or monitoring system** — for active health checks that verify the SMTP server is accepting connections, negotiating TLS, and responding to client commands. Use these as canary probes from external monitoring locations.

3. **Mailu health endpoints** — for container-level health management. Docker and Kubernetes will automatically restart unhealthy containers based on health check results, providing self-healing infrastructure.

## Why Self-Host Mail Server Monitoring?

Mail delivery is critical infrastructure. Self-hosted monitoring gives you:

- **Immediate detection** of mail queue buildup before messages bounce or get rejected
- **Delivery rate tracking** to spot ISP blacklisting or rate limiting before users complain
- **TLS verification** to ensure encrypted connections are working correctly
- **Authentication monitoring** to detect credential abuse or open relay misconfigurations
- **Compliance logging** for audit trails of all monitoring probes and health checks
- **Cost control** — commercial email monitoring services charge per mailbox; self-hosted scales freely

For broader mail infrastructure monitoring, our [SMTP bounce management guide](../2026-05-24-self-hosted-email-bounce-management-postal-stalwart-haraka-guide/) covers how to handle delivery failures, and our [email authentication deep dive](../2026-05-18-self-hosted-email-authentication-opendkim-rspamd-opendmarc-guide/) ensures your SPF, DKIM, and DMARC records are correctly configured. If you're managing mail delivery agents, our [LDA comparison](../2026-05-13-self-hosted-mail-delivery-agents-dovecot-lda-maildrop-guide/) complements this monitoring guide.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Server Health Monitoring",
  "description": "Monitor mail server health with postfix-exporter for Prometheus metrics, swaks for active SMTP testing, and Mailu health endpoints for container-level monitoring.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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

## FAQ

### What is the difference between passive and active mail server monitoring?

Passive monitoring (postfix-exporter) observes existing mail traffic by parsing logs and metrics. Active monitoring (swaks) initiates test SMTP transactions to verify the server responds correctly. Both are needed: passive monitoring catches real problems, active monitoring catches problems before real users are affected.

### How often should I run swaks health checks?

Every 5 minutes is a good balance between responsiveness and server load. For critical production servers, reduce to every 2-3 minutes. Avoid running faster than every minute, as repeated connections from the same source IP may trigger rate limiting or abuse detection.

### Can I use postfix-exporter with mail servers other than Postfix?

No. The postfix-exporter is specifically designed to parse Postfix log format. For Exim monitoring, use the exim-exporter. For Haraka, use the haraka-prometheus-stats plugin. Each MTA has different log formats requiring different parsers.

### What Prometheus alert thresholds should I set for Postfix?

Recommended alerts: queue depth > 500 messages for 10 minutes (warning), bounce rate > 20% over 1 hour (warning), zero deliveries in 30 minutes (critical), connection rate spike > 3x normal (warning — possible abuse), and deferred rate > 50% (warning — possible upstream issues).

### Does Mailu's health check monitor individual mailboxes?

No. Mailu health checks verify that the server components (Postfix, Dovecot, Rspamd) are running and accepting connections. They do not check individual mailbox storage, quota usage, or per-user delivery status. For mailbox-level monitoring, use the postfix-exporter combined with Dovecot statistics.

### How do I monitor TLS certificate expiration for my mail server?

Use a separate certificate monitoring tool like the x509-exporter or cert-exporter to track SSL certificate expiration dates for your mail server's SMTP and IMAPS ports. Set alerts at 30 days and 7 days before expiration. This is complementary to SMTP health checks, which verify TLS negotiation works but do not check certificate validity dates.
