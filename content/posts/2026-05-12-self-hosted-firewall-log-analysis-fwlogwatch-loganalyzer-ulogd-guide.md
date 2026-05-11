---
title: "Self-Hosted Firewall Log Analysis: FWLogwatch vs LogAnalyzer vs ULOGd"
date: "2026-05-12"
tags: ["firewall", "log-analysis", "security", "network-monitoring", "self-hosted"]
draft: false
---

Firewall logs are a goldmine of security intelligence — but only if you can read them. Raw iptables, nftables, or pf logs are dense, unstructured, and impossible to parse manually at scale. This guide compares three open-source firewall log analysis tools that transform raw firewall data into actionable security insights.

## Why Firewall Log Analysis Matters

Every firewall drop, reject, and accept event tells a story about your network's security posture. Without proper analysis tools, you're flying blind — unable to spot port scans, brute force attempts, or lateral movement until it's too late.

Self-hosted firewall log analysis gives you:

- **Real-time threat detection** — Identify port scans, SYN floods, and brute force attacks as they happen
- **Compliance reporting** — Generate audit-ready reports for PCI DSS, SOC 2, and HIPAA requirements
- **Traffic visualization** — Understand which services are being targeted and from where
- **Historical trend analysis** — Spot long-term attack patterns and seasonal threat variations
- **Automated alerting** — Get notified when suspicious activity crosses defined thresholds

For broader network security monitoring, see our [IDS/IPS comparison guide](../2026-04-18-suricata-vs-snort-vs-zeek-self-hosted-ids-ips-guide-2026/) and [WAF deployment guide](../2026-04-18-bunkerweb-vs-modsecurity-vs-crowdsec-self-hosted-waf-guide-2026/). If you need DNS-layer protection, our [DNS firewall guide](../2026-04-21-self-hosted-dns-firewall-rpz-unbound-powerdns-bind9-knot-guide-2026/) covers RPZ-based blocking.

## FWLogwatch

**FWLogwatch** is a purpose-built firewall log analyzer that parses logs from iptables, ipchains, pf, ipfw, and Windows firewalls. It generates HTML and text reports with statistics on blocked packets, top attackers, and targeted ports.

### Key Features

- Multi-firewall support (iptables, ipchains, pf, ipfw, Windows)
- HTML and plain text report generation
- Port scan detection with configurable thresholds
- Top-N statistics (attackers, targeted ports, protocols)
- Time-based aggregation (hourly, daily, weekly)
- Email report delivery

### Installation

```bash
# Debian/Ubuntu
sudo apt install fwlogwatch

# RHEL/CentOS
sudo dnf install fwlogwatch
```

### Configuration

FWLogwatch uses a single configuration file at `/etc/fwlogwatch/fwlogwatch.conf`:

```ini
# /etc/fwlogwatch/fwlogwatch.conf
OUTPUT_TYPE = html
OUTPUT_DIR = /var/www/html/fwlogwatch
LOG_FILE = /var/log/syslog
RESOLVE_NAMES = yes
TIME_FORMAT = 12h
REPORT_TYPE = summary
PORTSCAN_THRESHOLD = 10
TOP_ATTACKERS = 20
TOP_PORTS = 20
TOP_PROTOCOLS = yes
EMAIL_REPORT = yes
EMAIL_TO = admin@example.com
```

### Docker Deployment

```yaml
version: "3.8"
services:
  fwlogwatch:
    image: linuxserver/fwlogwatch:latest
    container_name: fwlogwatch
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - /var/log:/var/log:ro
      - ./config:/config
      - ./output:/output
    restart: unless-stopped
```

FWLogwatch excels at quick deployment and simple report generation. Its strength is in summarizing firewall activity into digestible reports — ideal for small to medium deployments where you need a weekly security summary without complex infrastructure.

## LogAnalyzer (Adiscon)

**LogAnalyzer** (by Adiscon) is a web-based log analysis frontend for syslog data. While not firewall-specific, it includes powerful filtering, charting, and reporting capabilities that work exceptionally well with firewall logs from rsyslog, syslog-ng, and other syslog sources.

### Key Features

- Web-based GUI with real-time log viewing
- Advanced filtering and search (regex, field-based)
- Interactive charts and graphs
- User authentication and role-based access
- Custom report builder
- Supports MySQL/PostgreSQL/MSSQL backends
- Event correlation and grouping

### Installation

