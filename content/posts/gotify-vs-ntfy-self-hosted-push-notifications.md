---
title: "Gotify vs ntfy: Best Self-Hosted Push Notifications 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted push notification services in 2026. Compare Gotify and ntfy for sending instant notifications to your devices without relying on third-party services like Pushbullet or Pushover."
---

Push notifications are the nervous system of a self-hosted infrastructure. They tell you when a backup finishes, when your server disk is nearly full, when a CI/CD pipeline fails, or when someone logs into your services. For years, services like Pushbullet and Pushover dominated this space — but both come with monthly fees, closed source code, and the inherent privacy risk of routing your personal alerts through someone else's servers.

In 2026, the two best self-hosted push notification services are **Gotify** and **ntfy** (pronounced "notify"). Both are open source, free to run, and give you complete control over your notification infrastructure. But they take fundamentally different approaches to solving the same problem.

This guide compares both solutions in depth, provides complete Docker deployment instructions, and helps you choose the right tool for your setup.

## Why Self-Host Your Push Notifications

Before diving into the tools, it's worth understanding why self-hosting notifications matters:

- **Privacy**: Commercial notification services see every alert you send — including password change confirmations, security warnings, and personal messages. Self-hosting keeps this data on your own server.
- **No subscription fees**: Pushover costs $5 one-time per platform, Pushbullet Pro is $3/month. Self-hosted alternatives are free forever.
- **No rate limits**: When you control the server, you set the limits. Sending 10,000 notifications during a migration? No problem.
- **Internal network alerts**: Self-hosted services work entirely on your LAN. You can receive alerts even when your internet connection is down, as long as your local network is up.
- **Integration flexibility**: Both Gotify and ntfy offer simple REST APIs that can be called from any script, cron job, monitoring tool, or application.
- **Regulatory compliance**: If you're managing infrastructure that handles sensitive data (healthcare, finance), routing alerts through third parties may violate compliance requirements.

## Gotify: The Structured Notification Server

Gotify is a mature, well-established push notification server written in Go. It uses a traditional client-server model where applications register on the server and send messages to specific "applications" (which act as notification categories).

### Architecture

Gotify follows a classic multi-user model:

```
┌─────────────┐     REST API     ┌──────────────┐
│  Scripts    │ ────────────────►│              │
│  Cron Jobs  │                  │   Gotify     │
│  Monitoring │ ────────────────►│    Server    │
└─────────────┘                  │              │
                                 └──────┬───────┘
                                        │ WebSocket
                                        ▼
                                 ┌──────────────┐
                                 │   Android    │
                                 │   App /      │
                                 │   Web UI     │
                                 └──────────────┘
```

Each application gets its own API token. Messages are organized by application and priority level (1–10), with customizable icons per application.

### Docker Deployment

Here's a production-ready Docker Compose configuration for Gotify:

```yaml
version: "3"
services:
  gotify:
    image: gotify/server:latest
    container_name: gotify
    restart: unless-stopped
    environment:
      - TZ=UTC
    volumes:
      - ./gotify/data:/app/data
    ports:
      - "8080:80"
    # For production, put behind a reverse proxy and remove the port mapping
```

After starting the container with `docker compose up -d`, visit `http://your-server:8080`. The default credentials are `admin` / `admin` — change these immediately.

### Reverse Proxy Setup (Traefik)

For production use, you'll want TLS and a proper domain:

```yaml
  gotify:
    image: gotify/server:latest
    container_name: gotify
    restart: unless-stopped
    volumes:
      - ./gotify/data:/app/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.gotify.rule=Host(`gotify.example.com`)"
      - "traefik.http.routers.gotify.entrypoints=websecure"
      - "traefik.http.routers.gotify.tls.certresolver=letsencrypt"
      - "traefik.http.services.gotify.loadbalancer.server.port=80"
    networks:
      - web
```

### Sending Notifications

Gotify provides a straightforward REST API. Here's how to send a notification using curl:

```bash
curl -X POST "https://gotify.example.com/message?token=<APP_TOKEN>" \
  -F "title=Backup Complete" \
  -F "message=Daily backup finished successfully. 2.3GB uploaded." \
  -F "priority=5"
```

You can also send JSON payloads for more control:

```bash
curl -X POST "https://gotify.example.com/message?token=<APP_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Disk Warning",
    "message": "/dev/sda1 is at 92% capacity",
    "priority": 8,
    "extras": {
      "client::display": {
        "contentType": "text/markdown"
      }
    }
  }'
```

The `extras` field supports rich formatting, including Markdown rendering and external notification actions.

### Gotify CLI

Gotify ships with an official CLI tool for quick testing and scripting:

