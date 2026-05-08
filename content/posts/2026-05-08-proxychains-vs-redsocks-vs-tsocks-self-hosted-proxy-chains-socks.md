---
title: "Self-Hosted Proxy Chains and SOCKS: proxychains-ng vs redsocks vs tsocks Guide 2026"
date: "2026-05-08"
tags: ["networking", "proxy", "socks", "proxychains", "redsocks", "privacy", "server-admin"]
draft: false
---

Routing network traffic through proxy chains is a common requirement in server administration, development, and security operations. Whether you need to route application traffic through a SOCKS5 tunnel, transparently redirect all outbound connections through a proxy, or chain multiple proxies for enhanced privacy, the right tool makes a significant difference. This guide compares three popular open-source solutions: **proxychains-ng**, **redsocks**, and **tsocks**.

## What Are Proxy Chain and SOCKS Routing Tools?

Proxy chain tools intercept application network connections and redirect them through SOCKS or HTTP proxies. Unlike system-wide proxy settings that only affect applications respecting those settings, these tools work at a lower level — either through dynamic library preloading (LD_PRELOAD) or transparent firewall redirection (iptables). This means they can route traffic from applications that have no built-in proxy support.

## proxychains-ng: Dynamic Library Proxy Interception

**proxychains-ng** (New Generation) is the actively maintained fork of the original proxychains project. It uses LD_PRELOAD to intercept socket API calls (connect, sendto, etc.) and redirects them through configured proxies. It supports SOCKS4, SOCKS5, and HTTP CONNECT proxies, and can chain multiple proxies together.

### Key Features

- LD_PRELOAD-based interception (no root required)
- SOCKS4, SOCKS5, and HTTP CONNECT proxy support
- Proxy chaining (multiple hops)
- DNS leak protection
- Per-application proxy configuration
- Random proxy selection from a pool
- Compatible with most dynamically linked binaries

### Installation

```bash
# Debian/Ubuntu
sudo apt install proxychains4

# Build from source
git clone https://github.com/rofl0r/proxychains-ng.git
cd proxychains-ng
./configure
make
sudo make install
sudo make install-config
```

### Configuration

Edit `/etc/proxychains4.conf`:

```ini
[ProxyList]
# Add proxies here - they will be used in order
socks5  127.0.0.1 1080
socks5  10.0.0.2 1080
http    192.168.1.1 3128
```

### Basic Usage

```bash
# Route a single command through proxy chain
proxychains4 curl https://api.example.com

# Run a script through proxies
proxychains4 python3 script.py

# Dynamic mode (uses proxy chain in config order)
proxychains4 -f /etc/proxychains4.conf ssh user@remote-server

# Strict chain mode (fail if any proxy is down)
proxychains4 -f /etc/proxychains4.conf strict curl https://example.com
```

### Docker Compose

```yaml
version: "3.8"
services:
  # SOCKS5 proxy (use with proxychains)
  danted:
    image: snert/docker-danted:latest
    container_name: danted-socks5
    network_mode: host
    environment:
      - CFGFILE=/etc/danted/danted.conf
    volumes:
      - ./danted.conf:/etc/danted/danted.conf:ro
    restart: unless-stopped

  # Application container with proxychains
  app:
    image: ubuntu:22.04
    container_name: proxied-app
    network_mode: host
    command: >
      bash -c "
        apt-get update && apt-get install -y proxychains4 curl &&
        proxychains4 curl -s https://api.example.com
      "
    depends_on:
      - danted
```

## redsocks: Transparent TCP-to-Proxy Redirection

**redsocks** is a transparent proxy redirector that works at the network level using iptables. It intercepts all TCP traffic destined for specific IP ranges and redirects it through a SOCKS4, SOCKS5, or HTTP proxy. Unlike proxychains-ng, it does not require LD_PRELOAD and works with any application — including statically linked binaries.

### Key Features

- Transparent redirection via iptables (no LD_PRELOAD)
- Works with statically linked binaries
- SOCKS4, SOCKS5, HTTP CONNECT, and HTTPS CONNECT
- Per-destination proxy routing rules
- UDP relay support via redudp companion
- Lightweight C implementation
- No per-application configuration needed

### Installation

```bash
# Debian/Ubuntu
sudo apt install redsocks

# Build from source
git clone https://github.com/darkk/redsocks.git
cd redsocks
make
sudo cp redsocks /usr/local/bin/
```

