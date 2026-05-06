---
title: "Prometheus Alertmanager vs ntfy vs Gotify: Best Self-Hosted Alert Routing 2026"
date: "2026-05-07"
tags: ["comparison", "guide", "self-hosted", "monitoring", "devops", "notifications"]
draft: false
description: "Compare Prometheus Alertmanager, ntfy, and Gotify for self-hosted alert routing and notification delivery. Learn which open-source alerting platform fits your monitoring stack."
---

Every monitoring system generates alerts — when CPU usage spikes, a disk fills up, or a service crashes. The challenge is not generating alerts but delivering them to the right people through the right channels at the right time. Alert routing infrastructure sits between your monitoring tools and your notification endpoints, handling deduplication, grouping, escalation, and delivery.

Three open-source projects address this problem from different angles: Prometheus Alertmanager provides sophisticated alert routing for the Prometheus ecosystem, ntfy offers a simple HTTP-based push notification server, and Gotify delivers real-time WebSocket-based messaging with a built-in web interface. This guide compares them and shows you how to deploy each one.

## Comparison Table

| Feature | Prometheus Alertmanager | ntfy | Gotify |
|---------|------------------------|------|--------|
| **GitHub Stars** | 8,400+ | 30,000+ | 15,000+ |
| **License** | Apache 2.0 | Apache 2.0 / MPL 2.0 | Apache 2.0 |
| **Language** | Go | Go, Python (client) | Go, Android app |
| **Primary Use** | Alert routing & deduplication | Push notification server | Real-time messaging server |
| **Ingest Protocol** | Prometheus Alert API | HTTP PUT/POST, CLI | HTTP POST, WebSocket |
| **Notification Channels** | Email, PagerDuty, Slack, OpsGenie, Webhook, Pushover, SNS, VictorOps, WeChat | Any webhook, email (via plugins), mobile push, desktop | WebSocket, web UI, Android app |
| **Deduplication** | Yes (alert fingerprints) | No | No |
| **Grouping** | Yes (by labels, time windows) | No | No |
| **Silence/Inhibition** | Yes (silence rules, inhibition rules) | No | No |
| **Escalation** | Via routing tree | Manual | Manual |
| **Multi-tenant** | No | Yes (topic-based) | Yes (user-based) |
| **Message Persistence** | No (alert lifecycle only) | Configurable (disk) | Yes (SQLite) |
| **Authentication** | Basic auth, mTLS | Access tokens per topic | User accounts with JWT |
| **Best For** | Production alert routing | Simple event notifications | Team messaging & alerts |

## Prometheus Alertmanager

Alertmanager is the alert routing and notification engine of the Prometheus ecosystem. It receives alerts from Prometheus (or any compatible source), deduplicates them based on labels, groups related alerts together, applies silence and inhibition rules, and routes them to configured notification receivers.

### Key Features

- **Advanced routing tree**: Route alerts to different receivers based on label matchers. Send critical alerts to PagerDuty, warnings to Slack, and info to email — all from a single Alertmanager instance.
- **Deduplication and grouping**: Alerts with the same labels are grouped into a single notification. Configurable group intervals prevent notification storms during outages.
- **Silence management**: Temporarily mute alerts during maintenance windows. Silences can be created via the web UI or API with label matchers and expiration times.
- **Inhibition rules**: Suppress lower-priority alerts when higher-priority alerts are firing. For example, suppress "disk space low" alerts when "node down" is already firing.
- **Receiver integrations**: Native support for Email, Slack, PagerDuty, OpsGenie, VictorOps, Pushover, Webhook, AWS SNS, WeChat, and Discord.
- **High availability**: Multiple Alertmanager instances form a mesh cluster for redundancy. Alerts are gossip-protocol replicated between instances.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  alertmanager:
    image: prom/alertmanager:latest
    command:
      - "--config.file=/etc/alertmanager/alertmanager.yml"
      - "--storage.path=/alertmanager"
      - "--cluster.peer=alertmanager:9094"
      - "--web.listen-address=:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - am-data:/alertmanager
    ports:
      - "9093:9093"
    networks:
      - alerting

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alert-rules.yml:/etc/prometheus/alert-rules.yml
      - prom-data:/prometheus
    ports:
      - "9090:9090"
    depends_on:
      - alertmanager
    networks:
      - alerting

volumes:
  am-data:
  prom-data:

networks:
  alerting:
    driver: bridge
