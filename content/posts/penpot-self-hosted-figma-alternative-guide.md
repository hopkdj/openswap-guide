---
title: "Penpot vs Figma: Best Open-Source Design Tool 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosting Penpot, the open-source Figma alternative for UI/UX design. Installation, Docker setup, feature comparison, and collaboration tips."
---

Design teams everywhere are tired of vendor lock-in, monthly per-seat pricing, and the fact that their entire workflow lives on someone else's servers. Figma dominates the UI/UX design space, but it comes with real costs — both financial and in terms of data sovereignty. Enter **Penpot**, the first truly open-source design and prototyping platform built for cross-functional teams.

In this guide, we'll cover what Penpot offers, how it stacks up against Figma, and walk you through a complete self-hosted deployment using Docker Compose.

## Why Self-Host Your Design Tool

Before diving into Penpot, it's worth understanding why self-hosting a design tool matters more than you might think.

**Data sovereignty** is the biggest driver. When you use a cloud-only tool like Figma, every wireframe, mockup, and prototype lives on company servers you don't control. For teams in regulated industries — healthcare, finance, government — this is often a compliance nightmare. Self-hosting means your design assets never leave your infrastructure.

**Cost at scale** is another factor. Figma's pricing starts reasonable but escalates quickly as teams grow. A professional license runs $12/month per editor, and organization-tier features cost significantly more. Penpot is free and open-source — the only cost is your own infrastructure, which for a typical team is just a modest VPS.

**Offline access** is a genuine advantage for teams in areas with unreliable connectivity. A self-hosted instance on your local network works regardless of your internet connection status.

**Customization and extensibility** matter too. With open-source software, you can modify the tool itself, build custom plugins, integrate with internal systems, and contribute improvements back to the community.

## What Is Penpot?

Penpot is an open-source, web-based design and prototyping platform launched by Kaleidos, a Spanish software cooperative. Unlike many "open-source alternatives" that are rough around the edges, Penpot is a polished, production-ready tool with an active development team, regular releases, and a growing ecosystem.

Key features include:

- **Vector-based design editor** with a familiar canvas-based interface
- **Component system** with variants, properties, and nested components
- **Interactive prototyping** with transitions, animations, and conditional logic
- **Real-time collaboration** — multiple designers can work on the same file simultaneously
- **Developer handoff** with CSS code inspection, asset export, and design specs
- **Design tokens** support for systematic design systems
- **SVG-native** — all designs are stored as standard SVG files, not proprietary formats
- **Git-like version history** for tracking design changes over time

Penpot is built with a Clojure backend and a TypeScript frontend, using PostgreSQL for data storage and Redis for caching and real-time collaboration.

## Penpot vs Figma: Feature Comparison

Here's how Penpot stacks up against Figma across the features that matter most to design teams:

| Feature | Penpot (Self-Hosted) | Figma (Cloud) |
|---------|---------------------|---------------|
| **License** | MPL 2.0 (Open Source) | Proprietary (SaaS) |
| **Cost** | Free (your infra only) | $12–$75/editor/month |
| **Data location** | Your servers | Figma servers |
| **Real-time collaboration** | Yes | Yes |
| **Component system** | Yes (variants, props, slots) | Yes (variants, properties) |
| **Prototyping** | Yes (flows, transitions) | Yes (flows, smart animate) |
| **Design tokens** | Yes (native) | Yes (via variables) |
| **Plugin ecosystem** | Growing (native + web) | Extensive |
| **Offline mode** | Yes (self-hosted) | Limited |
| **File format** | Open SVG | Propetary |
| **Developer handoff** | Built-in (CSS, SVG export) | Built-in (Dev Mode) |
| **Team libraries** | Yes | Yes (paid tiers) |
| **Branching/merging** | Version history | Branching (paid) |
| **Custom fonts** | Yes | Yes |
| **Auto layout** | Yes (Flex Layout) | Yes (Auto Layout) |
| **API / integrations** | REST API | REST + WebSocket API |

### Where Penpot Excels

- **SVG-native architecture** means your designs are never locked into a proprietary format. Export to SVG and you have a complete, editable vector file.
- **Flex Layout** is Penpot's implementation of CSS Flexbox — it maps directly to how developers build layouts, reducing the designer-to-developer translation gap.
- **Open standard** — because Penpot files are SVG-based, you can programmatically generate, modify, or audit designs using standard tools.

### Where Figma Still Leads

- **Plugin ecosystem** is significantly larger. Figma's plugin marketplace has thousands of community-built extensions.
- **FigJam** whiteboarding is a separate product that Penpot doesn't yet match.
- **Advanced prototyping features** like smart animate and scroll-driven animations are more mature in Figma.
- **Community and resources** — tutorials, courses, and design system templates are far more abundant for Figma.