### Configuration

Create `/etc/redsocks.conf`:

```ini
base {
    log_debug = off;
    log_info = on;
    log = "stderr";
    daemon = off;
    redirector = iptables;
}

redsocks {
    local_ip = 0.0.0.0;
    local_port = 12345;
    ip = 127.0.0.1;
    port = 1080;
    type = socks5;
}
```

### iptables Rules

```bash
# Start redsocks daemon
sudo redsocks -c /etc/redsocks.conf

# Redirect all outbound TCP traffic to redsocks
sudo iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-ports 12345

# Redirect traffic from a specific subnet
sudo iptables -t nat -A PREROUTING -p tcp -s 192.168.1.0/24 -j REDIRECT --to-ports 12345

# Exclude local network from proxying
sudo iptables -t nat -A OUTPUT -d 192.168.0.0/16 -p tcp -j RETURN
sudo iptables -t nat -A OUTPUT -d 127.0.0.0/8 -p tcp -j RETURN
```

### Docker Deployment

```yaml
version: "3.8"
services:
  redsocks:
    image: alpine:latest
    container_name: redsocks
    network_mode: host
    cap_add:
      - NET_ADMIN
    volumes:
      - ./redsocks.conf:/etc/redsocks.conf:ro
    command: >
      sh -c "
        apk add --no-cache redsocks iptables &&
        redsocks -c /etc/redsocks.conf
      "
    restart: unless-stopped
```

## tsocks: Transparent SOCKS Interception

**tsocks** is one of the oldest transparent SOCKS tools, using LD_PRELOAD to redirect TCP connections through a SOCKS server. While largely superseded by proxychains-ng in terms of features and maintenance, it remains useful for its simplicity and low resource footprint.

### Key Features

- LD_PRELOAD-based interception
- SOCKS4 and SOCKS5 support
- Simple configuration file
- Low overhead
- Path-based proxy selection rules
- Works with most dynamically linked binaries

### Installation

```bash
# Debian/Ubuntu
sudo apt install tsocks

# Build from source
git clone https://github.com/pc/tsocks.git
cd tsocks
./configure
make
sudo make install
```

### Configuration

Edit `/etc/tsocks.conf`:

```ini
# Local networks (no proxy)
local = 192.168.0.0/255.255.255.0
local = 10.0.0.0/255.0.0.0

# Default SOCKS server
server = 127.0.0.1
server_type = 5
server_port = 1080
```

### Basic Usage

```bash
# Route a command through tsocks
tsocks curl https://api.example.com

# Use with SSH
tsocks ssh user@remote-server

# Set environment variable for automatic use
export TSOCKS_CONF_FILE=/path/to/custom/tsocks.conf
tsocks python3 script.py
```

## Comparison Table

| Feature | proxychains-ng | redsocks | tsocks |
|---------|---------------|----------|--------|
| **Interception Method** | LD_PRELOAD | iptables (transparent) | LD_PRELOAD |
| **Root Required** | No | Yes | No |
| **SOCKS4** | Yes | Yes | Yes |
| **SOCKS5** | Yes | Yes | Yes |
| **HTTP CONNECT** | Yes | Yes | No |
| **HTTPS CONNECT** | No | Yes | No |
| **Proxy Chaining** | Yes (multiple hops) | No (single proxy) | No |
| **DNS Leak Protection** | Yes | Partial | No |
| **Static Binary Support** | No | Yes | No |
| **UDP Relay** | No | Yes (redudp) | No |
| **Per-App Config** | Yes | No | No |
| **Last Active** | 2026 | 2024 | 2016 |
| **GitHub Stars** | 10,500+ | 3,600+ | 100+ |
| **License** | GPL-2.0 | MIT | GPL-2.0 |

## Why Self-Host Proxy Infrastructure

Managing your own proxy routing infrastructure gives you complete control over how traffic flows through your network. Relying on third-party proxy services or commercial solutions introduces dependencies that can affect availability, performance, and security.

Running your own proxy chain tools on self-hosted servers means you can route traffic through infrastructure you control. This is critical for organizations with compliance requirements that mandate traffic must not traverse untrusted intermediaries. With proxychains-ng, redsocks, or tsocks deployed on your own machines, you define exactly which proxies handle your traffic, where they are located, and how they are configured.

