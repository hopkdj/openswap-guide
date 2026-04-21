---
title: "Shlink vs Kutt vs YOURLS: Best Self-Hosted URL Shortener 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare the top self-hosted URL shorteners in 2026: Shlink, Kutt, and YOURLS. Complete Docker deployment guides, feature comparison, and API walkthroughs for running your own Bitly alternative."
---

## Why Self-Host Your URL Shortener?

Commercial link shorteners like Bitly, Rebrandly, and TinyURL control your redirects, harvest your click data, and can shut down your links at any time. For developers, marketers, and anyone who cares about their digital footprint, self-hosting a URL shortener makes practical sense:

- **Full Data Ownership**: Every click, referrer, and geographic insight stays on your server. No third-party analytics harvesting your audience data.
- **Custom Domains Without Limits**: Use as many branded domains as you want without paying per-domain enterprise fees.
- **No Link Rot Risk**: Commercial services can delete your links, change pricing, or go out of business. Your self-hosted instance persists as long as your server runs.
- **API Control**: Programmatic link creation with no rate limits or API tier restrictions.
- **Privacy**: No tracking pixels injected into your redirects. No selling click data to advertisers.
- **Cost**: Free forever after initial server setup, compared to $35–$500+/month for commercial plans with comparable features.

Whether you need branded short links for marketing campaigns, internal redirect management, or a personal link collection, the self-hosted options in 2026 are mature, well-documented, and ready for production use.

## Quick Comparison Table

