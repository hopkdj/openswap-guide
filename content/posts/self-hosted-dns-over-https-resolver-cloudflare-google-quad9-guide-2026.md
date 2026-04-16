---
title: "Best Self-Hosted DNS-over-HTTPS Resolvers 2026: Cloudflare, Google, Quad9 & More"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosting DNS-over-HTTPS (DoH) resolvers in 2026. Compare Cloudflare, Google DNS, Quad9, AdGuard, and custom setups with Docker configurations and performance benchmarks."
---

DNS queries are the backbone of every internet connection, yet most people send them in plain text for anyone on the network to intercept. DNS-over-HTTPS (DoH) encrypts your DNS traffic inside standard HTTPS connections, making it indistinguishable from regular web traffic. Self-hosting your own DoH resolver gives you full control over DNS resolution, filtering policies, and logging — no third-party provider can see what domains you resolve.

## Why Self-Host a DNS-over-HTTPS Resolver

Running your own DoH resolver sits at the intersection of privacy, performance, and control. When you rely on your ISP's default DNS server, every domain lookup is visible to your provider, subject to manipulation, and potentially throttled. Even switching to a public DoH provider like Cloudflare or Google means trusting them with your full browsing history.

Self-hosting solves these problems in one step. Your resolver handles all DNS lookups locally, encrypts them via HTTPS for upstream queries, and gives you the power to block ads, trackers, and malicious domains at the DNS layer. For homelab operators, small businesses, and privacy-conscious individuals, a self-hosted DoH resolver is one of the highest-impact infrastructure upgrades you can make.

The benefits are concrete:

- **End-to-end encryption**: DNS queries are wrapped in TLS, preventing ISP snooping, public Wi-Fi interception, and on-path manipulation.
- **Custom filtering**: Block ads, malware, and adult content before requests ever leave your network.
- **Zero third-party logging**: Your DNS data never touches a provider's servers unless you configure it to.
- **Improved performance**: Local caching reduces lookup latency from 50-200ms down to sub-millisecond for repeated queries.
- **Full auditability**: Every DNS decision is transparent and logged on your own infrastructure.

## Understanding DNS-over-HTTPS

DNS-over-HTTPS works by sending DNS queries over standard HTTPS (port 443) instead of traditional DNS (port 53). The protocol uses HTTP POST or GET requests to transmit DNS wire-format data, encrypted with TLS. This approach has several advantages over DNS-over-TLS (DoT):

- **Port 443 blending**: DoH traffic looks identical to regular HTTPS traffic, making it harder to block or throttle.
- **HTTP/2 multiplexing**: Multiple queries can share a single TCP connection, reducing overhead.
- **Browser-native support**: Firefox, Chrome, and Edge all have built-in DoH configuration.
- **Flexible routing**: You can route DoH through any HTTP proxy, CDN, or load balancer.

The trade-off is that DoH gives control to the browser or OS-level resolver rather than the system DNS stack, which can complicate network-wide deployment. That's where a self-hosted DoH resolver shines — it acts as a central point for your entire network, translating encrypted DoH queries from clients into recursive DNS lookups.

## Top Self-Hosted DoH Resolver Options

### Cloudflared (Cloudflare's DoH Proxy)

Cloudflared is Cloudflare's official daemon that acts as a local DoH proxy. It listens on a local address, accepts standard DNS queries from your network, and forwards them to Cloudflare's DoH endpoint over HTTPS.

**Pros**: Extremely easy to set up, actively maintained, built-in DNS caching, automatic failover to multiple upstream DoH providers.

**Cons**: Tied to Cloudflare's ecosystem by default, limited built-in filtering (requires external tools like AdGuard Home).

**Docker Compose Setup**:

```yaml
version: "3.8"
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: proxy-dns
    environment:
      - TUNNEL_DNS_UPSTREAM=https://1.1.1.1/dns-query,https://1.0.0.1/dns-query,https://9.9.9.9/dns-query
    ports:
      - "5053:5053/udp"
      - "5053:5053/tcp"
    networks:
      - dns-network

networks:
  dns-network:
    driver: bridge
```

Once running, point your router's DNS or individual devices to `your-server-ip:5053`. Cloudflared will handle all DoH forwarding transparently.

### AdGuard Home

