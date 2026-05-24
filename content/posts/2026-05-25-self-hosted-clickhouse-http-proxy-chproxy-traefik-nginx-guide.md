---
title: "Self-Hosted ClickHouse HTTP Proxy & Load Balancing: CHProxy vs Traefik vs Nginx (2026)"
date: "2026-05-25"
tags: ["clickhouse", "proxy", "load-balancing", "database", "http-proxy"]
draft: false
---

ClickHouse is one of the fastest open-source columnar databases for real-time analytics, but as query volume grows, a single ClickHouse instance becomes a bottleneck. HTTP proxy and load balancing solutions distribute queries across multiple ClickHouse servers, manage connection pooling, enforce rate limits, and provide a single entry point for client applications.

This guide compares three approaches to ClickHouse HTTP proxying: **CHProxy** (purpose-built for ClickHouse), **Traefik** (cloud-native reverse proxy), and **Nginx** (general-purpose HTTP load balancer). We'll cover deployment, routing strategies, rate limiting, and which solution fits your ClickHouse architecture.

## Comparison Overview

| Feature | CHProxy | Traefik | Nginx |
|---------|---------|---------|-------|
| Purpose | ClickHouse-specific | Cloud-native reverse proxy | General HTTP proxy |
| Protocol | HTTP/HTTPS (ClickHouse native) | HTTP, TCP, gRPC | HTTP, TCP, WebSocket |
| Query Routing | User/cluster-aware | Path/host-based | Weight, IP hash, least connections |
| Rate Limiting | Per-user, per-cluster | Middleware-based | Limit_req, limit_conn |
| Caching | Query result caching | Response caching | Proxy cache |
| Health Checks | Built-in (ClickHouse-specific) | Built-in | Active/passive |
| Configuration | YAML | Dynamic (labels, API) | Config file |
| GitHub Stars | 1,460+ | 54,000+ | N/A (core) |
| License | MIT | MIT | BSD |

## CHProxy: Purpose-Built ClickHouse Proxy

CHProxy is an open-source HTTP proxy designed specifically for ClickHouse. It understands ClickHouse's query semantics, user management, and cluster topology — enabling intelligent routing that generic proxies cannot provide.

### Key Features

- **User-Aware Routing**: Routes queries based on ClickHouse user credentials, enforcing per-user quotas
- **Cluster Topology**: Distributes queries across ClickHouse cluster nodes with awareness of shard/replica layout
- **Query Caching**: Caches identical query results to reduce load on ClickHouse servers
- **Rate Limiting**: Configurable rate limits per user, per network, or globally
- **Request Queuing**: Queues requests when all backends are busy instead of returning errors
- **Query Rewrite**: Rewrites queries on the fly (e.g., adding `max_execution_time` limits)

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  chproxy:
    image: contentsquare/chproxy:latest
    container_name: chproxy
    restart: unless-stopped
    ports:
      - "9090:9090"
      - "443:443"
    volumes:
      - ./chproxy.yml:/opt/chproxy/config.yml:ro
      - ./certs:/etc/chproxy/certs:ro
    depends_on:
      - clickhouse-1
      - clickhouse-2

  clickhouse-1:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-1
    restart: unless-stopped
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - ch1-data:/var/lib/clickhouse
    ulimits:
      nofile:
        soft: 262144
        hard: 262144

  clickhouse-2:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-2
    restart: unless-stopped
    ports:
      - "8124:8123"
      - "9001:9000"
    volumes:
      - ch2-data:/var/lib/clickhouse
    ulimits:
      nofile:
        soft: 262144
        hard: 262144

volumes:
  ch1-data:
  ch2-data:
```

`chproxy.yml` configuration:

```yaml
server:
  http:
    listen_addr: ":9090"
    allowed_networks: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

clusters:
  - name: "analytics"
    nodes:
      - "http://clickhouse-1:8123"
      - "http://clickhouse-2:8123"
    users:
      - name: "default"
        to_cluster: "analytics"
        to_user: "default"
        max_concurrent_queries: 100
        max_execution_time: 30s

caches:
  - name: "default_cache"
    dir: "/tmp/chproxy_cache"
    max_size: 500mb
    expire: 1h
