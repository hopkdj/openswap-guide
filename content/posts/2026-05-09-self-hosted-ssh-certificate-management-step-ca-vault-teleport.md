---
title: "Self-Hosted SSH Certificate Management: step-ca vs Vault vs Teleport (2026)"
date: "2026-05-09"
draft: false
tags: ["ssh", "certificate-management", "security", "pki", "zero-trust", "access-management"]
---

Managing SSH access at scale is one of the most common infrastructure challenges. Traditional SSH key management relies on distributing public keys via `authorized_keys` files, which becomes unwieldy as teams grow: keys are rarely rotated, departed employees retain access, and auditing who accessed what server is nearly impossible.

SSH certificates solve these problems by using a certificate authority (CA) to sign short-lived SSH credentials. Instead of managing individual keys, you trust the CA and let it issue time-limited certificates for users and hosts.

This guide compares three open-source tools for self-hosted SSH certificate management: **smallstep step-ca**, **HashiCorp Vault**, and **Teleport**.

## Comparison Table

| Feature | step-ca | HashiCorp Vault | Teleport |
|---------|---------|----------------|----------|
| **Stars** | 8,400+ | 35,500+ | 20,200+ |
| **Primary Focus** | Private CA (X.509 + SSH) | Secrets management platform | Zero-trust access platform |
| **SSH CA** | Yes (built-in) | Yes (SSH secrets engine) | Yes (built-in) |
| **TLS/PKI** | Yes (full ACME server) | Yes (PKI secrets engine) | Yes (application access) |
| **Certificate Lifetime** | Configurable (minutes to years) | Configurable (minutes to years) | Short-lived (minutes to hours) |
| **Authentication** | JWT, OAuth, SSO, API key | Multiple auth methods (LDAP, OIDC, etc.) | GitHub, SAML, OIDC, SSO |
| **Audit Logging** | Basic (certificate issuance log) | Comprehensive (audit device) | Comprehensive (session recording) |
| **Session Recording** | No | No | Yes (SSH session playback) |
| **Docker Image** | smallstep/step-ca | hashicorp/vault | gravitational/teleport |
| **Last Active** | 2026 | 2026 | 2026 |
| **Language** | Go | Go | Go |

## smallstep step-ca: The Lightweight Private CA

step-ca is a private certificate authority that issues both X.509 TLS certificates and SSH certificates. It is designed to be simple, secure, and ACME-compatible — making it the easiest option to deploy for teams that need SSH certificates without a complex secrets management platform.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  step-ca:
    image: smallstep/step-ca:latest
    ports:
      - "443:443"
    volumes:
      - step-ca-data:/home/step
    environment:
      - DOCKER_STEPCA_INIT=true
      - STEPCA_INIT_NAME="Internal CA"
      - STEPCA_INIT_DNS="ca.internal"
      - STEPCA_INIT_ADDRESS="0.0.0.0:443"
      - STEPCA_INIT_PROVISIONER=admin@example.com
    restart: unless-stopped

volumes:
  step-ca-data:
```

### Generating SSH Certificates

```bash
# Initialize the CA (interactive)
step ca init \
  --name="Internal CA" \
  --dns="ca.internal" \
  --address="0.0.0.0:443" \
  --provisioner="admin@example.com"

# Generate an SSH user certificate
step ssh certificate user@company \
  ~/.ssh/id_ed25519.pub \
  --provisioner="admin@example.com" \
  --not-after="24h"

# Generate an SSH host certificate
step ssh certificate server.example.com \
  /etc/ssh/ssh_host_ed25519_key.pub \
  --host \
  --provisioner="admin@example.com" \
  --not-after="8760h"
```

### SSH Client Configuration

```bash
# Configure SSH to use the step CA
step ssh config >> ~/.ssh/config

# The above adds:
# Host *
#   CertificateFile ~/.step/ssh/id_ed25519-cert.pub
#   UserKnownHostsFile ~/.step/ssh/known_hosts
```

### SSH Server Configuration

```bash
# On the SSH server, configure TrustedUserCAKeys
step ssh config --host >> /etc/ssh/sshd_config

# This adds:
# TrustedUserCAKeys /etc/ssh/trusted_user_ca_keys.pub
# RevokedKeys /etc/ssh/revoked_keys