```

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  smtp_smarthost: "smtp.example.com:587"
  smtp_from: "alerts@example.com"

route:
  receiver: "slack-warnings"
  group_by: ["alertname", "severity"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: "pagerduty-critical"
    - match:
        severity: warning
      receiver: "slack-warnings"
    - match_re:
        service: "database|postgresql"
      receiver: "email-dba"

receivers:
  - name: "slack-warnings"
    slack_configs:
      - channel: "#alerts"
        send_resolved: true
        text: "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"

  - name: "pagerduty-critical"
    pagerduty_configs:
      - service_key: "your-pagerduty-service-key"

  - name: "email-dba"
    email_configs:
      - to: "dba-team@example.com"
        send_resolved: true
```

### When to Choose Alertmanager

Alertmanager is the best choice when you already use Prometheus for monitoring and need sophisticated alert routing. The routing tree, deduplication, and inhibition rules are essential for large-scale environments where hundreds of alerts fire simultaneously during incidents.

## ntfy

ntfy (pronounced "notify") is a simple HTTP-based pub/sub notification server. You send a POST request to a topic URL, and all subscribers to that topic receive the notification. It requires no authentication setup by default (though token-based auth is available), works through any HTTP proxy, and has excellent mobile and desktop clients.

### Key Features

- **HTTP-first design**: Send notifications with a simple `curl -d "message" https://your-ntfy.sh/my-topic`. No SDK, no complex API, just HTTP.
- **Topic-based pub/sub**: Anyone who knows the topic URL can subscribe. Topics are created on first use.
- **Priority levels**: Support for min, low, default, high, and urgent priority levels with configurable notification behavior on mobile.
- **Tags and emojis**: Attach emoji tags to notifications for visual categorization.
- **Message attachments**: Send files, images, and documents along with text notifications.
- **Self-hosted or cloud**: Use the public instance at ntfy.sh or run your own server for full data control.
- **Webhook subscriptions**: Configure ntfy to forward notifications to external webhooks for integration with Slack, Discord, or email.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  ntfy:
    image: binwiederhier/ntfy:latest
    command:
      - "serve"
    environment:
      - NTFY_BASE_URL=https://ntfy.example.com
      - NTFY_CACHE_DURATION=12h
      - NTFY_AUTH_DEFAULT_ACCESS=***
    volumes:
      - ntfy-cache:/var/cache/ntfy
      - ntfy-config:/etc/ntfy
    ports:
      - "8080:80"
    restart: unless-stopped

volumes:
  ntfy-cache:
  ntfy-config:
```

Integration with Prometheus via webhook receiver:

```yaml
# alertmanager.yml snippet for ntfy
receivers:
  - name: "ntfy"
    webhook_configs:
      - url: "http://ntfy:80/alerts"
        send_resolved: true
        max_alerts: 10
```

```yaml
# ntfy server configuration for webhook
# /etc/ntfy/server.yml
base-url: "https://ntfy.example.com"
cache-duration: "12h"
upstream-base-url: "https://ntfy.sh"
```

### When to Choose ntfy

ntfy is the right choice when you need a simple, universal notification transport that works with any HTTP-based system. It is ideal for teams that want to send notifications from scripts, cron jobs, CI pipelines, and monitoring tools without configuring complex integrations.

## Gotify

Gotify is a self-hosted messaging server that provides real-time push notifications via WebSocket. It includes a built-in web interface, Android app, and CLI client. Messages are organized by applications, each with its own API token.

### Key Features

- **Application-based organization**: Each sending application gets a unique token and appears as a separate channel in the web UI.
- **WebSocket delivery**: Real-time message delivery with no polling. The web UI updates instantly when new messages arrive.
- **Priority system**: Messages have priority levels (0-10) that determine notification behavior on the Android client.
- **Web interface**: Clean, responsive web UI for viewing message history, managing applications, and configuring users.
- **Android app**: Native Android client with push notification support, dark mode, and customizable notification channels.
- **Plugins**: Extensible via a plugin system for custom notification channels and integrations.

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  gotify:
    image: gotify/server:latest
    environment:
      - GOTIFY_DEFAULTUSER_NAME=admin
      - GOTIFY_DEFAULTUSER_PASS=admin
      - GOTIFY_SERVER_PORT=80
      - GOTIFY_SERVER_KEEPALIVEPERIODSECONDS=60
    volumes:
      - gotify-data:/app/data
    ports:
      - "8080:80"
    restart: unless-stopped

volumes:
  gotify-data:
```

