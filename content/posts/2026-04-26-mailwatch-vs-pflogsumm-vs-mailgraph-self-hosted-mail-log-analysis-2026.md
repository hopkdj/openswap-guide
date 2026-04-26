---
title: "MailWatch vs PFLogSumm vs Mailgraph: Self-Hosted Mail Log Analysis Tools 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "email", "monitoring"]
draft: false
description: "Compare self-hosted mail log analysis tools — MailWatch, PFLogSumm, and Mailgraph — for monitoring Postfix queues, visualizing mail traffic, and tracking SMTP delivery performance."
---

Running a self-hosted mail server means you're responsible for monitoring delivery health, tracking queue backlogs, and diagnosing bounce issues. Without proper log analysis tools, you're flying blind — unable to see if spam is overwhelming your server, if queues are stuck, or if delivery rates are dropping.

In this guide, we compare three self-hosted mail log analysis tools: **MailWatch**, **PFLogSumm**, and **Mailgraph**. Each takes a different approach to post-processing Postfix (and compatible MTA) logs, giving you visibility into your email infrastructure.

## Why Self-Hosted Mail Log Analysis Matters

When you manage your own mail server, you lose the built-in dashboards that SaaS email providers offer. Tools like MailWatch, PFLogSumm, and Mailgraph fill that gap by parsing `/var/log/mail.log` (or equivalent) and presenting actionable metrics:

- **Queue depth** — detect stuck messages before they bounce
- **Delivery rates** — track successful sends vs. deferrals vs. rejections
- **Spam/virus detection** — monitor how much junk your filters are catching
- **Volume trends** — spot unusual spikes that indicate abuse or attacks
- **Top senders/recipients** — identify who's generating the most traffic

For related reading, see our guide on [Postfix/Rspamd spam filtering setup](../spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide/) and the [complete email deliverability guide](../self-hosted-email-deliverability-inbox-placement-guide-2026/).

## MailWatch: Full Web-Based Mail Monitoring

