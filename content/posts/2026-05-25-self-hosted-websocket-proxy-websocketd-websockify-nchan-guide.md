---
title: "Self-Hosted WebSocket Proxy & Gateway: websocketd vs Websockify vs Nchan (2026)"
date: "2026-05-25"
tags: ["comparison", "guide", "self-hosted", "networking", "websocket", "proxy"]
draft: false
---

WebSocket proxies bridge the gap between traditional request-response protocols and persistent bidirectional communication. Whether you are exposing a legacy CLI tool as a real-time web API, enabling browser-based VNC access to remote desktops, or building a high-performance pub/sub messaging layer, a WebSocket proxy is the critical infrastructure component that makes it possible.

Cloud-hosted WebSocket relay services charge per-connection fees, impose message size limits, and introduce latency. Self-hosted open-source WebSocket proxies eliminate these constraints and give you full control over connection limits, message routing, and security policies.

This guide compares three distinct approaches to WebSocket proxying: **websocketd** (the stdin/stdout bridge), **Websockify** (the TCP-to-WebSocket translator), and **Nchan** (the Nginx-based pub/sub engine). Each solves a different class of WebSocket problems.

## Why Self-Host WebSocket Infrastructure?

WebSocket connections are long-lived and stateful, making them fundamentally different from HTTP requests. When you route WebSocket traffic through third-party relay services, you introduce a single point of failure, add latency for every message, and lose visibility into connection health metrics.

Self-hosting gives you direct access to connection logs, message throughput statistics, and the ability to customize proxy behavior for your specific protocols. For applications handling sensitive real-time data — financial tickers, IoT telemetry, or collaborative editing — keeping WebSocket traffic within your own network is a security and compliance requirement.

For broader real-time communication needs, see our [WebRTC SFU comparison](../2026-04-15-janus-vs-mediasoup-vs-livekit-self-hosted-webrtc-sfu-guide/). If you need API gateway capabilities alongside WebSocket proxying, our [API gateway plugin ecosystems article](../2026-05-20-self-hosted-api-gateway-plugin-systems-kong-tyk-apishixian-guide/) covers complementary solutions.

## websocketd

websocketd is a small, elegant tool that turns any program using standard input and output into a WebSocket server. It works like inetd for WebSockets — when a client connects, websocketd launches your script and connects its stdin/stdout to the WebSocket stream. When the client disconnects, the process terminates.

### Architecture

websocketd operates as a lightweight daemon that listens on a TCP port for WebSocket upgrade requests. On each connection, it spawns a new instance of your configured program and creates bidirectional pipes between the WebSocket and the program's stdin/stdout. Text data flows directly — what the program writes to stdout is sent as a WebSocket message, and what the client sends arrives on the program's stdin.

The design is intentionally simple: no configuration files, no database, no dependencies beyond a POSIX shell and a C compiler. This simplicity makes it extremely reliable and easy to debug.

### Key Features

- **stdin/stdout bridging** — any CLI program becomes a WebSocket service
- **Process-per-connection** — each client gets an isolated process instance
- **Multiple protocols** — supports WebSocket, HTTP, and CGI modes
- **Static file serving** — can serve HTML/JS files alongside WebSocket endpoints
- **Cross-platform** — single binary, no runtime dependencies
- **Language agnostic** — works with Bash, Python, Node.js, Go, or any executable

### Docker Deployment

```yaml
version: "3.8"
services:
  websocketd:
    image: joewalnes/websocketd:latest
    ports:
      - "8080:8080"
    volumes:
      - ./scripts:/scripts
    command: --port=8080 --dir=/scripts
    restart: unless-stopped
```

Example script (`/scripts/counter.sh`):
```bash
#!/bin/bash
for i in $(seq 1 10); do
    echo "Count: $i"
    sleep 1
done
```

Any client connecting to `ws://localhost:8080/counter.sh` receives 10 incrementing messages.

### GitHub Stats

- **Repository:** joewalnes/websocketd
- **Stars:** 17,454+
- **Last Updated:** April 2026

## Websockify

Websockify is a WebSocket-to-TCP proxy/bridge originally created for noVNC (browser-based VNC access). It allows any TCP-based application — VNC servers, SSH daemons, database connections — to be accessed through a WebSocket connection from a web browser. Unlike websocketd's process-per-connection model, Websockify proxies to pre-existing TCP services.

### Architecture

Websockify listens for WebSocket connections on one port and forwards the bidirectional byte stream to a target TCP address and port. It handles the WebSocket protocol handshake and frames, then transparently relays raw bytes to and from the backend TCP service.

The proxy supports both standalone mode (direct TCP forwarding) and token-based mode (mapping URL tokens to specific backend targets). The token system enables a single Websockify instance to route connections to different backend services based on the connection URL.

### Key Features

