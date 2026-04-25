---
title: "Twemproxy vs Mcrouter vs Envoy: Self-Hosted Cache Proxy Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "cache", "redis", "memcached", "proxy"]
draft: false
description: "Compare self-hosted cache proxy solutions — Twemproxy, Mcrouter, and Envoy — for Redis and Memcached sharding, connection pooling, and failover. Includes Docker Compose configs and deployment guides."
---

When you run a single Redis or Memcached instance, everything works fine — until it doesn't. As traffic grows, you need to shard across multiple cache backends, pool connections efficiently, and handle failover without application changes. That's where a cache proxy sits between your services and your cache layer, transparently managing routing, sharding, and resilience.

This guide compares three self-hosted cache proxy solutions — **Twemproxy** (nutcracker), **Mcrouter**, and **Envoy** — each representing a different generation of caching infrastructure. Whether you're scaling a Memcached fleet or consolidating Redis clusters behind a single entry point, understanding these tools helps you build a cache architecture that scales without rewriting application code.

## Why Self-Host a Cache Proxy

A cache proxy solves several operational problems that become painful at scale:

- **Connection pooling** — Hundreds of application instances each opening connections to cache servers wastes file descriptors and memory. A proxy consolidates connections.
- **Consistent hashing / sharding** — Distribute keys across multiple cache backends so no single server becomes a bottleneck.
- **Automatic failover** — When a cache node dies, the proxy reroutes traffic to healthy backends without application-side retry logic.
- **Protocol translation** — Some proxies can translate between Redis and Memcached protocols, or add TLS to plaintext cache connections.
- **Centralized monitoring** — One proxy layer means one place to observe cache hit rates, latency, and error counts across your entire cache fleet.

Running these proxies yourself (rather than using managed cloud services) keeps your cache traffic within your network, eliminates egress costs, and gives you full control over configuration and failover behavior.

## Twemproxy (Nutcracker)

**Twemproxy** (also known as *nutcracker*) was created by Twitter and released as open source in 2012. It is a fast, lightweight proxy for Memcached and Redis that implements consistent hashing for automatic key distribution.

