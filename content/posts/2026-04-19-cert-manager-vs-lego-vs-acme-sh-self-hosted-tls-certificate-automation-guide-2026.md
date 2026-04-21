---
title: "cert-manager vs LEGO vs acme.sh: Self-Hosted TLS Certificate Automation Guide 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "tls", "certificates", "security", "devops"]
draft: false
description: "Compare cert-manager, LEGO, and acme.sh for self-hosted TLS certificate automation. Complete guide with Docker Compose configs, DNS challenge setup, and auto-renewal strategies for 2026."
---

Managing TLS certificates manually is one of the most common causes of service outages. Expired certificates bring down websites, break API endpoints, and disrupt email delivery. In 2026, the solution is straightforward: automate certificate provisioning and renewal using a self-hosted ACME client.

This guide compares three leading open-source tools for self-hosted TLS certificate management: **cert-manager** ([kubernetes](https://kubernetes.io/)-native), **LEGO** (standalone Go binary), and **acme.sh** (shell-script based). We'll cover installation, DNS challenge configuration, [docker](https://www.docker.com/) deployment, and auto-renewal strategies so you can choose the right tool for your infrastructure.

## Why Self-Host Your TLS Certificate Management?

Relying on managed certificate services or manual `certbot` runs introduces single points of failure and operational overhead. Self-hosting your ACME client gives you:

- **Full control** over certificate lifecycle — issue, renew, revoke on your schedule
- **No external dependencies** — your certificates aren't tied to a third-party platform
- **DNS-01 challenge support** — issue wildcard certificates without exposing any HTTP endpoint
- **Integration flexibility** — hook certificate issuance into CI/CD pipelines, infrastructure-as-code, or container orchestration
- **Cost savings** — Let's Encrypt and other ACME CAs are free; you only pay for your server

Whether you're running a [self-hosted email server](../self-hosted-email-server-postfix-dovecot-rspamd-complete-guide-2026/) that needs valid TLS for mail delivery, or managing certificates across a fleet of [reverse proxies](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide-2026/), having a reliable certificate automation tool is essential infrastructure.

## Project Overview and Live Stats

Here's how the three tools compare as of April 2026, based on live GitHub data:

| Feature | cert-manager | LEGO | acme.sh |
|---------|-------------|------|---------|
| **GitHub Stars** | 13,756 | 9,480 | 46,335 |
| **Last Updated** | 2026-04-18 | 2026-04-19 | 2026-04-14 |
| **Language** | Go | Go | Shell |
| **Primary Use** | Kubernetes clusters | Standalone servers & scripts | Any Unix server |
| **DNS Providers** | 20+ (via webhook) | 80+ (built-in) | 100+ (built-in) |
| **Wildcard Support** | Yes (DNS-01) | Yes (DNS-01) | Yes (DNS-01) |
| **Auto-Renewal** | Built-in (K8s controller) | Requires cron/systemd | Built-in (cron) |
| **Docker Image** | Official | Official | Official |
| **Best For** | Kubernetes operators | Go developers, DevOps scripts | Sysadmins, quick setup |

**cert-manager** by Jetstack (now part of F5) is the de facto standard for Kubernetes certificate management. It runs as a controller inside your cluster and automatically provisions certificates via Kubernetes Custom Resource Definitions (CRDs). With 13,756 stars and active development, it's the go-to choice for cloud-native teams.

**LEGO** by go-acme is a standalone ACME client written in Go. It supports over 80 DNS providers natively and is designed for use in scripts, CI/CD pipelines, and standalone servers. Its binary-only distribution makes it ideal for containerized deployments. Updated as recently as today, the project is actively maintained.

**acme.sh** is the most popular ACME client by a wide margin with 46,335 stars. Written as a pure Unix shell script, it requires no dependencies beyond `curl` and `openssl`. It supports over 100 DNS providers and has a built-in cron-based renewal system. Its simplicity makes it accessible to any system administrator.

## How ACME Certificate Issuance Works

All three tools use the same underlying protocol: the **ACME (Automatic Certificate Management Environment)** protocol defined in RFC 8555. The workflow is consistent across tools:

1. **Order creation** — the client requests a certificate for specific domain(s)
2. **Challenge selection** — the CA (e.g., Let's Encrypt) offers challenge types (HTTP-01, DNS-01, TLS-ALPN-01)
3. **Challenge fulfillment** — the client proves domain ownership
4. **Validation** — the CA verifies the challenge response
5. **Certificate issuance** — the CA returns the signed certificate

For self-hosted infrastructure, **DNS-01 challenges** are the most versatile option because they:
- Support wildcard certificates (`*.example.com`)
- Don't require port 80 to be open
- Work behind NAT and firewalls
- Allow certificate issuance for internal domains

## Installation and Quick Start

### cert-manager (Kubernetes)

cert-manager is installed via Helm into your Kubernetes cluster:

```bash
# Add the Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.16.0 \
  --set installCRDs=true
```

Create a ClusterIssuer for Let's Encrypt production:

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-account-key
    solvers:
    - dns01:
        cloudflare:
          apiTokenSecretRef:
            name: cloudflare-api-token
            key: api-token
```

Request a certificate with a Certificate resource:

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-tls
  namespace: default
spec:
  secretName: example-com-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - example.com
  - "*.example.com"
```

cert-manager automatically handles renewal — certificates are renewed approximately 30 days before expiry by default.

### LEGO (Standalone / Docker)

LEGO is distributed as a single Go binary. Install it from the GitHub releases page or via package managers:

```bash
# Install via Go (requires Go 1.21+)
go install github.com/go-acme/lego/v4/cmd/lego@latest

# Or download the binary
curl -sL https://github.com/go-acme/lego/releases/download/v4.20.1/lego_v4.20.1_linux_amd64.tar.gz \
  -o lego.tar.gz
tar -xzf lego.tar.gz lego
sudo mv lego /usr/local/bin/
```

Run with DNS-01 challenge (Cloudflare example):

```bash
export CLOUDFLARE_DNS_API_TOKEN="your-cloudflare-api-token"

lego --email="admin@example.com" \
  --domains="example.com" \
  --domains="*.example.com" \
  --dns="cloudflare" \
  --accept-tos \
  run
```

Certificates are saved to `~/.lego/certificates/`. Set up auto-renewal with a cron job:

```bash
# Renew certificates every Monday at 3 AM
0 3 * * 1 /usr/local/bin/lego \
  --email="admin@example.com" \
  --domains="example.com" \
  --domains="*.example.com" \
  --dns="cloudflare" \
  --accept-tos \
  renew --days 30 && \
  systemctl reload nginx
```

Docker Compose deployment:

```yaml
services:
  lego:
    image: goacme/lego:latest
    container_name: lego
    volumes:
      - ./lego-data:/root/.lego
      - ./certs:/etc/lego/certificates
    environment:
      - CLOUDFLARE_DNS_API_TOKEN=${CF_API_TOKEN}
    command: >
      --email=admin@example.com
      --domains=example.com
      --domains=*.example.com
      --dns=cloudflare
      --accept-tos
      run
    restart: "no"
```

### acme.sh (Shell Script)

acme.sh installs itself to your home directory and sets up automatic renewal:

```bash
# Install acme.sh
curl https://get.acme.sh | sh -s email=admin@example.com
source ~/.bashrc

# Set DNS provider credentials
export CF_Token="your-cloudflare-api-token"
export CF_Account_ID="your-cloudflare-account-id"

# Issue a wildcard certificate
acme.sh --issue \
  --dns dns_cf \
  -d example.com \
  -d "*.example.com" \
  --server letsencrypt

# Install the certificate to your desired location
acme.sh --install-cert \
  -d example.com \
  --key-file /etc/ssl/private/example.com.key \
  --fullchain-file /etc/ssl/certs/example.com.crt \
  --reloadcmd "systemctl reload nginx"
```

acme.sh automatically installs a cron entry during installation. Renewal is handled transparently — no manual cron setup needed.

Docker Compose deployment:

```yaml
services:
  acme:
    image: neilpang/acme.sh:latest
    container_name: acme-sh
    volumes:
      - ./acme-data:/acme.sh
      - ./certs:/certs
    environment:
      - CF_Token=${CF_API_TOKEN}
      - CF_Account_ID=${CF_ACCOUNT_ID}
    command: >
      --issue
      --dns dns_cf
      -d example.com
      -d "*.example.com"
      --server letsencrypt
      --home /acme.sh
    restart: "no"
```

## DNS Provider Support

DNS-01 challenges require API access to your DNS provider. Here's how the three tools compare on DNS provider support:

| Provider | cert-manager | LEGO | acme.sh |
|----------|-------------|------|---------|
| Cloudflare | ✅ Native | ✅ Built-in | ✅ Built-in |
| AWS Route53 | ✅ Native | ✅ Built-in | ✅ Built-in |
| Google Cloud DNS | ✅ Native | ✅ Built-in | ✅ Built-in |
| DigitalOcean | ✅ Native | ✅ Built-in | ✅ Built-in |
| Azure DNS | ✅ Native | ✅ Built-in | ✅ Built-in |
| OVH | ✅ Native | ✅ Built-in | ✅ Built-in |
| Namecheap | ✅ Webhook | ✅ Built-in | ✅ Built-in |
| GoDaddy | ✅ Webhook | ✅ Built-in | ✅ Built-in |
| Hetzner | ✅ Webhook | ✅ Built-in | ✅ Built-in |
| Porkbun | ✅ Webhook | ✅ Built-in | ✅ Built-in |
| **Total providers** | ~20 (native) + webhooks | 80+ built-in | 100+ built-in |

cert-manager relies on external webhook extensions for less common providers, which adds deployment com[plex](https://www.plex.tv/)ity. LEGO and acme.sh have broader built-in support, making them easier to deploy across diverse DNS infrastructures.

## Security Best Practices

Regardless of which tool you choose, follow these security practices:

### 1. Use API Tokens, Not Account Keys

Never store your DNS provider's account-level API key. Instead, create scoped tokens with minimal permissions:

- **Cloudflare**: Use Zone → DNS → Edit permission only
- **AWS Route53**: Scope to specific hosted zones with IAM policies
- **Google Cloud DNS**: Use service account with `dns.changes.create` on specific zones

### 2. Protect Private Keys

```bash
# Set restrictive permissions on certificate directories
sudo chmod 700 /etc/ssl/private
sudo chmod 600 /etc/ssl/private/*.key

# For Docker volumes, use read-only mounts where possible
volumes:
  - ./certs:/etc/ssl/certs:ro
```

### 3. Set Up Certificate Monitoring

Even with auto-renewal, monitor certificate expiry to catch failures early:

```bash
# Check certificate expiry date
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null \
  | openssl x509 -noout -enddate

# Automated check (alert if less than 14 days remaining)
openssl x509 -checkend 1209600 -noout -in /etc/ssl/certs/example.com.crt
if [ $? -eq 1 ]; then
  echo "CRITICAL: Certificate expires within 14 days!" | mail -s "Cert Alert" admin@example.com
fi
```

### 4. Use Multiple ACME Servers

Configure a secondary CA (e.g., ZeroSSL, Buypass, or Google Trust Services) as a fallback:

```bash
# acme.sh supports multiple CAs
acme.sh --issue -d example.com --server buypass
acme.sh --issue -d example.com --server zerossl
```

LEGO also supports alternate ACME directories:

```bash
lego --server="https://api.zerossl.com/acme/acme-v02-newAccount" \
  --email="admin@example.com" \
  --domains="example.com" \
  --dns="cloudflare" run
```

## Migration from Manual certbot

If you're currently using manual `certbot` renewals, migration is straightforward:

```bash
# 1. Stop using certbot cron jobs
sudo systemctl disable certbot.timer 2>/dev/null
sudo crontab -e  # Remove certbot entries

# 2. Move existing certificates to a shared location
sudo cp -r /etc/letsencrypt/live/example.com/ /etc/ssl/certs/

# 3. Switch to your chosen tool (examples above)

# 4. Verify new certificates work before removing old ones
curl -vI https://example.com 2>&1 | grep "expire date"
```

For Kubernetes users already running cert-manager, you can import existing Let's Encrypt account keys to avoid rate limit issues:

```bash
# Extract the account key from certbot
kubectl create secret generic letsencrypt-prod-account-key \
  --from-file=private-key-secret=/etc/letsencrypt/accounts/acme-v02.api.letsencrypt.org/directory/<account-id>/private_key.json \
  --namespace cert-manager
```

## Choosing the Right Tool

Your choice depends on your infrastructure:

| Scenario | Recommended Tool | Reason |
|----------|-----------------|--------|
| Kubernetes cluster | **cert-manager** | Native K8s integration, CRDs, automatic secret management |
| Single server, multiple domains | **acme.sh** | Easiest setup, automatic cron, broadest DNS support |
| CI/CD pipeline integration | **LEGO** | Single binary, programmatic API, Go library |
| Mixed infrastructure | **LEGO + acme.sh** | LEGO for automation, acme.sh for ad-hoc issuance |
| GitOps / IaC workflows | **LEGO** | Reproducible binary, easy to pin versions |
| Quick setup for small team | **acme.sh** | One command install, zero dependencies |

If you're managing certificates for a [PKI infrastructure](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/) or need internal CA integration, consider pairing any of these tools with Step CA for a complete certificate lifecycle solution.

## FAQ

### What is the difference between HTTP-01 and DNS-01 challenges?

HTTP-01 requires the ACME client to serve a verification file at `http://yourdomain/.well-known/acme-challenge/`. This means port 80 must be publicly accessible and the domain must resolve to your server. DNS-01 requires creating a specific DNS TXT record (`_acme-challenge.yourdomain.com`), which works for any domain regardless of network topology. DNS-01 is the only challenge type that supports wildcard certificates.

### How often do Let's Encrypt certificates need to be renewed?

Let's Encrypt certificates are valid for 90 days. Best practice is to renew at 60 days (30 days before expiry) to provide a safety margin. All three tools in this guide support automatic renewal: cert-manager handles it via the Kubernetes controller, acme.sh sets up a cron job during installation, and LEGO can be scheduled via cron or systemd timers.

### Can I use these tools with self-hosted Kubernetes distributions like k3s or Talos?

Yes. cert-manager works with any Kubernetes distribution that supports Custom Resource Definitions, including [k3s, k0s, and Talos Linux](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/). The installation process is identical regardless of the Kubernetes distribution. For lightweight distributions without a full Helm setup, you can also apply cert-manager manifests directly with `kubectl`.

### What happens if DNS challenge automation fails?

If a DNS-01 challenge fails (e.g., API token expired, DNS provider outage), the certificate won't be issued or renewed. This is why monitoring certificate expiry is critical. Set up alerts using tools like [Gatus or Prometheus Blackbox Exporter](../gatus-vs-blackbox-exporter-vs-smokeping-self-hosted-endpoint-monitoring-2026/) to detect expiring certificates. Additionally, configure a secondary ACME server (ZeroSSL, Buypass) as a fallback to reduce the impact of any single provider's issues.

### Is acme.sh safe to use? It's just a shell script.

Yes. acme.sh is one of the most widely deployed ACME clients with over 46,000 GitHub stars. It's been audited by the community, is the default ACME client in many Linux distributions, and supports the full ACME v2 protocol. Being a shell script means it has zero dependencies — no Python, no Go runtime, just `curl` and `openssl` which are present on virtually every Unix system. However, like any script that handles credentials, ensure you restrict file permissions on the `~/.acme.sh/` directory.

### Can I issue certificates for internal domains (e.g., *.internal.example.com)?

You can use DNS-01 challenges for any domain you control DNS for, including internal domains. However, Let's Encrypt requires the domain to be publicly resolvable for validation. For purely internal domains, consider using [Step CA](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/) as your internal CA instead. Step CA provides the same ACME protocol interface but for private certificate issuance.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "cert-manager vs LEGO vs acme.sh: Self-Hosted TLS Certificate Automation Guide 2026",
  "description": "Compare cert-manager, LEGO, and acme.sh for self-hosted TLS certificate automation. Complete guide with Docker Compose configs, DNS challenge setup, and auto-renewal strategies for 2026.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
