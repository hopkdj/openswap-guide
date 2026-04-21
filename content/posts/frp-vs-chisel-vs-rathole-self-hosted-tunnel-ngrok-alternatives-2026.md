---
title: "frp vs chisel vs rathole: Best Self-Hosted Tunnel Tools 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "networking", "tunneling"]
draft: false
description: "Compare frp, chisel, and rathole — three open-source self-hosted tunnel tools that let you expose local services behind NATs to the internet. Docker configs, setup guides, and performance benchmarks included."
---

When you need to expose a local service — a development server, a self-hosted application, or an internal API — to the public internet, tunneling tools are the answer. Commercial services like ngrok made this popular, but they come with bandwidth limits, paid tiers, and the requirement to route your traffic through a third-party server.

Self-hosted tunnel tools give you full control: you run the server on your own infrastructure, set your own limits, and keep your traffic private. In this guide, we compare three of the best open-source options: **frp**, **chisel**, and **rathole**.

## Why Self-Host Your Tunnel Instead of Using ngrok?

Running your own tunnel server has several advantages over commercial alternatives:

- **No bandwidth or connection limits** — you're only constrained by your server's capacity
- **Full privacy** — traffic goes through your own server, not a third party
- **Persistent URLs** — no need to regenerate temporary URLs every session
- **Custom domains** — point your own domain to your tunnel server
- **No cost at scale** — commercial tools get expensive with heavy usage
- **Self-sovereign infrastructure** — one less external dependency in your stack

For related reading, check out our [reverse proxy comparison](../reverse-proxy-comparison/) for understanding the broader proxy landscape, our [overlay networks guide](../self-hosted-overlay-networks-zerotier-nebula-netmaker-guide-2026/) for alternative NAT traversal approaches, and our [webhook relay and tunnel guide](../self-hosted-webhook-relay-tunnel-guide/) for event-driven tunneling patterns.

## Quick Comparison Overview

| Feature | **frp** | **chisel** | **rathole** |
|---|---|---|---|
| **Language** | Go | Go | Rust |
| **GitHub Stars** | 105,986 | 15,896 | 13,373 |
| **Last Updated** | April 2026 | April 2026 | April 2026 |
| **License** | Apache 2.0 | MIT | Apache 2.0 / MIT |
| **TCP Tunneling** | Yes | Yes | Yes |
| **UDP Tunneling** | Yes | Yes | Yes |
| **HTTP/HTTPS** | Yes (built-in vhost) | No (raw TCP only) | No (raw TCP only) |
| **WebSocket** | Yes | Yes | No |
| **STCP (Secret)** | Yes | No | Yes |
| **P2P NAT Traversal** | Yes (xtcp) | No | No |
| **Encryption** | Optional (TLS) | Built-in (SSH-based) | Built-in (Noise Protocol / TLS) |
| **Auth** | Token, OIDC | User/password | Token |
| **Dashboard** | Web UI | No | No |
| **Plugin System** | Yes | No | No |
| **Config Format** | TOML | CLI args | TOML |
| **Single Binary** | Yes | Yes | Yes |
| **Best For** | Full-featured production | Quick simple tunnels | High-performance minimal setup |

## frp: The Feature-Rich Powerhouse

