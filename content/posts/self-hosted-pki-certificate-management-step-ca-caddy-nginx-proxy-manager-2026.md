---
title: "Complete Guide to Self-Hosted Certificate Management and PKI 2026"
date: 2026-04-14
tags: ["comparison", "guide", "self-hosted", "privacy", "security", "tls", "pki"]
draft: false
description: "Complete guide to self-hosted PKI and TLS certificate management in 2026. Compare Step CA, Caddy, and Nginx Proxy Manager with ACME — setup, automation, and best practices for running your own certificate authority."
---

Every self-hosted infrastructure eventually runs into the same problem: TLS certificates. You set up a home lab, deploy a dozen services behind a reverse proxy, and suddenly you are wrestling with expired certs, self-signed warnings, and Let's Encrypt rate limits. If you manage internal services that are not publicly accessible — databases, monitoring dashboards, container registries — public CAs cannot help you at all.

This is where a self-hosted Public Key Infrastructure (PKI) becomes essential. Running your own certificate authority gives you complete control over certificate issuance, lifecycles, trust chains, and revocation — without depending on external services.

## Why Self-Host Your Certificate Authority

The case for running your own CA grows stronger every year:

- **Internal services need TLS too.** Every service in your homelab or corporate network benefits from encrypted connections. A self-hosted CA issues certificates for services that have no public domain name.
- **No rate limits.** Let's Encrypt enforces strict issuance limits per domain per week. With your own CA, you can issue unlimited certificates.
- **Short-lived certificates by default.** Modern security best practices favor certificates that expire in hours or days rather than years. Your own CA can automate this without cost.
- **Zero external dependencies.** No OCSP responders calling home, no Certificate Transparency logs exposing your internal hostnames, no reliance on a third-party service staying online.
- **Unified trust.** Install one root certificate on all your devices and every internal service is trusted automatically. No more clicking "Proceed Anyway" in your browser.
- **Compliance and audit.** Many security frameworks (SOC 2, ISO 27001) require documented certificate management processes. A self-hosted CA gives you full audit trails.
- **Cost savings at scale.** If you manage dozens or hundreds of services, wildcard certificates from commercial CAs get expensive quickly.

In 2026, three solutions stand out for self-hosted certificate management: **Step CA**, **Caddy**, and **Nginx Proxy Manager** with ACME integration. Each takes a fundamentally different approach.

## Option 1: Step CA — The Dedicated Certificate Authority

