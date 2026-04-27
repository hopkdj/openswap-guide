---
title: "Certbot vs acme.sh vs lego vs Dehydrated: Best ACME DNS-01 Challenge Tools 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "security", "tls"]
draft: false
description: "Compare Certbot, acme.sh, lego, and Dehydrated for ACME DNS-01 challenge automation. Complete guide to wildcard certificates, DNS provider integration, and self-hosted TLS deployment in 2026."
---

When you need TLS certificates for domains that aren't directly accessible via HTTP — wildcard certificates, internal services, or machines behind NAT — the ACME DNS-01 challenge is the only reliable option. Unlike the HTTP-01 challenge which requires a publicly accessible web server, DNS-01 proves domain ownership by creating a specific DNS TXT record that the Certificate Authority (CA) can verify.

This guide compares the four leading open-source ACME clients that support DNS-01 challenges: **Certbot**, **acme.sh**, **lego**, and **Dehydrated**. We'll cover installation, Docker deployment, DNS provider integration, and automated renewal so you can pick the right tool for your infrastructure.

For a broader look at certificate automation including Kubernetes-native approaches, see our [cert-manager vs lego vs acme.sh comparison](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide-2026/).

## What Is the ACME DNS-01 Challenge?

The ACME protocol (RFC 8555) defines how clients can automatically obtain TLS certificates from CAs like Let's Encrypt, ZeroSSL, and Google Trust Services. The DNS-01 challenge works as follows:

1. The ACME client requests a certificate for `*.example.com`
2. The CA responds with a challenge token and a key authorization
3. The client creates a TXT record at `_acme-challenge.example.com` with the key authorization
4. The CA queries DNS for that TXT record
5. If the record matches, the CA issues the certificate

This process is ideal for:
- **Wildcard certificates** — the only challenge type that supports `*.domain.com`
- **Internal services** — no HTTP endpoint needs to be publicly accessible
- **Load-balanced environments** — avoids the need for shared storage or coordinated HTTP responses
- **Offline issuance** — certificates can be generated on a separate machine and deployed later

## Why Use DNS-01 Instead of HTTP-01?

The HTTP-01 challenge is simpler to set up but has significant limitations:

| Feature | HTTP-01 Challenge | DNS-01 Challenge |
|---------|-------------------|-------------------|
| Wildcard certificates | Not supported | Fully supported |
| Requires public HTTP port | Yes (port 80) | No |
| Works behind NAT/firewall | No | Yes |
| Requires web server access | Yes | No |
| DNS provider API needed | No | Yes |
| Ideal for internal services | No | Yes |
| Supports multiple CAs | Yes | Yes |

If you run a reverse proxy like [nginx, Caddy, or Traefik](../2026-04-24-self-hosted-mutual-tls-mtls-nginx-caddy-traefik-envoy-guide-2026/) and need wildcard certs for multiple subdomains, DNS-01 is the only practical choice.

## Certbot vs acme.sh vs lego vs Dehydrated: Comparison

Here is how the four tools stack up as of April 2026:

| Feature | Certbot | acme.sh | lego | Dehydrated |
|---------|---------|---------|------|------------|
| GitHub stars | 33,012 | 46,409 | 9,496 | 6,198 |
| Language | Python | Shell | Go | Shell |
| License | Apache 2.0 | GPL 3.0 | MIT | MIT |
| DNS-01 support | Yes (via plugins) | Yes (native) | Yes (native) | Yes (via hooks) |
| Wildcard certs | Yes | Yes | Yes | Yes |
| ZeroSSL support | Yes | Yes | Yes | No |
| Google Trust Services | Yes | Yes | Yes | Limited |
| Docker image | Official | Community | Official | None |
| DNS providers | ~20 plugins | 100+ built-in | 60+ built-in | Via custom hooks |
| Auto-renewal | systemd timer | Built-in cron | systemd/cron | Manual or cron |
| Configuration | INI/CLI flags | Environment vars | CLI flags + env | Config file |
| Key size options | RSA + ECDSA | RSA + ECDSA | RSA + ECDSA + ED25519 | RSA + ECDSA |
| Multi-domain SANs | Yes | Yes | Yes | Yes |
| Staging environment | Yes | Yes | Yes | Yes |
| ACME v2 support | Yes | Yes | Yes | Yes |
| Last active | 2026-04-24 | 2026-04-26 | 2026-04-25 | 2026-02-03 |

