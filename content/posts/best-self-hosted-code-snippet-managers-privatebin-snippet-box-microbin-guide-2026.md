---
title: "Best Self-Hosted Code Snippet Managers 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy", "developer-tools"]
draft: false
description: "Compare the top open-source self-hosted code snippet managers and pastebins: PrivateBin, Snippet Box, and microbin. Includes Docker deployment guides, feature comparisons, and setup instructions."
---

Every developer accumulates a growing collection of code snippets, configuration files, one-liners, and troubleshooting notes. The question is: where do you keep them? Cloud-based solutions like GitHub Gist or Pastebin are convenient, but they come with privacy concerns, usage limits, and the risk of service shutdown.

Self-hosted code snippet managers solve these problems by giving you full control over your data, zero vendor lock-in, and the ability to customize everything to your workflow. In this guide, we compare three of the best open-source, self-hosted options available in 2026: **PrivateBin**, **Snippet Box**, and **microbin**.

## Why Self-Host Your Code Snippets?

Before diving into the tools, here's why running your own snippet manager makes sense:

- **Privacy**: Code snippets often contain internal API endpoints, configuration values, or proprietary algorithms. Self-hosting ensures this data never leaves your infrastructure.
- **No limits**: Cloud pastebins impose character limits, expiration policies, and rate restrictions. Your own server has no such constraints.
- **Searchability**: A personal snippet library becomes a searchable knowledge base that grows with your experience.
- **Team sharing**: Self-hosted tools enable secure sharing within your team or organization without relying on third-party services.
- **Offline access**: When your snippets live on your own network, they're available even without internet connectivity.
- **Cost**: All three tools we cover are free and open-source. Your only cost is the server to run them on.

## Quick Comparison at a Glance

