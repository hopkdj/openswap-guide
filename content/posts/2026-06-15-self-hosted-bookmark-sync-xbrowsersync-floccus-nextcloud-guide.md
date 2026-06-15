---
title: "Self-Hosted Bookmark Sync Platforms: xBrowserSync vs Floccus vs Nextcloud Bookmarks"
date: "2026-06-15"
tags: ["bookmarks", "sync", "browser", "nextcloud", "privacy", "self-hosted"]
draft: false
---

Browser bookmarks are the digital equivalent of sticky notes — essential but messy. When you use multiple browsers across different devices, keeping bookmarks synchronized becomes a genuine challenge. While Chrome Sync and Firefox Sync are convenient, they send your browsing habits to Google and Mozilla respectively. Self-hosted bookmark sync gives you the same cross-device convenience with complete privacy control.

In this guide, we compare three leading self-hosted bookmark synchronization solutions: **xBrowserSync** (856 stars), **Floccus** (8,123 stars), and **Nextcloud Bookmarks** (1,186 stars).

## Why Self-Host Your Bookmark Sync?

Your bookmarks reveal a lot about you — your interests, work projects, financial accounts, health concerns, and private research topics. Syncing them through a corporate cloud means trusting that company with a detailed map of your online life. Self-hosting keeps this intimate data under your own control, on your own infrastructure.

Beyond privacy, self-hosting gives you platform independence. Chrome Sync only works with Chrome, and Firefox Sync only works with Firefox. Self-hosted solutions bridge browser ecosystems — sync bookmarks between Firefox on your desktop and Chrome on your phone, or between any combination of browsers you use across work and personal devices.

For teams and families, self-hosted bookmark sync enables shared bookmark collections without paying for enterprise plans. Create a shared "team resources" folder that everyone can access, or maintain separate personal collections with a single self-hosted backend. No per-user licensing fees, no vendor lock-in.

For more on self-hosted bookmark management and read-later workflows, see our [bookmark manager comparison](../self-hosted-bookmark-managers-linkding-shaarli-wallabag/) and [read-it-later tools guide](../linkwarden-vs-wallabag-vs-shaarli-self-hosted-read-later-tools-guide-2026/).

## Feature Comparison

| Feature | xBrowserSync | Floccus | Nextcloud Bookmarks |
|---------|-------------|---------|-------------------|
| Stars | 856 | 8,123 | 1,186 |
| Language | TypeScript | JavaScript | JavaScript |
| Architecture | Server + Browser Extension | Browser Extension + Multiple Backends | Nextcloud App |
| Backend Options | xBrowserSync API only | Nextcloud, WebDAV, Google Drive, Git, local file | Nextcloud only |
| Encryption | AES-256-GCM (zero-knowledge) | None (relies on backend) | Via HTTPS transport |
| Browsers | Chrome, Firefox, Edge | Chrome, Firefox, Edge, Opera, Brave | Via Floccus or Nextcloud mobile |
| Folder Support | Yes | Yes | Yes |
| Tags | No | No | Yes |
| Sharing | No | Limited (via shared backend) | Yes (Nextcloud shares) |
| Docker Support | Requires MongoDB | N/A (extension) | Via Nextcloud Docker |
| Mobile Access | No native app | Via Kiwi Browser (Android) | Nextcloud mobile apps |
| Last Updated | Mar 2026 | Jun 2026 | Jun 2026 |

## xBrowserSync: Purpose-Built Privacy

xBrowserSync is the most focused solution — it does one thing (bookmark sync) and does it with strong encryption. Bookmarks are encrypted with AES-256-GCM before they leave your browser, meaning even if someone compromises your server, they cannot read your bookmarks without your passphrase. This zero-knowledge architecture is the gold standard for privacy.

**Key Strengths:**
- Zero-knowledge encryption: bookmarks encrypted client-side before sync
- Dedicated server API purpose-built for bookmark sync
- Lightweight and focused — no feature bloat
- Open-source server component you fully control
- Cross-browser support via native browser extensions

**Self-Hosting xBrowserSync API:**

