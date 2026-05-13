---
title: "Self-Hosted Mail Statistics Dashboards — Mailgraph vs PFLogSummit vs MailWatch"
date: "2026-05-14"
tags: ["email", "monitoring", "postfix", "statistics", "dashboard"]
draft: false
---

Monitoring email server performance and traffic patterns is essential for maintaining reliable mail infrastructure. Whether you're running Postfix, Sendmail, or another MTA, having visibility into mail volume, delivery rates, and queue sizes helps you identify problems before they impact users.

In this guide, we compare three open-source, self-hosted mail statistics and visualization tools: **Mailgraph**, **PFLogSummit** (with HTML GUI), and **MailWatch**.

## Why Monitor Mail Server Statistics?

Email infrastructure operates silently until something goes wrong. A sudden spike in deferred messages might indicate DNS issues. A drop in incoming mail could signal a blacklist problem. Rising queue sizes often precede delivery failures. Having real-time and historical statistics dashboards lets you spot these trends early and maintain high delivery rates.

For organizations managing their own mail servers — whether for internal communications, transactional email, or newsletter delivery — statistics dashboards are as essential as CPU and memory monitoring.

## Tool Comparison

| Feature | Mailgraph | PFLogSummit (HTML GUI) | MailWatch |
|---------|-----------|------------------------|-----------|
| GitHub Stars | 71+ | 10+ (GUI) | 124+ |
| Language | Perl | Perl/Shell (Bash) | PHP |
| MTA Support | Postfix, Sendmail | Postfix only | Postfix, Sendmail |
| Real-time Graphs | Yes | No | No |
| HTML Reports | No (RRD graphs) | Yes | Yes (Web UI) |
| Spam/Virus Tracking | Limited | No | Yes (with SpamAssassin/ClamAV) |
| Database Backend | RRD files | None (text parsing) | MySQL/MariaDB |
| Docker Support | Community | Community | Official |
| Active Development | Stable | Maintenance | Active |
| License | GPL-2.0 | GPL-2.0 | GPL-3.0 |

## 1. Mailgraph

**Mailgraph** is a classic, lightweight mail statistics tool that reads Postfix or Sendmail syslog output in real-time and generates RRD (Round Robin Database) graphs. It produces simple but effective visualizations of sent, received, bounced, and bounced messages over time.

### Key Features

- **Real-time graphing** — updates every minute with live mail traffic data
- **Multiple MTA support** — works with both Postfix and Sendmail
- **Lightweight** — minimal resource footprint, runs on any server
- **RRD backend** — automatic data rotation, no database administration needed
- **Web integration** — graphs can be served via any web server

### Installation

```bash
# Debian/Ubuntu
apt-get install mailgraph

# The daemon reads syslog and generates RRD files
systemctl enable mailgraph
systemctl start mailgraph

# Graphs are stored in /var/lib/mailgraph/
ls /var/lib/mailgraph/*.rrd
# mailgraph-days.rrd  mailgraph-months.rrd  mailgraph-weeks.rrd  mailgraph-years.rrd
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  mailgraph:
    image: crazymax/mailgraph:latest
    container_name: mailgraph
    volumes:
      - /var/log:/var/log:ro
      - mailgraph-data:/var/lib/mailgraph
      - mailgraph-www:/var/www/html
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: mailgraph-web
    ports:
      - "8080:80"
    volumes:
      - mailgraph-www:/usr/share/nginx/html:ro
    depends_on:
      - mailgraph

volumes:
  mailgraph-data:
  mailgraph-www:
```

### Viewing Graphs

```bash
# Mailgraph generates HTML pages with embedded graphs
# Serve them with any web server:
cp /usr/share/mailgraph/mailgraph.cgi /var/www/cgi-bin/
# Or use the rrdtool command to export graphs:
rrdtool graph /tmp/mail-daily.png   --start -86400   DEF:sent=/var/lib/mailgraph/mailgraph-days.rrd:sent:AVERAGE   LINE2:sent#00AA00:"Sent"
```

### When to Use

Mailgraph is perfect for administrators who want a simple, set-and-forget mail statistics solution. Its real-time graphs are ideal for NOC dashboards and operations centers where live mail traffic visibility is needed.

## 2. PFLogSummit with HTML GUI

**PFLogSummit** is a Perl script that parses Postfix log files and generates summary statistics reports covering delivery status, volume by sender/recipient, top destinations, and more. The community-built HTML GUI wrapper transforms the text report into a browsable web dashboard.

### Key Features

- **Comprehensive statistics** — detailed breakdowns of mail flow patterns
- **On-demand reports** — generate reports for any date range
- **No persistent storage** — parses logs on demand, no database required
- **HTML report generation** — community GUI provides web-friendly output
- **Lightweight** — single script, minimal dependencies

### Installation

```bash
# Install pflogsumm
apt-get install pflogsumm

# Generate a daily report
pflogsumm /var/log/mail.log

# Generate an HTML report for a date range
pflogsumm -d yesterday /var/log/mail.log > /tmp/daily-report.txt

# With HTML GUI wrapper:
cd /opt/PFLogSumm-HTML-GUI
./generate-report.sh /var/log/mail.log
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  pflogsumm:
    image: catatnight/postfix:latest
    container_name: pflogsumm-runner
    volumes:
      - mail-logs:/var/log:ro
      - reports:/opt/reports
    command: >
      sh -c "pflogsumm -d today /var/log/mail.log > /opt/reports/daily-report.html"
    restart: "no"

  web:
    image: nginx:alpine
    container_name: pflogsumm-web
    ports:
      - "8081:80"
    volumes:
      - reports:/usr/share/nginx/html:ro

volumes:
  mail-logs:
  reports:
```

### Scheduled Report Generation

