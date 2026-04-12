---
title: "Radicale vs Baïkal vs Xandikos: Best Self-Hosted CalDAV/CardDAV Server 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare Radicale, Baïkal, and Xandikos — the top three lightweight self-hosted CalDAV and CardDAV servers. Complete setup guides with Docker, reverse proxy, and client configuration for keeping your calendars and contacts private in 2026."
---

Your calendar knows when you wake up, where you work, who you meet, and what you care about. Your contacts list is a map of your entire social and professional life. Yet most people hand this data over to Google, Apple, or Microsoft without a second thought.

Self-hosting your calendar and contacts gives you back control. With the CalDAV and CardDAV protocols — open standards supported by virtually every calendar and contacts app — you can run your own sync server on a $5 VPS or a Raspberry Pi. This guide compares the three leading standalone CalDAV/CardDAV servers: **Radicale**, **Baïkal**, and **Xandikos**.

## Why Self-Host Your Calendar and Contacts

The reasons are straightforward:

- **Privacy**: Your schedule and relationships are sensitive data. A self-hosted server means no third party scans your events for advertising profiles or trains models on your contact graph.
- **No vendor lock-in**: CalDAV and CardDAV are open RFC standards (RFC 4791 and RFC 6352). Any standards-compliant client works with any server. Switch apps freely — Thunderbird, DAVx5, GNOME Calendar, iOS, macOS, Outlook — they all connect the same way.
- **Full ownership**: Your data lives on hardware you control. Export it, back it up, migrate it — on your terms.
- **Lightweight footprint**: Unlike running a full Nextcloud instance just for calendar sync, dedicated CalDAV/CardDAV servers consume minimal RAM (often under 100 MB) and need almost no CPU.
- **Reliability**: These servers have been production-stable for years. Once configured, they run silently in the background with near-zero maintenance.

If you already run Nextcloud and only need calendar and contacts, its built-in CalDAV/CardDAV support may suffice. But if you want something purpose-built, fast, and resource-efficient, read on.

## Understanding CalDAV and CardDAV

Before comparing servers, it helps to understand the protocols:

- **CalDAV** (RFC 4791) extends WebDAV to manage calendar data stored in iCalendar (`.ics`) format. It supports events, to-dos, journals, free/busy queries, and scheduling.
- **CardDAV** (RFC 6352) similarly extends WebDAV for vCard (`.vcf`) contact data. It supports contact creation, searching, grouping, and synchronization.

Both run over HTTP/HTTPS, use standard authentication, and are supported natively or via add-ons on every major platform:

| Platform | Calendar (CalDAV) | Contacts (CardDAV) |
|----------|-------------------|--------------------|
| Android | DAVx5 + Etar Calendar | DAVx5 + Contacts app |
| iOS / iPadOS | Built-in (Add Account → Other) | Built-in (same flow) |
| macOS | Built-in (System Settings → Internet Accounts) | Built-in (same) |
| Windows | Outlook (via add-on), Thunderbird | Thunderbird |
| Linux | GNOME Calendar, Evolution, Thunderbird | GNOME Contacts, Thunderbird |
| Web | Radicale Manager, Baïkal admin | Baïkal admin |

## Contenders at a Glance

| Feature | Radicale | Baïkal | Xandikos |
|---------|----------|--------|----------|
| **Language** | Python | PHP | Python |
| **Storage** | Flat files | SQLite / MySQL | Git repository |
| **GitHub Stars** | 3,200+ | 2,800+ | 900+ |
| **Web Admin UI** | Minimal (Radicale Manager plugin) | Full admin panel | None (CLI only) |
| **Docker Image** | Official | Community | Community |
| **RAM Usage** | ~30 MB | ~50 MB | ~40 MB |
| **Multi-user** | Yes | Yes | Yes |
| **LDAP Auth** | Via plugin | Built-in | No |
| **Rights Management** | Regex-based file | Per-user / per-collection | Basic |
| **Web Interface** | Optional (third-party) | Yes (admin + basic web UI) | No |
| **Active Development** | Yes (steady) | Yes (periodic) | Yes (slow but steady) |
| **Best For** | Simplicity, minimalism | Users wanting a web admin panel | Git-backed version control lovers |

## Radicale: Minimalist and Reliable