```

### When to Choose CHProxy

- You need ClickHouse-aware routing with user and cluster topology awareness
- Query result caching is important for your read-heavy analytics workload
- You want per-user rate limiting and execution time enforcement
- You run a ClickHouse cluster and need intelligent shard/replica distribution

## Traefik as ClickHouse Reverse Proxy

Traefik is a modern, cloud-native reverse proxy and load balancer designed for dynamic service discovery. While not ClickHouse-specific, it excels at routing HTTP traffic with automatic TLS, middleware chains, and Kubernetes-native configuration.

### Key Features

- **Dynamic Configuration**: Automatic backend discovery via Docker labels, Kubernetes CRDs, or Consul
- **Automatic TLS**: Let's Encrypt integration for zero-touch certificate management
- **Middleware Chain**: Compose rate limiting, authentication, header manipulation, and retry logic
- **Dashboard**: Built-in web UI for monitoring routes and backend health

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./dynamic.yml:/etc/traefik/dynamic.yml:ro
      - traefik-acme:/etc/traefik/acme

  clickhouse-1:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-1
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ch1.rule=Host(`ch.example.com`)"
      - "traefik.http.routers.ch1.service=ch1"
      - "traefik.http.services.ch1.loadbalancer.server.port=8123"
      - "traefik.http.routers.ch1.middlewares=ratelimit"
      - "traefik.http.middlewares.ratelimit.ratelimit.average=100"
      - "traefik.http.middlewares.ratelimit.ratelimit.burst=50"
    volumes:
      - ch1-data:/var/lib/clickhouse

  clickhouse-2:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-2
    restart: unless-stopped
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.ch2.rule=Host(`ch.example.com`) && PathPrefix(`/replica2`)"
      - "traefik.http.routers.ch2.service=ch2"
      - "traefik.http.services.ch2.loadbalancer.server.port=8123"
    volumes:
      - ch2-data:/var/lib/clickhouse

volumes:
  traefik-acme:
  ch1-data:
  ch2-data:
```

`traefik.yml` configuration:

```yaml
entryPoints:
  web:
    address: ":80"
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false
  file:
    filename: /etc/traefik/dynamic.yml

api:
  dashboard: true
  insecure: true

log:
  level: INFO
```

### When to Choose Traefik

- You already use Traefik for other services in your stack
- Automatic TLS certificate management is a priority
- You need dynamic backend discovery for ephemeral ClickHouse containers
- You want a unified proxy for both ClickHouse and other HTTP services

## Nginx as ClickHouse Load Balancer

Nginx is the battle-tested HTTP reverse proxy and load balancer used by millions of production systems. While it lacks ClickHouse-specific features, its stability, performance, and flexibility make it a solid choice for simple load balancing scenarios.

### Key Features

- **Proven Reliability**: Decades of production use at massive scale
- **Flexible Load Balancing**: Round-robin, least connections, IP hash, and weighted distribution
- **Connection Pooling**: Keepalive connections to upstream ClickHouse servers
- **SSL Termination**: TLS termination with SNI support
- **Access Logging**: Detailed request logging for audit and analytics

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  nginx:
    image: nginx:latest
    container_name: nginx-ch
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - clickhouse-1
      - clickhouse-2

  clickhouse-1:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-1
    restart: unless-stopped
    volumes:
      - ch1-data:/var/lib/clickhouse

  clickhouse-2:
    image: clickhouse/clickhouse-server:latest
    container_name: clickhouse-2
    restart: unless-stopped
    volumes:
      - ch2-data:/var/lib/clickhouse

volumes:
  ch1-data:
  ch2-data:
```

`nginx.conf` configuration:

```nginx
worker_processes auto;
events {
    worker_connections 4096;
}

