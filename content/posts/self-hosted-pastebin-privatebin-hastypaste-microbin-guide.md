---
title: "Best Self-Hosted Pastebin Solutions 2026: PrivateBin, MicroBin, and More"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted pastebin solutions in 2026. Compare PrivateBin, MicroBin, and Hastypaste for secure text and code sharing with Docker deployment guides."
---

Sharing code snippets, error logs, and configuration files is a daily routine for developers and system administrators. Public pastebin services like Pastebin.com have existed for decades, but they come with serious limitations: your data lives on someone else's server, there are no guarantees about deletion, and sensitive information like API keys or stack traces can be indexed, scraped, or exposed in data breaches.

A self-hosted pastebin solves all of these problems. You control where the data lives, how long it persists, and who can access it. For teams working on proprietary code, handling incident response logs, or sharing credentials during migrations, a self-hosted paste server is not a luxury — it is a practical necessity.

## Why Self-Host a Pastebin?

The case for running your own paste service is stronger than ever in 2026. Here is why organizations and individual developers are making the switch:

**Data sovereignty.** When you paste a stack trace containing database connection strings, or share a configuration file with internal endpoints, that data should not leave your infrastructure. Self-hosting ensures zero third-party exposure.

**Automatic expiration with real enforcement.** Public pastebins claim to support expiring links, but the data often persists on backup tapes and caches indefinitely. On your own server, expiration is enforced at the file level — when a paste expires, it is physically deleted.

**Private sharing within teams.** Need to share a one-time password, a migration script, or a debug log with a colleague? A self-hosted pastebin gives you internal URLs that are only accessible from your network or behind your authentication layer.

**No rate limits or ads.** Public services throttle heavy users and display advertisements. Your own instance has no artificial limits and no tracking scripts.

**Compliance requirements.** Industries subject to GDPR, HIPAA, or SOC 2 regulations cannot legally paste production logs or personally identifiable information on public platforms. Self-hosting keeps you within compliance boundaries.

**Zero dependency risk.** Public pastebins shut down, change their terms of service, or go behind paywalls without notice. Your own instance stays available as long as your server is running.

## Top Self-Hosted Pastebin Solutions

Three open-source pastebin applications stand out in 2026, each targeting a different use case. Understanding their differences will help you pick the right tool for your environment.

### PrivateBin — The Privacy-First Champion

PrivateBin is the most feature-complete self-hosted pastebin available. Its defining characteristic is **zero-knowledge encryption**: all encryption and decryption happens in the browser using JavaScript. The server never sees the plaintext content of any paste. Even if someone compromises the server, they only see encrypted blobs.

PrivateBin supports password-protected pastes, burn-after-reading mode, syntax highlighting for over 200 programming languages, file attachments, discussion threads on pastes, and fine-grained expiration controls. It stores data in flat files by default but also supports MySQL, MariaDB, PostgreSQL, SQLite, Google Cloud Storage, and Amazon S3 as backends.

The project has been actively maintained since 2013 and has a large community. It is the default choice for anyone who takes privacy seriously.

### MicroBin — The Minimalist Alternative

MicroBin is a newer entrant designed around simplicity. Written in Rust, it is distributed as a single static binary with no external dependencies beyond a SQLite database. The entire application is contained in one file, making deployment and upgrades trivial.

MicroBin offers paste creation with expiration, syntax highlighting, a clean modern interface, and an optional read-only API. It does not have client-side encryption, but it is significantly easier to deploy than PrivateBin and consumes far fewer resources.

The project is ideal for homelab users, small teams, or anyone who wants a "set it and forget it" paste server without managing PHP runtimes or web servers.

### Hastypaste — The Speed-Oriented Option

Hastypaste is a lightweight paste server built in Python with a focus on speed and simplicity. It provides a minimal web interface, a straightforward REST API, and supports automatic paste expiration. It is designed to be the spiritual successor to services like hastebin.com but self-hosted.

Hastypaste is the simplest of the three options to understand and modify. If you want a paste server that you can customize, extend, or integrate into existing Python-based infrastructure, this is the platform to start with.

## Feature Comparison

| Feature | PrivateBin | MicroBin | Hastypaste |
|---|---|---|---|
| Language | PHP | Rust | Python |
| Client-side encryption | Yes | No | No |
| Password-protected pastes | Yes | No | No |
| Burn-after-reading | Yes | No | No |
| File attachments | Yes | No | No |
| Syntax highlighting | 200+ languages | Yes | Yes |
| Discussion threads | Yes | No | No |
| REST API | Limited | Yes | Yes |
| Database support | Flat files, MySQL, PostgreSQL, SQLite, S3, GCS | SQLite | SQLite |
| Docker image | Official | Official | Community |
| Binary size | ~5 MB | ~8 MB single binary | ~50 MB with deps |
| RAM usage | ~50 MB | ~10 MB | ~30 MB |
| Active development | Yes | Yes | Yes |
| License | zlib | MIT | MIT |

## Deploying PrivateBin with Docker

PrivateBin is the recommended choice for most users. Here is a complete deployment guide.

### Basic Docker Compose Setup

Create a directory for your PrivateBin installation:

