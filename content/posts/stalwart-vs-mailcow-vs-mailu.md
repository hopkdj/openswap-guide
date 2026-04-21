---
title: "Best Self-Hosted Email Server 2026: Stalwart vs Mailcow vs Mailu (Docker Setup)"
date: 2026-04-12
tags: ["comparison", "self-hosted", "email", "docker", "guide", "privacy"]
draft: false
description: "Compare the top self-hosted email server solutions in 2026: Stalwart Mail Server, Mailcow, and Mailu. Complete Docker compose setups, feature comparison, and deployment guides for running your own email server."
---

## Why Self-Host Your Email Server?

Email is the backbone of digital communication — yet most people hand their entire inbox to Gmail, Outlook, or Yahoo. That means **Google reads every email you send**, Microsoft scans your attachments for advertising signals, and your metadata becomes a commodity sold to brokers.

Self-hosting your email server gives you:

- **Full privacy** — no corporation scanning, indexing, or profiling your mail
- **Complete control** — your rules, your retention policy, your data
- **No account bans** — never lose access because an algorithm flagged you
- **Custom domains** — professional email without paying $6/user/month
- **Unlimited mailboxes** — create addresses for every service, family member, or project

The challenge? Email is notoriously com[plex](https://www.plex.tv/). You need SMTP, IMAP, webmail, spam filtering, DKIM/DMARC/SPF records, TLS certificates, and anti-abuse measures. Tha[docker](https://www.docker.com/)actly why turnkey Docker-based email server solutions exist.

In 2026, three solutions lead the self-hosted email space with fundamentally d[mailcow](https://mailcow.email/)t philosophies: **Stalwart Mail Server**, **Mailcow**, and **Mailu**. Let's compare them side by side.

## Quick Comparison Table

| Feature | Stalwart Mail Server | Mailcow | Mailu |
|---------|---------------------|---------|-------|
| **License** | AGPLv3 | GPL-3.0 | MIT |
| **Written In** | Rust | PHP + Python + Go + Various | Python |
| **Architecture** | Single binary | Multi-container (12+ services) | Multi-container (6-8 services) |
| **Min RAM** | ~128 MB | ~4 GB | ~1 GB |
| **CPU Cores** | 1 | 2+ recommended | 1-2 |
| **Web UI** | ✅ Built-in admin + webmail | ✅ Full admin panel | ✅ Admin panel |
| **Webmail** | ✅ Built-in (JMAP/Web) | ✅ SOGo webmail | ✅ Roundcube / SnappyMail |
| **ActiveSync** | ✅ Via JMAP | ✅ Via SOGo | ❌ Not supported |
| **Spam Filter** | ✅ Built-in (RSpamD-like) | ✅ RSpamD | ✅ RSpamD |
| **Antivirus** | ✅ ClamAV integration | ✅ ClamAV | ✅ ClamAV (optional) |
| **DNS Records** | ✅ Built-in ACME | ✅ Automated (ACME) | ✅ Automated (ACME) |
| **Calendar/Contacts** | ✅ JMAP native | ✅ SOGo (CalDAV/CardDAV) | ❌ Via SOGo add-on |
| **Multi-Domain** | ✅ Full support | ✅ Full support | ✅ Full support |
| **API** | ✅ REST + JMAP | ✅ REST API | ✅ REST API |
| **Docker Compose** | ✅ Single container | ✅ Pre-built compose | ✅ Pre-built compose |
| **Best For** | Minimalists, Rust fans, low-RAM | Teams, full-featured deployments | Budget homelabs, simplicity |

---

## 1. Stalwart Mail Server — The Modern Single-Binary Approach

**Best for**: Minimalists who want a lightweight, modern email server running on a Raspberry Pi or cheap VPS

### Key Features

Stalwart is the newcomer that's shaking up the email server space. Written entirely in **Rust**, it packs SMTP, IMAP, JMAP, Sieve filtering, spam detection, and ACME certificate management into a **single binary**. No PHP, no Python, no 12-container Docker stacks.

- **JMAP native** — Modern JSON-based mail access protocol (RFC 8620), faster and more efficient than IMAP
- **Built-in spam filtering** — No separate RSpamD or SpamAssassin process needed
- **ACME/Let's Encrypt** — Automatic TLS certificate provisioning and renewal
- **Memory-safe** — Rust eliminates entire classes of security vulnerabilities (buffer overflows, use-after-free)
- **SQLite/PostgreSQL/MySQL** — Flexible storage backends
- **Sieve scripts** — Server-side mail filtering rules
- **Single-binary deployment** — One process to manage, one log file to read

Stalwart is ideal when you want email without the operational overhead of managing a dozen microservices.

### Docker Compose Deployment

```yaml
# docker-compose.yml — Stalwart Mail Server
services:
  stalwart-mail:
    image: stalwartlabs/mail-server:latest
    container_name: stalwart-mail
    restart: unless-stopped
    ports:
      - "25:25"       # SMTP (inbound)
      - "465:465"     # SMTPS (submission, implicit TLS)
      - "587:587"     # SMTP submission (STARTTLS)
      - "993:993"     # IMAPS
      - "8080:8080"   # HTTP (JMAP + admin UI)
      - "443:443"     # HTTPS (if using built-in ACME)
    environment:
      - SERVER_HOSTNAME=mail.example.com
    volumes:
      - stalwart-data:/opt/stalwart-mail
      - ./stalwart.toml:/etc/stalwart/stalwart.toml:ro
    networks:
      - mail-net

volumes:
  stalwart-data:

networks:
  mail-net:
    driver: bridge
```

**stalwart.toml** (minimal config):

```toml
# /etc/stalwart/stalwart.toml
[server]
hostname = "mail.example.com"

[session.trust]
proxy-protocol = false

[storage]
type = "sqlite"
path = "/opt/stalwart-mail/data/stalwart.db"

[smtp.listener."127.0.0.1:25"]
protocol = "smtp"

[smtp.listener."0.0.0.0:465"]
protocol = "smtp"
tls.implicit = true

[jmap.listener."0.0.0.0:8080"]
protocol = "jmap"

[imap.listener."0.0.0.0:993"]
protocol = "imap"

[acme]
enable = true
email = "admin@example.com"
domains = ["mail.example.com"]
```

**Resource usage**: ~128 MB RAM idle, single container. Stalwart can comfortably run on a $5/month VPS or a Raspberry Pi 4.

---

## 2. Mailcow — The Full-Featured Enterprise Suite

**Best for**: Teams, businesses, and anyone who needs ActiveSync, full calendar/contacts sync, and a polished admin experience

### Key Features

Mailcow (specifically **mailcow: dockerized**) is the most feature-complete self-hosted email solution available. It bundles over a dozen services into a carefully orchestrated Docker Compose setup:

- **Postfix + Dovecot** — Battle-tested SMTP and IMAP/POP3 servers
- **SOGo** — Full groupware: webmail, calendar (CalDAV), contacts (CardDAV), and **ActiveSync** for native phone sync
- **RSpamD** — Advanced spam filtering with Bayesian learning and neural network scoring
- **ClamAV** — Real-time antivirus scanning
- **SOGo ActiveSync** — Native push email on iOS and Android without third-party apps
- **Built-in ACME** — Automatic Let's Encrypt certificates for all domains
- **OAuth2 / SAML / LDAP** — Enterprise authentication integration
- **Watchdog** — Health monitoring and auto-restart for all containers
- **Backup scripts** — Built-in incremental backup to S3 or local storage
- **REST API** — Full programmatic control for automation

Mailcow is the "just works" option. The trade-off is resource consumption — it needs at least 4 GB RAM and 2 CPU cores to run smoothly.

### Docker Compose Deployment

```yaml
# docker-compose.yml — Mailcow (simplified — use mailcow-installer for production)
services:
  unbound-mailcow:
    image: mailcow/unbound:1.23
    restart: unless-stopped
    dns:
      - 127.0.0.1
      - 1.1.1.1
    environment:
      - TZ=UTC
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.254
    volumes:
      - unbound-data:/var/cache/unbound

  redis-mailcow:
    image: redis:7-alpine
    restart: unless-stopped
    command: /etc/redis/conf.d/redis.conf
    volumes:
      - redis-data:/data
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.249

  clamd-mailcow:
    image: mailcow/clamd:1.71
    restart: unless-stopped
    environment:
      - TZ=UTC
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.250
    volumes:
      - clamd-db:/var/lib/clamav

  rspamd-mailcow:
    image: mailcow/rspamd:1.99
    restart: unless-stopped
    environment:
      - TZ=UTC
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.253
    volumes:
      - rspamd-data:/var/lib/rspamd

  postfix-mailcow:
    image: mailcow/postfix:1.80
    restart: unless-stopped
    environment:
      - TZ=UTC
      - LOG_LINES=9999
    depends_on:
      - redis-mailcow
    dns:
      - 172.22.1.254
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.252
    volumes:
      - postfix-data:/var/spool/postfix
    ports:
      - "25:25"
      - "465:465"
      - "587:587"

  dovecot-mailcow:
    image: mailcow/dovecot:2.2
    restart: unless-stopped
    environment:
      - TZ=UTC
      - MAILCOW_REPLACEME=dovecot
    depends_on:
      - redis-mailcow
    dns:
      - 172.22.1.254
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.251
    volumes:
      - vmail-data:/var/vmail
      - crypt-data:/etc/dovecot/crypt
    ports:
      - "110:110"
      - "995:995"
      - "143:143"
      - "993:993"

  sogo-mailcow:
    image: mailcow/sogo:1.133
    restart: unless-stopped
    environment:
      - TZ=UTC
      - DBNAME=sogo
    depends_on:
      - redis-mailcow
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.248
    volumes:
      - sogo-web-data:/usr/lib/GNUstep/SOGo

  acme-mailcow:
    image: mailcow/acme:1.90
    restart: unless-stopped
    dns:
      - 172.22.1.254
    environment:
      - ADDITIONAL_SAN=mail.example.com
      - ACME_CONTACT=admin@example.com
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.255
    volumes:
      - acme-data:/etc/acme

  nginx-mailcow:
    image: mailcow/nginx:1.26
    restart: unless-stopped
    depends_on:
      - sogo-mailcow
    dns:
      - 172.22.1.254
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.247
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - acme-data:/etc/acme:ro

  memcached-mailcow:
    image: memcached:alpine
    restart: unless-stopped
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.246

  olefy-mailcow:
    image: mailcow/olefy:1.13
    restart: unless-stopped
    networks:
      mailcow-network:
        ipv4_address: 172.22.1.245

networks:
  mailcow-network:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 172.22.1.0/24

volumes:
  unbound-data:
  redis-data:
  clamd-db:
  rspamd-data:
  postfix-data:
  vmail-data:
  crypt-data:
  sogo-web-data:
  acme-data:
```

> **Note**: For production, use the official Mailcow installer (`mailcow-installer`) which generates a complete `docker-compose.yml` with all services, health checks, and correct versions. The compose above shows the architecture. Install via:
> ```bash
> git clone https://github.com/mailcow/mailcow-dockerized
> cd mailcow-dockerized
> ./generate_config.sh
> docker compose pull
> docker compose up -d
> ```

**Resource usage**: ~4 GB RAM minimum, ~6 GB recommended. Needs a VPS with at least 2 vCPUs.

---

## 3. Mailu — The Lightweight & Simple Alternative

**Best for**: Homelab enthusiasts, small teams, and anyone who wants self-hosted email without the resource demands of Mailcow

### Key Features

Mailu takes a middle-ground approach. It's a Docker Compose-based email server that's significantly lighter than Mailcow but more feature-rich than a single binary. It's built with a **modular plugin architecture** — you only run the components you need.

- **Modular design** — Pick and choose components: SMTP, IMAP, webmail, admin, antivirus
- **Multiple webmail options** — Roundcube (classic) or SnappyMail (modern, lightweight)
- **RSpamD** — Same spam engine as Mailcow
- **Optional ClamAV** — Antivirus is opt-in to save RAM
- **Admin UI** — Clean Flask-based web interface for domain and mailbox management
- **REST API** — Programmatic management
- **Optional SOGo** — Add CalDAV/CardDAV if needed (not enabled by default)
- **Mitogen optimization** — Fast container startup and communication
- **Podman support** — Works with Docker or Podman

Mailu is the sweet spot for homelabs: full email functionality with the ability to trim resource usage by disabling optional components.

### Docker Compose Deployment

```yaml
# docker-compose.yml — Mailu (modular — enable only what you need)
services:
  # Core: DNS resolver
  resolver:
    image: mailu/unbound:2.0
    restart: unless-stopped
    networks:
      default:
        ipv4_address: 192.168.203.254

  # Redis for caching and rate limiting
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      default:
        ipv4_address: 192.168.203.2

  # Core: SMTP server
  smtp:
    image: mailu/postfix:2.0
    restart: unless-stopped
    depends_on:
      - resolver
      - redis
    volumes:
      - mail-data:/mail
      - dkim-data:/overrides/dkim
    ports:
      - "25:25"
      - "465:465"
      - "587:587"
    environment:
      - HOSTNAMES=mail.example.com
      - DOMAIN=example.com
      - SECRET_KEY=change-this-to-a-random-string
      - COMPOSE_PROJECT_NAME=mailu
      - DB_FLAVOR=sqlite
    networks:
      default:
        ipv4_address: 192.168.203.10

  # Core: IMAP server
  imap:
    image: mailu/dovecot:2.0
    restart: unless-stopped
    depends_on:
      - resolver
      - redis
    volumes:
      - mail-data:/mail
      - dkim-data:/overrides/dkim
    ports:
      - "110:110"
      - "995:995"
      - "143:143"
      - "993:993"
    environment:
      - HOSTNAMES=mail.example.com
      - DOMAIN=example.com
      - SECRET_KEY=change-this-to-a-random-string
      - COMPOSE_PROJECT_NAME=mailu
      - DB_FLAVOR=sqlite
    networks:
      default:
        ipv4_address: 192.168.203.11

  # Optional: Antivirus (remove to save ~500MB RAM)
  antivirus:
    image: mailu/clamav:2.0
    restart: unless-stopped
    volumes:
      - mail-data:/mail
    networks:
      default:
        ipv4_address: 192.168.203.12

  # Optional: Spam filtering
  antispam:
    image: mailu/rspamd:2.0
    restart: unless-stopped
    depends_on:
      - resolver
    volumes:
      - rspamd-data:/var/lib/rspamd
    networks:
      default:
        ipv4_address: 192.168.203.13

  # Optional: Webmail (Roundcube)
  webmail:
    image: mailu/roundcube:2.0
    restart: unless-stopped
    depends_on:
      - imap
    environment:
      - HOSTNAMES=mail.example.com
      - DOMAIN=example.com
      - SECRET_KEY=change-this-to-a-random-string
      - COMPOSE_PROJECT_NAME=mailu
    networks:
      default:
        ipv4_address: 192.168.203.20

  # Admin panel
  admin:
    image: mailu/admin:2.0
    restart: unless-stopped
    depends_on:
      - resolver
      - redis
    volumes:
      - mail-data:/mail
      - dkim-data:/overrides/dkim
      - data-data:/data
    environment:
      - HOSTNAMES=mail.example.com
      - DOMAIN=example.com
      - SECRET_KEY=change-this-to-a-random-string
      - COMPOSE_PROJECT_NAME=mailu
      - DB_FLAVOR=sqlite
      - INITIAL_ADMIN_PW=secure-password-here
    networks:
      default:
        ipv4_address: 192.168.203.30

  # Front: Reverse proxy + ACME
  front:
    image: mailu/nginx:2.0
    restart: unless-stopped
    depends_on:
      - admin
      - webmail
    volumes:
      - certs-data:/certs
    ports:
      - "80:80"
      - "443:443"
    environment:
      - HOSTNAMES=mail.example.com
      - DOMAIN=example.com
      - SECRET_KEY=change-this-to-a-random-string
      - COMPOSE_PROJECT_NAME=mailu
    networks:
      default:
        ipv4_address: 192.168.203.40

networks:
  default:
    driver: bridge
    ipam:
      driver: default
      config:
        - subnet: 192.168.203.0/24

volumes:
  redis-data:
  mail-data:
  dkim-data:
  rspamd-data:
  data-data:
  certs-data:
```

> **Note**: For production, use the official Mailu setup wizard:
> ```bash
> mkdir -p /mailu && cd /mailu
> docker run -it --rm -v /mailu:/setup -v /var/run/docker.sock:/var/run/docker.sock mailu/admin setup
> # Follow the interactive wizard, then:
> docker compose up -d
> ```

**Resource usage**: ~1 GB RAM with all components, ~512 MB if you skip ClamAV. Runs comfortably on a $10/month VPS.

---

## Performance & Resource Comparison

| Metric | Stalwart | Mailcow | Mailu |
|--------|----------|---------|-------|
| **Idle RAM** | ~128 MB | ~3.8 GB | ~800 MB |
| **Under Load (100 users)** | ~350 MB | ~5.5 GB | ~1.5 GB |
| **Disk (fresh install)** | ~200 MB | ~3 GB | ~1.5 GB |
| **Startup Time** | < 2 seconds | ~30 seconds | ~15 seconds |
| **Container Count** | 1 | 12+ | 6-8 |
| **Min VPS Cost** | $4/mo (1 vCPU, 512 MB) | $20/mo (2 vCPU, 4 GB) | $10/mo (1 vCPU, 1 GB) |
| **Message Throughput** | ~50K msgs/min (single core) | ~30K msgs/min | ~25K msgs/min |

### Benchmark Notes

- **Stalwart** benefits enormously from Rust's zero-cost abstractions. On a single-core VPS, it handles more concurrent connections than Mailcow does on 4 cores.
- **Mailcow** trades efficiency for features. The RSpamD + ClamAV + SOGo combo is resource-hungry but delivers enterprise-grade functionality.
- **Mailu** scales well when you disable ClamAV. The optional architecture means you can run a minimal mail server on a $6 VPS and add features as needed.

### When to Choose Which

| Scenario | Recommended |
|----------|-------------|
| Raspberry Pi / $5 VPS / minimal setup | **Stalwart** |
| Business with ActiveSync + calendar needs | **Mailcow** |
| Homelab on a budget, want flexibility | **Mailu** |
| Maximum deliverability & reputation tools | **Mailcow** |
| Security-focused (memory-safe codebase) | **Stalwart** |
| Want to learn email infrastructure | **Mailu** |

---

## Essential DNS Configuration (All Three)

Regardless of which email server you choose, proper DNS records are critical for deliverability. Here's what you **must** configure:

```
# DNS Records for mail.example.com
; A record — points your mail hostname to your server
mail.example.com.    IN  A      203.0.113.42

; MX record — tells the world where to send email
example.com.         IN  MX  10 mail.example.com.

; SPF — prevents spoofing
example.com.         IN  TXT  "v=spf1 mx ip4:203.0.113.42 -all"

; DKIM — cryptographically signs outgoing mail
mail._domainkey.example.com. IN TXT "v=DKIM1; k=rsa; p=MIIBIjANBgkq..."

; DMARC — policy for handling failed authentication
_dmarc.example.com.  IN  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"

; Reverse DNS (PTR) — set by your VPS provider
203.0.113.42         IN  PTR  mail.example.com.

; MTA-STS — enforces TLS for inbound mail (2026 best practice)
_mta-sts.example.com. IN TXT "v=STSv1; id=2026041200"
```

All three solutions (Stalwart, Mailcow, Mailu) will generate the DKIM key for you. The MTA-STS record is a 2026 best practice that's increasingly required by major mail providers.

---

## Frequently Asked Questions

### 1. Can I self-host email on a home network?

**Technically yes, but it's not recommended.** Most residential ISPs block port 25 (SMTP) to prevent spam. Even if your ISP allows it, residential IP addresses are on email blacklists (SORBS, Spamhaus PBL), meaning your emails will land in recipients' spam folders or get rejected entirely.

**The solution**: Use a VPS (Hetzner, OVH, DigitalOcean, Linode) with a clean IP reputation. All three solutions work great on a $5-20/month VPS.

### 2. Which solution has the best spam filtering?

**Mailcow** has the most mature spam filtering setup. Its RSpamD integration includes Bayesian learning, neural network scoring, URL reputation checks, and a web UI for managing spam rules. **Mailu** uses the same RSpamD engine but with a more basic default configuration. **Stalwart** has built-in spam detection that's improving rapidly but doesn't yet match RSpamD's ecosystem of plugins and community rules.

### 3. Do I need ActiveSync?

ActiveSync matters if you want **native push email** on iOS and Android without using third-party email apps. With ActiveSync, the Mail app on your iPhone receives new emails instantly (push) rather than checking every 15 minutes (pull). **Mailcow** supports this via SOGo. **Stalwart** supports JMAP which provides similar functionality through compatible apps. **Mailu** does not include ActiveSync by default, though you can add SOGo as an optional component.

If you're okay using the SOGo webmail, FairEmail (Android), or Apple Mail with IMAP IDLE, you don't need ActiveSync.

### 4. How difficult is it to set up and maintain?

**Stalwart** is the easiest — a single binary, one config file, and you're running. Maintenance is minimal since there are no inter-container dependencies.

**Mailcow** has the most polished setup experience (interactive installer, automatic DNS checks, built-in diagnostics) but the most complex maintenance (12+ containers to update and monitor).

**Mailu** sits in the middle — the setup wizard is straightforward, and the modular design means fewer moving parts than Mailcow. Updates are simpler because you only restart the containers you use.

### 5. Can I migrate from Gmail/Outlook to a self-hosted server?

Yes. All three solutions support IMAP migration. The typical process:

1. Generate an **app password** in your Gmail/Outlook account
2. Use `imapsync` or the built-in migration tools (Mailcow has a dedicated migration UI)
3. Point your DNS MX records to the new server
4. Configure your email clients with the new IMAP/SMTP settings

**Mailcow** makes this easiest with its web-based migration tool that walks you through the process. **Stalwart** and **Mailu** require command-line `imapsync` but the process is well-documented.

### 6. What about email deliverability — will my emails reach Gmail inboxes?

This is the #1 concern for self-hosted email. Deliverability depends on:

1. **Correct DNS records** (SPF, DKIM, DMARC, PTR/MTA-STS) — all three solutions help you set these up
2. **Clean IP reputation** — use a VPS provider known for good email IP ranges (Hetzner, OVH)
3. **Warm-up period** — new IPs need 2-4 weeks of gradual sending volume to build reputation
4. **Reverse DNS** — your VPS provider must set a PTR record (Hetzner and OVH allow this; DigitalOcean requires a support ticket)
5. **Feedback loops** — register with Gmail Postmaster Tools and Microsoft SNDS to monitor your reputation

**None** of these tools guarantee 100% inbox placement — that's a function of your IP reputation, sending patterns, and recipient provider policies. But with proper configuration, all three achieve excellent deliverability rates.

### 7. Can I run multiple mail servers behind a load balancer?

**Stalwart** supports clustering natively — multiple instances can share a PostgreSQL backend for high availability.

**Mailcow** is designed as a single-node deployment. Horizontal scaling requires external load balancing and shared storage, which is not officially supported.

**Mailu** can run multiple frontends (nginx) pointing to the same backend, but the architecture assumes a single mail server. Multi-node is possible but not officially documented.

### 8. Is JMAP (used by Stalwart) better than IMAP?

**JMAP** (JSON Meta Application Protocol, RFC 8620) is the modern successor to IMAP. It offers:

- **Batched operations** — fetch multiple messages in one request
- **Delta sync** — only download what changed since last sync
- **JSON-based** — easier for developers to work with
- **Built-in calendar/contacts** — no need for separate CalDAV/CardDAV servers

The catch: **client support** is still limited. FastMail's webmail and mobile apps support JMAP natively. Thunderbird has experimental JMAP support. Apple Mail and Outlook do not yet support JMAP. IMAP remains the universal standard.

For most users in 2026, IMAP is still the practical choice. JMAP is the future, and Stalwart is betting on it — but you'll need compatible clients to take advantage.

---

## Conclusion & Recommendation

All three solutions are production-ready, but they serve different audiences:

**Choose Stalwart Mail Server if:**
- You run on a budget VPS ($4-6/month) or a Raspberry Pi
- You value simplicity: one binary, one config file
- You care about security (Rust memory safety)
- You're comfortable with newer technology and emerging protocol standards (JMAP)

**Choose Mailcow if:**
- You need ActiveSync for native mobile email sync
- You run a team or small business that needs calendar and contacts
- You want the most polished admin experience
- You have the resources (4+ GB RAM) and don't mind managing more containers

**Choose Mailu if:**
- You want a balance between features and resource efficiency
- You like modular architecture (enable only what you need)
- You're on a mid-range VPS ($8-12/month)
- You want to understand email infrastructure while having sensible defaults

For most homelab users starting out in 2026, **Stalwart** offers the lowest barrier to entry with the smallest resource footprint. For teams and businesses, **Mailcow** remains the gold standard for feature completeness. And **Mailu** is the pragmatic middle ground that works well for most use cases.
