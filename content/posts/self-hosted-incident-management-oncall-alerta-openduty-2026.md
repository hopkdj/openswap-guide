---
title: "Self-Hosted Incident Management & On-Call Alerting: Grafana OnCall vs Alerta vs OpenDuty (2026)"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "monitoring", "devops"]
draft: false
description: "Compare Grafana OnCall, Alerta, and OpenDuty for self-hosted incident management and on-call rotation. Complete setup guides, feature comparison, and PagerDuty replacement strategies for 2026."
---

## Why Self-Host Your Incident Management?

Commercial on-call and incident management platforms like PagerDuty, Opsgenie, and VictorOps have become prohibitively expensive for small teams and homelab operators. A basic PagerDuty plan starts at $21/user/month and quickly escalates once you need features like incident workflows, status pages, and advanced escalation policies. For a team of five, that is over $1,200 per year — money that could go toward better hardware instead.

Self-hosting your incident management stack solves multiple problems at once:

- **No per-user pricing** — run the software for your entire team without counting seats
- **Unlimited alert volume** — no artificial caps on how many incidents you can process
- **Complete data ownership** — incident histories, response times, and post-mortem notes never leave your infrastructure
- **Deep integration flexibility** — wire in any monitoring tool via webhooks without paying for premium connectors
- **On-prem notification routing** — route alerts through internal Gotify, Ntfy, or Matrix instances that external SaaS tools cannot reach
- **Custom escalation logic** — build multi-tier routing policies that match your exact organizational structure

Whether you manage a production Kubernetes cluster, a homelab with dozens of services, or a small business IT stack, self-hosted incident management gives you enterprise-grade alerting without the enterprise-grade price tag. This guide covers the three most capable open-source options available in 2026.

## What Is Incident Management and On-Call Alerting?

Incident management is the process of detecting, responding to, and resolving service disruptions. A complete incident management system handles three core functions:

1. **Alert aggregation** — collect alerts from multiple monitoring tools (Prometheus, Zabbix, Uptime Kuma, custom scripts) into a single pane of glass
2. **On-call rotation** — automatically route alerts to the right person based on schedules, escalation policies, and team assignments
3. **Incident lifecycle tracking** — log when incidents start, who acknowledges them, what actions were taken, and when they resolve

On-call alerting is the mechanism that ensures someone is always available to respond. It manages rotation schedules (daily, weekly, custom), escalation chains (if the primary person does not respond within 15 minutes, escalate to the secondary), and notification delivery (phone call, SMS, push notification, email, chat message).

Without proper incident management, alerts get lost in Slack channels, nobody knows who is on call, and critical outages go unnoticed until a customer complains. Self-hosted solutions give you the same functionality as PagerDuty and Opsgenie, but running on your own infrastructure.

## Feature Comparison: Grafana OnCall vs Alerta vs OpenDuty

| Feature | Grafana OnCall | Alerta | OpenDuty |
|---------|----------------|--------|----------|
| **License** | Apache 2.0 | Apache 2.0 | MIT |
| **Language** | Python (Django) + React | Python (Flask) + Angular/React | Python (Django) |
| **GitHub Stars** | 1,200+ | 1,400+ | 200+ |
| **Latest Release** | Actively developed | Actively developed | Community maintained |
| **On-Call Schedules** | ✅ Full rotation management | ⚠️ Manual assignment | ✅ Basic rotations |
| **Escalation Policies** | ✅ Multi-tier, time-based | ✅ Rule-based routing | ⚠️ Limited |
| **Alert Deduplication** | ✅ Automatic | ✅ Correlation engine | ❌ None |
| **Alert Sources** | 30+ integrations | 50+ integrations | ~10 integrations |
| **Slack Integration** | ✅ Native | ✅ Native | ❌ |
| **Telegram Integration** | ✅ Native | ⚠️ Via webhook | ❌ |
| **Phone/SMS Calls** | ✅ Via Twilio, Vonage | ⚠️ Via plugins | ⚠️ Via Twilio |
| **Mobile App** | ✅ iOS and Android | ❌ Web only | ❌ |
| **API** | ✅ REST | ✅ REST | ✅ REST |
| **Multi-Tenant** | ✅ Teams and organizations | ✅ Customers and environments | ❌ |
| **Post-Mortem/Blameless** | ✅ Built-in notes | ⚠️ Via annotations | ❌ |
| **Status Page** | ⚠️ Via Grafana | ❌ | ❌ |
| **Docker Support** | ✅ Official images | ✅ Official images | Community images |
| **Prometheus Integration** | ✅ Native | ✅ Native | ❌ |
| **Database** | PostgreSQL, MySQL, SQLite | PostgreSQL, MongoDB | PostgreSQL, MySQL |
| **Complexity** | Medium-High | Medium | Low |

