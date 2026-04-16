---
title: "Self-Hosted SSH Bastion Host & Jump Server Guide: Teleport, Guacamole, Trisail 2026"
date: 2026-04-16
tags: ["comparison", "guide", "self-hosted", "security", "ssh", "infrastructure"]
draft: false
description: "Complete guide to self-hosted SSH bastion hosts and jump servers. Compare Teleport, Apache Guacamole, and Trisail with Docker Compose setups, RBAC configuration, and production best practices for 2026."
---

## Why Self-Host an SSH Bastion Host?

Every homelab, small team, and distributed infrastructure faces the same problem: you have dozens of servers, VMs, and containers spread across clouds and local networks, and you need secure, audited access to all of them. Opening SSH port 22 on every machine is a security nightmare. Managing individual SSH keys across a growing fleet becomes unsustainable. And when someone leaves the team, you're manually revoking keys on every server.

A **bastion host** (also called a jump server or SSH gateway) solves all of this. It's a single hardened entry point that sits between you and your infrastructure. All SSH connections flow through it, giving you:

- **Centralized access control** — one place to manage who can reach what
- **Session recording and auditing** — full transcripts of every command executed
- **No direct SSH exposure** — your backend servers never face the public internet
- **Role-based permissions** — developers get different access than operators
- **Single sign-on** — authenticate once, access everything

Commercial solutions like AWS Systems Manager Session Manager and ScaleFT exist, but they lock you into a vendor, charge per-node licensing fees, and send your session metadata to third-party servers. Self-hosted alternatives give you the same capabilities with full data sovereignty and zero per-node costs.

---

## The Contenders: Teleport vs Guacamole vs Trisail

Three open-source projects dominate the self-hosted bastion space, each with a different philosophy.

### Teleport (Gravitational)

Teleport is the most comprehensive option. It replaces SSH entirely with its own protocol built on top of SSH and TLS, adding identity-aware access, session recording, application proxying, Kubernetes access, and database access — all through a single binary. It supports GitHub, OIDC, SAML, and local authentication.

**Best for**: Teams that want a unified access plane covering SSH, Kubernetes, databases, and web apps with strong audit requirements.

### Apache Guacamole

Guacamole is a clientless remote desktop gateway. It supports SSH, RDP, VNC, and Kubernetes through a web browser — no client software needed. You connect to Guacamole's web interface, select a connection, and get a terminal or desktop in your browser. It's simpler than Teleport but covers more protocols.

**Best for**: Environments that need mixed SSH and remote desktop access through a single web portal, especially for less technical users.

### Trisail (formerly ShellHub)

Trisail is a lightweight SSH gateway designed specifically for edge and IoT deployments. It uses a reverse-SSH model where agents on target machines initiate outbound connections to the gateway, meaning no firewall changes or port forwarding is required on the target side. It's the simplest to deploy in network-restricted environments.

**Best for**: Homelab users and IoT/edge deployments where target machines are behind NAT or restrictive firewalls.

---

## Feature Comparison

| Feature | Teleport | Apache Guacamole | Trisail |
|---|---|---|---|
| **SSH access** | Yes (native protocol) | Yes (via web terminal) | Yes (reverse SSH) |
| **RDP / VNC** | No | Yes | No |
| **Kubernetes access** | Yes (kubectl proxy) | Yes (web console) | No |
| **Database access** | Yes (PostgreSQL, MySQL, MongoDB) | No | No |
| **Application proxy** | Yes (HTTP/HTTPS) | No | No |
| **Authentication** | OIDC, SAML, GitHub, local | CAS, LDAP, SAML, Duo, TOTP | GitHub, SAML, local |
| **RBAC** | Full policy engine (YAML) | Connection-level permissions | Organization-based |
| **Session recording** | Yes (video + text) | Yes (video) | Yes (text only) |
| **Audit log** | Yes (structured events) | Yes (connection logs) | Yes (connection logs) |
| **Hardware token (FIDO2)** | Yes | Via SSO provider | No |
| **Access requests** | Yes (approval workflow) | No | No |
| **Agent model** | Teleport daemon on each node | Guacamole daemon (guacd) | Trisail agent on each node |
| **Firewall requirements** | Open proxy port on Teleport server | Open Guacamole web port | Only agents need outbound |
| **Resource usage** | Medium (~256MB RAM) | Low (~128MB RAM) | Low (~64MB RAM) |
| **License** | OSS (AGPL-3.0) + Enterprise | Apache 2.0 | Apache 2.0 |
| **Docker support** | Official images | Official images | Official images |

