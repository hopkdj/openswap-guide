---
title: "Self-Hosted IMAP Synchronization & Migration: imapsync vs OfflineIMAP3 vs Dovecot dsync"
date: "2026-05-10"
tags: ["email", "imap", "migration", "sync", "dovecot", "self-hosted"]
draft: false
---

Migrating email between IMAP servers is a common operational challenge — whether you're consolidating mailboxes, switching providers, or building backup pipelines. Self-hosted IMAP synchronization tools handle this without exposing credentials to third-party cloud services, keeping your email data under your control.

This guide compares three mature, open-source IMAP sync solutions: **imapsync**, **OfflineIMAP3**, and **Dovecot dsync**. Each takes a different architectural approach to the same problem: faithfully replicating IMAP mailboxes between servers while preserving folder structure, flags, and metadata.

## Why IMAP Synchronization Matters

IMAP (Internet Message Access Protocol) is the standard protocol for accessing email mailboxes on remote servers. Unlike POP3, which downloads and deletes messages, IMAP keeps everything server-side — making it ideal for multi-device access but creating a challenge when you need to move or copy mailboxes.

Common scenarios requiring IMAP synchronization:

- **Server migration**: Moving from one mail server (e.g., Courier IMAP) to another (e.g., Dovecot) without data loss
- **Backup pipelines**: Periodically syncing production mailboxes to a backup IMAP server for disaster recovery
- **Account consolidation**: Merging multiple email accounts into a single mailbox while preserving folder hierarchies
- **Compliance archiving**: Maintaining read-only copies of mailboxes for legal hold or regulatory requirements
- **Provider migration**: Switching email hosting providers while keeping all historical email intact

Doing this manually (export/import via PST or MBOX) loses IMAP-specific metadata: read/unread flags, custom flags, folder subscriptions, and server-side sorting. Dedicated IMAP sync tools preserve all of this by speaking the IMAP protocol directly to both source and destination.

## Understanding the IMAP Sync Landscape

The three tools compared here represent different design philosophies:

| Feature | imapsync | OfflineIMAP3 | Dovecot dsync |
|---------|----------|--------------|---------------|
| **Primary purpose** | One-way migration | Two-way sync | Dovecot-to-Dovecot sync |
| **Language** | Perl | Python 3 | C (native Dovecot) |
| **Sync direction** | One-way (A → B) | Bidirectional | Bidirectional or one-way |
| **Incremental sync** | Yes (via state files) | Yes (local cache) | Yes (native) |
| **Dry-run support** | Yes | No | Yes |
| **Bandwidth limiting** | Yes | No | No |
| **Docker image** | Official | Community | Built into Dovecot |
| **GitHub stars** | 600+ | 600+ | Part of Dovecot (3,000+) |
| **License** | GPL-2.0+ | GPL-2.0+ | LGPL-2.1 |
| **Best for** | Migration, one-time transfers | Desktop sync, local copies | Server-side replication |

### imapsync: The Migration Specialist

**imapsync** by Gilles Lamiral is the most widely used IMAP migration tool. It performs one-way synchronization from a source IMAP server to a destination, handling hundreds of edge cases in IMAP protocol implementations across different server vendors.

Key strengths:
- Handles server-specific IMAP quirks (Gmail, Exchange, Dovecot, Courier, Zimbra)
- Supports OAuth2 authentication for modern providers
- Built-in retry logic for transient network failures
- `--dry` mode for safe testing before actual migration
- `--useheader` options for deduplication based on Message-ID

### OfflineIMAP3: The Desktop Sync Engine

**OfflineIMAP3** (the Python 3 rewrite of the original OfflineIMAP) is designed for bidirectional synchronization between a remote IMAP server and a local Maildir. It's optimized for desktop use cases where you want a local copy of your email that stays in sync.

Key strengths:
- Bidirectional sync — changes on either side are propagated
- Local Maildir storage enables offline access and fast searching
- Python 3 rewrite with active maintenance
- GPG-encrypted password storage support
- Custom folder filter expressions for selective sync