```bash
mkdir -p ~/privatebin/{cfg,data}
cd ~/privatebin
```

Create the `docker-compose.yml` file:

```yaml
version: "3.8"

services:
  privatebin:
    image: privatebin/nginx-fpm-alpine:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/srv/data
      - ./cfg/conf.php:/srv/cfg/conf.php:ro
    environment:
      - TZ=UTC
```

Start the service:

```bash
docker compose up -d
```

Access PrivateBin at `http://localhost:8080`. The default configuration works out of the box with flat-file storage.

### Hardening PrivateBin for Production

The default configuration is functional but not hardened. Create a custom `cfg/conf.php` for production use:

```php
<?php
return [
    'main' => [
        'name' => 'My PrivateBin',
        'discussion' => false,
        'opendiscussion' => false,
        'password' => true,
        'fileupload' => false,
        'burnafterreadingselected' => true,
        'defaultformatter' => 'syntaxhighlighting',
        'syntaxhighlightingtheme' => 'dark',
        'sizelimit' => 10485760,
        'template' => 'bootstrap-dark',
        'info' => 'Zero-knowledge pastebin — server cannot read your data.',
        'cspheader' => "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; media-src data:; base-uri 'self'; form-action 'self'; connect-src 'self';",
    ],
    'expire' => [
        'default' => '1week',
        'max' => '1month',
    ],
    'purge' => [
        'limit' => 300,
        'batchsize' => 10,
    ],
    'model' => [
        'class' => 'Filesystem',
    ],
    'model_options' => [
        'dir' => '/srv/data',
    ],
    'sri' => [
        'disable' => false,
    ],
];
```

Restart to apply:

```bash
docker compose down && docker compose up -d
```

Key production changes: disabled public discussions, enabled password protection by default, set a dark theme, capped paste size at 10 MB, limited maximum expiration to one month, and added a strict Content Security Policy header.

### Adding Nginx Reverse Proxy with TLS

For production access, place PrivateBin behind Nginx with Let's Encrypt TLS:

```nginx
server {
    listen 80;
    server_name paste.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name paste.example.com;

    ssl_certificate /etc/letsencrypt/live/paste.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/paste.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### PostgreSQL Backend for High-Traffic Deployments

If you expect more than a few hundred pastes per day, switch from flat files to PostgreSQL:

```yaml
version: "3.8"

services:
  privatebin:
    image: privatebin/nginx-fpm-alpine:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./cfg/conf.php:/srv/cfg/conf.php:ro
    environment:
      - TZ=UTC
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: privatebin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: privatebin
    volumes:
      - privatebin_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U privatebin"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  privatebin_db:
```

Update `conf.php` to use the database backend:

```php
'model' => [
    'class' => 'Database',
],
'model_options' => [
    'dsn' => 'pgsql:host=postgres;dbname=privatebin',
    'tbl' => 'paste',
    'usr' => 'privatebin',
    'pwd' => getenv('DB_PASSWORD'),
],
```

## Deploying MicroBin with Docker

MicroBin is ideal when you want the simplest possible setup. The entire application is a single binary.

### Docker Compose

```yaml
version: "3.8"

services:
  microbin:
    image: danielszabo99/microbin:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/uploads
    environment:
      - MICROBIN_PUBLIC_URI=http://paste.example.com
      - MICROBIN_SITE_NAME=My MicroBin
      - MICROBIN_ADMIN_USERNAME=admin
      - MICROBIN_ADMIN_PASSWORD=change-me
      - MICROBIN_HIGHLIGHTSYNTAX=true
      - MICROBIN_MAX_BURNS=50
      - MICROBIN_DEFAULT_EXPIRY=1day
      - MICROBIN_FOOTER_TEXT="Powered by MicroBin"
```

Start it:

```bash
docker compose up -d
```

That is the entire configuration. MicroBin handles everything internally — no separate web server, no PHP runtime, no database configuration. The SQLite database is created automatically in the `uploads` directory.

### Running as a Systemd Service (No Docker)

If you prefer not to use Docker, MicroBin can run as a native systemd service:

```bash
# Download the latest release binary
curl -L -o /usr/local/bin/microbin \
  https://github.com/szabodanika/microbin/releases/latest/download/microbin-x86_64-linux

chmod +x /usr/local/bin/microbin
mkdir -p /var/lib/microbin
```

Create the systemd unit:

```ini
[Unit]
Description=MicroBin Pastebin Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
ExecStart=/usr/local/bin/microbin
WorkingDirectory=/var/lib/microbin
Environment=MICROBIN_PUBLIC_URI=http://paste.example.com
Environment=MICROBIN_SITE_NAME=MicroBin
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo mv microbin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now microbin
```

## Deploying Hastypaste

Hastypaste offers a middle ground with its Python-based architecture and clean API.

### Docker Compose

```yaml
version: "3.8"

services:
  hastypaste:
    image: ghcr.io/hastypaste/hastypaste:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data:/data
    environment:
      - HP_MAX_LENGTH=400000
      - HP_PASTE_EXPIRY=86400
      - HP_BIND=0.0.0.0:8080
