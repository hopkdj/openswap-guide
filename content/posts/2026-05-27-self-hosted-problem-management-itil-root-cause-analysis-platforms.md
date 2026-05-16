---
title: "Self-Hosted Problem Management: ITIL Root Cause Analysis Platforms in 2026"
date: "2026-05-17"
tags: ["problem-management", "ITSM", "incident-management", "root-cause", "ITIL"]
draft: false
---

When incidents strike, fixing the immediate issue is only half the battle. **Problem management** — the ITIL practice of identifying and eliminating root causes to prevent recurring incidents — is what separates reactive teams from proactive ones. While incident management tools handle alerting and response, problem management platforms track known errors, root cause analyses, and permanent fixes.

In this guide, we compare three self-hosted platforms that support problem management workflows: **osTicket** (ticketing with problem tracking), **iTop** (full ITSM suite with CMDB), and **Zammad** (modern ticketing with problem/incident linking).

## What Is ITIL Problem Management?

ITIL defines problem management as the practice of reducing the likelihood and impact of incidents by identifying actual root causes and managing workarounds and known errors. The key distinction from incident management:

- **Incident**: A service disruption that needs immediate resolution ("The database is down")
- **Problem**: The underlying cause of one or more incidents ("The database crashes when connection pool exceeds 200")

Problem management involves:
- **Root cause analysis (RCA)**: Systematic investigation of incident patterns
- **Known error database (KEDB)**: Cataloging documented issues with workarounds
- **Trend analysis**: Identifying recurring incidents across services
- **Permanent fix tracking**: Ensuring workarounds evolve into permanent solutions
- **Proactive problem identification**: Finding issues before they cause incidents

Without problem management, teams firefight the same issues repeatedly. With it, you build institutional knowledge and systematically eliminate recurring failures.

## Comparison: Problem Management Platforms

| Feature | osTicket | iTop (ITSM) | Zammad |
|---------|----------|-------------|--------|
| **Primary Focus** | Help desk ticketing | Full ITSM suite | Modern customer support |
| **Problem Tracking** | Custom fields + categories | Dedicated problem objects | Via linked tickets |
| **CMDB Integration** | No | Yes (built-in) | No |
| **SLA Management** | Basic | Advanced | Advanced |
| **Knowledge Base** | Basic FAQ | Full KEDB | Internal knowledge base |
| **Root Cause Analysis** | Manual (custom fields) | Structured workflow | Manual |
| **REST API** | Yes | Yes | Yes |
| **Docker Support** | Community images | Official image | Official image |
| **GitHub Stars** | 3,700+ | 1,200+ | 6,400+ |
| **Best For** | Small teams, simple workflows | Enterprise ITIL compliance | Modern UX, fast deployment |

## 1. osTicket — Lightweight Problem Tracking

osTicket is the most popular open-source help desk system. While not a dedicated ITSM platform, it supports problem management through custom ticket categories, SLA plans, and FAQ integration.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  osticket:
    image: linuxserver/osticket:latest
    container_name: osticket
    ports:
      - "8080:80"
    volumes:
      - osticket-config:/config
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    depends_on:
      - osticket-db
    restart: unless-stopped

  osticket-db:
    image: mariadb:11
    container_name: osticket-db
    volumes:
      - osticket-db-data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=osticket_root_pass
      - MYSQL_DATABASE=osticket
      - MYSQL_USER=osticket
      - MYSQL_PASSWORD=osticket_pass
    restart: unless-stopped

  osticket-cron:
    image: alpine:latest
    container_name: osticket-cron
    volumes:
      - osticket-config:/config
    command: >
      sh -c "while true; do
        php /config/www/osticket/api/cron.php;
        sleep 300;
      done"
    restart: unless-stopped

volumes:
  osticket-config:
  osticket-db-data:
```

osTicket supports problem management through **custom ticket fields** and **help topics**. Create a "Problem" category with fields for root cause, workaround, and permanent fix status. Use SLA plans to ensure problems are resolved within defined timeframes.

**Configuring problem categories in osTicket:**
```
Settings > Help Topics > Add Topic:
  Name: Problem - Root Cause Analysis
  Department: IT Operations
  Priority: High
  Custom Fields:
    - Root Cause (text area)
    - Affected Services (dropdown)
    - Workaround Available (yes/no)
    - Permanent Fix Status (open/in-progress/resolved)
