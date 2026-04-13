---
title: "Best Self-Hosted Whiteboard & Diagram Tools: Excalidraw vs WBO vs Draw.io 2026"
date: 2026-04-13
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to self-hosted collaborative whiteboard and diagram tools. Compare Excalidraw, WBO, and Draw.io with Docker deployment instructions."
---

When teams need to sketch architecture diagrams, brainstorm product ideas, or run remote planning sessions, cloud whiteboard services are the default choice. Miro, FigJam, and Lucidspark all work well — until you realize your diagrams live on someone else's servers, your brainstorming sessions are subject to usage limits, and your proprietary architecture sketches are stored in a third-party database.

Self-hosted whiteboard and diagram tools solve all three problems at once. You keep full control over your data, eliminate per-seat licensing costs, and run the software on your own infrastructure. In 2026, the open-source ecosystem offers several mature options that rival their commercial counterparts.

This guide covers the three most popular self-hosted whiteboard tools — **Excalidraw**, **WBO (Whiteboard Online)**, and **Draw.io (diagrams.net)** — with hands-on Docker deployment instructions for each.

## Why Self-Host Your Whiteboard Tools

### Data Privacy and Ownership

Whiteboard sessions often contain sensitive information: product roadmaps, system architecture diagrams, organizational charts, and early-stage design concepts. When you use a hosted service, that data leaves your network. Self-hosting keeps everything inside your infrastructure, which matters for:

- Companies under GDPR, HIPAA, or SOC 2 compliance requirements
- Teams working on unreleased products or patents
- Organizations with strict data residency policies
- Anyone who simply prefers to own their data

### No Usage Limits or Paywalls

Commercial whiteboard tools typically charge per editor seat, limit the number of boards, or gate features behind premium tiers. Self-hosted tools have no seat limits, no board limits, and no feature restrictions. Once deployed, every team member gets full access at zero marginal cost.

### Offline Availability and Reliability

When your internet connection drops or a SaaS provider has an outage, your whiteboards become inaccessible. Self-hosted tools run on your own hardware or private cloud, so availability depends on infrastructure you control. For teams that run critical planning sessions or incident response war rooms, this reliability matters.

### Deep Integration Potential

Self-hosted tools can integrate directly with your internal systems: SSO via your identity provider, storage on your NAS or object store, and automation through your internal webhook infrastructure. You are not limited to whatever integrations the vendor chose to build.

## Excalidraw: Sketch-Style Diagrams That Look Great

Excalidraw is a virtual whiteboard tool that produces hand-drawn-style diagrams. It excels at architecture diagrams, flowcharts, wireframes, and quick sketches. Its distinctive sketch aesthetic makes diagrams feel informal and collaborative rather than rigid and corporate.

### Key Features

- **Hand-drawn visual style** — Diagrams look like they were sketched on a whiteboard, which encourages iteration and reduces the pressure for pixel-perfect output
- **End-to-end encryption** — Collaboration sessions can be encrypted so that even the server cannot read the board contents
- **Library system** — Save and reuse custom elements, icons, and component templates across boards
- **Export flexibility** — Boards can be exported as PNG, SVG, or clipboard-ready images
- **Scene sharing** — Generate shareable links with optional encryption for one-off collaboration

### Docker Deployment

The official Excalidraw image provides both the frontend and the collaboration server in a single deployment:

```yaml
# docker-compose.yml for Excalidraw
version: "3"

services:
  excalidraw:
    image: excalidraw/excalidraw:latest
    container_name: excalidraw
    restart: unless-stopped
    ports:
      - "3000:80"
    environment:
      - NODE_ENV=production
    networks:
      - whiteboard-net

  # Optional: collaboration backend for real-time multi-user editing
  excalidraw-collab:
    image: excalidraw/excalidraw-room:latest
    container_name: excalidraw-collab
    restart: unless-stopped
    ports:
      - "3001:80"
    networks:
      - whiteboard-net

networks:
  whiteboard-net:
    driver: bridge
```

Start the service:

```bash
docker compose up -d
```

Access Excalidraw at `http://your-server:3000`. The collaboration server runs on port 3001 and enables real-time multi-user editing.

### Reverse Proxy Configuration

For production use with TLS, configure your reverse proxy. Here is an example for Caddy:

```caddyfile
draw.example.com {
    reverse_proxy localhost:3000
}

collab.example.com {
    reverse_proxy localhost:3001
}
```

