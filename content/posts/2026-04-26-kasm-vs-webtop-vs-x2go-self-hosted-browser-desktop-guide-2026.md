---
title: "Kasm Workspaces vs LinuxServer Webtop vs x2go: Self-Hosted Browser Desktop Guide 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "remote-desktop", "docker"]
draft: false
description: "Compare Kasm Workspaces, LinuxServer Webtop, and x2go for self-hosted browser-based desktop access. Installation guides, Docker configs, and feature comparison for 2026."
---

When you need remote access to a full desktop environment through a web browser, you have several self-hosted options — each with different architectures, resource footprints, and use cases. Whether you are isolating risky browsing sessions, providing developers with pre-configured workspaces, or accessing your home lab from anywhere, choosing the right platform matters.

In this guide, we compare three popular approaches: **Kasm Workspaces**, **LinuxServer Webtop**, and **x2go**. These tools serve different niches — from enterprise-grade workspace orchestration to lightweight Docker containers to traditional X11 remote desktop — and understanding their tradeoffs helps you pick the right solution.

For a broader look at self-hosted remote access tools including client-based solutions, see our [remote desktop comparison](../self-hosted-remote-desktop-guacamole-rustdesk-meshcentral-guide/) and [SSH bastion server guide](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/).

## Why Self-Host a Browser Desktop?

Running your own browser-based desktop platform gives you control over several important factors:

- **Security isolation**: Run untrusted applications or browse risky websites inside disposable containers that are destroyed after each session
- **Cost control**: Avoid per-user SaaS pricing for virtual desktop infrastructure (VDI)
- **Customization**: Pre-install exactly the tools your team needs — development environments, design software, or specialized applications
- **Privacy**: All data stays on your own hardware; no third-party provider has access to your sessions
- **Always-available access**: Access your full desktop from any device with a browser — Chromebook, tablet, or phone

## What Are We Comparing?

### Kasm Workspaces

Kasm Workspaces is a containerized workspace delivery platform that streams full desktop environments and individual applications to any modern web browser. Originally built for security research and browser isolation, it has evolved into a full VDI replacement. The core platform is available as a free community edition with a paid enterprise tier.

Kasm uses a Docker-based architecture with a management layer that handles user authentication, session routing, image management, and policy enforcement. Each workspace runs in its own isolated Docker container with GPU passthrough support.

Key facts: Kasm has active community repositories on GitHub, regular updates, and supports a growing catalog of pre-built workspace images including development environments, office suites, and security tools.

### LinuxServer Webtop

LinuxServer Webtop is a collection of Docker images that run full desktop environments (XFCE, KDE, MATE, i3) accessible through a browser via noVNC and Guacamole. It is part of the broader LinuxServer.io ecosystem, which maintains hundreds of popular self-hosted Docker images.

Webtop is simpler than Kasm — there is no management console, no user directory, and no session orchestration. You run one or more containers, each representing a single desktop, and connect to them directly. This makes it ideal for personal use or small homelabs where you do not need multi-user management.

With over 4,100 stars on GitHub and active maintenance (last updated April 2026), Webtop is one of the most popular ways to run a Linux desktop in a browser.

### x2go

x2go is an open-source remote desktop solution based on the NX protocol — a highly optimized X11 transport protocol that compresses display data for efficient transmission over low-bandwidth connections. Unlike the browser-based tools above, x2go uses a dedicated client application (available for Windows, macOS, and Linux) to connect to an x2go server.

x2go has been around since 2008 and is mature and stable, but development has slowed considerably in recent years. The last major release was several years ago, and the project has largely been maintained by the community. Despite this, it remains an excellent choice for traditional Linux-to-Linux remote desktop sessions, particularly on slow or unreliable connections.

## Feature Comparison

| Feature | Kasm Workspaces | LinuxServer Webtop | x2go |
|---|---|---|---|
| **Access method** | Web browser (noVNC-based) | Web browser (noVNC/Guacamole) | Desktop client (x2goclient) |
| **Architecture** | Docker containers + management server | Individual Docker containers | NX protocol over SSH |
| **Multi-user support** | Yes — full user management, roles, SSO | No — one container per user | Yes — multi-user Linux server |
| **Desktop environments** | Ubuntu, CentOS, Kali, Parrot, custom images | XFCE, KDE, MATE, i3, Awesome | Any X11 desktop (system-level) |
| **Session persistence** | Optional — can be ephemeral or persistent | Persistent (volume-backed) | Persistent (server filesystem) |
| **GPU acceleration** | Yes — GPU passthrough support | Limited — no native GPU passthrough | No — CPU rendering only |
| **Audio support** | Yes — PulseAudio streaming | Yes — PulseAudio in container | Yes — PulseAudio over NX |
| **Clipboard sync** | Yes — bidirectional | Yes — bidirectional | Yes — bidirectional |
| **File transfer** | Upload/download via web UI | Via mounted volumes | Built-in file transfer in client |
| **Installation complexity** | Moderate — requires install script | Simple — single docker-compose | Moderate — requires server + client |
| **Resource usage** | Moderate — Docker + management overhead | Low to moderate — per-container | Low — no container overhead |
| **Mobile support** | Good — responsive web UI | Fair — desktop UI on mobile | Poor — no mobile client |
| **License** | Community (free) + Enterprise (paid) | GPL v3 (fully open source) | GPL v2 (fully open source) |
| **Best for** | Teams, browser isolation, VDI replacement | Personal use, homelabs, simple setups | Traditional Linux remote desktop |

