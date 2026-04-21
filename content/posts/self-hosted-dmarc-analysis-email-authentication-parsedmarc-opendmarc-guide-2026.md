---
title: "Self-Hosted DMARC Analysis & Email Authentication Guide 2026"
date: 2026-04-21
tags: ["comparison", "guide", "self-hosted", "email", "security", "dmarc"]
draft: false
description: "Compare self-hosted DMARC report analysis tools — parsedmarc, OpenDMARC, and Open-DMARC-Analyzer. Learn to monitor email authentication, detect spoofing, and enforce DMARC policies without SaaS."
---

If you run your own mail server, protecting your domain from spoofing and phishing is non-negotiable. DMARC (Domain-based Message Authentication, Reporting, and Conformance) is the standard that ties SPF and DKIM together, telling receiving servers what to do when authentication fails — and sending you reports about every attempt to impersonate your domain.

The problem? DMARC aggregate reports arrive as gzipped XML files in your inbox. Reading them manually is impossible at scale. SaaS solutions like Dmarcian, Valimail, and EasyDMARC charge monthly fees to parse and visualize them. This guide covers the best **self-hosted alternatives** that give you full control over your DMARC data — for free.

## Why Self-Host Your DMARC Analysis?

Running your own DMARC analyzer has several advantages over SaaS:

- **Complete data ownership** — your DMARC reports contain sensitive information about who sends email on your behalf. Self-hosting keeps this data on your infrastructure.
- **No monthly fees** — SaaS DMARC analyzers typically charge $10–$100+/month depending on domain count and report volume.
- **No report volume limits** — parse every single aggregate report without hitting tier caps.
- **Full customization** — build custom dashboards, alerting rules, and integrations with your existing monitoring stack.
- **Regulatory compliance** — some industries require that authentication data never leaves your controlled infrastructure.

For a complete guide to setting up the mail server itself, see our [Postfix + Dovecot + Rspamd mail server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/). If you're also looking into email aliases for additional domain protection, check out our [SimpleLogin vs AnonAddy comparison](../2026-04-20-simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/).

## How DMARC Works: SPF, DKIM, and DMARC Together

Before diving into tools, it helps to understand the three pillars of email authentication:

| Protocol | What It Does | How It Works |
|----------|-------------|-------------|
| **SPF** (Sender Policy Framework) | Verifies the sending server is authorized | DNS TXT record listing allowed IP addresses |
| **DKIM** (DomainKeys Identified Mail) | Verifies the email wasn't tampered with in transit | Cryptographic signature in email headers |
| **DMARC** | Tells receivers what to do when SPF/DKIM fail | DNS TXT record with policy (`none`, `quarantine`, `reject`) |

DMARC adds two critical capabilities:
1. **Policy enforcement** — tells receiving servers whether to reject, quarantine, or simply monitor emails that fail authentication.
2. **Reporting** — domain owners receive aggregate (XML) and forensic (individual email) reports showing authentication results across all receiving servers.

The aggregate reports (sent to the `rua` address in your DMARC record) are where the analysis tools come in. Each report covers a 24-hour window and details every source IP that attempted to send email using your domain, whether it passed SPF/DKIM, and the volume of messages.

## Top Self-Hosted DMARC Analysis Tools

Here's a comparison of the leading open-source DMARC analysis solutions:

| Feature | **parsedmarc** | **OpenDMARC** | **Open-DMARC-Analyzer** |
|---------|---------------|---------------|------------------------|
| **Language** | Python | C | PHP |
| **Stars** | 1,233 | 129 | 269 |
| **Last Updated** | April 2026 | May 2025 | June 2024 |
| **Type** | Report parser + dashboard | Milter (policy enforcement) | Web dashboard |
| **Database** | Elasticsearch / OpenSearch | SQLite / syslog | MySQL / PostgreSQL |
| **Web UI** | Kibana / Grafana dashboards | None (log-based) | Built-in PHP dashboard |
| **Aggregate Reports** | ✅ Parses and indexes | ✅ Processes | ✅ Displays (pre-parsed data) |
| **Forensic Reports** | ✅ Parses and indexes | ✅ Processes | ❌ |
| **Policy Enforcement** | ❌ | ✅ (milter) | ❌ |
| **TLS Reporting** | ✅ (TLS-RPT) | ❌ | ❌ |
| **Docker Support** | ✅ Official compose | ⚠️ Manual setup | ⚠️ Manual setup |
| **Best For** | Full analysis pipeline | Mail server integration | Lightweight web dashboard |