```

Start the service:

```bash
docker compose up -d
```

Hastypaste exposes a simple REST API for programmatic paste creation:

```bash
# Create a paste via API
curl -X POST http://localhost:8080/paste \
  -H "Content-Type: text/plain" \
  -d '{"content": "print(\"hello world\")", "syntax": "python", "expiry": 3600}'

# Returns: {"key": "abc123", "url": "http://localhost:8080/abc123"}

# Retrieve a paste
curl http://localhost:8080/raw/abc123
```

## Integrating Pastebin into Your Workflow

A self-hosted pastebin becomes genuinely useful when integrated into your daily tools. Here are practical integration patterns.

### CLI Shortcut for Quick Pastes

Add a shell function to `~/.bashrc` or `~/.zshrc` for sending files to your PrivateBin instance:

```bash
pastebin() {
    local file="${1:--}"
    local expire="${2:-1day}"

    curl -s -X POST "https://paste.example.com" \
        -d "content=$(cat "$file")" \
        -d "pasteFormat=text" \
        -d "expiration=${expire}" | \
        grep -oP 'https://[^"]+' | head -1
}

# Usage:
# pastebin error.log 1hour
# cat config.yaml | pastebin - 1week
```

### Vim Integration

Add this to your `~/.vimrc` to send the current buffer to your paste server:

```vim
function! PasteToPrivateBin()
    let l:content = join(getline(1, '$'), "\n")
    let l:cmd = 'echo "' . l:content . '" | curl -s -X POST https://paste.example.com -d "content=-" -d "pasteFormat=' . &ft . '"'
    let l:result = system(l:cmd)
    echo l:result
endfunction

nnoremap <leader>p :call PasteToPrivateBin()<CR>
```

### VS Code Integration

Several extensions support custom pastebin backends. Install "Paste Image" or "Clipboard to URL" and configure the endpoint to point to your MicroBin or Hastypaste API. For PrivateBin, the CLI approach via shell task integration works well:

```json
{
    "tasks": [
        {
            "label": "Paste to PrivateBin",
            "type": "shell",
            "command": "cat ${file} | pastebin - 1week",
            "problemMatcher": []
        }
    ]
}
```

### CI/CD Integration

Include paste creation in your CI pipeline for sharing build artifacts, test logs, or deployment reports:

```yaml
# GitHub Actions example
- name: Upload Build Log to PrivateBin
  if: failure()
  run: |
    PASTE_URL=$(curl -s -X POST "https://paste.example.com" \
      -d "content=$(cat build.log)" \
      -d "pasteFormat=text" \
      -d "expiration=1week" | \
      grep -oP 'https://[^"]+' | head -1)
    echo "::notice::Build log available at: $PASTE_URL"
```

## Security Best Practices

Running a pastebin on your infrastructure introduces security considerations that are worth addressing proactively.

**Rate limiting.** Public-facing paste servers attract abuse. Add rate limiting to your reverse proxy:

```nginx
limit_req_zone $binary_remote_addr zone=paste:10m rate=10r/m;

server {
    location / {
        limit_req zone=paste burst=20 nodelay;
        proxy_pass http://127.0.0.1:8080;
    }
}
```

**Content scanning.** Consider running uploaded content through a malware scanner if you allow file attachments. ClamAV integrates well via a cron job that scans the paste data directory:

```bash
0 */6 * * * clamscan -r /var/lib/privatebin/data --move=/var/lib/privatebin/quarantine --log=/var/log/clamscan.log
```

**Network segmentation.** For internal team use, restrict access to your LAN or VPN. With Docker, bind to localhost only and let Nginx handle external access with authentication:

```yaml
ports:
  - "127.0.0.1:8080:8080"
```

**Regular backups.** Even with auto-expiration, back up your paste data directory. With PrivateBin, this is a simple rsync:

```bash
rsync -avz /var/lib/privatebin/data/ backup-server:/backups/privatebin/
```

**Disable external paste submission.** If the pastebin is strictly internal, add HTTP basic authentication or restrict by IP range in your Nginx configuration:

```nginx
allow 10.0.0.0/8;
allow 172.16.0.0/12;
allow 192.168.0.0/16;
deny all;
```

## Which Solution Should You Choose?

The decision comes down to your specific requirements:

**Choose PrivateBin** if privacy is your top priority. Client-side encryption means the server operator (even you) cannot read paste contents. This is critical for regulated industries or when sharing sensitive credentials. It is also the best choice if you need file attachments, discussion threads, or enterprise-grade database backends.

**Choose MicroBin** if you value simplicity and low resource usage. A single binary with no dependencies, minimal RAM footprint, and a clean interface make it ideal for homelab deployments, Raspberry Pi instances, or small teams that need a reliable paste server without complexity.

**Choose Hastypaste** if you need a programmable API and Python-based extensibility. It is the easiest to customize and integrate into existing Python workflows. The straightforward REST API makes it a natural fit for automated pipelines and tooling.

All three solutions can be running on a $5 VPS or a Raspberry Pi with less than 100 MB of RAM. The barrier to self-hosting a pastebin has never been lower, and the privacy and control benefits make it one of the most practical self-hosted services you can deploy today.