Or with Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name draw.example.com;

    ssl_certificate /etc/letsencrypt/live/draw.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/draw.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

The WebSocket upgrade headers are critical — Excalidraw's collaboration features rely on WebSocket connections.

### Advanced Configuration

Excalidraw supports several environment variables for customization:

```yaml
environment:
  # Set the default language
  - DEFAULT_LANGUAGE=en

  # Enable or disable specific export formats
  - ALLOW_EXPORT=png,svg,clipboard

  # Custom library URL for team-shared components
  - LIBRARY_URL=https://libraries.excalidraw.com
```

You can also host a private library server to share team-specific components:

```yaml
  excalidraw-library:
    image: nginx:alpine
    container_name: excalidraw-library
    volumes:
      - ./libraries:/usr/share/nginx/html:ro
    ports:
      - "3002:80"
    networks:
      - whiteboard-net
```

## WBO (Whiteboard Online): Lightweight Real-Time Collaboration

WBO (Whiteboard Online) is a minimalist, real-time collaborative whiteboard focused on speed and simplicity. It does not try to be a full diagramming tool — instead, it provides a blank canvas with drawing tools optimized for low-latency multi-user sessions.

### Key Features

- **Real-time collaboration** — Multiple users draw simultaneously with sub-100ms latency
- **Persistent boards** — Boards are saved automatically and survive server restarts
- **Board naming** — Any URL path creates a new board (`/board/my-project` creates a board named "my-project")
- **Minimal resource usage** — The entire application is under 5MB and runs comfortably on a Raspberry Pi
- **No accounts required** — Users join boards by visiting a URL; no registration needed

### Docker Deployment

WBO is exceptionally lightweight to deploy:

```yaml
# docker-compose.yml for WBO
version: "3"

services:
  wbo:
    image: lovasoa/wbo:latest
    container_name: wbo-whiteboard
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./wbo-boards:/opt/app/server-data:rw
    environment:
      - MAX_BOARD_SIZE=50
      - MAX_PARALLEL_CONNECTIONS=100
    networks:
      - whiteboard-net

networks:
  whiteboard-net:
    driver: bridge
```

Start the service:

```bash
docker compose up -d
```

Access WBO at `http://your-server:8080`. Create a new board by visiting any path, such as `http://your-server:8080/boards/team-standup`.

### Volume Persistence

The `/opt/app/server-data` directory stores all board data. Mapping it to a host volume ensures boards survive container recreation:

```bash
# Create the data directory
mkdir -p ./wbo-boards

# Verify boards are being saved
ls -la ./wbo-boards/
```

### Performance Tuning

For larger teams, adjust the connection and board limits:

```yaml
environment:
  # Maximum number of concurrent connections
  - MAX_PARALLEL_CONNECTIONS=200

  # Maximum board size in megabytes
  - MAX_BOARD_SIZE=100

  # Idle timeout in seconds (0 = no timeout)
  - IDLE_TIMEOUT=3600
```

For very large boards, you may also want to increase Nginx's WebSocket buffer sizes:

```nginx
location / {
    proxy_pass http://localhost:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;
}
```

### Backup Strategy