## Self-Hosting Penpot: Complete Setup Guide

Penpot provides an official Docker Compose configuration that makes self-hosting straightforward. Here's how to get a production-ready instance running.

### Prerequisites

- A server with at least 2 CPU cores and 4 GB RAM (4+ GB recommended for teams)
- Docker and Docker Compose installed
- A domain name pointing to your server
- TLS certificates (Let's Encrypt / Certbot)

### Step 1: Create the Project Directory

```bash
mkdir -p ~/penpot && cd ~/penpot
```

### Step 2: Download the Official Docker Compose File

Penpot maintains official compose files. The latest stable version includes all required services:

```bash
curl -L -o docker-compose.yaml \
  https://raw.githubusercontent.com/penpot/penpot/main/docker/images/docker-compose.yaml
```

### Step 3: Configure the Environment

Create a `.env` file with your configuration:

```bash
cat > .env << 'EOF'
# Public-facing URL (change to your domain)
PENPOT_PUBLIC_URI=https://design.yourdomain.com

# PostgreSQL configuration
POSTGRES_PASSWORD=your-secure-db-password-here

# SMTP configuration (required for email invitations)
PENPOT_SMTP_DEFAULT_ENABLED=true
PENPOT_SMTP_DEFAULT_FROM=penpot@yourdomain.com
PENPOT_SMTP_DEFAULT_HOST=smtp.yourdomain.com
PENPOT_SMTP_DEFAULT_PORT=587
PENPOT_SMTP_DEFAULT_TLS=true
PENPOT_SMTP_DEFAULT_USER=penpot@yourdomain.com
PENPOT_SMTP_DEFAULT_PASSWORD=your-smtp-password

# Registration settings
PENPOT_REGISTRATION_ENABLED=true

# Default permissions for new users
PENPOT_FLAGS=enable-registration enable-smtp enable-prepl-server
EOF
```

### Step 4: Full Production Docker Compose

Here's a production-ready `docker-compose.yaml` with all services configured:

```yaml
version: "3.5"

networks:
  penpot:
    driver: bridge

volumes:
  penpot_postgres_data:
  penpot_assets_data:
  traefik_data:

services:
  ## Traefik reverse proxy
  traefik:
    image: traefik:v3.1
    networks:
      - penpot
    ports:
      - 80:80
      - 443:443
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_data:/data
    command:
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--providers.docker"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/data/acme.json"
    restart: unless-stopped

  ## PostgreSQL database
  postgres:
    image: postgres:16
    networks:
      - penpot
    volumes:
      - penpot_postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_INITDB_ARGS=--data-checksums
      - POSTGRES_DB=penpot
      - POSTGRES_USER=penpot
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    restart: unless-stopped

  ## Redis for caching and real-time features
  redis:
    image: redis:7-alpine
    networks:
      - penpot
    command: redis-server --appendonly yes
    volumes:
      - penpot_redis_data:/data
    restart: unless-stopped

  ## Penpot backend
  penpot-backend:
    image: penpotapp/backend:latest
    networks:
      - penpot
    volumes:
      - penpot_assets_data:/opt/data/assets
    environment:
      - PENPOT_FLAGS=${PENPOT_FLAGS}
      - PENPOT_PUBLIC_URI=${PENPOT_PUBLIC_URI}
      - PENPOT_DATABASE_URI=postgresql://postgres:5432/penpot
      - PENPOT_DATABASE_USERNAME=penpot
      - PENPOT_DATABASE_PASSWORD=${POSTGRES_PASSWORD}
      - PENPOT_REDIS_URI=redis://redis:6379/0
      - PENPOT_ASSETS_STORAGE_BACKEND=assets-fs
      - PENPOT_STORAGE_ASSETS_FS_DIRECTORY=/opt/data/assets
      - PENPOT_TELEMETRY_ENABLED=false
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  ## Penpot frontend
  penpot-frontend:
    image: penpotapp/frontend:latest
    networks:
      - penpot
    ports:
      - 9001:80
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.penpot.rule=Host(`design.yourdomain.com`)"
      - "traefik.http.routers.penpot.entrypoints=websecure"
      - "traefik.http.routers.penpot.tls.certresolver=letsencrypt"
      - "traefik.http.services.penpot.loadbalancer.server.port=80"
    environment:
      - PENPOT_PUBLIC_URI=${PENPOT_PUBLIC_URI}
    depends_on:
      - penpot-backend
      - penpot-exporter
    restart: unless-stopped

  ## Penpot exporter (for PDF/PNG export)
  penpot-exporter:
    image: penpotapp/exporter:latest
    networks:
      - penpot
    environment:
      - PENPOT_PUBLIC_URI=http://penpot-frontend:80
      - PENPOT_REDIS_URI=redis://redis:6379/0
    restart: unless-stopped
```

### Step 5: Launch the Stack

```bash
docker compose up -d
```

The initial startup takes a minute or two as the database initializes. Check the logs to confirm everything is running:

```bash
docker compose logs -f
```

You should see the backend connect to PostgreSQL and Redis, and the frontend start serving on port 9001.

### Step 6: Access and Create Your First Account

Navigate to `https://design.yourdomain.com` and create your admin account. The first user registered on a fresh Penpot instance automatically becomes a team administrator.

### Step 7: Optional — Disable Public Registration

For team use, you may want to disable open registration after creating initial accounts:

```bash
# Edit .env and remove 'enable-registration' from PENPOT_FLAGS
sed -i 's/enable-registration //' .env
docker compose up -d penpot-backend
```

Alternatively, use email domain whitelisting:

```bash
PENPOT_REGISTRATION_DOMAIN_WHITELIST="yourcompany.com"
```

## Advanced Configuration

### LDAP / OAuth2 Authentication

Penpot supports OIDC, SAML, and LDAP authentication for enterprise single sign-on. Here's an example OIDC configuration for Keycloak:

```bash
# Add to your .env file
PENPOT_OIDC_CLIENT_ID=penpot
PENPOT_OIDC_CLIENT_SECRET=your-client-secret
PENPOT_OIDC_BASE_URL=https://auth.yourdomain.com/realms/master
PENPOT_OIDC_NAME=Keycloak
```

### Custom Fonts

Upload custom fonts by mounting them into the frontend container:

```yaml
penpot-frontend:
  volumes:
    - ./custom-fonts:/opt/app/fonts
```

Then register them in the Penpot settings UI under **Profile > Fonts**.

### Backup Strategy

Penpot's state is entirely in PostgreSQL and the assets volume. A simple backup script:

```bash
#!/bin/bash
BACKUP_DIR="/backup/penpot/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Database dump
docker compose exec -T postgres pg_dump -U penpot penpot > "$BACKUP_DIR/penpot.sql"

# Assets backup
docker compose exec -T penpot-backend tar czf - /opt/data/assets > "$BACKUP_DIR/assets.tar.gz"

# Keep last 30 days
find /backup/penpot -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

Add this to cron for automated daily backups:

```bash
0 2 * * * /root/penpot/backup.sh >> /var/log/penpot-backup.log 2>&1
```

### Scaling for Larger Teams

For teams of 20+ concurrent users, consider these adjustments:

- **PostgreSQL**: Increase `shared_buffers` to 25% of available RAM
- **Redis**: Enable persistence with AOF (`appendonly yes`)
- **Backend**: Run multiple backend containers behind a load balancer
- **Assets**: Switch to S3-compatible storage instead of filesystem:

```bash
PENPOT_ASSETS_STORAGE_BACKEND=assets-s3
PENPOT_STORAGE_ASSETS_S3_ENDPOINT=https://s3.yourdomain.com
PENPOT_STORAGE_ASSETS_S3_BUCKET=penpot-assets
PENPOT_STORAGE_ASSETS_S3_ACCESS_KEY=your-key
PENPOT_STORAGE_ASSETS_S3_SECRET_KEY=your-secret
```

## Migration from Figma

Moving from Figma to Penpot requires some manual work, but the process is manageable:

1. **Export from Figma**: Select frames and export as SVG. For complex files, use the "Copy as SVG" option.
2. **Import into Penpot**: Use **File > Import** and select your SVG files. Penpot preserves layers, groups, and most vector properties.
3. **Rebuild components**: Penpot's component system works differently from Figma's. You'll need to recreate component variants, but the Flex Layout system often results in cleaner, more developer-friendly components.
4. **Set up design tokens**: Penpot has native design token support. Define your color palette, typography scale, and spacing system in the Tokens panel.

Note that Figma's `.fig` files are not directly importable — there's no official converter. For large design systems, plan a migration sprint rather than a one-shot transfer.

## Conclusion

Penpot has matured into a genuinely viable alternative to Figma for most design workflows. It's not a perfect clone — the plugin ecosystem is smaller and some advanced prototyping features are still catching up. But for teams that value data sovereignty, predictable costs, and open standards, Penpot is the clear choice in 2026.

The self-hosted setup takes about 15 minutes with Docker Compose, and once running, it requires minimal maintenance. For small to mid-size teams, a single $10/month VPS instance handles the load comfortably.

If you're evaluating open-source design tools, Penpot deserves a serious look. Start with the Docker setup above, import a few existing designs, and see how the Flex Layout system works for your workflow.
