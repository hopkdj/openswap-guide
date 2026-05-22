---
title: "Self-Hosted TCP Load Balancing — HAProxy TCP Mode vs Nginx Stream vs Envoy TCP Proxy"
date: "2026-05-20"
tags: ["networking", "load-balancer", "tcp", "proxy", "self-hosted"]
draft: false
---

While HTTP load balancing gets most of the attention, many critical services operate at the TCP layer — databases, message queues, game servers, and custom protocols. When you need to distribute raw TCP traffic across backend servers without inspecting the application payload, three open-source tools stand out: **HAProxy TCP mode**, **Nginx stream module**, and **Envoy TCP proxy**.

This guide compares all three for TCP-only load balancing scenarios, covering performance, configuration, health checking, and Docker deployment to help you build a reliable layer 4 load balancing infrastructure.

## Why Layer 4 (TCP) Load Balancing Matters

Layer 4 load balancers operate at the transport layer, forwarding TCP connections without parsing the application protocol. This approach offers several advantages over layer 7 (HTTP) load balancing:

- **Protocol agnostic**: Works with any TCP-based service — MySQL, Redis, PostgreSQL, gRPC, custom protocols
- **Lower latency**: No HTTP parsing overhead — direct TCP connection forwarding
- **TLS passthrough**: Backend servers handle encryption; the load balancer sees only encrypted bytes
- **Simpler configuration**: No need to understand application-specific headers or routing rules

For self-hosted infrastructure, TCP load balancing is essential for database clusters, cache pools, and any service that uses a custom TCP protocol.

## Tool Comparison

| Feature | HAProxy TCP Mode | Nginx Stream | Envoy TCP Proxy |
|---|---|---|---|
| GitHub Stars | 6,553 | Part of Nginx (21,000+) | 24,000+ |
| TCP Proxy Support | Native (primary mode) | Via stream module | Native listener filter |
| Health Checks | TCP check, HTTP check, custom | TCP check | TCP, HTTP, gRPC, Redis, custom |
| Load Algorithms | Round-robin, leastconn, source, uri, hdr | Round-robin, leastconn, ip_hash | Round-robin, least_request, ring_hash, maglev |
| Connection Limits | Per-backend, per-server | Per-server | Per-cluster, per-endpoint |
| Rate Limiting | Stick tables, counters | limit_conn, limit_req | Local rate limit, global rate limit service |
| TLS Passthrough | Yes (SNI-based routing) | Yes (SNI-based routing) | Yes (via filter chain) |
| Observability | Stats page, Prometheus export | stub_status, third-party exporters | Built-in stats, Prometheus, tracing |
| Dynamic Config | Runtime API (HAProxy 2.0+) | Requires reload | xDS API (dynamic, no restart) |
| Configuration Style | Declarative (haproxy.cfg) | Declarative (nginx.conf) | Declarative + API (xDS) |
| License | GPL v2 | BSD 2-Clause | Apache 2.0 |

## HAProxy TCP Mode: The Dedicated Load Balancer

HAProxy was built specifically as a load balancer and reverse proxy. Its TCP mode provides mature, battle-tested layer 4 load balancing with extensive configuration options.

**Strengths:**
- Best-in-class health checking — TCP, HTTP, SMTP, LDAP, MySQL, and custom checks
- Runtime API for dynamic configuration changes without restart
- Stick tables for connection persistence and rate limiting
- Extremely low memory footprint — handles 100K+ concurrent connections
- Mature ecosystem with extensive documentation and community
- Dedicated TCP proxy mode — this is HAProxy's native strength

**Weaknesses:**
- Configuration reload requires a brief transition period
- No built-in service discovery (requires external scripts or HAProxy Enterprise)
- Steeper learning curve for advanced features
- Stats interface is functional but dated

**Installation:**

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y haproxy

# Verify TCP module support
haproxy -vv | grep -i stream
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  haproxy-tcp:
    image: haproxy:3.1
    container_name: haproxy-tcp
    ports:
      - "3306:3306"   # MySQL
      - "6379:6379"   # Redis
      - "5432:5432"   # PostgreSQL
      - "8404:8404"   # Stats
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    restart: unless-stopped