http {
    upstream clickhouse_backend {
        least_conn;
        server clickhouse-1:8123 weight=5;
        server clickhouse-2:8123 weight=5;
        keepalive 32;
    }

    server {
        listen 80;
        server_name ch.example.com;

        location / {
            proxy_pass http://clickhouse_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 300s;
            proxy_connect_timeout 10s;

            # Rate limiting
            limit_req zone=ch_rate burst=20 nodelay;
        }

        location = /ping {
            proxy_pass http://clickhouse_backend;
        }
    }

    limit_req_zone $binary_remote_addr zone=ch_rate:10m rate=50r/s;
}
```

### When to Choose Nginx

- You need a simple, reliable load balancer with minimal configuration
- Your team already manages Nginx for other services
- You prefer static configuration over dynamic service discovery
- You need fine-grained control over connection pooling and timeout behavior

## Why Self-Host Your ClickHouse Proxy?

Running a ClickHouse proxy in-house gives you full control over query routing logic, rate limiting policies, and caching behavior. Purpose-built proxies like CHProxy understand ClickHouse's query semantics — they can route queries to specific shards based on user credentials, cache identical query results, and enforce per-user execution time limits that generic proxies cannot provide.

Self-hosted proxy solutions also eliminate the latency and reliability risks of relying on external load balancers. When your proxy runs on the same network as your ClickHouse cluster, query routing adds only milliseconds of overhead. Combined with local query caching, this can reduce overall query latency by 40-60% for repetitive analytics workloads.

For organizations managing multiple ClickHouse clusters, a self-hosted proxy provides a unified entry point that abstracts cluster topology from client applications. As you scale from a single server to a multi-shard, multi-replica deployment, your applications continue connecting to the same proxy endpoint while the proxy handles intelligent routing behind the scenes.

For broader ClickHouse management, see our [ClickHouse Kubernetes operations guide](../2026-05-16-self-hosted-clickhouse-kubernetes-operations-altinity-operator-clickhouse-backup-guide/) and our [ClickHouse management UI comparison](../2026-05-13-self-hosted-clickhouse-management-uis-tabix-clickcat-telescope-guide/). If you need database query routing for MySQL, our [MySQL Router vs MaxScale vs ProxySQL comparison](../2026-05-10-database-query-routing-mysql-router-maxscale-proxysql-guide/) covers MySQL-specific proxy solutions.

## Choosing the Right ClickHouse Proxy

For ClickHouse-native features — user-aware routing, query caching, and per-user rate limiting — CHProxy is the clear choice. It is purpose-built for ClickHouse and understands the database's query semantics in ways generic proxies cannot.

Traefik is the best option if you need a unified proxy for ClickHouse alongside other services, with automatic TLS and dynamic backend discovery. Nginx remains the most reliable choice for simple load balancing when you need proven stability and straightforward configuration.

## FAQ

### What is the difference between CHProxy and a generic reverse proxy?

CHProxy understands ClickHouse's query semantics, user management system, and cluster topology. It can route queries to specific shards based on user credentials, cache identical query results, enforce per-user execution time limits, and queue requests when all backends are busy. Generic proxies like Nginx only distribute HTTP requests without understanding what the queries contain.

### Does CHProxy support HTTPS?

Yes. CHProxy supports TLS termination with configurable certificate and key paths. It can also act as a TLS client when connecting to ClickHouse servers that require encrypted connections.

### Can I use CHProxy with ClickHouse Cloud?

Yes. CHProxy works with any HTTP-accessible ClickHouse endpoint, including managed services like ClickHouse Cloud. Configure the cluster nodes in `chproxy.yml` to point to your managed endpoint URLs.

### How does CHProxy query caching work?

When a client sends a SELECT query, CHProxy computes a hash of the query text and checks if an identical query was recently cached. If a cache hit occurs, CHProxy returns the cached result immediately without forwarding the query to ClickHouse. Cache entries expire based on the configured TTL (time-to-live), and the cache is stored on disk for persistence across restarts.

### Can Nginx do health checks for ClickHouse backends?

Nginx Open Source supports passive health checks — it marks backends as unavailable after connection failures. Nginx Plus adds active health checks that periodically ping the `/ping` endpoint. For most ClickHouse deployments, passive checks are sufficient since ClickHouse's `/ping` endpoint responds within milliseconds.

### Should I use CHProxy with Traefik together?

Yes, this is a common pattern. Traefik handles TLS termination, routing, and external access control, while CHProxy handles ClickHouse-specific query routing, caching, and rate limiting. Traefik forwards traffic to CHProxy, which then distributes queries across ClickHouse cluster nodes.

### How many concurrent queries can CHProxy handle?

CHProxy is designed to handle thousands of concurrent connections. The `max_concurrent_queries` setting per user controls how many queries from each user can execute simultaneously. Excess queries are queued rather than rejected, preventing overload while maintaining service availability.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ClickHouse HTTP Proxy & Load Balancing: CHProxy vs Traefik vs Nginx (2026)",
  "description": "Compare ClickHouse HTTP proxy solutions: CHProxy, Traefik, and Nginx. Includes Docker Compose configs, routing strategies, rate limiting, and query caching comparisons.",
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
