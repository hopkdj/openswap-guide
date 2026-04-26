---
title: "Homer vs Heimdall vs Flame: Best Self-Hosted Startpage Dashboard 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "homelab"]
draft: false
description: "Compare the top three self-hosted startpage dashboards in 2026: Homer, Heimdall, and Flame. Detailed feature comparison, Docker setup guides, and recommendations for homelab operators."
---

If you run a homelab or self-host multiple services, you know the frustration of managing a growing list of URLs, ports, and bookmarks. Every new container or application adds another address to remember. A self-hosted startpage dashboard solves this permanently: a single landing page that organizes all your services, shows their status, and becomes your browser's home page.

While tools like **Homepage**, **Dashy**, and **Homarr** focus on dynamic widget integrations and API-driven dashboards, a different class of tools prioritizes simplicity and speed. In this guide, we compare the three most popular lightweight self-hosted startpages in 2026 — **Homer**, **Heimdall**, and **Flame** — each offering a distinct approach to organizing your self-hosted services.

| Feature | Homer | Heimdall | Flame |
|---|---|---|---|
| **GitHub Stars** | 11,296 | 9,133 | 6,313 |
| **Language** | Vue | PHP | TypeScript |
| **License** | Apache-2.0 | MIT | MIT |
| **Last Updated** | Apr 2026 | Nov 2025 | Apr 2026 |
| **Docker Image** | `b4bz/homer` | `linuxserver/heimdall` | `pawelmalak/flame` |
| **Default Port** | 8080 | 80/443 | 5005 |
| **Configuration** | YAML file | Web UI | Web UI + env vars |
| **Built-in Search** | No | No | Yes |
| **Docker Integration** | No | No | Yes (auto-detect) |
| **Authentication** | No | No | Yes (password) |
| **Themes** | Yes (custom YAML) | Yes (built-in) | Yes (color picker) |
| **Bookmarks** | Yes | Yes | Yes |
| **Service Status** | Via API widgets | Health check | No |
| **Static Site** | Yes | No | No |

## Why Use a Self-Hosted Startpage Dashboard

Before comparing the tools, let's clarify why a lightweight startpage matters — especially if you already have monitoring stacks and container dashboards.

### Single Point of Entry

A startpage is the first thing you see when you open your browser. Instead of maintaining a bookmarks bar with 30+ entries, you get a clean, organized grid of your most-used services. Each entry can have a custom icon, name, and tag, making navigation instant.

### Zero External Dependencies

Unlike cloud-based startpages (Momentum, Toby, NightTab cloud), self-hosted startpages work entirely offline. When your internet connection drops, your startpage still loads from your local network. This is critical for homelab operators who need access to local tools during upstream outages.

### Privacy by Design

No telemetry, no accounts, no tracking. Your service list never leaves your server. Homer goes further — it's a fully static site served from disk, meaning there's literally no backend process to collect data.

### Complementary to Monitoring Dashboards

A startpage is not a replacement for tools like Uptime Kuma or Prometheus. It serves a different purpose: quick navigation. Where [Uptime Kuma monitors your services](../self-hosted-cron-job-monitoring-healthchecks-uptime-kuma-prometheus-guide-2026/) and [Portainer manages your containers](../self-hosted-container-management-dashboards-portainer-dockge-yacht-guide/), Homer, Heimdall, and Flame simply help you find and launch them.

## Homer: The Minimalist Static Homepage

**Homer** is a lightweight, static homepage generated from a single YAML configuration file. There is no database, no backend, and no web-based editor — just a YAML file you edit and the page updates on the next load. This simplicity is both its greatest strength and its most limiting factor.

### Key Features

- **Fully static**: Compiled at startup from YAML. Zero runtime processing.
- **YAML configuration**: Everything defined in `config.yml` — services, groups, messages, and theme.
- **Service status widgets**: Built-in API integrations to display status from AdGuard Home, Pi-hole, Sonarr, Radarr, Plex, and more.
- **Offline-first**: Once loaded, the page requires no server interaction.
- **Custom themes**: Fully customizable through CSS variables in the YAML config.

### Docker Compose Setup for Homer