## Installing Kasm Workspaces

Kasm provides an automated installation script that sets up the Docker infrastructure, management services, and networking on a single host.

### System Requirements

- Ubuntu 20.04/22.04 LTS (recommended)
- Minimum 4 GB RAM (8 GB recommended)
- Docker installed
- 2 CPU cores minimum

### Quick Install

```bash
# Download the installation script
curl -O https://raw.githubusercontent.com/kasmtech/workspaces-core/develop/kasm_release/install.sh

# Make it executable and run as root
chmod +x install.sh
sudo bash install.sh
```

After installation, access the management console at `https://<your-server-ip>:8443`. The default credentials are `admin@kasm.local` with a password generated during install.

### Creating a Workspace

Once logged in, navigate to **Workspaces** → **Workspace Groups** to assign pre-built images to users. Kasm ships with images for:

- Ubuntu desktop with Firefox
- Kali Linux with security tools
- Parrot OS
- Development environments (Python, Node.js, Go)
- Office productivity suites

### Custom Workspace Image

To build your own workspace image:

```dockerfile
FROM kasmweb/core-ubuntu-focal:1.15.0

# Install additional packages
RUN apt-get update && apt-get install -y \
    vim \
    git \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up user environment
USER kasm-user
WORKDIR /home/kasm-user
```

Build and push to a registry, then register the image in the Kasm admin console.

## Installing LinuxServer Webtop

Webtop is deployed as a standard Docker container. The simplest way to run it is with a docker-compose file.

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  webtop:
    image: lscr.io/linuxserver/webtop:latest
    container_name: webtop
    security_opt:
      - seccomp:unconfined
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
      - SUBFOLDER=/
      - TITLE=Webtop
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./webtop-config:/config
    ports:
      - 3000:3000
    shm_size: "1gb"
    restart: unless-stopped
```

### Available Desktop Flavors

LinuxServer provides multiple tags for different desktop environments:

```yaml
# KDE Plasma (full-featured)
image: lscr.io/linuxserver/webtop:kde

# XFCE (lightweight)
image: lscr.io/linuxserver/webtop:xfce

# MATE (traditional)
image: lscr.io/linuxserver/webtop:mate

# i3 (tiling window manager)
image: lscr.io/linuxserver/webtop:i3

# Arch Linux base
image: lscr.io/linuxserver/webtop:arch

# Alpine Linux base (minimal)
image: lscr.io/linuxserver/webtop:alpine
```

### Accessing Your Desktop

Once the container is running, open `http://<server-ip>:3000` in any browser. You will see the full desktop environment rendered in the browser window. Audio is supported via PulseAudio streaming.

## Installing x2go

x2go uses a traditional server-client model. You install the server on the remote machine and the client on your local device.

### Server Installation (Ubuntu/Debian)

```bash
# Add the x2go PPA
sudo add-apt-repository ppa:x2go/stable

# Install the server
sudo apt update
sudo apt install x2goserver x2goserver-xsession

# Install a desktop environment if not present
sudo apt install xfce4 xfce4-goodies

# The server auto-registers with SSH — no additional daemon needed
```

### Client Installation

```bash
# Ubuntu/Debian client
sudo apt install x2goclient

# macOS client
brew install --cask x2goclient

# Windows — download from https://wiki.x2go.org/doku.php/download:start
```

### Connecting to Your Server

1. Open x2go client
2. Click **Session** → **New session**
3. Enter server hostname, your SSH username, and session type (XFCE)
4. Set connection speed (LAN, WAN, or custom)
5. Click **OK** and then connect — authenticate with your SSH credentials

### Optimizing x2go for Low Bandwidth

x2go excels on slow connections. In the session settings:

- **Connection type**: Set to WAN or 3G for aggressive compression
- **Display resolution**: Lower to 1024x768 for bandwidth savings
- **Disable desktop effects**: Turn off compositing and animations
- **Use JPEG compression**: In the media settings, enable JPEG for better image compression over slow links

```
# Example ~/.x2go/x2goclient.conf tuning
# Lower quality for speed
jpeg=9
# Disable sound if not needed
sound=false
```

## Performance Comparison

### Resource Usage

| Metric | Kasm Workspaces | LinuxServer Webtop | x2go |
|---|---|---|---|
| **Idle RAM** | ~800 MB (management + container) | ~400-600 MB per container | ~200 MB (server daemon) |
| **CPU overhead** | Moderate (Docker + streaming) | Low-moderate | Very low (NX compression) |
| **Network at idle** | ~50 Kbps | ~30 Kbps | ~5 Kbps |
| **Network (video)** | ~2-5 Mbps | ~1-3 Mbps | ~0.5-2 Mbps |

