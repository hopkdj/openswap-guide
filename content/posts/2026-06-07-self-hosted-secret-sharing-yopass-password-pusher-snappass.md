---
title: "Self-Hosted One-Time Secret Sharing: Yopass vs Password Pusher vs SnapPass"
date: "2026-06-07"
tags: ["password-sharing", "secret-management", "security", "privacy", "encryption", "self-hosted"]
draft: false
---

## Why Self-Host Your Secret Sharing?

Sending passwords, API keys, and sensitive information over email, Slack, or messaging apps is a security anti-pattern. Those messages persist indefinitely in chat logs, email archives, and backups — creating a trail of secrets scattered across multiple systems. One-time secret sharing tools solve this by generating expiring links that self-destruct after being viewed.

Self-hosting a secret sharing service gives you control over where your sensitive data lives. No third party sees your secrets, you control the retention policy, and you can integrate the service with your existing authentication infrastructure. For teams handling credentials, database connection strings, or customer data, running your own instance is a compliance requirement rather than a convenience.

Whether you're sharing database passwords, API tokens, or SSH keys with colleagues, self-hosting ensures these critical secrets never touch a third-party server you don't control. For managing long-lived secrets in Kubernetes, see our [Kubernetes secrets management guide](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/). For encrypted backup strategies, our [encrypted backup comparison](../2026-04-22-duplicati-vs-duplicacy-vs-duplicity-self-hosted-encrypted-backup-2026/) covers protecting data at rest.

## One-Time Secret Tools Compared

Three mature open source projects lead the self-hosted secret sharing space. Each takes a slightly different approach to the same core problem:

| Feature | Yopass | Password Pusher | SnapPass |
|---------|--------|-----------------|----------|
| **GitHub Stars** | 2,825+ | 3,035+ | 898+ |
| **Language** | Go | Ruby on Rails | Python (Flask) |
| **Encryption** | Client-side (browser) | Server-side (AES-256) | Server-side (Fernet) |
| **Expiration** | Configurable views/time | Configurable views/days | Configurable time |
| **One-Time View** | Yes (configurable) | Yes (configurable) | Yes |
| **File Attachments** | Yes | No (text only) | No (text only) |
| **Password Protection** | Optional | Optional | No |
| **REST API** | Yes | Yes | Yes |
| **CLI Client** | Yes (yopass CLI) | Yes (pwpush CLI) | No |
| **Database** | Memcached or Redis | PostgreSQL/MySQL/SQLite | Redis |
| **Docker Image** | Yes (GHCR) | Yes (Docker Hub) | Yes (Docker Hub) |

### Yopass — Client-Side Encryption Focus

Yopass takes the strongest privacy stance by encrypting secrets in the browser before they ever leave the user's machine. The server only sees ciphertext — it cannot decrypt your secrets even if compromised. The decryption key is embedded in the share URL fragment (the part after `#`), which browsers never send to the server.

```yaml
# docker-compose.yml for Yopass
version: '3'
services:
  yopass:
    image: ghcr.io/jhaals/yopass:latest
    ports:
      - "8080:1337"
    environment:
      - MEMCACHED=memcached:11211
      - MAX_LENGTH=10000
    depends_on:
      - memcached

  memcached:
    image: memcached:latest
    entrypoint: memcached -m 64 -I 1M
```

Yopass also supports file attachments up to a configurable size limit, making it useful for sharing certificates, SSH keys, and configuration files — not just text secrets. The optional password protection adds a second layer: even if someone intercepts the link, they need the password to decrypt.

### Password Pusher — Enterprise-Ready Features

Password Pusher has the most comprehensive feature set, targeting enterprise teams who need audit trails, branding, and granular expiration controls. It supports multiple database backends (PostgreSQL for production, SQLite for quick testing), LDAP/OIDC authentication, and detailed access logs showing when a secret was viewed and by whom.

```yaml
# docker-compose.yml for Password Pusher (with PostgreSQL)
version: '3'
services:
  pwpush:
    image: pglombardo/pwpush:latest
    ports:
      - "5100:5100"
    environment:
      DATABASE_URL: "postgresql://pwpush:pwpush@postgres:5432/pwpush"
      PWPUSH_MAILER_SENDER: "noreply@example.com"
      PWPUSH_FQDN: "pwpush.example.com"
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: pwpush
      POSTGRES_PASSWORD: pwpush
      POSTGRES_DB: pwpush
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

Password Pusher's CLI tool (`pwpush`) is particularly useful for automation — you can pipe secrets directly from scripts:

```bash
# Generate and share a random password
openssl rand -base64 24 | pwpush