Self-hosted proxy routing also eliminates the cost of commercial proxy services. For high-volume traffic patterns — such as web scraping, API testing across regions, or distributed system monitoring — commercial proxy bandwidth costs can be substantial. Self-hosted solutions using your own server infrastructure have no per-gigabyte charges.

Furthermore, self-hosted proxy tools integrate seamlessly with your existing network infrastructure. You can route traffic through the same VLANs, use the same DNS servers, and apply the same firewall rules as your production services. This consistency simplifies troubleshooting and reduces the attack surface compared to routing traffic through external proxy networks.

For organizations managing reverse proxy deployments, understanding how to route backend traffic through proxies is essential for scenarios like multi-region failover or geo-distributed API access. Our [reverse proxy comparison](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) covers the server-side proxy configuration, while these client-side tools handle the outbound routing.

When testing proxy resilience, combining transparent proxy tools with fault injection frameworks helps you validate failover behavior. Our [chaos engineering guide](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) shows how to simulate proxy failures and verify your routing configuration handles them correctly.

For DNS privacy in proxy setups, ensuring your proxy configuration does not leak DNS queries is critical. Our [DNS query logging guide](../2026-04-23-self-hosted-dns-query-logging-analytics-dashboards-2026/) covers monitoring DNS traffic to verify that all lookups are properly routed through your configured proxy chain.

## Choosing the Right Proxy Tool

- **Use proxychains-ng** when you need per-application proxy configuration with support for proxy chaining. It is the best choice for developers who need different applications to use different proxy configurations, or when you need to route traffic through multiple proxy hops for enhanced privacy.
- **Use redsocks** when you need system-wide transparent proxy redirection that works with all applications, including statically linked binaries. Its iptables-based approach means no LD_PRELOAD limitations, and its UDP relay support via redudp makes it the most comprehensive solution for full traffic redirection.
- **Use tsocks** only when you need the absolute simplest configuration for basic SOCKS5 routing and proxychains-ng is not available. Its age and lack of active maintenance make it a last resort, but its simplicity can be an advantage in constrained environments.

## FAQ

### What is the difference between LD_PRELOAD and iptables-based proxy routing?

LD_PRELOAD (used by proxychains-ng and tsocks) intercepts socket calls at the library level by loading a shared library before the application's own libraries. This works per-process and does not require root access. iptables-based routing (used by redsocks) intercepts traffic at the kernel network stack level, affecting all traffic matching the firewall rules. This works system-wide, supports statically linked binaries, but requires root access and network namespace management.

### Can proxychains-ng work with statically linked binaries?

No. LD_PRELOAD only affects dynamically linked binaries. Static binaries like Go programs or musl-compiled tools will not be intercepted by proxychains-ng or tsocks. For these, use redsocks with iptables, or recompile the binary with dynamic linking.

### How do I prevent DNS leaks when using proxy chains?

DNS leaks occur when DNS queries bypass the proxy and go directly to your ISP's DNS server. proxychains-ng has built-in DNS leak protection (`proxy_dns` directive) that routes DNS queries through the SOCKS proxy. For redsocks, you need to redirect port 53 (DNS) traffic through a DNS-over-proxy resolver or configure your DNS server to be reachable only through the proxy. tsocks has no DNS leak protection.

### Can I chain multiple proxies with redsocks?

No. redsocks redirects traffic to a single upstream proxy. To achieve proxy chaining, you would need to run multiple redsocks instances with different iptables rules, or use proxychains-ng which supports chaining natively through its configuration file by listing multiple proxies in sequence.

### Is it legal to use proxy chains?

Using proxy chains for legitimate purposes — such as accessing geo-restricted content you are authorized to view, testing your own infrastructure, or protecting privacy — is legal in most jurisdictions. However, using proxies to bypass sanctions, access content you are not authorized to view, or conduct unauthorized activities may violate laws. Always check local regulations and terms of service.

### How does proxy chaining affect performance?

Each proxy hop adds latency (typically 10-100ms per hop) and potential bandwidth reduction. A chain of 3 proxies might reduce throughput by 20-50% compared to a direct connection, depending on the proxy servers' capacity and network conditions. For performance-critical applications, minimize the number of hops and choose proxies with low latency and high bandwidth capacity.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Proxy Chains and SOCKS: proxychains-ng vs redsocks vs tsocks Guide 2026",
  "description": "Compare proxychains-ng, redsocks, and tsocks for self-hosted proxy chains and SOCKS routing. Includes Docker configs, iptables rules, and feature comparison.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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