### Choosing the Right Tool

- **Grafana OnCall** — Best overall choice if you already use Grafana or want the most feature-complete PagerDuty replacement. Excellent for teams that need proper on-call schedules, escalation policies, and mobile push notifications.

- **Alerta** — Best for high-volume alert environments that need powerful deduplication and correlation. Ideal if you run multiple monitoring systems and need to consolidate thousands of alerts into actionable incidents.

- **OpenDuty** — Best for simple setups that need basic on-call rotation without complexity. Good for small teams or homelab users who want lightweight PagerDuty-like functionality with minimal infrastructure.

## Grafana OnCall: Complete Self-Hosted Setup Guide

Grafana OnCall is the most feature-rich open-source incident management platform. It provides on-call schedules, escalation chains, alert grouping, and direct integration with the Grafana ecosystem. It is the closest open-source equivalent to PagerDuty available today.

### Architecture Overview

Grafana OnCall consists of three main components:

- **Engine** — Django-based backend that handles schedules, escalations, and alert processing
- **Celery Workers** — Async task processing for notifications, webhooks, and scheduled jobs
- **UI** — React frontend (can run standalone or embedded in Grafana)

### Docker Compose Deployment

Create a directory for the deployment:

```bash
mkdir -p ~/oncall && cd ~/oncall
```

Create the `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  oncall_engine:
    image: grafana/oncall:latest
    restart: unless-stopped
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_NAME=oncall
      - DATABASE_USER=oncall
      - DATABASE_PASSWORD=oncall_secret_pass
      - DATABASE_HOST=oncall_db
      - DATABASE_PORT=5432
      - RABBITMQ_URI=amqp://oncall:oncall_rabbit@oncall_rabbit:5672
      - SECRET_KEY=replace-with-your-secure-random-key
      - BASE_URL=https://oncall.yourdomain.com
      - CELERY_BROKER_URL=amqp://oncall:oncall_rabbit@oncall_rabbit:5672
    ports:
      - "8080:8080"
    depends_on:
      - oncall_db
      - oncall_rabbit
    networks:
      - oncall_net

  oncall_celery:
    image: grafana/oncall:latest
    restart: unless-stopped
    command: celery -A oncall.settings worker --loglevel=info
    environment:
      - DATABASE_TYPE=postgresql
      - DATABASE_NAME=oncall
      - DATABASE_USER=oncall
      - DATABASE_PASSWORD=oncall_secret_pass
      - DATABASE_HOST=oncall_db
      - DATABASE_PORT=5432
      - RABBITMQ_URI=amqp://oncall:oncall_rabbit@oncall_rabbit:5672
      - SECRET_KEY=replace-with-your-secure-random-key
      - CELERY_BROKER_URL=amqp://oncall:oncall_rabbit@oncall_rabbit:5672
    depends_on:
      - oncall_db
      - oncall_rabbit
    networks:
      - oncall_net

  oncall_db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=oncall
      - POSTGRES_USER=oncall
      - POSTGRES_PASSWORD=oncall_secret_pass
    volumes:
      - oncall_db_data:/var/lib/postgresql/data
    networks:
      - oncall_net

  oncall_rabbit:
    image: rabbitmq:3-management-alpine
    restart: unless-stopped
    environment:
      - RABBITMQ_DEFAULT_USER=oncall
      - RABBITMQ_DEFAULT_PASS=oncall_rabbit
    volumes:
      - oncall_rabbit_data:/var/lib/rabbitmq
    networks:
      - oncall_net

volumes:
  oncall_db_data:
  oncall_rabbit_data:

networks:
  oncall_net:
    driver: bridge
```