[Step CA](https://smallstep.com/certificates) by Smallstep is the most powerful and purpose-built self-hosted certificate authority available. Written in Go, it implements the full ACME protocol, supports SCEP for legacy device enrollment, and provides a CLI tool (`step`) that makes certificate management trivial.

### Architecture

Step CA runs as a lightweight daemon that listens on a configurable port. It manages its own root CA key pair, intermediate CA, certificate database, and revocation list. Clients communicate with it over HTTPS using the ACME protocol or the native Step CA protocol.

Key features:
- Full ACME v2 support (HTTP-01, TLS-ALPN-01, DNS-01 challenges)
- SCEP support for enrolling routers, switches, and IoT devices
- Automatic certificate renewal via `step-ca` agent
- X.509 and SSH certificate issuance from the same CA
- Provisioners for OIDC, JWK, AWS IAM, Azure, GCP, and X.509 bootstrap
- Certificate revocation with CRL and OCSP
- Webhook-based authorization for custom policy enforcement
- Runs on a Raspberry Pi with minimal resources

### Installation and Setup

The fastest way to deploy Step CA is with Docker:

```yaml
# docker-compose.yml for Step CA
version: "3.8"

services:
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    restart: unless-stopped
    ports:
      - "9000:9000"
    volumes:
      - ./step:/home/step
      - ./data:/home/step/data
    environment:
      - DOCKER_STEPCA_INIT_NAME=Homelab Root CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=ca.homelab.local,localhost
      - DOCKER_STEPCA_INIT_ADDRESS=:9000
      - DOCKER_STEPCA_INIT_PASSWORD_FILE=/home/step/password.txt
    entrypoint: >
      sh -c '
      echo "my-secure-root-password" > /home/step/password.txt &&
      chmod 600 /home/step/password.txt &&
      /entrypoint.sh'
```

Initialize the CA:

```bash
docker compose up -d
docker compose logs step-ca | grep "fingerprint"
# Note the root CA fingerprint — you will need it to bootstrap clients
```

Bootstrap a client machine to trust your CA:

```bash
# Install the step CLI
brew install smallstep/tap/step

# Bootstrap — downloads the root CA and configures trust
step ca bootstrap --ca-url https://ca.homelab.local:9000 \
  --fingerprint "a1b2c3d4e5f6..."

# The root certificate is now installed in your system trust store
```

Issue your first certificate:

```bash
# Create a one-time token for the provisioner
TOKEN=$(step ca token app.homelab.local --provisioner admin@homelab.local)

# Request a certificate
step ca certificate app.homelab.local app.crt app.key --token $TOKEN

# Verify the certificate
step certificate inspect app.crt
```

### ACME Integration

Step CA fully supports ACME, which means any ACME-compatible client can use it as a drop-in replacement for Let's Encrypt:

```bash
# Using certbot with Step CA as the ACME directory
certbot certonly \
  --server https://ca.homelab.local:9000/acme/acme/directory \
  -d app.homelab.local \
  --standalone

# Or using Caddy's internal ACME client
caddy reverse-proxy --from app.homelab.local:443 \
  --to localhost:8080 \
  --acme-ca https://ca.homelab.local:9000/acme/acme/directory
```

### SSH Certificates

One of Step CA's standout features is unified X.509 and SSH certificate management:

```bash
# Issue an SSH user certificate
step ssh certificate alice@homelab alice-ssh.pub \
  --principal alice --principal alice@homelab.local

# Issue an SSH host certificate
step ssh certificate app.homelab.local ssh_host_ed25519_key.pub \
  --host --principal app.homelab.local

# Configure SSH server to trust Step CA host certificates
# Add to /etc/ssh/sshd_config:
# TrustedUserCAKeys /etc/ssh/step_ca.pub
```

With SSH certificates, you eliminate SSH key distribution entirely. The CA signs user keys on demand, and any server that trusts the CA automatically accepts them.

## Option 2: Caddy — The Self-Healing Web Server

[Caddy](https://caddyserver.com/) is a web server and reverse proxy with built-in automatic TLS certificate management. While not a full CA in the traditional sense, Caddy's certificate automation capabilities make it an excellent choice for self-hosted environments that primarily need public-facing TLS.

### Architecture

Caddy integrates directly with Let's Encrypt and ZeroSSL for public certificates, and can also use Step CA or other ACME servers for internal certificates. Its standout feature is fully automatic certificate issuance and renewal — you never need to think about certificates again.

Key features:
- Automatic HTTPS with zero configuration
- Built-in ACME client for Let's Encrypt, ZeroSSL, and custom CAs
- On-demand TLS — issues certificates at connection time for unknown domains
- OCSP stapling enabled by default
- DNS challenge support for 50+ providers (Cloudflare, Route 53, GoDaddy, etc.)
- Graceful certificate reloading with zero downtime
- JSON API for dynamic configuration
- Written in Go, single binary deployment

### Installation and Setup

Install Caddy and configure it to issue certificates automatically:

```bash
# Install Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

Configure with a Caddyfile:

```Caddyfile
# /etc/caddy/Caddyfile

# Public services — automatic Let's Encrypt certificates
app.example.com {
    reverse_proxy localhost:8080

    # Optional: use DNS challenge for wildcard certs
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}

# Internal services — use Step CA as the ACME server
internal.homelab.local {
    reverse_proxy localhost:3000

    tls {
        ca https://ca.homelab.local:9000/acme/acme/directory
        ca_root /etc/ssl/certs/step-ca-root.crt
    }
}

# On-demand TLS — certificates issued on first connection
*.dynamic.homelab.local {
    reverse_proxy {http.reverse_proxy.upstream.hostport}

    tls {
        on_demand
    }
}
```

### On-Demand TLS

Caddy's on-demand TLS feature is unique — it issues certificates the first time a client connects to a new domain:

```Caddyfile
{
    on_demand_tls {
        ask https://ca.homelab.local:9000/check
        interval 2m
        burst 5
    }
}

*.services.homelab.local {
    reverse_proxy {upstreams}

    tls {
        on_demand
    }
}
```

This is incredibly useful for multi-tenant environments where new subdomains are created dynamically. Caddy checks with your backend whether the domain is authorized, then issues and caches the certificate automatically.

### Docker Deployment

```yaml
version: "3.8"

services:
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"  # For HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}

volumes:
  caddy_data:
  caddy_config:
```

## Option 3: Nginx Proxy Manager — The GUI Approach

[Nginx Proxy Manager](https://nginxproxymanager.com/) provides a web-based interface for managing Nginx reverse proxies with integrated Let's Encrypt certificate management. It is the most beginner-friendly option and perfect for homelab users who prefer a graphical interface over configuration files.

### Architecture

NPM wraps Nginx with a Vue.js web UI and a SQLite/MySQL/PostgreSQL database for configuration storage. Certificate requests are handled through a built-in ACME client that talks to Let's Encrypt.

Key features:
- Web-based management interface
- One-click Let's Encrypt certificate issuance
- Automatic certificate renewal
- DNS challenge support for popular providers
- Access lists with basic authentication
- Stream (TCP/UDP) proxy support
- Custom Nginx configuration overrides
- SSL certificate import for custom CA certs

### Installation and Setup

```yaml
version: "3.8"

services:
  app:
    image: jc21/nginx-proxy-manager:latest
    container_name: npm
    restart: unless-stopped
    ports:
      - "80:80"
      - "81:81"    # Web UI
      - "443:443"
    volumes:
      - ./data:/data
      - ./letsencrypt:/etc/letsencrypt
    environment:
      - DB_SQLITE_FILE=/data/database.sqlite

  # Optional: Cloudflare DNS challenge support
  # NPM supports DNS providers via certbot DNS plugins
```

Access the web UI at `http://your-server:81` (default credentials: admin@example.com / changeme).

### Issuing Certificates via the UI

1. Navigate to **SSL Certificates** in the sidebar
2. Click **Add SSL Certificate**
3. Choose **Let's Encrypt**
4. Enter your domain name(s)
5. Select DNS challenge if the domain is not publicly accessible
6. Click **Save** — NPM handles the ACME challenge and stores the certificate

### Using Custom CA Certificates

For internal services, you can upload certificates issued by your own CA:

1. Go to **SSL Certificates** → **Add SSL Certificate** → **Custom**
2. Upload the certificate key, certificate, and intermediate chain
3. Assign the certificate to any proxy host

This works well in combination with Step CA: use Step CA to issue internal certificates, then upload them to NPM for use with your reverse proxy rules.

## Comparison: Step CA vs Caddy vs Nginx Proxy Manager

| Feature | Step CA | Caddy | Nginx Proxy Manager |
|---------|---------|-------|---------------------|
| **Type** | Dedicated CA | Web server + ACME client | GUI proxy manager |
| **Root CA** | Self-hosted root | Uses Let's Encrypt / ZeroSSL | Uses Let's Encrypt |
| **ACME Server** | Yes (full ACME v2) | ACME client only | ACME client only |
| **ACME Client** | Built-in `step` CLI | Built-in | Built-in (certbot) |
| **Internal Certs** | Native — primary use case | Via custom ACME CA | Manual import only |
| **Auto Renewal** | Via `step-ca` agent | Built-in (default 30 days) | Built-in (daily check) |
| **SSH Certificates** | Yes | No | No |
| **SCEP Support** | Yes | No | No |
| **DNS Challenges** | ACME DNS-01 | 50+ providers | Limited set |
| **On-Demand TLS** | No | Yes | No |
| **Web UI** | No (CLI only) | No (JSON API) | Yes (Vue.js) |
| **Beginner Friendly** | Moderate | Moderate | Excellent |
| **Resource Usage** | ~50 MB RAM | ~30 MB RAM | ~100 MB RAM |
| **Written In** | Go | Go | Node.js + Nginx |
| **Best For** | Enterprise PKI, SSH | Public-facing services | Homelabs, beginners |

## Recommended Architecture: Combining All Three

The most robust self-hosted PKI setup combines these tools:

```
                    ┌─────────────────┐
                    │   Step CA       │
                    │   (Internal CA) │
                    │   :9000         │
                    └────┬────────┬───┘
                         │        │
              ACME       │        │  Native step CLI
           ┌─────────────┘        └──────────────┐
           ▼                                     ▼
    ┌──────────────┐                    ┌────────────────┐
    │    Caddy     │                    │  Internal Apps │
    │ (Public TLS) │                    │  (step client) │
    │   :443       │                    │  with short-   │
    └──────────────┘                    │  lived certs   │
                                        └────────────────┘

    External ───▶ Caddy ───▶ Backend services
                  (Let's Encrypt for public domains,
                   Step CA for internal domains)
```

### Full Deployment Example

Here is a complete Docker Compose setup that ties everything together:

```yaml
version: "3.8"

networks:
  proxy:
    external: true
  internal:
    driver: bridge

services:
  # ── Internal Certificate Authority ──
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    restart: unless-stopped
    networks:
      - internal
    ports:
      - "9000:9000"
    volumes:
      - step_data:/home/step
    environment:
      - DOCKER_STEPCA_INIT_NAME=Homelab Root CA
      - DOCKER_STEPCA_INIT_DNS_NAMES=ca.internal,localhost
      - DOCKER_STEPCA_INIT_ADDRESS=:9000

  # ── Edge Reverse Proxy with Automatic TLS ──
  caddy:
    image: caddy:2-alpine
    container_name: caddy
    restart: unless-stopped
    networks:
      - proxy
      - internal
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
      - ./step-root.crt:/etc/ssl/certs/step-root.crt:ro
    depends_on:
      - step-ca

  # ── Internal Application ──
  app:
    image: your-app:latest
    container_name: app
    restart: unless-stopped
    networks:
      - internal
    environment:
      - TLS_CERT=/certs/app.crt
      - TLS_KEY=/certs/app.key

  # ── Certificate Renewal Agent ──
  cert-renewer:
    image: smallstep/step:latest
    container_name: cert-renewer
    restart: unless-stopped
    networks:
      - internal
    volumes:
      - ./certs:/certs
      - ./step:/home/step:ro
    command: >
      sh -c '
      step ca bootstrap --ca-url https://step-ca:9000 --fingerprint $${FINGERPRINT} --no-prompt &&
      while true; do
        step ca certificate app.internal /certs/app.crt /certs/app.key \
          --provisioner admin --password-file /home/step/password.txt \
          --not-after 24h --force &&
        echo "Certificate renewed at $$(date)" &&
        sleep 21h
      done'

volumes:
  step_data:
  caddy_data:
  caddy_config:
```

Corresponding Caddyfile:

```Caddyfile
{
    # Use Step CA for internal domains
    local_certs
}

# Public-facing service
app.example.com {
    reverse_proxy app:8080

    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
}

# Internal service — use Step CA
monitoring.homelab.local {
    reverse_proxy app:3000

    tls {
        ca https://step-ca:9000/acme/acme/directory
        ca_root /etc/ssl/certs/step-root.crt
    }
}
```

## Certificate Lifecycle Best Practices

Regardless of which tool you choose, follow these principles:

### 1. Use Short-Lived Certificates

Certificates should expire in hours or days, not years. Step CA makes this easy:

```bash
# Issue a certificate valid for 24 hours
step ca certificate app.homelab.local app.crt app.key \
  --not-after 24h

# Or 7 days for services where frequent renewal is impractical
step ca certificate db.homelab.local db.crt db.key \
  --not-after 168h
```

Short-lived certificates eliminate the need for revocation — if a key is compromised, the certificate expires before an attacker can do much damage.

### 2. Automate Renewal

Never manually renew certificates. Use automated agents:

```bash
# Step CA built-in renewal
step ca renew app.crt app.key --daemon

# This runs as a background process and renews at the optimal time
# (roughly 2/3 of the way through the certificate lifetime)
```

### 3. Distribute the Root CA Properly

Install your root CA on all client devices:

```bash
# Linux (Debian/Ubuntu)
sudo cp root-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# macOS
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain root-ca.crt

# Windows (PowerShell as Administrator)
Import-Certificate -FilePath "root-ca.crt" \
  -CertStoreLocation Cert:\LocalMachine\Root
```

### 4. Monitor Certificate Expiry

Even with automation, monitor your certificates:

```bash
# Check expiry date of any certificate
step certificate inspect app.crt --short | grep Validity

# Or use openssl
openssl x509 -in app.crt -noout -dates

# Monitor all certificates in a directory
for cert in /certs/*.crt; do
  echo "=== $cert ==="
  openssl x509 -in "$cert" -noout -enddate
done
```

### 5. Back Up Your Root CA

Your root CA key is the most critical secret in your infrastructure. Back it up securely:

```bash
# Backup the Step CA keys
tar czf step-ca-backup-$(date +%Y%m%d).tar.gz \
  step/certs/step-ca-root_key.pem \
  step/certs/intermediate_ca_key.pem \
  step/db/

# Encrypt the backup
cat step-ca-backup-*.tar.gz | \
  age -r "age1..." > step-ca-backup-encrypted.tar.gz.age

# Store in multiple locations (offline + cloud)
```

## Which Should You Choose?

The decision depends on your needs:

**Choose Step CA if:** You run internal services that need TLS, want SSH certificates, require short-lived certificates, or need enterprise-grade PKI with SCEP and webhook support. It is the gold standard for self-hosted certificate authorities.

**Choose Caddy if:** Your primary need is public-facing TLS with zero configuration, you want on-demand certificate issuance for dynamic domains, or you need a reverse proxy that handles HTTPS automatically.

**Choose Nginx Proxy Manager if:** You prefer a web interface, manage a homelab with a handful of services, want the simplest possible setup, or are new to TLS certificate management.

**Best practice:** Run Step CA as your internal certificate authority and use Caddy as your edge reverse proxy. Caddy handles public-facing Let's Encrypt certificates while using Step CA for any internal domains. This gives you the best of both worlds — automatic public TLS and complete control over your internal PKI.

The days of self-signed certificate warnings and manual certificate management are over. Pick a tool, deploy it once, and let automation handle the rest.