**Key takeaways:**
- **Certbot** is the most widely known ACME client with official Docker images and strong plugin support, but DNS plugins are separate packages that need individual installation.
- **acme.sh** has the broadest DNS provider support with 100+ integrations built in, making it the easiest choice for uncommon DNS providers.
- **lego** is the most lightweight binary (single Go executable) with strong ED25519 key support and clean API design.
- **Dehydrated** is the simplest shell script but requires the most manual configuration for DNS hooks.

## Installing Each Tool

### Certbot

Certbot is available through system package managers on most distributions:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-dns-cloudflare

# RHEL/CentOS/Fedora
sudo dnf install certbot python3-certbot-dns-cloudflare

# macOS (Homebrew)
brew install certbot
```

For DNS-01 challenges, you also need the corresponding DNS plugin. Available plugins include `python3-certbot-dns-cloudflare`, `python3-certbot-dns-route53`, `python3-certbot-dns-google`, and more.

### acme.sh

acme.sh installs to `~/.acme.sh` and manages its own cron job:

```bash
curl https://get.acme.sh | sh -s email=your@email.com
source ~/.bashrc

# Set DNS provider credentials
export CF_Token="your_cloudflare_api_token"
export CF_Account_ID="your_account_id"

# Issue wildcard certificate
acme.sh --issue --dns dns_cf -d example.com -d '*.example.com'
```

### lego

lego is distributed as a single static binary:

```bash
# Download from GitHub releases
curl -fsSL https://github.com/go-acme/lego/releases/download/v4.20.1/lego_v4.20.1_linux_amd64.tar.gz | tar xz
sudo mv lego /usr/local/bin/lego
chmod +x /usr/local/bin/lego

# Issue certificate with Cloudflare DNS
export CLOUDFLARE_DNS_API_TOKEN="your_token"
lego --email your@email.com --dns cloudflare --domains example.com --domains '*.example.com' run
```

### Dehydrated

Dehydrated is a single bash script:

```bash
git clone https://github.com/dehydrated/dehydrated.git
cd dehydrated
sudo cp dehydrated /usr/local/bin/
sudo chmod +x /usr/local/bin/dehydrated

# Accept terms
dehydrated --register --accept-terms

# Create config
mkdir -p /etc/dehydrated
cat > /etc/dehydrated/config << 'EOF'
CA="https://acme-v02.api.letsencrypt.org/directory"
WELLKNOWN="/var/lib/dehydrated/acme-challenges"
HOOK="/etc/dehydrated/hook.sh"
EOF
```

## Docker Deployment Examples

### Certbot with Docker

Certbot provides official Docker images that handle certificate issuance and renewal:

```yaml
services:
  certbot:
    image: certbot/certbot:latest
    container_name: certbot-dns
    volumes:
      - ./certs:/etc/letsencrypt
      - ./certbot-logs:/var/log/letsencrypt
    environment:
      - CLOUDFLARE_DNS_API_TOKEN=${CF_TOKEN}
    entrypoint: "/bin/sh -c"
    command: >
      "certbot certonly --dns-cloudflare
      --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini
      -d example.com -d '*.example.com'
      --agree-tos --email admin@example.com
      --non-interactive --keep-until-expiring"

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./certs:/etc/letsencrypt:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - certbot
```

Create the Cloudflare credentials file:

```ini
# cloudflare.ini
dns_cloudflare_api_token = your_api_token_here
```

### acme.sh with Docker

While acme.sh doesn't have an official Docker image, the community maintains reliable images:

```yaml
services:
  acmesh:
    image: neilpang/acme.sh:latest
    container_name: acme-sh
    volumes:
      - ./certs:/acme.sh
    environment:
      - CF_Token=${CF_TOKEN}
      - CF_Account_ID=${CF_ACCOUNT_ID}
      - CF_Email=${CF_EMAIL}
    command: >
      --issue
      --dns dns_cf
      -d example.com
      -d '*.example.com'
      --force
      --log
