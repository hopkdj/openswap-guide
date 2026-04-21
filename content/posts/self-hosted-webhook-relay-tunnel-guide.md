---
title: "Best Self-Hosted ngrok Alternatives 2026: frp, Bore & Cloudflare Tunnel"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "networking", "devops"]
draft: false
description: "A comprehensive comparison of open-source and self-hosted ngrok alternatives in 2026. Learn how to set up frp, Bore, and Cloudflare Tunnel to expose local services securely without relying on paid third-party relays."
---

Developers constantly need to expose local services to the internet — for testing webhooks, demonstrating work-in-progress to clients, collaborating on APIs, or debugging integrations with external platforms. ngrok became the default solution for this, but its free tier comes with limitations: random URLs, session timeouts, connection caps, and an opaque middleman seeing all your traffic.

In 2026, the landscape of tunnel and relay tools is richer than ever. Open-source alternatives let you self-host your own relay server, use free infrastructure like Cloudflare's global network, or set up lightweight peer-to-peer tunnels. This guide covers three of the most practical options — **frp**, **Bore**, and **Cloudflare Tunnel** — with complete [docker](https://www.docker.com/)-based setup instructions and a head-to-head comparison.

## Why Self-Host Your Tunnel / Webhook Relay

Running your own relay infrastructure instead of depending on a third-party tunneling service delivers several tangible advantages:

**No middleman inspecting your traffic.** When you route through a commercial tunnel provider, all HTTP and TCP traffic passes through their servers. Even with TLS, the relay operator can see metadata, connection patterns, and in some configurations, decrypted content. Self-hosting means the traffic path is entirely under your control.

**Permanent, predictable URLs.** Free tiers of tunneling services typically assign a new random URL each session. Paid plans lock in subdomains at $10–25/month. With a self-hosted relay, you define your own domain and subdomain structure once and reuse it indefinitely.

**No connection or bandwidth limits.** Self-hosted solutions are limited only by your server's bandwidth and CPU. A $5 VPS with a 1 Gbps uplink can handle far more throughput than any free-tier tunnel service.

**Support for any protocol.** Many commercial tunnel services only support HTTP/HTTPS and limited TCP forwarding. Open-source alternatives can forward raw TCP, UDP, gRPC, and even custom protocols without restriction.

**Cost transparency.** Once you have a VPS or home server with a public IP, tunneling costs nothing extra. There are no subscription tiers, per-connection fees, or surprise overage charges.

## frp (Fast Reverse Proxy): The Battle-Tested Relayer

**frp** is one of the oldest and most widely deployed open-source reverse proxy solutions. Written in Go, it supports TCP, UDP, HTTP, HTTPS, and STCP (Secret TCP) modes. The project has been actively maintained since 2016 and is used in production environments ranging from IoT deployments to enterprise staging infrastructure.

### Architecture

frp uses a simple server-agent model:

- **frps** (server) — runs on a machine with a public IP address; accepts incoming connections and routes them to the appropriate client
- **frpc** (client) — runs on your local machine; establishes an outbound connection to frps and registers tunnel rules

The key insight: frpc initiates the connection to frps, so no inbound firewall rules are needed on the client side. This works behind NAT, corporate firewalls, and restrictive network policies.

### Docker Setup for frps (Server)

Create a Docker Compose file on your public-facing server:

```yaml
# docker-compose.yml — frps server
services:
  frps:
    image: snowdreamtech/frps:latest
    container_name: frps
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./frps.ini:/etc/frp/frps.ini:ro
```

Configuration file for the server:

```ini
# frps.ini
[common]
bind_port = 7000
bind_udp_port = 7001
kcp_bind_port = 7000
vhost_http_port = 8080
vhost_https_port = 8443
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = YOUR_DASHBOARD_PASSWORD
token = YOUR_AUTH_TOKEN
log_level = info
max_ports_per_client = 0
```

Start the server:

```bash
docker compose up -d
```

Open `http://your-server-ip:7500` to access the built-in dashboard showing active tunnels, traffic stats, and connection logs.

### Docker Setup for frpc (Client)

On your local development machine:

```yaml
# docker-compose.yml — frpc client
services:
  frpc:
    image: snowdreamtech/frpc:latest
    container_name: frpc
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./frpc.ini:/etc/frp/frpc.ini:ro
```

```ini
# frpc.ini
[common]
server_addr = your-server-ip
server_port = 7000
token = YOUR_AUTH_TOKEN

[web-app]
type = http
local_port = 3000
custom_domains = dev.yourdomain.com

[ssh-access]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 6000

[dns-server]
type = udp
local_port = 53
remote_port = 6053
```

Start the client:

```bash
docker compose up -d
```

After starting, your local app on port 3000 is accessible at `http://dev.yourdomain.com:8080`, SSH is reachable via `your-server-ip:6000`, and DNS is forwarded through UDP on port 6053.

