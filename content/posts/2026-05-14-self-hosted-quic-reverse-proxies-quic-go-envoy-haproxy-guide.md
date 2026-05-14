---
title: "Self-Hosted QUIC Reverse Proxies: quic-go, Envoy, and HAProxy Compared"
date: "2026-05-14"
tags: ["quic", "reverse-proxy", "load-balancing", "http3", "networking"]
draft: false
---

QUIC (Quick UDP Internet Connections) has evolved from an experimental Google protocol to the foundation of HTTP/3, offering faster connection establishment, improved multiplexing, and better performance over lossy networks. Deploying a QUIC-capable reverse proxy is essential for modern infrastructure that needs to serve HTTP/3 traffic while maintaining backward compatibility with HTTP/2 and HTTP/1.1.

This guide compares three production-ready QUIC reverse proxy solutions: **quic-go**, **Envoy Proxy**, and **HAProxy**. Each takes a different approach to QUIC termination — from a pure-Go library to enterprise-grade proxies with extensive configuration options.

## What Is a QUIC Reverse Proxy?

A QUIC reverse proxy terminates QUIC connections from clients and forwards the decrypted traffic to backend servers over TCP, HTTP/2, or HTTP/1.1. This architecture provides several advantages:

- **Zero-RTT resumption**: QUIC supports 0-RTT connection resumption, reducing latency for returning clients
- **Connection migration**: Clients can switch networks (WiFi to cellular) without breaking connections
- **Head-of-line blocking elimination**: Unlike HTTP/2 over TCP, QUIC multiplexes streams independently
- **Improved TLS 1.3 integration**: QUIC bakes in TLS 1.3, eliminating the TCP+TLS handshake overhead

## quic-go: Production QUIC in Pure Go

