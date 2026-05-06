---
title: "Best Self-Hosted ASGI Servers 2026: Hypercorn vs Daphne vs Uvicorn"
date: "2026-05-07"
tags: ["asgi", "python", "web-server", "backend", "self-hosted"]
draft: false
---

The ASGI (Asynchronous Server Gateway Interface) specification is the modern standard for Python web applications, replacing WSGI for async-capable frameworks like FastAPI, Starlette, Django Channels, and Quart. This guide compares three leading ASGI servers: **Hypercorn**, **Daphne**, and **Uvicorn**.

## What Is ASGI and Why Does It Matter?

ASGI is the asynchronous successor to WSGI. While WSGI handles only synchronous HTTP request-response cycles, ASGI supports WebSockets, HTTP/2, server-sent events, and long-lived connections. If your Python application uses async/await, WebSockets, or streaming responses, you need an ASGI server.

The server you choose affects connection handling, HTTP/2 support, WebSocket performance, process management, and deployment complexity. For high-traffic applications or real-time features, the right ASGI server can mean the difference between stable performance and connection drops under load.

## Tool Comparison at a Glance

| Feature | Hypercorn | Daphne | Uvicorn |
|---------|-----------|--------|---------|
| HTTP/2 Support | Yes | Yes | No (via proxy) |
| HTTP/3 Support | Yes (QUIC) | No | No |
| WebSocket | Yes | Yes | Yes |
| ASGI-3 | Yes | Yes | Yes |
| WSGI Support | Yes | No | No |
| TLS Support | Built-in | No (proxy needed) | No (proxy needed) |
| Multi-Process | No (needs manager) | No (needs manager) | No (needs manager) |
| GitHub Stars | 1,563 | 2,665 | 10,635 |
| GitHub Repo | [pgjones/hypercorn](https://github.com/pgjones/hypercorn) | [django/daphne](https://github.com/django/daphne) | [encode/uvicorn](https://github.com/encode/uvicorn) |
| License | MIT | BSD-3-Clause | BSD-3-Clause |
| Maintainer | Individual (pgjones) | Django Project | Encode OSS |
| Python Versions | 3.8+ | 3.8+ | 3.8+ |

## Uvicorn

Uvicorn is the most popular ASGI server, built on uvloop and httptools for maximum performance. It is the default recommendation for FastAPI and Starlette applications.

### Key Features

- **High performance**: Built on uvloop (libuv) and httptools for fast request handling
- **FastAPI default**: Recommended and most commonly used server for FastAPI applications
- **Hot reload**: Built-in file watching for development with automatic restart
- **Lifecycle support**: Full ASGI-3 lifespan protocol for startup and shutdown events
- **Wide ecosystem**: Extensive documentation, community support, and third-party integrations

### Installation

```bash
pip install uvicorn[standard]
```

The `[standard]` extra installs uvloop, httptools, and other performance dependencies.

### Basic Usage

```bash
# Run a FastAPI application
uvicorn main:app --host 0.0.0.0 --port 8000

# With worker processes (requires gunicorn)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Development mode with hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Compose with Gunicorn

```yaml
version: "3.8"
services:
  web:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
    command: >
      gunicorn main:app
      --workers 4
      --worker-class uvicorn.workers.UvicornWorker
      --bind 0.0.0.0:8000
      --access-logfile -
      --error-logfile -
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
```

### Nginx Reverse Proxy Configuration

```nginx
upstream uvicorn_backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://uvicorn_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://uvicorn_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Hypercorn

Hypercorn is an ASGI server developed by the same author as Quart. It supports HTTP/1, HTTP/2, HTTP/3 (QUIC), and WebSockets natively, making it the most protocol-complete ASGI server.

### Key Features

- **HTTP/3 support**: Only ASGI server with native QUIC/HTTP/3 support
- **HTTP/2 support**: Native HTTP/2 without requiring a reverse proxy
- **WSGI compatibility**: Can serve both ASGI and WSGI applications
- **TLS built-in**: Native TLS support without needing a reverse proxy
- **Worker management**: Supports multiple worker types (asyncio, uvloop, Trio)

### Installation

```bash
pip install hypercorn[http3]
```

### Basic Usage

```bash
# Run with HTTP/2 support
hypercorn main:app --bind 0.0.0.0:8000

# With TLS (HTTP/2 automatically enabled)
hypercorn main:app --bind 0.0.0.0:8443 \
  --certfile /path/to/cert.pem \
  --keyfile /path/to/key.pem

# Development mode with reload
hypercorn main:app --reload --bind 0.0.0.0:8000
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  web:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
      - ./certs:/certs:ro
    command: >
      hypercorn main:app
      --bind 0.0.0.0:8443
      --certfile /certs/cert.pem
      --keyfile /certs/key.pem
      --workers 4
    ports:
      - "8443:8443"
    environment:
      - PYTHONUNBUFFERED=1
```

### HTTP/3 Configuration

```bash
# Enable HTTP/3 with QUIC
hypercorn main:app \
  --bind 0.0.0.0:8443 \
  --quic-bind 0.0.0.0:8443 \
  --certfile cert.pem \
  --keyfile key.pem
```

## Daphne

Daphne is the ASGI server developed by the Django project. It was originally built for Django Channels and remains the reference implementation for ASGI-2 and ASGI-3.

### Key Features

- **Django Channels integration**: Purpose-built for Django's async and WebSocket support
- **Reference implementation**: The original ASGI server, closely following the specification
- **Django integration**: Seamless integration with Django's routing and channel layers
- **Stability**: Mature codebase with long-term support from the Django project

### Installation

```bash
pip install daphne
```

### Basic Usage

```bash
# Run a Django Channels application
daphne -b 0.0.0.0 -p 8000 myproject.asgi:application

# With multiple workers (requires supervisor or systemd)
daphne -b 0.0.0.0 -p 8000 myproject.asgi:application
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  web:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
    command: >
      daphne -b 0.0.0.0 -p 8000
      -u /tmp/daphne.sock
      myproject.asgi:application
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=myproject.settings
      - PYTHONUNBUFFERED=1
```

### Django Channels Routing

```python
# myproject/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from myapp import consumers

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/chat/<str:room_name>/", consumers.ChatConsumer),
            path("ws/notifications/", consumers.NotificationConsumer),
        ])
    ),
})
```

## When to Use Each Server

| Scenario | Best Server |
|----------|-------------|
| FastAPI or Starlette application | Uvicorn |
| Django Channels application | Daphne |
| HTTP/2 or HTTP/3 required | Hypercorn |
| Maximum raw performance | Uvicorn |
| Native TLS without reverse proxy | Hypercorn |
| WebSocket-heavy application | Uvicorn or Hypercorn |
| WSGI + ASGI hybrid deployment | Hypercorn |
| Django ecosystem integration | Daphne |
| QUIC/HTTP/3 protocol support | Hypercorn |

## Why Self-Host Your ASGI Server?

Running your own ASGI server gives you complete control over the application lifecycle, connection handling, and deployment architecture. Managed PaaS platforms abstract away server configuration, but they also limit your ability to tune connection pools, customize TLS settings, or deploy HTTP/3 endpoints.

Self-hosted ASGI servers integrate directly with your existing infrastructure — your load balancer, your certificate management, your monitoring stack. You can deploy behind Nginx for static file serving, integrate with Prometheus for metrics collection, and configure custom health check endpoints.

For teams running multiple Python services, self-hosted ASGI servers enable consistent deployment patterns across all applications. Standardize on one server with a shared Docker Compose configuration, shared Nginx templates, and unified logging formats.

For broader application server options, see our [Tomcat vs WildFly vs Gunicorn comparison](../2026-04-27-tomcat-vs-wildfly-vs-gunicorn-self-hosted-application-servers-guide-2026/) and [Nginx Unit vs Gunicorn vs Caddy guide](../2026-05-03-nginx-unit-vs-gunicorn-vs-caddy-self-hosted-application-server-guide-2026/). For web server-level comparisons, our [OpenResty vs Nginx vs Caddy guide](../2026-04-29-openresty-vs-nginx-vs-caddy-self-hosted-web-server-guide-2026/) covers the proxy and serving layer.

## FAQ

### What is the difference between ASGI and WSGI?

WSGI (Web Server Gateway Interface) is the synchronous standard for Python web applications, handling one request at a time. ASGI (Asynchronous Server Gateway Interface) supports asynchronous operations, WebSockets, HTTP/2, and long-lived connections. ASGI is backward-compatible with WSGI applications but adds async capabilities.

### Do I need a reverse proxy with Uvicorn?

Uvicorn does not have built-in TLS support, so you need a reverse proxy (Nginx, Caddy, or Traefik) for HTTPS termination. Hypercorn includes native TLS support, allowing direct HTTPS connections without a proxy. For production deployments, a reverse proxy is recommended regardless for static file serving and connection buffering.

### Can Uvicorn handle WebSockets?

Yes, Uvicorn fully supports WebSockets through the ASGI protocol. FastAPI and Starlette applications using Uvicorn can handle WebSocket connections natively. Configure your reverse proxy to pass the `Upgrade` and `Connection` headers for WebSocket traffic.

### How many workers should I run?

A common starting point is `(2 x CPU cores) + 1` workers. For a 4-core server, start with 9 workers. Monitor memory usage and connection handling to adjust. Each Uvicorn worker is a separate process, so memory consumption scales linearly with worker count.

### Is Hypercorn production-ready?

Yes, Hypercorn is production-ready and used by many organizations. However, it has fewer users than Uvicorn, meaning less community-tested edge case coverage. For most applications, Hypercorn works reliably. The HTTP/3 support is experimental and should be tested thoroughly before enabling in production.

### Which ASGI server has the best performance?

Uvicorn generally delivers the highest raw throughput due to its uvloop and httptools foundation. Benchmarks typically show Uvicorn handling 20-30% more requests per second than Daphne. Hypercorn's performance is close to Uvicorn when using the uvloop worker, with slightly higher latency on HTTP/2 connections.

### Can I use Daphne with FastAPI?

Yes, Daphne can serve any ASGI-3 application including FastAPI. However, Uvicorn is the recommended server for FastAPI and has better integration with FastAPI's features. Daphne is primarily optimized for Django Channels and may require additional configuration for non-Django applications.

### How do I enable HTTP/2 with Uvicorn?

Uvicorn does not support HTTP/2 natively. Enable HTTP/2 through your reverse proxy — Nginx with `http2 on;` directive, or Caddy which enables HTTP/2 automatically with HTTPS. The proxy handles HTTP/2 termination and forwards HTTP/1.1 to Uvicorn.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Best Self-Hosted ASGI Servers 2026: Hypercorn vs Daphne vs Uvicorn",
  "description": "Compare Hypercorn, Daphne, and Uvicorn ASGI servers for self-hosted Python web applications, with Docker Compose deployment guides and performance analysis.",
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