[Radicale](https://radicale.org/) is the most popular standalone CalDAV/CardDAV server. Written in Python, it stores data as plain files on disk and aims to be small, simple, and correct. It implements the full CalDAV and CardDAV specifications and has been around since 2009.

### Strengths

- **Dead simple to set up**: A working server takes three commands.
- **Extremely lightweight**: Runs on a Raspberry Pi Zero with room to spare.
- **No database needed**: Data is stored as `.ics` and `.vcf` files — easy to back up with `rsync` or `restic`.
- **Active community**: The largest user base of any standalone CalDAV server.
- **Plugin ecosystem**: Supports authentication plugins, rights management, and storage backends.

### Weaknesses

- **No built-in web admin**: You manage users via config files or use the third-party Radicale Manager.
- **Flat file storage**: Great for simplicity, but can slow down with thousands of calendars/users.
- **Limited web UI**: The built-in web interface only shows a basic status page.

### Docker Setup

```yaml
# docker-compose.yml
services:
  radicale:
    image: tomsquest/docker-radicale:3
    container_name: radicale
    restart: unless-stopped
    ports:
      - "5232:5232"
    volumes:
      - ./config:/etc/radicale
      - ./data:/var/lib/radicale/collections
      - ./users:/etc/radicale/users
    environment:
      - TZ=UTC

  # Optional: web management interface
  radicale-manager:
    image: crauer-it/radicale-manager:latest
    container_name: radicale-manager
    restart: unless-stopped
    ports:
      - "5233:80"
    environment:
      - RADICALE_URL=http://radicale:5232
    depends_on:
      - radicale
```

Create the htpasswd file for authentication:

```bash
mkdir -p radicale/config radicale/data radicale/users

# Install htpasswd utility (apache2-utils on Debian/Ubuntu)
htpasswd -Bbc radicale/users/users alice
htpasswd -Bb radicale/users/users bob

# Create Radicale config
cat > radicale/config/config << 'EOF'
[server]
hosts = 0.0.0.0:5232

[auth]
type = htpasswd
htpasswd_filename = /etc/radicale/users/users
htpasswd_encryption = bcrypt

[rights]
type = authenticated

[storage]
filesystem_folder = /var/lib/radicale/collections

[web]
type = none
EOF

docker compose up -d
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name calendar.example.com;

    ssl_certificate /etc/letsencrypt/live/calendar.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5232;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for CalDAV/CardDAV
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

### Connecting Clients

**Android** (DAVx5):
1. Install DAVx5 from F-Droid or Play Store
2. Add account → Login with URL and user name
3. URL: `https://calendar.example.com/alice/`
4. Enter username and password

**iOS / macOS**:
1. Settings → Calendar → Accounts → Add Account → Other
2. Add CalDAV Account
3. Server: `calendar.example.com`, username, password
4. For contacts: Settings → Contacts → Accounts → Add CardDAV Account

**Thunderbird**:
1. Add Calendar → On the Network → CalDAV
2. URL: `https://calendar.example.com/alice/`
3. For contacts: Install TbSync + DAV Provider add-on

## Baïkal: Feature-Rich with a Web Admin

[Baïkal](https://sabre.io/baikal/) is a PHP-based CalDAV/CardDAV server built on the sabre/dav framework — the same library that powers ownCloud/Nextcloud's calendar backend. Its standout feature is a polished web admin interface where you can manage users, calendars, and address books without touching the command line.

### Strengths

- **Full web admin panel**: Create users, calendars, and address books from a browser.
- **Multiple database backends**: SQLite for simplicity, MySQL/PostgreSQL for scale.
- **sabre/dav foundation**: Battle-tested library used by major projects.
- **Built-in web UI**: Users can access a basic web interface for their calendars and contacts.
- **LDAP authentication**: Built-in support for LDAP/Active Directory.

### Weaknesses

- **PHP dependency**: Requires a PHP runtime (though the Docker image handles this).
- **Heavier than Radicale**: More dependencies, slightly higher resource usage.
- **Release cadence**: Updates come less frequently than Radicale.

### Docker Setup

```yaml
# docker-compose.yml
services:
  baikal:
    image: ckulka/baikal:nginx
    container_name: baikal
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./config:/var/www/baikal/config
      - ./data:/var/www/baikal/Specific
      - ./db:/var/www/baikal/DB
    environment:
      - TZ=UTC
      - INSTALL=yes
```

For the first run, visit `http://your-server:8080/admin/` to run the installation wizard. You'll set:

1. Admin credentials
2. Database type (SQLite is fine for most users)
3. Timezone and server base URL

After initial setup, remove `INSTALL=yes` from the environment variables and restart.

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name calendar.example.com;

    ssl_certificate /etc/letsencrypt/live/calendar.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.example.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Baïkal-specific headers
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # Block access to sensitive directories
    location ~ ^/(Core|vendor|html)/ {
        deny all;
    }
}
```

### Creating Users and Calendars via Web Admin

1. Log in to `https://calendar.example.com/admin/`
2. Go to **Users and Resources** → **Users** → click **+**
3. Set display name, password, and optionally an email
4. The user automatically gets a default calendar and address book
5. To add extra calendars: click the user → **+ Calendar** → set name and description
6. To add extra address books: click the user → **+ Address Book** → set name

### Connecting Clients

The process is identical to Radicale — just point your clients to the Baïkal server URL. Baïkal's auto-discovery works well with most clients:

- **CalDAV URL**: `https://calendar.example.com/dav.php/calendars/alice/`
- **CardDAV URL**: `https://calendar.example.com/dav.php/addressbooks/alice/`

## Xandikos: Git-Backed Version Control

[Xandikos](https://www.xandikos.org/) takes a fundamentally different approach: it stores all CalDAV and CardDAV data as a **Git repository**. Every change is automatically committed, giving you full version history of every calendar event and contact modification. Written in Python by Jelmer Vernooij (a prominent Debian developer), it's designed for correctness and standards compliance.

### Strengths

- **Git versioning**: Every change is tracked. You can diff, blame, and revert any calendar or contact edit.
- **Excellent standards compliance**: One of the most RFC-compliant CalDAV/CardDAV implementations.
- **Efficient storage**: Git's delta compression means minimal disk usage even with long histories.
- **Audit trail**: Know exactly who changed what and when — invaluable for shared calendars.
- **No database**: Like Radicale, it avoids database dependencies.

### Weaknesses

- **No web admin UI**: Everything is managed via config files or the API.
- **Smaller community**: Fewer users means fewer tutorials and community resources.
- **Git learning curve**: If something breaks, you may need Git troubleshooting skills.
- **Slower with large datasets**: Git operations can slow down with very large collections.

### Docker Setup

```yaml
# docker-compose.yml
services:
  xandikos:
    image: xandikos/xandikos:latest
    container_name: xandikos
    restart: unless-stopped
    ports:
      - "5234:8080"
    volumes:
      - ./collections:/var/lib/xandikos/collections
      - ./config:/etc/xandikos
    environment:
      - XANDIKOS_AUTOCREATE=principal,calendar,addressbook
      - TZ=UTC
```

### Manual Setup (Without Docker)

```bash
# Install Xandikos
pip install xandikos

# Create directory structure
mkdir -p ~/xandikos/collections

# Create a user directory
mkdir -p ~/xandikos/collections/alice

# Run the server
xandikos --listen-address 0.0.0.0 --listen-port 8080 \
    --autocreate-principal \
    --realm "My CalDAV Server" \
    --directory ~/xandikos/collections
```

### Nginx Reverse Proxy with Basic Auth

```nginx
server {
    listen 443 ssl http2;
    server_name calendar.example.com;

    ssl_certificate /etc/letsencrypt/live/calendar.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5234;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Pass authentication to Xandikos
        auth_basic "CalDAV Server";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_set_header Authorization "";  # Let Nginx handle auth
    }
}
```

### Browsing Git History

One of Xandikos' best features is the ability to inspect changes directly in the Git repository:

```bash
cd ~/xandikos/collections

# See all recent changes across all calendars
git log --oneline -20

# See what changed in a specific commit
git show abc1234

# View the diff of the last calendar event change
git diff HEAD -- "**/*.ics"

# Find who deleted a contact
git log --diff-filter=D -- "**/*.vcf"

# Restore a deleted contact from yesterday
git checkout HEAD~1 -- path/to/deleted-contact.vcf
```

## Comparison Deep Dive

### Performance and Resource Usage

| Metric | Radicale | Baïkal | Xandikos |
|--------|----------|--------|----------|
| **Idle RAM** | ~30 MB | ~50 MB | ~40 MB |
| **Sync 100 contacts** | < 0.5s | < 0.5s | < 1.0s |
| **Sync 1000 events** | < 2s | < 2s | < 3s |
| **Disk (1000 events + 500 contacts)** | ~5 MB | ~8 MB | ~3 MB (with Git) |
| **Backup method** | `cp` / `rsync` / `restic` | `mysqldump` or `cp` SQLite | `git bundle` / `git push` |

All three are dramatically lighter than running Nextcloud for calendar sync alone (which typically needs 512 MB+ RAM).

### Security Considerations

All three servers share similar security requirements:

1. **Always use HTTPS** — never expose CalDAV/CardDAV over plain HTTP, especially since passwords are sent with every sync.
2. **Use strong passwords** or token-based authentication.
3. **Keep the server updated** — all three receive security patches regularly.
4. **Fail2ban integration**: Protect against brute-force login attempts:

```ini
# /etc/fail2ban/jail.local
[radicale]
enabled = true
port = 5232
filter = radicale
logpath = /var/log/radicale/access.log
maxretry = 5
bantime = 3600

# /etc/fail2ban/filter.d/radicale.conf
[Definition]
failregex = ^.*Authentication for user .* failed$
ignoreregex =
```

### Backup Strategies

**Radicale** (file-based):
```bash
# Simple backup with restic
restic backup /var/lib/radicale/collections \
    --tag radicale \
    --exclude "*.lock"

# Or plain rsync to a remote server
rsync -avz /var/lib/radicale/ backup-server:/backups/radicale/
```

**Baïkal** (SQLite):
```bash
# Backup the SQLite database
sqlite3 /var/www/baikal/DB/db.sqlite ".backup '/backups/baikal-$(date +%F).sqlite'"

# Or with MySQL
mysqldump baikal > /backups/baikal-$(date +%F).sql
```

**Xandikos** (Git-native):
```bash
cd ~/xandikos/collections

# Push to a remote Git server
git push origin main

# Create a portable bundle
git bundle create /backups/xandikos-$(date +%F).bundle --all

# Clone the bundle on another machine
git clone /backups/xandikos-2026-04-12.bundle new-collections/
```

### Migration Between Servers

Moving between any of these three is straightforward because they all speak standard CalDAV/CardDAV:

1. Point your client (DAVx5, Thunderbird, etc.) to the new server URL.
2. The client will download all data from the old server and upload it to the new one.
3. Or export `.ics`/`.vcf` files from the old server and import them into the new one.

For bulk migration, tools like [vdirsyncer](https://vdirsyncer.pimutils.org/) can synchronize between any two CalDAV/CardDAV servers:

```ini
# ~/.vdirsyncer/config
[pair old_to_new]
a = old_server
b = new_server
collections = ["from a", "from b"]

[storage old_server]
type = "caldav"
url = "https://old-server.example.com/"
username = "alice"
password = "password123"

[storage new_server]
type = "caldav"
url = "https://new-server.example.com/"
username = "alice"
password = "newpassword456"
```

Then run `vdirsyncer sync` to migrate everything.

## Which One Should You Choose?

**Choose Radicale if**: You want the simplest, most lightweight solution. It's the default recommendation for most homelab users. Set it up in five minutes, forget about it, and it just works. The flat file storage makes backups trivial.

**Choose Baïkal if**: You want a web admin interface to manage users and calendars without SSH access. This is ideal for family setups or small teams where a non-technical person needs to create accounts or manage shared calendars. The sabre/dav foundation also means excellent protocol compatibility.

**Choose Xandikos if**: You value version control and audit trails. If you run a shared household calendar or manage contacts for a small business, the ability to see who changed what and revert mistakes is invaluable. The Git integration also means your backup strategy is simply `git push`.

All three are excellent choices. The "best" server depends on your technical comfort level and whether you need a web interface. None of them will disappoint.

## Final Thoughts

Self-hosting your calendar and contacts is one of the highest-impact privacy upgrades you can make for minimal effort. These servers run reliably on hardware as modest as a Raspberry Pi, consume almost no resources, and give you complete ownership of some of your most personal data.

Pair any of these servers with DAVx5 on Android or native CalDAV/CardDAV on iOS/macOS, put them behind a reverse proxy with Let's Encrypt SSL, and you have a fully functional, private alternative to Google Calendar and iCloud Contacts — no subscription fees, no data harvesting, no vendor lock-in.