```yaml
services:
  homer:
    image: b4bz/homer:latest
    container_name: homer
    volumes:
      - ./homer/assets:/www/assets
    ports:
      - "8080:8080"
    restart: unless-stopped
```

Place your `config.yml` file in the `./homer/assets/` directory. Here is a minimal configuration:

```yaml
---
title: "Homelab Dashboard"
subtitle: "My Services"
logo: "logo.png"

theme: default
colors:
  light:
    highlight-primary: "#3367d6"
  dark:
    highlight-primary: "#3367d6"

services:
  - name: "Infrastructure"
    icon: "fas fa-cloud"
    items:
      - name: "Portainer"
        logo: "assets/tools/portainer.png"
        url: "http://portainer.local:9000"
      - name: "AdGuard Home"
        logo: "assets/tools/adguard.png"
        url: "http://adguard.local:3000"
        type: "Adguard"

  - name: "Media"
    icon: "fas fa-video"
    items:
      - name: "Plex"
        logo: "assets/tools/plex.png"
        url: "http://plex.local:32400"
        type: "Plex"
```

The `type` field enables built-in API health checks for supported services. Homer will ping the service and display its status (online/offline) directly on the startpage.

## Heimdall: The Visual App Launcher

**Heimdall**, developed by LinuxServer.io, takes a different approach. Instead of YAML configuration, it provides a full web-based UI for adding, editing, and organizing your applications. You authenticate, click "Add Application," and fill in a form. It also supports enhanced app types that display live data — weather, calendar events, and system stats.

### Key Features

- **Web-based configuration**: No file editing required. Add and manage apps through the browser.
- **Enhanced apps**: Special app types that pull live data (weather, Radarr queue, Sonarr calendar).
- **User support**: Multi-user capability with per-user customization.
- **Icon auto-fetch**: Automatically fetches app icons from a built-in library.
- **Built on Laravel**: PHP application with SQLite backend.

### Docker Compose Setup for Heimdall

```yaml
services:
  heimdall:
    image: lscr.io/linuxserver/heimdall:latest
    container_name: heimdall
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./heimdall/config:/config
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
```

Heimdall follows the LinuxServer.io standard image pattern with `PUID`, `PGID`, and `TZ` environment variables. After the first boot, access the web UI at `http://your-server:80` and you'll be prompted to create an admin account. From there, you can add applications via the web interface — no YAML editing required.

For reverse proxy setups, you can configure Heimdall to use only port 80 or route through your existing [reverse proxy configuration](../self-hosted-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/).

## Flame: The Modern Startpage with Built-in Search

**Flame** is the newest of the three, built with TypeScript and designed as a modern, minimal startpage. Its standout feature is built-in search — you can search the web directly from your startpage without navigating to a search engine. It also has native Docker integration, automatically discovering and adding containers based on Docker labels.

### Key Features

- **Built-in search**: Integrated web search bar right on the startpage.
- **Docker auto-discovery**: Labels on your containers automatically add them to Flame.
- **Web-based editor**: Add and edit apps/bookmarks through the browser UI.
- **Password protection**: Built-in authentication to restrict access.
- **Workspaces**: Organize services into separate tabs/groups.
- **Active development**: Most recently updated of the three (April 2026).

### Docker Compose Setup for Flame

```yaml
services:
  flame:
    image: pawelmalak/flame:multiarch
    container_name: flame
    volumes:
      - ./flame/data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - PASSWORD=your-secure-password
    ports:
      - "5005:5005"
    restart: unless-stopped
```

Flame requires a `PASSWORD` environment variable for authentication. The Docker socket mount is optional but enables the auto-discovery feature — any container with the label `flame.type=application` will be automatically added to your startpage.

To use Docker labels for auto-discovery, add these labels to your existing containers:

```yaml
services:
  portainer:
    image: portainer/portainer-ce:latest
    labels:
      flame.type: "application"
      flame.name: "Portainer"
      flame.url: "http://portainer.local:9000"
      flame.icon: "icon-docker"
```

Flame will pick these up and add Portainer to your startpage automatically — no manual configuration needed. This is the most powerful feature of Flame and the reason many homelab operators choose it over the alternatives.

## Detailed Comparison

### Ease of Setup