# Share with 1-day expiry and 2-view limit
echo "API_KEY=sk-abc123" | pwpush --days 1 --views 2
```

The optional "deletable by viewer" setting lets recipients actively destroy a secret after they've used it, providing confirmation that sensitive material has been consumed.

### SnapPass — Minimalist and Lightweight

SnapPass is the simplest of the three — a single Python Flask application backed by Redis. It does one thing well: accept a secret, generate a one-time URL, and delete the secret after the first view. There's no authentication, no file attachments, no CLI — just dead-simple secret sharing.

```yaml
# docker-compose.yml for SnapPass
version: '3'
services:
  snappass:
    image: pinterest/snappass:latest
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
      - NO_SSL=True
      - STATIC_URL=false
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
```

SnapPass uses Fernet symmetric encryption for stored secrets and supports configurable expiration via the `SECRET_EXPIRY` parameter. Its simplicity makes it ideal for teams that want a no-frills tool that "just works" with near-zero maintenance overhead. The entire application fits in a few hundred lines of Python.

## Deployment and Reverse Proxy Setup

All three tools are designed to run behind a reverse proxy. Here's a typical Caddy configuration that handles TLS termination:

```caddy
secrets.example.com {
    reverse_proxy localhost:8080
}

# Or with Nginx
# server {
#     listen 443 ssl;
#     server_name secrets.example.com;
#     location / {
#         proxy_pass http://localhost:8080;
#     }
# }
```

## Why Self-Host Instead of Using a Public Service

Public secret sharing services exist (pwpush.com, yopass.se), but self-hosting provides distinct advantages:

1. **Data sovereignty**: Your secrets never leave your infrastructure. For organizations subject to GDPR, HIPAA, or SOC 2, this is non-negotiable.
2. **No trust required**: With Yopass's client-side encryption, even you can't read the secrets. Public services could theoretically log plaintext before encryption.
3. **Custom expiration policies**: Set default retention to hours instead of days, or enforce mandatory viewer limits.
4. **Integration**: Embed secret sharing into internal tools via API, or add SSO with your existing identity provider.

## Integration Patterns and Automation

The real power of self-hosted secret sharing emerges when you integrate it with existing workflows. Here are common patterns:

**CI/CD Pipeline Integration**: Use the Password Pusher CLI in your deployment scripts to share staging credentials with QA engineers or deliver production database passwords to on-call staff. The `pwpush` command accepts stdin, making it scriptable:

```bash
# In a CI pipeline, generate and share temporary DB credentials
vault read -field=password database/creds/readonly | pwpush --days 1 --views 3
```

**Helpdesk and IT Support**: When a user calls about a password reset, instead of reading the temporary password over the phone, generate it and share via Password Pusher. The one-time view limit ensures the password isn't reused, and the audit log confirms when the user received it.

**Incident Response**: During security incidents, avoid sharing API keys and access tokens in Slack or email — these channels may be compromised. Use Yopass for client-side encrypted sharing of incident response credentials, ensuring even the collaboration platform can't leak them.

**API-First Workflows**: All three tools expose REST APIs. Password Pusher has the most mature API with JSON push endpoints and webhook callbacks. Yopass's API is simpler but supports the core create-share-retrieve cycle. SnapPass offers a basic API that returns the secret URL.

## FAQ

### Is client-side encryption really more secure?

It depends on your threat model. Client-side encryption (Yopass) prevents the server operator from reading secrets. Server-side encryption (Password Pusher, SnapPass) protects data at rest but the server has access to plaintext during processing. For sharing secrets within your organization where you trust the server, the difference is minimal. For sharing with external parties, client-side encryption provides stronger guarantees.

### Can these tools handle secrets larger than a few kilobytes?

Yopass supports file attachments with configurable size limits. Password Pusher handles text up to 1MB by default (configurable). SnapPass is designed for shorter text like passwords and tokens. For sharing large configuration files, Yopass or a dedicated file transfer tool is more appropriate.

### How do I prevent brute-force attempts on shared links?

All three tools use cryptographically random URLs (typically 128+ bits of entropy), making brute-force attacks computationally infeasible. Yopass adds decryption key entropy on top. You can further protect links by enabling password protection (Yopass, Password Pusher) and setting short expiration times.

### What happens to secrets after expiration?

Yopass deletes secrets from Memcached/Redis on expiry. Password Pusher marks them as expired in the database but retains metadata for audit purposes. SnapPass removes the key from Redis immediately on first view or expiry. All three ensure the plaintext is not recoverable after expiration in normal operation.

### Which one should I choose for a small team?

For teams of 2-10 people, Password Pusher offers the best balance of features and simplicity. The PostgreSQL backend provides durability, the API enables automation, and the CLI tool integrates well with dev workflows. Yopass is better if privacy is paramount (client-side encryption). SnapPass is ideal if you want something you can deploy in 30 seconds and never think about again.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted One-Time Secret Sharing: Yopass vs Password Pusher vs SnapPass",
  "description": "Compare self-hosted one-time secret sharing tools. Yopass uses client-side encryption for maximum privacy, Password Pusher offers enterprise audit features, and SnapPass provides minimalist simplicity. Includes Docker Compose configs and deployment guide.",
  "datePublished": "2026-06-07",
  "dateModified": "2026-06-07",
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
