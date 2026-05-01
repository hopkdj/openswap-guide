---
title: "Baikal vs SabreDAV vs Nextcloud Contacts — Self-Hosted CardDAV Contact Management"
date: 2026-05-01T14:00:00+00:00
tags: ["contact-management", "carddav", "self-hosted", "privacy", "baikal", "sabredav", "nextcloud"]
draft: false
---

Managing contacts across devices without handing them to Google or Apple is a growing concern for privacy-conscious users. CardDAV, an open protocol for syncing address books, gives you full control over your contact data. In this guide, we compare three self-hosted CardDAV solutions — **Baikal**, **SabreDAV**, and **Nextcloud Contacts** — so you can pick the right one for your infrastructure.

## What Is CardDAV and Why Self-Host Contacts?

CardDAV is a protocol built on WebDAV that allows clients to store, sync, and manage contact information. It's the same protocol Apple uses under the hood for iCloud contacts, but when self-hosted, you own the data entirely.

Self-hosting your contacts means:
- **No vendor lock-in** — your data lives on your server, not in a proprietary cloud
- **Cross-device sync** — any CardDAV-compatible client (iOS, Android, Thunderbird, macOS) connects to the same source
- **Privacy by design** — no telemetry, no scanning, no data mining of your address book
- **Integration with groupware** — pair with CalDAV for calendar sync using the same server

For a complete overview of self-hosted calendar and contact servers, check our [Radicale vs Baikal vs Xandikos guide](../radicale-vs-baikal-vs-xandikos-self-hosted-calendar-contacts/).

## At a Glance: Comparison Table

| Feature | Baikal | SabreDAV | Nextcloud Contacts |
|---------|--------|----------|-------------------|
| **GitHub Stars** | 3,139 | 1,702 | 34,778 (Nextcloud server) |
| **Primary Protocol** | CalDAV + CardDAV | CalDAV + CardDAV | CardDAV (via Nextcloud) |
| **Language** | PHP | PHP | PHP |
| **Database** | SQLite / MySQL | SQLite / MySQL / PostgreSQL | MySQL / PostgreSQL / SQLite |
| **Web UI** | Admin panel only | None (library only) | Full contacts UI |
| **Docker Support** | Official image | Community images | Official image |
| **Active Development** | Yes (regular updates) | Yes (library updates) | Yes (very active) |
| **Best For** | Lightweight CalDAV/CardDAV server | Developers building on CardDAV | Full-featured contact management |

## Baikal — Lightweight CalDAV + CardDAV Server

Baikal is a minimal, fast, and easy-to-deploy CalDAV and CardDAV server. It's designed for individuals and small teams who need reliable contact and calendar sync without the overhead of a full groupware suite.

### Key Features

- **Simple setup** — web-based installer, works out of the box with SQLite
- **Admin UI** — manage users, address books, and calendars from a browser
- **Lightweight** — runs on minimal hardware, low memory footprint
- **SabreDAV-based** — built on the proven SabreDAV library, ensuring protocol compliance

### Docker Compose Deployment

```yaml
services:
  baikal:
    image: ckulka/baikal:latest
    container_name: baikal
    ports:
      - "8080:80"
    volumes:
      - ./baikal/config:/var/www/baikal/config
      - ./baikal/Specific:/var/www/baikal/Specific
    restart: unless-stopped
```

For production use, add a reverse proxy with TLS termination. If you're also running other self-hosted services like an email server, Baikal integrates well with your existing setup — see our [complete email server guide](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) for Postfix/Dovecot configuration patterns.

### Pros and Cons

| Pros | Cons |
|------|------|
| Dead simple to set up | No user-facing contact UI |
| Supports both CalDAV and CardDAV | Limited to single-user or small teams |
| Low resource requirements | No group sharing features |
| Well-documented | SQLite-only for default setup |

## SabreDAV — The CardDAV Library Powering Everything

SabreDAV isn't a standalone product — it's the PHP library that powers Baikal, Nextcloud, and many other CalDAV/CardDAV implementations. But you can also deploy it directly as a server if you need a custom setup.

