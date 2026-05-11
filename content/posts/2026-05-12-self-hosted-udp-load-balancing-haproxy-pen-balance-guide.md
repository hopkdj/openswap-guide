---
title: "Self-Hosted UDP Load Balancing: HAProxy UDP Mode vs Pen vs Balance"
date: "2026-05-12"
tags: ["load-balancing", "udp", "networking", "high-availability", "self-hosted"]
draft: false
---

TCP load balancing is a solved problem — HAProxy, Nginx, and Envoy dominate the space. But UDP load balancing is a different beast. UDP is connectionless, stateless, and has no handshake to track. This makes UDP load balancing fundamentally different from TCP, requiring specialized tools that understand session persistence without connection state. This guide compares three open-source UDP load balancing solutions.

## Why UDP Load Balancing Matters

Many critical services run over UDP and need load balancing for scalability and high availability:

- **DNS resolvers** — Distribute queries across multiple Unbound, BIND, or PowerDNS instances
- **Syslog collectors** — Balance incoming syslog traffic across multiple log aggregation nodes
- **RADIUS/FreeRADIUS** — Distribute authentication requests across multiple RADIUS servers
- **NTP servers** — Balance time synchronization requests across multiple NTP daemons
- **Game servers** — Distribute player connections across multiple game server instances
- **VoIP/SIP** — Balance SIP signaling and RTP media streams across multiple PBX instances
- **SNMP traps** — Distribute trap traffic across multiple trap receivers
- **Streaming protocols** — Balance RTMP, QUIC, and WebRTC traffic

For TCP and HTTP load balancing, see our [advanced load balancer guide](../2026-05-03-self-hosted-load-balancer-advanced-haproxy-lua-traefik-middleware-envoy-wasm/) and [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) for anycast-based approaches. If you need API-level load balancing, our [API gateway comparison](../self-hosted-api-gateway-apisix-kong-tyk-guide/) covers Layer 7 routing.

## HAProxy UDP Mode (Frontend/Backend UDP)

**HAProxy** is primarily known as a TCP/HTTP load balancer, but since version 2.4, it has native UDP load balancing support through `mode udp` frontends and backends. This makes HAProxy a compelling option if you're already using it for TCP/HTTP traffic.

### Key Features

- Native UDP mode (HAProxy 2.4+)
- Round-robin, leastconn, source, and uri balancing algorithms
- Health checks via UDP probes
- Session persistence via source IP hashing
- Statistics web interface
- Rate limiting and connection limiting
- Lua scripting for custom logic
- Active health checks with configurable intervals

### Installation

```bash
# Debian 12+ / Ubuntu 22.04+ (HAProxy 2.4+)
sudo apt install haproxy

# Verify UDP support
haproxy -vv | grep -i "udp"
```

### Configuration

```ini
# /etc/haproxy/haproxy.cfg
global
    log stdout format short local0
    maxconn 50000

defaults
    log     global
    mode    udp
    timeout connect 5s
    timeout client  30s
    timeout server  30s
    retries 3

# DNS load balancing
frontend dns_udp
    bind *:53 udp
    default_backend dns_servers
    option udp-check

backend dns_servers
    balance source
    option udp-check
    expect string id.server
    server dns1 10.0.1.10:53 check inter 5s fall 3 rise 2
    server dns2 10.0.1.11:53 check inter 5s fall 3 rise 2
    server dns3 10.0.1.12:53 check inter 5s fall 3 rise 2

# Syslog load balancing
frontend syslog_udp
    bind *:514 udp
    default_backend syslog_servers

backend syslog_servers
    balance roundrobin
    server syslog1 10.0.2.10:514 check inter 10s fall 3 rise 2
    server syslog2 10.0.2.11:514 check inter 10s fall 3 rise 2

# RADIUS load balancing
frontend radius_udp
    bind *:1812 udp
    default_backend radius_servers

backend radius_servers
    balance source
    server radius1 10.0.3.10:1812 check inter 10s fall 3 rise 2
    server radius2 10.0.3.11:1812 check inter 10s fall 3 rise 2
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:2.8-alpine
    container_name: haproxy-udp
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    ports:
      - "53:53/udp"
      - "514:514/udp"
      - "1812:1812/udp"
      - "8404:8404"
    restart: unless-stopped
```