---

## Deployment Guide

### 1. Deploying Teleport

Teleport's open-source edition (Community Edition) covers SSH access, session recording, RBAC, and OIDC authentication — everything most homelabs and small teams need.

#### Docker Compose Setup

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  teleport:
    image: public.ecr.aws/gravitational/teleport-distroless:16
    container_name: teleport
    restart: unless-stopped
    ports:
      - "3023:3023"   # SSH proxy
      - "3024:3024"   # Auth server (node heartbeats)
      - "3025:3025"   # Reverse tunnel
      - "443:443"     # Web UI
      - "3080:3080"   # HTTP (redirects to HTTPS)
    volumes:
      - ./config:/etc/teleport
      - ./data:/var/lib/teleport
    environment:
      - TELEPORT_AUTH_SERVER=localhost:3025
    command: ["teleport", "start", "-c", "/etc/teleport/teleport.yaml"]
    networks:
      - teleport-net

networks:
  teleport-net:
    driver: bridge
```

#### Teleport Configuration

Create `config/teleport.yaml`:

```yaml
version: v3
teleport:
  nodename: teleport-gateway
  data_dir: /var/lib/teleport
  log:
    output: stderr
    severity: INFO
    format:
      output: text

auth_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3025
  cluster_name: teleport.example.com
  authentication:
    type: local
    second_factor: on
    webauthn:
      rp_id: teleport.example.com
  # Default role for all users
  roles:
    - name: admin
      options:
        cert_format: standard
        max_session_ttl: 8h
        forward_agent: true
      allow:
        logins: ["root", "ubuntu", "deploy"]
        node_labels:
          "*": "*"

proxy_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3023
  web_listen_addr: 0.0.0.0:443
  public_addr: teleport.example.com:443
  ssh_public_addr: teleport.example.com:3023
  kube_listen_addr: 0.0.0.0:3026
  tunnel_listen_addr: 0.0.0.0:3024

ssh_service:
  enabled: "no"  # Teleport itself is the proxy, not a target node
```

#### Starting Teleport and Creating the First User

```bash
docker compose up -d

# Create the first admin user
docker exec teleport tctl users add admin --roles=editor,access \
  --logins=root,ubuntu,deploy

# This prints a URL — open it in your browser to complete setup
```

#### Connecting a Target Node

On each server you want to manage, install the Teleport agent and join it to the cluster:

```bash
# On the target node
docker run --rm --entrypoint=tctl \
  -v $(pwd)/config:/etc/teleport \
  public.ecr.aws/gravitational/teleport-distroless:16 \
  tokens add --type=node

# Copy the generated join token, then on the target:
docker run -d --name teleport-agent \
  --network host \
  --restart unless-stopped \
  -v /var/lib/teleport:/var/lib/teleport \
  public.ecr.aws/gravitational/teleport-distroless:16 \
  teleport start \
    --roles=node \
    --auth-server=teleport.example.com:3025 \
    --token=<JOIN_TOKEN> \
    --labels=env=production,team=backend
```

#### Creating RBAC Rules

Teleport's role engine is its standout feature. Create `role-dev.yaml`:

```yaml
kind: role
version: v7
metadata:
  name: developer
spec:
  allow:
    logins: ["deploy", "app"]
    node_labels:
      "env": "staging"
      "team": ["backend", "frontend"]
    rules:
      - resources: ["session"]
        verbs: ["list", "read"]
  deny:
    node_labels:
      "env": "production"
    # Developers cannot access production nodes