### Key Features

- **Protocol-compliant** — implements CalDAV, CardDAV, and WebDAV to spec
- **Extensible** — plugin architecture for custom authentication, ACL, and storage backends
- **Database flexibility** — supports SQLite, MySQL, and PostgreSQL
- **Battle-tested** — used by thousands of production deployments

### Docker Compose Deployment

```yaml
services:
  sabredav:
    image: ghcr.io/sabre-io/server:latest
    container_name: sabredav
    ports:
      - "8080:80"
    volumes:
      - ./sabredav/data:/var/www/html/data
      - ./sabredav/config:/var/www/html/config
    environment:
      - SABREDB_TYPE=mysql
      - SABREDB_HOST=db
      - SABREDB_NAME=sabredav
      - SABREDB_USER=sabre
      - SABREDB_PASS=changeme
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:11
    container_name: sabredav-db
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=sabredav
      - MYSQL_USER=sabre
      - MYSQL_PASSWORD=changeme
    volumes:
      - ./sabredav/db:/var/lib/mysql
    restart: unless-stopped
```

### Pros and Cons

| Pros | Cons |
|------|------|
| Maximum flexibility | Requires PHP knowledge to customize |
| Industry-standard compliance | No built-in admin UI |
| Powers Baikal and Nextcloud | Documentation geared toward developers |
| Supports multiple database backends | Not end-user friendly out of the box |

## Nextcloud Contacts — Full-Featured Contact Management

Nextcloud Contacts is the address book app within the Nextcloud ecosystem. It offers a polished web UI, group sharing, and deep integration with the broader Nextcloud platform.

### Key Features

- **Rich web UI** — search, edit, and organize contacts in your browser
- **Group sharing** — share address books with other Nextcloud users
- **App ecosystem** — integrates with Nextcloud Mail, Talk, Calendar, and more
- **Federation support** — sync contacts across Nextcloud instances
- **VCard 4.0 support** — full specification compliance

### Docker Compose Deployment

```yaml
services:
  nextcloud:
    image: nextcloud:apache
    container_name: nextcloud-contacts
    ports:
      - "8080:80"
    volumes:
      - ./nextcloud/html:/var/www/html
      - ./nextcloud/apps:/var/www/html/custom_apps
      - ./nextcloud/config:/var/www/html/config
      - ./nextcloud/data:/var/www/html/data
    environment:
      - MYSQL_HOST=db
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=changeme
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:11
    container_name: nextcloud-db
    command: --transaction-isolation=READ-COMMITTED --binlog-format=ROW
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=nextcloud
      - MYSQL_USER=nextcloud
      - MYSQL_PASSWORD=changeme
    volumes:
      - ./nextcloud/db:/var/lib/mysql
    restart: unless-stopped

  redis:
    image: redis:alpine
    container_name: nextcloud-redis
    restart: unless-stopped
```

After deployment, install the Contacts app from the Nextcloud app store. The CardDAV endpoint will be available at `https://your-domain/remote.php/dav/addressbooks/`.

### Pros and Cons

| Pros | Cons |
|------|------|
| Full-featured web UI | Heavy resource footprint |
| Group sharing and federation | Requires full Nextcloud stack |
| App ecosystem integration | Overkill if you only need contacts |
| Active development community | More complex to maintain |

## Which Should You Choose?

**Choose Baikal if** you want a lightweight, no-fuss CardDAV server. It's perfect for individuals or families who need contact sync across devices without running a full groupware suite. The admin UI is minimal but effective, and setup takes under 5 minutes.

**Choose SabreDAV if** you're a developer building a custom solution. It gives you the raw CardDAV protocol implementation with full control over authentication, storage, and extensions. If you need to embed CardDAV into an existing application, this is your starting point.

**Choose Nextcloud Contacts if** you want a polished, full-featured contact management experience. The web UI is excellent for managing large address books, and the group sharing features make it ideal for teams. The trade-off is the heavier infrastructure requirement — you're deploying an entire Nextcloud instance, not just a contacts server.

## Connecting Clients