Generate a secure secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Replace `replace-with-your-secure-random-key` in the compose file with the output, then start the stack:

```bash
docker compose up -d
```

The engine will be available at `http://localhost:8080`. The default admin credentials are created on first run — check the container logs for the initial setup instructions.

### Configuring On-Call Schedules

After logging in, navigate to **Schedules** to create your first on-call rotation:

1. Click **Create Schedule**
2. Choose rotation type: **Rolling** (fixed shifts that cycle) or **Custom**
3. Set shift length (e.g., 24 hours for daily rotation, 168 hours for weekly)
4. Add team members to the rotation
5. Set the rotation start date and time

You can create multiple layers — for example, a primary on-call layer and a secondary backup layer that only gets notified if the primary does not acknowledge within a specified window.

### Setting Up Escalation Chains

Escalation chains define what happens when an alert fires:

1. Go to **Escalation Chains** → **Create**
2. Name the chain (e.g., "Production Critical")
3. Add escalation steps in order:
   - **Notify user via push** — sends mobile notification to the on-call person
   - **Wait 15 minutes** — give them time to acknowledge
   - **Notify user via SMS** — escalate to phone if no acknowledgment
   - **Notify another user** — escalate to a different team member
   - **Repeat** — loop back to the first step for continuous alerting

### Integrating Prometheus Alerts

Grafana OnCall has native Prometheus integration. Add this to your Prometheus `alertmanager.yml`:

```yaml
route:
  receiver: "oncall"
  group_by: ["alertname", "job"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: "oncall"
    webhook_configs:
      - url: "https://oncall.yourdomain.com/integrations/v1/prometheus/YOUR_INTEGRATION_KEY/"
        send_resolved: true
```

The integration key is generated within Grafana OnCall under **Integrations** → **Prometheus**. Once configured, every Prometheus alert automatically creates an incident in OnCall, respects escalation policies, and notifies the correct on-call engineer.

## Alerta: Complete Self-Hosted Setup Guide

Alerta specializes in high-volume alert consolidation and deduplication. If your monitoring stack generates thousands of alerts per hour from Prometheus, Nagios, Zabbix, and custom scripts, Alerta can reduce noise by correlating related alerts into single incidents.

### Architecture Overview

Alerta consists of:

- **API Server** — Flask-based REST API that receives, processes, and stores alerts
- **Web UI** — Modern single-page application for alert management
- **Database** — PostgreSQL (recommended) or MongoDB for alert storage
- **Plugins** — Extensible plugin system for enrichment, notification, and transformation

### Docker Compose Deployment

```bash
mkdir -p ~/alerta && cd ~/alerta
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  alerta-web:
    image: alerta/alerta-web:latest
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://alerta:alerta_db_pass@alerta-db:5432/monitoring
      - AUTH_REQUIRED=True
      - PROVIDER=basic
      - ADMIN_USERS=admin@yourdomain.com
      - PLUGINS=reject,blackout,normalise,enhance
      - CORS_ORIGINS=https://alerta.yourdomain.com
    ports:
      - "8081:8080"
    depends_on:
      - alerta-db
    networks:
      - alerta_net

  alerta-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=monitoring
      - POSTGRES_USER=alerta
      - POSTGRES_PASSWORD=alerta_db_pass
    volumes:
      - alerta_db_data:/var/lib/postgresql/data
    networks:
      - alerta_net

volumes:
  alerta_db_data:

networks:
  alerta_net:
    driver: bridge
```

Start the deployment:

```bash
docker compose up -d
```