```bash
# Install
go install github.com/gotify/cli/v2/gotify@latest

# Configure
gotify init
gotify config

# Send a message
gotify push "Server restart completed at $(date)"
gotify push -t "Alert" -p 8 "High CPU usage detected on node-3"
```

### Gotify Plugins

One of Gotify's standout features is its plugin system. Written in Go and compiled to shared libraries, plugins can extend Gotify's functionality:

- **Gotify WebPush**: Send notifications via the Web Push API (works on iOS via Safari)
- **Gotify Discord/Telegram bridges**: Forward notifications to external services
- **Gotify Matrix**: Bridge to Matrix rooms

Install plugins by placing the `.so` file in Gotify's plugin directory and restarting:

```yaml
volumes:
  - ./gotify/data:/app/data
  - ./gotify/plugins:/app/plugins
environment:
  - GOTIFY_PLUGIN_DIR=/app/plugins
```

## ntfy: The HTTP-Based Simplicity Champion

ntfy takes a radically different approach. Instead of a traditional client-server model with user accounts and applications, ntfy uses a **pub/sub model based on HTTP topics**. You send a message to a topic via HTTP PUT or POST, and any subscriber to that topic receives it instantly.

### Architecture

```
┌─────────────┐    PUT /my-topic    ┌──────────────┐
│  Scripts    │ ───────────────────►│              │
│  Cron Jobs  │                     │     ntfy     │
│  Monitoring │ ───────────────────►│    Server    │
└─────────────┘                     │              │
                                    └──────┬───────┘
                                           │ SSE / WebSocket
                                           ▼
                                    ┌──────────────┐
                                    │   Browser    │
                                    │   Mobile App │
                                    │   CLI        │
                                    └──────────────┘
```

No accounts required. No application registration. Just pick a topic name and start publishing and subscribing.

### Docker Deployment

ntfy's Docker setup is even simpler than Gotify's:

```yaml
version: "3"
services:
  ntfy:
    image: binwiederhier/ntfy:latest
    container_name: ntfy
    restart: unless-stopped
    command:
      - serve
    environment:
      - TZ=UTC
    volumes:
      - ./ntfy/cache:/var/cache/ntfy
      - ./ntfy/config:/etc/ntfy
      - ./ntfy/lib:/var/lib/ntfy
    ports:
      - "8080:80"
    user: "1000:1000"
```

Create a configuration file at `./ntfy/config/server.yml`:

```yaml
# ntfy server configuration
base-url: "https://ntfy.example.com"
listen-http: ":80"

# Authentication (optional but recommended)
auth-file: "/var/lib/ntfy/user.db"
auth-default-access: "deny-all"

# Cache and message retention
cache-file: "/var/cache/ntfy/cache.db"
attachment-cache-dir: "/var/cache/ntfy/attachments"
message-timeout: "12h"

# Upstream: connect to the public ntfy.sh for fallback delivery
# upstream-base-url: "https://ntfy.sh"
```

### Reverse Proxy Setup (Nginx)

ntfy works well behind any reverse proxy. Here's an Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name ntfy.example.com;

    ssl_certificate /etc/letsencrypt/live/ntfy.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ntfy.example.com/privkey.pem;

    # Increase client max body size for file attachments
    client_max_body_size 15m;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;

        # WebSocket support (required for real-time delivery)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for real-time message delivery
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### Sending Notifications

ntfy's API is beautifully simple. Send a notification with a single curl command:

```bash
# Basic notification
curl -d "Backup completed at $(date)" ntfy.example.com/my-topic

# With title, priority, and tags
curl \
  -H "Title: Disk Alert" \
  -H "Priority: urgent" \
  -H "Tags: warning,server" \
  -d "Root partition is 94% full on webserver-01" \
  ntfy.example.com/server-alerts

# With JSON body for structured data
curl -H "Content-Type: application/json" \
  -d '{
    "topic": "deployments",
    "message": "Production deploy v2.4.1 succeeded",
    "title": "Deployment Complete",
    "priority": "high",
    "tags": ["rocket", "production"],
    "actions": [
      {
        "action": "view",
        "label": "View Logs",
        "url": "https://ci.example.com/builds/1234"
      }
    ]
  }' \
  ntfy.example.com/deployments
```

