---
title: "Self-Hosted Cron Job Monitoring: Healthchecks vs Uptime Kuma vs Prometheus 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "monitoring", "cron", "alerting"]
draft: false
description: "Compare the best self-hosted cron job monitoring tools in 2026. Healthchecks, Uptime Kuma heartbeat monitors, and Prometheus Alertmanager — with Docker setup guides and alerting configurations."
---

Cron jobs run the infrastructure: database backups, report generation, data synchronization, cleanup tasks. When they fail silently, the consequences range from stale dashboards to data loss. A dedicated cron job monitoring system sends you an alert the moment a scheduled task misses its window, so you can fix problems before they compound.

This guide compares three approaches to self-hosted cron monitoring: **Healthchecks** (a purpose-built open-source service), **Uptime Kuma** (a general monitoring platform with heartbeat support), and **Prometheus Alertmanager** (an alerting engine for teams already running Prometheus). Each has a different strengths profile, and the right choice depends on your existing infrastructure stack.

> If you are looking for tools to *schedule* and orchestrate cron jobs rather than monitor them, see our [self-hosted cron job scheduler guide](../self-hosted-cron-job-schedulers-cronicle-rundeck-go-autocomplete-guide-2026/) for a comparison of Cronicle, Rundeck, and Go-Autocomplete.

## Why Self-Hosted Cron Job Monitoring Matters

Cron is the oldest job scheduler on Unix, but it has a critical blind spot: **silence on failure**. A cron job that exits with a non-zero code or hangs indefinitely leaves no trace unless you explicitly configure output handling. On a server running dozens of cron tasks, it is easy to miss a failed backup or a stalled data import for days.

A cron monitoring service solves this with a simple heartbeat pattern:

1. Your cron job sends an HTTP request (a "ping") to the monitoring service at the end of each run
2. The service tracks whether each ping arrives within the expected window
3. If a ping is late or missing, the service sends you an alert via email, Slack, webhook, or PagerDuty

Self-hosting this service means your monitoring data never leaves your infrastructure, your alert rules are fully customizable, and you avoid the subscription costs of commercial alternatives like Dead Man's Snitch or Cronitor.io.

## Healthchecks: Purpose-Built Cron Monitoring

