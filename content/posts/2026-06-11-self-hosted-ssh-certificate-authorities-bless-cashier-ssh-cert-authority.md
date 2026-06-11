---
title: "Self-Hosted Lightweight SSH Certificate Authorities: BLESS vs Cashier vs ssh-cert-authority"
date: "2026-06-11"
tags: ["ssh", "security", "certificate-authority", "devops", "infrastructure", "access-management", "zero-trust"]
draft: false
---

## Introduction

SSH keys are the backbone of server access management, but at scale they become a nightmare. Key rotation, revocation, and distribution across hundreds of servers and developers create security gaps that attackers exploit. SSH Certificate Authorities (CAs) solve this by issuing short-lived, automatically expiring certificates — no more stale authorized_keys files or forgotten deploy keys.

While enterprise solutions like HashiCorp Vault and Teleport offer comprehensive SSH CA capabilities, they come with significant operational complexity. For teams that need focused, lightweight SSH certificate management, three open-source tools stand out: **Netflix's BLESS**, **Cashier**, and **ssh-cert-authority**.

## Comparison Table

| Feature | BLESS (Netflix) | Cashier | ssh-cert-authority |
|---------|-----------------|---------|-------------------|
| **Architecture** | AWS Lambda function | Go daemon with OAuth | Go CLI + server |
| **Certificate Type** | SSH user certificates | SSH user certificates | SSH user + host certificates |
| **Authentication** | AWS IAM (via Lambda) | OAuth2/OIDC (Google, GitHub, Okta) | SSH key + config-based policies |
| **Deployment Model** | Serverless (AWS Lambda + KMS) | Self-hosted daemon | Self-hosted binary |
| **Key Storage** | AWS KMS (encrypted) | Local or cloud KMS | On-disk CA key |
| **Certificate Lifetime** | Configurable (typically 5-30 min) | Configurable (typically 1-24h) | Configurable (per-policy) |
| **Audit Logging** | AWS CloudTrail | Built-in logging | File-based logging |
| **Multi-Factor Auth** | AWS IAM MFA policies | Via OAuth provider MFA | Not built-in |
| **Docker Support** | Community Dockerfile | Official Docker image | Single binary (no Docker needed) |
| **GitHub Stars** | 2,760+ | 730+ | 740+ |
| **Language** | Python | Go | Go |

## BLESS: Netflix's Serverless SSH CA

