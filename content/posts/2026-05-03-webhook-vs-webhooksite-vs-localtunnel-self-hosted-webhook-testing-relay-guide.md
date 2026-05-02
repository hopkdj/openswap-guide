---
title: "Self-Hosted Webhook Testing & Relay Servers 2026: Webhook vs Webhook.site vs LocalTunnel"
date: 2026-05-03T10:00:00Z
tags: ["webhooks", "webhook-testing", "localtunnel", "reverse-proxy", "self-hosted", "developer-tools", "ngrok-alternative"]
draft: false
---

Testing webhooks locally is notoriously difficult. Your development machine sits behind a NAT, firewall, or carrier-grade network that external services cannot reach. Webhook testing and relay tools solve this by creating a public endpoint that forwards requests to your local development server. This guide compares three self-hosted solutions: **webhook**, **webhook.site**, and **LocalTunnel**.

## What Are Webhook Relay & Testing Tools?

When building integrations with Stripe, GitHub, Slack, or any service that sends webhook notifications, you need a way to receive those callbacks during development. Webhook relay tools create a bridge between the public internet and your local machine, allowing you to test and debug webhook handlers without deploying to a public server.

| Feature | webhook (adnanh) | webhook.site | LocalTunnel |
|---------|-----------------|--------------|-------------|
| **Purpose** | Run commands on webhook events | Visual webhook inspection/debugging | Expose local HTTP server publicly |
| **Stars** | 11,700+ | 6,500+ | 22,200+ |
| **Last Updated** | February 2026 | April 2026 | August 2025 |
| **Primary Language** | Go | JavaScript/TypeScript | JavaScript |
| **Execution Engine** | Runs shell commands on hook | Stores and displays requests | Forwards HTTP traffic |
| **UI Dashboard** | No (CLI/HTTP API only) | Yes (web interface) | No (CLI only) |
| **Custom Domains** | Yes (your own server) | No (webhook.site subdomain) | Yes (your own server) |
| **Self-Hosted** | Yes | Yes (open-source) | Yes |
| **Request Replay** | No | Yes (replay stored requests) | No |
| **HTTPS** | Built-in (Let's Encrypt) | Yes | Via your own proxy |
| **Best For** | Automation, CI/CD triggers | Visual debugging, QA testing | Local development tunneling |

## webhook: The Automation Engine

webhook by adnanh is a lightweight server that triggers shell commands when HTTP requests arrive at configured endpoints. It is designed for automation — CI/CD triggers, deployment hooks, and IoT event handling.

### Configuration

```yaml
# hooks.yaml
- id: deploy-staging
  execute-command: /opt/scripts/deploy.sh
  command-working-directory: /opt/app
  trigger-rule:
    match:
      type: payload-hash-sha256
      secret: "my-secret-key"
      parameter:
        source: header
        name: X-Hub-Signature-256
  response-message: "Deployment triggered"

- id: restart-service
  execute-command: /usr/bin/systemctl restart myapp
  trigger-rule:
    match:
      type: value
      action: equals
      parameter:
        source: payload
        name: action
      value: restart
```

### Docker Deployment

```yaml
version: "3.8"
services:
  webhook:
    image: "almir/webhook:latest"
    ports:
      - "9000:9000"
    volumes:
      - ./hooks.yaml:/etc/webhook/hooks.yaml:ro
      - /opt/scripts:/opt/scripts:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: [
      "-hooks=/etc/webhook/hooks.yaml",
      "-verbose",
      "-hotreload"
    ]
```

### Key Features

- **Hot Reload**: Configuration changes take effect without restart
- **Pass Arguments**: Extract data from webhook payloads and pass as command arguments
- **Secret Validation**: HMAC verification (SHA1, SHA256, SHA512) for secure hooks
- **Output Capture**: Log command stdout/stderr for debugging
- **Middleware Support**: IP whitelisting, header matching, and payload conditions

## webhook.site: Visual Webhook Inspector

webhook.site provides a web interface for inspecting incoming HTTP requests in real-time. Every request is logged with full headers, body, and query parameters. You can also craft custom responses to test how external services handle your replies.

### Self-Hosted Deployment

```yaml
version: "3.8"
services:
  webhook-site:
    image: "webhooksite/webhook.site:latest"
    ports:
      - "8080:80"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

  redis:
    image: "redis:7-alpine"
    ports:
      - "6379:6379"
```

### Key Features

- **Real-Time Inspection**: Watch requests arrive live via WebSocket
- **Request History**: Browse, search, and filter all received requests
- **Custom Responses**: Define response status codes, headers, and body
- **Request Replay**: Re-send captured requests to test handler changes
- **Multiple Endpoints**: Generate unique URLs for different test scenarios

## LocalTunnel: Expose Local Servers

LocalTunnel creates a public URL that forwards all traffic to your local development server. It is the most popular self-hostable ngrok alternative, letting external services reach your localhost during development.

### Usage

```bash
# Install globally
npm install -g localtunnel

# Expose local port 3000 with a custom subdomain
lt --port 3000 --subdomain myapp-dev

# Expose with local server
lt --port 8080 --local-host 127.0.0.1

# Print the public URL
# Your url is: https://myapp-dev.loca.lt
```

### Self-Hosted Server

```bash
# Run your own LocalTunnel server (no dependency on loca.lt)
npm install -g localtunnel-server

# Start the server
lt --port 3000

# The server runs on port 3000
# Clients connect with: lt --port 8080 --host https://your-server.example.com
```

### Docker Deployment

```yaml
version: "3.8"
services:
  lt-server:
    image: "defunctzombie/localtunnel-server:latest"
    ports:
      - "3000:3000"
    environment:
      - LT_PORT=3000
```

### Key Features

- **Zero Configuration**: One command exposes any local HTTP service
- **Custom Subdomains**: Choose memorable URLs for your tunnels
- **Self-Hostable**: Run your own server for full control and no rate limits
- **No Install Required**: Works with npx for one-off usage
- **TCP Forwarding**: Forward any TCP port, not just HTTP

## Comparison: When to Use Each Tool

### Use webhook (adnanh) When:
- You need to **execute commands** on webhook events
- Building **CI/CD pipelines** triggered by GitHub, GitLab, or Bitbucket webhooks
- Automating **server deployments**, container restarts, or notification routing
- You want **HMAC signature verification** for secure hook endpoints

### Use webhook.site When:
- You need to **visually inspect** webhook payloads during development
- Debugging **third-party integrations** (Stripe events, Slack slash commands)
- Testing **custom response handling** by crafting specific HTTP replies
- You need a **request log** for audit or QA purposes

### Use LocalTunnel When:
- You need to **expose a local server** to the public internet
- Testing **OAuth callbacks** that require a public redirect URI
- Developing **mobile app integrations** that hit your local API
- You want a **free ngrok alternative** with self-hosted control

## Why Self-Host Your Webhook Tools?

Running webhook infrastructure on your own servers eliminates dependency on third-party tunneling services that impose rate limits, disconnect after inactivity, or log your traffic. Self-hosted tools give you:

- **Full Privacy**: Webhook payloads never pass through external servers
- **No Rate Limits**: Process unlimited requests without upgrade tiers
- **Custom Domains**: Use your own domain for professional webhook endpoints
- **Persistent History**: Store webhook logs as long as needed for debugging

For related reading, see our [reverse proxy comparison](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-r/) and [API gateway guide](../self-hosted-api-gateway-apisix-kong-tyk-guide/). For webhook management at scale, check our [webhook management platforms comparison](../hook0-vs-svix-vs-hookdeck-self-hosted-webhook-management-guide-2026/).


## Why Self-Host Your Webhook Infrastructure?

Running webhook tooling on your own servers eliminates dependency on third-party tunneling services that impose rate limits, disconnect after inactivity, or log your traffic. Commercial services like ngrok free tier limit you to 20 connections per minute and random subdomains that change every session. Self-hosted alternatives give you unlimited throughput, persistent URLs, and complete privacy.

For development teams building payment integrations, self-hosted webhook tools ensure that sensitive payment data (credit card tokens, PII) never passes through external relay servers. Your webhook payloads stay within your network boundary from the sending service directly to your development machine.

When combined with an internal reverse proxy and certificate management, your webhook testing infrastructure matches production conditions — same TLS termination, same domain names, same network topology. This eliminates the class of bugs that only appear when moving from a tunnel URL to your production domain.

For related reading, see our [reverse proxy comparison](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-r/) and [API gateway guide](../self-hosted-api-gateway-apisix-kong-tyk-guide/). For webhook management at scale, check our [webhook management platforms comparison](../hook0-vs-svix-vs-hookdeck-self-hosted-webhook-management-guide-2026/).

## FAQ

### Is LocalTunnel safe for production use?

LocalTunnel is designed for development and testing. While the self-hosted server is stable, it does not include production-grade features like rate limiting, authentication, or traffic encryption between tunnel endpoints. For production webhook delivery, use a dedicated API gateway or reverse proxy.

### Can webhook (adnanh) handle high-throughput events?

webhook is lightweight and can handle hundreds of requests per second on modest hardware. However, it executes commands synchronously — if your command takes time to run, subsequent requests queue up. For high-throughput scenarios, design your command scripts to be fast and use async processing (write to a queue, process separately).

### How do I secure self-hosted webhook.site?

The open-source webhook.site stores all received requests in Redis. In a self-hosted setup, ensure: (1) Redis is not exposed publicly, (2) you add authentication (reverse proxy with basic auth or OAuth), (3) implement request retention policies to prevent unbounded storage growth.

### Can I use webhook.site and LocalTunnel together?

Yes. A common pattern is to use LocalTunnel to expose your local dev server, then configure the third-party service to send webhooks to your LocalTunnel URL. Use webhook.site in parallel to capture a copy of the same webhooks for inspection.

### What is the difference between webhook and a reverse proxy?

webhook triggers actions (shell commands) based on incoming HTTP requests — it is an automation tool. A reverse proxy (like Nginx or Traefik) forwards requests to backend services without executing commands. They serve different purposes: webhook is for event-driven automation, reverse proxies are for traffic routing.

### Does webhook support HTTPS?

webhook itself does not terminate TLS. You should place it behind a reverse proxy (Nginx, Caddy, Traefik) that handles HTTPS termination. Alternatively, run it on a server with a load balancer that provides TLS termination.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Webhook Testing & Relay Servers 2026: Webhook vs Webhook.site vs LocalTunnel",
  "description": "Compare three self-hosted webhook tools — webhook for automation, webhook.site for visual debugging, and LocalTunnel for exposing local servers. Covers deployment, security, and use cases.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