volumes:
  haproxy-config:
```

**HAProxy TCP configuration:**

```haproxy
global
    maxconn 50000
    log stdout format raw local0

defaults
    mode tcp
    timeout connect 5s
    timeout client 30s
    timeout server 30s
    option tcplog
    log global

# MySQL cluster - least connections
frontend mysql_fe
    bind *:3306
    default_backend mysql_be

backend mysql_be
    balance leastconn
    option mysql-check user haproxy
    server mysql1 10.0.1.10:3306 check inter 3s fall 3 rise 2
    server mysql2 10.0.1.11:3306 check inter 3s fall 3 rise 2
    server mysql3 10.0.1.12:3306 check inter 3s fall 3 rise 2 backup

# Redis cluster with source IP hashing
frontend redis_fe
    bind *:6379
    default_backend redis_be

backend redis_be
    balance source
    option tcp-check
    tcp-check send PING

    tcp-check expect string +PONG
    server redis1 10.0.2.10:6379 check inter 2s fall 2 rise 2
    server redis2 10.0.2.11:6379 check inter 2s fall 2 rise 2

# Stats page
listen stats
    bind *:8404
    stats enable
    stats uri /
    stats refresh 10s
```

## Nginx Stream Module: The Versatile Proxy

Nginx's stream module adds layer 4 load balancing capabilities to the already popular web server. If you already run Nginx for HTTP traffic, adding TCP proxying is straightforward.

**Strengths:**
- Unified configuration with HTTP proxy — one tool for both layers
- Excellent performance — event-driven architecture
- SNI-based TLS routing without decrypting traffic
- IP-based connection limiting
- Familiar configuration syntax for existing Nginx users

**Weaknesses:**
- Health checks require Nginx Plus (commercial) or third-party modules
- Configuration changes require full reload (not graceful for TCP)
- Less granular TCP control compared to HAProxy
- Fewer load balancing algorithms than HAProxy

**Installation:**

```bash
# Nginx with stream module (compiled by default in most distributions)
apt-get update && apt-get install -y nginx

# Verify stream module is loaded
nginx -V 2>&1 | grep --color=never "with-stream"
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  nginx-stream:
    image: nginx:1.27
    container_name: nginx-stream
    ports:
      - "3306:3306"
      - "6379:6379"
      - "5432:5432"
    volumes:
      - ./nginx-stream.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
```

**Nginx stream configuration:**

```nginx
events {
    worker_connections 4096;
}

stream {
    log_format basic '$remote_addr [$time_local] '
                     '$protocol $status $bytes_sent $bytes_received '
                     '$session_time';

    access_log /var/log/nginx/stream-access.log basic;

    # MySQL load balancing
    upstream mysql_backend {
        least_conn;
        server 10.0.1.10:3306 weight=3;
        server 10.0.1.11:3306;
        server 10.0.1.12:3306 backup;
    }

    server {
        listen 3306;
        proxy_pass mysql_backend;
        proxy_timeout 30s;
        proxy_connect_timeout 5s;
    }

    # Redis with IP hash
    upstream redis_backend {
        ip_hash;
        server 10.0.2.10:6379;
        server 10.0.2.11:6379;
    }

    server {
        listen 6379;
        proxy_pass redis_backend;
        proxy_timeout 60s;
    }

    # PostgreSQL with round-robin
    upstream postgres_backend {
        server 10.0.3.10:5432;
        server 10.0.3.11:5432;
        server 10.0.3.12:5432;
    }

    server {
        listen 5432;
        proxy_pass postgres_backend;
        proxy_timeout 30s;
        proxy_connect_timeout 5s;
    }
}
```

## Envoy TCP Proxy: The Dynamic Modern Option

Envoy's TCP proxy filter provides layer 4 load balancing as part of its broader service mesh capabilities. It excels in dynamic environments where backend endpoints change frequently.

**Strengths:**
- Dynamic configuration via xDS API — no restarts needed for backend changes
- Extensive observability — built-in Prometheus metrics, distributed tracing
- Advanced load balancing — ring hash, maglev, weighted round-robin
- Filter chain architecture — composable TCP processing pipeline
- Native integration with Kubernetes and service mesh ecosystems
- Excellent for multi-tenant environments

**Weaknesses:**
- Steeper learning curve — xDS API and protobuf configuration
- Higher resource usage than HAProxy or Nginx
- Complex setup for simple use cases
- Configuration can be verbose compared to declarative config files

**Installation:**

```bash
# Download Envoy binary
curl -L https://github.com/envoyproxy/envoy/releases/download/v1.31.0/envoy-1.31.0-linux-x86_64
chmod +x envoy
sudo mv envoy /usr/local/bin/

