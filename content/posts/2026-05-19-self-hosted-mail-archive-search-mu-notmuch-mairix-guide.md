---
title: "Self-Hosted Mail Archive Search Tools — mu vs notmuch vs mairix"
date: "2026-05-19"
tags: ["email", "search", "maildir", "archive", "self-hosted"]
draft: false
---

When your mail archive grows beyond a few thousand messages, finding specific emails becomes a real challenge. Most email clients rely on IMAP SEARCH commands that are slow, limited, and struggle with full-text queries across large Maildir or mbox collections. Dedicated mail indexing and search tools solve this by building local search indexes — enabling near-instant full-text search across tens of thousands of messages.

This guide compares three leading open-source mail archive search tools: **mu**, **notmuch**, and **mairix**. Each takes a different approach to indexing and querying email, with distinct strengths depending on your workflow, storage format, and integration needs.

## Quick Comparison

| Feature | mu | notmuch | mairix |
|---------|----|---------|--------|
| GitHub Stars | 1,696 | 198 | 139 |
| Primary Format | Maildir | Maildir, MH, mbox | Maildir, MH, mbox |
| Index Engine | Xapian | Xapian | Custom inverted index |
| Full-Text Search | Yes | Yes | Yes |
| Header Search | Yes | Yes | Yes |
| Date Range Queries | Yes | Yes | No |
| Boolean Queries | Yes | Yes | Limited |
| Thread View | Yes | Yes | No |
| Emacs Integration | mu4e (built-in) | notmuch-emacs | None |
| CLI Speed (100k msgs) | ~15s index | ~20s index | ~10s index |
| Language | C++ + Guile | C | C |
| License | GPL-3.0 | GPL-3.0 | GPL-3.0 |

## mu — Fast Maildir Indexer with Emacs Integration

**mu** is the most feature-rich of the three tools. Built on the Xapian search engine, it indexes Maildir folders and provides powerful query capabilities including date ranges, boolean operators, and full-text search.

### Installation

```bash
# Debian/Ubuntu
sudo apt install mu4e

# macOS
brew install mu

# From source
git clone https://github.com/djcb/mu.git
cd mu && ./autogen.sh && make && sudo make install
```

### Indexing and Searching

```bash
# Initialize index for a Maildir
mu init --maildir=~/Mail --my-address=user@example.com

# Build the index
mu index

# Search for messages
mu find "from:github date:2026-01..2026-05"
mu find "subject:invoice flag:unread"
mu find "body:deployment AND from:ops-team"

# Search by flag/status
mu find "flag:flagged OR flag:important"
```

### Docker Compose Deployment

For users who want to run mu alongside their mail server in a container:

```yaml
version: "3.8"
services:
  mu-search:
    image: ghcr.io/djcb/mu:latest
    volumes:
      - ./Maildir:/mail:ro
      - ./mu-index:/var/lib/mu
    command: ["mu", "index", "--maildir=/mail"]
    restart: on-failure
```

### Key Features

- **mu4e**: A full-featured Emacs email client built on top of mu, providing a Gmail-like interface with threading, search, and composition
- **Guile bindings**: Scriptable API for custom mail processing workflows
- **Incremental indexing**: Only re-indexes changed messages, keeping updates fast
- **Thread grouping**: Automatically groups related messages into conversation threads

## notmuch — Tag-Based Email Organization

**notmuch** pioneered the tag-based approach to email management. Rather than organizing messages into folders, notmuch lets you apply arbitrary tags to any message, enabling flexible, multi-dimensional organization.

### Installation

```bash
# Debian/Ubuntu
sudo apt install notmuch notmuch-emacs

# macOS
brew install notmuch

# From source
git clone https://git.notmuchmail.org/git/notmuch
cd notmuch && ./configure && make && sudo make install
```

### Indexing and Searching

```bash
# Initialize notmuch database
notmuch new

# Search with powerful query syntax
notmuch search "from:alice and subject:meeting and date:2026-01-01..2026-05-01"
notmuch search "tag:inbox and tag:unread and crypto:signed"

# Tag-based organization
notmuch tag +archive -- "tag:inbox and older:6months"
notmuch tag -inbox +read -- "id:message-id@example.com"

# Show threads
notmuch search --format=json "tag:inbox" | notmuch show --format=mbox
```

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  notmuch-indexer:
    image: docker.io/notmuch/notmuch:latest
    volumes:
      - ./Maildir:/mail:ro
      - ./notmuch-db:/root/.notmuch
    environment:
      - NOTMUCH_PATH=/mail
    command: ["notmuch", "new"]
    restart: on-failure
```

### Key Features

- **Tag-based organization**: Apply unlimited tags to any message for flexible categorization
- **notmuch-emacs**: Full Emacs interface with mail composition, search, and tag management
- **Cryptographic support**: Detects and indexes PGP/GPG signed and encrypted messages
- **Hooks system**: Run custom scripts after indexing, enabling automation workflows
- **JSON output**: Machine-readable output format for integration with other tools

## mairix — Lightweight Mail Indexer

**mairix** is the simplest and most lightweight option. It builds a small inverted index file that maps keywords to message locations, enabling fast searches without the overhead of a full database engine.

### Installation

```bash
# Debian/Ubuntu
sudo apt install mairix

