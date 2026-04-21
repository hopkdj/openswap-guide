---
title: "Best Self-Hosted RSS Readers 2026: FreshRSS vs Miniflux vs Tiny Tiny RSS"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the top self-hosted RSS feed readers in 2026. Complete setup guides for FreshRSS, Miniflux, and Tiny Tiny RSS with Docker configurations."
---

RSS is not dead. In fact, self-hosted RSS readers are experiencing a renaissance in 2026. As social media algorithms bury content behind paywalls and engagement-driven feeds, a growing number of people are returning to RSS to reclaim control over what they read, when they read it, and who tracks their reading habits.

Self-hosting your RSS reader means no subscription fees, no account lock-in, no data mining, and no surprise shutdowns. Your feeds, your server, your rules. This guide covers the three best open-source, self-hosted RSS readers available today and walks you through deploying each one with [docker](https://www.docker.com/).

## Why Self-Host Your RSS Reader in 2026

The case for self-hosting an RSS reader comes down to four pillars: **privacy, permanence, control, and cost**.

**Privacy**: Cloud-based RSS services (Feedly, Inoreader, NewsBlur) track what you read, how long you spend on each article, and which topics interest you most. That data is valuable — and it's not yours. A self-hosted reader keeps every interaction on your own server.

**Permanence**: Google killed Google Reader in 2013. Newsblur has had downtime. Inoreader has repeatedly changed its free tier. When you self-host, the service lives as long as your server runs. No corporate decisions can take it away.

**Control**: You decide the update frequency, the retention period, the filters, and the integrations. Want to keep every article for five years? Configure it. Want to filter out clickbait domains at the feed level? Done.

**Cost**: Every self-hosted RSS reader in this guide is free and open source. Your only cost is the server — which can be a $5/month VPS, a Raspberry Pi at home, or even the same machine running your other self-hosted services.

## Quick Comparison Table

| Feature | FreshRSS | Miniflux | Tiny Tiny RSS |
|---|---|---|---|
| **Language** | PHP | Go | PHP |
| **Database** | SQLite / MySQL / PostgreSQL | PostgreSQL only | PostgreSQL only |
| **Resource Usage** | Low (50–150 MB RAM) | Ultra-low (10–30 MB RAM) | Moderate (100–250 MB RAM) |
| **Web UI** | Full-featured, modern | Minimalist, keyboard-driven | Feature-rich, customizable |
| **Mobile Apps** | Fever API (works with Reeder, NetNewsWire) | Native Miniflux apps (iOS/Android) | API (multiple third-party apps) |
| **Extensions** | Yes (plugin system) | No (intentionally minimal) | Yes (plugin system) |
| **OPML Import/Export** | Yes | Yes | Yes |
| **Multi-User** | Yes | Yes | Yes |
| **Docker Support** | Excellent | Excellent (single binary) | Excellent |
| **Best For** | Most users, feature-rich experience | Minimalists, low-resource servers | Power users who want deep customization |

---

## 1. FreshRSS — The Best All-Around Self-Hosted RSS Reader

FreshRSS is the most popular open-source RSS reader for good reason. It offers a polished web interface, supports multiple databases, has a robust extension system, and exposes Fever and Google Reader APIs so you can use your favorite mobile app to read feeds on the go.

### Why Choose FreshRSS

FreshRSS strikes the best balance between features and simplicity. It supports categories, tags, filters, and custom CSS themes. The extension system lets you add functionality like article deduplication, automatic archiving rules, and integration with external services. Its Fever API compatibility means you can use Reeder on iOS, Readably on Android, or any Fever-compatible client.

### Docker Installation

FreshRSS runs on PHP and supports SQLite for single-user setups or PostgreSQL/MySQL for multi-user deployments. Here's a production-ready Docker Compose configuration using PostgreSQL:

```yaml
version: "3.8"

services:
  freshrss-db:
    image: postgres:16-alpine
    container_name: freshrss-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: freshrss
      POSTGRES_USER: freshrss
      POSTGRES_PASSWORD: your_secure_password_here
    volumes:
      - freshrss_data:/var/lib/postgresql/data
    networks:
      - freshrss-net

  freshrss:
    image: freshrss/freshrss:latest
    container_name: freshrss
    restart: unless-stopped
    environment:
      CRON_MIN: "3,33"
      TZ: "UTC"
    volumes:
      - freshrss_config:/var/www/FreshRSS/data
      - freshrss_extensions:/var/www/FreshRSS/extensions
    ports:
      - "8080:80"
    depends_on:
      - freshrss-db
    networks:
      - freshrss-net

volumes:
  freshrss_data:
  freshrss_config:
  freshrss_extensions:

networks:
  freshrss-net:
    driver: bridge
```

Save this as `docker-compose.yml` and deploy:

```bash
mkdir -p freshrss && cd freshrss
# Create the docker-compose.yml file above
docker compose up -d
```

After the containers start, open `http://your-server-ip:8080` and complete the setup wizard. Select PostgreSQL as your database, use `freshrss-db` as the host, and enter the credentials from the compose file.

### Setting Up Feed Refresh

FreshRSS uses a cron mechanism to refresh feeds. The `CRON_MIN: "3,33"` setting tells it to check for new articles at 3 and 33 minutes past every hour. For more frequent updates, adjust this value:

```bash
# Check every 15 minutes (at 0, 15, 30, 45)
CRON_MIN: "*/15"
```

You can also trigger a manual refresh from the web UI by clicking the **Update** button, or via the CLI:

```bash
docker exec freshrss ./cli/actualize --user your_username
```

### Enabling the Fever API for Mobile Access

One of FreshRSS's strongest features is Fever API compatibility. To enable it:

1. Log into FreshRSS as an administrator
2. Go to **Settings → Authentication**
3. Enable **Allow API access**
4. Set an API password (different from your login password)
5. Note the API endpoint: `https://your-domain.com/api/fever.php`

Now configure Reeder, NetNewsWire, or any Fever-compatible client with that endpoint and API password. Your mobile reader syncs seamlessly with your self-hosted instance.

---

## 2. Miniflux — The Minimalist, Resource-Efficient Choice

Miniflux takes a radically different approach. Written in Go, it compiles to a single binary, uses almost no resources, and has a deliberately minimal interface. There are no themes, no extensions, and no feature creep. What you get is a fast, reliable, keyboard-driven RSS reader that does one thing exceptionally well.

### Why Choose Miniflux

Miniflux is ideal if you value speed and simplicity above all else. The entire application is a single Go binary with no external dependencies beyond PostgreSQL. It starts in under a second, handles thousands of feeds without breaking a sweat, and its API is clean and well-documented. The official mobile apps (iOS and Android) are inexpensive one-time purchases — no subscriptions.

If your server has limited resources (a $5 VPS or a Raspberry Pi), Miniflux is the clear winner. It typically uses 10–30 MB of RAM, compared to 100+ MB for PHP-based alternatives.

### Docker Installation

Miniflux requires PostgreSQL and ships as a single binary. The Docker image is straightforward:

```yaml
version: "3.8"

services:
  miniflux-db:
    image: postgres:16-alpine
    container_name: miniflux-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: miniflux
      POSTGRES_PASSWORD: your_secure_password_here
      POSTGRES_DB: miniflux
    volumes:
      - miniflux_data:/var/lib/postgresql/data
    networks:
      - miniflux-net

  miniflux:
    image: miniflux/miniflux:latest
    container_name: miniflux
    restart: unless-stopped
    environment:
      DATABASE_URL: "postgres://miniflux:your_secure_password_here@miniflux-db/miniflux?sslmode=disable"
      RUN_MIGRATIONS: "1"
      CREATE_ADMIN: "1"
      ADMIN_USERNAME: "admin"
      ADMIN_PASSWORD: "your_admin_password_here"
      BASE_URL: "https://rss.your-domain.com"
      CERTIFICATE_FILE: "/etc/ssl/certs/cert.pem"
      KEY_FILE: "/etc/ssl/private/key.pem"
      LISTEN_ADDR: "0.0.0.0:8080"
    ports:
      - "8081:8080"
    depends_on:
      - miniflux-db
    networks:
      - miniflux-net

volumes:
  miniflux_data:

networks:
  miniflux-net:
    driver: bridge
```

Deploy it:

```bash
mkdir -p miniflux && cd miniflux
docker compose up -d
```

Miniflux automatically runs database migrations on startup thanks to `RUN_MIGRATIONS: "1"`. The admin user is created on first run — change the default password immediately.

### Configuration Tips

Miniflux uses environment variables for all configuration. Here are the most useful settings:

```yaml
environment:
  # How often to refresh feeds (in minutes)
  POLLING_FREQUENCY: "30"
  
  # How many concurrent fetchers to use
  WORKER_POOL_SIZE: "5"
  
  # Number of days to keep read articles
  PURGE_ARCHIVE_DAYS: "90"
  
  # Enable bookmarklet for adding feeds from the browser
  BOOKMARKLET: "1"
  
  # OAuth2 integration (optional — supports Google, OpenID Connect)
  OAUTH2_USER_CREATION: "1"
```

### Using the API and Native Apps

Miniflux has a RESTful API that covers every feature. You can manage feeds, articles, categories, and users programmatically:

```bash
# Get all feeds
curl -u "admin:your_admin_password_here" \
  "https://rss.your-domain.com/v1/feeds"

# Add a new feed
curl -u "admin:your_admin_password_here" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://rss.your-domain.com/v1/feeds" \
  -d '{"feed_url": "https://hnrss.org/newest"}'

# Get unread articles count
curl -u "admin:your_admin_password_here" \
  "https://rss.your-domain.com/v1/counts"
```

The official mobile apps connect directly to your Miniflux instance. On iOS, search for "Miniflux" in the App Store. On Android, it's available on Google Play and F-Droid. Both are one-time purchases with no recurring fees.

---

## 3. Tiny Tiny RSS (tt-rss) — The Power User's Choice

Tiny Tiny RSS (often abbreviated as tt-rss) is the veteran of self-hosted RSS readers. It has been around since 2005 and offers the deepest feature set of any option on this list. If you want granular control over every aspect of your reading experience — custom filters, label-based organization, article scoring, and extensive plugin support — tt-rss delivers.

### Why Choose Tiny Tiny RSS

tt-rss is for users who want maximum control. Its plugin system is mature and includes plugins for全文 fetching, YouTube channel tracking, IRC/XMPP notifications, and integration with read-it-later services. The article scoring system lets you prioritize important feeds and deprioritize noisy ones. The label system provides an alternative to traditional folder organization.

The trade-off is com[plex](https://www.plex.tv/)ity. tt-rss has more configuration options than most people need, and its interface, while functional, feels dated compared to FreshRSS. But if you're willing to invest time in configuration, tt-rss is the most capable self-hosted RSS reader available.

### Docker Installation

tt-rss requires PostgreSQL and uses a two-container setup (application + updater):

```yaml
version: "3.8"

services:
  ttrss-db:
    image: postgres:16-alpine
    container_name: ttrss-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ttrss
      POSTGRES_PASSWORD: your_secure_password_here
      POSTGRES_DB: ttrss
    volumes:
      - ttrss_data:/var/lib/postgresql/data
    networks:
      - ttrss-net

  ttrss:
    image: cthulhoo/ttrss-web:latest
    container_name: ttrss
    restart: unless-stopped
    environment:
      SELF_URL_PATH: "https://ttrss.your-domain.com"
      DB_HOST: "ttrss-db"
      DB_PORT: "5432"
      DB_NAME: "ttrss"
      DB_USER: "ttrss"
      DB_PASS: "your_secure_password_here"
      TTRSS_PLUGINS: "auth_internal, af_readability, af_comics, af_redditimgur, note, toggle_markread"
      PUID: "1000"
      PGID: "1000"
    volumes:
      - ttrss_config:/config
      - ttrss_feed_icons:/var/www/feed-icons
    ports:
      - "8082:80"
    depends_on:
      - ttrss-db
    networks:
      - ttrss-net

  ttrss-updater:
    image: cthulhoo/ttrss-web:latest
    container_name: ttrss-updater
    restart: unless-stopped
    environment:
      DB_HOST: "ttrss-db"
      DB_PORT: "5432"
      DB_NAME: "ttrss"
      DB_USER: "ttrss"
      DB_PASS: "your_secure_password_here"
      TTRSS_PLUGINS: "auth_internal"
    command: update_daemon2.php
    depends_on:
      - ttrss-db
    networks:
      - ttrss-net

volumes:
  ttrss_data:
  ttrss_config:
  ttrss_feed_icons:

networks:
  ttrss-net:
    driver: bridge
```

Deploy:

```bash
mkdir -p ttrss && cd ttrss
docker compose up -d
```

The default login is `admin` / `password` — change it immediately under **Preferences → Authentication**.

### Key Features Worth Configuring

**Article Filters**: tt-rss lets you create rules that automatically label, star, publish, or score articles based on title, author, or feed content. Go to **Actions → Edit Filters** to create rules like:

- Filter out articles with "sponsored" in the title (assign score -100)
- Star all articles from specific feeds
- Auto-label security-related articles

**Readability Mode**: Enable the `af_readability` plugin (included in the compose file above) to fetch the full article text from websites that only provide excerpts. This transforms partial feeds into complete reading experiences without leaving your reader.

**Feed Categories and Labels**: Unlike simple folder-based organization, tt-rss supports both hierarchical categories and free-form labels. Use categories for broad grouping (Tech, News, Blogs) and labels for cross-cutting concerns (Read Later, Important, Reference).

---

## Securing Your RSS Reader with a Reverse Proxy

Regardless of which reader you choose, you should put it behind a reverse proxy with HTTPS. Here's a Caddy configuration that handles TLS automatically:

```caddy
rss.your-domain.com {
    reverse_proxy localhost:8080
    encode gzip
    log {
        outpu[nginx](https://nginx.org/)e /var/log/caddy/rss.log
    }
}
```

Or with Nginx and Let's Encrypt:

```nginx
server {
    listen 443 ssl http2;
    server_name rss.your-domain.com;

    ssl_certificate /etc/letsencrypt/live/rss.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rss.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Migrating from Cloud-Based RSS Services

All three readers support OPML import/export, making migration straightforward:

1. **Export from your current service**: Most cloud RSS readers have an "Export OPML" option in settings. Download the `.opml` file.
2. **Import to your self-hosted reader**:
   - **FreshRSS**: Settings → Manage feeds → Import OPML
   - **Miniflux**: Settings → Import → Upload OPML file
   - **tt-rss**: Preferences → Feeds → OPML → Import my OPML
3. **Wait for the first refresh**: After import, your reader will begin fetching feeds on its next scheduled update. You can trigger a manual refresh to speed this up.

## Which Should You Choose?

The decision comes down to your priorities:

- **Choose FreshRSS** if you want the best balance of features, usability, and mobile app support. It's the safest recommendation for most users. The extension system means you can add functionality as you need it.

- **Choose Miniflux** if you run on limited hardware, prefer keyboard navigation, or want a reader that "just works" with minimal configuration. Its single-binary architecture makes it the easiest to deploy and maintain.

- **Choose Tiny Tiny RSS** if you're a power user who wants deep customization, article scoring, advanced filtering, and the most mature plugin ecosystem. The configuration overhead is real, but the payoff is a reader that adapts to your exact workflow.

All three are excellent, actively maintained, and free. You can't make a wrong choice — the best RSS reader is the one you actually use every day.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
