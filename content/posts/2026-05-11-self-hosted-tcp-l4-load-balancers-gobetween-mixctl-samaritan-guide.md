---
title: "Self-Hosted TCP/L4 Load Balancers: GoBetween vs Mixctl vs Samaritan"
date: "2026-05-11"
tags: ["comparison", "guide", "self-hosted", "networking", "load-balancing"]
draft: false
description: "Compare GoBetween, Mixctl, and Samaritan — three open-source TCP/L4 load balancers for modern infrastructure. Docker deployment guides, feature comparison, and production configurations."
---

TCP and Layer 4 load balancing is a foundational requirement for any distributed system. Unlike HTTP reverse proxies that operate at Layer 7 and understand request semantics, L4 load balancers work with raw TCP/UDP streams — making them protocol-agnostic, faster, and ideal for database connections, gRPC, custom protocols, and high-throughput network services.

Commercial L4 load balancers from F5, Citrix, or HAProxy Enterprise carry steep licensing costs. The open-source ecosystem offers powerful alternatives that handle millions of connections per second without any licensing fees.

## What Is a Layer 4 Load Balancer?

A Layer 4 (Transport Layer) load balancer distributes incoming network traffic based on IP addresses and port numbers, without inspecting the payload. This makes it:

- **Protocol-agnostic** — works with any TCP or UDP service (databases, gRPC, custom binary protocols)
- **Low-latency** — no payload parsing means sub-microsecond forwarding overhead
- **Transparent** — preserves original source/destination IPs with Direct Server Return (DSR) modes
- **High-throughput** — ideal for database connection pools, WebSocket farms, and high-frequency trading systems

L4 load balancers sit at a different layer than HTTP reverse proxies (HAProxy HTTP mode, Nginx, Traefik). For raw TCP/UDP distribution — MySQL connections, Redis clusters, or gRPC streams — an L4 balancer is the right tool.

## Comparison Overview