```bash
# Add to crontab for daily reports at midnight
0 0 * * * pflogsumm -d yesterday /var/log/mail.log |   mail -s "Daily Mail Statistics" admin@example.com

# Or generate HTML and serve via web:
0 0 * * * /opt/PFLogSumm-HTML-GUI/generate-report.sh   /var/log/mail.log /var/www/html/daily-report.html
```

### When to Use

PFLogSummit is ideal for administrators who need detailed, periodic mail statistics without the overhead of a real-time monitoring system. Its on-demand nature makes it perfect for weekly or monthly capacity planning reports.

## 3. MailWatch

**MailWatch** (MailWatch for MailScanner) is a comprehensive web-based front-end that provides detailed mail server statistics, spam and virus tracking, message tracking, and quarantine management. While originally designed as a MailScanner companion, it works with any Postfix or Sendmail setup.

### Key Features

- **Full web interface** — browser-based dashboard with filtering and search
- **Message tracking** — search for individual messages by sender, recipient, or ID
- **Spam/virus statistics** — track SpamAssassin scores and ClamAV detections
- **Quarantine management** — view and release quarantined messages
- **User management** — multi-user access with per-domain views
- **MySQL backend** — persistent storage for historical analysis

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  mailwatch-db:
    image: mariadb:10.11
    container_name: mailwatch-db
    environment:
      - MYSQL_ROOT_PASSWORD=mailwatch-db-pass
      - MYSQL_DATABASE=mailwatch
      - MYSQL_USER=mailwatch
      - MYSQL_PASSWORD=mailwatch-pass
    volumes:
      - mailwatch-db:/var/lib/mysql
    restart: unless-stopped

  mailwatch:
    image: mailwatch/mailwatch:latest
    container_name: mailwatch
    ports:
      - "8080:80"
    environment:
      - DB_HOST=mailwatch-db
      - DB_NAME=mailwatch
      - DB_USER=mailwatch
      - DB_PASSWORD=mailwatch-pass
      - MAILLOG=/var/log/mail.log
    volumes:
      - /var/log:/var/log:ro
    depends_on:
      - mailwatch-db
    restart: unless-stopped

volumes:
  mailwatch-db:
```

### Postfix Integration

```bash
# Configure Postfix to log to MailWatch database
# In main.cf, add a milter or use the mailwatch postfix logger:
postconf -e 'always_bcc = mailarchive@example.com'

# Or configure the MailWatch postfix logger to read maillog:
# /etc/mailwatch/conf.php
define('MAIL_LOG', '/var/log/mail.log');
```

### When to Use

MailWatch is the most feature-rich option, suitable for organizations that need comprehensive mail server monitoring with spam/virus tracking, message search, and quarantine management. It's particularly valuable for environments running SpamAssassin or ClamAV alongside their MTA.

## Setting Up Your Mail Statistics Pipeline

```
Postfix/Sendmail Logs → Log Parser → Statistics Engine → Dashboard/Reports
        ↓                    ↓              ↓              ↓
    /var/log/mail.log   Mailgraph      RRD Graphs     Real-time Web
                      PFLogSummit    Text Reports     On-demand HTML
                      MailWatch      MySQL Database   Full Web UI
```

### Recommended Log Rotation

```bash
# Ensure mail logs are properly rotated for historical analysis
cat /etc/logrotate.d/rsyslog-postfix
/var/log/mail.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
```

For related reading, see our [Postfix mail queue management guide](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsu/) for monitoring mail queues, our [MTA-STS email security guide](../2026-04-28-self-hosted-mta-sts-smtp-dane-email-security-guide-2026/) for transport security, and our [greylisting servers comparison](../2026-05-10-self-hosted-greylisting-servers-postgrey-sqlgrey-rspamd-gui/) for spam reduction techniques.

## FAQ

### What is the difference between Mailgraph and PFLogSummit?

Mailgraph provides real-time, continuously updating graphs of mail traffic (sent, received, bounced) using RRD databases. PFLogSummit generates on-demand summary reports by parsing log files, providing more detailed statistics but without real-time visualization.

### Can I use these tools with Exchange or Office 365?

No. These tools are designed for Unix-based mail servers (Postfix, Sendmail) that write to syslog files. For Exchange or Office 365, you would need Microsoft's built-in message trace tools or third-party SaaS solutions.

### How much disk space do these tools require?

Mailgraph uses RRD files which have a fixed size (typically a few MB). PFLogSummit requires no persistent storage. MailWatch needs a MySQL database, typically 100MB-1GB depending on mail volume and retention period.

### Do these tools track individual email messages?

MailWatch can track individual messages through its web interface. Mailgraph and PFLogSummit provide aggregate statistics only — you can see totals and trends but not look up specific messages.

### Can I monitor multiple mail servers with one dashboard?

MailWatch supports multi-server setups by aggregating logs from multiple sources. Mailgraph and PFLogSummit are designed for single-server monitoring, though you can run separate instances for each server.

### How historical can the data go?

Mailgraph's RRD files typically store days, weeks, months, and years of data at decreasing resolution. PFLogSummit can analyze any archived log file. MailWatch retention depends on your database cleanup configuration.

## Choosing the Right Mail Statistics Tool

- **For real-time visibility**: Mailgraph provides live-updating graphs perfect for NOC dashboards.
- **For periodic detailed reports**: PFLogSummit generates comprehensive statistics without persistent storage overhead.
- **For full-featured monitoring**: MailWatch offers the most complete solution with spam tracking, message search, and quarantine management.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Statistics Dashboards — Mailgraph vs PFLogSummit vs MailWatch",
  "description": "Compare open-source mail statistics and monitoring tools — Mailgraph for real-time graphs, PFLogSummit for detailed reports, and MailWatch for comprehensive web-based dashboards.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