**Homer** requires you to write YAML by hand. If you're comfortable editing config files and want full control over every pixel, this is fast. If you prefer visual editors, Homer will feel restrictive.

**Heimdall** is the easiest to set up for beginners. Docker run, open browser, create account, start adding apps. No file editing, no YAML syntax to learn.

**Flame** sits in the middle. It has a web-based editor for manual additions, but its real power comes from Docker label auto-discovery, which requires adding labels to your existing containers.

### Performance and Resource Usage

| Metric | Homer | Heimdall | Flame |
|---|---|---|---|
| **Image Size** | ~50 MB | ~250 MB | ~120 MB |
| **RAM Usage** | < 20 MB | ~150 MB | ~80 MB |
| **Startup Time** | < 1 second | ~5 seconds | ~3 seconds |
| **Runtime Overhead** | None (static) | PHP + SQLite | Node.js + SQLite |

Homer wins on resource usage by a wide margin because it serves static files. There is no database, no runtime processing, and no backend. Heimdall is the heaviest, running a PHP application with Laravel framework. Flame sits in the middle with a lightweight Node.js server.

### Customization

**Homer** offers the deepest customization through YAML and CSS. You can change every color, layout, font, and message. The trade-off is that every change requires editing the config file and restarting the container.

**Heimdall** has built-in themes and a color picker, but the layout structure is fixed. You can rearrange apps and choose icons, but you cannot fundamentally change how the page looks.

**Flame** offers color customization and workspace organization through its web UI. The layout is clean and modern but less flexible than Homer's YAML-driven approach.

### Best Use Cases

- **Homer**: Users who want a fast, lightweight, fully static startpage and don't mind editing YAML. Ideal for NAS users running minimal resource setups.
- **Heimdall**: Beginners who want a visual, no-code solution with enhanced app types (weather, media server queues). Best for users who prefer GUI over config files.
- **Flame**: Homelab operators who want Docker auto-discovery and built-in search. Best for users running 10+ containers who want their startpage to update automatically.

## FAQ

### What is the difference between a startpage and a monitoring dashboard?

A startpage (like Homer, Heimdall, or Flame) is designed for quick navigation — a visual bookmark manager that helps you find and launch your self-hosted services. A monitoring dashboard (like Grafana or Netdata) displays real-time metrics, charts, and alerts. They serve different purposes and are often used together: the startpage for launching services, the monitoring dashboard for observing them.

### Can I use these tools behind a reverse proxy?

Yes, all three work behind a reverse proxy. Homer runs on port 8080, Heimdall on port 80/443, and Flame on port 5005. You can route any of them through Nginx Proxy Manager, Caddy, or Traefik to access them via a custom domain with HTTPS. See our [reverse proxy comparison guide](../self-hosted-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) for detailed setup instructions.

### Which tool is best for beginners?

Heimdall is the most beginner-friendly because it has a full web-based UI — no YAML editing or command-line configuration required. You install it via Docker, open the browser, and start adding applications through point-and-click forms. Homer requires YAML knowledge, and Flame's Docker auto-discovery requires understanding container labels.

### Do any of these tools support user authentication?

Flame supports password protection through the `PASSWORD` environment variable. Heimdall has a full user system with per-user customization. Homer has no built-in authentication — if you need access control, you must implement it at the reverse proxy level (e.g., Basic Auth via Nginx or Authelia).

### Can I migrate from one tool to another?

There is no automated migration path between these tools because they store configuration differently: Homer uses YAML, Heimdall uses SQLite, and Flame uses a local JSON/SQLite store. However, since all configuration data is stored locally on disk, you can export your service URLs and manually recreate them in the new tool.

### How do I back up my startpage configuration?

For **Homer**, back up the `config.yml` file and the `assets/` directory. For **Heimdall**, back up the `/config` volume (contains the SQLite database). For **Flame**, back up the `/app/data` directory. These are all single-directory backups, making them easy to include in your regular [Docker backup strategy](../docker-compose-guide/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Homer vs Heimdall vs Flame: Best Self-Hosted Startpage Dashboard 2026",
  "description": "Compare the top three self-hosted startpage dashboards in 2026: Homer, Heimdall, and Flame. Detailed feature comparison, Docker setup guides, and recommendations for homelab operators.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