- **TCP-to-WebSocket bridge** — proxy any TCP service through WebSocket
- **Token-based routing** — map URL tokens to different backend targets
- **SSL/TLS support** — can terminate HTTPS/WSS connections
- **noVNC integration** — designed for browser-based remote desktop access
- **Python implementation** — easy to modify and extend
- **Multiple backends** — supports pure-Python and C-optimized WebSocket frames

### Docker Deployment

```yaml
version: "3.8"
services:
  vnc-server:
    image: consol/ubuntu-xfce-vnc:latest
    container_name: vnc-backend

  websockify:
    image: mhart/websockify:latest
    ports:
      - "6080:6080"
    command: --web /usr/share/novnc 6080 vnc-server:5900
    depends_on:
      - vnc-server
    restart: unless-stopped
```

This setup exposes a VNC server through a WebSocket connection accessible from any modern browser via noVNC's web interface.

### GitHub Stats

- **Repository:** novnc/websockify
- **Stars:** 4,397+
- **Last Updated:** May 2026

## Nchan

Nchan is an Nginx module that transforms Nginx into a fast, scalable pub/sub messaging server with WebSocket, Server-Sent Events (SSE), and Long-Polling support. Unlike websocketd and Websockify which are point-to-point bridges, Nchan is a full messaging infrastructure layer — publishers send messages to channels, and any number of subscribers receive them in real-time.

### Architecture

Nchan operates as an Nginx module, meaning it runs inside the Nginx worker process and inherits Nginx's event-driven architecture, connection handling, and configuration system. Messages are stored in shared memory segments shared across all Nginx workers, enabling efficient fan-out to thousands of subscribers on the same channel.

The module supports message buffering, channel multiplexing, per-subscriber presence notifications, and message history replay. It can store messages in memory for immediate delivery or persist them to Redis for durability across Nginx restarts.

### Key Features

- **Pub/sub messaging** — publish to channels, subscribe from any protocol
- **Multi-protocol** — WebSocket, SSE, Long-Polling, and HTTP push
- **Nginx integration** — inherits Nginx's performance and configuration
- **Message buffering** — configurable per-channel message history
- **Presence detection** — subscriber join/leave notifications
- **Redis backend** — optional Redis storage for distributed messaging
- **Channel permissions** — access control via Nginx location directives

### Docker Deployment

```yaml
version: "3.8"
services:
  nchan:
    image: wandenberg/nginx-push-stream-module:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
```

Example Nginx configuration with Nchan:
```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    nchan_max_reserved_memory 256m;

    location ~ /pub/(.*) {
        nchan_publisher;
        nchan_channel_id $1;
        nchan_message_timeout 60s;
    }

    location ~ /sub/(.*) {
        nchan_subscriber websocket;
        nchan_channel_id $1;
    }
}
```

Publish: `curl -X POST http://localhost/pub/alerts -d "System alert: high CPU"`
Subscribe: Open `ws://localhost/sub/alerts` in any WebSocket client

### GitHub Stats

- **Repository:** slact/nchan
- **Stars:** 3,063+
- **Last Updated:** February 2026

## Feature Comparison

| Feature | websocketd | Websockify | Nchan |
|---------|-----------|------------|-------|
| **Architecture** | Process-per-connection | TCP-to-WS bridge | Nginx pub/sub module |
| **Protocol** | WebSocket + CGI | WebSocket + TCP | WS, SSE, Long-Poll, HTTP |
| **Communication Model** | Point-to-point | Point-to-point | Pub/sub (fan-out) |
| **Backend Type** | Any executable | Pre-existing TCP service | In-memory/Redis channels |
| **Message Persistence** | None (streaming) | None (streaming) | Buffered + Redis |
| **SSL/TLS** | Via reverse proxy | Built-in | Via Nginx |
| **Scalability** | Limited (process per client) | Moderate | High (Nginx workers) |
| **Best For** | CLI tool webification | Remote desktop (noVNC) | Real-time messaging |
| **Configuration** | Command-line args | Command-line args | Nginx config directives |
| **GitHub Stars** | 17,454+ | 4,397+ | 3,063+ |
| **Language** | C | Python | C (Nginx module) |

## Choosing the Right WebSocket Proxy

**Use websocketd when** you want to expose existing command-line scripts, monitoring tools, or data generators as WebSocket services. Its process-per-connection model means each client gets a fresh execution context — perfect for streaming log output, running periodic diagnostics, or providing interactive shell-like interfaces over the web.

**Use Websockify when** you need to expose TCP-based services (VNC, SSH, databases, custom protocols) to web browsers via WebSocket. Its primary use case is noVNC — giving browser-based remote desktop access — but it works with any TCP service that speaks a text or binary protocol.

**Use Nchan when** you need a pub/sub messaging system with WebSocket delivery. If you have multiple publishers and subscribers, need message history, or want to mix WebSocket with SSE and Long-Polling clients, Nchan's Nginx-based architecture provides the scalability and features that point-to-point bridges cannot.