HAProxy's UDP mode is ideal if you already run HAProxy for TCP/HTTP traffic. You get a unified configuration, familiar management tools, and the robust HAProxy ecosystem. The main limitation is that UDP health checks are limited — HAProxy can send a probe and expect a response, but many UDP services don't have a built-in "health check" protocol.

## Pen

**Pen** is a lightweight UDP (and TCP) load balancer written in C. It's been around since 2001 and is designed for simplicity — a single binary with a straightforward command-line interface. Despite its age, it remains effective for UDP load balancing use cases.

### Key Features

- UDP and TCP load balancing
- Round-robin and source-based balancing
- Built-in health checking (UDP ping)
- Session persistence via client IP
- Very low resource usage (~2MB memory)
- Simple CLI configuration (no config file needed)
- Daemon mode with PID file management
- Supports IPv4 and IPv6

### Installation

```bash
# Debian/Ubuntu
sudo apt install pen

# Build from source
git clone https://github.com/alexandergoude/pen.git
cd pen
./configure && make && sudo make install
```

### Configuration

Pen is configured entirely via command-line arguments:

```bash
# DNS load balancing (round-robin)
pen -f -u -r 53 10.0.1.10:53 10.0.1.11:53 10.0.1.12:53

# Syslog load balancing with source IP persistence
pen -f -u -s 514 10.0.2.10:514 10.0.2.11:514

# RADIUS load balancing with health checks
pen -f -u -r -H "ping" 1812 10.0.3.10:1812 10.0.3.11:1812

# Run as daemon with PID file
pen -d -p /var/run/pen-dns.pid -r 53 10.0.1.10:53 10.0.1.11:53

# Monitor Pen status
penctl localhost:2001 show
```

Command-line flags:
- `-f` — Run in foreground (remove for daemon mode)
- `-u` — UDP mode
- `-r` — Round-robin balancing (default is source-based)
- `-s` — Source IP persistence
- `-d` — Daemon mode
- `-p` — PID file path
- `-H` — Health check string to send

### Docker Deployment

```yaml
version: "3.8"
services:
  pen-dns:
    image: alpine:latest
    container_name: pen-dns
    command: >
      sh -c "apk add pen &&
             pen -f -u -r 53 10.0.1.10:53 10.0.1.11:53 10.0.1.12:53"
    ports:
      - "53:53/udp"
    restart: unless-stopped

  pen-syslog:
    image: alpine:latest
    container_name: pen-syslog
    command: >
      sh -c "apk add pen &&
             pen -f -u -r 514 10.0.2.10:514 10.0.2.11:514"
    ports:
      - "514:514/udp"
    restart: unless-stopped
```

Pen is the simplest possible UDP load balancer. Its command-line-only configuration is both a strength (easy to understand, no config file syntax to learn) and a weakness (no hot reload, no structured config management). It's best for straightforward UDP balancing where you need minimal overhead.

## Balance

**Balance** is another lightweight TCP/UDP load balancer written in C. Similar in philosophy to Pen, it uses a simple command-line interface and is designed for embedded systems and resource-constrained environments. It supports TCP, UDP, and even SCTP load balancing.

### Key Features

- UDP, TCP, and SCTP load balancing
- Round-robin, weighted, and hash-based balancing
- TCP/UDP health checking
- Session persistence via source IP or port hashing
- Extremely low resource usage (~1MB memory)
- Simple CLI configuration
- Built-in HTTP status page
- Supports transparent proxy mode

### Installation

```bash
# Debian/Ubuntu
sudo apt install balance

# Build from source
wget https://www.inlab.de/balance-3.61.tar.gz
tar xzf balance-3.61.tar.gz
cd balance-3.61
make && sudo make install
```