```bash
# Install dependencies (Debian/Ubuntu)
sudo apt install apache2 php php-mysql php-gd libapache2-mod-php mariadb-server

# Download LogAnalyzer
cd /tmp
wget https://download.adiscon.com/loganalyzer/loganalyzer-4.1.23.tar.gz
tar xzf loganalyzer-4.1.23.tar.gz
sudo cp -r loganalyzer-4.1.23/src /var/www/html/loganalyzer
sudo touch /var/www/html/loganalyzer/config.php
sudo chmod 666 /var/www/html/loganalyzer/config.php
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  loganalyzer:
    image: linuxserver/loganalyzer:latest
    container_name: loganalyzer
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=UTC
    volumes:
      - ./config:/config
      - /var/log:/var/log:ro
    ports:
      - "8080:80"
    depends_on:
      - mysql
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: loganalyzer-db
    environment:
      - MYSQL_ROOT_PASSWORD=loganalyzer_pass
      - MYSQL_DATABASE=loganalyzer
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql_data:
```

### Firewall Log Pipeline

Configure rsyslog to forward firewall logs to the LogAnalyzer database:

```bash
# /etc/rsyslog.d/30-firewall.conf
:msg, contains, "IPTABLES" /var/log/firewall.log
:msg, contains, "IPTABLES" @127.0.0.1:514

# /etc/rsyslog.d/firewall-to-mysql.conf
module(load="ommysql")
:msg, contains, "IPTABLES" :ommysql:127.0.0.1,loganalyzer,root,loganalyzer_pass
```

LogAnalyzer is the most feature-rich option, providing a full web interface with charts, filtering, and user management. It's ideal for teams that need a centralized log analysis platform that handles firewall logs alongside other syslog sources.

## ULOGd (Netfilter ULOG Daemon)

**ULOGd** is the userspace logging daemon for netfilter/iptables. Unlike FWLogwatch (which parses existing log files) and LogAnalyzer (a syslog frontend), ULOGd receives packets directly from the kernel via the NFLOG netlink target, providing richer data including full packet payloads.

### Key Features

- Direct kernel integration via NFLOG target
- Full packet payload capture (optional)
- Multiple output plugins (MySQL, PostgreSQL, SQLite, CSV, PCAP, syslog)
- Real-time streaming analysis
- Low overhead compared to LOG target
- Supports connection tracking data
- IPv4 and IPv6 support

### Installation

```bash
# Debian/Ubuntu
sudo apt install ulogd2

# RHEL/CentOS
sudo dnf install ulogd2
```

### Configuration

```ini
# /etc/ulogd.conf
[global]
logfile="/var/log/ulogd/ulogd.log"
loglevel=1
plugin="/usr/lib/ulogd/ulogd_inppkt_NFLOG.so"
plugin="/usr/lib/ulogd/ulogd_raw2packet_BASE.so"
plugin="/usr/lib/ulogd/ulogd_output_LOGEMU.so"
plugin="/usr/lib/ulogd/ulogd_output_MYSQL.so"

[logemu]
file="/var/log/ulogd/pktlog.log"
sync=1

[mysql]
table="ulog"
pass="ulogd_pass"
user="ulogd"
db="ulogd"
host="localhost"
```

### iptables/nftables Integration

```bash
# iptables NFLOG rule (replaces LOG target)
sudo iptables -A INPUT -j NFLOG --nflog-group 1 --nflog-prefix "FIREWALL: "

# nftables equivalent
sudo nft add rule inet filter input counter log group 1 prefix "FIREWALL: "
```

### Docker Deployment with MySQL

```yaml
version: "3.8"
services:
  ulogd:
    image: custom/ulogd2:latest
    container_name: ulogd
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    volumes:
      - ./ulogd.conf:/etc/ulogd.conf:ro
      - ulogd_data:/var/log/ulogd
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: ulogd-db
    environment:
      - MYSQL_ROOT_PASSWORD=ulogd_root
      - MYSQL_DATABASE=ulogd
      - MYSQL_USER=ulogd
      - MYSQL_PASSWORD=ulogd_pass
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"
    restart: unless-stopped

volumes:
  ulogd_data:
  mysql_data:
```

ULOGd is the most powerful option for deep packet analysis. Its NFLOG integration means it captures packet-level data that file-based parsers miss, making it ideal for forensic analysis and detailed threat investigation.

## Feature Comparison

| Feature | FWLogwatch | LogAnalyzer | ULOGd |
|---------|-----------|-------------|-------|
| **Firewall Support** | iptables, pf, ipfw | Any syslog source | Netfilter/NFLOG only |
| **Interface** | CLI + HTML reports | Web GUI | CLI + database output |
| **Real-time Analysis** | No (batch) | Yes | Yes |
| **Packet Payload** | No | No | Yes |
| **Database Output** | No | MySQL/PostgreSQL/MSSQL | MySQL/PostgreSQL/SQLite |
| **User Auth** | No | Yes (LDAP/AD) | No |
| **Charts/Graphs** | Basic HTML | Interactive | Via external tools |
| **Email Alerts** | Yes (reports) | Yes (via syslog) | No |
| **Docker Support** | Community images | LinuxServer.io | Custom builds |
| **Resource Usage** | Low | Medium | Low-Medium |
| **Learning Curve** | Easy | Moderate | Steep |

