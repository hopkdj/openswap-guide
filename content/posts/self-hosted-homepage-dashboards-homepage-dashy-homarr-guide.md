---
title: "Best Self-Hosted Homepage Dashboards: Homepage vs Dashy vs Homarr 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to the best self-hosted homepage dashboards in 2026. Compare Homepage, Dashy, and Homarr with setup guides, feature comparisons, and recommendations."
---

If you run even a modest number of self-hosted services — a media server, a few containers, monitoring tools, and maybe a git forge — you know the pain of bookmark sprawl. Every new service adds another port, another URL, another tab to juggle. A self-hosted homepage dashboard solves this once and for all: a single landing page that organizes all your services, shows their status at a glance, and doubles as a personalized browser start page.

In this guide, we compare the three most popular self-hosted dashboard projects in 2026 — **Homepage**, **Dashy**, and **Homarr** — and walk through concrete installation and configuration examples for each.

## Why Run a Self-Hosted Homepage Dashboard

Before diving into comparisons, it is worth understanding why a dedicated dashboard beats a simple bookmarks page.

### Centralized Service Discovery

A homelab or self-hosted environment typically includes a dozen or more services running across different machines, containers, and ports. A dashboard provides a single entry point — the first thing you see when you open your browser — with logically grouped links to everything that matters.

### Real-Time Status Monitoring

Unlike static bookmarks, self-hosted dashboards can ping your services and display their health status directly on the homepage. A green dot means everything is running; a red indicator tells you something needs attention before you even click.

### Information at a Glance

Modern dashboards integrate with service APIs to surface useful information without opening individual applications. You can see disk usage from your NAS, pending updates from your package manager, recent downloads from your torrent client, or calendar events — all on one page.

### Privacy and Full Control

Cloud-based start pages and dashboard services (like Momentum or Toby) collect browsing data and require accounts. A self-hosted dashboard lives entirely on your infrastructure. No telemetry, no accounts, no third-party servers. Your service list, your data, your rules.

### Zero Dependency on External Services

When your internet goes down, your cloud-based dashboard goes with it. A self-hosted homepage continues to work on your local network regardless of upstream connectivity, which is especially valuable for homelab operators who need access to local tools during outages.

## Overview of the Three Contenders

### Homepage (by gethomepage)

**Homepage** is a modern, highly configurable dashboard built with Next.js. It emphasizes clean design, rich service integrations, and a YAML-based configuration that is both human-readable and version-control-friendly. It supports dozens of built-in widgets for Docker, Kubernetes, various media servers, monitoring stacks, and more.

- **Repository:** `github.com/gethomepage/homepage`
- **Language:** JavaScript / Next.js
- **Configuration:** YAML files
- **Docker image:** `ghcr.io/gethomepage/homepage`

### Dashy (by lissy93)

**Dashy** is a feature-rich dashboard focused on extreme customizability. It supports themes, icons, authentication, multiple pages, and a built-in configuration editor with live preview. Its YAML-based config is supplemented by a web UI for making changes without editing files directly.

- **Repository:** `github.com/lissy93/dashy`
- **Language:** Vue.js
- **Configuration:** YAML + web UI editor
- **Docker image:** `lissy93/dashy`

### Homarr (byajnsh)

**Homarr** is a sleek, modern dashboard with drag-and-drop customization and deep integrations with popular self-hosted apps. It stands out for its visual editor — you customize the layout directly in the browser by dragging widgets around rather than editing config files.

- **Repository:** `github.com/ajnart/homarr`
- **Language:** TypeScript / Next.js
- **Configuration:** Web-based visual editor
- **Docker image:** `ghcr.io/ajnsh/homarr`

## Feature Comparison