### Production Tips

For production use, put frps behind a reverse proxy with[caddy](https://caddyserver.com/)

```yaml
services:
  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

  frps:
    image: snowdreamtech/frps:latest
    restart: unless-stopped
    volumes:
      - ./frps.ini:/etc/frp/frps.ini:ro

volumes:
  caddy_data:
  caddy_config:
```

```caddyfile
# Caddyfile
dev.yourdomain.com {
    reverse_proxy frps:8080
}
```

Caddy automatically provisions and renews TLS certificates via Let's Encrypt, giving you HTTPS without manual certificate management.

## Bore: The Minimalist Tunnel

**Bore** (written in Rust) takes a radically different approach. Where frp offers a Swiss Army knife of features, Bore does one thing extremely well: expose a single local TCP port through a public relay with minimal configuration. The entire client is a single binary with no configuration file needed.

### Why Choose Bore

- **Simplicity** — a single command starts a tunnel
- **Rust performance** — low memory footprint and fast connection handling
- **Authentication** — token-based auth prevents unauthorized use of your relay
- **CLI-first** — no dashboard, no YAML, no com[plex](https://www.plex.tv/) configuration

### Server Setup

Install Bore on your public server:

```bash
curl -sL https://github.com/ekzhang/bore/releases/latest/download/bore-x86_64-unknown-linux-musl.tar.gz \
  | tar xz -C /usr/local/bin bore
```

Or use Docker:

```yaml
services:
  bore-server:
    image: ekzhang/bore:latest
    container_name: bore-server
    restart: unless-stopped
    command: bore-server
    ports:
      - "7835:7835"     # control port
      - "8000-8100:8000-8100"  # tunnel port range
    environment:
      - BORE_SECRET=YOUR_SECRET_TOKEN
```

The port range `8000-8100` defines which remote ports clients can be assigned. Each active tunnel consumes one port from this range.

### Client Usage

On your local machine, expose port 3000:

```bash
bore local 3000 --to your-server-ip --port 8000 --secret YOUR_SECRET_TOKEN
```

That's it. The command prints the public URL and forwards all traffic from `your-server-ip:8000` to `localhost:3000`. No configuration files, no daemon management.

For HTTP-specific use with automatic HTTPS via Caddy:

```yaml
# docker-compose.yml on the server
services:
  bore-server:
    image: ekzhang/bore:latest
    restart: unless-stopped
    command: bore-server
    ports:
      - "7835:7835"
      - "8000-8100:8000-8100"
    environment:
      - BORE_SECRET=YOUR_SECRET_TOKEN

  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data

volumes:
  caddy_data:
```

```caddyfile
dev.yourdomain.com {
    reverse_proxy bore-server:8000
}
```

### When Bore Falls Short

Bore's minimalism is its strength and its limitation. It only supports TCP forwarding — no HTTP virtual hosting, no UDP, no STCP mode, no built-in dashboard. If you need multiple services behind a single relay with domain-based routing, frp is the better choice.

## Cloudflare Tunnel: The Zero-Cost Global Option

**Cloudflare Tunnel** (cloudflared) is not fully open source, but it is free to use and leverages Cloudflare's global edge network. Unlike frp or Bore, you don't need your own public server — Cloudflare's infrastructure acts as the relay. Traffic is encrypted end-to-end, and you get automatic TLS, DDoS protection, and CDN caching as bonuses.

### Architecture

Cloudflare Tunnel works by running a lightweight daemon (`cloudflared`) on your local machine. This daemon establishes outbound-only connections to the nearest Cloudflare edge location. When a request hits your domain, Cloudflare routes it through the existing tunnel — no inbound ports required.

### Installation

Install cloudflared on your local machine:

```bash
# Linux (amd64)
curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# macOS
brew install cloudflared
```

Or use Docker:

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token YOUR_TUNNEL_TOKEN
    # or use: command: tunnel run --url http://host.docker.internal:3000
```

### Quick Setup via CLI

1. **Authenticate:**

```bash
cloudflared tunnel login
```

This opens a browser to authorize cloudflared to access your Cloudflare account and creates `~/.cloudflared/cert.pem`.

2. **Create a tunnel:**

```bash
cloudflared tunnel create dev-tunnel
```

This outputs a tunnel ID (UUID) and stores credentials in `~/.cloudflared/<TUNNEL_ID>.json`.

3. **Route your domain:**

```bash
cloudflared tunnel route dns dev-tunnel dev.yourdomain.com
```

This creates a CNAME record in your Cloudflare DNS zone pointing `dev.yourdomain.com` to the tunnel.

4. **Run the tunnel:**

```bash
cloudflared tunnel run --url http://localhost:3000 dev-tunnel
```

Your local application on port 3000 is now accessible at `https://dev.yourdomain.com` with automatic HTTPS.

### Persistent Configuration

For a production setup, create a YAML config:

```yaml
# ~/.cloudflared/config.yml
tunnel: YOUR_TUNNEL_ID
credentials-file: /root/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: dev.yourdomain.com
    service: http://localhost:3000
  - hostname: api.yourdomain.com
    service: http://localhost:8080
  - hostname: admin.yourdomain.com
    service: http://localhost:9000
    # Optional: add Cloudflare Access authentication
    access:
      - required: true
        allow:
          - email: admin@yourdomain.com
  - service: http_status:404  # catch-all rule
```

Run as a system service:

```bash
sudo cloudflared --config ~/.cloudflared/config.yml service install
sudo systemctl enable --now cloudflared
```

### Cloudflare Access Integration

One unique advantage: you can add authentication without modifying your application. Cloudflare Access sits in front of your service and requires visitors to authenticate via email, SSO, or one-time PIN:

```yaml
  - hostname: admin.yourdomain.com
    service: http://localhost:9000
    access:
      - required: true
        allow:
          - email: admin@yourdomain.com
          - email: dev@yourdomain.com
```

No code changes, no OAuth setup — just configuration.

## Head-to-Head Comparison

| Feature | frp | Bore | Cloudflare Tunnel |
|---------|-----|------|-------------------|
| **Open source** | Yes (MIT) | Yes (MIT) | No (binary only) |
| **Language** | Go | Rust | Go |
| **HTTP support** | Yes, with virtual hosting | TCP only | Yes, with virtual hosting |
| **TCP support** | Yes | Yes | Yes (via TCP ingress) |
| **UDP support** | Yes | No | No |
| **STCP mode** | Yes | No | No |
| **Built-in dashboard** | Yes | No | No (Cloudflare dashboard) |
| **TLS / HTTPS** | Via reverse proxy | Via reverse proxy | Automatic |
| **Own server required** | Yes | Yes | No |
| **Cost** | Server cost only | Server cost only | Free |
| **Global edge network** | No | No | Yes (300+ locations) |
| **DDoS protection** | No | No | Yes (built into Cloudflare) |
| **Authentication** | Token-based | Secret token | Cloudflare Access (SSO, email) |
| **Multiple services** | Unlimited per client | One per connection | Unlimited via ingress rules |
| **Setup complexity** | Medium | Low | Low |
| **Docker image** | Official | Official | Official |

## Choosing the Right Tool

**Use frp when** you need a fully open-source, self-hosted solution with maximum protocol support. It handles HTTP, HTTPS, TCP, UDP, and STCP tunnels simultaneously, has a built-in dashboard for monitoring, and is battle-tested in production environments. The configuration is more involved, but the flexibility is unmatched.

**Use Bore when** you want the simplest possible setup for a quick TCP tunnel. A single command exposes any local port, and the Rust binary has a tiny memory footprint. It's perfect for ad-hoc debugging sessions, temporary demo sharing, or environments where you want minimal infrastructure. The trade-off is no HTTP virtual hosting and no UDP support.

**Use Cloudflare Tunnel when** you want a free, zero-maintenance solution with automatic HTTPS and global edge routing. It eliminates the need for a public server entirely and adds DDoS protection and CDN benefits. The main limitation is the dependency on Cloudflare's infrastructure — if Cloudflare experiences an outage, your tunnel goes down with it.

## Security Best Practices

Regardless of which tool you choose, follow these security guidelines:

1. **Never tunnel production services** without authentication. Tunnel endpoints are internet-facing by design and will be discovered by automated scanners within minutes.
2. **Use strong tokens.** The shared secret or token should be at least 32 characters and stored securely — not committed to version control.
3. **Limit exposed ports.** Only forward the specific ports you need. Do not use wide port ranges unless necessary.
4. **Add authentication layers.** Use HTTP Basic Auth, Cloudflare Access, or your application's own auth — do not rely on obscurity.
5. **Monitor connections.** All three tools provide logging. Review connection logs regularly for unexpected access patterns.
6. **Rotate tokens periodically.** If you suspect a token has been compromised, regenerate it immediately. frp requires updating both `frps.ini` and all `frpc.ini` clients; Bore requires restarting the server with a new secret; Cloudflare requires regenerating the tunnel credentials.

## Conclusion

The days of being locked into ngrok's pricing and limitations are over. Whether you need a fully self-hosted reverse proxy with protocol flexibility (frp), a minimalist one-command tunnel (Bore), or a free global-edge solution with zero infrastructure (Cloudflare Tunnel), there is a mature, well-maintained option available in 2026.

For most development teams, **frp** provides the best balance of features, transparency, and control. For quick debugging and demos, **Bore** cannot be beaten for simplicity. And for projects already on Cloudflare, **Cloudflare Tunnel** adds tunneling at zero marginal cost with enterprise-grade edge security.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