# Or use Docker (recommended)
docker pull envoyproxy/envoy:v1.31.0
```

**Docker Compose deployment:**

```yaml
version: "3.8"
services:
  envoy-tcp:
    image: envoyproxy/envoy:v1.31.0
    container_name: envoy-tcp
    ports:
      - "3306:3306"
      - "6379:6379"
      - "5432:5432"
      - "9901:9901"   # Admin/stats
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
    command: envoy -c /etc/envoy/envoy.yaml --log-level info
    restart: unless-stopped
```

**Envoy TCP proxy configuration:**

```yaml
admin:
  address:
    socket_address:
      address: 0.0.0.0
      port_value: 9901

static_resources:
  listeners:
    # MySQL listener
    - name: mysql_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 3306
      filter_chains:
        - filters:
            - name: envoy.filters.network.tcp_proxy
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.tcp_proxy.v3.TcpProxy
                stat_prefix: mysql
                cluster: mysql_cluster

    # Redis listener
    - name: redis_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 6379
      filter_chains:
        - filters:
            - name: envoy.filters.network.tcp_proxy
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.tcp_proxy.v3.TcpProxy
                stat_prefix: redis
                cluster: redis_cluster

  clusters:
    - name: mysql_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: LEAST_REQUEST
      load_assignment:
        cluster_name: mysql_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: 10.0.1.10
                      port_value: 3306
              - endpoint:
                  address:
                    socket_address:
                      address: 10.0.1.11
                      port_value: 3306
              - endpoint:
                  address:
                    socket_address:
                      address: 10.0.1.12
                      port_value: 3306
      health_checks:
        - timeout: 3s
          interval: 5s
          unhealthy_threshold: 3
          healthy_threshold: 2
          tcp_health_check: {}

    - name: redis_cluster
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: RING_HASH
      lb_policy_config:
        ring_hash_lb_config:
          maximum_ring_size: 65536
      load_assignment:
        cluster_name: redis_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: 10.0.2.10
                      port_value: 6379
              - endpoint:
                  address:
                    socket_address:
                      address: 10.0.2.11
                      port_value: 6379
      health_checks:
        - timeout: 2s
          interval: 3s
          unhealthy_threshold: 2
          healthy_threshold: 2
          custom_health_check:
            health_checker:
              name: envoy.health_checkers.redis