| Feature | Homepage | Dashy | Homarr |
|---------|----------|-------|--------|
| **UI Framework** | Next.js (React) | Vue.js | Next.js (React) |
| **Configuration** | YAML files | YAML + web editor | Visual drag-and-drop |
| **Docker Integration** | Excellent (native) | Good | Good |
| **Status Checking** | Built-in | Built-in | Built-in |
| **Authentication** | Optional (middleware) | Built-in (OIDC, form) | Built-in |
| **Multi-page Support** | Yes (YAML sections) | Yes (tabs/pages) | Yes (boards) |
| **Widget Ecosystem** | 40+ built-in widgets | Moderate | Moderate |
| **Kubernetes Support** | Yes | No | No |
| **Themes** | Limited (CSS overrides) | Extensive (custom + preset) | Limited |
| **Icon Options** | Auto-fetch + custom | Auto-fetch + 100+ built-in | Auto-fetch + custom |
| **Mobile Responsive** | Yes | Yes | Yes |
| **Search** | No | Yes (built-in) | Yes (built-in) |
| **Performance** | Very fast | Moderate | Fast |
| **API Access** | No | Yes | Yes (limited) |
| **Active Development** | Very active | Active | Very active |
| **Docker Image Size** | ~200 MB | ~300 MB | ~150 MB |
| **Resource Usage** | Low (~80 MB RAM) | Moderate (~150 MB RAM) | Low (~100 MB RAM) |

## Detailed Breakdown

### Homepage: The Homelab Operator's Choice

Homepage is the go-to dashboard for homelab enthusiasts who want deep service integrations with minimal fuss. Its strength lies in its extensive widget library and seamless Docker integration.

**Key strengths:**

- **Rich widget ecosystem** — Over 40 built-in widgets covering Docker, Proxmox, Kubernetes, Pi-hole, AdGuard Home, Sonarr, Radarr, Plex, Transmission, qBittorrent, and many more. These widgets display real data: download speeds, upcoming TV episodes, disk usage, container counts.
- **YAML-first configuration** — Perfect for GitOps workflows. Store your configuration in a Git repository, version your changes, and roll back if something breaks.
- **Docker socket integration** — Homepage can read your Docker socket directly and auto-discover services labeled for inclusion. This means adding a new container to your dashboard can be as simple as adding a Docker label.
- **Excellent performance** — Built with Next.js, Homepage renders quickly and uses minimal resources.
- **Smart home integration** — Widgets for Home Assistant allow displaying sensor data, switch states, and automation status directly on the dashboard.

**Weaknesses:**

- No built-in authentication (relies on reverse proxy auth or network-level access control).
- Configuration requires editing YAML files — no visual editor.
- Limited theme customization compared to Dashy.

### Dashy: The Power User's Playground

Dashy is the most feature-complete dashboard in terms of raw capabilities. If you want granular control over every pixel, Dashy delivers.

**Key strengths:**

- **Web-based configuration editor** — Edit your dashboard from within the browser with live preview. No need to SSH in and edit YAML files.
- **Built-in authentication** — Supports form-based login, OIDC, and Keycloak integration out of the box.
- **Extensive theming** — Dozens of preset color schemes plus full CSS customization. You can make Dashy look exactly how you want.
- **Built-in search** — Type to search across all your services and bookmarks instantly.
- **Multiple pages and sections** — Organize complex setups across tabs or separate pages.
- **API for programmatic access** — Dashy exposes an API that external tools can use to query and modify the dashboard.

**Weaknesses:**

- Heavier resource usage than competitors.
- The sheer number of options can be overwhelming for new users.
- Docker integration is less polished than Homepage's label-based auto-discovery.
- Some features require the paid "Pro" version (though the open-source version is fully functional for most users).

### Homarr: The Visual Customizer

Homarr takes a fundamentally different approach: instead of writing YAML, you build your dashboard visually by dragging and dropping widgets and links directly on the page.

**Key strengths:**

- **Drag-and-drop layout** — Customize everything visually. Resize widgets, rearrange sections, and position items exactly where you want them without touching a config file.
- **Modern, polished UI** — Homarr has one of the best-looking default interfaces among dashboard projects. It feels like a premium product out of the box.
- **App integrations** — Deep integrations with popular self-hosted applications including Sonarr, Radarr, Lidarr, qBittorrent, Transmission, Pi-hole, and Home Assistant.
- **Built-in authentication** — User management with role-based access control.
- **Easy to get started** — New users can have a working dashboard in under 5 minutes with no configuration files.

