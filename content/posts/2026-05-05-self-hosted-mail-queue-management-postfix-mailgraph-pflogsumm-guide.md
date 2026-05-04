---
title: "Self-Hosted Mail Queue Management — Postfix Queue, Mailgraph, pflogsumm Guide"
date: 2026-05-05
tags: ["email", "postfix", "queue", "monitoring", "self-hosted", "mta"]
draft: false
---

Managing an email server means managing queues — the holding areas where messages wait for delivery, retry, or bounce. When queues grow unexpectedly, emails get delayed, users complain, and deliverability suffers. Self-hosted mail queue management tools help you monitor, analyze, and troubleshoot these queues before they become critical.

This guide covers three essential tools for self-hosted mail queue management: **Postfix queue tools** (postqueue, postsuper, qshape), **Mailgraph** (real-time queue visualization), and **pflogsumm** (Postfix log summary and reporting).

## Understanding Mail Queues

Every Mail Transfer Agent (MTA) uses queues to manage email flow:

- **Incoming/hold queue**: Messages received but not yet processed
- **Active queue**: Messages currently being delivered
- **Deferred queue**: Messages that failed delivery and will be retried
- **Bounce queue**: Messages that permanently failed and need to bounce back to sender

The deferred queue is where most problems manifest — a growing deferred queue usually means DNS issues, recipient server problems, or configuration errors.

## Postfix Queue Management Tools

Postfix includes built-in queue management utilities that provide the foundation for any mail server administration.

### Viewing Queue Status

```bash
# List all queued messages
postqueue -p

# Show queue summary (count by status)
mailq | tail -1

# Count deferred messages
postqueue -p | grep -c "^[A-F0-9]"

# View detailed queue stats
postconf -h queue_directory
ls -la /var/spool/postfix/deferred/ | wc -l
```

### Managing Queue Messages

```bash
# Flush the entire queue (retry all deferred messages)
postqueue -f

# Flush a specific message
postqueue -i <queue_id>

# Delete a specific message from queue
postsuper -d <queue_id>

# Delete ALL deferred messages (use with caution!)
postsuper -d ALL deferred

# Re-queue a message (move from hold to active)
postsuper -r <queue_id>

# Hold a message for manual review
postsuper -h <queue_id>
```

### Qshape — Queue Age Analysis

Qshape is a Postfix utility that shows queue depth by domain and age:

```bash
# Show deferred queue by domain (top 20)
qshape deferred | head -25

# Show active queue
qshape active

# Show deferred queue with age breakdown
qshape -s 15 deferred
```

The qshape output shows how many messages are queued per destination domain, grouped by age (T, 5, 10, 20, 40, 80, 160+ minutes). A healthy queue has most messages in the T (total) column with minimal entries in older age buckets.

### Docker Compose Setup for Postfix with Queue Monitoring

```yaml
# docker-compose.yml for Postfix with queue monitoring sidecar
version: "3.8"
services:
  postfix:
    image: ghcr.io/bokysan/docker-postfix:latest
    container_name: postfix
    ports:
      - "25:25"
      - "587:587"
    environment:
      - ALLOWED_SENDER_DOMAINS=example.com
      - RELAYHOST=smtp.relay.example.com
      - TZ=UTC
    volumes:
      - postfix-data:/var/spool/postfix
      - ./postfix-override:/etc/postfix-override
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postfix-data:
```

## Mailgraph — Real-Time Queue Visualization

Mailgraph provides a web-based visualization of your mail server's traffic, showing messages sent, received, bounced, and deferred over time.

### Installing Mailgraph

```bash
# On Debian/Ubuntu
sudo apt-get install -y mailgraph

# The daemon reads the Postfix log and generates RRD graphs
sudo systemctl enable mailgraph
sudo systemctl start mailgraph

# Access the web interface
# http://your-server/cgi-bin/mailgraph.cgi
```

### Interpreting Mailgraph Output

Mailgraph generates several RRD-based graphs:
- **Sent/Received**: Total message count over time (hourly, daily, weekly)
- **Bounced**: Messages that permanently failed delivery
- **Deferred**: Messages temporarily held for retry
- **Virus/Spam**: If integrated with amavis or rspamd

A sudden spike in the deferred graph typically indicates DNS resolution failures, recipient server rejecting connections, rate limiting by destination servers, or network connectivity issues.

## pflogsumm — Postfix Log Summary Reports

pflogsumm parses Postfix log files and generates summary reports showing message volume, delivery status, top senders/recipients, and queue statistics.

### Generating Reports

