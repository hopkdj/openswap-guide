---
title: "Centrifugo vs Mercure vs Soketi: Best Self-Hosted WebSocket Push Server 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "real-time", "websocket"]
draft: false
description: "Compare Centrifugo, Mercure, and Soketi for self-hosted WebSocket push servers. Full feature comparison, Docker configs, and deployment guide for real-time messaging."
---

## Why Self-Host a WebSocket Push Server

Real-time communication is now a baseline requirement for modern web applications. Live chat, collaborative editing, notification feeds, stock tickers, multiplayer dashboards, and IoT telemetry all depend on pushing data to connected clients the moment it becomes available. While managed services like Pusher, PubNub, and Ably solve this problem out of the box, they come with recurring costs, vendor lock-in, and data sovereignty concerns.

Self-hosting a WebSocket push server gives you full control over your real-time infrastructure. You own the data, set your own scaling limits, avoid per-connection or per-message pricing, and keep everything within your network perimeter. For applications handling sensitive user data or requiring guaranteed uptime independent of third-party APIs, self-hosted WebSocket servers are the sensible choice.

In this guide, we compare three leading open-source self-hosted WebSocket push servers: **Centrifugo**, **Mercure**, and **Soketi**. Each takes a different architectural approach to solving the same problem — we'll help you pick the right one for your use case.

## Overview: Three Approaches to Real-Time Push

