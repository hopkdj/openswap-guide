---
title: "Best Self-Hosted Status Pages 2026: Cachet vs Statping-ng vs Upptime"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "monitoring", "status-page"]
draft: false
description: "Compare the best open-source self-hosted status page solutions — Cachet, Statping-ng, and Upptime. Complete Docker setup guides, feature comparison, and webhook integrations for 2026."
---

## Why Self-Host Your Status Page?

A status page is the first place users check when something goes wrong. Commercial services like Atlassian Statuspage, Instatus, and Statuspage.io charge $15–$500+ per month for features like custom domains, email notifications, and incident history. Self-hosting a status page gives you:

- **Zero subscription costs** — run unlimited public and private status pages for free
- **Full data ownership** — incident logs, uptime history, and metrics never leave your infrastructure
- **Internal service visibility** — display status for private APIs, databases, and internal tools that external services cannot reach
- **Complete customization** — modify the UI, add custom branding, and integrate with your existing tooling
- **No vendor lock-in** — migrate or export your data at any time without restrictions

Whether you run a homelab, manage a startup's infrastructure, or operate an enterprise platform, a self-hosted status page is essential for transparent communication. This guide covers the three best open-source options available in 2026.

## Option 1: Cachet — The Battle-Tested Status Page

[Cachet](https://cachethq.io/) is the most well-known open-source status page application. Built with PHP and Laravel, it has been in production since 2014 and powers status pages for thousands of organizations worldwide.

### Key Features

- **Incident Management** — Create, update, and resolve incidents with timeline tracking
- **Component Groups** — Organize services into logical groups (e.g., "API Services," "Databases")
- **Subscriber Notifications** — Email and webhook notifications for status changes
- **Custom Branding** — Fully customizable themes with CSS overrides
- **REST API** — Programmatic control over components, incidents, and metrics
- **Metric Charts** — Display real-time and historical performance graphs
- **Multi-language Support** — Translated into 20+ languages

### Strengths

Cachet's biggest advantage is maturity. It has been production-tested for over a decade, has extensive documentation, and a large community. The Laravel foundation makes it easy to customize and extend with plugins. The built-in metrics system lets you plot custom data points like request latency, error rates, or queue depth directly on your status page.

### Limitations

- Requires a PHP environment (Apache/Nginx + PHP-FPM + database)
- The original project was archived in 2020, but the community fork [Cachet HQ](https://github.com/cachethq/Cachet) keeps it maintained
- No built-in monitoring — you must push metrics from external tools
- Heavier resource footprint compared to lightweight alternatives

### Docker Deployment

```yaml
# docker-compose.yml for Cachet
version: "3.8"

services:
  cachet:
    image: cachethq/docker:2.4.0
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - APP_DEBUG=false
      - APP_KEY=base64:YOUR_APP_KEY_HERE
      - APP_URL=http://status.example.com
      - DB_DRIVER=sqlite
      - DATABASE_URL=sqlite:///data/database.sqlite
    volumes:
      - cachet-data:/var/www/html/bootstrap/cache
      - cachet-db:/var/www/html/database
    restart: unless-stopped

volumes:
  cachet-data:
  cachet-db:
```

Generate the application key before first run:

```bash
# Generate a random 32-character key
docker run --rm cachethq/docker:2.4.0 php artisan key:generate --show

# Or generate one with OpenSSL
openssl rand -base64 32
```

After starting the containers, access `http://your-server:8000` and complete the setup wizard to create your admin account and configure your first components.

### Pushing Metrics via API

```bash
# Push a custom metric (e.g., API response time)
curl -X POST http://status.example.com/api/v1/metrics/1/points \
  -H "X-Cachet-Token: YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": 142.5,
    "timestamp": "'$(date -u +%Y-%m-%d\ %H:%M:%S)'"
  }'
```

### Creating an Incident

```bash
curl -X POST http://status.example.com/api/v1/incidents \
  -H "X-Cachet-Token: YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "API Degradation",
    "message": "We are experiencing increased latency on our API endpoints. Investigation is underway.",
    "status": 2,
    "visible": 1,
    "component_id": 1,
    "component_status": 3
  }'
```

## Option 2: Statping-ng — Modern Status Page with Built-In Monitoring

[Statping-ng](https://github.com/statping-ng/statping-ng) is the community-maintained fork of the original Statping project. Unlike Cachet, it includes **built-in health monitoring** — it actively checks your services and automatically updates the status page when something goes down.

### Key Features

- **Active Health Checks** — Monitor HTTP, TCP, UDP, ICMP, and gRPC endpoints
- **Automatic Status Updates** — Services go down? The status page updates automatically
- **Incident Timeline** — Automatic incident creation with recovery detection
- **Multi-User Authentication** — Role-based access with OAuth support (Google, GitHub, SAML)
- **Dark/Light Theme** — Built-in theme switching
- **Webhook Integrations** — Send alerts to Slack, Discord, Telegram, email, and custom webhooks
- **SQLite/MySQL/PostgreSQL** — Flexible database backends
- **Docker-First Design** — Minimal configuration required

### Strengths

Statping-ng's killer feature is that it **monitors for you**. You don't need a separate monitoring tool pushing data to your status page — just configure the endpoints you want to track, and Statping-ng handles the rest. It performs health checks on a configurable schedule, creates incidents automatically when services fail, and resolves them when they recover.

The Go-based architecture is lightweight, fast, and compiles to a single binary. It uses significantly less memory than Cachet and starts up in under a second.

### Limitations

- Smaller community than Cachet (though actively maintained)
- Fewer customization options for the UI
- Metrics and charts are less flexible than Cachet's system
- The original project's history of maintainer turnover may concern some users

### Docker Deployment

```yaml
# docker-compose.yml for Statping-ng
version: "3.8"

services:
  statping:
    image: statping/statping-ng:latest
    ports:
      - "8080:8080"
    environment:
      - DB_CONN=sqlite
      - IS_DOCKER=true
    volumes:
      - statping-data:/app/data
    restart: unless-stopped

volumes:
  statping-data:
```

For production with PostgreSQL:

```yaml
version: "3.8"

services:
  statping:
    image: statping/statping-ng:latest
    ports:
      - "8080:8080"
    environment:
      - DB_CONN=postgres
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_USER=statping
      - DB_PASS=secure_password_here
      - DB_DATABASE=statping
      - IS_DOCKER=true
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=statping
      - POSTGRES_PASSWORD=secure_password_here
      - POSTGRES_DB=statping
    volumes:
      - pg-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pg-data:
```

### Configuring Monitors via the UI

After starting Statping-ng, access `http://your-server:8080` and:

1. Create your admin account in the setup wizard
2. Navigate to **Services** → **Add Service**
3. Configure each service you want to monitor:
   - **Name**: Display name (e.g., "Main Website")
   - **URL**: Endpoint to check (e.g., `https://example.com`)
   - **Check Type**: HTTP, TCP, Ping, or gRPC
   - **Interval**: How often to check (e.g., 30 seconds)
   - **Timeout**: Maximum response time before failure
   - **Expected Status Code**: Usually 200
   - **Headers**: Custom headers if needed (e.g., API keys)

### Setting Up Webhook Notifications

```yaml
# Example Slack webhook configuration
# In Statping-ng UI: Notifiers → Add Notifier → Webhook
# URL: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
# Method: POST
# Body template:
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "{{.Service.Name}} is {{.FailString}}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Service: {{.Service.Name}}\nURL: {{.Service.Domain}}\nError: {{.FailReason}}"
      }
    }
  ]
}
```

## Option 3: Upptime — Git-Powered Status Pages

[Upptime](https://upptime.js.org/) takes a radically different approach. Instead of running a dedicated server, it uses **GitHub Actions** to monitor your services and **GitHub Pages** to host the status page. Everything is stored in a Git repository.

### Key Features

- **Zero Server Required** — Runs entirely on GitHub's infrastructure
- **GitHub Actions Monitoring** — Checks run on GitHub's scheduled cron
- **GitHub Pages Hosting** — Static status page hosted for free
- **Automatic Issue Tracking** — Downtime creates GitHub Issues automatically
- **Commit History as Audit Log** — Every status change is a Git commit
- **Multiple Monitor Types** — HTTP, TCP, DNS, and port checks
- **Custom Domains** — Point your own domain to the GitHub Pages site
- **Free Tier** — Completely free with GitHub's generous Action minutes

### Strengths

Upptime is ideal if you want **zero infrastructure overhead**. No servers to maintain, no databases to back up, no Docker containers to update. Everything runs on GitHub: monitoring via Actions, hosting via Pages, and incident tracking via Issues. The Git-based audit trail means every status change is permanently recorded in your commit history.

For open-source projects and small teams already on GitHub, this is the path of least resistance. Setup takes under 5 minutes using the provided template repository.

### Limitations

- **GitHub dependency** — If GitHub has an outage, your status page may be affected
- **Check interval limited** — Minimum 5 minutes (GitHub Actions scheduling)
- **No real-time updates** — Status changes only appear after the next scheduled check
- **Limited customization** — Template-based UI with restricted theming options
- **GitHub Action minutes** — Heavy usage may consume your monthly free quota

### Quick Setup

```bash
# 1. Use the Upptime template
# Go to https://github.com/upptime/upptime and click "Use this template"

# 2. Clone your new repository
git clone https://github.com/YOUR-USERNAME/status-page.git
cd status-page

# 3. Edit the configuration
cat > .upptimerc.yml << 'EOF'
owner: YOUR-GITHUB-USERNAME
repo: status-page

sites:
  - name: Main Website
    url: https://example.com
    expectedStatusCodes:
      - 200
    assignees:
      - YOUR-USERNAME
    headerPrefix: "🟢"
    favicon: "https://example.com/favicon.ico"

  - name: API Server
    url: https://api.example.com/health
    expectedStatusCodes:
      - 200

  - name: Database (TCP)
    url: "tcp://db.example.com:5432"
    expectedStatusCodes: []

status-website:
  cname: status.example.com
  logoUrl: https://example.com/logo.png
  name: Example Status Page
  navbar:
    - title: Home
      href: /
    - title: Documentation
      href: https://docs.example.com
EOF

# 4. Commit and push — GitHub Actions will handle the rest
git add .upptimerc.yml
git commit -m "Configure status page monitors"
git push origin main
```

### Customizing the Status Page

```yaml
# Add to .upptimerc.yml for advanced customization
status-website:
  cname: status.example.com
  name: "Example Infrastructure Status"
  introTitle: "**Status Page** for all Example services"
  introMessage: "Real-time status and historical uptime data."
  favicon: "https://example.com/favicon.ico"
  logoUrl: "https://example.com/logo.svg"
  darkMode: true
  publicCommit: true
  
  # Add custom navigation links
  navbar:
    - title: Status
      href: /
    - title: API Docs
      href: https://docs.example.com
    - title: Support
      href: https://support.example.com
    - title: GitHub
      href: https://github.com/example
```

## Feature Comparison Table

| Feature | Cachet | Statping-ng | Upptime |
|---------|--------|-------------|---------|
| **Cost** | Free (self-hosted) | Free (self-hosted) | Free (GitHub) |
| **Language** | PHP (Laravel) | Go | Node.js (GitHub Actions) |
| **Built-In Monitoring** | ❌ No (API push only) | ✅ Yes (HTTP, TCP, Ping, gRPC) | ✅ Yes (GitHub Actions) |
| **Auto Incident Creation** | ❌ Manual | ✅ Automatic | ✅ Automatic (GitHub Issues) |
| **Status Page Hosting** | Self-hosted | Self-hosted | GitHub Pages |
| **Infrastructure Required** | Server + DB | Server + DB (optional) | None (GitHub) |
| **Custom Domains** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Subscriber Notifications** | ✅ Email, Webhook | ✅ Slack, Discord, Telegram, Webhook | ✅ GitHub Notifications |
| **REST API** | ✅ Full API | ✅ Limited API | ❌ No (Git-based) |
| **Metrics & Charts** | ✅ Custom metrics | ✅ Basic charts | ✅ Response time graphs |
| **Min Check Interval** | N/A (push-based) | 5 seconds | 5 minutes |
| **Dark Mode** | Via theme | ✅ Built-in | ✅ Built-in |
| **Multi-User / Auth** | ✅ Admin dashboard | ✅ OAuth, SAML | ✅ GitHub auth |
| **Incident Timeline** | ✅ Manual entries | ✅ Automatic | ✅ GitHub Issues |
| **Resource Usage** | Medium (PHP-FPM) | Low (single binary) | Zero (serverless) |
| **Setup Complexity** | Medium | Low | Very Low |
| **Best For** | Enterprise, customizable | Self-hosters wanting monitoring | GitHub-based, zero-infra |

## Which Should You Choose?

### Choose Cachet if:
- You need a polished, customizable status page with full API control
- You already have monitoring infrastructure (Prometheus, Datadog, etc.) and just need a presentation layer
- You want metrics charts with custom data points
- Your team is comfortable with PHP/Laravel for customizations
- You need multi-language support out of the box

### Choose Statping-ng if:
- You want an all-in-one solution with built-in monitoring and status page
- You prefer Go-based, low-resource services
- You need active health checks without running a separate monitoring tool
- You want automatic incident creation and recovery detection
- You need Slack, Discord, or Telegram notifications built in

### Choose Upptime if:
- You want zero infrastructure to manage
- You're already invested in the GitHub ecosystem
- Your check interval of 5 minutes is acceptable
- You want a permanent Git-based audit trail of all incidents
- You're running an open-source project or small team

## Running Multiple Status Pages with Docker Compose

Here's a complete setup that runs Cachet and Statping-ng side by side behind a reverse proxy, letting you test both:

```yaml
# docker-compose.yml - Status Page Stack
version: "3.8"

networks:
  status-net:
    driver: bridge

services:
  # Cachet Status Page
  cachet:
    image: cachethq/docker:2.4.0
    container_name: cachet
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - APP_KEY=base64:YOUR_KEY_HERE
      - APP_URL=http://cachet.example.com
      - DB_DRIVER=sqlite
      - DATABASE_URL=sqlite:///data/database.sqlite
    volumes:
      - cachet-data:/var/www/html/bootstrap/cache
      - cachet-db:/var/www/html/database
    networks:
      - status-net
    restart: unless-stopped

  # Statping-ng with Built-In Monitoring
  statping:
    image: statping/statping-ng:latest
    container_name: statping
    ports:
      - "8080:8080"
    environment:
      - DB_CONN=sqlite
      - IS_DOCKER=true
    volumes:
      - statping-data:/app/data
    networks:
      - status-net
    restart: unless-stopped

  # Nginx reverse proxy to route traffic
  nginx:
    image: nginx:alpine
    container_name: status-proxy
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - cachet
      - statping
    networks:
      - status-net
    restart: unless-stopped

volumes:
  cachet-data:
  cachet-db:
  statping-data:
```

```nginx
# nginx.conf - Reverse proxy configuration
upstream cachet {
    server cachet:8000;
}

upstream statping {
    server statping:8080;
}

server {
    listen 80;
    server_name cachet.example.com;

    location / {
        proxy_pass http://cachet;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name statping.example.com;

    location / {
        proxy_pass http://statping;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Integrating with Your Monitoring Stack

For Cachet users who need active monitoring, here's how to connect Prometheus alerts to your status page:

```bash
#!/bin/bash
# prometheus-to-cachet.sh
# Script to push Prometheus alert state to Cachet

CACHET_URL="http://status.example.com/api/v1"
CACHET_TOKEN="YOUR_API_TOKEN"
COMPONENT_ID=1

# Query Prometheus for current alert state
ALERT_STATE=$(curl -s "http://prometheus:9090/api/v1/query?query=up{job='my-service'}" | \
  jq '.data.result[0].value[1]')

if [ "$ALERT_STATE" = "0" ]; then
    # Service is down — create incident
    curl -X POST "$CACHET_URL/incidents" \
      -H "X-Cachet-Token: $CACHET_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Service Down",
        "message": "Prometheus detected service is unreachable.",
        "status": 1,
        "visible": 1,
        "component_id": '"$COMPONENT_ID"',
        "component_status": 4
      }'
else
    # Service is up — push metric
    curl -X POST "$CACHET_URL/metrics/$COMPONENT_ID/points" \
      -H "X-Cachet-Token: $CACHET_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "value": 100
      }'
fi
```

Add this to a cron job or run it from your alertmanager webhook receiver for automatic status updates.

## Final Recommendations

For most self-hosters in 2026, **Statping-ng** offers the best balance of features and simplicity. It monitors your services automatically, updates the status page without manual intervention, and sends alerts through the channels you already use. The single-binary Go architecture means minimal resource usage and easy updates.

If you need maximum customization and API flexibility, **Cachet** remains the gold standard for enterprise status pages. Pair it with your existing monitoring stack, and you get a professional-grade status portal.

For teams that want zero infrastructure to manage, **Upptime** is unbeatable. The GitHub-native approach means your status page is literally part of your codebase — version controlled, reviewed, and deployed through the same workflow as your applications.