```

To install certificates to a persistent volume after issuance:

```yaml
    command: >
      --issue
      --dns dns_cf
      -d example.com
      -d '*.example.com'
      --install-cert
      -d example.com
      --key-file /acme.sh/certs/privkey.pem
      --fullchain-file /acme.sh/certs/fullchain.pem
      --reloadcmd "cat /acme.sh/certs/fullchain.pem /acme.sh/certs/privkey.pem > /acme.sh/certs/combined.pem"
```

### lego with Docker

lego provides official Docker images:

```yaml
services:
  lego:
    image: goacme/lego:latest
    container_name: lego-dns
    volumes:
      - ./certs:/data
    environment:
      - CLOUDFLARE_DNS_API_TOKEN=${CF_TOKEN}
      - LEGO_EMAIL=admin@example.com
    command: >
      --dns cloudflare
      --domains example.com
      --domains '*.example.com'
      --accept-tos
      --path /data
      run
```

The certificates are stored in `/data/certificates/` within the container and mapped to `./certs/` on the host.

## DNS Provider API Setup

Most DNS providers require an API token with specific permissions for DNS record management:

### Cloudflare

Create an API token at the Cloudflare dashboard with these permissions:
- Zone → DNS → Edit
- Zone → Zone → Read

```bash
# acme.sh
export CF_Token="your_token"
export CF_Account_ID="your_account_id"
acme.sh --issue --dns dns_cf -d '*.example.com'

# lego
export CLOUDFLARE_DNS_API_TOKEN="your_token"
lego --dns cloudflare -d '*.example.com' run
```

### AWS Route 53

Create an IAM policy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:GetChange",
        "route53:ChangeResourceRecordSets",
        "route53:ListHostedZonesByName"
      ],
      "Resource": "*"
    }
  ]
}
```

```bash
# Certbot
sudo certbot certonly \
  --dns-route53 \
  -d example.com -d '*.example.com'

# lego (uses AWS credentials from environment)
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
lego --dns route53 -d '*.example.com' run
```

### Google Cloud DNS

Create a service account with the `DNS Administrator` role and export the key:

```bash
# lego
export GCE_SERVICE_ACCOUNT_FILE="/path/to/service-account.json"
lego --dns gcloud -d '*.example.com' run

# Certbot
sudo certbot certonly \
  --dns-google \
  --dns-google-credentials /path/to/service-account.json \
  -d '*.example.com'
```

## Automated Renewal Setup

### Certbot (systemd timer)