[BLESS](https://github.com/Netflix/bless), developed by Netflix's security team, takes a unique approach to SSH certificate management — it runs entirely as an AWS Lambda function, using AWS KMS for cryptographic operations and IAM for authentication.

### Key Features

- **Serverless architecture**: No long-running server to maintain or patch — Lambda handles scaling
- **KMS-backed CA key**: The SSH CA private key is encrypted at rest in AWS KMS and never leaves
- **IAM-based authentication**: Users authenticate via their AWS IAM credentials, leveraging existing AWS access controls
- **Ultra-short-lived certs**: Designed for certificates lasting 5-30 minutes, dramatically reducing the blast radius of compromised credentials
- **CloudTrail auditing**: Every certificate issuance is logged in AWS CloudTrail for compliance
- **Region-agnostic**: Can be deployed across multiple AWS regions for high availability

### Architecture

```
User (AWS CLI) → AWS API Gateway → Lambda (BLESS) → AWS KMS (sign cert)
                                                        ↓
                                                SSH Certificate returned
```

### Docker Compose (Simulated Local Development)

```yaml
version: "3.8"
services:
  bless-local:
    image: ghcr.io/lyft/bless:latest
    container_name: bless
    ports:
      - "9999:9999"
    environment:
      - BLESS_CA_PRIVATE_KEY=kms://your-kms-key-arn
      - BLESS_AWS_REGION=us-east-1
      - BLESS_USER_ROLE=arn:aws:iam::123456789:role/bless-user
      - BLESS_LOGGING_LEVEL=INFO
    restart: unless-stopped
```

**Important**: BLESS requires an AWS account with Lambda, API Gateway, KMS, and IAM configured. For non-AWS environments, Cashier or ssh-cert-authority are better choices.

### Client Usage

```bash
# Request an SSH certificate from BLESS
blessclient --region us-east-1 --bastion_user myuser   --bastion_ip bastion.example.com --remote_username ubuntu

# The client sends the user's SSH public key to BLESS,
# which returns a signed certificate valid for 15 minutes
```

## Cashier: OAuth-Backed SSH CA for Modern Teams

[Cashier](https://github.com/nsheridan/cashier) is a Go-based SSH certificate authority that integrates with your existing identity provider via OAuth2/OIDC. Instead of managing SSH keys directly, users authenticate through Google Workspace, GitHub, Okta, or any OIDC-compatible provider.

### Key Features

- **OAuth2/OIDC integration**: Support for Google, GitHub, GitLab, Okta, Azure AD, and any OIDC provider
- **Web-based certificate issuance**: Users visit a web portal, authenticate via SSO, and receive an SSH certificate
- **Configurable certificate lifetime**: Default 24-hour certificates with configurable maximum duration
- **Just-in-time access**: Certificates are issued on-demand, not pre-provisioned
- **ssh-agent integration**: Cashier can add certificates directly to the user's SSH agent
- **Prometheus metrics**: Built-in metrics endpoint for monitoring and alerting
- **Audit logging**: Structured logging with certificate issuance details

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  cashier:
    image: nsheridan/cashier:latest
    container_name: cashier
    ports:
      - "10000:10000"
    environment:
      - CASHIER_SERVER_ADDR=:10000
      - CASHIER_SERVER_URL=https://ssh-ca.yourdomain.com
      - CASHIER_SSH_SIGNING_KEY=/etc/cashier/ca_key
      - CASHIER_SSH_MAX_AGE=24h
      - CASHIER_OAUTH_PROVIDER=google
      - CASHIER_OAUTH_CLIENT_ID=your-google-client-id
      - CASHIER_OAUTH_CLIENT_SECRET=your-google-client-secret
      - CASHIER_OAUTH_REDIRECT_URL=https://ssh-ca.yourdomain.com/auth/callback
    volumes:
      - ./ca_key:/etc/cashier/ca_key:ro
      - ./cashier-data:/data
    restart: unless-stopped
```

### SSH Server Configuration

```bash
# On each target server, add to /etc/ssh/sshd_config:
TrustedUserCAKeys /etc/ssh/cashier-ca.pub

# Restart SSH
sudo systemctl restart sshd

# Now any certificate signed by Cashier's CA is trusted
```

### Nginx Reverse Proxy Configuration

```nginx
server {
    listen 443 ssl;
    server_name ssh-ca.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/ssh-ca.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ssh-ca.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## ssh-cert-authority: Minimalist CLI-Driven CA

[ssh-cert-authority](https://github.com/cloudtools/ssh-cert-authority) takes the simplest possible approach: a single Go binary that signs SSH certificates based on configuration-defined policies. No web UI, no OAuth, no serverless — just a CLI tool for operators.

### Key Features

- **Policy-based access**: Define who can access which servers as which user in YAML configuration
- **Host certificate support**: Sign both user and host certificates (BLESS and Cashier focus on user certs)
- **Principals management**: Control which usernames a certificate grants access to
- **Command restriction**: Limit what commands can be executed via SSH `ForceCommand`
- **Source IP restriction**: Bind certificates to specific source IP addresses
- **Extensions support**: Add custom SSH certificate extensions

### Installation and Configuration

```bash
# Download the binary
curl -L -o ssh-cert-authority https://github.com/cloudtools/ssh-cert-authority/releases/latest/download/ssh-cert-authority-linux-amd64
chmod +x ssh-cert-authority

# Generate CA key pair
ssh-keygen -t ed25519 -f ca_key -C "SSH CA"
```

### Policy Configuration

```yaml
# /etc/ssh-cert-authority/config.yaml
certificate_authority:
  private_key_path: /etc/ssh-cert-authority/ca_key
  public_key_path: /etc/ssh-cert-authority/ca_key.pub

policies:
  - name: developers
    users:
      - alice
      - bob
    servers:
      - "*.dev.example.com"
      - "staging.example.com"
    principals:
      - ubuntu
      - deploy
    max_validity: 12h
    extensions:
      permit-X11-forwarding: false
      permit-agent-forwarding: false

  - name: admins
    users:
      - charlie
    servers:
      - "*"
    principals:
      - root
      - ubuntu
    max_validity: 4h
    extensions:
      permit-X11-forwarding: true
      permit-agent-forwarding: true
```

## Why Self-Host Your SSH CA?

Managing SSH access at scale without a certificate authority leads to three common security failures: stale authorized_keys entries from former employees, developers sharing private keys for convenience, and inability to revoke access quickly during security incidents.

SSH certificates solve all three — certificates automatically expire, eliminating stale access. Each developer gets their own certificate, tied to their identity, making key sharing pointless. And if needed, you can rotate the CA key to invalidate all certificates simultaneously.

For teams already using [enterprise certificate management with step-ca or Vault](../2026-04-25-step-ca-vs-teleport-vs-vault-self-hosted-ssh-certificate-management-guide-2026/), these lightweight alternatives fill a different niche. BLESS excels in AWS-native environments where serverless operations are preferred. Cashier shines when you want OAuth-based SSO without deploying a full secrets management platform. And ssh-cert-authority is ideal for small teams that want policy-based SSH access with minimal infrastructure overhead.

If your infrastructure involves [centralized intrusion prevention](../2026-04-24-fail2ban-vs-sshguard-vs-crowdsec-self-hosted-intrusion-prevention-2026/), SSH certificates complement those defenses by ensuring that even if an attacker obtains a key, it'll expire before they can use it.

For teams managing [self-hosted secrets rotation](../2026-04-25-vault-vs-infisical-vs-passbolt-self-hosted-secrets-rotation-guide-2026/), adding an SSH CA eliminates the need to rotate SSH keys entirely — just issue new certificates on each login.

## Choosing the Right Tool

**Choose BLESS if:**
- Your infrastructure is entirely on AWS
- You want serverless operations with no servers to patch
- You already use IAM for access control
- You need ultra-short-lived certificates (5-30 minutes)

**Choose Cashier if:**
- Your team uses Google Workspace, GitHub, or Okta for SSO
- You want a web-based, user-friendly certificate issuance flow
- You need audit logging and Prometheus metrics out of the box
- Your infrastructure spans multiple cloud providers

**Choose ssh-cert-authority if:**
- You want the simplest possible deployment (single binary)
- You need both user AND host certificate signing
- You prefer configuration-as-code (YAML policies)
- You're in an air-gapped or non-cloud environment

## FAQ

### How is this different from SSH key pairs?

Traditional SSH keys have no built-in expiration — once a public key is in authorized_keys, access is permanent until someone removes it. SSH certificates include an expiration timestamp after which the server rejects them automatically. Certificates also carry metadata (principals, extensions, source IP) that provides finer-grained access control than keys.

### Can I use these tools without a cloud provider?

Cashier and ssh-cert-authority run entirely on your own infrastructure with no cloud dependencies. BLESS requires AWS (Lambda + KMS). For on-premises deployments, Cashier with a local OIDC provider (like Keycloak or Authentik) is the most full-featured option.

### What happens when a certificate expires?

The SSH server rejects the connection with "certificate expired." Users must re-authenticate and obtain a new certificate. This is the security model — frequent re-authentication ensures access is always tied to a valid identity.

### Do I need to modify SSH server configuration?

Yes, you need to add the CA's public key to each server's `TrustedUserCAKeys` directive in `/etc/ssh/sshd_config`. Once configured, any certificate signed by that CA is trusted for any user. This is a one-time setup per server.

### How does certificate revocation work?

SSH supports certificate revocation lists (CRLs) via the `RevokedKeys` directive. However, with short-lived certificates (under 24 hours), revocation is rarely necessary — the certificate expires before it can be misused. For immediate revocation, rotate the CA key and reissue certificates to authorized users.

### Can I use these alongside existing SSH key infrastructure?

Yes. SSH servers can trust both authorized_keys and signed certificates simultaneously. You can phase in certificate-based access without disrupting existing key-based access, then gradually remove authorized_keys entries.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Lightweight SSH Certificate Authorities: BLESS vs Cashier vs ssh-cert-authority",
  "description": "Compare BLESS, Cashier, and ssh-cert-authority for self-hosted SSH certificate management. Covers serverless Lambda CA, OAuth-backed access, and policy-based key signing.",
  "datePublished": "2026-06-11",
  "dateModified": "2026-06-11",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