AdGuard Home is a full-featured network-wide ad and tracker blocker that supports DoH, DoT, and DNSCrypt as both client and server protocols. It's the most popular self-hosted DNS solution for homelabs.

**Pros**: Beautiful web dashboard, comprehensive filtering (adlists, custom blocklists), DoH/DoT/DNSCrypt support, DNS caching, per-client configuration, query logging with analytics.

**Cons**: More resource-intensive than a simple proxy, filtering rules require maintenance.

**Docker Compose Setup**:

```yaml
version: "3.8"
services:
  adguardhome:
    image: adguard/adguardhome:latest
    container_name: adguardhome
    restart: unless-stopped
    volumes:
      - ./adguard-work:/opt/adguardhome/work
      - ./adguard-conf:/opt/adguardhome/conf
    ports:
      - "53:53/udp"
      - "53:53/tcp"
      - "80:80/tcp"
      - "443:443/tcp"
      - "853:853/tcp"
      - "3000:3000/tcp"
    cap_add:
      - NET_ADMIN
    networks:
      - dns-network

networks:
  dns-network:
    driver: bridge
```

After the initial setup wizard on port 3000, configure your upstream DNS servers in the settings. You can point AdGuard Home to multiple DoH providers:

```
https://dns.quad9.net/dns-query
https://dns.adguard-dns.com/dns-query
https://cloudflare-dns.com/dns-query
```

AdGuard Home will automatically select the fastest upstream and failover on errors. The built-in filtering engine supports over 100 public blocklist sources and custom rules.

### Technitium DNS Server

Technitium DNS Server is a lesser-known but powerful option that supports DoH, DoT, and standard DNS with a clean web interface. It's written in C# and runs on .NET, making it cross-platform.

**Pros**: Built-in ad blocking, DoH server mode (clients connect directly to it via HTTPS), self-signed or Let's Encrypt TLS certificate support, recursive DNS resolver, blocklist management, DNS-over-QUIC support.

**Cons**: Smaller community than AdGuard Home, .NET runtime dependency.

**Docker Compose Setup**:

```yaml
version: "3.8"
services:
  technitium:
    image: technitium/dns-server:latest
    container_name: technitium-dns
    restart: unless-stopped
    environment:
      - DNS_SERVER_DOMAIN=dns.example.com
      - DNS_SERVER_ADMIN_PASSWORD=your-secure-password
    volumes:
      - ./dns-config:/etc/dns
    ports:
      - "5380:5380/tcp"
      - "53443:53443/tcp"
      - "53:53/udp"
      - "53:53/tcp"
      - "853:853/tcp"
    networks:
      - dns-network

networks:
  dns-network:
    driver: bridge
```

Technitium's standout feature is its ability to act as a full DoH *server* — clients can connect directly to `https://your-server:53443/dns-query` without needing a separate proxy. This makes it ideal for remote clients or mobile devices that need encrypted DNS outside your local network.

### Dnscrypt-Proxy

Dnscrypt-Proxy is a flexible DNS proxy that supports DoH, DNSCrypt, and DoT. It's designed to be lightweight and highly configurable, running as a single binary with no external dependencies.

**Pros**: Minimal resource usage, supports multiple encrypted protocols simultaneously, anonymized DNS relays, local caching, DNSCloak mobile app support, extensive configuration options.

**Cons**: No built-in web dashboard (configuration via text file), steeper learning curve.

**Docker Compose Setup**:

```yaml
version: "3.8"
services:
  dnscrypt-proxy:
    image: visibilityspots/docker-dnscrypt-proxy:latest
    container_name: dnscrypt-proxy
    restart: unless-stopped
    ports:
      - "53:53/udp"
      - "53:53/tcp"
    volumes:
      - ./dnscrypt-proxy.toml:/etc/dnscrypt-proxy/dnscrypt-proxy.toml
    networks:
      - dns-network

networks:
  dns-network:
    driver: bridge
```

The configuration file is where the magic happens. A typical `dnscrypt-proxy.toml` for DoH:

```toml
listen_addresses = ['0.0.0.0:53']

[query_log]
  file = '/var/log/dnscrypt-proxy/query.log'

[nx_log]
  file = '/var/log/dnscrypt-proxy/nx.log'

[static]
  [static.'cloudflare-doh']
    stamp = 'sdns://AQcAAAAAAAAABjEuMS4xLjEAABwAAQABAAAAAAAgAAAAAAAAAAAAGmNsb3VkZmxhcmU'

  [static.'quad9-doh']
    stamp = 'sdns://AQcAAAAAAAAABzkuOS45LjkAABwAAQABAAAAAAAgAAAAAAAAAAAAGmRucy5xdWFkOS5uZXQ'

server_names = ['cloudflare-doh', 'quad9-doh']
```

### Nginx + Unbound (DIY DoH Server)

For maximum control, you can build a DoH server from scratch using Nginx as the HTTPS frontend and Unbound as the recursive resolver. This approach gives you complete ownership of every layer.

**Pros**: Full control over TLS configuration, no third-party DNS dependency, auditable at every layer, supports any DNS backend.

**Cons**: Requires manual setup and maintenance, deeper networking knowledge needed.

**Docker Compose Setup**:

```yaml
version: "3.8"
services:
  unbound:
    image: mvance/unbound:latest
    container_name: unbound
    restart: unless-stopped
    volumes:
      - ./unbound.conf:/opt/unbound/etc/unbound/unbound.conf
    networks:
      - dns-network

  nginx-doh:
    image: nginx:alpine
    container_name: nginx-doh
    restart: unless-stopped
    depends_on:
      - unbound
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    ports:
      - "443:443/tcp"
    networks:
      - dns-network

networks:
  dns-network:
    driver: bridge
```

The Nginx configuration for DoH forwarding:

```nginx
server {
    listen 443 ssl http2;
    server_name dns.example.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location /dns-query {
        proxy_pass http://unbound:53;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
    }
}
```

This setup uses Unbound as the recursive resolver (it performs root server lookups directly, not forwarding to any provider) and Nginx as the DoH endpoint. Clients connect to `https://dns.example.com/dns-query` over HTTPS, Nginx decrypts and forwards to Unbound, and Unbound resolves the query from root servers.

## Comparison Table

| Feature | Cloudflared | AdGuard Home | Technitium | Dnscrypt-Proxy | Nginx + Unbound |
|---------|-------------|--------------|------------|-----------------|-----------------|
| **Setup Difficulty** | Easy | Easy | Moderate | Moderate | Advanced |
| **DoH Client Support** | Yes | Yes | Yes | Yes | Yes |
| **DoH Server Mode** | No | Yes | Yes | No | Yes |
| **Built-in Ad Blocking** | No | Yes | Yes | Partial | No |
| **Web Dashboard** | No | Yes | Yes | No | No |
| **DNS Caching** | Yes | Yes | Yes | Yes | Yes |
| **Resource Usage** | Low | Moderate | Moderate | Very Low | Low |
| **Multi-Protocol** | DoH only | DoH/DoT/DNSCrypt | DoH/DoT/DNSCrypt/DoQ | DoH/DNSCrypt/DoT | DoH only |
| **Per-Client Config** | No | Yes | Yes | No | No |
| **Query Logging** | Basic | Full | Full | Full | Via Unbound |
| **Best For** | Quick proxy | Full-featured homelab | Remote DoH server | Lightweight setups | Maximum control |

## Choosing the Right Upstream DoH Provider

Even with a self-hosted resolver, you need to decide which upstream DoH endpoints to query (unless using Unbound for full recursion). Here are the most trusted providers:

| Provider | DoH Endpoint | Logging Policy | Best Feature |
|----------|-------------|----------------|--------------|
| **Cloudflare** | `https://1.1.1.1/dns-query` | No persistent logs | Speed and global CDN |
| **Google** | `https://dns.google/dns-query` | 24-48 hour temp logs | Largest infrastructure |
| **Quad9** | `https://dns.quad9.net/dns-query` | No persistent logs | Malware blocking |
| **AdGuard** | `https://dns.adguard-dns.com/dns-query` | No persistent logs | Built-in ad filtering |
| **NextDNS** | `https://random-id.dns.nextdns.io/dns-query` | Configurable | Customizable blocklists |
| **Mullvad** | `https://dns.mullvad.net/dns-query` | No logs | Strong privacy stance |

For maximum privacy, configure your resolver to use multiple upstream providers with round-robin or fastest-response selection. This way, no single provider sees your full DNS query history.

