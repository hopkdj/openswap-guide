---
title: "Fail2Ban vs SSHGuard vs CrowdSec: Self-Hosted Intrusion Prevention 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "security", "intrusion-prevention"]
draft: false
description: "Compare Fail2Ban, SSHGuard, and CrowdSec for self-hosted automated intrusion prevention. Learn which tool best protects your servers from brute-force attacks, credential stuffing, and malicious scanning in 2026."
---

When you expose any service to the internet, brute-force attacks are not a matter of *if* but *when*. SSH servers see thousands of failed login attempts per day from botnets scanning the entire IPv4 space. Web applications face credential stuffing and directory enumeration. Without automated protection, your server wastes resources on malicious traffic and eventually risks compromise.

This guide compares three self-hosted intrusion prevention systems: **Fail2Ban** (the battle-tested standard), **SSHGuard** (the lightweight alternative), and **CrowdSec** (the modern crowdsourced solution). We'll cover architecture, deployment, configuration, and help you choose the right tool for your infrastructure.

For a broader view of network security, see our [Suricata vs Snort vs Zeek IDS/IPS guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) for deep packet inspection, and our [pfSense vs OPNsense firewall router guide](../pfsense-vs-opnsense-vs-ipfire-self-hosted-firewall-router-guide-2026/) for perimeter defense.

## Why Self-Host Intrusion Prevention

Cloud providers offer managed WAF and DDoS protection, but they can't replace local log-based intrusion prevention at the server level. Self-hosted tools:

- **Monitor local log files** in real-time for authentication failures, 404 scanning, rate limit violations, and other suspicious patterns
- **Automatically ban offending IPs** via iptables, nftables, or firewall APIs before damage is done
- **Work behind any reverse proxy** — they don't depend on cloud infrastructure
- **Provide granular control** over ban duration, threshold levels, and notification preferences
- **Are completely free** with no per-request pricing or bandwidth limits

Unlike network-level IDS/IPS systems that inspect packet payloads, these tools work by parsing application logs and reacting to patterns — making them complementary to, not a replacement for, tools like [Suricata or Zeek](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/).

## Fail2Ban: The Battle-Tested Standard

