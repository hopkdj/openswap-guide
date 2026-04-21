---
title: "SearXNG vs Whoogle vs LibreX: Best Self-Hosted Private Search Engines 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Compare SearXNG, Whoogle, and LibreX — the top open-source, self-hosted private search engines. Complete installation guides, feature comparison, and setup instructions for 2026."
---

Google tracks every query you make, builds a profile of your interests, and sells that data to advertisers. Even privacy-focused alternatives like DuckDuckGo still collect some information and rely on centralized infrastructure. If you want truly private search with zero tracking, zero profiling, and zero data retention, self-hosting is the answer.

This guide compares the three best open-source, self-hosted private search engines — **SearXNG**, **Whoogle**, and **LibreX** — with full installation instructions, feature comparisons, and deployment configurations for 2026.

## Why Self-Host Your Own Search Engine

Self-hosting a private search engine gives you capabilities no cloud service can match:

- **Zero tracking**: Your queries never leave your server. No IP logging, no cookies, no fingerprinting.
- **No data retention**: Results are fetched in real-time and discarded. Nothing is stored.
- **Full control**: Choose your own search backends, rate limits, caching strategies, and filters.
- **Multi-engine aggregation**: Combine results from Google, Bing, DuckDuckGo, Wikipedia, and dozens of sources into one view.
- **Bypass censorship**: Route requests through your own infrastructure to avoid geo-restrictions and search manipulation.
- **Family and team use**: Deploy once on your home server and share with your household or organization.

Whether you're a privacy advocate, a developer who searches constantly, or a team that needs shared search infrastructure, a self-hosted search engine pays for itself in control and peace of mind.

---

## What Are Self-Hosted Private Search Engines?

Self-hosted private search engines are open-source applications that you run on your own server. They work in two main ways:

1. **Meta-search engines**: Query multiple upstream search engines (Google, Bing, DuckDuckGo, etc.) on your behalf, aggregate the results, strip all tracking parameters, and return clean results to you. You're the only client — no shared pool of users.

2. **Proxy search engines**: Act as a privacy-preserving proxy to a single upstream engine (usually Google). They rewrite requests to remove tracking, strip ads, and return clean results — all without the upstream engine ever seeing your real IP.

Both approaches are dramatically more private than using any commercial search engine directly.

---

## SearXNG: The Most Feature-Rich Meta-Search Engine

**SearXNG** is the actively maintained fork of the original SearX project. It's a full-featured meta-search engine that queries over 70 different search services — web, images, videos, music, maps, news, science, files, IT, social media, and more — and returns aggregated, de-duplicated results with zero tracking.

### Key Features

- **70+ search engines** across 26 categories including web, images, videos, torrents, scientific papers, and software packages
- **150+ language/locale combinations** with automatic detection
- **JSON/CSV output** for programmatic access and API usage
- **Built-in result filtering** by date, engine, category, and safe search level
- **Custom engine support** — add your own search backends via YAML configuration
- **OpenSearch and RSS feed** support for browser integration
- **Plugin system** with hotkey support, self-information display, and URL rewriting
- **Rate limiting and caching** built in to avoid overwhelming upstream providers
- **Tor and proxy support** for maximum anonymity

### [docker](https://www.docker.com/) Installation

The fastest way to deploy SearXNG is with Docker:

```bash
mkdir -p ~/searxng && cd ~/searxng

cat > docker-compose.yml << 'EOF'
version: "3.8"
services:
  searxng:
    image: docker.io/searxng/searxng:latest
    container_name: searxng
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - SEARXNG_BASE_URL=http://localhost:8080/
      - SEARXNG_SECRET=$(openssl rand -hex 32)
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
EOF

# Create settings directory with default config
docker run --rm -d --name searxng-temp \
  -e SEARXNG_BASE_URL=http://localhost:8080/ \
  docker.io/searxng/searxng:latest
docker cp searxng-temp:/usr/local/searxng/searxng/settings.yml ./searxng/settings.yml
docker rm -f searxng-temp

# Start the service
docker compose up -d
```

### Essential Configuration

Edit `searxng/settings.yml` to customize your deployment:

```yaml
use_instance_settings: true

general:
  debug: false
  instance_name: "My Private Search"
  contact_url: false
  enable_metrics: false

search:
  safe_search: 0
  autocomplete: "google"
  default_lang: "auto"
  formats:
    - html
    - json

server:
  port: 8080
  bind_address: "0.0.0.0"
  secret_key: "your-secret-key-here"
  limiter: true
  image_proxy: true
  method: "POST"

engines:
  - name: google
    engine: google
    shortcut: g
    disabled: false
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
    disabled: false
  - name: wikipedia
    engine: wikipedia
    shortcut: wp
    disabled: false

outgoing:
  request_timeout: 6.0
  max_request_timeout: 15.0
  useragent_suffix: ""
  pool_connections: 100
  pool_maxsize: 20
```

### Adding a Reverse Proxy

For production use with HTTPS, put SearxNG behind Caddy:

```bash
cat > Caddyfile << 'EOF'
search.yourdomain.com {
    reverse_proxy localhost:8080
    encode gzip
}
EOF

docker run -d --name caddy \
  -p 443:443 -p 80:80 \
  -v ./Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  -v caddy_config:/config \
  --restart unless-stopped \
  caddy:alpine
```

---

## Whoogle: Clean, Ad-Free Google Search Proxy

**Whoogle** (Webapp Hoogling on Google) takes a different approach — instead of aggregating multiple engines, it acts as a lightweight, privacy-preserving proxy to Google Search specifically. It strips all ads, AMP links, tracking parameters, and JavaScript from Google results, returning clean HTML that looks like a minimalist version of Google.

### Key Features

- **Google results without tracking**: All queries are proxied through your server — Google never sees your IP
- **Zero ads and AMP links**: Results are clean and focused
- **No JavaScript required**: Works with JS disabled in your browser
- **Dark mode and themes**: Built-in light, dark, and system theme support
- **Custom CSS support**: Full theme customization
- **Tor and SOCKS5 proxy support**: Route through Tor for maximum anonymity
- **View image results** directly without leaving the proxy
- **Random user agent rotation** to prevent fingerprinting
- **URL tracking parameter removal**: Strips all `utm_` and analytics parameters
- **Near-zero resource usage**: Lightweight Flask app that runs on a Raspberry Pi

### Docker Installation

```bash
mkdir -p ~/whoogle && cd ~/whoogle

cat > docker-compose.yml << 'EOF'
version: "3.8"
services:
  whoogle:
    image: benbusby/whoogle-search:latest
    container_name: whoogle
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - WHOOGLE_AUTOCOMPLETE=1
      - WHOOGLE_ALT_TW=nitter.net
      - WHOOGLE_ALT_YT=invidious.example.com
      - WHOOGLE_ALT_IG=bibliogram.art
      - WHOOGLE_ALT_RD=libreddit.example.com
      - WHOOGLE_CONFIG_STYLE="body{background:#1a1a2e;color:#eee;}"
      - WHOOGLE_CONFIG_THEME="dark"
      - WHOOGLE_CONFIG_SAFE=0
      - WHOOGLE_CONFIG_ALTS=1
      - WHOOGLE_CONFIG_NEW_TAB=1
      - EXPOSE_PORT=5000
EOF

docker compose up -d
```

### Advanced Configuration with Tor

For maximum privacy, route all Whoogle requests through Tor:

```bash
cat >> docker-compose.yml << 'EOF'
  tor:
    image: peterdavehello/tor-socks-proxy:latest
    container_name: whoogle-tor
    restart: unless-stopped
    depends_on:
      - whoogle

  whoogle:
    environment:
      - WHOOGLE_PROXY_TYPE=5
      - WHOOGLE_PROXY_LOC=tor
      - WHOOGLE_PROXY_USER=
      - WHOOGLE_PROXY_PASS=
    depends_on:
      - tor
EOF

docker compose up -d
```

### URL Rewriting for Privacy

Whoogle can automatically replace links to known tracking services with privacy-respecting alternatives:

```bash
# Add to your docker-compose.yml environment section:
- WHOOGLE_ALT_TW=nitter.privacytools.io
- WHOOGLE_ALT_YT=yewtu.be
- WHOOGLE_ALT_IG=bibliogram.1d4.us
- WHOOGLE_ALT_RD=libredd.it
- WHOOGLE_ALT_MD=md.vern.cc
- WHOOGLE_ALT_TL=lingva.ml
- WHOOGLE_ALT_SN=sepiasearch.org
- WHOOGLE_ALT_PIN=bingesushi.com
- WHOOGLE_ALT_REDDIT=libredd.it
```

---

## LibreX: Minimalist Framework for Privacy Search

**LibreX** is a minimalist PHP-based privacy search framework that supports multiple backends. It's designed to be extremely lightweight and easy to deploy, with a focus on simplicity and speed. LibreX can search via Google, Bing, DuckDuckGo, and Qwant backends while maintaining complete privacy.

### Key Features

- **Multiple search backends**: Google, Bing, DuckDuckGo, Qwant, and SearXNG
- **Extremely lightweight**: PHP-based, no dependencies, runs on any shared hosting
- **No JavaScript, no ads, no tracking**: Completely clean search experience
- **Responsive design**: Works on mobile and desktop out of the box
- **Video search** support via Invidious and Piped instances
- **Suggest API** integration for autocomplete
- **Simple PHP deployment**: No Docker required — just upload to any PHP web server
- **Torrent search** capability through optional backends
- **Zero database**: Stateless operation, nothing to maintain

### Docker Installation

```bash
mkdir -p ~/librex && cd ~/librex

cat > docker-compose.yml << 'EOF'
version: "3.8"
services:
  librex:
    image: ghcr.io/librex/librex:latest
    container_name: librex
    restart: unless-stopped
    ports:
      - "8888:80"
    environment:
      - LIBREX_BACKEND=google
      - LIBREX_SUGGEST_BACKEND=google
      - LIBREX_INVIOUS=https://yewtu.be
      - LIBREX_AUTO_COMPLETE=1
EOF

docker compose up -d
```

### Manual PHP Deployment

LibreX can also be deployed without Docker on any PHP server:

```bash
# Clone the repository
git clone https://github.com/hnhx/librex.git
cd librex

# Copy the configuration template
cp config.php config.local.php

# Edit the configuration
cat > config.local.php << 'EOF'
<?php
return [
    'instance_name' => 'My LibreX Instance',
    'backend' => 'google',
    'suggest_backend' => 'google',
    'auto_complete' => true,
    'dark_mode' => true,
    'language' => 'en',
    'invidious' => 'https://yewtu.be',
    'number_of_results' => 10,
    'safe_search' => 0,
    'disable_user_js' => true,
    'static_proxy' => '',
    'frontends' => [
        'twitter' => 'nitter.privacytools.io',
        'youtube' => 'yewtu.be',
        'reddit' => 'libredd.it',
        'instagram' => 'bibliogram.1d4.us',
    ],
    'api_keys' => [],
];
EOF

# Deploy with built-in PHP server (development)
php -S 0.0.0.0:8888

# Or deploy behind any PH[nginx](https://nginx.org/)able web server
# For Nginx + PHP-FPM:
```

```nginx
server {
    listen 80;
    server_name search.yourdomain.com;
    root /var/www/librex;
    index index.php;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }
}
```

---

## Feature Comparison: SearXNG vs Whoogle vs LibreX

