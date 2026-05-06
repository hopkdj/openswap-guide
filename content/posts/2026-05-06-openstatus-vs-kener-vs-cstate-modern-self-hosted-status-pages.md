---
title: "OpenStatus vs Kener vs cstate: Best Modern Self-Hosted Status Pages 2026"
date: 2026-05-06
tags: ["comparison", "guide", "self-hosted", "monitoring", "status-page"]
draft: false
---

Status pages are the first line of communication when your infrastructure experiences downtime. They keep users informed, reduce support ticket volume, and build trust through transparency. While legacy tools like Cachet and Statping dominated the early days of self-hosted status pages, a new generation of tools has emerged with modern stacks, better monitoring integrations, and cleaner user experiences.

In this guide, we compare three leading modern status page platforms — **OpenStatus**, **Kener**, and **cstate** — examining their architectures, deployment options, feature sets, and ideal use cases.

## OpenStatus: Full-Stack Status Platform with Monitoring as Code

[OpenStatus](https://github.com/openstatusHQ/openstatus) (8,600+ GitHub stars) is a comprehensive status page platform built with Next.js, featuring both uptime monitoring and API monitoring capabilities. It stands out for its "monitoring as code" philosophy — you define your monitors in configuration files, and OpenStatus handles the rest.

**Key features:**

- **Uptime monitoring** with configurable intervals and multi-region checks
- **API monitoring as code** — define monitors in YAML/JSON configuration
- **Incident management** with status updates, timelines, and post-mortems
- **Status page customization** with custom domains, branding, and themes
- **Notification integrations** — email, Slack, Discord, webhooks, and more
- **Open-source core** with a generous feature set in the free tier
- **Powered by Turso** (libSQL) for lightweight, embedded database storage

OpenStatus is designed for teams that want both the status page and the monitoring infrastructure in a single platform. It runs scheduled checks against your services and automatically updates the status page when issues are detected.

### Deploying OpenStatus with Docker Compose

OpenStatus provides an official Docker Compose configuration with libSQL and Tinybird for analytics:

```yaml
services:
  libsql:
    image: ghcr.io/tursodatabase/libsql-server:latest
    ports:
      - "8080:8080"
    volumes:
      - libsql-data:/var/lib/sqld
    environment:
      - SQLD_NODE=primary
    restart: unless-stopped

  openstatus:
    image: ghcr.io/openstatushq/openstatus:latest
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=file:./data/openstatus.db
      - CRON_SECRET=***
      - RESEND_API_KEY=***
    depends_on:
      - libsql
    restart: unless-stopped

volumes:
  libsql-data:
```

The platform requires environment variables for the database connection, cron job secret (for scheduled monitoring), and an email provider (Resend) for notifications.

## Kener: Modern Status Pages with Stunning Design

[Kener](https://github.com/rajnandan1/kener) (4,900+ GitHub stars) focuses on delivering beautiful, modern status pages with a batteries-included approach. Built with Next.js, PostgreSQL, and Redis, Kener provides a polished experience out of the box with minimal configuration.

**Key features:**

- **Stunning UI** — modern, responsive design with dark mode support
- **Multiple data sources** — supports PostgreSQL, MySQL, or SQLite backends
- **BullMQ-powered scheduler** — reliable job queue for uptime checks
- **Custom monitors** — HTTP, TCP, ping, and DNS monitoring
- **Incident timeline** — detailed incident history with status updates
- **API-driven** — configure monitors programmatically via REST API
- **Self-contained deployment** — Redis and database bundled in Docker Compose

Kener's strength is its combination of beautiful presentation with powerful monitoring capabilities. It's designed for teams that want a status page that looks professional without extensive customization.

### Deploying Kener with Docker Compose

Kener ships with an official Docker Compose that includes Redis for the job queue:

```yaml
services:
  redis:
    image: redis:7-alpine
    container_name: kener-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  kener:
    image: rajnandan1/kener:latest
    container_name: kener
    ports:
      - "3000:3000"
    environment:
      KENER_SECRET_KEY: generate-with-openssl-rand-base64-32
      ORIGIN: http://localhost:3000
      REDIS_URL: redis://redis:***@postgres:5432/kener
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis_data:
```

Generate a secure secret key before deployment:

```bash
openssl rand -base64 32
```

## cstate: Ultra-Lightweight Static Status Pages

[cstate](https://github.com/cstate/cstate) (2,800+ GitHub stars) takes a fundamentally different approach. Instead of a dynamic application with a database, cstate generates **static HTML** using Hugo — the same static site generator that powers this website. There is no server-side processing, no database, and no API.

**Key features:**

- **Static site generation** — zero server-side dependencies after build
- **Hugo-powered** — fast build times, excellent SEO, and reliable hosting
- **No database required** — incidents and components are defined in YAML/Markdown
- **IE8+ browser support** — outstanding compatibility with older browsers
- **Preloaded CMS** — built-in Netlify CMS for easy content management
- **Read-only API** — JSON output for programmatic status checking
- **Badges and widgets** — embeddable status badges for your websites
- **Minimal resource footprint** — runs on the cheapest hosting tiers

cstate is the lightest option by far. It generates a complete static website that can be hosted on GitHub Pages, Netlify, Vercel, or any static file server. Updates are made by editing YAML configuration files and rebuilding the site.

### Deploying cstate with Docker

While cstate is primarily a static site generator, you can containerize it for local development or serve it via a lightweight web server:

```yaml
services:
  cstate:
    image: hugomods/hugo:exts
    container_name: cstate-builder
    volumes:
      - ./cstate-site:/src
      - ./cstate-public:/public
    command: hugo --minify --destination /public
    restart: "no"

  cstate-web:
    image: nginx:alpine
    container_name: cstate-web
    ports:
      - "80:80"
    volumes:
      - ./cstate-public:/usr/share/nginx/html:ro
    depends_on:
      - cstate
    restart: unless-stopped
```

Alternatively, host cstate directly on GitHub Pages with a simple CI/CD pipeline — no server needed at all.

## Feature Comparison

| Feature | OpenStatus | Kener | cstate |
|---------|-----------|-------|--------|
| **Architecture** | Next.js + libSQL | Next.js + PostgreSQL + Redis | Hugo (static HTML) |
| **GitHub Stars** | 8,600+ | 4,900+ | 2,800+ |
| **Monitoring** | Built-in uptime + API | Built-in HTTP/TCP/ping/DNS | Manual status updates |
| **Database** | libSQL (embedded) | PostgreSQL/MySQL/SQLite | None (static files) |
| **Real-time checks** | Yes (scheduled cron jobs) | Yes (BullMQ scheduler) | No (manual updates) |
| **Incident management** | Full timeline + post-mortems | Incident history + updates | YAML-defined incidents |
| **Custom domains** | Yes | Yes | Yes (via hosting) |
| **Notifications** | Email, Slack, Discord, webhooks | Email via SMTP/Resend | Webhook-based |
| **API** | REST API for monitors | REST API for configuration | Read-only JSON API |
| **Resource usage** | Moderate (Node.js + DB) | Moderate-High (Node.js + Redis + DB) | Minimal (static files) |
| **Hosting options** | VPS, Docker, managed | VPS, Docker | Any static host, GitHub Pages |
| **Self-hosted** | Yes (open-source core) | Yes (fully open-source) | Yes (fully open-source) |

## Which Status Page Tool Should You Choose?

**Choose OpenStatus if:**
- You want an all-in-one monitoring + status page solution
- Your team prefers "monitoring as code" configuration
- You need multi-region uptime checks built in
- You want modern notification integrations (Slack, Discord, webhooks)

**Choose Kener if:**
- Visual design and user experience are top priorities
- You need a robust job queue (BullMQ + Redis) for reliable monitoring
- You want database flexibility (PostgreSQL, MySQL, or SQLite)
- You prefer a batteries-included, self-contained deployment

**Choose cstate if:**
- You want the absolute minimum resource footprint
- You already use Hugo or prefer static site workflows
- You need to host on the cheapest/free tiers (GitHub Pages)
- You value simplicity and reliability over real-time automation
- You need browser compatibility extending back to IE8

## Why Self-Host Your Status Page?

Using a SaaS status page provider introduces a single point of failure — if the status page provider goes down, you cannot communicate your own outage to your users. Self-hosting eliminates this risk entirely. You maintain full control over your status page infrastructure, ensuring it remains available even when your primary services experience issues.

Self-hosted status pages also eliminate monthly subscription costs, avoid vendor lock-in, and keep incident data within your infrastructure. For organizations with compliance requirements (HIPAA, SOC 2, GDPR), keeping status data on-premises simplifies audit processes. The open-source tools covered in this guide — OpenStatus, Kener, and cstate — all offer complete self-hosted deployments without any paid tier requirements.

For teams already running self-hosted monitoring stacks, integrating a self-hosted status page creates a cohesive observability pipeline. If you use tools like Prometheus or Grafana for infrastructure monitoring, pairing them with OpenStatus or Kener gives you end-to-end visibility from metrics collection to public communication. For related reading on infrastructure monitoring, see our [comparison of monitoring platforms](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide/).

If you also manage uptime and SLA reporting, our [SLA compliance guide](../2026-05-04-self-hosted-sla-compliance-uptime-reporting-uptime-kuma-cachet-gatus-guide/) covers tools that complement a status page with formal SLA tracking. For incident response workflows, our [circuit breaker and fault tolerance guide](../2026-05-01-self-hosted-circuit-breaker-envoy-haproxy-linkerd-fault-tolerance-guide/) explains how to build resilience into your service architecture.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "OpenStatus vs Kener vs cstate: Best Modern Self-Hosted Status Pages 2026",
  "description": "Compare OpenStatus, Kener, and cstate for self-hosted status pages. Feature comparison, Docker Compose configs, and deployment guides for modern uptime monitoring.",
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

## FAQ

### Is OpenStatus free to self-host?

Yes. OpenStatus has an open-source core that you can self-host without any licensing fees. The self-hosted version includes uptime monitoring, API monitoring, status pages, incident management, and notification integrations. They offer a managed cloud version with additional features, but the self-hosted option is fully functional for most use cases.

### Does Kener support multiple status pages?

Kener supports managing multiple monitors and status components within a single instance. You can configure separate monitors for different services, each with their own status indicators and incident history. The Next.js frontend allows you to customize the layout and branding for different audiences.

### Can cstate automatically detect outages?

No. cstate is a static site generator and does not perform active monitoring or outage detection. You update component statuses and incidents by editing YAML configuration files and rebuilding the site. For automated outage detection, pair cstate with an external monitoring tool like Uptime Kuma or a custom health-check script that updates the cstate configuration and triggers a rebuild.

### Which status page tool uses the least server resources?

cstate uses virtually zero server resources after the initial Hugo build — it serves plain HTML, CSS, and JavaScript files. OpenStatus and Kener both require Node.js runtimes and databases (libSQL for OpenStatus, PostgreSQL + Redis for Kener), making them more resource-intensive. For low-traffic status pages on minimal infrastructure, cstate is the most efficient choice.

### Can I migrate from Cachet or Statping to these tools?

Migration paths vary by tool. cstate uses simple YAML configuration that is easy to recreate manually. OpenStatus and Kener both offer APIs for programmatic setup, so you can script migrations from Cachet's database. None of the three tools have official one-click migration tools from legacy status page platforms, but the configuration is straightforward enough to rebuild manually.

### Do these tools support custom branding and domains?

Yes, all three support custom branding. OpenStatus and Kener provide built-in theme customization through their web interfaces. cstate allows full theme customization through Hugo templates and CSS. All three support custom domains — OpenStatus and Kener through reverse proxy configuration, and cstate through your static hosting provider's domain settings.