| Attribute | Detail |
|---|---|
| GitHub | [twitter/twemproxy](https://github.com/twitter/twemproxy) |
| Stars | ~12,300 |
| Language | C |
| Last Active | March 2024 |
| Protocols | Memcached, Redis |
| Hashing | ketama, md5, murmur, hsieh, fnv1a_64 |
| Connections | Persistent, with auto ejection of failed servers |

Twemproxy is the pioneer of the cache proxy category. Its configuration is simple YAML-based, it supports multiple hash distributions (including the popular Ketama algorithm), and it automatically ejects failed servers from the pool for a configurable timeout period.

### When to Use Twemproxy

- You need a lightweight, battle-tested Redis/Memcached proxy with minimal resource overhead
- Your sharding needs are straightforward: consistent hashing across a static pool of backends
- You want a proxy written in C with near-zero overhead and sub-millisecond latency impact
- You're comfortable with a project that is effectively in maintenance mode

### Twemproxy Docker Compose Configuration

```yaml
version: "3.8"

services:
  twemproxy:
    image: yowainwright/twemproxy:latest
    container_name: twemproxy
    ports:
      - "22122:22122"
    volumes:
      - ./nutcracker.yml:/etc/nutcracker/nutcracker.yml:ro
    depends_on:
      - redis1
      - redis2
    networks:
      - cache-net

  redis1:
    image: redis:7-alpine
    container_name: redis1
    networks:
      - cache-net

  redis2:
    image: redis:7-alpine
    container_name: redis2
    networks:
      - cache-net

networks:
  cache-net:
    driver: bridge
```

Configuration file (`nutcracker.yml`):

```yaml
redis_pool:
  listen: 0.0.0.0:22122
  hash: fnv1a_64
  distribution: ketama
  auto_eject_hosts: true
  redis: true
  timeout: 400
  server_retry_timeout: 30000
  server_failure_limit: 3
  servers:
    - redis1:6379:1
    - redis2:6379:1
```

This configuration pools two Redis backends behind a single listener on port 22122. Keys are distributed using the FNV-1a hash with Ketama consistent hashing, ensuring that when servers are added or removed, only a minimal subset of keys are remapped.

### Installing Twemproxy from Source

```bash
apt-get update && apt-get install -y \
    git build-essential autoconf automake libtool

git clone https://github.com/twitter/twemproxy.git
cd twemproxy
autoreconf -fvi
./configure --enable-debug=log
make
src/nutcracker -h
```

## Mcrouter

**Mcrouter** was developed by Meta (Facebook) to manage their massive Memcached deployment — tens of thousands of instances across multiple data centers. It is a Memcached protocol router that provides advanced routing capabilities beyond simple consistent hashing.

| Attribute | Detail |
|---|---|
| GitHub | [facebook/mcrouter](https://github.com/facebook/mcrouter) |
| Stars | ~3,300 |
| Language | C++ |
| Last Active | April 2026 |
| Protocols | Memcached only |
| Routing | Prefix-based, all-fastest, all-sync, pool routing |
| Failover | Miss failover, warmup, automatic reconnection |

Mcrouter's standout feature is its **prefix-based routing** — you can route different key prefixes to entirely different backend pools. This enables gradual migration (split traffic between old and new clusters), region-aware routing, and complex topologies that Twemproxy cannot express.

### Mcrouter Routing Configurations

```
# /etc/mcrouter/mcrouter.conf
{
  "pools": {
    "pool_a": {
      "servers": [
        "10.0.0.1:11211",
        "10.0.0.2:11211"
      ]
    },
    "pool_b": {
      "servers": [
        "10.0.1.1:11211",
        "10.0.1.2:11211"
      ]
    }
  },
  "route": {
    "type": "OperationSelectorRoute",
    "operation_policies": {
      "add": "AllFastest|Pool|pool_a",
      "delete": "AllFastest|Pool|pool_a",
      "get": "LatestRoute|Pool|pool_a",
      "set": "AllFastest|Pool|pool_a"
    },
    "default_policy": "PoolRoute|pool_a"
  }
}
```

### Prefix-Based Routing for Gradual Migration

```
# /etc/mcrouter/migration.conf
{
  "pools": {
    "old_cluster": {
      "servers": ["10.0.0.1:11211", "10.0.0.2:11211"]
    },
    "new_cluster": {
      "servers": ["10.0.1.1:11211", "10.0.1.2:11211"]
    }
  },
  "route": {
    "type": "PrefixSelectorRoute",
    "prefixes": {
      "new_users:": "PoolRoute|new_cluster",
      "sessions:": "PoolRoute|new_cluster"
    },
    "default": "PoolRoute|old_cluster"
  }
}
```

This routes all keys starting with `new_users:` and `sessions:` to the new cluster, while everything else goes to the old cluster. Change the prefix selectors to shift traffic gradually — a pattern impossible with Twemproxy's flat hashing approach.

### Mcrouter Docker Compose Configuration

```yaml
version: "3.8"

services:
  mcrouter:
    image: memcached/mcrouter:latest
    container_name: mcrouter
    ports:
      - "5000:5000"
    volumes:
      - ./mcrouter.conf:/etc/mcrouter/mcrouter.conf:ro
    command: >
      --port=5000
      --config-file=/etc/mcrouter/mcrouter.conf
      --async-dir=/var/spool/mcrouter
    depends_on:
      - memcached1
      - memcached2
    networks:
      - cache-net

  memcached1:
    image: memcached:1.6-alpine
    container_name: memcached1
    command: memcached -m 256
    networks:
      - cache-net

  memcached2:
    image: memcached:1.6-alpine
    container_name: memcached2
    command: memcached -m 256
    networks:
      - cache-net

networks:
  cache-net:
    driver: bridge
```

## Envoy Proxy (Cache Filter)

**Envoy** is a cloud-native L7 proxy and communication bus originally designed for service meshes. While it's a general-purpose proxy, its extensible filter architecture enables caching capabilities that make it a viable cache proxy for modern deployments.

| Attribute | Detail |
|---|---|
| GitHub | [envoyproxy/envoy](https://github.com/envoyproxy/envoy) |
| Stars | ~27,900 |
| Language | C++ |
| Last Active | April 2026 (daily commits) |
| Protocols | HTTP/2, gRPC, Redis (via extension), TCP |
| Cache | HTTP cache filter, Redis proxy extension, WASM filters |
| Features | mTLS, observability, rate limiting, circuit breaking |

Envoy is the most actively maintained of the three, with daily commits from a massive community. Its **Redis Proxy** filter (`envoy.filters.network.redis_proxy`) provides Redis protocol parsing, connection pooling, and consistent hashing — essentially a cache proxy built into a broader proxy ecosystem.

### Envoy Redis Proxy Configuration

```yaml
# envoy-redis.yaml
static_resources:
  listeners:
    - name: redis_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 6380
      filter_chains:
        - filters:
            - name: envoy.filters.network.redis_proxy
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.redis_proxy.v3.RedisProxy
                stat_prefix: egress_redis
                prefix_routes:
                  routes:
                    - prefix: "user:"
                      cluster: redis_cluster_a
                    - prefix: "session:"
                      cluster: redis_cluster_b
                  catch_all_cluster:
                    name: redis_default
                settings:
                  op_timeout: 5s
                latency_in_micros: true

  clusters:
    - name: redis_cluster_a
      connect_timeout: 1s
      type: STRICT_DNS
      lb_policy: MAGLEV
      load_assignment:
        cluster_name: redis_cluster_a
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: redis-a1
                      port_value: 6379
              - endpoint:
                  address:
                    socket_address:
                      address: redis-a2
                      port_value: 6379

    - name: redis_cluster_b
      connect_timeout: 1s
      type: STRICT_DNS
      lb_policy: MAGLEV
      load_assignment:
        cluster_name: redis_cluster_b
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: redis-b1
                      port_value: 6379

    - name: redis_default
      connect_timeout: 1s
      type: STRICT_DNS
      lb_policy: MAGLEV
      load_assignment:
        cluster_name: redis_default
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: redis-default
                      port_value: 6379
```

### Envoy Docker Compose Configuration

```yaml
version: "3.8"

services:
  envoy:
    image: envoyproxy/envoy:v1.31-latest
    container_name: envoy-cache
    ports:
      - "6380:6380"
      - "9901:9901"
    volumes:
      - ./envoy-redis.yaml:/etc/envoy/envoy.yaml:ro
    networks:
      - cache-net

  redis-a1:
    image: redis:7-alpine
    container_name: redis-a1
    networks:
      - cache-net

  redis-a2:
    image: redis:7-alpine
    container_name: redis-a2
    networks:
      - cache-net

networks:
  cache-net:
    driver: bridge
```

The `9901` port exposes Envoy's admin interface with Prometheus metrics — you get detailed per-route hit rates, latency histograms, and connection statistics out of the box. For related reading on Envoy's broader capabilities, see our [mTLS with Envoy guide](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) and [rate limiting setup](../self-hosted-rate-limiting-api-throttling-nginx-traefik-envoy-kong-guide-2026/).

## Feature Comparison

| Feature | Twemproxy | Mcrouter | Envoy |
|---|---|---|---|
| **Protocol** | Redis + Memcached | Memcached only | Redis + HTTP + TCP + gRPC |
| **Sharding** | Ketama, fnv1a, murmur | Prefix-based routing | Prefix routes + Maglev LB |
| **Connection pooling** | Yes | Yes | Yes (per-cluster) |
| **Auto eject hosts** | Yes (configurable timeout) | No (relies on health checks) | Via outlier detection |
| **Failover** | Server failure limit + retry | Miss failover, warmup | Circuit breaker + retry |
| **TLS support** | No | No | Yes (built-in) |
| **Metrics** | Basic stats via admin port | Async log files | Prometheus, StatsD, tracing |
| **Active development** | Maintenance mode (2024) | Active (Meta) | Very active (daily) |
| **Complexity** | Low (single YAML) | Medium (JSON routing config) | High (full YAML config) |
| **Resource footprint** | Minimal (~5MB RSS) | Moderate (~50MB RSS) | Higher (~100MB+ RSS) |
| **Key migration** | Not supported | Prefix-based routing | Prefix routes |
| **Open source license** | Apache 2.0 | BSD | Apache 2.0 |

## Choosing the Right Cache Proxy

### Choose Twemproxy when:

- You need a dead-simple Redis or Memcached proxy with consistent hashing
- Your backend pool is relatively static (infrequent server additions/removals)
- You want minimal resource overhead — Twemproxy runs comfortably on a 256MB instance
- You don't need TLS or advanced routing logic

Twemproxy remains a solid choice for small-to-medium deployments where the requirements are simple and the proxy just needs to distribute keys evenly.

### Choose Mcrouter when:

- You're running Memcached at scale and need sophisticated routing
- You need gradual migration capabilities (prefix-based traffic splitting)
- You operate across multiple data centers or availability zones
- You want Meta-proven battle-tested routing logic

Mcrouter's prefix routing is unmatched for migration scenarios. If you're moving from one Memcached cluster to another, Mcrouter lets you shift traffic prefix by prefix with zero downtime.

### Choose Envoy when:

- You need a unified proxy that handles caching alongside mTLS, rate limiting, and observability
- You're already running Envoy as a service mesh sidecar or API gateway
- You require TLS termination at the cache proxy layer
- You want rich Prometheus metrics and distributed tracing integration

Envoy is the right choice when the cache proxy is part of a broader infrastructure strategy. Its Redis proxy filter may not have Twemproxy's simplicity, but it integrates seamlessly with the rest of the Envoy ecosystem.

## Performance Considerations

All three proxies add some latency overhead compared to direct cache connections:

- **Twemproxy**: ~0.1-0.3ms added latency — minimal because it's a thin C proxy with no protocol translation overhead
- **Mcrouter**: ~0.2-0.5ms added latency — slightly higher due to its complex routing logic, but negligible in practice
- **Envoy**: ~0.3-0.8ms added latency — highest overhead due to its full L7 filter chain, but includes observability that the others lack

For most applications, sub-millisecond proxy overhead is imperceptible. The benefits of centralized connection management, sharding, and failover far outweigh the tiny latency increase.

## Monitoring Your Cache Proxy

Proper monitoring is essential when a proxy sits between your applications and cache backends. Without visibility, cache failures become application failures.

### Envoy Monitoring (Built-in Prometheus)

```yaml
# Enable Prometheus scraping on Envoy's admin port
admin:
  address:
    socket_address:
      address: 127.0.0.1
      port_value: 9901
  access_log_path: /dev/null
```

```bash
# Scrape metrics
curl -s http://localhost:9901/stats/prometheus | grep redis
```

### Twemproxy Stats

```bash
# Enable stats in nutcracker.yml
stats_addr: 0.0.0.0:22222
stats_interval: 30000

# Query stats
curl -s http://localhost:22222
```

### Mcrouter Logging

```bash
# Enable async logging
mcrouter --config-file=/etc/mcrouter/mcrouter.conf \
         --async-dir=/var/spool/mcrouter \
         --stats_logging_interval=10000 \
         --logdir=/var/log/mcrouter
```

## Related Reading

For related infrastructure guides, see our [database connection pooling comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide-2026/) and the [in-memory data grid guide](../2026-04-22-hazelcast-vs-apache-ignite-vs-infinispan-self-hosted-in-memory-data-grid-guide-2026/) for alternatives to traditional caching. If you're also evaluating cache backends, our [Valkey vs Dragonfly vs Garnet comparison](../valkey-vs-dragonfly-vs-garnet/) covers the modern Redis-compatible options.

## FAQ

### What is the difference between a cache proxy and a cache server?

A cache server (like Redis or Memcached) stores the actual cached data. A cache proxy sits between your applications and cache servers, managing how requests are distributed, pooled, and routed. The proxy doesn't store data itself — it intelligently directs traffic to the right backend servers based on hashing, prefix rules, or load balancing algorithms.

### Can Twemproxy handle Redis Cluster mode?

No. Twemproxy expects standalone Redis instances and implements its own sharding via consistent hashing. It does not understand Redis Cluster's slot-based partitioning. If you need to proxy a Redis Cluster, consider using Envoy's Redis proxy filter or connecting directly to the cluster with a cluster-aware client library.

### Does Mcrouter support Redis protocols?

No. Mcrouter is purpose-built for the Memcached ASCII protocol only. It cannot proxy Redis, HTTP, or any other protocol. If you need Redis proxying, Twemproxy or Envoy are better choices.

### How do I migrate from Twemproxy to Mcrouter or Envoy?

Migration requires careful planning since Mcrouter only speaks Memcached. If you're on Redis, Twemproxy-to-Envoy is the most straightforward path since both support Redis. Update your application connection strings to point to the new proxy, deploy the new proxy alongside Twemproxy, and verify identical behavior before decommissioning the old proxy. Use a load balancer or DNS switch to cut over.

### Is it safe to run a cache proxy in production with only one backend?

Yes, but you lose the main benefits of sharding and failover. A single-backend proxy primarily provides connection pooling and monitoring. For production deployments, at least two cache backends are recommended so the proxy can redistribute traffic when one fails.

### Can I use Envoy's cache filter as a replacement for Redis?

No. Envoy's HTTP cache filter caches HTTP responses — it is not a general-purpose key-value cache. For Redis/Memcached proxying, use Envoy's `redis_proxy` network filter. Envoy does not store data; it only routes and manages connections to your actual cache backends.

### How does Twemproxy handle server failures?

Twemproxy uses `auto_eject_hosts: true` combined with `server_failure_limit` and `server_retry_timeout`. When a backend fails to respond `server_failure_limit` times consecutively, Twemproxy removes it from the pool for `server_retry_timeout` milliseconds, then attempts to reconnect. During ejection, keys that would hash to that server are not served — unlike Mcrouter which can fail over to alternative backends.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Twemproxy vs Mcrouter vs Envoy: Self-Hosted Cache Proxy Guide 2026",
  "description": "Compare self-hosted cache proxy solutions — Twemproxy, Mcrouter, and Envoy — for Redis and Memcached sharding, connection pooling, and failover. Includes Docker Compose configs and deployment guides.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
