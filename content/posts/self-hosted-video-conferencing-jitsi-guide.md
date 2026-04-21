---
title: "Complete Guide to Self-Hosted Jitsi Meet 2026"
date: 2026-04-12
tags: ["comparison", "guide", "self-hosted", "privacy"]
draft: false
description: "Complete guide to deploying Jitsi Meet for private, self-hosted video conferencing in 2026. Covers Docker setup, security hardening, scaling, and alternatives."
---

Video conferencing has become an essential part of modern communication. Yet most people still rely on proprietary platforms that collect meeting metadata, track participant behavior, and impose artificial limits on call duration and participant counts. Self-hosting your own video conferencing infrastructure puts you back in control.

[Jitsi Meet](https://jitsi.org/) is the leading open-source video conferencing platform. It supports unlimited meeting duration, end-to-end encryption, and scales from a home lab to enterprise deployments. This guide walks you through deploying, securing, and scaling Jitsi Meet on your own hardware in 2026.

## Why Self-Host Your Video Conferencing

The case for self-hosting video calls is stronger than ever:

- **Privacy**: Meeting metadata — who called whom, when, and for how long — stays on your server. No third-party analytics or telemetry.
- **No artificial limits**: Free tiers of commercial services cap meetings at 40–60 minutes or limit participants. Self-hosted Jitsi has no such restrictions.
- **Full customization**: Brand the interface, integrate with your existing authentication (LDAP, OAuth, SAML), and enable or disable features as needed.
- **Compliance**: For organizations subject to GDPR, HIPAA, or other regulations, keeping call data on-premises simplifies audit trails and data retention policies.
- **Cost at scale**: Commercial video conferencing platforms charge per-host per month. A single self-hosted server can handle dozens of concurrent meetings for the cost of a few monthly subscriptions.

## Architecture Overview

Before deploying, it helps to understand what makes up a Jitsi installation. The platform is not a single application but a collection of coordinated services:

| Component | Purpose |
|-----------|---------|
| **Jitsi Meet (Web UI)** | React-based web interface, served via [nginx](https://nginx.org/) |
| **Jitsi Videobridge (JVB)** | SFU (Selective Forwarding Unit) — routes video streams between participants |
| **Jicofo** | Focus component — manages conference rooms, allocates bridges, handles SIP gateway |
| **Prosody** | XMPP server — the messaging backbone connecting all components |
| **Jigasi** | SIP gateway — bridges Jitsi meetings with traditional phone networks |
| **Jibri** | Recording and streaming service — captures meetings to file or streams to YouTube |

The official Jitsi [docker](https://www.docker.com/) compose setup packages these components together, making deployment straightforward. For small to medium deployments (up to ~50 concurrent participants), a single server is sufficient. Larger deployments require horizontal scaling with multiple JVB instances.

## Quick Start: Deploy Jitsi Meet with Docker

The fastest way to get a working Jitsi Meet instance is using the official Docker Compose repository. This method handles all inter-service networking and configuration automatically.

### Prerequisites

- A server with at least **4 vCPUs, 8 GB RAM, and 50 GB storage**
- A public domain name pointing to your server's IP
- Docker and Docker Compose installed
- Ports **80, 443, 10000/UDP, and 4443/TCP** open

### Step 1: Clone the Repository

```bash
git clone https://github.com/jitsi/docker-jitsi-meet.git
cd docker-jitsi-meet
```

### Step 2: Configure the Environment

Copy the example environment file and generate secure secrets:

```bash
cp env.example .env

# Generate all required secrets in one command
./gen-passwords.sh
```

The `gen-passwords.sh` script creates random passwords for Jicofo, JVB, Prosody authentication, and Jibri. Never skip this step — using default or empty passwords exposes your deployment to abuse.

Edit the `.env` file to set your domain and enable key features:

```bash
# Domain configuration
PUBLIC_URL="meet.yourdomain.com"

# Enable authentication to control who can create rooms
ENABLE_AUTH=1
AUTH_TYPE=internal

# Enable recording (requires Jibri)
# ENABLE_RECORDING=1

# Enable transcription (experimental)
# ENABLE_TRANSCRIPTIONS=1

# Enable guest access so anyone can join created rooms
ENABLE_GUESTS=1

# Set your timezone
TZ=UTC
```

### Step 3: Create Required Directories

Jitsi Docker requires persistent directories for configuration and recordings:

```bash
mkdir -p ~/.jitsi-meet-cfg/{web,transcripts,prosody/config,prosody/prosody-plugins-custom,jicofo,jvb,jigasi,jibri,log}
```

### Step 4: Launch the Stack

```bash
docker compose up -d
```

The first pull will take a few minutes. Once running, verify the containers:

```bash
docker compose ps
```

You should see `web`, `jicofo`, `jvb`, and `prosody` all in a `running` state.

### Step 5: Configure DNS and HTTPS

Point your domain's A record to your server's public IP. Then, in the `.env` file, set:

```bash
ENABLE_LETSENCRYPT=1
LETSENCRYPT_DOMAIN=meet.yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

Restart the stack to apply:

```bash
docker compose down && docker compose up -d
```

The nginx container will automatically obtain and renew a Let's Encrypt certificate.

## Authentication and Access Control

A bare Jitsi installation allows anyone to create meetings. For a production deployment, you need authentication.

### Internal Authentication (Built-in)

The simplest approach uses Prosody's internal user database:

```bash
# In .env file
ENABLE_AUTH=1
AUTH_TYPE=internal
ENABLE_GUESTS=1
```

Create user accounts via the Prosody container:

```bash
docker compose exec prosody prosodyctl --config /config/prosody.cfg.lua register youruser meet.jitsi yourpassword
```

With `ENABLE_GUESTS=1`, authenticated users can create rooms, while unauthenticated guests can join them. This is the recommended setup for most teams.

### LDAP Authentication

For organizations with existing directory infrastructure, Jitsi supports LDAP:

```bash
ENABLE_AUTH=1
AUTH_TYPE=ldap
LDAP_URL=ldap://ldap.yourdomain.com:389
LDAP_BASE=DC=example,DC=com
LDAP_BINDDN=CN=admin,DC=example,DC=com
LDAP_BINDPW=adminpassword
LDAP_FILTER=(memberOf=CN=jitsi-users,OU=Groups,DC=example,DC=com)
LDAP_AUTH_METHOD=bind
LDAP_VERSION=3
LDAP_USE_TLS=1
LDAP_START_TLS=1
LDAP_TLS_CIPHERS=SECURE256
LDAP_TLS_CHECK_PEER=1
```

### JWT/Token Authentication

For programmatic access and integration with existing identity providers:

```bash
ENABLE_AUTH=1
AUTH_TYPE=jwt
JWT_APP_ID=your-app-id
JWT_APP_SECRET=your-app-secret
JWT_ACCEPTED_ISSUERS=your-app-id
JWT_ACCEPTED_AUDIENCES=your-app-id
JWT_TOKEN_AUTH_MODULE=token_verification
```

## Security Hardening

A self-hosted service is only as secure as its configuration. Apply these hardening measures:

### 1. Enable Room Passwords

Require a password for every meeting by editing the Prosody configuration:

```lua
-- In ~/.jitsi-meet-cfg/prosody/config/conf.d/jitsi-meet.cfg.lua
Component "conference.meet.jitsi" "muc"
    modules_enabled = {
        "muc_password_required";
    }
    muc_room_locking = true
    muc_room_default_public_jids = true
```

### 2. Configure Firewall Rules

Only expose the ports Jitsi actually needs:

```bash
ufw allow 80/tcp    # HTTP (for Let's Encrypt)
ufw allow 443/tcp   # HTTPS (web interface)
ufw allow 10000/udp # JVB media traffic
ufw allow 4443/tcp  # JVB fallback (TCP)
ufw enable
```

### 3. Set Up Fail2Ban

Protect against brute-force attacks on the authentication system:

```bash
# Install fail2ban on the host
apt install fail2ban -y

# Create jail for Jitsi Prosody
cat > /etc/fail2ban/jail.local << 'EOF'
[jitsi-prosody]
enabled = true
filter = jitsi-prosody
logpath = /var/log/jitsi/prosody.log
maxretry = 5
bantime = 3600
findtime = 600
EOF
```

### 4. Disable Unused Features

Minimize your attack surface by disabling services you don't need:

```bash
# In .env, ensure these are NOT set:
# ENABLE_TRANSCRIPTIONS=1   # Requires external API
# ENABLE_RECORDING=1         # Requires Jibri, additional resources
# ENABLE_XMPP_WEBSOCKET=0    # Disable if not needed
# ENABLE_SCTP=0              # Disable data channels if unused
```

### 5. Secure the Host OS

```bash
# Keep the system updated
apt update && apt upgrade -y

# Install unattended upgrades
apt install unattended-upgrades -y
dpkg-reconfigure -plow unattended-upgrades

# Disable root SSH login
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
```

## Scaling Beyond a Single Server

The default Docker setup works well for ~30–50 concurrent participants. Beyond that, you need horizontal scaling.

### Multiple Videobridges

The Videobridge (JVB) is the component that benefits most from horizontal scaling. You can run multiple JVB instances behind a single Jicofo:

```yaml
# docker-compose.override.yml
services:
  jvb2:
    <<: *jvb
    environment:
      - JVB_PORT=10001
      - JVB_TCP_PORT=4444
      - JVB_WS_SERVER_ID=jvb2.meet.jitsi
      - JVB_WS_DOMAIN=meet.jitsi
    ports:
      - '10001:10001/udp'
      - '4444:4444/tcp'
```

Jicofo automatically load-balances conferences across available bridges.

### Using an External TURN Server

For participants behind strict NATs, a TURN server relays media traffic. Coturn is the standard choice:

```bash
# Install coturn
apt install coturn -y

# Configure in /etc/turnserver.conf
listening-port=3478
tls-listening-port=5349
external-ip=YOUR_PUBLIC_IP
realm=meet.yourdomain.com
server-name=meet.yourdomain.com
lt-cred-mech
user=jitsi:your-turn-secret

# Start the service
systemctl enable coturn
systemctl start coturn
```

Then add to your Jitsi `.env`:

```bash
ENABLE_TURNS=1
TURNS_HOST=meet.yourdomain.com
TURNS_PORT=5349
TURN_CREDENTIALS=jitsi:your-turn-secret
```

## Monitoring and Maintenance

### Health Checks

Monitor your deployment with built-in Jitsi health endpoints:

```bash
# Check JVB health
curl http://localhost:8080/about/health

# Check Jicofo health
curl http://localhost:8888/about/health

# Check web interface
curl -o /dev/null -s -w "%{http_code}" https://meet.yourdomain.com
```

### Automated Backups

Back up your configuration and user data regularly:

```bash
#!/bin/bash
# backup-jitsi.sh
BACKUP_DIR="/opt/backups/jitsi/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r ~/.jitsi-meet-cfg/prosody/config "$BACKUP_DIR/prosody-config"
cp -r ~/.jitsi-meet-cfg/jicofo "$BACKUP_DIR/jicofo"
cp .env "$BACKUP_DIR/env-backup"

# Backup user accounts (Prosody internal auth)
docker compose exec prosody prosodyctl dump-users >> "$BACKUP_DIR/users.txt"

# Compress
tar czf "$BACKUP_DIR.tar.gz" -C /opt/backups/jitsi "$(date +%Y%m%d)"
rm -rf "$BACKUP_DIR"

# Keep last 30 days
find /opt/backups/jitsi -name "*.tar.gz" -mtime +30 -delete
```

Add this to cron for daily backups:

```bash
0 2 * * * /opt/scripts/backup-jitsi.sh
```

### Updating Jitsi

The Docker compose approach makes updates straightforward:

```bash
cd docker-jitsi-meet
git pull
docker compose pull
docker compose up -d
```

Always check the [release notes](https://github.com/jitsi/docker-jitsi-meet/releases) before updating, as breaking changes occasionally require manual migration steps.

## Jitsi Meet vs. Alternatives

While Jitsi is the most mature option, several other self-hosted video conferencing solutions exist:

| Feature | Jitsi Meet | BigBlueButton | LiveKit |
|---------|------------|---------------|---------|
| **License** | Apache 2.0 | LGPL 3.0 | AGPL 3.0 |
| **Protocol** | WebRTC (SFU) | WebRTC (SFU) | WebRTC (SFU) |
| **Setup Com[plex](https://www.plex.tv/)ity** | Moderate | High | Moderate |
| **Max Participants** | 100+ (with scaling) | 250+ | 1000+ |
| **Recording** | Via Jibri | Built-in | Via Egress |
| **Whiteboard** | Via Etherpad | Built-in | Via LiveKit Agents |
| **Screen Sharing** | Yes | Yes | Yes |
| **Mobile Apps** | Official iOS/Android | Official iOS/Android | SDK available |
| **API/SDK** | IFrame API | API + GraphQL | Go, JS, Swift, Kotlin SDKs |
| **Best For** | Quick meetings, general use | Education, webinars | Developer-heavy apps |

**Choose Jitsi Meet** if you need a drop-in replacement for Zoom/Google Meet that's quick to deploy and works well for general-purpose meetings.

**Choose BigBlueButton** if your primary use case is education — it includes built-in polling, breakout rooms, whiteboard, and shared notes.

**Choose LiveKit** if you're building a custom application and need SDK-level control over the WebRTC stack.

## Troubleshooting Common Issues

### Participants Can't See/ Hear Each Other

This is almost always a network/firewall issue. Port 10000/UDP must be open:

```bash
# Verify UDP port is reachable
nc -vuz your.server.ip 10000

# Check JVB is listening
ss -ulnp | grep 10000
```

If UDP is blocked by the network, enable TCP fallback:

```bash
# In .env
ENABLE_TCP_HARVESTER=1
JVB_TCP_HARVESTER_PORT=4443
```

### High CPU Usage

Video encoding is CPU-intensive. If your server struggles:

```bash
# Limit video quality in .env
DEPLOYMENTINFO_ENVIRONMENT=production
VIDEOQUALITY_PREFERRED_CODEC=VP8

# Set max resolution
VIDEOQUALITY_ENFORCE_PREFERRED_CODEC=true
```

Consider upgrading to a server with more vCPUs or enabling hardware encoding if your CPU supports it.

### Recording Fails with Jibri

Jibri requires Chrome and a virtual display. Common fixes:

```bash
# Check Jibri logs
docker compose logs jibri

# Verify Chrome is installed in the container
docker compose exec jibri google-chrome --version

# Ensure the /dev/shm size is sufficient (add to docker-compose.yml)
# shm_size: '2gb'
```

## Final Thoughts

Self-hosting Jitsi Meet in 2026 is more practical than ever. The Docker compose setup handles the complexity of coordinating multiple services, and a modest VPS can comfortably handle small team meetings. The key advantages — no meeting time limits, full data ownership, and deep customization — make it a compelling alternative to commercial platforms.

For most users, the standard Docker deployment with internal authentication, Let's Encrypt TLS, and a properly configured firewall provides everything needed for secure, private video conferencing. Start small, monitor your resource usage, and scale horizontally as your participant count grows.

Your communications infrastructure is worth owning. With a few Docker commands and a domain name, you can run a professional-grade video conferencing platform that answers to no one but you.

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