### Latency and Responsiveness

- **Kasm**: Near-instant for desktop tasks; slight lag on video playback. GPU passthrough significantly improves media performance.
- **Webtop**: Good for standard desktop use. noVNC adds slight overhead compared to native protocols.
- **x2go**: Excellent latency on LAN; the NX protocol is highly optimized. Best of the three for slow or high-latency connections.

## Security Considerations

### Kasm Workspaces

Kasm is designed with security as a primary use case. Each workspace runs in an isolated Docker container with restricted capabilities. Ephemeral sessions destroy the entire container after logout, leaving no trace. The management console supports SAML/OIDC SSO, two-factor authentication, and granular access policies.

### LinuxServer Webtop

Webtop inherits Docker's security model. Running with `seccomp:unconfined` is required for full desktop functionality but reduces container isolation. For improved security, run Webtop behind a reverse proxy with TLS and use authentication middleware. Consider using rootless Podman as an alternative to Docker.

### x2go

x2go uses SSH for transport, inheriting SSH's strong encryption and authentication. You can restrict access with SSH key-only authentication, fail2ban integration (see our [intrusion prevention guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/)), and firewall rules. The downside is that x2go sessions share the host OS — there is no container-level isolation between users.

## Which Should You Choose?

**Choose Kasm Workspaces if:**
- You need multi-user workspace management with SSO
- Browser isolation and disposable sessions are a priority
- You want pre-built images for development or security work
- GPU-accelerated workspaces are needed

**Choose LinuxServer Webtop if:**
- You need a simple, personal browser-based desktop
- You want quick setup with Docker
- You prefer XFCE, KDE, or other standard desktop environments
- You are already in the LinuxServer.io ecosystem

**Choose x2go if:**
- You need the lowest possible bandwidth usage
- You are connecting Linux-to-Linux with a dedicated client
- You want a mature, proven solution without container overhead
- Your network is unreliable or slow

## FAQ

### Is Kasm Workspaces free to use?

Yes, Kasm offers a free Community Edition that includes the core workspace streaming platform, user management, and pre-built images. The Enterprise Edition adds features like SAML SSO, LDAP integration, advanced policy controls, and priority support. For most homelab and small team use cases, the Community Edition is sufficient.

### Can LinuxServer Webtop run on ARM devices like Raspberry Pi?

Yes. LinuxServer provides multi-architecture images that work on amd64, arm64, and arm32v7. You can run Webtop on a Raspberry Pi 4 with 4+ GB RAM using the `lscr.io/linuxserver/webtop:latest` image. Performance will depend on the Pi model — Pi 4 handles XFCE well, while heavier desktops like KDE may be sluggish.

### Does x2go support Wayland desktop sessions?

No, x2go is built on the X11/NX protocol and does not support Wayland. You need to run an X11-based desktop environment (XFCE, MATE, LXDE) on the server. If your distribution defaults to Wayland (like recent Ubuntu or Fedora), you will need to switch to an X11 session for x2go to work.

### Can I use these tools for remote gaming or video editing?

None of these tools are optimized for real-time 3D rendering. Kasm Workspaces offers GPU passthrough which can handle light 3D work and video playback, but it is not a replacement for native performance. x2go and Webtop are not suitable for gaming — they are designed for productivity, development, and administrative tasks.

### How do I put these services behind a reverse proxy with HTTPS?

For Webtop, use nginx or Caddy to proxy port 3000 with WebSocket support:

```nginx
server {
    listen 443 ssl;
    server_name webtop.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

For Kasm, the built-in management console handles TLS. For x2go, the SSH transport is already encrypted — no additional HTTPS setup is needed.

### What happens to my files when a Kasm session ends?

In ephemeral mode (the default), all data in the workspace container is destroyed on logout. To persist files, you can configure persistent home directories or network storage mounts in the admin console. LinuxServer Webtop and x2go persist data by default since they write to the host filesystem or Docker volumes.

## Conclusion

All three tools solve the problem of remote desktop access, but they do it in fundamentally different ways. Kasm Workspaces is the most feature-rich, with enterprise-grade user management and container isolation. LinuxServer Webtop is the simplest to deploy and perfect for personal use. x2go remains the bandwidth champion and the best choice for traditional Linux remote administration over slow links.

Your choice depends on your use case: team VDI (Kasm), personal browser desktop (Webtop), or low-bandwidth Linux administration (x2go). For many homelab users, running Webtop alongside an x2go server provides the best of both worlds — browser access when convenient, optimized client-based access when performance matters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kasm Workspaces vs LinuxServer Webtop vs x2go: Self-Hosted Browser Desktop Guide 2026",
  "description": "Compare Kasm Workspaces, LinuxServer Webtop, and x2go for self-hosted browser-based desktop access. Installation guides, Docker configs, and feature comparison for 2026.",
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
