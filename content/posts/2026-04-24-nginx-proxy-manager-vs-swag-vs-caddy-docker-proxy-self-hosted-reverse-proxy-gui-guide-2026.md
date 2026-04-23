---
title: "Nginx Proxy Manager vs SWAG vs Caddy Docker Proxy: Best Self-Hosted Reverse Proxy GUI 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "privacy", "docker", "reverse-proxy"]
draft: false
description: "Compare Nginx Proxy Manager, SWAG, and Caddy Docker Proxy for self-hosted reverse proxy management. Docker compose configs, feature comparison, and deployment guides for managing SSL certificates and proxy hosts."
---

Every self-hosted homelab eventually needs a reverse proxy. You start with one service on port 8080, add another on 8081, and soon you are juggling a dozen exposed ports. A reverse proxy consolidates all your services behind a single entry point, routes traffic by domain name, and handles SSL certificate management automatically.

The three most popular self-hosted reverse proxy management tools are [Nginx Proxy Manager](https://nginxproxymanager.com), LinuxServer's [SWAG](https://github.com/linuxserver/docker-swag), and [Caddy Docker Proxy](https://github.com/lucaslorentz/caddy-docker-proxy). Each takes a fundamentally different approach to proxy management — from graphical web interfaces to label-driven automation. In this guide, we compare them side by side and walk through complete deployment configurations.

For related reading, see our [Traefik vs Nginx vs Caddy web server comparison](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/) and [complete TLS termination proxy guide](../self-hosted-tls-termination-proxy-traefik-caddy-haproxy-guide-2026/).

## Why Self-Host Your Reverse Proxy

Running your own reverse proxy gives you full control over how traffic reaches your services. Cloud-based proxy solutions route your data through third-party infrastructure, while self-hosted alternatives keep everything inside your network.

**Consolidated SSL management.** Instead of configuring Let's Encrypt certificates individually for each service, a reverse proxy handles certificate issuance and renewal in one place. All your subdomains share a single certificate management pipeline.

**Single public IP, many services.** With port forwarding limited to one or two ports on your router, a reverse proxy lets you expose dozens of services using domain-based routing on standard ports 80 and 443.

**Access control and authentication.** Reverse proxies can add authentication layers, IP-based access rules, and rate limiting before traffic reaches your backend services.

**Zero backend changes.** Your application containers do not need to know about SSL, domain names, or public routing. They listen on internal ports and let the proxy handle the rest.

## Project Overview and GitHub Stats

| Feature | Nginx Proxy Manager | SWAG (LinuxServer) | Caddy Docker Proxy |
|---|---|---|---|
| **GitHub** | [NginxProxyManager/nginx-proxy-manager](https://github.com/NginxProxyManager/nginx-proxy-manager) | [linuxserver/docker-swag](https://github.com/linuxserver/docker-swag) | [lucaslorentz/caddy-docker-proxy](https://github.com/lucaslorentz/caddy-docker-proxy) |
| **Stars** | 32,585 | 3,641 | 4,424 |
| **Last Updated** | April 20, 2026 | April 18, 2026 | April 22, 2026 |
| **License** | MIT | GPL-3.0 | Apache-2.0 |
| **Management UI** | Web GUI (React) | Config files + web UI (optional) | Docker labels only |
| **Web Server** | Nginx | Nginx | Caddy |
| **SSL Provider** | Let's Encrypt (built-in) | Certbot (Let's Encrypt) | Let's Encrypt (built-in) |
| **Database** | SQLite / MySQL | None (file-based) | None (label-based) |

Nginx Proxy Manager dominates in popularity with over 32,000 GitHub stars, offering the most polished web interface. SWAG brings the maturity of the LinuxServer.io ecosystem with battle-tested Nginx configurations. Caddy Docker Proxy takes the most modern approach with automatic configuration driven entirely by Docker labels and Caddy's native automatic HTTPS.

## Architecture and Design Philosophy

### Nginx Proxy Manager

Nginx Proxy Manager uses a traditional client-server architecture. A Node.js backend manages an SQLite (or MySQL) database of proxy hosts, SSL certificates, and access rules. A Nginx instance runs as the actual proxy, with its configuration dynamically generated from the database. The web interface communicates with the backend API to make changes.

```
User → Port 80/443 → Nginx (proxy) → Backend API (SQLite) → Web UI on :81
                                      ↓
                        Proxy Host Config stored in DB
```

This decoupled design means the proxy keeps running even if the management UI goes down. Configuration changes are persisted to the database and regenerated into Nginx config files on each change.

### SWAG (Secure Web Application Gateway)

SWAG is a pre-configured Nginx container from LinuxServer.io that bundles Certbot, Fail2ban, and a collection of ready-made reverse proxy configurations. Instead of a database, it relies on mounted configuration files and a library of sample proxy configs for popular services.

```
User → Port 80/443 → Nginx (proxy + Certbot + Fail2ban)
                      ↓
              Config files in /config/nginx/
              Sample configs in /config/nginx/proxy-confs/
```

SWAG also includes an optional web-based file manager (FileBrowser) and supports DNS challenge validation for domains without public DNS records.

### Caddy Docker Proxy

Caddy Docker Proxy replaces traditional configuration entirely. Instead of writing config files or clicking through a web UI, you annotate your Docker containers with labels. A sidecar process watches the Docker socket, reads these labels, and generates Caddy configuration in real time.

```
User → Port 80/443 → Caddy (proxy + automatic HTTPS)
                      ↑
              Docker Socket ← Caddy Docker Proxy (watcher)
                      ↓
              Container labels: caddy: example.com
```

This is the closest thing to "zero configuration" in the reverse proxy space. When you deploy a new container with the right labels, it is automatically proxied with HTTPS — no manual steps required.

## Docker Compose Deployment

### Nginx Proxy Manager

```yaml
version: "3.8"
services:
  nginx-proxy-manager:
    image: jc21/nginx-proxy-manager:latest
    container_name: nginx-proxy-manager
    restart: unless-stopped
    ports:
      - "80:80"
      - "81:81"
      - "443:443"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
    environment:
      - DB_SQLITE_FILE=/data/database.sqlite
```

After starting, access the web interface at `http://your-server-ip:81`. Default credentials are `admin@example.com` / `changeme`. Change these immediately on first login.

For production with MySQL instead of SQLite:

```yaml
version: "3.8"
services:
  app:
    image: jc21/nginx-proxy-manager:latest
    restart: unless-stopped
    ports:
      - "80:80"
      - "81:81"
      - "443:443"
    environment:
      - DB_MYSQL_HOST=db
      - DB_MYSQL_PORT=3306
      - DB_MYSQL_USER=npm
      - DB_MYSQL_PASSWORD=npm_password
      - DB_MYSQL_NAME=npm
    depends_on:
      - db

  db:
    image: jc21/mariadb-aria:latest
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=npm_root_password
      - MYSQL_DATABASE=npm
      - MYSQL_USER=npm
      - MYSQL_PASSWORD=npm_password
    volumes:
      - ./mysql:/var/lib/mysql
```

### SWAG

```yaml
version: "3.8"
services:
  swag:
    image: lscr.io/linuxserver/swag:latest
    container_name: swag
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - URL=yourdomain.com
      - SUBDOMAINS=www,app,api
      - VALIDATION=http
    volumes:
      - ./swag-config:/config
    ports:
      - "443:443"
      - "80:80"
    networks:
      - proxy-network

networks:
  proxy-network:
    external: true
```

SWAG requires a shared Docker network so it can reach backend containers by name. Create it with `docker network create proxy-network`, then connect your services to it.

For DNS challenge validation (no public port 80 required):

```yaml
environment:
  - URL=yourdomain.com
  - SUBDOMAINS=www,app
  - VALIDATION=dns
  - DNSPLUGIN=cloudflare
  - CERTPROVIDER=letsencrypt
  - PROPAGATION=3600
volumes:
  - ./cloudflare.ini:/config/dns-conf/cloudflare.ini:ro
```

### Caddy Docker Proxy

```yaml
version: "3.8"
services:
  caddy:
    image: lucaslorentz/caddy-docker-proxy:ci-alpine
    container_name: caddy-docker-proxy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - CADDY_DOCKER_POLLING_INTERVAL=30s
      - CADDY_DOCKER_CADDYFILE_PATH=/etc/caddy/Caddyfile
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - proxy-network

volumes:
  caddy_data:
  caddy_config:

networks:
  proxy-network:
    external: true
```

The key difference: Caddy Docker Proxy reads the Docker socket directly. No configuration files are needed beyond this compose file. Backend services are proxied by adding labels:

```yaml
version: "3.8"
services:
  portainer:
    image: portainer/portainer-ce:latest
    container_name: portainer
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    labels:
      caddy: portainer.yourdomain.com
      caddy.reverse_proxy: "{{upstreams 9000}}"
    networks:
      - proxy-network

  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    container_name: homepage
    restart: unless-stopped
    volumes:
      - ./homepage-config:/app/config
    labels:
      caddy: home.yourdomain.com
      caddy.reverse_proxy: "{{upstreams 3000}}"
      caddy.tls: "internal"
    networks:
      - proxy-network

volumes:
  portainer_data:

networks:
  proxy-network:
    external: true
```

Adding a new proxied service is as simple as deploying a container with the `caddy:` label. The proxy detects it within seconds and starts routing traffic with automatic HTTPS.

## Feature Comparison

| Feature | Nginx Proxy Manager | SWAG | Caddy Docker Proxy |
|---|---|---|---|
| **Management Interface** | Full web GUI | Config files (text editor) | Docker labels only |
| **SSL Automation** | Click-to-issue via UI | Certbot CLI + cron | Fully automatic |
| **DNS Challenge** | Yes (Cloudflare, etc.) | Yes (60+ providers via Certbot) | Yes (via Caddy DNS modules) |
| **Rate Limiting** | Yes (via Nginx config) | Yes (built-in templates) | Yes (Caddy native) |
| **Basic Auth** | Yes (UI-based) | Yes (htpasswd files) | Yes (via labels) |
| **Access Lists** | IP-based allow/deny | IP-based + Fail2ban | IP-based via Caddy |
| **Stream/TCP Proxy** | Yes | Yes | Limited |
| **WebSocket Support** | Yes | Yes | Yes (automatic) |
| **HTTP/2** | Yes | Yes | Yes (default) |
| **HTTP/3 (QUIC)** | No | No | Yes (built-in) |
| **Wildcard Certificates** | Yes | Yes | Yes |
| **OCSP Stapling** | Yes | Yes | Yes (automatic) |
| **IPv6 Support** | Yes | Yes | Yes |
| **Multi-tenant** | No | No | No |
| **Fail2ban Integration** | No | Yes (built-in) | No |
| **Container Auto-Discovery** | No | No | Yes |
| **Learning Curve** | Low (GUI-driven) | Medium (config files) | Low (label-driven) |

## Which One Should You Choose?

**Nginx Proxy Manager** is the best choice if you want a graphical interface. It is ideal for users who prefer clicking through a web dashboard to manage proxy hosts, issue SSL certificates, and configure access rules. The database-backed configuration means changes are persistent and auditable. It is the most popular option for a reason — it works out of the box with minimal configuration.

**SWAG** is the best choice for users already in the LinuxServer.io ecosystem. If your homelab runs LinuxServer containers (which most do), SWAG integrates seamlessly. The pre-built proxy configuration templates for hundreds of popular services save significant time. Fail2ban integration adds an intrusion prevention layer that the other two tools lack. The trade-off is that you manage configuration files manually.

**Caddy Docker Proxy** is the best choice for automation enthusiasts and Infrastructure-as-Code practitioners. The label-driven approach means your Docker compose files are self-documenting — the proxy configuration lives alongside the service definition. Caddy's automatic HTTPS means zero certificate management. HTTP/3 support out of the box is a bonus. The trade-off is less granular control compared to hand-tuned Nginx configs.

## FAQ

### Is Nginx Proxy Manager safe for production use?

Yes. Nginx Proxy Manager is used in production by thousands of organizations. The underlying Nginx proxy is a mature, battle-tested web server. The management UI adds a layer of convenience without compromising the stability of the proxy itself. For high-availability setups, use the MySQL backend option instead of SQLite.

### Can I migrate from SWAG to Nginx Proxy Manager?

There is no automated migration tool, but the transition is straightforward. Both use Nginx as the underlying proxy, so your proxy rules and SSL certificates can be recreated in the Nginx Proxy Manager web interface. Export your domain list from SWAG's config files, recreate the proxy hosts in NPM, and point your DNS records to the new proxy. The SSL certificates will need to be re-issued since they are tied to the server.

### Does Caddy Docker Proxy work with Docker Swarm or Kubernetes?

Caddy Docker Proxy specifically monitors the Docker socket and only works with single-node Docker. For Docker Swarm, use [Caddy Swarm Proxy](https://github.com/techknowlogick/caddy-docker-proxy) (a fork with Swarm support). For Kubernetes, use the [Caddy Ingress Controller](https://github.com/caddyserver/ingress) instead.

### Can SWAG handle multiple domains with separate certificates?

Yes. Set `URL=yourdomain.com` as the primary domain and add additional domains via the `SUBDOMAINS` environment variable or by creating additional proxy configuration files in `/config/nginx/proxy-confs/`. Each domain gets its own Let's Encrypt certificate. For completely separate domains, you can use the `EXTRA_DOMAINS` environment variable.

### How do I back up my reverse proxy configuration?

For **Nginx Proxy Manager**, back up the `data/` and `letsencrypt/` directories (or dump the MySQL database). For **SWAG**, back up the entire `/config` directory — it contains all Nginx configs, certificates, and Certbot data. For **Caddy Docker Proxy**, back up the `caddy_data` volume (contains certificates) and ensure your Docker compose files with labels are version-controlled — they are your configuration.

### Does any of these tools support TCP/UDP stream proxying?

Nginx Proxy Manager and SWAG both support TCP/UDP stream proxying through Nginx's stream module. You can proxy database connections, game servers, and other non-HTTP traffic. Caddy Docker Proxy has limited stream support — it primarily focuses on HTTP/HTTPS traffic. If you need extensive TCP proxying, NPM or SWAG is the better choice.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nginx Proxy Manager vs SWAG vs Caddy Docker Proxy: Best Self-Hosted Reverse Proxy GUI 2026",
  "description": "Compare Nginx Proxy Manager, SWAG, and Caddy Docker Proxy for self-hosted reverse proxy management. Docker compose configs, feature comparison, and deployment guides for managing SSL certificates and proxy hosts.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