Certbot includes a systemd timer that runs twice daily:

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run
```

For DNS plugins, add the credentials to `/etc/letsencrypt/renewal/*.conf`:

```ini
# /etc/letsencrypt/renewal/example.com.conf
[renewalparams]
dns_cloudflare_credentials = /etc/letsencrypt/cloudflare.ini
```

### acme.sh (built-in cron)

acme.sh automatically installs a cron entry during setup:

```bash
# Check installed cron job
crontab -l | grep acme

# Manual test
acme.sh --renew -d example.com --force

# Upgrade acme.sh to latest version
acme.sh --upgrade
```

### lego (systemd timer)

Create a systemd timer for automatic renewal:

```ini
# /etc/systemd/system/lego-renew.service
[Unit]
Description=Lego ACME Certificate Renewal

[Service]
Type=oneshot
ExecStart=/usr/local/bin/lego --email admin@example.com \
  --dns cloudflare \
  --domains example.com --domains '*.example.com' \
  --path /etc/lego renew
EnvironmentFile=/etc/lego/lego.env
```

```ini
# /etc/systemd/system/lego-renew.timer
[Unit]
Description=Run Lego renewal twice daily

[Timer]
OnCalendar=*-*-* 00/12:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now lego-renew.timer
```

### Dehydrated (cron)

```bash
# /etc/cron.daily/dehydrated
#!/bin/bash
/usr/local/bin/dehydrated --cron --hook /etc/dehydrated/hook.sh --config /etc/dehydrated/config
```

## Which Tool Should You Choose?

| Use Case | Recommended Tool | Reason |
|----------|-----------------|--------|
| Quick setup with popular DNS providers | acme.sh | 100+ providers built in, zero config |
| Kubernetes/infrastructure automation | lego | Single binary, clean API, ED25519 support |
| Enterprise/Compliance environments | Certbot | Well-audited, official packages, broad CA support |
| Minimal dependencies (bare bash) | Dehydrated | Single script, no runtime dependencies |
| Multi-cloud DNS providers | acme.sh | Broadest provider coverage |
| CI/CD pipeline integration | lego | Easy to embed in CI, no Python/Shell deps |
| Existing Certbot infrastructure | Certbot | Migration path is seamless |

If you are also interested in verifying your TLS configuration after deployment, check out our [SSL/TLS scanning tools guide](../2026-04-22-testssl-vs-sslyze-vs-sslscan-self-hosted-ssl-tls-scanning-guide-2026/).

## FAQ

### What is the difference between HTTP-01 and DNS-01 ACME challenges?

HTTP-01 requires placing a file at `http://yourdomain/.well-known/acme-challenge/` which the CA fetches over HTTP. DNS-01 requires creating a TXT record at `_acme-challenge.yourdomain.com` which the CA resolves via DNS. DNS-01 is the only method that supports wildcard certificates and works for services not accessible via the public internet.

### Can I use DNS-01 challenges without exposing my DNS provider API credentials?

All DNS-01 tools require API access to create TXT records. However, you can minimize risk by using scoped API tokens (e.g., Cloudflare tokens limited to DNS edit on specific zones) rather than full account keys. Tools like acme.sh and lego support reading credentials from environment variables, Docker secrets, or HashiCorp Vault rather than plaintext config files.

### How long does DNS propagation take for ACME challenges?

Most CAs poll for the DNS TXT record every 2-5 seconds and typically complete validation within 30-60 seconds. However, some DNS providers have higher propagation delays. If validation fails, all tools support configurable wait periods — acme.sh uses `--dnssleep`, Certbot uses `--dns-cloudflare-propagation-seconds`, and lego uses `--dns-timeout`.

### Do these tools support multiple CAs beyond Let's Encrypt?

Yes. Certbot, acme.sh, and lego all support Let's Encrypt, ZeroSSL, Google Trust Services, and BuyPass. Dehydrated supports Let's Encrypt and ZeroSSL with custom CA configuration. acme.sh allows switching CAs with `--server zerossl` or `--server buypass`. lego uses `--server` flag to specify any ACME v2 endpoint.

### Can I automate DNS-01 challenges if my DNS provider is not natively supported?

Yes. All four tools support custom DNS hooks. For acme.sh, create a `dns_myprovider.sh` script following their API format. For Certbot, write a Python plugin or use the `--manual-auth-hook` flag. For lego, implement the DNS provider interface in Go or use the `--dns` flag with a custom executable. For Dehydrated, the hook script receives `deploy_challenge` and `clean_challenge` calls.

### How do I renew certificates before they expire?

All tools handle renewal automatically when configured correctly. Certbot runs twice daily via systemd timer and only renews within 30 days of expiry. acme.sh checks certificates daily via cron and renews automatically. lego requires a systemd timer or cron entry to trigger renewal. Dehydrated needs a daily cron job with the `--cron` flag. You can always force a renewal manually for testing with the respective `--force` or `--dry-run` flags.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Certbot vs acme.sh vs lego vs Dehydrated: Best ACME DNS-01 Challenge Tools 2026",
  "description": "Compare Certbot, acme.sh, lego, and Dehydrated for ACME DNS-01 challenge automation. Complete guide to wildcard certificates, DNS provider integration, and self-hosted TLS deployment.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