## Choosing the Right Tool

**Use FWLogwatch when:**
- You need quick, no-fuss firewall log reports
- Your team is small and doesn't need a web interface
- You want scheduled email summaries of firewall activity
- You manage multiple firewall types (iptables, pf, Windows)

**Use LogAnalyzer when:**
- You need a centralized web-based log analysis platform
- Your team requires user authentication and role-based access
- You want to correlate firewall logs with other syslog sources
- Interactive charts and custom reports are important

**Use ULOGd when:**
- You need packet-level forensic data (not just log lines)
- You're running Linux with netfilter/iptables/nftables
- You want direct kernel integration for lower overhead
- You need to store full packet captures alongside metadata

## Security Best Practices

1. **Separate log storage** — Store firewall logs on a dedicated log server, not on the firewall itself. Attackers who compromise the firewall could erase local logs.

2. **Encrypt log transport** — Use TLS (rsyslog with `omssl` or `omrelp`) when forwarding logs between hosts. Unencrypted syslog can be intercepted and modified.

3. **Rate-limit logging** — Use `--limit` in iptables to prevent log flooding:
   ```bash
   sudo iptables -A INPUT -m limit --limit 5/min --limit-burst 10 -j LOG --log-prefix "RATE_LIMITED: "
   ```

4. **Rotate aggressively** — Firewall logs grow quickly. Configure logrotate with daily rotation and 30-day retention:
   ```
   /var/log/firewall.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
   }
   ```

5. **Monitor the analyzer itself** — Ensure your log analysis tool is healthy. A broken FWLogwatch cron job or crashed LogAnalyzer means you're blind to attacks.

## FAQ

### What is the difference between FWLogwatch and ULOGd?

FWLogwatch parses existing firewall log files (from `/var/log/syslog` or `/var/log/kern.log`) and generates summary reports. ULOGd receives packets directly from the kernel via the NFLOG netlink target, providing richer data including optional packet payloads. FWLogwatch is simpler and works with multiple firewall types; ULOGd is more powerful but Linux/netfilter-only.

### Can LogAnalyzer parse iptables logs directly?

LogAnalyzer reads from syslog databases (MySQL, PostgreSQL, MSSQL), not directly from log files. You need to configure rsyslog or syslog-ng to parse iptables log entries and forward them to the database that LogAnalyzer queries. The `ommysql` rsyslog module handles this.

### Does ULOGd replace iptables LOG target?

Yes and no. ULOGd uses the NFLOG target, which is a more efficient replacement for the LOG target. Instead of writing to syslog (which involves disk I/O), NFLOG sends packets to userspace via netlink sockets. You change your rules from `-j LOG` to `-j NFLOG --nflog-group 1`.

### How do I detect port scans with these tools?

FWLogwatch has built-in port scan detection (configurable via `PORTSCAN_THRESHOLD`). LogAnalyzer requires you to create custom filters that group source IPs hitting multiple ports within a time window. ULOGd can store the data, but you need an external tool (like a custom SQL query or Fail2ban) to detect scan patterns.

### Can I use these tools with nftables?

FWLogwatch can parse nftables logs if they follow the same format as iptables logs. ULOGd works natively with nftables via the `log group` rule syntax. LogAnalyzer is firewall-agnostic — it works with any syslog-formatted logs, including nftables.

### How much disk space do firewall logs consume?

A busy firewall can generate 50-500 MB of logs per day. FWLogwatch reports are small (KB range) since they're summaries. LogAnalyzer's database grows with log volume — plan for 1-5 GB per month. ULOGd with packet capture enabled can consume significant space (10+ GB/day) — only enable payload capture for targeted rules, not all traffic.

### Are there commercial alternatives to these open-source tools?

Yes. Splunk, Elastic Security, and IBM QRadar provide enterprise-grade log analysis with machine learning. However, for most organizations, the combination of FWLogwatch (reports), LogAnalyzer (web interface), and ULOGd (deep analysis) covers the same use cases at zero licensing cost.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Firewall Log Analysis: FWLogwatch vs LogAnalyzer vs ULOGd",
  "description": "Compare three open-source firewall log analysis tools — FWLogwatch, LogAnalyzer, and ULOGd — with Docker deployment configs, feature comparison, and security best practices.",
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
