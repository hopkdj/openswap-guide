---
title: "Self-Hosted Web Terminal Sharing: Wetty vs Gotty vs ShellHub 2026"
date: 2026-05-05
tags: ["terminal", "web-terminal", "shell", "wetty", "gotty", "shellhub", "remote-access", "comparison", "guide"]
draft: false
description: "Compare self-hosted web terminal sharing tools — Wetty, GoTTY, and ShellHub. Access your servers from any browser with secure WebSocket-based terminal sessions and Docker deployment configs."
---

Accessing server terminals from any device without installing SSH clients is increasingly valuable for teams managing distributed infrastructure. Web-based terminal tools bridge the gap between traditional SSH and modern browser-based workflows, enabling remote access from tablets, shared workstations, or locked-down environments.

This guide compares three popular self-hosted web terminal solutions: **Wetty**, **GoTTY**, and **ShellHub**. We cover deployment with Docker Compose, authentication options, security considerations, and help you choose the right tool for your access patterns.

## Overview of Web Terminal Tools

| Feature | Wetty | GoTTY | ShellHub |
|---------|-------|-------|----------|
| Type | Web SSH client | Terminal-to-web bridge | Full device management platform |
| Stars | 4,000+ | 14,000+ | 2,000+ |
| Protocol | SSH over WebSocket | Local terminal to WebSocket | SSH with agent-based management |
| Authentication | SSH keys/passwords | None built-in (use reverse proxy) | Device-level + user auth |
| Multi-user | Yes (via SSH) | Single session | Yes (team management) |
| Session recording | No | No | Yes |
| Docker support | Yes (official image) | Yes (community) | Yes (official compose) |
| Fleet management | No | No | Yes |

## Wetty — Web-based SSH Terminal

**Wetty** (4,000+ stars) is a web-based SSH client that runs in any modern browser. It connects to your SSH server over WebSocket and provides a full terminal emulator in the browser — xterm.js powered with proper escape sequence handling.

### Key Features

- **Browser-based SSH** — No client installation needed
- **xterm.js backend** — Full terminal emulation with color support
- **Reverse proxy friendly** — Works behind Nginx, Caddy, or Traefik
- **Customizable** — Theme, font, and terminal size options

### Docker Compose

```yaml
version: "3.8"
services:
  wetty:
    image: wettyoss/wetty:latest
    ports:
      - "3000:3000"
    environment:
      - SSHHOST=your-server.example.com
      - SSHPORT=22
      - SSHAUTH=password
    command: ["wetty", "--host", "0.0.0.0", "--port", "3000"]
    restart: unless-stopped
```

For SSH key authentication:

```yaml
version: "3.8"
services:
  wetty:
    image: wettyoss/wetty:latest
    ports:
      - "3000:3000"
    volumes:
      - ./ssh-keys:/home/wetty/.ssh:ro
    command: >
      wetty --host 0.0.0.0 --port 3000
      --ssh-host your-server.example.com
      --ssh-port 22
      --ssh-key /home/wetty/.ssh/id_ed25519
```

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name terminal.example.com;

    location / {
        proxy_pass http://localhost:3000;
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

## GoTTY — Share Your Terminal as a Web Application

**GoTTY** (14,000+ stars) is a simple command-line tool that turns any CLI program into a web application. Run `gotty top` to view your system monitor in a browser, or `gotty bash` to get a full shell session.

### Key Features

- **Any CLI to web** — Works with any command-line program
- **Lightweight** — Single Go binary, no dependencies
- **Read-only mode** — Share terminal output without allowing input
- **Credential protection** — Basic auth support

### Docker Compose

```yaml
version: "3.8"
services:
  gotty:
    image: yudai/gotty:latest
    ports:
      - "8080:8080"
    command: >
      gotty -w -p 8080
      --credential "admin:secretpassword"
      --permit-write
      bash
    restart: unless-stopped
```

For a read-only session (view only, no input):

```yaml
version: "3.8"
services:
  gotty:
    image: yudai/gotty:latest
    ports:
      - "8080:8080"
    command: >
      gotty -p 8080
      --credential "viewer:readonly"
      htop
    restart: unless-stopped
```

## ShellHub — Centralized Device Access Platform

**ShellHub** (2,000+ stars) goes beyond simple terminal sharing — it is a full device management platform built for IoT, edge computing, and distributed infrastructure. Devices register with a central server, and administrators can access any device through a web interface.

### Key Features

- **Agent-based architecture** — Devices connect outbound through firewalls/NAT
- **Team management** — Role-based access control for multiple users
- **Session recording** — Full audit trail of all terminal sessions
- **Firewall traversal** — No inbound ports needed on devices
- **API-driven** — REST API for automation and integration

### Docker Compose (Full Stack)

```yaml
version: "3.8"
services:
  shellhub:
    image: shellhubio/shellhub:latest
    ports:
      - "80:80"
      - "443:443"
    environment:
      - SHELLHUB_ADMIN_USER=admin
      - SHELLHUB_ADMIN_PASSWORD=changeme
      - SHELLHUB_SECRET_KEY=your-secret-key-here
    volumes:
      - shellhub-data:/data
    restart: unless-stopped

volumes:
  shellhub-data:
```

Install the agent on remote devices:

```bash
curl -sSf "https://your-shellhub-server/install.sh" | sh
# Register device with your namespace
shellhub-agent register --namespace my-org --name server-01
```

## Comparison: Choosing the Right Web Terminal

### Use Wetty when:
- You need a browser-based SSH client for occasional server access
- Your infrastructure already has SSH configured properly
- You want a simple, drop-in web terminal solution

### Use GoTTY when:
- You want to share specific CLI tools (htop, logs, monitoring) as web apps
- You need read-only terminal sharing for demonstrations
- You want a lightweight, single-binary solution

### Use ShellHub when:
- You manage many distributed devices (IoT, edge servers, remote offices)
- You need session recording and audit trails for compliance
- Devices are behind NAT or firewalls with no inbound access
- You need team-based access control

## Why Use Web-Based Terminals?

Web terminals solve real infrastructure access challenges. They enable support teams to access servers from restricted workstations, let managers view live system metrics without SSH keys, and provide a centralized access point for distributed device fleets. Security is maintained through HTTPS, authentication, and — in ShellHub case — session recording.

For **SSH certificate management**, see our [SSH certificate guide](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/). For **remote desktop access**, check our [remote desktop comparison](../2026-05-02-tactical-rmm-vs-meshcentral-vs-openrmm-self-hosted-remote-desktop-guide/). For **terminal shell history management**, our [terminal history guide](../2026-04-29-atuin-vs-mcfly-vs-bash-history-self-hosted-terminal-shell-history-guide/) covers shell enhancements.

## FAQ

### Is Wetty secure for production use?
Wetty uses your existing SSH infrastructure for security. All connections are encrypted via SSH, and you can add an HTTPS reverse proxy for transport security. The web interface itself does not handle authentication — it relies on SSH.

### Can GoTTY handle multiple concurrent users?
GoTTY supports multiple concurrent viewers in read-only mode. For write access, only one user can interact at a time. For multi-user write access, consider Wetty with SSH or ShellHub.

### Does ShellHub work with devices behind NAT?
Yes. ShellHub agents initiate outbound connections to the central server, so no inbound ports need to be opened on devices. This makes it ideal for IoT devices, home labs, and remote offices.

### How do I add HTTPS to these web terminals?
Use a reverse proxy like Nginx, Caddy, or Traefik with Let's Encrypt certificates. The Wetty and GoTTY configs above work behind any HTTPS reverse proxy.

### Can I restrict which commands users can run?
With GoTTY, specify the command in the Docker Compose config (e.g., `htop` instead of `bash`). With Wetty, use SSH ForceCommand directive. With ShellHub, use role-based access control.

### Is session recording available in all tools?
Only ShellHub provides built-in session recording. Wetty and GoTTY do not record sessions natively — you would need to add terminal recording via script command or a separate logging solution.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Web Terminal Sharing: Wetty vs Gotty vs ShellHub 2026",
  "description": "Compare self-hosted web terminal sharing tools — Wetty, GoTTY, and ShellHub. Access your servers from any browser with secure WebSocket-based terminal sessions and Docker deployment configs.",
  "datePublished": "2026-05-05",
  "dateModified": "2026-05-05",
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
