---
title: "ShellHub vs Sshwifty vs Wetty: Self-Hosted Web-Based SSH Access Guide 2026"
date: 2026-04-29
tags: ["comparison", "guide", "self-hosted", "ssh", "remote-access", "terminal"]
draft: false
description: "Compare ShellHub, Sshwifty, and Wetty for self-hosted web-based SSH access. Learn how to deploy each tool with Docker, configure authentication, and choose the right solution for your infrastructure."
---

Managing Linux servers remotely is a daily reality for system administrators and DevOps engineers. While traditional SSH clients work well on your local machine, there are scenarios where **web-based SSH access** becomes essential: emergency troubleshooting from any device, providing terminal access to team members without distributing SSH keys, or building a centralized access gateway for distributed infrastructure.

Three open-source tools stand out in this space: **[ShellHub](https://github.com/shellhub-io/shellhub)**, **[Sshwifty](https://github.com/nirui/sshwifty)**, and **[Wetty](https://github.com/butlerx/wetty)**. Each takes a fundamentally different approach to delivering SSH over the web. This guide compares them in detail and provides ready-to-use Docker configurations for each.

## Why Self-Host Web-Based SSH Access?

Running your own web-based SSH solution gives you several advantages over cloud-hosted alternatives:

- **Full data sovereignty** — no third party sees your terminal sessions or credentials
- **No subscription costs** — all three tools are open-source and free to self-host
- **Custom authentication** — integrate with your existing identity providers
- **Audit and compliance** — keep session logs on your own infrastructure
- **Network isolation** — access devices behind NAT or firewalls without opening ports

Whether you manage a handful of VPS instances or hundreds of edge devices, a self-hosted web SSH gateway simplifies remote access while maintaining security control.

## ShellHub: Centralized SSH Gateway for Edge and Cloud

[ShellHub](https://github.com/shellhub-io/shellhub) is the most feature-rich option, designed as a centralized SSH gateway that connects to your servers through outbound connections. Devices behind your infrastructure initiate connections *to* the ShellHub server, eliminating the need to open inbound SSH ports on each device.

### Key Features

- **Agent-based architecture** — a lightweight agent runs on each managed device
- **Multi-tenant support** — separate namespaces for different teams or projects
- **Session recording** — full terminal session playback for auditing
- **Firewall rules** — restrict SSH access by IP, user, or device
- **Public key management** — centralized SSH key distribution
- **Web terminal** — full-featured browser-based terminal with xterm.js
- **API-first** — RESTful API for automation and integration
- **Community edition** — free self-hosted version with core features

### Architecture

ShellHub uses a multi-service architecture with MongoDB for device/session metadata, Redis for caching, and an SSH gateway that multiplexes connections. The agent on each target device establishes an outbound WebSocket connection to the gateway, meaning devices can sit behind NAT or firewalls with zero inbound port configuration.

### Docker Compose Deployment

ShellHub's production deployment requires several services. Here is a simplified deployment using the official compose file:

```yaml
name: shellhub

services:
  ssh:
    image: shellhubio/ssh:latest
    restart: unless-stopped
    environment:
      - SHELLHUB_CLOUD=false
      - SHELLHUB_ENTERPRISE=false
      - SHELLHUB_LOG_LEVEL=info
      - PRIVATE_KEY=/run/secrets/ssh_private_key
    ports:
      - "2222:2222"
    depends_on:
      - mongo
      - redis
    secrets:
      - ssh_private_key

  mongo:
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

secrets:
  ssh_private_key:
    file: ./ssh_private_key

volumes:
  mongo_data:
  redis_data:
```

To deploy:

```bash
# Generate an SSH key for the gateway
ssh-keygen -t rsa -b 4096 -f ./ssh_private_key -N "" -q

# Start all services
docker compose up -d
```

Then install the agent on each target device:

```bash
docker run -d \
  --name shellhub-agent \
  --restart unless-stopped \
  --network host \
  --pid host \
  -v /var/run:/var/run \
  -v /:/host \
  shellhubio/agent:latest \
  -server http://YOUR_SHELLHUB_SERVER:80
```

### Best Use Cases

ShellHub excels when you need to manage a **large fleet of distributed devices** — IoT gateways, edge servers, or branch office machines that sit behind NAT. The agent-based model means you never need to touch firewall rules on individual devices, and the centralized dashboard gives you a single pane of glass for all your infrastructure.

## Sshwifty: Lightweight Web SSH and Telnet Client

[Sshwifty](https://github.com/nirui/sshwifty) takes a minimalist approach: it is a web-based SSH and Telnet client that runs as a single Go binary (or Docker container). Unlike ShellHub, it does not use agents — it acts as a proxy that connects directly to your SSH servers from the browser.

### Key Features

- **Single binary deployment** — no database, no message queue, no dependencies
- **SSH and Telnet support** — handles both protocols natively
- **Shared access passwords** — set a shared key to restrict who can connect
- **Preset configurations** — save connection profiles for quick access
- **WebSocket-based** — low-latency terminal with xterm.js rendering
- **Zero agent requirement** — connects to any standard SSH server
- **Docker image** — available as `niruix/sshwifty:latest`

### Docker Compose Deployment

Sshwifty is remarkably simple to deploy. Here is the production-ready configuration:

```yaml
version: "3.9"

services:
  sshwifty:
    image: niruix/sshwifty:latest
    container_name: sshwifty
    user: "nobody:nobody"
    restart: unless-stopped
    ports:
      - "127.0.0.1:8182:8182/tcp"
    environment:
      - SSHWIFTY_SHAREDKEY=your-strong-password-here
    volumes:
      - ./sshwifty.conf.json:/sshwifty.conf.json:ro
```

Create a preset configuration file at `sshwifty.conf.json` for saved connections:

```json
{
  "PresetServers": [
    {
      "Title": "Production Web Server",
      "Protocol": "SSH",
      "Host": "10.0.1.10",
      "Port": 22,
      "Meta": {
        "AuthMethod": "Password"
      }
    },
    {
      "Title": "Database Server",
      "Protocol": "SSH",
      "Host": "10.0.1.20",
      "Port": 2222,
      "Meta": {
        "AuthMethod": "Password"
      }
    }
  ]
}
```

Deploy and access:

```bash
docker compose up -d
# Access at http://localhost:8182
```

For production, place a reverse proxy in front with TLS termination. Sshwifty listens on `127.0.0.1:8182` by default, which is the recommended binding when using a reverse proxy.

### Best Use Cases

Sshwifty is ideal for **small to medium teams** that need quick web-based SSH access to a known set of servers. The single-container deployment means you can spin it up in minutes, and the preset system lets administrators pre-configure connection profiles so users don't need to know server IP addresses. It is also useful for **temporary access grants** — share the URL and password, and users get a full terminal without installing anything.

## Wetty: Terminal in the Browser Over HTTP/HTTPS

[Wetty](https://github.com/butlerx/wetty) (Web + TTY) is one of the oldest projects in this space. It runs a local SSH connection on the server and exposes it through a web terminal via xterm.js. Unlike the other two options, Wetty connects to SSH servers from the Wetty server itself — users authenticate to Wetty, and Wetty authenticates to the target SSH server.

### Key Features

- **Mature project** — over 5,200 GitHub stars, active since 2013
- **Node.js-based** — runs on any platform with Node.js 18+
- **SSH agent forwarding** — supports key-based authentication to target servers
- **Custom title and branding** — configurable window title
- **SSL/TLS support** — built-in HTTPS with custom certificate paths
- **npm global install** — `npm -g i wetty` for bare-metal deployment
- **Docker container** — `wettyoss/wetty` image available

### Docker Compose Deployment

Wetty's docker-compose sets up both the Wetty service and an nginx reverse proxy:

```yaml
version: '3.5'

services:
  wetty:
    image: wettyoss/wetty
    restart: unless-stopped
    ports:
      - '3000:3000'
    environment:
      SSHHOST: 'localhost'
      SSHPORT: 22
      SSHAUTH: 'publickey,password'
      TITLE: 'My Server Terminal'

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - wetty
```

Create the nginx configuration at `nginx.conf`:

```nginx
server {
    listen 80;
    server_name wetty.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name wetty.example.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    location / {
        proxy_pass http://wetty:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

Start the stack:

```bash
mkdir -p ssl
# Place your SSL certificates in ssl/
docker compose up -d
# Access at https://wetty.example.com
```

### Best Use Cases

Wetty shines when you need a **quick terminal on a single server** — think of it as a web-based `screen` or `tmux` session that anyone with browser access can join. It is commonly used in homelab setups, educational environments, and scenarios where you want to give non-technical users terminal access without teaching them SSH. The mature ecosystem means it integrates well with existing nginx or Apache reverse proxy configurations.

## Comparison Table

| Feature | ShellHub | Sshwifty | Wetty |
|---|---|---|---|
| **Architecture** | Agent-based gateway | Web proxy client | Server-side SSH bridge |
| **GitHub Stars** | 1,997 | 3,072 | 5,254 |
| **Primary Language** | TypeScript | Go / JavaScript | TypeScript |
| **Last Updated** | April 2026 | March 2026 | April 2026 |
| **Database Required** | MongoDB + Redis | None | None |
| **Agent on Target** | Required | Not needed | Not needed |
| **Telnet Support** | No | Yes | No |
| **Session Recording** | Yes | No | No |
| **Multi-tenant** | Yes | No | No |
| **NAT Traversal** | Built-in (outbound) | Manual port config | Manual port config |
| **Auth Methods** | SSH keys, OAuth | Password, presets | SSH keys, password |
| **Docker Image** | `shellhubio/ssh` | `niruix/sshwifty` | `wettyoss/wetty` |
| **Reverse Proxy** | Built-in | Required (recommended) | Required (recommended) |
| **Best For** | Large device fleets | Quick team access | Single server terminal |

## Choosing the Right Tool

The decision between these three tools comes down to your infrastructure scale and access patterns:

**Choose ShellHub if:**
- You manage 10+ servers or edge devices
- Devices are behind NAT or strict firewalls
- You need session recording and audit trails
- Multiple teams need isolated access namespaces

**Choose Sshwifty if:**
- You need a lightweight, single-container solution
- You want pre-configured connection presets for your team
- You need both SSH and Telnet access
- Quick deployment is a priority over advanced features

**Choose Wetty if:**
- You want a simple web terminal for a single server
- You need mature, battle-tested software
- You already run nginx and want tight integration
- You want to give browser-only users terminal access

## Security Considerations

Regardless of which tool you choose, follow these security best practices:

1. **Always use TLS** — never expose web-based SSH over plain HTTP in production
2. **Restrict network binding** — bind to `127.0.0.1` and use a reverse proxy for external access
3. **Enable rate limiting** — protect against brute-force login attempts on the web interface
4. **Use SSH keys over passwords** — configure public key authentication wherever possible
5. **Keep containers updated** — monitor GitHub releases and update images regularly
6. **Restrict access with firewall rules** — use tools like CrowdSec or Fail2ban to block repeated failed attempts
7. **Audit session logs** — enable logging and review access patterns periodically

For additional SSH hardening, consider our guides on [SSH bastion and jump server configuration](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) and [SSH certificate management](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) for advanced authentication setups.

## FAQ

### Is web-based SSH access secure?

Yes, when configured properly. All three tools use standard SSH encryption for the connection between the web server and the target machine. The web interface itself should always be served over HTTPS (TLS) to encrypt browser-to-server communication. The main risk is the web authentication layer — use strong passwords, SSH keys, or OAuth to protect access.

### Can ShellHub access devices behind NAT without port forwarding?

Yes, this is ShellHub's primary advantage. The agent on each target device initiates an outbound WebSocket connection to the ShellHub server. Since outbound connections are typically allowed through firewalls, no inbound port forwarding or NAT configuration is needed on the target devices.

### Does Sshwifty support SSH key authentication?

Sshwifty supports password-based authentication to target SSH servers out of the box. For key-based auth, you can mount SSH private keys into the container and configure them in the preset JSON file. The shared key (`SSHWIFTY_SHAREDKEY`) protects the web interface itself, while individual SSH credentials are entered per connection or stored in presets.

### Which tool is best for a small homelab with 3-5 servers?

Sshwifty is likely the best fit for a small homelab. It deploys as a single Docker container, requires no database, and lets you pre-configure all your server connections in a JSON file. Wetty is also a good option if you want something even simpler and don't mind a slightly less polished interface.

### Can I use these tools alongside traditional SSH clients?

Absolutely. These tools provide a web-based *alternative* access method — they do not replace or interfere with standard SSH. Your existing SSH configurations, keys, and workflows continue to work normally. The web interface is just an additional way to reach your servers.

### Does Wetty support multiple users simultaneously?

Yes, Wetty handles multiple concurrent connections. Each browser tab creates an independent SSH session to the target server. However, Wetty does not have built-in user management — all users connect through the same Wetty instance and authenticate directly to the SSH server with their own credentials.

### How do I add TLS/HTTPS to Sshwifty?

Sshwifty does not handle TLS natively. The recommended approach is to place a reverse proxy like nginx, Caddy, or Traefik in front of it. Bind Sshwifty to `127.0.0.1:8182` and configure your reverse proxy to handle TLS termination and forward traffic to the local port. For a complete reverse proxy comparison, see our [nginx vs Caddy vs Traefik guide](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "ShellHub vs Sshwifty vs Wetty: Self-Hosted Web-Based SSH Access Guide 2026",
  "description": "Compare ShellHub, Sshwifty, and Wetty for self-hosted web-based SSH access. Learn how to deploy each tool with Docker, configure authentication, and choose the right solution for your infrastructure.",
  "datePublished": "2026-04-29",
  "dateModified": "2026-04-29",
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