| Feature | PrivateBin | Snippet Box | microbin |
|---------|-----------|-------------|----------|
| **Language** | PHP | TypeScript (Node.js) | Rust |
| **GitHub Stars** | 8,200+ | 1,080+ | 4,100+ |
| **License** | zlib | MIT | Apache 2.0 |
| **[docker](https://www.docker.com/) Image** | Official | Official | Official |
| **Encryption** | Client-side AES-256 | Server-side | Server-side |
| **Syntax Highlighting** | Yes | Yes | Yes |
| **Password Protection** | Yes | No (built-in) | Yes |
| **Expiration Support** | Yes | No | Yes |
| **File Attachments** | Yes | No | Yes |
| **Dark Mode** | Yes | Yes | Yes |
| **REST API** | No | Yes | Yes |
| **Database** | Flat file / MySQL / SQLite | SQLite | SQLite |
| **Binary Size** | ~15 MB (PHP) | ~200 MB (Node) | ~8 MB (single binary) |
| **Best For** | Secure pastebin | Code organization | Lightweight sharing |

---

## 1. PrivateBin — Zero-Knowledge Secure Pastebin

**PrivateBin** is the most popular self-hosted pastebin with over 8,200 stars on GitHub. Its defining feature is **client-side encryption**: data is encrypted and decrypted entirely in the browser using 256-bit AES, meaning the server never sees your plaintext data.

### Key Features

- End-to-end encryption with passwords derived from URL fragments (the part after `#` is never sent to the server)
- Self-destructing snippets with configurable burn-after-read and time-based expiration
- File attachment support with encrypted uploads
- Syntax highlighting for 300+ programming languages
- Discussion threads on any pasted snippet
- Multiple storage backends: flat files, MySQL, SQLite, PostgreSQL, Google Cloud Storage, Amazon S3
- Template system for custom branding
- Rate limiting and spam protection
- Dark mode built in

### Docker Installation

```bash
# Create persistent data directory
mkdir -p ~/privatebin/{cfg,data}

# Run PrivateBin with Docker
docker run -d \
  --name privatebin \
  -p 8080:8080 \
  -v ~/privatebin/cfg:/srv/cfg \
  -v ~/privatebin/data:/srv/data \
[nginx](https://nginx.org/)TZ=UTC \
  privatebin/nginx-fpm-alpine:latest
```

### Configuration

PrivateBin's configuration lives in `~/privatebin/cfg/conf.ini`. Here's a production-ready setup:

```ini
[main]
name = "My PrivateBin"
discussion = true
opendiscussion = false
password = true
burnafterreadingselected = true
fileupload = true
filesize_limit = 10
fileage_limit = 30

[expire]
default = "1week"

[expire_options]
1hour = 3600
1day = 86400
1week = 604800
1month = 2592000
1year = 31536000
never = 0

[formatter_options]
plaintext = "Plain Text"
syntaxhighlighting = "Source Code"
markdown = "Markdown"

; Storage backend — use SQLite for simplicity
[server]
class = Database
[model]
class = Database

[database]
class = SQLite
dsn = "sqlite:/srv/data/db.sq3"
```

After updating the config, restart the container:

```bash
docker restart privatebin
```

### Docker Compose Setup

For a more complete deployment with a reverse proxy:

```yaml
version: "3.8"

services:
  privatebin:
    image: privatebin/nginx-fpm-alpine:latest
    container_name: privatebin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./cfg:/srv/cfg
      - ./data:/srv/data
    environment:
      - TZ=UTC
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Save as `docker-compose.yml` and run:

```bash
docker compose up -d
```

Access PrivateBin at `http://your-server:8080`.

### When to Choose PrivateBin

Pick PrivateBin when security and privacy are your top priorities. The client-side encryption model means even if someone gains access to your server, they cannot read stored snippets without the decryption keys (which live only in the URL). It's ideal for sharing sensitive code, credentials, or configuration across team members.

---

## 2. Snippet Box — Developer-Focused Snippet Organizer

**Snippet Box** is designed specifically as a code snippet organizer rather than a pastebin. It features a clean, modern UI with powerful search, tagging, and syntax highlighting. Unlike PrivateBin's ephemeral model, Snippet Box is built for long-term snippet management.

### Key Features

- Intuitive card-based interface for browsing and managing snippets
- Syntax highlighting with language auto-detection
- Tag-based organization with color-coded labels
- Full-text search across all snippets
- Markdown support for descriptions
- Public/private visibility toggle per snippet
- REST API for programmatic access
- Single-user authentication with password protection
- SQLite database for simple setup
- Responsive design works on mobile and desktop

### Docker Installation

```bash
# Create data directory
mkdir -p ~/snippetbox/data

# Run Snippet Box
docker run -d \
  --name snippetbox \
  -p 3000:3000 \
  -v ~/snippetbox/data:/data \
  -e "NODE_ENV=production" \
  pawelmalak/snippet-box:latest
```

### Initial Setup

After the container starts, visit `http://your-server:3000` and create your admin account on first launch. You'll set a username and password that protects your snippet library.

### Docker Compose with Reverse Proxy

```yaml
version: "3.8"

services:
  snippetbox:
    image: pawelmalak/snippet-box:latest
    container_name: snippetbox
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./data:/data
    environment:
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000"]
      interval: 30s
     [caddy](https://caddyserver.com/)out: 5s
      retries: 3

  # Optional: add Caddy reverse proxy for HTTPS
  caddy:
    image: caddy:2-alpine
    container_name: snippetbox-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - snippetbox

volumes:
  caddy_data:
```

Create a `Caddyfile` alongside your compose file:

```
snippetbox.yourdomain.com {
    reverse_proxy snippetbox:3000
}
```

### Using the REST API

Snippet Box includes a REST API for creating, reading, updating, and deleting snippets programmatically. First, generate an API token from the settings page, then:

```bash
# Create a new snippet via API
curl -X POST http://your-server:3000/api/snippets \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "title": "Docker Prune Command",
    "content": "docker system prune -a --volumes",
    "language": "bash",
    "tags": ["docker", "cleanup"],
    "type": "private"
  }'

# List all snippets
curl http://your-server:3000/api/snippets \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Search snippets
curl "http://your-server:3000/api/snippets?search=docker" \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

### When to Choose Snippet Box

Choose Snippet Box if you want a dedicated, organized library for your personal or team code snippets. Its tag-based organization, search capabilities, and REST API make it ideal for developers who want a permanent, searchable reference library. The card-based UI is also the most visually appealing of the three options.

---

## 3. microbin — Ultra-Lightweight Pastebin in Rust

**microbin** is a minimalist pastebin written in Rust, designed to be as small, fast, and dependency-free as possible. The entire application compiles to a single binary of approximately 8 MB with zero runtime dependencies.

### Key Features

- Single binary with no external dependencies
- Extremely low memory footprint (under 20 MB RAM)
- Built-in syntax highlighting for 200+ languages
- Password-protected snippets with optional expiration
- File attachment uploads
- REST API with JSON responses
- QR code generation for snippet URLs
- Dark mode support
- SQLite database (file-based, no server needed)
- Docker image based on `scratch` (minimal base image)
- Configurable via environment variables or TOML config
- URL shortening built in

### Docker Installation

```bash
# Create data directory
mkdir -p ~/microbin/data

# Run microbin
docker run -d \
  --name microbin \
  -p 8080:8080 \
  -v ~/microbin/data:/app/data \
  -e MICROBIN_PUBLIC_PASTING=true \
  -e MICROBIN_HIGHLIGHTSYNTAX=true \
  -e MICROBIN_DEFAULT_EXPIRY=24hour \
  -e MICROBIN_FILE_UPLOADS=true \
  -e MICROBIN_MAX_FILE_SIZE_MB=50 \
  ghcr.io/szabodanika/microbin:latest
```

### Configuration via Environment Variables

microbin uses environment variables for all configuration. Here's a comprehensive production setup:

```bash
# Instance settings
MICROBIN_INSTANCE_TITLE="My MicroBin"
MICROBIN_INSTANCE_FOOTER="Self-hosted snippet manager"
MICROBIN_BIND="0.0.0.0:8080"

# Security
MICROBIN_ADMIN_USERNAME="admin"
MICROBIN_ADMIN_PASSWORD="your-secure-password"
MICROBIN_PUBLIC_PASTING=true
MICROBIN_NO_LISTING=true

# Features
MICROBIN_HIGHLIGHTSYNTAX=true
MICROBIN_FILE_UPLOADS=true
MICROBIN_MAX_FILE_SIZE_MB=50
MICROBIN_DEFAULT_EXPIRY=7day
MICROBIN_QR=true

# Limits
MICROBIN_MAX_BODY_SIZE_MB=10
MICROBIN_RATE_LIMIT=10
```

### Docker Compose Full Setup

```yaml
version: "3.8"

services:
  microbin:
    image: ghcr.io/szabodanika/microbin:latest
    container_name: microbin
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - MICROBIN_INSTANCE_TITLE=My MicroBin
      - MICROBIN_ADMIN_USERNAME=admin
      - MICROBIN_ADMIN_PASSWORD=changeme-now
      - MICROBIN_PUBLIC_PASTING=true
      - MICROBIN_NO_LISTING=true
      - MICROBIN_HIGHLIGHTSYNTAX=true
      - MICROBIN_FILE_UPLOADS=true
      - MICROBIN_MAX_FILE_SIZE_MB=50
      - MICROBIN_DEFAULT_EXPIRY=7day
      - MICROBIN_QR=true
      - MICROBIN_RATE_LIMIT=10
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8080"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 64M
```

### Bare-Metal Installation

One of microbin's advantages is its simplicity — you can run it directly on any Linux system:

```bash
# Download the latest release binary
curl -L https://github.com/szabodanika/microbin/releases/latest/download/microbin-x86_64-linux \
  -o /usr/local/bin/microbin
chmod +x /usr/local/bin/microbin

# Create data directory
mkdir -p /opt/microbin/data

# Run it
/opt/microbin/microbin \
  --bind 0.0.0.0:8080 \
  --data-dir /opt/microbin/data \
  --public-pasting \
  --highlight-syntax
```

### Systemd Service

For production use, create a systemd service:

```ini
[Unit]
Description=MicroBin Self-Hosted Pastebin
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/local/bin/microbin \
  --bind 0.0.0.0:8080 \
  --data-dir /opt/microbin/data \
  --public-pasting \
  --highlight-syntax \
  --no-listing
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Save to `/etc/systemd/system/microbin.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now microbin
sudo systemctl status microbin
```

### When to Choose microbin

Choose microbin when you want the smallest, fastest possible pastebin with minimal resource usage. Its single-binary design makes it perfect for low-powered devices like Raspberry Pi, embedded systems, or environments where you want to minimize attack surface. The built-in QR code generation and URL shortening are nice bonuses for quick sharing.

---

## Detailed Feature Comparison

### Security Model

| Aspect | PrivateBin | Snippet Box | microbin |
|--------|-----------|-------------|----------|
| Encryption | Client-side AES-256 | Server transport only | Server transport only |
| Password per snippet | Yes | No | Yes |
| Burn after read | Yes | No | No |
| Server sees plaintext | No | Yes | Yes |
| Admin can read snippets | No | Yes (unencrypted) | Yes (unencrypted) |

PrivateBin's zero-knowledge architecture is unmatched for security. The encryption key is embedded in the URL fragment (after `#`), which browsers never transmit to servers. This means even a compromised server cannot decrypt your data.

### Storage and Scalability

| Aspect | PrivateBin | Snippet Box | microbin |
|--------|-----------|-------------|----------|
| Default backend | Flat files | SQLite | SQLite |
| Alternative DBs | MySQL, SQLite, PostgreSQL, S3, GCS | SQLite only | SQLite only |
| Max snippet size | Configurable (default: 2 MB) | ~100 KB | Configurable (default: 10 MB) |
| File attachments | Yes (encrypted) | No | Yes (unencrypted) |
| Multi-user | No (single admin) | Single user | Admin + public |

For team environments with high storage demands, PrivateBin's S3 and database backends provide the most scalability options. Snippet Box and microbin keep things simple with SQLite.

### API and Automation

| Aspect | PrivateBin | Snippet Box | microbin |
|--------|-----------|-------------|----------|
| REST API | No | Yes (full CRUD) | Yes (create/read/list) |
| CLI tool | No | Community scripts | Community scripts |
| Webhook support | No | No | No |
| Integration examples | Browser extensions | API clients | curl/wget |

Snippet Box leads in API capabilities with a full CRUD REST API, making it the best choice for developers who want to automate snippet management or integrate with their IDE.

---

## Running All Three Side-by-Side

If you want to evaluate all three tools on the same server, here's a unified Docker Compose configuration:

```yaml
version: "3.8"

services:
  privatebin:
    image: privatebin/nginx-fpm-alpine:latest
    container_name: privatebin
    restart: unless-stopped
    ports:
      - "8081:8080"
    volumes:
      - ./privatebin/cfg:/srv/cfg
      - ./privatebin/data:/srv/data

  snippetbox:
    image: pawelmalak/snippet-box:latest
    container_name: snippetbox
    restart: unless-stopped
    ports:
      - "8082:3000"
    volumes:
      - ./snippetbox/data:/data

  microbin:
    image: ghcr.io/szabodanika/microbin:latest
    container_name: microbin
    restart: unless-stopped
    ports:
      - "8083:8080"
    volumes:
      - ./microbin/data:/app/data
    environment:
      - MICROBIN_PUBLIC_PASTING=true
      - MICROBIN_HIGHLIGHTSYNTAX=true
```

Access each tool at:
- PrivateBin: `http://your-server:8081`
- Snippet Box: `http://your-server:8082`
- microbin: `http://your-server:8083`

## Adding HTTPS with Caddy

For production deployments, always use HTTPS. Here's a quick Caddy configuration that handles all three services:

```
privatebin.yourdomain.com {
    reverse_proxy privatebin:8080
}

snippets.yourdomain.com {
    reverse_proxy snippetbox:3000
}

paste.yourdomain.com {
    reverse_proxy microbin:8080
}
```

Caddy automatically obtains and renews TLS certificates via Let's Encrypt. No additional configuration needed.

---

## Which Should You Choose?

The right tool depends on your specific needs:

**Choose PrivateBin if:**
- You need maximum security and privacy
- You're sharing sensitive information (credentials, keys, internal code)
- You want self-destructing, ephemeral snippets
- Your team values zero-knowledge encryption
- You need file attachment support with encryption

**Choose Snippet Box if:**
- You want a permanent, organized snippet library
- You need tag-based organization and full-text search
- You want REST API access for automation
- You prefer a modern, card-based interface
- You're building a personal or team knowledge base

**Choose microbin if:**
- You need the lightest possible footprint
- You're running on resource-constrained hardware (Raspberry Pi, VPS)
- You want a single binary with zero dependencies
- You need QR code generation for quick mobile sharing
- You prefer Rust-based security and performance

## Final Thoughts

Self-hosting your code snippets is one of the highest-return infrastructure investments a developer can make. All three tools are free, open-source, and actively maintained. PrivateBin leads in security, Snippet Box excels in organization and developer experience, and microbin wins on minimalism and performance.

For most developers, we recommend starting with **Snippet Box** for day-to-day snippet management and running **PrivateBin** alongside it for sharing sensitive information. Both can coexist on the same server with minimal resource overhead, giving you the best of both worlds.

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