| Feature | **Shlink** | **Kutt** | **YOURLS** |
|---------|-----------|--------|------------|
| **Language** | PHP (Swoole/ReactPHP) | Node.js | PHP |
| **License** | MIT | MIT | MIT |
| **Database** | PostgreSQL, MySQL, MariaDB, SQLite | PostgreSQL, SQLite | MySQL, MariaDB |
| **[docker](https://www.docker.com/) Image Size** | ~120 MB | ~180 MB | ~90 MB |
| **Min RAM** | 256 MB | 512 MB | 128 MB |
| **Web UI** | ✅ (separate image) | ✅ (built-in) | ✅ (built-in) |
| **REST API** | ✅ Full | ✅ Full | ✅ Plugin-based |
| **CLI** | ✅ Official | ❌ No | ❌ No |
| **Bulk Import** | ✅ CSV | ✅ CSV | ✅ CSV/Plugin |
| **Custom Domains** | ✅ Unlimited | ✅ Unlimited | ✅ Plugin |
| **Link Expiration** | ✅ Time + Visit-based | ✅ Time-based | ⚠️ Plugin only |
| **QR Code Generation** | ✅ Built-in | ✅ Built-in | ⚠️ Plugin only |
| **Password Protection** | ✅ Yes | ✅ Yes | ⚠️ Plugin only |
| **Geo-targeted Redirects** | ✅ Yes | ❌ No | ⚠️ Plugin only |
| **2FA Support** | ❌ No | ✅ Yes | ⚠️ Plugin only |
| **Active Development** | ✅ Very Active | ⚠️ Slower | ✅ Steady |
| **GitHub Stars** | 3,200+ | 5,800+ | 10,500+ |

## 1. Shlink — The API-First Powerhouse

[Shlink](https://shlink.io) is the most feature-rich option in this comparison. Built on PHP with an async runtime, it provides a comprehensive REST API, a standalone web client, a CLI tool, and integrations with virtually every workflow you can imagine. It's the choice for teams and developers who need programmatic control.

### Key Features

- **Advanced Analytics**: Visit tracking with referrer, country, city, browser, OS, and device type. All data exportable via API.
- **Geo-Targeted Redirects**: Send users to different destination URLs based on their geographic location — perfect for region-specific campaigns.
- **Link Expiration**: Set links to expire after a specific date, a number of visits, or both.
- **Short Code Generation**: Multiple strategies — sequential, random, OAuth-based, or custom slugs.
- **Tagging System**: Organize links with tags and filter analytics by tag groups.
- **Non-Validating Mode**: Allow creation of short URLs for destinations that don't exist yet (useful for pre-launch campaigns).

### Docker Deployment

Shlink requires a database and optionally a web client. Here's a complete production-ready setup with PostgreSQL:

```yaml
# docker-compose.yml
services:
  shlink-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: shlink
      POSTGRES_USER: shlink
      POSTGRES_PASSWORD: ${DB_PASSWORD:-SecureP@ss2026}
    volumes:
      - shlink-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shlink"]
      interval: 10s
      timeout: 5s
      retries: 5

  shlink:
    image: shlinkio/shlink:stable
    restart: unless-stopped
    depends_on:
      shlink-db:
        condition: service_healthy
    environment:
      DEFAULT_DOMAIN: links.example.com
      IS_HTTPS_ENABLED: "true"
      GEOLITE_LICENSE_KEY: ${GEOLITE_KEY}
      DB_DRIVER: postgres
      DB_HOST: shlink-db
      DB_NAME: shlink
      DB_USER: shlink
      DB_PASSWORD: ${DB_PASSWORD:-SecureP@ss2026}
      INITIAL_API_KEY: ${SHLINK_API_KEY:-your-secret-api-key}
      INITIAL_SHORT_CODES_LENGTH: 6
      REDIRECT_STATUS_CODE: 302
      REDIRECT_CACHE_LIFETIME: 30
      ANONYMIZE_REMOTE_ADDR: "false"
      DISABLE_TRACK_PARAM: no-track
      INVALID_SHORT_URL_REDIRECT_TO: https://example.com/404
      REGULAR_404_REDIRECT_TO: https://example.com
      BASE_URL_REDIRECT_TO: https://example.com
    ports:
      - "8080:8080"

  shlink-web:
    image: shlinkio/shlink-web-client:latest
    restart: unless-stopped
    environment:
      SHLINK_SERVER_URL: https://links.example.com
    ports:
      - "3000:8080"

volumes:
  shlink-db-data:
```

```bash
# Create environment file
cat > .env << 'EOF'
DB_PASSWORD=SecureP@ss2026
SHLINK_API_KEY=sk_prod_a1b2c3d4e5f6g7h8i9j0
GEOLITE_KEY=your_maxmind_geolite_key
EOF

# Launch
docker compose up -d

# Verify
curl -s http://localhost:8080/rest/v3/short-urls \
  -H "X-Api-Key: sk_prod_a1b2c3d4e5f6g7h8i9j0" | jq .
```

### Using the CLI

Shlink ships with an excellent CLI tool for link management:

```bash
# Generate a new short URL
docker compose exec shlink bin/cli short-url:generate https://example.com/long-page --tags marketing,campaign

# List all short URLs
docker compose exec shlink bin/cli short-url:list

# View analytics for a specific short code
docker compose exec shlink bin/cli short-url:visits abc123

# Import links from CSV
docker compose exec shlink bin/cli import:links links.csv
```

### API Example: Creating Links Programmatically

```bash
# Create a short URL with expiration and geo-targeting
curl -X POST https://links.example.com/rest/v3/short-urls \
  -H "X-Api-Key: sk_prod_a1b2c3d4e5f6g7h8i9j0" \
  -H "Content-Type: application/json" \
  -d '{
    "longUrl": "https://example.com/product-launch",
    "customSlug": "launch",
    "maxVisits": 1000,
    "validSince": "2026-04-12T00:00:00+00:00",
    "validUntil": "2026-05-12T23:59:59+00:00",
    "tags": ["marketing", "q2-2026"],
    "title": "Q2 Product Launch Page",
    "domain": "links.example.com",
    "forwardQuery": true,
    "geoRedirects": [
      {"countryCode": "US", "longUrl": "https://example.com/us"},
      {"countryCode": "GB", "longUrl": "https://example.com/uk"}
    ]
  }'
```

---

## 2. Kutt — The Modern Minimalist

[Kutt](https://kutt.it) is a Node.js-based URL shortener with a beautiful built-in web interface, user registration, and two-factor authentication. It prioritizes simplicity and user experience over raw feature count, making it the best choice for individuals and small teams who want a polished, out-of-the-box experience.

### Key Features

- **User Accounts**: Registration with email verification and optional 2FA via TOTP.
- **Built-in Web UI**: No separate web client needed — the interface is part of the same container.
- **Link Protection**: Password-protected short URLs for private sharing.
- **Batch Operations**: Create, edit, and delete multiple links at once.
- **Admin Dashboard**: Manage all users, links, and domains from a single interface.
- **Clean Analytics**: Visit count, referrer, and browser/OS breakdowns without overwhelming detail.

### Docker Deployment

Kutt requires a database (PostgreSQL or SQLite) and Redis for caching. Here's a production setup:

```yaml
# docker-compose.yml
services:
  kutt-db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: kutt
      POSTGRES_USER: kutt
      POSTGRES_PASSWORD: ${DB_PASSWORD:-KuttS3cur3!}
    volumes:
      - kutt-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kutt"]
      interval: 10s
      timeout: 5s
      retries: 5

  kutt-redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD:-RedisP@ss2026}
    volumes:
      - kutt-redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-RedisP@ss2026}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  kutt:
    image: kutt/kutt:latest
    restart: unless-stopped
    depends_on:
      kutt-db:
        condition: service_healthy
      kutt-redis:
        condition: service_healthy
    environment:
      DEFAULT_DOMAIN: links.example.com
      SITE_NAME: "OpenSwap Links"
      ADMIN_EMAILS: admin@example.com
      DB_DRIVER: pg
      DB_HOST: kutt-db
      DB_PORT: 5432
      DB_NAME: kutt
      DB_USER: kutt
      DB_PASSWORD: ${DB_PASSWORD:-KuttS3cur3!}
      REDIS_ENABLED: "true"
      REDIS_HOST: kutt-redis
      REDIS_PORT: 6379
      REDIS_PASSWORD: ${REDIS_PASSWORD:-RedisP@ss2026}
      JWT_SECRET: ${JWT_SECRET:-jwt-super-secret-key-change-this}
      MAIL_ENABLED: "true"
      MAIL_HOST: smtp.example.com
      MAIL_PORT: 587
      MAIL_SECURE: "false"
      MAIL_USER: noreply@example.com
      MAIL_PASSWORD: ${MAIL_PASSWORD:-EmailP@ss2026}
      DISALLOW_REGISTRATION: "false"
      DISALLOW_ANONYMOUS_LINKS: "true"
    ports:
      - "3000:3000"

volumes:
  kutt-db-data:
  kutt-redis-data:
```

```bash
# Deploy
cat > .env << 'EOF'
DB_PASSWORD=KuttS3cur3!
REDIS_PASSWORD=RedisP@ss2026
JWT_SECRET=jwt-super-secret-key-change-this-in-production
MAIL_PASSWORD=EmailP@ss2026
EOF

docker compose up -d

# Check status
docker compose ps
```

### Setting Up Your First Admin Account

Kutt uses an `ADMIN_EMAILS` environment variable to grant admin privileges. After deployment:

```bash
# Register as admin
curl -X POST http://localhost:3000/api/v2/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "AdminStr0ng!"
  }'

# Login and get JWT token
curl -X POST http://localhost:3000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "AdminStr0ng!"
  }' | jq .token
```

### API Example

```bash
# Create a short link
TOKEN=$(curl -s -X POST http://localhost:3000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminStr0ng!"}' | jq -r .token)

curl -X POST http://localhost:3000/api/v2/links \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "https://example.com/blog/self-hosting-guide",
    "description": "Self-hosting guide blog post",
    "expire_in": "30 days"
  }'
```

---

## 3. YOURLS — The Battle-Tested Veteran

[YOURLS](https://yourls.org) (Your Own URL Shortener) has been around since 2009 and is the most mature project in this comparison. Written in PHP with a plugin architecture, it powers millions of short links and has the largest ecosystem of community extensions. It's the choice if you want stability, a massive plugin library, and WordPress-like extensibility.

### Key Features

- **Plugin Ecosystem**: 100+ community plugins for everything from spam protection to API enhancements.
- **WordPress Integration**: Dedicated plugins for creating short links directly from the WordPress editor.
- **Bookmarklet**: Browser bookmarklet to instantly shorten the current page URL.
- **Sample Pages**: Built-in API documentation and stats pages for each link.
- **CORS Support**: Cross-origin resource sharing for frontend applications.
- **Massive Community**: Over a decade of development, extensive documentation, and active forums.

### Docker Deployment

YOURLS is the simplest to deploy — it only needs a MySQL/MariaDB database and the PHP application itself:

```yaml
# docker-compose.yml
services:
  yourls-db:
    image: mariadb:11
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:-R00tP@ss!}
      MYSQL_DATABASE: yourls
      MYSQL_USER: yourls
      MYSQL_PASSWORD: ${DB_PASSWORD:-YourlS2026!}
    volumes:
      - yourls-db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5

  yourls:
    image: yourls:latest
    restart: unless-stopped
    depends_on:
      yourls-db:
        condition: service_healthy
    environment:
      YOURLS_DB_HOST: yourls-db
      YOURLS_DB_USER: yourls
      YOURLS_DB_PASS: ${DB_PASSWORD:-YourlS2026!}
      YOURLS_DB_NAME: yourls
      YOURLS_SITE: https://links.example.com
      YOURLS_USER: admin
      YOURLS_PASS: ${YOURLS_PASSWORD:-Adm1nStr0ng!}
      YOURLS_DEBUG: "false"
      YOURLS_UNIQUE_URLS: "true"
      YOURLS_PRIVATE: "true"
      YOURLS_COOKIEKEY: "random-salt-key-change-this-now"
    ports:
      - "8080:80"
    volumes:
      - yourls-plugins:/var/www/html/user/plugins

volumes:
  yourls-db-data:
  yourls-plugins:
```

```bash
# Deploy
cat > .env << 'EOF'
DB_ROOT_PASSWORD=R00tP@ss!
DB_PASSWORD=YourlS2026!
YOURLS_PASSWORD=Adm1nStr0ng!
EOF

docker compose up -d

# Visit http://localhost:8080/admin/install.php to initialize the database
# Then log in at http://localhost:8080/admin/
```

### Installing Plugins

YOURLS shines with its plugin ecosystem. Here's how to add essential plugins:

```bash
# Install the JSON API plugin (enables REST API)
docker compose exec yourls \
  git clone https://github.com/YOURLS/YOURLS-API.git /var/www/html/user/plugins/api

# Install QR code generation
docker compose exec yourls \
  git clone https://github.com/tomslade/yourls-qrcode.git /var/www/html/user/plugins/qrcode

# Install password protection
docker compose exec yourls \
  git clone https://github.com/tomslade/yourls-password.git /var/www/html/user/plugins/password

# Activate plugins via the admin interface, or edit user/config.php:
# $yourls_plugins_active = ['api', 'qrcode', 'password'];
```

### API Usage with JSON API Plugin

```bash
# Create a short URL
curl "http://localhost:8080/yourls-api.php" \
  -d "signature=admin&format=json&action=shorturl&url=https://example.com/page"

# Get statistics
curl "http://localhost:8080/yourls-api.php" \
  -d "signature=admin&format=json&action=stats"

# Expand a short URL
curl "http://localhost:8080/yourls-api.php" \
  -d "signature=admin&format=json&action=expand&shorturl=abc123"
```

---

## Head-to-Head: Which One Should You Choose?

### Best for Developers and Teams: **Shlink**

If you need a URL shortener with a comprehensive API, CLI access, geo-targeted redirects, link expiration rules, and QR code generation out of the box, Shlink is the clear winner. Its separation of concerns (API server + web client) means you can integrate it into any workflow — CI/CD pipelines, marketing automation, developer tooling — without being tied to a specific UI.

### Best for Individuals and Small Teams: **Kutt**

If you want a beautiful, zero-config web interface with user accounts, 2FA, and clean analytics, Kutt delivers the best user experience. The fact that the web UI and API are in the same container makes deployment simpler, and the admin dashboard is genuinely pleasant to use. The trade-off is fewer advanced features — no geo-targeting, no visit-based expiration.

### Best for WordPress Users and Plugin Lovers: **YOURLS**

If you run a WordPress site, YOURLS integration is unmatched. The plugin ecosystem means you can add virtually any feature — spam filters, social sharing buttons, custom short code patterns, advanced analytics — without touching code. The older codebase means it's incredibly stable, but also that some features require hunting for and installing third-party plugins rather than working out of the box.

## Resource Requirements Comparison

| Metric | Shlink | Kutt | YOURLS |
|--------|--------|------|--------|
| **Docker Images** | 2-3 (app + web + db) | 3 (app + redis + db) | 2 (app + db) |
| **Disk (fresh install)** | ~200 MB | ~300 MB | ~150 MB |
| **RAM (idle)** | ~256 MB | ~512 MB | ~128 MB |
| **RAM (under load)** | ~512 MB | ~768 MB | ~256 MB |
| **CPU** | Low | Low-Medium | Very Low |
| **Backup Com[plex](https://www.plex.tv/)ity** | Low (dump DB) | Medium (dump DB + Redis) | Low (dump DB) |
| **Scaling** | Horizontal (stateless API) | Horizontal (stateless app) | Vertical (monolithic) |

## Reverse Proxy Setup (All Three)

Regardless of which option you choos[caddy](https://caddyserver.com/)u'll want a reverse proxy for HTTPS. Here's a Caddy configuration that works for all three:

```caddyfile
# Caddyfile
links.example.com {
    reverse_proxy localhost:8080  # Change port per service:
                                  # Shlink: 8080
                                  # Kutt: 3000
                                  # YOURLS: 8080

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }

    encode gzip zstd
    log {
        output file /var/log/caddy/links.log
    }
}
```

Or if you're using Traefik with Docker labels:

```yaml
  shlink:
    image: shlinkio/shlink:stable
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.shlink.rule=Host(`links.example.com`)"
      - "traefik.http.routers.shlink.entrypoints=websecure"
      - "traefik.http.routers.shlink.tls=true"
      - "traefik.http.routers.shlink.tls.certresolver=letsencrypt"
      - "traefik.http.services.shlink.loadbalancer.server.port=8080"
```

## Migration from Bitly

If you're moving from Bitly, here's how to preserve your existing links:

```bash
# 1. Export your Bitly links via their API
curl -H "Authorization: Bearer BITLY_ACCESS_TOKEN" \
  "https://api-ssl.bitly.com/v4/groups/GROUP_GUID/bitlinks?size=100" \
  | jq -r '.bitlinks[] | [.link, .long_url] | @csv' > bitly-export.csv

# 2. Transform for Shlink import
awk -F',' '{print $2","$1}' bitly-export.csv > shlink-import.csv

# 3. Import into Shlink
docker compose exec shlink bin/cli import:links /data/shlink-import.csv

# For YOURLS, use the Bulk Shortener plugin:
# Upload the CSV through the admin panel after installing the plugin
```

## Monitoring and Maintenance

Set up health checks to ensure your shortener stays reliable:

```bash
# Simple uptime monitoring with curl
while true; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://links.example.com/rest/v3/health)
  if [ "$STATUS" != "200" ]; then
    echo "$(date): Health check failed (HTTP $STATUS)" | \
      mail -s "URL Shortener Down" admin@example.com
  fi
  sleep 60
done
```

For database backups, a simple cron job handles everything:

```bash
# Add to crontab: 0 2 * * * /opt/scripts/backup-url-shortener.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec -T shlink-db pg_dump -U shlink shlink | \
  gzip > /backups/shlink-db-${DATE}.sql.gz
# Keep last 30 days
find /backups -name "shlink-db-*.sql.gz" -mtime +30 -delete
```

## Final Verdict

All three options are production-ready and will serve you well. Your choice comes down to workflow preferences:

- **Shlink** if you want the most features and best API — it's the Swiss Army knife of URL shorteners.
- **Kutt** if you want the best UI and simplest setup — it looks and feels like a modern SaaS product.
- **YOURLS** if you want maximum extensibility and WordPress integration — the plugin ecosystem is unmatched.

The common thread is that all three give you what commercial services can't: complete ownership of your link data, zero per-link costs, and the freedom to run on whatever infrastructure you choose. Once deployed behind a reverse proxy with HTTPS, any of these will reliably serve millions of redirects with minimal maintenance.

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
