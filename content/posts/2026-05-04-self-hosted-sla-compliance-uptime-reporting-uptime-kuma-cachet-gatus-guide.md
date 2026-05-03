---
title: "Self-Hosted SLA Compliance & Uptime Reporting: Uptime Kuma vs Cachet vs Gatus (2026)"
date: 2026-05-04
tags: ["comparison", "guide", "self-hosted", "monitoring", "sla", "compliance", "reporting"]
draft: false
description: "Compare Uptime Kuma, Cachet, and Gatus for self-hosted SLA compliance tracking and uptime reporting. Learn which open-source monitoring tool delivers the SLA dashboards and compliance reports your contracts require."
---

When your service contracts guarantee 99.9% uptime, a simple green/red status indicator isn't enough. You need documented SLA compliance reports, historical uptime percentages, incident timelines, and breach alerting — all evidence that holds up during vendor reviews and customer audits. Cloud monitoring platforms like Pingdom and Datadog charge premium pricing for SLA reporting features, but you can build the same capability with open-source tools running on your own infrastructure.

This guide compares three popular self-hosted monitoring platforms — **Uptime Kuma**, **Cachet**, and **Gatus** — through the lens of SLA compliance tracking, uptime reporting, and audit-ready documentation. For broader monitoring comparisons, see our [Gatus vs k6 vs Uptime Kuma synthetic monitoring guide](../2026-04-28-gatus-vs-k6-vs-uptime-kuma-self-hosted-synthetic-monitoring-guide-2026/) and [SLO management tools comparison](../2026-04-23-sloth-vs-pyrra-vs-slo-generator-self-hosted-slo-management-guide/).

## Why SLA Compliance Reporting Matters

SLA (Service Level Agreement) compliance tracking serves several business-critical functions:

- **Contract enforcement**: Most B2B service contracts include uptime guarantees with financial penalties for breaches. Accurate tracking prevents disputes and ensures credits are applied correctly.
- **Customer transparency**: Public status pages with historical uptime data build trust and reduce support ticket volume during incidents.
- **Regulatory compliance**: Industries like healthcare (HIPAA), finance (PCI DSS), and government (FedRAMP) require documented availability metrics and incident records.
- **Capacity planning**: Historical uptime trends reveal patterns — recurring outages at specific times, degradation under load, or correlated failures across services.
- **Vendor accountability**: If you depend on upstream providers, SLA tracking provides evidence for escalation or renegotiation.

## Understanding SLA vs SLO vs SLI

Before comparing tools, it helps to understand the terminology:

| Term | Definition | Example |
|------|------------|---------|
| **SLI** (Service Level Indicator) | The actual measured metric | API responded in 200ms |
| **SLO** (Service Level Objective) | The target value for an SLI | 99.9% of requests under 500ms |
| **SLA** (Service Level Agreement) | The contractual commitment with consequences | 99.9% uptime or service credit applies |

For SLO-specific tooling (error budgets, burn rates), check our [Sloth vs Pyrra vs SLO Generator guide](../2026-04-23-sloth-vs-pyrra-vs-slo-generator-self-hosted-slo-management-guide/). This article focuses on SLA compliance reporting — the contractual, customer-facing side of availability tracking.

## Uptime Kuma: The SLA Dashboard Leader