All three solutions use the standard CardDAV protocol, so client setup is identical:

- **iOS/iPadOS**: Settings → Contacts → Accounts → Add Account → Other → Add CardDAV Account
- **Android**: Use DAVx5 (available on F-Droid) or the built-in contacts sync in many ROMs
- **Thunderbird**: Install the CardBook extension for full CardDAV support
- **macOS**: System Preferences → Internet Accounts → Add CardDAV

The server URL format is:
- Baikal: `https://your-server/dav.php/`
- SabreDAV: `https://your-server/server.php/addressbooks/`
- Nextcloud: `https://your-server/remote.php/dav/addressbooks/`

## Why Self-Host Your Contacts?

Taking control of your contact data is one of the most impactful self-hosting moves you can make. Your address book contains sensitive information — names, phone numbers, email addresses, physical addresses, and personal notes about the people in your life. When you use Google Contacts or iCloud, that data is scanned, analyzed, and potentially used for profiling and advertising.

Self-hosting gives you complete ownership. You decide who has access, how long data is retained, and whether it's encrypted at rest. Combined with a self-hosted email server, you create a fully private communication stack that no third party can monitor or monetize.

For organizations, self-hosted CardDAV eliminates compliance risks associated with storing employee and customer contact data in public cloud services. It also ensures business continuity — if your server is under your control, there's no risk of an account suspension locking you out of your own data.

If you're building a complete privacy-focused infrastructure, consider pairing your CardDAV server with other self-hosted tools. Our [privacy search engines comparison](../searxng-vs-whoogle-vs-librex-self-hosted-privacy-search-engines-2026/) and [email alias services guide](../simplelogin-vs-anonaddy-vs-forwardemail-self-hosted-email-alias-guide-2026/) cover complementary tools for protecting your digital footprint.

## FAQ

### What is the difference between CardDAV and CalDAV?

CardDAV is for syncing contact information (names, phone numbers, email addresses), while CalDAV is for syncing calendar events and tasks. Both are built on the WebDAV protocol and often run on the same server. Baikal and SabreDAV support both protocols simultaneously.

### Can I use Baikal without CalDAV?

Yes. Baikal supports CardDAV-only mode. You can create address books without setting up calendars, which is useful if you only need contact sync and prefer a different calendar solution.

### Is SabreDAV production-ready?

Absolutely. SabreDAV powers Baikal, Nextcloud, and many enterprise deployments. It's been actively maintained since 2009 and is the reference implementation for CardDAV in PHP. The library undergoes regular security audits and protocol compliance testing.

### How do I back up my CardDAV contacts?

For Baikal and SabreDAV, back up the SQLite database file or run `mysqldump` for MySQL. For Nextcloud, use the `occ` command: `php occ dav:sync-system-addressbook`. You can also export contacts as vCard files from any CardDAV client for offline backups.

### Can I migrate from Google Contacts to a self-hosted CardDAV server?

Yes. Export your Google Contacts as a vCard (.vcf) file from Google Takeout or the Google Contacts web UI. Then import it into your self-hosted server — Baikal supports vCard import through its admin panel, and Nextcloud has a bulk import feature in the Contacts app.

### Does self-hosted CardDAV work on iPhone and Android?

Yes. iOS has built-in CardDAV support (Settings → Contacts → Accounts). Android requires a third-party app like DAVx5, which syncs CardDAV contacts to the native Android contacts app. Both platforms support push sync for real-time updates.

### How many users can Baikal handle?

Baikal comfortably handles dozens of users on a Raspberry Pi. The SQLite backend is suitable for single-user or small-team setups. For larger deployments, switch to MySQL or PostgreSQL for better concurrency and performance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Baikal vs SabreDAV vs Nextcloud Contacts — Self-Hosted CardDAV Contact Management",
  "description": "Compare three self-hosted CardDAV contact management solutions: Baikal, SabreDAV, and Nextcloud Contacts. Includes Docker Compose configs, feature comparisons, and client setup guides.",
  "datePublished": "2026-05-01",
  "dateModified": "2026-05-01",
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