The web UI is available at `http://localhost:8081`. Log in with the admin email configured above. You will be prompted to set a password on first login.

### Alert Deduplication and Correlation

Alerta automatically deduplicates alerts based on `resource`, `event`, and `environment` fields. When the same alert fires repeatedly, Alerta increments a `duplicateCount` counter and updates the `lastReceiveTime` instead of creating a new incident.

To configure deduplication rules, create a plugin file at `/etc/alerta/plugins/custom.py`:

```python
from alerta.plugins import PluginBase
from alerta.models.alert import Alert

class CustomDedup(PluginBase):
    def pre_receive(self, alert: Alert, **kwargs) -> Alert:
        # Merge alerts from the same host with different severity
        if alert.service == ["production"]:
            alert.environment = "prod"
            # Normalize severity: warning -> major, critical -> critical
            if alert.severity == "warning":
                alert.severity = "major"
        return alert

    def post_receive(self, alert: Alert, **kwargs) -> Alert:
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return
```

### Configuring Notification Rules

Alerta sends notifications through its plugin system. To set up email notifications, create `/etc/alerta/alerta.conf`:

```ini
[alerta]
debug = false

[database]
driver = postgres
name = monitoring
host = alerta-db
port = 5432

[email]
type = smtp
enabled = yes
smtp_host = smtp.yourdomain.com
smtp_port = 587
smtp_username = alerts@yourdomain.com
smtp_password = your_email_password
smtp_use_ssl = false
smtp_starttls = true
from = alerts@yourdomain.com

[notifications]
group_alerts = True
group_alert_timeout = 300
```

For Slack integration, install the Slack plugin:

```bash
pip install alerta-slack
```

Then add to the `PLUGINS` environment variable:

```yaml
environment:
  - PLUGINS=reject,blackout,normalise,enhance,slack
  - SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
  - SLACK_CHANNEL=#incidents
```

### Integrating Multiple Alert Sources

Alerta accepts alerts from virtually any source via its REST API. Here is how to send an alert using curl:

```bash
curl -X POST http://localhost:8081/api/alert \
  -H "Content-Type: application/json" \
  -H "Authorization: Key YOUR_API_KEY" \
  -d '{
    "resource": "web-server-01",
    "event": "HighCPU",
    "environment": "production",
    "severity": "critical",
    "service": ["nginx", "web-frontend"],
    "value": "95%",
    "text": "CPU usage exceeded 95% for 5 minutes",
    "tags": ["production", "cpu", "web"],
    "timeout": 3600
  }'
```

You can also integrate with Prometheus Alertmanager by adding this to `alertmanager.yml`:

```yaml
receivers:
  - name: "alerta"
    webhook_configs:
      - url: "http://localhost:8081/api/webhooks/prometheus?api-key=YOUR_API_KEY"
        send_resolved: true
```

## OpenDuty: Lightweight Self-Hosted On-Call Setup

OpenDuty is the simplest of the three options — a Django-based application that provides basic on-call rotation and PagerDuty-compatible escalation. It is ideal for small teams that need straightforward scheduling without the complexity of Grafana OnCall or Alerta.

### Docker Compose Deployment

```bash
mkdir -p ~/openduty && cd ~/openduty
```

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  openduty:
    image: ustream/openduty:latest
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://openduty:od_secret@openduty-db:5432/openduty
      - SECRET_KEY=replace-with-your-secure-key
      - ALLOWED_HOSTS=*
    ports:
      - "8082:8000"
    depends_on:
      - openduty-db
    networks:
      - openduty_net

  openduty-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_DB=openduty
      - POSTGRES_USER=openduty
      - POSTGRES_PASSWORD=od_secret
    volumes:
      - openduty_db_data:/var/lib/postgresql/data
    networks:
      - openduty_net

volumes:
  openduty_db_data:

networks:
  openduty_net:
    driver: bridge