[Uptime Kuma](https://github.com/louislam/uptime-kuma) is the most popular self-hosted monitoring tool with over 86,000 GitHub stars. Its SLA reporting features make it the go-to choice for teams that need uptime compliance tracking without complex configuration.

### SLA Reporting Features

- **Automatic SLA calculation**: Uptime Kuma calculates uptime percentages per monitor over configurable time windows (24h, 7d, 30d, custom date ranges).
- **Visual SLA dashboard**: Color-coded uptime bars show availability at a glance — green for compliant periods, red for downtime events.
- **Incident timeline**: Each downtime event is logged with start time, end time, duration, and affected monitors — creating an audit trail for SLA breach investigations.
- **Status pages**: Public-facing status pages aggregate monitor health and display current SLA percentages, ideal for customer-facing transparency.
- **Certificate expiry monitoring**: Built-in SSL certificate monitoring prevents outages caused by expired TLS certificates.
- **Multi-protocol support**: HTTP(s), TCP, ping, DNS, push, Steam game servers, Docker containers, and more.

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  uptime-kuma:
    image: louislam/uptime-kuma:1
    container_name: uptime-kuma
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - uptime-kuma-data:/app/data

volumes:
  uptime-kuma-data:
    driver: local
```

### SLA Report Export

Uptime Kuma's web UI displays SLA percentages directly on the dashboard. For formal reporting, you can:

1. **Screenshot the SLA dashboard** for quick compliance snapshots
2. **Use the API** to programmatically fetch uptime statistics:
```bash
# Get monitor list
curl -X GET http://localhost:3001/api/monitor-list

# Get monitor uptime data (requires authentication)
curl -X POST http://localhost:3001/api/monitor-uptime \
  -H "Content-Type: application/json" \
  -d '{"monitorID": 1, "period": "30d"}'
```
3. **Export heartbeat data** from the SQLite database for custom report generation:
```bash
sqlite3 /path/to/uptime-kuma-data/kuma.db \
  "SELECT monitor_id, datetime, status FROM heartbeat WHERE monitor_id = 1 ORDER BY datetime DESC LIMIT 100;"
```

### Limitations for SLA Use Cases

- No built-in PDF report generation — you need to export data and format externally
- SLA calculations are based on simple up/down status, not weighted by severity
- No native SLA breach alerting (e.g., notify when monthly uptime drops below 99.5%)
- Status pages are basic — no custom branding or multi-language support without configuration

## Cachet: Status Pages with Incident Management

[Cachet](https://github.com/cachethq/cachet) is an open-source status page system designed for public-facing incident communication. While it doesn't calculate SLA percentages automatically, its incident management workflow creates the documentation trail that SLA compliance audits require.

### SLA-Related Features

- **Incident timeline**: Rich incident tracking with severity levels (none, minor, major, critical), status updates, and resolution timestamps — the raw data needed for SLA breach analysis.
- **Component grouping**: Organize services into components and component groups, mapping directly to SLA-defined service boundaries.
- **Metrics dashboard**: Custom metrics tracking with chart visualization — you can track uptime percentage, response time, or any custom SLI.
- **Subscriber notifications**: Email and webhook notifications keep stakeholders informed during incidents, reducing SLA communication failures.
- **API-driven**: Full REST API for integrating with external monitoring systems and pulling data into SLA reports.
- **Custom branding**: White-label status pages match your company's branding for customer-facing communications.

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  cachet:
    image: cachethq/docker:latest
    container_name: cachet
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DB_DRIVER=sqlite
      - APP_ENV=production
      - APP_DEBUG=false
      - APP_URL=http://localhost:8000
      - APP_KEY=base64:YourBase64KeyHere==
    volumes:
      - cachet-data:/var/www/html/bootstrap/cache
      - cachet-db:/var/www/html/database
    depends_on:
      - cachet-db

  cachet-db:
    image: postgres:16-alpine
    container_name: cachet-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=cachet
      - POSTGRES_USER=cachet
      - POSTGRES_PASSWORD=changeme
    volumes:
      - cachet-postgres:/var/lib/postgresql/data

volumes:
  cachet-data:
  cachet-db:
  cachet-postgres:
```

### Using Cachet for SLA Compliance

Cachet's workflow for SLA documentation:

1. **Define components** matching your SLA service definitions (API, Website, Database, CDN)
2. **Log incidents** with severity, timestamps, and resolution details
3. **Update incident status** through the lifecycle: Investigating → Identified → Monitoring → Resolved
4. **Export incident data** via the REST API for SLA report generation:
```bash
# Get all incidents
curl -X GET http://localhost:8000/api/v1/incidents \
  -H "X-Cachet-Token: YOUR_API_TOKEN"

# Get incidents for a specific date range
curl -X GET "http://localhost:8000/api/v1/incidents?start_date=2026-04-01&end_date=2026-04-30" \
  -H "X-Cachet-Token: YOUR_API_TOKEN"
```

### Limitations

- No automatic SLA percentage calculation — you must compute uptime from incident data
- Requires manual incident creation (no built-in active monitoring)
- Best paired with an external monitoring tool (Uptime Kuma, Prometheus) for automatic detection
- The open-source version lacks some enterprise features (SSO, advanced permissions)

## Gatus: Health Checks with SLA Scoring

[Gatus](https://github.com/TwiN/gatus) is a developer-focused health check tool with built-in SLA scoring, alerting, and a clean dashboard. Its configuration-as-code approach and automated SLA calculations make it ideal for infrastructure teams.

### SLA Reporting Features

- **Automatic SLA scoring**: Gatus calculates uptime percentage per endpoint and displays it on the dashboard with color-coded thresholds.
- **Condition-based health checks**: Define complex health criteria using HTTP status codes, response body patterns, response time thresholds, and certificate validity.
- **Alerting with SLA triggers**: Configure alerts for specific conditions — including SLA threshold breaches — via Slack, PagerDuty, Discord, email, webhooks, and more.
- **Configuration as code**: YAML-based configuration means your monitoring setup is version-controlled, reviewable, and reproducible.
- **Response time tracking**: Track both availability AND performance SLAs — Gatus records response times for each check.
- **Badge support**: Generate uptime badges for README files and dashboards, embedding live SLA data directly into documentation.

### Docker Compose Deployment

```yaml
version: '3.8'

services:
  gatus:
    image: twinproduction/gatus:latest
    container_name: gatus
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./config.yaml:/config/config.yaml:ro
      - gatus-data:/data

volumes:
  gatus-data:
    driver: local
```

### Configuration Example with SLA Alerts

```yaml
storage:
  type: sqlite
  path: /data/gatus.db

endpoints:
  - name: production-api
    url: https://api.example.com/health
    interval: 30s
    conditions:
      - "[STATUS] == 200"
      - "[RESPONSE_TIME] < 500"
      - "[CERTIFICATE_EXPIRATION] > 48h"
    alerts:
      - type: slack
        description: "Production API SLA breach"
        send-on-resolved: true
        failure-threshold: 3
        success-threshold: 1

  - name: customer-portal
    url: https://portal.example.com
    interval: 1m
    conditions:
      - "[STATUS] == 200"
      - "[BODY] == pathto(pathto('$.status')) == 'ok'"
    alerts:
      - type: pagerduty
        description: "Customer portal down — SLA impact"
        send-on-resolved: true
        integration-key: "your-pagerduty-key"

alerting:
  slack:
    webhook-url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  pagerduty:
    integration-key: "your-pagerduty-key"
```

### SLA Data Export

Gatus stores all check results in SQLite, making it straightforward to generate SLA reports:

```bash
# Query SLA data from Gatus database
sqlite3 /data/gatus.db <<EOF
SELECT 
  e.name,
  COUNT(*) as total_checks,
  SUM(CASE WHEN r.success = 1 THEN 1 ELSE 0 END) as successful_checks,
  ROUND(100.0 * SUM(CASE WHEN r.success = 1 THEN 1 ELSE 0 END) / COUNT(*), 4) as sla_percentage,
  MIN(r.timestamp) as period_start,
  MAX(r.timestamp) as period_end
FROM endpoints e
JOIN results r ON e.id = r.endpoint_id
WHERE r.timestamp > datetime('now', '-30 days')
GROUP BY e.name;
EOF
```

### Limitations

- Dashboard is functional but minimal — no fancy visualizations or custom branding
- SLA calculations are based on check success/failure, not weighted by impact
- No built-in public status page (though you can embed badges)
- SQLite storage may not scale for high-frequency monitoring across hundreds of endpoints

## SLA Compliance Feature Comparison

| Feature | Uptime Kuma | Cachet | Gatus |
|---------|-------------|--------|-------|
| **SLA percentage calculation** | ✅ Automatic | ❌ Manual from incidents | ✅ Automatic |
| **Uptime dashboard** | ✅ Visual bars | ❌ Metrics only | ✅ Score display |
| **Incident tracking** | ✅ Automatic | ✅ Rich manual workflow | ❌ Via alerting only |
| **Status pages** | ✅ Built-in | ✅ Primary feature | ❌ Badges only |
| **Public transparency** | ✅ Public status pages | ✅ Branded status pages | ❌ Embedded badges |
| **Alerting** | ✅ 100+ channels | ✅ Email/webhook | ✅ Slack, PagerDuty, etc. |
| **API access** | ✅ REST API | ✅ REST API | ❌ No API (config-only) |
| **Configuration** | ✅ Web UI | ✅ Web UI | ✅ YAML files |
| **Certificate monitoring** | ✅ Built-in | ❌ | ✅ Via conditions |
| **Response time SLA** | ❌ Basic | ✅ Custom metrics | ✅ Built-in |
| **SLA breach alerts** | ❌ Manual threshold | ❌ Manual | ✅ Configurable thresholds |
| **Report export** | ⚠️ API/SQLite only | ⚠️ API export | ⚠️ SQLite query |
| **Custom branding** | ⚠️ Limited | ✅ Full white-label | ❌ Minimal |
| **Docker support** | ✅ Official image | ✅ Official image | ✅ Official image |
| **GitHub stars** | 86,000+ | 14,000+ | 8,000+ |

## Choosing the Right SLA Tool

### Pick Uptime Kuma if:
- You need **automatic SLA percentage calculation** out of the box
- You want a **polished web UI** for non-technical team members
- You need **public status pages** with minimal setup
- You monitor a **mix of protocols** (HTTP, TCP, DNS, Docker, etc.)

### Pick Cachet if:
- Your priority is **customer-facing incident communication**
- You need **rich incident workflows** with severity levels and status updates
- You want **white-label status pages** that match your brand
- You already have monitoring and need a **status page layer** on top

### Pick Gatus if:
- You prefer **configuration-as-code** for version-controlled monitoring
- You need **complex health check conditions** (response body, response time, certificate)
- You want **SLA breach alerting** with configurable thresholds
- You're comfortable with **SQLite queries** for custom report generation

## Why Self-Host Your SLA Monitoring?

Self-hosting SLA monitoring tools gives you several advantages over cloud-based alternatives:

- **Complete data ownership**: Your uptime data, incident records, and SLA metrics never leave your infrastructure — critical for compliance audits and vendor negotiations.
- **No per-monitor pricing**: Cloud SLA tools charge per endpoint monitored. Self-hosted tools let you monitor unlimited services for the cost of a single server.
- **Custom integrations**: Direct database access means you can build custom SLA reports, integrate with internal billing systems, or feed data into executive dashboards.
- **No vendor lock-in**: Export your data anytime. Switch tools without losing historical SLA records.
- **Internal network monitoring**: Monitor private services that aren't accessible from external cloud monitoring endpoints.

For related infrastructure monitoring, check our [HertzBeat vs Prometheus vs Netdata guide](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide-2026/) and [Nagios vs Icinga vs Cacti comparison](../2026-04-25-nagios-vs-icinga-vs-cacti-self-hosted-infrastructure-monitoring-guide-2026/).

## FAQ

### What's the difference between SLA and SLO?

An SLA (Service Level Agreement) is a contractual commitment between a service provider and customer, typically including financial penalties for non-compliance. An SLO (Service Level Objective) is an internal target — the level of service your team aims to achieve. SLOs are usually stricter than SLAs to provide a safety buffer. For SLO management tools, see our [Sloth vs Pyrra vs SLO Generator guide](../2026-04-23-sloth-vs-pyrra-vs-slo-generator-self-hosted-slo-management-guide/).

### How is uptime percentage calculated?

Uptime percentage = (Total time - Downtime) / Total time × 100. For example, if a service was down for 43.2 minutes in a 30-day month (43,200 minutes), uptime = (43,200 - 43.2) / 43,200 × 100 = 99.9%. Most SLA tools calculate this automatically from heartbeat check results.

### Can I generate PDF SLA reports from these tools?

None of the three tools generate PDF reports natively. Uptime Kuma and Gatus store data in SQLite, which you can query and format using any reporting tool. Cachet provides a REST API for exporting incident data. For automated PDF generation, consider pairing with a reporting tool or using the data export to feed a custom report template.

### How often should I check services for accurate SLA tracking?

For SLA compliance, check intervals of 30 seconds to 2 minutes are typical. More frequent checks (every 10-30 seconds) give more accurate uptime calculations but increase server load. Less frequent checks (5+ minutes) may miss brief outages, artificially inflating your SLA percentage.

### What happens when an SLA is breached?

When uptime drops below the contracted threshold, the service provider typically owes the customer a service credit. Accurate SLA tracking ensures both parties agree on whether a breach occurred. Tools like Gatus can alert you proactively when uptime trends suggest an approaching breach, giving you time to investigate before the contractual deadline.

### Can I monitor internal services with these tools?

Yes. All three tools run on your own infrastructure, so they can monitor internal services not accessible from the public internet. Uptime Kuma and Gatus support TCP and HTTP checks against any reachable endpoint. Cachet relies on external monitoring to populate its status pages but can display internal service status.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SLA Compliance & Uptime Reporting: Uptime Kuma vs Cachet vs Gatus (2026)",
  "description": "Compare Uptime Kuma, Cachet, and Gatus for self-hosted SLA compliance tracking and uptime reporting. Learn which open-source monitoring tool delivers the SLA dashboards and compliance reports your contracts require.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