```

Apply it:

```bash
tctl create -f role-dev.yaml
```

Now users with the `developer` role can SSH into staging nodes but are explicitly denied access to production — enforced at the protocol level, not just as a suggestion.

---

### 2. Deploying Apache Guacamole

Guacamole is ideal when you need both SSH terminal access and remote desktop (RDP/VNC) through a single web interface.

#### Docker Compose Setup

Guacamole requires three components: PostgreSQL (for connection storage), guacd (the daemon that handles protocols), and the Guacamole web application.

```yaml
version: "3.8"

services:
  guacd:
    image: guacamole/guacd:1.5.5
    container_name: guacd
    restart: unless-stopped
    networks:
      - guac-net

  postgres:
    image: postgres:16-alpine
    container_name: guac-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: guacamole_db
      POSTGRES_USER: guacamole_user
      POSTGRES_PASSWORD: ${GUAC_DB_PASSWORD:-StrongPass123!}
    volumes:
      - guac-db-data:/var/lib/postgresql/data
    networks:
      - guac-net

  guacamole:
    image: guacamole/guacamole:1.5.5
    container_name: guacamole
    restart: unless-stopped
    depends_on:
      - guacd
      - postgres
    ports:
      - "8080:8080"
    environment:
      GUACD_HOSTNAME: guacd
      POSTGRES_HOSTNAME: postgres
      POSTGRES_DATABASE: guacamole_db
      POSTGRES_USER: guacamole_user
      POSTGRES_PASSWORD: ${GUAC_DB_PASSWORD:-StrongPass123!}
    networks:
      - guac-net

volumes:
  guac-db-data:

networks:
  guac-net:
    driver: bridge
```

#### Database Initialization

Guacamole's Docker image includes a schema initialization script. Run it once before starting the service:

```bash
# Generate and apply the database schema
docker run --rm guacamole/guacamole:1.5.5 /opt/guacamole/bin/initdb.sh \
  --postgres > guac-init.sql

docker cp guac-init.sql guac-postgres:/tmp/guac-init.sql
docker exec guac-postgres psql -U guacamole_user -d guacamole_db -f /tmp/guac-init.sql
```

Then start everything:

```bash
docker compose up -d
```

Access Guacamole at `http://your-server:8080/guacamole/`. Default credentials are `guacadmin` / `guacadmin` — change this immediately.

#### Adding SSH Connections

Through the web interface:

1. Log in as `guacadmin`
2. Navigate to **Settings → Connections → New Connection**
3. Configure the connection:

```
Name:        Web Server 01
Protocol:    SSH
Hostname:    192.168.1.50
Port:        22
Username:    ubuntu
```

Under **Parameters → Authentication**, select the password field or upload a private key for key-based authentication.

For parameterized connections that work across multiple hosts, use **Connection Groups** to organize servers by environment (staging, production, homelab) and apply connection-level permissions to user groups.

---

### 3. Deploying Trisail

Trisail's reverse-SSH model is the simplest for homelab setups where target machines are behind NAT, CGNAT, or firewalls you cannot modify.

#### Docker Compose Setup

```yaml
version: "3.8"

services:
  trisail-server:
    image: trisail/trisail:latest
    container_name: trisail-server
    restart: unless-stopped
    ports:
      - "8080:8080"   # Web UI
      - "443:443"     # HTTPS for agent connections
      - "2222:2222"   # SSH proxy port
    volumes:
      - ./trisail-data:/etc/trisail
      - ./certs:/etc/trisail/certs
    environment:
      TRISAIL_SERVER_KEY: ${TRISAIL_SERVER_KEY}
      TRISAIL_DOMAIN: trisail.example.com
    networks:
      - trisail-net

networks:
  trisail-net:
    driver: bridge
```

#### Installing the Agent on Target Nodes

The agent connects outbound to your Trisail server, so no inbound ports need to be opened on target machines:

```bash
curl -fsSL https://trisail.io/install.sh | sh -s -- \
  --server https://trisail.example.com \
  --key ${TRISAIL_SERVER_KEY}
```

Or via Docker on the target:

```bash
docker run -d --name trisail-agent \
  --restart unless-stopped \
  --network host \
  -e TRISAIL_SERVER=https://trisail.example.com \
  -e TRISAIL_KEY=${TRISAIL_SERVER_KEY} \
  trisail/trisail-agent:latest
```