```

## 2. iTop — Full ITSM Suite with CMDB

iTop (IT Operational Portal) is a comprehensive ITSM platform that implements ITIL problem management natively. It includes a CMDB for tracking configuration items, dedicated problem objects linked to incidents, and a known error database.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  itop:
    image: itophub/itop:3.1
    container_name: itop
    ports:
      - "8081:80"
    volumes:
      - itop-data:/var/www/html
      - itop-conf:/etc/itop
    environment:
      - ITOP_DB_HOST=itop-db
      - ITOP_DB_USER=itop
      - ITOP_DB_PASSWORD=itop_pass
      - ITOP_DB_NAME=itop
    depends_on:
      - itop-db
    restart: unless-stopped

  itop-db:
    image: mariadb:11
    container_name: itop-db
    volumes:
      - itop-db-data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=itop_root_pass
      - MYSQL_DATABASE=itop
      - MYSQL_USER=itop
      - MYSQL_PASSWORD=itop_pass
    command:
      - "--max-allowed-packet=64M"
      - "--innodb-log-file-size=64M"
    restart: unless-stopped

volumes:
  itop-data:
  itop-conf:
  itop-db-data:
```

iTop's problem management workflow:
1. **Incidents are linked to problems** — when multiple incidents share the same root cause, they are associated with a single problem record
2. **Root cause analysis** — iTop provides structured fields for RCA methodology (5 Whys, fishbone diagrams)
3. **Known error management** — documented workarounds are stored in the KEDB and linked to CIs in the CMDB
4. **Change management** — permanent fixes are tracked through iTop's change management module

The CMDB integration is iTop's differentiator. When a problem is linked to a configuration item (server, application, network device), you can trace the impact across your entire infrastructure.

## 3. Zammad — Modern Ticketing with Problem Workflows

Zammad is a modern, web-based support and ticketing system with a clean UI, real-time collaboration features, and API-first design. While not a dedicated ITSM tool, its flexible ticket types and linking capabilities support problem management workflows.

### Docker Compose Setup

```yaml
version: "3.8"

services:
  zammad:
    image: zammad/zammad-docker-compose:latest
    container_name: zammad
    ports:
      - "8082:80"
    environment:
      - NGINX_SERVER_SCHEME=http
      - POSTGRESQL_HOST=zammad-postgresql
      - POSTGRESQL_PORT=5432
      - POSTGRESQL_DB=zammad
      - POSTGRESQL_USER=zammad
      - POSTGRESQL_PASS=zammad_pass
      - ELASTICSEARCH_HOST=http://zammad-elasticsearch:9200
      - MEMCACHED_SERVERS=zammad-memcached:11211
      - REDIS_URL=redis://zammad-redis:6379
      - RAILS_TRUSTED_PROXIES=127.0.0.1
    depends_on:
      - zammad-postgresql
      - zammad-elasticsearch
      - zammad-memcached
      - zammad-redis
    restart: unless-stopped

  zammad-postgresql:
    image: postgres:15
    container_name: zammad-postgresql
    volumes:
      - zammad-pg-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=zammad
      - POSTGRES_PASSWORD=zammad_pass
      - POSTGRES_DB=zammad
    restart: unless-stopped

  zammad-elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: zammad-elasticsearch
    volumes:
      - zammad-es-data:/usr/share/elasticsearch/data
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    restart: unless-stopped

  zammad-memcached:
    image: memcached:latest
    container_name: zammad-memcached
    restart: unless-stopped

  zammad-redis:
    image: redis:7-alpine
    container_name: zammad-redis
    restart: unless-stopped

  zammad-init:
    image: zammad/zammad-docker-compose:latest
    container_name: zammad-init
    depends_on:
      - zammad-postgresql
      - zammad-elasticsearch
    command: ["zammad-init"]
    restart: "no"

volumes:
  zammad-pg-data:
  zammad-es-data:
```

Zammad supports problem management through:
- **Ticket linking**: Connect related incident tickets to a master "problem" ticket
- **Text modules**: Store known error descriptions and workarounds as reusable text blocks
- **Object attribute customization**: Add custom fields for root cause analysis, impact assessment, and resolution tracking
- **SLA management**: Define response and resolution time targets for problem tickets
- **Reporting**: Built-in reporting for tracking problem resolution trends

