---
title: "Self-Hosted IRC: The Lounge vs ZNC vs Ergo — Complete Setup Guide 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Set up your own always-on IRC experience with The Lounge, ZNC, or Ergo. Compare IRC web clients, bouncers, and full servers with Docker configs, SSL setup, and deployment guides."
---

Internet Relay Chat has been around since 1988, but it remains one of the most resilient, decentralized, and privacy-respecting real-time communication protocols. Unlike Discord, Slack, or Teams — where your messages live on someone else's servers and your identity is tied to a corporate account — IRC is open, federated, and fully self-controllable.

This guide covers three self-hosted IRC solutions at different levels of the stack: **The Lounge** (a modern web IRC client with always-on connections), **ZNC** (a traditional IRC bouncer that keeps you connected to any network), and **Ergo** (a complete IRC server for running your own network). Whether you want a better way to access public IRC networks or host your own private server, there's a solution here for you.

## Why Self-Host Your IRC Setup

Running your own IRC infrastructure solves problems that cloud chat platforms create:

- **No platform lock-in** — IRC is an open protocol. You can switch clients, servers, or networks at any time without losing your identity or history.
- **Always-on presence** — A self-hosted bouncer or web client stays connected 24/7, so you never miss messages even when your laptop is closed.
- **Complete message history** — Scrollback and logs stored on your server, not in a proprietary cloud database you can't export.
- **Privacy** — No telemetry, no analytics, no corporate surveillance of your conversations.
- **Lightweight** — IRC uses minimal bandwidth and CPU. A single $5/month VPS can host an IRC server for hundreds of users.
- **Decentralized** — No single point of failure. Thousands of independent IRC networks exist worldwide, and you can run your own.
- **Open standards** — IRCv3 extensions add modern features like message tagging, account authentication, and real-time typing indicators.

For related reading on self-hosted messaging alternatives, see our [Matrix/Synapse messaging guide](../matrix-synapse-self-hosted-messaging-guide/) and [Revolt Discord alternative](../revolt-self-hosted-discord-alternative-guide/). If you're building a broader communication stack, our [[mattermost](https://mattermost.com/) vs Rocket.Chat vs Zulip comparison](../mattermost-vs-rocketchat-vs-zulip/) covers team chat platforms.

## The Three Solutions at a Glance

These three tools solve different problems in the IRC ecosystem:

