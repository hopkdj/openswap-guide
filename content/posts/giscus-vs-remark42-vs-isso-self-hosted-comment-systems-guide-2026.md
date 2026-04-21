---
title: "Giscus vs Remark42 vs Isso: Best Self-Hosted Comment Systems 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "privacy", "blogging"]
draft: false
description: "Compare three self-hosted comment systems — Giscus, Remark42, and Isso — with Docker setup guides, feature comparisons, and deployment best practices for static sites and blogs."
---

If you run a self-hosted blog, documentation site, or static website, you need a way for readers to leave comments — but relying on third-party services like Disqus means surrendering user data, injecting tracking scripts, and accepting ads you don't control. Self-hosted comment systems give you full ownership of every comment, zero third-party tracking, and complete control over moderation and data retention.

In this guide, we compare three mature, open-source self-hosted comment engines: **Giscus**, **Remark42**, and **Isso**. We'll look at their architecture, feature sets, deployment com[plex](https://www.plex.tv/)ity, and real-world performance so you can pick the right tool for your site.

## Why Self-Host Your Comment System

Using a hosted comment service introduces several problems:

- **Privacy violations**: Disqus and similar services set tracking cookies across every site using their widget, building cross-site user profiles.
- **Performance impact**: Third-party comment widgets load dozens of external resources, adding 2-4 seconds to page load times.
- **Vendor lock-in**: Migrating thousands of comments off a hosted platform is painful — often requiring scraping or unreliable export tools.
- **Ads and distractions**: Free tiers inject ads and "recommended content" widgets into your comment sections.
- **Censorship risk**: A hosted provider can disable your account or alter your content at any time.

Self-hosting solves all of these. Your comments load from your own domain (no third-party scripts), your visitors' data stays under your control, and you own the database permanently.

## Giscus — GitHub-Powered Comments