```

## Performance and Resource Usage

| Metric | HAProxy | Nginx Stream | Envoy |
|---|---|---|---|
| Memory per 10K connections | ~50 MB | ~40 MB | ~120 MB |
| CPU overhead (idle) | Minimal | Minimal | Moderate |
| Throughput (connections/sec) | 200K+ | 150K+ | 100K+ |
| Config reload time | ~0ms (runtime API) | ~100ms (graceful) | ~0ms (xDS) |
| Startup time | Instant | Instant | ~1-2s |

## When to Choose Each Tool

**Choose HAProxy TCP mode when:**
- You need the most mature and battle-tested TCP load balancer
- Advanced health checks are critical (MySQL, SMTP, LDAP, custom protocols)
- You want runtime configuration changes without restarts
- You need connection persistence via stick tables
- Your primary workload is load balancing (not HTTP serving)

**Choose Nginx stream when:**
- You already run Nginx and want to add TCP proxying without new infrastructure
- Your TCP load balancing needs are straightforward (round-robin, least connections)
- You want unified HTTP and TCP configuration in a single tool
- You value simplicity and minimal configuration complexity

**Choose Envoy TCP proxy when:**
- You run Kubernetes or a service mesh and want consistent load balancing
- Backend endpoints change dynamically and you need zero-downtime updates
- You need advanced load balancing algorithms (ring hash, maglev)
- Built-in observability and distributed tracing are important
- You are building a multi-tenant platform with per-tenant TCP routing

## Why Self-Host Your TCP Load Balancer?

Running your own layer 4 load balancer gives you complete visibility into connection patterns, latency distributions, and backend health. Commercial load balancers often abstract away these details, making it harder to debug connection issues or optimize traffic distribution.

Self-hosted TCP load balancers integrate seamlessly with self-hosted backend services. Pair HAProxy or Nginx stream with your self-hosted database clusters, message queues, and application servers for a fully self-contained infrastructure stack. For related load balancing guides, see our [DNS failover with Keepalived and PowerDNS](../2026-04-24-self-hosted-dns-failover-keepalived-powerdns-haproxy-guide/) and [bare metal Kubernetes load balancing](../2026-04-26-metallb-vs-kube-vip-vs-cilium-lb-bare-metal-kubernetes-load-balancer-guide/).

Cost savings are substantial. Hardware load balancers from F5 or Citrix cost $10,000-$50,000 plus annual support contracts. HAProxy, Nginx stream, and Envoy are free and run on commodity hardware. Even for high-traffic deployments, a single commodity server with HAProxy can handle more connections than entry-level hardware appliances.

Self-hosting also eliminates vendor lock-in. Your load balancing configuration is stored in plain text files or version-controlled YAML, making it portable across environments. When you need to replicate your load balancing setup across data centers or cloud providers, the same configuration works everywhere without licensing complications.

If you are also configuring SNI-based TLS routing for your TCP services, our [SNI proxy comparison](../2026-04-26-sniproxy-vs-haproxy-vs-caddy-self-hosted-sni-proxy-tls-routing-guide/) covers tools that route encrypted traffic based on the TLS Server Name Indication extension.

## FAQ

### What is the difference between layer 4 and layer 7 load balancing?

Layer 4 (TCP) load balancers forward connections based on IP addresses and port numbers without inspecting the application data. Layer 7 (HTTP) load balancers parse HTTP headers and can route based on URL paths, hostnames, cookies, and content. Use layer 4 for database and cache traffic, layer 7 for web applications.

### Can HAProxy do both TCP and HTTP load balancing?

Yes. HAProxy supports both modes simultaneously. Use `mode tcp` for TCP proxying and `mode http` for HTTP load balancing in the same configuration file. You can even mix modes across different frontend/backend pairs.

### Does Nginx stream support health checks?

The open-source version of Nginx has basic passive health checking (marks servers as down after connection failures). Active health checks require Nginx Plus (commercial) or third-party modules like nginx_upstream_check.

### Which tool has the best health checking?

HAProxy has the most comprehensive health check options, supporting TCP, HTTP, SMTP, LDAP, MySQL, and custom check scripts. Envoy also supports a wide range including TCP, HTTP, gRPC, and Redis checks. Nginx stream has the most limited options in its open-source version.

### Can I use these tools for TLS passthrough?

Yes. All three support TLS passthrough, where encrypted traffic is forwarded to backend servers without decryption. Both HAProxy and Nginx support SNI-based routing even in passthrough mode, allowing you to route to different backends based on the requested hostname.

### How do I monitor TCP load balancer performance?

HAProxy provides a built-in stats page (HTTP) and Prometheus export. Nginx stream logs connection metrics that can be parsed with log analyzers. Envoy has the most comprehensive built-in metrics, including connection counts, byte rates, and per-endpoint health status — all exportable to Prometheus.

### Can I run multiple TCP load balancers for high availability?

Yes. Deploy two or more load balancer instances with keepalived (VRRP) or a DNS-based failover mechanism. For Kubernetes deployments, use a Service of type LoadBalancer to distribute traffic across Envoy or Nginx pods.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TCP Load Balancing — HAProxy TCP Mode vs Nginx Stream vs Envoy TCP Proxy",
  "description": "Compare three open-source TCP load balancers for self-hosted infrastructure: HAProxy TCP mode, Nginx stream module, and Envoy TCP proxy. Covers health checks, Docker deployment, and when to choose each.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