The agent establishes a persistent reverse tunnel. You then connect through Trisail's web UI or SSH proxy to reach any registered node — regardless of its network topology.

---

## Choosing the Right Bastion Host

### Choose Teleport when:

- You need SSH, Kubernetes, database, and web app access through one gateway
- Audit compliance requires detailed session recordings with search
- You want approval-based access requests (a developer requests production access, an admin approves)
- Your team uses OIDC/SAML identity providers and you want seamless SSO
- You need hardware security key (FIDO2) enforcement for admin accounts

### Choose Apache Guacamole when:

- You need both SSH and remote desktop (RDP/VNC) access
- Users should connect through a browser with no client installation
- You have Windows servers alongside Linux machines
- Your team includes non-technical users who need simple point-and-click access
- You prefer Apache 2.0 licensing over AGPL

### Choose Trisail when:

- Target machines are behind NAT, firewalls, or CGNAT (common in residential ISPs)
- You want the simplest possible deployment with minimal configuration
- You're managing IoT devices, edge servers, or homelab nodes
- You need a lightweight solution with low resource overhead
- Your primary use case is SSH access with basic session logging

---

## Security Best Practices for Self-Hosted Bastion Hosts

Regardless of which solution you choose, follow these hardening steps:

### 1. Put the Bastion Behind a Reverse Proxy

Never expose the bastion's management port directly. Use Caddy or Nginx with TLS:

```caddy
bastion.example.com {
    reverse_proxy localhost:8080
    tls {
        protocols tls1.2 tls1.3
    }
}
```

### 2. Enable Fail2Ban on the Bastion Host

```bash
# /etc/fail2ban/jail.local
[sshd]
enabled = true
maxretry = 3
bantime = 3600
findtime = 600
```

### 3. Restrict Bastion Host Access by IP

If your team works from known IP ranges, add a firewall rule:

```bash
# Allow only your office/home IPs to reach the bastion
ufw allow from 203.0.113.0/24 to any port 443
ufw allow from 198.51.100.0/24 to any port 443
ufw deny 443  # Deny all other access
```

### 4. Rotate Credentials Regularly

Set up a cron job to rotate join tokens and service account passwords:

```bash
# Teleport: rotate auth tokens monthly
0 3 1 * * /usr/local/bin/tctl tokens rotate --type=node
```

### 5. Ship Audit Logs to Long-Term Storage

Bastion hosts are prime targets — if an attacker compromises the gateway and deletes logs, you lose all forensic evidence. Forward logs to a separate system:

```yaml
# Teleport audit log shipping (teleport.yaml)
auth_service:
  audit_events_uri:
    - file:///var/lib/teleport/audit
    - postgres://audit-user:pass@log-server:5432/audit_db
```

---

## Migration from Direct SSH Access

If your servers currently allow direct SSH from the internet, migrate in phases:

1. **Phase 1**: Deploy the bastion host and register all nodes as read-only (no access restrictions yet)
2. **Phase 2**: Create user accounts and RBAC roles, test access through the bastion
3. **Phase 3**: Remove direct SSH access from backend servers by updating firewall rules or `sshd_config` (`AllowUsers` directive to only accept connections from the bastion's IP)
4. **Phase 4**: Enable session recording and review the first week of logs to catch permission gaps

```bash
# On each backend server, restrict SSH to bastion IP only
# /etc/ssh/sshd_config
AllowUsers root ubuntu deploy
# Then in firewall:
iptables -A INPUT -p tcp --dport 22 -s <BASTION_IP> -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -j DROP
```

---

## Summary

Self-hosted SSH bastion hosts eliminate the friction of managing SSH keys across dozens of servers while adding security features most teams don't even know they need — session recording, RBAC, and SSO. Teleport leads in features and compliance readiness, Guacamole wins for mixed SSH/desktop environments, and Trisail is the simplest choice for NAT-heavy deployments.

All three run on a single $5 VPS, support Docker Compose deployment, and cost nothing in licensing. The only investment is the initial setup time, which pays for itself the first time you need to audit who accessed what, or onboard a new team member in two clicks instead of distributing SSH keys to twelve servers.