[MailWatch](https://github.com/mailwatch/mailwatch) is a comprehensive web-based mail log analyzer designed for Postfix and MailScanner setups. It stores parsed log data in a MySQL/MariaDB database and provides a full web interface for real-time monitoring, reporting, and quarantine management.

### Key Features

- Real-time mail log parsing into a relational database
- Web dashboard with graphs, tables, and drill-down reports
- Quarantine management for spam/virus-flagged messages
- Per-user mail tracking and reporting
- Mail queue monitoring with action buttons (release, delete, defer)
- Multi-server support for monitoring multiple Postfix instances
- User/role management for team environments

### Docker Compose Setup

MailWatch can be deployed using Docker Compose with MariaDB as the backend:

```yaml
version: '3.8'
services:
  mailwatch-db:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: mailwatch_root_pass
      MYSQL_DATABASE: mailwatch
      MYSQL_USER: mailwatch
      MYSQL_PASSWORD: mailwatch_db_pass
    volumes:
      - mailwatch-db-data:/var/lib/mysql
    restart: unless-stopped
    networks:
      - mailwatch-net

  mailwatch-web:
    image: mailwatch/mailwatch:latest
    environment:
      DB_HOST: mailwatch-db
      DB_NAME: mailwatch
      DB_USER: mailwatch
      DB_PASS: mailwatch_db_pass
    ports:
      - "8080:80"
    volumes:
      - /var/log/mail.log:/var/log/mail.log:ro
      - mailwatch-config:/opt/mailwatch/conf
    depends_on:
      - mailwatch-db
    restart: unless-stopped
    networks:
      - mailwatch-net

networks:
  mailwatch-net:
    driver: bridge

volumes:
  mailwatch-db-data:
  mailwatch-config:
```

### Installation on Linux

For a bare-metal install on Debian/Ubuntu:

```bash
# Install dependencies
sudo apt install apache2 libapache2-mod-php php-mysql php-gd php-mbstring mariadb-server

# Clone MailWatch
cd /opt
sudo git clone https://github.com/mailwatch/mailwatch.git
cd mailwatch

# Create database
sudo mysql -u root -p
CREATE DATABASE mailwatch;
GRANT ALL ON mailwatch.* TO 'mailwatch'@'localhost' IDENTIFIED BY 'your_password';
FLUSH PRIVILEGES;
EXIT;

# Import schema and configure
sudo cp conf.php.example conf.php
# Edit conf.php with your database credentials
sudo php install.php

# Configure Postfix to pipe logs to MailWatch
# Add to /etc/postfix/master.cf:
#   mailwatch unix - n n - - pipe
#     flags=R user=mailwatch argv=/opt/mailwatch/tools/MailWatch/pmilter.pl

# Start the log parser
sudo /opt/mailwatch/tools/Cron_jobs/mailwatch_importer.php
```

## PFLogSumm: Command-Line Postfix Log Summarizer

[PFLogSumm](https://github.com/jkerpeters/pflogsumm) is a Perl-based log summary tool specifically designed for Postfix. It parses Postfix log files and generates concise, readable summary reports — perfect for cron-jobs that email you daily or weekly stats.

### Key Features

- Generates human-readable summary reports from Postfix logs
- Tracks deliveries, deferrals, bounces, and rejections
- Identifies top senders, recipients, and destination domains
- Calculates hourly/daily mail volume distribution
- Reports on SMTP response codes and common error patterns
- Lightweight — no database, no web server required
- Designed for automated cron execution with email delivery

### Docker Usage

While PFLogSumm is a CLI tool, you can run it in a container for isolated execution:

```yaml
version: '3.8'
services:
  pflogsumm:
    image: alpine:latest
    volumes:
      - /var/log/mail.log:/var/log/mail.log:ro
      - ./pflogsumm-report:/tmp/report
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache perl pflogsumm
      pflogsumm -d today /var/log/mail.log > /tmp/report/pflogsumm-report.txt
    restart: "no"
```

### Installation and Daily Report Setup

```bash
# Install on Debian/Ubuntu
sudo apt install pflogsumm

# Generate a report for today
sudo pflogsumm -d today /var/log/mail.log

# Generate a report for yesterday
sudo pflogsumm -d yesterday /var/log/mail.log

# Generate with detailed host statistics
sudo pflogsumm -d today --extreme_detail /var/log/mail.log | head -80

# Set up a daily cron report via email
# Create /etc/cron.daily/pflogsumm-report:
#!/bin/bash
pflogsumm -d yesterday /var/log/mail.log | \
  mail -s "Postfix Summary for $(date -d yesterday +%Y-%m-%d)" admin@yourdomain.com

sudo chmod +x /etc/cron.daily/pflogsumm-report
```

### Sample Output

```
Postfix Logs Summary (pflogsumm 1.1.6)
========================================
Grand Totals
------------
messages
    1452 received
    1438 delivered
       0 forwarded
      14 deferred (deferral)
      14 bounced
       6 rejected (0.4%)
       1 reject warnings
       0 hold
       0 discarded

Per-Hour Traffic Summary
    Time  Received  Delivered  Deferred  Bounced  Rejected
    0000        22         22         0        0         0
    0100        15         15         0        0         0
    ...
    1400       142        140         2        0         0
```

## Mailgraph: Visual Mail Traffic Graphing

[Mailgraph](https://github.com/msimerson/mailgraph) is a simple but effective RRDtool-based mail statistics visualizer. It creates real-time graphs of sent, received, bounced, and rejected mail volumes using data from the system mail log. While it lacks the depth of MailWatch or the report detail of PFLogSumm, it excels at providing an at-a-glance view of mail traffic patterns.

### Key Features

- Real-time RRDtool-based graphs of mail activity
- Tracks sent, received, bounced, rejected, and virus-tagged messages
- Supports Postfix, Sendmail, Exim, and Qmail log formats
- Extremely lightweight — minimal CPU and memory footprint
- CGI-based web interface for graph display
- Historical data retention (daily, weekly, monthly, yearly views)
- No database required — RRDtool handles time-series storage

### Docker Compose Setup

```yaml
version: '3.8'
services:
  mailgraph:
    image: alpine:latest
    volumes:
      - /var/log/mail.log:/var/log/mail.log:ro
      - mailgraph-rrd:/var/lib/mailgraph
    ports:
      - "8081:80"
    environment:
      - LOGFILE=/var/log/mail.log
      - RRD_DIR=/var/lib/mailgraph
    entrypoint: ["/bin/sh", "-c"]
    command: |
      apk add --no-cache rrdtool mailgraph apache2
      mkdir -p /var/lib/mailgraph
      mailgraph -l /var/log/mail.log -d
      mkdir -p /var/www/localhost/htdocs
      ln -s /usr/share/mailgraph/mailgraph.cgi /var/www/localhost/htdocs/
      httpd -f -h /var/www/localhost/htdocs
    restart: unless-stopped

volumes:
  mailgraph-rrd:
```

### Bare-Metal Installation

```bash
# Install on Debian/Ubuntu
sudo apt install mailgraph rrdtool

# Start the daemon (monitors /var/log/mail.log)
sudo systemctl enable mailgraph
sudo systemctl start mailgraph

# Access graphs at:
# http://your-server/cgi-bin/mailgraph.cgi

# The CGI script is typically at /usr/lib/cgi-bin/mailgraph.cgi
# You may need to enable CGI in your web server
```

### Apache Configuration for Mailgraph CGI

```apache
<VirtualHost *:80>
    ServerName mailgraph.yourdomain.com
    DocumentRoot /var/www/mailgraph

    ScriptAlias /cgi-bin/ /usr/lib/cgi-bin/
    <Directory "/usr/lib/cgi-bin">
        AllowOverride None
        Options +ExecCGI -MultiViews +SymLinksIfOwnerMatch
        Require all granted
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/mailgraph-error.log
    CustomLog ${APACHE_LOG_DIR}/mailgraph-access.log combined
</VirtualHost>
```

## Comparison Table

| Feature | MailWatch | PFLogSumm | Mailgraph |
|---------|-----------|-----------|-----------|
| **Interface** | Web (PHP/MySQL) | CLI (Perl) | Web (CGI/RRDtool) |
| **Real-time** | Yes (near-real-time parsing) | No (scheduled reports) | Yes (live RRD updates) |
| **Database** | MySQL/MariaDB required | None required | RRDtool time-series |
| **Queue management** | Full (release/delete/defer) | No | No |
| **Quarantine** | Yes (spam/virus) | No | No |
| **Per-user stats** | Yes | Yes (in reports) | No |
| **Historical trends** | Database-backed | Log-file dependent | RRDtool (daily/weekly/monthly/yearly) |
| **Multi-server** | Yes | No | No |
| **Resource usage** | Moderate (DB + web) | Minimal (CLI only) | Very low (RRDtool) |
| **Setup complexity** | High | Low | Low-Medium |
| **Best for** | Full mail server monitoring | Automated daily/weekly reports | Quick visual traffic overview |
| **GitHub stars** | 500+ | Community maintained | 100+ |
| **Last active** | 2025 | Mature/stable | Mature/stable |

## Choosing the Right Tool

### Use MailWatch if:
- You need a comprehensive, web-based mail monitoring solution
- You manage a high-volume mail server and need per-user tracking
- You want quarantine management integrated with log analysis
- Multiple team members need access to mail statistics
- You need real-time queue monitoring with action capabilities

### Use PFLogSumm if:
- You want simple, automated daily or weekly summary reports via email
- You prefer CLI tools without database dependencies
- You need to integrate mail stats into existing monitoring pipelines
- You want detailed breakdown of SMTP response codes and error patterns
- Your infrastructure is minimal and you don't need a web interface

### Use Mailgraph if:
- You want a quick visual overview of mail traffic patterns
- You need historical trend graphs (daily, weekly, monthly)
- You prefer a lightweight solution with minimal resource usage
- You run multiple MTAs (Postfix, Sendmail, Exim) and want unified graphs
- You want something that "just works" with near-zero configuration

### Best Combination

Many administrators use **PFLogSumm + Mailgraph** together: PFLogSumm sends you detailed daily email reports, while Mailgraph provides a always-on dashboard for quick visual checks. For production environments requiring full queue management and per-user tracking, **MailWatch** is the most comprehensive option.

## FAQ

### Can MailWatch work with MTAs other than Postfix?
MailWatch is primarily designed for Postfix and MailScanner setups. While it can parse some Sendmail log formats, full functionality requires Postfix. For Exim or other MTAs, consider Mailgraph which supports multiple MTA log formats.

### Does PFLogSumm support real-time monitoring?
No, PFLogSumm is designed for batch processing of log files. It generates summary reports from completed log entries. For real-time monitoring, use MailWatch or Mailgraph, which parse logs continuously.

### How much disk space does Mailgraph's RRDtool storage use?
RRDtool uses fixed-size circular buffers, so disk usage is predictable and bounded. A typical Mailgraph installation uses 2-5 MB of disk space regardless of how long it runs, since old data is automatically overwritten according to the RRD archive configuration.

### Can I run these tools alongside a mail server on the same machine?
Yes, all three tools are designed to run on the same server as your MTA. Mailgraph and PFLogSumm are particularly lightweight. MailWatch requires a MySQL/MariaDB instance, which adds more resource overhead but is still feasible on a 1-2 GB RAM server.

### How do I set up automated alerts for mail queue problems?
PFLogSumm can be combined with a wrapper script that checks for elevated bounce or defer rates and sends alerts. MailWatch includes built-in queue monitoring — you can set thresholds for queue depth and receive notifications. Mailgraph doesn't include alerting but can be paired with external monitoring tools like Nagios or Prometheus.

### Are these tools compatible with Rspamd or SpamAssassin integration?
MailWatch can display spam/virus detection statistics if your MTA is configured with SpamAssassin or Rspamd. PFLogSumm includes spam-related counters in its reports when the MTA logs tag messages. For comprehensive spam filtering management, see our [Rspamd vs SpamAssassin comparison](../spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MailWatch vs PFLogSumm vs Mailgraph: Self-Hosted Mail Log Analysis Tools 2026",
  "description": "Compare self-hosted mail log analysis tools — MailWatch, PFLogSumm, and Mailgraph — for monitoring Postfix queues, visualizing mail traffic, and tracking SMTP delivery performance.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