**Weaknesses:**

- Less suitable for GitOps workflows since configuration is stored in a database rather than YAML files.
- Fewer built-in widgets compared to Homepage.
- No Kubernetes support.
- The visual editor, while convenient, can feel limiting for complex layouts that are trivial in YAML.

## Installation and Setup

### Installing Homepage

Homepage is straightforward to deploy with Docker Compose. Create a directory for your configuration and launch the stack:

```bash
mkdir -p ~/homepage/config
cd ~/homepage
```

Create the Docker Compose file:

```yaml
# docker-compose.yml
version: "3.8"
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - ./config:/app/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=America/New_York
```

Now create the configuration files. Homepage uses a `settings.yaml` for global settings and a `services.yaml` for your service list:

```yaml
# config/settings.yaml
title: My Homelab
background:
  image: https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1920&q=80
  blur: sm
  saturate: 50
  brightness: 50
  opacity: 50

cardBlur: sm
useServiceWorker: true

layout:
  Media:
    icon: mdi-play-circle
  Infrastructure:
    icon: mdi-server
  Monitoring:
    icon: mdi-chart-box
```

```yaml
# config/services.yaml
- Media:
    - Plex:
        icon: plex
        href: http://192.168.1.100:32400
        description: Media server
        widget:
          type: plex
          url: http://192.168.1.100:32400
          key: YOUR_PLEX_TOKEN

    - Jellyfin:
        icon: jellyfin
        href: http://192.168.1.100:8096
        description: Alternative media server
        widget:
          type: jellyfin
          url: http://192.168.1.100:8096
          key: YOUR_JELLYFIN_API_KEY

    - Sonarr:
        icon: sonarr
        href: http://192.168.1.100:8989
        description: TV series manager
        widget:
          type: sonarr
          url: http://192.168.1.100:8989
          key: YOUR_SONARR_API_KEY

- Infrastructure:
    - Proxmox:
        icon: proxmox
        href: https://192.168.1.50:8006
        description: Hypervisor

    - Gitea:
        icon: gitea
        href: http://192.168.1.100:3000
        description: Git forge

- Monitoring:
    - Uptime Kuma:
        icon: uptime-kuma
        href: http://192.168.1.100:3001
        description: Service monitoring

    - Grafana:
        icon: grafana
        href: http://192.168.1.100:3000
        description: Metrics dashboards
```

Add Docker auto-discovery labels to any container you want Homepage to pick up automatically:

```yaml
# Example: adding labels to an existing service
services:
  nginx:
    image: nginx:alpine
    labels:
      - homepage.group=Infrastructure
      - homepage.name=Nginx
      - homepage.icon=nginx
      - homepage.href=http://192.168.1.100
```

Start the stack:

```bash
docker compose up -d
```

Access your dashboard at `http://your-server-ip:3000`.

### Installing Dashy

Dashy deployment is equally simple with Docker Compose:

```bash
mkdir -p ~/dashy
cd ~/dashy
```

Create the Docker Compose file:

```yaml
# docker-compose.yml
version: "3.8"
services:
  dashy:
    image: lissy93/dashy:latest
    container_name: dashy
    restart: unless-stopped
    ports:
      - "4000:8080"
    volumes:
      - ./conf.yml:/app/public/conf.yml
      - ./item-icons:/app/public/item-icons
    environment:
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "node", "/app/services/healthcheck"]
      interval: 1m30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Create a comprehensive configuration file:

```yaml
# conf.yml
pageInfo:
  title: My Dashboard
  description: Self-hosted services dashboard
  navLinks:
    - title: Documentation
      path: https://dashy.to/docs
    - title: GitHub
      path: https://github.com/lissy93/dashy