### parsedmarc — The Comprehensive DMARC Parser

[parsedmarc](https://github.com/domainaware/parsedmarc) is the most popular self-hosted DMARC analysis tool, written in Python by Sean Whalen. It fetches aggregate and forensic reports from a dedicated IMAP mailbox, parses the XML, and indexes results into Elasticsearch or OpenSearch for visualization with Kibana or Grafana.

**Key features:**
- Parses both aggregate and forensic DMARC reports
- Supports TLS Reporting (TLS-RPT) analysis
- Real-time dashboard with Kibana or Grafana
- Handles multiple domains and organizations
- IMAP-based report collection (works with any mail provider)
- Active development with regular updates

### OpenDMARC — Policy Enforcement at the Mail Server Level

[OpenDMARC](https://github.com/trusteddomainproject/OpenDMARC) from the Trusted Domain Project is a C-based milter (mail filter) that integrates directly with Postfix, Sendmail, and other MTAs. Rather than analyzing reports, it **enforces** DMARC policy on incoming mail — checking SPF and DKIM alignment and applying the domain's published policy (none, quarantine, or reject).

**Key features:**
- Real-time DMARC policy enforcement on incoming mail
- Integrates as a milter with Postfix and Sendmail
- Logs authentication results for later analysis
- Lightweight and battle-tested
- Can generate historical authentication reports

OpenDMARC doesn't parse incoming DMARC reports — it enforces policy. Pair it with parsedmarc for a complete solution.

### Open-DMARC-Analyzer — Lightweight Web Dashboard

[Open-DMARC-Analyzer](https://github.com/userjack6880/Open-DMARC-Analyzer) is a PHP-based web application that provides a visual dashboard for DMARC reports. It works with data pre-parsed by tools like `rrdmarc` or `dmarcts-report-parser`, presenting authentication results in an easy-to-read web interface backed by MySQL or PostgreSQL.

**Key features:**
- Simple PHP web interface — no Elasticsearch required
- Timeline visualization of DMARC results
- Domain and source IP breakdowns
- Pass/fail rate charts
- Lightweight resource requirements

This is ideal for administrators who want a visual dashboard without the overhead of an Elasticsearch cluster.

## Setting Up parsedmarc with Docker Compose

parsedmarc provides an official Docker Compose configuration that deploys the parser alongside Elasticsearch or OpenSearch. Here's a production-ready setup using OpenSearch (the open-source Elasticsearch alternative):

```yaml
version: "3.8"

services:
  opensearch:
    image: opensearchproject/opensearch:2
    environment:
      - discovery.type=single-node
      - node.name=opensearch
      - bootstrap.memory_lock=true
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=YourSecurePassword123!
      - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - opensearch-data:/usr/share/opensearch/data
    ports:
      - "127.0.0.1:9200:9200"
    ulimits:
      memlock:
        soft: -1
        hard: -1
    healthcheck:
      test: ["CMD-SHELL", "curl -sk -u admin:YourSecurePassword123! https://localhost:9200/_cluster/health | grep -q 'green\\|yellow'"]
      interval: 10s
      timeout: 10s
      retries: 24

  parsedmarc:
    image: domainaware/parsedmarc:latest
    depends_on:
      opensearch:
        condition: service_healthy
    volumes:
      - ./parsedmarc.ini:/etc/parsedmarc.ini:ro
    restart: unless-stopped

volumes:
  opensearch-data:
```

Create a `parsedmarc.ini` configuration file:

```ini
[general]
host = opensearch
port = 9200
username = admin
password = YourSecurePassword123!
ssl = true
verify = false

[mailbox]
host = mail.example.com
port = 993
ssl = true
user = dmarc-reports@example.com
password = your-mailbox-password

[watchdog]
interval = 60
```

Start the stack:

```bash
docker compose up -d
```

The parser will begin fetching DMARC reports from the configured mailbox every 60 seconds and indexing them into OpenSearch. You can then connect Kibana or Grafana to visualize the data.

## Setting Up OpenDMARC as a Postfix Milter

OpenDMARC integrates into your mail server as a milter, checking incoming email against DMARC policy. Here's how to configure it with Postfix.

### 1. Install OpenDMARC

```bash
# Debian/Ubuntu
sudo apt install opendmarc

# RHEL/CentOS/Rocky
sudo dnf install opendmarc
```

### 2. Configure OpenDMARC

Edit `/etc/opendmarc.conf`:

```ini
# Connect to Postfix via Unix socket
Socket local:/var/run/opendmarc/opendmarc.sock

# Use a separate user/group
UserID opendmarc:opendmarc

# History file for reporting
HistoryFile /var/run/opendmarc/opendmarc.dat

# Reject messages that fail DMARC (for your own enforcement)
RejectFailures false

# Trusted authentication results from upstream
TrustedAuthservIDs YOUR_HOSTNAME

# Ignore mail from authenticated users (local submission)
IgnoreAuthenticatedClients true

# Ignore localhost
IgnoreHosts /etc/opendmarc/ignore.hosts
```

### 3. Configure Postfix to Use the Milter

Add to `/etc/postfix/main.cf`:

```ini
# OpenDMARC milter
smtpd_milters = unix:/var/run/opendmarc/opendmarc.sock
non_smtpd_milters = unix:/var/run/opendmarc/opendmarc.sock
milter_default_action = accept
```

### 4. Create the Ignore Hosts File

Create `/etc/opendmarc/ignore.hosts` to skip DMARC checks for trusted sources:

```
127.0.0.1
::1
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

### 5. Restart Services

```bash
sudo systemctl restart opendmarc
sudo systemctl restart postfix
```

OpenDMARC will now check DMARC alignment on all incoming mail and add `Authentication-Results` headers. The history file at `/var/run/opendmarc/opendmarc.dat` can be used with reporting scripts.

## Setting Up Open-DMARC-Analyzer Web Dashboard

For a lightweight web dashboard without Elasticsearch, Open-DMARC-Analyzer provides a PHP-based interface:

```bash
# Clone the repository
git clone https://github.com/userjack6880/Open-DMARC-Analyzer.git
cd Open-DMARC-Analyzer

# Create MySQL database
mysql -u root -p -e "CREATE DATABASE dmarc_analyzer;"
mysql -u root -p dmarc_analyzer < mysql.sql

# Configure the application
cp config.php.pub config.php
# Edit config.php with your database credentials

# Set up Apache/Nginx to serve the directory
# Example Nginx config:
```

```nginx
server {
    listen 80;
    server_name dmarc.example.com;
    root /var/www/dmarc-analyzer;
    index index.php;

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.2-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

You'll also need a parser to feed data into the database. The tool works with `dmarcts-report-parser`:

```bash
# Install the parser
git clone https://github.com/techsneeze/dmarcts-report-parser.git
cd dmarcts-report-parser

# Parse DMARC XML reports and load into the database
./dmarcts-report-parser.pl -c dmarcts-report-parser.conf -p
```

Set up a cron job to run the parser daily:

```bash
# /etc/cron.d/dmarc-parse
0 2 * * * root /opt/dmarcts-report-parser/dmarcts-report-parser.pl -c /opt/dmarcts-report-parser/dmarcts-report-parser.conf -p >> /var/log/dmarc-parser.log 2>&1
```

## Self-Hosted vs SaaS DMARC Tools

| Factor | Self-Hosted | SaaS (Dmarcian, Valimail, EasyDMARC) |
|--------|------------|--------------------------------------|
| **Cost** | Free (server costs only) | $10–$100+/month |
| **Data Privacy** | Full control — data stays on your server | Reports sent to third party |
| **Setup Effort** | Moderate — requires server administration | Minimal — just point DNS records |
| **Customization** | Unlimited — build any dashboard or alert | Limited to provider's features |
| **Scalability** | Depends on your infrastructure | Handles unlimited volume |
| **Maintenance** | You manage updates and backups | Provider handles everything |
| **Support** | Community / self-reliant | Dedicated support team |
| **Compliance** | Meets strict data residency requirements | May not satisfy all compliance needs |

## Choosing the Right Tool

Your choice depends on what you need:

- **Full analysis pipeline** — Use **parsedmarc** with OpenSearch/Kibana. It handles everything from report collection to visualization, supports TLS-RPT, and is the most actively maintained option.
- **Policy enforcement on your mail server** — Use **OpenDMARC** as a Postfix milter. It checks incoming mail against DMARC policy in real time. Combine it with parsedmarc for complete coverage.
- **Lightweight dashboard without Elasticsearch** — Use **Open-DMARC-Analyzer** with MySQL. It's simple, resource-efficient, and works well for small to medium deployments.
- **Complete email security stack** — Combine all three: OpenDMARC for real-time enforcement, parsedmarc for report analysis, and Open-DMARC-Analyzer for quick dashboard access.

For related reading on building a complete self-hosted email infrastructure, see our [Stalwart vs Mailcow vs Mailu comparison](../stalwart-vs-mailcow-vs-mailu/) and our guide to [self-hosted email archiving](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/).

## FAQ

### What is a DMARC report and why do I need to analyze it?

DMARC aggregate reports are XML files sent by receiving mail servers (like Gmail, Yahoo, and Outlook) that detail every email claiming to be from your domain over a 24-hour period. They show which sources passed or failed SPF and DKIM checks, helping you identify unauthorized senders, misconfigured services, and active spoofing attempts. Without analyzing these reports, you can't safely move your DMARC policy from `none` (monitoring) to `quarantine` or `reject` (enforcement).

### Can I use parsedmarc with Gmail as the report mailbox?

Yes. parsedmarc connects to any IMAP server. Create a dedicated Gmail account or label for DMARC reports, set up an app password, and configure parsedmarc's `[mailbox]` section with the Gmail IMAP settings (`imap.gmail.com`, port 993, SSL enabled). Gmail's IMAP access must be enabled in the account settings.

### Do I need both OpenDMARC and parsedmarc?

They serve different purposes. OpenDMARC enforces DMARC policy on **incoming** mail to your server (protecting you from spoofed emails). parsedmarc analyzes DMARC reports **about your domain** sent by other servers (helping you protect your own domain from being spoofed). For comprehensive email security, you want both: OpenDMARC on your mail server and parsedmarc monitoring reports about your domain.

### How often should DMARC reports be parsed?

DMARC aggregate reports are sent daily by most major receivers. Parsing them every 1–4 hours is sufficient. parsedmarc's default watchdog interval of 60 seconds checks for new reports continuously. There's no benefit to parsing more frequently than every few minutes, since reports arrive at most once per day from each source.

### What happens if I set my DMARC policy to "reject" without analyzing reports first?

This is dangerous. Without analyzing reports, you don't know which legitimate services send email on your domain's behalf. Setting `p=reject` without first identifying and authorizing all sending sources (via SPF records and DKIM keys) will cause legitimate email — newsletters, transactional emails, password resets — to be rejected by receiving servers. Always start with `p=none`, analyze reports for 2–4 weeks, authorize all legitimate sources, then gradually move to `p=quarantine` and finally `p=reject`.

### Is OpenSearch required for parsedmarc, or can I use Elasticsearch?

parsedmarc supports both. The official Docker Compose file includes configurations for both Elasticsearch and OpenSearch. OpenSearch is the open-source fork of Elasticsearch (created after Elastic changed licensing), and is recommended for fully self-hosted deployments. Elasticsearch works equally well if you already have it running.

### Can Open-DMARC-Analyzer parse DMARC reports directly?

No. Open-DMARC-Analyzer is a display layer only — it reads from a MySQL or PostgreSQL database that must be populated by a separate parser like `dmarcts-report-parser` or `rrdmarc`. The typical workflow is: receive DMARC reports → parse XML with a CLI tool → load into database → view in Open-DMARC-Analyzer's web UI.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted DMARC Analysis & Email Authentication Guide 2026",
  "description": "Compare self-hosted DMARC report analysis tools — parsedmarc, OpenDMARC, and Open-DMARC-Analyzer. Learn to monitor email authentication, detect spoofing, and enforce DMARC policies without SaaS.",
  "datePublished": "2026-04-21",
  "dateModified": "2026-04-21",
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