The tag system supports [emoji shortcodes](https://ntfy.sh/docs/emojis/), and the `actions` field creates tappable buttons in mobile notifications — for example, linking directly to a dashboard or CI run.

### ntfy CLI and Subscription

Subscribe to topics from the command line to receive messages in real time:

```bash
# Subscribe to a topic (streams messages as they arrive)
ntfy sub my-topic

# Subscribe with auto-completion
ntfy sub -u https://ntfy.example.com server-alerts

# Pipe notifications to other tools
ntfy sub monitoring | grep -i "error" | mail -s "Error Alert" admin@example.com
```

### User Authentication and ACLs

While ntfy works without authentication out of the box, production deployments should enable it:

```bash
# Create admin user
ntfy user add --role=admin admin

# Create regular user
ntfy user add jenkins

# Grant read-write access to a topic
ntfy access jenkins deployments read-write

# Grant read-only access to a group
ntfy access @developers deployments read
```

## Head-to-Head Comparison

| Feature | Gotify | ntfy |
|---------|--------|------|
| **Architecture** | Client-server with user accounts | Pub/sub with HTTP topics |
| **Authentication** | Built-in multi-user system | Optional ACL-based system |
| **API Style** | REST with app tokens | Simple HTTP PUT/POST |
| **Real-time Delivery** | WebSocket | WebSocket + Server-Sent Events |
| **Mobile Apps** | Android only (official) | Android + iOS (official) |
| **Web UI** | Full web interface | Built-in web UI |
| **iOS Support** | Via WebPush plugin only | Native app on App Store |
| **Attachments** | Yes (files, images) | Yes (up to configurable size) |
| **Message Persistence** | SQLite database | File-based cache |
| **Tags/Emojis** | No native tag system | Full emoji shortcode support |
| **Notification Actions** | Limited (via extras) | Full action button support |
| **Upstream Relay** | No | Can relay to public ntfy.sh |
| **Federation** | No | No (but upstream relay exists) |
| **Plugin System** | Go shared libraries | No plugin system |
| **Language** | Go | Go |
| **Resource Usage** | ~50MB RAM | ~30MB RAM |
| **Binary Size** | ~18MB | ~15MB |
| **Maturity** | Since 2018 | Since 2021 |
| **GitHub Stars** | ~12k+ | ~19k+ |

## When to Choose Gotify

Gotify is the better choice when:

- **You need a structured multi-user setup**: Gotify's user and application model provides clear separation. Each team or service gets its own application token, making it easy to audit and revoke access.
- **You want Markdown-formatted messages**: Gotify natively supports Markdown in notification bodies, making alerts more readable.
- **You need extensibility through plugins**: The plugin system allows deep customization, including bridging to other messaging platforms.
- **You prefer a traditional web interface**: Gotify's web UI is polished and provides full message management, user administration, and application configuration.
- **You're already in the Android ecosystem**: The Gotify Android app is mature, reliable, and integrates well with Android's notification system.

### Example: Monitoring Script with Gotify

```bash
#!/bin/bash
# check-disk.sh - Monitor disk usage and alert via Gotify

GOTIFY_URL="https://gotify.example.com"
GOTIFY_TOKEN="your-app-token"
THRESHOLD=90

df -P | awk 'NR>1 {print $5, $6}' | while read usage mount; do
    usage=${usage%\%}
    if [ "$usage" -ge "$THRESHOLD" ]; then
        curl -s -X POST "${GOTIFY_URL}/message?token=${GOTIFY_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{
            \"title\": \"Disk Space Alert\",
            \"message\": \"**${mount}** is at **${usage}%** capacity.\n\nConsider cleaning up or expanding the volume.\",
            \"priority\": 8
          }"
    fi
done
```

## When to Choose ntfy

ntfy is the better choice when:

- **You need iOS support**: ntfy has an official iOS app on the App Store. Gotify requires the WebPush plugin and browser configuration.
- **You want the simplest possible setup**: With ntfy, sending your first notification takes a single curl command. No account creation, no app registration, no token management.
- **You need pub/sub patterns**: ntfy's topic-based model naturally fits event-driven architectures. Multiple services publish to topics; multiple subscribers consume from them.
- **You want emoji tags and action buttons**: ntfy's notification metadata system is richer, with emoji tags, clickable action buttons, and structured JSON payloads.
- **You want upstream relay**: ntfy can relay messages through the public ntfy.sh service, enabling notifications even when your server is temporarily unreachable.
- **You need Server-Sent Events**: ntfy supports both WebSocket and SSE, giving you flexibility in how you consume the event stream. SSE is often easier to work with from browser JavaScript.

### Example: CI/CD Pipeline Notifications with ntfy

```bash
#!/bin/bash
# deploy.sh - Send deployment status via ntfy

NTFY_URL="https://ntfy.example.com"
TOPIC="deployments"

start_time=$(date +%s)
echo "Starting deployment..."

# ... your deployment steps here ...
deploy_result=$?

end_time=$(date +%s)
duration=$((end_time - start_time))

if [ $deploy_result -eq 0 ]; then
    curl -s \
      -H "Title: Deploy Successful" \
      -H "Priority: high" \
      -H "Tags: white_check_mark,rocket" \
      -H "Actions: view, View Pipeline, https://ci.example.com/${BUILD_ID}; view, View Changelog, https://github.com/org/repo/commits/main" \
      -d "Version ${VERSION} deployed to production in ${duration}s" \
      "${NTFY_URL}/${TOPIC}"
else
    curl -s \
      -H "Title: Deploy Failed" \
      -H "Priority: urgent" \
      -H "Tags: x,rotating_light" \
      -H "Actions: view, View Logs, https://ci.example.com/${BUILD_ID}/log" \
      -d "Deployment failed with exit code ${deploy_result}. Check logs immediately." \
      "${NTFY_URL}/${TOPIC}"
    exit 1
fi
```

### Example: Uptime Monitoring Integration

```bash
#!/bin/bash
# ping-monitor.sh - Simple uptime check with ntfy alerts

NTFY_URL="https://ntfy.example.com"
TOPIC="uptime"
TARGETS=("https://example.com" "https://api.example.com" "https://status.example.com")

for url in "${TARGETS[@]}"; do
    status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
    
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
        echo "OK: $url ($status_code)"
    else
        curl -s \
          -H "Title: Service Down" \
          -H "Priority: urgent" \
          -H "Tags: no_entry_sign,$(echo $url | sed 's/[^a-zA-Z0-9]/_/g')" \
          -d "$url returned HTTP $status_code" \
          "${NTFY_URL}/${TOPIC}"
    fi
done
```

## Migration Considerations

If you're currently using Pushbullet or Pushover, migration is straightforward with either tool:

**From Pushover**: Both services support title, message, and priority fields that map directly to Pushover's API. Update your scripts to point to your self-hosted endpoint and swap the token format.

**From Pushbullet**: Pushbullet's device-targeted model maps well to Gotify's application system. If you use Pushbullet's channels, ntfy's topic model is an even closer fit.

For gradual migration, run both services in parallel. Most monitoring tools (Prometheus Alertmanager, Grafana, Uptime Kuma) support custom webhook notifications that work with both Gotify and ntfy.

### Alertmanager Configuration (ntfy)

```yaml
# alertmanager.yml
receivers:
  - name: 'ntfy'
    webhook_configs:
      - url: 'https://ntfy.example.com/alerts'
        send_resolved: true
        http_config:
          headers:
            Title: '{{ .CommonAnnotations.summary }}'
            Priority: '{{ if eq .Status "firing" }}urgent{{ else }}ok{{ end }}'
            Tags: '{{ if eq .Status "firing" }}rotating_light{{ else }}white_check_mark{{ end }}'
```

### Uptime Kuma Integration

Both services work with Uptime Kuma's notification system:

- **Gotify**: Use the Gotify notification type — enter your server URL and app token
- **ntfy**: Use the generic Webhook notification type with a curl-based payload, or use ntfy's webhook compatibility endpoint

## Performance and Resource Usage

Both tools are extremely lightweight, but there are measurable differences:

| Metric | Gotify | ntfy |
|--------|--------|------|
| Idle RAM | ~50MB | ~30MB |
| Binary Size | ~18MB | ~15MB |
| Docker Image | ~45MB | ~35MB |
| SQLite DB Growth | ~1KB per message | ~500B per message |
| Concurrent Connections | 1,000+ (WebSocket) | 10,000+ (SSE) |
| Startup Time | ~1s | ~0.5s |

For a homelab with dozens of services, either tool is negligible. For larger deployments with hundreds of publishers and thousands of subscribers, ntfy's SSE-based architecture handles higher concurrency with lower resource overhead.

## Final Recommendation

**For most homelab users, ntfy is the better choice.** Its topic-based pub/sub model is intuitive, the iOS app support is a significant advantage for mixed-device households, and the single-command API makes scripting trivial. The emoji tags and action buttons make notifications genuinely useful rather than just informational.

**For teams and organizations, Gotify has the edge.** Its structured user/application model, plugin system, and Markdown support make it better suited for environments where access control, auditability, and message formatting matter.

**For the ultimate setup**: run ntfy as your primary notification service for scripts and monitoring, and use Gotify for team-based alerts where user isolation and Markdown formatting are needed. Both can run on the same low-end VPS or Raspberry Pi with minimal resource impact.

The best self-hosted notification service is the one you actually set up. Both Gotify and ntfy can be deployed in under five minutes with Docker — so pick one and start sending yourself alerts today.