[frp](https://github.com/fatedier/frp) (Fast Reverse Proxy) is the most popular and feature-complete self-hosted tunnel tool, with over 105,000 GitHub stars. It supports a wide range of proxy types and includes a built-in web dashboard for monitoring.

### Key Features

- **Multiple proxy types**: TCP, UDP, HTTP, HTTPS, STCP (secret TCP), XTCP (P2P NAT traversal), TCPMUX, and SUDP
- **Built-in HTTP vhost routing**: route multiple HTTP services through a single port using host headers
- **Web dashboard**: monitor connections, bandwidth, and proxy status at a glance
- **Plugin system**: extend functionality with HTTP plugins, Unix domain socket proxies, and more
- **Client-side load balancing**: distribute traffic across multiple local services
- **Connection pooling**: pre-allocated connections for lower latency
- **Bandwidth limiting**: per-proxy bandwidth control

### Installation

Download the latest release from GitHub:

```bash
# Server (public VPS)
wget https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz
tar -xzf frp_0.61.1_linux_amd64.tar.gz
sudo cp frp_0.61.1_linux_amd64/frps /usr/local/bin/
sudo cp frp_0.61.1_linux_amd64/frps.toml /etc/frp/
```

```bash
# Client (local machine)
wget https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz
tar -xzf frp_0.61.1_linux_amd64.tar.gz
sudo cp frp_0.61.1_linux_amd64/frpc /usr/local/bin/
sudo cp frp_0.61.1_linux_amd64/frpc.toml /etc/frp/
```

### Server Configuration (frps.toml)

The frp server runs on your public VPS. Here is a minimal production-ready configuration:

```toml
# /etc/frp/frps.toml
bindPort = 7000

# Optional: enable the web dashboard
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "your_secure_password"

# Optional: enable KCP for faster UDP-based transport
# kcpBindPort = 7000

# Optional: authentication token
auth.token = "your_shared_secret_token"

# Logging
log.to = "/var/log/frps.log"
log.level = "info"
log.maxDays = 7
```

### Client Configuration (frpc.toml)

On your local machine, configure frpc to connect to the server:

```toml
# /etc/frp/frpc.toml
serverAddr = "your-vps-ip"
serverPort = 7000
auth.token = "your_shared_secret_token"

# Expose SSH over TCP
[[proxies]]
name = "ssh-tcp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 6000

# Expose a local web app via HTTP (vhost routing)
[[proxies]]
name = "webapp"
type = "http"
localPort = 8080
customDomains = ["app.example.com"]

# Expose a development server with HTTPS termination
[[proxies]]
name = "dev-https"
type = "https"
localPort = 3000
customDomains = ["dev.example.com"]
```

### [docker](https://www.docker.com/) Deployment

```yaml
# docker-compose.yml — frp server
version: "3"
services:
  frps:
    image: snowdreamtech/frps:latest
    container_name: frps
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./frps.toml:/etc/frp/frps.toml:ro
```

```yaml
# docker-compose.yml — frp client
version: "3"
services:
  frpc:
    image: snowdreamtech/frpc:latest
    container_name: frpc
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./frpc.toml:/etc/frp/frpc.toml:ro
    # For exposing Docker host services, use host networking
```

## chisel: The Minimalist TCP Tunnel

[chisel](https://github.com/jpillora/chisel) takes a different approach — it creates fast TCP/UDP tunnels over HTTP with built-in SSH encryption. At around 16,000 stars, it is smaller than frp but excels at simplicity and security-by-default.

### Key Features

- **SSH-based encryption** — all traffic is encrypted by default, no extra configuration needed
- **HTTP/HTTP2 transport** — tunnels work over standard HTTP ports (80/443), useful for restrictive firewalls
- **Single binary** — the same binary works as both client and server
- **Fast reconnect** — automatic reconnection with minimal downtime
- **User authentication** — optional credential-based access control
- **SOCKS5 proxy support** — dynamic port forwarding like SSH's `-D` flag

### Installation

```bash
# Install from GitHub releases
wget https://github.com/jpillora/chisel/releases/download/v1.10.1/chisel_1.10.1_linux_amd64
chmod +x chisel_1.10.1_linux_amd64
sudo mv chisel_1.10.1_linux_amd64 /usr/local/bin/chisel
```

### Server Setup

```bash
# Start chisel server on your VPS
# --port: listening port for incoming tunnel connections
# --key: path to SSH key for authentication (optional)
chisel server --port 9000 --reverse --auth "user:password"
```

For production, run it as a systemd service:

```ini
# /etc/systemd/system/chisel.service
[Unit]
Description=Chisel Tunnel Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/chisel server --port 9000 --reverse --auth "admin:secret123"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable chisel
sudo systemctl start chisel
```

### Client Setup

```bash
# Reverse tunnel: expose local port 8080 on the server's port 3000
chisel client --auth "user:password" your-vps-ip:9000 R:3000:127.0.0.1:8080

# SOCKS5 proxy: dynamic forwarding on local port 1080
chisel client --auth "user:password" your-vps-ip:9000 1080:socks

# Forward multiple ports at once
chisel client --auth "user:password" your-vps-ip:9000 \
  R:3000:127.0.0.1:8080 \
  R:4000:127.0.0.1:3306 \
  R:5000:127.0.0.1:5432
```

### Docker Deployment

```yaml
# docker-compose.yml — chisel server
version: "3"
services:
  chisel:
    image: jpillora/chisel:latest
    container_name: chisel-server
    restart: unless-stopped
    command: server --port 9000 --reverse --auth "admin:secret123"
    ports:
      - "9000:9000"
      # Map the remote ports that will be exposed through tunnels
      - "3000:3000"
      - "4000:4000"
```

```yaml
# docker-compose.yml — chisel client
version: "3"
services:
  chisel:
    image: jpillora/chisel:latest
    container_name: chisel-client
    restart: unless-stopped
    command: client --auth "admin:secret123" your-vps-ip:9000 R:3000:app:8080
    # Replace "app" with the service name in your Docker network
```

## rathole: The High-Performance Rust Alternative

[rathole](https://github.com/rapiz1/rathole) is a lightweight, high-performance reverse proxy written in Rust. It explicitly positions itself as an alternative to both frp and ngrok, focusing on minimal overhead and maximum throughput. With about 13,400 stars, it is the newest of the three but has a very active development cycle.

### Key Features

- **Rust performance** — memory-safe, low-latency, minimal resource footprint
- **Noise Protocol encryption** — modern cryptographic handshake, built-in by default
- **TLS support** — optional TLS transport for environments that require certificate-based security
- **TOML configuration** — consistent, human-readable config format for both server and client
- **Minimal binary size** — typically under 5 MB, significantly smaller than Go-based alternatives
- **No external dependencies** — single static binary, works on any Linux system

### Installation

```bash
# Download the latest release
wget https://github.com/rapiz1/rathole/releases/download/v0.5.0/rathole-x86_64-unknown-linux-gnu.tar.gz
tar -xzf rathole-x86_64-unknown-linux-gnu.tar.gz
sudo mv rathole /usr/local/bin/
sudo chmod +x /usr/local/bin/rathole
```

### Server Configuration (server.toml)

```toml
# /etc/rathole/server.toml
[server]
bind_addr = "0.0.0.0:2333"
default_token = "your_shared_secret"

# Optional: TLS encryption
# [server.transport]
# type = "tls"
# [server.transport.tls]
# trusted_ca_cert = "/etc/rathole/ca.crt"
# cert = "/etc/rathole/server.crt"
# key = "/etc/rathole/server.key"

# Define services
[server.services.web-app]
bind_addr = "0.0.0.0:5202"

[server.services.database]
bind_addr = "0.0.0.0:5203"

[server.services.ssh]
bind_addr = "0.0.0.0:5222"
```

### Client Configuration (client.toml)

```toml
# /etc/rathole/client.toml
[client]
remote_addr = "your-vps-ip:2333"
default_token = "your_shared_secret"

# Optional: TLS
# [client.transport]
# type = "tls"
# [client.transport.tls]
# trusted_ca_cert = "/etc/rathole/ca.crt"
# hostname = "your-vps-hostname"

# Map local services to the server
[client.services.web-app]
local_addr = "127.0.0.1:8080"

[client.services.database]
local_addr = "127.0.0.1:5432"

[client.services.ssh]
local_addr = "127.0.0.1:22"
```

### Running as a systemd Service

```ini
# /etc/systemd/system/rathole-server.service
[Unit]
Description=Rathole Tunnel Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/rathole /etc/rathole/server.toml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable rathole-server
sudo systemctl start rathole-server
sudo systemctl status rathole-server
```

### Docker Deployment

```yaml
# docker-compose.yml — rathole server
version: "3"
services:
  rathole-server:
    image: rapiz1/rathole:latest
    container_name: rathole-server
    restart: unless-stopped
    command: /app/rathole /etc/rathole/server.toml
    volumes:
      - ./server.toml:/etc/rathole/server.toml:ro
    ports:
      - "2333:2333"  # Control channel
      - "5202:5202"  # Web app tunnel
      - "5203:5203"  # Database tunnel
      - "5222:5222"  # SSH tunnel
```

```yaml
# docker-compose.yml — rathole client
version: "3"
services:
  rathole-client:
    image: rapiz1/rathole:latest
    container_name: rathole-client
    restart: unless-stopped
    command: /app/rathole /etc/rathole/client.toml
    volumes:
      - ./client.toml:/etc/rathole/client.toml:ro
    network_mode: host
```

## Performance Comparison

Based on independent benchmarks and architectural analysis:

| Metric | **frp** | **chisel** | **rathole** |
|---|---|---|---|
| **Throughput** | High (Go goroutines) | Medium (HTTP framing) | Very High (Rust async) |
| **Memory Usage** | ~15-30 MB | ~10-20 MB | ~5-10 MB |
| **Binary Size** | ~15 MB | ~10 MB | ~3-5 MB |
| **Latency** | Low (~1-3ms) | Medium (~5-10ms, HTTP overhead) | Very Low (~0.5-1ms) |
| **Concurrent Connections** | 10,000+ | 1,000-5,000 | 10,000+ |
| **CPU Usage (idle)** | Low | Very Low | Very Low |

**Key takeaways:**
- **frp** handles the highest connection counts thanks to Go's goroutine model and built-in connection pooling. It is the best choice for serving many different services through a single tunnel server.
- **chisel** has slightly higher latency due to its HTTP transport layer, but this also makes it ideal for bypassing restrictive firewalls that only allow HTTP traffic on port 80/443.
- **rathole** wins on raw performance and resource efficiency. Its Rust async runtime and minimal design make it the best choice for high-throughput, low-latency scenarios — such as streaming or database replication over tunnels.

## Choosing the Right Tool

### Use frp When:

- You need HTTP/HTTPS vhost routing for multiple web services
- You want a web dashboard to monitor your tunnels
- You need P2P NAT traversal (xtcp mode)
- You want plugin extensibility for custom proxy logic
- You are running many different services through one tunnel server
- You need STCP (secret TCP) to restrict who can connect to your tunnels

### Use chisel When:

- You need the simplest possible setup with encryption out of the box
- Your network only allows HTTP/HTTPS traffic (ports 80/443)
- You want SOCKS5 proxy support for dynamic port forwarding
- You prefer user/password authentication over shared tokens
- You need fast reconnect behavior in unstable network conditions

### Use rathole When:

- Raw throughput and low latency are your top priorities
- You want the smallest possible binary and memory footprint
- You prefer modern cryptography (Noise Protocol) over SSH-based encryption
- You are deploying on resource-constrained hardware (Raspberry Pi, small VPS)
- You want a simple TOML-based configuration without a web UI

## Security Best Practices for Self-Hosted Tunnels

Regardless of which tool you choose, follow these security guidelines:

1. **Always use authentication** — never run a tunnel server without a token or password. An unauthenticated tunnel server is an open relay for attackers.
2. **Bind to localhost where possible** — on the client side, your tunnel exposes `127.0.0.1` services. Never bind `localIP` to `0.0.0.0` unless you intend to expose your entire network.
3. **Use TLS or built-in encryption** — frp supports optional TLS, chisel encrypts by default via SSH, and rathole uses the Noise Protocol. Never send sensitive data over an unencrypted tunnel.
4. **Keep binaries updated** — all three tools release security patches regularly. Set up automated updates or monitor their GitHub release pages.
5. **Use a reverse proxy in front of your tunnel server** — place your tunnel server behind[nginx](https://nginx.org/)verse proxy (see our [nginx vs Caddy vs Traefik guide](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/)) to handle TLS termination and add an extra layer of protection.
6. **Firewall your tunnel ports** — only open the specific remote ports you need on your VPS firewall. Do not open the full port range.
7. **Monitor connection logs** — frp's dashboard and log files help you spot unauthorized connection attempts. For chisel and rathole, use systemd journal or external log aggregation.

## FAQ

### Is it legal to run your own tunnel server?

Yes. Running a self-hosted tunnel server on your own infrastructure is completely legal. It is functionally equivalent to running any other network service. The key difference from commercial tools like ngrok is that you control the server and the traffic flow.

### Can I use these tunnel tools with Cloudflare?

Yes, you can point a Cloudflare-managed domain to your tunnel server's IP address. For HTTPS, Cloudflare can handle TLS termination at the edge. However, if you want end-to-end encryption, configure TLS on the tunnel itself as well. For Cloudflare-specific tunneling, note that Cloudflare Tunnel (`cloudflared`) is a separate tool with its own architecture.

### Which tunnel tool is fastest for database replication?

**rathole** is the best choice for database replication due to its minimal latency and high throughput. Its Rust async runtime handles sustained high-bandwidth transfers [postgresql](https://www.postgresql.org/)iently than Go-based alternatives. For PostgreSQL or MySQL replication over a WAN connection, rathole's low overhead makes a measurable difference in sync times.

### Can I expose multiple services through a single tunnel?

Yes. All three tools support multiple service tunnels from a single client connection. In frp, define multiple `[[proxies]]` blocks. In chisel, pass multiple `R:port:host:localport` arguments. In rathole, define multiple `[client.services.*]` sections in your TOML config.

### How do I handle TLS/HTTPS for tunneled services?

You have two options. **Option 1**: Use frp's built-in HTTPS proxy type, which handles TLS termination at the tunnel server. **Option 2**: Run a reverse proxy (nginx, Caddy, or Traefik) on your VPS in front of the tunnel server, and let it handle TLS for all services. The second approach is more flexible and works with all three tunnel tools.

### Are these tools suitable for production use?

Yes, all three are used in production environments. **frp** has the largest user base and the most battle-tested track record with over 105,000 stars. **chisel** is widely used for pentesting and development scenarios. **rathole** is newer but its Rust foundation gives it strong safety guarantees. For mission-critical production workloads, frp's maturity and monitoring dashboard give it the edge.

### What happens if the tunnel connection drops?

All three tools implement automatic reconnection. **frp** uses heartbeat detection and reconnects with configurable intervals. **chisel** is known for particularly fast reconnection behavior. **rathole** reconnects automatically on connection loss. For production setups, consider running the client as a systemd service with `Restart=always` to ensure recovery even if the process crashes.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "frp vs chisel vs rathole: Best Self-Hosted Tunnel Tools 2026",
  "description": "Compare frp, chisel, and rathole — three open-source self-hosted tunnel tools that let you expose local services behind NATs to the internet. Docker configs, setup guides, and performance benchmarks included.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