| Feature | SearXNG | Whoogle | LibreX |
|---------|---------|---------|--------|
| **Type** | Meta-search aggregator | Google proxy | Multi-backend framework |
| **Search backends** | 70+ engines | Google only | Google, Bing, DDG, Qwant |
| **Language** | Python | Python | PHP |
| **Categories** | 26 (web, images, video, music, news, science, IT, files, etc.) | Web, images, news | Web, images, videos, torrents |
| **API output** | JSON, CSV | JSON | None (web only) |
| **Docker support** | Official image | Official image | Community image |
| **Tor support** | Yes (SOCKS) | Yes (SOCKS) | Via backend proxy |
| **Self-hosted** | Yes | Yes | Yes |
| **JavaScript required** | No | No | No |
| **Plugin system** | Yes | No | No |
| **Custom CSS/themes** | Limited | Yes (full) | Yes (via config) |
| **URL rewriting** | Yes | Extensive | Via config |
| **Resource usage** | Medium (~200MB RAM) | Low (~50MB RAM) | Very low (~30MB RAM) |
| **Mobile responsive** | Yes | Yes | Yes |
| **OpenSearch support** | Yes | No | No |
| **Federation** | Yes (instances can share config) | No | No |
| **Rate limiting** | Built-in | Basic | None |
| **Deployment com[plex](https://www.plex.tv/)ity** | Medium | Low | Very low |
| **Best for** | Power users, developers, teams | Google loyalists wanting privacy | Minimal deployments, shared hosting |

---

## Which One Should You Choose?

### Choose SearXNG if:

- You want access to **dozens of search engines** in one place
- You need **API access** with JSON output for automation
- You want **specialized search categories** (science, IT, music, torrents, news)
- You're building a **team or family search instance** with diverse needs
- You want **federation support** to share your instance with others
- You need **advanced filtering**, plugins, and customization options

SearXNG is the Swiss Army knife of private search. It's the most powerful and flexible option, ideal for power users who want to replace all their search needs with a single self-hosted instance.

### Choose Whoogle if:

- You **prefer Google's search results** but want zero tracking
- You want the **simplest possible deployment**
- You want **automatic URL rewriting** to replace tracking links with privacy alternatives
- You have **limited server resources** (runs on a Raspberry Pi Zero)
- You want a **Google-like interface** without the bloat, ads, and AMP links

Whoogle is the best choice for people who like Google's result quality but refuse to accept the privacy trade-offs. It's lightweight, simple, and gets the job done beautifully.

### Choose LibreX if:

- You want the **lightest possible deployment** (PHP, no Docker needed)
- You're on **shared hosting** without Docker support
- You prefer **simplicity over features**
- You want a **minimal, fast-loading interface**
- You need to deploy on a **resource-constrained VPS**

LibreX is the minimalist's choice. It's not as feature-rich as the others, but it's incredibly easy to deploy and uses virtually no resources.

---

## Production Deployment Checklist

Whichever option you choose, follow these steps for a production-ready deployment:

### 1. Use HTTPS

Never expose a search engine over plain HTTP. Use Caddy for automatic TLS:

```bash
# Caddy automatically obtains and renews TLS certificates
docker run -d --name caddy \
  -p 443:443 -p 80:80 \
  -v ./Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:alpine
```

### 2. Add Authentication (Optional)

If you're sharing your instance, add basic auth:

```nginx
# Nginx basic auth for search.yourdomain.com
location / {
    auth_basic "Private Search";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8080;
}

# Generate credentials
htpasswd -c /etc/nginx/.htpasswd username
```

### 3. Set Up Automated Backups

Back up your configuration files:

```bash
#!/bin/bash
# backup-search-config.sh
BACKUP_DIR="/backup/search-config"
mkdir -p "$BACKUP_DIR"

docker compose -f ~/searxng/docker-compose.yml down
tar czf "$BACKUP_DIR/searxng-$(date +%Y%m%d).tar.gz" ~/searxng/
docker compose -f ~/searxng/docker-compose.yml up -d

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
```

### 4. Monitor Uptime

Add your search instance to a monitoring tool:

```yaml
# Add to your uptime-kuma monitors
- name: "Private Search"
  url: "https://search.yourdomain.com"
  interval: 300
  retries: 3
```

### 5. Keep Software Updated

Set up automated updates with Watchtower:

```yaml
# Add to your docker-compose.yml
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 86400 --cleanup
```

---

## Conclusion

Self-hosting your own search engine is one of the highest-impact privacy upgrades you can make. Every search query you perform reveals something about you — your interests, your problems, your health concerns, your financial situation. By running SearXNG, Whoogle, or LibreX on your own server, you keep that data entirely under your control.

For most users, **SearXNG** offers the best balance of features, search engine variety, and customization. If you specifically want Google-quality results without the tracking, **Whoogle** is the perfect proxy. And if you need something ultra-lightweight that runs anywhere, **LibreX** gets the job done with minimal resources.

All three are free, open-source, and can be deployed in under five minutes. There's no reason to keep feeding your search data to companies that profit from it. Take back your privacy today.

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