```yaml
# docker-compose.yml for xBrowserSync
version: "3.8"
services:
  xbrowsersync-api:
    image: node:20-alpine
    container_name: xbrowsersync
    working_dir: /app
    command: sh -c "npm install && npm start"
    ports:
      - "8080:8080"
    volumes:
      - ./xbrowsersync-data:/app/data
      - ./xbrowsersync-settings.json:/app/settings.json:ro
    environment:
      - NODE_ENV=production
    restart: unless-stopped

  mongodb:
    image: mongo:7
    container_name: xbrowsersync-db
    volumes:
      - ./mongodb-data:/data/db
    restart: unless-stopped
```

The xBrowserSync API requires MongoDB as its database backend. Create a `settings.json` configuration file:

```json
{
  "port": 8080,
  "db": {
    "host": "mongodb",
    "port": 27017,
    "name": "xbrowsersync"
  },
  "maxSyncSize": 25600,
  "status": {
    "message": "Self-hosted xBrowserSync"
  }
}
```

After deploying, configure your browser extensions to point to your self-hosted API URL instead of the default public service. In the extension settings, enter your custom server URL (e.g., `https://bookmarks.yourdomain.com`).

## Floccus: The Flexible Aggregator

Floccus takes a fundamentally different approach — instead of providing its own sync server, it's a browser extension that syncs bookmarks TO existing services. It supports Nextcloud, WebDAV, Google Drive, and even local file sync via Git. This makes it incredibly flexible and means you may not need to deploy any new server at all.

**Key Strengths:**
- Works with infrastructure you may already have (Nextcloud, WebDAV)
- Supports multiple sync profiles (personal + work bookmarks)
- Can sync to local files (great for Git-based workflows)
- Active development with frequent updates (last updated June 2026)
- Supports deeply nested folder structures

**Self-Hosting with Nextcloud and Floccus:**

Floccus itself is a browser extension — no server to deploy specifically for Floccus. Instead, you configure a sync backend:

```yaml
# docker-compose.yml for Nextcloud (as Floccus backend)
version: "3.8"
services:
  nextcloud:
    image: nextcloud:28-apache
    container_name: nextcloud-floccus
    ports:
      - "8443:80"
    volumes:
      - ./nextcloud-data:/var/www/html
    environment:
      - NEXTCLOUD_ADMIN_USER=admin
      - NEXTCLOUD_ADMIN_PASSWORD=secure-password-change-me
      - SQLITE_DATABASE=nextcloud
    restart: unless-stopped
```

After setting up Nextcloud, install the Floccus browser extension, add your Nextcloud URL as a sync target, and choose which bookmark folders to sync. Floccus offers three sync strategies:

- **Two-way sync** — Changes merge bidirectionally between browser and server
- **One-way push** — Local bookmarks overwrite server; server changes ignored
- **One-way pull** — Server bookmarks overwrite local; local changes ignored

For a lighter-weight alternative that doesn't require Nextcloud, use a simple WebDAV server:

```yaml
# docker-compose.yml for WebDAV backend
version: "3.8"
services:
  webdav:
    image: bytemark/webdav
    container_name: webdav-floccus
    ports:
      - "8081:80"
    volumes:
      - ./webdav-data:/var/lib/dav
    environment:
      - AUTH_TYPE=Basic
      - USERNAME=floccus
      - PASSWORD=your-secure-password
    restart: unless-stopped
```

WebDAV with Floccus is the most minimal setup possible — a single container providing bookmark sync with no database or complex configuration.

## Nextcloud Bookmarks: The Integrated Solution

If you already run Nextcloud, its built-in Bookmarks app is the most natural choice. It integrates seamlessly with the Nextcloud ecosystem — you can share bookmark folders with other Nextcloud users, access bookmarks via the Nextcloud mobile app, and use the Bookmarks REST API with Floccus for browser sync.

**Key Strengths:**
- Native Nextcloud integration — no separate service to maintain
- Folder sharing with other Nextcloud users
- Tags and full-text search across all bookmarks
- REST API for programmatic access and integration
- Mobile access via Nextcloud iOS and Android apps

**Installing Nextcloud Bookmarks:**

```bash
# SSH into your Nextcloud server or use docker exec:
docker exec -it nextcloud php occ app:enable bookmarks

# Configure automatic link previews
docker exec -it nextcloud php occ config:app:set bookmarks previews --value=true
```

Or install via the Nextcloud web interface: navigate to Apps → Search "Bookmarks" → Download and enable.