# Restart SSH
systemctl restart sshd
```

## HashiCorp Vault: The Enterprise Secrets Platform

Vault is a comprehensive secrets management platform that includes an SSH secrets engine. If you are already using Vault for secrets, encryption, or PKI, adding SSH certificate management is a natural extension.

### Docker Compose with Dev Mode (Testing)

```yaml
version: "3.8"
services:
  vault:
    image: hashicorp/vault:latest
    cap_add:
      - IPC_LOCK
    ports:
      - "8200:8200"
    environment:
      - VAULT_DEV_ROOT_TOKEN_ID=myroot
      - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
    volumes:
      - vault-data:/vault/file
    restart: unless-stopped

volumes:
  vault-data:
```

### Production Configuration

```yaml
version: "3.8"
services:
  vault:
    image: hashicorp/vault:latest
    cap_add:
      - IPC_LOCK
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config:/vault/config
      - vault-data:/vault/file
    command: ["vault", "server", "-config=/vault/config/config.hcl"]
    restart: unless-stopped

volumes:
  vault-data:
```

### Vault Config for SSH CA

```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/vault/config/vault.crt"
  tls_key_file  = "/vault/config/vault.key"
}

disable_mlock = true
```

### Configuring the SSH Secrets Engine

```bash
export VAULT_ADDR='https://vault.internal:8200'
vault login

# Enable the SSH secrets engine
vault secrets enable ssh

# Configure a CA role for user certificates
vault write ssh/roles/user-role \
  key_type=ca \
  default_user=ubuntu \
  allow_user_certificates=true \
  allowed_users="*" \
  ttl=24h

# Sign an SSH public key
vault write ssh/sign/user-role \
  public_key=@~/.ssh/id_ed25519.pub \
  valid_principals="user@company"
```

### SSH Server Configuration with Vault

```bash
# Configure Vault to manage SSH host keys
vault write ssh/config/ca generate_signing_key=true

# On each SSH server, configure Vault to sign host keys
vault write ssh/config/zero-address role="host-role"
```

## Teleport: Zero-Trust Access with Session Recording

Teleport is a zero-trust access platform that provides SSH access with built-in certificate management, role-based access control, and session recording. Unlike step-ca and Vault, Teleport is purpose-built for infrastructure access rather than general-purpose secrets management.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  teleport:
    image: public.ecr.aws/gravitational/teleport-distroless:latest
    ports:
      - "3023:3023"   # SSH proxy
      - "3024:3024"   # SSH tunnel (multiplexing)
      - "3025:3025"   # Auth server
      - "443:443"     # Web UI / API
      - "3080:3080"   # Web UI (HTTP)
    volumes:
      - teleport-data:/var/lib/teleport
      - ./teleport-config:/etc/teleport
    command: ["teleport", "start", "-c", "/etc/teleport/teleport.yaml"]
    restart: unless-stopped

volumes:
  teleport-data:
```

### Teleport Configuration

```yaml
# /etc/teleport/teleport.yaml
version: v3
teleport:
  nodename: teleport-server
  data_dir: /var/lib/teleport
  log:
    output: stderr
    severity: INFO
  ca_pin: ""

auth_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3025
  cluster_name: teleport-cluster
  authentication:
    type: local
    second_factor: otp

ssh_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3022
  labels:
    env: production
    team: infrastructure

proxy_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3023
  web_listen_addr: 0.0.0.0:443
  tunnel_listen_addr: 0.0.0.0:3024
  public_addr: teleport.example.com:443
```

### Creating a User and Role

```bash
# Create a user (generates an invite link)
tctl users add admin --roles=editor --logins=root,ubuntu

# Define a role
cat > developer.yaml << 'EOF'
kind: role
metadata:
  name: developer
spec:
  allow:
    logins: [ubuntu, deploy]
    node_labels:
      "env": ["staging", "development"]
    rules:
      - resources: ["session"]
        verbs: ["list", "read"]
  deny:
    node_labels:
      "env": ["production"]
version: v7
EOF

tctl create -f developer.yaml
```

### Connecting via Teleport

```bash
# Login via the CLI
tsh login --proxy=teleport.example.com --user=admin

# SSH to a node
tsh ssh ubuntu@production-server

# Replay a recorded session
tsh play <session-id>
```

## When to Use Each Tool