[Healthchecks](https://github.com/healthchecks/healthchecks) is an open-source cron monitoring service written in Python and Django. It is the most widely adopted open-source option in this category, with nearly 10,000 GitHub stars and active development. As of April 2026, the project was last updated on April 16, 2026.

### How It Works

You create a "check" in the Healthchecks web UI, which gives you a unique URL. At the end of your cron job, you `curl` that URL:

```bash
# Your cron job
0 2 * * * /usr/local/bin/backup-database.sh && curl -fsS --retry 3 https://your-healthchecks.example.com/ping/your-check-uuid
```

If Healthchecks does not receive a ping within the configured grace period, it sends an alert through your chosen channel. Healthchecks supports email, Slack, Discord, PagerDuty, webhooks, Signal, Telegram, Gotify, and more.

### Key Features

- **Heartbeat monitoring** with configurable period and grace period
- **Cron expression support** — set complex schedules like `0 2 * * 1-5` (weekdays at 2 AM)
- **Multiple ping methods** — HTTP GET/POST, email, Telegram bot
- **Check groups and tags** — organize checks by project or environment
- **Flips detection** — tracks when a check alternates between up and down
- **Calendar view** — visualize check history
- **API access** — manage checks programmatically
- **Badges** — embed status badges in README files or dashboards
- **Team management** — assign checks to different users or teams

### Docker Compose Setup

Healthchecks runs as a Django web application backed by PostgreSQL. Here is the official Docker Compose configuration:

```yaml
volumes:
  db-data:

services:
  db:
    image: postgres:16
    volumes:
      - db-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=${DB_NAME:-healthchecks}
      - POSTGRES_PASSWORD=${DB_PASSWORD:-secretpassword}

  web:
    image: healthchecks/healthchecks:latest
    env_file:
      - .env
    ports:
      - "8000:8000"
      - "2525:2525"
    depends_on:
      - db
    command: >
      bash -c 'while !</dev/tcp/db/5432; do sleep 1; done;
      uwsgi /opt/healthchecks/docker/uwsgi.ini'
```

Create a `.env` file alongside the compose file with your configuration:

```env
DB_NAME=healthchecks
DB_PASSWORD=secretpassword
SECRET_KEY=your-django-secret-key
DEBUG=False
SITE_ROOT=https://monitoring.example.com
DEFAULT_FROM_EMAIL=noreply@example.com
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=your-smtp-password
SMTPD_PORT=2525
```

For email-based pinging (your cron job sends an email instead of an HTTP request), the SMTP listener on port 2525 receives and processes incoming emails. Enable it by setting `SMTPD_PORT=2525` and mapping the port in the compose file.

### Healthchecks Pricing

Healthchecks is fully open source under the BSD 3-Clause license. The hosted version at healthchecks.io offers a free tier with 20 checks and paid plans for larger teams. Self-hosted, there are no limits on checks or users.

## Uptime Kuma: General Monitoring with Heartbeat Support

[Uptime Kuma](https://github.com/louislam/uptime-kuma) is primarily known as a self-hosted uptime monitoring dashboard, supporting 90+ monitor types including HTTP, TCP, DNS, and Docker container checks. With over 85,000 GitHub stars, it is one of the most popular self-hosted monitoring tools available. As of April 2026, the project was last updated on April 19, 2026.

While not purpose-built for cron monitoring like Healthchecks, Uptime Kuma includes a **Heartbeat monitor** type that serves the same function: your cron job pings a URL at the end of execution, and Uptime Kuma alerts you if the ping is late.

### How Heartbeat Monitors Work

In Uptime Kuma, you create a monitor of type "Heartbeat" and set the interval. The monitor generates a unique heartbeat URL. Your cron job sends a request to that URL when it completes:

```bash
# Example cron entry with Uptime Kuma heartbeat
0 3 * * * /opt/scripts/nightly-report.sh && curl -fsS https://uptime-kuma.example.com/api/push/heartbeat-id?status=up&msg=OK&ping=
```

Uptime Kuma then displays the heartbeat status on its dashboard and can trigger notifications through its extensive notification channel list.

### Key Features

- **90+ monitor types** — HTTP, TCP, DNS, Docker, gRPC, and heartbeat
- **Beautiful dashboard** — clean, real-time status overview
- **Status pages** — public-facing status pages for service transparency
- **Notification channels** — Telegram, Discord, Slack, email, webhook, Pushover, Gotify, and many more
- **Multi-language support** — 40+ languages
- **2FA authentication** — secure access to your monitoring dashboard
- **Map and certificate monitoring** — track SSL certificate expiry
- **Docker auto-discovery** — automatically detect and monitor containers

### Docker Compose Setup

Uptime Kuma is simpler to deploy than Healthchecks since it uses SQLite by default and does not require a separate database:

```yaml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    container_name: uptime-kuma
    volumes:
      - uptime-kuma-data:/app/data
    ports:
      - "3001:3001"
    restart: unless-stopped

volumes:
  uptime-kuma-data:
```

That is it — a single service with a persistent volume. Uptime Kuma stores all configuration, monitors, and heartbeat data in its internal SQLite database. For most self-hosted setups, this is more than sufficient.

For production deployments handling thousands of monitors, consider the [two-tier deployment](https://github.com/louislam/uptime-kuma/wiki/Two-Tier-Deployment) pattern with a separate database backend.

### When to Choose Uptime Kuma for Cron Monitoring

Uptime Kuma is the right choice when you want a single monitoring platform that covers both uptime checks *and* cron job monitoring. If you already use Uptime Kuma for service monitoring, adding heartbeat monitors for your cron jobs means one less tool to maintain.

However, Uptime Kuma's heartbeat feature is less mature than Healthchecks' dedicated cron monitoring. It lacks cron expression parsing, calendar views, and the flip tracking that Healthchecks provides.

## Prometheus Alertmanager: Infrastructure-Grade Cron Monitoring

For teams already running Prometheus for metrics collection, the **Alertmanager** component can handle cron job monitoring through a push-based pattern. This is not a simple ping service — it is a full alerting pipeline with grouping, silencing, inhibition, and routing.

### How It Works

Instead of a simple HTTP ping, you push a metric from your cron job to Prometheus's pushgateway, or use a file-based approach where the cron job touches a file and Prometheus's `node_filesystem` exporter detects its age. A Prometheus alerting rule fires if the metric is stale:

```yaml
# prometheus.yml — alerting rule for cron job monitoring
groups:
  - name: cron-alerts
    rules:
      - alert: CronJobBackupDatabaseNotRun
        expr: absent(up{job="backup-database"} == 1) and on() hour() > 2
        for: 30m
        labels:
          severity: critical
          team: infrastructure
        annotations:
          summary: "Database backup cron job has not run today"
          description: "The backup-database cron job was expected to run at 2:00 AM but has not completed."
```

The Alertmanager then routes this alert to your notification channels.

### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: "smtp.example.com:587"
  smtp_from: "alerts@example.com"
  smtp_auth_username: "alerts@example.com"
  smtp_auth_password: "your-smtp-password"

route:
  group_by: ["alertname", "team"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: "email-critical"
  routes:
    - match:
        severity: critical
      receiver: "pagerduty-critical"
    - match:
        severity: warning
      receiver: "slack-warnings"

receivers:
  - name: "email-critical"
    email_configs:
      - to: "oncall@example.com"
        send_resolved: true
  - name: "pagerduty-critical"
    pagerduty_configs:
      - service_key: "your-pagerduty-service-key"
  - name: "slack-warnings"
    slack_configs:
      - api_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
        channel: "#infra-alerts"
        title: "{{ .GroupLabels.alertname }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
```

### When to Choose Prometheus Alertmanager

Prometheus Alertmanager is the right choice when:

- You already run Prometheus for infrastructure monitoring
- You want cron job alerts to be part of your unified alerting pipeline
- You need advanced routing, grouping, and silencing capabilities
- You want to correlate cron job failures with system metrics (CPU, memory, disk)

However, this approach has a steeper learning curve and requires maintaining a full Prometheus stack. For simple cron monitoring, Healthchecks or Uptime Kuma are significantly easier to set up.

## Comparison Table

| Feature | Healthchecks | Uptime Kuma | Prometheus Alertmanager |
|---|---|---|---|
| **Primary purpose** | Cron job monitoring | Uptime monitoring | Alerting pipeline |
| **GitHub stars** | ~10,000 | ~85,000 | ~8,400 (Alertmanager) |
| **Language** | Python/Django | JavaScript/Node.js | Go |
| **Database** | PostgreSQL (required) | SQLite (built-in) | TSDB (built-in) |
| **Docker complexity** | 2 services (web + DB) | 1 service | 2+ services |
| **Heartbeat pings** | ✅ Dedicated | ✅ Heartbeat type | ⚠️ Via pushgateway |
| **Cron expressions** | ✅ Full support | ❌ Not supported | ⚠️ Manual rules |
| **Calendar view** | ✅ Built-in | ❌ | ❌ |
| **Status pages** | ❌ | ✅ Built-in | ❌ |
| **Notification channels** | 20+ | 90+ | 20+ |
| **API access** | ✅ REST API | ✅ REST API | ✅ REST API |
| **Team management** | ✅ | ✅ (basic) | ❌ |
| **SSL cert monitoring** | ❌ | ✅ | ❌ |
| **Best for** | Dedicated cron monitoring teams | Teams wanting one monitoring tool for everything | Teams already running Prometheus |

## Choosing the Right Tool

The decision comes down to your existing infrastructure and the scope of your monitoring needs:

- **Choose Healthchecks** if cron monitoring is your primary concern. It is purpose-built for this exact use case, with cron expression support, calendar views, and flip tracking. The two-service Docker setup is straightforward. For more on self-hosted monitoring approaches, see our [endpoint monitoring guide comparing Gatus, Blackbox Exporter, and Smokeping](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/).

- **Choose Uptime Kuma** if you want a single dashboard for both service uptime and cron job monitoring. The single-container Docker deployment is the simplest of the three options, and the status page feature is a bonus. If you also need to monitor certificate expiry, our [certificate monitoring guide](../2026-04-19-self-hosted-certificate-monitoring-expiry-alerting-certimate-x509-exporter-certspotter-guide-2026/) covers tools that complement Uptime Kuma.

- **Choose Prometheus Alertmanager** if you are already running Prometheus. Adding cron job alerting to your existing alert pipeline costs almost nothing in terms of new infrastructure, and you gain the ability to correlate job failures with system-level metrics.

For teams looking to centralize their observability stack, combining Healthchecks for cron monitoring with a metrics platform gives comprehensive coverage. See our [database monitoring guide comparing pgWatch2, Percona PMM, and pgMonitor](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) for complementary monitoring tools.

## Frequently Asked Questions

### What is the difference between cron job monitoring and uptime monitoring?

Uptime monitoring checks whether a service or website is reachable (HTTP status codes, response times, TCP connections). Cron job monitoring tracks whether a scheduled task actually ran and completed successfully. A cron job can succeed even when the server is under heavy load, and a server can be up while a cron job silently fails — so the two monitoring types serve different purposes.

### Can I use Healthchecks without setting up PostgreSQL?

No, Healthchecks requires PostgreSQL as its database backend. However, if you want a simpler setup with no external database, Uptime Kuma uses SQLite internally and deploys as a single Docker container.

### How do I monitor a cron job that runs longer than 24 hours?

Healthchecks supports "long-running" jobs with a start and end ping pattern. Send a `/start` ping when the job begins and a `/end` (or regular) ping when it completes. Healthchecks will alert you if the job does not finish within the expected duration.

### Is it possible to chain multiple alert channels in Healthchecks?

Yes. You can configure multiple notification channels per check (email + Slack + webhook, for example). Healthchecks sends alerts through all configured channels simultaneously. You can also set different channels for "up" and "down" events.

### How does Uptime Kuma heartbeat compare to Healthchecks for cron monitoring?

Uptime Kuma's heartbeat is functional but basic. It supports a simple ping URL and interval, but lacks cron expression parsing, calendar views, and flip tracking. For basic "did my job run" monitoring, it works well. For advanced cron scheduling patterns and historical analysis, Healthchecks is the stronger choice.

### What happens if the monitoring service itself goes down?

This is the classic monitoring problem. For self-hosted setups, consider running the monitoring service on a separate server from your cron jobs. Healthchecks and Uptime Kuma both support external notification services (email via external SMTP, Slack, PagerDuty), so even if your monitoring server has issues, alerts can still be delivered through external channels.

### Can I monitor Windows scheduled tasks with these tools?

Yes. All three tools use HTTP-based ping endpoints, which any scripting language can call. On Windows, add a `curl` or PowerShell `Invoke-WebRequest` call at the end of your scheduled task script to ping the monitoring service.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Cron Job Monitoring: Healthchecks vs Uptime Kuma vs Prometheus 2026",
  "description": "Compare the best self-hosted cron job monitoring tools in 2026. Healthchecks, Uptime Kuma heartbeat monitors, and Prometheus Alertmanager — with Docker setup guides and alerting configurations.",
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