## Deployment Best Practices

### Reverse Proxy for TLS

All WebSocket proxies should sit behind a TLS-terminating reverse proxy in production:

```nginx
server {
    listen 443 ssl;
    server_name ws.example.com;

    ssl_certificate /etc/ssl/certs/ws.pem;
    ssl_certificate_key /etc/ssl/private/ws.pem;

    location / {
        proxy_pass http://websocketd:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
```

The `proxy_read_timeout 86400s` is critical — WebSocket connections are long-lived and the default 60-second timeout will disconnect idle clients.

### Connection Limits

WebSocket connections consume server resources for their entire lifetime. Set appropriate limits:

```nginx
limit_conn_zone $binary_remote_addr zone=ws_limit:10m;

location /ws/ {
    limit_conn ws_limit 100;
    proxy_pass http://websocket_backend;
}
```

### Monitoring WebSocket Traffic

```bash
# Count active WebSocket connections
ss -tnp | grep ESTAB | grep -c websocket

# Monitor Nchan channel stats
curl http://localhost/nchan_stats

# Track Websockify proxy throughput
# Add logging middleware to the Python proxy
```

## Security Considerations

WebSocket proxies introduce unique security challenges compared to traditional HTTP services. Since connections are persistent, authentication must happen during or immediately after the WebSocket handshake — there is no automatic session management.

- **Authenticate early** — validate tokens or credentials in the first WebSocket message
- **Rate limit connections** — prevent connection exhaustion attacks
- **Validate message sizes** — buffer overflow protection for message relay
- **Use WSS always** — WebSocket traffic is plaintext without TLS
- **Isolate backends** — Websockify targets should be on internal networks only
- **Script sanitization** — websocketd runs user scripts; validate inputs and limit privileges

## FAQ

### Can websocketd run Python or Node.js scripts?

Yes. websocketd launches any executable, so Python scripts (`#!/usr/bin/env python3`), Node.js scripts (`#!/usr/bin/env node`), and compiled binaries all work. The only requirement is that the program reads from stdin and writes to stdout. For Python, use `sys.stdout.write()` with `sys.stdout.flush()` to ensure messages are sent immediately.

### Does Websockify support binary data?

Yes. Websockify transparently relays raw bytes between the WebSocket and TCP connections, so binary protocols (VNC RFB protocol, database wire protocols, custom binary formats) work without modification. The WebSocket framing layer handles the binary/text distinction automatically.

### Can Nchan replace RabbitMQ or Redis Pub/Sub?

Nchan is a lighter-weight alternative for simple pub/sub needs. It does not support message acknowledgment, dead-letter queues, or complex routing patterns like RabbitMQ. However, for real-time notification delivery, live dashboards, and chat applications, Nchan's simplicity and Nginx integration make it an excellent choice. The Redis backend adds message persistence across restarts.

### How do I handle WebSocket reconnection in production?

All three proxies benefit from a reverse proxy with health checks. Configure your load balancer to detect failed WebSocket backends and route new connections to healthy instances. On the client side, implement exponential backoff reconnection with jitter to prevent thundering herd problems when a proxy restarts.

### Is Nchan suitable for IoT device messaging?

Yes, Nchan is well-suited for IoT telemetry. Each device can publish to a device-specific channel (`/pub/device-{id}/telemetry`), and subscribers can listen to individual devices or use channel groups. The in-memory message buffer handles temporary subscriber disconnections, and the Redis backend provides durability for critical telemetry data.

### What is the maximum number of concurrent WebSocket connections?

websocketd is limited by process creation overhead — typically hundreds to low thousands per server. Websockify handles thousands with its async Python model. Nchan, running inside Nginx event-driven architecture, can handle tens of thousands of concurrent connections on modest hardware, limited primarily by file descriptor limits and memory for message buffers.

## Why Self-Host Your WebSocket Proxy?

Self-hosting WebSocket infrastructure eliminates vendor lock-in, reduces per-message costs, and keeps real-time data within your security perimeter. Third-party WebSocket relay services often charge per-connection or per-message fees that scale unfavorably as your user base grows. A self-hosted proxy on a $5 VPS can handle thousands of concurrent connections at a fixed cost.

For real-time application architectures, combine WebSocket proxies with [event-driven Kubernetes tools](../2026-05-07-self-hosted-event-driven-kubernetes-operators-keda-tekton-argoref/) for automatic scaling, and use [API gateway plugins](../2026-05-20-self-hosted-api-gateway-plugin-systems-kong-tyk-apishixian-guide/) for authentication and rate limiting at the edge.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted WebSocket Proxy & Gateway: websocketd vs Websockify vs Nchan (2026)",
  "description": "Compare three open-source WebSocket proxy solutions: websocketd, Websockify, and Nchan. Learn architectures, Docker deployment, and choose the right tool.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