```bash
# Generate today's summary
pflogsumm /var/log/mail.log

# Generate yesterday's report
pflogsumm -d yesterday /var/log/mail.log

# Generate weekly report via cron
pflogsumm -d 7 /var/log/mail.log

# HTML output for web dashboards
pflogsumm -h /var/log/mail.log > /var/www/mail-report.html
```

### Automated pflogsumm via Cron

```bash
# Add to crontab for daily email reports
0 8 * * * pflogsumm -d yesterday /var/log/mail.log \
  | mail -s "Mail Server Daily Report" admin@example.com
```

## Comparison: Mail Queue Management Tools

| Feature | Postqueue/Postsuper | Mailgraph | pflogsumm |
|---------|-------------------|-----------|-----------|
| **Type** | CLI commands | Web visualization | Log parser/report |
| **Real-time** | Yes (live queue) | Yes (RRD graphs) | No (historical) |
| **Queue management** | Full CRUD | Read-only | Read-only |
| **Visualization** | Text table | RRD graphs | Text/HTML report |
| **Alerting** | Manual | No (visual only) | Via cron + email |
| **Resource usage** | Minimal | Low | Very low (batch) |
| **Best for** | Admin troubleshooting | Ops dashboard | Daily reporting |

## Queue Troubleshooting Workflow

When your mail queue grows unexpectedly, follow this diagnostic workflow:

```bash
# Step 1: Check queue size
postqueue -p | tail -1

# Step 2: Identify problem domains
qshape deferred | head -20

# Step 3: Check recent delivery failures
tail -100 /var/log/mail.log | grep "status=deferred"

# Step 4: Test DNS resolution for problematic domains
dig MX problem-domain.com
dig problem-domain.com MX +short

# Step 5: Check if the remote server is reachable
telnet mx.problem-domain.com 25

# Step 6: Review Postfix configuration
postconf -n | grep -E "relay|smtp|bounce"
```

For managing mail server administration at scale, see our [Postfix vs Exim MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide-2026/) and [complete email server setup guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/). For log analysis beyond queue monitoring, our [mail log analytics guide](../2026-04-26-mailwatch-vs-pflogsumm-vs-mailgraph-self-hosted-mail-log-an/) covers additional tools.

## Why Monitor Mail Queues?

Mail queue monitoring is essential for any production email server. **Early problem detection** lets you identify delivery issues before users notice — a growing deferred queue is often the first sign of DNS problems, IP reputation issues, or remote server outages.

**Deliverability optimization** requires understanding your queue patterns. If certain domains consistently defer, you may need to adjust your sending patterns, implement proper SPF/DKIM/DMARC records, or consider a relay service.

**Capacity planning** becomes data-driven when you track queue metrics over time. pflogsumm reports show traffic trends that help you size your server correctly and plan for peak periods.

Combined with [spam filtering solutions](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/) and proper [SMTP relay configuration](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2026/), queue management completes your email infrastructure toolkit.

## FAQ

### What is a deferred mail queue?
The deferred queue holds messages that temporarily failed delivery and will be retried later. Postfix uses exponential backoff — first retry after approximately 1000 seconds, then progressively longer intervals. Messages stay in the deferred queue until they succeed or reach the maximum retry time (default: 5 days).

### How do I clear a stuck mail queue?
Use `postsuper -d ALL deferred` to delete all deferred messages. For targeted cleanup, use `postqueue -p` to list messages, then `postsuper -d <id>` to delete specific ones. Be cautious — this permanently removes messages without notifying senders.

### Why is my Postfix queue growing?
Common causes include: DNS resolution failures for recipient domains, remote servers rate-limiting your IP, network connectivity issues, incorrect MX records, or your server IP being on a spam blocklist. Use `qshape deferred` to identify which domains are affected.

### What is the difference between postqueue and mailq?
`mailq` is a compatibility wrapper around `postqueue -p`. They produce identical output. `postqueue` also supports additional operations like `-f` (flush queue), `-i` (flush specific message), and interactive mode.

### How often should I check my mail queue?
For production mail servers, check queue status at least every 15 minutes via monitoring tools. Set up alerts when the deferred queue exceeds a threshold (e.g., 500 messages). For smaller servers, hourly checks via cron are usually sufficient.

### Can Mailgraph monitor multiple Postfix servers?
Mailgraph is designed for single-server monitoring. For multi-server setups, consider centralized solutions like ELK Stack, Grafana Loki, or Grafana with the Postfix exporter for Prometheus.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Queue Management — Postfix Queue, Mailgraph, pflogsumm Guide",
  "description": "Learn to manage self-hosted mail queues with Postfix tools, Mailgraph visualization, and pflogsumm reporting. Includes Docker configs and troubleshooting workflows.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
