---
title: "Self-Hosted Web Proxy Guide: Squid vs Tinyproxy vs Caddy 2026"
date: 2026-04-15
tags: ["proxy", "privacy", "self-hosted", "networking", "comparison"]
draft: false
description: "Complete guide to self-hosted web proxy servers in 2026. Compare Squid, Tinyproxy, and Caddy as forward proxy solutions for privacy, caching, and network control."
---

When you browse the web, every request leaves your device and travels through your ISP's infrastructure before reaching its destination. Your internet service provider can see every domain you visit, log your browsing habits, and in many regions, sell that data to third parties. A self-hosted web proxy puts you back in control of your network traffic — encrypting, filtering, and caching your requests on your own terms.

Whether you need to bypass geographic restrictions, filter malicious content, cache frequently accessed resources to save bandwidth, or simply keep your browsing history away from your ISP, running your own proxy server is one of the most practical privacy upgrades you can make in 2026.

This guide covers three of the best open-source forward proxy servers available today — **Squid**, **Tinyproxy**, and **Caddy** — with practical deployment instructions, configuration examples, and a detailed comparison to help you choose the right tool for your needs.

## What Is a Forward Proxy and Why Self-Host One?

A **forward proxy** sits between your device and the internet. When you configure your browser or system to use a proxy, your requests go to the proxy server first. The proxy then forwards those requests to the target website on its behalf and returns the response to you.

### Key Benefits of Self-Hosting a Web Proxy

**Privacy from your ISP.** Without a proxy, your ISP sees every domain you connect to in plaintext (even with HTTPS, the SNI field reveals the domain name). A proxy hosted on a remote server means your ISP only sees a single encrypted connection to your proxy — not every site you visit.

**Content filtering and access control.** Parents can block inappropriate content. Organizations can enforce acceptable use policies. You can block ads, trackers, and malware domains at the network level before they ever reach your devices.

**Bandwidth savings through caching.** Proxy servers store copies of frequently accessed resources. When multiple devices request the same files — software updates, popular websites, streaming assets — the proxy serves cached copies instead of downloading them again. For households with many devices or offices with dozens of users, this can cut bandwidth usage by 30-60%.

**Bypassing geographic restrictions.** If you deploy a proxy in a different country, your web traffic appears to originate from that location. This is useful for accessing region-locked content, testing geo-targeted websites, or reaching services blocked in your area.

**Centralized logging and monitoring.** All outbound traffic flows through one point, making it easy to audit usage, detect anomalies, and generate reports about network activity.

## Squid: The Enterprise-Grade Forward Proxy