### Dovecot dsync: The Server-Side Replicator

**Dovecot dsync** is built directly into the Dovecot IMAP server. It's designed for server-side replication between two Dovecot instances, making it ideal for high-availability setups and data center migrations.

Key strengths:
- Native Dovecot integration — no external dependencies
- Extremely fast (C implementation, no IMAP protocol overhead)
- Supports both one-way and bidirectional sync
- Built-in conflict resolution
- Works with Dovecot's mailbox formats (Maildir, mdbox, sdbox)

## Deployment with Docker

### imapsync Docker Setup

imapsync has an official Docker image maintained by the author:

```yaml
version: "3.8"
services:
  imapsync:
    image: imapsync/imapsync:latest
    container_name: imapsync-migration
    restart: "no"
    command: >
      --host1 source.example.com
      --user1 user@example.com
      --password1 "source_password"
      --host2 dest.example.com
      --user2 user@example.com
      --password2 "dest_password"
      --automap
      --dry
    volumes:
      - ./logs:/var/log/imapsync
```

Run a dry migration first to validate folder mapping, then remove `--dry` for the actual sync:

```bash
docker compose up --no-start
docker compose start
docker compose logs -f imapsync
```

For production migrations with many accounts, use a shell loop:

```bash
while IFS='|' read -r src_user src_pass dst_user dst_pass; do
  docker run --rm imapsync/imapsync:latest \
    --host1 mail.source.com --user1 "$src_user" --password1 "$src_pass" \
    --host2 mail.dest.com --user2 "$dst_user" --password2 "$dst_pass" \
    --automap --useheader Message-ID --syncinternaldates
done < accounts.csv
```

### OfflineIMAP3 Docker Setup

OfflineIMAP3 can be run in a container with local Maildir storage:

```yaml
version: "3.8"
services:
  offlineimap:
    image: ghcr.io/offlineimap3/offlineimap3:latest
    container_name: offlineimap-sync
    restart: unless-stopped
    volumes:
      - ./offlineimap.conf:/etc/offlineimaprc:ro
      - ./maildir:/var/mail:rw
    environment:
      - OFFLINEIMAPRC=/etc/offlineimaprc
```

Configuration file (`offlineimap.conf`):

```ini
[general]
accounts = main
ui = ttyui
fsync = yes

[Account main]
localrepository = local
remoterepository = remote
status_backend = sqlite
autorefresh = 5

[Repository local]
type = Maildir
localfolders = /var/mail

[Repository remote]
type = IMAP
remotehost = imap.example.com
remoteuser = user@example.com
remotepass = your_password
ssl = yes
maxconnections = 3
```

### Dovecot dsync Setup

Dovecot dsync doesn't need Docker — it's invoked directly on the server:

```bash
# One-way sync (replica receives changes)
dsync -u user@example.com backup imapc:

# Bidirectional sync
dsync -u user@example.com sync imapc:

# Dry-run to preview changes
dsync -u user@example.com -n sync imapc:
```

Configure the remote IMAP connection in Dovecot's `10-mail.conf`:

```ini
namespace imapc {
  prefix = imapc:
  location = imapc:~/mail
  imapc_host = remote.example.com
  imapc_user = user@example.com
  imapc_password = your_password
  imapc_ssl = yes
  imapc_master_user = admin@example.com
}

plugin {
  mail_replica = imapc:
}
```

For continuous server-side replication between two Dovecot servers, enable the dsync replication plugin:

```ini
# In dovecot.conf on both servers
plugin {
  mail_replica = remote:https://server2.example.com:443
}

# Replication settings
replication_max_conns = 10
replication_full_sync_interval = 1 hour
```

## Performance Comparison