### Configuration

Like Pen, Balance is configured via command-line arguments:

```bash
# DNS load balancing (round-robin)
balance -u -r 53 10.0.1.10:53 10.0.1.11:53 10.0.1.12:53

# Syslog with weighted distribution (primary gets 2x traffic)
balance -u -w 514 10.0.2.10:514=2 10.0.2.11:514=1

# NTP with source IP hashing (same client always hits same server)
balance -u -H 123 10.0.4.10:123 10.0.4.11:123

# Daemon mode with status port
balance -u -d -c 9000 53 10.0.1.10:53 10.0.1.11:53

# View running configuration
balance -C localhost:9000
```

Command-line flags:
- `-u` — UDP mode
- `-r` — Round-robin
- `-w` — Weighted round-robin (append `=weight` to server address)
- `-H` — Hash-based (source IP)
- `-d` — Daemon mode
- `-c` — Control/status port

### Docker Deployment

```yaml
version: "3.8"
services:
  balance-dns:
    image: debian:bookworm-slim
    container_name: balance-dns
    command: >
      sh -c "apt-get update && apt-get install -y balance &&
             balance -u -f -r 53 10.0.1.10:53 10.0.1.11:53 10.0.1.12:53"
    ports:
      - "53:53/udp"
      - "9000:9000"
    restart: unless-stopped
```

Balance is very similar to Pen in philosophy but offers a few additional features: weighted round-robin balancing, a built-in HTTP status page, and SCTP support. It's slightly more feature-rich while maintaining the same low resource footprint.

## Feature Comparison

| Feature | HAProxy UDP | Pen | Balance |
|---------|------------|-----|---------|
| **UDP Mode** | Native (v2.4+) | Yes | Yes |
| **TCP Mode** | Yes | Yes | Yes |
| **Config Method** | Config file | CLI args | CLI args |
| **Hot Reload** | Yes | No | No |
| **Health Checks** | UDP probes | UDP ping | UDP/TCP probes |
| **Balancing Algorithms** | 7+ (rr, source, leastconn, uri, hdr, etc.) | Round-robin, source | Round-robin, weighted, hash |
| **Session Persistence** | Source hash, cookie, table | Source IP | Source IP, port hash |
| **Statistics Interface** | Web UI (built-in) | CLI (`penctl`) | HTTP status page |
| **Rate Limiting** | Yes | No | No |
| **Lua Scripting** | Yes | No | No |
| **Resource Usage** | Medium (~20MB) | Very Low (~2MB) | Very Low (~1MB) |
| **IPv6 Support** | Yes | Yes | Yes |
| **Active Development** | Yes (active) | Minimal | Minimal |
| **Learning Curve** | Moderate (config syntax) | Easy (CLI only) | Easy (CLI only) |

## Choosing the Right Tool

**Use HAProxy UDP mode when:**
- You already run HAProxy for TCP/HTTP traffic
- You need advanced features: health checks, rate limiting, Lua scripting
- You want a web-based statistics dashboard
- You need hot reload configuration without dropping connections
- Your team is already familiar with HAProxy configuration syntax

**Use Pen when:**
- You need the simplest possible UDP load balancer
- Resource constraints are tight (embedded systems, small VMs)
- You want zero-config-file overhead (CLI-only setup)
- Your load balancing needs are straightforward (round-robin or source-based)

**Use Balance when:**
- You need weighted round-robin (different traffic ratios per server)
- You want a built-in HTTP status page for monitoring
- You need SCTP load balancing alongside UDP
- You prefer CLI configuration but want more options than Pen provides

## Performance Tuning

### HAProxy UDP Optimization

```ini
# Increase UDP socket buffer sizes
global
    nbproc 1
    nbthread 4
    maxconn 100000

defaults
    # Tune UDP timeouts
    timeout client 60s
    timeout server 60s

frontend dns_udp
    # Increase receive buffer
    bind *:53 udp rcvbuf 1048576
```

### Pen Tuning