[Giscus](https://giscus.app) is a commenting system built on top of GitHub Discussions. Instead of running a separate comment server, it uses GitHub's API to store and retrieve comments. When a visitor leaves a comment, Giscus creates a GitHub Discussion in a repository you designate.

### Key Features

- **Zero server infrastructure**: No database, no backend to maintain — GitHub handles everything.
- **GitHub authentication**: Users log in with their GitHub account, eliminating spam registrations.
- **Markdown support**: Full GitHub-flavored Markdown with code blocks, tables, and task lists.
- **Reactions**: Emoji reactions (👍, 👎, 👀, ❤️, 🎉, 🚀) backed by GitHub's native reaction system.
- **Lightweight widget**: The embed script is ~27KB gzipped — significantly smaller than Disqus.
- **Open source**: MIT licensed, TypeScript codebase with 11,500+ stars.
- **Free tier**: Uses GitHub Discussions, which is free for public repositories.

### Architecture

Giscus runs entirely client-side as a JavaScript widget. It communicates with GitHub's GraphQL API to fetch and post comments. No server component is required — you only need to configure a public GitHub repository with Discussions enabled.

### Deployment

There is no server to deploy. Installation is a single `<script>` tag:

```html
<script src="https://giscus.app/client.js"
        data-repo="your-org/your-repo"
        data-repo-id="REPO_ID"
        data-category="Comments"
        data-category-id="CATEGORY_ID"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="preferred_color_scheme"
        data-lang="en"
        crossorigin="anonymous"
        async>
</script>
```

To get `data-repo-id` and `data-category-id`, visit [giscus.app](https://giscus.app) and enter your repository details — the tool generates the correct values automatically.

### Pros and Cons

| Aspect | Details |
|--------|---------|
| Infrastructure | Zero — no server required |
| Authentication | GitHub only (limits audience) |
| Moderation | Via GitHub Discussions UI |
| Data ownership | Comments live on GitHub, not your server |
| Offline access | Comments unavailable if GitHub is down |
| Cost | Free for public repos |

## Remark42 — Full-Featured Comment Engine

[Remark42](https://remark42.com) is a Go-based self-hosted comment engine with 5,400+ stars and active development (updated today). It provides a complete commenting solution with a built-in UI, multiple authentication providers, and powerful moderation tools.

### Key Features

- **Multiple auth providers**: Email, Google, GitHub, Facebook, Twitter, Discord, Slack, Yandex, Microsoft, and more via OAuth2.
- **Markdown with images**: Full Markdown editor with image uploads (stored locally or on S3-compatible storage).
- **Nested/threaded comments**: Unlimited nesting depth with collapse/expand controls.
- **Import/Export**: Import from Disqus, WordPress, and native formats. Export to JSON.
- **Email notifications**: Configurable email alerts for new comments and replies.
- **Granular moderation**: Approve, delete, or pin individual comments. Block users by IP.
- **RSS feed**: Per-site and per-user comment feeds.
- **Admin dashboard**: Web-based admin panel for moderation, comment management, and us[docker](https://www.docker.com/)inistration.

### Docker Deployment

Remark42 ships a well-maintained Docker image. Here's a production-ready `docker-compose.yml`:

```yaml
version: "3.8"

services:
  remark42:
    image: ghcr.io/umputun/remark42:latest
    container_name: remark42
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      - REMARK_URL=https://comments.yourdomain.com
      - SECRET=<generate-a-random-secret-key>
      - SITE=yourdomain.com
      - AUTH_GITHUB_CID=<github-client-id>
      - AUTH_GITHUB_CSEC=<github-client-secret>
      - NOTIFY_TYPE=email
      - NOTIFY_EMAIL_FROM=comments@yourdomain.com
      - NOTIFY_EMAIL_ADMIN=you@yourdomain.com
      - SMTP_HOST=smtp.yourdomain.com
      - SMTP_PORT=587
      - SMTP_TLS=true
      - SMTP_USERNAME=comments@yourdomain.com
      - SMTP_PASSWORD=<smtp-password>
    volumes:
      - ./remark42-data:/srv/var
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
```

Start with:

```bash
mkdir -p rema[nginx](https://nginx.org/)data
docker compose up -d
```

Then configure Nginx as a reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name comments.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/comments.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/comments.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Embedding on Your Site

```html
<script>
    var remark_config = {
        host: "https://comments.yourdomain.com",
        site_id: "yourdomain.com",
        components: ["embed", "counter", "last-comments"],
        theme: "dark",
        page_title: "Article Title",
        locale: "en",
        show_email_subscription: true
    };
</script>
<script>
    (function(c) {
        for(var i = 0; i < c.length; i++){
            var d = document.createElement("script");
            d.src = remark_config.host + "/web/" + c[i] + ".js";
            d.charset = "utf-8";
            d.async = true;
            (document.head || document.body).appendChild(d);
        }
    })(remark_config.components || ["embed"]);
</script>
```

## Isso — Lightweight Disqus Alternative

[Isso](https://isso-comments.de) is a Python-based lightweight comment server positioned as a direct Disqus replacement. At 5,200+ stars, it prioritizes simplicity and privacy over feature breadth.

### Key Features

- **SQLite storage**: Single-file database, trivial to back up and migrate.
- **Zero dependencies for readers**: No account required — visitors type their name and email (email is hashed and never stored).
- **Threaded comments**: Two-level nesting with auto-collapse for deep threads.
- **Moderation queue**: Approve or reject comments via a web admin interface.
- **Spam protection**: Built-in proof-of-work and optional IP-based rate limiting.
- **Privacy-first**: No tracking, no cookies, no third-party connections.
- **Small footprint**: The entire server is a single Python package — runs comfortably on a $5 VPS.

### Docker Deployment

Isso provides an official Dockerfile and docker-compose setup. Here's a production-ready configuration:

```yaml
version: "3.8"

services:
  isso:
    build:
      context: .
      dockerfile: Dockerfile
    image: isso:latest
    container_name: isso
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./db:/db
      - ./config/isso.cfg:/config/isso.cfg:ro
    environment:
      - ISSO_SETTINGS=/config/isso.cfg
      - ISSO_ENDPOINT=https://comments.yourdomain.com
    healthcheck:
      test: wget --no-verbose --tries=1 --spider $$ISSO_ENDPOINT/health || exit 1
      interval: 30s
      retries: 3
      start_period: 10s
      timeout: 10s
```

The Isso configuration file (`isso.cfg`):

```ini
[general]
dbpath = /db/comments.db
host = https://yourdomain.com/
notify = false
log-file = false

[server]
listen = http://0.0.0.0:8080/
reload = off
profile = off

[moderation]
enabled = true
purge-after = 30d
notify-reply = false

[guard]
enabled = true
ratelimit = 2
direct-reply = 3
reply-to-self = false
require-author = true
require-email = false

[hash]
salt = Eech7cohXoog4ahc
algorithm = pbkdf2
```

Start the server:

```bash
mkdir -p db config
# Place isso.cfg in config/
docker compose up -d
```

### Embedding on Your Site

```html
<script src="https://comments.yourdomain.com/js/embed.min.js"
        data-isso="https://comments.yourdomain.com"
        data-isso-css="true"
        data-isso-lang="en"
        data-isso-reply-to-self="false"
        data-isso-require-author="true"
        data-isso-require-email="false"
        data-isso-max-comments-top="10"
        data-isso-max-comments-nested="5"
        data-isso-vote="true"
        data-isso-feed="true">
</script>

<section id="isso-thread"></section>
```

## Feature Comparison

| Feature | Giscus | Remark42 | Isso |
|---------|--------|----------|------|
| **License** | MIT | MIT | MIT |
| **Language** | TypeScript | Go | Python |
| **GitHub Stars** | 11,560 | 5,477 | 5,270 |
| **Last Updated** | 2025-07-06 | 2026-04-18 | 2026-03-27 |
| **Server Required** | No | Yes | Yes |
| **Database** | GitHub Discussions | BoltDB (embedded) | SQLite |
| **Authentication** | GitHub only | OAuth2 (8+ providers) | None (anonymous) |
| **Markdown Support** | Yes (GFM) | Yes | Yes |
| **Image Uploads** | Via GitHub | Local / S3 | No |
| **Nested Comments** | Flat | Unlimited | 2 levels |
| **Reactions** | Emoji (GitHub) | Yes (votes) | Yes (upvote/downvote) |
| **Email Notifications** | No | Yes | Optional |
| **Import from Disqus** | No | Yes | Via script |
| **Admin Dashboard** | GitHub Discussions | Built-in web UI | Basic web UI |
| **RSS Feed** | No | Yes | Via endpoint |
| **Docker Support** | N/A | Official image | Official image |
| **Resource Usage** | Zero (client-side) | ~30MB RAM | ~50MB RAM |
| **Backup** | GitHub export | File copy (BoltDB) | File copy (SQLite) |

## Choosing the Right System

### Choose Giscus if:

- Your audience is primarily developers with GitHub accounts
- You want zero infrastructure maintenance
- Your site already integrates with GitHub (documentation sites, project pages)
- You're comfortable with comments living on GitHub's servers

### Choose Remark42 if:

- You want the most feature-rich self-hosted option
- Multiple authentication providers are important
- You need email notifications and RSS feeds
- You want image uploads and rich Markdown editing
- You have a technical team to maintain a Docker container

### Choose Isso if:

- You want the simplest possible self-hosted solution
- Anonymous commenting (no login required) is a priority
- You prefer Python over Go
- You want a single SQLite file for easy backups
- You run on minimal hardware (e.g., a $5 VPS or Raspberry Pi)

## Privacy Considerations

All three systems are privacy-respecting compared to Disqus:

- **Giscus**: Users authenticate via GitHub — GitHub sees the interaction but no other third-party tracker is involved. The widget loads from `giscus.app`, which is a CDN.
- **Remark42**: No third-party tracking. All authentication is handled through your own OAuth2 apps. Email addresses are only stored if the user opts in for notifications.
- **Isso**: The most private option. No accounts, no cookies, no third-party connections. Email addresses are hashed with a server-side salt and never stored in plaintext.

If privacy is your primary concern, Isso offers the cleanest architecture. If you need a balance of features and privacy, Remark42 is the strongest all-around choice.

## Related Reading

For readers building a self-hosted site, you may also find these guides useful:

- Our [static site generator comparison](../self-hosted-static-site-generators-hugo-jekyll-astro-eleventy/) covers Hugo, Jekyll, Astro, and Eleventy — excellent platforms to pair with a self-hosted comment system.
- If you're self-hosting a blog, check out our [WriteFreely blogging platform guide](../writefreely-self-hosted-blogging-platform-guide/) for a complete self-hosted publishing stack.
- For tracking visitors without compromising privacy, see our [web analytics comparison](../matomo-vs-plausible-vs-umami-web-analytics-guide/) covering Matomo, Plausible, and Umami.

## FAQ

### Can I migrate my Disqus comments to a self-hosted system?

Yes. Remark42 has a built-in Disqus importer — upload your Disqus XML export and it converts everything automatically. Isso has a community migration script (`isso-migrate`) that handles Disqus, WordPress, and static comment formats. Giscus does not support direct import since it uses GitHub Discussions as storage, but you can manually copy-paste or use community scripts to convert Disqus exports to GitHub Discussions.

### Do self-hosted comment systems handle spam?

All three have anti-spam measures. Giscus relies on GitHub's account system — spammers need a GitHub account, which raises the barrier significantly. Remark42 has IP-based rate limiting, CAPTCHA options, and a moderation queue. Isso has built-in proof-of-work (a lightweight computational puzzle), rate limiting, and a moderation queue for comment approval. For high-traffic sites, Remark42 offers the most configurable spam protection.

### Can I use these with static site generators like Hugo or Jekyll?

Yes, all three embed via a `<script>` tag that works with any HTML page. This makes them compatible with Hugo, Jekyll, Astro, Eleventy, Next.js static export, and any other SSG that generates HTML. You paste the embed snippet into your site's comment partial or template, and it renders automatically for each page.

### How much server resources do these need?

Remark42 runs comfortably on 30-50MB of RAM with a small Go binary. Isso uses 50-80MB RAM due to the Python/Gunicorn process plus SQLite. Giscus uses zero server resources since it's purely client-side. A $5/month VPS is more than sufficient for Remark42 or Isso serving thousands of daily visitors.

### Can I theme the comment widget to match my site?

All three support theming. Giscus has built-in `light`, `dark`, and `transparent` themes, plus automatic `preferred_color_scheme` detection. Remark42 supports `light`, `dark`, and custom CSS themes. Isso ships with a minimal CSS theme that you can override by setting `data-isso-css="false"` and providing your own stylesheet — the DOM structure is well-documented.

### What happens to my comments if I shut down the server?

With Remark42 and Isso, your comments are stored in files on your server (BoltDB for Remark42, SQLite for Isso). You own the data permanently — just back up the database file. With Giscus, comments live on GitHub's servers. If GitHub shuts down Discussions or your repository is deleted, the comments are lost unless you've exported them. For true data ownership, Remark42 or Isso is the safer choice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Giscus vs Remark42 vs Isso: Best Self-Hosted Comment Systems 2026",
  "description": "Compare three self-hosted comment systems — Giscus, Remark42, and Isso — with Docker setup guides, feature comparisons, and deployment best practices for static sites and blogs.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
