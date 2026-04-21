---
title: "WriteFreely vs Ghost vs Medium: Best Self-Hosted Blogging Platform 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to WriteFreely, the minimalist self-hosted blogging platform. Learn why it's the best open-source alternative to Medium and Substack in 2026, with Docker setup, ActivityPub federation, and theming."
---

Blogging is not dead — it just got decentralized. In 2026, a growing number of writers, developers, and creators are walking away from Medium, Substack, and WordPress.com in favor of self-hosted blogging platforms that give them full ownership of their content, audience, and data. At the forefront of this movement is **WriteFreely**, an open-source, minimalist publishing platform that doubles as a node in the Fediverse.

This guide covers why WriteFreely has become the go-to choice for self-hosted blogging, walks you through a complete [docker](https://www.docker.com/) deployment, and compares it against the lead[ghost](https://ghost.org/)lternatives including Ghost and the proprietary platforms you're probably already paying for.

## Why Self-Host Your Blog in 2026

The arguments for self-hosting a blog have never been stronger. Here's what you gain when you take control of your publishing platform:

**Full content ownership**: On Medium or Substack, your articles live on someone else's servers under someone else's terms. They can change the algorithm, restrict your reach, modify the revenue split, or shut down entirely. When you self-host, your words live on your server. Period.

**No paywalls or revenue splits**: Medium's partner program requires exclusivity and takes a cut. Substack charges 10% of paid subscriptions. WriteFreely costs nothing beyond your server — and you keep 100% of any revenue from donations, sponsorships, or paid memberships you choose to add.

**Built-in discoverability via ActivityPub**: WriteFreely supports the ActivityPub protocol, meaning your blog posts can appear in the feeds of Mastodon, Friendica, and other Fediverse users. You get the network effects of a platform like Medium without giving up independence.

**Minimalism as a feature**: WriteFreely strips away the noise — no ads, no analytics dashboards, no notification bells, no algorithmic feeds. Just clean typography, fast page loads, and your words. It's designed for reading, not engagement farming.

**Privacy for your readers**: No tracking pixels, no cookie banners, no third-party scripts loading on every page view. Your readers' visits stay between them and your server.

## What Is WriteFreely?

WriteFreely is an open-source blogging platform written in Go. It was created by the team behind Write.as with the goal of building a simple, federation-ready publishing tool that anyone can run on a modest server.

Key characteristics:

- **Single binary** — written in Go, easy to deploy and update
- **Markdown-first editing** — write in plain text with a clean editor
- **ActivityPub support** — your blog joins the Fediverse automatically
- **Multi-user blogs** — run a publication with multiple writers, or host blogs for friends
- **Custom themes** — CSS-based theming with a growing community stylesheet ecosystem
- **SQLite or MySQL** — lightweight database options
- **Built-in HTTP server** — no reverse proxy required for basic setups

WriteFreely is used by independent journalists, technical writers, hobbyists, and organizations that want a no-nonsense publishing stack. It powers everything from personal dev blogs to multi-author zines.

## Comparison: WriteFreely vs Ghost vs Medium vs Substack

| Feature | WriteFreely | Ghost | Medium | Substack |
|---|---|---|---|---|
| **License** | AGPL-3.0 | MIT (self-hosted) | Proprietary | Proprietary |
| **Cost** | Free (self-hosted) | Free (self-hosted), $9/mo+ (hosted) | Free / $5/mo (membership) | Free / 10% revenue cut |
| **Writing format** | Markdown | Markdown + card blocks | Rich text editor | Rich text editor |
| **ActivityPub** | Native | Via plugin | No | No |
| **Newsletter** | Via webhooks | Built-in | No | Built-in |
| **Multi-user** | Yes | Yes | No (single author) | No (single author) |
| **Themes** | CSS-based | Handlebars templates | Fixed layout | Fixed layout |
| **Resource usage** | ~30 MB RAM | ~300 MB RAM (Node.js) | N/A (cloud) | N/A (cloud) |
| **Database** | SQLite / MySQL | MySQL / PostgreSQL | N/A (cloud) | N/A (cloud) |
| **Custom domains** | Yes | Yes | No | Yes |
| **Analytics** | None (privacy-focused) | Built-in | Built-in | Built-in |
| **Best for** | Minimalist writers, Fediverse users | Professional publishers, newsletters | General audience reach | Paid newsletter creators |

### When to Choose WriteFreely

- You want a **distraction-free writing experience** with Markdown
- You care about **Fediverse integration** out of the box
- You run on a **low-resource server** (Raspberry Pi, $4 VPS)
- You prefer **simplicity over feature bloat**
- You want to **own your content completely**

### When Ghost Might Be Better

- You need a built-in **newsletter and membership system**
- You want a **visual page builder** with card blocks
- You have a team that needs **rich content management workflows**
- You're comfortable with higher resource requirements

### When to Stay on Medium or Substack

- You rely on their **existing audience and discovery algorithms**
- You don't want to manage a server at all
- Your primary monetization depends on their **built-in payment infrastructure**

## Prerequisites

Before deploying WriteFreely, make sure you have:

- A Linux server (Ubuntu 22.04+, Debian 12+, or any modern distro)
- Docker and Docker Compose installed
- A domain name pointing to your server's IP ad[nginx](https://nginx.org/)
- (Optional) A reverse proxy like Caddy or Nginx for HTTPS

If you don't have Docker installed yet:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Log out and back in for the group membership to take effect.

## Deploying WriteFreely with Docker Compose

Create a project directory and set up the compose stack:

```bash
mkdir -p ~/writefreely && cd ~/writefreely
mkdir -p data keys
```

Now create the `docker-compose.yml` file:

```yaml
version: "3"

services:
  writefreely:
    image: writeas/writefreely:latest
    container_name: writefreely
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/go/keys
      - ./config.ini:/go/config.ini:ro
      - ./keys:/go/keys
    environment:
      - WRITEFREELY_PORT=8080
      - WRITEFREELY_BIND=0.0.0.0
    depends_on:
      - db
    networks:
      - writefreely_net

  db:
    image: mysql:8.0
    container_name: writefreely_db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: your-root-password-here
      MYSQL_DATABASE: writefreely
      MYSQL_USER: writefreely
      MYSQL_PASSWORD: your-db-password-here
    volumes:
      - db_data:/var/lib/mysql
    networks:
      - writefreely_net

volumes:
  db_data:

networks:
  writefreely_net:
    driver: bridge
```

For an even lighter setup, you can skip MySQL entirely and use SQLite — WriteFreely supports it out of the box. Here's the minimal single-container version:

```yaml
version: "3"

services:
  writefreely:
    image: writeas/writefreely:latest
    container_name: writefreely
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - writefreely_data:/go/keys
      - ./config.ini:/go/config.ini:ro
    networks:
      - writefreely_net

volumes:
  writefreely_data:

networks:
  writefreely_net:
    driver: bridge
```

Save this as `docker-compose.yml` and start the container:

```bash
docker compose up -d
```

WriteFreely will now be running on `http://your-server-ip:8080`.

## Generating the Configuration File

WriteFreely uses a `config.ini` file for all settings. The easiest way to generate one is to run the built-in config wizard:

```bash
docker compose exec writefreely ./writefreely --config
```

This interactive wizard will ask you a series of questions:

```
Database type? [1] SQLite  [2] MySQL
> 1

HTTP listening address (e.g. localhost:8080):
> 0.0.0.0:8080

Site name (e.g. My Blog):
> OpenSwap Guide

Site description:
> A self-hosted blog about open source alternatives

Public or restricted? [1] Public  [2] Restricted
> 1

Enable federation (ActivityPub)? [y/N]:
> y

Default blog visibility: [1] Public  [2] Private
> 1

Admin username:
> admin

Admin password:
> ********
```

This generates a `config.ini` file. Copy it to your project directory and restart:

```bash
docker compose exec writefreely cat /go/config.ini > ./config.ini
docker compose down && docker compose up -d
```

### Manual Configuration

Alternatively, create the `config.ini` manually for full control:

```ini
[server]
hidden_host =
port = 8080
bind = 0.0.0.0
templates_parent_dir =
static_parent_dir =
pages_parent_dir =
keys_parent_dir =

[app]
site_name = OpenSwap Guide
site_description = A self-hosted blog about open source alternatives
host = https://blog.yourdomain.com
theme = write
disable_js = false
webfonts = 1
landing = /
simple_nav = false
wf_modesty = 0
chalkdow = false
monospace = false
no_footer_branding = false
pixel_sub_path =

[database]
type = sqlite3
filename = /go/data/writefreely.db

[auth]
min_password_len = 8

[oauth]
enabled = false
```

## Setting Up HTTPS with Caddy

A blog without HTTPS is a blog nobody will trust. The easiest way to add TLS is with Caddy, which handles certificate provisioning automatically via Let's Encrypt.

Create a `Caddyfile` in your project directory:

```
blog.yourdomain.com {
    reverse_proxy writefreely:8080
    encode gzip
}
```

Update your `docker-compose.yml` to include Caddy:

```yaml
services:
  writefreely:
    image: writeas/writefreely:latest
    container_name: writefreely
    restart: unless-stopped
    volumes:
      - writefreely_data:/go/keys
      - ./config.ini:/go/config.ini:ro
    networks:
      - writefreely_net

  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - writefreely_net

volumes:
  writefreely_data:
  caddy_data:
  caddy_config:

networks:
  writefreely_net:
    driver: bridge
```

Make sure your `config.ini` reflects the HTTPS URL:

```ini
[app]
host = https://blog.yourdomain.com
```

Restart everything:

```bash
docker compose down && docker compose up -d
```

Caddy will automatically obtain and renew your TLS certificate. Your blog is now live at `https://blog.yourdomain.com`.

## Writing and Publishing Your First Post

Once WriteFreely is running, navigate to your blog URL and click **Sign Up** to create your account. After logging in:

1. Click **New Post** in the top navigation
2. Write your post in Markdown — the editor supports live preview
3. Add a title, and optionally a custom slug for the URL
4. Set the post to **Public** or keep it **Unlisted** (accessible only via direct link)
5. Click **Publish**

Your post is instantly live. If ActivityPub is enabled, it's also discoverable by Fediverse users.

### Writing from the Command Line

WriteFreely has a clean API that supports posting from the terminal. First, get your access token:

```bash
curl -X POST https://blog.yourdomain.com/api/auth/token \
  -d "alias=your-username" \
  -d "password=your-password"
```

Then publish a post:

```bash
curl -X POST https://blog.yourdomain.com/api/posts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First API Post",
    "content": "# Hello World\n\nThis post was published via the WriteFreely API.",
    "visibility": "public"
  }'
```

This makes it easy to integrate WriteFreely into CI/CD pipelines, automated workflows, or static site generators.

## Enabling ActivityPub Federation

One of WriteFreely's most powerful features is its built-in ActivityPub support. When enabled, every public post on your blog becomes a federated object that can be followed, boosted, and replied to from any ActivityPub-compatible platform.

### How It Works

When you publish a post, WriteFreely:

1. Creates an ActivityPub `Note` or `Article` object
2. Announces it to followers via `Create` activities
3. Accepts `Follow` requests from Mastodon, Friendica, and other servers
4. Delivers replies and boosts back to the originating servers

### Setting It Up

ActivityPub is configured during the initial `--config` wizard. If you need to enable it on an existing instance, update your `config.ini`:

```ini
[app]
federation = true
federated_timeline = true
```

Then restart WriteFreely. Your blog now has a federation-ready actor at `@yourblog@blog.yourdomain.com`.

### Following Your Blog from Mastodon

From your Mastodon account, search for your blog's handle (e.g., `@blog@blog.yourdomain.com`) and follow it. Every new public post will appear in your Mastodon feed. Your Mastodon followers can also discover and follow your blog independently.

### Federation Best Practices

- Keep your **instance description** informative so visitors from the Fediverse understand what your blog is about
- Use **descriptive post titles** — they appear as the subject line in federated contexts
- Consider a **custom profile header** in your theme to make your blog recognizable in Fediverse timelines
- Be aware that **federation is irreversible** — once a post is federated, copies may exist on other servers even if you delete the original

## Customizing Your Blog with Themes

WriteFreely ships with a clean default theme, but the theming system is flexible. You can customize nearly every visual aspect through CSS.

### Built-in Theme Options

In your `config.ini`, the `theme` setting controls the base layout:

```ini
[app]
theme = write       # Clean, typography-focused
```

Available built-in themes include `write` (the default), and you can toggle additional options:

```ini
[app]
webfonts = 1        # Use web fonts (Inter, Lora)
monospace = 0       # Enable monospace fonts
no_footer_branding = false
```

### Custom CSS

WriteFreely allows you to inject custom CSS directly into your blog. From the admin panel, navigate to your blog settings and add CSS in the **Custom CSS** field.

Here's a practical example that adds a dark mode toggle, improved code block styling, and subtle animations:

```css
/* Dark mode via prefers-color-scheme */
@media (prefers-color-scheme: dark) {
  body {
    background: #1a1a2e;
    color: #e0e0e0;
  }
  article a {
    color: #7ec8e3;
  }
  pre, code {
    background: #16213e;
    border: 1px solid #0f3460;
  }
  blockquote {
    border-left-color: #7ec8e3;
    color: #b0b0b0;
  }
}

/* Improved code blocks */
pre {
  padding: 1rem 1.5rem;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.9em;
  line-height: 1.6;
}

code {
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* Smooth link transitions */
a {
  transition: color 0.2s ease;
}

/* Subtle article card effect */
article {
  padding: 2rem 0;
  border-bottom: 1px solid rgba(128, 128, 128, 0.2);
}
```

### Community Themes

The WriteFreely community has created dozens of themes. You can find them on the [WriteFreely themes directory](https://writefreely.org/themes) and on GitHub. To install a community theme, copy its CSS into your blog's custom CSS field or self-host the stylesheet and link it.

## Running Multiple Blogs on One Instance

WriteFreely supports multiple blogs per instance, making it ideal for running a publication or hosting blogs for friends and family.

### Creating Additional Blogs

After logging in as admin, visit the admin panel and create new blogs:

```bash
# Via the API
curl -X POST https://blog.yourdomain.com/api/blogs \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alias": "tech-blog",
    "title": "Tech Blog",
    "privacy": 1
  }'
```

Each blog gets its own URL (`blog.yourdomain.com/tech-blog/`), its own settings, and its own set of authors.

### User Management

WriteFreely's multi-user system lets you:

- Assign **writers** who can publish to specific blogs
- Create **admin users** with full instance control
- Set blog-level **privacy** (public, unlisted, or private)
- Enable **open registration** so visitors can create their own blogs

## Backups and Maintenance

A self-hosted blog is only as reliable as its backup strategy. WriteFreely makes this straightforward.

### Database Backup

For SQLite (the default):

```bash
# Backup the database
cp ~/writefreely/data/writefreely.db ~/writefreely/backups/writefreely-$(date +%F).db

# Compress and store
tar czf ~/writefreely/backups/writefreely-$(date +%F).tar.gz \
  -C ~/writefreely/data writefreely.db
```

For MySQL:

```bash
docker exec writefreely_db mysqldump \
  -u writefreely -p'your-db-password-here' writefreely \
  > ~/writefreely/backups/writefreely-$(date +%F).sql
```

### Automated Backups with Cron

Add a cron job to run daily backups:

```bash
# Edit crontab
crontab -e

# Add this line (daily at 2 AM)
0 2 * * * cd ~/writefreely && docker compose exec -T db mysqldump -u writefreely -p'your-db-password-here' writefreely | gzip > /backups/writefreely-$(date +\%F).sql.gz
```

### Updating WriteFreely

```bash
cd ~/writefreely
docker compose pull writefreely
docker compose down && docker compose up -d
```

The `:latest` tag ensures you always get the newest version. WriteFreely's migration system handles database schema changes automatically.

## Performance and Resource Usage

WriteFreely is remarkably lightweight:

- **Memory**: ~20–40 MB RAM for the Go binary
- **CPU**: Near-zero when idle, minimal spikes on page load
- **Disk**: ~50 MB for the binary + database (grows with content)
- **Page load**: Under 200ms on a $4 VPS

This makes it feasible to run WriteFreely alongside other self-hosted services on a single low-end VPS or even a Raspberry Pi. For comparison, a typical Ghost installation requires 300–500 MB of RAM due to its Node.js runtime and asset compilation pipeline.

## Conclusion

WriteFreely represents what self-hosted blogging should be: simple, fast, private, and connected to the wider fediverse without the bloat. It's not trying to be a CMS, a newsletter platform, or a social network — it's a place to publish your words and have them reach people who want to read them.

If you're tired of platform risk, algorithmic feeds, and the endless feature creep of modern publishing tools, WriteFreely offers a refreshing alternative. Pair it with Caddy for HTTPS, enable ActivityPub for federation, and you have a complete, production-ready blog that runs on less than 40 MB of RAM.

The best part? Once it's deployed, you barely think about it. You just write.

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