## Advanced Configuration Tips

### Running DoH with TLS Certificates

If you're exposing your DoH resolver to the internet (for remote access), you need valid TLS certificates. Use Let's Encrypt with Certbot:

```bash
# Install Certbot
apt-get install certbot python3-certbot-nginx -y

# Get certificate
certbot certonly --nginx -d dns.example.com

# Auto-renew via cron
echo "0 0 * * * certbot renew --quiet" | crontab -
```

### DNS-over-HTTPS with Load Balancing

For high-availability setups, run multiple resolver instances behind a load balancer:

```yaml
version: "3.8"
services:
  haproxy:
    image: haproxy:alpine
    ports:
      - "443:443"
    volumes:
      - ./haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
      - ./certs:/etc/haproxy/certs:ro

  adguard-1:
    image: adguard/adguardhome:latest
    volumes:
      - ./adguard-1-conf:/opt/adguardhome/conf
      - ./adguard-1-work:/opt/adguardhome/work

  adguard-2:
    image: adguard/adguardhome:latest
    volumes:
      - ./adguard-2-conf:/opt/adguardhome/conf
      - ./adguard-2-work:/opt/adguardhome/work
```

HAProxy configuration for DoH load balancing:

```
frontend doh-in
    bind *:443 ssl crt /etc/haproxy/certs/dns.example.com.pem
    default_backend doh-servers

backend doh-servers
    balance roundrobin
    server adguard1 adguard-1:443 check ssl verify none
    server adguard2 adguard-2:443 check ssl verify none
```

### Monitoring Your DNS Resolver

Set up basic monitoring to track query volume, cache hit rates, and upstream response times:

```bash
# Query AdGuard Home stats via API
curl -s http://localhost:3000/control/stats | jq '.num_dns_queries'

# Monitor with Prometheus (AdGuard Home exporter)
docker run -d \
  --name adguard-exporter \
  -p 9617:9617 \
  -e ADGUARD_URL=http://adguardhome:3000 \
  ghcr.io/ebrianne/adguard-exporter:latest
```

### Firewall Rules for DNS

Ensure your DNS traffic flows correctly while blocking unencrypted DNS leaks:

```bash
# Allow DNS from local network only
iptables -A INPUT -p udp --dport 53 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 53 -s 192.168.1.0/24 -j ACCEPT

# Block all other inbound DNS
iptables -A INPUT -p udp --dport 53 -j DROP
iptables -A INPUT -p tcp --dport 53 -j DROP

# Force all outbound DNS through your resolver
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-port 53
iptables -t nat -A OUTPUT -p tcp --dport 53 -j REDIRECT --to-port 53
```

## Browser and OS Configuration

Once your DoH resolver is running, configure clients to use it:

### Firefox

1. Go to `about:preferences#privacy`
2. Scroll to "DNS over HTTPS"
3. Select "Custom"
4. Enter your resolver URL: `https://dns.example.com/dns-query`

### Chrome/Edge

1. Go to `chrome://settings/security`
2. Under "Use secure DNS", toggle on
3. Select "Custom" and enter your DoH endpoint

### macOS

macOS natively supports DoH in System Settings > Network > DNS. Add your resolver's DoH URL in the DNS over HTTPS section.

### Windows 11

Settings > Network & Internet > Ethernet/Wi-Fi > DNS server assignment > Edit > set to "Automatic (DNS over HTTPS)" and point to your resolver.

### Android

Android 9+ supports Private DNS (which uses DoT, not DoH). For DoH on mobile, use apps like Intra or configure it through a VPN profile that routes DNS to your resolver.

## Conclusion

Self-hosting a DNS-over-HTTPS resolver is one of the most impactful privacy upgrades you can make to your network infrastructure. The barrier to entry is low — AdGuard Home or Cloudflared can be running in Docker within minutes — and the benefits compound over time as you fine-tune filtering rules and monitoring.

For most users, **AdGuard Home** offers the best balance of features and usability. For those who want a pure DoH proxy with zero configuration, **Cloudflared** is the quickest path. Advanced operators who need full control and zero upstream dependency should consider the **Nginx + Unbound** combination.

Whatever you choose, the result is the same: your DNS queries are encrypted, your browsing data stays private, and you control every aspect of name resolution on your network.
