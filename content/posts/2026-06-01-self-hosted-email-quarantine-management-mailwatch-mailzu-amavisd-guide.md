---
title: "Self-Hosted Email Quarantine Management: MailWatch vs MailZu vs amavisd-new Quarantine Release (2026)"
date: "2026-06-01"
tags: ["email", "spam-filtering", "self-hosted", "mail-server", "quarantine", "amavis", "mailwatch", "anti-spam", "security"]
draft: false
---

## Introduction

Email quarantine is the unsung hero of self-hosted mail infrastructure. When your spam filter correctly identifies a malicious message, that message doesn't disappear — it goes into quarantine, where it waits for administrative review. Without a proper quarantine management interface, your users are left wondering where their missing emails went, and administrators must manually sift through raw quarantine databases or log files to release false positives. **MailWatch**, **MailZu**, and **amavisd-new's built-in quarantine release** represent three approaches to solving this problem, from the full-featured MailWatch dashboard to the lightweight MailZu interface to amavisd's native SQL quarantine tools.

This article compares these three self-hosted email quarantine management solutions to help you choose the right interface for your mail infrastructure.

## Why Self-Host Email Quarantine Management?

Managing your own email quarantine keeps **sensitive email content within your infrastructure**. When a quarantined message contains confidential business information, you don't want it stored on or accessible through a third-party cloud service. Self-hosted quarantine management gives you full control over retention policies, access permissions, and audit logging. Second, **domain-level control**: you can configure different quarantine policies for different domains, set per-user release permissions, and integrate quarantine management with your existing authentication system (LDAP, Active Directory, or IMAP). Third, **operational visibility**: a dedicated quarantine dashboard shows you trends — which senders are frequently blocked, whether your spam thresholds are too aggressive, and whether legitimate mail is being silently lost. For the underlying spam filtering infrastructure, see our [SpamAssassin vs Rspamd vs Amavis comparison](../2026-04-26-spamassassin-vs-rspamd-vs-amavis-self-hosted-spam-filtering-guide-2026/). For monitoring your mail server health, check our [mail server monitoring guide](../2026-05-26-self-hosted-mail-server-health-monitoring-postfix-exporter-swaks-mailu-guide/). If you're evaluating POP3 mail delivery options alongside quarantine management, our [POP3 server comparison](../2026-05-25-self-hosted-pop3-email-servers-dovecot-courier-cyrus-guide/) covers the delivery side.

## Tool Comparison

| Feature | MailWatch | MailZu | amavisd-new Quarantine |
|---------|-----------|--------|------------------------|
| **Target MTA** | MailScanner | amavisd-new | amavisd-new |
| **Interface** | Web dashboard (PHP) | Web UI (PHP) | CLI + SQL queries |
| **User Self-Service** | Yes | Yes | No (admin only) |
| **Multi-Domain** | Yes | Yes | N/A |
| **Release Workflow** | Approve/deny with notes | Simple release/delete | Manual SQL operations |
| **Reporting & Graphs** | Comprehensive | Minimal | None |
| **Authentication** | LDAP/IMAP/Internal | LDAP/IMAP/SQL | System-level only |
| **Active Development** | Yes (2026) | Stale (2014 fork) | Yes (amavisd-new) |
| **Docker Support** | Community images | Community images | Part of amavis images |
| **GitHub Stars** | 124 | 4 | N/A (bundled with amavis) |

## MailWatch for MailScanner