[Squid](https://www.squid-cache.org/) is the most mature and feature-rich open-source proxy server available. First released in 1996, it has decades of development behind it and powers proxy infrastructure for organizations worldwide. Squid supports HTTP, HTTPS, FTP, and more, with advanced caching, access control, and authentication features.

### When to Choose Squid

- You need advanced caching with fine-grained control over what gets cached and for how long
- You require authentication (LDAP, NTLM, Basic, Digest, OAuth)
- You need ICAP integration for content adaptation (virus scanning, ad blocking)
- You are managing proxy access for a large team or organization
- You want detailed access logging and SNMP monitoring

### Installing Squid with Docker

The quickest way to deploy Squid is via Docker. This configuration sets up a forward proxy with authentication and access controls:

```yaml
# docker-compose.yml
services:
  squid:
    image: sameersbn/squid:latest
    container_name: squid-proxy
    restart: unless-stopped
    ports:
      - "3128:3128"
    volumes:
      - ./squid.conf:/etc/squid/squid.conf:ro
      - ./squid-cache:/var/spool/squid
      - ./squid-log:/var/log/squid
    environment:
      - CACHE_MEM=256MB
      - CACHE_DISK=1GB
```

Create a `squid.conf` with the following configuration:

```
# squid.conf — Forward proxy with access controls

http_port 3128

# Disk cache settings
cache_dir ufs /var/spool/squid 1024 16 256
cache_mem 256 MB

# Access control lists
acl localnet src 192.168.1.0/24
acl safe_ports port 80 443 21 22 53 110 143
acl SSL_ports port 443

# Block dangerous ports
http_access deny !safe_ports
http_access deny CONNECT !SSL_ports

# Only allow local network
http_access allow localnet
http_access deny all

# Cache configuration
refresh_pattern ^ftp:           1440    20%     10080
refresh_pattern ^gopher:        1440    0%      1440
refresh_pattern -i (/cgi-bin/|\?) 0     0%      0
refresh_pattern .               0       20%     4320

# Logging
access_log /var/log/squid/access.log squid
cache_log /var/log/squid/cache.log
cache_store_log /var/log/squid/store.log
```

Start the proxy:

```bash
mkdir -p squid-cache squid-log
docker compose up -d
```

Verify it is working:

```bash
curl -x http://localhost:3128 -I https://www.google.com
# Should return HTTP/2 200
```

### Adding Basic Authentication

To require a username and password:

```
# Add to squid.conf
auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic children 5
auth_param basic realm Squid Proxy
auth_param basic credentialsttl 2 hours

acl authenticated proxy_auth REQUIRED
http_access allow authenticated localnet
http_access deny all
```

Create the password file:

```bash
# Install apache2-utils for htpasswd
apt-get install -y apache2-utils

# Create password file
htpasswd -c /etc/squid/passwd yourusername
# Enter password when prompted
```

### Enabling HTTPS Interception (SSL Bump)

For full content inspection — including blocking malicious HTTPS content — Squid can intercept and re-encrypt TLS connections. This requires generating a CA certificate:

```bash
# Generate CA certificate
openssl req -new -newkey rsa:2048 -sha256 -days 3650 \
  -nodes -x509 -extensions v3_ca \
  -keyout squid-ca.key -out squid-ca.pem
```

Then add to your `squid.conf`:

```
https_port 3129 intercept ssl-bump \
  generate-host-certificates=on \
  dynamic_cert_mem_cache_size=4MB \
  cert=/etc/squid/squid-ca.pem \
  key=/etc/squid/squid-ca.key

sslcrtd_program /usr/lib/squid/security_file_certgen \
  -s /var/spool/squid/ssl_db -M 4MB
ssl_bump peek all
ssl_bump bump all
```

**Important:** SSL bumping requires clients to trust your custom CA certificate. Install `squid-ca.pem` in each client's trusted certificate store.

## Tinyproxy: Lightweight and Simple

[Tinyproxy](https://tinyproxy.github.io/) lives up to its name — it is a small, fast, and straightforward forward proxy for HTTP and HTTPS traffic. If Squid is a Swiss Army knife, Tinyproxy is a pocket knife: it does fewer things, but it does them with minimal resource usage and simple configuration.

### When to Choose Tinyproxy

- You are running on a low-resource device like a Raspberry Pi or VPS with 256 MB RAM
- You need a basic HTTP/HTTPS forward proxy without complex caching
- You want a configuration file that fits on a single screen
- You are setting up a quick personal proxy without enterprise features
- You prefer simplicity over feature depth

### Installing Tinyproxy with Docker

```yaml
# docker-compose.yml
services:
  tinyproxy:
    image: monusky/tinyproxy:latest
    container_name: tinyproxy
    restart: unless-stopped
    ports:
      - "8888:8888"
    environment:
      - ALLOW=0.0.0.0/0
      - PORT=8888
      - BASICAUTH=user:password
```

### Manual Installation on Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y tinyproxy

# Edit configuration
sudo nano /etc/tinyproxy/tinyproxy.conf
```

A typical configuration:

```
# tinyproxy.conf

Port 8888
Listen 0.0.0.0

# Restrict access to your subnet
Allow 192.168.1.0/24
Allow 10.0.0.0/8

# Optional: require authentication
BasicAuth user yourpassword

# Disable Via header for extra privacy
DisableViaHeader Yes

# Log settings
LogLevel Info
LogFile "/var/log/tinyproxy/tinyproxy.log"

# Filter specific domains (optional)
# Filter "/etc/tinyproxy/filter"
# FilterURLs On
FilterDefaultDeny No
```

Add blocked domains to `/etc/tinyproxy/filter`, one per line:

```
\.ads\.
\.tracker\.
\.analytics\.
doubleclick\.net
facebook\.com/tr
google-analytics\.com
```

Restart and verify:

```bash
sudo systemctl restart tinyproxy
sudo systemctl enable tinyproxy

# Test from another machine
curl -x http://YOUR_SERVER_IP:8888 -I https://example.com
```

### Domain Filtering with Tinyproxy

Tinyproxy supports basic domain filtering through a text file. Enable filtering in your `tinyproxy.conf`:

```
Filter "/etc/tinyproxy/filter"
FilterURLs On
FilterDefaultDeny No
```

This approach is not as sophisticated as a dedicated ad blocker, but it blocks requests before they leave your network, reducing bandwidth and improving page load times.

## Caddy: The Modern Proxy with Automatic HTTPS

[Caddy](https://caddyserver.com/) is best known as an automatic HTTPS reverse proxy, but it can also function as a forward proxy through community plugins and its flexible module system. Caddy's standout feature is automatic TLS certificate management via Let's Encrypt — it obtains and renews certificates without any manual intervention.

### When to Choose Caddy

- You need automatic HTTPS with zero configuration
- You want a single binary that handles reverse proxy, forward proxy, and static file serving
- You prefer Caddyfile or JSON configuration over legacy config formats
- You are building a modern infrastructure stack and want consistent tooling
- You need HTTP/3 (QUIC) support out of the box

### Installing Caddy

On most Linux distributions:

```bash
# Install using the official script
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

Or via Docker:

```yaml
# docker-compose.yml
services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
      - "2019:2019"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config

volumes:
  caddy-data:
  caddy-config:
```

### Caddyfile Configuration for Forward Proxy

Caddy uses a plugin-based architecture for forward proxy support. Install the `caddy-forward-proxy` plugin using `xcaddy`:

```bash
go install github.com/caddyserver/xcaddy/cmd/xcaddy@latest
xcaddy build --with github.com/kljensen/caddy-forward-proxy
```

Then create a Caddyfile:

```
:443 {
    tls your-email@example.com

    forward_proxy {
        hide_ip
        hide_via
        auth user password
        probe_resistance secret-link.example.com
    }

    handle_path /status {
        respond "Caddy proxy is running" 200
    }
}
```

The `probe_resistance` option makes the proxy respond with a 404 for all requests that do not include proper authentication credentials. This prevents scanners and bots from detecting that a proxy is running on your server.

### Caddy as a Reverse Proxy

While this guide focuses on forward proxies, Caddy's real strength is as a reverse proxy. Here is how quickly you can set up a reverse proxy with automatic HTTPS:

```
example.com {
    reverse_proxy app-server:8080

    encode gzip zstd
    header {
        -Server
        Strict-Transport-Security max-age=31536000
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
    }
}
```

That is the entire configuration. Caddy automatically obtains an HTTPS certificate, sets up HTTP-to-HTTPS redirection, compresses responses with gzip and zstd, and adds security headers. No other proxy server makes HTTPS this effortless.

## Comparison: Squid vs Tinyproxy vs Caddy

| Feature | Squid | Tinyproxy | Caddy |
|---------|-------|-----------|-------|
| **Primary role** | Forward proxy + cache | Forward proxy | Reverse/forward proxy |
| **HTTP/HTTPS support** | Full | Full | Full + HTTP/3 |
| **Caching** | Advanced, multi-level | None | None |
| **Authentication** | LDAP, NTLM, Basic, Digest, OAuth | Basic auth | Basic auth |
| **Content filtering** | ICAP, regex, ACLs | Domain filter file | Via plugins |
| **SSL/TLS interception** | Yes (SSL bump) | No | Via plugins |
| **Automatic HTTPS** | No | No | Yes (Let's Encrypt) |
| **Configuration** | Complex (squid.conf) | Simple (tinyproxy.conf) | Modern (Caddyfile / JSON) |
| **RAM usage** | 100-500 MB | 10-30 MB | 30-100 MB |
| **Disk usage** | 50-500 MB (cache) | Less than 1 MB | 10-50 MB (certs) |
| **Learning curve** | Steep | Gentle | Moderate |
| **Best for** | Enterprise, large teams | Personal use, low-resource | Modern stacks, HTTPS-first |
| **License** | GPL-2.0 | GPL-3.0 | Apache-2.0 |
| **Active development** | Yes | Yes | Yes (very active) |
| **Docker support** | Good | Good | Excellent |

## Choosing the Right Proxy for Your Use Case

### Personal Privacy Proxy

For a single user or household, **Tinyproxy** is the simplest option. Deploy it on a $5/month VPS in the country of your choice, configure basic authentication, and point your browser at it. The entire setup takes about 10 minutes and uses less than 30 MB of RAM.

```bash
# One-line deployment on a fresh VPS
curl -fsSL https://get.docker.com | sh
docker run -d --name tinyproxy -p 8888:8888 \
  -e ALLOW=YOUR_IP/32 \
  -e BASICAUTH=user:$(openssl rand -base64 12) \
  monusky/tinyproxy:latest
```

### Office or Team Proxy

For a team of 10-100+ users, **Squid** is the clear choice. Its caching alone can reduce bandwidth costs by 30-60% when multiple people access the same resources. The advanced ACL system lets you create different access policies for different user groups — for example, allowing the engineering team unrestricted access while restricting the guest network to specific domains.

### Modern HTTPS-First Infrastructure

If you are already running Caddy as a reverse proxy for your services, adding forward proxy capabilities through plugins keeps your infrastructure consistent. The automatic HTTPS management means you never have to worry about certificate expiration, and the HTTP/3 support future-proofs your setup.

## Security Considerations

Running a proxy server introduces security responsibilities. Here are the essential hardening steps:

**Restrict access by IP.** Never leave a proxy open to the entire internet. Always limit access to specific IP addresses or subnets:

```
# Squid
acl allowed src 203.0.113.0/24
http_access allow allowed

# Tinyproxy
Allow 203.0.113.0/24
```

**Use strong authentication.** Basic authentication sends credentials in base64-encoded form. Always run your proxy over a TLS connection:

```bash
# Generate a self-signed cert for Squid
openssl req -x509 -newkey rsa:4096 -keyout key.pem \
  -out cert.pem -days 365 -nodes
```

**Keep the proxy software updated.** Proxy servers handle untrusted input from the internet. Subscribe to security advisories for your chosen proxy and apply updates promptly.

**Monitor logs for abuse.** Check your proxy logs regularly for unusual patterns — excessive requests, access to known malicious domains, or traffic from unexpected IP addresses:

```bash
# Squid: top requested domains
awk '{print $7}' /var/log/squid/access.log | \
  sort | uniq -c | sort -rn | head -20

# Tinyproxy: recent connections
tail -100 /var/log/tinyproxy/tinyproxy.log | \
  grep CONNECT | awk '{print $5}' | sort | uniq -c | sort -rn
```

**Consider using a firewall.** Even with proxy-level restrictions, add an additional layer with iptables or nftables:

```bash
# Only allow port 8888 from your IP
iptables -A INPUT -p tcp --dport 8888 \
  -s 203.0.113.50 -j ACCEPT
iptables -A INPUT -p tcp --dport 8888 -j DROP
```

## Conclusion

Self-hosting a web proxy is one of the most cost-effective privacy upgrades available in 2026. For the price of a small VPS — typically $3-5 per month — you get full control over your outbound web traffic, protection from ISP tracking, and the ability to filter content at the network level.

- **Tinyproxy** is the best choice for personal use: simple, lightweight, and fast to deploy
- **Squid** is the right tool for teams and organizations: powerful caching, granular access control, and enterprise-grade features
- **Caddy** shines when you want automatic HTTPS and a modern, consistent proxy solution across your entire infrastructure

All three are open source, actively maintained, and well-supported in Docker. Pick the one that matches your technical requirements and deploy it today — your browsing data is worth protecting.
