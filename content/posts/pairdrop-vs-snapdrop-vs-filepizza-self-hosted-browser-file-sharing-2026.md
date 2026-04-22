---
title: "PairDrop vs Snapdrop vs FilePizza: Best Self-Hosted Browser File Sharing 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "file-sharing", "webrtc", "p2p"]
draft: false
description: "Compare PairDrop, Snapdrop, and FilePizza — three open-source, self-hosted tools for browser-to-browser file transfer over WebRTC. Includes Docker setup, feature comparison, and deployment guide."
---

Transferring files between devices used to mean uploading to a cloud service, sharing a link, and hoping the recipient downloads before the link expires. Browser-based file sharing tools eliminate that friction entirely — open your browser, find the recipient on the same network, and send files directly peer-to-peer.

In this guide, we compare three popular open-source options: [PairDrop](https://github.com/schlagmichdoch/PairDrop), [Snapdrop](https://github.com/RobinLinus/snapdrop), and [FilePizza](https://github.com/kern/filepizza). All three run entirely in the browser using WebRTC, require no signup, and can be self-hosted for full privacy.

**Quick stats at a glance:**

| Project | GitHub Stars | Last Updated | Language | License |
|---------|-------------|--------------|----------|---------|
| Snapdrop | 19,700+ | Feb 2025 | JavaScript | GPL-3.0 |
| PairDrop | 10,100+ | Feb 2025 | JavaScript | GPL-3.0 |
| FilePizza | 10,000+ | Apr 2026 | TypeScript | MIT |

## Why Self-Host Your File Sharing

Public file-sharing services like [snapdrop.net](https://snapdrop.net) or [file.pizza](https://file.pizza) work great for casual transfers, but self-hosting gives you control:

- **No third-party servers** — files never touch infrastructure you don't control
- **Custom TURN/STUN configuration** — configure relay servers for cross-network transfers
- **Branded experience** — customize the UI with your organization's branding
- **Rate limiting** — prevent abuse on public-facing instances
- **Private networks** — deploy on your LAN for fast local transfers without internet dependency
- **No data retention policies to worry about** — your server, your rules

For related reading on broader file sharing and synchronization solutions, see our [complete guide to self-hosted file sync and sharing (Nextcloud, Seafile, Syncthing)](../self-hosted-file-sync-sharing-nextcloud-seafile-syncthing-guide/) and our [comparison of web-based file managers (Filebrowser, Filegator, Cloud Commander)](../filebrowser-vs-filegator-vs-cloud-commander-self-hosted-web-file-managers-2026/).

## Snapdrop: The Original Browser AirDrop Clone

Snapdrop pioneered the concept of an AirDrop-like experience that works in any modern browser. Launched in 2015, it remains the most starred project in this category.

### How Snapdrop Works

Snapdrop uses WebRTC for peer-to-peer data transfer and WebSockets for peer discovery. When you open the Snapdrop page, your browser connects to a signaling server that tells it about other devices on the same network. Once peers discover each other, the actual file transfer happens directly between browsers — the server is never involved in moving the file data.

### Features

- **Progressive Web App (PWA)** — install on your phone or desktop for a native-like experience
- **No file size limits** — transfer files as large as your devices can handle
- **Text message support** — send plain text snippets alongside files
- **Clean, minimal UI** — shows all nearby devices as circles with random pet names
- **Zero configuration** — just open the page and start sending

### Snapdrop Docker Compose Setup

Snapdrop's official docker-compose.yml runs both a Node.js signaling server and an Nginx reverse proxy with auto-generated TLS certificates:

```yaml
version: "3"
services:
  node:
    image: "node:lts-alpine"
    user: "node"
    working_dir: /home/node/app
    volumes:
      - ./server/:/home/node/app
    command: ash -c "npm i && node index.js"
  nginx:
    build:
      context: ./docker/
      dockerfile: nginx-with-openssl.Dockerfile
    image: "nginx-with-openssl"
    volumes:
      - ./client:/usr/share/nginx/html
      - ./docker/nginx/default.conf:/etc/nginx/conf.d/default.conf
      - ./docker/certs:/etc/ssl/certs
      - ./docker/openssl:/mnt/openssl
    ports:
      - "8080:80"
      - "443:443"
    env_file: ./docker/fqdn.env
    entrypoint: /mnt/openssl/create.sh
    command: ["nginx", "-g", "daemon off;"]
```

For a production deployment, you will want to configure the `fqdn.env` file with your domain name so the Nginx container can generate valid TLS certificates. WebRTC requires a secure context (HTTPS), so self-signed certificates work only on localhost or LAN.

**Simplified deployment (LinuxServer.io image):**

```bash
docker run -d \
  --name=snapdrop \
  -e PUID=1000 \
  -e PGID=1000 \
  -e TZ=Etc/UTC \
  -p 3000:3000 \
  --restart unless-stopped \
  linuxserver/snapdrop:latest
```

Then access at `http://your-server-ip:3000`.

## PairDrop: The Actively Maintained Fork

PairDrop started as a fork of Snapdrop and has grown into its own project with significant feature additions. It addresses several limitations of the original Snapdrop while keeping the same familiar interface.

### What PairDrop Adds Over Snapdrop

- **Room-based sharing** — create private rooms so only invited peers can see each other, even across different networks
- **QR code generation** — scan a QR code on your phone to instantly join the room
- **Cross-platform file transfer** — works across LAN and WAN when configured with a TURN server
- **WebSocket fallback** — when WebRTC peer-to-peer connections are blocked by firewalls, PairDrop falls back to WebSocket relay
- **Active development** — more frequent updates and community contributions than the original Snapdrop
- **Debug mode** — built-in debugging tools for troubleshooting connection issues

### PairDrop Docker Compose Setup

PairDrop's official compose file uses the LinuxServer.io image, which packages everything you need in a single container:

```yaml
version: "3"
services:
  pairdrop:
    image: "lscr.io/linuxserver/pairdrop:latest"
    container_name: pairdrop
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - WS_FALLBACK=false
      - RATE_LIMIT=false
      - RTC_CONFIG=false
      - DEBUG_MODE=false
      - TZ=Etc/UTC
    ports:
      - "127.0.0.1:3000:3000"
```

To enable WebSocket fallback for users behind restrictive firewalls, set `WS_FALLBACK=true`. For rate limiting to prevent abuse on public instances, set `RATE_LIMIT=true` (limits clients to 1,000 requests per 5 minutes).

### PairDrop with TURN Server (Cross-Network Transfer)

For transfers between devices on different networks, PairDrop needs a STUN/TURN relay server. You can combine it with a Coturn instance:

```yaml
version: "3"
services:
  pairdrop:
    image: "lscr.io/linuxserver/pairdrop:latest"
    container_name: pairdrop
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - WS_FALLBACK=true
      - RATE_LIMIT=true
      - RTC_CONFIG=/config/rtc_config.json
      - TZ=Etc/UTC
    ports:
      - "3000:3000"
    volumes:
      - ./rtc_config.json:/config/rtc_config.json:ro

  coturn:
    image: coturn/coturn
    ports:
      - "3478:3478"
      - "3478:3478/udp"
      - "5349:5349"
      - "5349:5349/udp"
      - "60000-60128:60000-60128/udp"
    environment:
      - DETECT_EXTERNAL_IP=yes
      - DETECT_RELAY_IP=yes
    command: >
      -n --log-file=stdout
      --min-port=60000 --max-port=60128
      --realm=yourdomain.com
```

The `rtc_config.json` file should point to your TURN server. For more on setting up STUN/TURN infrastructure, check our [detailed guide on self-hosted TURN and STUN servers (Coturn, Restund, Pion)](../self-hosted-turn-stun-servers-coturn-restund-pion-webrtc-guide-2026/).

## FilePizza: One-Time Peer-to-Peer File Transfers

FilePizza takes a different approach. Instead of showing all nearby devices on a landing page, FilePizza lets a single uploader generate a "slice" (a unique URL) that one or more downloaders can use. The transfer happens directly peer-to-peer via WebRTC — the server only handles signaling.

### Key Design Decisions

- **No server-side storage** — files are never uploaded to or stored on the server
- **One-time transfers** — once all downloaders disconnect, the upload is gone
- **Unlimited file size** — since files stream directly from uploader to downloader
- **Multiple simultaneous downloaders** — one uploader can serve many downloaders at once
- **Modern stack** — built with Next.js, React, and TypeScript

### FilePizza Docker Compose Setup

FilePizza's production setup requires Redis for signaling state and optionally Coturn for NAT traversal:

```yaml
services:
  redis:
    image: redis:latest
    ports:
      - "127.0.0.1:6379:6379"
    networks:
      - filepizza
    volumes:
      - redis_data:/data

  coturn:
    image: coturn/coturn
    ports:
      - "3478:3478"
      - "3478:3478/udp"
      - "5349:5349"
      - "5349:5349/udp"
      - "60000-60128:60000-60128/udp"
    environment:
      - DETECT_EXTERNAL_IP=yes
      - DETECT_RELAY_IP=yes
    command: >
      -n --log-file=stdout
      --redis-userdb="ip=redis connect_timeout=30"
      --min-port=60000 --max-port=60128
    networks:
      - filepizza

  filepizza:
    image: kern/filepizza:latest
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - REDIS_URL=redis://redis:6379
    networks:
      - filepizza
    depends_on:
      - redis

networks:
  filepizza:
    driver: bridge

volumes:
  redis_data:
```

FilePizza's development compose is simpler — just Redis and the app. The production version adds Coturn for NAT traversal, making it suitable for cross-network transfers.

## Feature Comparison Table

| Feature | Snapdrop | PairDrop | FilePizza |
|---------|----------|----------|-----------|
| **GitHub Stars** | 19,700+ | 10,100+ | 10,000+ |
| **Last Updated** | Feb 2025 | Feb 2025 | Apr 2026 |
| **License** | GPL-3.0 | GPL-3.0 | MIT |
| **WebRTC P2P** | Yes | Yes | Yes |
| **PWA Support** | Yes | Yes | Partial |
| **Room-Based Sharing** | No | Yes | No (URL-based) |
| **QR Code Join** | No | Yes | No |
| **WebSocket Fallback** | No | Yes | No |
| **Multi-Download** | Broadcast | Broadcast | One uploader, many downloaders |
| **Rate Limiting** | No | Built-in | No |
| **Debug Mode** | No | Built-in | No |
| **TURN Server Support** | Manual config | Built-in config flag | Via Coturn compose |
| **Docker Image** | Community LSIO | Official LSIO | Official (`kern/filepizza`) |
| **Dependencies** | Node.js, Nginx | Single container | Redis (required) |
| **External Signaling** | Own server | Own server | Redis |

## Deployment Recommendations

### For Home Networks and LAN Transfers

**PairDrop** is the best choice. It is actively maintained, has a single Docker container deployment, and works immediately on any local network. The room feature means you can create a private room, share the link or QR code, and only the people you invite will see each other — even if they are on different Wi-Fi networks.

```bash
docker run -d \
  --name pairdrop \
  -p 3000:3000 \
  -e PUID=1000 -e PGID=1000 \
  -e TZ=Etc/UTC \
  --restart unless-stopped \
  lscr.io/linuxserver/pairdrop:latest
```

### For Quick One-Time File Drops

**FilePizza** excels when you want to send a large file to someone without both parties being on the same network. Generate a unique URL, share it via any channel, and the recipient downloads directly from your browser. No server storage, no account needed.

### For a Classic AirDrop-Like Experience

**Snapdrop** offers the simplest, most polished landing page experience. It shows all nearby devices as circles and lets you tap to send files. However, the project has seen slower development activity compared to PairDrop. If you need the latest features and active maintenance, PairDrop is the better fork to use.

### Reverse Proxy Configuration

When deploying behind a reverse proxy like Nginx or Traefik, you must proxy WebSocket connections for the signaling to work. Here is an Nginx configuration that works for all three tools:

```nginx
server {
    listen 443 ssl;
    server_name fileshare.example.com;

    ssl_certificate /etc/ssl/certs/fileshare.crt;
    ssl_certificate_key /etc/ssl/private/fileshare.key;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

The `Upgrade` and `Connection` headers are critical — without them, the WebSocket signaling connection fails and devices cannot discover each other.

## Frequently Asked Questions

### Do these tools store files on the server?

No. All three tools use WebRTC for peer-to-peer data transfer. The server's only role is peer discovery (signaling) — telling browsers about each other so they can establish a direct connection. File data never passes through the server. FilePizza explicitly does not store files server-side; files stream directly from the uploader's browser to the downloader's browser.

### Can I transfer files between devices on different networks?

Yes, but you need a TURN server configured. WebRTC tries to establish a direct peer-to-peer connection first, but if both devices are behind NAT (which is almost always the case for different networks), a TURN relay server is required. PairDrop has built-in support for TURN configuration via the `RTC_CONFIG` environment variable. FilePizza includes Coturn in its production docker-compose. Snapdrop requires manual TURN configuration.

### What is the maximum file size I can transfer?

There is no hardcoded limit in any of these tools. The practical limit depends on the devices involved — browser memory, available RAM, and network stability. For very large files (several gigabytes), PairDrop's WebSocket fallback or FilePizza's streaming approach tend to be more reliable than pure WebRTC data channels.

### Do I need HTTPS to run these tools?

Yes. WebRTC APIs are only available in secure contexts, meaning you must serve these applications over HTTPS (or localhost). For local network deployments, you can use self-signed certificates or a local CA. For public-facing instances, use Let's Encrypt or any standard TLS certificate.

### Which tool is the most actively maintained?

As of April 2026, FilePizza is the most actively updated (last commit within the past week). PairDrop is the most actively developed fork in the Snapdrop ecosystem, with room-based sharing, QR codes, and WebSocket fallback. The original Snapdrop project has slowed significantly, with its last meaningful update in early 2025.

### Can I customize the UI or branding?

All three projects are open-source and can be modified. PairDrop and Snapdrop have HTML/CSS in their `public/` directories that can be edited directly. FilePizza, being a Next.js application, requires rebuilding after UI changes. For a quick rebrand, PairDrop is the easiest to customize thanks to its simpler architecture.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PairDrop vs Snapdrop vs FilePizza: Best Self-Hosted Browser File Sharing 2026",
  "description": "Compare PairDrop, Snapdrop, and FilePizza — three open-source, self-hosted tools for browser-to-browser file transfer over WebRTC. Includes Docker setup, feature comparison, and deployment guide.",
  "datePublished": "2026-04-22",
  "dateModified": "2026-04-22",
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