The Bookmarks app automatically crawls saved links to generate previews with page titles and descriptions:

```bash
# Run the preview crawler manually
docker exec -it nextcloud php occ bookmarks:preview

# Or set up a cron job
docker exec -it nextcloud php occ bookmarks:crawl
```

## Choosing the Right Solution

**Choose xBrowserSync if:** Privacy is your top concern and you want a dedicated, encrypted bookmark sync that just works. The zero-knowledge encryption is a killer feature — no one but you can read your bookmarks, even if your server is compromised.

**Choose Floccus if:** You already run Nextcloud, ownCloud, or any WebDAV server. Its flexibility is unmatched — you can sync to virtually any storage backend without deploying new infrastructure. It's also the best option for syncing between Chrome and Firefox on desktop, with support for all major browsers.

**Choose Nextcloud Bookmarks if:** You're already invested in the Nextcloud ecosystem and want bookmark management integrated with your existing file sharing, calendar, contacts, and other Nextcloud apps. The native sharing features make it excellent for team use.

## Setting Up HTTPS with Nginx

A production-ready reverse proxy configuration that hosts all three bookmark solutions:

```nginx
server {
    listen 443 ssl http2;
    server_name bookmarks.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/bookmarks.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bookmarks.yourdomain.com/privkey.pem;

    # xBrowserSync API
    location /xbrowsersync/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Nextcloud (for Bookmarks and Floccus backend)
    location / {
        proxy_pass http://127.0.0.1:8443/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 10G;
    }
}
```

Generate your SSL certificate with Certbot:

```bash
certbot certonly --standalone -d bookmarks.yourdomain.com
```

## FAQ

### Is xBrowserSync truly zero-knowledge?

Yes. Encryption and decryption happen entirely in your browser using the Web Crypto API. Your passphrase never leaves your device, and bookmarks are encrypted with AES-256-GCM before being transmitted to the server. The server stores only encrypted blobs that are useless without the decryption key that only your browser holds.

### Can I use Floccus without any server at all?

Yes — Floccus supports local file sync. You can point it to a folder on your computer and sync bookmarks as `.xbel` files. Combine this with Syncthing for peer-to-peer sync or a Git repository for version-controlled bookmark history. This completely eliminates the need for any traditional server.

### What happens if my Nextcloud instance goes down?

With Floccus, your bookmarks remain safely in your browser's local storage. When the server comes back online, sync resumes automatically from where it left off. With Nextcloud Bookmarks accessed directly (without Floccus), you'd temporarily lose access to the web interface, but your local browser bookmarks are completely unaffected.

### Can I import existing bookmarks from Chrome or Firefox?

All three solutions support importing. xBrowserSync and Floccus sync whatever bookmarks already exist in your browser — install the extension and it picks up your current bookmarks automatically. Nextcloud Bookmarks has a web-based import tool supporting HTML bookmark exports from Chrome, Firefox, Safari, and most other browsers.

### Which handles the most bookmarks?

All three can handle thousands of bookmarks without issues. xBrowserSync has a configurable `maxSyncSize` (default 25MB) to prevent abuse. Nextcloud Bookmarks' performance depends on your Nextcloud server's database tuning. Floccus performance depends on the backend — Nextcloud handles large sets well, while WebDAV may be noticeably slower with 5000+ items.

### Can I self-host this on a Raspberry Pi?

Yes — all three solutions run well on a Raspberry Pi 4 with 2GB+ RAM. Nextcloud is the heaviest component in the stack. If using Floccus with a lightweight WebDAV backend, or xBrowserSync standalone, even a Raspberry Pi Zero 2 W has sufficient resources for personal bookmark sync serving a handful of devices.


<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Bookmark Sync Platforms: xBrowserSync vs Floccus vs Nextcloud Bookmarks",
  "description": "Compare three self-hosted bookmark synchronization solutions: xBrowserSync (zero-knowledge encryption), Floccus (multi-backend flexibility), and Nextcloud Bookmarks (integrated ecosystem).",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
  },
  "about": {
    "@type": "Thing",
    "name": "Self-Hosted Bookmark Sync Platforms: xBrowserSync vs Floccus vs Nextcloud Bookmarks"
  },
  "proficiencyLevel": "Intermediate"
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