**Use step-ca when:**
- You need a simple, dedicated SSH + TLS certificate authority
- Your primary requirement is certificate issuance without session recording
- You want ACME compatibility for automatic TLS certificate renewal
- You prefer a lightweight, single-purpose tool over a platform
- You are a small-to-medium team that needs SSH certificates without complex RBAC

**Use HashiCorp Vault when:**
- You are already using Vault for secrets management or PKI
- You need SSH certificates as part of a broader secrets management strategy
- You require dynamic SSH credentials (Vault generates key pairs on demand)
- Your organization needs comprehensive audit logging across all secrets
- You have an existing Vault infrastructure and want to consolidate tooling

**Use Teleport when:**
- You need SSH session recording and playback for compliance
- You want a web-based SSH client with role-based access control
- You need unified access for SSH, Kubernetes, databases, and web applications
- You require just-in-time access with time-limited certificates
- You need to comply with SOC 2, HIPAA, or PCI-DSS audit requirements

## Why Self-Host SSH Certificate Management?

Self-hosting SSH certificate infrastructure provides critical security and compliance benefits:

- **Eliminate SSH key sprawl**: Instead of managing hundreds of `authorized_keys` files across servers, you manage a single CA. User access is granted through certificate issuance, not key distribution
- **Short-lived credentials**: Certificates expire automatically. A 24-hour certificate means a compromised key is useless after a day. Contrast this with traditional SSH keys that never expire until manually revoked
- **Automatic revocation**: When an employee leaves, you do not need to update `authorized_keys` on every server. The CA simply stops issuing certificates for that user
- **Compliance and auditing**: Certificate issuance logs provide a clear record of who received access and when. Teleport goes further with full session recording, showing exactly what commands were executed
- **Zero vendor dependency**: Cloud SSH solutions (AWS Systems Manager, Azure Arc) tie your access management to a specific cloud provider. Self-hosted solutions work identically across AWS, GCP, Azure, and bare metal

For SSH security hardening, see our [Fail2ban vs SSHGuard vs CrowdSec guide](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/). If you need TLS certificate automation alongside SSH certificates, check our [cert-manager vs Lego vs ACME.SH comparison](../2026-04-19-cert-manager-vs-lego-vs-acme-sh-self-hosted-tls-certificate-automation-guide/). For Kubernetes access management, our [Teleport guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/) covers container security hardening.

## FAQ

### What is the difference between SSH keys and SSH certificates?

SSH keys are a public/private key pair where the public key is placed in `authorized_keys` on each server. SSH certificates are public keys signed by a Certificate Authority (CA). Instead of trusting individual keys, servers trust the CA's public key. The CA can issue time-limited certificates with embedded principals (allowed usernames), extensions (capabilities), and critical options (source IP restrictions).

### How long should SSH certificates be valid?

For user certificates, 8-24 hours is typical. The certificate should be valid long enough for a work session but short enough that compromise has limited impact. For host certificates, longer lifetimes (1 year) are acceptable since host keys change less frequently. Teleport defaults to very short lifetimes (minutes), while step-ca and Vault allow you to configure any duration.

### Can I use SSH certificates with existing SSH keys?

Yes. SSH certificates work on top of existing SSH key pairs. You generate a key pair as normal, then submit the public key to your CA (step-ca, Vault, or Teleport) for signing. The CA returns a certificate file that you use alongside your private key. Your private key never leaves your machine.

### What happens when an SSH certificate expires?

When a certificate expires, the SSH server rejects the connection because the certificate is no longer valid. The user must request a new certificate from the CA. This is typically automated: `step ssh login`, `vault ssh`, or `tsh login` will issue a fresh certificate. The old private key remains valid but needs a new signature.

### Do I need to restart sshd after configuring SSH certificates?

Yes, after adding `TrustedUserCAKeys` to `/etc/ssh/sshd_config`, you must restart the SSH daemon: `systemctl restart sshd`. However, this does not disconnect existing sessions. Only new connections will use certificate authentication.

### Can SSH certificates replace passwords entirely?

Yes. With SSH certificates, users authenticate by presenting a valid certificate signed by the trusted CA. No password is needed on the SSH server side. The user's identity is established during certificate issuance (via OAuth, SSO, or other authentication at the CA level), not during the SSH connection itself.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SSH Certificate Management: step-ca vs Vault vs Teleport (2026)",
  "description": "Compare step-ca, HashiCorp Vault, and Teleport for self-hosted SSH certificate management. Covers deployment, configuration, and when to use each tool.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