| Feature | The Lounge | ZNC | Ergo |
|---|---|---|---|
| **Type** | Web IRC client | IRC bouncer | IRC server (ircd) |
| **Primary Use** | Access IRC from any browser | Stay connected to IRC networks | Host your own IRC network |
| **Language** | TypeScript/Node.js | C++ | Go |
| **GitHub Stars** | 6,220+ | 2,100+ | 3,100+ |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2026 |
| **Always-On** | Yes (server stays connected) | Yes (bouncer stays connected) | N/A (it IS the server) |
| **Multi-User** | Yes | Yes | Yes |
| **Web Interface** | Built-in | No (use with any IRC client) | No (it IS the server) |
| **SSL/TLS** | Supported | Supported | Built-in (ACME/Let's Encrypt) |
| **SASL Auth** | Yes | Yes | Yes |
| **Message Storage** | In-memory (optional file logging) | Playback buffer on reconnect | Built-in message history |
| **Bouncer Mode** | Yes (always-on client) | Yes (dedicated bouncer) | Yes (bouncer built in) |
| **[docker](https://www.docker.com/) Image** | LinuxServer.io / GHCR | LinuxServer.io | GHCR |
| **Best For** | Users who want a web-based IRC experience | Users connecting to multiple IRC networks | Organizations wanting a private IRC network |

## The Lounge — Modern Self-Hosted Web IRC Client

**The Lounge** is a self-hosted web IRC client that runs on your server but provides a full IRC experience from any browser. It stays connected to IRC networks even when you close your browser tab, functioning as both a client and a lightweight bouncer.

### Key Features

- Responsive web UI that works on desktop and mobile browsers
- File uploads and inline image previews
- Push notifications (via Pushbullet or generic web push)
- Themes and customizable layouts
- Built-in user management with admin panel
- Supports all major IRC networks (Libera.Chat, OFTC, Rizon, etc.)
- IRCv3 support including message history, typing indicators, and server-time

### Docker Compose Setup

The easiest way to deploy The Lounge is via the LinuxServer.io image, which handles dependencies and provides a consistent update path:

```yaml
services:
  thelounge:
    image: lscr.io/linuxserver/thelounge:latest
    container_name: thelounge
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./thelounge-config:/config
    ports:
      - 9000:9000
    restart: unless-stopped
```

After starting with `docker compose up -d`, access the web interface at `http://your-server:9000`. Create your first user:

```bash
docker exec thelounge thelounge add yourusername
```

The config files are stored in `./thelounge-config/`, including user configurations with network details, IRC nicknames, and connection preferences. Each user can add multiple networks through the web UI.

### Connecting to a Network

Once logged in, click the "+" button to add a network. Configure:

- **Network name**: Libera.Chat (or any network)
- **Server host**: `irc.libera.chat`
- **Port**: `6697` (TLS) or `6667` (plaintext)
- **TLS**: Enable for encrypted connections
- **Nick**: Your desired nickname
- **SASL**: If the network requires authentication (e.g., NickServ), enter your credentials

The Lounge will maintain this connection in the background. When you open the web UI from any device, your scrollback and channel history are immediately available.

## ZNC — The Classic IRC Bouncer

**ZNC** is an IRC bouncer — it sits between your IRC client and the IRC network, maintaining a persistent connection even when your client disconnects. When you reconnect, ZNC plays back missed messages from its buffer.

### Key Features

- Connect to multiple IRC networks from a single bouncer
- Playback buffer shows missed messages on reconnect
- Modular architecture: connect modules for auto-voice, channel forwarding, web admin, and more
- Supports SSL/TLS for both upstream (bouncer-to-network) and downstream (client-to-bouncer) connections
- Web administration interface for managing networks and users
- Works with any IRC client (HexChat, WeeChat, Irssi, The Lounge, etc.)
- Network-specific nicknames and channel configurations

### Docker Compose Setup

LinuxServer.io provides a well-maintained ZNC image:

```yaml
services:
  znc:
    image: lscr.io/linuxserver/znc:latest
    container_name: znc
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    volumes:
      - ./znc-config:/config
    ports:
      - 6501:6501
    restart: unless-stopped
```

On first run, ZNC generates a default configuration. You'll need to create an admin account:

```bash
# Generate a password hash
docker exec znc znc --makepass

# Or use the web interface at http://your-server:6501 to set up
```

The ZNC configuration file (`znc.conf`) controls everything: users, networks, modules, and listeners. A minimal config for a single user on one network looks like:

```
Listener4 = port=6501, ssl=true

<User youruser>
    Admin = true
    Nick = YourNick
    AltNick = YourNick_

    <Network libera>
        Server = irc.libera.chat +6697

        <Chan #linux>
        </Chan>

        <Chan #programming>
        </Chan>
    </Network>
</User>
```

The `+` before the port number enables SSL. ZNC's web admin interface (accessible at `https://your-server:6501`) makes managing networks and channels much easier than editing config files.

### Using ZNC with Any IRC Client

To connect your IRC client to ZNC:

- **Server**: `your-server.example.com`
- **Port**: `6501`
- **TLS**: Enabled
- **Password**: `youruser/networkname:zncpassword` (format: `user/network:pass`)
- **Nick**: Whatever ZNC is configured to use

This setup means you can switch between IRC clients (desktop WeeChat at home, mobile IRC on the go) without losing your connection or message history.

## Ergo — Self-Hosted IRC Server

**Ergo** is a full IRC server written in Go. Unlike The Lounge and ZNC — which connect to existing IRC networks — Ergo lets you host your own IRC network. It's designed for organizations, communities, or anyone who wants a private, self-contained chat server.

### Key Features

- Full IRCv3 compliance with modern extensions
- Built-in bouncer functionality (no separate bouncer needed)
- Persistent connections with message history replay
- Built-in TLS certificate management via ACME (Let's Encrypt)
- No external database — everything stored in a lightweight embedded system
- NickServ and ChanServ services built in
- Supports both traditional IRC clients and web connections
- Low resource usage — a single binary with no runtime dependencies
- Optional identd support for enterprise environments

### Docker Compose Setup

Ergo provides an official image on GitHub Container Registry:

```yaml
services:
  ergo:
    image: ghcr.io/ergochat/ergo:latest
    container_name: ergo
    ports:
      - 6667:6667
      - 6697:6697
    volumes:
      - ./ergo-config:/ircd
      - ./ergo-data:/ircd/data
    restart: unless-stopped
    command: ["--conf", "/ircd/ircd.yaml"]
```

On first run, generate the default configuration:

```bash
mkdir -p ergo-config ergo-data
docker run --rm -v $(pwd)/ergo-config:/ircd ghcr.io/ergochat/ergo:latest mkconf
```

### Configuring Ergo

Edit the generated `ircd.yaml` to customize your server:

```yaml
network:
  name: "MyNetwork"
  server:
    - "irc.example.com"

server:
  websockets:
    - addr: "0.0.0.0"
      port: 8090
      tls: false

accounts:
  authentication-enabled: true
  bouncers:
    enabled: true

data:
  path: "/ircd/data"

channels:
  registration:
    enabled: true
```

Key configuration points:

- **`accounts.authentication-enabled`**: Enable to allow user registration and login via NickServ
- **`accounts.bouncers.enabled`**: Enable built-in bouncer mode so users can stay connected even when their client disconnects
- **`channels.registration.enabled`**: Allow users to register channels with ChanServ
- **`server.websockets`**: Enable websocket support for web-based IRC clients (including The Lounge)

After editing, start the server:

```bash
docker compose up -d
```

### Creating an Admin Account

```bash
docker exec ergo ergo register admin yourpassword admin@example.com
```

Then connect with any IRC client to `your-server:6697` (TLS) and log in with SASL or `/msg NickServ IDENTIFY`.

## Choosing the Right Solution

The decision depends on what problem you're solving:

### Use The Lounge if:
- You want a polished web interface for accessing existing IRC networks
- You need always-on connections with mobile-friendly access
- You don't want to manage separate bouncer infrastructure
- You connect to one or two networks and want simplicity

### Use ZNC if:
- You connect to multiple IRC networks (Libera, OFTC, Rizon, etc.)
- You prefer using your own IRC client (WeeChat, HexChat, Irssi)
- You need extensive customization via modules
- You want a battle-tested bouncer with decades of development history

### Use Ergo if:
- You want to run your own private IRC network
- You need a server for your organization or community
- You want built-in bouncer functionality without extra infrastructure
- You need IRCv3 compliance with modern features out of the box

### Combining Solutions

These tools are not mutually exclusive. A common setup is **Ergo + The Lounge**: run Ergo as your private IRC server and connect The Lounge to it for a web-based experience. Another popular combination is **ZNC + The Lounge**, where The Lounge connects to ZNC as its upstream, giving you both bouncer-level persistence and a beautiful web interface.

F[nginx](https://nginx.org/)e reverse proxy in front of these services, our [Nginx vs Caddy vs Traefik comparison](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/) covers the best options for exposing your IRC web interface securely over HTTPS. If you're accessing your IRC server remotely, consider setting up a [WireGuard VPN](../self-hosted-vpn-solutions-wireguard-openvpn-tailscale-guide/) for encrypted tunnel access.

## SSL/TLS Configuration for IRC

Secure your IRC connections with TLS. For The Lounge and ZNC (behind a reverse proxy), obtain certificates with Certbot or use your proxy's built-in ACME support:

```nginx
# Nginx reverse proxy for The Lounge
server {
    listen 443 ssl http2;
    server_name irc.example.com;

    ssl_certificate /etc/letsencrypt/live/irc.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/irc.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:9000;
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

Ergo handles TLS natively — just point it to your certificate files in `ircd.yaml` under the `tls` section, or enable ACME for automatic Let's Encrypt certificates.

## FAQ

### What is the difference between an IRC client, bouncer, and server?

An **IRC client** (like HexChat or The Lounge) is the application you use to send and receive messages. An **IRC bouncer** (like ZNC) sits between your client and the IRC network, maintaining a persistent connection and buffering messages. An **IRC server** (like Ergo) is the actual infrastructure that routes messages between users — it's what you run to create your own IRC network. The Lounge is unique because it combines client and lightweight bouncer functionality.

### Can I use The Lounge with ZNC?

Yes. The Lounge can connect to ZNC as its upstream IRC server. Configure The Lounge to point to your ZNC instance (typically on port 6501 with TLS), and you get both ZNC's multi-network bouncer features and The Lounge's modern web interface. The connection format for the password is `user/network:zncpassword`.

### Do I need an IRC server if I just want to chat on existing networks?

No. If you want to join channels on public IRC networks like Libera.Chat, OFTC, or Rizon, you only need a client (or bouncer + client). An IRC server like Ergo is only needed if you want to host your own private network with custom channels and user management.

### Is IRC still relevant in 2026?

Yes. IRC remains widely used in open source communities (Libera.Chat hosts thousands of project channels), cybersecurity, DevOps, and privacy-conscious organizations. Its lightweight nature, open protocol, and lack of corporate control make it ideal for communities that value decentralization. IRCv3 extensions have also modernized the protocol with features like message history, typing indicators, and account services.

### How do I migrate from a hosted IRC service to a self-hosted setup?

The migration depends on your starting point. If you're moving from a hosted bouncer service (like ZNC on a shared provider), export your ZNC configuration and import it into your self-hosted instance. If you're moving to a self-hosted server like Ergo, users will need to connect to your new server address and re-register nicknames. Channel operators should use `/CS TRANSFER` or export channel settings before the switch.

### Can I run all three — The Lounge, ZNC, and Ergo — on the same server?

Absolutely. Each runs on different ports by default (The Lounge on 9000, ZNC on 6501, Ergo on 6667/6697). They have no port conflicts and can coexist on a single VPS with minimal resources. A typical combined setup uses Ergo as the private IRC server, ZNC as a bouncer for external networks, and The Lounge as a web frontend for both.

### How much bandwidth does an IRC server use?

Very little. A lightly-used IRC server with 10-20 concurrent users typically uses less than 1 MB of bandwidth per day. IRC is a text-based protocol, so even with active channels, bandwidth consumption is minimal compared to modern messaging platforms that sync images, videos, and rich media.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted IRC: The Lounge vs ZNC vs Ergo — Complete Setup Guide 2026",
  "description": "Set up your own always-on IRC experience with The Lounge, ZNC, or Ergo. Compare IRC web clients, bouncers, and full servers with Docker configs, SSL setup, and deployment guides.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
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