# macOS
brew install mairix

# From source
git clone https://github.com/rc0/mairix.git
cd mairix && make && sudo make install
```

### Configuration and Searching

```bash
# Create ~/.mairixrc
cat > ~/.mairixrc << 'EOF'
base=/home/user/Mail
mformat=maildir
database=/home/user/.mairix/database

maildir=Inbox:~/Mail/Inbox
maildir=Sent:~/Mail/Sent
maildir=Archive:~/Mail/Archive
EOF

# Build index
mairix

# Search
mairix "from:boss subject:urgent"
mairix "body:kubernetes deployment"
```

### Key Features

- **Minimal footprint**: Index file is typically under 1MB even for 100k+ messages
- **Fast searches**: Sub-second response for most queries due to simple index structure
- **No external dependencies**: Self-contained C binary, no database libraries required
- **Low resource usage**: Ideal for resource-constrained environments like Raspberry Pi or small VPS
- **MH and mbox support**: Works with all three major mail storage formats

## Why Self-Host Your Mail Archive Search?

Running your own mail indexing server gives you complete control over your email data. When you use cloud-based search providers, every query leaves your infrastructure and lands on someone else's servers. With self-hosted tools like mu, notmuch, or mairix, your entire email corpus — including attachments, headers, and message bodies — stays on your own hardware.

Data ownership is the primary motivation. Your mail archive often contains sensitive business correspondence, personal communications, and confidential documents. Indexing and searching locally means zero data exposure to third parties. For organizations handling regulated data (GDPR, HIPAA, financial records), this is not optional — it's a compliance requirement.

Performance is another significant factor. Cloud mail providers often limit search scope to recent messages or impose rate limits on complex queries. With local indexing, you can search your entire archive of hundreds of thousands of messages in milliseconds. There are no API limits, no query restrictions, and no waiting for remote servers to process your request.

Cost savings compound over time. Commercial email archiving solutions charge per mailbox per month, often with tiered pricing based on storage volume. Open-source tools like mu, notmuch, and mairix are free, run on commodity hardware, and scale to millions of messages without additional licensing costs.

For related reading on self-hosted email infrastructure, see our [email archiving guide](../2026-04-18-self-hosted-email-archiving-mailpiler-dovecot-stalwart-guide-2026/) which covers dedicated archive servers, and our [IMAP synchronization article](../2026-05-10-self-hosted-imap-synchronization-migration-imapsync-offlineimap3-dovecot-dsync/) for migrating mail between servers. If you need to set up the underlying mail server first, our [MTA comparison](../2026-04-29-postfix-vs-exim-self-hosted-mta-comparison-guide-2026/) covers the mail transfer options.

## Choosing the Right Tool

**Choose mu if:** You use Emacs and want a complete email client experience, or need the most feature-rich search capabilities including date ranges, boolean operators, and threading. mu4e is arguably the best terminal-based email client available.

**Choose notmuch if:** You prefer tag-based organization over folder hierarchies, or need cryptographic message detection. notmuch's tag system lets you organize mail in ways that traditional folder structures cannot match.

**Choose mairix if:** You need the lightest possible footprint on resource-constrained hardware, or want the simplest possible setup with zero configuration overhead. mairix excels in environments where minimal resource usage is the primary concern.

## FAQ

### Can these tools search across multiple Maildir folders simultaneously?

Yes, all three tools support indexing multiple Maildir, MH, or mbox folders in a single index. mu and notmuch handle this automatically when pointed at a top-level Maildir. mairix requires explicit configuration of each folder path in `.mairixrc`.

### How long does indexing take for a large archive (100k+ messages)?

mu typically indexes 100k messages in 15-20 seconds on modern hardware. notmuch takes 20-30 seconds for the same workload. mairix is fastest at 10-15 seconds but offers fewer query features. All three support incremental updates that process only new or changed messages.

### Do these tools support searching within email attachments?

No, none of these tools index attachment contents directly. They index the message body and headers. For attachment content search, you would need to extract and index attachments separately using tools like Apache Tika or Elasticsearch.

### Can I run these tools on a headless server without a GUI?

Yes, all three are primarily command-line tools. mu has mu4e for Emacs (terminal-based), notmuch has notmuch-emacs (also terminal-based), and mairix is CLI-only. All can run over SSH on remote servers with no graphical environment required.

### How do I keep the index up to date with new incoming mail?

mu and notmuch support incremental indexing triggered by new mail delivery. You can configure procmail, Sieve, or maildirwatch to trigger `mu index` or `notmuch new` when new messages arrive. mairix requires manual re-indexing or a cron job running `mairix` periodically.

### Is Xapian (used by mu and notmuch) reliable for large indexes?

Xapian is a mature, production-grade search engine used by Debian, Wikipedia, and many other large-scale projects. It handles indexes with millions of documents reliably. Both mu and notmuch have been using Xapian for over a decade with proven stability.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Mail Archive Search Tools — mu vs notmuch vs mairix",
  "description": "Compare three leading open-source mail archive search tools: mu, notmuch, and mairix. Learn which tool is best for indexing and searching large email collections.",
  "datePublished": "2026-05-19",
  "dateModified": "2026-05-19",
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