Configure Gotify as an Alertmanager receiver:

```yaml
# alertmanager.yml
receivers:
  - name: "gotify"
    webhook_configs:
      - url: "http://gotify:80/message?token=YOUR_APP_TOKEN"
        send_resolved: true
```

### When to Choose Gotify

Gotify is the best choice for teams that want a self-hosted messaging platform with a rich web interface and mobile app. It works well as a team notification hub where multiple services send alerts to a shared dashboard.

## Architecture Comparison

### Alertmanager: The Router

Alertmanager is purpose-built for routing. It does not generate alerts — it receives them from Prometheus (or compatible systems) and decides where to send them. The routing tree is the core abstraction: each alert traverses the tree, matching against label selectors until it reaches a receiver.

### ntfy: The Transport

ntfy is a notification transport layer. It does not do alert processing, deduplication, or grouping. It simply delivers messages to subscribers. Its strength is simplicity: any system that can make an HTTP request can send a notification.

### Gotify: The Hub

Gotify is a messaging hub that combines message storage, a web UI, and real-time delivery. It sits between Alertmanager and ntfy in complexity — more structured than ntfy but less sophisticated than Alertmanager for routing.

## Why Self-Host Your Alert Routing?

Self-hosting alert routing infrastructure keeps your incident response data private and under your control. Cloud notification services have rate limits, per-user pricing, and can become single points of failure during outages. Running your own alerting stack means you are not dependent on external services when your infrastructure needs attention most.

Additionally, self-hosted alert routing integrates with existing monitoring stacks without requiring data egress. For regulated environments where alert data contains sensitive information (hostnames, IP addresses, service identifiers), keeping notifications internal is often a compliance requirement.

For building a complete monitoring stack, see our [Prometheus long-term storage guide](../2026-04-27-grafana-mimir-vs-thanos-vs-cortex-self-hosted-prometheus-long-term-storage-guide-2026/) and [comprehensive monitoring comparison](../2026-04-25-hertzbeat-vs-prometheus-vs-netdata-self-hosted-monitoring-guide/) for complementary tools.

## Frequently Asked Questions

### Can I use ntfy or Gotify as a replacement for Alertmanager?

ntfy and Gotify handle notification delivery but not alert routing. They do not deduplicate alerts, group related alerts, or apply silence and inhibition rules. For simple setups where you only need to deliver notifications, they are sufficient. For production environments with complex alert routing requirements, use Alertmanager as the router and ntfy/Gotify as delivery endpoints.

### How does Alertmanager deduplicate alerts?

Alertmanager creates a fingerprint for each alert based on its labels. When multiple Prometheus instances send the same alert (common in HA setups), Alertmanager recognizes the duplicate fingerprint and keeps only one copy. This prevents duplicate notifications during multi-Prometheus deployments.

### Can I send alerts from Alertmanager to ntfy or Gotify?

Yes. Alertmanager supports generic webhook receivers. Configure a webhook receiver pointing to your ntfy topic URL or Gotify application endpoint. This combines Alertmanager's routing intelligence with ntfy's or Gotify's delivery capabilities.

### How do I handle alert fatigue with self-hosted alerting?

Alert fatigue comes from too many low-value notifications. Use Alertmanager's grouping and inhibition rules to consolidate related alerts. Set appropriate repeat intervals so the same alert does not notify repeatedly. Route only critical alerts to synchronous channels (phone, PagerDuty) and warnings to asynchronous channels (email, Slack).

### Is ntfy secure enough for production alerts?

ntfy supports token-based authentication, access control lists per topic, and HTTPS. For production use, always run ntfy behind a reverse proxy with TLS, enable authentication, and use unique topic names. The default access control can be set to deny-all, requiring explicit token grants per topic.

### How do I set up high availability for Alertmanager?

Run multiple Alertmanager instances with the `--cluster.peer` flag pointing to each other. They form a gossip cluster and replicate alert state. Place a load balancer in front of them and configure Prometheus to send alerts to all instances. The Prometheus configuration uses `alert_relabel_configs` to route to the cluster.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Prometheus Alertmanager vs ntfy vs Gotify: Best Self-Hosted Alert Routing 2026",
  "description": "Compare Prometheus Alertmanager, ntfy, and Gotify for self-hosted alert routing and notification delivery in your monitoring stack.",
  "datePublished": "2026-05-07",
  "dateModified": "2026-05-07",
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