```

Start the stack:

```bash
docker compose up -d
```

### Configuring On-Call Schedules

OpenDuty provides a straightforward schedule interface:

1. Create a **Service** (e.g., "Production Infrastructure")
2. Define a **Schedule** with rotation rules (daily, weekly)
3. Add **Users** to the rotation
4. Configure **Escalation Policies** — define how long to wait before escalating and who to escalate to

The interface is less polished than Grafana OnCall, but it covers the essential functionality: who is on call, when they rotate, and who gets notified if the primary does not respond.

### PagerDuty-Compatible Webhook

One of OpenDuty's strengths is its PagerDuty-compatible API. If you have existing scripts or tools that integrate with PagerDuty, you can often point them at OpenDuty with minimal changes:

```bash
curl -X POST http://localhost:8082/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "service_key": "YOUR_SERVICE_KEY",
    "event_type": "trigger",
    "description": "Database connection pool exhausted",
    "details": {
      "host": "db-primary-01",
      "metric": "connection_pool_usage",
      "value": "100%"
    }
  }'
```

## Reverse Proxy and HTTPS Configuration

All three platforms should run behind a reverse proxy with TLS termination. Here is a Caddy configuration that works for any of them:

```caddy
oncall.yourdomain.com {
    reverse_proxy localhost:8080
    encode gzip
    tls your@email.com
}

alerta.yourdomain.com {
    reverse_proxy localhost:8081
    encode gzip
    tls your@email.com
}

openduty.yourdomain.com {
    reverse_proxy localhost:8082
    encode gzip
    tls your@email.com
}
```

Alternatively, using Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name oncall.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/oncall.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/oncall.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Migrating from PagerDuty

If you are replacing PagerDuty with a self-hosted solution, here is a practical migration path:

### Phase 1: Parallel Running (Week 1-2)

Set up your self-hosted instance alongside PagerDuty. Forward alerts to both systems simultaneously to verify that incidents are created correctly and escalation policies work as expected.

### Phase 2: Schedule Migration (Week 3)

Recreate your on-call schedules in the new system. Export your PagerDuty schedule data via their API and import it into your chosen platform. Grafana OnCall and Alerta both support API-based schedule creation.

### Phase 3: Integration Migration (Week 4)

Update your monitoring tools to send alerts to the new system instead of PagerDuty:

- **Prometheus Alertmanager** — update webhook URLs
- **Zabbix** — change media type to point to the new API
- **Custom scripts** — replace PagerDuty API calls with your new endpoint
- **Third-party services** — update webhook destinations

### Phase 4: PagerDuty Decommission (Week 5)

After running in parallel for a full on-call cycle and verifying that all integrations work, decommission PagerDuty. Keep backups of historical incident data before closing the account.

## Monitoring Your Incident Management System

It is ironic (but essential) to monitor your monitoring system. Add health checks for your incident management platform:

```yaml
# Add to your Uptime Kuma or monitoring stack
- name: "OnCall Engine Health"
  type: http
  url: "https://oncall.yourdomain.com/health/"
  interval: 60
  expected_status: 200

- name: "Alerta API Health"
  type: http
  url: "https://alerta.yourdomain.com/api/health"
  interval: 60
  expected_status: 200

- name: "PostgreSQL Database"
  type: tcp
  host: "localhost"
  port: 5432
  interval: 30
```

## Final Recommendation

For most teams in 2026, **Grafana OnCall** is the best self-hosted incident management platform. It offers the most complete feature set — on-call schedules, escalation policies, mobile apps, and native Grafana integration — under the permissive Apache 2.0 license. If you already run Grafana for dashboards, OnCall integrates seamlessly as a native panel.

Choose **Alerta** if your primary challenge is alert noise and deduplication. Its correlation engine is unmatched among open-source options, and the plugin architecture lets you build custom alert processing pipelines.

Choose **OpenDuty** if you need something simple and lightweight — a basic on-call rotation system for a small team that does not justify the infrastructure overhead of the other two options.

All three platforms eliminate the per-user pricing model that makes PagerDuty expensive. All three keep your incident data on your own servers. And all three can replace PagerDuty entirely with proper configuration and migration planning.
