---
title: "Self-Hosted Terminal Sharing 2026: tmate, ttyd & Wetty Compared"
date: 2026-04-15
tags: ["comparison", "guide", "self-hosted", "privacy", "devops", "collaboration"]
draft: false
description: "Complete guide to self-hosted terminal sharing and pair programming tools in 2026. Compare tmate, ttyd, and Wetty with Docker setup instructions, security hardening, and real-world use cases."
---

Every developer has been in this situation: a production server is misbehaving, a junior engineer is stuck on a configuration issue, or you need to walk a teammate through a com[plex](https://www.plex.tv/) debugging session. You could paste commands over chat, ship a screen recording, or grant SSH access and hope for the best. Or you could share your terminal in real time, with a single link.

Terminal sharing tools solve this problem elegantly. They let you broadcast a live terminal session to anyone with a URL, support multi-user collaboration where both parties can type, and work entirely in the browser — no client installation required. In 2026, three open-source tools dominate this space: **tmate**, **ttyd**, and **Wetty**. Each takes a fundamentally different approach, and each has strengths that make it the right choice for specific scenarios.

This guide compares all t[docker](https://www.docker.com/)provides complete Docker-based deployment instructions, and covers security hardening so you can run these tools in production without exposing your infrastructure.

## Why Self-Host Terminal Sharing

Commercial terminal sharing services exist, but they introduce dependencies that most teams would rather avoid.

**Data never leaves your infrastructure.** When you share a terminal session through a third-party service, every keystroke, command output, and environment variable passes through their servers. Even with encryption in transit, the service operator has access to your session data. Self-hosting means the relay runs on hardware you control, behind your own firewall, with your own access policies.

**No account required, no limits.** Commercial tools typically require registration, impose session duration limits, restrict the number of concurrent viewers, or gate collaboration features behind paid plans. Self-hosted tools have none of these restrictions. Share with one person or one hundred — the only limit is your server's capacity.

**Works behind corporate firewalls.** Many self-hosted terminal sharing tools use WebSocket connections on standard ports (80/443), which traverse corporate firewalls and proxy servers without special configuration. This makes them ideal for enterprise environments where SSH access to production machines is heavily restricted.

**Persistent sessions for training and documentation.** Some tools support recording sessions for later playback, creating a searchable archive of troubleshooting procedures, onboarding walkthroughs, and deployment runbooks. This turns ad-hoc collaboration into institutional knowledge.

**Zero-cost at any scale.** Once deployed on your own infrastructure, terminal sharing costs nothing per session, per user, or per hour. A single small VPS can serve an entire organization's collaboration needs.

## tmate: Instant Terminal Sharing via SSH Multiplexing

**tmate** is a fork of tmux designed specifically for terminal sharing. It creates a tmux session and immediately exposes it through a secure WebSocket tunnel, generating an SSH connection string and a web-based terminal URL. The design philosophy is minimalism: install one binary, run one command, share instantly.

### Architecture

tmate operates on a client-server model that mirrors tmux:

- The **tmate client** runs on your local machine, creating a tmux session
- The **tmate server** (default: public relay at `tmate.io`) maintains the tunnel and accepts incoming WebSocket connections
- Viewers connect via SSH or a web browser, joining the same shared session

The default configuration uses the public `tmate.io` relay, which means your session data passes through a third-party server. For self-hosting, you run your own tmate server instance, eliminating this dependency entirely.

### Installing and Running tmate

On Debian/Ubuntu:

```bash
sudo apt install tmate
```

On macOS with Homebrew:

```bash
brew install tmate
```

To start a shared session:

```bash
tmate
```

tmate will display connection strings:

```
ssh: ssh YnR4c3JzZkZANXQudG1hdGUuaW8
web: https://tmate.io/t/YnR4c3JzZkZANXQudG1hdGUuaW8
read-only: https://tmate.io/ro/YnR4c3JzZkZANXQudG1hdGUuaW8
```

### Self-Hosting the tmate Server

To run your own relay server with Docker:

```yaml
# docker-compose.yml — tmate server
services:
  tmate-server:
    image: ghcr.io/tmate-io/tmate:latest
    container_name: tmate-server
    restart: unless-stopped
    ports:
      - "22:22"        # SSH connections
      - "443:443"      # WebSocket connections
    volumes:
      - ./tmate.conf:/etc/tmate/tmate.conf
      - ./certs:/etc/tmate/certs:ro
    environment:
      - TMATE_HOSTNAME=tmate.yourdomain.com
```

Configuration file (`tmate.conf`):

```
# /etc/tmate/tmate.conf
set -g tmate-server-host "0.0.0.0"
set -g tmate-server-port 22
set -g tmate-websocket-host "0.0.0.0"
set -g tmate-websocket-port 443
set -g tmate-websocket-path "/"

# TLS configuration
set -g tmate-websocket-tls-key "/etc/tmate/certs/privkey.pem"
set -g tmate-websocket-tls-cert "/etc/tmate/certs/fullchain.pem"
```

Clients then connect to your server:

```bash
tmate -F -S /tmp/tmate.sock new-session
tmate set -g tmate-server "tmate.yourdomain.com"
```

### tmate Strengths and Weaknesses

tmate excels at **instant, zero-configuration sharing**. If you already use tmux, there is essentially no learning curve. The SSH-based connection works from any terminal, and the read-only URLs are perfect for sharing with stakeholders who need visibility but should not have write access. Session recording is built in through tmux's native `pipe-pane` feature.

However, tmate is fundamentally a **point-to-point** tool. It shares one terminal session at a time. There is no web-based dashboard to manage multiple sessions, no user authentication beyond SSH keys, and no integration with existing identity providers. The web terminal, while functional, is less polished than purpose-built web terminal solutions.

## ttyd: Web-Based Terminal for Any Command

**ttyd** takes a different approach entirely. Instead of sharing an existing terminal session, it runs any command-line program and exposes it through a web-based terminal interface. The result is a lightweight, single-binary terminal server that can serve anything from a full shell to specialized command-line tools.

### Architecture

ttyd is a single Go binary that:

1. Spawns a command (usually a shell like `/bin/bash`)
2. Attaches a pseudo-terminal (pty) to the process
3. Serves a web-based terminal (built on xterm.js) over HTTP/WebSocket
4. Handles terminal resizing, color output, and clipboard integration

The architecture is deliberately simple: one process, one port, no external dependencies. This makes it easy to containerize, deploy behind a reverse proxy, and scale horizontally.

### Docker Setup for ttyd

Basic deployment with shell access:

```yaml
# docker-compose.yml — ttyd
services:
  ttyd:
    image: lscr.io/linuxserver/ttyd:latest
    container_name: ttyd
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    ports:
      - "7681:7681"
    command: ["/bin/bash"]
```

For a more controlled setup with authentication:

```yaml
services:
  ttyd-auth:
    image: lscr.io/linuxserver/ttyd:latest
    container_name: ttyd-auth
    restart: unless-stopped
    ports:
      - "7682:7681"
    volumes:
      - ./config:/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: ["-c", "admin:secretpassword", "--writable", "/bin/bash"]
```

The `-c` flag sets basic HTTP authentication credentials. For production use, place ttyd behind a rev[nginx](https://nginx.org/)proxy with proper TLS and authentication:

```nginx
# /etc/nginx/sites-available/ttyd
server {
    listen 443 ssl;
    server_name terminal.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/terminal.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/terminal.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:7681;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Basic auth via nginx
        auth_basic "Terminal Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

### Running Arbitrary Commands

ttyd's flexibility comes from its ability to run **any command**, not just shells:

```bash
# Run htop as a monitored terminal
ttyd htop

# Run a Python REPL
ttyd python3

# Run a specific script with restricted environment
ttyd --writable /opt/scripts/deploy.sh

# Run with read-only mode (viewer cannot type)
ttyd -R tail -f /var/log/syslog
```

This makes ttyd useful beyond terminal sharing. You can use it to expose monitoring dashboards, database consoles, or deployment scripts through a web interface — each on its own port, with its own access controls.

### ttyd Strengths and Weaknesses

ttyd shines when you need to **expose specific commands or tools** through a web interface. Its single-binary design makes deployment trivial, and the ability to run arbitrary commands opens up creative use cases beyond simple terminal sharing. The web terminal interface is polished, with proper xterm.js rendering, clipboard support, and responsive terminal resizing.

The main limitation is that ttyd does not support **multi-user sessions** natively. Each connection spawns a separate process. To achieve shared sessions, you would need to pair ttyd with tmux or screen inside the container. There is also no built-in session recording or replay capability.

## Wetty: SSH in the Browser

**Wetty** (Web + tty) is the most infrastructure-oriented of the three tools. It acts as an SSH-to-WebSocket bridge, allowing users to connect to any SSH server through their web browser. Rather than creating new terminal sessions, Wetty provides browser-based access to existing SSH infrastructure.

### Architecture

Wetty is a Node.js application that:

1. Runs a web server serving an xterm.js-based terminal
2. Accepts SSH credentials from the user (or uses key-based authentication)
3. Establishes an SSH connection to the target host
4. Bridges the SSH session to the browser via WebSocket

This design means Wetty does not manage terminal sessions itself — it is a **pass-through** to existing SSH servers. The SSH server handles authentication, authorization, shell allocation, and session management. Wetty merely provides a browser-accessible interface.

### Docker Setup for Wetty

```yaml
# docker-compose.yml — Wetty
services:
  wetty:
    image: wettyoss/wetty:latest
    container_name: wetty
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - SSHHOST=your-ssh-server.example.com
      - SSHPORT=22
      - BASE=/
    command: ["--ssh-host", "your-ssh-server.example.com", "--ssh-port", "22"]
```

For a fully self-contained setup where Wetty runs on the same host it provides access to:

```yaml
services:
  wetty-local:
    image: wettyoss/wetty:latest
    container_name: wetty-local
    restart: unless-stopped
    network_mode: "host"
    environment:
      - SSHHOST=127.0.0.1
      - SSHPORT=22
    command: ["--ssh-host", "127.0.0.1", "--ssh-port", "22", "--base", "/terminal"]
```

### Advanced Wetty Configuration with Reverse Proxy

For production deployment, Wetty should sit behind a reverse proxy with TLS termination and authentication:

```nginx
# /etc/nginx/sites-available/wetty
server {
    listen 443 ssl http2;
    server_name ssh.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ssh.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ssh.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self' wss:;";

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;

        # Forward client certificate for SSH auth
        proxy_set_header X-SSL-Client-Cert $ssl_client_cert;
    }
}
```

### Integrating Wetty with Existing SSH Infrastructure

Wetty's primary advantage is that it works with your **existing SSH setup**. No new authentication systems, no separate user management, no additional attack surface on the target servers. Users authenticate through Wetty's web interface, and Wetty forwards those credentials to the SSH server using the same mechanisms you already have configured:

- Public key authentication
- Password authentication
- Two-factor authentication (if configured on the SSH server)
- Certificate-based authentication
- LDAP/Active Directory integration (via SSH PAM modules)

This means Wetty can provide browser-based access to hundreds of servers without any changes to the existing infrastructure. The SSH servers do not even need to know Wetty exists.

### Wetty Strengths and Weaknesses

Wetty is the best choice when you need to **provide browser-based SSH access to existing infrastructure**. It requires zero changes to your servers, integrates seamlessly with existing authentication and authorization systems, and gives users the full power of SSH through a browser tab.

However, Wetty is the least suited for **ad-hoc terminal sharing**. It does not create shareable sessions, does not support read-only viewing modes, and does not provide session recording. It is an SSH client in the browser, not a collaboration tool.

## Head-to-Head Comparison

| Feature | tmate | ttyd | Wetty |
|---------|-------|------|-------|
| **Primary use case** | Quick terminal sharing | Web terminal for any command | Browser-based SSH access |
| **Multi-user sessions** | Yes (shared tmux) | No (per-connection process) | No (per-connection SSH) |
| **Read-only mode** | Yes (separate URL) | Yes (`-R` flag) | No |
| **Session recording** | Yes (tmux `pipe-pane`) | No | No |
| **Authentication** | SSH keys | HTTP basic auth, reverse proxy | SSH (any method) |
| **Browser terminal** | Yes (xterm.js) | Yes (xterm.js) | Yes (xterm.js) |
| **SSH access** | Yes (native) | No | Yes (pass-through) |
| **Self-hosting complexity** | Medium (needs relay server) | Low (single binary) | Low (single binary) |
| **Reverse proxy support** | Yes (WebSocket) | Yes (WebSocket) | Yes (WebSocket) |
| **Docker image size** | ~15 MB | ~10 MB | ~50 MB |
| **Dependencies** | tmux, SSH | None (static binary) | Node.js |
| **Clipboard support** | Limited | Yes | Yes |
| **Terminal resizing** | Yes | Yes | Yes |
| **Access to existing SSH infra** | No | No | Yes |

## Choosing the Right Tool

The decision comes down to your specific workflow:

**Choose tmate if** you need instant terminal sharing with read-only links and session recording. It is the best fit for pair programming, debugging sessions, and training scenarios where one person drives and others observe. The tmux integration means experienced terminal users feel immediately at home.

**Choose ttyd if** you want to expose specific command-line tools through a web interface. Its ability to run any command makes it versatile: monitoring dashboards, database consoles, deployment scripts, or interactive shells. The simple deployment model makes it easy to run multiple instances, each serving a different purpose.

**Choose Wetty if** you need browser-based access to existing SSH infrastructure without modifying the target servers. It is ideal for organizations that want to provide terminal access through a web portal, integrate with existing identity providers, or give contractors limited access without distributing SSH keys.

## Security Hardening for Production Deployment

Terminal sharing tools expose powerful access to your systems. Hardening is not optional.

### TLS Everywhere

Never run terminal sharing tools over plain HTTP. All three tools transmit keystrokes and command output, which includes passwords, API keys, and sensitive file contents. Use Let's Encrypt or your organization's CA to obtain TLS certificates, and configure your reverse proxy to redirect all HTTP traffic to HTTPS.

```bash
# Obtain certificates with certbot
sudo certbot certonly --standalone -d terminal.yourdomain.com

# Auto-renewal via cron
echo "0 3 * * * certbot renew --quiet && systemctl reload nginx" | sudo tee -a /etc/crontab
```

### Network Isolation

Run terminal sharing tools in isolated Docker networks. Do not give them access to your internal network unless absolutely necessary:

```yaml
services:
  ttyd:
    image: lscr.io/linuxserver/ttyd:latest
    networks:
      - terminal-net
    # No access to host network or internal services

networks:
  terminal-net:
    driver: bridge
    internal: false  # Allow outbound internet for package installs
```

### Time-Limited Access Tokens

For tmate and ttyd, implement session timeouts to prevent stale sessions from remaining accessible:

```bash
# tmate: auto-disconnect after 30 minutes of inactivity
tmate set -g detach-on-destroy on
tmate set -g lock-after-time 1800

# ttyd: use a wrapper script with timeout
ttyd --timeout 1800 /bin/bash
```

### Audit Logging

Log all connections and commands for compliance and incident response:

```bash
# Enable command logging via bash PROMPT_COMMAND
echo 'export PROMPT_COMMAND="history -a; logger -t terminal-share \"USER=\$USER CMD=\$(history 1)\""' >> /etc/bash.bashrc

# Docker-level logging with log rotation
# Add to docker-compose.yml:
# logging:
#   driver: json-file
#   options:
#     max-size: "10m"
#     max-file: "5"
```

### Rate Limiting

Protect against brute-force authentication attempts at the reverse proxy level:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=terminal:10m rate=5r/m;

server {
    location / {
        limit_req zone=terminal burst=3 nodelay;
        # ... proxy configuration
    }
}
```

## Conclusion

Terminal sharing should not require a commercial SaaS subscription, and it certainly should not route your keystrokes through servers you do not control. In 2026, tmate, ttyd, and Wetty provide three distinct approaches to self-hosted terminal access, each optimized for different workflows.

For most development teams, running **tmate** on a small VPS covers the majority of collaboration needs: instant sharing, read-only links for stakeholders, and session recording for documentation. **ttyd** fills the gap when you need to expose specific tools through a browser. **Wetty** provides the bridge between existing SSH infrastructure and browser-based access.

All three tools are open source, free to run, and deployable with Docker in under five minutes. The only question is which one matches your workflow.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