| Feature | Centrifugo | Mercure | Soketi |
|---------|-----------|---------|--------|
| **Stars** | 10,181 | 5,228 | 5,585 |
| **Language** | Go | Go | TypeScript (Node.js) |
| **Last Updated** | April 2026 | April 2026 | March 2025 |
| **License** | MIT | AGPL-3.0 | MIT |
| **Protocol** | Custom WebSocket + SSE + GRPC + WebTransport | Mercure protocol (SSE over HTTP/2) | Pusher-compatible WebSocket |
| **Transport** | WebSocket, SSE, GRPC, WebTransport, HTTP-streaming | Server-Sent Events (SSE) | WebSocket |
| **Backend** | Redis, NATS, PostgreSQL, Redis Cluster, Tarantool | Built-in BoltDB, optional Mercure hub cluster | Redis |
| **Channels** | Unlimited named channels with wildcards | Topic-based subscriptions | Pusher channel model |
| **Presence** | Yes (user online/offline tracking) | Yes (via subscriber list) | Yes (via Pusher presence channels) |
| **History** | Yes (configurable per-channel) | Via last-event-id reconnection | Limited |
| **Authentication** | JWT, HMAC, anonymous, custom backends | JWT, cookie-based | Pusher app key/secret |
| **[docker](https://www.docker.com/) Image** | `centrifugo/centrifugo` | `dunglas/mercure` | `soketi/soketi` |
| **Best For** | Large-scale PUB/SUB, multi-tenant apps | Web API integration, Symfony ecosystem | Pusher drop-in replacement |

Centrifugo leads in maturity and feature breadth — it is a dedicated PUB/SUB real-time messaging server designed to be language-agnostic with official SDKs for JavaScript, React, React Native, Swift, Kotlin, Flutter, and more. Mercure takes a standards-first approach, implementing its own IETF draft protocol on top of Server-Sent Events, making it exceptionally easy to integrate with any HTTP API framework. Soketi positions itself as a Pusher-compatible server, ideal for teams already using Pusher SDKs who want to self-host without changing client code.

## Centrifugo: Scalable Real-Time Messaging Server

[Centrifugo](https://github.com/centrifugal/centrifugo) is the most feature-complete option in this comparison. Written in Go, it handles hundreds of thousands of concurrent connections on a single node and scales horizontally via Redis or NATS backends. Its design philosophy is "set up once and forget" — you configure the server, connect your application backend via a simple HTTP or GRPC API, and let Centrifugo handle all real-time transport details.

### Key Features

- **Multiple transports**: WebSocket, Server-Sent Events, GRPC, WebTransport, and HTTP-streaming — clients pick what works best for their environment
- **Channel subscriptions**: Named channels with wildcard support (e.g., `news:tech:*`) for fine-grained access control
- **User presence**: Real-time tracking of who is subscribed to which channel
- **Message history**: Per-channel message replay for clients that reconnect after a disconnect
- **Join/leave notifications**: Automatic events when users subscribe or unsubscribe from channels
- **Server-side subscriptions**: Push messages to channels without client-side subscription (useful for notifications)
- **RPC over WebSocket**: Call backend functions from the client via the same WebSocket connection
- **Admin dashboard**: Built-in monitoring UI with connection counts, message rates, and channel stats

### Docker Deployment

```yaml
version: "3.8"

services:
  centrifugo:
    image: centrifugo/centrifugo:latest
    container_name: centrifugo
    ports:
      - "8000:8000"
    command: centrifugo --config=/etc/centrifugo/config.json
    volumes:
      - ./centrifugo-config.json:/etc/centrifugo/config.json:ro
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: centrifugo_redis
    ports:
      - "6379:6379"
    command: redis-server --save "" --appendonly no
    restart: unless-stopped
```

Save as `docker-compose.yml` and create the configuration file:

```json
{
  "token_hmac_secret_key": "your-secret-key-change-this",
  "api_key": "your-api-key-change-this",
  "allowed_origins": ["https://yourdomain.com"],
  "history_meta_ttl": "72h",
  "node_info_metrics_interval": "60s",
  "presence": true,
  "join_leave": true,
  "history_size": 100,
  "history_ttl": "24h",
  "redis": {
    "address": "redis:6379"
  }
}
```

Start with:

```bash
docker-compose up -d
```

### Publishing Messages

Centrifugo uses a simple HTTP API for publishing messages from your application backend:

```bash
curl -X POST http://localhost:8000/api \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-change-this" \
  -d '{
    "method": "publish",
    "params": {
      "channel": "news:tech",
      "data": {
        "title": "New Release: WebSocket Server Comparison",
        "timestamp": "2026-04-19T12:00:00Z"
      }
    }
  }'
```

### Client-Side Connection

On the browser side, use the official JavaScript SDK:

```javascript
import { Centrifuge } from 'centrifuge';

const centrifuge = new Centrifuge('ws://localhost:8000/connection/websocket');

centrifuge.on('connecting', () => console.log('Connecting...'));
centrifuge.on('connected', () => console.log('Connected!'));
centrifuge.on('disconnected', () => console.log('Disconnected'));

const sub = centrifuge.newSubscription('news:tech');
sub.on('publication', (ctx) => {
  console.log('New message:', ctx.data);
  // Update UI with real-time data
});
sub.subscribe();

centrifuge.connect();
```

## Mercure: The Standards-Based Real-Time Protocol

[Mercure](https://github.com/dunglas/mercure) takes a fundamentally different approach. Instead of creating a custom protocol, Mercure is built on top of Server-Sent Events (SSE) — a native browser API that requires zero client-side libraries. The Mercure protocol is standardized as an [IETF Internet-Draft](https://datatracker.ietf.org/doc/draft-dunglas-mercure/), ensuring long-term interoperability.

Created by Kévin Dunglas and sponsored by Les-Tilleuls.coop, Mercure is particularly popular in the PHP/Symfony ecosystem (it ships with API Platform), but its simplicity makes it language-agnostic.

### Key Features

- **SSE-first**: Uses Server-Sent Events, a browser-native API — no client SDK required
- **Authorization built-in**: JWT-based topic authorization at the protocol level
- **Private updates**: Optional encryption so only authorized subscribers can read message content
- **Reconnection support**: `Last-Event-ID` header enables clients to resume after disconnects
- **Hub architecture**: Decoupled from your application — any HTTP server can publish to it
- **Battery-efficient**: SSE connections consume less battery than WebSocket polling on mobile devices
- **Caddy-based**: Built as a Caddy module, inheriting automatic HTTPS, HTTP/2, and HTTP/3 support

### Docker Deployment

```bash
docker run \
  -e MERCURE_PUBLISHER_JWT_KEY='your-secret-key-change-this' \
  -e MERCURE_SUBSCRIBER_JWT_KEY='your-secret-key-change-this' \
  -e MERCURE_EXTRA_DIRECTIVES='cors_origins https://yourdomain.com' \
  -p 3000:3000 \
  -d dunglas/mercure \
  mercure run \
    --config /etc/mercure/Caddyfile.dev \
    --address :3000
```

For a production Docker Compose setup:

```yaml
version: "3.8"

services:
  mercure:
    image: dunglas/mercure:latest
    container_name: mercure
    ports:
      - "3000:3000"
      - "443:443"
    environment:
      - MERCURE_PUBLISHER_JWT_KEY=your-secret-key-change-this
      - MERCURE_SUBSCRIBER_JWT_KEY=your-secret-key-change-this
      - MERCURE_EXTRA_DIRECTIVES=cors_origins https://yourdomain.com
      - SERVER_NAME=:3000
    restart: unless-stopped
```

### Publishing Messages

Mercure uses a standard HTTP POST to the hub's `/publish` endpoint:

```bash
curl -X POST 'http://localhost:3000/.well-known/mercure' \
  -H 'Authorization: Bearer <publisher-jwt-token>' \
  -d 'topic=https://yourdomain.com/books/1' \
  -d 'data={"title":"Updated Title","status":"published"}' \
  -d 'private=true'
```

### Client-Side Connection

The beauty of Mercure is that you need **no library at all** — just the native browser `EventSource` API:

```javascript
const url = new URL('http://localhost:3000/.well-known/mercure');
url.searchParams.append('topic', 'https://yourdomain.com/books/{id}');

const eventSource = new EventSource(url.toString(), {
  withCredentials: true
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update received:', data);
  // Update your UI
};

eventSource.onerror = () => {
  console.error('Connection lost — browser will auto-reconnect');
};
```

For private topics, include the subscriber JWT token as a cookie or query parameter.

## Soketi: Pusher-Compatible Drop-In Replacement

[Soketi](https://github.com/soketi/soketi) is built for teams already using the Pusher SDK who want to migrate to self-hosted infrastructure without rewriting client code. It implements the Pusher protocol, meaning you swap the Pusher endpoint for your Soketi server URL and everything else works identically.

Built on TypeScript and Node.js, Soketi is the youngest of the three options. **Important note**: its last update was in March 2025, which is significantly older than Centrifugo and Mercure. For new projects, consider this a potential maintenance risk.

### Key Features

- **Pusher protocol compatible**: Drop-in replacement — no client code changes needed
- **Horizontal scaling**: Redis-based pub/sub for multi-node deployments
- **Channel types**: Public, private, presence, and private-presence channels
- **Webhooks**: HTTP callbacks for connection events (subscribe, unsubscribe, client events)
- **Laravel integration**: First-class support for Laravel Echo and the Laravel ecosystem
- **Simple configuration**: JSON-based config with sensible defaults

### Docker Deployment

```yaml
version: "3.8"

services:
  soketi:
    image: soketi/soketi:latest
    container_name: soketi
    ports:
      - "6001:6001"
      - "9601:9601"
    environment:
      - SOKETI_DEFAULT_APP_ID=your-app-id
      - SOKETI_DEFAULT_APP_KEY=your-app-key
      - SOKETI_DEFAULT_APP_SECRET=your-app-secret
      - SOKETI_DEFAULT_APP_ENABLE_CLIENT_MESSAGES=true
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    container_name: soketi_redis
    ports:
      - "6379:6379"
    restart: unless-stopped
```

### Publishing Messages

Use the Pusher-compatible HTTP API:

```bash
curl -X POST 'http://localhost:6001/apps/your-app-id/events' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "order-updated",
    "channels": ["orders"],
    "data": {
      "order_id": 1234,
      "status": "shipped",
      "tracking": "ABC123"
    }
  }'
```

### Client-Side Connection (Laravel Echo example)

```javascript
import Echo from 'laravel-echo';
import Pusher from 'pusher-js';

window.Pusher = Pusher;

window.Echo = new Echo({
  broadcaster: 'pusher',
  key: 'your-app-key',
  wsHost: 'localhost',
  wsPort: 6001,
  forceTLS: false,
});

window.Echo.channel('orders')
  .listen('order-updated', (data) => {
    console.log('Order updated:', data);
    // Update UI
  });
```

## Comparison: When to Use Each

| Scenario | Recommendation | Why |
|----------|---------------|-----|
| Large-scale multi-tenant SaaS | **Centrifugo** | Redis/NATS clustering, unlimited channels, presence, history |
| Symfony / API Platform project | **Mercure** | First-class integration, zero client libraries needed |
| Drop-in Pusher replacement | **Soketi** | Pusher-compatible, Laravel Echo support |
| Mobile battery efficiency | **Mercure** | SSE consumes less battery than WebSocket keep-alive |
| Browser-only, no SDKs | **Mercure** | Native `EventSource` API works everywhere |
| Multi-protocol (WS + GRPC + WebTransport) | **Centrifugo** | Only option supporting all four transports |
| Simplest setup | **Mercure** | Single binary, no external dependencies for BoltDB mode |
| Laravel / PHP ecosystem | **Soketi** | Pusher protocol, Lara[kubernetes](https://kubernetes.io/)ompatibility |
| Kubernetes-native deployment | **Centrifugo** | Helm charts, active community, documented K8s patterns |
| IETF-standardized protocol | **Mercure** | Only option with an official IETF draft specification |

## Performance and Scalability

**Centrifugo** is the performance leader. Written in Go with a single-binary design, it routinely benchmarks at 500,000+ concurrent connections per node. Horizontal scaling is achieved through Redis or NATS backends — the Centrifugo team publishes detailed [benchmark results](https://centrifugal.dev/docs/server/engines) showing sub-millisecond message delivery latency across clustered nodes.

**Mercure** also performs well thanks to its Go/Caddy foundation. The SSE-only transport means each connection is a single HTTP/2 or HTTP/3 stream, which is lighter than WebSocket for read-heavy workloads. Mercure's built-in BoltDB storage mode requires no external dependencies, making it the simplest to deploy for small to medium workloads. For high-traffic deployments, Mercure supports PostgreSQL or a custom adapter for distributed setups.

**Soketi** runs on Node.js, which has a lower per-connection memory footprint than some alternatives but generally trails Go-based servers at extreme scale. For most applications (tens of thousands of concurrent connections), Soketi performs perfectly adequately. The Redis-backed clustering model works well for horizontal scaling.

## Security Considerations

All three servers support JWT-based authentication, but their approaches differ:

- **Centrifugo** supports HMAC-signed tokens with flexible claims (user ID, channel access, expiration). It also offers a token verification API for custom backends and anonymous subscription modes for public channels.
- **Mercure** uses separate publisher and subscriber JWT keys, with topic-level authorization encoded in the JWT claims. Private topics are encrypted at the protocol level.
- **Soketi** follows the Pusher app key/secret model. Channels are secured via signed subscription tokens, and private channels require authentication through your application backend.

For production deployments, always enable TLS termination. Centrif[nginx](https://nginx.org/)nd Soketi typically sit behind a reverse proxy (Nginx, Caddy, or Traefik), while Mercure's Caddy foundation includes automatic HTTPS via Let's Encrypt. For related reverse proxy options, see our [Nginx vs Caddy vs Traefik comparison](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/).

## Frequently Asked Questions

### Can I use Mercure with a WebSocket client instead of SSE?

No — Mercure is specifically designed around Server-Sent Events. SSE is a one-way protocol (server to client), which matches Mercure's publish/subscribe model. If you need bidirectional WebSocket communication, Centrifugo or Soketi are better choices. The advantage of SSE is that it works in any modern browser with zero dependencies.

### Does Centrifugo require a Redis backend?

No — Centrifugo can run in standalone (memory-only) mode for development and small deployments. Redis or NATS is only needed for horizontal scaling across multiple Centrifugo nodes. In standalone mode, all state is held in process memory, which is fine for single-node deployments handling up to ~50,000 connections depending on message volume.

### Is Soketi still actively maintained?

Soketi's last release was in March 2025, which is older than both Centrifugo and Mercure. For production-critical applications, this is a consideration. The codebase is stable and functional, but you should evaluate whether the community activity level meets your risk tolerance. Centrifugo and Mercure both show active development as of April 2026.

### Can I migrate from Pusher to Soketi without changing client code?

Yes — this is Soketi's primary value proposition. It implements the Pusher protocol, so you only need to change the WebSocket host and port in your client configuration. Laravel users can update their `broadcasting.php` config to point to their Soketi server. Channels, events, and authentication flows work identically.

### How does Mercure handle reconnection after a network drop?

Mercure leverages the `Last-Event-ID` mechanism built into the SSE specification. When a client reconnects, the browser automatically sends the last received event ID in the request. Mercure uses this to replay any missed events, ensuring no data is lost during transient network failures. This works out of the box with no custom client code.

### Which option supports the most programming languages?

Centrifugo has the broadest SDK coverage with official clients for JavaScript, React, React Native, Swift (iOS), Kotlin (Android), Flutter, Go, Python, Java, Dart, and Swift. Mercure requires no SDK at all — any language with an HTTP client can publish, and any browser can subscribe via the native `EventSource` API. Soketi works with any Pusher SDK, which covers most popular languages.

### Can I use these behind a reverse proxy?

All three support reverse proxy deployments. Centrifugo and Soketi need WebSocket upgrade headers configured in your proxy. For Nginx, this means adding `proxy_set_header Upgrade $http_upgrade` and `proxy_set_header Connection "upgrade"`. Mercure, being SSE-based, works with any standard HTTP reverse proxy without special configuration. If you're deploying behind an API gateway, see our [API gateway comparison](../self-hosted-api-gateway-apisix-kong-tyk-guide/) for proxy options.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Centrifugo vs Mercure vs Soketi: Best Self-Hosted WebSocket Push Server 2026",
  "description": "Compare Centrifugo, Mercure, and Soketi for self-hosted WebSocket push servers. Full feature comparison, Docker configs, and deployment guide for real-time messaging.",
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
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