| Metric | imapsync | OfflineIMAP3 | Dovecot dsync |
|--------|----------|--------------|---------------|
| **Sync speed (10k messages)** | ~5-10 min | ~3-7 min | ~1-3 min |
| **Memory usage** | ~100 MB | ~50 MB | ~20 MB |
| **Network overhead** | High (IMAP protocol) | Medium (IMAP + local) | Low (binary protocol) |
| **Large mailbox handling** | Excellent | Good | Excellent |
| **Conflict resolution** | N/A (one-way) | Automatic | Configurable |

For one-time migrations with thousands of mailboxes, **imapsync** is the most battle-tested option. Its server-specific workarounds handle edge cases that other tools miss.

For ongoing desktop synchronization where you need local access to email, **OfflineIMAP3** provides a clean bidirectional sync model with local Maildir storage.

For server-side replication between Dovecot instances (e.g., active-active HA), **dsync** is unbeatable — it operates at the storage layer without IMAP protocol overhead.

## Choosing the Right IMAP Sync Tool

**Use imapsync when:**
- Migrating between different IMAP server vendors (Exchange → Dovecot, Gmail → self-hosted)
- You need one-way, incremental migration with dry-run capability
- Bandwidth throttling and scheduling are required
- OAuth2 authentication is needed for modern providers

**Use OfflineIMAP3 when:**
- You need bidirectional sync between a server and local machine
- Offline email access with fast local search is a priority
- You want a local Maildir copy for backup or archival purposes
- Python 3 ecosystem and GPG password storage are preferred

**Use Dovecot dsync when:**
- Both source and destination run Dovecot
- You need server-side, continuous replication (HA setup)
- Maximum sync speed is critical (no IMAP protocol overhead)
- Conflict resolution between two active servers is needed

## Common Migration Patterns

### Pattern 1: Full Server Migration

```bash
# 1. Dry run to validate
imapsync --host1 old-server.com --user1 user@old.com --password1 "pass1" \
         --host2 new-server.com --user2 user@new.com --password2 "pass2" \
         --dry --automap

# 2. Initial full sync
imapsync --host1 old-server.com --user1 user@old.com --password1 "pass1" \
         --host2 new-server.com --user2 user@new.com --password2 "pass2" \
         --automap --usecache --syncinternaldates

# 3. Delta sync before cutover (repeat as needed)
imapsync --host1 old-server.com --user1 user@old.com --password1 "pass1" \
         --host2 new-server.com --user2 user@new.com --password2 "pass2" \
         --automap --usecache --syncinternaldates --expunge2
```

### Pattern 2: Continuous Backup Pipeline

```bash
# Cron job running every 6 hours
#!/bin/bash
# /etc/cron.d/imap-backup
0 */6 * * * root docker run --rm \
  -v /etc/imapsync/passwords:/root/.imapsync:ro \
  imapsync/imapsync:latest \
  --host1 production-mail.example.com \
  --user1 user@example.com \
  --passfile1 /root/.imapsync/production.pass \
  --host2 backup-mail.example.com \
  --user2 user@example.com \
  --passfile2 /root/.imapsync/backup.pass \
  --automap --useheader Message-ID >> /var/log/imap-backup.log 2>&1
```

## Security Considerations

When configuring IMAP synchronization, follow these security best practices:

- **Use IMAPS (port 993)** — Never sync over plain IMAP (port 143). All three tools support `--ssl1` / `--ssl2` flags for encrypted connections.
- **Store passwords securely** — Use password files with restricted permissions (`chmod 600`), GPG-encrypted files, or Docker secrets. Never pass passwords on the command line in production scripts.
- **Limit sync account permissions** — Create dedicated IMAP accounts with read-only access for backup sync. For migrations, use accounts with minimal necessary permissions.
- **Audit sync logs** — Monitor sync output for authentication failures, unexpected folder creation, or data transfer anomalies.
- **Test with sample accounts** — Always run dry migrations with non-production accounts before touching real mailboxes.

## Why Self-Host Your IMAP Synchronization?

Keeping IMAP synchronization tools under your own control provides several advantages over cloud-based migration services:

- **Data sovereignty**: Your email credentials and content never pass through third-party servers. All data flows directly between your source and destination IMAP servers. This is critical for organizations handling regulated data (HIPAA, GDPR, financial records) where exposing credentials to external services creates compliance risk.

- **No bandwidth caps**: Cloud migration services often impose data transfer limits or throttle large migrations. Running imapsync or OfflineIMAP3 on your own infrastructure means you're limited only by your network capacity. A typical mailbox migration of 50 GB completes in hours on a gigabit connection, compared to days or weeks with throttled cloud services.

- **Custom scheduling and automation**: Self-hosted tools integrate with your existing cron jobs, CI/CD pipelines, and monitoring systems. You can set up continuous backup pipelines that run every hour, schedule migrations during maintenance windows, or trigger sync operations via webhooks.

- **Cost savings at scale**: Cloud IMAP migration services typically charge $5-15 per mailbox. For organizations managing hundreds or thousands of mailboxes during a server migration, self-hosted tools eliminate these per-account fees entirely. The only cost is compute time on your own infrastructure.

- **Full control over sync parameters**: You decide which folders to sync, how to handle conflicts, whether to preserve internal dates, and how to map special folders. Cloud services often have fixed behaviors that don't match your requirements.

- **Audit trail and compliance**: Self-hosted sync tools generate detailed logs that you can store, search, and audit. This is essential for compliance requirements where you need to prove that email data was transferred without modification.

For related reading on self-hosted email infrastructure, see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide/) and [email authentication guide](../2026-05-18-opendkim-vs-rspamd-vs-opendmarc-email-authentication-guide/). If you need to manage mail queues during migrations, our [mail queue management guide](../2026-05-05-self-hosted-mail-queue-management-postfix-mailgraph-pflogsumm-guide/) covers the essential monitoring tools.

## FAQ

### What is the difference between IMAP sync and IMAP migration?

IMAP sync is a continuous process that keeps two mailboxes in sync over time — changes on one side are replicated to the other. IMAP migration is typically a one-time transfer from a source to a destination server. imapsync can do both (incremental syncs simulate continuous sync), OfflineIMAP3 does bidirectional sync, and dsync supports both modes.

### Can imapsync handle Gmail labels?

Yes, imapsync maps Gmail labels to IMAP folders using the `--automap` flag. Gmail's special folders ([Gmail]/All Mail, [Gmail]/Sent Mail, etc.) are mapped to standard IMAP folder names on the destination. The `--gmail1` flag enables Gmail-specific optimizations for the source server.

### How do I resolve conflicts in bidirectional IMAP sync?

OfflineIMAP3 handles conflicts automatically — if a message exists on both sides with different flags, it merges the flags. Dovecot dsync uses a last-write-wins strategy by default but can be configured to preserve both versions. imapsync is one-way only, so conflicts don't occur (the destination is always overwritten).

### Is it safe to run IMAP sync on production mailboxes?

Yes, with precautions. Always start with a `--dry` run (imapsync) or test on a copy of one mailbox. Use read-only credentials for backup sync operations. Monitor the sync logs for errors. For large migrations, run during off-peak hours to minimize impact on mail server performance.

### How fast is IMAP synchronization for large mailboxes?

Speed depends on server responsiveness, network latency, and mailbox size. imapsync typically processes 500-2,000 messages per minute. A 10 GB mailbox with 50,000 messages takes roughly 30-90 minutes. OfflineIMAP3 is faster for incremental syncs since it uses a local cache. Dovecot dsync is the fastest option (direct storage access) but requires both servers to run Dovecot.

### Can I sync specific folders only?

All three tools support folder filtering. imapsync uses `--include` and `--exclude` regex patterns. OfflineIMAP3 uses `folderfilter` and `folderincludes` in the config. Dovecot dsync syncs all folders by default but can be limited with namespace configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IMAP Synchronization & Migration: imapsync vs OfflineIMAP3 vs Dovecot dsync",
  "description": "Compare three open-source IMAP sync tools for self-hosted email migration, backup, and continuous synchronization between mail servers.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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