| Feature | GoBetween | Mixctl | Samaritan |
|---------|-----------|--------|-----------|
| Stars | 1,988 | 465 | 321 |
| Language | Go | Go | Go |
| License | MIT | MIT | Apache 2.0 |
| Protocols | TCP, UDP, TLS, SNI | TCP | TCP, TLS |
| Load Algorithms | Round-robin, Weighted, Least-conn, Hash, IP-hash | Round-robin, Weighted | Round-robin, Weighted, Least-conn, IP-hash |
| Health Checks | TCP, HTTP, Redis, MySQL | TCP | TCP, HTTP |
| Dashboard | Web UI | CLI only | CLI only |
| Service Discovery | Consul, SRV DNS | Static | Static |
| TLS Termination | Yes (SNI-based) | No | Yes |
| Rate Limiting | Yes | No | Yes |
| Docker Support | Official image | Official image | Dockerfile |
| Last Updated | 2025-08 | 2026-04 | 2023-03 |
| GitHub | [yyyar/gobetween](https://github.com/yyyar/gobetween) | [inlets/mixctl](https://github.com/inlets/mixctl) | [samaritan-proxy/samaritan](https://github.com/samaritan-proxy/samaritan) |

## GoBetween

GoBetween is the most feature-rich open-source L4 load balancer. Written in Go by Alexey Yarmolchuk, it supports TCP, UDP, TLS, and SNI-based routing with a built-in web dashboard.

### Key Features

- **Multi-protocol support**: TCP, UDP, TLS termination, SNI routing
- **Rich load balancing algorithms**: Round-robin, Weighted, Least-connections, Hash-based, IP-hash
- **Built-in health checks**: TCP connect, HTTP, Redis ping, MySQL ping
- **Service discovery**: Consul integration, SRV DNS records
- **Web dashboard**: Real-time metrics, connection counts, backend status
- **Rate limiting**: Per-client and per-server rate limiting
- **Zero-downtime reloads**: Configuration changes without dropping connections

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gobetween:
    image: yyyar/gobetween:latest
    container_name: gobetween
    restart: unless-stopped
    ports:
      - "8000:8000"    # Admin API / Dashboard
      - "3000:3000/tcp" # TCP frontend
      - "5000:5000/udp" # UDP frontend
    volumes:
      - ./gobetween.toml:/etc/gobetween/gobetween.toml:ro
    networks:
      - lb-net

networks:
  lb-net:
    driver: bridge
```

### Configuration Example (gobetween.toml)

```toml
[api]
enabled = true
bind = "0.0.0.0:8000"

[servers.sample]
bind = "0.0.0.0:3000"
protocol = "tcp"

[servers.sample.discovery]
kind = "static"
static_list = [
  "10.0.0.1:3306",
  "10.0.0.2:3306",
  "10.0.0.3:3306"
]

[servers.sample.balance]
strategy = "leastconn"

[servers.sample.healthcheck]
fails = 3
passes = 2
interval = "5s"
kind = "tcp"
timeout = "2s"
```

## Mixctl

Mixctl is a minimalist TCP load balancer from Alex Ellis (inlets project author). It trades features for simplicity — a single binary with round-robin and weighted load balancing, designed for edge computing and tunnel scenarios.

### Key Features

- **Minimal footprint**: Single binary, ~10MB Docker image
- **Round-robin and weighted balancing**: Simple, predictable distribution
- **TCP health checks**: Automatic backend detection
- **Designed for inlets tunnels**: Works seamlessly with inlets PRO for TCP tunneling
- **CLI configuration**: No web UI, config via command-line flags

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  mixctl:
    image: ghcr.io/inlets/mixctl:latest
    container_name: mixctl
    restart: unless-stopped
    ports:
      - "8080:8080"
    command:
      - "tcp"
      - "--port=8080"
      - "--targets=10.0.0.1:3000,10.0.0.2:3000,10.0.0.3:3000"
      - "--health-check-interval=5s"
    networks:
      - lb-net

networks:
  lb-net:
    driver: bridge
```

### Command-Line Usage

```bash
# Basic TCP load balancing
mixctl tcp --port=8080 --targets=10.0.0.1:3000,10.0.0.2:3000

# With weighted distribution
mixctl tcp --port=8080 --targets=10.0.0.1:3000:3,10.0.0.2:3000:1

# With health checking
mixctl tcp --port=8080 --targets=10.0.0.1:3000,10.0.0.2:3000 --health-check-interval=10s
```

## Samaritan

Samaritan is a transparent proxy with infrastructure focus. Written in Go, it provides TCP/TLS load balancing with advanced routing rules, rate limiting, and a plugin architecture.

### Key Features

- **Transparent proxy mode**: Intercept and forward traffic without client configuration
- **Advanced routing**: Rule-based routing with header/body inspection
- **Rate limiting**: Token bucket rate limiting per client
- **TLS termination**: Built-in TLS support with SNI
- **Plugin architecture**: Extensible via Go plugins
- **Metrics export**: Prometheus-compatible metrics endpoint

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  samaritan:
    build:
      context: .
      dockerfile: Dockerfile
    image: samaritan-proxy/samaritan:latest
    container_name: samaritan
    restart: unless-stopped
    ports:
      - "2080:2080"
      - "9090:9090"  # Metrics
    volumes:
      - ./samaritan.yaml:/etc/samaritan/samaritan.yaml:ro
    networks:
      - lb-net

networks:
  lb-net:
    driver: bridge
```

### Configuration Example (samaritan.yaml)

```yaml
servers:
  - name: tcp-lb
    listen: "0.0.0.0:2080"
    protocol: tcp
    backends:
      - address: "10.0.0.1:3000"
        weight: 3
      - address: "10.0.0.2:3000"
        weight: 1
      - address: "10.0.0.3:3000"
        weight: 2
    health_check:
      interval: 10s
      timeout: 3s
      type: tcp
    load_balance: leastconn
```

## Performance Considerations

L4 load balancers are inherently fast because they don't parse application-layer protocols. Here is how the three compare in practice:

- **GoBetween**: Handles ~50K concurrent connections with minimal memory overhead (~50MB RSS). The web dashboard adds ~10% overhead when enabled.
- **Mixctl**: The lightest option — ~15MB RSS with negligible CPU usage. Best for edge deployments where resources are constrained.
- **Samaritan**: ~40MB RSS with the plugin system. Rate limiting adds moderate overhead but provides enterprise-grade traffic control.

For most production scenarios, all three tools will saturate the network before hitting CPU limits. The choice comes down to feature requirements rather than raw performance.

## Choosing the Right L4 Load Balancer

**Choose GoBetween if**: You need a full-featured L4 balancer with a web dashboard, multiple health check types, and service discovery. It is the closest open-source equivalent to a commercial L4 appliance.

**Choose Mixctl if**: You want simplicity above all else. A single binary, CLI-only configuration, and a tiny resource footprint make it ideal for edge computing, IoT gateways, and resource-constrained environments.

**Choose Samaritan if**: You need transparent proxy capabilities with advanced routing rules and rate limiting. Its plugin architecture makes it extensible for custom traffic handling.

## Security Best Practices

1. **Network segmentation**: Place the load balancer in a DMZ with only the required ports exposed to the public network
2. **TLS termination**: Use GoBetween or Samaritan for TLS termination at the L4 layer to offload encryption from backends
3. **Health check hardening**: Configure health checks with appropriate timeouts and failure thresholds to avoid false positives
4. **Rate limiting**: Enable rate limiting (GoBetween, Samaritan) to protect backends from connection floods
5. **Monitoring**: Export Prometheus metrics (Samaritan) or use the GoBetween dashboard for real-time visibility

## Why Self-Host Your TCP Load Balancer?

Self-hosting your L4 load balancing infrastructure gives you complete control over traffic routing, eliminates per-connection licensing fees, and keeps sensitive data within your network perimeter. Commercial L4 solutions from F5, Citrix, or Kemp charge thousands of dollars annually per instance — costs that scale with your infrastructure.

With open-source alternatives, you get:

- **Zero licensing costs**: All three tools are open-source under permissive licenses (MIT, Apache 2.0)
- **Protocol flexibility**: Handle any TCP or UDP traffic — MySQL, PostgreSQL, Redis, gRPC, or custom binary protocols
- **No vendor lock-in**: Configuration is file-based and portable across cloud providers
- **Edge deployment**: Lightweight enough to run on a Raspberry Pi or single-core VM
- **Transparent operations**: L4 balancers are invisible to applications — no code changes required

For organizations managing database clusters, gRPC microservices, or custom protocol servers, self-hosted L4 load balancing is a foundational building block. For broader infrastructure automation, see our [HA clustering guide](../2026-04-21-keepalived-vs-corosync-pacemaker-self-hosted-ha-clustering-guide/). If you also need HTTP-level load balancing, check our [HAProxy management guide](../2026-04-24-haproxy-dataplane-api-vs-prometheus-exporter-vs-runtime-api-self-hosted-haproxy-management-guide-2026/). For Kubernetes deployments, our [ingress controller comparison](../2026-04-22-traefik-vs-nginx-ingress-vs-contour-kubernetes-ingress-controller-guide-2026/) covers the L7 side.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted TCP/L4 Load Balancers: GoBetween vs Mixctl vs Samaritan",
  "description": "Compare GoBetween, Mixctl, and Samaritan open-source TCP/L4 load balancers. Docker deployment guides, feature comparison, and production configurations for 2026.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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

## FAQ

### What is the difference between Layer 4 and Layer 7 load balancing?

Layer 4 load balancers operate at the TCP/UDP level, routing traffic based on IP addresses and ports without inspecting the payload. Layer 7 load balancers operate at the HTTP/application level, routing based on URLs, headers, and content. L4 is faster and protocol-agnostic; L7 is more intelligent but limited to HTTP-like protocols.

### Can GoBetween handle UDP traffic?

Yes, GoBetween supports both TCP and UDP load balancing. Configure `protocol = "udp"` in the server definition. This makes it suitable for DNS, syslog, and other UDP-based services.

### Does Mixctl support TLS termination?

No, Mixctl is a pure TCP load balancer and does not support TLS termination. If you need TLS, use GoBetween or Samaritan, or place a TLS terminator (like stunnel) in front of Mixctl.

### How do I monitor GoBetween backends?

GoBetween includes a built-in REST API on port 8000 (configurable) that provides real-time backend status, connection counts, and health check results. You can also enable the web dashboard for a visual interface.

### Can I use these load balancers with Kubernetes?

Yes, but they are better suited for bare-metal or VM deployments. For Kubernetes, use native Service objects (kube-proxy) or dedicated ingress controllers. Mixctl is particularly useful for edge tunneling into Kubernetes clusters.

### What happens when all backends are unhealthy?

GoBetween returns the last known healthy backend (sticky failover). Mixctl returns a connection refused error. Samaritan can be configured with a fallback backend or custom error response.