[MailWatch](https://github.com/mailwatch/MailWatch) is the most mature and actively developed quarantine management solution, designed as a web frontend for **MailScanner** — a comprehensive email security system that handles spam detection, virus scanning, and policy enforcement. MailWatch provides a rich PHP-based dashboard with multi-domain support, user self-service quarantine access, message release workflows with approval notes, and comprehensive reporting.

```yaml
# docker-compose.yml for MailWatch
version: "3.8"
services:
  mailwatch:
    image: mailwatch/mailwatch:latest
    container_name: mailwatch
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./mailwatch/data:/var/www/html
      - ./mailwatch/quarantine:/var/spool/MailScanner/quarantine
    environment:
      - DB_HOST=mailwatch-db
      - DB_NAME=mailscanner
      - DB_USER=mailwatch
      - DB_PASS=securepassword
      - MAILWATCH_HOME=/var/www/html
    depends_on:
      - mailwatch-db
  mailwatch-db:
    image: mariadb:10.6
    container_name: mailwatch-db
    restart: unless-stopped
    volumes:
      - ./mailwatch/db:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=mailscanner
      - MYSQL_USER=mailwatch
      - MYSQL_PASSWORD=securepassword
```

MailWatch's standout feature is its **quarantine release workflow**: users can browse their quarantined messages, preview content, request release, and administrators can approve with comments. The reporting module tracks spam/virus hit rates, top senders, and quarantine volume over time. Authentication integrates with LDAP, IMAP, or its internal user database.

## MailZu for amavisd-new

[MailZu](https://sourceforge.net/projects/mailzu/) is a simpler PHP-based web interface designed specifically for **amavisd-new's** SQL quarantine. Unlike MailWatch, which is a full MailScanner frontend, MailZu focuses narrowly on quarantine viewing and release. It supports multi-domain configurations, per-user quarantine views, and basic release/delete operations.

```yaml
# docker-compose.yml for MailZu with amavis
version: "3.8"
services:
  mailzu:
    image: robertdebock/mailzu:latest
    container_name: mailzu
    restart: unless-stopped
    ports:
      - "8081:80"
    volumes:
      - ./mailzu/config:/var/www/html/mailzu/config
    environment:
      - DB_HOST=amavis-db
      - DB_NAME=amavis
      - DB_USER=amavis
      - DB_PASS=amavispassword
      - MAILZU_ADMIN=admin@example.com
    depends_on:
      - amavis-db
  amavis-db:
    image: mariadb:10.6
    container_name: amavis-db
    restart: unless-stopped
    volumes:
      - ./amavis/db:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=amavis
      - MYSQL_USER=amavis
      - MYSQL_PASSWORD=amavispassword
```

MailZu's main advantage over amavisd-new's native quarantine is **user self-service**: end users can log in and view/release their own quarantined messages without administrator intervention. However, MailZu's development has largely stalled — the primary fork on GitHub shows no updates since 2014. It works reliably with current amavisd-new versions but lacks modern features like responsive design or REST API endpoints.

## amavisd-new Native Quarantine Release

[amavisd-new](https://gitlab.com/amavis/amavis) includes a built-in quarantine mechanism that stores blocked messages in an SQL database or on the filesystem. The native approach does not provide a web interface — administrators interact with quarantined messages through SQL queries, the `amavisd-release` command-line tool, or custom scripts.

```sql
-- View quarantined messages for a recipient
SELECT mail_id, secret_id, sender, subject, time_num
FROM quarantine
WHERE mail_text LIKE '%recipient@example.com%'
ORDER BY time_num DESC LIMIT 20;

-- Release a specific quarantined message
CALL amavis.release('mail_id_value', 'secret_id_value');
```

```bash
# Release a quarantined message via CLI
amavisd-release mail_id=abc123 secret_id=def456
```

This approach is **administrator-only** — there is no user self-service, no web dashboard, and no visual reporting. However, it requires zero additional software beyond amavisd-new itself, making it the simplest option for small setups where only the system administrator needs quarantine access. For environments with multiple users or domains, the lack of a web interface becomes a significant operational bottleneck.

## Choosing the Right Approach

The right choice depends on your email security stack and user needs:

- **MailScanner users**: MailWatch is the natural choice — it's purpose-built for MailScanner and provides the richest feature set with active development support.
- **amavisd-new users with multiple users**: MailZu provides the user self-service interface that amavisd-new lacks, though its stale development status means you should test compatibility with your amavisd-new version.
- **Single-admin setups**: amavisd-new's native quarantine release is sufficient — no additional web interface needed, just SQL queries and the `amavisd-release` CLI tool.
- **Modern alternatives**: If you're setting up new infrastructure, consider all-in-one mail solutions like Mailcow or Mailu, which bundle spam filtering and quarantine management into integrated web dashboards.

## FAQ

### What's the difference between quarantine and spam folders?

A **spam folder** is a per-user mailbox folder where suspected spam is delivered with modified headers (e.g., `X-Spam-Flag: YES`). Users can browse it like any other folder in their email client. A **quarantine** is a separate storage system outside the user's mailbox — messages are held in a database or filesystem and require explicit release to be delivered. Quarantine is more secure (no accidental clicks on malicious content) but requires a management interface for legitimate message release.

### Can I automate quarantine cleanup?

Yes. Both amavisd-new and MailScanner support automated quarantine expiration. In amavisd-new, set `$QUARANTINEDAYS = 7;` to auto-delete messages older than 7 days. MailScanner has a similar `Quarantine Whole Message = yes` and retention settings. MailWatch includes a cron-based cleanup script (`mailwatch_quarantine_cleanup.php`) that can remove old entries from both the quarantine and the database. Automating cleanup prevents storage bloat and reduces the review burden.

### Do I need a separate database for quarantine?

For production deployments, yes. Both amavisd-new and MailScanner can store quarantine metadata in MySQL/MariaDB or PostgreSQL. The database stores message IDs, sender/recipient addresses, subjects, spam scores, and virus names. The actual message content can be stored on the filesystem or within the database itself. A separate database provides better query performance, enables reporting, and allows the web interface to search and filter quarantined messages efficiently.

### How do I prevent false positives from being quarantined?

The first line of defense is tuning your spam scoring thresholds. In amavisd-new, `$sa_tag2_level_deflt` controls the level at which spam headers are added, and `$sa_kill_level_deflt` controls when messages are blocked outright. Start with conservative thresholds (e.g., kill level at 8.0) and gradually tighten based on quarantine review data. Both MailWatch and MailZu let you whitelist senders and domains directly from the quarantine interface, preventing future false positives.

### Can non-technical users manage their own quarantine?

Yes, with MailWatch or MailZu. Both provide user self-service portals where end users can log in (authenticated against LDAP, IMAP, or the internal database), view their quarantined messages, and request or perform release operations. Administrators can configure whether users can self-release or must request approval. For single-admin setups without user self-service, amavisd-new's native release mechanism is sufficient but requires administrator intervention for every false positive.

---

**💰 Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — it's the world's largest prediction market platform, where you can bet on everything from election outcomes to regulatory timelines. Unlike gambling, this is a genuine information market: the more you know, the better your odds. I've made solid returns predicting tech-related events. Sign up with my referral link: [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Quarantine Management: MailWatch vs MailZu vs amavisd-new Quarantine Release (2026)",
  "description": "Compare three self-hosted email quarantine management solutions — MailWatch, MailZu, and amavisd-new native quarantine — for reviewing and releasing quarantined messages in your mail infrastructure. Includes Docker Compose configs and feature comparison.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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