## Choosing the Right Problem Management Platform

**Use osTicket when:**
- You need a simple, lightweight ticketing system
- Problem management needs are basic (tracking root causes and workarounds)
- Your team is small (under 20 agents)
- You want the lowest operational overhead

**Use iTop when:**
- You need full ITIL compliance (problem, incident, change, CMDB)
- Configuration item tracking is essential for root cause analysis
- You operate a medium-to-large IT organization
- Known error database management is a requirement

**Use Zammad when:**
- Modern UI and user experience matter
- You need Elasticsearch-powered search across all tickets
- Real-time collaboration (live chat, shared drafts) is important
- You want API-first extensibility for custom integrations

## Why Self-Host Your Problem Management Platform?

Problem management data is deeply sensitive — it contains detailed records of system failures, security incidents, and operational weaknesses. Hosting this data on a third-party SaaS platform means sharing your organization's vulnerability history with an external provider. Self-hosting keeps this intelligence entirely within your infrastructure.

Self-hosted platforms also integrate seamlessly with your existing monitoring and alerting stack. When Prometheus detects a recurring metric anomaly, your monitoring system can automatically create a problem ticket via REST API. When a known error is documented, your runbooks can reference the KEDB directly. These integrations are harder to achieve with cloud-based ITSM tools that impose API rate limits and data export restrictions.

For organizations pursuing ITIL certification or SOC 2 compliance, self-hosted problem management provides the audit trail and data sovereignty that external providers cannot guarantee. Every problem record, root cause analysis, and known error update is logged locally and can be included in compliance reports.

For incident response workflows, see our [incident management and on-call guide](../self-hosted-incident-management-oncall-alerta-openduty-2026/). If you need alert routing for problem detection, our [Prometheus Alertmanager vs ntfy guide](../2026-05-07-prometheus-alertmanager-vs-ntfy-vs-gotify-self-hosted-alert-routing-guide/) covers notification pipelines. For Kubernetes-specific event tracking that feeds problem identification, check our [Kubernetes event monitoring guide](../2026-05-16-self-hosted-kubernetes-event-monitoring-kwatch-kube-eventer-exporter-guide/).

## FAQ

### What is the difference between incident management and problem management?

Incident management focuses on restoring service as quickly as possible after a disruption. Problem management investigates why the incident occurred and implements permanent fixes to prevent recurrence. Incident management is reactive (fix it now); problem management is proactive (make sure it never happens again).

### How many incidents trigger a problem record?

There is no fixed threshold — it depends on your organization's risk tolerance. Some teams create a problem record after a single P1 incident. Others wait for 3+ incidents with the same root cause within a defined period. iTop and Zammad both support configurable thresholds for automatic problem creation.

### What should a root cause analysis (RCA) document contain?

A complete RCA includes: incident summary, timeline of events, impact assessment, root cause identification (using methods like 5 Whys or fishbone diagrams), contributing factors, corrective actions, preventive measures, and lessons learned. Both iTop and Zammad support custom fields to structure this information.

### How does a known error differ from a problem?

A problem is the underlying cause that is still being investigated. A known error is a problem that has been analyzed and documented with a workaround. The known error database (KEDB) stores these documented issues so that future incidents can be resolved quickly using established workarounds while permanent fixes are developed.

### Can problem management be automated?

Partial automation is possible. Monitoring systems can detect recurring incident patterns and automatically create problem tickets. Automated tools can suggest likely root causes based on historical data. However, the actual root cause analysis and permanent fix design require human expertise. iTop and Zammad both support API-driven problem ticket creation from external monitoring tools.

### How do you measure problem management effectiveness?

Key metrics include: mean time to identify root cause (MTTI), percentage of incidents linked to known problems, number of recurring incidents per month, problem resolution rate within SLA, and reduction in incident volume after permanent fixes. All three platforms support reporting on these metrics through built-in dashboards or API exports.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Problem Management: ITIL Root Cause Analysis Platforms in 2026",
  "description": "Compare osTicket, iTop, and Zammad for ITIL problem management and root cause analysis. Self-hosted Docker Compose deployment with known error tracking.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