[quic-go](https://github.com/quic-go/quic-go) (11,500+ stars) is a pure-Go QUIC implementation that includes both a QUIC library and an HTTP/3 server. It is the most widely used open-source QUIC implementation and powers HTTP/3 support in many Go-based projects.

### Key Features
- Pure Go implementation — no C dependencies, easy to cross-compile
- Full HTTP/3 server with standard `http.Handler` interface
- QUIC connection migration support
- 0-RTT connection resumption
- Active development with regular releases

### Docker Deployment

```yaml
version: "3.8"
services:
  quic-proxy:
    image: golang:1.22-alpine
    container_name: quic-proxy
    ports:
      - "443:443/udp"
      - "443:443/tcp"
    volumes:
      - ./proxy:/app
      - ./certs:/certs:ro
    working_dir: /app
    command: |
      sh -c "apk add --no-cache git && go install github.com/quic-go/quic-go/http3/example@latest && http3_example -bind :443 -cert /certs/cert.pem -key /certs/key.pem"
    restart: unless-stopped
```

### Pros and Cons
- **Pro**: Easiest to embed in Go applications; no external dependencies
- **Pro**: HTTP/3 implementation tracks the latest IETF drafts
- **Con**: No built-in configuration file — requires Go code or CLI flags
- **Con**: No native load balancing; needs to be paired with a TCP/UDP load balancer

## Envoy Proxy: Enterprise QUIC Termination

[Envoy](https://github.com/envoyproxy/envoy) (27,900+ stars) is a cloud-native edge/middle/service proxy that added HTTP/3 and QUIC support as a first-class feature. Envoy provides the most comprehensive QUIC reverse proxy configuration of any open-source project.

### Key Features
- Full HTTP/3 QUIC listener support with dynamic configuration
- Integration with xDS control plane for service mesh deployments
- Advanced load balancing (weighted, ring hash, maglev)
- Built-in observability (stats, tracing, access logging)
- gRPC, REST, and WebSocket support over QUIC

### Docker Compose Configuration

```yaml
version: "3.8"
services:
  envoy:
    image: envoyproxy/envoy:v1.30-latest
    container_name: envoy-quic
    ports:
      - "443:443/udp"
      - "443:443/tcp"
      - "8443:8443/tcp"
    volumes:
      - ./envoy.yaml:/etc/envoy/envoy.yaml:ro
      - ./certs:/certs:ro
    command: envoy -c /etc/envoy/envoy.yaml --log-level info
    restart: unless-stopped
```

Minimal `envoy.yaml` for QUIC termination:

```yaml
static_resources:
  listeners:
    - name: quic_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 443
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: quic_reverse_proxy
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match: { prefix: "/" }
                          route:
                            cluster: backend_service
                http_filters:
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
                codec_type: HTTP3
          transport_socket:
            name: envoy.quic.listeners.quic.transport_socket
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.quic.v3.QuicDownstreamTransport
              downstream_tls_context:
                common_tls_context:
                  tls_certificates:
                    - certificate_chain: { filename: /certs/cert.pem }
                      private_key: { filename: /certs/key.pem }
  clusters:
    - name: backend_service
      connect_timeout: 5s
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: backend_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: backend
                      port_value: 8080
```

### Pros and Cons
- **Pro**: Most feature-complete QUIC implementation with xDS support
- **Pro**: Extensive observability and traffic management
- **Con**: Complex configuration; steep learning curve
- **Con**: Higher resource usage compared to lightweight alternatives

## HAProxy: QUIC-Enabled Load Balancing

[HAProxy](https://github.com/haproxy/haproxy) (6,500+ stars) added QUIC and HTTP/3 support starting with version 2.6+. Known for its reliability and performance in high-traffic environments, HAProxy provides QUIC termination with its familiar configuration syntax.

### Key Features
- QUIC listener support with HTTP/3 frontend
- Seamless HTTP/3 to HTTP/2/1.1 backend translation
- ACL-based routing, stick tables, and rate limiting
- Low memory footprint and high throughput
- Familiar configuration syntax for existing HAProxy users

### Docker Compose Setup

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.9-alpine
    container_name: haproxy-quic
    ports:
      - "443:443/tcp"
      - "443:443/udp"
      - "8404:8404/tcp"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/certs:ro
    restart: unless-stopped
```

HAProxy configuration (`haproxy.cfg`):

```ini
global
    log stdout format raw local0
    maxconn 4096

defaults
    log     global
    mode    http
    option  httplog
    timeout connect 5000ms
    timeout client  50000ms
    timeout server  50000ms

frontend quic_fe
    bind *:443 quic ssl crt /certs/cert.pem alpn h3,h2,http/1.1
    default_backend http_back

backend http_back
    balance roundrobin
    server web1 backend1:8080 check
    server web2 backend2:8080 check
```

### Pros and Cons
- **Pro**: Simple, declarative configuration syntax
- **Pro**: Excellent performance with low overhead
- **Con**: QUIC support is newer and less mature than Envoy's
- **Con**: No native service mesh integration

## Comparison Table

| Feature | quic-go | Envoy | HAProxy |
|---|---|---|---|
| QUIC Protocol Support | Full (IETF) | Full (IETF) | Full (IETF) |
| HTTP/3 | Native | Native | Native |
| Configuration | Go code / CLI | YAML (xDS) | Declarative config |
| Load Balancing | None (library) | Advanced (ring hash, maglev) | Round-robin, leastconn |
| 0-RTT Resumption | Yes | Yes | Yes |
| Connection Migration | Yes | Yes | Limited |
| Observability | Basic (Go metrics) | Extensive (stats, tracing) | Basic (stats page) |
| Service Mesh (xDS) | No | Yes | No |
| Resource Usage | Low | Medium-High | Low |
| GitHub Stars | 11,500+ | 27,900+ | 6,500+ |
| Best For | Go app embedding | Enterprise / service mesh | Traditional load balancing |

## Choosing the Right QUIC Reverse Proxy

**Choose quic-go if** you are building a Go application and want to embed HTTP/3 support directly. It is the simplest option for Go developers and requires no separate proxy deployment.

**Choose Envoy if** you need enterprise-grade traffic management, xDS integration, or are already running a service mesh. Envoy's QUIC implementation is the most mature and feature-rich among open-source options.

**Choose HAProxy if** you already use HAProxy for TCP/HTTP load balancing and want to add HTTP/3 support with minimal configuration changes. Its familiar syntax and low resource overhead make migration straightforward.

## Why Self-Host Your QUIC Infrastructure?

Running your own QUIC reverse proxy gives you complete control over TLS certificates, cipher suites, and connection parameters. Unlike managed CDN solutions, self-hosted QUIC termination keeps all traffic within your network boundary, eliminating third-party dependencies and reducing latency for internal services.

For organizations managing multi-region deployments, self-hosted QUIC proxies can be paired with anycast DNS to provide optimal routing. This approach avoids vendor lock-in with cloud-specific HTTP/3 solutions and gives you the flexibility to tune QUIC parameters (idle timeouts, migration settings, congestion control) for your specific workload.

Self-hosted QUIC infrastructure also integrates seamlessly with existing internal tooling. For DNS-level routing and failover, combine with solutions from our [DNS failover guide](../2026-04-24-self-hosted-dns-failover-keepalived-powerdns-haproxy-guide/). For comprehensive reverse proxy management with GUI tools, see our [reverse proxy GUI comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide/).


## Security Considerations for QUIC Deployment

Deploying QUIC reverse proxies introduces unique security considerations that differ from traditional TCP-based HTTPS termination. Since QUIC runs over UDP, firewall rules must be updated to allow UDP port 443 in addition to TCP port 443. Many organizations have restrictive outbound UDP policies that can inadvertently block QUIC traffic, causing clients to fall back to HTTP/2 over TCP.

Certificate management for QUIC follows the same patterns as traditional TLS — Let's Encrypt, ACME clients, and internal PKI all work identically. The key difference is that QUIC requires TLS 1.3, which means older certificate types (RSA keys below 2048-bit, SHA-1 signatures) are incompatible. Modern ECDSA certificates are recommended for optimal QUIC performance.

Connection migration, a feature of QUIC that allows clients to maintain sessions across network changes, can have security implications. In environments where source IP-based access control is enforced, a migrating connection may appear to come from a different IP address, potentially triggering security policies. Consider implementing application-layer authentication alongside network-level controls.

For comprehensive load balancing configurations that complement QUIC termination, our [UDP load balancing guide](../2026-05-12-self-hosted-udp-load-balancing-haproxy-pen-balance-guide/) covers additional traffic distribution strategies.

## FAQ

### What is the difference between QUIC and HTTP/3?
QUIC is the transport-layer protocol that runs over UDP, providing reliable, ordered delivery with built-in TLS 1.3. HTTP/3 is the application-layer protocol that runs on top of QUIC, replacing HTTP/2 over TCP. In practice, HTTP/3 always uses QUIC as its transport.

### Does quic-go require a separate reverse proxy?
No. quic-go includes an HTTP/3 server (`http3.ListenAndServe`) that can serve as a standalone QUIC terminator. However, it does not include load balancing or routing features — for those, you need Envoy or HAProxy.

### Can Envoy handle both QUIC and TCP traffic on the same port?
No. QUIC runs over UDP while TCP runs over TCP. You typically bind QUIC on port 443/udp and TCP/TLS on port 443/tcp. Envoy can run both listeners simultaneously.

### Is HAProxy's QUIC support production-ready?
Yes, HAProxy 2.6+ includes stable QUIC support. However, the QUIC implementation is newer than Envoy's, so some edge cases may be less thoroughly tested. For most standard HTTP/3 reverse proxy use cases, it is production-ready.

### Do I need special SSL certificates for QUIC?
No. QUIC uses standard TLS 1.3 certificates. Any SSL certificate that works for HTTPS will work for QUIC. The key difference is that the certificate is negotiated within the QUIC handshake rather than a separate TLS layer on top of TCP.

### How does QUIC improve performance over HTTP/2?
QUIC eliminates head-of-line blocking by multiplexing streams at the transport layer. In HTTP/2 over TCP, a single lost TCP packet blocks all streams. With QUIC, lost packets only affect the specific stream they belong to. Additionally, QUIC's 0-RTT resumption reduces connection latency for returning clients.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted QUIC Reverse Proxies: quic-go, Envoy, and HAProxy Compared",
  "description": "Compare quic-go, Envoy, and HAProxy for self-hosted QUIC reverse proxy and HTTP/3 termination. Includes Docker configs, feature comparison, and deployment guides.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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