appConfig:
  theme: cyber
  layout: auto
  iconSize: medium
  language: en
  auth:
    users:
      - user: admin
        hash: "$argon2id$v=19$m=65536,t=3,p=4$..."
    enableUserAccounts: true
    enableLoginScreen: true

sections:
  - name: Media
    icon: fas fa-play-circle
    items:
      - title: Plex
        description: Media Server
        icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/plex.png
        url: http://192.168.1.100:32400
        statusCheck: true
        statusCheckUrl: http://192.168.1.100:32400/identity

      - title: Jellyfin
        description: Media Server
        icon: jellyfin
        url: http://192.168.1.100:8096
        statusCheck: true

      - title: Navidrome
        description: Music Server
        icon: navidrome
        url: http://192.168.1.100:4533
        statusCheck: true

  - name: Infrastructure
    icon: fas fa-server
    items:
      - title: Proxmox
        icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/proxmox.png
        url: https://192.168.1.50:8006
        statusCheck: true

      - title: Nextcloud
        icon: nextcloud
        url: http://192.168.1.100:8080
        statusCheck: true

  - name: Monitoring
    icon: fas fa-chart-line
    items:
      - title: Grafana
        icon: grafana
        url: http://192.168.1.100:3000

      - title: Uptime Kuma
        icon: uptime-kuma
        url: http://192.168.1.100:3001

  - name: Tools
    icon: fas fa-wrench
    items:
      - title: Vaultwarden
        icon: vaultwarden
        url: http://192.168.1.100:8088

      - title: Paperless-ngx
        icon: paperless
        url: http://192.168.1.100:8000
```

Start Dashy:

```bash
docker compose up -d
```

Access at `http://your-server-ip:4000`. Log in with the configured credentials and use the built-in config editor to make live changes.

### Installing Homarr

Homarr deployment uses Docker Compose with slightly different volume requirements:

```bash
mkdir -p ~/homarr/{configs,data,icons}
cd ~/homarr
```

Create the Docker Compose file:

```yaml
# docker-compose.yml
version: "3.8"
services:
  homarr:
    image: ghcr.io/ajnsh/homarr:latest
    container_name: homarr
    restart: unless-stopped
    ports:
      - "7575:7575"
    volumes:
      - ./configs:/app/data/configs
      - ./data:/data
      - ./icons:/app/public/icons
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - SECRET_ENCRYPTION_KEY=your-secret-key-at-least-32-characters-long
```

The `SECRET_ENCRYPTION_KEY` is used to encrypt stored credentials for service integrations. Generate a strong random key:

```bash
openssl rand -base64 48
```

Start Homarr:

```bash
docker compose up -d
```

Access at `http://your-server-ip:7575`. You will be prompted to create an admin account on first visit. After logging in, click the "Edit Mode" button in the top-right corner to start customizing your dashboard visually.

To add a service link:
1. Click "Add Item" in edit mode.
2. Enter the service name and URL.
3. Homarr auto-detects the icon from a built-in library.
4. Drag the new item to position it.

To add a widget (e.g., Docker container status):
1. Click "Add Widget" in edit mode.
2. Select the widget type (e.g., "Docker").
3. Configure the widget to point to your Docker socket.
4. Resize and position as needed.

Homarr's visual editor makes it incredibly easy to iterate on your layout — changes are applied instantly with no config file editing or container restarts required.

## Advanced Configurations

### Reverse Proxy Setup with Nginx

For production use, you will want to place your dashboard behind a reverse proxy with HTTPS. Here is an Nginx configuration that works for any of the three dashboards:

```nginx
server {
    listen 80;
    server_name dashboard.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name dashboard.example.com;

    ssl_certificate /etc/letsencrypt/live/dashboard.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dashboard.example.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        proxy_pass http://127.0.0.1:3000;  # Change port as needed
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (needed by Homepage and Homarr)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Obtain an SSL certificate with Certbot:

```bash
sudo certbot --nginx -d dashboard.example.com
```

### Integrating with Authelia or Authentik

For dashboards without built-in authentication (like Homepage), you can add authentication using a reverse proxy with Authelia or Authentik.

Here is a Caddy configuration with Authelia integration:

```caddyfile
dashboard.example.com {
    encode gzip
    reverse_proxy localhost:3000

    forward_auth authelia:9091 {
        uri /api/verify?rd=https://auth.example.com/
        copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
    }
}
```

This setup allows you to protect your dashboard with two-factor authentication, biometric login via WebAuthn, or single sign-on through your existing identity provider.

### Using Homepage with Docker Labels for Auto-Discovery

One of Homepage's most powerful features is auto-discovery via Docker labels. Instead of manually adding every service to `services.yaml`, you can label your containers and Homepage will find them automatically:

```yaml
# docker-compose.yml for a typical service
services:
  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    ports:
      - "7878:7878"
    labels:
      - homepage.group=Media Management
      - homepage.name=Radarr
      - homepage.icon=radarr
      - homepage.href=http://localhost:7878
      - homepage.widget.type=radarr
      - homepage.widget.url=http://localhost:7878
      - homepage.widget.key=${RADARR_API_KEY}

  bazarr:
    image: lscr.io/linuxserver/bazarr:latest
    container_name: bazarr
    ports:
      - "6767:6767"
    labels:
      - homepage.group=Media Management
      - homepage.name=Bazarr
      - homepage.icon=bazarr
      - homepage.href=http://localhost:6767
      - homepage.widget.type=bazarr
      - homepage.widget.url=http://localhost:6767
      - homepage.widget.key=${BAZARR_API_KEY}
```

This approach means your dashboard configuration lives alongside your service definitions, making it easy to maintain and version-control.

## Which Dashboard Should You Choose?

The answer depends on your priorities and technical comfort level.

### Choose Homepage if:

- You want the richest set of built-in widgets and service integrations.
- You prefer YAML-based configuration and GitOps workflows.
- You run Docker or Kubernetes and want seamless container integration.
- Performance and low resource usage are important to you.
- You already have authentication handled at the network or reverse proxy level.

Homepage is the best choice for experienced homelab operators who want maximum information density and deep integrations with their existing infrastructure.

### Choose Dashy if:

- You want built-in authentication and access control.
- You need extensive theme customization and visual variety.
- You want a built-in search function for finding services quickly.
- You prefer having both a YAML config file AND a web-based editor.
- You need an API for programmatic dashboard management.

Dashy is ideal for users who want the most features out of the box and are willing to accept slightly higher resource usage in exchange for functionality.

### Choose Homarr if:

- You want the easiest setup experience with zero configuration files.
- Visual drag-and-drop customization is important to you.
- You prefer a modern, polished interface without extensive tweaking.
- You need built-in user authentication with role-based access.
- You are newer to self-hosting and want the gentlest learning curve.

Homarr is the best starting point for beginners and anyone who values a visual editing experience over YAML configuration.

## Quick Decision Matrix

| Priority | Recommendation |
|----------|---------------|
| Most widget integrations | Homepage |
| Easiest to set up | Homarr |
| Best built-in security | Dashy |
| Lowest resource usage | Homepage |
| Best visual customization | Dashy |
| Best for Kubernetes | Homepage |
| Best for beginners | Homarr |
| Best for GitOps workflows | Homepage |
| Most features out of the box | Dashy |
| Best default appearance | Homarr |

## Conclusion

All three projects — Homepage, Dashy, and Homarr — are excellent choices for a self-hosted homepage dashboard. They are all actively maintained, free and open-source, and Docker-ready. The "best" one depends entirely on your workflow preferences and technical needs.

For a homelab with dozens of services where every container's status matters, Homepage's widget ecosystem and Docker integration are unmatched. For a family or team environment where different users need different access levels, Dashy's built-in authentication and theming options shine. For anyone who wants to get a beautiful, functional dashboard running in under five minutes without touching a config file, Homarr is the clear winner.

The good news is that all three are lightweight enough to run simultaneously on a single machine. Try them all, see which one fits your workflow, and stick with the one that makes managing your self-hosted services feel effortless.
