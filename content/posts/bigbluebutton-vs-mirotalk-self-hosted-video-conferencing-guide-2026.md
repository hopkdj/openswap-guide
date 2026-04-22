---
title: "BigBlueButton vs MiroTalk: Best Self-Hosted Video Conferencing 2026"
date: 2026-04-22
tags: ["comparison", "guide", "self-hosted", "privacy", "video-conferencing"]
draft: false
description: "Compare BigBlueButton and MiroTalk for self-hosted video conferencing in 2026. Covers Docker deployment, architecture, features, and scalability for education and enterprise use."
---

Video conferencing has become essential for education, business, and remote collaboration. Yet commercial platforms like Zoom, Microsoft Teams, and Google Meet collect meeting metadata, impose participant limits, and require ongoing subscriptions. Self-hosting your video conferencing infrastructure gives you full control over data, removes artificial caps, and eliminates recurring licensing costs.

While [Jitsi Meet](https://jitsi.org/) is the most well-known open-source option, two other families of tools have matured significantly: **BigBlueButton**, built specifically for online education, and **MiroTalk**, a lightweight WebRTC platform with both peer-to-peer and server-based variants. This guide compares all three approaches to help you choose the right self-hosted video conferencing solution for your use case.

## Why Self-Host Video Conferencing

The arguments for running your own video conferencing server extend well beyond cost savings:

- **Data sovereignty**: Meeting recordings, chat logs, and participant analytics never leave your infrastructure. No third-party servers store your conversation metadata.
- **No participant or time limits**: Commercial platforms throttle free tiers at 40–60 minutes or cap attendees at 100. Self-hosted solutions have no such restrictions.
- **Full customization**: Brand the interface, integrate with LDAP or SAML authentication, enable or disable specific features, and modify the code to fit your workflow.
- **Compliance readiness**: Organizations subject to GDPR, FERPA (for education), or HIPAA benefit from keeping all communication data on-premises.
- **Predictable pricing**: A single $50/month VPS can replace dozens of commercial licenses, with costs that stay flat as your user base grows.

## Option 1: BigBlueButton — Education-First Web Conferencing

[BigBlueButton](https://bigbluebutton.org/) is an open-source web conferencing system designed specifically for online learning. With over 9,000 stars on GitHub and active development (last commit April 2026), it is the most feature-complete self-hosted alternative to Zoom for educational institutions.

### Architecture

BigBlueButton is not a single application — it is a coordinated stack of specialized services:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **HTML5 Client** | React, WebRTC | Browser-based meeting interface |
| **Kurento/Mediasoup** | Media server | Video/audio routing and mixing |
| **FreeSWITCH** | VoIP server | Audio conferencing, SIP bridging |
| **bbb-web** | Scala/Grails | API server, meeting management |
| **bbb-graphql-server** | Hasura + PostgreSQL | Real-time data subscriptions |
| **bbb-graphql-middleware** | Node.js | GraphQL connection management |
| **bbb-graphql-actions** | Node.js | Server-side mutation handlers |
| **Redis** | In-memory store | Pub/sub messaging between components |
| **Nginx** | Web server | Reverse proxy, static file serving |

The architecture has evolved significantly from its original Kurento-based media server to include GraphQL for real-time data flow and Mediasoup for more efficient video routing.

### Key Features

- **Shared whiteboard** with annotation tools, multi-user drawing, and shape libraries
- **Presentation upload** — convert PDF, PPTX, and DOCX to shareable slides with page-by-page navigation
- **Breakout rooms** — split participants into sub-groups for collaborative work
- **Polling and shared notes** — real-time engagement tools built into the interface
- **Recording and playback** — sessions are recorded with synchronized audio, video, whiteboard, and chat
- **Closed captioning** — integrated live captioning support
- **Analytics dashboard** — participation metrics, engagement tracking, and attendance reports

### Installation with bbb-install.sh

BigBlueButton uses an automated installation script rather than Docker, because it requires direct access to specific ports and system services for optimal media performance.

**Prerequisites:**
- Ubuntu 20.04 or 22.04 LTS (64-bit)
- Minimum 8 CPU cores, 16 GB RAM, 250 GB SSD
- Public IPv4 and IPv6 addresses
- Domain name (e.g., `bbb.example.com`) pointing to your server
- Ports **80/tcp, 443/tcp, 16384–32768/UDP** open

```bash
# Install BigBlueButton 2.7 with Let's Encrypt SSL and Greenlight frontend
wget -qO- https://ubuntu.bigbluebutton.org/bbb-install.sh | bash -s -- \
  -v focal-270 \
  -s bbb.example.com \
  -e admin@example.com \
  -g
```

The `-g` flag installs **Greenlight**, BigBlueButton's web frontend that provides room management, user authentication, and meeting scheduling. Without Greenlight, users access meetings directly via the BigBlueButton API.

### Installing Greenlight Separately

Greenlight v3 runs as a Docker Compose application:

```yaml
# docker-compose.yml for Greenlight v3
services:
  greenlight:
    image: bigbluebutton/greenlight:v3
    container_name: greenlight-v3
    restart: unless-stopped
    ports:
      - "3100:3100"
    env_file: .env
    volumes:
      - greenlight-db:/var/lib/postgresql/data

  db:
    image: postgres:14
    container_name: greenlight-db
    restart: unless-stopped
    environment:
      POSTGRES_DB: greenlight
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - greenlight-db:/var/lib/postgresql/data

volumes:
  greenlight-db:
```

Configure the `.env` file with your BigBlueButton API endpoint and secret:

```bash
# .env
SECRET_KEY_BASE=$(openssl rand -hex 64)
BIGBLUEBUTTON_ENDPOINT=https://bbb.example.com/bigbluebutton/
BIGBLUEBUTTON_SECRET=$(bbb-conf --secret | grep Secret | awk '{print $2}')
RAILS_LOG_LEVEL=info
DB_PASSWORD=your-secure-password
```

### Hardware Requirements

| Scale | CPU | RAM | Storage | Concurrent Meetings |
|-------|-----|-----|---------|-------------------|
| Small (testing) | 4 cores | 8 GB | 100 GB | 1–2 |
| Medium (classroom) | 8 cores | 16 GB | 250 GB | 5–10 |
| Large (department) | 16 cores | 32 GB | 500 GB | 20–30 |

BigBlueButton is resource-intensive because it handles media transcoding, recording, and the full application stack on a single host. For larger deployments, Greenlight can be separated onto its own server.

## Option 2: MiroTalk P2P — Lightweight Peer-to-Peer Conferencing

[MiroTalk P2P](https://github.com/miroslavpejic85/mirotalk) is a self-hosted WebRTC video conferencing platform with 4,400+ stars on GitHub. It uses a pure peer-to-peer mesh architecture where every participant connects directly to every other participant — no media server required.

### Architecture

The P2P architecture is elegantly simple:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Node.js signaling** | Socket.IO | Room management, peer discovery |
| **WebRTC** | Browser native | Direct peer-to-peer audio/video/data |
| **Coturn** (optional) | STUN/TURN server | NAT traversal for restricted networks |
| **Express.js** | Web framework | HTTP server, static file serving |

No media server means zero transcoding overhead. Your server only handles signaling (WebSocket connections for room coordination), and the actual video streams flow directly between browsers.

### Key Features

- **Unlimited meeting duration** with no participant count restrictions (practical limit: ~6–8 due to mesh topology)
- **Screen sharing** with window, tab, or full desktop selection
- **File sharing** — send files directly between participants via WebRTC data channels
- **Chat** — public room chat and private 1-to-1 messaging
- **Recording** — local browser recording using `getDisplayMedia` API
- **Collaborative whiteboard** — built-in drawing canvas
- **End-to-end privacy** — no media passes through the server

### Docker Deployment

MiroTalk P2P deploys with a single Docker container. First, create the configuration:

```bash
mkdir mirotalk && cd mirotalk
cp .env.example .env
```

Configure your `.env` file:

```bash
# .env
PORT=3000
HOST=localhost
HOST_PROT=https
TURN_SERVER=turn:your-turn-server:3478
TURN_USERNAME=mirotalk
TURN_PASSWORD=your-turn-password
```

Then deploy with Docker Compose:

```yaml
# docker-compose.yml
services:
  mirotalk:
    image: mirotalk/p2p:latest
    container_name: mirotalk
    hostname: mirotalk
    restart: unless-stopped
    ports:
      - '3000:3000'
    volumes:
      - ./.env:/src/.env:ro
      # Optional: mount custom config for rebranding
      # - ./app/src/config.js:/src/app/src/config.js:ro
```

```bash
docker compose up -d
```

Access the interface at `https://your-domain.com:3000`. Create a room by entering a name and sharing the URL with participants. For production deployments, add a reverse proxy with TLS (see the reverse proxy section below).

### Practical Limitations

The mesh topology means each participant uploads `(N-1)` video streams. With 6 participants on a 10 Mbps uplink, each person sends 5 streams at ~1 Mbps — consuming the full uplink. This makes MiroTalk P2P ideal for small groups (2–6 people) but unsuitable for larger meetings.

## Option 3: MiroTalk SFU — Scalable Server-Based Conferencing

[MiroTalk SFU](https://github.com/miroslavpejic85/mirotalksfu) addresses the mesh topology limitation by introducing a Selective Forwarding Unit (SFU) media server. With 2,900+ stars on GitHub, it supports 20+ participants per meeting while maintaining the same clean interface as the P2P variant.

### Architecture

The SFU variant adds a media server layer:

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Node.js signaling** | Socket.IO | Room management, peer coordination |
| **Mediasoup** | SFU media server | Receives one stream per participant, forwards to others |
| **Coturn** (optional) | STUN/TURN | NAT traversal |
| **Express.js** | Web framework | HTTP serving, REST API |

With an SFU, each participant sends **one** stream to the server, and the server selectively forwards streams to each participant based on their bandwidth and screen layout. This reduces upload bandwidth from `O(N²)` to `O(N)`.

### Docker Deployment

The SFU deployment is similar to P2P but with different port requirements for the media server:

```yaml
# docker-compose.yml for MiroTalk SFU
services:
  mirotalksfu:
    image: mirotalk/sfu:latest
    container_name: mirotalksfu
    hostname: mirotalksfu
    restart: unless-stopped
    ports:
      - '3010:3010/tcp'
      - '40000-40100:40000-40100/tcp'
      - '40000-40100:40000-40100/udp'
    volumes:
      - ./app/src/config.js:/src/app/src/config.js:ro
      - ./.env:/src/.env:ro
      # For recording support:
      # - ./app/rec:/src/app/rec
```

```bash
mkdir mirotalk-sfu && cd mirotalk-sfu
# Copy config and .env from repo
docker compose up -d
```

The wide UDP port range (40000–40100) is required for WebRTC media transport. In production, configure your firewall to allow this range.

### Additional SFU Features

- **RTMP streaming** — broadcast meetings to YouTube, Twitch, or custom RTMP endpoints
- **Recording** — server-side recording with configurable storage
- **Webhook integration** — trigger external services on meeting events (join, leave, start, stop)
- **Breakout rooms** — split meetings into sub-groups
- **Adaptive bitrate** — the SFU adjusts stream quality per participant based on available bandwidth

## Feature Comparison

| Feature | BigBlueButton | MiroTalk P2P | MiroTalk SFU |
|---------|--------------|-------------|-------------|
| **Architecture** | Full-stack monolith | Peer-to-peer mesh | SFU media server |
| **Max participants** | 100+ | 6–8 (practical) | 20–50 |
| **Shared whiteboard** | ✅ Rich annotations | ✅ Basic | ✅ Basic |
| **Presentation upload** | ✅ PDF/PPTX/DOCX | ❌ | ❌ |
| **Breakout rooms** | ✅ Built-in | ❌ | ✅ |
| **Recording** | ✅ Server-side, full playback | ✅ Browser-local | ✅ Server-side |
| **Live captioning** | ✅ | ❌ | ❌ |
| **Polling** | ✅ | ❌ | ❌ |
| **Chat** | ✅ Public + private | ✅ Public + private | ✅ Public + private |
| **Screen sharing** | ✅ | ✅ | ✅ |
| **File sharing** | ✅ | ✅ Via WebRTC | ❌ |
| **SIP integration** | ✅ FreeSWITCH | ❌ | ❌ |
| **Analytics** | ✅ Dashboard | ❌ | ❌ |
| **Greenlight frontend** | ✅ Room management | ❌ | ❌ |
| **RTMP streaming** | Via plugin | ❌ | ✅ Built-in |
| **Docker deployment** | Partial (Greenlight only) | ✅ Full | ✅ Full |
| **Minimum RAM** | 16 GB | 512 MB | 2 GB |
| **Minimum CPU** | 8 cores | 1 core | 2 cores |
| **Best for** | Education, training | Small team calls | Medium meetings |

## Reverse Proxy Configuration

For production deployments, place a reverse proxy in front of your video conferencing server to handle TLS termination and provide clean URLs. Here is an Nginx configuration that works for both MiroTalk variants:

```nginx
server {
    listen 443 ssl http2;
    server_name meet.example.com;

    ssl_certificate /etc/letsencrypt/live/meet.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meet.example.com/privkey.pem;

    # WebSocket support (required for signaling)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";

    location / {
        proxy_pass http://127.0.0.1:3000;  # MiroTalk P2P
        # proxy_pass http://127.0.0.1:3010;  # MiroTalk SFU
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Coturn TURN server (if running on same host)
    location /turn {
        proxy_pass http://127.0.0.1:3478;
    }
}
```

For BigBlueButton, the `bbb-install.sh` script configures Nginx automatically. Manual configuration is rarely needed.

## Coturn STUN/TURN Setup

For participants behind restrictive NATs or corporate firewalls, a TURN relay server ensures connections succeed. MiroTalk and BigBlueButton both benefit from a dedicated Coturn instance. For a detailed guide on deploying Coturn and other STUN/TURN solutions, see our [complete guide to self-hosted TURN/STUN servers](../self-hosted-turn-stun-servers-coturn-restund-pion-webrtc-guide-2026/).

Quick Coturn deployment:

```yaml
# docker-compose.yml for Coturn
services:
  coturn:
    image: coturn/coturn:latest
    container_name: coturn
    restart: unless-stopped
    network_mode: host
    command: >
      -n
      --lt-cred-mech
      --user=mirotalk:your-secret-password
      --realm=meet.example.com
      --external-ip=YOUR_PUBLIC_IP
      --min-port=49152
      --max-port=65535
```

Add the TURN server credentials to your MiroTalk `.env` file or BigBlueButton's `/etc/bigbluebutton/turn-stun-servers.xml`.

## Choosing the Right Platform

**Choose BigBlueButton if:**
- You run an educational institution or training organization
- You need presentation sharing, whiteboards, and breakout rooms
- You require server-side recording with synchronized playback
- You have the hardware resources (16+ GB RAM, 8+ cores)
- You want an integrated analytics dashboard

**Choose MiroTalk P2P if:**
- You need quick, small-group meetings (2–6 people)
- You want minimal server resource usage (runs on a $5 VPS)
- Privacy is paramount — no media touches your server
- You need a dead-simple deployment (one Docker container)

**Choose MiroTalk SFU if:**
- You need medium-sized meetings (10–30 participants)
- You want the lightweight MiroTalk interface with better scalability
- You need RTMP streaming to external platforms
- You have a modest server (2+ GB RAM, 2+ cores)

For organizations evaluating all self-hosted communication tools, our comparisons of [self-hosted voice chat platforms](../2026-04-21-mumble-vs-teamspeak-vs-jamulus-self-hosted-voice-chat-2026/) and [VoIP PBX systems](../2026-04-18-kamailio-vs-asterisk-vs-freeswitch-self-hosted-voip-pbx-guide-2026/) cover complementary infrastructure for a complete self-hosted communication stack.

## FAQ

### Is BigBlueButton free to use?

Yes. BigBlueButton is released under the LGPL-3.0 license and is completely free to download, install, and use. There are no licensing fees, user limits, or feature restrictions. Commercial support is available from third-party providers if you need professional assistance.

### How many participants can BigBlueButton handle?

A properly sized BigBlueButton server (8 cores, 16 GB RAM) can handle 20–30 concurrent meetings with 50–100 participants each. The practical limit per meeting depends on server capacity and network bandwidth. For very large deployments, multiple BBB servers can be load-balanced.

### What is the difference between MiroTalk P2P and SFU?

MiroTalk P2P uses a peer-to-peer mesh where every participant connects directly to every other participant. This works well for 2–6 people but doesn't scale. MiroTalk SFU introduces a media server (Mediasoup) that receives one stream per participant and selectively forwards streams to others, enabling meetings with 20–50 participants on modest hardware.

### Do I need a TURN server for MiroTalk?

A TURN server is recommended for production deployments. Without it, participants behind symmetric NATs or strict corporate firewalls may fail to connect. For small teams on the same network, direct P2P connections usually work. Coturn is the most popular open-source TURN server and integrates easily with both MiroTalk variants.

### Can BigBlueButton run on Docker?

Not directly. BigBlueButton requires direct access to system services (FreeSWITCH, Nginx, Redis, PostgreSQL) and specific port ranges for media. The official installation method uses `bbb-install.sh` on Ubuntu. However, the Greenlight frontend (room management UI) does run as a Docker Compose application and can be deployed separately from the BBB backend.

### How do I add authentication to MiroTalk?

MiroTalk P2P and SFU support basic authentication via environment variables. For enterprise-grade authentication, integrate with your existing identity provider using OIDC or SAML. The SFU variant supports webhook-based authentication hooks that can validate participants against an external service before granting room access.

### What are the bandwidth requirements for self-hosted video conferencing?

For MiroTalk P2P with 4 participants: each participant needs ~4 Mbps upload (3 streams at ~1.3 Mbps each). For MiroTalk SFU: each participant needs ~1.5 Mbps upload (one stream to the server), and the server needs ~30 Mbps total for 20 participants. For BigBlueButton: plan for 2–4 Mbps per active video stream, plus additional bandwidth for recordings and presentation sharing.

### Can I record meetings with MiroTalk?

MiroTalk P2P records locally in the browser using the `getDisplayMedia` API — the recording file is saved on the participant's device. MiroTalk SFU supports server-side recording (when enabled in the `.env`), which saves recordings to the server filesystem. BigBlueButton has the most sophisticated recording system, capturing synchronized audio, video, whiteboard, and chat with a playback interface.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "BigBlueButton vs MiroTalk: Best Self-Hosted Video Conferencing 2026",
  "description": "Compare BigBlueButton and MiroTalk for self-hosted video conferencing in 2026. Covers Docker deployment, architecture, features, and scalability for education and enterprise use.",
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