Since WBO stores boards as individual files, backup is straightforward:

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backup/wbo/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"
cp -r /opt/wbo-boards/* "$BACKUP_DIR/"

# Keep 30 days of backups
find /backup/wbo -type d -mtime +30 -exec rm -rf {} +
```

Add this as a cron job for automated daily backups:

```bash
# Run backup every day at 2 AM
0 2 * * * /opt/scripts/wbo-backup.sh
```

## Draw.io (diagrams.net): Professional Diagramming Engine

Draw.io (also known as diagrams.net) is the most feature-rich option in this comparison. It is a full-featured diagramming application with support for flowcharts, network diagrams, UML, BPMN, org charts, mind maps, and dozens of other diagram types. Unlike Excalidraw's sketch style, Draw.io produces polished, professional diagrams suitable for documentation and presentations.

### Key Features

- **Extensive shape libraries** — Built-in support for AWS, Azure, GCP, Kubernetes, Cisco, and many other icon sets
- **Multiple diagram types** — Flowcharts, UML, BPMN, ER diagrams, network topology, org charts, mind maps, and more
- **File format support** — Import and export Visio (.vsdx), Lucidchart, Gliffy, SVG, PDF, and PNG files
- **Storage integrations** — Native support for local storage, WebDAV, GitHub, GitLab, and object storage
- **Plugin system** — Extend functionality with custom plugins and templates

### Docker Deployment

The Draw.io integration image provides a self-contained deployment:

```yaml
# docker-compose.yml for Draw.io
version: "3"

services:
  drawio:
    image: jgraph/drawio:latest
    container_name: drawio
    restart: unless-stopped
    ports:
      - "8090:8080"
    environment:
      # Disable external storage integrations for a clean self-hosted setup
      - DRAWIO_BASE_URL=https://draw.example.com
      - DRAWIO_SERVER_URL=https://draw.example.com/
    volumes:
      - ./drawio-storage:/var/lib/drawio
    networks:
      - whiteboard-net

networks:
  whiteboard-net:
    driver: bridge
```

Start the service:

```bash
docker compose up -d
```

Access Draw.io at `http://your-server:8090`. The application runs entirely in the browser — the server primarily handles file storage and sharing.

### Configuring Local Storage

By default, Draw.io encourages users to save files to external storage. For a fully self-hosted setup, configure the built-in storage:

```yaml
environment:
  # Use the internal storage backend
  - DRAWIO_SELF_CONTAINED=1

  # Set the maximum file upload size (in bytes)
  - DRAWIO_MAX_FILE_SIZE=104857600

  # Configure the base URL for sharing links
  - DRAWIO_BASE_URL=https://draw.example.com
```

### Reverse Proxy with Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name draw.example.com;

    ssl_certificate /etc/letsencrypt/live/draw.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/draw.example.com/privkey.pem;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Preloading Custom Libraries

For teams that need consistent diagram templates, you can preload custom shape libraries:

```bash
# Create a custom library directory
mkdir -p ./drawio-storage/libraries

# Copy your team's standard shapes
cp ./team-shapes/*.xml ./drawio-storage/libraries/

# Mount in docker-compose
volumes:
  - ./drawio-storage/libraries:/var/lib/drawio/libraries:ro
```

## Comparison: Excalidraw vs WBO vs Draw.io

| Feature | Excalidraw | WBO | Draw.io |
|---------|-----------|-----|---------|
| **Primary Use Case** | Sketch-style diagrams & wireframes | Real-time freeform drawing | Professional diagrams & flowcharts |
| **Visual Style** | Hand-drawn sketch | Freeform pen/pencil | Clean, polished, professional |
| **Real-time Collaboration** | Yes (with collab server) | Yes (built-in) | Limited (requires additional setup) |
| **End-to-End Encryption** | Yes | No | No |
| **Shape Libraries** | Basic community libraries | None (freeform only) | Extensive (AWS, Azure, GCP, UML, etc.) |
| **Export Formats** | PNG, SVG, clipboard | PNG, SVG | PNG, SVG, PDF, Visio, HTML |
| **Import Support** | Excalidraw files | WBO board files | Visio, Lucidchart, Gliffy, XML |
| **Docker Image Size** | ~180 MB | ~4.5 MB | ~160 MB |
| **RAM Usage (idle)** | ~150 MB | ~15 MB | ~120 MB |
| **Persistent Storage** | Manual (save files) | Automatic (server-side) | Configurable (local or external) |
| **Authentication** | None built-in | None built-in | None built-in (gate via reverse proxy) |
| **Mobile Friendly** | Yes | Yes | Partially |
| **Offline Mode** | Yes (PWA) | No | Yes (desktop app available) |
| **Plugin System** | Limited | No | Yes |
| **Learning Curve** | Very easy | Trivial | Moderate |

## Choosing the Right Tool

### Choose Excalidraw When:

- You want diagrams that feel informal and encourage iteration
- End-to-end encryption is a requirement for collaboration sessions
- Your team creates architecture diagrams, wireframes, and quick sketches regularly
- You want the best balance of simplicity and visual quality

Excalidraw is the sweet spot for most engineering teams. Its sketch style reduces the friction between thinking and drawing, and the encryption means sensitive architecture discussions stay private.

### Choose WBO When:

- You need the absolute lowest-latency real-time collaboration
- You want something that runs on minimal hardware (even a Raspberry Pi)
- Freeform drawing is more important than structured diagrams
- You want zero setup — just visit a URL and start drawing

WBO is ideal for quick brainstorming sessions, incident response whiteboarding, and situations where speed matters more than polish.

### Choose Draw.io When:

- You need professional diagrams for documentation or presentations
- Your team works with UML, BPMN, network topology, or org charts
- You need to import existing Visio or Lucidchart files
- You want access to comprehensive cloud provider icon sets

Draw.io is the right choice when diagram quality matters and you need the full feature set of a professional diagramming application.

## Running All Three Behind a Single Domain

For teams that want multiple tools available, you can run all three behind a single reverse proxy with path-based routing:

```yaml
# Complete docker-compose with all three tools
version: "3"

services:
  excalidraw:
    image: excalidraw/excalidraw:latest
    container_name: excalidraw
    restart: unless-stopped
    expose:
      - "80"
    networks:
      - whiteboard-net

  excalidraw-collab:
    image: excalidraw/excalidraw-room:latest
    container_name: excalidraw-collab
    restart: unless-stopped
    expose:
      - "80"
    networks:
      - whiteboard-net

  wbo:
    image: lovasoa/wbo:latest
    container_name: wbo-whiteboard
    restart: unless-stopped
    volumes:
      - ./wbo-boards:/opt/app/server-data:rw
    expose:
      - "80"
    networks:
      - whiteboard-net

  drawio:
    image: jgraph/drawio:latest
    container_name: drawio
    restart: unless-stopped
    expose:
      - "8080"
    networks:
      - whiteboard-net

  # Traefik reverse proxy
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yaml:/etc/traefik/traefik.yaml:ro
      - ./acme.json:/acme.json
    networks:
      - whiteboard-net

networks:
  whiteboard-net:
    driver: bridge
```

Traefik configuration:

```yaml
# traefik.yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    exposedByDefault: false

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@example.com
      storage: /acme.json
      httpChallenge:
        entryPoint: web
```

Then add labels to each service in docker-compose:

```yaml
  excalidraw:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.excalidraw.rule=Host(`draw.example.com`) && PathPrefix(`/sketch`)"
      - "traefik.http.routers.excalidraw.tls.certresolver=letsencrypt"

  wbo:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.wbo.rule=Host(`draw.example.com`) && PathPrefix(`/whiteboard`)"
      - "traefik.http.routers.wbo.tls.certresolver=letsencrypt"

  drawio:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.drawio.rule=Host(`draw.example.com`) && PathPrefix(`/diagrams`)"
      - "traefik.http.routers.drawio.tls.certresolver=letsencrypt"
```

This gives you a unified whiteboard portal at `draw.example.com` with `/sketch`, `/whiteboard`, and `/diagrams` routing to the appropriate tool.

## Security Hardening Checklist

Regardless of which tool you choose, follow these baseline security practices:

1. **Always use TLS** — Terminate TLS at your reverse proxy. Never expose whiteboard tools over plain HTTP on a public network.

2. **Add authentication at the reverse proxy level** — None of these tools include built-in authentication. Use your reverse proxy to add basic auth, OIDC, or SSO:

```nginx
# Nginx basic auth example
location / {
    auth_basic "Whiteboard Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:3000;
}
```

Generate the password file:

```bash
htpasswd -c /etc/nginx/.htpasswd username
```

3. **Restrict access by IP when possible** — If your whiteboard tools are only used internally, bind to localhost and access via VPN or SSH tunnel:

```bash
# SSH tunnel to remote whiteboard
ssh -L 3000:localhost:3000 user@your-server
```

4. **Regular backups** — Board data is only valuable if it is backed up. Use the volume-based backup strategy shown in the WBO section, adapted for your tool of choice.

5. **Keep images updated** — Run `docker compose pull && docker compose up -d` regularly to get security patches. Automate this with Watchtower:

```yaml
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --schedule "0 0 4 * * *" --cleanup
```

## Conclusion

Self-hosted whiteboard tools have matured to the point where there is no reason to send your diagrams to a third-party service. Excalidraw delivers the best experience for quick sketches and architecture diagrams with encryption built in. WBO is the lightest option for real-time freeform collaboration. Draw.io provides the deepest feature set for professional diagramming.

All three deploy with a single `docker compose up -d`, run on modest hardware, and cost nothing beyond your server infrastructure. Pick the tool that matches your team's workflow — or run all three behind a single domain and let people choose.