```bash
# Increase UDP receive buffer via sysctl
sudo sysctl -w net.core.rmem_max=16777216
sudo sysctl -w net.core.rmem_default=1048576

# Run Pen with increased socket buffer
pen -f -u -r -b 1048576 53 10.0.1.10:53 10.0.1.11:53
```

### Kernel UDP Buffer Tuning

```bash
# /etc/sysctl.d/99-udp-lb.conf
# Increase UDP socket buffers for high-throughput load balancing
net.core.rmem_max = 134217728
net.core.rmem_default = 16777216
net.core.wmem_max = 134217728
net.core.wmem_default = 16777216
net.core.netdev_max_backlog = 5000
net.ipv4.udp_mem = 8388608 12582912 16777216

sudo sysctl -p /etc/sysctl.d/99-udp-lb.conf
```

## FAQ

### Why can't I use Nginx for UDP load balancing?

Nginx does support UDP load balancing via the `stream` module (`stream { upstream dns_servers { ... } }`). However, this guide focused on dedicated UDP load balancers (HAProxy UDP mode, Pen, Balance) because they offer more UDP-specific features. Nginx's UDP support is functional but limited compared to HAProxy's richer feature set or Pen/Balance's simplicity. If you're already running Nginx, the `stream` module is a perfectly valid fourth option.

### How does session persistence work with UDP?

Since UDP is connectionless, there's no "session" to track in the TCP sense. Session persistence for UDP typically means: all packets from the same source IP go to the same backend server. This is called "source IP hashing" and is critical for protocols like DNS (where a client expects responses from the same server it queried) and RADIUS (where authentication state is server-local).

### Can these tools handle QUIC/HTTP3 traffic?

HAProxy has native QUIC support (since 2.8) with HTTP/3 termination. Pen and Balance operate at the raw UDP level and can forward QUIC packets, but they cannot inspect or terminate QUIC connections. For QUIC load balancing with HTTP/3 awareness, HAProxy is the only option among these three.

### What about anycast as a UDP load balancing method?

Anycast (advertising the same IP from multiple locations via BGP) is an excellent UDP load balancing technique — especially for DNS. It works at the network layer and requires no proxy software. However, anycast requires BGP configuration and multiple network locations. Our [BGP routing guide](../2026-04-19-frrouting-vs-bird-vs-openbgpd-self-hosted-bgp-routing-guide-2026/) covers BGP setup. For single-site deployments, a software load balancer is more practical.

### How do I monitor UDP load balancer health?

HAProxy provides a built-in statistics web interface (typically on port 8404) with per-backend connection counts, response times, and health status. Pen has the `penctl` CLI tool for querying runtime status. Balance provides an HTTP status page on its control port. All three can export metrics to Prometheus via sidecar exporters or built-in endpoints.

### Is UDP load balancing stateful or stateless?

It depends on the tool. Pen and Balance with source IP hashing are stateless — they compute the backend from the source IP using a hash function. HAProxy can maintain connection tables for stateful tracking (tracking which source IP is mapped to which backend). For most UDP use cases, stateless source hashing is sufficient and more resilient to restarts.

### What's the maximum throughput for these tools?

On modern hardware: HAProxy can handle 500,000+ UDP packets/sec with proper tuning. Pen can handle 200,000+ packets/sec with minimal CPU. Balance is similar to Pen. The bottleneck is usually the backend servers, not the load balancer itself. For extremely high-throughput scenarios (millions of packets/sec), consider kernel-space solutions like XDP/eBPF (covered in our [XDP/eBPF network tools guide](../2026-05-10-self-hosted-xdp-ebpf-network-tools-xdp-tools-bpftool-cilium-ebpf-guide-2026/)).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted UDP Load Balancing: HAProxy UDP Mode vs Pen vs Balance",
  "description": "Compare three open-source UDP load balancers — HAProxy UDP mode, Pen, and Balance — with Docker configs, performance tuning, and protocol-specific setups.",
  "datePublished": "2026-05-12",
  "dateModified": "2026-05-12",
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