[Fail2Ban](https://github.com/fail2ban/fail2ban) (17,600+ stars, updated April 2026) has been the go-to intrusion prevention tool since 2004. It monitors log files, applies configurable filters (regex patterns), and bans IPs that exceed a threshold of failures.

### How Fail2Ban Works

1. **Log monitoring** — Tail specified log files (auth.log, nginx access.log, etc.)
2. **Filter matching** — Apply regex filters to detect failed authentication, scanning, or other suspicious patterns
3. **Jail enforcement** — When a filter matches N times within a time window, trigger an action (typically iptables DROP)
4. **Auto-unban** — After a configurable ban duration, remove the block automatically

### Docker Deployment

Fail2Ban doesn't ship an official Docker Compose file, but the LinuxServer.io image provides a production-ready setup:

```yaml
# docker-compose.yml — Fail2Ban
services:
  fail2ban:
    image: lscr.io/linuxserver/fail2ban:latest
    container_name: fail2ban
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
      - /var/log:/var/log:ro
      # Mount service-specific logs
      - /var/log/auth.log:/var/log/auth.log:ro
      - /var/log/nginx/access.log:/var/log/nginx/access.log:ro
      - /var/log/nginx/error.log:/var/log/nginx/error.log:ro
    network_mode: host  # Required for iptables access
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped
```

The `network_mode: host` is critical — Fail2Ban needs to modify the host's iptables/nftables rules, which requires direct network namespace access.

### Configuration Example

```ini
# /config/fail2ban/jail.local

[DEFAULT]
bantime = 3600        # 1 hour ban
findtime = 600        # 10 minute detection window
maxretry = 5          # 5 failures before ban
backend = systemd     # Use systemd journal (or "auto" for file-based)

# SSH protection
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400       # 24 hours for SSH

# Nginx HTTP authentication
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

# Nginx bot detection (404 scanning)
[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 20
```

### Fail2Ban Strengths

- **150+ pre-built filters** — SSH, Apache, Nginx, Postfix, Dovecot, WordPress, and more
- **Massive community** — Any log format you can think of has a filter
- **Mature and stable** — 20+ years of development, extremely reliable
- **Flexible actions** — Can ban via iptables, nftables, send email, run custom scripts
- **Simple to understand** — The jail/filter/action model is straightforward

### Fail2Ban Limitations

- **No built-in dashboard** — CLI-only (`fail2ban-client status`)
- **No IP reputation data** — Only reacts to what it sees locally
- **Single-node only** — Each server independently discovers and bans IPs
- **Regex-based filters** — Can be brittle; complex log formats require custom regex

## SSHGuard: The Lightweight Alternative

[SSHGuard](https://github.com/sshguard/sshguard) (78 stars) takes a minimalist approach. Instead of parsing diverse log formats with complex regex, it hooks directly into system log mechanisms (syslog, systemd journal) and monitors for repeated authentication failures across multiple services.

### How SSHGuard Works

1. **Log ingestion** — Reads from syslog or journalctl natively (no tail + regex)
2. **Pattern detection** — Built-in parsers for SSH, FTP, SMTP, IMAP, POP3, and HTTP authentication failures
3. **IP blocking** — Adds offending IPs to firewall rulesets via pf, iptables, ipfw, or netfilter
4. **Auto-unban** — Removes blocks after the configured penalty period

### Docker Deployment

SSHGuard also lacks an official Docker image, but can be run via community images:

```yaml
# docker-compose.yml — SSHGuard
services:
  sshguard:
    image: linuxserver/sshguard:latest
    container_name: sshguard
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
      - /var/log:/var/log:ro
      - /run/systemd:/run/systemd:ro
    network_mode: host
    cap_add:
      - NET_ADMIN
    restart: unless-stopped
```

### Configuration Example

```ini
# /etc/sshguard.conf

# Backend: use iptables-standalone for direct iptables control
BACKEND="/usr/local/libexec/sshg-fw-iptables"

# Log source: systemd journal (recommended)
LOGREADER="LANG=C /bin/journalctl -afb -p info -n1 -t sshd -o cat"

# Whitelist trusted IPs (comma-separated)
WHITELIST=192.168.1.0/24,10.0.0.0/8

# Blacklist file for permanent bans
BLACKLIST_FILE=/etc/sshguard/blacklist.db

# Threshold: ban after 3 failures within 1200 seconds
# Penalty: 1200 seconds (20 minutes) minimum ban
THRESHOLD=3
BLOCK_TIME=1200
DETECTION_TIME=1200

# Services to monitor (pidfile paths or service names)
SERVICES=sshd,postfix,dovecot
```

For a custom filter on Nginx, SSHGuard uses a simpler pattern-matching approach:

```bash
# Custom Nginx auth failure detection
# Add to your log format and configure SSHGuard to parse it
log_format security '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"';
```

### SSHGuard Strengths

- **Extremely lightweight** — Written in C, minimal CPU and memory footprint
- **No regex complexity** — Built-in parsers are faster and more reliable than regex
- **Simple configuration** — Single config file with clear options
- **Multi-protocol support** — SSH, FTP, SMTP, IMAP, POP3 out of the box
- **Permanent blacklist** — Can maintain a persistent blacklist of repeat offenders

### SSHGuard Limitations

- **Small community** — Fewer contributors and less active development
- **Limited filter extensibility** — Adding support for new log formats requires C code changes
- **No crowdsourced intelligence** — Purely local detection
- **Fewer pre-built integrations** — Doesn't cover as many services as Fail2Ban

## CrowdSec: The Modern Crowdsourced Solution

[CrowdSec](https://github.com/crowdsecurity/crowdsec) (13,160+ stars, updated April 2026) represents a paradigm shift in intrusion prevention. Instead of each server independently discovering threats, CrowdSec shares IP reputation data across its entire user base. If one user's server detects a malicious IP, all other CrowdSec users are protected from it.

### How CrowdSec Works

1. **Log parsing** — Uses YAML-based parsers (not regex) to extract structured events from logs
2. **Scenario detection** — Apply behavioral scenarios (brute-force, port scan, web crawl) to parsed events
3. **Local decisions** — Ban IPs locally via bouncers (iptables, nginx, Traefik, Cloudflare)
4. **Community sharing** — Anonymously share detected malicious IPs with the CrowdSec network
5. **Global intelligence** — Receive IP reputation scores from the community CTI (Cyber Threat Intelligence) database

### Docker Deployment

CrowdSec provides official Docker images and a recommended Docker Compose setup:

```yaml
# docker-compose.yml — CrowdSec
services:
  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec
    environment:
      GID: "${GID-1000}"
      COLLECTIONS: "crowdsecurity/linux crowdsecurity/sshd crowdsecurity/nginx"
    volumes:
      - ./config/acquis.yaml:/etc/crowdsec/acquis.yaml
      - ./config/db:/var/lib/crowdsec/data/
      - ./config:/etc/crowdsec
      - /var/log:/var/log:ro
      - /var/log/nginx:/var/log/nginx:ro
    networks:
      - crowdsec
    restart: unless-stopped

  # Web UI dashboard
  metabase:
    image: metabase/metabase:latest
    container_name: crowdsec-metabase
    ports:
      - "3000:3000"
    volumes:
      - ./metabase-data:/metabase-data
    environment:
      MB_DB_FILE: /metabase-data/metabase.db
    depends_on:
      - crowdsec
    networks:
      - crowdsec
    restart: unless-stopped

networks:
  crowdsec:
    driver: bridge
```

### Acquisition Configuration

```yaml
# acquis.yaml — Tell CrowdSec which logs to monitor
---
filenames:
  - /var/log/auth.log
  - /var/log/syslog
labels:
  type: syslog
---
filenames:
  - /var/log/nginx/access.log
  - /var/log/nginx/error.log
labels:
  type: nginx
---
filenames:
  - /var/log/journal/*.log
labels:
  type: journalctl
```

### Scenario Example

```yaml
# /etc/crowdsec/scenarios/ssh-brute-force.yaml
type: trigger
name: crowdsecurity/ssh-brute-force
description: "Detect SSH brute-force attempts"
filter: "evt.Meta.log_type == 'ssh_failed-auth' && evt.Parsed.program == 'sshd'"
groupby: "evt.Meta.source_ip"
blackhole: 1m
conditions:
  - "Queue.GotifyCount > 3"
leak: true
labels:
  type: brute_force
  confidence: 1
  service: ssh
```

### Nginx Bouncer Integration

To block malicious IPs at the reverse proxy level:

```bash
# Install the Nginx bouncer
apt install crowdsec-nginx-bouncer

# /etc/crowdsec/bouncers/crowdsec-nginx-bouncer.conf
api_url: http://localhost:8080/
api_key: <your-api-key>
enabled: true

# Nginx automatically blocks IPs flagged by CrowdSec
# No additional nginx configuration needed
```

### CrowdSec Strengths

- **Crowdsourced IP intelligence** — 100M+ shared IP reputations from the community
- **Structured YAML parsers** — More reliable and maintainable than regex
- **Built-in dashboard** — Metabase integration provides visual analytics
- **Flexible bouncer architecture** — Block at iptables, nginx, Traefik, HAProxy, Cloudflare, or AWS WAF level
- **API-first design** — Full REST API for integration with other tools
- **Active development** — 13,000+ stars, frequent releases, growing ecosystem

### CrowdSec Limitations

- **More complex setup** — Parser/bouncer/scenario architecture has a steeper learning curve
- **Requires internet access** — Community sharing needs outbound connectivity (can run in local-only mode but loses crowdsourced benefits)
- **Higher resource usage** — More CPU and memory than SSHGuard or Fail2Ban
- **Privacy considerations** — Shares detected IPs with the community (anonymized, but still a consideration)

## Comparison Table

| Feature | Fail2Ban | SSHGuard | CrowdSec |
|---|---|---|---|
| **Stars / Activity** | 17,600+ / Active | 78 / Low | 13,160+ / Very Active |
| **Language** | Python | C | Go |
| **Log Parsing** | Regex filters | Built-in parsers | YAML parsers |
| **Crowdsourced IPs** | No | No | Yes (100M+ shared) |
| **Web Dashboard** | No (CLI only) | No (CLI only) | Yes (Metabase) |
| **Services Covered** | 150+ | ~10 | 50+ via collections |
| **Docker Support** | Community image | Community image | Official image |
| **Blocking Methods** | iptables, nftables | iptables, pf, ipfw | iptables, nginx, Traefik, Cloudflare |
| **IP Blacklist** | Manual | Persistent file | Local + community |
| **API** | CLI client | None | Full REST API |
| **Resource Usage** | Low | Very Low | Moderate |
| **Learning Curve** | Easy | Easy | Moderate |
| **Best For** | General-purpose servers | Minimal SSH protection | Modern infra with dashboards |

## How to Choose

### Choose Fail2Ban if:
- You need broad service coverage (150+ filters)
- You want the simplest, most battle-tested solution
- Your infrastructure is small-to-medium (single servers or a few nodes)
- You don't need a web dashboard

### Choose SSHGuard if:
- You primarily need SSH protection
- Resource usage is a critical concern (IoT, edge devices, low-memory VPS)
- You prefer minimal configuration and C-level performance
- You want a permanent blacklist for repeat offenders

### Choose CrowdSec if:
- You value crowdsourced threat intelligence
- You want a visual dashboard for security analytics
- You're running modern infrastructure (Kubernetes, containers, cloud)
- You need API integration with other security tools
- You want to block at multiple layers (host, reverse proxy, CDN)

## Recommended Architecture

For a production server, the most robust setup combines CrowdSec with a reverse proxy bouncer:

```
Internet → Traefik/Nginx (CrowdSec bouncer) → Application
                          ↑
                    CrowdSec Agent (log parser + scenario engine)
                          ↑
                    /var/log/* (auth.log, nginx access.log, etc.)
```

This blocks malicious IPs at the reverse proxy level before they even reach your application, while the CrowdSec agent continuously learns from the community threat feed.

For simpler setups (single VPS running SSH + a few services), Fail2Ban with its pre-built jails is the path of least resistance. Install, enable the `sshd` and `nginx-http-auth` jails, and you're protected within minutes.

## FAQ

### Is Fail2Ban still relevant in 2026?

Yes. Fail2Ban remains the most widely deployed intrusion prevention tool. Its 150+ pre-built filters cover virtually every common service, and its maturity means it works reliably out of the box. For many use cases, it's still the best choice despite newer alternatives.

### Can I run multiple intrusion prevention tools at the same time?

Yes, but with caution. Running Fail2Ban and CrowdSec together is possible since they use different detection mechanisms. However, running two tools that both modify iptables can cause conflicts — one tool might unban an IP that the other still wants blocked. If you run CrowdSec, it's generally recommended to disable Fail2Ban for the same services.

### Does CrowdSec work offline without internet access?

CrowdSec can run in local-only mode without sharing data with the community. You lose access to the crowdsourced IP reputation database, but local detection and banning still work normally. This is suitable for air-gapped networks or strict privacy requirements.

### How much system resources does each tool consume?

SSHGuard is the lightest, typically using less than 5 MB of RAM and near-zero CPU. Fail2Ban uses 20-50 MB RAM depending on the number of active jails. CrowdSec uses 100-300 MB RAM due to its Go runtime, parser pipeline, and database. For resource-constrained systems, SSHGuard or Fail2Ban are the better choices.

### Can these tools protect web applications against credential stuffing?

Fail2Ban and CrowdSec can both detect and block credential stuffing attacks by monitoring HTTP authentication failures in web server logs. CrowdSec has built-in scenarios specifically for HTTP credential stuffing, while Fail2Ban requires custom filter configuration for this use case. SSHGuard does not support HTTP log parsing.

### What's the difference between intrusion prevention and IDS/IPS?

Intrusion prevention tools like Fail2Ban, SSHGuard, and CrowdSec work at the application log level — they parse authentication logs and web access logs to detect and ban malicious IPs. Network IDS/IPS systems like [Suricata and Snort](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) inspect packet payloads at the network level to detect attack signatures. They serve complementary roles: IDS/IPS catches network-level attacks, while log-based tools catch application-level abuse. For full-stack security, also consider [runtime security monitoring with Falco](../falco-vs-osquery-vs-auditd-self-hosted-runtime-security-guide-2026/) and [web application protection with BunkerWeb](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Fail2Ban vs SSHGuard vs CrowdSec: Self-Hosted Intrusion Prevention 2026",
  "description": "Compare Fail2Ban, SSHGuard, and CrowdSec for self-hosted automated intrusion prevention. Learn which tool best protects your servers from brute-force attacks, credential stuffing, and malicious scanning in 2026.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
