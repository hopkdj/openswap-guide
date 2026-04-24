---
title: "Step-CA vs Teleport vs Vault: Self-Hosted SSH Certificate Management Guide 2026"
date: 2026-04-25
tags: ["comparison", "guide", "self-hosted", "ssh", "security", "certificates"]
draft: false
description: "Compare step-ca, Teleport, and HashiCorp Vault for self-hosted SSH certificate management. Complete guide with Docker configs, comparison table, and deployment instructions."
---

Managing SSH access at scale with static public keys is a security nightmare. When engineers leave the company or rotate devices, you must manually revoke keys on every server. SSH certificate-based authentication solves this by issuing short-lived, automatically expiring credentials — but which self-hosted tool should you use to act as your Certificate Authority (CA)?

In this guide, we compare three production-ready open-source solutions: **[step-ca](https://github.com/smallstep/certificates)** (8.4k stars), **[Teleport](https://github.com/gravitational/teleport)** (20k stars), and **[HashiCorp Vault](https://github.com/hashicorp/vault)** (35k stars). Each can serve SSH certificates, but they differ significantly in complexity, feature set, and operational overhead.

For related reading, see our [self-hosted SSH bastion server guide](../self-hosted-ssh-bastion-jump-server-teleport-guacamole-trysail-guide-2026/) and [PKI certificate management with step-ca](../self-hosted-pki-certificate-management-step-ca-caddy-nginx-proxy-manager-2026/). If you're building a broader authentication infrastructure, our [lightweight SSO comparison](../2026-04-21-casdoor-vs-zitadel-vs-authentik-lightweight-sso-guide-2026/) covers complementary tools.

## Why Use SSH Certificates Instead of Static Keys

SSH public key authentication has been the default for decades, but it has fundamental problems at any scale beyond a handful of servers:

- **No automatic expiration** — A deployed public key works forever until manually removed
- **No revocation mechanism** — Revoking access requires updating `authorized_keys` on every target server
- **No identity metadata** — A public key doesn't tell you who owns it or why it was granted
- **Audit gaps** — You can't easily answer "who had access to production on March 15th?"

SSH certificates solve all of these problems. Instead of distributing public keys to every server, you configure servers to trust a single Certificate Authority (CA). The CA signs short-lived certificates (e.g., 1-hour or 24-hour validity) that embed identity information — username, roles, permitted principals. When a certificate expires, access is automatically revoked with no manual intervention.

The tradeoff is that you need a CA service to issue and manage certificates. That's where step-ca, Teleport, and Vault come in.

## SSH Certificate Management: Feature Comparison

| Feature | step-ca | Teleport | HashiCorp Vault |
|---------|---------|----------|-----------------|
| **Stars** | 8,433 | 20,181 | 35,493 |
| **Language** | Go | Go | Go |
| **License** | Mozilla Public 2.0 | Apache 2.0 (Community), Elastic (Enterprise) | BUSL 1.1 |
| **SSH Certificates** | ✅ Yes | ✅ Yes | ✅ Yes (SSH Secrets Engine) |
| **X.509/TLS Certificates** | ✅ Yes | ✅ Yes | ✅ Yes (PKI Secrets Engine) |
| **ACME Support** | ✅ Yes | ❌ No | ❌ No |
| **Short-lived Certs** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Certificate Revocation** | ✅ CRL / OCSP | ✅ Built-in | ✅ CRL |
| **Role-Based Access** | ✅ Provisioners | ✅ RBAC + SSO | ✅ Policies |
| **SSO Integration** | ✅ OIDC, SAML, GitHub, GitLab, Azure AD, AWS | ✅ SAML, OIDC, GitHub, Okta | ✅ OIDC, SAML, LDAP, Okta, AWS |
| **Session Recording** | ❌ No | ✅ Yes (built-in) | ❌ No |
| **Kubernetes Access** | ❌ No | ✅ Yes (Kube agent) | ✅ Yes (K8s auth) |
| **Database Access** | ❌ No | ✅ Yes | ✅ Yes |
| **Application Proxy** | ❌ No | ✅ Yes (App Access) | ❌ No |
| **Web UI** | ❌ No (CLI only) | ✅ Yes | ✅ Yes |
| **Docker Image** | `smallstep/step-ca` | `public.ecr.aws/gravitational/teleport-dockerless` | `hashicorp/vault` |
| **Storage Backend** | SQLite, PostgreSQL, MySQL, BadgerDB | SQLite, etcd, DynamoDB, Firestore | Raft, Consul, etcd, DynamoDB, S3 |
| **High Availability** | ✅ (with PostgreSQL/MySQL) | ✅ (with etcd/DynamoDB) | ✅ (with Consul/Raft) |

## Option 1: step-ca — Lightweight Certificate Authority

[step-ca](https://github.com/smallstep/certificates) by Smallstep is a purpose-built certificate authority that handles both X.509/TLS and SSH certificates. It's the simplest and most focused option — if you only need certificate issuance and nothing else, step-ca is your best bet.

**Strengths:**
- Minimal footprint — single binary, easy to deploy
- ACME protocol support (compatible with cert-manager, acme.sh)
- Multiple provisioner types (OIDC, JWK, AWS, GCP, Azure, K8s SA)
- Flexible storage backends including PostgreSQL for HA
- Open-source (MPL 2.0) with no feature gating

**Limitations:**
- No built-in web UI — all management via CLI (`step`)
- No session recording, proxy, or audit features
- Focused solely on certificates — not an access platform

### Deploying step-ca with Docker

```yaml
version: "3.8"

services:
  step-ca:
    image: smallstep/step-ca:latest
    container_name: step-ca
    ports:
      - "9000:9000"
    volumes:
      - ./step-config:/home/step/config
      - ./step-secrets:/home/step/secrets
    environment:
      - DOCKER_STEPCA_INIT_NAME=ssh-ca
      - DOCKER_STEPCA_INIT_DNS_NAMES=localhost,step-ca.internal
      - DOCKER_STEPCA_INIT_REMOTE_MANAGEMENT_ENABLED=true
      - STEPCA_PASSWORD_FILE=/run/secrets/ca-password
    secrets:
      - ca-password
    restart: unless-stopped

secrets:
  ca-password:
    file: ./ca-password.txt
```

After starting the container, initialize your SSH CA:

```bash
# Enter the container
docker exec -it step-ca sh

# Generate SSH CA key pair
step ssh init
step certificate create ssh-host-ca ssh-host-ca.crt ssh-host-ca.key --profile ssh-host-ca
step certificate create ssh-user-ca ssh-user-ca.crt ssh-user-ca.key --profile ssh-user-ca

# Copy the user CA public key to all target servers
scp ssh-user-ca.pub root@your-server:/etc/ssh/trusted-user-ca-keys.pub
```

Then configure SSH servers to trust your CA by adding to `/etc/ssh/sshd_config`:

```
TrustedUserCAKeys /etc/ssh/trusted-user-ca-keys.pub
```

Generate a short-lived SSH certificate for a user:

```bash
step ssh certificate alice id_ecdsa --principal alice --principal deploy \
  --not-after 24h \
  --provisioner "Google" \
  --token-file /tmp/auth-token
```

## Option 2: Teleport — Full Access Platform

[Teleport](https://github.com/gravitational/teleport) is the most feature-rich option. Beyond SSH certificate issuance, it provides a complete access plane: SSH proxy with session recording, Kubernetes access, database access, and application proxy — all with short-lived certificates and SSO-based authentication.

**Strengths:**
- All-in-one access platform — SSH, K8s, databases, applications
- Built-in session recording and audit log
- Rich web UI and role-based access control
- Native SSO integration (SAML, OIDC, GitHub, Okta)
- Teleport Community Edition is fully open-source (Apache 2.0)

**Limitations:**
- Overkill if you only need SSH certificates
- More complex deployment (auth server + proxy server)
- Enterprise features require paid license
- Larger operational footprint

### Deploying Teleport with Docker

Teleport requires two components: the auth server and the proxy. Here's a single-node deployment for testing:

```yaml
version: "3.8"

services:
  teleport:
    image: public.ecr.aws/gravitational/teleport-dockerless:16
    container_name: teleport
    hostname: teleport.example.com
    ports:
      - "3023:3023"   # SSH proxy
      - "3024:3024"   # Kubernetes proxy
      - "3025:3025"   # Auth server
      - "443:3080"    # Web UI / HTTPS proxy
      - "3080:3080"   # Web UI / HTTP proxy
    volumes:
      - ./teleport-config:/etc/teleport
      - ./teleport-data:/var/lib/teleport
    command: ["teleport", "start", "--diag-addr=0.0.0.0:3000"]
    restart: unless-stopped
```

Create the initial Teleport configuration file at `./teleport-config/teleport.yaml`:

```yaml
version: v3
teleport:
  nodename: teleport.example.com
  data_dir: /var/lib/teleport
  log:
    output: stderr
    severity: INFO
  ca_pin: ""
auth_service:
  enabled: "yes"
  listen_addr: 0.0.0.0:3025
  cluster_name: teleport.example.com
proxy_service:
  enabled: "yes"
  web_listen_addr: 0.0.0.0:3080
  public_addr: teleport.example.com:443
  ssh_public_addr: teleport.example.com:3023
  kube_public_addr: teleport.example.com:3024
ssh_service:
  enabled: "yes"
  labels:
    env: production
  commands:
    - name: hostname
      command: [hostname]
      period: 1m0s
```

After starting Teleport, create the initial admin user:

```bash
docker exec -it teleport tctl users add admin --roles=editor,access
# Follow the invitation link to set up your account
```

Connect a target server by installing the Teleport agent and configuring it to join the cluster:

```yaml
# teleport-agent-config.yaml
version: v3
teleport:
  nodename: app-server-01
  auth_token: /etc/teleport/token
  auth_servers:
    - teleport.example.com:3025
ssh_service:
  enabled: "yes"
  labels:
    role: application
    env: production
auth_service:
  enabled: "no"
proxy_service:
  enabled: "no"
```

## Option 3: HashiCorp Vault — Secrets Management with SSH Engine

[HashiCorp Vault](https://github.com/hashicorp/vault) is primarily a secrets management platform, but its SSH Secrets Engine can dynamically generate SSH credentials. It supports two modes: **OTP mode** (Vault generates a one-time password for SSH access) and **CA mode** (Vault acts as an SSH Certificate Authority, similar to step-ca and Teleport).

**Strengths:**
- Integrates with existing Vault infrastructure (if you already use it)
- Supports both OTP and CA modes for SSH
- Rich policy system with fine-grained access control
- Multiple storage backends with built-in HA (Raft)
- Audit logging for all secret access

**Limitations:**
- SSH is one feature among many — not the primary focus
- Business Source License (BUSL 1.1) — not fully open source
- More complex setup compared to dedicated SSH tools
- No built-in session recording or proxy functionality

### Deploying Vault with Docker

```yaml
version: "3.8"

services:
  vault:
    image: hashicorp/vault:1.18
    container_name: vault
    ports:
      - "8200:8200"
    volumes:
      - ./vault-config:/vault/config
      - ./vault-data:/vault/data
      - ./vault-file:/vault/file
    environment:
      - VAULT_ADDR=http://0.0.0.0:8200
    cap_add:
      - IPC_LOCK
    command: ["vault", "server", "-config=/vault/config/vault.hcl"]
    restart: unless-stopped
```

Create the Vault configuration at `./vault-config/vault.hcl`:

```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"
ui           = true
```

Initialize and unseal Vault:

```bash
# Initialize Vault (save the root token and unseal keys!)
docker exec -it vault vault operator init

# Unseal Vault (run 3 times with different unseal keys)
docker exec -it vault vault operator unseal <unseal-key-1>
docker exec -it vault vault operator unseal <unseal-key-2>
docker exec -it vault vault operator unseal <unseal-key-3>

# Login
docker exec -it vault vault login <root-token>
```

Enable the SSH Secrets Engine and configure CA mode:

```bash
# Enable SSH secrets engine
docker exec -it vault vault secrets enable ssh

# Configure as a signed CA
docker exec -it vault vault write ssh/config/ca generate_signing_key=true

# Create a role that allows signing SSH certificates
docker exec -it vault vault write ssh/roles/my-role \
  key_type=ca \
  allowed_users=alice,bob,deploy \
  allow_user_certificates=true \
  ttl=24h \
  max_ttl=72h \
  default_critical_options=""

# The trusted user CA public key is available at:
# GET /v1/ssh/public_key
```

Sign an SSH key for a user:

```bash
# Create a role that maps to a Vault policy
docker exec -it vault vault write ssh/roles/deploy-role \
  key_type=ca \
  allowed_users=deployer \
  allow_user_certificates=true \
  ttl=1h \
  default_extensions=permit-pty,permit-port-forwarding

# Sign a public key
curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
  -X POST http://localhost:8200/v1/ssh/sign/my-role \
  -d '{"public_key": "ssh-ed25519 AAAA... user@host", "valid_principals": "deployer"}'

# The response contains the signed certificate
```

## Deployment Comparison

For teams evaluating these tools, the operational complexity varies significantly:

| Criterion | step-ca | Teleport | Vault |
|-----------|---------|----------|-------|
| **Initial Setup Time** | ~15 minutes | ~30 minutes | ~45 minutes |
| **Components Required** | 1 (CA server) | 2 (auth + proxy) | 1 (Vault server) |
| **Client Tool** | `step` CLI | `tsh` CLI | `vault` CLI |
| **Server Agent Needed** | ❌ No | ✅ Yes (teleport-node) | ❌ No (CA mode) |
| **Configuration Complexity** | Low | Medium | High |
| **Learning Curve** | Shallow | Steep | Steep |
| **Community Support** | Active | Very Active | Very Active |
| **Documentation Quality** | Excellent | Excellent | Excellent |

## Choosing the Right Tool

The right choice depends on your requirements:

**Choose step-ca if:**
- You only need certificate issuance (SSH + TLS)
- You want the simplest, most lightweight option
- You need ACME protocol support for TLS automation
- You prefer a fully open-source tool (MPL 2.0)
- Your team already uses the `step` CLI for certificate management

**Choose Teleport if:**
- You need SSH access plus session recording and audit
- You want a unified access plane (SSH, K8s, databases, apps)
- You need SSO-based authentication with fine-grained RBAC
- You're managing infrastructure across multiple environments
- You want a web-based access dashboard for your team

**Choose Vault if:**
- You already run Vault for secrets management
- You need SSH access integrated with other secret types (API keys, DB credentials)
- You need OTP-based SSH access (not just certificates)
- You want fine-grained dynamic secret generation
- Your team is already familiar with Vault policies and workflows

For most teams starting from scratch with only SSH certificate needs, **step-ca** is the fastest path to production. Teams that need a broader access control plane should evaluate **Teleport**. Teams already invested in the HashiCorp ecosystem will find **Vault**'s SSH engine a natural extension.

## FAQ

### What is the difference between SSH keys and SSH certificates?
SSH public keys are permanent credentials that grant indefinite access until manually revoked. SSH certificates are short-lived credentials signed by a Certificate Authority (CA) that include identity information, expiration times, and permitted principals. When a certificate expires, access is automatically revoked without any server-side changes.

### Can I use SSH certificates with existing OpenSSH servers?
Yes. OpenSSH has supported certificate-based authentication since version 5.7 (2011). You simply configure `sshd_config` with `TrustedUserCAKeys` pointing to your CA's public key. No additional software is needed on target servers.

### How long should SSH certificates be valid?
Typical validity periods range from 1 hour to 24 hours for user certificates, and up to 30 days for host certificates. Shorter validity means faster automatic revocation but requires more frequent certificate renewal. Most production environments use 8-24 hour user certificates.

### Do I need to install an agent on every server?
With **step-ca** and **Vault** in CA mode, no — servers only need to trust the CA public key in `sshd_config`. With **Teleport**, you install a node agent on each server you want to manage through the Teleport proxy, which enables session recording and other advanced features.

### Is step-ca suitable for production use?
Yes. step-ca is used in production by thousands of organizations. For HA deployments, use PostgreSQL or MySQL as the storage backend instead of the default SQLite. The Smallstep team also offers a managed version (Smallstep PKI) if you prefer not to self-host.

### Can Vault generate SSH credentials without certificates?
Yes. Vault's SSH Secrets Engine supports **OTP mode**, where Vault generates a one-time password for SSH access instead of using certificates. In this mode, the Vault server temporarily opens a port on the target, the user SSH's through Vault with the OTP, and Vault injects the credential. This is useful when you can't modify `sshd_config` on target servers.

### How does Teleport compare to a traditional SSH bastion host?
Teleport replaces the traditional bastion host with a certificate-based proxy. Instead of SSHing through a jump server and managing its `authorized_keys`, Teleport issues short-lived certificates that allow direct access to target servers, with all sessions recorded and audited. It eliminates the bastion as a single point of failure and a credential management burden.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Step-CA vs Teleport vs Vault: Self-Hosted SSH Certificate Management Guide 2026",
  "description": "Compare step-ca, Teleport, and HashiCorp Vault for self-hosted SSH certificate management. Complete guide with Docker configs, comparison table, and deployment instructions.",
  "datePublished": "2026-04-25",
  "dateModified": "2026-04-25",
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
